"""Build/verify a portable copy of the already-frozen primary; never refit it."""
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import shutil

from .features import FEATURE_NAMES, FEATURE_UNITS
from .metrica_sample import frozen_candidate
from .prepare import REPO, sha256
from .training import FEATURE_SETS, HGB_PARAMS


def write_json(path,value):
    path.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+'\n',encoding='utf-8')


def safe_path(root,relative):
    path=(root/relative).resolve(strict=True);path.relative_to(root);return path


def verify_bundle(bundle,check_runtime=False):
    """Hash known packaged files before deserialization; no dataset I/O.

    Extra local runtime/venv/output files are allowed, but no known model, source,
    config or requirement may change. Optional runtime checking only reads
    installed version metadata, not model libraries or match inputs.
    """
    root=Path(bundle).resolve(strict=True)
    manifest=json.loads((root/'bundle_manifest.json').read_text())
    if manifest.get('status')!='ready' or manifest.get('bundle_version') not in (1,2):
        raise ValueError('ready versioned bundle required')
    for relative,digest in manifest['files_sha256'].items():
        if sha256(safe_path(root,relative))!=digest:raise ValueError('bundle hash mismatch: '+relative)
    from .features import CONTEXT_NAMES
    allowed = [list(FEATURE_SETS['no-signed-position'])]
    if manifest['bundle_version'] == 2:
        allowed.append(list(FEATURE_SETS['no-signed-position'] + CONTEXT_NAMES))
    if manifest['feature_names'] not in allowed:raise ValueError('bundle feature order mismatch')
    for field,hash_field in (('model_file','model_sha256'),('decoder_file','decoder_sha256')):
        if sha256(safe_path(root,manifest[field]))!=manifest[hash_field]:raise ValueError('bundle candidate hash mismatch')
    if check_runtime:
        actual={name:importlib.metadata.version(name) for name in manifest['packages']}
        if actual!=manifest['packages']:raise ValueError('bundle dependency versions differ; install bundled requirements in a local venv')
    return manifest


def load_bundle(bundle):
    """Load only verified trusted local artifacts; no fitting or model selection."""
    root=Path(bundle).resolve(strict=True);manifest=verify_bundle(root,check_runtime=True)
    import joblib
    artifact=joblib.load(safe_path(root,manifest['model_file']))
    model = artifact['model']
    if list(artifact['feature_names'])!=manifest['feature_names']:
        raise ValueError('serialized model configuration mismatch')
    algorithm = manifest.get('algorithm','hgb')
    if algorithm == 'coverage_router_v1':
        from .observation_router import CoverageRouter
        routing = manifest['routing']
        expected = dict(algorithm=algorithm,baseline=HGB_PARAMS,context=HGB_PARAMS,
                        home_reference=routing['home_reference'],away_reference=routing['away_reference'])
        if type(model) is not CoverageRouter or model.get_params()!=expected or model.n_features_in_!=18:
            raise ValueError('serialized router configuration mismatch')
    elif algorithm != 'hgb' or model.get_params()!=HGB_PARAMS:
        raise ValueError('serialized model configuration mismatch')
    parameters=json.loads(safe_path(root,manifest['decoder_file']).read_text())
    return artifact['model'],parameters


def verify_experiment_sources(experiment,manifest):
    """Bind packaged algorithm bytes to the evaluated source on either OS.

    Input: an external ready manifest and matching protocol. Output: verified
    relative SHA-256 map. Paths use forward slashes; only package Python and the
    pure metric source are allowed. Added/removed/modified modules fail closed.
    This performs no model or dataset loading and never follows provenance paths.
    """
    sources = {p.relative_to(REPO).as_posix():sha256(p) for p in (REPO/'external_baseline').glob('*.py')}
    sources['evaluation/possession_metrics.py'] = sha256(REPO/'evaluation/possession_metrics.py')
    expected = {p.replace('\\','/'):h for p,h in manifest.get('source_sha256',{}).items()}
    protocol = json.loads((experiment/'protocol.json').read_text())
    declared = {p.replace('\\','/'):h for p,h in protocol.get('source_sha256',{}).items()}
    if not expected or sources!=expected or declared!=expected:
        raise ValueError('experiment source differs from current package; evaluate these bytes before freezing')
    return sources


