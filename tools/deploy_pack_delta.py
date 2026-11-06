"""Apply a small journaled pack delta, checking complete hashes before and after."""
from pathlib import Path
import argparse, hashlib, json, os

def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('previous', type=Path)
p.add_argument('replacement', type=Path)
p.add_argument('--drive', type=Path, required=True)
a = p.parse_args()
root = a.drive.resolve()
assert root == Path(root.anchor) and root.drive.lower() != 'c:'
assert all((root/name).is_dir() for name in ['atmosphere', 'Nintendo', 'switch'])
assert a.previous.stat().st_size <= a.replacement.stat().st_size
assert a.replacement.stat().st_size - a.previous.stat().st_size < 65536
target = root/'switch/lucid-blocks/game.pck'
ranges = []
offset = 0
with a.previous.open('rb') as old, a.replacement.open('rb') as new:
    while original := old.read(1024*1024):
        updated = new.read(len(original))
        if original != updated:
            i = 0
            while i < len(original):
                if original[i] == updated[i]:
                    i += 1
                    continue
                start = i
                while i < len(original) and original[i] != updated[i]:
                    i += 1
                ranges.append({'offset': offset+start, 'old': original[start:i].hex(), 'new': updated[start:i].hex()})
        offset += len(original)
    tail = new.read()
assert sum(len(bytes.fromhex(r['new'])) for r in ranges) + len(tail) < 65536
old_sha, new_sha = sha(a.previous), sha(a.replacement)
print('Checking complete installed pack:', target, flush=True)
installed = sha(target)
assert installed in (old_sha, new_sha), 'Unknown pack; nothing written'
journal = {'old_sha256': old_sha, 'new_sha256': new_sha, 'old_size': a.previous.stat().st_size,
           'new_size': a.replacement.stat().st_size, 'ranges': ranges, 'tail': tail.hex()}
backup = target.parent/'.rollback'/('pack-delta-'+new_sha[:12]+'.json')
backup.parent.mkdir(parents=True, exist_ok=True)
backup.write_text(json.dumps(journal, indent=2)+'\n')
if installed == old_sha:
    with target.open('r+b') as f:
        try:
            for r in ranges:
                f.seek(r['offset'])
                assert f.read(len(bytes.fromhex(r['old']))) == bytes.fromhex(r['old'])
            for r in ranges:
                f.seek(r['offset']); f.write(bytes.fromhex(r['new']))
            f.seek(a.previous.stat().st_size); f.write(tail)
            f.flush(); os.fsync(f.fileno())
        except BaseException:
            for r in ranges:
                f.seek(r['offset']); f.write(bytes.fromhex(r['old']))
            f.truncate(a.previous.stat().st_size)
            f.flush(); os.fsync(f.fileno())
            raise
print('Checking complete updated pack...', flush=True)
assert sha(target) == new_sha
report = {'drive': str(root), 'pack_sha256': new_sha, 'small_write_bytes': len(tail)+sum(len(bytes.fromhex(r['new'])) for r in ranges), 'verified': True}
reports = Path('C:/Users/dimas/lucid-build/reports')
(reports/('pack-delta-'+root.drive[0]+'-'+new_sha[:12]+'.json')).write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2), flush=True)
