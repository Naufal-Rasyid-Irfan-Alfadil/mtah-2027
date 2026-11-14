"""Checksum-first external feasibility audit; no labels, training or inference."""
import argparse
import ast
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / 'docs/soccertrack_v1_2_117093_possession_inputs.json'
TARGET_KEY = re.compile(r'possess|ballstatus|owner|control|dead|playstate', re.I)


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def parse_loc(value):
    if value in (None, '', 'NA', 'nan'):
        return None
    parsed = ast.literal_eval(value)
    if (not isinstance(parsed, (list, tuple)) or len(parsed) != 2
            or any(type(v) not in (float, int) or not math.isfinite(v) for v in parsed)):
        raise ValueError('Invalid coordinate literal')
    return tuple(float(v) for v in parsed)


def inspect_tracking_xml(path, player_teams):
    context = ET.iterparse(path, events=('start', 'end'))
    _, root = next(context)
    if root.tag != 'data':
        raise ValueError('Unexpected tracker XML root')
    periods, attributes, player_attributes, ball_attributes = {}, Counter(), Counter(), Counter()
    for event, frame in context:
        if event != 'end' or frame.tag != 'frame':
            continue
        period = frame.get('eventPeriod')
        if not period:
            raise ValueError('Frame without period')
        state = periods.setdefault(period, dict(n_frames=0, ball_status_counts=Counter(),
            player_counts=Counter(), known_team_record_counts=Counter(), unknown_player_records=0,
            missing_player_locations=0, invalid_player_locations=0, missing_ball_locations=0,
            invalid_ball_locations=0, frame_min=None, frame_max=None, frame_step_counts=Counter(),
            match_time_min=None, match_time_max=None, nonmonotonic_match_times=0,
            last_frame=None, last_time=None, coordinate_min=[None, None], coordinate_max=[None, None]))
        if sum(p['n_frames'] for p in periods.values()) >= 1_000_000:
            raise ValueError('Frame count audit cap exceeded')
        attributes.update(frame.attrib.keys())
        state['n_frames'] += 1
        state['ball_status_counts'][frame.get('ballStatus', '<missing>')] += 1
        number = float(frame.attrib['frameNumber'])
        time = float(frame.attrib['matchTime'])
        if not number.is_integer() or not math.isfinite(time):
            raise ValueError('Invalid frame number/time')
        number = int(number)
        if state['last_frame'] is not None:
            state['frame_step_counts'][str(number - state['last_frame'])] += 1
        if state['last_time'] is not None and time <= state['last_time']:
            state['nonmonotonic_match_times'] += 1
        state['last_frame'], state['last_time'] = number, time
        for key, value in [('frame', number), ('match_time', time)]:
            state[key + '_min'] = value if state[key + '_min'] is None else min(state[key + '_min'], value)
            state[key + '_max'] = value if state[key + '_max'] is None else max(state[key + '_max'], value)
        players = frame.findall('player')
        state['player_counts'][str(len(players))] += 1
        for player in players:
            player_attributes.update(player.attrib.keys())
            pid = player.get('playerId', player.get('id'))
            team = player_teams.get(pid)
            if team is None:
                state['unknown_player_records'] += 1
            else:
                state['known_team_record_counts'][team] += 1
            try:
                loc = parse_loc(player.get('loc'))
            except (ValueError, SyntaxError):
                state['invalid_player_locations'] += 1
                continue
            if loc is None:
                state['missing_player_locations'] += 1
            else:
                for axis, v in enumerate(loc):
                    lo, hi = state['coordinate_min'][axis], state['coordinate_max'][axis]
                    state['coordinate_min'][axis] = v if lo is None else min(lo, v)
                    state['coordinate_max'][axis] = v if hi is None else max(hi, v)
        balls = frame.findall('ball')
        if not balls:
            state['missing_ball_locations'] += 1
        for ball in balls:
            ball_attributes.update(ball.attrib.keys())
            try:
                if parse_loc(ball.get('loc')) is None:
                    state['missing_ball_locations'] += 1
            except (ValueError, SyntaxError):
                state['invalid_ball_locations'] += 1
        root.clear()
    for state in periods.values():
        state.pop('last_frame')
        state.pop('last_time')
    return dict(periods=periods, frame_attribute_counts=attributes,
                player_attribute_counts=player_attributes, ball_attribute_counts=ball_attributes,
                candidate_target_fields=[k for k in attributes if TARGET_KEY.search(k)],
                alignment_to_v1_2_video_verified=False,
                independent_ball_observation_verified=False,
                independent_possession_target_verified=False)


