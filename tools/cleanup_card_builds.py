"""Remove obsolete generated builds only after a verified deployment."""
from pathlib import Path
import argparse, json, os, re, shutil

BUILD=Path('C:/Users/dimas/lucid-build')

def clean(root, build='NSP03', rollback_build='NSP02'):
    root=root.resolve()
    if str(root)!=root.anchor or root.drive.lower()==os.environ.get('SystemDrive','C:').lower():
        raise ValueError('Expected a non-system card root')
    if not all((root/p).is_dir() for p in ('switch','Nintendo','atmosphere')):
        raise ValueError('Switch card markers missing')
    current_name='LUCID_BLOCKS_NX_FULL_'+build+'.nsp'
    local=json.loads((BUILD/'release'/current_name).with_suffix('.verified.json').read_text())
    if not (BUILD/'release'/('LUCID_BLOCKS_NX_FULL_'+rollback_build+'.nsp')).is_file():
        raise ValueError('PC rollback installer is missing')
    deployed=json.loads((root/'switch/lucid-blocks/test-build.json').read_text())
    if deployed['files'][current_name]['sha256']!=local['sha256']:
        raise ValueError('Current build has not been verified on this card')
    removed=[]
    for name in ('LUCID_BLOCKS_NX_FULL_NSP01.nsp','LUCID_BLOCKS_NX_FULL_NSP02.nsp','LUCID_BLOCKS_NX_FULL_NSP03.nsp','LUCID_BLOCKS_NX_FULL_NSP04.nsp','LUCID_BLOCKS_NX_FULL_NSP05.nsp','LUCID_BLOCKS_NX_forwarder.nsp'):
        if name == current_name: continue
        p=root/name
        if p.is_file():
            removed.append({'path':str(p),'bytes':p.stat().st_size})
            p.unlink()
    rollback=(root/'switch/lucid-blocks/.rollback').resolve()
    assert rollback.parent==(root/'switch/lucid-blocks').resolve()
    if rollback.exists():
        for folder in rollback.iterdir():
            if folder.is_file() and re.fullmatch(r'(pack-delta-[a-f0-9]+|opt01-spawn-delta)\.json',folder.name):
                removed.append({'path':str(folder),'bytes':folder.stat().st_size})
                folder.unlink()
                continue
            if not folder.is_dir() or not re.fullmatch(r'\d{8}-\d{6}',folder.name):
                raise ValueError('Unexpected rollback entry: '+str(folder))
            resolved=folder.resolve()
            if resolved.parent!=rollback or folder.is_symlink():
                raise ValueError('Unexpected rollback target')
            files=[p for p in folder.rglob('*') if p.is_file()]
            for p in files:
                if p.name not in ('lucid-blocks.nro','game.pck','README.txt','LUCID_BLOCKS_NX_FULL_NSP03.nsp','LUCID_BLOCKS_NX_FULL_NSP04.nsp','LUCID_BLOCKS_NX_FULL_NSP05.nsp','LUCID_BLOCKS_NX_FULL_NSP06.nsp') and not re.fullmatch(r'(pack-delta-[a-f0-9]+|opt01-spawn-delta)\.json',p.name):
                    raise ValueError('Unexpected file in rollback: '+str(p))
            removed.append({'path':str(resolved),'bytes':sum(p.stat().st_size for p in files)})
            shutil.rmtree(resolved)
    report={'drive':str(root),'verified_current_sha256':local['sha256'],'removed':removed,'bytes_removed':sum(p['bytes'] for p in removed),'pc_rollback':'release/LUCID_BLOCKS_NX_FULL_'+rollback_build+'.nsp','personal_saves_touched':False}
    (BUILD/('reports/cleanup-'+build.lower()+'-'+root.drive[0].lower()+'.json')).write_text(json.dumps(report,indent=2)+'\n')
    print(root,'obsolete build bytes removed:',report['bytes_removed'])

if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--build',default='NSP03',choices=['NSP03','NSP04','NSP05','NSP06'])
    p.add_argument('--rollback',default='NSP02',choices=['NSP02','NSP03','NSP04','NSP05'])
    p.add_argument('drive',type=Path,nargs='+')
    args=p.parse_args()
    for root in args.drive:clean(root,args.build,args.rollback)
