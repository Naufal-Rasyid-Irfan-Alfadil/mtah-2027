"""Read-only raw/decoded diagnosis with sparse external event context, never GT.

No model fitting/inference, event-to-target conversion, or F1 computation.
Import/help only import the standard library and existing lightweight helpers.
"""
import argparse
from bisect import bisect_left
from collections import Counter
from contextlib import closing
import csv
import html
from itertools import zip_longest
import json
from pathlib import Path
import sqlite3

from .prepare import sha256, REPO


def write_json(path, data):
    path.write_text(json.dumps(data,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')


def runs(rows, column):
    """[period, first N, exclusive last N, start seconds, stop seconds, value].

    Original keys/time are retained; a gap, non-40-ms step or half change breaks
    the run. This describes predictions/observations, not ground-truth spells.
    """
    result=[]
    for row in rows:
        period,frame,stamp=row[:3];value=row[column]
        if (result and result[-1][0]==period and result[-1][2]==frame
                and round(result[-1][4]*1e6)==stamp and result[-1][5]==value):
            result[-1][2]=frame+1;result[-1][4]=(stamp+40000)/1e6
        else:
            result.append([period,frame,frame+1,stamp/1e6,(stamp+40000)/1e6,value])
    return result


def read_rows(run_dir):
    """Read aligned frozen sample predictions/coverage from SQLite read-only.

    Rows are period, source-frame, relative us, raw H/A/D, decoded H/A/D,
    complete-ball flag, p_D, and D-to-alive flag. No new model output is created.
    """
    paths=[run_dir/n for n in ('manifest.json','features.sqlite','predictions.sqlite')]
    manifest=json.loads(paths[0].read_text())
    if manifest.get('status')!='ready' or manifest.get('metrica_sample_version')!=1:
        raise ValueError('ready sample inference artifact required')
    for p in paths[1:]:
        if sha256(p)!=manifest['outputs_sha256'][p.name]:raise ValueError('sample artifact hash mismatch')
    def connect(path):
        db=sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True)
        db.execute('PRAGMA query_only=ON');return db
    rows=[]
    with closing(connect(paths[1])) as f,closing(connect(paths[2])) as p:
        frows=f.execute('SELECT match_id,period,source_frame,time_us,ball_xy_observed FROM features ORDER BY period,source_frame')
        prows=p.execute('SELECT match_id,period,source_frame,time_us,raw_label,label,p_D FROM predictions ORDER BY period,source_frame')
        for a,b in zip_longest(frows,prows):
            if a is None or b is None or a[:4]!=b[:4]:raise ValueError('feature/prediction timeline mismatch')
            if b[4] not in ('H','A','D') or b[5] not in ('H','A','D'):raise ValueError('invalid prediction label')
            rows.append([*a[1:4],b[4],b[5],int(a[4]),b[6],int(b[4]=='D' and b[5]!='D')])
    if not rows:raise ValueError('empty timeline')
    return manifest['match_id'],rows,paths


def event_references(path, rows):
    """Attach sparse event anchors by exact (period,N), never nearest time.

    BALL OUT's end frame and SET PIECE's start frame are contextual anchors.
    END HALF and other events retain their source fields. Placeholder end=0
    is not an interval. Ball-out -> next restart spans are review candidates,
    not inferred dead-ball targets; intervening events are recorded explicitly.
    """
    lookup={(r[0],r[1]):r for r in rows}
    events=[]
    with Path(path).open(newline='',encoding='utf-8-sig') as f:
        reader=csv.DictReader(f)
        required={'Team','Type','Subtype','Period','Start Frame','End Frame'}
        if not required.issubset(reader.fieldnames or []):raise ValueError('unsupported Metrica event schema')
        for number,row in enumerate(reader,2):
            period=int(row['Period']);start=int(row['Start Frame']);end=int(row['End Frame'])
            if period not in (1,2):raise ValueError('unsupported event period')
            kind=row['Type'].strip().upper()
            valid_end=end>=start and end>0
            anchor=end if kind=='BALL OUT' and valid_end else start
            matched=lookup.get((period,anchor))
            events.append(dict(source_row=number,period=period,type=kind,subtype=row['Subtype'],team=row['Team'],
                start_frame=start,end_frame=end,interval_available=valid_end,anchor_frame=anchor,
                anchor_policy='end' if kind=='BALL OUT' and valid_end else 'start',
                matched=matched is not None,time_s=matched[2]/1e6 if matched else None,
                raw_label=matched[3] if matched else None,decoded_label=matched[4] if matched else None,
                ball_observed=matched[5] if matched else None))
    return events


def analyze(rows, events):
    """Count decoder effects and contextual spans without assigning correctness.

    Fractions are predicted D occupancy/ball coverage, never accuracy/F1. Span
    bounds exclude both anchors; periods/gaps remain explicit. Every possible
    same-half next-SET-PIECE pair is retained without a fitted duration cutoff.
    """
    changes={a:{b:0 for b in ('H','A','D')} for a in ('H','A','D')}
    by_coverage={str(v):dict(frames=0,raw_D=0,decoded_D=0,D_to_alive=0,p_D_sum=0.) for v in (0,1)}
    for row in rows:
        changes[row[3]][row[4]]+=1
        d=by_coverage[str(row[5])];d['frames']+=1;d['raw_D']+=int(row[3]=='D');d['decoded_D']+=int(row[4]=='D')
        d['D_to_alive']+=row[7];d['p_D_sum']+=row[6]
    for value in by_coverage.values():
        value['mean_raw_p_D']=value.pop('p_D_sum')/value['frames'] if value['frames'] else None
    period_rows={p:[r for r in rows if r[0]==p] for p in (1,2)}
    periods={}
    for p,data in period_rows.items():
        if data:periods[str(p)]=dict(frames=len(data),raw_label_counts=dict(Counter(r[3] for r in data)),
            decoded_label_counts=dict(Counter(r[4] for r in data)),missing_ball_frames=sum(not r[5] for r in data))
    spans=[]
    for event in events:
        if event['type']!='BALL OUT' or not event['interval_available'] or not event['matched']:continue
        following=[e for e in events if e['period']==event['period'] and e['type']=='SET PIECE'
                   and e['start_frame']>event['anchor_frame'] and e['matched']]
        if not following:continue
        restart=min(following,key=lambda e:(e['start_frame'],e['source_row']))
        data=period_rows[event['period']];keys=[r[1] for r in data]
        a,b=bisect_left(keys,event['anchor_frame']+1),bisect_left(keys,restart['start_frame'])
        selected=data[a:b]
        intervening=[e for e in events if e['period']==event['period'] and event['anchor_frame']<e['start_frame']<restart['start_frame']]
        spans.append(dict(period=event['period'],ball_out_row=event['source_row'],restart_row=restart['source_row'],
            ball_out_end_frame=event['anchor_frame'],restart_start_frame=restart['start_frame'],
            reference_gap_seconds=(restart['start_frame']-event['anchor_frame'])/25,
            observed_interior_frames=len(selected),missing_interior_frame_numbers=restart['start_frame']-event['anchor_frame']-1-len(selected),
            raw_D_frames=sum(r[3]=='D' for r in selected),decoded_D_frames=sum(r[4]=='D' for r in selected),
            D_to_alive_frames=sum(r[7] for r in selected),missing_ball_frames=sum(not r[5] for r in selected),
            intervening_event_types=dict(Counter(e['type'] for e in intervening)),
            status='context_only_not_dead_ball_GT'))
    removed=[r for r in runs(rows,7) if r[5]==1]
    removed.sort(key=lambda r:(-(r[2]-r[1]),r[0],r[1]))
    return dict(frames=len(rows),periods=periods,label_change_matrix=changes,by_complete_ball=by_coverage,
        event_type_counts=dict(Counter(e['type'] for e in events)),unmatched_event_anchors=sum(not e['matched'] for e in events),
        reference_span_count=len(spans),reference_spans=spans,longest_D_to_alive_runs=removed[:20],
        raw_D_total=sum(r[3]=='D' for r in rows),decoded_D_total=sum(r[4]=='D' for r in rows),
        D_to_alive_total=sum(r[7] for r in rows),
        evaluation='contextual diagnostics only; no dense GT, accuracy or F1; spans may overlap and must not be summed as a target mask')


HTML='''<!doctype html><html lang="en"><meta charset="utf-8"><title>__TITLE__</title>
<style>body{font:15px system-ui;margin:30px;color:#17212d;background:#fafbfc}canvas{width:100%;border:1px solid #ccd3da;background:white}label,select,input{margin:5px}pre{white-space:pre-wrap}h1{font-size:24px}.note{max-width:1000px;color:#465566}</style>
<h1>__TITLE__</h1><p class="note">External sample only. Raw/decoded labels are predictions. Ball-out → next set-piece gaps are review references, never ground truth. H blue · A red · D gold. No model parameters changed.</p>
<label>Half <select id="half"><option>1</option><option>2</option></select></label>
<label>Start (sample seconds) <input id="start" type="number" step="1"></label>
<label>Window <select id="window"><option value="30">30 s</option><option value="120" selected>120 s</option><option value="600">600 s</option><option value="0">Full half</option></select></label>
<button id="prev">←</button><button id="next">→</button><br>
<label>Jump to event <select id="event"></select></label>
<canvas id="chart" width="1200" height="290"></canvas><pre id="detail">Hover over markers to inspect an event.</pre>
<details><summary>Aggregate diagnosis</summary><pre id="summary"></pre></details>
<script id="data" type="application/json">__DATA__</script>
<script>
const data=JSON.parse(document.getElementById('data').textContent), el=id=>document.getElementById(id), canvas=el('chart'),ctx=canvas.getContext('2d');
const colors={H:'#2878b5',A:'#d64d4d',D:'#d7a62b',0:'#cbd3db',1:'#369184'},left=125,right=1180,width=right-left;
let viewStart=0,viewStop=120,markers=[];
function active(){return Number(el('half').value)}
function updateHalf(){const p=active(),r=data.raw.filter(r=>r[0]===p);el('start').value=r[0][3];el('event').replaceChildren();
 const init=document.createElement('option');init.textContent='Select a contextual event';init.value='';el('event').append(init);
 data.events.forEach((e,i)=>{if(e.period===p&&e.matched&&['BALL OUT','SET PIECE'].includes(e.type)){const o=document.createElement('option');o.value=i;o.textContent=e.type+' '+e.subtype+' @ frame '+e.anchor_frame+' / '+e.time_s.toFixed(2)+' s';el('event').append(o)}});draw()}
function draw(){const p=active(),r=data.raw.filter(r=>r[0]===p),min=r[0][3],max=r[r.length-1][4],seconds=Number(el('window').value);
 viewStart=seconds?Math.max(min,Math.min(Number(el('start').value),max-.04)):min;viewStop=seconds?Math.min(max,viewStart+seconds):max;
 ctx.clearRect(0,0,1200,290);ctx.font='14px system-ui';ctx.fillStyle='#243447';markers=[];
 const x=t=>left+(t-viewStart)/(viewStop-viewStart)*width;
 [['Raw',data.raw],['Decoded',data.decoded],['Ball observed',data.ball],['D → H/A',data.removed]].forEach(([name,segments],j)=>{let y=45+j*43;ctx.fillStyle='#243447';ctx.fillText(name,8,y+19);ctx.fillStyle='#f1f3f5';ctx.fillRect(left,y,width,27);
 segments.forEach(s=>{if(s[0]!==p||s[4]<=viewStart||s[3]>=viewStop)return;if(j===3&&!s[5])return;ctx.fillStyle=j===3?'#a14792':colors[s[5]];const a=Math.max(viewStart,s[3]),b=Math.min(viewStop,s[4]);ctx.fillRect(x(a),y,Math.max(.5,x(b)-x(a)),27)})});
 ctx.fillStyle='#243447';for(let i=0;i<=6;i++){const t=viewStart+(viewStop-viewStart)*i/6;ctx.fillText(t.toFixed(1)+' s',Math.min(1120,x(t)),240)}
 data.events.forEach(e=>{if(e.period!==p||!e.matched||e.time_s<viewStart||e.time_s>viewStop||!['BALL OUT','SET PIECE'].includes(e.type))return;const px=x(e.time_s);ctx.strokeStyle=e.type==='BALL OUT'?'#6b4b11':'#193c6d';ctx.beginPath();ctx.moveTo(px,22);ctx.lineTo(px,212);ctx.stroke();ctx.fillStyle=ctx.strokeStyle;ctx.fillText(e.type==='BALL OUT'?'O':'S',px,18);markers.push([px,e])});
 ctx.fillStyle='#465566';ctx.fillText('O = BALL OUT end-frame reference; S = SET PIECE start-frame reference. Times remain sample-relative.',8,274)}
el('half').onchange=updateHalf;el('start').onchange=draw;el('window').onchange=draw;
el('prev').onclick=()=>{el('start').value=Number(el('start').value)-(Number(el('window').value)||120);draw()};
el('next').onclick=()=>{el('start').value=Number(el('start').value)+(Number(el('window').value)||120);draw()};
el('event').onchange=()=>{if(el('event').value==='')return;const e=data.events[Number(el('event').value)];el('start').value=e.time_s-10;el('window').value='30';el('detail').textContent=JSON.stringify(e,null,2);draw()};
canvas.onmousemove=event=>{const x=(event.clientX-canvas.getBoundingClientRect().left)*canvas.width/canvas.getBoundingClientRect().width;const found=markers.filter(m=>Math.abs(m[0]-x)<8);if(found.length)el('detail').textContent=JSON.stringify(found[0][1],null,2)};
el('summary').textContent=JSON.stringify(data.summary,null,2);updateHalf();
</script></html>'''


def review(run_dir, event_file, output):
    run_dir,event_file,output=Path(run_dir).resolve(strict=True),Path(event_file).resolve(strict=True),Path(output).resolve()
    match,rows,paths=read_rows(run_dir);paths.append(event_file)
    hashes={str(p):sha256(p) for p in paths}
    output.mkdir(parents=True,exist_ok=False)
    try:
        events=event_references(event_file,rows);summary=analyze(rows,events);summary['match_id']=match
        write_json(output/'summary.json',summary);write_json(output/'event_references.json',events)
        display_summary={k:v for k,v in summary.items() if k not in ('reference_spans','longest_D_to_alive_runs')}
        payload=dict(raw=runs(rows,3),decoded=runs(rows,4),ball=runs(rows,5),removed=runs(rows,7),events=events,summary=display_summary)
        page=HTML.replace('__TITLE__',html.escape(match+' — decoder review')).replace('__DATA__',json.dumps(payload,separators=(',',':')).replace('</','<\\/'))
        (output/'timeline.html').write_text(page,encoding='utf-8')
        if any(sha256(Path(p))!=h for p,h in hashes.items()):raise ValueError('diagnostic input changed')
        write_json(output/'manifest.json',dict(status='ready',sample_review_version=1,inputs_sha256=hashes,
            source_sha256=sha256(Path(__file__)),outputs_sha256={p.name:sha256(p) for p in output.iterdir() if p.is_file()},
            fitting=False,inference=False,target_creation=False,official_data=False,
            attribution='Metrica Sports public sample tracking/event data; original repo README acknowledgement applies'))
        print(json.dumps({k:summary[k] for k in ('match_id','frames','raw_D_total','decoded_D_total','D_to_alive_total','reference_span_count')},indent=2))
        return summary
    except Exception as error:
        write_json(output/'FAILED.json',dict(status='failed',error=str(error)));raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('run','events','output'):parser.add_argument('--'+name,type=Path,required=True)
    args=parser.parse_args();review(args.run,args.events,args.output)


if __name__=='__main__':main()
