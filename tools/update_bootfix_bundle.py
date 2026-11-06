"""Refresh the local bundle after removing early clock-service access."""

from pathlib import Path

import argparse,hashlib,json,re,shutil,subprocess,mmap

from assemble_sd import validate_nro,digest

BUILD=Path('C:/Users/dimas/lucid-build')

ROOT=Path(__file__).resolve().parents[1]

engine=BUILD/'godot-switch-upstream/bin'

parser=argparse.ArgumentParser(description=__doc__)

parser.add_argument('--revision',choices=['bootfix01','bootfix02','bootfix03','bootfix04','opt01','opt02','opt03','opt04'],default='bootfix01')

parser.add_argument('--pack',type=Path,help='Replace game.pck with a newly checked resource pack')

args=parser.parse_args()

label=args.revision.upper()

nro=engine/'switch_template_release.nro'

elf=engine/'godot.switch.template_release.double.arm64.exe'

symbols=subprocess.check_output(['C:/devkitPro/devkitA64/bin/aarch64-none-elf-nm.exe',str(elf)],text=True)

forbidden=[line for line in symbols.splitlines() if re.search(r'\b(?:clkrst\w*|pcv\w*)$',line)]

assert not forbidden,forbidden

assert re.search(r'\bT gdblocks_init$',symbols,re.M)

