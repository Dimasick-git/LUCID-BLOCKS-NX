from pathlib import Path
import difflib,subprocess
r=Path('C:/Users/dimas/lucid-blocks-nx');e=Path('C:/Users/dimas/lucid-build/godot-switch-upstream');g=Path('C:/Users/dimas/lucid-build/game')
p=e/'platform/switch/display_server_switch.h';s=p.read_text();s=s.replace('Size2i window_size = Size2i(1280, 720);','''Size2i window_size = Size2i(1280, 720);
    Point2i mouse_position = Point2i(640, 360);
    DisplayServerEnums::MouseMode mouse_mode = DisplayServerEnums::MOUSE_MODE_VISIBLE;
    DisplayServerEnums::MouseMode mouse_override_mode = DisplayServerEnums::MOUSE_MODE_VISIBLE;
    bool mouse_override_enabled = false;''')
s=s.replace('void mouse_set_mode(DisplayServerEnums::MouseMode p_mode) override {}','void mouse_set_mode(DisplayServerEnums::MouseMode p_mode) override { mouse_mode = p_mode; }\n    DisplayServerEnums::MouseMode mouse_get_mode() const override { return mouse_override_enabled ? mouse_override_mode : mouse_mode; }\n    void warp_mouse(const Point2i &p_position) override;')
s=s.replace('void mouse_set_mode_override(DisplayServerEnums::MouseMode p_mode) override {}','void mouse_set_mode_override(DisplayServerEnums::MouseMode p_mode) override { mouse_override_mode = p_mode; }').replace('void mouse_set_mode_override_enabled(bool p_override_enabled) override {}','void mouse_set_mode_override_enabled(bool p_override_enabled) override { mouse_override_enabled = p_override_enabled; }').replace('Point2i mouse_get_position() const override { return Point2i(); }','Point2i mouse_get_position() const override { return mouse_position; }');p.write_text(s)
p=e/'platform/switch/display_server_switch.cpp';s=p.read_text();s=s.replace('void DisplayServerSwitch::_dispatch_input_event(const Ref<InputEvent> &p_event) {','void DisplayServerSwitch::_dispatch_input_event(const Ref<InputEvent> &p_event) {\n    Ref<InputEventMouse> mouse = p_event;\n    if (mouse.is_valid()) mouse_position = mouse->get_position();')
s=s.replace('case DisplayServerEnums::FEATURE_TOUCHSCREEN:','case DisplayServerEnums::FEATURE_MOUSE:\n        case DisplayServerEnums::FEATURE_TOUCHSCREEN:')
s+='''
void DisplayServerSwitch::warp_mouse(const Point2i &p_position) {
    Point2i next = p_position.clamp(Point2i(), window_size - Size2i(1, 1));
    Point2i relative = next - mouse_position;
    mouse_position = next;
    Ref<InputEventMouseMotion> motion;
    motion.instantiate();
    motion->set_window_id(DisplayServerEnums::MAIN_WINDOW_ID);
    motion->set_device(-1);
    motion->set_position(next);
    motion->set_global_position(next);
    motion->set_relative(relative);
    motion->set_screen_relative(relative);
    motion->set_button_mask(Input::get_singleton()->get_mouse_button_mask());
    Input::get_singleton()->parse_input_event(motion);
}
''';p.write_text(s)
for rel in ['platform/switch/display_server_switch.h','platform/switch/display_server_switch.cpp']:
 old=subprocess.check_output(['git','-C',str(e),'show','HEAD:'+rel],text=True);new=(e/rel).read_text();dest=r/'patches'/Path(rel+'.patch');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(''.join(difflib.unified_diff(old.splitlines(True),new.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)))
rel='main/ui/mouse/mouse_handler.gd';p=g/rel;s=p.read_text();s=s.replace('func _ready() -> void :','''var nx_cursor: TextureRect

func _ready() -> void :
    if OS.has_feature("switch"):
        var layer := CanvasLayer.new()
        layer.layer = 1000
        add_child(layer)
        nx_cursor = TextureRect.new()
        nx_cursor.mouse_filter = Control.MOUSE_FILTER_IGNORE
        nx_cursor.texture_filter = CanvasItem.TEXTURE_FILTER_NEAREST
        layer.add_child(nx_cursor)
        window_focused = true
        _nx_menu_buttons()
'''.replace('    ','\t'))
s=s.replace('Input.set_custom_mouse_cursor(pressed_cursor_resized if clicked else default_cursor_resized, Input.CURSOR_ARROW, resized_hotspot)','''Input.set_custom_mouse_cursor(pressed_cursor_resized if clicked else default_cursor_resized, Input.CURSOR_ARROW, resized_hotspot)
    if is_instance_valid(nx_cursor):
        var image: Image = pressed_cursor_resized if clicked else default_cursor_resized
        nx_cursor.texture = ImageTexture.create_from_image(image)
        nx_cursor.size = image.get_size()
'''.replace('    ','\t'))
s=s.replace('func _process(delta: float) -> void :','''func _process(delta: float) -> void :
    if is_instance_valid(nx_cursor):
        nx_cursor.visible = not captured and window_focused
        var screen_scale: Vector2 = get_viewport().get_screen_transform().get_scale()
        nx_cursor.scale = Vector2.ONE / screen_scale
        nx_cursor.position = get_viewport().get_mouse_position() - resized_hotspot * nx_cursor.scale
'''.replace('    ','\t'))
s+='''
func _nx_menu_buttons() -> void:
    for action in ["ui_accept", "mouse_simulate", "ui_cancel", "back"]:
        if not InputMap.has_action(action):
            continue
        for event in InputMap.action_get_events(action):
            if event is InputEventJoypadButton:
                InputMap.action_erase_event(action, event)
        var button := InputEventJoypadButton.new()
        button.device = -1
        button.button_index = JOY_BUTTON_B if action in ["ui_accept", "mouse_simulate"] else JOY_BUTTON_A
        InputMap.action_add_event(action, button)
'''.replace('    ','\t')
p.write_text(s);old=(Path('C:/Users/dimas/lucid-build/recovered-original')/rel).read_text();dest=r/'patches'/Path(rel+'.patch');dest.parent.mkdir(parents=True,exist_ok=True);dest.write_text(''.join(difflib.unified_diff(old.splitlines(True),s.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)))
print('Added virtual mouse backend, software cursor and Nintendo menu actions')
