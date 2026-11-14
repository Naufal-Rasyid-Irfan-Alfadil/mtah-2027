"""One fixed external-only HGB baseline. Import/help never fit or read datasets."""

import argparse
from collections import Counter
from contextlib import closing
import importlib.metadata
from itertools import zip_longest
import json
from pathlib import Path
import platform
import sqlite3
import time

from .contracts import CONTRACT_VERSION, FrameKey, SPLITS, STEP_US
from .features import FEATURE_NAMES, FEATURE_UNITS, FEATURE_VERSION
from .prepare import REPO, git_metadata, peak_memory_bytes, sha256

LABELS = ("H", "A", "D")
# sklearn 1.7.2 defaults, except the documented reproducibility/leakage controls.
# Fixed before looking at validation scores; no CLI sweep or selected threshold.
HGB_PARAMS = dict(loss="log_loss", learning_rate=0.1, max_iter=100,
                  max_leaf_nodes=31, max_depth=None, min_samples_leaf=20,
                  l2_regularization=0.0, max_features=1.0, max_bins=255,
                  categorical_features=None, monotonic_cst=None, interaction_cst=None,
                  warm_start=False, early_stopping=False, scoring="loss",
                  validation_fraction=None, n_iter_no_change=10, tol=1e-7,
                  verbose=0, random_state=0, class_weight=None)
PACKAGES = ("numpy", "pandas", "scikit-learn", "scipy", "joblib", "threadpoolctl")
FEATURE_SETS = {
    "all16": FEATURE_NAMES,
    "no-signed-position": tuple(n for n in FEATURE_NAMES if n not in ("ball_x_m", "ball_y_m")),
}


def project_features(x, feature_set="all16"):
    """Project raw v1 features to the fixed model allowlist, without fitting.

    Input must have the original 16 columns in FEATURE_NAMES order. Outputs
    preserve rows, NaNs, metre/m/s units and time boundaries. The single ablation
    drops signed ball x/y; it does not replace them, relabel teams or flip axes.
    """
    if feature_set not in FEATURE_SETS:
        raise ValueError("unsupported feature set")
    if x.ndim != 2 or x.shape[1] != len(FEATURE_NAMES):
        raise ValueError("expected original 16-feature matrix")
    return x[:, [FEATURE_NAMES.index(n) for n in FEATURE_SETS[feature_set]]]


def _validate_reference(reference, features, targets):
    """Verify an unchanged, matching original raw baseline; do not read its scores."""
    reference = Path(reference).resolve(strict=True)
    manifest_path = reference/"manifest.json"
    manifest = read_ready_manifest(manifest_path)
    config = manifest["config"]
    expected = dict(hgb_params=HGB_PARAMS, threads=1, training_period=1,
                    validation_period=2, decoder=None, preprocessing=None)
    if config.get("feature_names") != list(FEATURE_NAMES) or any(config.get(k) != v for k,v in expected.items()):
        raise ValueError("reference must be the matching fixed 16-feature raw baseline")
    if manifest.get("python") != platform.python_version() or manifest.get("packages") != {p:importlib.metadata.version(p) for p in PACKAGES}:
        raise ValueError("reference runtime/dependency versions differ")
    for path in (features,targets,features.parent/"manifest.json",targets.parent/"manifest.json"):
        if manifest["inputs_sha256"].get(str(path)) != sha256(path):
            raise ValueError("reference inputs differ from ablation inputs")
    for name,digest in manifest["outputs_sha256"].items():
        if name not in ("model.joblib","predictions.sqlite","config.json") or sha256(reference/name) != digest:
            raise ValueError("reference output hash mismatch")
    if "predictions.sqlite" not in manifest["outputs_sha256"]:
        raise ValueError("reference predictions hash missing")
    return reference


def _reference_labels(reference, data, period):
    """Read raw reference labels with exact key/time/split alignment, never positional joins."""
    import numpy as np
    keys,stamps = data[:2]
    path = (reference/"predictions.sqlite").resolve()
    with closing(sqlite3.connect(path.as_uri()+"?mode=ro",uri=True)) as db:
        rows = db.execute("SELECT match_id,period,source_frame,timestamp_us,split,label FROM predictions WHERE period=? ORDER BY match_id,period,source_frame",(period,)).fetchall()
    if len(rows) != len(keys) or any(row[:5] != (k.match_id,k.period,k.source_frame,t,SPLITS[period]) for row,k,t in zip(rows,keys,stamps)):
        raise ValueError("reference prediction timeline mismatch")
    if any(row[5] not in LABELS for row in rows):
        raise ValueError("invalid reference label")
    return np.asarray([row[5] for row in rows])


