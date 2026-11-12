"""One fixed whole-match development experiment; import/help perform no data I/O."""

import argparse
from collections import Counter
from contextlib import closing
import gc
import importlib.metadata
import json
from pathlib import Path
import platform
import sqlite3
import time

from .contracts import FrameKey
from .features import FEATURE_NAMES, FEATURE_UNITS
from .prepare import REPO, sha256, git_metadata, peak_memory_bytes
from .robustness import SCENARIOS, stress_feature_matrices
from .augmented import TRAIN_SEED
from .temporal import decode_probabilities
from .diagnostics import contiguous_runs
from .training import (FEATURE_SETS, HGB_PARAMS, PACKAGES, LABELS, load_split,
                       project_features, predict_raw, evaluate_timeline, read_ready_manifest)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False)+'\n', encoding='utf-8')


def read_only(path):
    db = sqlite3.connect(path.resolve().as_uri()+'?mode=ro', uri=True)
    db.execute('PRAGMA query_only=ON')
    db.execute('PRAGMA cache_size=-8192')
    db.execute('PRAGMA temp_store=FILE')
    return db


def validate_match(prepared, features):
    """Validate explicit external v1 artifacts; return ID, paths and attribution.

    Both halves must exist, in centred metres at 25 Hz. Paths are current-local;
    historical Windows input names are preserved rather than used to open files.
    Target rows join exactly later, never by index or inferred timestamps.
    """
    prepared, features = Path(prepared).resolve(strict=True), Path(features).resolve(strict=True)
    pm_path, fm_path = prepared/'manifest.json', features/'manifest.json'
    pm, fm = read_ready_manifest(pm_path), read_ready_manifest(fm_path)
    obs, target, feature = prepared/'observations.sqlite', prepared/'targets.sqlite', features/'features.sqlite'
    if (fm.get('feature_names') != list(FEATURE_NAMES) or fm.get('units') != FEATURE_UNITS
            or fm.get('feature_version') != 1
            or fm['input']['parent_manifest_sha256'] != sha256(pm_path)
            or fm['input']['sha256'] != sha256(obs) or fm['output_sha256'] != sha256(feature)):
        raise ValueError('feature/preparation lineage, hash or units mismatch')
    if (pm['config']['fps'], pm['config']['coordinate_unit'], pm['config']['origin']) != (25, 'm', 'pitch_center'):
        raise ValueError('unsupported preparation units/time convention')
    match = pm['match']['match_id']
    with closing(read_only(feature)) as db:
        roles = db.execute('SELECT DISTINCT match_id,period FROM features ORDER BY match_id,period').fetchall()
        meta = db.execute('SELECT json FROM feature_metadata').fetchall()
    if roles != [(match, 1), (match, 2)] or len(meta) != 1:
        raise ValueError('one declared match and both halves required')
    meta = json.loads(meta[0][0])
    if meta.get('feature_names') != list(FEATURE_NAMES) or meta.get('units') != FEATURE_UNITS:
        raise ValueError('feature metadata mismatch')
    return dict(match_id=match, observations=obs, targets=target, features=feature,
                paths=[pm_path, fm_path, obs, target, feature], attribution=pm.get('provenance', {}))


def validate_partitions(training, validation):
    ids = [m['match_id'] for m in training]
    if not ids or ids != sorted(set(ids)) or validation['match_id'] in ids:
        raise ValueError('training matches must be unique/sorted and disjoint from validation')
    if any(m['features'] == validation['features'] or m['targets'] == validation['targets'] for m in training):
        raise ValueError('training/validation paths overlap')


