"""Snapshot two fixed candidates, then evaluate a distinct external match once."""

import argparse
from contextlib import closing
import importlib.metadata
import json
from pathlib import Path
import shutil
import sqlite3
import time

from .contracts import FrameKey
from .features import FEATURE_NAMES, FEATURE_UNITS
from .prepare import REPO, sha256, git_metadata, peak_memory_bytes
from .temporal import decode_probabilities
from .training import (FEATURE_SETS, PACKAGES, HGB_PARAMS, read_ready_manifest,
                       load_split, project_features, predict_raw, evaluate_timeline)

DEVELOPMENT_MATCHES = ("DFL-MAT-J03WOH",)
PRIMARY = "augmented"


def _json(path,value):
    path.write_text(json.dumps(value,indent=2,sort_keys=True,allow_nan=False)+"\n",encoding="utf-8")


def freeze(original_classifier,original_decoder,augmented_classifier,augmented_decoder,
           test_match,output,confirm_unused=False):
    """Copy both model/parameter pairs and lock a protocol before new target access.

    No observation/target labels or metrics are parsed; existing prediction bytes
    are hashed only for candidate lineage. Confirmed unused history is required
    for evaluation, not inferred from absent local files or a fresh repository.
    A pending snapshot can be reviewed but cannot evaluate. The primary candidate
    is fixed as augmented, based on earlier external stress work, not test scores.
    No automatic winner selection, refitting or parameter changes are supported.
    """
    if not test_match or test_match in DEVELOPMENT_MATCHES:
        raise ValueError("a distinct external match is required")
    output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    try:
        candidates={}
        source_hashes={}
        for name,c,d in (("original",original_classifier,original_decoder),("augmented",augmented_classifier,augmented_decoder)):
            c,d=Path(c).resolve(strict=True),Path(d).resolve(strict=True)
            cm,dm=read_ready_manifest(c/"manifest.json"),read_ready_manifest(d/"manifest.json")
            config=cm["config"]
            if config["feature_names"]!=list(FEATURE_SETS["no-signed-position"]) or config["hgb_params"]!=HGB_PARAMS or config.get("decoder") is not None:
                raise ValueError("matching fixed raw14 candidate required")
            if (config.get("training_augmentation") is not None)!=(name=="augmented"):
                raise ValueError("candidate augmentation identity mismatch")
            if cm.get("packages")!={p:importlib.metadata.version(p) for p in PACKAGES}:
                raise ValueError("candidate runtime versions differ")
            if dm["inputs_sha256"].get(str(c/"manifest.json"))!=sha256(c/"manifest.json") or dm["inputs_sha256"].get(str(c/"predictions.sqlite"))!=sha256(c/"predictions.sqlite"):
                raise ValueError("classifier/decoder lineage mismatch")
            target=output/name
            target.mkdir()
            for directory,manifest,file in ((c,cm,"model.joblib"),(d,dm,"decoder_parameters.json")):
                path=directory/file
                if sha256(path)!=manifest["outputs_sha256"][file]:
                    raise ValueError("candidate artifact hash mismatch")
                source_hashes[str(path)]=sha256(path)
                source_hashes[str(directory/"manifest.json")]=sha256(directory/"manifest.json")
                shutil.copyfile(path,target/file)
            candidates[name]=dict(model_file=f"{name}/model.joblib",model_sha256=sha256(target/"model.joblib"),
                parameters_file=f"{name}/decoder_parameters.json",parameters_sha256=sha256(target/"decoder_parameters.json"),
                feature_names=config["feature_names"],hgb_params=config["hgb_params"],
                training_provenance=cm.get("provenance",{}))
        if candidates["original"]["parameters_sha256"]!=candidates["augmented"]["parameters_sha256"]:
            raise ValueError("both candidates must reuse the same decoder parameters")
        if any(sha256(Path(p))!=h for p,h in source_hashes.items()):
            raise ValueError("candidate source changed while freezing")
        code_hashes={str(p.relative_to(REPO)):sha256(p) for p in sorted((REPO/"external_baseline").glob("*.py"))}
        code_hashes["evaluation/possession_metrics.py"]=sha256(REPO/"evaluation/possession_metrics.py")
        protocol=dict(status="ready",contract_version=1,holdout_version=1,test_match=test_match,
            development_matches=DEVELOPMENT_MATCHES,primary=PRIMARY,candidates=candidates,
            history_confirmed_unused=bool(confirm_unused),
            history_basis="explicit user confirmation required, not filesystem absence",
            evaluation="both halves are test; source parser split names do not authorize training",
            policy="no fitting/tuning/automatic winner selection; if used for model selection or further tuning, reclassify this match as development",
            inputs_sha256=source_hashes,packages={p:importlib.metadata.version(p) for p in PACKAGES},
            source_sha256=code_hashes,git=git_metadata())
        _json(output/"protocol.json",protocol)
        return protocol
    except Exception as error:
        _json(output/"FAILED.json",dict(status="failed",error=str(error)))
        raise


