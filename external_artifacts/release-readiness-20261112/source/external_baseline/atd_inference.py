"""Local-operator tactical ATD inference; agent validation uses synthetic files.

No default dataset paths, data discovery, GT, video, homography or Smart Tagging.
Import/help are I/O-free. Official inputs are opened only by an explicit local
operator invocation; no fitting/calibration or private-match inspection occurs.
"""
import argparse
from collections import Counter
from contextlib import closing
import csv
import json
import math
from pathlib import Path
import sqlite3
import xml.etree.ElementTree as ET

from .contracts import FrameKey
from .features import EntityPosition, FrameFeatureExtractor, FEATURE_NAMES, ContextFeatureExtractor, CONTEXT_NAMES
from .prepare import sha256
from .training import project_features, predict_raw
from .temporal import decode_probabilities
from .atd_periods import provider_periods,validate_periods,organizer_period_scope


def metadata(path,period_scope=None):
    """Parse Metrica FIFA metadata without positional roster assumptions.

    Dimensions are declared metres, x/y channels must be normalized, FPS=25.
    DataFormatSpecification frame ranges map raw groups to PlayerChannelRefs;
    changing lineups/order use their declared mapping. Provider half boundaries
    are inclusive 1-based ATD frames when provider mode is selected. Alternatively,
    an explicit verified organizer scope supplies already-normalized intervals.
    No mode infers an index base or merges the two halves into one recording.
    """
    root=ET.parse(path).getroot()
    for element in root.iter():element.tag=element.tag.rsplit('}',1)[-1]
    meta=root.find('Metadata') if root.tag!='Metadata' else root
    if meta is None:raise ValueError('FIFA Metadata required')
    if float(meta.findtext('./GlobalConfig/FrameRate','nan'))!=25:raise ValueError('25-Hz metadata required')
    length=float(meta.findtext('.//FieldSize/Width','nan'));width=float(meta.findtext('.//FieldSize/Height','nan'))
    if not all(math.isfinite(v) and v>0 for v in (length,width)):raise ValueError('finite positive pitch dimensions required')
    teams=[e.get('id') for e in meta.findall('./Teams/Team')]
    if len(teams)!=2 or len(set(teams))!=2 or not all(teams):raise ValueError('two unique teams required')
    score=meta.find('.//MatchParameters/Score')
    home=score.get('idLocalTeam') if score is not None else teams[0]
    away=score.get('idVisitingTeam') if score is not None else teams[1]
    if set((home,away))!=set(teams):raise ValueError('home/away metadata conflict')
    players={}
    for e in meta.findall('./Players/Player'):
        identity=e.get('id');team=e.get('teamId')
        if not identity or identity in players or team not in teams:raise ValueError('invalid player/team metadata')
        players[identity]='H' if team==home else 'A'
    channels={}
    for e in meta.findall('.//PlayerChannels/PlayerChannel'):
        identity=e.get('id');player=e.get('playerId');axis=e.get('channelId')
        if not identity or identity in channels or player not in players or not axis:raise ValueError('invalid player channel')
        channels[identity]=(player,axis)
    normalized={}
    for e in meta.findall('.//Channels/Channel'):
        if e.get('id') in ('x','y'):
            normalized.setdefault(e.get('id'),set()).add((e.findtext('Unit') or '').strip().lower())
    if any(normalized.get(axis)!={'normalized'} for axis in ('x','y')):
        raise ValueError('explicit normalized x/y channels required')
    parameters={}
    for e in meta.findall('./GlobalConfig/ProviderGlobalParameters/ProviderParameter'):
        name=e.findtext('Name');value=(e.findtext('Value') or '').strip()
        if name in parameters:raise ValueError('duplicate provider parameter')
        parameters[name]=value
    periods=(provider_periods(parameters) if period_scope is None
             else validate_periods(period_scope['periods']))
    if period_scope is None and any(parameters.get(name) for name in ('first_extra_half_start','first_extra_half_end','second_extra_half_start','second_extra_half_end')):
        raise ValueError('extra-time periods unsupported')
    formats=[]
    for spec in root.findall('./DataFormatSpecifications/DataFormatSpecification'):
        try:start,end=int(spec.attrib['startFrame']),int(spec.attrib['endFrame'])
        except (KeyError,ValueError) as error:raise ValueError('explicit integer layout bounds required') from error
        children=list(spec)
        # A layout lower bound of zero may cover raw ID 1; it does not rebase
        # row IDs. frames() still requires exactly 1..expected independently.
        if (start<0 or end<start or spec.get('separator')!=':' or len(children)!=3
                or children[0].tag!='StringRegister' or children[0].get('name')!='frameCount'
                or children[1].tag!='SplitRegister' or children[1].get('separator')!=';'
                or children[2].tag!='SplitRegister' or children[2].get('separator')!=','):
            raise ValueError('unsupported ATD format specification')
        layout=[];seen=set()
        for group in children[1]:
            if group.tag!='SplitRegister' or group.get('separator')!=',':raise ValueError('unsupported player group')
            refs=[channels.get(e.get('playerChannelId')) if e.tag=='PlayerChannelRef' else None for e in group]
            if not refs or any(r is None for r in refs) or len({r[0] for r in refs})!=1:raise ValueError('unresolved player channel reference')
            player=refs[0][0];axes=[r[1] for r in refs]
            if player in seen or len(set(axes))!=len(axes) or not {'x','y'}.issubset(axes):raise ValueError('invalid slot axes/player')
            seen.add(player);layout.append(dict(player=player,team=players[player],axes=axes))
        ball=[e.get('channelId') if e.tag=='BallChannelRef' else None for e in children[2]]
        if not layout or None in ball or len(set(ball))!=len(ball) or not {'x','y'}.issubset(ball):raise ValueError('invalid ball channels')
        formats.append(dict(start=start,end=end,players=layout,ball=ball))
    formats.sort(key=lambda f:f['start'])
    if not formats or any(a['end']>=b['start'] for a,b in zip(formats,formats[1:])):
        raise ValueError('nonoverlapping explicit ATD layouts required')
    return dict(length_m=length,width_m=width,fps=25,home_id=home,away_id=away,
        team_mapping='score local/visiting IDs' if score is not None else 'documented FIFA team order',periods=periods,formats=formats,
        period_scope=period_scope or dict(source='provider',output_convention='atd_1_based_inclusive'))