def revise_adapter(bundle,output):
    """Create a separate parser-only revision of a verified frozen bundle.

    Copy only files explicitly covered by the parent's manifest, never its
    directories or extra local inputs/outputs. Keep evaluated model-selection
    source provenance intact; separately attest the changed adapter sources
    and public organizer metadata. Model, feature, router and decoder bytes
    stay identical. No fitting, match input, GT or inference is invoked.
    """
    root,output=Path(bundle).resolve(strict=True),Path(output).resolve()
    if output.exists():raise FileExistsError(output)
    parent=verify_bundle(root,check_runtime=True)
    parent_digest=sha256(root/'bundle_manifest.json')
    allowed_roots={'src','model','provenance'}
    allowed_files={'README.md','feature_contract.json','requirements.txt',
                   'requirements-external-training.txt','CODE_LICENSE','run_tactical.py','verify_bundle.py'}
    for name in parent['files_sha256']:
        parts=Path(name).parts
        if 'tactical' in parts or not (parts[0] in allowed_roots or name in allowed_files):
            raise ValueError('parent file outside known source/model/provenance inventory')
    patched=('atd_inference.py','atd_periods.py','inference_bundle.py')
    new_sources={name:sha256(REPO/'external_baseline'/name) for name in patched}
    public_digest=sha256(REPO/'games.py')
    output.mkdir(parents=True)
    try:
        for name in parent['files_sha256']:
            destination=output/name;destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copyfile(safe_path(root,name),destination)
        for name in patched:
            shutil.copyfile(REPO/'external_baseline'/name,output/'src/external_baseline'/name)
        shutil.copyfile(REPO/'games.py',output/'src/organizer_game_metadata.py')
        # The old ready manifest is provenance, not a claim that new adapter
        # bytes were used for the historical external selection experiment.
        (output/'provenance/adapter').mkdir(parents=True)
        shutil.copyfile(root/'bundle_manifest.json',output/'provenance/adapter/parent_bundle_manifest.json')
        revision=dict(revision=1,kind='metadata_adapter_only',
            parent_bundle_manifest_sha256=parent_digest,
            reason='explicit public per-half source when provider fields do not describe two halves',
            period_sources=['provider','organizer-public'],default_period_source='provider',
            patched_source_sha256=new_sources,public_games_source_sha256=public_digest,
            public_documentation_sha256=sha256(REPO/'DATA.md'),
            public_source_origin='repository games.py:half_video_blocks and DATA.md:Frame alignment / Which frames are graded',
            source_scope='published per-half evaluation blocks, not possession labels or inferred kickoffs',
            video_convention='0-based inclusive',raw_atd_convention='1-based inclusive',
            conversion='raw_id=video_frame+1; never apply IdFrame offsets to raw IDs',
            classifier_retrained=False,model_changed=False,features_changed=False,
            router_thresholds_changed=False,decoder_parameters_changed=False,
            full_recording_fallback=False,official_data_read=False,official_inference_run=False)
        write_json(output/'provenance/adapter/revision.json',revision)
        contract=json.loads((output/'feature_contract.json').read_text())
        contract['scope']='two explicit halves from provider or verified public organizer metadata; X outside; no whole-recording fallback'
        write_json(output/'feature_contract.json',contract)
        (output/'README.md').write_text('# V2 adapter revision 1\n\n'
            'Frozen classifier, features, router thresholds and decoder unchanged. '
            'This revision adds an explicit public organizer period source; provider is still the default.\n\n'
            'Verify: `python -B verify_bundle.py --runtime`.\n\n'
            'Operator-only inference: `python -B run_tactical.py --bundle . --metadata PATH_XML '
            '--tracking PATH_TXT --output NEW_PATH --period-source organizer-public --game BAR-ATH --operator-local`.\n\n'
            'Organizer source is the included public games.py function half_video_blocks, '
            'with published video indices converted to inclusive raw ATD IDs by +1. '
            'It is not a zero-based guess about provider fields. Both halves remain separate '
            'for feature state and decoder calls. Rows outside the published per-half scope are X. '
            'The recording length/FPS must match the selected public game. '
            'No GT label or mask file, video, homography or Smart Tagging is opened.\n\n'
            'External model-selection provenance is inherited; the changed adapter is separately '
            'attested in provenance/adapter. Agent validation uses synthetic/public metadata only; '
            'actual official input compatibility and predictive quality remain unverified.\n',encoding='utf-8')
        if any(sha256(REPO/'external_baseline'/n)!=h for n,h in new_sources.items()) or sha256(REPO/'games.py')!=public_digest:
            raise ValueError('adapter/public source changed while packaging')
        for key,digest_key in (('model_file','model_sha256'),('decoder_file','decoder_sha256')):
            if sha256(output/parent[key])!=parent[digest_key]:raise ValueError('frozen model or decoder changed')
        manifest=dict(parent,adapter_revision=1,parent_bundle_manifest_sha256=parent_digest,
            organizer_metadata_file='src/organizer_game_metadata.py',adapter_provenance='provenance/adapter/revision.json',
            runtime_source_sha256={p.relative_to(output/'src').as_posix():sha256(p) for p in (output/'src').rglob('*.py')},
            files_sha256={p.relative_to(output).as_posix():sha256(p) for p in output.rglob('*') if p.is_file()})
        write_json(output/'bundle_manifest.json',manifest)
        verify_bundle(output,check_runtime=True)
        if sha256(root/'bundle_manifest.json')!=parent_digest:raise ValueError('parent manifest changed')
        verify_bundle(root,check_runtime=True)
        return manifest
    except Exception as error:
        if (output/'bundle_manifest.json').exists():
            failed=json.loads((output/'bundle_manifest.json').read_text());failed['status']='failed'
            write_json(output/'bundle_manifest.json',failed)
        write_json(output/'FAILED.json',dict(status='failed',error=str(error)))
        raise


