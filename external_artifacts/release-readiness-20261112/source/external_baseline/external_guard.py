"""Opt-in process guard for this external experiment; import performs no I/O."""
import os
from pathlib import Path
import sys
from urllib.parse import unquote, urlparse

ROOT=Path(__file__).resolve().parents[1]


def install():
    """Block official/unknown workspace datasets, including directory traversal.

    Permit only named DFL preparation/feature inputs, named external V2 outputs,
    synthetic temporary files and known V1 model/source/provenance files. No
    root bundle scan is permitted. Runtime packages remain on the project drive.
    The hook persists for this process; entrypoints use explicit module names.
    """
    artifacts=ROOT/'external_artifacts'
    directories=[artifacts/'v2',artifacts/'local-runtime/training-venv',artifacts/'local-runtime/tmp',
        ROOT/'data/external_dfl/J03WMX']
    directories += [artifacts/n for n in ('J03WOH-run2','J03WOH-features-run2',
        'J03WPY-prepared-v1','J03WPY-features-v1','J03WQQ-prepared-v1','J03WQQ-features-v1',
        'J03WMX-refined-prepared-v1','J03WMX-refined-features-v1',
        'inference-bundle-v1/model','inference-bundle-v1/src','inference-bundle-v1/provenance')]
    files={artifacts/'inference-bundle-v1'/n for n in ('bundle_manifest.json','requirements.txt',
        'requirements-external-training.txt','CODE_LICENSE','run_tactical.py','verify_bundle.py',
        'feature_contract.json','README.md')}
    forbidden=[ROOT/'evaluation/gt',ROOT/'evaluation/results',ROOT/'local_official_artifacts',
               artifacts/'inference-bundle-v1/tactical']
    def audit(event,args):
        if event not in ('open','sqlite3.connect','os.listdir','os.scandir') or not args or not isinstance(args[0],(str,bytes,os.PathLike)):
            return
        raw=os.fsdecode(args[0])
        if raw.startswith('file:'):raw=unquote(urlparse(raw).path)
        p=Path(raw).resolve()
        if any(p==q or q in p.parents for q in forbidden) or 'bar-ath' in p.name.lower():
            raise PermissionError('official dataset access blocked')
        allowed=p in files or any(p==q or q in p.parents for q in directories)
        if not allowed and (p==artifacts or artifacts in p.parents or p==ROOT/'data' or ROOT/'data' in p.parents):
            raise PermissionError('unknown external/official data access blocked: '+str(p))
        if event=='open':
            mode,flags=args[1:3]
            writing=(isinstance(mode,str) and any(c in mode for c in 'wax+')) or (isinstance(flags,int) and bool(flags & (os.O_WRONLY|os.O_RDWR|os.O_CREAT)))
            if writing and ROOT not in p.parents and Path('/tmp') not in p.parents:
                raise PermissionError('write outside project/tmp blocked')
    sys.addaudithook(audit)


def main():
    import runpy
    mode,*args=sys.argv[1:]
    modules=dict(refine='external_baseline.v2_refinement',prepare='external_baseline.prepare',
                 features='external_baseline.features',tests='unittest')
    if mode not in modules:raise ValueError('explicit external entrypoint required')
    install()
    sys.path.insert(0,str(ROOT/'tests'))
    sys.argv=[modules[mode],*args]
    runpy.run_module(modules[mode],run_name='__main__')


if __name__=='__main__':main()
