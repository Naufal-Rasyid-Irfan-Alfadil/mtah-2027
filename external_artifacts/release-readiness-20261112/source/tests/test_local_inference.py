"""Synthetic-only bundle portability and tactical contract; no official inputs."""
from contextlib import closing
import csv
import json
from pathlib import Path
import shutil
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from external_baseline import atd_inference as atd
from external_baseline.inference_bundle import build,verify_bundle,load_bundle
from external_baseline.prepare import sha256,REPO
from external_baseline.features import FrameFeatureExtractor
from external_baseline.contracts import FrameKey
import test_metrica_sample as sample_tests


def metadata_xml(end=8,periods=((2,3),(6,7))):
    """Roster deliberately reversed; channel specs, not roster order, assign slots."""
    return f'''<main><Metadata><GlobalConfig><FrameRate>25</FrameRate><ProviderGlobalParameters>
    <ProviderParameter><Name>first_half_start</Name><Value>{periods[0][0]}</Value></ProviderParameter>
    <ProviderParameter><Name>first_half_end</Name><Value>{periods[0][1]}</Value></ProviderParameter>
    <ProviderParameter><Name>second_half_start</Name><Value>{periods[1][0]}</Value></ProviderParameter>
    <ProviderParameter><Name>second_half_end</Name><Value>{periods[1][1]}</Value></ProviderParameter>
    </ProviderGlobalParameters></GlobalConfig><Sessions><Session><MatchParameters><Score idLocalTeam="home" idVisitingTeam="away"/></MatchParameters>
    <FieldSize><Width>105</Width><Height>68</Height></FieldSize></Session></Sessions>
    <Teams><Team id="away"/><Team id="home"/></Teams><Players><Player id="a" teamId="away"/><Player id="h" teamId="home"/></Players>
    <Sensors><Sensor><Channels><Channel id="x"><Unit>normalized</Unit></Channel><Channel id="y"><Unit>normalized</Unit></Channel></Channels></Sensor></Sensors>
    <PlayerChannels><PlayerChannel id="hx" playerId="h" channelId="x"/><PlayerChannel id="hy" playerId="h" channelId="y"/>
    <PlayerChannel id="ax" playerId="a" channelId="x"/><PlayerChannel id="ay" playerId="a" channelId="y"/></PlayerChannels>
    </Metadata><DataFormatSpecifications><DataFormatSpecification startFrame="1" endFrame="{end}" separator=":">
    <StringRegister name="frameCount"/><SplitRegister separator=";"><SplitRegister separator=","><PlayerChannelRef playerChannelId="hx"/><PlayerChannelRef playerChannelId="hy"/></SplitRegister>
    <SplitRegister separator=","><PlayerChannelRef playerChannelId="ay"/><PlayerChannelRef playerChannelId="ax"/></SplitRegister></SplitRegister>
    <SplitRegister separator=","><BallChannelRef channelId="x"/><BallChannelRef channelId="y"/></SplitRegister>
    </DataFormatSpecification></DataFormatSpecifications></main>'''


class LocalInferenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp=tempfile.TemporaryDirectory();cls.addClassCleanup(cls.temp.cleanup)
        cls.root=Path(cls.temp.name)
        # Existing helper makes a tiny three-class synthetic model only.
        sample_tests.MetricaSampleTests.setUpClass()
        cls.addClassCleanup(sample_tests.MetricaSampleTests.doClassCleanups)
        cls.snapshot=cls.root/'snapshot';shutil.copytree(sample_tests.MetricaSampleTests.snapshot,cls.snapshot)
        for name in ('requirements-multimatch-training.txt','requirements-external-training.txt'):
            shutil.copyfile(REPO/name,cls.snapshot/name)
        cls.bundle=cls.root/'bundle'
        build(cls.snapshot,cls.bundle)

    def test_metadata_channel_order_team_roles_and_missing_outside(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);meta=p/'synthetic.xml';raw=p/'synthetic.txt'
            meta.write_text(metadata_xml())
            m=atd.metadata(meta)
            self.assertEqual((m['home_id'],m['away_id']),('home','away'))
            # First slot H at (+3,+4); second slot uses declared y,x order.
            h=f'{.5+3/105},{.5-4/68}';a=f'{.5},{1.1}'
            raw.write_text(''.join(f'{i}:{h};{a}:'+('NaN,NaN' if i==2 else '.5,.5')+'\n' for i in range(1,9)))
            frames=list(atd.frames(raw,m,8))
            self.assertEqual([v[0] for v in frames],list(range(8)))
            self.assertEqual([v[1] for v in frames],[None,1,1,None,None,2,2,None])
            values=FrameFeatureExtractor(105,68).extract(FrameKey('s',1,0),0,frames[0][3])
            self.assertAlmostEqual(values['nearest_home_m'],5)
            self.assertAlmostEqual(values['nearest_away_m'],63)
            self.assertEqual(values['ball_inside_pitch'],1)
            values=FrameFeatureExtractor(105,68).extract(FrameKey('s',1,1),40000,frames[1][3])
            self.assertEqual(values['ball_record_present'],1)
            self.assertEqual(values['ball_xy_observed'],0)
            self.assertIsNone(atd.normalized_pair('NaN',['x','y'],105,68))
            self.assertEqual(atd.normalized_pair('NaN,NaN',['x','y'],105,68),(None,None))

    def test_declared_layout_switch_no_roster_slot_inference(self):
        import xml.etree.ElementTree as ET
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);meta=p/'s.xml';raw=p/'s.txt'
            root=ET.fromstring(metadata_xml());spec=root.find('./DataFormatSpecifications/DataFormatSpecification')
            spec.set('endFrame','4')
            second=ET.fromstring(ET.tostring(spec));second.set('startFrame','5');second.set('endFrame','8')
            groups=second.find("SplitRegister[@separator=';']")
            groups[:]=list(reversed(list(groups)))
            root.find('DataFormatSpecifications').append(second);ET.ElementTree(root).write(meta)
            m=atd.metadata(meta)
            raw.write_text(''.join(f'{i}:'+('.5,.5;.5,.6' if i<5 else '.5,.6;.5,.5')+':.5,.5\n' for i in range(1,9)))
            f=list(atd.frames(raw,m,8))
            self.assertEqual([e.team for e in f[0][3]][:2],['H','A'])
            self.assertEqual([e.team for e in f[4][3]][:2],['A','H'])

    def test_invalid_schema_units_fps_scope_and_raw_alignment(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);meta=p/'s.xml';raw=p/'s.txt'
            for text in (metadata_xml().replace('<FrameRate>25','<FrameRate>30'),
                         metadata_xml().replace('<Unit>normalized','<Unit>metres'),
                         metadata_xml(periods=((2,6),(6,7))),
                         metadata_xml().replace('<Name>first_half_start</Name>','<Name>unknown</Name>')):
                meta.write_text(text)
                with self.assertRaises(ValueError):atd.metadata(meta)
            meta.write_text(metadata_xml());m=atd.metadata(meta)
            for text in ('1:NaN;NaN:NaN\n3:NaN;NaN:NaN\n','1:NaN:NaN\n','0:NaN;NaN:NaN\n','1:NaN;NaN:NaN\n'):
                raw.write_text(text)
                with self.assertRaises(ValueError):list(atd.frames(raw,m,8))

    def test_bundle_portable_and_tamper_rejected_before_loading(self):
        verify_bundle(self.bundle,True)
        model,parameters=load_bundle(self.bundle)
        self.assertEqual(model.n_features_in_,14)
        with tempfile.TemporaryDirectory() as folder:
            moved=Path(folder)/'portable';shutil.copytree(self.bundle,moved)
            result=subprocess.run([sys.executable,'-B',str(moved/'verify_bundle.py'),'--runtime'],cwd=folder,capture_output=True,text=True,env={'PATH':str(Path(sys.executable).parent)})
            self.assertEqual(result.returncode,0,result.stderr)
            result=subprocess.run([sys.executable,'-B',str(moved/'run_tactical.py'),'--help'],cwd=folder,capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            with (moved/'model/model.joblib').open('ab') as f:f.write(b'bad')
            with patch('joblib.load',side_effect=AssertionError('must fail before deserialization')):
                with self.assertRaisesRegex(ValueError,'hash'):load_bundle(moved)
        with self.assertRaises(FileExistsError):build(self.snapshot,self.bundle)

    def test_full_199319_submission_contract_no_fit_no_gt_and_reproduction(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);meta=p/'synthetic.xml';raw=p/'synthetic.txt'
            meta.write_text(metadata_xml(end=199319))
            with raw.open('w') as f:
                for i in range(1,199320):f.write(f'{i}:NaN;NaN:NaN\n')
            before=[sha256(v) for v in (meta,raw,self.bundle/'model/model.joblib',self.bundle/'model/decoder_parameters.json')]
            with patch('sklearn.ensemble.HistGradientBoostingClassifier.fit',side_effect=AssertionError('no fit')), \
                 patch('external_baseline.training.evaluate_timeline',side_effect=AssertionError('no GT')):
                report=atd.run(self.bundle,meta,raw,p/'one')
                atd.run(self.bundle,meta,raw,p/'two')
            self.assertEqual(report['rows'],199319)
            self.assertEqual(report['label_counts']['X'],199315)
            with (p/'one/submission.csv').open() as f:
                rows=list(csv.DictReader(f))
            self.assertEqual(len(rows),199319)
            self.assertEqual([int(r['frame']) for r in rows],list(range(199319)))
            self.assertEqual([i for i,r in enumerate(rows) if r['label']!='X'],[1,2,5,6])
            # The official format checker is a pure function: synthetic CSV only.
            import pandas as pd
            from evaluation.possession_metrics import validate_submission
            self.assertIsNone(validate_submission(pd.read_csv(p/'one/submission.csv'),199319))
            for name in ('submission.csv','submission_raw.csv','features.sqlite','predictions.sqlite'):
                self.assertEqual(sha256(p/'one'/name),sha256(p/'two'/name))
            self.assertEqual(before,[sha256(v) for v in (meta,raw,self.bundle/'model/model.joblib',self.bundle/'model/decoder_parameters.json')])
            with self.assertRaises(FileExistsError):atd.run(self.bundle,meta,raw,p/'one')
            raw.write_text('1:NaN;NaN:NaN\n')
            with self.assertRaises(ValueError):atd.run(self.bundle,meta,raw,p/'failed')
            self.assertTrue((p/'failed/FAILED.json').exists());self.assertFalse((p/'failed/manifest.json').exists())

    def test_cold_import_help_no_dataset_or_model_access(self):
        script='''import sys,runpy
def audit(event,args):
    if event in ('open','sqlite3.connect'):
        p=str(args[0]).replace(chr(92),'/').lower()
        if any(s in p for s in ('/data/','/local_official_artifacts/','/evaluation/gt/','/evaluation/results/')) or p.endswith(('.json','.xml','.txt','.csv','.sqlite','.joblib','.mp4')):
            raise RuntimeError('forbidden data access '+p)
sys.addaudithook(audit)
import external_baseline.atd_inference, external_baseline.inference_bundle
assert not any(m in sys.modules for m in ('numpy','pandas','sklearn','joblib'))
sys.argv=['atd','--help'];runpy.run_module('external_baseline.atd_inference',run_name='__main__')
'''
        result=subprocess.run([sys.executable,'-B','-c',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':unittest.main()
