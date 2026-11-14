"""Only synthetic metadata: distinguish zero-based ambiguity from absent scope."""
import json
import io
from contextlib import redirect_stdout
from pathlib import Path
import subprocess
import sys
import unittest
import xml.etree.ElementTree as ET

from check_atd_metadata import BOUND_NAMES,summarize
from unittest.mock import patch


def fixture(values,namespace=False):
    body=''.join('<ProviderParameter><Name>'+name+'</Name><Value>'+str(value)+'</Value></ProviderParameter>'
                 for name,value in zip(BOUND_NAMES,values))
    return ET.fromstring('<main'+(' xmlns="synthetic"' if namespace else '')+'><Metadata><GlobalConfig>'
        '<ProviderGlobalParameters>'+body+'</ProviderGlobalParameters></GlobalConfig></Metadata>'
        '<DataFormatSpecifications><DataFormatSpecification startFrame="1" endFrame="8"/>'
        '</DataFormatSpecifications></main>')


class PreflightTests(unittest.TestCase):
    def test_one_zero_start_range_and_empty_second_half_is_not_two_halves(self):
        report=summarize(fixture((0,17,'','')))
        self.assertEqual(report['status'],'one_range_zero_start_empty_second_half')
        self.assertEqual(report['complete_numeric_range_count'],1)
        self.assertTrue(report['second_half_bounds_empty'])
        self.assertFalse(report['physical_half_boundaries_confirmed'])
        self.assertFalse(report['index_base_inferred'])
        self.assertNotIn('17',json.dumps(report))

    def test_missing_file_and_malformed_xml_are_distinct_without_leaking_details(self):
        from check_atd_metadata import main
        for error,status in ((FileNotFoundError('PRIVATE_PATH'),'metadata_file_not_found'),
                             (IsADirectoryError('PRIVATE_PATH'),'metadata_path_is_directory'),
                             (PermissionError('PRIVATE_PATH'),'metadata_permission_denied'),
                             (ET.ParseError('PRIVATE_XML_FRAGMENT'),'metadata_malformed_xml'),
                             (OSError('PRIVATE_PATH'),'metadata_io_error')):
            output=io.StringIO()
            with patch('sys.argv',['check','--metadata','synthetic.xml']), \
                 patch('check_atd_metadata.ET.parse',side_effect=error), redirect_stdout(output):
                with self.assertRaises(SystemExit) as caught:main()
            self.assertEqual(caught.exception.code,2)
            report=json.loads(output.getvalue())
            self.assertEqual(report['status'],status)
            self.assertNotIn('PRIVATE',output.getvalue())

    def test_valid_scope_namespace_and_no_frame_values_disclosed(self):
        report=summarize(fixture((173,293,381,491),True))
        self.assertEqual(report['status'],'bounds_pass_current_adapter')
        serialized=json.dumps(report)
        for value in ('173','293','381','491'):self.assertNotIn(value,serialized)
        self.assertFalse(report['index_base_inferred'])
        self.assertFalse(report['metadata_modified'])

    def test_all_zero_scope_does_not_become_one_frame_or_full_recording(self):
        report=summarize(fixture((0,0,0,0)))
        self.assertEqual(report['status'],'all_zero_bounds_unusable')
        self.assertEqual(report['boundary_field_categories']['zero'],4)

    def test_zero_start_is_ambiguous_without_inventing_offset(self):
        report=summarize(fixture((0,2,5,7)))
        self.assertEqual(report['status'],'nonpositive_bounds_index_base_unknown')
        self.assertFalse(report['index_base_inferred'])

    def test_negative_reversed_overlapping_and_missing(self):
        for values,status in (((-1,2,5,7),'nonpositive_bounds_index_base_unknown'),
                              ((3,2,5,7),'reversed_bounds'),
                              ((1,5,4,7),'overlapping_halves'),
                              (('',2,5,7),'missing_or_noninteger_bounds'),
                              (('bad',2,5,7),'missing_or_noninteger_bounds')):
            self.assertEqual(summarize(fixture(values))['status'],status)

    def test_import_and_help_never_open_dataset(self):
        script='''import runpy,sys
def audit(event,args):
    if event=='open' and str(args[0]).lower().endswith(('.xml','.csv','.sqlite','.joblib','.mp4')):
        raise AssertionError('dataset access during help')
sys.addaudithook(audit)
import check_atd_metadata
sys.argv=['check_atd_metadata','--help']
runpy.run_module('check_atd_metadata',run_name='__main__')
'''
        result=subprocess.run([sys.executable,'-B','-c',script],capture_output=True,text=True,
                              cwd=Path(__file__).resolve().parents[1])
        self.assertEqual(result.returncode,0,result.stderr)


if __name__=='__main__':unittest.main()
