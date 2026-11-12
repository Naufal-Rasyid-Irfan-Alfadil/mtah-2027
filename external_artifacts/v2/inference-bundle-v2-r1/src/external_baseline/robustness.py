"""Fixed observation-level stress tests on external validation, with frozen models."""

import argparse
from collections import Counter
from contextlib import closing
import importlib.metadata
from itertools import groupby
import json
import math
from pathlib import Path
import platform
import sqlite3
import time

from .contracts import FrameKey
from .features import (FEATURE_NAMES, EntityPosition, FrameFeatureExtractor,
                       _validate_observation_db)
from .prepare import REPO, sha256, git_metadata, peak_memory_bytes
from .temporal import decode_probabilities, _prediction_rows
from .training import (FEATURE_SETS, PACKAGES, HGB_PARAMS, load_split,
                       read_ready_manifest, predict_raw, project_features, evaluate_timeline)

SEED = 2027
SCENARIOS = (
    {"name":"clean","kind":"identity"},
    {"name":"ball_drop_iid20","kind":"ball_drop","probability":.2},
    {"name":"ball_drop_burst2s","kind":"ball_burst","period_frames":500,"missing_frames":50},
    {"name":"ball_x_missing_iid20","kind":"ball_partial","probability":.2},
    {"name":"player_drop_iid20","kind":"player_drop","probability":.2},
    {"name":"position_jitter_025m","kind":"jitter","sigma_m":.25},
    {"name":"frame_gap1s_every60s","kind":"frame_gap","period_frames":1500,"missing_frames":25},
)


def perturb_frame(entities, offset, scenario, rng):
    """Return (retained, new entities, audit counts), without labels or target masks.

    Coordinates are centred metres; offsets are original N minus the half's first
    N (not compacted row indices). Ball/full-frame masks are selected independently
    of coordinate validity. Player draws follow stable entity order. Jitter is
    independent per finite axis and frame, without clipping. Missing axes remain
    missing. Each scenario owns a fresh seeded generator; source objects are
    immutable and never edited. Frame removal is distinct from absent ball data.
    """
    entities = list(entities)
    kind = scenario["kind"]
    counts = Counter()
    if kind == "frame_gap":
        if offset % scenario["period_frames"] < scenario["missing_frames"]:
            return False,[],Counter(selected_frames=1,removed_frames=1)
        return True,entities,counts
    selected = False
    if kind in ("ball_drop","ball_partial"):
        selected = rng.random() < scenario["probability"]
    elif kind == "ball_burst":
        selected = offset % scenario["period_frames"] < scenario["missing_frames"]
    elif kind not in ("identity","player_drop","jitter"):
        raise ValueError("unknown stress scenario")
    counts["selected_frames"] += int(selected)
    result=[]
    for entity in entities:
        if entity.team == "BALL" and selected:
            if kind in ("ball_drop","ball_burst"):
                counts["ball_records_removed"] += 1
                continue
            counts["ball_x_masked_records"] += 1
            result.append(EntityPosition(entity.entity_id,entity.team,None,entity.y_m))
        elif kind == "player_drop" and entity.team in ("H","A") and rng.random() < scenario["probability"]:
            counts["player_records_removed"] += 1
        elif kind == "jitter":
            coords=[]
            for value in (entity.x_m,entity.y_m):
                if value is not None and math.isfinite(value):
                    coords.append(value+float(rng.normal(0,scenario["sigma_m"])))
                    counts["jittered_axes"] += 1
                else:
                    coords.append(value)
            result.append(EntityPosition(entity.entity_id,entity.team,*coords))
        else:
            result.append(entity)
    return True,result,counts


