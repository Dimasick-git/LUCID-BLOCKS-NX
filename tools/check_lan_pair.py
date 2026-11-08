"""Exercise automatic discovery and co-op through the real game menus."""
from pathlib import Path
import hashlib, os, struct, subprocess, sys, json, argparse
from inspect_pck import inspect, MAGIC
from project_binary import prepend_autoloads

ROOT = Path(__file__).resolve().parents[1]
BUILD = Path('C:/Users/dimas/lucid-build')
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--scan-only',action='store_true')
parser.add_argument('--label',default='lan-pair')
parser.add_argument('--clients',type=int,choices=(1,3),default=1)
parser.add_argument('--gameplay',action='store_true')
parser.add_argument('--entities',action='store_true')
parser.add_argument('--npc',choices=('manikin','kodama','mimic','gel','moth','hwobbb'))
args=parser.parse_args()
assert args.label.replace('-','').isalnum()
exe = BUILD/'host-check/switch-profile.exe'
script = ROOT/'tools/probes/lan_pair.gd'
stage = BUILD/('host-check/lan-pair' if args.clients==1 else 'host-check/lan-four')
stage.mkdir(exist_ok=True)
subprocess.run([str(BUILD/'tools/gdre_tools.exe'), '--headless', '--bytecode=4.6.0',
    '--output='+str(stage), '--compile='+str(script)], check=True, capture_output=True)
info = inspect(exe)
with exe.open('rb') as f:
    e = next(e for e in info['entries'] if e['path']=='project.binary')
    f.seek(e['offset']); original = f.read(e['size'])

def inject(files, remove=()):
    current = inspect(exe)
    entries = {e['path']:dict(e) for e in current['entries'] if e['path'] not in remove}
    with exe.open('r+b') as f:
        f.seek(-12, 2)
        for name, data in files.items():
            entries[name] = dict(path=name, offset=f.tell(), size=len(data), md5=hashlib.md5(data).hexdigest(), flags=0)
            f.write(data)
        directory = f.tell(); f.write(struct.pack('<I', len(entries)))
        for e in entries.values():
            name=e['path'].encode(); name+=bytes((-len(name))%4)
            f.write(struct.pack('<I', len(name))+name+struct.pack('<QQ', e['offset']-current['file_base'],e['size'])+bytes.fromhex(e['md5'])+struct.pack('<I',e['flags']))
        f.write(struct.pack('<QI',f.tell()-current['pack_offset'],MAGIC))
        f.seek(current['pack_offset']+32); f.write(struct.pack('<Q',directory-current['pack_offset']))
    inspect(exe)