def training_counts(keys, stamps, labels, valid):
    """Count clean H/A/D training occupancy and adjacent transitions in one half.

    Same continuity rule as the legacy decoder, allowing either original half.
    Invalid labels, 40-ms gaps, match/half changes break runs; no smoothing yet.
    Caller supplies only declared training matches, never validation targets.
    """
    import numpy as np
    if not keys or not (len(keys) == len(stamps) == len(labels) == len(valid)):
        raise ValueError('nonempty equal-length training timeline required')
    states = np.zeros(3, dtype=np.int64)
    transitions = np.zeros((3,3), dtype=np.int64)
    runs = contiguous_runs(keys, stamps, valid)
    for start, stop in runs:
        for i in range(start, stop):
            current = LABELS.index(labels[i])
            states[current] += 1
            if i > start:
                transitions[LABELS.index(labels[i-1]),current] += 1
    return dict(state_counts=states.tolist(), transition_counts=transitions.tolist(), training_runs=len(runs))


def aggregate_decoder(parts):
    """Pool clean training counts, then apply add-one smoothing exactly once.

    Each part contains one original training half's clean counts, so no
    boundary transition is invented and augmentation duplicates never enter
    occupancy/transition counts. Outputs are H/A/D probabilities at 25 Hz.
    """
    import numpy as np
    if not parts:
        raise ValueError('decoder requires training counts')
    states = sum((np.asarray(p['state_counts'], dtype=np.int64) for p in parts), np.zeros(3, dtype=np.int64))
    transitions = sum((np.asarray(p['transition_counts'], dtype=np.int64) for p in parts), np.zeros((3, 3), dtype=np.int64))
    if not (states > 0).all():
        raise ValueError('decoder requires H/A/D training targets')
    result = dict(decoder_version=1, classes=list(LABELS), fps=25, pseudocount=1.0,
                  emission='log classifier posterior - log training state prior',
                  emission_weight=1.0, transition_weight=1.0)
    prior = (states+1)/(states.sum()+3)
    result.update(state_counts=states.tolist(), transition_counts=transitions.tolist(),
                  state_prior=prior.tolist(), initial_prior=prior.tolist(),
                  transition_matrix=((transitions+1)/(transitions.sum(axis=1, keepdims=True)+3)).tolist(),
                  valid_training_frames=int(states.sum()), observed_transitions=int(transitions.sum()),
                  training_runs=sum(p['training_runs'] for p in parts))
    return result


def append_views(data, replay, x_file, y_file):
    """Append equal-weight valid samples from the seven existing training views.

    X contains the unchanged 14 features in metres/m/s or NaN, y is H/A/D.
    All original frames remain in data/replay for temporal checks; only fitting
    samples are filtered. Each half restarts seed 2028 and its temporal state.
    Binary output order is match, half, scenario, original source-frame order.
    """
    import numpy as np
    keys, stamps, x, y, valid = data
    rkeys, rstamps, matrices, retained, audits = replay
    if keys != rkeys or stamps != rstamps or not np.array_equal(x, matrices['clean'], equal_nan=True):
        raise ValueError('training observation replay differs from feature/target timeline')
    views = {}
    for scenario in SCENARIOS:
        name = scenario['name']
        use = retained[name] & valid
        rows = project_features(matrices[name][use], 'no-signed-position')
        rows.astype(np.float64, copy=False).tofile(x_file)
        np.asarray(y[use], dtype='U1').tofile(y_file)
        views[name] = dict(fitted_rows=int(use.sum()), retained_frames=int(retained[name].sum()),
                           class_counts=dict(Counter(y[use])), perturbation_audit=dict(audits[name]))
    return dict(match_id=keys[0].match_id, period=keys[0].period,
                original_frames=len(keys), valid_frames=int(valid.sum()), views=views)


def fit_pool(x_path, y_path, n_features=14):
    """Fit one fixed single-thread HGB from disk-backed, already-valid samples.

    Avoid another all-valid boolean copy of X. No validation, early stopping,
    weighting, imputation or parameter selection is accepted by this interface.
    n_features is explicitly 14 (v1 default) or 18 (v2 context); X is float64,
    y is U1 H/A/D and missing inputs remain NaN. Caller owns temporal resets.
    """
    import numpy as np
    from sklearn.ensemble import HistGradientBoostingClassifier
    from threadpoolctl import threadpool_limits
    n = y_path.stat().st_size // np.dtype('U1').itemsize
    if n_features not in (14, 18) or not n or x_path.stat().st_size != n*n_features*8:
        raise ValueError('invalid training pool sizes')
    x = np.memmap(x_path, dtype=np.float64, mode='r', shape=(n, n_features))
    y = np.memmap(y_path, dtype='U1', mode='r', shape=(n,))
    if set(np.unique(y)) != set(LABELS):
        raise ValueError('training pool must contain H/A/D')
    model = HistGradientBoostingClassifier(**HGB_PARAMS)
    with threadpool_limits(limits=1):
        model.fit(x, y)
    return model, n