def stress_feature_matrices(observations, period=2, seed=SEED, context=False):
    """Replay one explicit half into seven fixed feature matrices and masks.

    One streaming read; memory holds one frame of entities plus per-scenario
    frame matrices. Features are recomputed after perturbation, including speed,
    distances and coverage. Removed frames retain their original keys but are not
    passed to an extractor; the next frame's speed therefore sees the gap. No
    target file or fitted preprocessing is used. Default half 2/seed 2027 retains
    the stress protocol. Augmentation explicitly uses half 1 and another seed.
    Returns keys, timestamps, matrices, retained masks and audit counters.
    With context=True, matrices are (N,20) in FEATURE_NAMES + CONTEXT_NAMES
    order and causal context is recomputed after perturbation. Default remains
    the original (N,16) contract. No target or identity-based velocity is used.
    """
    import numpy as np
    from .features import ContextFeatureExtractor, CONTEXT_NAMES
    names = FEATURE_NAMES + CONTEXT_NAMES if context else FEATURE_NAMES
    extractor_type = ContextFeatureExtractor if context else FrameFeatureExtractor
    if period not in (1,2):
        raise ValueError("explicit first or second half required")
    with closing(sqlite3.connect(Path(observations).resolve().as_uri()+"?mode=ro",uri=True)) as db:
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA cache_size=-8192")
        db.execute("PRAGMA temp_store=FILE")
        meta=_validate_observation_db(db)
        count=db.execute("SELECT COUNT(*) FROM frames WHERE period=?",(period,)).fetchone()[0]
        first=db.execute("SELECT MIN(source_frame) FROM frames WHERE period=?",(period,)).fetchone()[0]
        if not count:
            raise ValueError("observations required for selected half")
        matrices={s["name"]:np.full((count,len(names)),np.nan) for s in SCENARIOS}
        retained={s["name"]:np.zeros(count,dtype=bool) for s in SCENARIOS}
        audits={s["name"]:Counter(input_frames=count) for s in SCENARIOS}
        extractors={s["name"]:extractor_type(meta["length_m"],meta["width_m"]) for s in SCENARIOS}
        generators={s["name"]:np.random.default_rng(seed) for s in SCENARIOS}
        rows=db.execute("""SELECT f.match_id,f.period,f.source_frame,f.timestamp_us,o.entity_id,o.team,o.x_m,o.y_m
            FROM frames f LEFT JOIN observations o USING(match_id,period,source_frame)
            WHERE f.period=? ORDER BY f.match_id,f.period,f.source_frame,o.entity_id""",(period,))
        keys,stamps=[],[]
        for i,(identity,group) in enumerate(groupby(rows,key=lambda r:r[:4])):
            key,stamp=FrameKey(*identity[:3]),identity[3]
            if key.match_id != meta["match_id"]:
                raise ValueError("observation match mismatch")
            keys.append(key)
            stamps.append(stamp)
            entities=[EntityPosition(*row[4:]) for row in group if row[4] is not None]
            for scenario in SCENARIOS:
                name=scenario["name"]
                keep,changed,counts=perturb_frame(entities,key.source_frame-first,scenario,generators[name])
                audits[name].update(counts)
                retained[name][i]=keep
                if keep:
                    matrices[name][i]=list(extractors[name].extract(key,stamp,changed).values())
        if len(keys)!=count:
            raise ValueError("observation frame count changed")
        return keys,stamps,matrices,retained,audits


def _score_summary(metrics):
    return dict(spell_f1_mean=metrics["spell_f1_mean"],macro_f1=metrics["macro_f1"],
                n_pred_spells=metrics["n_pred_spells"],n_gt_spells=metrics["n_gt_spells"],
                n_graded=metrics["n_graded"],n_abstain_on_graded=metrics["n_abstain_on_graded"],
                per_class_f1={k:v["f1"] for k,v in metrics["per_class"].items()})


def validate_frozen_pipeline(observations,features,targets,classifier,decoder):
    """Verify explicit external artifact lineage/hashes without loading a model.

    Returns resolved input paths, verified files and classifier/decoder manifests.
    Does not read scores or fit anything; callers retain/recheck hashes over work.
    """
    o,f,t=[Path(v).resolve(strict=True) for v in (observations,features,targets)]
    classifier,decoder=Path(classifier).resolve(strict=True),Path(decoder).resolve(strict=True)
    if [v.name for v in (o,f,t)]!=["observations.sqlite","features.sqlite","targets.sqlite"]:
        raise ValueError("explicit observation/feature/target filenames required")
    om_path,fm_path,tm_path=o.parent/"manifest.json",f.parent/"manifest.json",t.parent/"manifest.json"
    om,fm,tm=[read_ready_manifest(v) for v in (om_path,fm_path,tm_path)]
    cm_path,dm_path=classifier/"manifest.json",decoder/"manifest.json"
    cm,dm=read_ready_manifest(cm_path),read_ready_manifest(dm_path)
    if fm["input"]["sha256"]!=sha256(o) or fm["input"]["parent_manifest_sha256"]!=sha256(om_path) or sha256(om_path)!=sha256(tm_path):
        raise ValueError("observation/feature/target lineage mismatch")
    if fm["output_sha256"]!=sha256(f):
        raise ValueError("feature hash mismatch")
    if cm["config"]["feature_names"]!=list(FEATURE_SETS["no-signed-position"]) or cm["config"].get("decoder") is not None:
        raise ValueError("frozen raw 14-feature classifier required")
    if cm.get("packages")!={p:importlib.metadata.version(p) for p in PACKAGES}:
        raise ValueError("classifier dependency versions differ")
    for v in (f,t,fm_path,tm_path):
        if cm["inputs_sha256"].get(str(v))!=sha256(v) or dm["inputs_sha256"].get(str(v))!=sha256(v):
            raise ValueError("frozen pipeline input provenance mismatch")
    if dm["inputs_sha256"].get(str(classifier/"predictions.sqlite"))!=sha256(classifier/"predictions.sqlite") or dm["inputs_sha256"].get(str(cm_path))!=sha256(cm_path):
        raise ValueError("decoder was not fitted for this raw classifier artifact")
    paths=[o,f,t,om_path,fm_path,tm_path,cm_path,dm_path]
    for directory,manifest in ((classifier,cm),(decoder,dm)):
        for name,digest in manifest["outputs_sha256"].items():
            if Path(name).name!=name or name not in ("model.joblib","predictions.sqlite","config.json","comparison.json","decoder_parameters.json","metrics.json"):
                raise ValueError("unexpected artifact output name")
            v=directory/name
            if sha256(v)!=digest:
                raise ValueError("frozen pipeline output hash mismatch")
            paths.append(v)
    return o,f,t,classifier,decoder,paths,cm,dm


