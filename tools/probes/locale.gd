extends SceneTree
var failed := false
func check(value: bool, message: String) -> void:
    if not value:
        printerr("LOCALE_CHECK_FAILED: ", message)
        failed = true
func _initialize() -> void:
    run.call_deferred()
func run() -> void:
    var locale = root.get_node_or_null("NxLocale")
    if locale == null:
        locale = load("res://nx_locale.gd").new()
        locale.name = "NxLocale"
        root.add_child(locale)
    check(locale.messages.size() >= 780, "catalog count")
    check(TranslationServer.get_locale().begins_with("en"), "English default")
    var panel := VBoxContainer.new()
    panel.position = Vector2(60, 40)
    panel.size = Vector2(1160, 640)
    panel.add_theme_constant_override("separation", 14)
    var font := FontFile.new()
    font.data = FileAccess.get_file_as_bytes("res://silkscreen.ttf")
    var theme := Theme.new()
    theme.default_font = font
    theme.default_font_size = 24
    panel.theme = theme
    root.add_child(panel)
    var heading := Label.new()
    heading.text = "Language / Язык"
    panel.add_child(heading)
    var choice := OptionButton.new()
    choice.add_item("English")
    choice.add_item("Русский")
    choice.select(1)
    panel.add_child(choice)
    var labels: Array[Label] = []
    for source in ["Display", "Audio", "Controls", "render distance", "camera sensitivity", "invert look y", "save changes"]:
        var label := Label.new()
        label.text = source
        label.name = "Test" + str(labels.size())
        panel.add_child(label)
        labels.append(label)
    locale.set_language("ru")
    await process_frame
    await process_frame
    check(font.has_char(0x0416), "font Cyrillic fallback")
    check(locale.text("Display") != "Display", "Display translation")
    check(labels[0].atr(labels[0].text) == locale.text("Display"), "automatic Control translation")
    check(choice.get_popup().get_theme_font("font").has_char(0x042F), "popup Cyrillic")
    for label in labels:
        check(locale.text(label.text) != label.text, "missing translation: " + label.text)
        check(label.get_minimum_size().x <= 1160, "translation width: " + label.text)
    locale.set_language("en")
    check(locale.text("Display") == "Display", "English restored")
    locale.set_language("ru")
    await process_frame
    await RenderingServer.frame_post_draw
    var image := root.get_texture().get_image()
    check(image != null and not image.is_empty(), "viewport readback")
    image.save_png("C:/Users/dimas/lucid-build/reports/locale-russian-preview.png")
    print("LOCALE_FONT_AND_SWITCH_CHECK_", "FAILED" if failed else "PASSED")
    quit(1 if failed else 0)
