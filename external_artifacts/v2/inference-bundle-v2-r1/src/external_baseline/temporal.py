"""One fixed external-only Markov/Viterbi comparator; no classifier retraining."""

import argparse
from contextlib import closing
import importlib.metadata
import json
from pathlib import Path
import platform
import sqlite3
import time

from .contracts import FrameKey, SPLITS
from .diagnostics import contiguous_runs
from .prepare import REPO, sha256, git_metadata, peak_memory_bytes
from .training import (LABELS, FEATURE_SETS, load_split, read_ready_manifest,
                       evaluate_timeline, comparison_entry)

DECODER_VERSION = 1
PSEUDOCOUNT = 1.0  # Fixed Laplace smoothing, not selected from validation.


def estimate_markov(keys, stamps, labels, valid):
    """Estimate state prior and row-normalized transitions from valid half-1 GT.

    Counts use adjacent 40 ms original frame keys within a valid contiguous run.
    Missing/ambiguous targets and observation/period gaps cannot form training
    transitions. One fixed pseudocount is added to each class/transition cell.
    Initial prior equals the smoothed frame occupancy prior, avoiding an estimate
    based on the single kickoff. Units: transitions per 25 Hz step; no durations
    or validation probabilities are fitted. Returns JSON-serializable parameters.
    """
    import numpy as np
    if not keys or any(k.period != 1 for k in keys):
        raise ValueError("decoder fitting requires nonempty half-1 training only")
    if not (len(keys) == len(stamps) == len(labels) == len(valid)):
        raise ValueError("training timeline length mismatch")
    lookup = {label:i for i,label in enumerate(LABELS)}
    state_counts = np.zeros(3,dtype=np.int64)
    transitions = np.zeros((3,3),dtype=np.int64)
    runs = contiguous_runs(keys,stamps,valid)
    for start,stop in runs:
        for i in range(start,stop):
            if labels[i] not in lookup:
                raise ValueError("invalid supervised training label")
            current = lookup[labels[i]]
            state_counts[current] += 1
            if i > start:
                transitions[lookup[labels[i-1]],current] += 1
    if not (state_counts > 0).all():
        raise ValueError("decoder training must contain valid H, A and D")
    prior = (state_counts+PSEUDOCOUNT)/(state_counts.sum()+3*PSEUDOCOUNT)
    matrix = (transitions+PSEUDOCOUNT)/(transitions.sum(axis=1,keepdims=True)+3*PSEUDOCOUNT)
    return dict(decoder_version=DECODER_VERSION, classes=list(LABELS), fps=25,
                pseudocount=PSEUDOCOUNT, state_counts=state_counts.tolist(),
                transition_counts=transitions.tolist(), valid_training_frames=int(state_counts.sum()),
                training_runs=len(runs), observed_transitions=int(transitions.sum()),
                state_prior=prior.tolist(), initial_prior=prior.tolist(),
                transition_matrix=matrix.tolist(),
                emission="log classifier posterior - log training state prior",
                emission_weight=1.0, transition_weight=1.0)


def _probability_array(values, shape, name, positive=False):
    import numpy as np
    values = np.asarray(values,dtype=float)
    if values.shape != shape or not np.isfinite(values).all() or (values < 0).any() or (values > 1).any():
        raise ValueError("invalid "+name)
    if positive and not (values>0).all():
        raise ValueError(name+" must be strictly positive")
    if not np.allclose(values.sum(axis=-1),1,atol=1e-8,rtol=0):
        raise ValueError(name+" must sum to one")
    return values


