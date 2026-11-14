"""Validate a recovered V2 release using synthetic inputs only; never score a match."""
import argparse
from contextlib import redirect_stdout, redirect_stderr
from datetime import datetime
import hashlib
import importlib.metadata
import json
import os
import platform
from pathlib import Path
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    source, output = args.source.resolve(), args.output.resolve()
    source.relative_to(ROOT)
    output.relative_to(ROOT)
    output.mkdir(parents=True, exist_ok=False)
    temp = ROOT / 'runtime/tmp'
    temp.mkdir(parents=True, exist_ok=True)
    os.environ['TEMP'] = os.environ['TMP'] = str(temp)
    tempfile.tempdir = str(temp)
    # No enumeration of datasets. Reject original official/unknown inputs even
    # if a future test accidentally references them.
    def guard(event, arguments):
        if event not in ('open', 'os.listdir', 'os.scandir', 'sqlite3.connect'):
            return
        if not arguments or not isinstance(arguments[0], (str, bytes, os.PathLike)):
            return
        p = Path(os.fsdecode(arguments[0])).resolve()
        forbidden = (ROOT/'data', ROOT/'evaluation/gt', ROOT/'evaluation/results',
                     ROOT/'local_official_artifacts', ROOT/'mtah-2027',
                     ROOT/'inference-bundle-v1')
        if any(p == q or q in p.parents for q in forbidden):
            raise PermissionError('Official or unverified input blocked')
        artifacts = ROOT/'external_artifacts'
        if (p == artifacts or artifacts in p.parents) and not (p == source or source in p.parents or p == output or output in p.parents):
            raise PermissionError('Unverified artifact blocked')
    sys.addaudithook(guard)
    sys.path[:0] = [str(source), str(source/'tests')]
    handoff = json.loads((source/'HANDOFF_MANIFEST.json').read_text(encoding='utf-8'))
    for name, digest in handoff['files_sha256'].items():
        if sha(source/name) != digest:
            raise ValueError('Recovered handoff checksum mismatch: '+name)
    from external_baseline.inference_bundle import verify_bundle, load_bundle
    bundle = source/'external_artifacts/v2/inference-bundle-v2-r1'
    manifest = verify_bundle(bundle, check_runtime=True)
    report = dict(status='checking', official_data_access=False,
                  checked_at=datetime.now().astimezone().isoformat(),
                  python=sys.version, executable=sys.executable, platform=platform.platform(),
                  handoff_files_verified=len(handoff['files_sha256']),
                  packages={p: importlib.metadata.version(p) for p in manifest['packages']},
                  bundle_manifest_sha256=sha(bundle/'bundle_manifest.json'),
                  model_sha256=sha(bundle/manifest['model_file']),
                  decoder_sha256=sha(bundle/manifest['decoder_file']))
    modules = ['test_atd_period_sources', 'test_metadata_preflight',
               'test_local_inference', 'test_observation_router']
    with (output/'synthetic-tests.log').open('x', encoding='utf-8') as log:
        with redirect_stdout(log), redirect_stderr(log):
            suite = unittest.defaultTestLoader.loadTestsFromNames(modules)
            result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    report['tests'] = dict(run=result.testsRun, failures=len(result.failures), errors=len(result.errors))
    if not result.wasSuccessful():
        report['status'] = 'tests_failed'
        (output/'report.json').write_text(json.dumps(report, indent=2)+'\n')
        raise RuntimeError('Synthetic checks failed; see log')
    # Load the actual trusted, checksum-verified frozen R. Verify routing on
    # missing observations without fitting, scoring, or reading any match.
    import numpy as np
    model, _ = load_bundle(bundle)
    x = np.full((3, 18), np.nan)
    np.testing.assert_array_equal(model.predict_proba(x), model.baseline.predict_proba(x[:, :14]))
    report['frozen_R_missing_observation_fallback'] = 'identical_to_A'
    from external_baseline.atd_inference import run
    from test_local_inference import metadata_xml
    with tempfile.TemporaryDirectory() as folder:
        fixture = Path(folder)
        metadata, tracking = fixture/'synthetic.xml', fixture/'synthetic.txt'
        metadata.write_text(metadata_xml(), encoding='utf-8')
        tracking.write_text(''.join(f'{i}:.4,.5;.5,.6:.5,.5\n' for i in range(1, 9)), encoding='utf-8')
        with (output/'frozen-R-synthetic.log').open('x', encoding='utf-8') as log, redirect_stdout(log):
            run(bundle, metadata, tracking, fixture/'out', expected=8)
        report['frozen_R_synthetic_rows'] = 8
    verify_bundle(bundle, check_runtime=True)
    for name, digest in handoff['files_sha256'].items():
        if sha(source/name) != digest:
            raise ValueError('Synthetic checks changed handoff bytes: '+name)
    archive = output/'inference-bundle-v2-r1.zip'
    inventory = dict(manifest['files_sha256'])
    inventory['bundle_manifest.json'] = sha(bundle/'bundle_manifest.json')
    with zipfile.ZipFile(archive, 'x', zipfile.ZIP_DEFLATED) as z:
        for name in sorted(inventory):
            z.write(bundle/name, 'inference-bundle-v2-r1/'+name)
    with zipfile.ZipFile(archive) as z:
        assert len(z.namelist()) == len(inventory)
        for name, digest in inventory.items():
            if hashlib.sha256(z.read('inference-bundle-v2-r1/'+name)).hexdigest() != digest:
                raise ValueError('Archive checksum mismatch: '+name)
    # A moved copy must pass the unmodified verifier as well.
    with tempfile.TemporaryDirectory() as folder:
        with zipfile.ZipFile(archive) as z:
            z.extractall(folder)
        verify_bundle(Path(folder)/'inference-bundle-v2-r1', check_runtime=True)
    report.update(status='ready_synthetic_only', zip_sha256=sha(archive),
                  zip_members_verified=len(inventory), moved_bundle_verified=True,
                  actual_official_compatibility='not_validated',
                  DFL_dataset_fallback='pending_external_data_acquisition')
    (output/'report.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
