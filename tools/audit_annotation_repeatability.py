"""Describe paired external pixel measurements; never load model parameters."""
import argparse
import csv
import hashlib
import json
import math
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'external_artifacts/v3'
SNAPSHOT_SHA = 'f8d2092da58461126ba21bea7d000008a28e358ce49c3566fb1b4e847f12819f'
TASK_SHA = '9b26590aac91d9404bdc38f7f14f4ae35e3365873910dd6c93c8ec50611615e5'


def checked_path(base, name):
    path = (base / name).resolve(strict=True)
    path.relative_to(base.resolve())
    return path


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require_hash(path, expected):
    if digest(path) != expected:
        raise ValueError('Checksum mismatch: ' + str(path))


def read_csv(path):
    with path.open(newline='', encoding='utf-8-sig') as stream:
        return list(csv.DictReader(stream))


def percentile(values, fraction):
    if not values:
        return None
    values = sorted(values)
    index = fraction * (len(values) - 1)
    lo, hi = math.floor(index), math.ceil(index)
    return values[lo] + (values[hi] - values[lo]) * (index - lo)


def summary(points):
    signed = [p['signed_displacement_px'] for p in points]
    absolute = [abs(v) for v in signed]
    return dict(n=len(points), signed_median_px=percentile(signed, .5),
                absolute_median_px=percentile(absolute, .5),
                absolute_p95_px=percentile(absolute, .95),
                absolute_max_px=max(absolute, default=None))


def validate_repeat(row, spec):
    if row['used_for_fitting'] != 'false' or not row['annotator']:
        raise ValueError('Invalid fitting/annotator provenance')
    exposure_keys = ('previous_coordinates_visible_during_repeat',
                     'model_overlay_seen_during_repeat')
    if any(row[k] not in ('true', 'false') for k in exposure_keys):
        raise ValueError('Exposure provenance incomplete')
    if row['visibility'] in ('ambiguous', 'occluded'):
        if row['pixel_x_local'] or row['pixel_y_local']:
            raise ValueError('Unavailable repeat must have no coordinates')
        return None
    if row['visibility'] != 'visible':
        raise ValueError('Repeat visibility unresolved')
    xy = {axis: float(row['pixel_' + axis + '_local']) for axis in ('x', 'y')}
    if not all(math.isfinite(v) for v in xy.values()):
        raise ValueError('Nonfinite repeat coordinate')
    if not (0 <= xy['x'] < spec['width'] and 0 <= xy['y'] < spec['height']):
        raise ValueError('Repeat coordinate outside crop')
    if xy[spec['fixed_local_axis']] != spec['fixed_local_value']:
        raise ValueError('Repeat does not use the fixed slice')
    return xy


