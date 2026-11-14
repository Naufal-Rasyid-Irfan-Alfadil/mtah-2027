"""Aggregate external-only raw-baseline diagnosis. No fitting or decoding."""

import argparse
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import time

from .contracts import STEP_US, SPLITS
from .features import FEATURE_NAMES
from .prepare import REPO, sha256, git_metadata, peak_memory_bytes
from .training import LABELS, load_split, read_ready_manifest


def contiguous_runs(keys, stamps, valid):
    """Return [start,stop) index spans with valid targets and adjacent 25 Hz keys.

    Arrays keep original frame keys. Invalid targets, missing N, timestamp gaps,
    match changes and half boundaries always break runs. No compaction/filling.
    """
    if not (len(keys) == len(stamps) == len(valid)):
        raise ValueError("timeline length mismatch")
    runs, start = [], None
    for i, (key, stamp, good) in enumerate(zip(keys, stamps, valid)):
        adjacent = i > 0 and (key.match_id, key.period, key.source_frame-1, stamp-STEP_US) == (
            keys[i-1].match_id, keys[i-1].period, keys[i-1].source_frame, stamps[i-1])
        if start is not None and (not good or not adjacent):
            runs.append((start, i))
            start = None
        if good and start is None:
            start = i
    if start is not None:
        runs.append((start, len(keys)))
    return runs


def distribution(values):
    """Finite-only descriptive summary; missing count explicit, no fitted bins."""
    import numpy as np
    values = np.asarray(values, dtype=float)
    finite = values[np.isfinite(values)]
    return dict(defined=int(len(finite)), missing=int(len(values)-len(finite)),
                mean=float(finite.mean()) if len(finite) else None,
                p10=float(np.quantile(finite, .1)) if len(finite) else None,
                median=float(np.median(finite)) if len(finite) else None,
                p90=float(np.quantile(finite, .9)) if len(finite) else None)


def label_run_summary(labels, runs):
    """Describe maximal H/A/D runs, inside supplied valid contiguous spans only.

    Lengths are frames (25 Hz) and mean seconds. A one-frame run is an exact
    count, not a tuned short-spell cutoff. D is a stoppage, not a possession.
    """
    lengths = {label: [] for label in LABELS}
    transitions = {a+"->"+b: 0 for a in LABELS for b in LABELS if a != b}
    for start, stop in runs:
        head = start
        for i in range(start+1, stop):
            if labels[i] != labels[i-1]:
                lengths[labels[head]].append(i-head)
                transitions[labels[i-1]+"->"+labels[i]] += 1
                head = i
        lengths[labels[head]].append(stop-head)
    summary = {}
    for label, spans in lengths.items():
        stats = distribution(spans)
        summary[label] = dict(runs=len(spans), frames=sum(spans), single_frame_runs=spans.count(1),
                              length_frames=stats, mean_duration_s=stats["mean"]/25 if spans else None)
    return dict(by_label=summary, transitions=transitions,
                possession_spells=len(lengths["H"])+len(lengths["A"]))


