"""Assemble the NRO, checked game pack and forwarder into one SD directory."""
from pathlib import Path
import argparse, hashlib, json, shutil, struct
ROOT=Path(__file__).resolve().parents[1]
BUILD=Path('C:/Users/dimas/lucid-build')

def digest(path):
    with path.open('rb') as file:
        return hashlib.file_digest(file,'sha256').hexdigest()

def validate_nro(path):
    with path.open('rb') as file:
        header=file.read(128)
        assert header[16:20]==b'NRO0','NRO magic'
        size=struct.unpack_from('<I',header,24)[0]
        assert 128<size<path.stat().st_size,'NRO size/assets'
        for at in (32,40,48):
            offset,length=struct.unpack_from('<II',header,at)
            assert offset+length<=size,'NRO segment bounds'
        file.seek(size);assets=file.read(56)
        assert assets[:4]==b'ASET','NRO asset header'
        for at in (8,24,40):
            offset,length=struct.unpack_from('<QQ',assets,at)
            assert size+offset+length<=path.stat().st_size,'Asset bounds'
        offset,length=struct.unpack_from('<QQ',assets,24)
        assert length==0x4000,'NACP size'
        file.seek(size+offset);nacp=file.read(length)
        assert nacp[:0x200].split(b'\0')[0]==b'Lucid Blocks NX','NACP title'
        assert nacp[0x200:0x300].split(b'\0')[0]==b'Dimasick-git','NACP publisher'
        assert nacp[0x3060:0x3070].split(b'\0')[0] in (b'0.1.0-test1',b'0.1.0-nsp03',b'0.1.0-nsp04',b'0.1.0-nsp05',b'0.1.0-nsp06',b'0.1.0-nsp07'),'NACP version'
    return {'segments_and_assets_valid':True,'program_bytes':size,'total_bytes':path.stat().st_size}

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,default=BUILD/'release/SD_ROOT')
    args=parser.parse_args()
    if args.output.exists():raise SystemExit('Refusing to overwrite an existing assembled directory')
    engine=BUILD/'godot-switch-upstream/bin/switch_template_release.nro'
    validation=validate_nro(engine)
    game=BUILD/'release/game.pck'
    report=json.loads(game.with_suffix('.verified.json').read_text())
    assert report['original_resource_checksums_verified'] and report['entries']==7522
    assert report['runtime_requirement']=='Godot/Horizon with static gdblocks extension'
    forwarder=BUILD/'release/LUCID_BLOCKS_NX_forwarder.nsp'
    nsp_report=json.loads(forwarder.with_suffix('.verified.json').read_text())
    assert nsp_report['packaged_npdm_verified'] and digest(forwarder)==nsp_report['sha256']
    mappings={
        'switch/lucid-blocks/lucid-blocks.nro':engine,
        'switch/lucid-blocks/game.pck':game,
        'LUCID_BLOCKS_NX_forwarder.nsp':forwarder,
        'switch/lucid-blocks/README.txt':ROOT/'docs/SD_README.txt',
        'switch/lucid-blocks/licenses/Godot-LICENSE.txt':BUILD/'godot-switch-upstream/LICENSE.txt',
        'switch/lucid-blocks/licenses/Godot-COPYRIGHT.txt':BUILD/'godot-switch-upstream/COPYRIGHT.txt',
        'switch/lucid-blocks/licenses/gdblocks-LICENSE.md':BUILD/'upstream-gdblocks/LICENSE.md',
        'switch/lucid-blocks/licenses/forwarder-LICENSE.md':ROOT/'forwarder/LICENSE.md',
    }
    manifest={'build':'0.1.0-test1','game_version':'5.2.0','console_gameplay_verified':False,'nro_validation':validation,'files':{}}
    for name,source in mappings.items():
        assert source.stat().st_size<0xffffffff,'File exceeds FAT32 maximum'
        target=args.output/name;target.parent.mkdir(parents=True,exist_ok=True)
        print('Assembling',name,flush=True);shutil.copyfile(source,target)
        sha=digest(source);assert digest(target)==sha
        manifest['files'][name]={'bytes':target.stat().st_size,'sha256':sha}
    (args.output/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    print('Assembled:',args.output,flush=True)

if __name__=='__main__':main()
