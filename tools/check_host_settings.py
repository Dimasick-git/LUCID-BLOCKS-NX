"""Temporarily inject a UI test into the disposable host copy, then remove it."""
from pathlib import Path
import hashlib, os, struct, subprocess, sys, argparse
from inspect_pck import inspect, MAGIC
from project_binary import prepend_autoloads

ROOT = Path(__file__).resolve().parents[1]
BUILD = Path('C:/Users/dimas/lucid-build')
exe = BUILD/'host-check/switch-profile.exe'
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--probe',type=Path,default=ROOT/'tools/probes/host_settings.gd')
parser.add_argument('--pass-marker',default='REAL_SETTINGS_LANGUAGE_SAVE_CANCEL_PASSED')
args=parser.parse_args()
script = args.probe.resolve()
stage = BUILD/'host-check'/('probe-'+script.stem)
stage.mkdir(exist_ok=True)
subprocess.run([str(BUILD/'tools/gdre_tools.exe'), '--headless', '--bytecode=4.6.0',
    '--output='+str(stage), '--compile='+str(script)], check=True, capture_output=True)
info = inspect(exe)
with exe.open('rb') as f:
    e = next(e for e in info['entries'] if e['path']=='project.binary')
    f.seek(e['offset']); original = f.read(e['size'])

def inject(files, remove=()):
    current = inspect(exe)
    entries = {e['path']:dict(e) for e in current['entries'] if e['path'] not in remove}
    with exe.open('r+b') as f:
        f.seek(-12, 2)
        for name, data in files.items():
            entries[name] = dict(path=name, offset=f.tell(), size=len(data), md5=hashlib.md5(data).hexdigest(), flags=0)
            f.write(data)
        directory = f.tell(); f.write(struct.pack('<I', len(entries)))
        for e in entries.values():
            name=e['path'].encode(); name+=bytes((-len(name))%4)
            f.write(struct.pack('<I', len(name))+name+struct.pack('<QQ', e['offset']-current['file_base'],e['size'])+bytes.fromhex(e['md5'])+struct.pack('<I',e['flags']))
        f.write(struct.pack('<QI',f.tell()-current['pack_offset'],MAGIC))
        f.seek(current['pack_offset']+32); f.write(struct.pack('<Q',directory-current['pack_offset']))
    inspect(exe)

addon = 'NxPort/'+script.stem+'_probe.gdc'
env = os.environ.copy()
for key, name in [('APPDATA','appdata'),('LOCALAPPDATA','localappdata')]:
    path=stage/name; path.mkdir(exist_ok=True); env[key]=str(path)
try:
    inject({'project.binary':prepend_autoloads(original, {'NxSettingsProbe':'res://'+addon}), addon:(stage/(script.stem+'.gdc')).read_bytes()})
    with (BUILD/'reports/host-settings-real.log').open('wb') as log:
        result=subprocess.run([str(exe), '--rendering-method','gl_compatibility', '--resolution','1280x720'],
            cwd=Path('C:/Program Files (x86)/Steam/steamapps/common/lucid-blocks'), env=env,
            stdout=log, stderr=subprocess.STDOUT, timeout=120, creationflags=subprocess.CREATE_NO_WINDOW)
    output=(BUILD/'reports/host-settings-real.log').read_text(encoding='utf-8',errors='replace')
    success=result.returncode==0 and args.pass_marker in output and 'SCRIPT ERROR' not in output
    print('Real settings UI check:', 'PASSED' if success else 'FAILED', flush=True)
    if not success:print(output[-5000:].encode('ascii','backslashreplace').decode())
finally:
    inject({'project.binary':original}, remove=[addon])
raise SystemExit(0 if success else 1)
