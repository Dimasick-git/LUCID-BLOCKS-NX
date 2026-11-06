"""Reproduce the devkitA64 PIC/soft-TP fault and check static TLS codegen."""
from pathlib import Path
import json,re,subprocess
BUILD=Path('C:/Users/dimas/lucid-build')
ROOT=Path(__file__).resolve().parents[1]
source=BUILD/'native/tls-abi-probe.cpp'
source.write_text('extern thread_local const void *constructing;\nvoid save_constructing(const void *p) { constructing = p; }\n')
compiler='C:/devkitPro/devkitA64/bin/aarch64-none-elf-g++.exe'
output={}
for label,flags in [('old_pic',['-fPIC']),('static_pie',['-fPIE','-ftls-model=local-exec'])]:
    target=source.with_name('tls-abi-'+label+'.s')
    subprocess.run([compiler,'-O2','-mtp=soft',*flags,'-S',str(source),'-o',str(target)],check=True)
    output[label]=target.read_text()
bad_store=r'str\s+x\d+,\s*\[x(\d+),\s*x\1\]'
assert re.search(bad_store,output['old_pic']),'Expected reproducer changed; investigate compiler version'
assert not re.search(bad_store,output['static_pie'])
assert ':tprel_hi12:' in output['static_pie'] and ':tprel_lo12_nc:' in output['static_pie']
platform=(ROOT/'platform/scons/switch.py').read_text()
assert "'-fPIE'" in platform and "'-ftls-model=local-exec'" in platform and "'-fPIC'" not in platform
report={'old_invalid_store_reproduced':True,'static_pie_uses_tp_relative_offsets':True,'assembly':output,'console_runtime_verified':False}
(BUILD/'reports/tls-codegen-check.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS: reproduced old [TP,TP] store; static PIE/local-exec uses distinct TP-relative address')
