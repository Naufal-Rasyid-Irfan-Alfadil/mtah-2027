"""Checksum-bound diagnostics on one external video; no fitting or possession model."""
import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
from pathlib import Path

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(8*1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve()
    output.relative_to(ROOT/'external_artifacts/v3')
    if output.exists():
        raise FileExistsError(output)
    specification = json.loads((ROOT/'docs/soccertrack_v1_2_video_download.json').read_text())
    entry = specification['files'][0]
    base = (ROOT/specification['local_root']).resolve()
    video = (base/entry['path']).resolve(strict=True)
    video.relative_to(base)
    before = video.stat()
    if before.st_size != entry['bytes'] or digest(video) != entry['payload_sha256']:
        raise ValueError('External video checksum/size mismatch')
    package = json.loads((ROOT/'docs/soccertrack_v1_2_audit_download.json').read_text())
    for f in package['files']:
        p = (base/f['path']).resolve(strict=True)
        p.relative_to(base)
        b = p.read_bytes()
        oid = hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()
        if len(b) != f['bytes'] or (not f['lfs'] and oid != f['git_oid']):
            raise ValueError('External package mismatch: '+f['path'])
        if f['lfs'] and hashlib.sha256(b).hexdigest() != f.get('payload_sha256'):
            raise ValueError('External numeric payload checksum mismatch')
    raw = base/'raw/117092'
    kp = json.loads((raw/'117092_keypoints.json').read_text())
    world = np.array([[float(v) for v in key.strip('()').split(',')] for key in kp], dtype=np.float64)
    observed = np.array(list(kp.values()), dtype=np.float64)
    with np.load(raw/'117092_camera_intrinsics.npz', allow_pickle=False) as z:
        k, d, knew = z['K'], z['D'], z['Knew']
    h = np.load(raw/'117092_homography.npy', allow_pickle=False)
    # The publisher's documented chain, held fixed for diagnosis. These points
    # were used in its calibration fit, so residuals are explicitly not holdout.
    projected_undistorted = cv2.perspectiveTransform(world.reshape(-1, 1, 2), h)
    normalized = cv2.perspectiveTransform(projected_undistorted, np.linalg.inv(knew))
    predicted = cv2.fisheye.distortPoints(normalized, k, d).reshape(-1, 2)
    undistorted_observed = cv2.fisheye.undistortPoints(observed.reshape(-1, 1, 2), k, d, P=knew)
    raw_errors = np.linalg.norm(predicted-observed, axis=1)
    und_errors = np.linalg.norm(projected_undistorted.reshape(-1,2)-undistorted_observed.reshape(-1,2), axis=1)
    def stats(values):
        return dict(median=float(np.median(values)), p95=float(np.quantile(values, .95)),
                    max=float(np.max(values)))
    capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG)
    if not capture.isOpened():
        raise ValueError('Cannot decode verified external video')
    info = {key:capture.get(prop) for key, prop in dict(fps=cv2.CAP_PROP_FPS,
        container_frame_count=cv2.CAP_PROP_FRAME_COUNT, width=cv2.CAP_PROP_FRAME_WIDTH,
        height=cv2.CAP_PROP_FRAME_HEIGHT).items()}
    if info['fps'] != 25 or info['container_frame_count'] != 67375:
        capture.release()
        raise ValueError('Stream differs from pinned release changelog')
    output.mkdir(parents=True)
    samples = []
    try:
        for index in (0, 30000, 67374):
            capture.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = capture.read()
            if not ok or frame.shape[:2] != (int(info['height']), int(info['width'])):
                raise ValueError('External sample decode failed')
            name = f'external-117092-frame-{index}.jpg'
            preview = cv2.resize(frame, (1920, 953))
            if not cv2.imwrite(str(output/name), preview):
                raise OSError('Cannot save preview')
            samples.append(dict(requested_video_index_0_based=index,
                backend_next_frame_position=capture.get(cv2.CAP_PROP_POS_FRAMES),
                backend_position_ms=capture.get(cv2.CAP_PROP_POS_MSEC),
                decoded_shape=list(frame.shape), preview=name))
            if index == 30000:
                overlay = frame.copy()
                for obs, pred in zip(observed, predicted):
                    a, b = tuple(np.rint(obs).astype(int)), tuple(np.rint(pred).astype(int))
                    cv2.line(overlay, a, b, (0, 200, 255), 2)
                    cv2.circle(overlay, a, 9, (0, 255, 0), 2)
                    cv2.drawMarker(overlay, b, (0, 0, 255), cv2.MARKER_CROSS, 18, 2)
                cv2.putText(overlay, 'EXTERNAL TRAINING: green=fit keypoints, red=fixed H+fisheye; diagnostic only',
                    (35, 65), cv2.FONT_HERSHEY_SIMPLEX, 1.0, (255,255,255), 2)
                cv2.imwrite(str(output/'geometry-diagnostic.jpg'), cv2.resize(overlay, (1920,953)))
    finally:
        capture.release()
    after = video.stat()
    if (before.st_size, before.st_mtime_ns) != (after.st_size, after.st_mtime_ns):
        raise ValueError('Video changed during audit')
    report = dict(checked_at=datetime.now(timezone.utc).isoformat(), dataset=specification['dataset'],
        revision=specification['revision'], video=dict(path=entry['path'], bytes=before.st_size,
        sha256=entry['payload_sha256'], evidence=entry['payload_sha256_evidence']),
        packages={p:importlib.metadata.version(p) for p in ['numpy','opencv-python-headless']},
        stream=info, samples=samples, all_frames_decoded=False,
        geometry=dict(contract='corner pitch metres -> H -> undistorted pixels -> inverse Knew -> fisheye K/D -> raw pixels',
            keypoints=65, raw_pixel_residual=stats(raw_errors), undistorted_pixel_residual=stats(und_errors),
            raw_pixel_residual_by_pitch_y={str(y):dict(count=int(np.sum(world[:,1]==y)),
                **stats(raw_errors[world[:,1]==y])) for y in (0.0,68.0)},
            independent_test=False, parameters_modified=False, refitting=False),
        empirical_event_alignment_verified=False, independent_possession_target_available=False,
        status='integrity_stream_samples_passed; geometry_diagnostic_only; production_blocked')
    report['outputs_sha256'] = {p.name:digest(p) for p in output.glob('*.jpg')}
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(status=report['status'], stream=info,
        raw_pixel_residual=stats(raw_errors), report=str(output/'report.json')), indent=2))


if __name__ == '__main__':
    main()
