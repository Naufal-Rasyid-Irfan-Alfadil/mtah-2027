"""Bounded local external A/B/C experiment; no official asset discovery.

Run: python -B -m external_baseline.v2 --output external_artifacts/v2/run1
Only the three documented DFL matches below are read. Validation is reused
development evidence, never an untouched test. No test-match scoring or downloads.
Outputs are append-only protocol, diagnosis, keyed NPZ posteriors/predictions,
metrics, selection, C model (if justified), and a hash manifest. C fits once.
"""
import argparse
from contextlib import closing
import copy
import gc
import json
from pathlib import Path
import platform

from .prepare import REPO, sha256
from .multimatch import (validate_match, validate_partitions, read_only,
                         feature_half, fit_pool, write_json)
from .features import FEATURE_NAMES, CONTEXT_NAMES
from .training import (FEATURE_SETS, HGB_PARAMS, load_split, predict_raw,
                       project_features, evaluate_timeline)
from .robustness import SCENARIOS, stress_feature_matrices
from .temporal import decode_probabilities
from .diagnostics import contiguous_runs, label_run_summary
from .inference_bundle import load_bundle, verify_bundle

MODEL_NAMES = FEATURE_SETS['no-signed-position'] + CONTEXT_NAMES
PROJECT = [i for i, n in enumerate(FEATURE_NAMES + CONTEXT_NAMES)
           if n not in ('ball_x_m', 'ball_y_m')]


def decoder_grid(baseline):
    """Five predefined B scores; A retains its exact version-1 parameters."""
    result = {'A': copy.deepcopy(baseline)}
    for alpha in (0, .5, 1):
        for beta in (.5, 1):
            if (alpha, beta) != (1, 1):
                result[f'B_a{alpha}_b{beta}'] = dict(baseline, decoder_version=2,
                    prior_correction=alpha, transition_weight=beta)
    return result


def guard_metrics(candidate, baseline):
    """Return named violations of the predeclared absolute .01 F1 safeguards."""
    violations = []
    for name in ('macro_f1',):
        if candidate[name] < baseline[name] - .01 - 1e-12:
            violations.append(name)
    if candidate['per_class']['D']['f1'] < baseline['per_class']['D']['f1'] - .01 - 1e-12:
        violations.append('D_f1')
    for tau in (12, 25):
        if candidate['transitions'][tau]['f1'] < baseline['transitions'][tau]['f1'] - .01 - 1e-12:
            violations.append(f'transition_{tau}')
    return violations


def select(metrics):
    """Select once from paired development scores, never historical test scores.

    metrics[candidate][scenario][overall/half_1/half_2] contains evaluator dicts.
    All stress guards compare the same scenario to A; thresholds use F1 units.
    Exact ties prefer Macro F1, then B over C and B closest to A.
    """
    reasons, passed = {}, []
    for name, scenarios in metrics.items():
        if name == 'A':
            continue
        c, a = scenarios['clean']['overall'], metrics['A']['clean']['overall']
        failures = guard_metrics(c, a)
        if c['spell_f1_mean'] < a['spell_f1_mean'] + .01 - 1e-12:
            failures.append('clean_spell_gain_below_0.01')
        for half in ('half_1', 'half_2'):
            if scenarios['clean'][half]['spell_f1_mean'] < metrics['A']['clean'][half]['spell_f1_mean'] - .01 - 1e-12:
                failures.append(half + '_spell')
        for scenario in scenarios:
            if scenario == 'clean':
                continue
            sc, sa = scenarios[scenario]['overall'], metrics['A'][scenario]['overall']
            failures.extend(scenario + ':' + f for f in guard_metrics(sc, sa))
            if sc['spell_f1_mean'] < sa['spell_f1_mean'] - .01 - 1e-12:
                failures.append(scenario + ':spell')
        reasons[name] = failures
        if not failures:
            passed.append(name)
    def rank(name):
        m = metrics[name]['clean']['overall']
        distance = 99 if name == 'C' else abs(float(name.split('_a')[1].split('_b')[0])-1) + abs(float(name.split('_b')[1])-1)
        return (-m['spell_f1_mean'], -m['macro_f1'], name == 'C', distance, name)
    return dict(selected=min(passed, key=rank) if passed else 'A', violations=reasons,
                independent_generalization=False, historical_assessment_used=False)


