"""Synthetic period-source audit: bounds, counters, state reset and packaging."""
from contextlib import closing
import copy
import json
from pathlib import Path
import shutil
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from external_baseline.atd_periods import provider_periods,organizer_period_scope
from external_baseline import atd_inference as atd
from external_baseline.inference_bundle import revise_adapter,verify_bundle
from external_baseline.prepare import REPO,sha256
import test_local_inference as local_fixture
metadata_xml=local_fixture.metadata_xml


def public_source(path,blocks=((1,0,3),(2,4,7))):
    path.write_text("import os\nGAMES={'SYNTH':{'fps':25,'n_video_frames':8}}\n"
                    +"def half_video_blocks(game,adjust=0):\n    assert adjust==0\n    return "+repr(list(blocks))+"\n")


def recording_metadata():
    return metadata_xml(periods=((0,8),('','')))


class PeriodSourceTests(unittest.TestCase):
    def test_empty_invalid_and_zero_values_are_not_silent_numeric_defaults(self):
        fields=dict(first_half_start='1',first_half_end='4',second_half_start='5',second_half_end='8')
        for value in ('','bad',None):
            with self.assertRaisesRegex(ValueError,'missing, empty or noninteger'):
                provider_periods(dict(fields,first_half_start=value))
        with self.assertRaisesRegex(ValueError,'invalid half bounds'):
            provider_periods(dict(fields,first_half_start='0'))
        self.assertEqual(provider_periods(fields),[(1,1,4),(2,5,8)])
        missing=fields.copy();del missing['second_half_start']
        with self.assertRaisesRegex(ValueError,'missing, empty or noninteger'):provider_periods(missing)

    def test_public_zero_based_inclusive_scope_maps_to_raw_plus_one_only(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'public.py';public_source(p,((1,0,1),(2,5,6)))
            scope=organizer_period_scope(p,'SYNTH',8)
            self.assertEqual(scope['periods'],[(1,1,2),(2,6,7)])
            self.assertEqual(scope['public_source_sha256'],sha256(p))
            for game,n,fps in ((None,8,25),('UNKNOWN',8,25),('SYNTH',9,25),('SYNTH',8,30)):
                with self.assertRaises(ValueError):organizer_period_scope(p,game,n,fps)
            for bad in (((1,0,4),(2,4,7)),((1,0,3),),((1,-1,3),(2,4,7))):
                public_source(p,bad)
                with self.assertRaises(ValueError):organizer_period_scope(p,'SYNTH',8)

    def test_recording_extent_does_not_automatically_become_two_halves(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);meta=p/'synthetic.xml';source=p/'public.py'
            meta.write_text(recording_metadata());public_source(source)
            before=meta.read_bytes()
            with self.assertRaisesRegex(ValueError,'invalid half bounds'):atd.metadata(meta)
            scope=organizer_period_scope(source,'SYNTH',8)
            parsed=atd.metadata(meta,scope)
            self.assertEqual(parsed['periods'],[(1,1,4),(2,5,8)])
            self.assertEqual(meta.read_bytes(),before)

    def test_layout_zero_lower_bound_never_rebases_raw_row_counter(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder);meta=p/'synthetic.xml';raw=p/'synthetic.txt'
            meta.write_text(metadata_xml().replace('startFrame="1"','startFrame="0"'))
            parsed=atd.metadata(meta)
            raw.write_text(''.join(f'{n}:NaN;NaN:NaN\n' for n in range(1,9)))
            self.assertEqual([r[0] for r in atd.frames(raw,parsed,8)],list(range(8)))
            raw.write_text(''.join(f'{n}:NaN;NaN:NaN\n' for n in range(8)))
            with self.assertRaisesRegex(ValueError,'ATD IDs'):list(atd.frames(raw,parsed,8))
            meta.write_text(metadata_xml().replace(' startFrame="1"',''))
            with self.assertRaisesRegex(ValueError,'explicit integer layout bounds'):atd.metadata(meta)


class RevisedBundleTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        local_fixture.LocalInferenceTests.setUpClass();cls.addClassCleanup(local_fixture.LocalInferenceTests.doClassCleanups)

    def fixture_revision(self,root,blocks=((1,0,3),(2,4,7))):
        parent=root/'parent';shutil.copytree(local_fixture.LocalInferenceTests.bundle,parent)
        # An unlisted synthetic extra must not be copied or opened.
        (parent/'operator_extra').mkdir();(parent/'operator_extra/do_not_copy.txt').write_text('synthetic extra')
        fake_repo=root/'source';(fake_repo/'external_baseline').mkdir(parents=True)
        for name in ('atd_inference.py','atd_periods.py','inference_bundle.py'):
            shutil.copyfile(REPO/'external_baseline'/name,fake_repo/'external_baseline'/name)
        public_source(fake_repo/'games.py',blocks);(fake_repo/'DATA.md').write_text('synthetic public scope documentation')
        with patch('external_baseline.inference_bundle.REPO',fake_repo):
            revised=revise_adapter(parent,root/'revised')
        return parent,root/'revised',revised

    def test_revision_preserves_payload_and_rejects_checksum_tampering(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);parent,bundle,manifest=self.fixture_revision(root)
            pm=verify_bundle(parent,True)
            for key in ('model_sha256','decoder_sha256','evaluated_source_sha256'):
                self.assertEqual(manifest.get(key),pm.get(key))
            self.assertFalse((bundle/'operator_extra').exists())
            verify_bundle(bundle,True)
            (bundle/'src/organizer_game_metadata.py').write_text('tampered')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):verify_bundle(bundle,True)
            with (parent/'model/model.joblib').open('ab') as stream:stream.write(b'tampered')
            with self.assertRaisesRegex(ValueError,'hash mismatch'):revise_adapter(parent,root/'must_not_exist')
            self.assertFalse((root/'must_not_exist').exists())

    def test_adjacent_halves_reset_features_and_decode_independently_without_fitting(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);_,bundle,_=self.fixture_revision(root)
            meta,raw=root/'synthetic.xml',root/'synthetic.txt'
            meta.write_text(recording_metadata())
            raw.write_text(''.join(f'{n}:.4,.5;.5,.6:'+('.7,.5' if n>=5 else '.5,.5')+'\n'
                                   for n in range(1,9)))
            decoder=atd.decode_probabilities
            with patch('sklearn.ensemble.HistGradientBoostingClassifier.fit',side_effect=AssertionError('no fit')), \
                 patch('external_baseline.training.evaluate_timeline',side_effect=AssertionError('no GT')), \
                 patch('external_baseline.atd_inference.decode_probabilities',wraps=decoder) as calls:
                atd.run(bundle,meta,raw,root/'out',8,period_source='organizer-public',game='SYNTH')
            self.assertEqual([[k.period for k in c.args[0]] for c in calls.call_args_list],[[1]*4,[2]*4])
            with closing(sqlite3.connect(root/'out/features.sqlite')) as db:
                # A frame/time gap does not explain this reset: frames 3/4 are
                # adjacent; only the public period change resets the context.
                rows=db.execute('SELECT frame,period,ball_speed_mps FROM features WHERE frame IN (0,4)').fetchall()
                self.assertEqual(rows,[(0,1,None),(4,2,None)])
            from external_baseline.features import ContextFeatureExtractor
            from external_baseline.contracts import FrameKey
            scope=organizer_period_scope(bundle/'src/organizer_game_metadata.py','SYNTH',8)
            parsed=atd.metadata(meta,scope);extractor=ContextFeatureExtractor(105,68)
            features=[extractor.extract(FrameKey('synthetic',p,f),t,e) for f,p,t,e in atd.frames(raw,parsed,8)]
            self.assertAlmostEqual(features[4]['nearest_home_median_1s'],31.5)
            self.assertEqual(features[4]['nearest_home_median_1s'],features[4]['nearest_home_m'])
            with self.assertRaisesRegex(ValueError,'invalid half bounds'):
                atd.run(bundle,meta,raw,root/'no_auto_fallback',8)
            self.assertFalse((root/'no_auto_fallback').exists())

    def test_gap_endpoints_and_x_mask_use_same_raw_video_lattice(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);_,bundle,_=self.fixture_revision(root,((1,0,1),(2,5,6)))
            meta,raw=root/'synthetic.xml',root/'synthetic.txt';meta.write_text(recording_metadata())
            raw.write_text(''.join(f'{n}:.4,.5;.5,.6:.5,.5\n' for n in range(1,9)))
            atd.run(bundle,meta,raw,root/'out',8,period_source='organizer-public',game='SYNTH')
            import csv
            with (root/'out/submission.csv').open() as stream:rows=list(csv.DictReader(stream))
            self.assertEqual([int(r['frame']) for r in rows if r['label']!='X'],[0,1,5,6])
            self.assertEqual([r['label'] for r in rows if int(r['frame']) in (2,3,4,7)],['X']*4)