def feature_half(match, period):
    """Read observation-only X16 and frame/time keys, without target masks."""
    import numpy as np
    with closing(read_only(match['features'])) as db:
        n = db.execute('SELECT COUNT(*) FROM features WHERE period=?', (period,)).fetchone()[0]
        x = np.empty((n, len(FEATURE_NAMES)), dtype=float)
        rows = db.execute('SELECT match_id,period,source_frame,timestamp_us,'+','.join(FEATURE_NAMES)+
                          ' FROM features WHERE period=? ORDER BY match_id,period,source_frame', (period,))
        keys, stamps = [], []
        for i, row in enumerate(rows):
            keys.append(FrameKey(*row[:3]))
            stamps.append(row[3])
            x[i] = row[4:]
    if not keys or any(k.match_id != match['match_id'] for k in keys) or np.isinf(x).any():
        raise ValueError('invalid feature timeline')
    return keys, stamps, x


def validate_reference(classifier, decoder):
    """Verify the user's local old augmented baseline before deserialization.

    Require matching library versions, 14 features, HGB parameters, augmentation
    views and seed. Preserve old parameter bytes and all historical manifests.
    """
    classifier, decoder = Path(classifier).resolve(strict=True), Path(decoder).resolve(strict=True)
    cm = read_ready_manifest(classifier/'manifest.json')
    dm = read_ready_manifest(decoder/'manifest.json')
    config = cm['config']
    aug = config.get('training_augmentation', {})
    packages = {p: importlib.metadata.version(p) for p in PACKAGES}
    if (cm['packages'] != packages or config['hgb_params'] != HGB_PARAMS
            or config['feature_names'] != list(FEATURE_SETS['no-signed-position'])
            or aug.get('views') != list(SCENARIOS) or aug.get('training_seed') != TRAIN_SEED):
        raise ValueError('reference config/runtime differs from fixed experiment')
    paths = [classifier/'manifest.json', decoder/'manifest.json']
    for directory, manifest, name in ((classifier, cm, 'model.joblib'), (decoder, dm, 'decoder_parameters.json')):
        path = directory/name
        if manifest['outputs_sha256'][name] != sha256(path):
            raise ValueError('reference artifact hash mismatch')
        paths.append(path)
    return classifier/'model.joblib', decoder/'decoder_parameters.json', paths


