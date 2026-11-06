from pathlib import Path
import argparse,json,subprocess,sys
root=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser();p.add_argument('--build-root',type=Path,default=Path('C:/Users/dimas/lucid-build'));a=p.parse_args();build=a.build_root.resolve()
args=[str(build/'venv/Scripts/python.exe'),'-m','SCons','-C',str(root),'platform=switch','arch=arm64','precision=double','target=template_release','custom_tools='+str(root/'platform/scons'),'custom_api_file='+str(build/'upstream-gdblocks/extension_api.json'),'build_profile='+str(root/'native/gdblocks-build-profile.json'),'build_root='+str(build),'-j1']
with (build/'reports/gdblocks-arm64-build.log').open('a',encoding='utf-8') as log:subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=True)
subprocess.run([sys.executable,str(root/'tools/validate_native.py'),'--build-root',str(build)],check=True)
