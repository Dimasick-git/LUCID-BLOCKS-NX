"""Capture local adaptations without committing or publishing game data."""
from pathlib import Path
import difflib, subprocess
ROOT = Path(__file__).resolve().parents[1]
BUILD = Path('C:/Users/dimas/lucid-build')
engine = BUILD/'godot-switch-upstream'
paths = subprocess.check_output(['git','-C',str(engine),'diff','--name-only']).decode().splitlines()
for rel in paths:
    if Path(rel).suffix not in ('.cpp','.h','.py','.glsl') and Path(rel).name != 'SCsub':
        continue
    previous = subprocess.check_output(['git','-C',str(engine),'show','HEAD:'+rel]).decode('utf-8')
    current = (engine/rel).read_text(encoding='utf-8')
    out = ROOT/'patches'/('engine' if rel.startswith('main/') else '')/Path(rel+'.patch')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(''.join(difflib.unified_diff(previous.splitlines(True),current.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)),encoding='utf-8')
for path in (BUILD/'game/main').rglob('*'):
    if path.suffix not in ('.gd','.gdshader'):
        continue
    rel = path.relative_to(BUILD/'game').as_posix()
    previous = (BUILD/'recovered-original'/rel).read_text(encoding='utf-8-sig')
    current = path.read_text(encoding='utf-8-sig')
    if previous == current:
        continue
    out = ROOT/'patches'/Path(rel+'.patch')
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(''.join(difflib.unified_diff(previous.splitlines(True),current.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)),encoding='utf-8')
native = BUILD/'upstream-gdblocks'
native_diff = subprocess.check_output(['git','-C',str(native),'diff','--',
    'extension/include/chunk.h','extension/include/world.h',
    'extension/src/chunk.cpp','extension/src/world.cpp'])
assert native_diff, 'Expected Switch native adaptations'
(ROOT/'patches/gdblocks-switch-memory.patch').write_bytes(native_diff)
print('Captured engine, native and game adaptations')