def summarize(keys, stamps, x, truth, valid, predicted, probabilities):
    """Diagnose frame errors, H/A confusion, geometry associations and flicker.

    Inputs: original keys, UTC microseconds, the fixed 16-feature metre/m/s
    matrix, nullable external labels, valid mask, raw H/A/D predictions and
    probabilities in H/A/D order. Outputs aggregate dictionaries only. Target
    values are used for diagnosis, never features, fitting or selection. Sign
    groups use the pitch centre, not learned thresholds or attack directions.
    """
    import numpy as np
    if not (len(keys) == len(stamps) == len(x) == len(truth) == len(valid) == len(predicted) == len(probabilities)):
        raise ValueError("diagnostic length mismatch")
    x, truth, valid = np.asarray(x,dtype=float), np.asarray(truth,dtype=object), np.asarray(valid,dtype=bool)
    predicted, probabilities = np.asarray(predicted), np.asarray(probabilities,dtype=float)
    if x.shape != (len(keys),len(FEATURE_NAMES)) or probabilities.shape != (len(keys),3):
        raise ValueError("diagnostic feature/probability shape mismatch")
    if not np.isfinite(probabilities).all() or (probabilities<0).any() or (probabilities>1).any() or not np.allclose(probabilities.sum(axis=1),1,atol=1e-8,rtol=0):
        raise ValueError("invalid probabilities")
    if any(p not in LABELS for p in predicted) or any(t not in LABELS for t in truth[valid]):
        raise ValueError("unsupported labels")
    correct = predicted == truth
    alive = valid & np.isin(truth,["H","A"])
    swaps = alive & np.isin(predicted,["H","A"]) & ~correct
    alive_to_dead = alive & (predicted=="D")
    dead_to_alive = valid & (truth=="D") & (predicted!="D")
    outcomes = {"correct":valid & correct, "HA_swap":swaps,
                "alive_to_D":alive_to_dead, "D_to_alive":dead_to_alive}
    max_prob = probabilities.max(axis=1)
    ordered = np.sort(probabilities,axis=1)
    margin = ordered[:,-1]-ordered[:,-2]
    logp = np.zeros_like(probabilities)
    np.log(probabilities,out=logp,where=probabilities>0)
    entropy = -(probabilities*logp).sum(axis=1)
    confidence = {name:dict(frames=int(mask.sum()), max_probability=distribution(max_prob[mask]),
                           top_two_margin=distribution(margin[mask]), entropy_nats=distribution(entropy[mask]))
                  for name,mask in outcomes.items()}
    ball_x = x[:,FEATURE_NAMES.index("ball_x_m")]
    home_distance = x[:,FEATURE_NAMES.index("nearest_home_m")]
    away_distance = x[:,FEATURE_NAMES.index("nearest_away_m")]
    geometry = {}
    comparable = alive & np.isfinite(home_distance) & np.isfinite(away_distance)
    home_closer, away_closer = home_distance<away_distance, away_distance<home_distance
    for label in LABELS:
        mask = valid & (truth==label)
        geometry[label] = dict(frames=int(mask.sum()),
            ball_x_m=distribution(ball_x[mask]),
            ball_y_m=distribution(x[mask,FEATURE_NAMES.index("ball_y_m")]),
            nearest_home_minus_away_m=distribution((home_distance-away_distance)[mask]),
            ball_speed_mps=distribution(x[mask,FEATURE_NAMES.index("ball_speed_mps")]))
    sides = {}
    for name, sign in (("negative",np.isfinite(ball_x) & (ball_x<0)),("centre",ball_x==0),
                       ("positive",np.isfinite(ball_x) & (ball_x>0)),("missing",~np.isfinite(ball_x))):
        mask = alive & sign
        sides[name] = dict(alive_frames=int(mask.sum()), HA_swaps=int((mask & swaps).sum()),
                           alive_to_D=int((mask & alive_to_dead).sum()),
                           correct=int((mask & correct).sum()),
                           true_H=int((mask & (truth=="H")).sum()), true_A=int((mask & (truth=="A")).sum()))
    nearest = dict(comparable_alive_frames=int(comparable.sum()),
                   ties=int((comparable & (home_distance==away_distance)).sum()),
                   closer_team_matches_target=int((comparable & (((truth=="H") & home_closer) | ((truth=="A") & away_closer))).sum()),
                   closer_team_matches_prediction=int((comparable & (((predicted=="H") & home_closer) | ((predicted=="A") & away_closer))).sum()))
    runs = contiguous_runs(keys,stamps,valid)
    internal_swaps = internal_dead_changes = 0
    error_lengths = []
    for start,stop in runs:
        error_start = None
        for i in range(start,stop):
            if not correct[i] and error_start is None:
                error_start=i
            if correct[i] and error_start is not None:
                error_lengths.append(i-error_start)
                error_start=None
            if i>start and truth[i]==truth[i-1] and truth[i] in ("H","A") and predicted[i]!=predicted[i-1]:
                if predicted[i] in ("H","A") and predicted[i-1] in ("H","A"):
                    internal_swaps+=1
                else:
                    internal_dead_changes+=1
        if error_start is not None:
            error_lengths.append(stop-error_start)
    # Inspect target-constant possessions, not arbitrary temporal windows.
    gt_runs, pred_runs = label_run_summary(truth,runs),label_run_summary(predicted,runs)
    return dict(observed_frames=len(keys), valid_frames=int(valid.sum()), invalid_frames=int((~valid).sum()),
                confusion_order=list(LABELS),
                confusion=[[int((valid & (truth==a) & (predicted==b)).sum()) for b in LABELS] for a in LABELS],
                frame_errors={name:int(mask.sum()) for name,mask in outcomes.items()},
                alive_frames=int(alive.sum()), confidence_by_outcome=confidence,
                geometry_by_target=geometry, alive_errors_by_ball_x_sign=sides, nearest_geometry=nearest,
                valid_contiguous_runs=len(runs), target_runs=gt_runs, prediction_runs=pred_runs,
                predicted_HA_switches_inside_constant_true_possession=internal_swaps,
                predicted_D_changes_inside_constant_true_possession=internal_dead_changes,
                error_run_length_frames=distribution(error_lengths))


