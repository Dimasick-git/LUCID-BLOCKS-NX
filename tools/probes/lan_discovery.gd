extends Node
var running := false
func _ready() -> void:
    process_mode = Node.PROCESS_MODE_ALWAYS
func _process(_delta: float) -> void:
    if running: return
    var ref = get_node_or_null("/root/Ref")
    if ref == null or not is_instance_valid(ref.main) or ref.coop_manager == null: return
    if ref.save_file_manager.device_file != null:
        ref.save_file_manager.device_file.set_data("tutorial", false)
    if not ref.main.loaded: return
    running = true
    run.call_deferred()
func check(value: bool, description: String) -> void:
    if not value:
        printerr("LAN_MENU_CHECK_FAILED: ", description)
        get_tree().quit(1)
func run() -> void:
    var ref = get_node("/root/Ref")
    var helper = get_node("/root/NxLan")
    check(not helper._valid_address("127.0.0.1"), "loopback cannot be a discovered peer")
    check(not helper._valid_address("0.0.0.0"), "wildcard cannot be a discovered peer")
    helper.rooms.clear()
    helper._receive_room("{bad json".to_utf8_buffer(), "192.168.4.77")
    helper._receive_room(JSON.stringify({"protocol":"LBNX1", "port":24567}).to_utf8_buffer(), "192.168.4.77")
    helper._receive_room(JSON.stringify({"protocol":helper.PROTOCOL, "port":0}).to_utf8_buffer(), "192.168.4.77")
    check(helper.rooms.is_empty(), "invalid and old-version packets rejected")
    for last in range(77,80):
        helper._receive_room(JSON.stringify({"protocol":helper.PROTOCOL, "port":24567, "world":"A very long world title for a nearby friend", "players":1}).to_utf8_buffer(), "192.168.4."+str(last))
    check(helper.rooms.size()==3, "valid room announcements accepted")
    helper._receive_room(JSON.stringify({"protocol":helper.PROTOCOL,"port":24567,"players":4}).to_utf8_buffer(),"192.168.4.77")
    check(helper.rooms["192.168.4.77"].players==4,"four-player room capacity retained")
    helper._connect_room("192.168.4.77")
    check(not helper.joining,"full room cannot be joined")
    helper._receive_room(JSON.stringify({"protocol":helper.PROTOCOL,"port":24567,"players":3}).to_utf8_buffer(),"192.168.4.77")
    check(helper.rooms["192.168.4.77"].players==3,"room with three players remains discoverable")
    get_node("/root/NxLocale").set_language("ru")
    ref.coop_manager._open_main_menu_coop_panel()
    helper.refresh_menus()
    await get_tree().process_frame
    await RenderingServer.frame_post_draw
    await get_tree().process_frame
    var panel: Control = ref.coop_manager.main_menu_coop_shell
    var rect := panel.get_global_rect()
    var view := get_viewport().get_visible_rect()
    check(rect.position.x >= -1 and rect.position.y >= -1 and rect.end.x <= view.end.x+1 and rect.end.y <= view.end.y+1, "room list and buttons fit screen")
    check(ref.coop_manager.main_menu_coop_panel.find_children("*", "LineEdit", true, false).is_empty(), "no manual IP or port fields")
    get_viewport().get_texture().get_image().save_png("C:/Users/dimas/lucid-build/reports/lan04-russian-found.png")
    helper.rooms.clear()
    ref.coop_manager._close_main_menu_coop_panel()
    print("LAN_AUTOMATIC_MENU_PASSED")
    get_tree().quit()
