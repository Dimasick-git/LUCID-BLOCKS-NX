extends Node

const DISCOVERY_PORT := 24568
const BROWSER_PORT := 24569
const DISCOVER := "LBNX4:DISCOVER"
const PROTOCOL := "LBNX4"
const GAME_PORT := 24567
const MAX_PLAYERS := 4
var server: PacketPeerUDP
var browser: PacketPeerUDP
var rooms: Dictionary = {}
var screens: Array = []
var local_addresses: Array[String] = []
var broadcast_addresses: Array[String] = ["255.255.255.255"]
var scan_targets: Array[String] = []
var scan_cursor := 0
var poll_elapsed := 0.0
var refresh_at := 0
var next_request_at := 0
var next_announce_at := 0
var next_retry_at := 0
var send_error_at := 0
var auto_join := false
var pending_host := false
var joining := false
var message := ""
var manager: Node
var hooked_main: Node
var connected_started := 0
var use_broadcast := true

func _ready() -> void:
    process_mode = Node.PROCESS_MODE_ALWAYS
    get_node("/root/NxLocale").language_changed.connect(refresh_menus)

func _button(sample: Button, text: String, action: String, callback: Callable) -> Button:
    var button := Button.new()
    button.theme = sample.theme
    button.theme_type_variation = sample.theme_type_variation
    button.add_theme_font_override("font", sample.get_theme_font("font"))
    button.add_theme_font_size_override("font_size", 12)
    button.custom_minimum_size = Vector2(0, 24)
    button.text = text
    button.set_meta("nx_lan_action", action)
    button.pressed.connect(callback)
    return button

func build_menu(owner: Node, sample: Button, in_world: bool) -> Control:
    manager = owner
    var overlay := Control.new()
    overlay.set_anchors_preset(Control.PRESET_FULL_RECT)
    overlay.z_index = 100
    overlay.visible = false
    overlay.mouse_filter = Control.MOUSE_FILTER_STOP
    var shade := ColorRect.new()
    shade.set_anchors_preset(Control.PRESET_FULL_RECT)
    shade.color = Color(0, 0, 0, 0.9)
    overlay.add_child(shade)
    var center := CenterContainer.new()
    center.set_anchors_preset(Control.PRESET_FULL_RECT)
    overlay.add_child(center)
    var panel := PanelContainer.new()
    panel.theme = sample.theme
    center.add_child(panel)
    var margin := MarginContainer.new()
    for edge in ["left", "right", "top", "bottom"]:
        margin.add_theme_constant_override("margin_" + edge, 10)
    panel.add_child(margin)
    var column := VBoxContainer.new()
    column.add_theme_constant_override("separation", 6)
    margin.add_child(column)
    var title := Label.new()
    title.text = "LOCAL CO-OP"
    title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    title.add_theme_font_size_override("font_size", 16)
    column.add_child(title)
    var hint := Label.new()
    hint.text = "Two Switch consoles on the same Wi-Fi"
    hint.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    hint.add_theme_font_size_override("font_size", 10)
    column.add_child(hint)
    var status := Label.new()
    status.custom_minimum_size.y = 26
    status.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
    status.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    status.add_theme_font_size_override("font_size", 11)
    column.add_child(status)
    var host := _button(sample, "Create room", "host", host_world)
    column.add_child(host)
    var find := _button(sample, "Find game automatically", "find", start_search)
    column.add_child(find)
    var room_box := VBoxContainer.new()
    room_box.add_theme_constant_override("separation", 5)
    column.add_child(room_box)
    var leave := _button(sample, "Leave room", "leave", _leave)
    column.add_child(leave)
    var back := _button(sample, "Back", "back", _back.bind(in_world))
    column.add_child(back)
    screens.append({"root":overlay, "panel":panel, "status":status, "host":host, "find":find, "rooms":room_box, "leave":leave, "sample":sample, "signature":"", "in_world":in_world})
    if in_world: owner.pause_menu_coop_shell = panel
    else: owner.main_menu_coop_shell = panel
    refresh_menus()
    return overlay

