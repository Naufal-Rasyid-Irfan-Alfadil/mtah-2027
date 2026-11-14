from pathlib import Path
import sys,argparse
root=Path(__file__).resolve().parent
sys.path.insert(0,str(root/'src'))
from external_baseline.inference_bundle import verify_bundle
p=argparse.ArgumentParser();p.add_argument('--runtime',action='store_true');a=p.parse_args()
verify_bundle(root,a.runtime)
print('Bundle verified')