def build_v2(experiment, output, assessment=None):
    """Freeze only a selected v2 single-change candidate after hash verification.

    Input is a ready external v2 run with protocol/selection/metrics hashes.
    Output is a new portable bundle, never an edit to v1. A rejected experiment
    cannot create a promoted bundle. Feature order (14 or 18), decoder version,
    metres/seconds, missing policy and causal context are carried explicitly.
    Runtime and the original baseline provenance come from verified v1. Official
    files are neither discovered nor copied; operator inference requires valid
    metadata half bounds and cannot silently use a full-recording segment.
    """
    experiment, output = Path(experiment).resolve(strict=True), Path(output).resolve()
    if output.exists(): raise FileExistsError(output)
    manifest = json.loads((experiment/'manifest.json').read_text())
    if manifest.get('status') != 'ready' or manifest.get('v2_version') != 2:
        raise ValueError('ready v2 experiment required')
    for name, digest in manifest['outputs_sha256'].items():
        if sha256(safe_path(experiment, name)) != digest:
            raise ValueError('experiment checksum mismatch')
    selection = json.loads((experiment/'selection.json').read_text())
    chosen = selection['selected']
    if chosen == 'A' or selection['violations'].get(chosen):
        raise ValueError('no accepted v2 candidate to freeze')
    if chosen not in ('C','R','B_a0_b0.5','B_a0_b1','B_a0.5_b0.5','B_a0.5_b1','B_a1_b0.5'):
        raise ValueError('unknown selected candidate')
    sources = verify_experiment_sources(experiment,manifest)
    protocol = json.loads((experiment/'protocol.json').read_text())
    if chosen == 'R' and protocol.get('algorithm')!='coverage_router_v1':
        raise ValueError('router protocol required')
    assessment_manifest = None
    if chosen == 'R':
        if assessment is None:
            raise ValueError('additional external assessment required before router release')
        assessment = Path(assessment).resolve(strict=True)
        assessment_manifest = json.loads((assessment/'manifest.json').read_text())
        if (assessment_manifest.get('status')!='ready' or not assessment_manifest.get('release_passed')
                or assessment_manifest.get('experiment_manifest_sha256')!=sha256(experiment/'manifest.json')
                or assessment_manifest.get('source_sha256')!=sources):
            raise ValueError('additional external assessment did not qualify this experiment')
        for name,digest in assessment_manifest['outputs_sha256'].items():
            if sha256(safe_path(assessment,name))!=digest:
                raise ValueError('assessment checksum mismatch')
    baseline = REPO/'external_artifacts/inference-bundle-v1'
    descriptor = verify_bundle(baseline, check_runtime=True)
    from .features import CONTEXT_NAMES, CONTEXT_UNITS
    uses_context = chosen in ('C','R')
    names = FEATURE_SETS['no-signed-position'] + (CONTEXT_NAMES if uses_context else ())
    output.mkdir(parents=True)
    try:
        (output/'model').mkdir()
        model_source = experiment/f'model_{chosen}.joblib' if uses_context else baseline/'model/model.joblib'
        shutil.copyfile(model_source, output/'model/model.joblib')
        shutil.copyfile(experiment/'selected_decoder.json', output/'model/decoder_parameters.json')
        for path in (REPO/'external_baseline').glob('*.py'):
            target = output/'src/external_baseline'/path.name
            target.parent.mkdir(parents=True, exist_ok=True); shutil.copyfile(path, target)
        target = output/'src/evaluation/possession_metrics.py'
        target.parent.mkdir(parents=True); shutil.copyfile(REPO/'evaluation/possession_metrics.py', target)
        shutil.copytree(baseline/'provenance', output/'provenance/baseline')
        for name in ('protocol.json', 'selection.json', 'diagnosis.json', 'metrics.json', 'manifest.json'):
            shutil.copyfile(experiment/name, output/'provenance'/name)
        if assessment_manifest is not None:
            (output/'provenance/assessment').mkdir()
            for name in ('protocol.json','metrics.json','decision.json','manifest.json'):
                shutil.copyfile(assessment/name,output/'provenance/assessment'/name)
        for name in ('requirements.txt', 'requirements-external-training.txt', 'CODE_LICENSE', 'run_tactical.py', 'verify_bundle.py'):
            shutil.copyfile(baseline/name, output/name)
        write_json(output/'feature_contract.json', dict(feature_version=2 if uses_context else 1,
            feature_names=list(FEATURE_NAMES + (CONTEXT_NAMES if uses_context else ())),
            model_features=list(names), units=dict(FEATURE_UNITS, **(CONTEXT_UNITS if uses_context else {})),
            fps=25, missing='NULL/NaN; no coordinate imputation',
            temporal='causal trailing 25 frames; reset match/half/frame/time gap',
            scope='explicit metadata halves; no full-recording fallback'))
        (output/'README.md').write_text('# Frozen external v2 candidate\n\n'
            + f'Candidate: {chosen}. Selected on reused J03WQQ development validation; no independent generalization claim.\n\n'
            + 'Install requirements in a local Python 3.11 venv; run verify_bundle.py --runtime. '
            + 'The local operator runs run_tactical.py --bundle . --metadata PATH --tracking PATH --output NEW_PATH --operator-local. '
            + 'Declared 25 Hz metadata half bounds are mandatory. No official data was validated by the agent. '
            + 'See provenance for selection, limitations, DFL attribution and CC-BY 4.0 license.\n', encoding='utf-8')
        write_json(output/'bundle_manifest.json', dict(status='ready', bundle_version=2, candidate=chosen,
            algorithm=protocol.get('algorithm','hgb'), routing=protocol.get('routing'),
            evaluated_source_sha256=sources,
            additional_assessment=assessment_manifest,
            model_file='model/model.joblib', decoder_file='model/decoder_parameters.json',
            model_sha256=sha256(output/'model/model.joblib'), decoder_sha256=sha256(output/'model/decoder_parameters.json'),
            feature_names=list(names), packages=descriptor['packages'], actual_official_data_validated=False,
            files_sha256={p.relative_to(output).as_posix():sha256(p) for p in output.rglob('*') if p.is_file()}))
        if any(sha256(REPO/name)!=digest or sha256(output/'src'/name)!=digest for name,digest in sources.items()):
            raise ValueError('source changed during packaging')
        verify_bundle(output, check_runtime=True)
    except Exception as error:
        write_json(output/'FAILED.json', dict(status='failed', error=str(error)))
        raise


