"""devkitA64 compiler settings for godot-cpp; produces Horizon static objects."""
import os
from pathlib import Path
import common_compiler_flags

def options(opts):
    opts.Add('devkitpro','devkitPro root',os.environ.get('DEVKITPRO','C:/devkitPro'))

def exists(env):
    return (Path(env.get('devkitpro','C:/devkitPro'))/'devkitA64/bin/aarch64-none-elf-g++.exe').is_file()

def generate(env):
    root=Path(env['devkitpro']).resolve();binary=root/'devkitA64/bin'
    env.Tool('gcc');env.Tool('g++');env.Tool('ar')
    env.PrependENVPath('PATH',str(binary))
    for key,exe in [('CC','gcc'),('CXX','g++'),('AR','gcc-ar'),('RANLIB','gcc-ranlib')]:
        env[key]=str(binary/('aarch64-none-elf-'+exe+'.exe'))
    env['LINK']=env['CXX'];env['LIBPREFIX']='lib';env['LIBSUFFIX']='.a'
    env['ARCOM']='${TEMPFILE("$AR $ARFLAGS $TARGET.posix $SOURCES.posix")}'
    env['MAXLINELENGTH']=2048
    env['lto']='none';env.use_hot_reload=False
    # These archives are linked into the NRO executable, never dlopen'ed.
    # devkitA64 15.2 + -mtp=soft emits an invalid [tp,tp] store for PIC TLS;
    # local-exec generates TP-relative offsets, matching libnx's static TLS.
    env.Append(CCFLAGS=['-march=armv8-a+crc+crypto','-mtune=cortex-a57','-mtp=soft','-fPIE','-ftls-model=local-exec','-ffunction-sections','-fdata-sections'])
    env.Append(CPPDEFINES=['__SWITCH__'])
    env.Append(CPPPATH=[str(root/'libnx/include')])
    common_compiler_flags.generate(env)
