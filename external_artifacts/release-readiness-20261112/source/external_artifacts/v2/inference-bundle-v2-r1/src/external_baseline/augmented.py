"""One fixed observation-augmentation experiment on external half-1 training."""

from collections import Counter
from contextlib import closing
import argparse
import importlib.metadata
import json
from pathlib import Path
import platform
import sqlite3
import time

from .contracts import FrameKey, SPLITS
from .features import FEATURE_NAMES
from .prepare import REPO, sha256, git_metadata, peak_memory_bytes
from .robustness import (SCENARIOS, SEED, stress_feature_matrices,
                         validate_frozen_pipeline, run_robustness)
from .temporal import decode_probabilities, _prediction_rows
from .training import (FEATURE_SETS, HGB_PARAMS, PACKAGES, load_split, fit_baseline,
                       predict_raw, project_features, evaluate_timeline,
                       comparison_entry, read_ready_manifest)

TRAIN_SEED = 2028


def build_training_pool(data, replay):
    """Return augmented (X14, labels, valid mask, audit), exclusively from half 1.

    Replay contains seven observation-only views, each already recomputed on its
    original timeline. Only retained frames with valid original DFL targets enter
    fitting; invalid targets are never manufactured or filled. Repeated frame
    IDs belong to separate views, not new matches. Every retained sample has
    equal weight; no class balancing or fitted preprocessing is introduced.
    """
    import numpy as np
    keys,stamps,x,y,valid=data
    replay_keys,replay_stamps,matrices,retained,audits=replay
    if not keys or any(k.period!=1 for k in keys):
        raise ValueError("augmentation fitting requires half 1 only")
    if keys!=replay_keys or stamps!=replay_stamps:
        raise ValueError("training observation/target timeline mismatch")
    if not np.array_equal(x,matrices["clean"],equal_nan=True):
        raise ValueError("clean training feature replay differs")
    xs,ys,views=[],[],{}
    for scenario in SCENARIOS:
        name=scenario["name"]
        keep=retained[name]
        if len(keep)!=len(keys) or matrices[name].shape!=x.shape:
            raise ValueError("training view shape mismatch")
        use=keep & valid
        xs.append(project_features(matrices[name][use],"no-signed-position"))
        ys.append(y[use])
        views[name]=dict(original_frames=len(keys),retained_frames=int(keep.sum()),
                        fitted_rows=int(use.sum()),excluded_invalid_retained=int((keep & ~valid).sum()),
                        target_class_counts=dict(Counter(y[use])),perturbation_audit=dict(audits[name]))
    pooled_x,pooled_y=np.concatenate(xs),np.concatenate(ys)
    return pooled_x,pooled_y,np.ones(len(pooled_y),dtype=bool),dict(
        source_period=1,unique_source_frames=len(keys),valid_source_frames=int(valid.sum()),
        fitted_rows=len(pooled_y),views=views,pooled_class_counts=dict(Counter(pooled_y)),
        clean_class_counts=dict(Counter(y[valid])),
        weighting="equal retained augmented sample; no per-frame reweighting or class balancing")


def _write_json(path,value):
    path.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")


def _write_predictions(path, results, decoded=False):
    """Write original clean frame keys; augmented copies are fitting rows only."""
    with closing(sqlite3.connect(path)) as db:
        extra="" if decoded else ",p_H REAL,p_A REAL,p_D REAL"
        db.execute(f"""CREATE TABLE predictions(match_id TEXT,period INTEGER,source_frame INTEGER,
            timestamp_us INTEGER,split TEXT,label TEXT{extra},
            PRIMARY KEY(match_id,period,source_frame)) WITHOUT ROWID""")
        for period,entry in results.items():
            keys,stamps,raw,probs,labels=entry
            if decoded:
                rows=((k.match_id,k.period,k.source_frame,int(s),SPLITS[period],str(label)) for k,s,label in zip(keys,stamps,labels))
                db.executemany("INSERT INTO predictions VALUES (?,?,?,?,?,?)",rows)
            else:
                rows=((k.match_id,k.period,k.source_frame,int(s),SPLITS[period],str(label),*map(float,p)) for k,s,label,p in zip(keys,stamps,raw,probs))
                db.executemany("INSERT INTO predictions VALUES (?,?,?,?,?,?,?,?,?)",rows)
        db.commit()


def _compare_stress(old,new):
    if set(old["scenarios"])!=set(new["scenarios"]):
        raise ValueError("reference stress scenario mismatch")
    result={}
    for name,entry in new["scenarios"].items():
        previous=old["scenarios"][name]
        for field in ("audit","input_frames","retained_frames","feature_coverage_on_retained_frames"):
            if previous[field]!=entry[field]:
                raise ValueError("stress observations/masks differ from reference")
        for field in ("n_graded","n_abstain_on_graded","n_gt_spells"):
            if previous["decoded_summary"][field]!=entry["decoded_summary"][field]:
                raise ValueError("stress evaluation target/coverage mismatch")
        a,b=previous["decoded_summary"],entry["decoded_summary"]
        result[name]=dict(original=a,augmented=b,
            delta_augmented_minus_original={k:b[k]-a[k] for k in ("spell_f1_mean","macro_f1","n_pred_spells")})
    return result


