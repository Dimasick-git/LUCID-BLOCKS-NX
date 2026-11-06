from pathlib import Path
import subprocess,json,hashlib
b=Path('C:/Users/dimas/lucid-build');game=Path('C:/Program Files (x86)/Steam/steamapps/common/lucid-blocks')
if (b/'recovered-original').exists():raise SystemExit('Original extraction already exists; refusing to overwrite it')
with (b/'reports/project-recovery.log').open('w',encoding='utf-8') as log:
 r=subprocess.run([str(b/'tools/gdre_tools.exe'),'--headless','--recover='+str(game/'lucid-blocks.exe'),'--output='+str(b/'recovered-original')],stdout=log,stderr=subprocess.STDOUT)
print('RECOVERY_EXIT',r.returncode)
raise SystemExit(r.returncode)
