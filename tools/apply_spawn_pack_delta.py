"""Apply the fixed-size OPT01 spawn-only correction to the connected card.

Full old/new SHA-256 checks bracket the tiny write. A rollback byte journal
is saved on PC and SD before changing the pack. No save files are touched.
"""
from pathlib import Path
import hashlib,json,os,shutil
from inspect_pck import inspect
BUILD=Path('C:/Users/dimas/lucid-build')
old=BUILD/'rejected/game-OPT01-before-spawn-correction.pck'
new=BUILD/'release/game.pck'
target=Path('D:/switch/lucid-blocks/game.pck')
assert Path('D:/atmosphere').is_dir() and Path('D:/Nintendo').is_dir()
assert old.stat().st_size==new.stat().st_size==target.stat().st_size
before={e['path']:e for e in inspect(old)['entries']}
after={e['path']:e for e in inspect(new)['entries']}
assert set(before)==set(after)
assert [name for name in after if before[name]['md5']!=after[name]['md5']]==['main/world/spawning/spawn_tester/spawn_tester.gdc']
assert all(before[name]['offset']==after[name]['offset'] for name in after)
assert all(before[name]['size']==after[name]['size'] for name in after if name!='main/world/spawning/spawn_tester/spawn_tester.gdc')
def sha(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
old_sha=sha(old);new_sha=sha(new)
ranges=[];position=0
with old.open('rb') as a,new.open('rb') as b:
    while original:=a.read(1024*1024):
        replacement=b.read(len(original))
        if original!=replacement:
            i=0
            while i<len(original):
                if original[i]==replacement[i]:i+=1;continue
                start=i
                while i<len(original) and original[i]!=replacement[i]:i+=1
                ranges.append({'offset':position+start,'old':original[start:i].hex(),'new':replacement[start:i].hex()})
        position+=len(original)
assert sum(len(bytes.fromhex(x['new'])) for x in ranges)<65536
print('Checking installed pack before patch...',flush=True)
installed_sha=sha(target)
assert installed_sha in (old_sha,new_sha),'Card pack differs from both verified inputs; no write performed'
journal={'target':str(target),'old_sha256':old_sha,'new_sha256':new_sha,'ranges':ranges}
local=BUILD/'reports/opt01-spawn-delta.json';local.write_text(json.dumps(journal,indent=2)+'\n')
rollback=target.parent/'.rollback/opt01-spawn-delta.json';rollback.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(local,rollback)
if installed_sha==old_sha:
    with target.open('r+b') as stream:
        for item in ranges:
            stream.seek(item['offset']);assert stream.read(len(bytes.fromhex(item['old'])))==bytes.fromhex(item['old'])
        for item in ranges:
            stream.seek(item['offset']);stream.write(bytes.fromhex(item['new']))
        stream.flush();os.fsync(stream.fileno())
    print('Patched',sum(len(bytes.fromhex(x['new'])) for x in ranges),'bytes; verifying complete pack...',flush=True)
assert sha(target)==new_sha
manifest=BUILD/'release/SD_ROOT/manifest.json'
assert json.loads(manifest.read_text())['files']['switch/lucid-blocks/game.pck']['sha256']==new_sha
shutil.copyfile(manifest,target.parent/'install-manifest.json')
journal['verified']=True;local.write_text(json.dumps(journal,indent=2)+'\n')
print('Spawn correction and full pack SHA-256 verified.',flush=True)
