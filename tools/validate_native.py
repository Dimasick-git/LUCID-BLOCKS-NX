from pathlib import Path
import argparse,hashlib,json,re,subprocess

def validate(build,devkit):
    out=build/'native';libs=[out/'libgdblocks.switch.template_release.double.arm64.a',build/'upstream-gdblocks/godot-cpp/bin/libgodot-cpp.switch.template_release.double.arm64.a']
    binary=devkit/'devkitA64/bin'
    report={'engine':'4.6.0','precision':'double','runtime_linked':False,'libraries':[]}
    for lib in libs:
        headers=subprocess.check_output([str(binary/'aarch64-none-elf-objdump.exe'),'-f',str(lib)],text=True)
        formats=set(re.findall(r'file format (\S+)',headers))
        if formats!={'elf64-littleaarch64'}:raise RuntimeError((lib,formats))
        report['libraries'].append({'path':str(lib),'bytes':lib.stat().st_size,'sha256':hashlib.sha256(lib.read_bytes()).hexdigest(),'object_count':headers.count('file format '),'formats':sorted(formats)})
    combined=out/'lucid-voxel-arm64.rel.o'
    subprocess.run([str(binary/'aarch64-none-elf-ld.exe'),'-r','--whole-archive',*[str(p) for p in libs],'--no-whole-archive','-o',str(combined)],check=True)
    undefined=subprocess.check_output([str(binary/'aarch64-none-elf-nm.exe'),'-u','-C',str(combined)],text=True)
    # The native game and bindings must resolve each other's Godot C++ symbols.
    internal=[x.strip() for x in undefined.splitlines() if 'godot::' in x and x.lstrip().startswith('U ')]
    if internal:raise RuntimeError('Unresolved Godot symbols: '+repr(internal[:20]))
    symbols=subprocess.check_output([str(binary/'aarch64-none-elf-nm.exe'),'-g','--defined-only',str(combined)],text=True)
    for symbol in ['gdblocks_init','lucid_nx_native_abi_version']:
        if not re.search(r'\b'+symbol+r'$',symbols,re.M):raise RuntimeError('Missing native entry: '+symbol)
    report['weak_optional_symbols']=[x.strip() for x in undefined.splitlines() if x.lstrip().startswith(('w ','v '))];report['relocatable_link_passed']=True;report['undefined_system_symbols']=len(undefined.splitlines());report['notes']='Static ARM64 component only. Godot/Horizon runtime and renderer are still required.'
    (build/'reports/native-validation.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--build-root',type=Path,default=Path('C:/Users/dimas/lucid-build'));p.add_argument('--devkitpro',type=Path,default=Path('C:/devkitPro'));a=p.parse_args();validate(a.build_root,a.devkitpro)
