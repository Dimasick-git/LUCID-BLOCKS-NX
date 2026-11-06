from pathlib import Path
import argparse,hashlib,shutil,struct,json
from inspect_pck import inspect,MAGIC
p=argparse.ArgumentParser();p.add_argument('original_exe',type=Path);p.add_argument('pack',type=Path);p.add_argument('output_exe',type=Path);p.add_argument('--verify-existing',action='store_true');a=p.parse_args()
original=inspect(a.original_exe);pack_info=inspect(a.pack)
if pack_info['engine']!=original['engine']:raise ValueError('Engine version differs')
if not a.verify_existing:
    with a.original_exe.open('rb') as src,a.output_exe.open('xb') as dst:
        left=original['pack_offset']
        while left:
            block=src.read(min(left,1024*1024))
            if not block:raise ValueError('Unexpected engine EOF')
            dst.write(block);left-=len(block)
        with a.pack.open('rb') as src:shutil.copyfileobj(src,dst,1024*1024)
        dst.write(struct.pack('<QI',a.pack.stat().st_size,MAGIC))
output=inspect(a.output_exe)
assert output['pack_offset']==original['pack_offset'] and output['entry_count']==pack_info['entry_count']
def prefix_digest(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        left=original['pack_offset']
        while left:
            data=f.read(min(left,1024*1024));h.update(data);left-=len(data)
    return h.hexdigest()
expected=prefix_digest(a.original_exe);assert prefix_digest(a.output_exe)==expected
report={'output':str(a.output_exe.resolve()),'engine_prefix_unchanged':True,'engine_prefix_sha256':expected,'entries':output['entry_count'],'original_installer_modified':False}
a.output_exe.with_suffix('.engine-verified.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
