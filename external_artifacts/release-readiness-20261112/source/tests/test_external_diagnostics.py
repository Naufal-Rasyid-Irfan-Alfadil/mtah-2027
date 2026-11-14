"""Manual diagnostic examples, without model fitting or real match data."""

from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from external_baseline.contracts import FrameKey
from external_baseline.diagnostics import contiguous_runs, diagnose, summarize
from external_baseline.features import FEATURE_NAMES
from external_baseline.prepare import sha256
from test_external_training import make_fixture


class DiagnosticTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global np
        try:
            import numpy as np
        except ImportError as error:
            raise unittest.SkipTest("optional numpy unavailable") from error

    def example(self, truth, pred, numbers=None, valid=None):
        n=len(truth)
        numbers=numbers if numbers is not None else list(range(n))
        keys=[FrameKey("synthetic",1,v) for v in numbers]
        x=np.zeros((n,len(FEATURE_NAMES)))
        x[:,FEATURE_NAMES.index("nearest_home_m")]=1
        x[:,FEATURE_NAMES.index("nearest_away_m")]=2
        probs=np.full((n,3),.05)
        for i,label in enumerate(pred):
            probs[i,("H","A","D").index(label)]=.9
        return summarize(keys,[v*40000 for v in numbers],x,truth,
                         valid if valid is not None else [True]*n,pred,probs)

    def test_manual_error_decomposition_and_confidence(self):
        r=self.example(["H","A","H","D","D"],["A","H","D","H","D"])
        self.assertEqual(r["frame_errors"],{"correct":1,"HA_swap":2,"alive_to_D":1,"D_to_alive":1})
        self.assertEqual(r["confusion"],[[0,1,1],[1,0,0],[1,0,1]])
        self.assertEqual(r["nearest_geometry"]["comparable_alive_frames"],3)
        self.assertEqual(r["nearest_geometry"]["closer_team_matches_target"],2)
        self.assertAlmostEqual(r["confidence_by_outcome"]["HA_swap"]["max_probability"]["median"],.9)
        self.assertAlmostEqual(r["confidence_by_outcome"]["HA_swap"]["top_two_margin"]["mean"],.85)
        self.assertEqual(r["alive_errors_by_ball_x_sign"]["centre"]["alive_frames"],3)

    def test_flicker_inside_constant_true_possession(self):
        r=self.example(["H"]*5,["H","A","H","H","H"])
        self.assertEqual(r["target_runs"]["possession_spells"],1)
        self.assertEqual(r["prediction_runs"]["possession_spells"],3)
        self.assertEqual(r["prediction_runs"]["by_label"]["H"]["single_frame_runs"],1)
        self.assertEqual(r["predicted_HA_switches_inside_constant_true_possession"],2)
        self.assertEqual(r["error_run_length_frames"]["median"],1)

    def test_gaps_invalid_half_and_timestamp_boundaries(self):
        r=self.example(["H"]*4,["H","A","H","A"],numbers=[10,11,14,15])
        self.assertEqual(r["valid_contiguous_runs"],2)
        self.assertEqual(r["target_runs"]["possession_spells"],2)
        self.assertEqual(r["predicted_HA_switches_inside_constant_true_possession"],2)
        keys=[FrameKey("s",1,10),FrameKey("s",1,11),FrameKey("s",1,12),FrameKey("s",2,10)]
        self.assertEqual(contiguous_runs(keys,[0,40000,120000,160000],[True]*4),[(0,2),(2,3),(3,4)])
        self.assertEqual(contiguous_runs(keys,[0,40000,80000,0],[True,False,True,True]),[(0,1),(2,3),(3,4)])

    def test_missing_geometry_and_invalid_target_not_zero_filled(self):
        keys=[FrameKey("s",1,v) for v in (10,11)]
        x=np.full((2,16),np.nan)
        r=summarize(keys,[0,40000],x,["H",None],[True,False],["H","A"],[[.8,.1,.1],[.1,.8,.1]])
        self.assertEqual(r["valid_frames"],1)
        self.assertEqual(r["nearest_geometry"]["comparable_alive_frames"],0)
        self.assertEqual(r["geometry_by_target"]["H"]["ball_x_m"]["defined"],0)
        self.assertIsNone(r["geometry_by_target"]["H"]["ball_x_m"]["median"])
        self.assertEqual(r["alive_errors_by_ball_x_sign"]["missing"]["alive_frames"],1)
        self.assertEqual(r["geometry_by_target"]["A"]["frames"],0)

    def test_artifact_roundtrip_no_mutation_and_hash_rejection(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            f,t=make_fixture(root)
            model_dir=root/"raw"
            model_dir.mkdir()
            p=model_dir/"predictions.sqlite"
            with closing(sqlite3.connect(f)) as fdb, closing(sqlite3.connect(p)) as db:
                db.execute("CREATE TABLE predictions(match_id TEXT,period INTEGER,source_frame INTEGER,timestamp_us INTEGER,split TEXT,label TEXT,p_H REAL,p_A REAL,p_D REAL)")
                db.executemany("INSERT INTO predictions VALUES (?,?,?,?,?,'H',.8,.1,.1)",
                               fdb.execute("SELECT match_id,period,source_frame,timestamp_us,split FROM features"))
                db.commit()
            paths=(f,t,f.parent/"manifest.json",t.parent/"manifest.json")
            (model_dir/"manifest.json").write_text(json.dumps({"status":"ready","contract_version":1,"outputs_sha256":{"predictions.sqlite":sha256(p)},"inputs_sha256":{str(v.resolve()):sha256(v) for v in paths}}),encoding="utf-8")
            before={str(v):sha256(v) for v in (f,t,p)}
            a=diagnose(f,t,p,root/"one")
            b=diagnose(f,t,p,root/"two")
            self.assertEqual(a["splits"],b["splits"])
            self.assertEqual({str(v):sha256(v) for v in (f,t,p)},before)
            self.assertEqual(a["splits"]["train"]["invalid_frames"],1)
            self.assertEqual(json.loads((root/"one"/"manifest.json").read_text())["status"],"ready")
            with self.assertRaises(FileExistsError):
                diagnose(f,t,p,root/"one")
            with closing(sqlite3.connect(p)) as db:
                db.execute("UPDATE predictions SET p_H=.7")
                db.commit()
            with self.assertRaisesRegex(ValueError,"hash"):
                diagnose(f,t,p,root/"bad")

    def test_import_help_no_data_or_training_dependency_access(self):
        script='''import sys,runpy
def audit(event,args):
    if event in ('open','sqlite3.connect'):
        p=str(args[0]).replace(chr(92),'/').lower()
        if p.endswith(('.sqlite','.xml','.csv','.mp4','.joblib')) or '/data/' in p:
            raise RuntimeError('unexpected data access '+p)
sys.addaudithook(audit)
import external_baseline.diagnostics
assert not any(m in sys.modules for m in ('numpy','sklearn','joblib','pandas'))
sys.argv=['diagnostics','--help']
runpy.run_module('external_baseline.diagnostics',run_name='__main__')
'''
        result=subprocess.run([sys.executable,"-B","-c",script],capture_output=True,text=True,cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=="__main__":
    unittest.main()