def decode_probabilities(keys, stamps, probabilities, parameters):
    """Return offline Viterbi H/A/D labels in original row order, without targets.

    Inputs are keyed 25 Hz classifier posteriors in H/A/D order and fixed fitted
    parameters. Each observation-contiguous run is decoded independently; class
    labels, valid-target masks, feature values and validation GT are not inputs.
    Objective: log(initial[s0]) + sum(log(posterior[t,s])-log(prior[s]))
    + sum(log(transition[s_prev,s])). Both weights are one. No minimum duration,
    abstention threshold or clipping of probabilities is used. Exact zeros have
    log score -inf. Ties use fixed H/A/D index order. Future observations within
    a run may influence earlier labels, so this is not online inference.

    Version 2 retains the same input/output shapes (N,3) -> (N,), but allows
    prior correction alpha in {0,.5,1} and transition beta in {.5,1}:
    log posterior - alpha*log prior + beta*log transition. Initial prior stays
    fixed. These discriminative score variants are not generative likelihoods.
    """
    import numpy as np
    if len(keys) != len(stamps):
        raise ValueError("prediction timeline length mismatch")
    version = parameters.get("decoder_version")
    if version not in (1, 2) or parameters.get("classes") != list(LABELS) or parameters.get("fps") != 25:
        raise ValueError("unsupported decoder contract/class order/FPS")
    if version == 1 and (parameters.get("emission_weight") != 1 or parameters.get("transition_weight") != 1):
        raise ValueError("only the fixed unweighted comparator is supported")
    # V2 is a bounded discriminative score experiment, not a generative HMM fit.
    alpha = parameters.get('prior_correction', 1.0) if version == 2 else 1.0
    beta = parameters.get('transition_weight', 1.0)
    if version == 2 and (alpha not in (0, .5, 1) or beta not in (.5, 1)
                         or parameters.get('emission_weight') != 1):
        raise ValueError('unsupported v2 score configuration')
    probs = _probability_array(probabilities,(len(keys),3),"posteriors")
    prior = _probability_array(parameters["state_prior"],(3,),"state prior",True)
    initial = _probability_array(parameters["initial_prior"],(3,),"initial prior",True)
    matrix = _probability_array(parameters["transition_matrix"],(3,3),"transition matrix",True)
    for old,new in zip(keys,keys[1:]):
        if (old.match_id,old.period,old.source_frame) >= (new.match_id,new.period,new.source_frame):
            raise ValueError("decoder frame keys must be unique and ordered")
    log_posterior = np.full_like(probs,-np.inf)
    np.log(probs,out=log_posterior,where=probs>0)
    emissions = log_posterior-alpha*np.log(prior)
    log_matrix = beta*np.log(matrix)
    result = np.empty(len(keys),dtype="U1")
    # Crucially, no target-valid mask is used for inference run boundaries.
    for start,stop in contiguous_runs(keys,stamps,[True]*len(keys)):
        parents = np.zeros((stop-start,3),dtype=np.int8)
        score = np.log(initial)+emissions[start]
        for offset in range(1,stop-start):
            candidates = score[:,None]+log_matrix
            parents[offset] = np.argmax(candidates,axis=0)
            score = candidates[parents[offset],np.arange(3)]+emissions[start+offset]
            score -= score.max()  # Common offset only; preserves the optimum.
        state = int(np.argmax(score))
        for offset in range(stop-start-1,-1,-1):
            result[start+offset] = LABELS[state]
            state = int(parents[offset,state])
    return result


