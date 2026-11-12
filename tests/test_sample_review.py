"""Manual decoder-change counts and sparse event references, never dense GT."""
import csv
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from external_baseline.sample_review import runs,analyze,event_references,HTML


class SampleReviewTests(unittest.TestCase):
    def test_manual_counts_coverage_and_gap_safe_runs(self):
        rows=[[1,10,400000,'D','H',0,.6,1],[1,11,440000,'D','D',0,.8,0],
              [1,13,520000,'A','D',1,.4,0],[2,14,560000,'D','A',1,.6,1]]
        result=analyze(rows,[])
        self.assertEqual(result['raw_D_total'],3);self.assertEqual(result['decoded_D_total'],2)
        self.assertEqual(result['D_to_alive_total'],2)
        self.assertEqual(result['label_change_matrix']['D'],{'H':1,'A':1,'D':1})
        self.assertEqual(result['by_complete_ball']['0']['D_to_alive'],1)
        self.assertEqual(len(runs(rows,4)),4) # gap/half must not join D segments
        self.assertNotIn('macro_f1',result)

    def test_event_spans_are_references_not_targets_and_do_not_cross_half(self):
        rows=[[1,n,n*40000,'D','H',0,.6,1] for n in range(10,17)]
        rows += [[2,20,800000,'A','A',1,.1,0]]
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'events.csv'
            with p.open('w',newline='') as f:
                w=csv.writer(f);w.writerow(['Team','Type','Subtype','Period','Start Frame','End Frame'])
                w.writerows([['Home','SET PIECE','KICK OFF',1,10,0],['Home','BALL OUT','',1,10,11],
                             ['Away','PASS','',1,12,14],['Away','SET PIECE','THROW IN',1,16,16],
                             ['Home','BALL OUT','',2,20,20],['Home','SHOT','',2,21,22]])
            events=event_references(p,rows);report=analyze(rows,events)
            self.assertFalse(events[0]['interval_available']);self.assertEqual(events[0]['anchor_frame'],10)
            self.assertEqual(report['reference_span_count'],1)
            span=report['reference_spans'][0]
            self.assertEqual(span['observed_interior_frames'],4)
            self.assertEqual(span['D_to_alive_frames'],4)
            self.assertEqual(span['intervening_event_types'],{'PASS':1})
            self.assertEqual(span['status'],'context_only_not_dead_ball_GT')
            self.assertEqual(report['unmatched_event_anchors'],1)

    def test_visualization_is_standalone_and_import_has_no_model_or_data_io(self):
        self.assertIn('Ball-out',HTML)
        self.assertIn('application/json',HTML)
        self.assertNotIn('src="https:',HTML)
        script='''import sys,runpy
def audit(event,args):
    if event in ('open','sqlite3.connect'):
        p=str(args[0]).lower()
        if p.endswith(('.json','.csv','.sqlite','.xml','.mp4','.joblib')):
            raise RuntimeError('unexpected data access')
sys.addaudithook(audit)
import external_baseline.sample_review
assert not any(m in sys.modules for m in ('numpy','pandas','sklearn','joblib'))
sys.argv=['review','--help'];runpy.run_module('external_baseline.sample_review',run_name='__main__')
'''
        result=subprocess.run([sys.executable,'-B','-c',script],capture_output=True,text=True)
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':unittest.main()
