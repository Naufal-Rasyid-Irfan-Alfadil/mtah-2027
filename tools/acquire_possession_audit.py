"""Acquire a fixed, small external audit package; no credentials or large files."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
REVISION = '325bd4c57ee8e135ab652f3921d274526ada496b'
CODE_REVISION = 'a752d294df2a0e816e827b70f284980698f5a50e'
DATA_FILES = ('raw/117093/117093_player_nodes.csv',
              'raw/117093/117093_12_class_events.json')
CODE_FILES = ('scripts/tracking_data_utils/io.py',
              'scripts/tracking_data_utils/dataclass.py',
              'src/data_utils/soccertrack_v2.py', 'LICENSE-DATA', 'LICENSE')
LINEAGE_FILES = ('docs/ground_truth_creation.md',
                 'src/coordinate_conversion/convert_raw_to_pitch_plane.py',
                 'src/video_utils/trim_video_into_halves.py',
                 'src/data_association/create_ground_truth.py',
                 'configs/video_trimming_config.yaml')


def sha(data):
    return hashlib.sha256(data).hexdigest()


def verify_blob(data, oid, size):
    if len(data) != size or hashlib.sha1(b'blob ' + str(len(data)).encode() + b'\0' + data).hexdigest() != oid:
        raise ValueError('Size or publisher Git blob checksum mismatch')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--lineage-only', action='store_true',
                        help='Fetch five pinned static pipeline sources only; no dataset requests')
    args = parser.parse_args()
    output = args.output.resolve()
    output.relative_to(ROOT / 'external_artifacts/v3')
    if output.exists():
        raise FileExistsError(output)
    catalogs = ROOT / 'external_artifacts/v3/feasibility-20261112-metadata'
    cm = json.loads((catalogs / 'manifest.json').read_text())
    entry = next(e for e in cm['sources'] if e['name'] == 'soccertrack-file-catalog')
    data = (catalogs / entry['file']).read_bytes()
    if sha(data) != entry['sha256']:
        raise ValueError('Catalog checksum mismatch')
    catalog = {e['path']: e for e in json.loads(data) if e['type'] == 'file'}
    source = ROOT / 'external_artifacts/v3/geometry-contract-source-20261112'
    sm = json.loads((source / 'manifest.json').read_text())
    tree = (source / 'tree.json').read_bytes()
    if sha(tree) != sm['tree_sha256'] or sm['revision'] != CODE_REVISION:
        raise ValueError('Source tree checksum/revision mismatch')
    code = {e['path']: e for e in json.loads(tree)['tree'] if e['type'] == 'blob'}
    requests = []
    for path in (() if args.lineage_only else DATA_FILES):
        e = catalog[path]
        if e.get('lfs') or e['size'] > 600_000:
            raise ValueError('Only the explicitly selected small non-LFS files are allowed')
        requests.append(dict(kind='external_match_audit_payload', path=path,
                             url=f'https://huggingface.co/datasets/atomscott/soccertrack-v2/resolve/{REVISION}/{path}',
                             git_oid=e['oid'], bytes=e['size'], license='CC BY 4.0'))
    for path in (LINEAGE_FILES if args.lineage_only else CODE_FILES):
        e = code[path]
        requests.append(dict(kind='publisher_static_source', path=path,
                             url=f'https://raw.githubusercontent.com/AtomScott/SoccerTrack-v2/{CODE_REVISION}/{path}',
                             git_oid=e['sha'], bytes=e['size']))
    if sum(e['bytes'] for e in requests) > 1_000_000:
        raise ValueError('Total size cap exceeded')
    output.mkdir(parents=True)
    records, network_failures = [], 0
    for entry in requests:
        record = dict(entry)
        record['requested_at'] = datetime.now(timezone.utc).isoformat()
        try:
            request = urllib.request.Request(entry['url'], headers={'User-Agent': 'MTAH-external-audit/1.0'})
            with urllib.request.urlopen(request, timeout=15) as response:
                body = response.read(entry['bytes'] + 1)
                verify_blob(body, entry['git_oid'], entry['bytes'])
                destination = output / ('dataset' if entry['kind'].startswith('external') else 'source') / entry['path']
                destination.parent.mkdir(parents=True, exist_ok=True)
                with destination.open('xb') as stream:
                    stream.write(body)
                record.update(status='checksum_verified', http_status=response.status,
                              sha256=sha(body), local_path=destination.relative_to(output).as_posix())
        except urllib.error.HTTPError as error:
            record.update(status='http_error', http_status=error.code)
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            record.update(status='network_error', error_type=type(error).__name__)
            network_failures += 1
        records.append(record)
    report = dict(created_at=datetime.now(timezone.utc).isoformat(),
                  dataset_revision=REVISION, code_revision=CODE_REVISION,
                  authenticated=False, credentials_read=False,
                  publisher_source_executed=False, large_files_downloaded=False,
                  max_total_bytes=1_000_000, requests=records)
    (output / 'manifest.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(output=str(output), results=[dict(path=e['path'], status=e['status'], http_status=e.get('http_status')) for e in records]), indent=2))
    if network_failures:
        raise SystemExit(2)


if __name__ == '__main__':
    main()
