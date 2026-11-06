"""Apply the captured GLES uniform-storage changes to the pinned engine."""
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[1]
engine=Path('C:/Users/dimas/lucid-build/godot-switch-upstream')
patches=sorted((ROOT/'patches/drivers/gles3').rglob('*.patch'))+[ROOT/'patches/servers/rendering/shader_compiler.cpp.patch']
command=['git','-C',str(engine),'apply']
paths=[str(p) for p in patches]
if subprocess.run(command+['--reverse','--check']+paths,capture_output=True).returncode==0:
 print('GLES uniform texture changes already applied')
else:
 subprocess.run(command+['--check']+paths,check=True)
 subprocess.run(command+paths,check=True)
 print('Applied GLES uniform texture changes')