def normalized_pair(token, axes, length, width):
    """Return centred metre x/y; preserve missing axes and finite outside values.

    Empty/standalone NaN is an absent record. An explicit NaN,NaN pair is a
    present record with invalid coordinates. Extra declared axes (speed/z) are
    ignored, never treated as feature targets or player velocity continuity.
    """
    if token.strip().lower() in ('','nan','n'):return None
    values=token.split(',')
    if len(values)!=len(axes):raise ValueError('ATD channel count mismatch')
    result=[]
    for axis,scale in (('x',length),('y',width)):
        value=values[axes.index(axis)].strip()
        number=float(value) if value.lower() not in ('','nan','n') else float('nan')
        coordinate=((number-.5) if axis=='x' else (.5-number))*scale if math.isfinite(number) else None
        if coordinate is not None and not math.isfinite(coordinate):raise ValueError('ATD coordinate overflow')
        result.append(coordinate)
    return tuple(result)


def frames(path, meta, expected):
    """Stream exact ATD IDs 1..expected, emitting zero-based video-frame keys.

    Read every row once and reject duplicates/gaps/order errors. Metadata alone
    determines period scopes; rows outside them remain X, not inferred dead ball.
    No official IdFrame counter offset, time calibration or nearest-frame join.
    """
    if expected<1 or max(p[2] for p in meta['periods'])>expected:raise ValueError('half bounds exceed expected tactical length')
    number=0;format_index=0
    with Path(path).open(encoding='utf-8') as stream:
        for line in stream:
            fields=line.strip().split(':');number+=1
            if len(fields)!=3 or int(fields[0])!=number or number>expected:raise ValueError('ATD IDs must be exactly 1..expected')
            while format_index<len(meta['formats']) and meta['formats'][format_index]['end']<number:format_index+=1
            if format_index==len(meta['formats']) or meta['formats'][format_index]['start']>number:
                raise ValueError('frame has no declared ATD layout')
            spec=meta['formats'][format_index]
            groups=fields[1].split(';') if fields[1] else ['']*len(spec['players'])
            if len(groups)==len(spec['players'])+1 and groups[-1]=='':groups.pop()
            if len(groups)!=len(spec['players']):raise ValueError('ATD slot count differs from metadata layout')
            entities=[]
            for token,slot in zip(groups,spec['players']):
                xy=normalized_pair(token,slot['axes'],meta['length_m'],meta['width_m'])
                if xy is not None and any(v is not None for v in xy):
                    entities.append(EntityPosition(slot['player'],slot['team'],*xy))
            ball=normalized_pair(fields[2],spec['ball'],meta['length_m'],meta['width_m'])
            if ball is not None:entities.append(EntityPosition('BALL','BALL',*ball))
            period=next((p for p,a,b in meta['periods'] if a<=number<=b),None)
            yield number-1,period,(number-1)*40000,entities
    if number!=expected:raise ValueError(f'ATD row count {number} != {expected}')