README='''# Frozen possession inference bundle

This package copies the predeclared expanded primary model and its decoder.
No model, prior, transition, threshold or feature was fitted/changed for packaging.

Run from this directory using a Python 3.11 virtual environment on the project
drive. The existing project training venv already has the required versions.
If creating another environment, keep downloads and temporary files local:

```bash
mkdir -p runtime/tmp
export TMPDIR="$PWD/runtime/tmp"
export SQLITE_TMPDIR="$TMPDIR"
export PIP_NO_CACHE_DIR=1
python3.11 -m venv .venv
.venv/bin/python -m pip install --no-cache-dir -r requirements.txt
.venv/bin/python verify_bundle.py --runtime
```

The operator, not the agent, runs official inference locally:

```bash
.venv/bin/python run_tactical.py --bundle . \\
  --metadata /YOUR/LOCAL/tactical_atd.xml \\
  --tracking /YOUR/LOCAL/tactical_atd.txt \\
  --output /YOUR/PROJECT/local_official_artifacts/run1 --operator-local
```

Default expected length is 199,319 tactical frames, raw ATD IDs 1..199319 and
submission frames 0..199318. The adapter accepts declared FIFA format ranges,
player-channel mappings, normalized x/y, 25 Hz, pitch dimensions and inclusive
1-based first/second-half bounds from metadata. Missing/unsupported/conflicting
metadata fails rather than guessing. Team IDs use local/visiting score metadata,
or documented FIFA team order when those attributes are absent. Anonymous slots
are not player-velocity identities. Player slots with no finite axes are omitted;
partial axes remain missing. Finite outside positions are never clipped.

Each half is decoded independently. Rows outside metadata half ranges become X.
No official GT mask, video, homography, Smart Tagging or evaluation GT is opened.
All raw rows must exist exactly once in order; missing raw rows are an error,
not silently invented. No per-frame adjustment, tuning or calibration is allowed.

Outputs: submission.csv (decoded), submission_raw.csv, scoped features.sqlite,
predictions.sqlite, report.json and a ready hash manifest. Existing output paths
are rejected. The CSV contract is checked structurally, never against GT.
Local actual outputs are private: keep them under an ignored
local_official_artifacts/ directory and do not send them back to the agent.

The agent validated this adapter with synthetic fixtures, including the complete
199,319-row contract; it has NOT inspected or tested the actual official input.
No correctness/competition-score guarantee follows from format validation.
The Metrica sample review also showed strong D-to-alive decoder changes; source
domain/decoder behavior remains a limitation and is documented separately.

Training data attribution: Deutsche Fussball Liga (DFL); Bassek, Rein, Weber and
Memmert (2025), Scientific Data 12:195, doi:10.1038/s41597-025-04505-y; CC-BY 4.0.
Model/source provenance and assessment history are retained under provenance/.
J03WOY and J03WR9 are consumed assessment evidence, not unused future tests.
Only load this project's own trusted local joblib models.
'''


