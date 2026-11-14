"""Fetch bounded public catalogs/docs and selected DFL metadata; no tracking or video."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import urllib.error
import urllib.request
from urllib.parse import urlsplit, urlunsplit


ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    'dfl-catalog-v1': 'https://api.figshare.com/v2/articles/28196177/versions/1',
    'soccertrack-version': 'https://huggingface.co/api/datasets/atomscott/soccertrack-v2/revision/v1.2',
    'soccertrack-file-catalog': 'https://huggingface.co/api/datasets/atomscott/soccertrack-v2/tree/v1.2?recursive=true&limit=1000',
    'soccertrack-changes': 'https://huggingface.co/datasets/atomscott/soccertrack-v2/resolve/v1.2/CHANGES_v1_2.md',
}
LIMIT = 2 * 1024 * 1024
DFL_METADATA = {
    'dfl-J03WOH-metadata': ('https://ndownloader.figshare.com/files/51643478',
                           'b9710781d400dd812f62b0a6e3d7bce8', 11745),
    'dfl-J03WQQ-metadata': ('https://ndownloader.figshare.com/files/51643484',
                           '5979209af316a914ce57347d0633df6c', 11932),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--probe-dfl-metadata', action='store_true',
                        help='Two external matchinformation XMLs, 23,677 bytes total; verify publisher MD5')
    args = parser.parse_args()
    output = args.output.resolve()
    output.relative_to(ROOT/'external_artifacts/v3')
    if output.exists():
        raise FileExistsError(output)
    output.mkdir(parents=True)
    entries = []
    sources = dict(SOURCES)
    if args.probe_dfl_metadata:
        sources.update({name: info[0] for name, info in DFL_METADATA.items()})
    for name, url in sources.items():
        entry = dict(name=name, url=url, retrieved_at=datetime.now(timezone.utc).isoformat(),
                     purpose='public catalog or release documentation; no match payload')
        if name in DFL_METADATA:
            entry.update(purpose='external DFL matchinformation XML; no positional or possession records',
                         catalog='https://api.figshare.com/v2/articles/28196177/versions/1',
                         license='CC BY 4.0', expected_md5=DFL_METADATA[name][1],
                         expected_bytes=DFL_METADATA[name][2])
        request = urllib.request.Request(url, headers={'User-Agent': 'MTAH-external-feasibility-audit/1.0'})
        try:
            with urllib.request.urlopen(request, timeout=25) as response:
                final = urlsplit(response.url)
                entry.update(http_status=response.status,
                             final_url=urlunsplit((final.scheme, final.netloc, final.path, '', '')),
                             content_type=response.headers.get('Content-Type'))
                limit = entry.get('expected_bytes', LIMIT)
                data = response.read(limit + 1)
                if len(data) > limit:
                    raise ValueError('Response exceeds metadata-only size cap')
                if name in DFL_METADATA and (len(data) != entry['expected_bytes'] or
                        hashlib.md5(data).hexdigest() != entry['expected_md5']):
                    raise ValueError('External metadata differs from publisher size/MD5')
                path = output/(name+'.response')
                path.write_bytes(data)
                entry.update(file=path.name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest())
        except urllib.error.HTTPError as error:
            entry.update(http_status=error.code, error=str(error))
        except (urllib.error.URLError, TimeoutError, ValueError) as error:
            entry.update(error=str(error))
        entries.append(entry)
    report = dict(created_at=datetime.now(timezone.utc).isoformat(),
                  authenticated=False, tracking_or_video_downloaded=False,
                  external_match_metadata_requested=args.probe_dfl_metadata,
                  max_bytes_per_response=LIMIT, sources=entries)
    (output/'manifest.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
