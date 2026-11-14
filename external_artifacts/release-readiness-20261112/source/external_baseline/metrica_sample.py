"""Observation-only inference on Metrica's public Sample Game 1/2 CSV format.

No dataset access/model imports on import/help. Events are never read, labels
never fitted, and no F1/accuracy is inferred without dense possession targets.
"""

import argparse
from collections import Counter
from contextlib import closing
import csv
from decimal import Decimal, InvalidOperation
import importlib.metadata
import json
import math
from pathlib import Path
import platform
import sqlite3
import time

from .contracts import FrameKey, STEP_US
from .features import EntityPosition, FrameFeatureExtractor, FEATURE_NAMES, FEATURE_UNITS
from .diagnostics import contiguous_runs
from .prepare import REPO, sha256, peak_memory_bytes, git_metadata
from .training import FEATURE_SETS, HGB_PARAMS, PACKAGES, predict_raw, project_features
from .temporal import decode_probabilities

LENGTH_M, WIDTH_M = 105.0, 68.0
UPSTREAM = 'https://github.com/metrica-sports/sample-data'


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n', encoding='utf-8')


def coordinate(value, length, invert=False):
    """Map normalized axis to centred metres; y grows up instead of down.

    Blank/NaN/infinity become None. Malformed text fails. Finite outside values
    remain outside, never clipped. This is a fixed unit conversion, not fitting.
    """
    if not value.strip():
        return None
    number = float(value)
    if not math.isfinite(number):
        return None
    result = (0.5-number if invert else number-0.5)*length
    if not math.isfinite(result):
        raise ValueError('coordinate conversion overflow')
    return result


def time_us(text):
    """Parse sample match-relative seconds exactly into integer microseconds.

    This is not a UTC timestamp. Relative times may restart in another period;
    only differences inside the same period establish 25-Hz continuity.
    """
    try:
        value = Decimal(text)*1_000_000
        if not value.is_finite() or value < 0 or value != value.to_integral_value():
            raise ValueError('nonnegative microsecond-resolution time required')
        return int(value)
    except InvalidOperation as error:
        raise ValueError('invalid match-relative time') from error


def tracking_rows(path, team):
    """Yield ((period, original frame), relative us, players, ball xy) in order.

    Strict three-row CSV header, explicit Home/Away mapping, unique player IDs,
    original gaps and periods 1/2. Fully unavailable roster slots are omitted;
    partial players remain present. Ball column always supplies one record,
    including an all-missing pair. Never infer on-pitch status from roster alone.
    """
    expected_team = {'H':'Home', 'A':'Away'}[team]
    with Path(path).open(newline='', encoding='utf-8-sig') as stream:
        reader = csv.reader(stream)
        try:
            tags, jerseys, names = [next(reader) for _ in range(3)]
        except StopIteration as error:
            raise ValueError('three-row tracking header required') from error
        width = len(names)
        if (names[:3] != ['Period','Frame','Time [s]'] or width < 5 or (width-3)%2
                or len(tags) != width or len(jerseys) != width):
            raise ValueError('unsupported tracking CSV header')
        players, ball_column, seen = [], None, set()
        for column in range(3, width, 2):
            name = names[column].strip()
            if names[column+1].strip():
                raise ValueError('expected paired x/y columns')
            if name.lower() == 'ball':
                if ball_column is not None:
                    raise ValueError('multiple ball columns')
                ball_column = column
            else:
                jersey = jerseys[column].strip()
                identity = 'Player'+jersey
                if (tags[column] != expected_team or not jerseys[column].strip()
                        or not name.startswith('Player') or name[6:].strip() != jersey or identity in seen):
                    raise ValueError('player identity/team header mismatch')
                seen.add(identity)
                players.append((column,team+':'+identity))
        if ball_column is None or not players:
            raise ValueError('players and one ball column required')
        previous, anchor = None, None
        for row in reader:
            if len(row) != width:
                raise ValueError('tracking row width mismatch')
            period, frame = int(row[0]), int(row[1])
            key = (period, frame)
            stamp = time_us(row[2])
            if period not in (1,2) or frame < 0 or (previous is not None and key <= previous):
                raise ValueError('unique ordered frames in periods 1/2 required')
            if anchor is None or anchor[0] != period:
                anchor = (period,frame,stamp)
            if stamp-anchor[2] != (frame-anchor[1])*STEP_US:
                raise ValueError('tracking time/frame spacing differs from 25 Hz')
            previous = key
            entities = []
            for column, identity in players:
                x = coordinate(row[column], LENGTH_M)
                y = coordinate(row[column+1], WIDTH_M, invert=True)
                if x is not None or y is not None:
                    entities.append(EntityPosition(identity,team,x,y))
            ball = (coordinate(row[ball_column], LENGTH_M),
                    coordinate(row[ball_column+1], WIDTH_M, invert=True))
            yield key,stamp,entities,ball


