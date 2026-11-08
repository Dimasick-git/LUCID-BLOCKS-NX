extends Node
var running := false
var role := "host"
var elapsed := 0.0
var connected_at := 0.0
var ready_reported := false
const TEST_CELL := Vector3i(4, 4, 4)
const TEST_BLOCK := 163165934
var block_seen := false
var host_phase := 0
var last_report := -1
var leaving := false
var scan_only := false
var visuals_started := false
var visuals_verified := false
var expected_peers := 1
var client_index := 0
var all_peers_ready := false
var all_ready_at := 0.0
var gameplay_mode := false
var gameplay_started := false
var gameplay_passed := false
var test_mob: Entity
var combat_client_sent := false
var combat_initial_health := 0
var combat_stage := 0
var test_death_position := Vector3.ZERO
var entities_mode := false
var entities_passed := false
var test_entities: Array[Entity] = []
var npc_names = ["manikin","kodama","mimic","gel","moth","hwobbb"]

func _ready() -> void:
    process_mode = Node.PROCESS_MODE_ALWAYS
    for arg in OS.get_cmdline_user_args():
        if arg.begins_with("--role="): role = arg.trim_prefix("--role=")
        if arg == "--scan-only": scan_only = true
        if arg == "--gameplay": gameplay_mode = true
        if arg == "--entities": entities_mode = true
        if arg.begins_with("--npc="): npc_names = [arg.trim_prefix("--npc=")]
        if arg.begins_with("--expected-peers="): expected_peers = int(arg.get_slice("=",1))
        if arg.begins_with("--client-index="): client_index = int(arg.get_slice("=",1))

func _process(delta: float) -> void:
    elapsed += delta
    if elapsed > 290.0:
        printerr("LAN_PAIR_TIMEOUT role=", role)
        get_tree().quit(2)
        return
    var ref = get_node_or_null("/root/Ref")
    if ref == null or not is_instance_valid(ref.main): return
    if is_instance_valid(ref.save_file_manager) and ref.save_file_manager.device_file != null:
        ref.save_file_manager.device_file.set_data("tutorial", false)
    if not running and ref.main.loaded and ref.coop_manager != null:
        running = true
        run.call_deferred()
    if not running or ref.coop_manager == null: return
    var manager = ref.coop_manager
    if gameplay_mode and all_peers_ready:
        tick_gameplay(ref,manager)
    if entities_mode and all_peers_ready:
        tick_entity_appearance(ref,manager)
    if manager.multiplayer.get_peers().size() == expected_peers and manager.peer_states.size() == expected_peers+1 and manager.markers.size() == expected_peers:
        var active_count := 0
        for state in manager.peer_states.values():
            if state.get("active",false): active_count += 1
        if active_count == expected_peers+1 and not all_peers_ready:
            all_peers_ready = true
            all_ready_at = elapsed
            print("LAN_PAIR_ALL_PEERS_READY role=",role," clients=",expected_peers)
    if manager.has_connected_remote_peers() and (role == "host" or manager.guest_persistent_ready):
        if not visuals_started:
            visuals_started = true
            exercise_visuals.call_deferred()
    if visuals_started and not visuals_verified:
        var validated := 0
        for remote_id in manager.multiplayer.get_peers():
            var data: Dictionary = manager.nx_peer_visuals.get(remote_id,{})
            var expected := Color(0.25,0.7,1) if remote_id == 1 else Color(1,0.3,0.2)
            if int(data.get("serial",0)) < 5 or not data.get("skin",Color.WHITE).is_equal_approx(expected) or not manager.markers.has(remote_id): continue
            var marker = manager.markers[remote_id]
            if marker.appearance != null and marker.appearance.item_mesh != null and marker.appearance.tint.is_equal_approx(expected):
                validated += 1
        if validated == expected_peers:
            visuals_verified = true
            print("LAN_PAIR_VISUALS_PASSED role=",role," peers=",validated)
    if role == "host" and host_phase > 0:
        if int(elapsed / 10.0) != last_report:
            last_report = int(elapsed / 10.0)
            print("LAN_PAIR_HOST_POLL states=", manager.peer_states.size(), " peers=", manager.multiplayer.get_peers(), " paused=", get_tree().paused)
        if host_phase == 1 and all_peers_ready:
            for id in manager.peer_states:
                if int(id) != 1 and bool(manager.peer_states[id].get("active", false)):
                    print("LAN_PAIR_HOST_GUEST_ACTIVE")
                    ref.world.place_block_at(TEST_CELL, ItemMap.map(TEST_BLOCK), true, true)
                    manager.broadcast_host_world_changes([[TEST_CELL, TEST_BLOCK]], [])
                    host_phase = 2
                    break
        elif host_phase == 2 and ref.world.get_block_type_at(TEST_CELL).id != TEST_BLOCK:
            print("LAN_PAIR_GUEST_BREAK_RECEIVED")
            connected_at = elapsed
            host_phase = 3
        elif host_phase == 3 and all_peers_ready and elapsed - all_ready_at > 25.0 and visuals_verified and (not gameplay_mode or gameplay_passed) and (not entities_mode or entities_passed):
            print("LAN_PAIR_STABLE role=host shared_block=true")
            get_tree().quit(0)
    if role == "client" and manager.guest_persistent_ready and ref.world.load_enabled and not ref.player.disabled and not ready_reported:
        ready_reported = true
        connected_at = elapsed
        var distance := 100000.0
        if manager.peer_states.has(1):
            distance = ref.player.global_position.distance_to(manager.peer_states[1].get("position", Vector3.ZERO))
        print("LAN_PAIR_CLIENT_READY distance=", distance, " remote_save=", ref.save_file_manager.nx_remote_world_loaded)
        if distance > 16.0 or not ref.save_file_manager.nx_remote_world_loaded:
            printerr("LAN_PAIR_BAD_SPAWN_OR_SAVE")
            get_tree().quit(3)
    if role == "client" and ready_reported and ref.world.is_position_loaded(TEST_CELL):
        var block = ref.world.get_block_type_at(TEST_CELL)
        if not block_seen and block != null and block.id == TEST_BLOCK:
            block_seen = true
            print("LAN_PAIR_HOST_PLACE_RECEIVED")
            manager.request_break_block.rpc_id(1, manager.get_active_dimension_instance_key(), TEST_CELL, TEST_BLOCK, false, false, false, false, false)
        elif block_seen and block != null and block.id != TEST_BLOCK and all_peers_ready and elapsed - all_ready_at > 18.0 and visuals_verified and (not gameplay_mode or gameplay_passed) and (not entities_mode or entities_passed):
            if not leaving:
                leaving = true
                leave_and_verify.call_deferred()

