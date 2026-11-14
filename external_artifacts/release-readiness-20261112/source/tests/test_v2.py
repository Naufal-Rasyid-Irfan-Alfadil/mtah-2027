"""Risk-focused v2 fixtures; no real match data or serialized baseline required."""
import copy
import tempfile
from pathlib import Path
import unittest
import json
import shutil
from contextlib import closing
from unittest.mock import patch
import numpy as np

from external_baseline.contracts import FrameKey
from external_baseline.features import ContextFeatureExtractor, EntityPosition
from external_baseline.temporal import decode_probabilities
from external_baseline.v2 import decoder_grid, select, guard_metrics
from external_baseline.training import predict_raw, evaluate_timeline


def parameters():
    return dict(decoder_version=1, classes=['H','A','D'], fps=25,
        emission_weight=1, transition_weight=1, state_prior=[1/3]*3,
        initial_prior=[1/3]*3,
        transition_matrix=[[.998,.001,.001],[.001,.998,.001],[.001,.001,.998]])


class V2Tests(unittest.TestCase):
    def test_selected_context_bundle_roundtrip_and_tamper(self):
        import joblib
        from test_local_inference import LocalInferenceTests, metadata_xml
        from external_baseline.inference_bundle import build_v2, verify_bundle
        from external_baseline.atd_inference import run as infer
        from external_baseline.training import fit_baseline
        from external_baseline.v2 import MODEL_NAMES
        from external_baseline.prepare import REPO, sha256
        LocalInferenceTests.setUpClass()
        self.addCleanup(LocalInferenceTests.doClassCleanups)
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            baseline = root/'external_artifacts/inference-bundle-v1'
            shutil.copytree(LocalInferenceTests.bundle, baseline)
            shutil.copytree(REPO/'external_baseline', root/'external_baseline', ignore=shutil.ignore_patterns('__pycache__'))
            (root/'evaluation').mkdir()
            shutil.copyfile(REPO/'evaluation/possession_metrics.py', root/'evaluation/possession_metrics.py')
            experiment = root/'experiment'; experiment.mkdir()
            x = np.random.default_rng(12).normal(size=(90,18))
            model = fit_baseline(x, np.array(['H','A','D']*30), np.ones(90,dtype=bool))
            joblib.dump(dict(model=model,feature_names=MODEL_NAMES), experiment/'model_C.joblib')
            sources = {p.relative_to(root).as_posix():sha256(p) for p in (root/'external_baseline').glob('*.py')}
            sources['evaluation/possession_metrics.py'] = sha256(root/'evaluation/possession_metrics.py')
            for name, value in {'protocol':dict(source_sha256=sources),'metrics':{},'diagnosis':{},
                                'selection':dict(selected='C', violations={'C':[]}),
                                'selected_decoder':parameters()}.items():
                (experiment/(name+'.json')).write_text(json.dumps(value))
            manifest = dict(status='ready',v2_version=2,source_sha256=sources,
                outputs_sha256={p.name:sha256(p) for p in experiment.iterdir()})
            (experiment/'manifest.json').write_text(json.dumps(manifest))
            bundle = root/'bundle2'
            with patch('external_baseline.inference_bundle.REPO', root):
                build_v2(experiment, bundle)
            self.assertEqual(len(verify_bundle(bundle)['feature_names']),18)
            meta, raw = root/'synthetic.xml', root/'synthetic.txt'
            meta.write_text(metadata_xml())
            raw.write_text(''.join(f'{i}:.4,.5;.5,.6:.5,.5\n' for i in range(1,9)))
            infer(bundle, meta, raw, root/'out', expected=8)
            import sqlite3
            with closing(sqlite3.connect(root/'out/features.sqlite')) as db:
                self.assertEqual(len(db.execute('PRAGMA table_info(features)').fetchall()),23)
                self.assertEqual(db.execute('SELECT ball_xy_age_s FROM features').fetchall(),[(0.0,)]*4)
            with (bundle/'model/decoder_parameters.json').open('a') as stream: stream.write(' ')
            with self.assertRaisesRegex(ValueError,'hash mismatch'): verify_bundle(bundle)

    def test_context_missing_causality_anonymous_slots_and_resets(self):
        f = ContextFeatureExtractor(100, 60)
        def extract(frame, entities, period=1, stamp=None):
            return f.extract(FrameKey('fixture', period, frame), frame*40000 if stamp is None else stamp, entities)
        self.assertIsNone(extract(0, [])['ball_xy_age_s'])
        entities = [EntityPosition('ball','BALL',0,0), EntityPosition('slot1','H',3,4)]
        a = extract(1, entities)
        self.assertEqual(a['nearest_home_median_1s'], 5)
        b = extract(2, [])
        self.assertIsNone(b['nearest_home_m'])
        self.assertEqual(b['ball_xy_age_s'], .04)
        self.assertAlmostEqual(b['ball_xy_fraction_1s'], 1/3)
        self.assertEqual(b['nearest_home_median_1s'], 5)
        for frame in range(3, 28): extract(frame, [])
        self.assertIsNone(extract(28, [])['nearest_home_median_1s'])
        self.assertIsNone(extract(30, [])['ball_xy_age_s'])
        extract(31, entities)
        self.assertIsNone(extract(32, [], period=2)['ball_xy_age_s'])
        extract(33, entities, period=2)
        self.assertIsNone(extract(34, [], period=2, stamp=999999)['ball_xy_age_s'])
        g = ContextFeatureExtractor(100, 60)
        renamed = [EntityPosition('ball','BALL',0,0), EntityPosition('other','H',3,4)]
        np.testing.assert_equal(list(g.extract(FrameKey('x',1,0),0,renamed).values()),
            list(ContextFeatureExtractor(100,60).extract(FrameKey('x',1,0),0,entities).values()))

    def test_weighted_decoder_bruteforce_and_v1_identity(self):
        from itertools import product
        p = parameters(); keys = [FrameKey('x',1,i) for i in range(4)]; stamps = [i*40000 for i in range(4)]
        probs = np.array([[.8,.1,.1],[.1,.8,.1],[.1,.2,.7],[.6,.3,.1]])
        before = copy.deepcopy(p)
        a = decode_probabilities(keys, stamps, probs, p)
        np.testing.assert_array_equal(a, decode_probabilities(keys, stamps, probs, dict(p,decoder_version=2,prior_correction=1)))
        self.assertEqual(p, before)
        for name, config in decoder_grid(p).items():
            alpha = config.get('prior_correction', 1); beta = config['transition_weight']
            def score(path):
                return np.log(p['initial_prior'][path[0]]) + sum(np.log(probs[i,s])-alpha*np.log(p['state_prior'][s]) for i,s in enumerate(path)) + beta*sum(np.log(p['transition_matrix'][u][v]) for u,v in zip(path,path[1:]))
            expected = max(product(range(3),repeat=4), key=score)
            actual = decode_probabilities(keys, stamps, probs, config)
            actual_path = [p['classes'].index(label) for label in actual]
            self.assertAlmostEqual(score(actual_path), score(expected), places=12, msg=name)

    def test_smoothing_can_destroy_true_short_possession_and_dead_ball(self):
        keys = [FrameKey('x',1,i) for i in range(9)]; stamps = [i*40000 for i in range(9)]
        for short in (1,2):
            probs = np.tile([.98,.01,.01], (9,1)); probs[4] = [.05,.05,.05]; probs[4,short] = .9
            result = decode_probabilities(keys, stamps, probs, parameters())
            self.assertEqual(np.argmax(probs[4]), short)
            self.assertEqual(result[4], 'H')
            # Splitting at a real gap must recover independently decoded runs.
            keys[4] = FrameKey('x',2,4)
            sub = decode_probabilities(keys[4:5], stamps[4:5], probs[4:5], parameters())
            self.assertEqual(sub[0], parameters()['classes'][short])
            keys[4] = FrameKey('x',1,4)

    def test_class_mapping_and_native_tie_order(self):
        class Model:
            classes_ = np.array(['D','A','H'])
            def predict_proba(self, x): return np.array([[.2,.3,.5],[.4,.4,.2]])
        labels, probs = predict_raw(Model(), np.zeros((2,14)))
        np.testing.assert_equal(probs, [[.5,.3,.2],[.2,.4,.4]])
        self.assertEqual(labels.tolist(), ['H','D'])

    def test_selection_rejects_stress_regression_and_accepts_boundary(self):
        keys = [FrameKey('x',1,i) for i in range(5)]
        m = evaluate_timeline(keys, [i*40000 for i in range(5)], ['H']*5, [True]*5, ['H']*5)
        def item(spell):
            result = copy.deepcopy(m); result['spell_f1_mean'] = spell
            return result
        def scenarios(spell):
            return {s: {h:item(spell) for h in ('overall','half_1','half_2')} for s in ('clean','ball_drop_iid20')}
        metrics = {'A':scenarios(.4), 'B_a1_b0.5':scenarios(.41)}
        self.assertEqual(select(metrics)['selected'], 'B_a1_b0.5')
        metrics['B_a1_b0.5']['ball_drop_iid20']['overall']['per_class']['D']['f1'] = -.02
        self.assertEqual(select(metrics)['selected'], 'A')


if __name__ == '__main__': unittest.main()
