from pathlib import Path
import os
root=Path(Dir('.').srcnode().abspath)
build=Path(ARGUMENTS.get('build_root','C:/Users/dimas/lucid-build')).resolve()
upstream=build/'upstream-gdblocks'
env=SConscript(str(upstream/'godot-cpp/SConstruct'))
for directory in (upstream/'extension').rglob('*'):
    if directory.is_dir():env.AppendUnique(CPPPATH=[str(directory)])
sources=sorted(str(p) for p in (upstream/'extension/src').rglob('*.cpp'))
sources.append(str(root/'native/abi_check.cpp'))
module=env.StaticLibrary(target=str(build/'native/gdblocks.switch.template_release.double.arm64.a'),source=sources)
Default(module,env['LIBS'])
