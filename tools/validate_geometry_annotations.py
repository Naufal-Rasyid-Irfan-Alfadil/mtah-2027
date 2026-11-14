"""Validate external geometry annotation provenance and completeness, without scoring models."""
import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEATURES = {'near_touchline_y68','far_touchline_y0','halfway_x52.5',
            'left_penalty_edge_x16.5','right_penalty_edge_x88.5','center_circle'}


def validate(task):
    task = Path(task).resolve()
    task.relative_to(ROOT/'external_artifacts/v3')
    manifest = json.loads((task/'manifest.json').read_text())
    source_manifest = (ROOT/manifest.get('source_manifest',
        'docs/soccertrack_v1_2_audit_download.json')).resolve(strict=True)
    source_manifest.relative_to(ROOT/'docs')
    source = json.loads(source_manifest.read_text())
    if (manifest.get('match') != source.get('match','117092')
            or manifest.get('dataset_revision') != source['revision']):
        raise ValueError('Task and source manifest match/revision differ')
    images = {i['path']:i for i in manifest['images']}
    for name, spec in images.items():
        path = (task/name).resolve(strict=True)
        path.relative_to(task)
        if hashlib.sha256(path.read_bytes()).hexdigest() != spec['sha256']:
            raise ValueError('Reference image checksum mismatch: '+name)
    e = next(e for e in source['files'] if e['path'].endswith('_keypoints.json'))
    source_root = (ROOT/manifest.get('source_root','Soccertrack V2')).resolve()
    source_root.relative_to(ROOT)
    source_path = (source_root/e['path']).resolve(strict=True)
    source_path.relative_to(source_root)
    data = source_path.read_bytes()
    if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest() != e['git_oid']:
        raise ValueError('Publisher keypoint checksum mismatch')
    fit_pixels = list(json.loads(data).values())
    with (task/'annotations.csv').open(newline='',encoding='utf-8-sig') as f:
        rows = list(csv.DictReader(f))
    expected = {(name,feature,str(point)) for name in images for feature in FEATURES for point in (1,2,3)}
    keys = [(r['image'],r['feature'],r['point']) for r in rows]
    if len(keys) != len(set(keys)) or set(keys) != expected:
        raise ValueError('Missing, duplicate or unexpected annotation slots')
    points, unavailable, pending = [], [], []
    for r in rows:
        image = images[r['image']]
        if r['image_sha256'] != image['sha256'] or int(r['frame_index_0_based']) != image['frame_index_0_based']:
            raise ValueError('Annotation image/frame provenance mismatch')
        if r['used_for_fitting'] != 'false':
            raise ValueError('Evaluation annotation marked for fitting')
        visibility = r['visibility']
        if visibility not in ('','visible','occluded','ambiguous'):
            raise ValueError('Unexpected visibility')
        if visibility != 'visible':
            if r['pixel_x'] or r['pixel_y']:
                raise ValueError('Unavailable/unreviewed point must not have inferred coordinates')
            (unavailable if visibility else pending).append(dict(image=r['image'],feature=r['feature'],point=r['point']))
            continue
        x,y = float(r['pixel_x']),float(r['pixel_y'])
        if not math.isfinite(x+y) or not (0<=x<image['width'] and 0<=y<image['height']):
            raise ValueError('Annotation coordinate outside original image')
        if not r['annotator'] or r['annotator_seen_predictions'] not in ('true','false'):
            raise ValueError('Incomplete operator provenance')
        distance = min(math.hypot(x-a,y-b) for a,b in fit_pixels)
        if distance < 20:
            raise ValueError('Annotation too close to publisher fitting point')
        points.append(dict(frame=image['frame_index_0_based'],feature=r['feature'],point=r['point'],
            x=x,y=y,distance_from_fit_px=distance,annotator=r['annotator'],
            seen_predictions=r['annotator_seen_predictions']=='true'))
    return dict(status='annotation_preflight_passed',slots=len(rows),populated_points=len(points),
        unavailable_slots=len(unavailable),unreviewed_slots=len(pending),
        frames_with_coordinates=sorted({p['frame'] for p in points}),
        features_with_coordinates=sorted({p['feature'] for p in points}),points=points,
        source_csv_sha256=hashlib.sha256((task/'annotations.csv').read_bytes()).hexdigest(),
        independently_verified_blinding=False,repeatability_measured=False,
        numerical_accuracy_gates_frozen=False,ready_for_geometry_scoring=False,
        ready_for_possession_evaluation=False,model_predictions_read=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.relative_to(ROOT/'external_artifacts/v3')
    if output.exists():
        raise FileExistsError(output)
    report = validate(args.task)
    output.write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))
