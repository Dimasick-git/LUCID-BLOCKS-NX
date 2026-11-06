# Runtime integration

The original game's exported API is Godot 4.6 double precision. The Horizon runtime is the pinned Godot Switch 4.7.3 rc fork, using the GLES compatibility renderer. The deko scaffold is not enabled.

`engine_modules/lucid_nx` loads the static ARM64 gdblocks entry through `GDExtensionManager::load_extension_from_function`. The function loader requires a `libgodot://` identifier; a `res://...gdextension` resource path is rejected before the entry is called. The bridge uses `libgodot://lucid_blocks_gdblocks` and lets the manager own the extension token, initialization levels and teardown.

Loading is requested during module SCENE initialization, after core extension interfaces and scene classes exist. The manager then invokes extension SCENE initialization before `Main::setup` finishes. The launcher checks required voxel classes before running game scripts, and aborts with a log if registration failed.

The desktop extension list is empty in the production PCK. Static archives are not dynamic GDExtension libraries and must never be placed in a `.gdextension` libraries table as if they were shared objects.

The Horizon `--main-pack` branch is enabled for the external SD game.pck. Clock-service initialization and all pcv/clkrst session operations are absent following the first hardware fatal report. GPU/global parameters use RGBA32UI texture storage to avoid the GLES uniform-block limit. A desktop GPU check validates bit patterns and partial updates; Tegra rendering still requires console testing.

BOOTFIX02 reached Godot/Mesa successfully, but its extension resource identifier was invalid. BOOTFIX03 corrects that identifier and checks native classes before entering scripts. Successful gameplay, audio, saves, sleep/resume and performance remain hardware acceptance checks.

BOOTFIX03 hardware report confirms static class registration. The next failure is a Data Abort in `ClassDB::_create_instance_func<Essence>` at offset 0x2dbb69c (Build ID e80aa1b76026790b03d0bc816ed3b6cece27e7b0). The instruction stores through `[x0,x0]` immediately after `__aarch64_read_tp`; the register is the thread pointer, so the generated address is twice TP. A minimal devkitA64 15.2 reproducer generates the same invalid instruction with `-fPIC -mtp=soft`.

BOOTFIX04 rebuilds both static archives with `-fPIE -ftls-model=local-exec -mtp=soft`. The static executable owns all TLS variables; local-exec emits TPREL high/low relocations. `check_tls_codegen.py` compares old/new generated assembly. Bundle validation checks the final Essence factory, and boot creates Essence/Item before starting the main scene. These checks do not replace a successful hardware run.

OPT01 hardware logs reached Game Ready, world loading and successful saves. Its long run emitted 48,512 unsupported dual-paraboloid shadow errors. OPT02 forces non-directional light shadows off in LightStorage under HORIZON_ENABLED, so scene culling skips their shadow passes. Water/fire scanning is bounded to the loaded radius under __SWITCH__; loaded chunks retain their simulation tick rate. The stagger calculation now includes Z instead of X twice. Five-second telemetry uses kernel memory queries without clock-service access. OPT02 hardware performance remains unverified.
