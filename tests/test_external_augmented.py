"""Synthetic training-view provenance and one-fit integration checks."""

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from external_baseline.augmented import TRAIN_SEED, build_training_pool, run_augmented
from external_baseline.prepare import sha256
from external_baseline.robustness import stress_feature_matrices, run_robustness
from external_baseline.training import load_split, fit_baseline
from external_baseline.temporal import decode_probabilities
from test_external_robustness import frozen_fixture


class AugmentedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global np
        try:
            import numpy as np
            import sklearn
            import joblib
        except ImportError as error:
            raise unittest.SkipTest("optional training dependencies unavailable") from error

    def test_pool_keeps_source_labels_and_excludes_unknowns_and_removed_frames(self):
        with tempfile.TemporaryDirectory() as folder:
            o,f,t,c,d=frozen_fixture(Path(folder))
            data=load_split(f,t,1)
            replay=stress_feature_matrices(o,period=1,seed=TRAIN_SEED)
            x,y,valid,audit=build_training_pool(data,replay)
            # Six views retain 89 valid rows, the frame-gap view retains 65.
            self.assertEqual(x.shape,(599,14))
            self.assertEqual(len(y),599)
            self.assertTrue(valid.all())
            self.assertTrue(np.isnan(x).any())
            self.assertEqual(audit["unique_source_frames"],90)
            self.assertEqual(audit["valid_source_frames"],89)
            self.assertEqual(audit["pooled_class_counts"],{"H":201,"A":196,"D":202})
            self.assertNotIn(None,y)
            self.assertEqual(audit["views"]["clean"]["excluded_invalid_retained"],1)
            self.assertEqual(audit["views"]["frame_gap1s_every60s"]["fitted_rows"],65)
            self.assertTrue(all(k.period==1 for k in replay[0]))
            replay_again=stress_feature_matrices(o,period=1,seed=TRAIN_SEED)
            np.testing.assert_array_equal(replay[2]["ball_drop_iid20"],replay_again[2]["ball_drop_iid20"])
            with self.assertRaisesRegex(ValueError,"half 1"):
                build_training_pool(load_split(f,t,2),stress_feature_matrices(o,period=2,seed=TRAIN_SEED))
            replay[2]["clean"][0,0]=99
            with self.assertRaisesRegex(ValueError,"replay"):
                build_training_pool(data,replay)

    def test_one_fit_reuses_decoder_and_replays_stress_without_input_mutation(self):
        import joblib
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            o,f,t,c,d=frozen_fixture(root)
            run_robustness(o,f,t,c,d,root/"reference_stress")
            tracked=(o,f,t,c/"model.joblib",c/"predictions.sqlite",d/"decoder_parameters.json",root/"reference_stress"/"robustness_report.json")
            hashes=[sha256(v) for v in tracked]
            with patch("external_baseline.augmented.fit_baseline",wraps=fit_baseline) as fitted, patch("external_baseline.augmented.decode_probabilities",wraps=decode_probabilities) as decoded, patch("external_baseline.temporal.estimate_markov",side_effect=AssertionError("decoder may not be refitted")):
                def load_checked(*args):
                    if args[2]==2:
                        self.assertEqual(fitted.call_count,1)
                        self.assertGreaterEqual(decoded.call_count,2)
                    return load_split(*args)
                with patch("external_baseline.augmented.load_split",side_effect=load_checked):
                    report=run_augmented(o,f,t,c,d,root/"reference_stress",root/"one")
                self.assertEqual(fitted.call_count,1)
                self.assertEqual(fitted.call_args.args[0].shape,(599,14))
            self.assertEqual([sha256(v) for v in tracked],hashes)
            self.assertEqual((root/"one"/"decoder"/"decoder_parameters.json").read_bytes(),(d/"decoder_parameters.json").read_bytes())
            self.assertEqual(len(report["stress"]),7)
            artifact=joblib.load(root/"one"/"classifier"/"model.joblib")
            self.assertEqual(artifact["model"].n_iter_,100)
            self.assertFalse(artifact["model"].do_early_stopping_)
            self.assertEqual(len(artifact["feature_names"]),14)
            manifest=json.loads((root/"one"/"manifest.json").read_text())
            self.assertEqual(manifest["status"],"ready")
            self.assertEqual(manifest["protocol"]["training_seed"],2028)
            self.assertEqual(manifest["protocol"]["validation_stress_seed"],2027)
            for name,digest in manifest["outputs_sha256"].items():
                self.assertEqual(sha256(root/"one"/name),digest)
            second=run_augmented(o,f,t,c,d,root/"reference_stress",root/"two")
            self.assertEqual(report,second)
            for subdir in ("classifier","decoder","stress"):
                self.assertEqual(sha256(root/"one"/subdir/"predictions.sqlite"),sha256(root/"two"/subdir/"predictions.sqlite"))
            with self.assertRaises(FileExistsError):
                run_augmented(o,f,t,c,d,root/"reference_stress",root/"one")
            with patch("external_baseline.augmented.fit_baseline",side_effect=RuntimeError("synthetic fit failure")):
                with self.assertRaisesRegex(RuntimeError,"synthetic fit failure"):
                    run_augmented(o,f,t,c,d,root/"reference_stress",root/"failed")
            self.assertTrue((root/"failed"/"FAILED.json").exists())
            self.assertFalse((root/"failed"/"manifest.json").exists())

    def test_help_import_without_data_or_model_dependencies(self):
        script='''import sys,runpy
def audit(event,args):
    if event in ('open','sqlite3.connect'):
        p=str(args[0]).replace(chr(92),'/').lower()
        if p.endswith(('.sqlite','.xml','.csv','.mp4','.joblib')) or '/data/' in p:
            raise RuntimeError('unexpected input access '+p)
sys.addaudithook(audit)
import external_baseline.augmented
assert not any(m in sys.modules for m in ('numpy','sklearn','joblib','pandas'))
sys.argv=['augmented','--help']
runpy.run_module('external_baseline.augmented',run_name='__main__')
'''
        result=subprocess.run([sys.executable,"-B","-c",script],capture_output=True,text=True,cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=="__main__":
    unittest.main()
