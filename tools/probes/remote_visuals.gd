extends Node
var running := false
var failed := false
const Marker = preload("res://NxPort/coop_mod/remote_player_marker.gd")
func _ready() -> void: process_mode = Node.PROCESS_MODE_ALWAYS
func _process(_delta: float) -> void:
    if running: return
    var ref = get_node_or_null("/root/Ref")
    if ref == null or not is_instance_valid(ref.main): return
    if ref.save_file_manager.device_file != null: ref.save_file_manager.device_file.set_data("tutorial",false)
    if not ref.main.loaded: return
    running = true
    run.call_deferred()
func check(value: bool, label: String) -> void:
    if not value:
        failed = true
        printerr("REMOTE_VISUAL_CHECK_FAILED: ",label)
func run() -> void:
    var viewport := SubViewport.new()
    viewport.size = Vector2i(640,720)
    viewport.own_world_3d = true
    viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
    add_child(viewport)
    var environment := WorldEnvironment.new()
    environment.environment = Environment.new()
    environment.environment.background_mode = Environment.BG_COLOR
    environment.environment.background_color = Color(0.05,0.06,0.08)
    environment.environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
    environment.environment.ambient_light_color = Color.WHITE
    environment.environment.ambient_light_energy = 0.8
    viewport.add_child(environment)
    var camera := Camera3D.new()
    viewport.add_child(camera)
    camera.position = Vector3(2,1.35,-3)
    camera.look_at(Vector3(0,0.95,0))
    var marker = Marker.new()
    viewport.add_child(marker)
    marker.setup(9001)
    marker.set_display_name("REMOTE TEST")
    for mesh in marker.avatar_instance.find_children("*","MeshInstance3D",true,false):
        print("REMOTE_SKIN_BIND mesh=",mesh.get_path()," skeleton_path=",mesh.skeleton," skin=",mesh.skin)
        if mesh.skin != null:
            print("REMOTE_SKIN_BIND_COUNT=",mesh.skin.get_bind_count()," first=",mesh.skin.get_bind_name(0)," bone=",mesh.skin.get_bind_bone(0))
            check(mesh.skeleton != NodePath(""),"skinned mesh has skeleton path")
            check(mesh.get_node_or_null(mesh.skeleton)==marker.avatar_skeleton,"mesh bound to animated skeleton")
    marker.apply_state(true,Vector3.ZERO,0,0,false,true,0,0)
    check(marker.using_imported_avatar,"avatar loaded")
    check(marker.appearance.skin_materials.size()>0,"skin material supports recoloring")
    var total := 0
    var blocks := 0
    var seen: Dictionary = {}
    for id in ItemMap.all_item_ids:
        var item: Item = ItemMap.map(id)
        marker.appearance.set_item(id)
        check(marker.appearance.item_mesh != null,"mesh for item "+str(id))
        if item is Block and not item.foliage and not item.override_icon:
            blocks += 1
            check(marker.appearance.item_mesh.material_override.get_shader_parameter("block_texture")==item.texture,"original block texture "+str(id))
        else:
            check(marker.appearance.item_mesh.material_override.albedo_texture==item.icon,"original item texture "+str(id))
        total += 1
        seen[item.get_class()] = true
        if total % 16 == 0: await get_tree().process_frame
    var example := -1
    for id in ItemMap.all_item_ids:
        if ItemMap.map(id) is Gun: example = id; break
    var data := {"item":example,"skin":Color(0.25,0.7,1),"left":false,"action":3,"serial":3,"phase":0.3,"duration":0.3,"seq":100,"epoch":1,"variant":"Gun"}
    marker.set_visual_state(data)
    marker.apply_state(true,Vector3.ZERO,0,0.4,false,true,0,3)
    for i in range(10): await get_tree().process_frame
    print("REMOTE_HAND_BONES=",marker.appearance.bones," position=",marker.appearance.item_root.global_position)
    check(marker.appearance.item_mesh.mesh != null,"held gun visible")
    check(marker.appearance.item_root.global_position.is_finite(),"hand transform finite")
    check(marker.appearance.item_root.global_position.distance_to(Vector3(0,1.0,-0.3))<0.8,"item attached near hand")
    for material in marker.appearance.skin_materials:
        check(material.get_shader_parameter("skin_color").is_equal_approx(data.skin),"color applied")
    await RenderingServer.frame_post_draw
    viewport.get_texture().get_image().save_png("C:/Users/dimas/lucid-build/reports/remote-player-gun.png")
    for state in range(5):
        data["seq"] = 101+state
        data["action"] = state
        marker.set_visual_state(data)
        check(marker.appearance.action==state,"action "+str(state))
    var before: int = marker.appearance.last_sequence
    data["seq"]=1
    marker.set_visual_state(data)
    check(marker.appearance.last_sequence==before,"stale visual packet ignored")
    marker.set_downed(true)
    await get_tree().process_frame
    check(not marker.appearance.item_root.visible,"no floating item when downed")
    marker.set_downed(false)
    data["seq"]=200;data["left"]=true;data["skin"]=Color(1,0.3,0.2)
    marker.set_visual_state(data)
    await get_tree().process_frame
    check(marker.appearance.left_handed,"left handed appearance")
    print("REMOTE_VISUAL_CATALOG total=",total," blocks=",blocks," classes=",seen.keys())
    print("REMOTE_VISUALS_", "FAILED" if failed else "PASSED")
    viewport.queue_free()
    await get_tree().process_frame
    get_tree().quit(1 if failed else 0)
