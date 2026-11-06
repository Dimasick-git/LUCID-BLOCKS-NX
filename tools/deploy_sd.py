"""Copy the assembled bundle to a recognized Switch card with SHA-256 checks."""
from pathlib import Path
import argparse, datetime, hashlib, json, os, shutil, uuid
BUILD=Path('C:/Users/dimas/lucid-build')

def digest(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--drive',type=Path,default=Path('E:/'))
    parser.add_argument('--bundle',type=Path,default=BUILD/'release/SD_ROOT')
    parser.add_argument('--only',action='append',help='Verify and update only this manifest path; repeat for a small patch')
    parser.add_argument('--game-backup-reference',type=Path,help='Use an identical verified local game.pck as rollback copy')
    args=parser.parse_args();root=args.drive.resolve()
    if str(root)!=root.anchor or root.drive.lower()==Path(os.environ.get('SystemDrive','C:')+'/').drive.lower():
        raise SystemExit('Expected a removable drive root, not the system disk')
    if not all((root/name).is_dir() for name in ['switch','atmosphere','Nintendo']):
        raise SystemExit('Switch card markers not found; no files written')
    bundle=args.bundle.resolve();manifest=json.loads((bundle/'manifest.json').read_text())
    if args.only and set(args.only)-set(manifest['files']):raise ValueError('Unknown selected bundle path')
    stamp=datetime.datetime.now().strftime('%Y%m%d-%H%M%S')
    backup=root/'switch/lucid-blocks/.rollback'/stamp
    deployed=[]
    for name,record in manifest['files'].items():
        if args.only and name not in args.only:continue
        rel=Path(name)
        if rel.is_absolute() or '..' in rel.parts or (name!='LUCID_BLOCKS_NX_forwarder.nsp' and not name.startswith('switch/lucid-blocks/')):
            raise ValueError('Unexpected bundle path: '+name)
        source=(bundle/rel).resolve();target=(root/rel).resolve()
        assert source.is_relative_to(bundle) and target.is_relative_to(root)
        assert source.stat().st_size==record['bytes'] and digest(source)==record['sha256']
        if target.is_file() and target.stat().st_size==record['bytes'] and digest(target)==record['sha256']:
            print('Already verified:',name,flush=True);deployed.append(name);continue
        target.parent.mkdir(parents=True,exist_ok=True)
        stage=target.with_name('.'+target.name+'.'+uuid.uuid4().hex+'.upload')
        print('Copying:',name,flush=True)
        total=0;shown=0;checksum=hashlib.sha256()
        with source.open('rb') as inp,stage.open('xb') as output:
            while block:=inp.read(1024*1024):
                output.write(block);checksum.update(block);total+=len(block)
                if total-shown>=64*1024*1024:
                    print(f'  {total//(1024*1024)} / {record["bytes"]//(1024*1024)} MiB',flush=True);shown=total
            output.flush();os.fsync(output.fileno())
        assert total==record['bytes'] and checksum.hexdigest()==record['sha256']
        assert digest(stage)==record['sha256'],'SD read-back failed'
        local_rollback=False
        if target.exists() and name=='switch/lucid-blocks/game.pck' and args.game_backup_reference:
            reference=args.game_backup_reference.resolve()
            if not reference.is_file() or reference==target:raise ValueError('Invalid local backup reference')
            if reference.stat().st_size==target.stat().st_size and digest(reference)==digest(target):
                local_rollback=True
                print('Existing game pack has identical local rollback copy:',reference,flush=True)
        if target.exists() and not local_rollback:
            saved=backup/rel;saved.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(target,saved)
            assert digest(saved)==digest(target),'Backup read-back failed'
        os.replace(stage,target)
        assert digest(target)==record['sha256']
        deployed.append(name);print('Verified:',name,flush=True)
    output=root/'switch/lucid-blocks/install-manifest.json'
    temp=output.with_name('.install-manifest.'+uuid.uuid4().hex+'.json')
    temp.write_text(json.dumps(manifest,indent=2)+'\n');os.replace(temp,output)
    report={'build':manifest['build'],'drive':str(root),'files_verified':deployed,
        'nsp_installed_on_console':False,'console_gameplay_verified':False}
    (BUILD/'reports/sd-deployment.json').write_text(json.dumps(report,indent=2)+'\n')
    print('Selected SD update verified.' if args.only else 'Complete SD copy verified. Install the NSP using DBI on the console.',flush=True)

if __name__=='__main__':main()