def build(snapshot,output):
    """Copy the frozen primary, source, requirements and provenance to new dir.

    No match data, predictions, GT or diagnostic files are read/copied. The
    source snapshot supplies model hashes, exact runtime and original feature
    contract; current adapter code is separately hashed for reproducibility.
    """
    snapshot=Path(snapshot).resolve(strict=True);output=Path(output).resolve()
    if output.exists():raise FileExistsError(output)
    candidate,paths=frozen_candidate(snapshot)
    protocol=json.loads((snapshot/'protocol.json').read_text())
    source_paths=list(sorted((REPO/'external_baseline').glob('*.py')))
    initial={str(p):sha256(p) for p in [*paths,*source_paths]}
    output.mkdir(parents=True)
    try:
        model_dir=output/'model';model_dir.mkdir()
        shutil.copyfile(paths[2],model_dir/'model.joblib')
        shutil.copyfile(paths[3],model_dir/'decoder_parameters.json')
        for p in source_paths:
            target=output/'src/external_baseline'/p.name
            target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,target)
        # Preserve the original metric source for complete source provenance.
        target=output/'src/evaluation/possession_metrics.py';target.parent.mkdir(parents=True)
        shutil.copyfile(REPO/'evaluation/possession_metrics.py',target)
        provenance=output/'provenance';provenance.mkdir()
        for name in ('protocol.json','snapshot_manifest.json','expanded_manifest.json','old_classifier_manifest.json'):
            if (snapshot/name).is_file():shutil.copyfile(snapshot/name,provenance/name)
        shutil.copyfile(snapshot/'requirements-multimatch-training.txt',output/'requirements.txt')
        shutil.copyfile(snapshot/'requirements-external-training.txt',output/'requirements-external-training.txt')
        shutil.copyfile(REPO/'LICENSE',output/'CODE_LICENSE')
        write_json(output/'feature_contract.json',dict(feature_names=FEATURE_NAMES,units=FEATURE_UNITS,
            model_features=FEATURE_SETS['no-signed-position'],fps=25,coordinates='centred metres, positive y up',
            missing='NULL/NaN; never imputed; speed from contiguous ball only',scope='provided metadata halves only'))
        (output/'README.md').write_text(README,encoding='utf-8')
        runner="from pathlib import Path\nimport sys\nsys.path.insert(0,str(Path(__file__).resolve().parent/'src'))\nfrom external_baseline.atd_inference import main\nif __name__=='__main__':main()\n"
        (output/'run_tactical.py').write_text(runner,encoding='utf-8')
        verifier="from pathlib import Path\nimport sys,argparse\nroot=Path(__file__).resolve().parent\nsys.path.insert(0,str(root/'src'))\nfrom external_baseline.inference_bundle import verify_bundle\np=argparse.ArgumentParser();p.add_argument('--runtime',action='store_true');a=p.parse_args()\nverify_bundle(root,a.runtime)\nprint('Bundle verified')\n"
        (output/'verify_bundle.py').write_text(verifier,encoding='utf-8')
        if any(sha256(Path(p))!=h for p,h in initial.items()):raise ValueError('packaging input/source changed')
        manifest=dict(status='ready',bundle_version=1,candidate=candidate.get('display_name','frozen_primary'),
            model_file='model/model.joblib',decoder_file='model/decoder_parameters.json',
            model_sha256=candidate['model_sha256'],decoder_sha256=candidate['parameters_sha256'],
            feature_names=list(FEATURE_SETS['no-signed-position']),packages=protocol.get('full_runtime_packages',protocol['packages']),
            python_build=platform.python_version(),frozen_protocol_sha256=sha256(snapshot/'protocol.json'),
            files_sha256={str(p.relative_to(output)):sha256(p) for p in sorted(output.rglob('*')) if p.is_file()},
            actual_official_data_validated=False,synthetic_validation_required=True,fitting=False,tuning=False)
        write_json(output/'bundle_manifest.json',manifest)
        verify_bundle(output,check_runtime=True)
        print(json.dumps({'bundle':str(output),'candidate':manifest['candidate'],'model_sha256':manifest['model_sha256']},indent=2))
        return manifest
    except Exception as error:
        write_json(output/'FAILED.json',dict(status='failed',error=str(error)));raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    sub=parser.add_subparsers(dest='action',required=True)
    create=sub.add_parser('build');create.add_argument('--snapshot',type=Path,required=True);create.add_argument('--output',type=Path,required=True)
    verify=sub.add_parser('verify');verify.add_argument('--bundle',type=Path,required=True);verify.add_argument('--runtime',action='store_true')
    revise=sub.add_parser('revise-adapter');revise.add_argument('--bundle',type=Path,required=True);revise.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.action=='build':build(args.snapshot,args.output)
    elif args.action=='revise-adapter':revise_adapter(args.bundle,args.output);print('Adapter revision verified')
    else:verify_bundle(args.bundle,args.runtime);print('Bundle verified')


if __name__=='__main__':main()
