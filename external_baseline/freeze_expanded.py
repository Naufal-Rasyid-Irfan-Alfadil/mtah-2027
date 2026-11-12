"""Freeze expanded and old augmented pipelines for the existing holdout evaluator.

Import/help perform no data access. Freezing reads manifests and model bytes,
never match data, predictions or metrics, and never deserializes/fits a model.
"""

import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil

from .features import FEATURE_NAMES, FEATURE_UNITS
from .multimatch import validate_reference, write_json
from .prepare import REPO, sha256, git_metadata
from .training import FEATURE_SETS, HGB_PARAMS, PACKAGES, read_ready_manifest


def freeze(expanded, classifier, decoder, test_match, output, confirm_unused=False):
    """Snapshot two local external-trained pipelines and the exact source/runtime.

    Retain 14 centred-metre/25-Hz observation features and each candidate's own
    decoder. Reject training/development/consumed assessment IDs. Confirmation
    is a user statement of full project history, not inferred from file absence.
    Pending snapshots cannot evaluate; confirmed snapshots support holdout v1.
    Outputs are new directories with relative candidate paths and SHA-256 hashes.
    """
    expanded = Path(expanded).resolve(strict=True)
    em = read_ready_manifest(expanded/'manifest.json')
    policy = em['protocol']
    if (em.get('multimatch_version') != 1 or policy['hgb_params'] != HGB_PARAMS
            or policy['feature_names'] != list(FEATURE_SETS['no-signed-position'])):
        raise ValueError('ready fixed expanded 14-feature model required')
    forbidden = set(policy['training'] + policy['validation'] + policy.get('consumed_assessment', []))
    if not test_match or test_match in forbidden:
        raise ValueError('test match was already used for training/development/assessment')
    for path, digest in em['source_sha256'].items():
        if sha256(REPO/path) != digest:
            raise ValueError('expanded pipeline source changed before freezing')
    old_model, old_params, reference_paths = validate_reference(classifier, decoder)
    classifier, decoder = Path(classifier).resolve(), Path(decoder).resolve()
    dm = read_ready_manifest(decoder/'manifest.json')
    if sha256(classifier/'manifest.json') not in dm['inputs_sha256'].values():
        raise ValueError('old classifier/decoder lineage mismatch')
    packages = {p:importlib.metadata.version(p) for p in PACKAGES}
    if em['packages'] != packages:
        raise ValueError('expanded dependency versions differ from current runtime')
    selected = ['model.joblib', 'decoder_parameters.json', 'protocol.json']
    for name in selected:
        if sha256(expanded/name) != em['outputs_sha256'][name]:
            raise ValueError('expanded candidate artifact hash mismatch')
    inputs = {str(p):sha256(p) for p in [expanded/'manifest.json', *[expanded/n for n in selected], *reference_paths]}
    source_paths = sorted((REPO/'external_baseline').glob('*.py')) + [REPO/'evaluation/possession_metrics.py']
    code_hashes = {str(p.relative_to(REPO)):sha256(p) for p in source_paths}
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    try:
        candidates = {}
        # The legacy evaluator's augmented key is the predeclared primary.
        # Display names make clear that original is also an augmented model.
        for name, display, model, parameters in (
            ('original','old_augmented',old_model,old_params),
            ('augmented','expanded',expanded/'model.joblib',expanded/'decoder_parameters.json')):
            directory = output/name
            directory.mkdir()
            for src, target in ((model,'model.joblib'),(parameters,'decoder_parameters.json')):
                shutil.copyfile(src, directory/target)
                if sha256(src) != sha256(directory/target):
                    raise ValueError('candidate snapshot copy differs')
            candidates[name] = dict(display_name=display, model_file=f'{name}/model.joblib',
                model_sha256=sha256(directory/'model.joblib'), parameters_file=f'{name}/decoder_parameters.json',
                parameters_sha256=sha256(directory/'decoder_parameters.json'),
                feature_names=list(FEATURE_SETS['no-signed-position']), hgb_params=HGB_PARAMS)
        # Preserve provenance and dependencies, without copying predictions or data.
        shutil.copyfile(expanded/'manifest.json', output/'expanded_manifest.json')
        shutil.copyfile(expanded/'protocol.json', output/'development_protocol.json')
        shutil.copyfile(classifier/'manifest.json', output/'old_classifier_manifest.json')
        shutil.copyfile(decoder/'manifest.json', output/'old_decoder_manifest.json')
        for relative in code_hashes:
            target = output/'source'/relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(REPO/relative, target)
        requirements = {}
        for name in ('requirements-external-training.txt','requirements-multimatch-training.txt'):
            shutil.copyfile(REPO/name, output/name)
            requirements[name] = sha256(output/name)
        installed = {name:importlib.metadata.version(name) for name in
                     (*PACKAGES,'python-dateutil','tzdata')}
        if any(sha256(Path(p)) != h for p,h in inputs.items()) or any(sha256(REPO/p) != h for p,h in code_hashes.items()):
            raise ValueError('input/source changed while freezing')
        protocol = dict(status='ready', contract_version=1, holdout_version=1,
            expanded_freeze_version=1, test_match=test_match, primary='augmented', primary_display_name='expanded',
            candidates=candidates, development_matches=sorted(set(policy['training']+policy['validation'])),
            consumed_assessment=policy.get('consumed_assessment', []),
            history_confirmed_unused=bool(confirm_unused),
            history_basis='explicit user confirmation covers this and old projects; filesystem absence is not evidence',
            evaluation='external_baseline.holdout evaluate; both halves test; all predictions precede target loading',
            metrics=dict(primary='spell_f1_mean', additional=['macro_f1','per_class','transitions'],
                         spell_ious=[.3,.4,.5,.6,.7], transition_tolerances_frames=[12,25], fps=25),
            feature_contract=dict(observation_features=list(FEATURE_NAMES), units=FEATURE_UNITS,
                model_features=list(FEATURE_SETS['no-signed-position']),
                missing='NULL/NaN, no imputation; retain gaps/half boundaries; no target-derived inputs'),
            policy='no fit/tuning/calibration/threshold changes or automatic winner; reuse for selection/tuning consumes test as development',
            decoder_policy='each candidate retains its own fixed decoder; no test-derived priors/transitions',
            inputs_sha256=inputs, source_sha256=code_hashes, requirements_sha256=requirements,
            packages=packages, full_runtime_packages=installed, python=platform.python_version(), git=git_metadata())
        write_json(output/'protocol.json', protocol)
        files = {str(p.relative_to(output)):sha256(p) for p in sorted(output.rglob('*')) if p.is_file()}
        write_json(output/'snapshot_manifest.json', dict(status='ready', files_sha256=files,
            test_data_access=False, model_deserialization=False, fitting=False))
        return protocol
    except Exception as error:
        write_json(output/'FAILED.json', dict(status='failed', error=str(error)))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('expanded','reference-classifier','reference-decoder','output'):
        parser.add_argument('--'+name, required=True, type=Path)
    parser.add_argument('--test-match', required=True)
    parser.add_argument('--confirm-unused', action='store_true')
    args = parser.parse_args()
    protocol = freeze(args.expanded,args.reference_classifier,args.reference_decoder,
                      args.test_match,args.output,args.confirm_unused)
    print(json.dumps({k:protocol[k] for k in ('test_match','primary_display_name','history_confirmed_unused')},indent=2))


if __name__ == '__main__':
    main()
