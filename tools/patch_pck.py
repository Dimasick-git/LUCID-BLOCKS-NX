"""Create a local Godot 4.6 PCK with checked replacement resources."""
from pathlib import Path
import argparse,hashlib,json,struct
from inspect_pck import inspect,MAGIC

def patch(source,destination,replacements,additions=None):
    additions=additions or {}
    inventory=inspect(source)
    names={e['path'] for e in inventory['entries']}
    if set(replacements)-names:raise ValueError('Replacement does not exist in original pack')
    if set(additions)&names:raise ValueError('Added resource already exists')
    for name in additions:
        if not name.startswith('NxPort/') or '..' in name.split('/') or ':' in name or '\\' in name:
            raise ValueError('New resources must stay inside NxPort/')
    records=[];header=bytearray(112);struct.pack_into('<6I',header,0,MAGIC,3,4,6,0,2);struct.pack_into('<Q',header,24,112)
    with Path(source).open('rb') as src,Path(destination).open('xb') as out:
        out.write(header)
        for entry in inventory['entries']:
            if entry['flags']!=0:raise ValueError('Unsupported entry flags')
            out.write(bytes((-out.tell())%16));offset=out.tell()-112;digest=hashlib.md5();written=0
            replacement=replacements.get(entry['path'])
            stream=Path(replacement).open('rb') if replacement else src
            if not replacement:src.seek(entry['offset'])
            remaining=Path(replacement).stat().st_size if replacement else entry['size']
            while remaining:
                block=stream.read(min(remaining,1024*1024))
                if not block:raise ValueError('Unexpected end of resource')
                out.write(block);digest.update(block);written+=len(block);remaining-=len(block)
            if replacement:stream.close()
            elif digest.hexdigest()!=entry['md5']:raise ValueError('Original checksum failed: '+entry['path'])
            records.append((entry['path'],offset,written,digest.digest()))
        for name,path in sorted(additions.items()):
            data=Path(path).read_bytes();out.write(bytes((-out.tell())%16));offset=out.tell()-112
            out.write(data);records.append((name,offset,len(data),hashlib.md5(data).digest()))
        directory=out.tell();out.write(struct.pack('<I',len(records)))
        for name,offset,size,md5 in records:
            encoded=name.encode('utf-8');encoded+=bytes((-len(encoded))%4)
            out.write(struct.pack('<I',len(encoded))+encoded+struct.pack('<QQ',offset,size)+md5+struct.pack('<I',0))
        out.seek(32);out.write(struct.pack('<Q',directory))
    result=inspect(destination)
    assert result['entry_count']==inventory['entry_count']+len(additions)
    return {'file':str(Path(destination).resolve()),'entries':len(records),'original_entries':inventory['entry_count'],'added':sorted(additions),'replaced':sorted(replacements),'bytes':Path(destination).stat().st_size,'original_resource_checksums_verified':True}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('source',type=Path);p.add_argument('output',type=Path);p.add_argument('--replace',action='append',default=[]);a=p.parse_args();replacements={}
    for item in a.replace:
        name,file=item.split('=',1);replacements[name]=Path(file)
    report=patch(a.source,a.output,replacements);a.output.with_suffix('.verified.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