def evaluate(protocol_path,features,targets,output):
    """Evaluate frozen candidates on full external match, without fitting.

    Match identity must differ from J03WOH and equal the predeclared match ID.
    Original keys/time, metre features and gaps stay intact. Both model pairs
    predict/decode both halves before any test labels/masks are loaded. Targets
    then join by full keys; ambiguous GT remains unscored. Outputs use split=test
    for both halves, irrespective of the parser's historical train/validation
    bookkeeping. No automatic candidate promotion is made from these scores.
    """
    import joblib
    import numpy as np
    protocol_path=Path(protocol_path).resolve(strict=True)
    protocol=json.loads(protocol_path.read_text(encoding="utf-8"))
    if protocol.get("status")!="ready" or protocol.get("holdout_version")!=1 or not protocol.get("history_confirmed_unused"):
        raise ValueError("ready protocol with explicit confirmed-unused history required")
    if protocol["test_match"] in DEVELOPMENT_MATCHES or protocol["primary"]!=PRIMARY or set(protocol["candidates"])!={"original","augmented"}:
        raise ValueError("invalid frozen holdout identity/candidate protocol")
    if protocol["packages"]!={p:importlib.metadata.version(p) for p in PACKAGES}:
        raise ValueError("frozen runtime versions differ")
    if not protocol.get("source_sha256") or any(sha256(REPO/p)!=h for p,h in protocol["source_sha256"].items()):
        raise ValueError("frozen pipeline source changed; a new pre-test protocol is required")
    f,t=Path(features).resolve(strict=True),Path(targets).resolve(strict=True)
    if f.name!="features.sqlite" or t.name!="targets.sqlite":
        raise ValueError("explicit external feature/target files required")
    fm_path,tm_path=f.parent/"manifest.json",t.parent/"manifest.json"
    fm,tm=read_ready_manifest(fm_path),read_ready_manifest(tm_path)
    if fm["input"]["parent_manifest_sha256"]!=sha256(tm_path) or fm["output_sha256"]!=sha256(f):
        raise ValueError("test preparation lineage/hash mismatch")
    files=[protocol_path,f,t,fm_path,tm_path]
    for candidate in protocol["candidates"].values():
        for field,digest in (("model_file","model_sha256"),("parameters_file","parameters_sha256")):
            relative=Path(candidate[field])
            if relative.is_absolute() or ".." in relative.parts:
                raise ValueError("snapshot artifact must stay within protocol directory")
            path=protocol_path.parent/relative
            if sha256(path)!=candidate[digest]:
                raise ValueError("frozen candidate hash mismatch")
            files.append(path)
    output=Path(output).resolve()
    output.mkdir(parents=True,exist_ok=False)
    started=time.perf_counter()
    try:
        inputs={str(p):sha256(p) for p in files}
        sources={str(p.relative_to(REPO)):sha256(p) for p in sorted((REPO/"external_baseline").glob("*.py"))}
        sources["evaluation/possession_metrics.py"]=sha256(REPO/"evaluation/possession_metrics.py")
        halves={}
        with closing(sqlite3.connect(f.as_uri()+"?mode=ro",uri=True)) as db:
            meta=[json.loads(r[0]) for r in db.execute("SELECT json FROM feature_metadata")]
            if len(meta)!=1 or meta[0]["feature_names"]!=list(FEATURE_NAMES) or meta[0]["units"]!=FEATURE_UNITS:
                raise ValueError("test feature contract mismatch")
            if [r[0] for r in db.execute("SELECT DISTINCT period FROM features ORDER BY period")]!=[1,2]:
                raise ValueError("test must contain both halves")
            for period in (1,2):
                rows=db.execute("SELECT match_id,period,source_frame,timestamp_us,"+",".join(FEATURE_NAMES)+" FROM features WHERE period=? ORDER BY match_id,period,source_frame",(period,)).fetchall()
                keys=[FrameKey(*r[:3]) for r in rows]
                if not keys or any(k.match_id!=protocol["test_match"] for k in keys):
                    raise ValueError("test match differs from predeclared protocol")
                halves[period]=(keys,[r[3] for r in rows],np.asarray([r[4:] for r in rows],dtype=float))
        predictions={}
        for name,candidate in protocol["candidates"].items():
            artifact=joblib.load(protocol_path.parent/candidate["model_file"])
            if tuple(artifact["feature_names"])!=FEATURE_SETS["no-signed-position"] or artifact["model"].get_params()!=HGB_PARAMS:
                raise ValueError("snapshot model feature/parameter contract mismatch")
            parameters=json.loads((protocol_path.parent/candidate["parameters_file"]).read_text())
            predictions[name]={}
            for period,(keys,stamps,x) in halves.items():
                raw,probs=predict_raw(artifact["model"],project_features(x,"no-signed-position"))
                decoded=decode_probabilities(keys,stamps,probs,parameters)
                predictions[name][period]=(raw,probs,decoded)
        # Test labels are first loaded after every candidate/half was inferred.
        data={period:load_split(f,t,period) for period in (1,2)}
        for period,(keys,stamps,x,y,valid) in data.items():
            if keys!=halves[period][0] or stamps!=halves[period][1] or not np.array_equal(x,halves[period][2],equal_nan=True):
                raise ValueError("test target/feature timeline changed")
        report=dict(match_id=protocol["test_match"],primary=protocol["primary"],candidates={},
                    interpretation="One comparative external holdout, both halves; no fitting or automatic selection. Reuse for tuning/model selection changes its status to development.")
        with closing(sqlite3.connect(output/"predictions.sqlite")) as db:
            db.execute("""CREATE TABLE predictions(candidate TEXT,match_id TEXT,period INTEGER,source_frame INTEGER,
                timestamp_us INTEGER,split TEXT,raw_label TEXT,decoded_label TEXT,p_H REAL,p_A REAL,p_D REAL,
                PRIMARY KEY(candidate,match_id,period,source_frame)) WITHOUT ROWID""")
            for name,parts in predictions.items():
                per_half={}
                for period,(raw,probs,decoded) in parts.items():
                    keys,stamps,x,y,valid=data[period]
                    per_half[str(period)]={"raw":evaluate_timeline(keys,stamps,y,valid,raw),"decoded":evaluate_timeline(keys,stamps,y,valid,decoded)}
                    db.executemany("INSERT INTO predictions VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                        ((name,k.match_id,k.period,k.source_frame,int(s),"test",str(a),str(b),*map(float,p))
                         for k,s,a,b,p in zip(keys,stamps,raw,decoded,probs)))
                keys=data[1][0]+data[2][0]
                stamps=data[1][1]+data[2][1]
                y=np.concatenate([data[p][3] for p in (1,2)])
                valid=np.concatenate([data[p][4] for p in (1,2)])
                raw=np.concatenate([parts[p][0] for p in (1,2)])
                decoded=np.concatenate([parts[p][2] for p in (1,2)])
                overall={"raw":evaluate_timeline(keys,stamps,y,valid,raw),"decoded":evaluate_timeline(keys,stamps,y,valid,decoded)}
                report["candidates"][name]=dict(per_half=per_half,overall=overall,observed_frames=len(keys),valid_targets=int(valid.sum()))
            db.commit()
        _json(output/"metrics.json",report)
        if any(sha256(Path(p))!=h for p,h in inputs.items()) or any(sha256(REPO/p)!=h for p,h in sources.items()):
            raise ValueError("input/source changed during holdout evaluation")
        _json(output/"manifest.json",dict(status="ready",contract_version=1,holdout_version=1,
            test_match=protocol["test_match"],primary=protocol["primary"],history_confirmed_unused=True,
            inputs_sha256=inputs,source_sha256=sources,packages=protocol["packages"],git=git_metadata(),
            outputs_sha256={name:sha256(output/name) for name in ("predictions.sqlite","metrics.json")},
            elapsed_seconds=round(time.perf_counter()-started,3),process_peak_resident_bytes=peak_memory_bytes(),
            test_status="Consumed for reporting these frozen candidates only. No automatic model promotion or official inference freeze."))
        return report
    except Exception as error:
        _json(output/"FAILED.json",dict(status="failed",error=str(error)))
        raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    commands=parser.add_subparsers(dest="command",required=True)
    freeze_parser=commands.add_parser("freeze")
    for name in ("original-classifier","original-decoder","augmented-classifier","augmented-decoder","output"):
        freeze_parser.add_argument("--"+name,required=True,type=Path)
    freeze_parser.add_argument("--test-match",required=True)
    freeze_parser.add_argument("--confirm-unused",action="store_true",help="explicit user-confirmed unused external match history")
    evaluate_parser=commands.add_parser("evaluate")
    for name in ("protocol","features","targets","output"):
        evaluate_parser.add_argument("--"+name,required=True,type=Path)
    args=parser.parse_args()
    if args.command=="freeze":
        protocol=freeze(args.original_classifier,args.original_decoder,args.augmented_classifier,args.augmented_decoder,args.test_match,args.output,args.confirm_unused)
        print(json.dumps({"protocol":str(args.output/"protocol.json"),"primary":protocol["primary"],"history_confirmed_unused":protocol["history_confirmed_unused"]},indent=2))
    else:
        report=evaluate(args.protocol,args.features,args.targets,args.output)
        print(json.dumps({name:{k:v["overall"]["decoded"][k] for k in ("spell_f1_mean","macro_f1","n_pred_spells","n_gt_spells")} for name,v in report["candidates"].items()},indent=2))


if __name__=="__main__":
    main()
