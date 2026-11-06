from pathlib import Path
import os,subprocess,json,argparse
parser=argparse.ArgumentParser();parser.add_argument("--pack",type=Path);parser.add_argument("--engine",type=Path);parser.add_argument("--label");args=parser.parse_args();label=args.label or ("patched-embedded" if args.engine else "patched" if args.pack else "original")
if not label.replace('-','').replace('_','').isalnum():raise ValueError('Unsafe report label')
b=Path('C:/Users/dimas/lucid-build');game=Path('C:/Program Files (x86)/Steam/steamapps/common/lucid-blocks')
env=os.environ.copy();sandbox=b/'host-check'/label;sandbox.mkdir(parents=True,exist_ok=True)
for key,folder in [('APPDATA','appdata'),('LOCALAPPDATA','localappdata')]:
 p=sandbox/folder;p.mkdir(exist_ok=True);env[key]=str(p)
logpath=b/('reports/host-'+label+'-startup.log')
with logpath.open('w',encoding='utf-8') as log:
 try:
  result=subprocess.run([str(args.engine or game/'lucid-blocks.exe'),'--headless','--quit-after','30','--disable-crash-handler','--log-file',str(b/('reports/host-'+label+'-engine.log'))]+(['--main-pack',str(args.pack)] if args.pack else []),cwd=game,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=45,creationflags=subprocess.CREATE_NO_WINDOW)
  code=result.returncode
 except subprocess.TimeoutExpired:code='timeout'
s=logpath.read_text(encoding='utf-8',errors='replace')
report={'exit':code,'log':str(logpath),'errors':[line[:350] for line in s.splitlines() if any(k in line for k in ['SCRIPT ERROR','Parse Error','ERROR:'])][:12],'userdata_isolated':True,'headless_only':True}
(b/('reports/host-'+label+'-startup.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
