"""Inspect an installed Godot PCK/embedded EXE without modifying it."""
from pathlib import Path
import argparse,collections,hashlib,json,mmap,struct
MAGIC=0x43504447

def inspect(path):
    with Path(path).open('rb') as file,mmap.mmap(file.fileno(),0,access=mmap.ACCESS_READ) as data:
        def u32(at): return struct.unpack_from('<I',data,at)[0]
        def u64(at): return struct.unpack_from('<Q',data,at)[0]
        if u32(0)==MAGIC:start=0
        else:
            if len(data)<12 or u32(len(data)-4)!=MAGIC:raise ValueError('No embedded PCK footer')
            start=len(data)-12-u64(len(data)-12)
        if start<0 or u32(start)!=MAGIC:raise ValueError('Invalid PCK header')
        version,major,minor,patch,flags=struct.unpack_from('<5I',data,start+4)
        if version not in (2,3):raise ValueError('Unsupported pack version')
        if flags&1:raise ValueError('Encrypted PCK directory is not supported')
        base=u64(start+24)+(start if version==3 or flags&2 else 0)
        directory=start+u64(start+32) if version==3 else start+96
        count=u32(directory);at=directory+4
        if count>1000000:raise ValueError('PCK entry count budget')
        entries=[];paths=set()
        for _ in range(count):
            size=u32(at);at+=4
            if size>4096 or at+size+36>len(data):raise ValueError('PCK entry bounds')
            name=data[at:at+size].rstrip(b'\0').decode('utf-8');at+=size
            offset,length=struct.unpack_from('<QQ',data,at);at+=16
            md5=data[at:at+16].hex();at+=16;entry_flags=u32(at);at+=4
            relative=name.removeprefix('res://').replace('\\','/')
            if relative.startswith('/') or '..' in relative.split('/') or ':' in relative or relative in paths:raise ValueError('Unsafe or duplicate resource path')
            paths.add(relative)
            if base+offset<0 or base+offset+length>len(data):raise ValueError('Resource outside executable')
            entries.append(dict(path=relative,offset=base+offset,size=length,md5=md5,flags=entry_flags))
        return dict(source=str(Path(path).resolve()),source_bytes=len(data),engine=f'{major}.{minor}.{patch}',pack_version=version,pack_offset=start,pack_flags=flags,file_base=base,directory_offset=directory,entry_count=count,resource_bytes=sum(e['size'] for e in entries),extensions=dict(collections.Counter(Path(e['path']).suffix for e in entries)),entries=entries)

def extract(source,entry,destination):
    if entry['flags']&1:raise ValueError('Encrypted resource not supported')
    with Path(source).open('rb') as file:
        file.seek(entry['offset']);data=file.read(entry['size'])
    if hashlib.md5(data).hexdigest()!=entry['md5']:raise ValueError('Resource MD5 mismatch: '+entry['path'])
    root=Path(destination).resolve();dest=(root/entry['path']).resolve()
    if not dest.is_relative_to(root):raise ValueError('Extraction escapes destination')
    dest.parent.mkdir(parents=True,exist_ok=True)
    if dest.exists():raise FileExistsError(dest)
    dest.write_bytes(data)

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source');p.add_argument('--report',type=Path,required=True);p.add_argument('--text-output',type=Path);a=p.parse_args()
    report=inspect(a.source);a.report.parent.mkdir(parents=True,exist_ok=True);a.report.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    if a.text_output:
        for entry in report['entries']:
            if Path(entry['path']).suffix in ('.gdextension','.gdshader','.glsl','.gd','.godot','.cfg','.import') or entry['path'] in ('project.binary','.godot/extension_list.cfg'):
                extract(a.source,entry,a.text_output)
    print(json.dumps({k:v for k,v in report.items() if k!='entries'},indent=2))
