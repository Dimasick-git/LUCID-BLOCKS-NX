"""Refresh a disposable desktop executable with the current resource changes.

The production pack stays untouched. Windows keeps its gdblocks DLL loader.
"""
from pathlib import Path
import argparse, hashlib, json, struct
from inspect_pck import inspect, MAGIC
BUILD=Path('C:/Users/dimas/lucid-build')
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('production_pack',type=Path)
parser.add_argument('host_exe',type=Path)
args=parser.parse_args()
if not args.host_exe.resolve().is_relative_to((BUILD/'host-check').resolve()):
    raise SystemExit('Only disposable host-check executables may be refreshed')
host=inspect(args.host_exe);pack=inspect(args.production_pack)
report=json.loads(args.production_pack.with_suffix('.verified.json').read_text())
changes=set(report['replaced'])-{'.godot/extension_list.cfg'}
entries={e['path']:e for e in pack['entries']}
with args.host_exe.open('r+b') as output,args.production_pack.open('rb') as source:
    at=host['directory_offset']+4
    for entry in host['entries']:
        output.seek(at);length=struct.unpack('<I',output.read(4))[0]
        metadata=at+4+length
        if entry['path'] in changes:
            new=entries[entry['path']]
            source.seek(new['offset']);data=source.read(new['size'])
            assert hashlib.md5(data).hexdigest()==new['md5']
            output.seek(-12,2);position=output.tell();output.write(data)
            output.write(struct.pack('<QI',position+len(data)-host['pack_offset'],MAGIC))
            output.seek(metadata)
            output.write(struct.pack('<QQ',position-host['file_base'],len(data))+bytes.fromhex(new['md5']))
        at=metadata+36
updated={e['path']:e for e in inspect(args.host_exe)['entries']}
assert all(updated[name]['md5']==entries[name]['md5'] for name in changes)
print('Host copy refreshed:',len(changes),'resources')
