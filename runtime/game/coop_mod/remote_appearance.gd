extends Node3D

const SKIN_SHADER = preload("res://NxPort/coop_mod/remote_skin.gdshader")
const BLOCK_MESH = preload("res://main/world/rendering/block_mesh/block_mesh.tres")
const BLOCK_SHADER = preload("res://NxPort/coop_mod/remote_block.gdshader")
var actor: Node3D
var skeleton: Skeleton3D
var item_root: Node3D
var item_mesh: MeshInstance3D
var item_id := -1
var skin_materials: Array[ShaderMaterial] = []
var tint := Color.WHITE
var left_handed := false
var action := 0
var phase := 0.0
var duration := 0.3
var action_serial := -1
var hand_variant := ""
var target_pitch := 0.0
var bones: Dictionary = {}
var head_rest := Quaternion.IDENTITY
var last_sequence := -1
var epoch := -1

func setup(owner_actor: Node3D) -> void:
    actor = owner_actor
    skeleton = actor.avatar_skeleton
    _prepare_skin(actor.avatar_instance)
    if skeleton != null:
        for side in ["Right", "Left"]:
            for part in ["Arm", "ForeArm", "Hand"]:
                bones[side+part] = skeleton.find_bone("mixamorig_"+side+part)
        bones["Head"] = skeleton.find_bone("mixamorig_Head")
        if int(bones["Head"]) >= 0: head_rest = skeleton.get_bone_pose_rotation(int(bones["Head"]))
    set_skin(actor.target_skin_color)
    set_item(actor.target_held_item_id)

func _prepare_skin(node: Node) -> void:
    if node == null: return
    if node is MeshInstance3D and node.mesh != null:
        if node.skin != null and skeleton != null:
            var skin: Skin = node.skin.duplicate()
            for bind in range(skin.get_bind_count()):
                var name := str(skin.get_bind_name(bind))
                if name != "":
                    var index := skeleton.find_bone(name)
                    if index >= 0:
                        skin.set_bind_name(bind,&"")
                        skin.set_bind_bone(bind,index)
            node.skin = skin
            # Explicit path is required for scenes packed by newer Godot tools.
            node.skeleton = node.get_path_to(skeleton)
        for surface in range(node.mesh.get_surface_count()):
            var original = node.get_active_material(surface)
            if original is StandardMaterial3D:
                var material := ShaderMaterial.new()
                material.shader = SKIN_SHADER
                material.set_shader_parameter("skin_texture", original.albedo_texture)
                material.set_shader_parameter("has_texture", original.albedo_texture != null)
                material.set_shader_parameter("base_color", original.albedo_color if original.albedo_texture != null else Color(0.72,0.6,0.5))
                material.set_shader_parameter("skin_color", tint)
                node.set_surface_override_material(surface, material)
                skin_materials.append(material)
    for child in node.get_children(): _prepare_skin(child)

func set_skin(color: Color) -> void:
    if tint.is_equal_approx(color): return
    tint = color
    for material in skin_materials: material.set_shader_parameter("skin_color", color)

func set_item(id: int) -> void:
    if id == item_id and is_instance_valid(item_root): return
    if is_instance_valid(item_root):
        remove_child(item_root)
        item_root.queue_free()
    item_root = null
    item_mesh = null
    item_id = id
    if not ItemMap.id_to_resource.has(id): return
    var item: Item = ItemMap.map(id)
    item_root = Node3D.new()
    item_root.name = "OriginalHeldItem"
    add_child(item_root)
    item_mesh = MeshInstance3D.new()
    item_mesh.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
    item_root.add_child(item_mesh)
    if item is Block and not item.foliage and not item.override_icon:
        item_mesh.mesh = BLOCK_MESH
        var material := ShaderMaterial.new()
        material.shader = BLOCK_SHADER
        material.set_shader_parameter("block_texture", item.texture)
        item_mesh.material_override = material
        item_mesh.scale = Vector3.ONE * 0.3
    else:
        item_mesh.mesh = item.mesh
        if item_mesh.mesh == null:
            var quad := QuadMesh.new()
            quad.size = Vector2(1,1)
            item_mesh.mesh = quad
        var material := StandardMaterial3D.new()
        material.albedo_texture = item.icon
        material.texture_filter = BaseMaterial3D.TEXTURE_FILTER_NEAREST
        material.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA_SCISSOR
        material.cull_mode = BaseMaterial3D.CULL_DISABLED
        material.roughness = 1.0
        item_mesh.material_override = material
        var bounds := item_mesh.mesh.get_aabb()
        var length := maxf(maxf(bounds.size.x, bounds.size.y), 0.01)
        var size := 0.55 if item is Tool or item is Gun or item is Wand else 0.27
        if item is Food: size = 0.2
        item_mesh.scale = Vector3.ONE * size / length
        item_mesh.rotation = Vector3(PI, PI*0.5, 0)
        var grip := Vector3(0.5,0.5,0.5)
        if item is Tool or item is Wand: grip.y = 0.8
        if item is Gun: grip = Vector3(0.5,0.8,0.5)
        item_mesh.position = -(item_mesh.basis * (bounds.position + bounds.size*grip))

