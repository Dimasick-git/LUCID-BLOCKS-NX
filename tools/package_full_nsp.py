"""Package and read back the self-contained Lucid Blocks test NSP."""
from pathlib import Path
import argparse, hashlib, json, os, shutil, struct, subprocess, tempfile
from nca_reader import Nca, pfs
from package_forwarder import verify as verify_launcher

BUILD = Path('C:/Users/dimas/lucid-build')
ROOT = Path(__file__).resolve().parents[1]

def digest(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def romfs_files(read):
    h = struct.unpack('<10Q', read(0, 80)); assert h[0] == 80
    dirs, files = read(h[3], h[4]), read(h[7], h[8])
    result, seen = {}, set()
    def walk(offset, path, depth=0):
        assert depth < 64 and offset not in seen
        seen.add(offset)
        _, _, child, file, _, length = struct.unpack_from('<6I', dirs, offset)
        name = dirs[offset+24:offset+24+length].decode()
        assert '/' not in name and name not in ('.', '..')
        here = path+'/'+name if path and name else name or path
        while file != 0xffffffff:
            _, nextfile, at, size, _, length = struct.unpack_from('<IIQQII', files, file)
            name = files[file+32:file+32+length].decode()
            assert '/' not in name and name not in ('.', '..')
            key = here+'/'+name if here else name
            assert key not in result
            result[key] = (h[9]+at, size)
            file = nextfile
        while child != 0xffffffff:
            nextchild = struct.unpack_from('<I', dirs, child+4)[0]
            walk(child, here, depth+1); child = nextchild
    walk(0, '')
    return result

def verify_payload(path, key_path, expected):
    # Existing verifier checks the original launcher NSO/NPDM and every NCA's
    # hashes, including the IVFC tree of the entire title RomFS.
    archives = verify_launcher(path, key_path)
    keys = {}
    for line in key_path.read_text().splitlines():
        if '=' in line:
            key, value = line.split('=', 1); keys[key.strip()] = value.strip()
    with path.open('rb') as f:
        def read(at, size):
            f.seek(at); return f.read(size)
        found = False
        for _, (base, size) in pfs(read, path.stat().st_size).items():
            nca = Nca(f, base, size, keys)
            if nca.header[0x205] != 0:
                continue
            for section in nca.sections:
                if section[2][3] != 3:
                    continue
                offset, length = nca.romfs(section)
                def readrom(at, size):
                    assert at+size <= length
                    return nca.read(section, offset+at, size)
                files = romfs_files(readrom)
                assert set(files) == set(expected)
                for name, record in expected.items():
                    at, size = files[name]
                    assert size == record['bytes']
                    sha = hashlib.sha256()
                    for pos in range(0, size, 4*1024*1024):
                        sha.update(readrom(at+pos, min(4*1024*1024, size-pos)))
                    assert sha.hexdigest() == record['sha256'], name
                found = True
        assert found
    return archives

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--pack', type=Path, required=True)
    p.add_argument('--keys', type=Path, required=True)
    p.add_argument('--output', type=Path, default=BUILD/'release/LUCID_BLOCKS_NX_FULL_NSP01.nsp')
    p.add_argument('--packer', type=Path, default=Path('C:/Users/dimas/uk-build/hacbrewpack-low-disk-v2/hacbrewpack-low-disk.exe'))
    a = p.parse_args()
    assert not a.output.exists()
    compression = json.loads(a.pack.with_suffix('.verified.json').read_text())
    assert compression['all_logical_resource_checksums_verified']
    assert digest(a.pack) == compression['sha256']
    assert shutil.disk_usage(BUILD).free > a.pack.stat().st_size*4+512*1024*1024
    with tempfile.TemporaryDirectory(prefix='lucid-full-nsp-', dir=BUILD) as temporary:
        work = Path(temporary)
        for name in ['exefs', 'control', 'romfs/lucid-blocks']:
            (work/name).mkdir(parents=True)
        shutil.copyfile(ROOT/'forwarder/hbl.nso', work/'exefs/main')
        shutil.copyfile(ROOT/'forwarder/hbl.npdm', work/'exefs/main.npdm')
        shutil.copyfile(ROOT/'forwarder/icon-dimasick.jpg', work/'control/icon_AmericanEnglish.dat')
        shutil.copyfile(BUILD/'godot-switch-upstream/bin/switch_template_release.nro', work/'romfs/lucid-blocks/lucid-blocks.nro')
        os.link(a.pack, work/'romfs/lucid-blocks/game.pck')
        shutil.copytree(BUILD/'nsp01-cache', work/'romfs/lucid-blocks/cache')
        payload = {f.relative_to(work/'romfs').as_posix(): {'bytes': f.stat().st_size, 'sha256': digest(f)}
                   for f in (work/'romfs').rglob('*') if f.is_file()}
        manifest = {'build': 'NSP01', 'title_id': '0100963461C50000',
                    'storage': 'installed title RomFS; SD saves and writable caches', 'files': payload}
        manifest_path = work/'romfs/install-manifest.json'
        manifest_path.write_text(json.dumps(manifest, indent=2)+'\n')
        expected = dict(payload)
        expected['install-manifest.json'] = {'bytes': manifest_path.stat().st_size, 'sha256': digest(manifest_path)}
        with (BUILD/'reports/full-nsp01-package.log').open('w') as log:
            subprocess.run(['C:/devkitPro/tools/bin/nacptool.exe', '--create', 'Lucid Blocks NX', 'Dimasick-git',
                            '0.1.0-nsp01', str(work/'control/control.nacp')], stdout=log, stderr=subprocess.STDOUT, check=True)
            subprocess.run([str(a.packer), '-k', str(a.keys), '--exefsdir', 'exefs', '--controldir', 'control',
                            '--romfsdir', 'romfs', '--nologo', '--titleid', '0100963461C50000',
                            '--titlename', 'Lucid Blocks NX', '--titlepublisher', 'Dimasick-git'],
                           cwd=work, stdout=log, stderr=subprocess.STDOUT, check=True)
        outputs = list((work/'hacbrewpack_nsp').glob('*.nsp')); assert len(outputs) == 1
        archives = verify_payload(outputs[0], a.keys, expected)
        assert outputs[0].stat().st_size < 0xffffffff
        shutil.move(str(outputs[0]), a.output)
    report = {'file': str(a.output), 'bytes': a.output.stat().st_size, 'sha256': digest(a.output),
              'build': 'NSP01', 'title_id': '0100963461C50000', 'nca_ivfc_and_payload_verified': True,
              'embedded_files': len(expected), 'archives': archives, 'console_launch_verified': False,
              'compressed_game_bytes': compression['bytes'], 'logical_game_bytes': compression['source_bytes']}
    a.output.with_suffix('.verified.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps(report, indent=2))

if __name__ == '__main__':
    main()