def assess_validation(match, candidates, output):
    """Predict/decode both halves for every candidate before opening val targets.

    Save raw H/A/D probabilities and decoded labels at original keys. Evaluation
    keeps invalid targets, gaps and period boundaries; overall F1 is recomputed
    on the combined timeline, not the mean of the half scores.
    """
    import numpy as np
    path = output/'predictions.sqlite'
    with closing(sqlite3.connect(path)) as db:
        db.execute('CREATE TABLE predictions(candidate TEXT,match_id TEXT,period INTEGER,source_frame INTEGER,timestamp_us INTEGER,split TEXT,raw_label TEXT,p_H REAL,p_A REAL,p_D REAL,decoded_label TEXT,PRIMARY KEY(candidate,match_id,period,source_frame)) WITHOUT ROWID')
        for period in (1, 2):
            keys, stamps, x = feature_half(match, period)
            for name, model, parameters in candidates:
                raw, probs = predict_raw(model, project_features(x, 'no-signed-position'))
                decoded = decode_probabilities(keys, stamps, probs, parameters)
                db.executemany('INSERT INTO predictions VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                    ((name,k.match_id,k.period,k.source_frame,int(t),'validation',str(r),*map(float,p),str(d))
                     for k,t,r,p,d in zip(keys, stamps, raw, probs, decoded)))
            db.commit()
        del x
        gc.collect()
        # First validation target access occurs here, after all predictions exist.
        combined = [[], [], [], []]
        halves = {}
        for period in (1, 2):
            keys, stamps, _, y, valid = load_split(match['features'], match['targets'], period)
            combined[0].extend(keys); combined[1].extend(stamps)
            combined[2].extend(y); combined[3].extend(valid)
            halves[period] = (keys, stamps, y, valid)
        result = {}
        for name, _, _ in candidates:
            result[name] = {}
            all_raw, all_decoded = [], []
            for period in (1, 2):
                keys, stamps, y, valid = halves[period]
                rows = db.execute('SELECT match_id,period,source_frame,timestamp_us,raw_label,decoded_label FROM predictions WHERE candidate=? AND period=? ORDER BY match_id,period,source_frame', (name, period)).fetchall()
                if len(rows) != len(keys) or any(r[:4] != (k.match_id,k.period,k.source_frame,t) for r,k,t in zip(rows,keys,stamps)):
                    raise ValueError('validation prediction/target timeline mismatch')
                raw, decoded = [r[4] for r in rows], [r[5] for r in rows]
                all_raw.extend(raw); all_decoded.extend(decoded)
                result[name][f'half_{period}'] = {v:evaluate_timeline(keys, stamps, y, valid, p) for v,p in (('raw',raw),('decoded',decoded))}
            keys, stamps, y, valid = combined
            result[name]['overall'] = {v:evaluate_timeline(keys, stamps, y, valid, p) for v,p in (('raw',all_raw),('decoded',all_decoded))}
        if db.execute('PRAGMA quick_check').fetchall() != [('ok',)]:
            raise ValueError('prediction integrity failure')
    return result