func apply(data: Dictionary) -> void:
    if epoch == int(data.get("epoch",0)) and int(data.get("seq",0)) <= last_sequence: return
    epoch = int(data.get("epoch",0))
    last_sequence = int(data.get("seq",0))
    set_item(int(data.get("item", -1)))
    set_skin(data.get("skin", Color.WHITE))
    left_handed = bool(data.get("left", false))
    action = int(data.get("action", 0))
    phase = clampf(float(data.get("phase", 0.0)),0,1)
    duration = maxf(float(data.get("duration",0.3)),0.05)
    action_serial = int(data.get("serial",0))
    hand_variant = str(data.get("variant", ""))

func update_pose(delta: float, pitch: float, crouch: float) -> void:
    if actor == null: return
    if is_instance_valid(item_root): item_root.visible = not actor.target_downed
    if actor.target_downed: return
    target_pitch = pitch
    if action in [1,2]: phase = fposmod(phase + delta/duration,1.0)
    elif action in [3,4]: phase = minf(1.0,phase+delta/duration)
    var side := "Left" if left_handed else "Right"
    var sign_x := -1.0 if left_handed else 1.0
    var hand := Vector3(sign_x*0.32,1.08-crouch*0.25,-0.3)
    var wave := sin(phase*PI)
    var item: Item = ItemMap.map(item_id) if ItemMap.id_to_resource.has(item_id) else null
    if action != 0:
        if item is Gun:
            hand.z += wave*0.13
            hand.y += wave*0.055
        elif item is Food:
            hand = hand.lerp(Vector3(sign_x*0.11,1.52-crouch*0.25,-0.12),wave)
        elif item is Block:
            hand.z -= wave*0.22
        elif hand_variant.containsn("sword") or hand_variant.containsn("knife"):
            hand.x += sign_x*wave*0.3
            hand.z -= wave*0.18
        elif hand_variant.containsn("shovel"):
            hand.z -= wave*0.35
            hand.y -= wave*0.1
        else:
            hand.y += cos(phase*PI)*0.25
            hand.z -= wave*0.28
    var aim := Basis(Vector3.RIGHT,pitch)
    var shoulder := Vector3(sign_x*0.22,1.35-crouch*0.25,0)
    hand = shoulder + aim*(hand-shoulder)
    var world_hand: Vector3 = actor.visual_root.global_transform * hand
    if skeleton != null:
        _aim_head(pitch)
        _solve_arm(side,world_hand)
        var hand_bone := int(bones.get(side+"Hand",-1))
        if hand_bone >= 0: world_hand = (skeleton.global_transform*skeleton.get_bone_global_pose(hand_bone)).origin
    if is_instance_valid(item_root):
        item_root.global_position = world_hand
        item_root.global_basis = actor.visual_root.global_basis.orthonormalized()*aim
        if action != 0 and not item is Gun:
            item_root.rotate_object_local(Vector3.RIGHT, wave*-0.65)

func _aim_head(pitch: float) -> void:
    var index := int(bones.get("Head",-1))
    if index >= 0:
        skeleton.set_bone_pose_rotation(index, head_rest)
        var axis: Vector3 = (skeleton.global_basis.inverse()*actor.visual_root.global_basis.x).normalized()
        _set_global_rotation(index, Quaternion(axis,pitch*0.65)*skeleton.get_bone_global_pose(index).basis.get_rotation_quaternion())

func _set_global_rotation(index: int, rotation: Quaternion) -> void:
    var parent := skeleton.get_bone_parent(index)
    # Godot 4 poses are local transforms, not deltas multiplied by rest.
    var basis := Quaternion.IDENTITY
    if parent >= 0: basis = skeleton.get_bone_global_pose(parent).basis.get_rotation_quaternion()
    skeleton.set_bone_pose_rotation(index, (basis.inverse()*rotation).normalized())

func _solve_arm(side: String, world_target: Vector3) -> void:
    var upper := int(bones.get(side+"Arm",-1))
    var lower := int(bones.get(side+"ForeArm",-1))
    var wrist := int(bones.get(side+"Hand",-1))
    if min(upper,lower,wrist) < 0: return
    var a := skeleton.get_bone_global_pose(upper).origin
    var b := skeleton.get_bone_global_pose(lower).origin
    var c := skeleton.get_bone_global_pose(wrist).origin
    var target := skeleton.to_local(world_target)
    var l1 := a.distance_to(b)
    var l2 := b.distance_to(c)
    if minf(l1,l2) < 0.0001: return
    var distance := clampf(a.distance_to(target),absf(l1-l2)+0.0001,l1+l2-0.0001)
    var forward := (target-a).normalized()
    var pole: Vector3 = skeleton.global_basis.inverse()*(actor.visual_root.global_basis*Vector3(-0.5 if side=="Left" else 0.5,-0.6,0.2))
    var perpendicular := pole - forward*pole.dot(forward)
    if perpendicular.length_squared()<0.000001: perpendicular = forward.cross(Vector3.UP)
    perpendicular = perpendicular.normalized()
    var along := (l1*l1-l2*l2+distance*distance)/(2.0*distance)
    var elbow := a+forward*along+perpendicular*sqrt(maxf(l1*l1-along*along,0.0))
    var upper_rotation := skeleton.get_bone_global_pose(upper).basis.get_rotation_quaternion()
    _set_global_rotation(upper,Quaternion((b-a).normalized(),(elbow-a).normalized())*upper_rotation)
    b = skeleton.get_bone_global_pose(lower).origin
    c = skeleton.get_bone_global_pose(wrist).origin
    var lower_rotation := skeleton.get_bone_global_pose(lower).basis.get_rotation_quaternion()
    _set_global_rotation(lower,Quaternion((c-b).normalized(),(target-b).normalized())*lower_rotation)