def _prediction_rows(path, period):
    """Load only keyed raw predictions/probabilities, never a serialized classifier."""
    import numpy as np
    with closing(sqlite3.connect(path.as_uri()+"?mode=ro",uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        if [r[0] for r in db.execute("SELECT DISTINCT period FROM predictions ORDER BY period")] != [1,2]:
            raise ValueError("raw predictions must cover both halves only")
        rows = db.execute("SELECT match_id,period,source_frame,timestamp_us,split,label,p_H,p_A,p_D FROM predictions WHERE period=? ORDER BY match_id,period,source_frame",(period,)).fetchall()
    if not rows or any(row[4] != SPLITS[period] or row[5] not in LABELS for row in rows):
        raise ValueError("invalid raw prediction split/label")
    keys,stamps = [FrameKey(*row[:3]) for row in rows],[row[3] for row in rows]
    probs = _probability_array([row[6:] for row in rows],(len(rows),3),"posteriors")
    raw = np.asarray([row[5] for row in rows])
    if any(probs[i,LABELS.index(label)] != probs[i].max() for i,label in enumerate(raw)):
        raise ValueError("raw labels disagree with posterior maxima")
    return keys,stamps,raw,probs


def _check_timeline(data, prediction_data):
    if data[0] != prediction_data[0] or list(data[1]) != list(prediction_data[1]):
        raise ValueError("raw predictions and target/feature timelines disagree")


def run_decoder(features,targets,predictions,output):
    """Fit one Markov comparator on half 1, decode offline, score both halves.

    Explicit ready external artifacts only, opened read-only. Raw classifier is
    the fixed 14-feature ablation and remains untouched. Validation targets are
    loaded only after validation decoding. Output stores decoded hard labels
    separately, not fake decoded probabilities or a tactical CSV. Failure leaves
    no ready manifest. No model refit, EM, tuning or official inputs are used.
    """
    paths = [Path(p).resolve(strict=True) for p in (features,targets,predictions)]
    f,t,p = paths
    if [v.name for v in paths] != ["features.sqlite","targets.sqlite","predictions.sqlite"]:
        raise ValueError("explicit feature/target/raw-prediction artifacts required")
    manifest_paths = [v.parent/"manifest.json" for v in paths]
    fm,tm,pm = [read_ready_manifest(v) for v in manifest_paths]
    if pm["config"].get("decoder") is not None or pm["config"].get("feature_names") != list(FEATURE_SETS["no-signed-position"]):
        raise ValueError("comparator requires the unchanged raw 14-feature classifier")
    if fm["output_sha256"] != sha256(f) or pm["outputs_sha256"]["predictions.sqlite"] != sha256(p):
        raise ValueError("artifact hash mismatch")
    if fm["input"]["parent_manifest_sha256"] != sha256(manifest_paths[1]):
        raise ValueError("feature/target preparation lineage mismatch")
    for v in (f,t,*manifest_paths[:2]):
        if pm["inputs_sha256"].get(str(v)) != sha256(v):
            raise ValueError("raw classifier input provenance mismatch")
    output = Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    started = time.perf_counter()
    try:
        hashes = {str(v):sha256(v) for v in (*paths,*manifest_paths)}
        sources = {str(v.relative_to(REPO)):sha256(v) for v in sorted((REPO/"external_baseline").glob("*.py"))}
        sources["evaluation/possession_metrics.py"] = sha256(REPO/"evaluation/possession_metrics.py")
        train_data = load_split(f,t,1)
        parameters = estimate_markov(train_data[0],train_data[1],train_data[3],train_data[4])
        config = dict(decoder="prior_corrected_markov_viterbi", decoder_version=DECODER_VERSION,
                      raw_feature_set="no-signed-position", pseudocount=PSEUDOCOUNT,
                      emission_weight=1,transition_weight=1,fit_period=1,validation_period=2,
                      inference_boundaries="observation gaps, time discontinuities and match/period only; no target masks",
                      temporal_mode="offline, uses future observations within run", selection="one fixed comparator; no sweep or automatic model promotion")
        for name,value in (("config.json",config),("decoder_parameters.json",parameters)):
            (output/name).write_text(json.dumps(value,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        training_predictions = _prediction_rows(p,1)
        _check_timeline(train_data,training_predictions)
        train_decoded = decode_probabilities(training_predictions[0],training_predictions[1],training_predictions[3],parameters)
        validation_predictions = _prediction_rows(p,2)
        val_decoded = decode_probabilities(validation_predictions[0],validation_predictions[1],validation_predictions[3],parameters)
        # Validation targets cannot affect parameters, scores or inference boundaries above.
        val_data = load_split(f,t,2)
        _check_timeline(val_data,validation_predictions)
        comparison = {"splits":{},"interpretation":"Reused external inter-half development validation, not inter-match test. F1 is not accuracy. No automatic replacement of raw baseline."}
        metrics = {}
        with closing(sqlite3.connect(output/"predictions.sqlite")) as db:
            db.execute("""CREATE TABLE predictions(match_id TEXT,period INTEGER,source_frame INTEGER,
                          timestamp_us INTEGER,split TEXT,label TEXT,
                          PRIMARY KEY(match_id,period,source_frame)) WITHOUT ROWID""")
            for split,data,raw_data,decoded in (("train",train_data,training_predictions,train_decoded),("validation",val_data,validation_predictions,val_decoded)):
                keys,stamps,x,y,valid = data
                raw_metrics = evaluate_timeline(keys,stamps,y,valid,raw_data[2])
                decoded_metrics = evaluate_timeline(keys,stamps,y,valid,decoded)
                raw_entry = comparison_entry(data,raw_data[2],raw_metrics)
                decoded_entry = comparison_entry(data,decoded,decoded_metrics)
                metrics[split] = dict(raw=raw_metrics,decoded=decoded_metrics,target_valid=int(valid.sum()),target_invalid=int((~valid).sum()))
                comparison["splits"][split] = dict(raw14=raw_entry,decoded14=decoded_entry,
                    delta_decoded_minus_raw={k:decoded_entry[k]-raw_entry[k] for k in ("spell_f1_mean","macro_f1","n_pred_spells","HA_swaps","HA_switches_inside_true_possession")})
                db.executemany("INSERT INTO predictions VALUES (?,?,?,?,?,?)",
                    ((k.match_id,k.period,k.source_frame,int(stamp),split,str(label)) for k,stamp,label in zip(keys,stamps,decoded)))
            db.commit()
        for name,value in (("metrics.json",metrics),("comparison.json",comparison)):
            (output/name).write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        if any(sha256(Path(v)) != h for v,h in hashes.items()) or any(sha256(REPO/v) != h for v,h in sources.items()):
            raise ValueError("input/source changed during decoding")
        manifest = dict(status="ready",contract_version=1,decoder_version=DECODER_VERSION,
                        config=config,inputs_sha256=hashes,source_sha256=sources,git=git_metadata(),
                        python=platform.python_version(),numpy=importlib.metadata.version("numpy"),
                        elapsed_seconds=round(time.perf_counter()-started,3),process_peak_resident_bytes=peak_memory_bytes(),
                        outputs_sha256={v:sha256(output/v) for v in ("config.json","decoder_parameters.json","predictions.sqlite","metrics.json","comparison.json")},
                        provenance={"parent":pm.get("provenance",{}),
                            "selection":"14-feature raw source chosen for the explicitly requested temporal comparator after external ablation; validation is reused development data.",
                            "parameters":"Only half-1 target counts; fixed add-one smoothing and unit weights, no validation fitting/calibration, duration cutoff or old-project parameters.",
                            "emission_assumption":"HGB posteriors are treated as class posteriors; divide by training occupancy prior to obtain relative likelihood scores. They are not asserted calibrated or independent over time.",
                            "method_reference":"https://www.inf.ed.ac.uk/teaching/courses/asr/2022-23/asr11-hybrid_hmm_nn.pdf",
                            "official_data":"No official inputs or GT accessed; no official inference pipeline freeze."})
        (output/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        return comparison
    except Exception as error:
        (output/"FAILED.json").write_text(json.dumps({"status":"failed","error":str(error)})+"\n",encoding="utf-8")
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("features","targets","predictions","output"):
        parser.add_argument("--"+name,required=True,type=Path)
    args=parser.parse_args()
    report=run_decoder(args.features,args.targets,args.predictions,args.output)
    print(json.dumps({s:{variant:{k:v[variant][k] for k in ("spell_f1_mean","macro_f1","n_pred_spells")} for variant in ("raw14","decoded14")} for s,v in report["splits"].items()},indent=2))


if __name__=="__main__":
    main()