def comparison_entry(data, predictions, metrics):
    """Compact geometric/temporal diagnosis on the unchanged full observation timeline."""
    import numpy as np
    keys,stamps,x,y,valid = data
    alive = valid & np.isin(y,["H","A"])
    swaps = alive & np.isin(predictions,["H","A"]) & (predictions != y)
    switches = 0
    for i in range(1,len(keys)):
        k,old = keys[i],keys[i-1]
        if (valid[i] and valid[i-1] and y[i] == y[i-1] and y[i] in ("H","A")
            and predictions[i] in ("H","A") and predictions[i-1] in ("H","A")
            and predictions[i] != predictions[i-1]
            and (k.match_id,k.period,k.source_frame-1,stamps[i]-STEP_US)
                == (old.match_id,old.period,old.source_frame,stamps[i-1])):
            switches += 1
    return dict(spell_f1_mean=metrics["spell_f1_mean"], macro_f1=metrics["macro_f1"],
                per_class_f1={k:v["f1"] for k,v in metrics["per_class"].items()},
                transition_f1={k:v["f1"] for k,v in metrics["transitions"].items()},
                n_pred_spells=metrics["n_pred_spells"], n_gt_spells=metrics["n_gt_spells"],
                HA_swaps=int(swaps.sum()), alive_frames=int(alive.sum()),
                alive_to_D=int((alive & (predictions=="D")).sum()),
                D_to_alive=int((valid & (y=="D") & (predictions!="D")).sum()),
                HA_switches_inside_true_possession=switches)


def read_ready_manifest(path):
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if value.get("status") != "ready" or value.get("contract_version") != CONTRACT_VERSION:
        raise ValueError("ready v1 manifest required")
    return value


def load_split(features, targets, period):
    """Return ordered (keys, timestamps, float64 X, labels, valid mask).

    Explicit read-only DB inputs are joined on match/period/source_frame, never
    array position. SQL NULL features become NaN, not zero. Full frame timeline
    is retained even for invalid targets. No fitting, filling or filtering here.
    Both DBs must have exactly matching keys; inconsistent validity fails.
    """
    import numpy as np

    with closing(sqlite3.connect(Path(features).resolve().as_uri()+"?mode=ro", uri=True)) as fdb, closing(sqlite3.connect(Path(targets).resolve().as_uri()+"?mode=ro", uri=True)) as tdb:
        for db in (fdb, tdb):
            db.execute("PRAGMA query_only=ON")
        meta = fdb.execute("SELECT json FROM feature_metadata").fetchall()
        if len(meta) != 1:
            raise ValueError("one feature metadata row required")
        meta = json.loads(meta[0][0])
        if meta.get("feature_version") != FEATURE_VERSION or meta.get("feature_names") != list(FEATURE_NAMES) or meta.get("units") != FEATURE_UNITS:
            raise ValueError("feature version/allowlist/units mismatch")
        cols = ",".join(FEATURE_NAMES)
        frows = fdb.execute(f"SELECT match_id,period,source_frame,timestamp_us,split,{cols} FROM features WHERE period=? ORDER BY match_id,period,source_frame", (period,))
        trows = tdb.execute("SELECT match_id,period,source_frame,label,valid_target FROM targets WHERE period=? ORDER BY match_id,period,source_frame", (period,))
        keys, stamps, values, labels, mask = [], [], [], [], []
        for f, t in zip_longest(frows, trows):
            if f is None or t is None or f[:3] != t[:3]:
                raise ValueError("feature/target keys do not match exactly")
            if f[4] != SPLITS[period]:
                raise ValueError("feature split disagrees with half")
            label, valid = t[3:]
            if valid not in (0, 1) or (valid == 1 and label not in LABELS) or (valid == 0 and label is not None):
                raise ValueError("inconsistent target label/valid mask")
            keys.append(FrameKey(*f[:3]))
            stamps.append(f[3])
            values.append(f[5:])
            labels.append(label)
            mask.append(bool(valid))
        if not keys:
            raise ValueError("empty required half")
        x = np.asarray(values, dtype=np.float64)
        if x.shape != (len(keys), len(FEATURE_NAMES)) or np.isinf(x).any():
            raise ValueError("invalid numeric features")
        return keys, stamps, x, np.asarray(labels, dtype=object), np.asarray(mask, dtype=bool)