def audit(task):
    task = task.resolve(strict=True)
    task.relative_to(BASE.resolve())
    require_hash(task / 'manifest.json', TASK_SHA)
    manifest = json.loads((task / 'manifest.json').read_text())
    if (manifest['kind'] != 'external_geometry_repeatability_collection'
            or manifest['match'] != '117093'):
        raise ValueError('Unexpected source identity')
    snapshot = checked_path(BASE, '117093-reference-freeze-20261113')
    if (ROOT / manifest['source_snapshot']).resolve() != snapshot:
        raise ValueError('Unexpected reference snapshot')
    require_hash(snapshot / 'freeze-manifest.json', SNAPSHOT_SHA)
    frozen = json.loads((snapshot / 'freeze-manifest.json').read_text())
    for entry in frozen['files']:
        path = checked_path(snapshot, entry['path'])
        if path.stat().st_size != entry['bytes']:
            raise ValueError('Reference file size mismatch')
        require_hash(path, entry['sha256'])
    require_hash(task / 'protocol.md', manifest['protocol_sha256'])
    require_hash(snapshot / 'annotations.csv', manifest['source_annotations_sha256'])
    status = json.loads((task / 'collection-status.json').read_text())
    require_hash(task / 'repeats.csv', status['repeats_csv_sha256'])
    if status['operator_exposure_provenance_complete_points'] != 18:
        raise ValueError('Exposure session confirmation is incomplete')
    originals = read_csv(snapshot / 'annotations.csv')
    original_by_key = {(r['image'], r['feature'], int(r['point'])): r for r in originals}
    if len(original_by_key) != 54 or len(originals) != 54:
        raise ValueError('Unexpected original slots')
    specs = {s['sample_id']: s for s in manifest['samples']}
    rows = read_csv(task / 'repeats.csv')
    if (len(rows) != 18 or len({r['sample_id'] for r in rows}) != 18
            or set(specs) != {r['sample_id'] for r in rows}):
        raise ValueError('Missing, duplicate or unexpected repeat slots')
    points, missing = [], []
    exposure_counts = Counter()
    for row in rows:
        spec = specs[row['sample_id']]
        require_hash(checked_path(task, spec['crop_path']), spec['crop_sha256'])
        require_hash(checked_path(snapshot, spec['source_image']), spec['source_image_sha256'])
        key = (spec['source_image'], spec['feature'], spec['original_point'])
        first = original_by_key[key]
        if (first['image_sha256'] != spec['source_image_sha256']
                or int(first['frame_index_0_based']) != spec['frame_index_0_based']
                or first['used_for_fitting'] != 'false' or first['visibility'] != 'visible'
                or first['annotator'] != row['annotator']):
            raise ValueError('Pair identity/provenance mismatch')
        xy = validate_repeat(row, spec)
        prior = row['previous_coordinates_visible_during_repeat'] == 'true'
        model = row['model_overlay_seen_during_repeat'] == 'true'
        exposure = ('both' if prior and model else 'previous_only' if prior
                    else 'model_only' if model else 'neither_self_reported')
        exposure_counts[exposure] += 1
        if xy is None:
            missing.append(dict(sample_id=row['sample_id'], reason=row['visibility'], exposure=exposure))
            continue
        raw = {axis: xy[axis] + spec['crop_origin_' + axis] for axis in ('x', 'y')}
        fixed = spec['fixed_local_axis']
        if raw[fixed] != float(first['pixel_' + fixed]):
            raise ValueError('Repeated slice differs from the original slice')
        axis = spec['measure_axis']
        delta = raw[axis] - float(first['pixel_' + axis])
        points.append(dict(sample_id=row['sample_id'], frame=spec['frame_index_0_based'],
                           feature=spec['feature'], measured_axis=axis,
                           original_raw_xy=[float(first['pixel_x']), float(first['pixel_y'])],
                           repeat_raw_xy=[raw['x'], raw['y']], signed_displacement_px=delta,
                           absolute_displacement_px=abs(delta), exposure=exposure))
    return dict(status='descriptive_repeatability_audit_complete', match='117093',
                slots=18, n_valid=len(points), n_missing=len(missing),
                n_exposed=sum(v for k, v in exposure_counts.items() if k != 'neither_self_reported'),
                exposure_counts=dict(exposure_counts), overall=summary(points),
                by_feature={key: summary([p for p in points if p['feature'] == key])
                            for key in sorted({s['feature'] for s in specs.values()})},
                by_frame={str(key): summary([p for p in points if p['frame'] == key])
                          for key in sorted({s['frame_index_0_based'] for s in specs.values()})},
                by_exposure={key: summary([p for p in points if p['exposure'] == key])
                             for key in sorted(exposure_counts)},
                points=points, missing=missing, independent_cameras=1,
                uncertainty_scope='descriptive same-operator fixed-axis paired displacement only',
                independent_blinding_verified=False, absolute_accuracy_established=False,
                production_error_budget_supported=False, numerical_accuracy_gates_frozen=False,
                model_predictions_read=False, geometry_scores_computed=False,
                used_for_fitting=False, ready_for_geometry_scoring=False,
                ready_for_possession_evaluation=False,
                source_checksums=dict(reference_manifest=SNAPSHOT_SHA, task_manifest=TASK_SHA,
                                      repeats_csv=digest(task / 'repeats.csv'),
                                      protocol=digest(task / 'protocol.md'),
                                      measurement_journal=digest(task / 'operator-repeat-measurements.jsonl')))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--task', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.relative_to(BASE.resolve())
    if output.exists():
        raise FileExistsError(output)
    if output.parent == args.task.resolve() or output.parent == BASE / '117093-reference-freeze-20261113':
        raise ValueError('Write analysis outside input packages')
    report = audit(args.task)
    with output.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps({k: report[k] for k in ('status', 'n_valid', 'n_missing', 'n_exposed', 'overall')}, indent=2))
