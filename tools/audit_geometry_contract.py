"""Research-only audit of fixed SoccerTrack camera artifacts; never fit or publish a model."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import pickletools
import zipfile

import cv2
import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def static_pose_literals(stream):
    """Inspect NPY/pickle syntax only; no unpickling, imports, REDUCE or BUILD execution.

    Only used after the exact camera archive passes its publisher checksum.
    This is a three-float audit of that known file, not a general object loader.
    """
    if np.lib.format.read_magic(stream) != (1, 0):
        raise ValueError('Unexpected pose header version')
    shape, _, dtype = np.lib.format.read_array_header_1_0(stream)
    if shape != (1, 3, 1) or not dtype.hasobject:
        raise ValueError('Unexpected pose header')
    payload = stream.read(4097)
    if len(payload) > 4096:
        raise ValueError('Pose syntax size cap exceeded')
    literals = [arg for op, arg, _ in pickletools.genops(payload) if op.name == 'BINFLOAT']
    if len(literals) != 3 or not np.isfinite(literals).all():
        raise ValueError('Expected exactly three finite pose literals')
    return np.array(literals, dtype=np.float64).reshape(3, 1)


def fixed_pose_homography(knew, rvec, tvec):
    rotation = cv2.Rodrigues(rvec)[0]
    h = knew @ np.column_stack((rotation[:, 0], rotation[:, 1], tvec[:, 0]))
    return h / h[2, 2]


def stats(errors):
    return dict(median=float(np.median(errors)), p95=float(np.quantile(errors, .95)),
                max=float(np.max(errors)), rms=float(np.sqrt(np.mean(errors**2))))


def prepare_reference_task(output):
    """Create unannotated external raw images, never labels from projections."""
    manifest = json.loads((ROOT/'docs/soccertrack_v1_2_video_download.json').read_text())
    entry = manifest['files'][0]
    video = ROOT/manifest['local_root']/entry['path']
    h = hashlib.sha256()
    with video.open('rb') as stream:
        for chunk in iter(lambda:stream.read(8*1024*1024), b''):
            h.update(chunk)
    if video.stat().st_size != entry['bytes'] or h.hexdigest() != entry['payload_sha256']:
        raise ValueError('Reference video checksum mismatch')
    capture = cv2.VideoCapture(str(video), cv2.CAP_FFMPEG)
    task = output/'reference-task'
    task.mkdir()
    images, rows = [], []
    features = ('near_touchline_y68', 'far_touchline_y0', 'halfway_x52.5',
                'left_penalty_edge_x16.5', 'right_penalty_edge_x88.5', 'center_circle')
    try:
        if not capture.isOpened():
            raise ValueError('Cannot decode reference video')
        for index in (7500,37500,60000):
            capture.set(cv2.CAP_PROP_POS_FRAMES,index)
            ok,frame = capture.read()
            if not ok or frame.shape != (1906,3840,3):
                raise ValueError('Reference frame decode mismatch')
            image = task/f'external-117092-frame-{index}-raw.png'
            if not cv2.imwrite(str(image),frame):
                raise OSError('Cannot write raw reference image')
            image_hash = hashlib.sha256(image.read_bytes()).hexdigest()
            images.append(dict(path=image.name,sha256=image_hash,frame_index_0_based=index,
                next_backend_frame=capture.get(cv2.CAP_PROP_POS_FRAMES),width=3840,height=1906))
            for feature in features:
                for point in (1,2,3):
                    rows.append(dict(image=image.name,image_sha256=image_hash,
                        frame_index_0_based=index,feature=feature,point=point,
                        pixel_x='',pixel_y='',visibility='',annotator='',
                        annotator_seen_predictions='',used_for_fitting='false'))
    finally:
        capture.release()
    with (task/'annotations.csv').open('x',newline='',encoding='utf-8') as stream:
        writer=csv.DictWriter(stream,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
    reference = dict(status='unannotated; not an evaluation dataset yet',
        video_sha256=entry['payload_sha256'],dataset_revision=manifest['revision'],
        match='117092',split='external_training_camera',images=images,
        requested_slots=len(rows),valid_annotations=0,labels_generated_from_projection=False,
        independent_cameras=1,protocol='docs/protokol_referensi_geometri_117092.md')
    (task/'manifest.json').write_text(json.dumps(reference,indent=2)+'\n',encoding='utf-8')
    return dict(path=str(task),requested_slots=len(rows),valid_annotations=0)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--prepare-reference-task',action='store_true')
    args = p.parse_args()
    output = args.output.resolve()
    output.relative_to(ROOT/'external_artifacts/v3')
    if output.exists():
        raise FileExistsError(output)
    manifest = json.loads((ROOT/'docs/soccertrack_v1_2_audit_download.json').read_text())
    base = ROOT/'Soccertrack V2'
    evidence = []
    for f in manifest['files']:
        data = (base/f['path']).read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        oid = hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
        if len(data) != f['bytes'] or (f['lfs'] and digest != f['payload_sha256']) or (not f['lfs'] and oid != f['git_oid']):
            raise ValueError('Artifact checksum mismatch: '+f['path'])
        evidence.append(dict(path=f['path'], sha256=digest))
    raw = base/'raw/117092'
    keypoints = json.loads((raw/'117092_keypoints.json').read_text())
    world = np.array([[float(x) for x in k.strip('()').split(',')] for k in keypoints])
    observed = np.array(list(keypoints.values()), dtype=np.float64)
    archive_path = raw/'117092_camera_intrinsics.npz'
    with np.load(archive_path, allow_pickle=False) as archive:
        k, d, knew, rms = archive['K'], archive['D'], archive['Knew'], float(archive['rms'])
    with zipfile.ZipFile(archive_path) as archive:
        with archive.open('rvecs.npy') as stream:
            rvec = static_pose_literals(stream)
        with archive.open('tvecs.npy') as stream:
            tvec = static_pose_literals(stream)
    h = np.load(raw/'117092_homography.npy', allow_pickle=False)
    regenerated_knew = cv2.fisheye.estimateNewCameraMatrixForUndistortRectify(
        k, d, (3840, 1906), np.eye(3), balance=1)
    hp = fixed_pose_homography(knew, rvec, tvec)
    obj = np.c_[world, np.zeros(len(world))].reshape(-1, 1, 3)
    pose_pixels = cv2.fisheye.projectPoints(obj, rvec, tvec, k, d)[0].reshape(-1, 2)
    def redistort(matrix):
        und = cv2.perspectiveTransform(world.reshape(-1, 1, 2), matrix)
        rays = cv2.perspectiveTransform(und, np.linalg.inv(knew))
        return cv2.fisheye.distortPoints(rays, k, d).reshape(-1, 2)
    supplied_pixels, algebra_pixels = redistort(h), redistort(hp)
    pose_errors = np.linalg.norm(pose_pixels-observed, axis=1)
    supplied_errors = np.linalg.norm(supplied_pixels-observed, axis=1)
    algebra_difference = float(np.max(np.abs(algebra_pixels-pose_pixels)))
    if algebra_difference > 1e-8 or abs(stats(pose_errors)['rms']-rms) > 1e-4:
        raise ValueError('Stored pose is not consistent with expected artifact contract')
    report = dict(checked_at=datetime.now(timezone.utc).isoformat(),
        dataset_revision=manifest['revision'], input_sha256=evidence,
        pose_extraction='static pickletools float literals after archive SHA256 verification; no pickle execution',
        fitted_parameters_changed=False, fit_called=False, independent_evaluation=False,
        Knew_reconstruction=dict(dimensions=[3840,1906], balance=1,
            max_absolute_difference=float(np.max(np.abs(regenerated_knew-knew)))),
        stored_pose=dict(rvec=rvec.tolist(), tvec=tvec.tolist(), stored_rms_px=rms,
            reproduced_fit_residual_px=stats(pose_errors)),
        algebra=dict(formula='Knew @ [R[:,0], R[:,1], t]; R=Rodrigues(stored rvec)',
            derived_homography=hp.tolist(), original_homography=h.tolist(),
            matrix_max_absolute_difference=float(np.max(np.abs(h-hp))),
            direct_pose_vs_derived_H_raw_pixel_max_abs=algebra_difference),
        supplied_H_fit_residual_px=stats(supplied_errors),
        chain_disagreement_raw_px=stats(np.linalg.norm(supplied_pixels-pose_pixels,axis=1)),
        conclusion='Knew and stored pose internally consistent; supplied H is not the exact plane homography of that pose',
        unresolved='Exact generating run/inlier mask for supplied H not provided; independent geometry and possession accuracy unproven',
        production_candidate_selected=False)
    # Original artifacts remain byte-identical; never save a replacement H.
    for e in evidence:
        if hashlib.sha256((base/e['path']).read_bytes()).hexdigest() != e['sha256']:
            raise ValueError('Input changed during audit')
    output.mkdir(parents=True)
    if args.prepare_reference_task:
        report['reference_task'] = prepare_reference_task(output)
    (output/'report.json').write_text(json.dumps(report,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__ == '__main__':
    main()