def merged_frames(home, away, match_id):
    """Merge ordered team streams by (period, frame), preserving their union.

    Same-key timestamps and duplicated ball axes must agree exactly (None-safe).
    Missing team rows stay missing; no nearest-time join, ball averaging, filling
    or synthetic frames are introduced. Memory holds one row from each stream.
    """
    readers = [iter(tracking_rows(home,'H')), iter(tracking_rows(away,'A'))]
    rows = [next(r,None) for r in readers]
    anchor = None
    while any(r is not None for r in rows):
        key = min(r[0] for r in rows if r is not None)
        current = [r for r in rows if r is not None and r[0] == key]
        if len(current) == 2 and (current[0][1] != current[1][1] or current[0][3] != current[1][3]):
            raise ValueError('team streams disagree on time or ball position')
        if anchor is None or anchor[0] != key[0]:
            anchor = (key[0],key[1],current[0][1])
        if current[0][1]-anchor[2] != (key[1]-anchor[1])*STEP_US:
            raise ValueError('merged team timeline differs from 25 Hz')
        entities = [e for r in current for e in r[2]]
        entities.append(EntityPosition('BALL','BALL',*current[0][3]))
        yield FrameKey(match_id,*key),current[0][1],entities
        for i,row in enumerate(rows):
            if row is not None and row[0] == key:
                rows[i] = next(readers[i],None)


def frozen_candidate(snapshot):
    """Verify the existing local frozen primary and runtime before loading it.

    Read only explicit snapshot/source bytes and metadata; no match data or test
    scores. Each saved model/decoder stays byte-identical. No candidate selection.
    """
    snapshot = Path(snapshot).resolve(strict=True)
    protocol_path = snapshot/'protocol.json'
    protocol = json.loads(protocol_path.read_text())
    manifest_path = snapshot/'snapshot_manifest.json'
    manifest = json.loads(manifest_path.read_text())
    if manifest.get('status') != 'ready' or protocol.get('status') != 'ready':
        raise ValueError('ready frozen snapshot required')
    for relative,digest in manifest['files_sha256'].items():
        path = (snapshot/relative).resolve(strict=True)
        path.relative_to(snapshot)
        if sha256(path) != digest:
            raise ValueError('snapshot file hash mismatch')
    for relative,digest in protocol['source_sha256'].items():
        if sha256(REPO/relative) != digest:
            raise ValueError('frozen core source changed')
    if protocol['packages'] != {p:importlib.metadata.version(p) for p in PACKAGES}:
        raise ValueError('frozen dependency versions differ')
    candidate = protocol['candidates'][protocol['primary']]
    if (candidate['feature_names'] != list(FEATURE_SETS['no-signed-position'])
            or candidate['hgb_params'] != HGB_PARAMS):
        raise ValueError('frozen 14-feature HGB required')
    paths = [protocol_path,manifest_path]
    for field,hash_field in (('model_file','model_sha256'),('parameters_file','parameters_sha256')):
        path = (snapshot/candidate[field]).resolve(strict=True)
        path.relative_to(snapshot)
        if sha256(path) != candidate[hash_field]:
            raise ValueError('frozen candidate hash mismatch')
        paths.append(path)
    return candidate,paths