def fit_baseline(x, labels, valid):
    """Fit exactly one HGB on supplied training rows only; keep NaNs native.

    Caller supplies half 1 only. Validity filtering applies solely to fitting,
    never to evaluation timeline. No validation arrays, weighting or calibration
    are accepted. Returns estimator with fixed params, seed and one thread.
    """
    from sklearn.ensemble import HistGradientBoostingClassifier
    from threadpoolctl import threadpool_limits

    if set(labels[valid]) != set(LABELS):
        raise ValueError("training must contain valid H, A and D targets")
    model = HistGradientBoostingClassifier(**HGB_PARAMS)
    with threadpool_limits(limits=1):
        model.fit(x[valid], labels[valid])
    return model


def predict_raw(model, x):
    """Return hard argmax labels and probabilities in H/A/D order, without decoding."""
    import numpy as np
    from threadpoolctl import threadpool_limits

    with threadpool_limits(limits=1):
        native = model.predict_proba(x)
    indices = [list(model.classes_).index(label) for label in LABELS]
    probs = native[:, indices]
    if not np.isfinite(probs).all() or not np.allclose(probs.sum(axis=1), 1):
        raise ValueError("invalid predicted probabilities")
    # Match estimator tie-breaking in its own class order, not reordered columns.
    labels = model.classes_[np.argmax(native, axis=1)]
    return labels, probs


def evaluate_timeline(keys, stamps, labels, valid, predictions, allow_abstain=False):
    """Score raw predictions on an external 25 Hz timeline, preserving missing time.

    Missing source-frame numbers are explicit X positions in the evaluation
    lattice. Invalid targets are X at their original positions. Period/match or
    timestamp discontinuities split runs. Temporal transition matching is done
    independently inside each valid contiguous run, then counts are pooled.
    Optional explicit X abstentions remain frame-level misses on valid targets;
    temporal metrics use the repository's within-GT-run abstention filling rule.
    This affects scoring only, never inference. F1 is not accuracy. No official
    GT or CSV loader is called. Default raw H/A/D validation is unchanged.
    """
    import numpy as np
    from evaluation import possession_metrics as pm

    if not (len(keys) == len(stamps) == len(labels) == len(valid) == len(predictions)):
        raise ValueError("timeline length mismatch")
    if not any(valid):
        raise ValueError("no valid evaluation targets")
    gt, pred, previous = [], [], None
    lookup = {label: i for i, label in enumerate(pm.LABELS)}
    for key, stamp, label, is_valid, prediction in zip(keys, stamps, labels, valid, predictions):
        if prediction not in (pm.LABELS if allow_abstain else LABELS) or (is_valid and label not in LABELS):
            raise ValueError("unsupported label")
        if previous is not None:
            old, old_stamp = previous
            if (key.match_id, key.period) == (old.match_id, old.period):
                delta = key.source_frame - old.source_frame
                if delta <= 0:
                    raise ValueError("evaluation frames must increase")
                padding = delta - 1
                if stamp - old_stamp != delta * STEP_US:
                    padding = max(1, padding)
            else:
                padding = 1
            gt.extend([pm.X]*padding)
            pred.extend([pm.X]*padding)
        gt.append(lookup[label] if is_valid else pm.X)
        pred.append(lookup[prediction])
        previous = (key, stamp)
    gt, pred = np.asarray(gt, dtype=np.int8), np.asarray(pred, dtype=np.int8)
    result = pm.evaluate(gt, pred, taus=(), bootstrap_n=0)
    runs = pm.valid_runs(gt)
    temporal_pred = pm.fill_abstentions(pred,runs)
    for tol in pm.TAUS:
        tp = fp = fn = ambiguous = 0
        latencies = []
        for run in runs:
            g, p = pm.transitions(gt, [run]), pm.transitions(temporal_pred, [run])
            score = pm.transition_scores(g, p, tol)
            tp += score["n_matched"]
            fp += score["n_spurious"]
            fn += score["n_missed"]
            ambiguous += score["n_ambiguous"]
            latencies.extend(p[0]-g[0] for g, p in score["pairs"])
        precision = tp/(tp+fp) if tp+fp else 0.0
        recall = tp/(tp+fn) if tp+fn else 0.0
        result["transitions"][tol] = dict(
            precision=precision, recall=recall, f1=2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.0,
            n_gt=tp+fn, n_pred=tp+fp, n_matched=tp, n_spurious=fp, n_missed=fn,
            n_ambiguous=ambiguous, mean_latency_frames=float(np.mean(latencies)) if latencies else None,
            mean_abs_latency_frames=float(np.mean(np.abs(latencies))) if latencies else None)
    result.update(observed_frames=len(keys), evaluation_lattice_frames=len(gt), valid_contiguous_runs=len(runs))
    return result


