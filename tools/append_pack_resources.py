"""Append changed resources to a verified pack, preserving other resource offsets."""
from pathlib import Path
import argparse, hashlib, json, shutil, struct
from inspect_pck import inspect

p = argparse.ArgumentParser(description=__doc__)
p.add_argument('previous', type=Path)
p.add_argument('repacked', type=Path)
p.add_argument('output', type=Path)
a = p.parse_args()
assert not a.output.exists()
old = inspect(a.previous)
new = inspect(a.repacked)
records = {e['path']: e for e in new['entries']}
assert set(records) == {e['path'] for e in old['entries']}
changed = [e['path'] for e in old['entries'] if e['md5'] != records[e['path']]['md5']]
assert changed and all(name.endswith(('.gdshader', '.gdc')) for name in changed), changed
shutil.copyfile(a.previous, a.output)
with a.output.open('r+b') as out, a.repacked.open('rb') as source:
    at = old['directory_offset'] + 4
    for entry in old['entries']:
        out.seek(at)
        length = struct.unpack('<I', out.read(4))[0]
        metadata = at + 4 + length
        if entry['path'] in changed:
            replacement = records[entry['path']]
            source.seek(replacement['offset'])
            data = source.read(replacement['size'])
            assert hashlib.md5(data).hexdigest() == replacement['md5']
            out.seek(0, 2)
            out.write(bytes((-out.tell()) % 16))
            offset = out.tell()
            out.write(data)
            out.seek(metadata)
            out.write(struct.pack('<QQ', offset-old['file_base'], len(data)) + bytes.fromhex(replacement['md5']))
        at = metadata + 36
result = inspect(a.output)
assert all(e['md5'] == records[e['path']]['md5'] for e in result['entries'])
with a.output.open('rb') as f:
    for entry in result['entries']:
        f.seek(entry['offset'])
        assert hashlib.md5(f.read(entry['size'])).hexdigest() == entry['md5'], entry['path']
report = json.loads(a.repacked.with_suffix('.verified.json').read_text())
report.update(file=str(a.output), bytes=a.output.stat().st_size, incremental_resources=changed,
              all_resource_checksums_verified=True)
a.output.with_suffix('.verified.json').write_text(json.dumps(report, indent=2)+'\n')
print('Verified appended resources:', changed)