func _back(in_world: bool) -> void:
    auto_join = false
    if in_world: manager._close_pause_menu_coop_panel()
    else: manager._close_main_menu_coop_panel()

func _leave() -> void:
    auto_join = false
    joining = false
    manager.leave_session()

func _is_hosting() -> bool:
    return manager != null and manager.has_active_session() and manager.multiplayer.is_server()

func _any_visible() -> bool:
    for screen in screens:
        if is_instance_valid(screen.root) and screen.root.is_visible_in_tree(): return true
    return false

func refresh_menus() -> void:
    if manager == null: return
    var hosting := _is_hosting()
    var live: bool = manager.has_active_session()
    var status_text := tr(message)
    if hosting:
        var peers: int = manager.multiplayer.get_peers().size()
        status_text = tr("Room open · waiting for your friend") if peers == 0 else tr("Friend connected · return to the game")
        status_text += "  %d/%d" % [peers+1, MAX_PLAYERS]
    elif joining: status_text = tr("Connecting to your friend's world…")
    elif auto_join: status_text = tr("Searching nearby… the game will connect automatically")
    elif message == "": status_text = tr("Create a room or find your friend's game")
    var signature := str(live) + str(joining) + TranslationServer.get_locale()
    for ip in rooms:
        signature += str([ip, rooms[ip].world, rooms[ip].players])
    for screen in screens:
        if not is_instance_valid(screen.root): continue
        var viewport_size: Vector2 = get_viewport().get_visible_rect().size
        screen.panel.custom_minimum_size = Vector2(minf(420, viewport_size.x - 32), 0)
        screen.status.text = status_text
        screen.host.visible = not live and not joining
        screen.find.visible = not live and not joining
        screen.find.text = "Stop searching" if auto_join else "Find game automatically"
        screen.leave.visible = live
        if screen.signature == signature: continue
        screen.signature = signature
        for child in screen.rooms.get_children():
            screen.rooms.remove_child(child)
            child.queue_free()
        if not live and not joining:
            var count := 0
            for ip in rooms:
                var room: Dictionary = rooms[ip]
                if int(room.players) >= MAX_PLAYERS or count >= (2 if viewport_size.y >= 320 else 1): continue
                var button := _button(screen.sample, "", "room", _connect_room.bind(ip))
                button.text = (tr("Join: %s") % str(room.world).left(22)) + "  %d/%d" % [room.players,MAX_PLAYERS]
                screen.rooms.add_child(button)
                count += 1

func host_world() -> void:
    auto_join = false
    if manager == null: return
    var ref = get_node("/root/Ref")
    if ref.world.load_enabled:
        _start_host()
        return
    pending_host = true
    message = "Choose a world — the room will open automatically"
    manager._close_main_menu_coop_panel()
    ref.main._on_main_menu_play_requested()
    print("[nx-lan] host intent: waiting for world selection")

func _start_host() -> void:
    pending_host = false
    manager.config["port"] = GAME_PORT
    manager._sync_inputs_from_config()
    manager.host_session()
    message = "" if _is_hosting() else "Could not open the room. Try again."
    if _is_hosting():
        if manager._is_pause_menu_coop_panel_open(): manager._close_pause_menu_coop_panel()
        if manager._is_main_menu_coop_panel_open(): manager._close_main_menu_coop_panel()
        var ref = get_node("/root/Ref")
        if int(ref.game_menu.state) == 4: ref.game_menu.close_pause()
    next_announce_at = 0
    refresh_menus()

func _world_loaded() -> void:
    if not pending_host: return
    _start_host()

func _cancel_host_selection() -> void:
    pending_host = false

func start_search() -> void:
    if auto_join:
        auto_join = false
        message = ""
    else:
        auto_join = true
        joining = false
        message = ""
        next_request_at = 0
        scan_cursor = 0
    refresh_menus()

