"""Archive the current verified SD bundle and retire older local archives."""
from pathlib import Path
import hashlib,json,zipfile
BUILD=Path('C:/Users/dimas/lucid-build')
root=BUILD/'release/SD_ROOT'
manifest=json.loads((root/'manifest.json').read_text())
build=manifest['build']
assert all(c.isalnum() or c in '.-' for c in build)
out=BUILD/'release'/('LUCID_BLOCKS_NX_'+build.upper().replace('-','_')+'.zip')
with zipfile.ZipFile(out,'x',compression=zipfile.ZIP_STORED,allowZip64=True) as archive:
    for path in sorted(root.rglob('*')):
        if path.is_file():archive.write(path,path.relative_to(root).as_posix())
with zipfile.ZipFile(out) as archive:assert archive.testzip() is None
with out.open('rb') as stream:sha=hashlib.file_digest(stream,'sha256').hexdigest()
report={'build':build,'bytes':out.stat().st_size,'sha256':sha,'zip_crc_verified':True}
out.with_suffix('.verified.json').write_text(json.dumps(report,indent=2)+'\n')
for older in (BUILD/'release').glob('LUCID_BLOCKS_NX_*.zip'):
    if older==out:continue
    for source in [older,older.with_suffix('.verified.json')]:
        target=BUILD/'rejected'/source.name
        assert target.resolve().is_relative_to(BUILD.resolve())
        if source.exists() and not target.exists():source.replace(target)
port=Path(__file__).resolve().parents[1]/'port.json'
settings=json.loads(port.read_text());settings['local_archive']=str(out);settings['current_build']=build
settings['engine_validation']=str(BUILD/('reports/engine-'+build.rsplit('-',1)[-1]+'-validation.json'))
settings['candidate_runtime']['console_boot_status']='BOOTFIX03 registered voxel classes; BOOTFIX04 fixes native TLS constructor codegen, console retest pending' if build.endswith('bootfix04') else 'Current boot fix awaits console retest'
if build.endswith('opt01'):
    settings['candidate_runtime']['console_boot_status']='BOOTFIX04 reached menu then OOM in Jolt terrain collision; OPT01 memory/profile changes await console test'
if build.endswith('opt02'):
    settings['candidate_runtime']['console_boot_status']='OPT01 loaded worlds and saved successfully; OPT02 removes local shadow error storm and bounds fluid scans, hardware performance retest pending'
if build.endswith('opt03'):
    settings['candidate_runtime']['console_boot_status']='OPT02 booted on console; OPT03 matte terrain shaders and SaltyNX bridge await hardware performance test'
if build.endswith('opt04'):
    settings['candidate_runtime']['console_boot_status']='OPT03 SaltyNX connected at 60 Hz; OPT04 shader binary hint and shared persistent item meshes await hardware test'
port.write_text(json.dumps(settings,indent=2)+'\n')
print(json.dumps(report,indent=2))
