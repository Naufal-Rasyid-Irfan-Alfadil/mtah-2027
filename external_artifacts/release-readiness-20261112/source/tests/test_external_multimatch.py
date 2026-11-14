"""Synthetic whole-match roles, no validation leakage, and immutable references."""

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

from external_baseline.multimatch import (aggregate_decoder, append_views,
    validate_partitions, validate_match, fit_pool, training_counts, run)
from external_baseline.augmented import TRAIN_SEED, build_training_pool
from external_baseline.robustness import SCENARIOS, stress_feature_matrices
from external_baseline.training import load_split
from external_baseline.temporal import estimate_markov, decode_probabilities
from external_baseline.prepare import sha256
from test_external_robustness import frozen_fixture


class MultimatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global np
        import numpy as np

    def test_counts_pool_before_smoothing_and_no_cross_half_transition(self):
        # Deliberately unequal class occupancy and different first/last labels.
        part = dict(decoder_version=1, classes=['H','A','D'], fps=25,
                    state_counts=[3,1,1], transition_counts=[[2,1,0],[0,0,1],[0,0,0]],
                    training_runs=1, pseudocount=1)
        second = dict(part, state_counts=[1,2,3],
                      transition_counts=[[0,0,0],[1,1,0],[0,1,2]])
        result = aggregate_decoder([part,second])
        self.assertEqual(result['state_counts'], [4,3,4])
        self.assertEqual(result['transition_counts'], [[2,1,0],[1,1,1],[0,1,2]])
        self.assertEqual(result['observed_transitions'], 9)
        np.testing.assert_allclose(result['state_prior'], [5/14,4/14,5/14])
        np.testing.assert_allclose(result['transition_matrix'][0], [3/6,2/6,1/6])
        self.assertEqual(result['training_runs'], 2)

    def fixture(self, root):
        base = root/'base'
        base.mkdir()
        o,f,t,c,d = frozen_fixture(base)
        # Synthetic reference carries the declared augmentation identity.
        manifest_path = c/'manifest.json'
        cm = json.loads(manifest_path.read_text())
        cm['config']['training_augmentation'] = dict(views=SCENARIOS, training_seed=TRAIN_SEED)
        manifest_path.write_text(json.dumps(cm))
        pairs = []
        for name in ('synthetic-a','synthetic-b','synthetic-v'):
            dest = root/name
            prepared, features = dest/'prepared', dest/'features'
            shutil.copytree(t.parent, prepared)
            shutil.copytree(f.parent, features)
            for path, tables in ((prepared/'observations.sqlite', ('frames','observations')),
                                 (prepared/'targets.sqlite', ('targets',)),
                                 (features/'features.sqlite', ('features',))):
                with closing(sqlite3.connect(path)) as db:
                    for table in tables:
                        db.execute(f'UPDATE {table} SET match_id=?', (name,))
                    if 'frames' in tables:
                        meta=json.loads(db.execute('SELECT json FROM metadata').fetchone()[0])
                        meta['match_id']=name
                        db.execute('UPDATE metadata SET json=?', (json.dumps(meta),))
                    db.commit()
            pm = json.loads((prepared/'manifest.json').read_text())
            pm.update(match=dict(match_id=name), config=dict(fps=25, coordinate_unit='m', origin='pitch_center'))
            (prepared/'manifest.json').write_text(json.dumps(pm))
            fm = json.loads((features/'manifest.json').read_text())
            from external_baseline.features import FEATURE_UNITS
            fm.update(units=FEATURE_UNITS)
            fm['input'].update(parent_manifest_sha256=sha256(prepared/'manifest.json'),
                               sha256=sha256(prepared/'observations.sqlite'))
            fm['output_sha256']=sha256(features/'features.sqlite')
            (features/'manifest.json').write_text(json.dumps(fm))
            pairs.append((prepared,features))
        return pairs,c,d

    def test_pool_half1_equals_legacy_and_half2_keeps_valid_source_labels(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            pairs,c,d=self.fixture(root)
            for period in (1,2):
                p,f=pairs[0]
                data=load_split(f/'features.sqlite',p/'targets.sqlite',period)
                replay=stress_feature_matrices(p/'observations.sqlite',period=period,seed=TRAIN_SEED)
                xp,yp=root/f'x{period}',root/f'y{period}'
                with xp.open('wb') as xf,yp.open('wb') as yf:
                    audit=append_views(data,replay,xf,yf)
                y=np.fromfile(yp,dtype='U1')
                self.assertEqual(len(y),sum(v['fitted_rows'] for v in audit['views'].values()))
                self.assertNotIn(None,y)
                self.assertEqual(audit['period'],period)
                if period==1:
                    x0,y0,_,_=build_training_pool(data,replay)
                    np.testing.assert_array_equal(np.fromfile(xp,dtype=float).reshape(-1,14),x0)
                    np.testing.assert_array_equal(y,y0)
                    self.assertEqual(aggregate_decoder([training_counts(data[0],data[1],data[3],data[4])]),
                                     estimate_markov(data[0],data[1],data[3],data[4]))
                else:
                    self.assertEqual(audit['original_frames'],60)
                    self.assertEqual(audit['valid_frames'],59)
            replay[2]['clean'][0,0]=99
            with (root/'badx').open('wb') as xf,(root/'bady').open('wb') as yf:
                with self.assertRaisesRegex(ValueError,'replay'):
                    append_views(data,replay,xf,yf)

    def test_whole_match_integration_leakage_reproduction_and_failure(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            pairs,c,d=self.fixture(root)
            before={p:sha256(p) for p in (c/'model.joblib',d/'decoder_parameters.json',pairs[0][0]/'targets.sqlite')}
            with patch('external_baseline.multimatch.fit_pool',wraps=fit_pool) as fit, \
                 patch('external_baseline.multimatch.training_counts',wraps=training_counts) as counted, \
                 patch('external_baseline.multimatch.decode_probabilities',wraps=decode_probabilities) as decoded:
                def checked(f,t,period):
                    if Path(t).parent==pairs[2][0]:
                        self.assertEqual(decoded.call_count,4)
                        self.assertEqual(fit.call_count,1)
                        self.assertEqual(counted.call_count,4)
                    return load_split(f,t,period)
                with patch('external_baseline.multimatch.load_split',side_effect=checked):
                    report=run(pairs[:2],pairs[2],c,d,root/'one')
                self.assertEqual(fit.call_count,1)
            manifest=json.loads((root/'one'/'manifest.json').read_text())
            self.assertEqual(manifest['status'],'ready')
            self.assertEqual(manifest['protocol']['training'],['synthetic-a','synthetic-b'])
            self.assertEqual(manifest['fitted_samples'],2*(599+389))
            self.assertFalse(manifest['early_stopping_used'])
            self.assertEqual(manifest['model_iterations'],100)
            params=json.loads((root/'one'/'decoder_parameters.json').read_text())
            self.assertEqual(params['valid_training_frames'],2*(89+59))
            self.assertEqual(params['training_runs'],8)
            self.assertEqual(report['decoded']['expanded']['n_graded'],148)
            with closing(sqlite3.connect(root/'one'/'predictions.sqlite')) as db:
                self.assertEqual(db.execute('SELECT COUNT(*) FROM predictions').fetchone()[0],300)
                self.assertEqual(db.execute('SELECT DISTINCT split FROM predictions').fetchall(),[('validation',)])
            self.assertEqual(before,{p:sha256(p) for p in before})
            for name,digest in manifest['outputs_sha256'].items():
                self.assertEqual(sha256(root/'one'/name),digest)
            # Change ONLY validation labels/masks. Fitted pool, parameters and
            # all predictions must remain byte-identical; scores may differ.
            with closing(sqlite3.connect(pairs[2][0]/'targets.sqlite')) as db:
                db.execute("UPDATE targets SET label='D',valid_target=1")
                db.commit()
            run(pairs[:2],pairs[2],c,d,root/'two')
            for name in ('training-X.bin','training-y.bin','decoder_parameters.json','predictions.sqlite','model.joblib'):
                self.assertEqual(sha256(root/'one'/name),sha256(root/'two'/name))
            with self.assertRaises(FileExistsError):
                run(pairs[:2],pairs[2],c,d,root/'one')
            with patch('external_baseline.multimatch.fit_pool',side_effect=RuntimeError('synthetic fit failure')):
                with self.assertRaisesRegex(RuntimeError,'synthetic fit failure'):
                    run(pairs[:2],pairs[2],c,d,root/'failed')
            self.assertFalse((root/'failed'/'manifest.json').exists())
            self.assertTrue((root/'failed'/'FAILED.json').exists())

    def test_partition_and_lineage_rejection(self):
        a=dict(match_id='a',features=Path('a'),targets=Path('at'))
        b=dict(match_id='b',features=Path('b'),targets=Path('bt'))
        validate_partitions([a],b)
        for train,val in (([a],a),([a,a],b),([b,a],dict(b,match_id='v'))):
            with self.assertRaises(ValueError):validate_partitions(train,val)
        with tempfile.TemporaryDirectory() as folder:
            pairs,c,d=self.fixture(Path(folder))
            p,f=pairs[0]
            validate_match(p,f)
            with (f/'features.sqlite').open('ab') as stream:stream.write(b'changed')
            with self.assertRaisesRegex(ValueError,'hash'):
                validate_match(p,f)

    def test_import_help_without_data_or_model_imports(self):
        script='''import sys,runpy
def audit(event,args):
    if event in ('open','sqlite3.connect'):
        p=str(args[0]).replace(chr(92),'/').lower()
        if any(s in p for s in ('/data/','/external_artifacts/','/evaluation/gt/','/evaluation/results/')) or p.endswith(('.sqlite','.xml','.csv','.mp4','.joblib')):
            raise RuntimeError('forbidden data access: '+p)
sys.addaudithook(audit)
import external_baseline.multimatch
assert not any(m in sys.modules for m in ('numpy','pandas','sklearn','joblib'))
sys.argv=['multimatch','--help']
runpy.run_module('external_baseline.multimatch',run_name='__main__')
'''
        result=subprocess.run([sys.executable,'-B','-c',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':
    unittest.main()
