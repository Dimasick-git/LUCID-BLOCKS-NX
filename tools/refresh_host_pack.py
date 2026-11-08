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
changes=(set(report['replaced'])|set(report.get('added',[])))-{'.godot/extension_list.cfg'}
entries={e['path']:e for e in pack['entries']}
host_entries={e['path']:dict(e) for e in host['entries']}
with args.host_exe.open('r+b') as output,args.production_pack.open('rb') as source:
    output.seek(-12,2)
    for name in sorted(changes):
        new=entries[name]
        source.seek(new['offset']);data=source.read(new['size'])
        assert hashlib.md5(data).hexdigest()==new['md5']
        position=output.tell();output.write(data)
        host_entries[name]=dict(new,offset=position)
    directory=output.tell();output.write(struct.pack('<I',len(pack['entries'])))
    for requested in pack['entries']:
        entry=host_entries[requested['path']]
        name=entry['path'].encode();name+=bytes((-len(name))%4)
        output.write(struct.pack('<I',len(name))+name+struct.pack('<QQ',entry['offset']-host['file_base'],entry['size'])+bytes.fromhex(entry['md5'])+struct.pack('<I',entry['flags']))
    output.write(struct.pack('<QI',output.tell()-host['pack_offset'],MAGIC))
    output.seek(host['pack_offset']+32);output.write(struct.pack('<Q',directory-host['pack_offset']))
updated={e['path']:e for e in inspect(args.host_exe)['entries']}
assert all(updated[name]['md5']==entries[name]['md5'] for name in changes)
print('Host copy refreshed:',len(changes),'resources')