func leave_and_verify() -> void:
    var ref = get_node("/root/Ref")
    await ref.coop_manager.leave_session()
    while ref.coop_manager.client_menu_kick_pending:
        await get_tree().process_frame
    if ref.save_file_manager.nx_remote_world_loaded or ref.world.load_enabled:
        printerr("LAN_PAIR_LEAVE_ISOLATION_FAILED")
        get_tree().quit(5)
        return
    print("LAN_PAIR_GUEST_RETURNED_TO_PERSONAL_MENU")
    print("LAN_PAIR_STABLE role=client shared_block=true")
    get_tree().quit(0)

func exercise_visuals() -> void:
    var ref = get_node("/root/Ref")
    var selected := TEST_BLOCK
    if role == "host":
        for id in ItemMap.all_item_ids:
            if ItemMap.map(id) is Gun: selected = id; break
    var item := ItemState.new()
    item.initialize(ItemMap.map(selected))
    ref.player.held_item_inventory.set_item(ref.player.held_item_index,item)
    print("LAN_PAIR_VISUAL_SOURCE role=",role," item=",selected," save_fields=",item.get_save_data().size())
    ref.save_file_manager.settings_file.set_data("skin_modulate",Color(0.25,0.7,1) if role=="host" else Color(1,0.3,0.2))
    ref.save_file_manager.settings_file.set_data("left_hand",role=="client")
    ref.player._on_settings_updated()
    await get_tree().process_frame
    for action in [3,3,1,2,4,0]:
        var hand = ref.player.get_node("%PlayerHand").current_hand
        match action:
            3: hand.hit()
            1: hand.hit_sustain_start()
            2: hand.interact_sustain_start()
            4: hand.interact()
            0: hand.idle()
        await get_tree().create_timer(0.15).timeout

