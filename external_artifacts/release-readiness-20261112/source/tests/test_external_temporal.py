"""Manual Markov counts, exhaustive-path checks and external-artifact fixtures."""

from contextlib import closing
import itertools
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from external_baseline.contracts import FrameKey
from external_baseline.prepare import sha256
from external_baseline.temporal import estimate_markov, decode_probabilities, run_decoder
from external_baseline.training import FEATURE_SETS, LABELS
from test_external_training import make_fixture


def raw_fixture(root):
    f,t=make_fixture(root)
    raw=root/"raw14"
    raw.mkdir()
    p=raw/"predictions.sqlite"
    with closing(sqlite3.connect(f)) as fdb, closing(sqlite3.connect(p)) as db:
        db.execute("CREATE TABLE predictions(match_id TEXT,period INTEGER,source_frame INTEGER,timestamp_us INTEGER,split TEXT,label TEXT,p_H REAL,p_A REAL,p_D REAL)")
        rows=[]
        for key in fdb.execute("SELECT match_id,period,source_frame,timestamp_us,split FROM features ORDER BY match_id,period,source_frame"):
            state=((key[2]-100)//10)%3
            probs=[.1,.1,.1]
            probs[state]=.8
            rows.append((*key,LABELS[state],*probs))
        db.executemany("INSERT INTO predictions VALUES (?,?,?,?,?,?,?,?,?)",rows)
        db.commit()
    manifest={"status":"ready","contract_version":1,
              "config":{"decoder":None,"feature_names":FEATURE_SETS["no-signed-position"]},
              "outputs_sha256":{"predictions.sqlite":sha256(p)},
              "inputs_sha256":{str(v.resolve()):sha256(v) for v in (f,t,f.parent/"manifest.json",t.parent/"manifest.json")}}
    (raw/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
    return f,t,p


class TemporalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global np
        try:
            import numpy as np
        except ImportError as error:
            raise unittest.SkipTest("optional numpy unavailable") from error

    def manual_parameters(self):
        return dict(decoder_version=1,classes=list(LABELS),fps=25,
                    state_prior=[.5,.3,.2],initial_prior=[.5,.3,.2],
                    transition_matrix=[[.96,.02,.02],[.03,.94,.03],[.02,.02,.96]],
                    emission_weight=1,transition_weight=1)

    def test_exact_training_counts_ignore_unknown_and_missing_time(self):
        keys=[FrameKey("s",1,n) for n in (10,11,12,15,16,17,18)]
        params=estimate_markov(keys,[n.source_frame*40000 for n in keys],
                               ["H","H",None,"A","A","D","D"],[1,1,0,1,1,1,1])
        self.assertEqual(params["state_counts"],[2,2,2])
        self.assertEqual(params["transition_counts"],[[1,0,0],[0,1,1],[0,0,1]])
        self.assertEqual(params["observed_transitions"],4)
        self.assertEqual(params["training_runs"],2)
        np.testing.assert_allclose(params["state_prior"],[1/3]*3)
        np.testing.assert_allclose(params["transition_matrix"],[[.5,.25,.25],[.2,.4,.4],[.25,.25,.5]])
        with self.assertRaises(ValueError):
            estimate_markov([FrameKey("s",2,0)],[0],["H"],[True])
        with self.assertRaises(ValueError):
            estimate_markov([FrameKey("s",1,0)],[0],["H"],[True])

    def test_viterbi_matches_exhaustive_corrected_posterior_objective(self):
        params=self.manual_parameters()
        probs=np.array([[.85,.1,.05],[.2,.7,.1],[.7,.2,.1],[.05,.1,.85]])
        keys=[FrameKey("s",1,n) for n in range(len(probs))]
        scored=[]
        for states in itertools.product(range(3),repeat=len(keys)):
            score=np.log(params["initial_prior"][states[0]])
            for i,s in enumerate(states):
                score+=np.log(probs[i,s])-np.log(params["state_prior"][s])
                if i:
                    score+=np.log(params["transition_matrix"][states[i-1]][s])
            scored.append((score,states))
        expected=max(scored,key=lambda v:v[0])[1]
        actual=decode_probabilities(keys,[n*40000 for n in range(len(keys))],probs,params)
        self.assertEqual(list(actual),[LABELS[s] for s in expected])

    def test_zero_probabilities_ties_and_class_order(self):
        params=self.manual_parameters()
        keys=[FrameKey("s",1,n) for n in range(3)]
        actual=decode_probabilities(keys,[0,40000,80000],[[1,0,0],[0,1,0],[0,0,1]],params)
        self.assertEqual(list(actual),list(LABELS))
        params.update(state_prior=[1/3]*3,initial_prior=[1/3]*3,transition_matrix=[[1/3]*3 for _ in range(3)])
        actual=decode_probabilities(keys,[0,40000,80000],[[1/3]*3]*3,params)
        self.assertEqual(list(actual),["H"]*3)

    def test_gap_period_and_time_reset_equal_independent_decoding(self):
        params=self.manual_parameters()
        chunks=[([FrameKey("s",1,n) for n in (10,11)],[0,40000],[[.99,.005,.005]]*2),
                ([FrameKey("s",1,n) for n in (14,15)],[160000,200000],[[.005,.99,.005]]*2),
                ([FrameKey("s",2,n) for n in (10,11)],[0,40000],[[.005,.005,.99]]*2),
                ([FrameKey("s",2,12)],[120000],[[.99,.005,.005]])]
        expected=[]
        for keys,stamps,probs in chunks:
            expected.extend(decode_probabilities(keys,stamps,probs,params))
        actual=decode_probabilities([k for c in chunks for k in c[0]],
            [t for c in chunks for t in c[1]],[p for c in chunks for p in c[2]],params)
        self.assertEqual(list(actual),expected)

    def test_invalid_probabilities_parameters_and_duplicate_keys_rejected(self):
        key=[FrameKey("s",1,0)]
        for p in ([[float("nan"),0,1]],[[.1,.2,.3]],[[-.1,.2,.9]]):
            with self.assertRaises(ValueError):
                decode_probabilities(key,[0],p,self.manual_parameters())
        params=self.manual_parameters()
        params["transition_weight"]=2
        with self.assertRaises(ValueError):
            decode_probabilities(key,[0],[[1,0,0]],params)
        with self.assertRaises(ValueError):
            decode_probabilities(key*2,[0,0],[[1,0,0]]*2,self.manual_parameters())

    def test_artifact_roundtrip_and_validation_target_independence(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            f,t,p=raw_fixture(root)
            tracked=(f,t,p,f.parent/"manifest.json",t.parent/"manifest.json",p.parent/"manifest.json")
            before=[sha256(v) for v in tracked]
            first=run_decoder(f,t,p,root/"one")
            self.assertEqual([sha256(v) for v in tracked],before)
            params=json.loads((root/"one"/"decoder_parameters.json").read_text())
            self.assertEqual(params["valid_training_frames"],89)
            self.assertEqual(params["observed_transitions"],87)
            # Change only synthetic validation GT/validity, refreshing its raw
            # input provenance. Inference must NOT use those boundary hints.
            with closing(sqlite3.connect(t)) as db:
                db.execute("UPDATE targets SET label='D',valid_target=1 WHERE period=2")
                db.execute("UPDATE targets SET label=NULL,valid_target=0 WHERE period=2 AND source_frame%4=0")
                db.commit()
            pm_path=p.parent/"manifest.json"
            manifest=json.loads(pm_path.read_text())
            manifest["inputs_sha256"][str(t.resolve())]=sha256(t)
            pm_path.write_text(json.dumps(manifest))
            run_decoder(f,t,p,root/"two")
            self.assertEqual((root/"one"/"decoder_parameters.json").read_bytes(),(root/"two"/"decoder_parameters.json").read_bytes())
            self.assertEqual(sha256(root/"one"/"predictions.sqlite"),sha256(root/"two"/"predictions.sqlite"))
            with closing(sqlite3.connect(root/"one"/"predictions.sqlite")) as db:
                self.assertEqual(db.execute("SELECT COUNT(*) FROM predictions").fetchone()[0],150)
                self.assertEqual(db.execute("PRAGMA quick_check").fetchone()[0],"ok")
                rows=db.execute("SELECT match_id,period,source_frame,timestamp_us,label FROM predictions WHERE period=2 ORDER BY match_id,period,source_frame").fetchall()
            with closing(sqlite3.connect(p)) as db:
                raw=db.execute("SELECT p_H,p_A,p_D FROM predictions WHERE period=2 ORDER BY match_id,period,source_frame").fetchall()
            reloaded=decode_probabilities([FrameKey(*row[:3]) for row in rows],[row[3] for row in rows],raw,params)
            self.assertEqual(list(reloaded),[row[4] for row in rows])
            self.assertIn("decoded14",first["splits"]["validation"])
            with self.assertRaises(FileExistsError):
                run_decoder(f,t,p,root/"one")

    def test_mismatched_hash_and_failed_output_readiness(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            f,t,p=raw_fixture(root)
            with closing(sqlite3.connect(p)) as db:
                db.execute("UPDATE predictions SET timestamp_us=timestamp_us+1 WHERE source_frame=100")
                db.commit()
            with self.assertRaisesRegex(ValueError,"hash"):
                run_decoder(f,t,p,root/"bad_hash")
            pm_path=p.parent/"manifest.json"
            manifest=json.loads(pm_path.read_text())
            manifest["outputs_sha256"]["predictions.sqlite"]=sha256(p)
            pm_path.write_text(json.dumps(manifest))
            with self.assertRaisesRegex(ValueError,"timelines"):
                run_decoder(f,t,p,root/"failed")
            self.assertTrue((root/"failed"/"FAILED.json").exists())
            self.assertFalse((root/"failed"/"manifest.json").exists())

    def test_import_help_no_data_or_training_imports(self):
        script='''import sys,runpy
def audit(event,args):
    if event in ('open','sqlite3.connect'):
        p=str(args[0]).replace(chr(92),'/').lower()
        if p.endswith(('.sqlite','.xml','.csv','.mp4','.joblib')) or '/data/' in p:
            raise RuntimeError('unexpected data/model access '+p)
sys.addaudithook(audit)
import external_baseline.temporal
assert not any(m in sys.modules for m in ('numpy','sklearn','joblib','pandas'))
sys.argv=['temporal','--help']
runpy.run_module('external_baseline.temporal',run_name='__main__')
'''
        result=subprocess.run([sys.executable,"-B","-c",script],capture_output=True,text=True,cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=="__main__":
    unittest.main()