func _connect_room(ip: String) -> void:
    if joining or not rooms.has(ip): return
    var room: Dictionary = rooms[ip]
    if not _valid_address(ip) or int(room.players) >= MAX_PLAYERS: return
    auto_join = false
    joining = true
    connected_started = Time.get_ticks_msec()
    message = ""
    manager.join_session(ip, int(room.port))
    print("[nx-lan] joining discovered room ip=", ip, " port=", room.port)
    refresh_menus()

func _valid_address(ip: String) -> bool:
    return ip.is_valid_ip_address() and not ":" in ip and not ip.begins_with("127.") and ip != "0.0.0.0"

func _refresh_addresses() -> void:
    local_addresses.clear()
    broadcast_addresses = ["255.255.255.255"]
    scan_targets.clear()
    var candidates: Array = Array(IP.get_local_addresses())
    candidates.sort_custom(func(a, b): return _address_priority(str(a)) < _address_priority(str(b)))
    var performance = get_node_or_null("/root/NxPerformance")
    if performance != null and performance.platform != null:
        candidates.push_front(str(performance.platform.call("get_lan_address")))
    var has_routed_ipv4: bool = candidates.any(func(value): return _valid_address(str(value)) and not str(value).begins_with("169.254."))
    for candidate in candidates:
        var ip := str(candidate)
        if not _valid_address(ip) or ip in local_addresses: continue
        if has_routed_ipv4 and ip.begins_with("169.254."): continue
        local_addresses.append(ip)
        var prefix := ip.get_slice(".", 0) + "." + ip.get_slice(".", 1) + "." + ip.get_slice(".", 2) + "."
        if prefix + "255" in broadcast_addresses: continue
        broadcast_addresses.append(prefix + "255")
        var cgnat := ip.begins_with("100.") and int(ip.get_slice(".",1)) >= 64 and int(ip.get_slice(".",1)) <= 127
        if ip.begins_with("192.168.") or ip.begins_with("10.") or ip.begins_with("172.") or ip.begins_with("169.254.") or cgnat:
            for last in range(1, 255):
                var target := prefix + str(last)
                scan_targets.append(target)
        if local_addresses.size() >= 3: break
    scan_cursor = 0
    print("[nx-lan] IPv4 addresses=", local_addresses, " broadcast=", broadcast_addresses)

func _address_priority(ip: String) -> int:
    if ip.begins_with("192.168.") or ip.begins_with("10.") or ip.begins_with("172."): return 0
    if ip.begins_with("169.254."): return 2
    return 1

func _open_udp(port: int) -> PacketPeerUDP:
    var udp := PacketPeerUDP.new()
    var result := udp.bind(port, "0.0.0.0")
    if result != OK:
        print("[nx-lan] IPv4 bind port=", port, " error=", result)
        udp.close()
        return null
    udp.set_broadcast_enabled(true)
    print("[nx-lan] IPv4 socket ready port=", udp.get_local_port())
    return udp

func _send(udp: PacketPeerUDP, ip: String, port: int, data: PackedByteArray) -> void:
    var result := udp.set_dest_address(ip, port)
    if result == OK: result = udp.put_packet(data)
    if result != OK and Time.get_ticks_msec() >= send_error_at:
        print("[nx-lan] send failed target=", ip, ":", port, " error=", result)
        send_error_at = Time.get_ticks_msec() + 3000

func _announcement() -> PackedByteArray:
    var ref = get_node("/root/Ref")
    return JSON.stringify({"protocol":PROTOCOL, "world":str(ref.save_file_manager.loaded_file_register.get_data("title", "Lucid Blocks")), "port":int(manager.config.get("port", GAME_PORT)), "players":1 + manager.multiplayer.get_peers().size()}).to_utf8_buffer()