def run_robustness(observations,features,targets,classifier,decoder,output):
    """Stress only external half 2 with one trusted frozen classifier/decoder pair.

    Inputs are explicit artifact paths/directories; sources stay read-only and
    are checked against their recorded lineage/hashes. No fit/estimate/tune call
    is made. Clean features, raw probabilities and decoded labels must exactly
    replay the frozen artifacts before a report can be ready. Target labels are
    loaded only after all perturbed predictions/decoding. Frame gaps produce X
    on the full evaluation timeline, not target removal or artificial D labels.
    """
    import joblib
    import numpy as np

    o,f,t,classifier,decoder,paths,cm,dm=validate_frozen_pipeline(observations,features,targets,classifier,decoder)
    output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter()
    try:
        hashes={str(v):sha256(v) for v in paths}
        sources={str(v.relative_to(REPO)):sha256(v) for v in sorted((REPO/"external_baseline").glob("*.py"))}
        sources["evaluation/possession_metrics.py"]=sha256(REPO/"evaluation/possession_metrics.py")
        protocol=dict(version=1,period=2,seed=SEED,scenarios=SCENARIOS,
                      fitting="none; classifier and decoder parameters frozen",
                      selection="predeclared engineering probes; not chosen to match official distributions or optimize scores",
                      evaluation="full original target timeline; removed frames predict X; temporal scorer fills abstentions within GT-valid runs only for scoring")
        (output/"protocol.json").write_text(json.dumps(protocol,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        artifact=joblib.load(classifier/"model.joblib")  # Own hash-verified local artifact only.
        if tuple(artifact["feature_names"])!=FEATURE_SETS["no-signed-position"] or artifact["model"].n_features_in_!=14 or artifact["model"].get_params()!=HGB_PARAMS:
            raise ValueError("frozen model feature order/parameters mismatch")
        params=json.loads((decoder/"decoder_parameters.json").read_text(encoding="utf-8"))
        keys,stamps,matrices,retained,audits=stress_feature_matrices(o)
        with closing(sqlite3.connect(f.as_uri()+"?mode=ro",uri=True)) as db:
            reference=db.execute("SELECT match_id,period,source_frame,timestamp_us,"+",".join(FEATURE_NAMES)+" FROM features WHERE period=2 ORDER BY match_id,period,source_frame").fetchall()
        if len(reference)!=len(keys) or any(row[:4]!=(k.match_id,k.period,k.source_frame,stamp) for row,k,stamp in zip(reference,keys,stamps)):
            raise ValueError("feature/observation validation timelines disagree")
        if not np.array_equal(matrices["clean"],np.asarray([r[4:] for r in reference],dtype=float),equal_nan=True):
            raise ValueError("clean observation feature replay differs")
        raw_reference=_prediction_rows((classifier/"predictions.sqlite").resolve(),2)
        if keys!=raw_reference[0] or stamps!=raw_reference[1]:
            raise ValueError("clean classifier timeline mismatch")
        results={}
        for scenario in SCENARIOS:
            name=scenario["name"]
            keep=retained[name]
            raw,decoded=np.full(len(keys),"X",dtype="U1"),np.full(len(keys),"X",dtype="U1")
            probs=np.full((len(keys),3),np.nan)
            if keep.any():
                raw[keep],probs[keep]=predict_raw(artifact["model"],project_features(matrices[name][keep],"no-signed-position"))
                decoded[keep]=decode_probabilities([k for k,g in zip(keys,keep) if g],[s for s,g in zip(stamps,keep) if g],probs[keep],params)
            results[name]=(raw,decoded,probs)
        if not np.array_equal(results["clean"][0],raw_reference[2]) or not np.array_equal(results["clean"][2],raw_reference[3]):
            raise ValueError("clean raw model replay differs")
        with closing(sqlite3.connect((decoder/"predictions.sqlite").resolve().as_uri()+"?mode=ro",uri=True)) as db:
            decoded_reference=db.execute("SELECT match_id,period,source_frame,timestamp_us,label FROM predictions WHERE period=2 ORDER BY match_id,period,source_frame").fetchall()
        if len(decoded_reference)!=len(keys) or any(row[:4]!=(k.match_id,k.period,k.source_frame,s) for row,k,s in zip(decoded_reference,keys,stamps)) or not np.array_equal(results["clean"][1],[r[4] for r in decoded_reference]):
            raise ValueError("clean decoder replay differs")
        # Labels/masks first enter the stress workflow here, after all inference.
        data=load_split(f,t,2)
        if data[0]!=keys or data[1]!=stamps:
            raise ValueError("target timeline mismatch")
        y,valid=data[3:]
        report=dict(scenarios={},interpretation="Synthetic stress on reused external inter-half validation; not an estimate of official performance or inter-match generalization. No tuning/retraining.")
        with closing(sqlite3.connect(output/"predictions.sqlite")) as db:
            db.execute("""CREATE TABLE predictions(scenario TEXT,match_id TEXT,period INTEGER,source_frame INTEGER,
                timestamp_us INTEGER,retained INTEGER,raw_label TEXT,decoded_label TEXT,p_H REAL,p_A REAL,p_D REAL,
                PRIMARY KEY(scenario,match_id,period,source_frame)) WITHOUT ROWID""")
            for scenario in SCENARIOS:
                name=scenario["name"]
                raw,decoded,probs=results[name]
                keep=retained[name]
                raw_metrics=evaluate_timeline(keys,stamps,y,valid,raw,allow_abstain=True)
                decoded_metrics=evaluate_timeline(keys,stamps,y,valid,decoded,allow_abstain=True)
                coverage={n:dict(defined=int(np.isfinite(matrices[name][keep,j]).sum()),missing=int((~np.isfinite(matrices[name][keep,j])).sum())) for j,n in enumerate(FEATURE_NAMES)}
                report["scenarios"][name]=dict(audit=dict(audits[name]),input_frames=len(keys),retained_frames=int(keep.sum()),
                    retained_fraction=float(keep.mean()),feature_coverage_on_retained_frames=coverage,
                    raw_metrics=raw_metrics,decoded_metrics=decoded_metrics,
                    raw_summary=_score_summary(raw_metrics),decoded_summary=_score_summary(decoded_metrics))
                db.executemany("INSERT INTO predictions VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    ((name,k.match_id,k.period,k.source_frame,int(s),int(g),str(a),str(b),*[float(v) if np.isfinite(v) else None for v in prob])
                     for k,s,g,a,b,prob in zip(keys,stamps,keep,raw,decoded,probs)))
            db.commit()
        clean=report["scenarios"]["clean"]["decoded_summary"]
        for value in report["scenarios"].values():
            value["decoded_delta_from_clean"]={n:value["decoded_summary"][n]-clean[n] for n in ("spell_f1_mean","macro_f1","n_pred_spells")}
        report.update(elapsed_seconds=round(time.perf_counter()-started,3),process_peak_resident_bytes=peak_memory_bytes(),clean_replay="exact features, raw labels/probabilities and decoded labels verified")
        (output/"robustness_report.json").write_text(json.dumps(report,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")
        if any(sha256(Path(v))!=h for v,h in hashes.items()) or any(sha256(REPO/v)!=h for v,h in sources.items()):
            raise ValueError("input/source changed during stress testing")
        manifest=dict(status="ready",contract_version=1,robustness_version=1,protocol=protocol,
                      inputs_sha256=hashes,source_sha256=sources,git=git_metadata(),python=platform.python_version(),
                      packages={p:importlib.metadata.version(p) for p in PACKAGES},
                      outputs_sha256={name:sha256(output/name) for name in ("protocol.json","predictions.sqlite","robustness_report.json")},
                      provenance={"frozen_decoder":dm.get("provenance",{}),"selection":protocol["selection"],
                                  "official_data":"No official data/GT accessed; no freezing or official inference adapter added."})
        (output/"manifest.json").write_text(json.dumps(manifest,indent=2,sort_keys=True)+"\n",encoding="utf-8")
        return report
    except Exception as error:
        (output/"FAILED.json").write_text(json.dumps({"status":"failed","error":str(error)})+"\n",encoding="utf-8")
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("observations","features","targets","classifier","decoder","output"):
        parser.add_argument("--"+name,required=True,type=Path)
    args=parser.parse_args()
    report=run_robustness(args.observations,args.features,args.targets,args.classifier,args.decoder,args.output)
    print(json.dumps({name:{"retained_fraction":v["retained_fraction"],**v["decoded_summary"]} for name,v in report["scenarios"].items()},indent=2))


if __name__=="__main__":
    main()