def train(features, targets, output, feature_set="all16", reference=None):
    """Train once on half 1 and evaluate raw half-2 predictions on external data.

    Both artifact paths must be explicit and ready. Their preparation lineage
    must agree. Writes model, keyed predictions, config, metrics and provenance
    in a new directory. Validation targets are loaded only after fit/predict.
    Default all16 preserves the original baseline. The sole ablation drops signed
    x/y and requires an explicit original reference. Model allowlist is saved
    with the estimator; the feature SQLite contract remains all 16 observations.
    No official assets, GT, sweep, decoder or full-match refit is performed.
    """
    import joblib
    import numpy as np

    features, targets = Path(features).resolve(strict=True), Path(targets).resolve(strict=True)
    if features.name != "features.sqlite" or targets.name != "targets.sqlite":
        raise ValueError("explicit features.sqlite and targets.sqlite paths required")
    fmanifest_path, tmanifest_path = features.parent/"manifest.json", targets.parent/"manifest.json"
    fm, tm = read_ready_manifest(fmanifest_path), read_ready_manifest(tmanifest_path)
    if fm.get("feature_version") != FEATURE_VERSION or fm.get("feature_names") != list(FEATURE_NAMES):
        raise ValueError("unsupported feature manifest")
    if fm["input"]["parent_manifest_sha256"] != sha256(tmanifest_path):
        raise ValueError("feature/target preparation lineage mismatch")
    if fm["output_sha256"] != sha256(features):
        raise ValueError("feature hash mismatch")
    if feature_set not in FEATURE_SETS:
        raise ValueError("unsupported feature set")
    if (feature_set == "all16") != (reference is None):
        raise ValueError("ablation requires --reference; all16 does not use a reference")
    reference = _validate_reference(reference,features,targets) if reference is not None else None
    model_features = FEATURE_SETS[feature_set]
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    try:
        paths = (features, targets, fmanifest_path, tmanifest_path)
        if reference is not None:
            paths += (reference/"manifest.json",reference/"predictions.sqlite",reference/"config.json",reference/"model.joblib")
        input_hashes = {str(p): sha256(p) for p in paths}
        source_hashes = {str(p.relative_to(REPO)): sha256(p) for p in sorted((REPO/"external_baseline").glob("*.py"))}
        source_hashes["evaluation/possession_metrics.py"] = sha256(REPO/"evaluation/possession_metrics.py")
        config = {"feature_names": model_features, "source_feature_names": FEATURE_NAMES,
                  "feature_set": feature_set, "feature_version": FEATURE_VERSION,
                  "hgb_params": HGB_PARAMS, "threads": 1, "training_period": 1,
                  "validation_period": 2, "decoder": None, "preprocessing": None,
                  "selection": ("one fixed configuration, no tuning or candidate selection" if reference is None else
                                "one predeclared 14-feature ablation motivated by external inter-half diagnostics; no sweep or automatic model promotion")}
        (output/"config.json").write_text(json.dumps(config, indent=2)+"\n", encoding="utf-8")
        train_data = load_split(features, targets, 1)
        model = fit_baseline(project_features(train_data[2],feature_set),*train_data[3:])
        joblib.dump({"model": model, "feature_names": model_features, "config": config}, output/"model.joblib", compress=3)
        # Validation observations only: do not open validation target rows until predictions exist.
        with closing(sqlite3.connect(features.as_uri()+"?mode=ro", uri=True)) as db:
            rows = db.execute(f"SELECT {','.join(FEATURE_NAMES)} FROM features WHERE period=2 ORDER BY match_id,period,source_frame").fetchall()
        val_x = np.asarray(rows, dtype=np.float64)
        if not rows:
            raise ValueError("empty validation half")
        val_predictions, val_probs = predict_raw(model, project_features(val_x,feature_set))
        val_data = load_split(features, targets, 2)
        if not np.array_equal(val_data[2], val_x, equal_nan=True):
            raise ValueError("validation features changed during prediction")
        tr_predictions, tr_probs = predict_raw(model, project_features(train_data[2],feature_set))
        reports = {}
        comparison = {"reference":str(reference), "variant":feature_set, "splits":{},
                      "interpretation":"External development comparison on reused inter-half validation; not inter-match test or proof of causation. No automatic model promotion."}
        with closing(sqlite3.connect(output/"predictions.sqlite")) as db:
            db.execute("""CREATE TABLE predictions(match_id TEXT,period INTEGER,source_frame INTEGER,
                timestamp_us INTEGER,split TEXT,label TEXT,p_H REAL,p_A REAL,p_D REAL,
                PRIMARY KEY(match_id,period,source_frame)) WITHOUT ROWID""")
            for split, data, predictions, probs in (("train", train_data, tr_predictions, tr_probs), ("validation", val_data, val_predictions, val_probs)):
                keys, stamps, x, y, valid = data
                db.executemany("INSERT INTO predictions VALUES (?,?,?,?,?,?,?,?,?)",
                    ((k.match_id,k.period,k.source_frame,int(stamp),split,str(label),*map(float,p))
                     for k,stamp,label,p in zip(keys,stamps,predictions,probs)))
                reports[split] = {"metrics": evaluate_timeline(keys, stamps, y, valid, predictions),
                                  "target_valid": int(valid.sum()), "target_invalid": int((~valid).sum()),
                                  "target_class_counts": dict(Counter(y[valid])),
                                  "prediction_counts": dict(Counter(predictions))}
                if reference is not None:
                    reference_predictions = _reference_labels(reference,data,keys[0].period)
                    reference_metrics = evaluate_timeline(keys,stamps,y,valid,reference_predictions)
                    old = comparison_entry(data,reference_predictions,reference_metrics)
                    new = comparison_entry(data,predictions,reports[split]["metrics"])
                    comparison["splits"][split] = {"baseline16":old,"ablation14":new,
                        "delta_ablation_minus_baseline":{k:new[k]-old[k] for k in
                            ("spell_f1_mean","macro_f1","n_pred_spells","HA_swaps","HA_switches_inside_true_possession")}}
            db.commit()
        if reference is not None:
            (output/"comparison.json").write_text(json.dumps(comparison,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        if any(sha256(Path(path)) != digest for path,digest in input_hashes.items()):
            raise ValueError("input changed during training")
        if any(sha256(REPO/path) != digest for path,digest in source_hashes.items()):
            raise ValueError("source changed during training")
        report = {"splits": reports, "elapsed_seconds": round(time.perf_counter()-started,3),
                  "process_peak_resident_bytes": peak_memory_bytes(), "iterations": int(model.n_iter_),
                  "early_stopping_used": bool(model.do_early_stopping_),
                  "interpretation": "Inter-half development validation on one external match; not inter-match test. F1 is not accuracy."}
        manifest = {"status": "ready", "contract_version": CONTRACT_VERSION,
                    "training_version": 1, "inputs_sha256": input_hashes, "source_sha256": source_hashes,
                    "git": git_metadata(), "python": platform.python_version(),
                    "packages": {p: importlib.metadata.version(p) for p in PACKAGES}, "config": config,
                    "outputs_sha256": {p: sha256(output/p) for p in (("model.joblib","predictions.sqlite","config.json","comparison.json") if reference is not None else ("model.joblib","predictions.sqlite","config.json"))},
                    "provenance": {"feature_attribution": fm.get("provenance",{}),
                                   "target_attribution": tm.get("provenance",{}),
                                   "parameters": "sklearn 1.7.2 defaults except early_stopping=False, validation_fraction=None, categorical_features=None and random_state=0; fixed before validation, no old project parameters copied.",
                                   "feature_experiment": config["selection"],
                                   "official_data": "No official data or GT read; no official candidate/threshold selection."}}
        for name,value in (("metrics.json",report),("manifest.json",manifest)):
            (output/name).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        return report
    except Exception as error:
        (output/"FAILED.json").write_text(json.dumps({"status":"failed","error":str(error)})+"\n",encoding="utf-8")
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--features",required=True,type=Path)
    parser.add_argument("--targets",required=True,type=Path)
    parser.add_argument("--output",required=True,type=Path)
    parser.add_argument("--feature-set",choices=tuple(FEATURE_SETS),default="all16")
    parser.add_argument("--reference",type=Path,help="original all16 baseline directory; required for the sole ablation")
    args = parser.parse_args()
    report = train(args.features,args.targets,args.output,args.feature_set,args.reference)
    print(json.dumps({split:{name:entry["metrics"][name] for name in ("spell_f1_mean","macro_f1","n_gt_spells","n_pred_spells")} for split,entry in report["splits"].items()},indent=2))


if __name__ == "__main__":
    main()