def run(training_pairs, validation_pair, classifier, decoder, output):
    """Freeze one external experiment, fit once, compare on development match.

    Prepared/feature directories are explicit. Both halves of every training
    match fit the HGB and clean decoder counts. No official or reserved test
    inputs are discovered. New output only; failed runs never publish ready.
    """
    import joblib
    output = Path(output).resolve()
    if output.exists():
        raise FileExistsError(output)
    training = [validate_match(*pair) for pair in training_pairs]
    validation = validate_match(*validation_pair)
    validate_partitions(training, validation)
    old_model, old_parameters, reference_paths = validate_reference(classifier, decoder)
    paths = [p for m in [*training,validation] for p in m['paths']] + reference_paths
    inputs = {str(p):sha256(p) for p in paths}
    sources = {str(p.relative_to(REPO)):sha256(p) for p in sorted((REPO/'external_baseline').glob('*.py'))}
    sources['evaluation/possession_metrics.py'] = sha256(REPO/'evaluation/possession_metrics.py')
    output.mkdir(parents=True)
    started = time.perf_counter()
    try:
        protocol = dict(version=1, training=[m['match_id'] for m in training], validation=[validation['match_id']],
            role_applies_to_both_halves=True, feature_names=FEATURE_SETS['no-signed-position'],
            hgb_params=HGB_PARAMS, threads=1, training_seed=TRAIN_SEED, augmentation_views=SCENARIOS,
            rng_policy='independent generator per scenario, restarted with seed 2028 per original half',
            sample_order='sorted match, period, scenario, original frame; equal weight per retained valid view sample',
            decoder='pool clean training state/transition counts; add-one once; same Viterbi rule',
            comparator='unchanged old augmented J03WOH half-1 model and its unchanged decoder',
            interpretation='development comparison, not untouched test; more data includes formerly-validation J03WOH half 2; classifier and decoder both refitted',
            consumed_assessment=['DFL-MAT-J03WOY'], reserved_test=['DFL-MAT-J03WR9'],
            selection='one predeclared run; no sweep, threshold selection or automatic promotion')
        write_json(output/'protocol.json', protocol)
        audits, counts = [], []
        x_path, y_path = output/'training-X.bin', output/'training-y.bin'
        with x_path.open('wb') as xf, y_path.open('wb') as yf:
            for match in training:
                for period in (1, 2):
                    print(f"Training views: {match['match_id']} half {period}", flush=True)
                    data = load_split(match['features'], match['targets'], period)
                    counts.append(training_counts(data[0], data[1], data[3], data[4]))
                    replay = stress_feature_matrices(match['observations'], period=period, seed=TRAIN_SEED)
                    audits.append(append_views(data, replay, xf, yf))
                    del replay, data
                    gc.collect()
        parameters = aggregate_decoder(counts)
        write_json(output/'training_audit.json', audits)
        write_json(output/'decoder_parameters.json', parameters)
        print('Fitting one fixed HGB', flush=True)
        model, n = fit_pool(x_path, y_path)
        joblib.dump(dict(model=model, feature_names=FEATURE_SETS['no-signed-position'], config=protocol), output/'model.joblib', compress=3)
        # Verify the serialized new model's output as well as using the old model.
        restored = joblib.load(output/'model.joblib')
        keys, stamps, x = feature_half(validation, 1)
        import numpy as np
        a, ap = predict_raw(model, project_features(x, 'no-signed-position'))
        b, bp = predict_raw(restored['model'], project_features(x, 'no-signed-position'))
        if not np.array_equal(a,b) or not np.array_equal(ap,bp):
            raise ValueError('serialized model failed exact prediction reproduction')
        del restored, keys, stamps, x, a, ap, b, bp
        gc.collect()
        print('Predicting both validation halves, then loading validation targets', flush=True)
        old = joblib.load(old_model)
        if list(old['feature_names']) != list(FEATURE_SETS['no-signed-position']) or old['model'].get_params() != HGB_PARAMS:
            raise ValueError('serialized reference config differs')
        metrics = assess_validation(validation, [('old_augmented',old['model'],json.loads(old_parameters.read_text())),
                                                  ('expanded',model,parameters)], output)
        write_json(output/'metrics.json', metrics)
        comparison = {variant:{name:{k:metrics[name]['overall'][variant][k] for k in ('spell_f1_mean','macro_f1','n_pred_spells','n_gt_spells','n_graded')} for name in metrics} for variant in ('raw','decoded')}
        comparison['interpretation'] = protocol['interpretation']
        write_json(output/'comparison.json', comparison)
        if any(sha256(Path(p)) != h for p,h in inputs.items()) or any(sha256(REPO/p) != h for p,h in sources.items()):
            raise ValueError('input/source changed during experiment')
        manifest = dict(status='ready', contract_version=1, multimatch_version=1, protocol=protocol,
            inputs_sha256=inputs, source_sha256=sources,
            outputs_sha256={p.name:sha256(p) for p in sorted(output.iterdir()) if p.is_file()},
            python=platform.python_version(), packages={p:importlib.metadata.version(p) for p in PACKAGES},
            git=git_metadata(), fitted_samples=n, model_iterations=int(model.n_iter_),
            early_stopping_used=bool(model.do_early_stopping_), elapsed_seconds=round(time.perf_counter()-started,3),
            process_peak_resident_bytes=peak_memory_bytes(), model_reload_exact=True,
            provenance={m['match_id']:m['attribution'] for m in [*training,validation]})
        write_json(output/'manifest.json', manifest)
        print(json.dumps(comparison, indent=2), flush=True)
        return comparison
    except Exception as error:
        write_json(output/'FAILED.json', dict(status='failed', error=str(error)))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--train', nargs=2, action='append', required=True, metavar=('PREPARED','FEATURES'))
    parser.add_argument('--validation', nargs=2, required=True, metavar=('PREPARED','FEATURES'))
    for name in ('reference-classifier','reference-decoder','output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    run(args.train, args.validation, args.reference_classifier, args.reference_decoder, args.output)


if __name__ == '__main__':
    main()
