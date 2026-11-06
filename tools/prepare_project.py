from pathlib import Path
import hashlib,json,shutil,subprocess
r=Path('C:/Users/dimas/lucid-blocks-nx');b=Path('C:/Users/dimas/lucid-build');original=b/'recovered-original';target=b/'game'
if target.exists():raise SystemExit('Working project already exists; refusing to overwrite')
shutil.copytree(original,target,ignore=shutil.ignore_patterns('.godot','gdre_export.log'))
patches=sorted((r/'patches/main').rglob('*.patch'))
if not patches:raise SystemExit('No game adaptations found')
subprocess.run(['git','-C',str(target),'apply','--check']+[str(p) for p in patches],check=True)
subprocess.run(['git','-C',str(target),'apply']+[str(p) for p in patches],check=True)
changes=[]
for delta in patches:
 rel=delta.relative_to(r/'patches').as_posix()[:-6]
 changes.append({'path':rel,'original_sha256':hashlib.sha256((original/rel).read_bytes()).hexdigest(),'patched_sha256':hashlib.sha256((target/rel).read_bytes()).hexdigest()})
# Keep original desktop native binaries available for later host comparison.
steam=Path('C:/Program Files (x86)/Steam/steamapps/common/lucid-blocks')
for source,dest in [('libgdblocks.windows.template_release.double.x86_64.dll','bin/libgdblocks.windows.template_release.double.x86_64.dll'),('libgodotsteam.windows.template_release.double.x86_64.dll','addons/godotsteam/win64/libgodotsteam.windows.template_release.double.x86_64.dll'),('steam_api64.dll','addons/godotsteam/win64/steam_api64.dll')]:
 dst=target/dest;dst.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(steam/source,dst)
(b/'reports/working-project-patches.json').write_text(json.dumps(changes,indent=2)+'\n')
print('Working project:',target,'; patches:',len(changes),'; original extraction retained')