var entity_acks: Dictionary = {}

func tick_entity_appearance(ref,manager) -> void:
    ref.player.invincible = true
    if role == "host":
        if test_entities.is_empty():
            var orphans_before := int(Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT))
            for npc_name in npc_names:
                var folder: String = "bubblebear" if npc_name == "hwobbb" else npc_name
                var entity: Entity = load("res://main/entity/"+folder+"/"+npc_name+".tscn").instantiate()
                entity.set_meta("coop_uuid","nx-appearance-"+npc_name)
                get_tree().root.add_child(entity)
                entity.max_health = 200
                entity.health = 200
                entity.invincible = true
                var model = manager._find_first_entity_model(entity)
                if model != null and "variant" in model: model.variant = maxi(0,model.variants-1)
                if model != null and "base_color_1" in model:
                    model.base_color_1 = Color(0.8,0.2,0.4)
                    model.base_color_2 = Color(0.2,0.8,0.4)
                    model.update_colors()
                if "color_1" in entity:
                    entity.color_1 = Color(0.8,0.2,0.4)
                    entity.color_2 = Color(0.2,0.8,0.4)
                    entity.update_colors()
                if "core_models" in entity: entity.variant = entity.core_models.size()-1
                if "copy_block" in entity:
                    entity.copy_block = ItemMap.map(TEST_BLOCK)
                    entity.update_block()
                test_entities.append(entity)
                entity.global_position = Vector3((test_entities.size()-1)*1.5-3,2,-2)
                if entity.has_method("override_position"): entity.override_position()
            var orphans_after := int(Performance.get_monitor(Performance.OBJECT_ORPHAN_NODE_COUNT))
            print("LAN_ENTITIES_ORPHANS before=",orphans_before," after=",orphans_after)
            assert(orphans_after <= orphans_before,"NPC creation does not leak unparented nodes")
        for i in test_entities.size():
            if is_instance_valid(test_entities[i]):
                if not test_entities[i].has_method("override_position"):
                    test_entities[i].global_position = Vector3(i*1.5-3,1,-2)
                    test_entities[i].set_physics_process(false)
    elif not entities_passed:
        for npc_name in npc_names:
            var entity = manager.synced_entities.get("nx-appearance-"+npc_name)
            if not is_instance_valid(entity): return
            var model = manager._find_first_entity_model(entity)
            if model != null and "variant" in model and model.variant != maxi(0,model.variants-1): return
            if model != null and "base_color_1" in model and not model.base_color_1.is_equal_approx(Color(0.8,0.2,0.4)): return
            if "color_1" in entity and not entity.color_1.is_equal_approx(Color(0.8,0.2,0.4)): return
            if "core_models" in entity and entity.variant != entity.core_models.size()-1: return
            if "copy_block" in entity and (entity.copy_block == null or entity.copy_block.id != TEST_BLOCK): return
        entities_passed = true
        print("LAN_ENTITIES_PASSED role=client index=",client_index," count=",npc_names.size())
        entities_result.rpc_id(1)

@rpc("any_peer","call_remote","reliable")
func entities_result() -> void:
    if role != "host": return
    entity_acks[multiplayer.get_remote_sender_id()] = true
    if entity_acks.size() == expected_peers:
        entities_passed = true
        print("LAN_ENTITIES_PASSED role=host guests=",entity_acks.size())

