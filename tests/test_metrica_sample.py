"""Manual unit/frame examples and synthetic frozen-model sample CSV inference."""
from contextlib import closing
import csv
import importlib.metadata
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from external_baseline import metrica_sample as sample
from external_baseline.features import FrameFeatureExtractor
from external_baseline.prepare import sha256, REPO
from external_baseline.training import FEATURE_SETS, HGB_PARAMS, PACKAGES, fit_baseline


def csv_fixture(path, team, rows):
    with path.open('w',newline='') as stream:
        writer=csv.writer(stream)
        writer.writerow(['','','',team,'',team,'','',''])
        writer.writerow(['','','','1','','2','','',''])
        writer.writerow(['Period','Frame','Time [s]','Player1','','Player2','','Ball',''])
        for period,frame,stamp,bx,by in rows:
            writer.writerow([period,frame,stamp,.5+3/105,.5-4/68,'NaN','NaN',bx,by])


class MetricaSampleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        global np
        import numpy as np
        import joblib
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        cls.snapshot=Path(cls.temp.name)/'snapshot';cls.snapshot.mkdir()
        model=fit_baseline(np.zeros((90,14)),np.asarray(['H','A','D']*30),np.ones(90,dtype=bool))
        joblib.dump(dict(model=model,feature_names=FEATURE_SETS['no-signed-position']),cls.snapshot/'model.joblib')
        sample.write_json(cls.snapshot/'parameters.json',dict(decoder_version=1,classes=['H','A','D'],fps=25,
            state_prior=[1/3]*3,initial_prior=[1/3]*3,transition_matrix=[[.98,.01,.01],[.01,.98,.01],[.01,.01,.98]],
            emission_weight=1,transition_weight=1))
        candidate=dict(display_name='synthetic',feature_names=FEATURE_SETS['no-signed-position'],hgb_params=HGB_PARAMS,
                       model_file='model.joblib',model_sha256=sha256(cls.snapshot/'model.joblib'),
                       parameters_file='parameters.json',parameters_sha256=sha256(cls.snapshot/'parameters.json'))
        sample.write_json(cls.snapshot/'protocol.json',dict(status='ready',primary='augmented',candidates=dict(augmented=candidate),
            source_sha256={'external_baseline/features.py':sha256(REPO/'external_baseline/features.py')},
            packages={p:importlib.metadata.version(p) for p in PACKAGES}))
        sample.write_json(cls.snapshot/'snapshot_manifest.json',dict(status='ready',files_sha256={p.name:sha256(p) for p in cls.snapshot.iterdir()}))

    def test_unit_conversion_missing_outside_and_relative_time(self):
        self.assertEqual(sample.coordinate('0',105),-52.5)
        self.assertEqual(sample.coordinate('1',105),52.5)
        self.assertEqual(sample.coordinate('0',68,True),34)
        self.assertEqual(sample.coordinate('1',68,True),-34)
        self.assertAlmostEqual(sample.coordinate('1.1',105),63)
        for value in ('','NaN','inf','-inf'):
            self.assertIsNone(sample.coordinate(value,105))
        with self.assertRaises(ValueError):sample.coordinate('broken',105)
        self.assertEqual(sample.time_us('0.04'),40000)
        for stamp in ('NaN','-0.04','0.0000001','bad'):
            with self.assertRaises(ValueError):sample.time_us(stamp)

    def test_manual_distance_speed_and_gap_half_resets_without_roster_fill(self):
        with tempfile.TemporaryDirectory() as folder:
            home,away=Path(folder)/'h.csv',Path(folder)/'a.csv'
            rows=[(1,1,'.04',.5,.5),(1,2,'.08',.5+.2/105,.5),(1,4,'.16',.6,.5),(2,100,'4',.6,.5)]
            csv_fixture(home,'Home',rows);csv_fixture(away,'Away',rows)
            frames=list(sample.merged_frames(home,away,'s'))
            extractor=FrameFeatureExtractor(105,68)
            values=[extractor.extract(k,t,e) for k,t,e in frames]
            self.assertEqual([(k.period,k.source_frame) for k,t,e in frames],[(1,1),(1,2),(1,4),(2,100)])
            self.assertEqual(values[0]['home_records'],1)
            self.assertEqual(values[0]['away_records'],1)
            self.assertAlmostEqual(values[0]['nearest_home_m'],5)
            self.assertAlmostEqual(values[1]['ball_speed_mps'],5)
            for i in (0,2,3):self.assertIsNone(values[i]['ball_speed_mps'])

    def test_union_missing_team_and_duplicate_ball_conflicts(self):
        with tempfile.TemporaryDirectory() as folder:
            h,a=Path(folder)/'h.csv',Path(folder)/'a.csv'
            rows=[(1,1,'.04',.5,.5),(1,2,'.08','NaN','NaN'),(1,3,'.12',.5,.5)]
            csv_fixture(h,'Home',rows);csv_fixture(a,'Away',[rows[0],rows[2]])
            frames=list(sample.merged_frames(h,a,'s'))
            self.assertEqual(len(frames),3)
            value=FrameFeatureExtractor(105,68).extract(*frames[1])
            self.assertEqual(value['away_records'],0)
            self.assertEqual(value['ball_record_present'],1)
            self.assertEqual(value['ball_xy_observed'],0)
            self.assertIsNone(value['nearest_home_m'])
            csv_fixture(a,'Away',[(1,1,'.04',.51,.5)])
            with self.assertRaisesRegex(ValueError,'disagree'):list(sample.merged_frames(h,a,'s'))
            csv_fixture(h,'Home',[(1,1,'.04',.5,.5)])
            csv_fixture(a,'Away',[(1,2,'.12',.5,.5)])
            with self.assertRaisesRegex(ValueError,'25 Hz'):list(sample.merged_frames(h,a,'s'))
            csv_fixture(a,'Away',[(1,1,'.08',.5,.5)])
            with self.assertRaisesRegex(ValueError,'disagree'):list(sample.merged_frames(h,a,'s'))

    def test_invalid_fps_duplicates_order_header_and_partial_axes(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'h.csv'
            for rows in ([(1,1,'.04',.5,.5),(1,2,'.073333',.5,.5)],
                         [(1,1,'.04',.5,.5),(1,1,'.04',.5,.5)],[(2,1,'.04',.5,.5),(1,2,'.08',.5,.5)]):
                csv_fixture(p,'Home',rows)
                with self.assertRaises(ValueError):list(sample.tracking_rows(p,'H'))
            csv_fixture(p,'Away',[(1,1,'.04',.5,.5)])
            with self.assertRaisesRegex(ValueError,'team'):list(sample.tracking_rows(p,'H'))
            csv_fixture(p,'Home',[(1,1,'.04','NaN',.7)])
            key,stamp,entities,ball=next(sample.tracking_rows(p,'H'))
            self.assertIsNone(ball[0]);self.assertAlmostEqual(ball[1],-13.6)
            with p.open() as f:rows=list(csv.reader(f))
            rows[3][4]='NaN' # partially observed player still counts as present
            with p.open('w',newline='') as f:csv.writer(f).writerows(rows)
            a=Path(folder)/'a.csv'
            csv_fixture(a,'Away',[(1,1,'.04','NaN',.7)])
            value=FrameFeatureExtractor(105,68).extract(*next(sample.merged_frames(p,a,'s')))
            self.assertEqual(value['home_records'],1)
            self.assertEqual(value['home_xy_observed'],0)
            self.assertIsNone(value['nearest_home_m'])
            with self.assertRaisesRegex(ValueError,'team'):
                list(sample.merged_frames(p,p,'s'))
            # Sample Game 2's literal "Player 26" spelling is equivalent to
            # the jersey ID; whitespace must not change geometry or counts.
            with p.open() as f:rows=list(csv.reader(f))
            rows[2][3]='Player 1'
            with p.open('w',newline='') as f:csv.writer(f).writerows(rows)
            self.assertEqual(next(sample.tracking_rows(p,'H'))[2][0].entity_id,'H:Player1')

    def test_inference_no_fit_no_metrics_reproducibility_and_failed_readiness(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);h,a=root/'h.csv',root/'a.csv'
            rows=[(1,1,'.04',.5,.5),(1,2,'.08','NaN','NaN'),(2,100,'4',.6,.5),(2,101,'4.04',.6,.5)]
            csv_fixture(h,'Home',rows);csv_fixture(a,'Away',rows)
            # Events are intentionally unusable and must never be read.
            (root/'events.csv').write_text('NOT GROUND TRUTH')
            before=[sha256(p) for p in (h,a,self.snapshot/'model.joblib',self.snapshot/'parameters.json')]
            with patch('sklearn.ensemble.HistGradientBoostingClassifier.fit',side_effect=AssertionError('no fitting')), \
                 patch('external_baseline.training.evaluate_timeline',side_effect=AssertionError('no GT metrics')):
                report=sample.run(h,a,self.snapshot,root/'one','synthetic')
                (root/'events.csv').write_text('CHANGED EVENTS MUST NOT AFFECT PREDICTIONS')
                sample.run(h,a,self.snapshot,root/'two','synthetic')
            self.assertEqual(report['frames'],4)
            self.assertEqual(report['evaluation_status'],'not_scored_no_dense_possession_GT')
            for name in ('features.sqlite','predictions.sqlite','predictions.csv'):
                self.assertEqual(sha256(root/'one'/name),sha256(root/'two'/name))
            self.assertEqual(before,[sha256(p) for p in (h,a,self.snapshot/'model.joblib',self.snapshot/'parameters.json')])
            with closing(sqlite3.connect(root/'one/predictions.sqlite')) as db:
                self.assertEqual(db.execute('SELECT period,source_frame,time_us FROM predictions ORDER BY period,source_frame').fetchall(),[(1,1,40000),(1,2,80000),(2,100,4000000),(2,101,4040000)])
            manifest=json.loads((root/'one/manifest.json').read_text())
            for name,digest in manifest['outputs_sha256'].items():self.assertEqual(sha256(root/'one'/name),digest)
            with self.assertRaises(FileExistsError):sample.run(h,a,self.snapshot,root/'one','synthetic')
            csv_fixture(a,'Away',[(1,1,'.04',.8,.5)])
            with self.assertRaisesRegex(ValueError,'disagree'):sample.run(h,a,self.snapshot,root/'failed','synthetic')
            self.assertTrue((root/'failed/FAILED.json').exists());self.assertFalse((root/'failed/manifest.json').exists())

    def test_tampered_snapshot_and_import_help_without_data_access(self):
        with tempfile.TemporaryDirectory() as folder:
            s=Path(folder)/'snapshot';shutil.copytree(self.snapshot,s)
            with (s/'model.joblib').open('ab') as f:f.write(b'bad')
            with self.assertRaisesRegex(ValueError,'hash'):sample.frozen_candidate(s)
        script='''import sys,runpy
def audit(event,args):
    if event in ('open','sqlite3.connect'):
        p=str(args[0]).replace(chr(92),'/').lower()
        if p.endswith(('.csv','.json','.sqlite','.xml','.mp4','.joblib')) or '/data/' in p:
            raise RuntimeError('unexpected data access: '+p)
sys.addaudithook(audit)
import external_baseline.metrica_sample
assert not any(m in sys.modules for m in ('numpy','pandas','sklearn','joblib'))
sys.argv=['metrica_sample','--help']
runpy.run_module('external_baseline.metrica_sample',run_name='__main__')
'''
        result=subprocess.run([sys.executable,'-B','-c',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':unittest.main()
