"""Operator-local ATD boundary preflight; import/help never open match inputs.

Print aggregate structural categories only, never values, paths, identities,
coordinates, target labels, or predictions. This is not a full ATD validator.
The agent runs this only on synthetic or verified public external metadata.
"""
import argparse
from collections import Counter
import json
import xml.etree.ElementTree as ET

BOUND_NAMES=tuple(p+'_'+edge for p in ('first_half','second_half') for edge in ('start','end'))


def summarize(root):
    """Classify XML boundary fields without exposing or interpreting frame IDs.

    Input: an in-memory FIFA XML Element; namespace wrappers are accepted.
    Output: counts and a structural status for the current 1-based, inclusive
    two-half adapter. Missing/noninteger values stay unknown. Zero is not
    converted to one, and all-zero data is not interpreted as a real period.
    No guessing of units, boundary scope, index base, or half-time position.
    """
    for element in root.iter():element.tag=element.tag.rsplit('}',1)[-1]
    meta=root if root.tag=='Metadata' else root.find('Metadata')
    if meta is None:return dict(status='metadata_container_missing',values_disclosed=False)
    records={}
    for entry in meta.findall('./GlobalConfig/ProviderGlobalParameters/ProviderParameter'):
        name=entry.findtext('Name')
        records.setdefault(name,[]).append((entry.findtext('Value') or '').strip())
    counts=Counter(missing=0,noninteger=0,zero=0,negative=0,positive=0)
    values={}
    for name in BOUND_NAMES:
        rows=records.get(name,[])
        if len(rows)!=1 or not rows[0]:counts['missing']+=1;continue
        try:value=int(rows[0])
        except ValueError:counts['noninteger']+=1;continue
        values[name]=value
        counts['zero' if value==0 else 'negative' if value<0 else 'positive']+=1
    reversed_periods=sum(values[p+'_end']<values[p+'_start']
        for p in ('first_half','second_half') if p+'_start' in values and p+'_end' in values)
    all_numeric=len(values)==4
    overlap=(all_numeric and values['first_half_end']>=values['second_half_start'])
    first_complete=all(n in values for n in ('first_half_start','first_half_end'))
    second_empty=all(not any(records.get(n,[])) for n in ('second_half_start','second_half_end'))
    one_zero_start_range=(first_complete and second_empty
                          and values['first_half_start']==0 and values['first_half_end']>0)
    if any(len(records.get(n,[]))>1 for n in BOUND_NAMES):status='duplicate_boundary_fields'
    elif one_zero_start_range:status='one_range_zero_start_empty_second_half'
    elif not all_numeric:status='missing_or_noninteger_bounds'
    elif counts['zero']==4:status='all_zero_bounds_unusable'
    elif reversed_periods:status='reversed_bounds'
    elif counts['zero'] or counts['negative']:status='nonpositive_bounds_index_base_unknown'
    elif overlap:status='overlapping_halves'
    else:status='bounds_pass_current_adapter'
    specs=root.findall('./DataFormatSpecifications/DataFormatSpecification')
    layout_counts=Counter(missing_or_noninteger=0,nonpositive_start=0,reversed=0)
    for spec in specs:
        try:start,end=int(spec.get('startFrame','')),int(spec.get('endFrame',''))
        except ValueError:layout_counts['missing_or_noninteger']+=1;continue
        layout_counts['nonpositive_start']+=int(start<1)
        layout_counts['reversed']+=int(end<start)
    extra_nonempty=sum(bool(v.strip()) for n,rows in records.items()
                       if n and 'extra_half' in n for v in rows)
    return dict(status=status,boundary_fields_expected=4,boundary_field_categories=dict(counts),
        complete_numeric_range_count=sum(all(p+'_'+edge in values for edge in ('start','end'))
                                         for p in ('first_half','second_half')),
        second_half_bounds_empty=second_empty,
        physical_half_boundaries_confirmed=False,
        reversed_period_count=reversed_periods,overlap_or_reversal_between_halves=bool(overlap),
        nonempty_extra_half_field_count=extra_nonempty,
        layout_count=len(specs),layout_issue_counts=dict(layout_counts),
        index_base_inferred=False,values_disclosed=False,metadata_modified=False,
        full_input_compatibility_checked=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata',required=True,help='explicit XML path; run locally by the operator')
    args=parser.parse_args()
    try:report=summarize(ET.parse(args.metadata).getroot())
    except (OSError,ET.ParseError) as error:
        if isinstance(error,FileNotFoundError):status='metadata_file_not_found'
        elif isinstance(error,IsADirectoryError):status='metadata_path_is_directory'
        elif isinstance(error,PermissionError):status='metadata_permission_denied'
        elif isinstance(error,ET.ParseError):status='metadata_malformed_xml'
        else:status='metadata_io_error'
        # Exception text can contain official paths or XML fragments: omit it.
        print(json.dumps(dict(status=status,values_disclosed=False)))
        raise SystemExit(2)
    print(json.dumps(report,indent=2,sort_keys=True))


if __name__=='__main__':main()
