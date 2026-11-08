extends Node
var platform: RefCounted
var loading := false
var loading_start_ms := 0
func _ready() -> void:
    process_mode = Node.PROCESS_MODE_ALWAYS
    if ClassDB.class_exists("NxPlatform"):
        platform = ClassDB.instantiate("NxPlatform")
func begin_loading() -> void:
    loading = true
    loading_start_ms = Time.get_ticks_msec()
    if platform != null:
        platform.call("set_loading", true)
func end_loading() -> void:
    if loading:
        print("[nx-loading] world_load_ms=", Time.get_ticks_msec() - loading_start_ms)
    loading = false
    if platform != null:
        platform.call("set_loading", false)
func _exit_tree() -> void:
    end_loading()
