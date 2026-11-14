"""Observation perturbation counterexamples and frozen-pipeline integration."""

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
from external_baseline.features import EntityPosition, FrameFeatureExtractor, FEATURE_NAMES
from external_baseline.prepare import sha256
from external_baseline.robustness import SCENARIOS, perturb_frame, run_robustness
from external_baseline.temporal import run_decoder
from external_baseline.training import evaluate_timeline, train
from test_external_training import make_fixture


def frozen_fixture(root):
    """Build self-consistent synthetic observations/features and freeze small models."""
    f,t=make_fixture(root)
    o=t.parent/"observations.sqlite"
    with closing(sqlite3.connect(o)) as db, closing(sqlite3.connect(f)) as src:
        db.executescript('''
            CREATE TABLE frames(match_id TEXT,period INTEGER,source_frame INTEGER,timestamp_us INTEGER,
                PRIMARY KEY(match_id,period,source_frame));
            CREATE TABLE observations(match_id TEXT,period INTEGER,source_frame INTEGER,entity_id TEXT,
                team TEXT,x_m REAL,y_m REAL,x_reason TEXT,y_reason TEXT,
                PRIMARY KEY(match_id,period,source_frame,entity_id));
            CREATE TABLE metadata(json TEXT);
        ''')
        for match,period,n,stamp in src.execute("SELECT match_id,period,source_frame,timestamp_us FROM features"):
            db.execute("INSERT INTO frames VALUES (?,?,?,?)",(match,period,n,stamp))
            rows=[(match,period,n,"BALL","BALL",((n-100)%3-1)*30,0,None,None),
                  (match,period,n,"h","H",-30,0,None,None),(match,period,n,"a","A",30,0,None,None)]
            db.executemany("INSERT INTO observations VALUES (?,?,?,?,?,?,?,?,?)",rows)
        db.execute("INSERT INTO metadata VALUES (?)",(json.dumps(dict(contract_version=1,match_id="synthetic",coordinate_unit="m",origin="pitch_center",fps=25,length_m=105,width_m=68)),))
        db.commit()
    fm_path=f.parent/"manifest.json"
    fm=json.loads(fm_path.read_text())
    fm["input"].update(observations=str(o),sha256=sha256(o))
    fm_path.write_text(json.dumps(fm))
    train(f,t,root/"baseline16")
    train(f,t,root/"raw14","no-signed-position",root/"baseline16")
    run_decoder(f,t,root/"raw14"/"predictions.sqlite",root/"decoder")
    return o,f,t,root/"raw14",root/"decoder"


class RobustnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global np
        try:
            import numpy as np
            import sklearn
            import joblib
        except ImportError as error:
            raise unittest.SkipTest("optional training dependencies unavailable") from error

    def test_full_partial_and_frame_missing_are_distinct(self):
        entities=[EntityPosition("BALL","BALL",0,0),EntityPosition("h","H",3,4)]
        cases=[("ball_drop",[],0), ("ball_partial",[None,0],1)]
        for kind,expected,present in cases:
            keep,changed,audit=perturb_frame(entities,0,{"kind":kind,"probability":1},np.random.default_rng(2027))
            self.assertTrue(keep)
            features=FrameFeatureExtractor(105,68).extract(FrameKey("s",2,10),0,changed)
            self.assertEqual(features["ball_record_present"],present)
            self.assertEqual(features["ball_xy_observed"],0)
            self.assertIsNone(features["nearest_home_m"])
            self.assertEqual(features["home_records"],1)
        keep,changed,_=perturb_frame(entities,0,{"kind":"frame_gap","period_frames":1500,"missing_frames":25},np.random.default_rng(2027))
        self.assertFalse(keep)
        self.assertEqual(changed,[])
        self.assertEqual(entities[0].x_m,0)

    def test_bursts_use_original_frame_offsets_not_row_positions(self):
        entities=[EntityPosition("BALL","BALL",1,1)]
        s={"kind":"ball_burst","period_frames":500,"missing_frames":50}
        for offset,missing in ((0,True),(49,True),(50,False),(499,False),(500,True)):
            with self.subTest(offset=offset):
                keep,changed,_=perturb_frame(entities,offset,s,np.random.default_rng(2027))
                self.assertTrue(keep)
                self.assertEqual(len(changed)==0,missing)

    def test_random_masks_repeat_and_do_not_depend_on_geometry_or_targets(self):
        scenario={"kind":"ball_drop","probability":.2}
        def mask(entities):
            rng=np.random.default_rng(2027)
            return [perturb_frame(entities,n,scenario,rng)[2]["selected_frames"] for n in range(100)]
        a=mask([EntityPosition("BALL","BALL",0,0)])
        self.assertEqual(a,mask([EntityPosition("BALL","BALL",1000,None)]))
        self.assertEqual(a,mask([]))
        self.assertTrue(0<sum(a)<100)
        self.assertEqual(len(SCENARIOS),7)

    def test_player_removal_keeps_ball_and_jitter_preserves_missing_outside(self):
        entities=[EntityPosition("BALL","BALL",60,None),EntityPosition("h","H",3,4)]
        _,changed,audit=perturb_frame(entities,0,{"kind":"player_drop","probability":1},np.random.default_rng(2027))
        self.assertEqual(changed,[entities[0]])
        self.assertEqual(audit["player_records_removed"],1)
        class FixedNoise:
            def normal(self,mean,sigma):
                return .25
        _,changed,audit=perturb_frame(entities,0,{"kind":"jitter","sigma_m":.25},FixedNoise())
        self.assertEqual((changed[0].x_m,changed[0].y_m),(60.25,None))
        self.assertEqual((entities[0].x_m,entities[0].y_m),(60,None))
        self.assertEqual(audit["jittered_axes"],3)

    def test_speed_recomputed_after_ball_missing_and_frame_gap(self):
        extractor=FrameFeatureExtractor(105,68)
        extractor.extract(FrameKey("s",2,10),0,[EntityPosition("BALL","BALL",0,0)])
        extractor.extract(FrameKey("s",2,11),40000,[])
        r=extractor.extract(FrameKey("s",2,12),80000,[EntityPosition("BALL","BALL",1,0)])
        self.assertIsNone(r["ball_speed_mps"])
        # Simulate skipping a whole frame (no extractor call).
        r=extractor.extract(FrameKey("s",2,14),160000,[EntityPosition("BALL","BALL",2,0)])
        self.assertIsNone(r["ball_speed_mps"])

    def test_abstentions_are_frame_misses_with_repository_temporal_semantics(self):
        keys=[FrameKey("s",2,n) for n in range(5)]
        y=["H","H","A","A","A"]
        p=["H","X","X","A","A"]
        with self.assertRaises(ValueError):
            evaluate_timeline(keys,[n*40000 for n in range(5)],y,[True]*5,p)
        r=evaluate_timeline(keys,[n*40000 for n in range(5)],y,[True]*5,p,allow_abstain=True)
        self.assertEqual(r["n_graded"],5)
        self.assertEqual(r["n_abstain_on_graded"],2)
        self.assertEqual(r["confusion"][0][3],1)
        self.assertEqual(r["confusion"][1][3],1)
        self.assertEqual(r["transitions"][12]["n_pred"],1)
        self.assertEqual(r["transitions"][12]["n_matched"],1)

    def test_frozen_end_to_end_clean_replay_determinism_and_gap_coverage(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            o,f,t,c,d=frozen_fixture(root)
            inputs=(o,f,t,c/"model.joblib",c/"predictions.sqlite",d/"decoder_parameters.json",d/"predictions.sqlite")
            hashes=[sha256(v) for v in inputs]
            with patch("sklearn.ensemble.HistGradientBoostingClassifier.fit",side_effect=AssertionError("no refit")), patch("external_baseline.temporal.estimate_markov",side_effect=AssertionError("no transition fitting")):
                a=run_robustness(o,f,t,c,d,root/"one")
                b=run_robustness(o,f,t,c,d,root/"two")
            self.assertEqual([sha256(v) for v in inputs],hashes)
            self.assertEqual(a["scenarios"],b["scenarios"])
            self.assertEqual(sha256(root/"one"/"predictions.sqlite"),sha256(root/"two"/"predictions.sqlite"))
            self.assertEqual(a["scenarios"]["clean"]["feature_coverage_on_retained_frames"]["ball_speed_mps"]["missing"],1)
            burst=a["scenarios"]["ball_drop_burst2s"]
            self.assertEqual(burst["audit"]["ball_records_removed"],50)
            self.assertEqual(burst["feature_coverage_on_retained_frames"]["ball_speed_mps"]["missing"],51)
            gap=a["scenarios"]["frame_gap1s_every60s"]
            self.assertEqual(gap["input_frames"],60)
            self.assertEqual(gap["retained_frames"],35)
            self.assertEqual(gap["decoded_metrics"]["n_graded"],59)  # invalid target already present, not removed for the stress
            self.assertEqual(gap["decoded_metrics"]["n_abstain_on_graded"],24)
            with closing(sqlite3.connect(root/"one"/"predictions.sqlite")) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM predictions").fetchone()[0],7*60)
                self.assertEqual(db.execute("SELECT COUNT(*) FROM predictions WHERE scenario='frame_gap1s_every60s' AND retained=0 AND raw_label='X' AND decoded_label='X' AND p_H IS NULL").fetchone()[0],25)
                self.assertEqual(db.execute("PRAGMA quick_check").fetchone()[0],"ok")
            with self.assertRaises(FileExistsError):
                run_robustness(o,f,t,c,d,root/"one")
            # A mismatching clean replay must never become a ready stress report.
            with patch("external_baseline.robustness.predict_raw",side_effect=lambda model,x:(np.full(len(x),"D"),np.tile([0,0,1],(len(x),1)))):
                with self.assertRaisesRegex(ValueError,"replay"):
                    run_robustness(o,f,t,c,d,root/"failed")
            self.assertTrue((root/"failed"/"FAILED.json").exists())
            self.assertFalse((root/"failed"/"manifest.json").exists())

    def test_import_help_does_not_open_data_or_load_model(self):
        script='''import sys,runpy
def audit(event,args):
    if event in ('open','sqlite3.connect'):
        p=str(args[0]).replace(chr(92),'/').lower()
        if p.endswith(('.sqlite','.xml','.csv','.mp4','.joblib')) or '/data/' in p:
            raise RuntimeError('unexpected input access '+p)
sys.addaudithook(audit)
import external_baseline.robustness
assert not any(m in sys.modules for m in ('numpy','sklearn','joblib','pandas'))
sys.argv=['robustness','--help']
runpy.run_module('external_baseline.robustness',run_name='__main__')
'''
        result=subprocess.run([sys.executable,"-B","-c",script],capture_output=True,text=True,cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=="__main__":
    unittest.main()
