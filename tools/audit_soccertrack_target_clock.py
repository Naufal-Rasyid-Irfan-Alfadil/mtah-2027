"""Research audit of provider clocks/statuses; no model or H/A/D target generation."""
import argparse
from collections import Counter, defaultdict
import csv
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PERIODS = {1: 'FIRST_HALF', 2: 'SECOND_HALF'}


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def clock_pairs(nodes, raw_events, bas, origins):
    actors = defaultdict(set)
    for node in nodes:
        if node['player_id']:
            actors[(node['event_period'], int(node['event_time']))].add(node['player_id'])
    anchors = defaultdict(set)
    for event in raw_events:
        half = int(event['gameTime'].split(' - ')[0])
        t = int(event['position'])
        for actor in actors[(PERIODS[half], t)]:
            anchors[(half, event['label'], actor)].add(t)
    results = {}
    for half in (1, 2):
        pairs, histogram, missing_actor = [], Counter(), 0
        events = [e for e in bas if int(e['gameTime'].split(' - ')[0]) == half]
        for event in events:
            actor = event.get('player_id')
            if actor is None:
                missing_actor += 1
                continue
            for raw_time in anchors[(half, event['label'], str(actor))]:
                offset = raw_time - int(event['position'])
                # Broad clock-identity search, not model accuracy optimization.
                if abs(offset - origins[half]) <= 5000:
                    histogram[offset] += 1
                    pairs.append((event, raw_time, offset))
        ranked = histogram.most_common()
        unique_mode = bool(ranked) and (len(ranked) == 1 or ranked[0][1] > ranked[1][1])
        mode = ranked[0][0] if unique_mode else None
        matched = [dict(label=e['label'], actor=str(e['player_id']), raw_time_ms=t,
                        released_position_ms=int(e['position']), released_frame_1_based=e['frame'])
                   for e, t, offset in pairs if offset == mode]
        results[str(half)] = dict(n_bas_events=len(events), missing_actor=missing_actor,
            top_offset_counts=ranked[:12], candidate_offset_ms=mode,
            matched_anchor_pairs=len(matched), matched_anchors=matched,
            same_provider_evidence_only=True, independent_visual_alignment_verified=False)
    return results


def audit(output):
    plan = json.loads((ROOT / 'docs/soccertrack_v1_2_117093_possession_verified.json').read_text())
    source = ROOT / 'Soccertrack V2'
    paths = {}
    for spec in plan['files']:
        p = (source / spec['path']).resolve()
        p.relative_to(source.resolve())
        if p.stat().st_size != spec['bytes']:
            raise ValueError('Source size mismatch')
        if spec['lfs']:
            if sha(p) != spec['payload_sha256']:
                raise ValueError('Tracking checksum mismatch')
        else:
            data = p.read_bytes()
            if hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() != spec['git_oid']:
                raise ValueError('Small source checksum mismatch')
        paths[p.suffix] = p
    with paths['.csv'].open(newline='', encoding='utf-8-sig') as stream:
        nodes = list(csv.DictReader(stream))
    raw_events = json.loads(paths['.json'].read_text())['annotations']
    published = json.loads((ROOT / 'docs/soccertrack_v1_2_117093_download.json').read_text())
    spec = next(e for e in published['files'] if e['path'].startswith('bas/'))
    data = (source / spec['path']).read_bytes()
    if hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() != spec['git_oid']:
        raise ValueError('Released BAS checksum mismatch')
    bas = json.loads(data)['actions']
    intervals, current, periods, ball_ids = [], {}, {}, Counter()
    parser = ET.iterparse(paths['.xml'], events=('start', 'end'))
    _, root = next(parser)
    if root.tag != 'data':
        raise ValueError('Unexpected XML root')
    for event, frame in parser:
        if event != 'end' or frame.tag != 'frame':
            continue
        period, status = frame.attrib['eventPeriod'], frame.attrib['ballStatus']
        f, t = int(frame.attrib['frameNumber']), int(frame.attrib['matchTime'])
        ps = periods.setdefault(period, dict(n=0, first_frame=f, first_time=t,
                                            last_frame=f, last_time=t, max_time_grid_error_ms=0))
        ps['n'] += 1
        ps['last_frame'], ps['last_time'] = f, t
        ps['max_time_grid_error_ms'] = max(ps['max_time_grid_error_ms'],
            abs(t - ps['first_time'] - 40 * (f - ps['first_frame'])))
        if period in current and current[period]['raw_status'] != status:
            intervals.append(current.pop(period))
        state = current.setdefault(period, dict(period=period, raw_status=status,
            raw_frame_start=f, raw_frame_end=f, raw_time_start_ms=t, raw_time_end_ms=t, n_frames=0))
        state.update(raw_frame_end=f, raw_time_end_ms=t, n_frames=state['n_frames'] + 1)
        for ball in frame.findall('ball'):
            ball_ids[ball.get('playerId', '<missing>')] += 1
        root.clear()
    intervals.extend(current.values())
    origins = {h: periods[p]['first_time'] for h, p in PERIODS.items()}
    clocks = clock_pairs(nodes, raw_events, bas, origins)
    report = dict(match='117093', dataset_revision=plan['revision'],
        raw_tracking_sha256=sha(paths['.xml']), released_bas_sha256=hashlib.sha256(data).hexdigest(),
        periods=periods, clock_comparison=clocks, raw_ball_id_counts=ball_ids,
        provider_status_intervals=len(intervals), raw_status_semantics_verified=False,
        independent_target_origin_verified=False, independent_visual_alignment_verified=False,
        provisional_mapping_hypotheses={'HOME':'H', 'AWAY':'A', 'BALLOUT':'D_pending_live_dead_definition',
                                        'NEUTRAL':'unknown_masked_not_automatically_D_or_X'},
        warning='Clock consensus is shared-provider lineage, not independent validation of possession labels.',
        trained=False, inference_run=False, candidate_scores_computed=False, production_eligible=False)
    output.mkdir(parents=True, exist_ok=False)
    with (output / 'raw-status-intervals.csv').open('x', newline='', encoding='utf-8') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(intervals[0]))
        writer.writeheader()
        writer.writerows(sorted(intervals, key=lambda e: (e['period'], e['raw_frame_start'])))
    with (output / 'report.json').open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(periods=periods, raw_ball_id_counts=ball_ids,
        clocks={h:{k:v for k,v in e.items() if k != 'matched_anchors'} for h,e in clocks.items()}), indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.relative_to(ROOT / 'external_artifacts/v3')
    if output.exists():
        raise FileExistsError(output)
    audit(output)
