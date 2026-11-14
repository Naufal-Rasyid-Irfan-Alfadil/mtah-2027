"""Synthetic compatibility checks for the expanded candidate holdout snapshot."""
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

from external_baseline.freeze_expanded import freeze
from external_baseline.holdout import evaluate
from external_baseline.multimatch import run
from external_baseline.prepare import sha256
from external_baseline.temporal import decode_probabilities
from external_baseline.training import load_split
import test_external_multimatch as multimatch_tests


class ExpandedFreezeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory()
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name)
        helper=multimatch_tests.MultimatchTests()
        pairs,cls.c,cls.d=helper.fixture(cls.root)
        # The shared synthetic helper adds augmentation metadata after creating
        # its decoder. Attest that synthetic manifest revision explicitly here.
        dm_path=cls.d/'manifest.json'
        dm=json.loads(dm_path.read_text())
        dm['inputs_sha256'][str((cls.c/'manifest.json').resolve())]=sha256(cls.c/'manifest.json')
        dm_path.write_text(json.dumps(dm))
        cls.expanded=cls.root/'expanded'
        run(pairs[:2],pairs[2],cls.c,cls.d,cls.expanded)
        test=cls.root/'test'
        shutil.copytree(pairs[2][0],test/'prepared')
        shutil.copytree(pairs[2][1],test/'features')
        cls.f,cls.t=test/'features/features.sqlite',test/'prepared/targets.sqlite'
        for path,table in ((cls.f,'features'),(cls.t,'targets')):
            with closing(sqlite3.connect(path)) as db:
                db.execute(f"UPDATE {table} SET match_id='synthetic-unused'")
                db.commit()
        pm_path=cls.t.parent/'manifest.json'
        pm=json.loads(pm_path.read_text()); pm['match']['match_id']='synthetic-unused'
        pm_path.write_text(json.dumps(pm))
        fm_path=cls.f.parent/'manifest.json'
        fm=json.loads(fm_path.read_text())
        fm['input']['parent_manifest_sha256']=sha256(pm_path)
        fm['output_sha256']=sha256(cls.f)
        fm_path.write_text(json.dumps(fm))

    def snapshot(self,name,confirmed=True,match='synthetic-unused'):
        output=self.root/name
        p=freeze(self.expanded,self.c,self.d,match,output,confirmed)
        return output,p

    def test_snapshot_primary_separate_decoders_and_copy_hashes(self):
        out,p=self.snapshot('snapshot')
        self.assertEqual(p['primary'],'augmented')
        self.assertEqual(p['candidates']['augmented']['display_name'],'expanded')
        self.assertEqual(p['candidates']['original']['display_name'],'old_augmented')
        self.assertNotEqual(p['candidates']['original']['parameters_sha256'],p['candidates']['augmented']['parameters_sha256'])
        sm=json.loads((out/'snapshot_manifest.json').read_text())
        for file,digest in sm['files_sha256'].items():self.assertEqual(sha256(out/file),digest)
        self.assertEqual(sha256(out/'augmented/model.joblib'),sha256(self.expanded/'model.joblib'))
        self.assertFalse(sm['test_data_access'])
        with self.assertRaises(FileExistsError):self.snapshot('snapshot')

    def test_pending_and_used_match_guards_precede_dataset_access(self):
        out,p=self.snapshot('pending',False)
        self.assertFalse(p['history_confirmed_unused'])
        with self.assertRaisesRegex(ValueError,'confirmed-unused'):
            evaluate(out/'protocol.json','not-a-dataset','not-a-target',self.root/'blocked')
        for match in ('synthetic-a','synthetic-b','synthetic-v','DFL-MAT-J03WOY'):
            with self.assertRaisesRegex(ValueError,'already used'):
                self.snapshot('used-'+match,True,match)

    def test_existing_evaluator_no_fit_target_order_and_reproduction(self):
        out,p=self.snapshot('evaluate')
        inputs=(self.f,self.t,self.expanded/'model.joblib',self.c/'model.joblib')
        before=[sha256(f) for f in inputs]
        with patch('sklearn.ensemble.HistGradientBoostingClassifier.fit',side_effect=AssertionError('no fitting')), \
             patch('external_baseline.temporal.estimate_markov',side_effect=AssertionError('no decoder fit')), \
             patch('external_baseline.holdout.decode_probabilities',wraps=decode_probabilities) as decoded:
            def checked(*args):
                self.assertEqual(decoded.call_count,4)
                return load_split(*args)
            with patch('external_baseline.holdout.load_split',side_effect=checked):
                first=evaluate(out/'protocol.json',self.f,self.t,self.root/'first')
        second=evaluate(out/'protocol.json',self.f,self.t,self.root/'second')
        self.assertEqual(first,second)
        self.assertEqual(sha256(self.root/'first/predictions.sqlite'),sha256(self.root/'second/predictions.sqlite'))
        self.assertEqual(before,[sha256(f) for f in inputs])
        with closing(sqlite3.connect(self.root/'first/predictions.sqlite')) as db:
            self.assertEqual(db.execute('SELECT DISTINCT split FROM predictions').fetchall(),[('test',)])
            self.assertEqual(db.execute('SELECT COUNT(*) FROM predictions').fetchone()[0],300)
        with (out/'augmented/model.joblib').open('ab') as stream:stream.write(b'changed')
        with self.assertRaisesRegex(ValueError,'hash mismatch'):
            evaluate(out/'protocol.json',self.f,self.t,self.root/'tampered')

    def test_import_help_without_dataset_or_model_imports(self):
        script='''import sys,runpy
def audit(event,args):
    if event in ('open','sqlite3.connect'):
        p=str(args[0]).replace(chr(92),'/').lower()
        if any(s in p for s in ('/data/','/external_artifacts/','/evaluation/gt/','/evaluation/results/')) or p.endswith(('.json','.sqlite','.xml','.csv','.mp4','.joblib')):
            raise RuntimeError('forbidden dataset access: '+p)
sys.addaudithook(audit)
import external_baseline.freeze_expanded
assert not any(m in sys.modules for m in ('numpy','pandas','sklearn','joblib'))
sys.argv=['freeze_expanded','--help']
runpy.run_module('external_baseline.freeze_expanded',run_name='__main__')
'''
        result=subprocess.run([sys.executable,'-B','-c',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':unittest.main()
