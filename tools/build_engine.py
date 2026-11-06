"""Build the pinned Horizon engine and static voxel bridge, one job by default."""
from pathlib import Path
import argparse, os, subprocess, sys
ROOT = Path(__file__).resolve().parents[1]
BUILD = Path('C:/Users/dimas/lucid-build')
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--log', type=Path, default=BUILD/'reports/engine-build-final.log')
args = parser.parse_args()
env = os.environ.copy()
env['DEVKITPRO'] = 'C:/devkitPro'
env['LUCID_NX_BUILD_ROOT'] = str(BUILD)
command = [sys.executable,'-m','SCons','-C',(BUILD/'godot-switch-upstream').as_posix(),
    'platform=switch','target=template_release','arch=arm64','precision=double',
    'custom_modules='+(ROOT/'engine_modules').as_posix(),'lto=none','optimize=speed_trace',
    'debug_symbols=yes','separate_debug_symbols=yes','-j1']
args.log.parent.mkdir(parents=True,exist_ok=True)
print('Building engine; log:',args.log,flush=True)
with args.log.open('w',encoding='utf-8') as log:
    result = subprocess.run(command,env=env,stdout=log,stderr=subprocess.STDOUT)
print('Engine build exit:',result.returncode,flush=True)
raise SystemExit(result.returncode)
