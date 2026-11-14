"""Restore only the checksum-listed handoff from Git blobs, without checkout filters."""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def blob(revision, name):
    return subprocess.check_output(
        ['git', 'cat-file', 'blob', f'{revision}:{name}'], cwd=ROOT)


def restore(output, revision='HEAD'):
    output = Path(output).resolve()
    output.relative_to(ROOT)
    if output.exists():
        raise FileExistsError(output)
    commit = subprocess.check_output(
        ['git', 'rev-parse', '--verify', revision + '^{commit}'], cwd=ROOT,
        text=True).strip()
    manifest_bytes = blob(commit, 'HANDOFF_MANIFEST.json')
    manifest = json.loads(manifest_bytes)
    # Validate every path and blob before creating the destination. No data
    # directory traversal, worktree data reads, or newline normalization.
    payload = {}
    for name, expected in manifest['files_sha256'].items():
        path = PurePosixPath(name)
        if (path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name
                or name.startswith(('evaluation/gt/', 'evaluation/results/',
                                        'local_official_artifacts/'))
                or (name.startswith('data/') and name != 'data/README.md')
                or (name.startswith('external_artifacts/') and not
                    name.startswith(('external_artifacts/v2/inference-bundle-v2-r1/',
                                     'external_artifacts/v2/refinement-run1/',
                                     'external_artifacts/v2/J03WMX-refined-assessment-v1/',
                                     'external_artifacts/v2/external-comparison-v1/')))):
            raise ValueError('Path outside handoff provenance allowlist: ' + name)
        data = blob(commit, name)
        if hashlib.sha256(data).hexdigest() != expected:
            raise ValueError('Git blob checksum mismatch: ' + name)
        payload[name] = data
    payload['HANDOFF_MANIFEST.json'] = manifest_bytes
    for name in ('HANDOFF.md', 'KONTEKS_PERCAKAPAN.md'):
        payload[name] = blob(commit, name)
    output.mkdir(parents=True)
    for name, data in payload.items():
        target = output / name
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open('xb') as stream:
            stream.write(data)
        if hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256(data).digest():
            raise ValueError('Written bytes differ: ' + name)
    return dict(commit=commit, manifest_files_verified=len(manifest['files_sha256']),
                files_written=len(payload), output=str(output))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True)
    parser.add_argument('--revision', default='HEAD')
    args = parser.parse_args()
    print(json.dumps(restore(args.output, args.revision), indent=2))