def run(home, away, snapshot, output, match_id):
    """Convert external CSVs, infer frozen H/A/D, and publish new local artifacts.

    Outputs preserve original (period, source_frame) and relative microseconds,
    not official tactical indices or UTC. Missing is NULL/NaN and temporal state
    resets on periods/gaps. Events/targets are not accepted. No metrics without
    dense GT, no fitting/calibration, and no overwrite. Failure is never ready.
    """
    home,away = Path(home).resolve(strict=True),Path(away).resolve(strict=True)
    output = Path(output).resolve()
    if home == away or not match_id.strip():
        raise ValueError('distinct team files and explicit match ID required')
    if output.exists():
        raise FileExistsError(output)
    candidate,paths = frozen_candidate(snapshot)
    paths += [home,away]
    inputs = {str(p):sha256(p) for p in paths}
    sources = {str(p.relative_to(REPO)):sha256(p) for p in sorted((REPO/'external_baseline').glob('*.py'))}
    output.mkdir(parents=True)
    started = time.perf_counter()
    try:
        import numpy as np
        import joblib
        model = joblib.load(paths[2])
        if (list(model['feature_names']) != list(FEATURE_SETS['no-signed-position'])
                or model['model'].get_params() != HGB_PARAMS):
            raise ValueError('serialized model contract differs')
        parameters = json.loads(paths[3].read_text())
        summaries = {}
        extractor = FrameFeatureExtractor(LENGTH_M,WIDTH_M)
        with closing(sqlite3.connect(output/'features.sqlite')) as db:
            db.execute('CREATE TABLE features(match_id TEXT,period INTEGER,source_frame INTEGER,time_us INTEGER,'+
                       ','.join(n+' REAL' for n in FEATURE_NAMES)+',PRIMARY KEY(match_id,period,source_frame)) WITHOUT ROWID')
            batch=[]
            for key,stamp,entities in merged_frames(home,away,match_id):
                values=extractor.extract(key,stamp,entities)
                summary=summaries.setdefault(key.period,dict(frames=0,first_frame=key.source_frame,last_frame=key.source_frame,
                    complete_ball_frames=0,feature_defined={n:0 for n in FEATURE_NAMES}))
                summary['frames']+=1;summary['last_frame']=key.source_frame
                summary['complete_ball_frames']+=values['ball_xy_observed']
                for n,v in values.items():summary['feature_defined'][n]+=int(v is not None)
                batch.append((key.match_id,key.period,key.source_frame,stamp,*values.values()))
                if len(batch)==4096:
                    db.executemany('INSERT INTO features VALUES ('+','.join('?' for _ in batch[0])+')',batch)
                    db.commit();batch.clear()
            if batch:db.executemany('INSERT INTO features VALUES ('+','.join('?' for _ in batch[0])+')',batch)
            if sorted(summaries) != [1,2]:
                raise ValueError('complete sample requires both halves')
            metadata=dict(feature_names=FEATURE_NAMES,units=FEATURE_UNITS,coordinate_origin='pitch_center',
                x_positive='right',y_positive='up',fps=25,time_origin='sample-relative seconds, not UTC')
            db.execute('CREATE TABLE feature_metadata(json TEXT)')
            db.execute('INSERT INTO feature_metadata VALUES (?)',(json.dumps(metadata),))
            db.commit()
            with closing(sqlite3.connect(output/'predictions.sqlite')) as predictions, (output/'predictions.csv').open('w',newline='') as csv_file:
                predictions.execute('CREATE TABLE predictions(match_id TEXT,period INTEGER,source_frame INTEGER,time_us INTEGER,raw_label TEXT,label TEXT,p_H REAL,p_A REAL,p_D REAL,PRIMARY KEY(match_id,period,source_frame)) WITHOUT ROWID')
                writer=csv.writer(csv_file,lineterminator='\n')
                writer.writerow(['period','source_frame','time_s','raw_label','label','p_H','p_A','p_D'])
                for period,summary in sorted(summaries.items()):
                    n=summary['frames'];x=np.empty((n,len(FEATURE_NAMES)),dtype=float);keys=[];stamps=[]
                    rows=db.execute('SELECT match_id,period,source_frame,time_us,'+','.join(FEATURE_NAMES)+' FROM features WHERE period=? ORDER BY source_frame',(period,))
                    for i,row in enumerate(rows):
                        keys.append(FrameKey(*row[:3]));stamps.append(row[3]);x[i]=row[4:]
                    raw,probabilities=predict_raw(model['model'],project_features(x,'no-signed-position'))
                    decoded=decode_probabilities(keys,stamps,probabilities,parameters)
                    predictions.executemany('INSERT INTO predictions VALUES (?,?,?,?,?,?,?,?,?)',
                        ((k.match_id,k.period,k.source_frame,t,str(r),str(d),*map(float,p)) for k,t,r,d,p in zip(keys,stamps,raw,decoded,probabilities)))
                    writer.writerows((k.period,k.source_frame,f'{t/1_000_000:.6f}',str(r),str(d),*map(float,p))
                                     for k,t,r,d,p in zip(keys,stamps,raw,decoded,probabilities))
                    runs=contiguous_runs(keys,stamps,[True]*n)
                    summary.update(raw_label_counts=dict(Counter(raw)),decoded_label_counts=dict(Counter(decoded)),
                        contiguous_runs=len(runs),missing_frame_numbers=summary['last_frame']-summary['first_frame']+1-n,
                        predicted_possession_spells=sum(int(decoded[i] in ('H','A') and (i==a or decoded[i]!=decoded[i-1])) for a,b in runs for i in range(a,b)))
                    predictions.commit()
                if predictions.execute('PRAGMA quick_check').fetchall() != [('ok',)]:raise ValueError('prediction integrity failure')
            if db.execute('PRAGMA quick_check').fetchall() != [('ok',)]:raise ValueError('feature integrity failure')
        report=dict(match_id=match_id,frames=sum(s['frames'] for s in summaries.values()),periods=summaries,
            candidate=candidate.get('display_name', 'frozen_primary'),evaluation_status='not_scored_no_dense_possession_GT',
            inputs='tracking only; events never read',coordinate_policy='x=(x-.5)*105; y=(.5-y)*68; no clipping, direction flipping or imputation',
            empty_player_policy='both missing axes means unobserved roster slot; partial players retained',
            ball_policy='explicit pair always a record, even when fully missing; duplicate streams must agree')
        write_json(output/'report.json',report)
        if any(sha256(Path(p)) != h for p,h in inputs.items()) or any(sha256(REPO/p) != h for p,h in sources.items()):
            raise ValueError('input/source changed during inference')
        write_json(output/'manifest.json',dict(status='ready',metrica_sample_version=1,inputs_sha256=inputs,
            source_sha256=sources,outputs_sha256={p.name:sha256(p) for p in sorted(output.iterdir()) if p.is_file()},
            source_repository=UPSTREAM,attribution='Metrica Sports public sample tracking data; acknowledge source for public use (upstream README)',
            match_id=match_id,frames=report['frames'],fitting=False,tuning=False,official_data=False,
            python=platform.python_version(),packages={p:importlib.metadata.version(p) for p in PACKAGES},git=git_metadata(),
            elapsed_seconds=round(time.perf_counter()-started,3),process_peak_resident_bytes=peak_memory_bytes()))
        print(json.dumps({k:report[k] for k in ('match_id','frames','candidate','evaluation_status')},indent=2),flush=True)
        return report
    except Exception as error:
        write_json(output/'FAILED.json',dict(status='failed',error=str(error)))
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('home','away','snapshot','output'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--match-id',required=True)
    args=parser.parse_args()
    run(args.home,args.away,args.snapshot,args.output,args.match_id)


if __name__=='__main__':main()
