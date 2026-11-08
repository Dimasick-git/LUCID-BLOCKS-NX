extends Node
var running := false
var failed := false
func _ready() -> void:
    process_mode = Node.PROCESS_MODE_ALWAYS
func check(value: bool, message: String) -> void:
    if not value:
        printerr("SETTINGS_CHECK_FAILED: ", message)
        failed = true
func _process(_delta: float) -> void:
    if running:
        return
    var ref = get_node_or_null("/root/Ref")
    if ref == null or not is_instance_valid(ref.main):
        return
    if is_instance_valid(ref.save_file_manager) and ref.save_file_manager.device_file != null:
        ref.save_file_manager.device_file.set_data("tutorial", false)
    if not ref.main.loaded:
        return
    running = true
    run.call_deferred()
func run() -> void:
    var ref = get_node("/root/Ref")
    var locale = get_node("/root/NxLocale")
    var settings = ref.settings_menu
    await ref.main._on_main_menu_settings_requested()
    check(settings.nx_language_option != null, "language selector exists")
    check(settings.nx_language_option.item_count == 2, "two supported languages")
    settings.nx_language_option.select(1)
    settings.nx_language_option.item_selected.emit(1)
    await get_tree().process_frame
    check(locale.language == "ru", "Russian preview")
    await RenderingServer.frame_post_draw
    get_viewport().get_texture().get_image().save_png("C:/Users/dimas/lucid-build/reports/settings-russian-display.png")
    var tabs = settings.get_node("%TabContainer")
    for i in range(tabs.get_tab_count()):
        tabs.current_tab = i
        await get_tree().process_frame
        await RenderingServer.frame_post_draw
        get_viewport().get_texture().get_image().save_png("C:/Users/dimas/lucid-build/reports/settings-russian-tab-%d.png" % i)
    settings.finalize_edit(true)
    ref.save_file_manager.write_settings_file()
    var saved = ResourceLoader.load(ref.save_file_manager.root_device_path().path_join("settings.tres"), "", ResourceLoader.CACHE_MODE_IGNORE)
    if saved != null:
        saved.is_dimensional = false
    check(saved != null and saved.get_data("language", "en") == "ru", "language written to isolated settings file")
    locale.set_language("en")
    get_node("/root/SettingsManager").initialize_settings_file()
    check(locale.language == "ru", "saved language restored")
    settings.initialize(1)
    settings.nx_language_option.select(0)
    settings.nx_language_option.item_selected.emit(0)
    check(locale.language == "en", "English preview")
    await ref.main._on_settings_menu_exited()
    check(locale.language == "ru", "cancel restores saved language")
    print("REAL_SETTINGS_LANGUAGE_SAVE_CANCEL_", "FAILED" if failed else "PASSED")
    get_tree().quit(1 if failed else 0)