def diagnose(features,targets,predictions,output):
    """Write aggregate report and provenance in a new directory, from explicit DBs.

    All SQLite inputs are read-only; matching source hashes/lineage and exact
    keyed prediction timestamps/splits are required. No model is deserialized,
    no retraining, calibration, decoder or prediction modification occurs.
    """
    import numpy as np
    paths = [Path(p).resolve(strict=True) for p in (features,targets,predictions)]
    f,t,p = paths
    if [v.name for v in paths] != ["features.sqlite","targets.sqlite","predictions.sqlite"]:
        raise ValueError("explicit feature/target/prediction artifact filenames required")
    manifest_paths = [v.parent/"manifest.json" for v in paths]
    fm,tm,pm = [read_ready_manifest(v) for v in manifest_paths]
    if fm["output_sha256"]!=sha256(f) or pm["outputs_sha256"]["predictions.sqlite"]!=sha256(p):
        raise ValueError("artifact hash mismatch")
    if fm["input"]["parent_manifest_sha256"]!=sha256(manifest_paths[1]):
        raise ValueError("feature/target lineage mismatch")
    for source in (f,t,*manifest_paths[:2]):
        if pm["inputs_sha256"].get(str(source))!=sha256(source):
            raise ValueError("prediction input provenance mismatch")
    output = Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter()
    try:
        hashes={str(v):sha256(v) for v in (*paths,*manifest_paths)}
        sources={str(v.relative_to(REPO)):sha256(v) for v in sorted((REPO/"external_baseline").glob("*.py"))}
        report={"splits":{},"policy":"Aggregate external diagnosis only; no model/parameter/prediction changes. Association is not proof of causation."}
        with closing(sqlite3.connect(p.as_uri()+"?mode=ro",uri=True)) as db:
            db.execute("PRAGMA query_only=ON")
            periods=[r[0] for r in db.execute("SELECT DISTINCT period FROM predictions ORDER BY period")]
            if periods!=[1,2]:
                raise ValueError("expected predictions for both halves only")
            for period in (1,2):
                keys,stamps,x,y,valid=load_split(f,t,period)
                pred_rows=db.execute("SELECT match_id,period,source_frame,timestamp_us,split,label,p_H,p_A,p_D FROM predictions WHERE period=? ORDER BY match_id,period,source_frame",(period,)).fetchall()
                if len(pred_rows)!=len(keys) or any(row[:5]!=(k.match_id,k.period,k.source_frame,stamp,SPLITS[period]) for row,k,stamp in zip(pred_rows,keys,stamps)):
                    raise ValueError("prediction keys/timestamps/splits do not match features")
                report["splits"][SPLITS[period]]=summarize(keys,stamps,x,y,valid,np.array([r[5] for r in pred_rows]),np.asarray([r[6:] for r in pred_rows]))
        report.update(elapsed_seconds=round(time.perf_counter()-started,3),process_peak_resident_bytes=peak_memory_bytes())
        if any(sha256(Path(v))!=h for v,h in hashes.items()) or any(sha256(REPO/v)!=h for v,h in sources.items()):
            raise ValueError("input/source changed during diagnosis")
        (output/"diagnostic_report.json").write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        manifest={"status":"ready","contract_version":1,"diagnostic_version":1,
                  "inputs_sha256":hashes,"source_sha256":sources,"git":git_metadata(),
                  "output_sha256":sha256(output/"diagnostic_report.json"),
                  "provenance":pm.get("provenance",{}),
                  "decisions":"Descriptive geometry, outcome confidence and run statistics; no selected thresholds or decoder. No official match accessed."}
        (output/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        return report
    except Exception as error:
        (output/"FAILED.json").write_text(json.dumps({"status":"failed","error":str(error)})+"\n",encoding="utf-8")
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("features","targets","predictions","output"):
        parser.add_argument("--"+name,required=True,type=Path)
    args=parser.parse_args()
    report=diagnose(args.features,args.targets,args.predictions,args.output)
    print(json.dumps({s:{k:v[k] for k in ("valid_frames","frame_errors","predicted_HA_switches_inside_constant_true_possession")} for s,v in report["splits"].items()},indent=2))


if __name__=="__main__":
    main()
