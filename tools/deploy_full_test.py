"""Copy a checked full NSP and matching hbmenu files to Switch cards."""
from pathlib import Path
import argparse, datetime, hashlib, json, os, shutil, uuid
from assemble_sd import validate_nro
BUILD=Path('C:/Users/dimas/lucid-build')
def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--nsp',type=Path,required=True)
    p.add_argument('--pack',type=Path,required=True)
    p.add_argument('--drive',type=Path,action='append',required=True)
    a=p.parse_args()
    nsp=json.loads(a.nsp.with_suffix('.verified.json').read_text())
    pack=json.loads(a.pack.with_suffix('.verified.json').read_text())
    payload=json.loads(a.nsp.with_suffix('.payload.json').read_text())
    if not nsp['nca_ivfc_and_payload_verified'] or not pack['all_logical_resource_checksums_verified']:raise ValueError('Unverified build')
    if digest(a.nsp)!=nsp['sha256'] or digest(a.pack)!=pack['sha256']:raise ValueError('Changed build')
    engine=BUILD/'godot-switch-upstream/bin/switch_template_release.nro';validate_nro(engine)
    for name,source in [('lucid-blocks/lucid-blocks.nro',engine),('lucid-blocks/game.pck',a.pack)]:
        if payload[name]['sha256']!=digest(source):raise ValueError('NSP/SD version mismatch')
    sources={a.nsp.name:a.nsp,'switch/lucid-blocks/lucid-blocks.nro':engine,'switch/lucid-blocks/game.pck':a.pack,
             'switch/lucid-blocks/README.txt':Path(__file__).resolve().parents[1]/'docs/SD_README.txt'}
    checks={name:digest(src) for name,src in sources.items()}
    roots=[d.resolve() for d in a.drive]
    if len(set(roots))!=len(roots):raise ValueError('Duplicate card')
    for root in roots:
        if str(root)!=root.anchor or root.drive.lower()==os.environ.get('SystemDrive','C:').lower():raise ValueError('Expected non-system drive root')
        if not all((root/n).is_dir() for n in ['switch','Nintendo','atmosphere']):raise ValueError('Switch markers missing: '+str(root))
        if shutil.disk_usage(root).free<sum(s.stat().st_size for s in sources.values())+2*1024**3:raise ValueError('Insufficient card space')
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    for root in roots:
        report={'drive':str(root),'build':nsp['build'],'files':{},'nsp_installed':False,'hardware_tested':False}
        print('Updating',root,flush=True)
        for name,source in sources.items():
            target=root/name;sha=checks[name]
            if not target.is_file() or digest(target)!=sha:
                target.parent.mkdir(parents=True,exist_ok=True)
                stage=target.with_name('.'+target.name+'.'+uuid.uuid4().hex+'.upload')
                print('Copying:',name,flush=True)
                try:
                    count=0;shown=0
                    with source.open('rb') as inp,stage.open('xb') as out:
                        while block:=inp.read(1024*1024):
                            out.write(block);count+=len(block)
                            if count-shown>=128*1024**2:
                                print('  MiB:',count//1024**2,'/',source.stat().st_size//1024**2,flush=True);shown=count
                        out.flush();os.fsync(out.fileno())
                    if count!=source.stat().st_size or digest(stage)!=sha:raise IOError('SD readback failed')
                    if target.exists():
                        old=root/'switch/lucid-blocks/.rollback'/stamp/name;old.parent.mkdir(parents=True,exist_ok=True)
                        previous_sha=digest(target)
                        # Same-volume rename preserves the verified previous file
                        # without rewriting hundreds of MB on the microSD.
                        os.replace(target,old)
                        if digest(old)!=previous_sha:
                            os.replace(old,target)
                            raise IOError('Rollback checksum failed')
                        try:
                            os.replace(stage,target)
                        except OSError:
                            os.replace(old,target)
                            raise
                    else:
                        os.replace(stage,target)
                    if digest(target)!=sha:raise IOError('Final checksum failed')
                finally:
                    if stage.exists():stage.unlink()
            report['files'][name]={'bytes':source.stat().st_size,'sha256':sha}
            print('Verified:',root/name,flush=True)
        (root/'switch/lucid-blocks/test-build.json').write_text(json.dumps(report,indent=2)+'\n')
        (BUILD/f'reports/deploy-{nsp["build"].lower()}-{root.drive[0].lower()}.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Card copies verified. Install the NSP through DBI on each console.',flush=True)
if __name__=='__main__':main()