def verify_inputs():
    """Verify named external artifacts and immutable bundle before model loading.

    Hash bytes in explicit local paths only; historical absolute paths are
    provenance strings, never fallback paths. Reject unexpected IDs/contracts.
    """
    bundle = REPO/'external_artifacts/inference-bundle-v1'
    descriptor = verify_bundle(bundle, check_runtime=True)
    lineage = json.loads((bundle/'provenance/expanded_manifest.json').read_text())['inputs_sha256']
    matches, hashes = [], {}
    for identity, prepared in (('J03WOH', 'J03WOH-run2'),
                               ('J03WPY', 'J03WPY-prepared-v1'),
                               ('J03WQQ', 'J03WQQ-prepared-v1')):
        feature_dir = 'J03WOH-features-run2' if identity == 'J03WOH' else identity+'-features-v1'
        match = validate_match(REPO/'external_artifacts'/prepared,
                               REPO/'external_artifacts'/feature_dir)
        if match['match_id'] != 'DFL-MAT-'+identity:
            raise ValueError('external match ID differs from protocol')
        pm = json.loads((match['targets'].parent/'manifest.json').read_text())
        if '28196177' not in json.dumps(pm.get('provenance', {})):
            raise ValueError('external DFL provenance required')
        # Prepared manifests use observation/target-specific hash keys.
        for field, filename in (('observations', 'observations.sqlite'), ('targets', 'targets.sqlite')):
            suffix = '/'+prepared+'/'+filename
            digests = {h for p, h in lineage.items() if p.replace('\\', '/').endswith(suffix)}
            if len(digests) != 1:
                raise ValueError('missing prepared checksum: '+filename)
            expected = digests.pop()
            if sha256(match[field]) != expected:
                raise ValueError('prepared checksum mismatch: '+filename)
        hashes.update({str(p): sha256(p) for p in match['paths']})
        matches.append(match)
    validate_partitions(matches[:2], matches[2])
    hashes[str(bundle/'bundle_manifest.json')] = sha256(bundle/'bundle_manifest.json')
    return matches, hashes, bundle, descriptor


def score(keys, stamps, y, valid, labels):
    """Official metric definitions on original external timeline, plus run diagnosis."""
    result = evaluate_timeline(keys, stamps, y, valid, labels)
    runs = contiguous_runs(keys, stamps, valid)
    result['label_runs'] = label_run_summary(labels, runs)
    return result


