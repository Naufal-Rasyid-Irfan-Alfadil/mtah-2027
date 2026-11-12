"""Risk-focused synthetic coverage routing and evaluated-source binding tests."""
import json
from pathlib import Path
import tempfile
import shutil
import subprocess
import sys
import copy
import unittest
from unittest.mock import patch

import numpy as np
from external_baseline.observation_router import CoverageRouter, MODEL_NAMES, reliable_rows
from external_baseline.training import HGB_PARAMS, predict_raw
from external_baseline.inference_bundle import verify_experiment_sources, build_v2, load_bundle
from external_baseline.prepare import sha256, REPO


class Component:
    def __init__(self,n,posterior):
        self.n_features_in_=n
        self.classes_=np.array(['D','H','A'])
        self.posterior=posterior
    def get_params(self): return HGB_PARAMS.copy()
    def predict_proba(self,x):
        assert x.shape[1]==self.n_features_in_
        return np.tile(self.posterior,(len(x),1))


class RouterTests(unittest.TestCase):
    def test_selection_preserves_guards_and_rejects_incomplete_or_nan_scores(self):
        from external_baseline.v2_refinement import select_refinement,SCENARIO_NAMES
        from external_baseline.training import evaluate_timeline
        from external_baseline.contracts import FrameKey
        labels=['H']*3+['D']*3+['A']*3
        base=evaluate_timeline([FrameKey('synthetic',1,i) for i in range(9)],
                              [i*40000 for i in range(9)],labels,[True]*9,labels)
        base['spell_f1_mean']=.4
        a={s:{h:copy.deepcopy(base) for h in ('overall','half_1','half_2')} for s in SCENARIO_NAMES}
        r=copy.deepcopy(a)
        for h in r['clean']:r['clean'][h]['spell_f1_mean']=.41
        self.assertEqual(select_refinement(dict(A=copy.deepcopy(a),R=copy.deepcopy(r)))['selected'],'R')
        r['player_drop_iid20']['overall']['transitions'][12]['f1']-=.011
        self.assertEqual(select_refinement(dict(A=copy.deepcopy(a),R=copy.deepcopy(r)))['selected'],'A')
        del r['clean']['half_1']
        with self.assertRaises(ValueError):select_refinement(dict(A=a,R=r))
        r=copy.deepcopy(a);r['clean']['overall']['spell_f1_mean']=float('nan')
        with self.assertRaises(ValueError):select_refinement(dict(A=a,R=r))

    def test_router_packaged_roundtrip_and_assessment_required(self):
        import joblib
        from test_local_inference import LocalInferenceTests, metadata_xml
        from external_baseline.training import fit_baseline
        from external_baseline.atd_inference import run
        LocalInferenceTests.setUpClass();self.addCleanup(LocalInferenceTests.doClassCleanups)
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            baseline=root/'external_artifacts/inference-bundle-v1'
            shutil.copytree(LocalInferenceTests.bundle,baseline)
            shutil.copytree(REPO/'external_baseline',root/'external_baseline',ignore=shutil.ignore_patterns('__pycache__'))
            (root/'evaluation').mkdir();shutil.copyfile(REPO/'evaluation/possession_metrics.py',root/'evaluation/possession_metrics.py')
            model_a,_=load_bundle(baseline)
            x=np.random.default_rng(3).normal(size=(90,18))
            model_c=fit_baseline(x,np.array(['H','A','D']*30),np.ones(90,dtype=bool))
            router=CoverageRouter(model_a,model_c,11,11)
            experiment=root/'experiment';experiment.mkdir()
            joblib.dump(dict(model=router,feature_names=MODEL_NAMES),experiment/'model_R.joblib')
            sources={p.relative_to(root).as_posix():sha256(p) for p in (root/'external_baseline').glob('*.py')}
            sources['evaluation/possession_metrics.py']=sha256(root/'evaluation/possession_metrics.py')
            for name,value in {'protocol':dict(source_sha256=sources,algorithm='coverage_router_v1',routing=dict(home_reference=11,away_reference=11)),
                'metrics':{},'diagnosis':{},'selection':dict(selected='R',violations={'R':[]}),
                'selected_decoder':json.loads((baseline/'model/decoder_parameters.json').read_text())}.items():
                (experiment/(name+'.json')).write_text(json.dumps(value))
            manifest=dict(status='ready',v2_version=2,source_sha256=sources,
                          outputs_sha256={p.name:sha256(p) for p in experiment.iterdir()})
            (experiment/'manifest.json').write_text(json.dumps(manifest))
            assessment=root/'assessment';assessment.mkdir()
            for name in ('protocol','metrics','decision'):(assessment/(name+'.json')).write_text('{}')
            am=dict(status='ready',release_passed=True,source_sha256=sources,
                    experiment_manifest_sha256=sha256(experiment/'manifest.json'),
                    outputs_sha256={p.name:sha256(p) for p in assessment.iterdir()})
            (assessment/'manifest.json').write_text(json.dumps(am))
            with patch('external_baseline.inference_bundle.REPO',root):
                with self.assertRaisesRegex(ValueError,'assessment required'):build_v2(experiment,root/'failed')
                self.assertFalse((root/'failed').exists())
                build_v2(experiment,root/'bundle',assessment)
            loaded,_=load_bundle(root/'bundle')
            np.testing.assert_array_equal(loaded.predict_proba(x),router.predict_proba(x))
            meta,raw=root/'synthetic.xml',root/'synthetic.txt'
            meta.write_text(metadata_xml());raw.write_text(''.join(f'{i}:.4,.5;.5,.6:.5,.5\n' for i in range(1,9)))
            run(root/'bundle',meta,raw,root/'out',expected=8)
            self.assertEqual(json.loads((root/'out/manifest.json').read_text())['status'],'ready')

    def test_unreliable_observations_use_baseline_without_class_permutation(self):
        x=np.zeros((6,18));x[:,MODEL_NAMES.index('ball_xy_fraction_1s')]=1
        x[:,MODEL_NAMES.index('home_xy_observed')]=11
        x[:,MODEL_NAMES.index('away_xy_observed')]=11
        x[1,MODEL_NAMES.index('ball_xy_fraction_1s')]=24/25
        x[2,MODEL_NAMES.index('home_xy_observed')]=10
        x[3,MODEL_NAMES.index('away_xy_observed')]=np.nan
        x[4,MODEL_NAMES.index('ball_xy_fraction_1s')]=np.nan
        before=x.copy()
        router=CoverageRouter(Component(14,[.8,.1,.1]),Component(18,[.1,.8,.1]),11,11)
        labels,probs=predict_raw(router,x)
        self.assertEqual(labels.tolist(),['H','D','D','D','D','H'])
        np.testing.assert_array_equal(probs[[1,2,3,4]],np.tile([.1,.1,.8],(4,1)))
        np.testing.assert_array_equal(x,before)
        self.assertFalse(hasattr(router,'fit'))
        self.assertEqual(router.predict_proba(np.empty((0,18))).shape,(0,3))

    def test_invalid_contract_and_reference_rejected(self):
        with self.assertRaises(ValueError): reliable_rows(np.zeros((2,14)),11,11)
        with self.assertRaises(ValueError): reliable_rows(np.zeros((2,18)),np.nan,11)
        with self.assertRaises(ValueError): CoverageRouter(Component(18,[.3,.3,.4]),Component(18,[.3,.3,.4]),11,11)

    def test_changed_or_added_source_cannot_be_packaged_as_evaluated(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);(root/'external_baseline').mkdir();(root/'evaluation').mkdir()
            module=root/'external_baseline/algorithm.py';module.write_text('value = 1\n')
            metric=root/'evaluation/possession_metrics.py';metric.write_text('metric = 1\n')
            sources={p.relative_to(root).as_posix():sha256(p) for p in (module,metric)}
            windows={k.replace('/','\\'):v for k,v in sources.items()}
            experiment=root/'experiment';experiment.mkdir()
            (experiment/'protocol.json').write_text(json.dumps(dict(source_sha256=windows)))
            manifest=dict(source_sha256=windows)
            with patch('external_baseline.inference_bundle.REPO',root):
                self.assertEqual(verify_experiment_sources(experiment,manifest),sources)
                module.write_text('value = 2\n')
                with self.assertRaisesRegex(ValueError,'source differs'): verify_experiment_sources(experiment,manifest)
                module.write_text('value = 1\n')
                (root/'external_baseline/new_algorithm.py').write_text('value = 3\n')
                with self.assertRaisesRegex(ValueError,'source differs'): verify_experiment_sources(experiment,manifest)

    def test_guard_denies_official_directory_even_for_listing(self):
        script='''from external_baseline.external_guard import install,ROOT
import os
install()
p=ROOT/'external_artifacts/inference-bundle-v1/tactical'
for operation in (lambda: open(p/'do-not-open.xml'),lambda: os.listdir(p),lambda: os.scandir(p)):
    try: operation()
    except PermissionError: pass
    else: raise AssertionError('official access was not blocked')
'''
        result=subprocess.run([sys.executable,'-B','-c',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__': unittest.main()
