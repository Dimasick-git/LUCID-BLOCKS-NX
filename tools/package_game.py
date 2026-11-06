from pathlib import Path
import argparse,json,subprocess,sys
root=Path(__file__).resolve().parents[1];build=Path('C:/Users/dimas/lucid-build');sys.path.insert(0,str(root/'tools'))
from inspect_pck import inspect
from project_binary import patch
from patch_pck import patch as patch_pack
p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=build/'release/game.pck');p.add_argument('--host-validation',action='store_true',help='Keep Windows gdblocks loader for desktop smoke testing only');a=p.parse_args()
if a.output.exists():raise SystemExit('Refusing to overwrite existing game pack')
source=Path('C:/Program Files (x86)/Steam/steamapps/common/lucid-blocks/lucid-blocks.exe');info=inspect(source);entries={e['path']:e for e in info['entries']};replacements={}
staging=build/'package-input';staging.mkdir(exist_ok=True)
changed=[]
for delta in (root/'patches/main').rglob('*.patch'):
 rel=delta.relative_to(root/'patches').as_posix()[:-6];current=build/'game'/rel
 if rel.endswith('.gd'):changed.append(current)
 elif rel.endswith('.gdshader'):replacements[rel]=current
compiled=staging/'compiled';compiled.mkdir(exist_ok=True)
args=[str(build/'tools/gdre_tools.exe'),'--headless','--bytecode=4.6.0','--output='+str(compiled)]+['--compile='+str(path) for path in changed]
with (build/'reports/switch-script-compile.log').open('w',encoding='utf-8') as log:subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,check=True)
for path in changed:
 target=path.stem+'.gdc';replacements[path.relative_to(build/'game').with_suffix('.gdc').as_posix()]=compiled/target
 assert (compiled/target).is_file(),target
with source.open('rb') as f:
 e=entries['project.binary'];f.seek(e['offset']);settings=f.read(e['size'])
settings=patch(settings,{'_custom_features':'switch','rendering/renderer/rendering_method':'gl_compatibility','rendering/renderer/rendering_method.mobile':'gl_compatibility','rendering/scaling_3d/mode':0,'threading/worker_pool/max_threads':2,'application/config/custom_user_dir_name':'LucidBlocksNX','display/window/size/window_width_override':1280,'display/window/size/window_height_override':720,'display/window/stretch/mode':'canvas_items','rendering/textures/canvas_textures/default_texture_filter':1})
(staging/'project.binary').write_bytes(settings);replacements['project.binary']=staging/'project.binary'
(staging/'extension_list.cfg').write_bytes(b'res://bin/gdblocks.gdextension\n' if a.host_validation else b'');replacements['.godot/extension_list.cfg']=staging/'extension_list.cfg'
a.output.parent.mkdir(parents=True,exist_ok=True);report=patch_pack(source,a.output,replacements)
report['runtime_requirement']='Desktop validation only' if a.host_validation else 'Godot/Horizon with static gdblocks extension';report['feature']='switch';report['gameplay_verified_on_console']=False
(a.output.with_suffix('.verified.json')).write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
