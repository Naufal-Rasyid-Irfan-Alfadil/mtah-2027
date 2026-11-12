"""Synthetic frozen-candidate evaluation; no new real match labels are accessed."""

from contextlib import closing
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from external_baseline.augmented import run_augmented
from external_baseline.holdout import freeze, evaluate
from external_baseline.prepare import sha256
from external_baseline.robustness import run_robustness
from external_baseline.temporal import decode_probabilities
from external_baseline.training import load_split
from test_external_robustness import frozen_fixture


class HoldoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        try:
            import numpy
            import sklearn
            import joblib
        except ImportError as error:
            raise unittest.SkipTest("optional training dependencies unavailable") from error
        cls.temp=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name)
        o,f,t,c,d=frozen_fixture(cls.root)
        run_robustness(o,f,t,c,d,cls.root/"stress")
        run_augmented(o,f,t,c,d,cls.root/"stress",cls.root/"augmented")
        cls.c,cls.d=c,d
        cls.ac,cls.ad=cls.root/"augmented"/"classifier",cls.root/"augmented"/"decoder"
        test=cls.root/"synthetic_test"
        (test/"features").mkdir(parents=True)
        (test/"prepared").mkdir()
        cls.f,cls.t=test/"features"/"features.sqlite",test/"prepared"/"targets.sqlite"
        shutil.copyfile(f,cls.f)
        shutil.copyfile(t,cls.t)
        for path,table in ((cls.f,"features"),(cls.t,"targets")):
            with closing(sqlite3.connect(path)) as db:
                db.execute(f"UPDATE {table} SET match_id='DFL-MAT-SYNTEST'")
                db.commit()
        tm=json.loads((t.parent/"manifest.json").read_text())
        tm["match"]={"match_id":"DFL-MAT-SYNTEST"}
        (cls.t.parent/"manifest.json").write_text(json.dumps(tm))
        fm=json.loads((f.parent/"manifest.json").read_text())
        fm["input"]["parent_manifest_sha256"]=sha256(cls.t.parent/"manifest.json")
        fm["output_sha256"]=sha256(cls.f)
        (cls.f.parent/"manifest.json").write_text(json.dumps(fm))

    def snapshot(self,name,confirmed=True):
        output=self.root/name
        protocol=freeze(self.c,self.d,self.ac,self.ad,"DFL-MAT-SYNTEST",output,confirmed)
        return output,protocol

    def test_snapshot_identity_source_immutability_and_pending_history_guard(self):
        source=(self.c/"model.joblib",self.ac/"model.joblib",self.d/"decoder_parameters.json")
        hashes=[sha256(p) for p in source]
        output,protocol=self.snapshot("pending",False)
        self.assertEqual(protocol["primary"],"augmented")
        self.assertFalse(protocol["history_confirmed_unused"])
        self.assertEqual([sha256(p) for p in source],hashes)
        self.assertEqual(sha256(output/"original"/"model.joblib"),hashes[0])
        self.assertEqual(sha256(output/"augmented"/"model.joblib"),hashes[1])
        # Reject before resolving or reading any feature/target dataset.
        with self.assertRaisesRegex(ValueError,"confirmed-unused"):
            evaluate(output/"protocol.json","not-present-features","not-present-targets",self.root/"blocked")
        with self.assertRaises(ValueError):
            freeze(self.c,self.d,self.ac,self.ad,"DFL-MAT-J03WOH",self.root/"development_as_test",True)
        with self.assertRaises(FileExistsError):
            freeze(self.c,self.d,self.ac,self.ad,"DFL-MAT-SYNTEST",output,False)

    def test_both_halves_test_no_fit_labels_after_all_inference_and_reproducibility(self):
        output,_=self.snapshot("confirmed")
        before=[sha256(p) for p in (self.f,self.t,output/"original"/"model.joblib",output/"augmented"/"model.joblib")]
        with patch("sklearn.ensemble.HistGradientBoostingClassifier.fit",side_effect=AssertionError("no refitting")), patch("external_baseline.temporal.estimate_markov",side_effect=AssertionError("no decoder fitting")), patch("external_baseline.holdout.decode_probabilities",wraps=decode_probabilities) as decoded:
            def checked(*args):
                self.assertEqual(decoded.call_count,4)
                return load_split(*args)
            with patch("external_baseline.holdout.load_split",side_effect=checked):
                report=evaluate(output/"protocol.json",self.f,self.t,self.root/"result_one")
        self.assertEqual(before,[sha256(p) for p in (self.f,self.t,output/"original"/"model.joblib",output/"augmented"/"model.joblib")])
        self.assertEqual(report["primary"],"augmented")
        self.assertEqual(set(report["candidates"]),{"original","augmented"})
        for candidate in report["candidates"].values():
            self.assertEqual(candidate["observed_frames"],150)
            self.assertEqual(candidate["valid_targets"],148)
            self.assertEqual(set(candidate["per_half"]),{"1","2"})
            self.assertEqual(candidate["overall"]["decoded"]["valid_contiguous_runs"],4)
        with closing(sqlite3.connect(self.root/"result_one"/"predictions.sqlite")) as db:
            self.assertEqual(db.execute("SELECT COUNT(*) FROM predictions").fetchone()[0],300)
            self.assertEqual(db.execute("SELECT DISTINCT split FROM predictions").fetchall(),[("test",)])
        second=evaluate(output/"protocol.json",self.f,self.t,self.root/"result_two")
        self.assertEqual(report,second)
        self.assertEqual(sha256(self.root/"result_one"/"predictions.sqlite"),sha256(self.root/"result_two"/"predictions.sqlite"))

    def test_wrong_match_and_changed_snapshot_cannot_be_evaluated(self):
        output,_=self.snapshot("mismatch")
        protocol=json.loads((output/"protocol.json").read_text())
        protocol["test_match"]="DFL-MAT-ANOTHER"
        (output/"protocol.json").write_text(json.dumps(protocol))
        with self.assertRaisesRegex(ValueError,"predeclared"):
            evaluate(output/"protocol.json",self.f,self.t,self.root/"wrong_match")
        self.assertTrue((self.root/"wrong_match"/"FAILED.json").exists())
        self.assertFalse((self.root/"wrong_match"/"manifest.json").exists())
        with (output/"original"/"model.joblib").open("ab") as handle:
            handle.write(b"synthetic corruption")
        with self.assertRaisesRegex(ValueError,"hash"):
            evaluate(output/"protocol.json",self.f,self.t,self.root/"corrupt")
        other,_=self.snapshot("source_mismatch")
        protocol=json.loads((other/"protocol.json").read_text())
        protocol["source_sha256"]["external_baseline/features.py"]="0"*64
        (other/"protocol.json").write_text(json.dumps(protocol))
        with self.assertRaisesRegex(ValueError,"frozen pipeline source"):
            evaluate(other/"protocol.json","never-read-features","never-read-targets",self.root/"source_rejected")

    def test_import_and_help_do_not_read_datasets(self):
        script='''import sys,runpy
def audit(event,args):
    if event in ('open','sqlite3.connect'):
        p=str(args[0]).replace(chr(92),'/').lower()
        if p.endswith(('.sqlite','.xml','.csv','.mp4','.joblib')) or '/data/' in p:
            raise RuntimeError('unexpected data/model access '+p)
sys.addaudithook(audit)
import external_baseline.holdout
assert not any(m in sys.modules for m in ('numpy','sklearn','joblib','pandas'))
sys.argv=['holdout','--help']
runpy.run_module('external_baseline.holdout',run_name='__main__')
'''
        result=subprocess.run([sys.executable,"-B","-c",script],capture_output=True,text=True,cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=="__main__":
    unittest.main()