if args.revision in ('bootfix02','bootfix03','bootfix04','opt01','opt02','opt03','opt04'):

    with elf.open('rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as data:

        assert data.find(b'`--main-pack` was specified on the command line, but this Godot binary was compiled without support')==-1,'Pack argument is still rejected'

        assert data.find(b'#define LUCID_NX_GLOBAL_TEXTURE')>=0,'Horizon uniform storage was not compiled'

    assert 'bind_global_shader_parameters' in symbols,'Horizon uniform binding missing from final link'

if args.revision in ('bootfix03','bootfix04','opt01','opt02','opt03','opt04'):

    bridge=(ROOT/'engine_modules/lucid_nx/register_types.cpp').read_text()

    path=re.search(r'load_extension_from_function\(\s*"([^"]+)"',bridge)[1]

    loader=(BUILD/'godot-switch-upstream/core/extension/gdextension_function_loader.cpp').read_text()

    required_prefix=re.search(r'p_path.begins_with\("([^"]+)"\)',loader)[1]

    assert path.startswith(required_prefix),(path,required_prefix)

    with elf.open('rb') as stream,mmap.mmap(stream.fileno(),0,access=mmap.ACCESS_READ) as data:

        assert data.find(path.encode())>=0,'Static extension path not linked'

        assert data.find((label+': required voxel classes present').encode())>=0,'Native class startup gate not linked'

if args.revision in ('bootfix04','opt01','opt02','opt03','opt04'):

    tls=json.loads((BUILD/'reports/tls-codegen-check.json').read_text())

    assert tls['old_invalid_store_reproduced'] and tls['static_pie_uses_tp_relative_offsets']

    factory=next(line for line in symbols.splitlines() if '_create_instance_func' in line and '7EssenceE' in line)

    address=int(factory.split()[0],16)

    assembly=subprocess.check_output(['C:/devkitPro/devkitA64/bin/aarch64-none-elf-objdump.exe','-d','-C','--start-address='+hex(address),'--stop-address='+hex(address+192),str(elf)],text=True)

    assert '__aarch64_read_tp' in assembly,'Expected native TLS access missing'

    assert not re.search(r'\bstr\s+x\d+,\s*\[x(\d+),\s*x\1\]',assembly),'Invalid [TP,TP] store remains in constructor'

    (BUILD/('reports/essence-'+args.revision+'-disassembly.txt')).write_text(assembly)

validation=validate_nro(nro)

bundle=BUILD/'release/SD_ROOT'

target=bundle/'switch/lucid-blocks/lucid-blocks.nro'

rejected=BUILD/'rejected';rejected.mkdir(exist_ok=True)

backup=rejected/('TEST1-before-'+label+'.nro')

if not backup.exists():shutil.copyfile(target,backup)

shutil.copyfile(nro,target)

assert digest(target)==digest(nro)

readme=bundle/'switch/lucid-blocks/README.txt'

text=(ROOT/'docs/SD_README.txt').read_text(encoding='utf-8')

text=text.replace('Lucid Blocks NX — 0.1.0-test1','Lucid Blocks NX — 0.1.0-test1 / '+label,1)

text+='\nBOOTFIX01: удалены обращения игры к службам частот pcv/clkrst.\nДля обновления достаточно заменить NRO; установленный форвардер подходит.\n'

if args.revision in ('bootfix02','bootfix03','bootfix04','opt01','opt02','opt03','opt04'):text+='BOOTFIX02: разрешена загрузка внешнего game.pck через --main-pack на Switch.\n'

if args.revision in ('bootfix03','bootfix04','opt01','opt02','opt03','opt04'):text+='BOOTFIX03: исправлен libgodot://-путь статического воксельного модуля; добавлена проверка обязательных классов до запуска скриптов.\n'

if args.revision in ('bootfix04','opt01','opt02','opt03','opt04'):text+='BOOTFIX04: статические библиотеки пересобраны с PIE/local-exec TLS; перед сценой проверяется создание Essence и Item.\n'

if args.revision in ('opt01','opt02','opt03','opt04'):text+='OPT01: профиль минимума 32 блока / 100%, полный viewport, без dithering; очередь мешей ограничена четырьмя чанками, временные буферы освобождаются после загрузки.\n'

if args.revision in ('opt02','opt03','opt04'):text+='OPT02: local shadows disabled; water/fire scan bounded to loaded radius; [nx-perf] telemetry every five seconds. Saved render scale is preserved.\n'


if args.revision=='opt03':text+='OPT03: matte terrain, fewer texture samples, inactive effect bypass; SaltyNX direct EGL telemetry and FPSLocker cap; detailed frame stages. Hardware retest pending.\n'
if args.revision=='opt04':text+='OPT04: retrievable shader binary hint; cached and shared item-icon meshes; startup stage timings. First GPU cache population still needs a console run.\n'
readme.write_text(text,encoding='utf-8')

path=bundle/'manifest.json';manifest=json.loads(path.read_text())

manifest['build']='0.1.0-test1-'+args.revision

manifest['nro_validation']=validation

if args.pack:

    checked=json.loads(args.pack.with_suffix('.verified.json').read_text())

    assert checked['original_resource_checksums_verified'] and checked['entries']==7522

    assert checked['runtime_requirement']=='Godot/Horizon with static gdblocks extension'

    previous=bundle/'switch/lucid-blocks/game.pck'

    saved=rejected/('game-before-'+label+'.pck')

    if not saved.exists():previous.replace(saved)

    shutil.copyfile(args.pack,previous)

    assert digest(previous)==digest(args.pack)

    manifest['files']['switch/lucid-blocks/game.pck']={'bytes':previous.stat().st_size,'sha256':digest(previous)}

for name in ['switch/lucid-blocks/lucid-blocks.nro','switch/lucid-blocks/README.txt']:

    p=bundle/name;manifest['files'][name]={'bytes':p.stat().st_size,'sha256':digest(p)}

path.write_text(json.dumps(manifest,indent=2)+'\n')

report={'build':manifest['build'],'nro_bytes':nro.stat().st_size,'sha256':digest(nro),

    'clock_service_symbols_present':False,'static_gdblocks_linked':True,

    'external_main_pack_rejection_removed':args.revision in ('bootfix02','bootfix03','bootfix04','opt01','opt02','opt03','opt04'),

    'horizon_uniform_storage_compiled':args.revision in ('bootfix02','bootfix03','bootfix04','opt01','opt02','opt03','opt04'),

    'static_extension_path_contract_checked':args.revision in ('bootfix03','bootfix04','opt01','opt02','opt03','opt04'),

    'native_tls_codegen_checked':args.revision in ('bootfix04','opt01','opt02','opt03','opt04'),

    'console_launch_verified':False,'initial_crash_evidence':str(BUILD/'reports/test1-system-crash')}

(BUILD/('reports/engine-'+args.revision+'-validation.json')).write_text(json.dumps(report,indent=2)+'\n')

for name in ['LUCID_BLOCKS_NX_0.1.0_TEST1.zip','LUCID_BLOCKS_NX_0.1.0_TEST1.verified.json']:

    source=BUILD/'release'/name;destination=rejected/name

    assert destination.resolve().is_relative_to(BUILD.resolve())

    if source.exists() and not destination.exists():source.replace(destination)

print(json.dumps(report,indent=2))