def run(output):
    """Execute fixed A/B/C protocol in a new output directory; never overwrite.

    Per-half replay arrays are (N,20), projected to (N,18) for C. Probabilities
    are (N,3) in H/A/D order. Targets enter fitting only on training matches,
    and scoring only after predictions. Removed frames break context/decoding.
    C diagnosis gate: any decoded error on valid ball-incomplete validation
    frames in a predeclared clean/drop/partial scenario. No feature search.
    """
    import numpy as np
    import joblib
    output = Path(output).resolve()
    output.relative_to(REPO/'external_artifacts/v2')
    if output.exists():
        raise FileExistsError(output)
    matches, hashes, bundle, descriptor = verify_inputs()
    model, baseline = load_bundle(bundle)
    parameters = decoder_grid(baseline)
    output.mkdir(parents=True)
    sources = {str(p.relative_to(REPO)): sha256(p) for p in (REPO/'external_baseline').glob('*.py')}
    sources['evaluation/possession_metrics.py'] = sha256(REPO/'evaluation/possession_metrics.py')
    protocol = dict(version=2, training=[m['match_id'] for m in matches[:2]],
        validation=matches[2]['match_id'], independent_test=None,
        consumed_assessment=['J03WOY', 'J03WR9'], grid=parameters,
        features_C=MODEL_NAMES, training_seed=2028, evaluation_seed=2027,
        scenarios=SCENARIOS, minimum_spell_gain=.01, maximum_regression=.01,
        c_gate='any valid ball-incomplete error on clean/ball-drop/ball-partial validation',
        fitting='one C only; unchanged HGB/augmentation; no combined B+C',
        source_sha256=sources, inputs_sha256=hashes, runtime=descriptor['packages'],
        python=platform.python_version(), baseline_model_sha256=descriptor['model_sha256'])
    write_json(output/'protocol.json', protocol)
    try:
        metrics = {name: {} for name in parameters}
        diagnosis = {'ball_incomplete_valid': 0, 'ball_incomplete_errors': 0,
                     'raw_to_decoded': {}, 'short_segments': {}}
        validation = matches[2]
        # First create paired baseline predictions and all decoder outputs.
        for period in (1, 2):
            print(f'Validation A/B replay half {period}', flush=True)
            keys, stamps, matrices, retained, _ = stress_feature_matrices(validation['observations'], period, 2027, context=True)
            original_keys, original_stamps, original_x = feature_half(validation, period)
            if keys != original_keys or stamps != original_stamps or not np.array_equal(matrices['clean'][:, :16], original_x, equal_nan=True):
                raise ValueError('baseline observation replay differs from cached features')
            for scenario in SCENARIOS:
                name = scenario['name']; use = retained[name]
                k = [v for v, keep in zip(keys, use) if keep]
                t = [v for v, keep in zip(stamps, use) if keep]
                x = matrices[name][use]
                raw, probs = predict_raw(model, project_features(x[:, :16], 'no-signed-position'))
                decoded = {n: decode_probabilities(k, t, probs, p) for n, p in parameters.items()}
                np.savez_compressed(output/f'half{period}-{name}.npz', source_frame=[v.source_frame for v in k],
                    timestamp_us=t, X=x, probabilities_A=probs, raw_A=raw, **decoded)
            del matrices
            gc.collect()
        # Targets loaded only after all A/B predictions have been persisted.
        truths = {p: load_split(validation['features'], validation['targets'], p) for p in (1, 2)}
        def evaluate_saved(candidate):
            for scenario in SCENARIOS:
                scenario_name = scenario['name']; all_k, all_t, all_y, all_v, all_l = [], [], [], [], []
                halves = {}
                for period in (1, 2):
                    with np.load(output/f'half{period}-{scenario_name}.npz') as data:
                        keys, stamps, _, y, valid = truths[period]
                        lookup = {k.source_frame: i for i, k in enumerate(keys)}
                        indices = [lookup[int(f)] for f in data['source_frame']]
                        k = [keys[i] for i in indices]; t = [stamps[i] for i in indices]
                        if t != data['timestamp_us'].tolist():
                            raise ValueError('prediction target timestamp mismatch')
                        yy, vv = y[indices], valid[indices]
                        labels = data[candidate]
                        halves[f'half_{period}'] = score(k, t, yy, vv, labels)
                        all_k.extend(k); all_t.extend(t); all_y.extend(yy); all_v.extend(vv); all_l.extend(labels)
                        if candidate == 'A':
                            if scenario['kind'] in ('identity', 'ball_drop', 'ball_burst', 'ball_partial'):
                                missing = vv & (data['X'][:, 3] == 0)
                                diagnosis['ball_incomplete_valid'] += int(missing.sum())
                                diagnosis['ball_incomplete_errors'] += int((missing & (labels != yy)).sum())
                            if scenario_name == 'clean':
                                for raw_label, decoded_label in zip(data['raw_A'], labels):
                                    pair = str(raw_label)+'->'+str(decoded_label)
                                    diagnosis['raw_to_decoded'][pair] = diagnosis['raw_to_decoded'].get(pair, 0)+1
                                for label in ('H', 'A', 'D'):
                                    for start, stop in contiguous_runs(k, t, vv):
                                        edges = [start]+[i for i in range(start+1, stop) if yy[i] != yy[i-1]]+[stop]
                                        for a, b in zip(edges, edges[1:]):
                                            if yy[a] != label: continue
                                            bucket = '<=1s' if b-a <= 25 else '1-3s' if b-a <= 75 else '>3s'
                                            key = label+':'+bucket
                                            record = diagnosis['short_segments'].setdefault(key, dict(segments=0, frames=0, correct_frames=0))
                                            record['segments'] += 1; record['frames'] += b-a
                                            record['correct_frames'] += int((labels[a:b] == label).sum())
                halves['overall'] = score(all_k, all_t, all_y, all_v, all_l)
                metrics[candidate][scenario_name] = halves
        for candidate in parameters:
            evaluate_saved(candidate)
        write_json(output/'diagnosis.json', diagnosis)
        if diagnosis['ball_incomplete_errors']:
            print('C diagnosis gate passed; building one 18-feature training pool', flush=True)
            xp, yp = output/'training-X.bin', output/'training-y.bin'
            audit = []
            with xp.open('wb') as xf, yp.open('wb') as yf:
                for match in matches[:2]:
                    for period in (1, 2):
                        keys, stamps, _, y, valid = load_split(match['features'], match['targets'], period)
                        rkeys, rstamps, matrices, retained, counts = stress_feature_matrices(match['observations'], period, 2028, context=True)
                        if keys != rkeys or stamps != rstamps:
                            raise ValueError('training observation/target alignment')
                        for scenario in SCENARIOS:
                            name = scenario['name']; use = retained[name] & valid
                            matrices[name][use][:, PROJECT].astype(np.float64).tofile(xf)
                            np.asarray(y[use], dtype='U1').tofile(yf)
                            audit.append(dict(match=match['match_id'], half=period, scenario=name, samples=int(use.sum())))
                        del matrices
                        gc.collect()
            c_model, n = fit_pool(xp, yp, n_features=18)
            joblib.dump(dict(model=c_model, feature_names=MODEL_NAMES, config=protocol), output/'model_C.joblib', compress=3)
            restored = joblib.load(output/'model_C.joblib')['model']
            metrics['C'] = {}; parameters['C'] = baseline
            write_json(output/'training_audit.json', dict(samples=n, views=audit))
            for period in (1, 2):
                for scenario in SCENARIOS:
                    path = output/f"half{period}-{scenario['name']}.npz"
                    with np.load(path) as saved:
                        data = {name: saved[name] for name in saved.files}
                    from .contracts import FrameKey
                    k = [FrameKey(validation['match_id'], period, int(f)) for f in data['source_frame']]
                    raw, probs = predict_raw(c_model, data['X'][:, PROJECT])
                    _, reload_probs = predict_raw(restored, data['X'][:, PROJECT])
                    if not np.array_equal(probs, reload_probs):
                        raise ValueError('C serialization changed probabilities')
                    data.update(raw_C=raw, probabilities_C=probs,
                        C=decode_probabilities(k, data['timestamp_us'], probs, baseline))
                    np.savez_compressed(path, **data)
            evaluate_saved('C')
        else:
            write_json(output/'C_skipped.json', dict(reason='no ball-incomplete validation error in predeclared diagnosis'))
        selection = select(metrics)
        write_json(output/'metrics.json', metrics)
        write_json(output/'selection.json', selection)
        write_json(output/'selected_decoder.json', parameters[selection['selected']])
        if any(sha256(Path(p)) != h for p, h in hashes.items()) or any(sha256(REPO/p) != h for p, h in sources.items()):
            raise ValueError('inputs/source changed during experiment')
        verify_bundle(bundle, check_runtime=True)
        write_json(output/'manifest.json', dict(status='ready', v2_version=2,
            inputs_sha256=hashes, source_sha256=sources, selection=selection,
            outputs_sha256={p.name: sha256(p) for p in output.iterdir() if p.is_file()}))
        print(json.dumps(selection, indent=2), flush=True)
        return selection
    except Exception as error:
        write_json(output/'FAILED.json', dict(status='failed', error=str(error)))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    run(args.output)


if __name__ == '__main__':
    main()