def run_augmented(observations,features,targets,classifier,decoder,reference_stress,output):
    """Fit exactly one augmented HGB, reuse identical decoder bytes, compare stress.

    Training view seed is 2028; existing validation stress seed remains 2027.
    HGB parameters/features/split are unchanged. Decoder estimation is never
    called. Validation labels are loaded after clean prediction/decoding; stress
    labels are used only by the frozen evaluation runner after all inference.
    All artifacts are new; parent models/data stay read-only. Root ready status
    requires successful fit, comparison and stress evaluation, with no promotion.
    """
    import joblib
    import numpy as np
    o,f,t,classifier,decoder,paths,cm,dm=validate_frozen_pipeline(observations,features,targets,classifier,decoder)
    if cm["config"]["hgb_params"]!=HGB_PARAMS or cm["config"].get("training_augmentation") is not None:
        raise ValueError("original non-augmented fixed HGB reference required")
    reference_stress=Path(reference_stress).resolve(strict=True)
    sm_path=reference_stress/"manifest.json"
    sm=read_ready_manifest(sm_path)
    if sm.get("robustness_version")!=1 or sm["protocol"]["period"]!=2 or sm["protocol"]["seed"]!=SEED or sm["protocol"]["scenarios"]!=list(SCENARIOS):
        raise ValueError("original fixed validation stress protocol required")
    expected={str(v):sha256(v) for v in paths}
    if sm["inputs_sha256"]!=expected:
        raise ValueError("reference stress pipeline/input provenance differs")
    paths.append(sm_path)
    for name,digest in sm["outputs_sha256"].items():
        if name not in ("protocol.json","predictions.sqlite","robustness_report.json") or sha256(reference_stress/name)!=digest:
            raise ValueError("reference stress artifact hash mismatch")
        paths.append(reference_stress/name)
    output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter()
    try:
        hashes={str(v):sha256(v) for v in paths}
        sources={str(v.relative_to(REPO)):sha256(v) for v in sorted((REPO/"external_baseline").glob("*.py"))}
        sources["evaluation/possession_metrics.py"]=sha256(REPO/"evaluation/possession_metrics.py")
        protocol=dict(version=1,training_period=1,validation_period=2,training_seed=TRAIN_SEED,
                      validation_stress_seed=SEED,views=SCENARIOS,
                      weighting="one equal-weight sample per retained valid frame per view",
                      model_features=FEATURE_SETS["no-signed-position"],hgb_params=HGB_PARAMS,
                      decoder="reuse byte-identical original parameter JSON; no estimation",
                      selection="one experiment motivated by observed external stress failures; no sweep, untouched-test claim or automatic model promotion")
        _write_json(output/"protocol.json",protocol)
        train_data=load_split(f,t,1)
        replay=stress_feature_matrices(o,period=1,seed=TRAIN_SEED)
        x,y,valid,audit=build_training_pool(train_data,replay)
        _write_json(output/"training_audit.json",audit)
        model=fit_baseline(x,y,valid)
        # Release augmented matrices before validation stress allocates its views.
        del x,y,valid,replay
        raw_dir,decoded_dir=output/"classifier",output/"decoder"
        raw_dir.mkdir()
        decoded_dir.mkdir()
        config=dict(cm["config"])
        config.update(training_augmentation=protocol,selection=protocol["selection"])
        _write_json(raw_dir/"config.json",config)
        joblib.dump(dict(model=model,feature_names=FEATURE_SETS["no-signed-position"],config=config),raw_dir/"model.joblib",compress=3)
        parameter_bytes=(decoder/"decoder_parameters.json").read_bytes()
        (decoded_dir/"decoder_parameters.json").write_bytes(parameter_bytes)
        parameters=json.loads(parameter_bytes)
        decoder_config=dict(dm["config"])
        decoder_config.update(selection="one augmentation experiment; byte-identical original decoder parameters")
        _write_json(decoded_dir/"config.json",decoder_config)
        results={}
        for period in (1,2):
            if period==1:
                keys,stamps,clean_x=train_data[:3]
            else:
                with closing(sqlite3.connect(f.as_uri()+"?mode=ro",uri=True)) as db:
                    rows=db.execute("SELECT match_id,period,source_frame,timestamp_us,"+",".join(FEATURE_NAMES)+" FROM features WHERE period=2 ORDER BY match_id,period,source_frame").fetchall()
                keys=[FrameKey(*r[:3]) for r in rows]
                stamps=[r[3] for r in rows]
                clean_x=np.asarray([r[4:] for r in rows],dtype=float)
            raw,probs=predict_raw(model,project_features(clean_x,"no-signed-position"))
            decoded=decode_probabilities(keys,stamps,probs,parameters)
            results[period]=(keys,stamps,raw,probs,decoded)
        val_data=load_split(f,t,2)
        if results[2][0]!=val_data[0] or results[2][1]!=val_data[1]:
            raise ValueError("validation target/prediction timeline mismatch")
        _write_predictions(raw_dir/"predictions.sqlite",results)
        _write_predictions(decoded_dir/"predictions.sqlite",results,decoded=True)
        raw_metrics,decoded_metrics,clean_comparison={},{},{}
        for period,data in ((1,train_data),(2,val_data)):
            keys,stamps,clean_x,labels,valid=data
            raw,decoded=results[period][2],results[period][4]
            rm=evaluate_timeline(keys,stamps,labels,valid,raw)
            vm=evaluate_timeline(keys,stamps,labels,valid,decoded)
            raw_metrics[SPLITS[period]]=dict(metrics=rm,target_valid=int(valid.sum()),target_invalid=int((~valid).sum()))
            decoded_metrics[SPLITS[period]]=dict(raw=rm,decoded=vm)
            original=_prediction_rows((classifier/"predictions.sqlite").resolve(),period)
            if original[0]!=keys or original[1]!=stamps:
                raise ValueError("original prediction timeline mismatch")
            original_decoded=decode_probabilities(keys,stamps,original[3],parameters)
            om=evaluate_timeline(keys,stamps,labels,valid,original_decoded)
            clean_comparison[SPLITS[period]]=dict(original=comparison_entry(data,original_decoded,om),
                                                augmented=comparison_entry(data,decoded,vm))
        raw_metrics.update(augmentation=audit,iterations=int(model.n_iter_),early_stopping_used=bool(model.do_early_stopping_))
        _write_json(raw_dir/"metrics.json",raw_metrics)
        _write_json(decoded_dir/"metrics.json",decoded_metrics)
        packages={p:importlib.metadata.version(p) for p in PACKAGES}
        common=dict(status="ready",contract_version=1,source_sha256=sources,git=git_metadata(),
                    python=platform.python_version(),packages=packages,
                    provenance=dict(parent=cm.get("provenance",{}),experiment=protocol["selection"],
                        label_source="unchanged original external targets for each retained half-1 observation view",
                        decoder_note="unchanged original training occupancy prior; augmented sample class proportions may differ slightly due to frame-gap removal"))
        raw_manifest=dict(common,training_version=1,config=config,
                          inputs_sha256={**hashes,str(output/"protocol.json"):sha256(output/"protocol.json")},
                          outputs_sha256={name:sha256(raw_dir/name) for name in ("config.json","model.joblib","predictions.sqlite","metrics.json")})
        _write_json(raw_dir/"manifest.json",raw_manifest)
        decoder_manifest=dict(common,decoder_version=1,config=decoder_config,numpy=packages["numpy"],
                              inputs_sha256={**hashes,str(raw_dir/"predictions.sqlite"):sha256(raw_dir/"predictions.sqlite"),str(raw_dir/"manifest.json"):sha256(raw_dir/"manifest.json")},
                              frozen_parameters_source=str(decoder/"decoder_parameters.json"),
                              outputs_sha256={name:sha256(decoded_dir/name) for name in ("config.json","decoder_parameters.json","predictions.sqlite","metrics.json")})
        _write_json(decoded_dir/"manifest.json",decoder_manifest)
        stress=run_robustness(o,f,t,raw_dir,decoded_dir,output/"stress")
        previous=json.loads((reference_stress/"robustness_report.json").read_text(encoding="utf-8"))
        comparison=dict(clean_splits=clean_comparison,stress=_compare_stress(previous,stress),
                        interpretation="One augmented model and unchanged decoder, evaluated on reused development clean/stress validation. Protocol was designed after earlier stress failures; this is not an untouched external-match test.")
        _write_json(output/"comparison.json",comparison)
        if (decoded_dir/"decoder_parameters.json").read_bytes()!=parameter_bytes:
            raise ValueError("frozen decoder parameters changed")
        if any(sha256(Path(v))!=h for v,h in hashes.items()) or any(sha256(REPO/v)!=h for v,h in sources.items()):
            raise ValueError("input/source changed during augmentation experiment")
        outputs={str(v.relative_to(output)):sha256(v) for v in sorted(output.rglob("*")) if v.is_file()}
        manifest=dict(status="ready",contract_version=1,augmentation_version=1,protocol=protocol,
                      inputs_sha256=hashes,source_sha256=sources,outputs_sha256=outputs,
                      git=git_metadata(),python=platform.python_version(),packages=packages,
                      elapsed_seconds=round(time.perf_counter()-started,3),process_peak_resident_bytes=peak_memory_bytes(),
                      provenance=common["provenance"])
        _write_json(output/"manifest.json",manifest)
        return comparison
    except Exception as error:
        _write_json(output/"FAILED.json",dict(status="failed",error=str(error)))
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ("observations","features","targets","classifier","decoder","reference-stress","output"):
        parser.add_argument("--"+name,required=True,type=Path)
    args=parser.parse_args()
    comparison=run_augmented(args.observations,args.features,args.targets,args.classifier,args.decoder,args.reference_stress,args.output)
    print(json.dumps({name:{variant:{k:v[variant][k] for k in ("spell_f1_mean","macro_f1")} for variant in ("original","augmented")} for name,v in comparison["stress"].items()},indent=2))


if __name__=="__main__":
    main()