func _receive_room(bytes: PackedByteArray, ip: String) -> void:
    if bytes.size() > 1024 or not _valid_address(ip): return
    var data = JSON.parse_string(bytes.get_string_from_utf8())
    if not data is Dictionary or data.get("protocol", "") != PROTOCOL: return
    var port := int(data.get("port", 0))
    if port < 1 or port > 65535: return
    var fresh := not rooms.has(ip)
    rooms[ip] = {"ip":ip, "port":port, "world":str(data.get("world", "Lucid Blocks")).left(40), "players":clampi(int(data.get("players", 1)),1,MAX_PLAYERS), "seen":Time.get_ticks_msec()}
    if fresh: print("[nx-lan] room found ip=", ip, " port=", port, " world=", rooms[ip].world)

func _process(delta: float) -> void:
    poll_elapsed += delta
    if poll_elapsed < 0.1: return
    poll_elapsed = 0.0
    var ref = get_node_or_null("/root/Ref")
    if ref == null or ref.coop_manager == null: return
    manager = ref.coop_manager
    if is_instance_valid(ref.main) and hooked_main != ref.main:
        hooked_main = ref.main
        hooked_main.world_loaded.connect(_world_loaded)
        var save_menu = hooked_main.get_node_or_null("%SaveFileMenu")
        if save_menu != null: save_menu.exited.connect(_cancel_host_selection)
    var now := Time.get_ticks_msec()
    if joining:
        if manager.guest_persistent_ready:
            joining = false
            message = ""
        elif now - connected_started > 30000 and not manager.receiving_host_world and not manager.client_restore_in_progress:
            joining = false
            manager.disconnect_session(false)
            message = "Connection failed. Search again."
    var hosting := _is_hosting()
    var browsing: bool = not manager.has_active_session() and (_any_visible() or auto_join)
    if not hosting and not browsing:
        if server != null: server.close(); server = null
        if browser != null: browser.close(); browser = null
        return
    if now >= refresh_at:
        _refresh_addresses()
        refresh_at = now + 10000
    if hosting:
        if browser != null: browser.close(); browser = null
        if server == null and now >= next_retry_at:
            server = _open_udp(DISCOVERY_PORT)
            if server == null: next_retry_at = now + 3000
        if server != null:
            for i in range(mini(server.get_available_packet_count(), 32)):
                var bytes := server.get_packet()
                var ip := server.get_packet_ip()
                var port := server.get_packet_port()
                if bytes.size() <= 64 and bytes.get_string_from_utf8() == DISCOVER:
                    _send(server, ip, port, _announcement())
            if now >= next_announce_at:
                if use_broadcast:
                    for ip in broadcast_addresses: _send(server, ip, BROWSER_PORT, _announcement())
                next_announce_at = now + 1000
    else:
        if server != null: server.close(); server = null
        if browser == null and now >= next_retry_at:
            browser = _open_udp(BROWSER_PORT)
            if browser == null: browser = _open_udp(0)
            if browser == null: next_retry_at = now + 3000
        if browser != null:
            if now >= next_request_at:
                if use_broadcast:
                    for ip in broadcast_addresses: _send(browser, ip, DISCOVERY_PORT, DISCOVER.to_utf8_buffer())
                next_request_at = now + 1500
            for i in range(8):
                if scan_cursor >= scan_targets.size(): break
                _send(browser, scan_targets[scan_cursor], DISCOVERY_PORT, DISCOVER.to_utf8_buffer())
                scan_cursor += 1
            for i in range(mini(browser.get_available_packet_count(), 32)):
                var bytes := browser.get_packet()
                var ip := browser.get_packet_ip()
                _receive_room(bytes, ip)
    for ip in rooms.keys():
        if now - int(rooms[ip].seen) > 5000: rooms.erase(ip)
    if auto_join and not joining:
        for ip in rooms:
            if int(rooms[ip].players) < MAX_PLAYERS:
                _connect_room(ip)
                break
    refresh_menus()

func _input(event: InputEvent) -> void:
    if manager == null or not event.is_action_pressed("back", false): return
    if manager._is_main_menu_coop_panel_open(): _back(false)
    elif manager._is_pause_menu_coop_panel_open(): _back(true)
    else: return
    get_viewport().set_input_as_handled()

func _exit_tree() -> void:
    if browser != null: browser.close()
    if server != null: server.close()