func tick_gameplay(ref,manager) -> void:
    if role == "host":
        if not gameplay_started:
            gameplay_started = true
            test_mob = load("res://main/entity/manikin/manikin.tscn").instantiate()
            test_mob.set_meta("coop_uuid","nx-combat-target")
            get_tree().root.add_child(test_mob)
            test_mob.global_position = Vector3(0.5,1,-2.0)
            test_mob.invincible = false
            test_mob.invincible_temporary = false
            test_mob.direct_damage_cooldown = false
            test_mob.can_endure = false
            test_mob.disabled = false
            combat_initial_health = test_mob.health
            var floor_changes: Array = []
            for x in range(-4,5):
                for z in range(-4,5): floor_changes.append([Vector3i(x,0,z),TEST_BLOCK])
            manager.broadcast_host_world_changes(floor_changes,[])
            print("LAN_COMBAT_HOST_SPAWN health=",test_mob.health)
        if is_instance_valid(test_mob):
            test_mob.global_position = Vector3(0.5,1,-2.0)
            test_mob.set_physics_process(false)
            if test_mob.health < combat_initial_health:
                print("LAN_COMBAT_HOST_DAMAGE_CONFIRMED health=",test_mob.health)
                combat_initial_health = test_mob.health
            if test_mob.dead and combat_stage == 0:
                var ghost_attack = test_mob.get_node_or_null("%Attack")
                if ghost_attack != null:
                    assert(not ghost_attack.attack(ref.player,ref.player.global_position),"dead mob cannot attack")
                    print("LAN_DEAD_MOB_ATTACK_REJECTED")
                combat_stage = 1
        if combat_stage == 1:
            for id in manager.peer_states:
                if int(id) != 1 and manager.peer_states[id].get("downed",false):
                    print("LAN_REVIVE_HOST_REQUEST position=",manager.peer_states[id].position)
                    manager._host_attempt_revive(1,int(id))
                    combat_stage = 2
    elif not combat_client_sent:
        var target = manager.synced_entities.get("nx-combat-target")
        if is_instance_valid(target):
            combat_client_sent = true
            attack_real_target.call_deferred(target)

func attack_real_target(target: Entity) -> void:
    var ref = get_node("/root/Ref")
    ref.player.global_position = Vector3(0.5,1,0.5)
    ref.coop_manager._reset_local_player_motion()
    var ray: RayCast3D = ref.player.get_node("%InteractRayCast3D")
    var area: Area3D = target.get_node("%InteractArea3D")
    ray.target_position = ray.to_local(area.global_position)
    await get_tree().physics_frame
    await get_tree().physics_frame
    var data: Dictionary = ref.player.get_interact_data()
    print("LAN_COMBAT_RAY target=",data.get("target")," expected=",target," cooldown=",target.direct_damage_cooldown," disabled=",target.disabled," collider=",ray.get_collider()," player=",ref.player.global_position," mob=",target.global_position," begin=",data.interact_begin," end=",data.interact_end," fallback=",ref.coop_manager.find_client_ray_attack_target(data.interact_begin,data.interact_end))
    if data.get("target") != target:
        printerr("LAN_COMBAT_RAY_TARGET_FAILED")
        get_tree().quit(8)
        return
    var attack = ref.player.get_node("%Attack")
    var initial_health: int = target.health
    for i in 3:
        var result: bool = attack.attack(target,area.global_position,0,0)
        print("LAN_COMBAT_ATTACK_SENT result=",result," round=",i)
        await get_tree().create_timer(0.7).timeout
    assert(target.health <= initial_health-3,"three client hits reduce authoritative health")
    print("LAN_COMBAT_REPEAT_PASSED health=",target.health)
    attack.damage = 999
    attack.attack(target,area.global_position,0,0)
    await get_tree().create_timer(0.5).timeout
    assert(not is_instance_valid(target) or target.dead,"client sees authoritative death")
    attack.damage = 1
    print("LAN_COMBAT_DEATH_PASSED")
    ref.player.die()
    assert(ref.coop_manager.local_downed,"real death is intercepted by co-op")
    test_death_position = ref.player.global_position
    for attempt in 150:
        if not ref.coop_manager.local_downed: break
        await get_tree().create_timer(0.1).timeout
    assert(not ref.coop_manager.local_downed,"host revives guest")
    assert(ref.player.health == int(ceil(ref.player.max_health*0.5)),"revive grants half health")
    assert(ref.player.global_position.distance_to(test_death_position)<1.0,"revived where downed")
    assert(ref.coop_manager._is_safe_respawn_position(ref.player.global_position),"revive has solid ground")
    print("LAN_REVIVE_IN_PLACE_PASSED health=",ref.player.health)
    await get_tree().create_timer(0.3).timeout
    ref.world.respawn_positions[Vector3i(3,1,3)] = true
    ref.coop_manager._enter_local_downed_state()
    await ref.coop_manager.nx_respawn_at_spawn()
    assert(not ref.coop_manager.local_downed,"manual spawn respawn completes")
    assert(ref.player.global_position.distance_to(Vector3(3.5,1,3.5))<1.0,"respawns at marked spawn")
    print("LAN_RESPAWN_AT_SPAWN_PASSED position=",ref.player.global_position)
    ref.coop_manager._enter_local_downed_state()
    ref.coop_manager._respawn_local_downed_near_partner()
    await get_tree().create_timer(0.5).timeout
    assert(not ref.coop_manager.local_downed,"manual partner respawn completes")
    assert(ref.player.global_position.distance_to(ref.coop_manager.peer_states[1].position)<3.2,"respawns near teammate")
    print("LAN_RESPAWN_NEAR_PARTNER_PASSED position=",ref.player.global_position)
    gameplay_passed = true
    print("LAN_GAMEPLAY_PASSED role=client")
    gameplay_result.rpc_id(1)

