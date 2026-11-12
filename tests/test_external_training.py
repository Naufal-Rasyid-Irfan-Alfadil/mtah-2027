"""Synthetic fitting and manual metric examples; never discover real datasets/GT."""

from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from external_baseline.contracts import FrameKey
from external_baseline.features import FEATURE_NAMES, FEATURE_UNITS, FrameFeatureExtractor, EntityPosition
from external_baseline.prepare import sha256
from external_baseline.training import (HGB_PARAMS, evaluate_timeline, fit_baseline,
                                        FEATURE_SETS, comparison_entry, load_split,
                                        predict_raw, project_features, train)


def make_fixture(root):
    prepared, feature_dir = root/"prepared", root/"features"
    prepared.mkdir()
    feature_dir.mkdir()
    (prepared/"manifest.json").write_text(json.dumps({"status":"ready","contract_version":1,"provenance":{"source":"synthetic"}}),encoding="utf-8")
    target_path, feature_path = prepared/"targets.sqlite", feature_dir/"features.sqlite"
    with closing(sqlite3.connect(target_path)) as t, closing(sqlite3.connect(feature_path)) as f:
        t.execute("CREATE TABLE targets(match_id TEXT,period INTEGER,source_frame INTEGER,label TEXT,valid_target INTEGER,PRIMARY KEY(match_id,period,source_frame))")
        f.execute(f"CREATE TABLE features(match_id TEXT,period INTEGER,source_frame INTEGER,timestamp_us INTEGER,split TEXT,{','.join(n+' REAL' for n in FEATURE_NAMES)},PRIMARY KEY(match_id,period,source_frame))")
        f.execute("CREATE TABLE feature_metadata(json TEXT)")
        f.execute("INSERT INTO feature_metadata VALUES (?)",(json.dumps({"feature_version":1,"feature_names":FEATURE_NAMES,"units":FEATURE_UNITS}),))
        for period, count, split in ((1,90,"train"),(2,60,"validation")):
            extractor = FrameFeatureExtractor(105,68)
            rows, targets = [], []
            for n in range(count):
                label = ("H","A","D")[n%3]
                key = FrameKey("synthetic",period,100+n)
                values = extractor.extract(key,n*40000,[EntityPosition("BALL","BALL",(n%3-1)*30,0),EntityPosition("h","H",-30,0),EntityPosition("a","A",30,0)])
                # Invalid target remains a frame, and first-row speed remains NaN.
                targets.append((key.match_id,period,key.source_frame,label if n!=7 else None,int(n!=7)))
                rows.append((key.match_id,period,key.source_frame,n*40000,split,*values.values()))
            f.executemany(f"INSERT INTO features VALUES({','.join('?' for _ in rows[0])})", reversed(rows))
            t.executemany("INSERT INTO targets VALUES(?,?,?,?,?)", reversed(targets))
        f.commit()
        t.commit()
    (feature_dir/"manifest.json").write_text(json.dumps({"status":"ready","contract_version":1,"feature_version":1,"feature_names":FEATURE_NAMES,"input":{"parent_manifest_sha256":sha256(prepared/"manifest.json")},"output_sha256":sha256(feature_path)}),encoding="utf-8")
    return feature_path,target_path


class TrainingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global np
        try:
            import numpy as np
            import sklearn
            import joblib
        except ImportError as error:
            raise unittest.SkipTest("optional training dependencies unavailable") from error

    def test_key_join_missing_and_valid_mask(self):
        with tempfile.TemporaryDirectory() as folder:
            f,t=make_fixture(Path(folder))
            keys,stamps,x,y,valid=load_split(f,t,1)
            self.assertEqual(len(keys),90)
            self.assertEqual((keys[0].source_frame,keys[-1].source_frame),(100,189))
            self.assertTrue(np.isnan(x[0,FEATURE_NAMES.index("ball_speed_mps")]))
            self.assertEqual(x.shape,(90,16))
            self.assertFalse(valid[7])
            self.assertIsNone(y[7])
            self.assertEqual(sum(valid),89)
            with closing(sqlite3.connect(t)) as db:
                db.execute("DELETE FROM targets WHERE period=1 AND source_frame=107")
                db.commit()
            with self.assertRaisesRegex(ValueError,"keys"):
                load_split(f,t,1)

    def test_fit_uses_only_valid_training_and_no_early_stopping(self):
        with tempfile.TemporaryDirectory() as folder:
            f,t=make_fixture(Path(folder))
            _,_,x,y,valid=load_split(f,t,1)
            model=fit_baseline(x,y,valid)
            self.assertFalse(model.do_early_stopping_)
            self.assertEqual(model.n_iter_,100)
            self.assertEqual(model.n_features_in_,16)
            self.assertEqual(model.get_params(),HGB_PARAMS)
            # Invalid label content cannot affect fitting.
            y[7]="invalid sentinel"
            other=fit_baseline(x,y,valid)
            np.testing.assert_array_equal(predict_raw(model,x)[1],predict_raw(other,x)[1])
            no_away=valid & (y!="A")
            with self.assertRaises(ValueError):
                fit_baseline(x,y,no_away)

    def test_manual_confusion_and_perfect_spells(self):
        keys=[FrameKey("synthetic",2,n) for n in range(10,16)]
        y=np.array(["H","H","D","D","A","A"],dtype=object)
        result=evaluate_timeline(keys,[i*40000 for i in range(6)],y,[True]*6,y)
        self.assertEqual(result["spell_f1_mean"],1)
        self.assertEqual(result["macro_f1"],1)
        self.assertEqual(result["n_gt_spells"],2)
        self.assertEqual(result["transitions"][12]["n_matched"],2)
        # One missed A frame: A precision=1, recall=1/2, F1=2/3.
        pred=y.copy()
        pred[-1]="D"
        result=evaluate_timeline(keys,[i*40000 for i in range(6)],y,[True]*6,pred)
        self.assertAlmostEqual(result["per_class"]["A"]["f1"],2/3)
        self.assertEqual(result["confusion"][1][2],1)

    def test_gaps_invalid_and_half_boundaries_never_merge_spells(self):
        keys=[FrameKey("synthetic",1,n) for n in (10,11,14,15)]+[FrameKey("synthetic",2,10)]
        y=["H","H",None,"H","H"]
        result=evaluate_timeline(keys,[0,40000,160000,200000,0],y,[True,True,False,True,True],["H"]*5)
        self.assertEqual(result["observed_frames"],5)
        self.assertEqual(result["evaluation_lattice_frames"],8)  # two missing N + period separator
        self.assertEqual(result["n_graded"],4)
        self.assertEqual(result["valid_contiguous_runs"],3)
        self.assertEqual(result["n_gt_spells"],3)
        self.assertEqual(result["spell_f1_mean"],1)

    def test_transition_matching_cannot_cross_short_invalid_gap(self):
        keys=[FrameKey("synthetic",2,n) for n in range(7)]
        # A GT transition in run 1 and a prediction transition in run 2 would
        # wrongly match at tolerance 12 if all transition lists were pooled.
        result=evaluate_timeline(keys,[n*40000 for n in range(7)],
            ["H","A","A",None,"H","H","H"],[1,1,1,0,1,1,1],
            ["H","H","H","D","H","A","A"])
        self.assertEqual(result["transitions"][12]["n_matched"],0)
        self.assertEqual(result["transitions"][12]["n_missed"],1)
        self.assertEqual(result["transitions"][12]["n_spurious"],1)

    def test_timestamp_discontinuity_and_empty_evaluation(self):
        keys=[FrameKey("synthetic",2,n) for n in (10,11)]
        result=evaluate_timeline(keys,[0,80000],["H","A"],[True]*2,["H","A"])
        self.assertEqual(result["valid_contiguous_runs"],2)
        self.assertEqual(result["transitions"][12]["n_gt"],0)
        with self.assertRaises(ValueError):
            evaluate_timeline(keys,[0,40000],[None,None],[False]*2,["H","A"])

    def test_end_to_end_roundtrip_and_validation_labels_do_not_affect_fit(self):
        import joblib
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            f,t=make_fixture(root)
            before=sha256(f)
            with patch("external_baseline.training.git_metadata",return_value={"commit":"synthetic"}):
                report=train(f,t,root/"one")
                with closing(sqlite3.connect(t)) as db:
                    db.execute("UPDATE targets SET label='D' WHERE period=2 AND valid_target=1")
                    db.commit()
                train(f,t,root/"two")
            self.assertEqual(sha256(f),before)
            a,b=(joblib.load(root/p/"model.joblib") for p in ("one","two"))
            x=load_split(f,t,1)[2]
            np.testing.assert_array_equal(predict_raw(a["model"],x)[1],predict_raw(b["model"],x)[1])
            self.assertEqual(sha256(root/"one"/"predictions.sqlite"),sha256(root/"two"/"predictions.sqlite"))
            self.assertEqual(report["splits"]["train"]["target_valid"],89)
            self.assertEqual(report["splits"]["validation"]["target_invalid"],1)
            with closing(sqlite3.connect(root/"one"/"predictions.sqlite")) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM predictions").fetchone()[0],150)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM predictions WHERE period=2 AND source_frame=107").fetchone()[0],1)
            with self.assertRaises(FileExistsError):
                train(f,t,root/"one")

    def test_lineage_mismatch_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            f,t=make_fixture(root)
            (t.parent/"manifest.json").write_text(json.dumps({"status":"ready","contract_version":1,"different":True}))
            with self.assertRaisesRegex(ValueError,"lineage"):
                train(f,t,root/"failed")

    def test_ablation_projection_drops_only_signed_xy_and_retains_nan(self):
        x=np.arange(48,dtype=float).reshape(3,16)
        x[0,6]=np.nan
        before=x.copy()
        expected=x[:,[0,1,2,3,6,7,8,9,10,11,12,13,14,15]]
        projected=project_features(x,"no-signed-position")
        np.testing.assert_array_equal(projected,expected)
        np.testing.assert_array_equal(x,before)
        x[:,4:6]*=-1000
        np.testing.assert_array_equal(project_features(x,"no-signed-position"),projected)
        self.assertEqual(len(FEATURE_SETS["all16"]),16)
        self.assertEqual(len(FEATURE_SETS["no-signed-position"]),14)
        with self.assertRaises(ValueError):
            project_features(x,"unknown")
        with self.assertRaises(ValueError):
            project_features(projected,"no-signed-position")

    def test_ablation_roundtrip_reference_unchanged_and_model_order(self):
        import joblib
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            f,t=make_fixture(root)
            baseline=train(f,t,root/"baseline")
            tracked=(f,t,root/"baseline"/"model.joblib",root/"baseline"/"predictions.sqlite",root/"baseline"/"manifest.json")
            hashes=[sha256(p) for p in tracked]
            variant=train(f,t,root/"ablation","no-signed-position",root/"baseline")
            self.assertEqual([sha256(p) for p in tracked],hashes)
            saved=joblib.load(root/"ablation"/"model.joblib")
            self.assertEqual(saved["feature_names"],FEATURE_SETS["no-signed-position"])
            self.assertEqual(saved["model"].n_features_in_,14)
            self.assertEqual(saved["model"].get_params(),HGB_PARAMS)
            self.assertFalse(variant["early_stopping_used"])
            comparison=json.loads((root/"ablation"/"comparison.json").read_text())
            for split,period in (("train",1),("validation",2)):
                data=load_split(f,t,period)
                labels,probs=predict_raw(saved["model"],project_features(data[2],"no-signed-position"))
                with closing(sqlite3.connect(root/"ablation"/"predictions.sqlite")) as db:
                    rows=db.execute("SELECT label,p_H,p_A,p_D FROM predictions WHERE period=? ORDER BY match_id,period,source_frame",(period,)).fetchall()
                np.testing.assert_array_equal(labels,[row[0] for row in rows])
                np.testing.assert_array_equal(probs,[row[1:] for row in rows])
                c=comparison["splits"][split]
                self.assertEqual(c["baseline16"]["spell_f1_mean"],baseline["splits"][split]["metrics"]["spell_f1_mean"])
                self.assertEqual(c["ablation14"]["macro_f1"],variant["splits"][split]["metrics"]["macro_f1"])
                self.assertEqual(c["delta_ablation_minus_baseline"]["HA_swaps"],c["ablation14"]["HA_swaps"]-c["baseline16"]["HA_swaps"])
            manifest=json.loads((root/"ablation"/"manifest.json").read_text())
            self.assertEqual(sha256(root/"ablation"/"comparison.json"),manifest["outputs_sha256"]["comparison.json"])
            with self.assertRaises(FileExistsError):
                train(f,t,root/"ablation","no-signed-position",root/"baseline")

    def test_ablation_geometry_reflection_retains_remaining_features(self):
        a,b=FrameFeatureExtractor(105,68),FrameFeatureExtractor(105,68)
        for i in range(2):
            key=FrameKey("synthetic",1,10+i)
            entities=[EntityPosition("BALL","BALL",1+i*.12,2+i*.16),
                      EntityPosition("h","H",-3,4),EntityPosition("a","A",6,-8)]
            reflected=[EntityPosition(e.entity_id,e.team,-e.x_m,-e.y_m) for e in entities]
            old=np.asarray([list(a.extract(key,i*40000,entities).values())],dtype=float)
            new=np.asarray([list(b.extract(key,i*40000,reflected).values())],dtype=float)
            self.assertNotEqual(old[0,4],new[0,4])
            np.testing.assert_array_equal(project_features(old,"no-signed-position"),project_features(new,"no-signed-position"))

    def test_ablation_requires_matching_reference_and_fixed_parameters(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            f,t=make_fixture(root)
            with self.assertRaisesRegex(ValueError,"reference"):
                train(f,t,root/"missing","no-signed-position")
            train(f,t,root/"baseline")
            with self.assertRaisesRegex(ValueError,"reference"):
                train(f,t,root/"bad-default",reference=root/"baseline")
            manifest_path=root/"baseline"/"manifest.json"
            manifest=json.loads(manifest_path.read_text())
            manifest["config"]["hgb_params"]["max_iter"]=99
            manifest_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,"matching"):
                train(f,t,root/"changed","no-signed-position",root/"baseline")

    def test_comparison_switch_count_respects_gaps_and_invalid_targets(self):
        keys=[FrameKey("synthetic",1,n) for n in (10,11,14,15,16)]
        data=(keys,[0,40000,160000,200000,240000],np.zeros((5,16)),
              np.array(["H","H","H",None,"H"],dtype=object),np.array([1,1,1,0,1],dtype=bool))
        pred=np.array(["H","A","H","A","H"])
        metrics=evaluate_timeline(keys,data[1],data[3],data[4],pred)
        summary=comparison_entry(data,pred,metrics)
        self.assertEqual(summary["HA_swaps"],1)
        self.assertEqual(summary["HA_switches_inside_true_possession"],1)

    def test_import_and_help_do_not_load_dependencies_or_data(self):
        script='''import sys,runpy
def audit(event,args):
    if event in ('open','sqlite3.connect'):
        p=str(args[0]).replace(chr(92),'/').lower()
        if p.endswith(('.sqlite','.xml','.csv','.mp4','.joblib')) or '/data/' in p:
            raise RuntimeError('unexpected dataset access '+p)
sys.addaudithook(audit)
import external_baseline.training
assert not any(m in sys.modules for m in ('sklearn','numpy','pandas','joblib'))
sys.argv=['training','--help']
runpy.run_module('external_baseline.training',run_name='__main__')
'''
        result=subprocess.run([sys.executable,"-B","-c",script],capture_output=True,text=True,cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode,0,result.stderr)


if __name__ == "__main__":
    unittest.main()