addon = 'NxPort/lan_pair_probe.gdc'
processes = []
logs = []
success = False
roles=['host']+['client' if i==1 else 'client'+str(i) for i in range(1,args.clients+1)]
try:
    inject({'project.binary':prepend_autoloads(original, {'NxLanPairProbe':'res://'+addon}), addon:(stage/'lan_pair.gdc').read_bytes()})
    for index,role in enumerate(roles):
        env = os.environ.copy()
        for key, name in [('APPDATA','appdata'),('LOCALAPPDATA','localappdata')]:
            path=stage/role/name; path.mkdir(parents=True,exist_ok=True); env[key]=str(path)
        log=(BUILD/('reports/'+args.label+'-'+role+'.log')).open('wb'); logs.append(log)
        processes.append(subprocess.Popen([str(exe), '--rendering-method', 'gl_compatibility', '--resolution', '320x180', '--disable-crash-handler','--', '--role='+('host' if index==0 else 'client'), '--client-index='+str(index), '--expected-peers='+str(args.clients)]+(['--scan-only'] if args.scan_only else [])+(['--gameplay'] if args.gameplay else [])+(['--entities'] if args.entities else [])+(['--npc='+args.npc] if args.npc else []),
            cwd=Path('C:/Program Files (x86)/Steam/steamapps/common/lucid-blocks'), env=env,
            stdout=log, stderr=subprocess.STDOUT, creationflags=subprocess.CREATE_NO_WINDOW))
    codes=[p.wait(timeout=330) for p in processes]
    for log in logs: log.close()
    outputs=[(BUILD/('reports/'+args.label+'-'+role+'.log')).read_text(encoding='utf-8',errors='replace') for role in roles]
    success=all(c==0 for c in codes) and all('LAN_PAIR_STABLE' in s and 'SCRIPT ERROR' not in s and 'Lambda capture at index' not in s for s in outputs)
    if args.gameplay: success = success and all('LAN_GAMEPLAY_PASSED' in s for s in outputs)
    if args.gameplay: success = success and 'LAN_DEAD_MOB_ATTACK_REJECTED' in outputs[0]
    if args.entities: success = success and all('LAN_ENTITIES_PASSED' in s for s in outputs)
    (BUILD/('reports/'+args.label+'-verified.json')).write_text(json.dumps({
        'passed':success, 'exit_codes':codes, 'real_game_processes':len(roles),
        'transport':'ENet with automatic IPv4 discovery', 'userdata_isolated':True,
        'broadcast_disabled':args.scan_only, 'peer_address_supplied':False,
        'main_menu_auto_host':'LAN_PAIR_HOST_MENU_BUTTONS_PASSED' in outputs[0],
        'automatic_discovery':all('[nx-lan] joining discovered room ip=' in s for s in outputs[1:]),
        'host_place_received': all('LAN_PAIR_HOST_PLACE_RECEIVED' in s for s in outputs[1:]),
        'guest_break_received': 'LAN_PAIR_GUEST_BREAK_RECEIVED' in outputs[0],
        'appearance_received_both_ways': all('LAN_PAIR_VISUALS_PASSED' in s for s in outputs),
        'combat_repeat_hits': all('LAN_COMBAT_REPEAT_PASSED' in s for s in outputs[1:]) if args.gameplay else None,
        'mob_death': all('LAN_COMBAT_DEATH_PASSED' in s for s in outputs[1:]) if args.gameplay else None,
        'dead_mob_attack_rejected': 'LAN_DEAD_MOB_ATTACK_REJECTED' in outputs[0] if args.gameplay else None,
        'revive_in_place': all('LAN_REVIVE_IN_PLACE_PASSED' in s for s in outputs[1:]) if args.gameplay else None,
        'respawn_at_spawn': all('LAN_RESPAWN_AT_SPAWN_PASSED' in s for s in outputs[1:]) if args.gameplay else None,
        'respawn_near_partner': all('LAN_RESPAWN_NEAR_PARTNER_PASSED' in s for s in outputs[1:]) if args.gameplay else None,
        'npc_appearance_all_guests': all('LAN_ENTITIES_PASSED' in s for s in outputs) if args.entities else None,
        'all_peers_present': all('LAN_PAIR_ALL_PEERS_READY' in s for s in outputs),
        'host_gameplay_without_wait_overlay': 'LAN_PAIR_HOST_MENU_BUTTONS_PASSED' in outputs[0],
        'common_spawn': 'LAN_PAIR_CLIENT_READY' in outputs[1] and 'LAN_PAIR_BAD_SPAWN_OR_SAVE' not in outputs[1],
        'console_tested':False,
        'desktop_renderer_limitations':'Original desktop GLES renderer reports its existing 4096 shader-instance limit; Horizon shader adapter is verified separately.'
    },indent=2)+'\n')
    print('LAN pair check:', 'PASSED' if success else 'FAILED', 'exit=', codes, flush=True)
    if not success:
        for role,output in zip(roles,outputs):
            lines=[s for s in output.splitlines() if any(t in s for t in ('LAN_PAIR','SCRIPT ERROR','at:', 'coop]', 'nx-'))]
            print(role, '\n'.join(lines[-45:]).encode('ascii','backslashreplace').decode())
finally:
    for process in processes:
        if process.poll() is None: process.kill(); process.wait()
    for log in logs:
        if not log.closed: log.close()
    inject({'project.binary':original}, remove=[addon])
raise SystemExit(0 if success else 1)
