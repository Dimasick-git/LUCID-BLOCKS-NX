"""Build and read back the small SD forwarder; key material stays local."""
from pathlib import Path
import argparse, hashlib, json, shutil, subprocess, tempfile
from nca_reader import Nca, pfs, sha
from validate_forwarder import validate

ROOT = Path(__file__).resolve().parents[1]
BUILD = Path('C:/Users/dimas/lucid-build')

def verify(path, keys_path):
    keys = {}
    for line in keys_path.read_text().splitlines():
        if '=' in line:
            key, value = line.split('=', 1)
            keys[key.strip()] = value.strip()
    found = False
    reports = []
    with path.open('rb') as file:
        def read(at, size):
            file.seek(at)
            return file.read(size)
        for name, (at, size) in pfs(read, path.stat().st_size).items():
            digest = hashlib.sha256(read(at, size)).hexdigest()
            assert name.endswith('.nca') and name.split('.')[0] == digest[:32], 'NCA content ID mismatch'
            nca = Nca(file, at, size, keys)
            for section in nca.sections:
                if section[2][3] == 2:
                    offset, _, entries = nca.pfs(section)
                    if 'main.npdm' in entries:
                        pos, length = entries['main.npdm']
                        data = nca.read(section, offset + pos, length)
                        validate(data)
                        # hacBrewPack changes only the public ACID modulus.
                        original = bytearray((ROOT/'forwarder/hbl.npdm').read_bytes())
                        packaged = bytearray(data)
                        import struct
                        for blob in (original, packaged):
                            acid = struct.unpack_from('<I', blob, 0x78)[0]
                            blob[acid+0x100:acid+0x200] = bytes(256)
                        assert packaged == original, 'NPDM changed beyond signing modulus'
                        pos, length = entries['main']
                        assert nca.read(section, offset+pos, length) == (ROOT/'forwarder/hbl.nso').read_bytes()
                        found = True
                elif section[2][3] == 3:
                    nca.romfs(section)
            reports.append({'name': name, 'bytes': size, 'sha256': digest})
    assert found, 'No program NPDM'
    return reports

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--keys', required=True, type=Path)
    parser.add_argument('--packer', type=Path, default=Path('C:/Users/dimas/uk-build/hacbrewpack-low-disk-v2/hacbrewpack-low-disk.exe'))
    parser.add_argument('--output', type=Path, default=BUILD/'release/LUCID_BLOCKS_NX_forwarder.nsp')
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit('Refusing to overwrite existing NSP')
    validate((ROOT/'forwarder/hbl.npdm').read_bytes())
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='lucid-forwarder-', dir=BUILD) as temporary:
        work = Path(temporary)
        (work/'exefs').mkdir(); (work/'control').mkdir()
        shutil.copyfile(ROOT/'forwarder/hbl.nso', work/'exefs/main')
        shutil.copyfile(ROOT/'forwarder/hbl.npdm', work/'exefs/main.npdm')
        shutil.copyfile(ROOT/'forwarder/icon.jpg', work/'control/icon_AmericanEnglish.dat')
        log = BUILD/'reports/forwarder-package.log'
        with log.open('w', encoding='utf-8') as stream:
            subprocess.run(['C:/devkitPro/tools/bin/nacptool.exe', '--create', 'Lucid Blocks NX', 'Dimasick-git', '0.1.0-test1', str(work/'control/control.nacp')], check=True, stdout=stream, stderr=subprocess.STDOUT)
            subprocess.run([str(args.packer), '-k', str(args.keys), '--exefsdir', 'exefs', '--controldir', 'control', '--noromfs', '--nologo', '--titleid', '0100963461C50000', '--titlename', 'Lucid Blocks NX', '--titlepublisher', 'Dimasick-git'], cwd=work, check=True, stdout=stream, stderr=subprocess.STDOUT)
        candidates = list((work/'hacbrewpack_nsp').glob('*.nsp'))
        assert len(candidates) == 1
        archives = verify(candidates[0], args.keys)
        shutil.copyfile(candidates[0], args.output)
    report = {'path': str(args.output), 'bytes': args.output.stat().st_size, 'sha256': hashlib.sha256(args.output.read_bytes()).hexdigest(), 'title_id': '0100963461C50000', 'nro': '/switch/lucid-blocks/lucid-blocks.nro', 'packaged_npdm_verified': True, 'archives': archives, 'console_launch_verified': False}
    args.output.with_suffix('.verified.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