def run(bundle, meta_path, raw_path, output, expected=199319,*,period_source='provider',game=None):
    """Local-only operator pipeline; synthetic tests are its agent validation.

    Save exact frame,label CSV, scoped raw/decoded probabilities/features and a
    hash manifest. Both halves decode independently; unscoped rows stay X. Input
    positions never fit anything, and neither GT nor official evaluators run.
    """
    from .inference_bundle import load_bundle, verify_bundle,safe_path
    import numpy as np
    meta_path,raw_path,output=Path(meta_path).resolve(strict=True),Path(raw_path).resolve(strict=True),Path(output).resolve()
    if output.exists():raise FileExistsError(output)
    descriptor=verify_bundle(bundle,check_runtime=True)
    hashes={str(p):sha256(p) for p in (meta_path,raw_path)}
    bundle_hash=sha256(Path(bundle).resolve()/'bundle_manifest.json')
    if period_source=='organizer-public':
        if 'organizer_metadata_file' not in descriptor:
            raise ValueError('bundle revision lacks public organizer metadata; use the revised bundle')
        public_path=safe_path(Path(bundle).resolve(),descriptor['organizer_metadata_file'])
        period_scope=organizer_period_scope(public_path,game,expected)
    elif period_source=='provider':
        if game is not None:raise ValueError('--game requires --period-source organizer-public')
        period_scope=None
    else:raise ValueError('unsupported period source; no full-recording fallback')
    meta=metadata(meta_path,period_scope)
    model,parameters=load_bundle(bundle)
    output.mkdir(parents=True)
    try:
        labels=np.full(expected,'X',dtype='U1');raw_labels=np.full(expected,'X',dtype='U1')
        # Bundle contract selects one extraction path; no feature-count guessing.
        context = len(descriptor['feature_names']) == 18
        feature_names = FEATURE_NAMES + CONTEXT_NAMES if context else FEATURE_NAMES
        extractor_type = ContextFeatureExtractor if context else FrameFeatureExtractor
        extractor=extractor_type(meta['length_m'],meta['width_m'])
        with closing(sqlite3.connect(output/'features.sqlite')) as db:
            db.execute('CREATE TABLE features(frame INTEGER PRIMARY KEY,period INTEGER,time_us INTEGER,'+','.join(n+' REAL' for n in feature_names)+')')
            batch=[]
            for frame,period,stamp,entities in frames(raw_path,meta,expected):
                if period is None:continue
                values=extractor.extract(FrameKey('tactical',period,frame),stamp,entities)
                batch.append((frame,period,stamp,*values.values()))
                if len(batch)==4096:
                    db.executemany('INSERT INTO features VALUES ('+','.join('?' for _ in batch[0])+')',batch);db.commit();batch.clear()
            if batch:db.executemany('INSERT INTO features VALUES ('+','.join('?' for _ in batch[0])+')',batch)
            db.commit()
            with closing(sqlite3.connect(output/'predictions.sqlite')) as predictions:
                predictions.execute('CREATE TABLE predictions(frame INTEGER PRIMARY KEY,period INTEGER,raw_label TEXT,label TEXT,p_H REAL,p_A REAL,p_D REAL)')
                for period,start,end in meta['periods']:
                    n=end-start+1;x=np.empty((n,len(feature_names)));keys=[];stamps=[]
                    for i,row in enumerate(db.execute('SELECT frame,time_us,'+','.join(feature_names)+' FROM features WHERE period=? ORDER BY frame',(period,))):
                        keys.append(FrameKey('tactical',period,row[0]));stamps.append(row[1]);x[i]=row[2:]
                    if len(keys)!=n:raise ValueError('incomplete scoped feature timeline')
                    indices = [feature_names.index(name) for name in descriptor['feature_names']]
                    raw,probabilities=predict_raw(model,x[:, indices])
                    decoded=decode_probabilities(keys,stamps,probabilities,parameters)
                    for k,r,d in zip(keys,raw,decoded):labels[k.source_frame]=d;raw_labels[k.source_frame]=r
                    predictions.executemany('INSERT INTO predictions VALUES (?,?,?,?,?,?,?)',
                        ((k.source_frame,period,str(r),str(d),*map(float,p)) for k,r,d,p in zip(keys,raw,decoded,probabilities)))
                predictions.commit()
                if predictions.execute('PRAGMA quick_check').fetchall()!=[('ok',)]:raise ValueError('prediction integrity failure')
            if db.execute('PRAGMA quick_check').fetchall()!=[('ok',)]:raise ValueError('feature integrity failure')
        for name,array in (('submission.csv',labels),('submission_raw.csv',raw_labels)):
            with (output/name).open('w',newline='',encoding='utf-8') as f:
                writer=csv.writer(f,lineterminator='\n');writer.writerow(['frame','label'])
                writer.writerows((i,str(v)) for i,v in enumerate(array))
        report=dict(rows=expected,frame_range=[0,expected-1],label_counts=dict(Counter(labels)),raw_label_counts=dict(Counter(raw_labels)),
            metadata_periods_ATD_1_based=meta['periods'],period_scope=meta['period_scope'],
            pitch_m=[meta['length_m'],meta['width_m']],team_mapping=meta['team_mapping'],
            scope_policy='X outside explicit per-half scope; no GT label/mask file read',fitting=False,scored=False,
            validation='exact row count/order and H/A/D/X labels constructed and checked; format only, not correctness')
        if len(labels)!=expected or set(labels)-set('HADX'):raise ValueError('submission contract failure')
        if any(sha256(Path(p))!=h for p,h in hashes.items()):raise ValueError('local input changed')
        verify_bundle(bundle,check_runtime=True)
        def write(name,value):(output/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n')
        write('report.json',report)
        write('manifest.json',dict(status='ready',atd_inference_version=2,inputs_sha256=hashes,bundle_manifest_sha256=bundle_hash,
            period_source=period_source,period_scope=meta['period_scope'],
            model_sha256=descriptor['model_sha256'],decoder_sha256=descriptor['decoder_sha256'],outputs_sha256={p.name:sha256(p) for p in output.iterdir() if p.is_file()},
            fitting=False,tuning=False,gt_access=False))
        print(json.dumps({'rows':expected,'submission':str(output/'submission.csv'),'scored':False},indent=2))
        return report
    except Exception as error:
        (output/'FAILED.json').write_text(json.dumps(dict(status='failed',error=str(error)))+'\n');raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('bundle','metadata','tracking','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--expected-frames',type=int,default=199319,help='tactical default; override only for external/synthetic fixtures')
    parser.add_argument('--period-source',choices=('provider','organizer-public'),default='provider',
        help='provider: two populated XML halves; organizer-public: documented per-half video scope in the verified bundle')
    parser.add_argument('--game',help='explicit organizer game ID; required only with organizer-public periods')
    parser.add_argument('--operator-local',action='store_true',help='explicit local operator execution; agent never invokes this on official inputs')
    args=parser.parse_args()
    if not args.operator_local:parser.error('--operator-local is required; no implicit official data access')
    run(args.bundle,args.metadata,args.tracking,args.output,args.expected_frames,
        period_source=args.period_source,game=args.game)


if __name__=='__main__':main()