def inspect_small(path):
    if path.suffix == '.csv':
        with path.open(newline='', encoding='utf-8-sig') as stream:
            reader = csv.DictReader(stream)
            columns, count = reader.fieldnames, sum(1 for _ in reader)
        return dict(kind='csv_schema', columns=columns, rows=count,
                    candidate_target_columns=[k for k in columns if TARGET_KEY.search(k)])
    obj = json.loads(path.read_text(encoding='utf-8-sig'))
    keys = Counter()
    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                keys[key] += 1
                walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)
    walk(obj)
    return dict(kind='json_schema', top_level_keys=sorted(obj) if isinstance(obj, dict) else None,
                key_counts=keys, candidate_target_fields=[k for k in keys if TARGET_KEY.search(k)],
                independent_possession_target_verified=False)


def audit(tracking_sha256=None):
    plan = json.loads(PLAN.read_text())
    if plan['match'] != '117093' or plan['local_root'] != 'Soccertrack V2':
        raise ValueError('Unexpected source identity')
    cm = json.loads((ROOT / plan['catalog_manifest']).read_text())
    e = next(e for e in cm['sources'] if e['name'] == 'soccertrack-file-catalog')
    cp = ROOT / 'external_artifacts/v3/feasibility-20261112-metadata' / e['file']
    if digest(cp) != plan['catalog_sha256'] or e['sha256'] != plan['catalog_sha256']:
        raise ValueError('Catalog checksum mismatch')
    catalog = {e['path']: e for e in json.loads(cp.read_text()) if e['type'] == 'file'}
    source = (ROOT / 'Soccertrack V2').resolve()
    metadata_plan = json.loads((ROOT / 'docs/soccertrack_v1_2_117093_download.json').read_text())
    me = next(e for e in metadata_plan['files'] if e['path'].endswith('_metadata.xml'))
    mp = source / me['path']
    data = mp.read_bytes()
    if hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() != me['git_oid']:
        raise ValueError('Metadata checksum mismatch')
    metadata = ET.fromstring(data)
    if metadata.find('match').get('matchId') != '117093':
        raise ValueError('Metadata match mismatch')
    teams = {t.get('id'): t.get('side') for t in metadata.findall('./teams/team')}
    player_teams = {p.get('id'): teams[p.get('teamId')] for p in metadata.findall('./players/player')}
    results = []
    for spec in plan['files']:
        expected = catalog[spec['path']]
        if spec['bytes'] != expected['size'] or spec['git_oid'] != expected['oid']:
            raise ValueError('Acquisition plan differs from pinned catalog')
        p = (source / spec['path']).resolve()
        p.relative_to(source)
        record = dict(path=spec['path'], expected_bytes=spec['bytes'])
        if not p.exists():
            record['status'] = 'missing'
        elif p.stat().st_size != spec['bytes']:
            record['status'] = 'size_mismatch_not_parsed'
        elif spec['lfs'] and tracking_sha256 is None:
            record['status'] = 'publisher_payload_checksum_required_not_parsed'
        else:
            if spec['lfs']:
                if not re.fullmatch(r'[0-9a-f]{64}', tracking_sha256 or ''):
                    raise ValueError('Expected publisher SHA256')
                if digest(p) != tracking_sha256:
                    raise ValueError('Tracking checksum mismatch; refusing parse')
                record['payload_checksum_evidence'] = 'operator_transcription_of_publisher_LFS_Details_not_independently_fetched'
            else:
                payload = p.read_bytes()
                if hashlib.sha1(b'blob ' + str(len(payload)).encode() + b'\0' + payload).hexdigest() != spec['git_oid']:
                    raise ValueError('Small payload Git blob checksum mismatch; refusing parse')
            record.update(status='checksum_verified_audited', sha256=digest(p),
                          schema=inspect_tracking_xml(p, player_teams) if p.suffix == '.xml' else inspect_small(p))
        results.append(record)
    return dict(match='117093', dataset_revision=plan['revision'], files=results,
                metadata_checksum_verified=True, roster_players=len(player_teams), team_side_by_id=teams,
                dense_independent_possession_targets_ready=False, source_claim_ballStatus='publisher Frame model only; payload not inferred',
                production_eligible=False, trained=False, inference_run=False, official_data_read=False,
                action='review actual payload schema/time/independent origin before any production implementation')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tracking-sha256')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.relative_to(ROOT / 'external_artifacts/v3')
    if output.exists():
        raise FileExistsError(output)
    report = audit(args.tracking_sha256)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(match=report['match'], files=[dict(path=e['path'], status=e['status']) for e in report['files']],
                         dense_independent_possession_targets_ready=False), indent=2))
