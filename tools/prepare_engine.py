"""Apply the port patches to an existing checkout of the pinned Switch fork."""
from pathlib import Path
import subprocess, shutil
ROOT=Path(__file__).resolve().parents[1]
BUILD=Path('C:/Users/dimas/lucid-build')
engine=BUILD/'godot-switch-upstream'
commit=subprocess.check_output(['git','-C',str(engine),'rev-parse','HEAD'],text=True).strip()
if commit!='650036e08177daeb0f72b7c2201fad7710efeffa':
    raise SystemExit('Unexpected engine revision; refusing to apply patches')
patches=[]
for directory in ['core','drivers','platform','servers','engine']:
    patches+=sorted((ROOT/'patches'/directory).rglob('*.patch'))
command=['git','-C',str(engine),'apply']
paths=[str(p) for p in patches]
if subprocess.run(command+['--reverse','--check']+paths,capture_output=True).returncode:
    subprocess.run(command+['--check']+paths,check=True)
    subprocess.run(command+paths,check=True)
else:
    print('Engine patches already applied')
for source in (ROOT/'runtime/switch').glob('*'):
    shutil.copyfile(source, engine/'platform/switch'/source.name)
icon = ROOT/'forwarder/icon-dimasick.jpg'
shutil.copyfile(icon if icon.exists() else ROOT/'forwarder/icon.jpg',engine/'platform/switch/icon.jpg')
romfs=engine/'platform/switch/romfs';romfs.mkdir(exist_ok=True)
(romfs/'README.txt').write_text('Lucid Blocks NX uses external /switch/lucid-blocks/game.pck.\n')
print('Prepared pinned engine for Lucid Blocks NX')