@rpc("any_peer","call_remote","reliable")
func gameplay_result() -> void:
    if role == "host" and combat_stage != 2: return
    gameplay_passed = true
    print("LAN_GAMEPLAY_PASSED role=",role)

func run() -> void:
    elapsed = 0.0
    var ref = get_node("/root/Ref")
    var manager = ref.coop_manager
    if scan_only:
        get_node("/root/NxLan").use_broadcast = false
        print("LAN_PAIR_UNICAST_ONLY")
    manager.config["address"] = "127.0.0.1"
    manager.config["port"] = 24567
    if manager.address_input != null: manager.address_input.text = "127.0.0.1"
    if manager.port_input != null: manager.port_input.value = 24567
    if role == "host":
        manager._open_main_menu_coop_panel()
        for button in manager.main_menu_coop_panel.find_children("*", "Button", true, false):
            if button.get_meta("nx_lan_action", "") == "host":
                button.pressed.emit()
                break
        await get_tree().create_timer(1.0).timeout
        assert(get_node("/root/NxLan").pending_host, "Main menu remembers host intent")
        assert(ref.main.get_node("%SaveFileMenu").visible, "Host button opens world selection")
        ref.save_file_manager.initialize_file()
        var register = ref.save_file_manager.loaded_file_register
        register.set_data("world_seed", 1337)
        register.set_data("title", "NX LAN isolated probe")
        register.set_data("divine", true)
        register.set_data("progression_disabled", true)
        ref.save_file_manager.load_file(register, false)
        await ref.main.enter_game(true, true)
        if gameplay_mode or entities_mode:
            for x in range(-4,5):
                for z in range(-4,5):
                    ref.world.place_block_at(Vector3(x,0,z),ItemMap.map(TEST_BLOCK),false,false)
        print("LAN_PAIR_HOST_WORLD_READY position=", ref.player.global_position)
        assert(manager.has_active_session(), "Selecting a world starts hosting automatically")
        await get_tree().process_frame
        assert(not manager.pause_menu_coop_panel.visible, "Host starts gameplay without a waiting overlay")
        assert(ref.game_menu.state == ref.game_menu.DEFAULT, "Host is not left in pause")
        await RenderingServer.frame_post_draw
        get_viewport().get_texture().get_image().save_png("C:/Users/dimas/lucid-build/reports/lan05-host-playing.png")
        print("LAN_PAIR_HOST_MENU_BUTTONS_PASSED")
        host_phase = 1
    else:
        manager._open_main_menu_coop_panel()
        await RenderingServer.frame_post_draw
        get_viewport().get_texture().get_image().save_png("C:/Users/dimas/lucid-build/reports/lan-menu-english.png")
        get_node("/root/NxLocale").set_language("ru")
        await RenderingServer.frame_post_draw
        get_viewport().get_texture().get_image().save_png("C:/Users/dimas/lucid-build/reports/lan-menu-russian.png")
        get_node("/root/NxLocale").set_language("en")
        await get_tree().create_timer(5.0+client_index*2.0).timeout
        var join_pressed := false
        for button in manager.main_menu_coop_panel.find_children("*", "Button", true, false):
            if button.get_meta("nx_lan_action", "") == "find":
                button.pressed.emit()
                join_pressed = true
                break
        assert(join_pressed, "Main LAN join button exists")
        print("LAN_PAIR_CLIENT_MENU_BUTTON_PASSED")
