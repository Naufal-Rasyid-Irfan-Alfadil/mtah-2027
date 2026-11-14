"""Audit the explicitly requested external 117092 package; no production loader."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile

import numpy as np


ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    base, output = args.input.resolve(), args.output.resolve()
    base.relative_to(ROOT)
    output.relative_to(ROOT/'external_artifacts/v3')
    if output.exists():
        raise FileExistsError(output)
    manifest = json.loads((ROOT/'docs/soccertrack_v1_2_audit_download.json').read_text())
    report = dict(checked_at=datetime.now(timezone.utc).isoformat(),
                  dataset=manifest['dataset'], revision=manifest['revision'],
                  source_root=str(base), license=manifest['license'], inventory=[])
    # Only these eight provenance-identified paths are opened, never glob data.
    for entry in manifest['files']:
        path = (base/entry['path']).resolve(strict=True)
        path.relative_to(base)
        if path.stat().st_size != entry['bytes']:
            raise ValueError('Size mismatch: '+entry['path'])
        data = path.read_bytes()
        oid = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if not entry['lfs'] and oid != entry['git_oid']:
            raise ValueError('Publisher Git blob mismatch: '+entry['path'])
        digest = hashlib.sha256(data).hexdigest()
        expected_sha256 = entry.get('payload_sha256')
        if expected_sha256 and digest != expected_sha256:
            raise ValueError('Publisher payload SHA256 mismatch: '+entry['path'])
        report['inventory'].append(dict(path=entry['path'], bytes=len(data),
            sha256=digest,
            publisher_checksum=('LFS_payload_SHA256_verified_operator_transcription'
                if entry['lfs'] and expected_sha256 else
                'pending_LFS_payload_digest' if entry['lfs'] else 'Git_blob_verified'),
            checksum_evidence=entry.get('payload_sha256_evidence')))
    raw = base/'raw/117092'
    keypoints = json.loads((raw/'117092_keypoints.json').read_text())
    world = np.array([[float(v) for v in k.strip('()').split(',')] for k in keypoints])
    pixels = np.array(list(keypoints.values()))
    if world.shape != (65, 2) or pixels.shape != (65, 2) or not np.isfinite(pixels).all():
        raise ValueError('Unexpected 117092 keypoint schema')
    report['keypoints'] = dict(count=len(world), world_min=world.min(0).tolist(),
        world_max=world.max(0).tolist(), pixel_min=pixels.min(0).tolist(),
        pixel_max=pixels.max(0).tolist(), world_origin='pitch_corner; not centered GSR',
        independent_evaluation_target=False)
    headers = {}
    with zipfile.ZipFile(raw/'117092_camera_intrinsics.npz') as archive:
        if sum(i.file_size for i in archive.infolist()) > 65536:
            raise ValueError('NPZ decompressed size exceeds audit cap')
        for name in archive.namelist():
            with archive.open(name) as stream:
                version = np.lib.format.read_magic(stream)
                if version == (1, 0):
                    shape, _, dtype = np.lib.format.read_array_header_1_0(stream)
                elif version == (2, 0):
                    shape, _, dtype = np.lib.format.read_array_header_2_0(stream)
                else:
                    raise ValueError('Unsupported NPY header version')
            headers[name] = dict(shape=list(shape), dtype=str(dtype), object_array=dtype.hasobject)
    with np.load(raw/'117092_camera_intrinsics.npz', allow_pickle=False) as archive:
        numeric = {name: archive[name] for name in ('K', 'D', 'Knew', 'rms')}
    if (numeric['K'].shape != (3, 3) or numeric['Knew'].shape != (3, 3)
            or numeric['D'].shape != (4, 1)
            or not all(np.isfinite(v).all() for v in numeric.values())):
        raise ValueError('Unexpected numeric calibration schema')
    h = np.load(raw/'117092_homography.npy', allow_pickle=False)
    if h.shape != (3, 3) or not np.isfinite(h).all() or np.linalg.matrix_rank(h) != 3:
        raise ValueError('Invalid homography')
    report['calibration'] = dict(npz_members=headers,
        numeric_parameters={k:v.tolist() for k,v in numeric.items()},
        object_arrays_loaded=False, homography=h.tolist(),
        homography_determinant=float(np.linalg.det(h)),
        homography_condition_number=float(np.linalg.cond(h)),
        note='Integrity and numeric schema checks do not establish geometry accuracy')
    events = json.loads((base/'bas/117092/117092_12_class_events.json').read_text())
    rows = events['actions']
    halves = []
    for half, n in ((1, 67375), (2, 67549)):
        selected = [r for r in rows if r['gameTime'].split(' - ')[0] == str(half)]
        if not selected:
            raise ValueError('Missing half actions')
        errors = [(r['frame']-1)*40-int(r['position']) for r in selected]
        halves.append(dict(half=half, actions=len(selected),
            min_frame=min(r['frame'] for r in selected),
            max_frame=max(r['frame'] for r in selected),
            frame_out_of_range=sum(type(r['frame']) is not int or not 1<=r['frame']<=n for r in selected),
            max_frame_time_error_ms=max(map(abs, errors)),
            halfway_time_events=sum(int(r['position'])%40==20 for r in selected)))
    if sum(v['actions'] for v in halves) != len(rows):
        raise ValueError('Unexpected event half')
    report['BAS'] = dict(top_level_keys=sorted(events), actions=len(rows), clock=events['clock'],
        fps=events['fps'], labels=dict(Counter(r['label'] for r in rows)),
        teams=dict(Counter(r['team'] for r in rows)), halves=halves,
        timeline='frame is 1-based; video_index=frame-1; use supplied frame, no recomputed rounding',
        automatic_smart_tagging=False, independent_dense_possession_target=False,
        video_alignment_empirically_verified=False)
    metadata = ET.parse(raw/'117092_tracker_box_metadata.xml').getroot()
    report['raw_metadata'] = dict(root=metadata.tag,
        tag_counts=dict(Counter(v.tag for v in metadata.iter())),
        periods=[dict(v.attrib) for v in metadata.iter('period')],
        pitch=[dict(v.attrib) for v in metadata.iter('pitch')],
        note='Raw provider clock includes extra period and is distinct from released two-half BAS')
    report['status'] = 'schema_audited; geometry_accuracy_and_possession_gates_pending'
    report['integrity_passed'] = all(e['publisher_checksum'] != 'pending_LFS_payload_digest'
                                    for e in report['inventory'])
    report['blocked'] = ([] if report['integrity_passed'] else
        ['publisher LFS payload SHA256 for numeric files']) + [
        'paired video decoding and actual stream dimensions',
        'independent geometry evaluation points',
        'independent ball observations/annotations and dense H/A/D possession targets']
    # Verify inputs were not mutated during inspection.
    for entry in report['inventory']:
        if hashlib.sha256((base/entry['path']).read_bytes()).hexdigest() != entry['sha256']:
            raise ValueError('Audit input changed')
    output.mkdir(parents=True)
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(status=report['status'], files=len(report['inventory']),
        verified_git_blobs=sum(not f['lfs'] for f in manifest['files']),
        keypoints=len(world), actions=len(rows), halves=halves,
        output=str(output/'report.json')), indent=2))


if __name__ == '__main__':
    main()
