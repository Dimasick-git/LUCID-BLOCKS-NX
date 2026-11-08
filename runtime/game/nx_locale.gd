extends Node

signal language_changed

const CATALOG_PATH := "res://NxPort/ru.json"
var language := "en"
var messages: Dictionary = {}
var _font_seen: Dictionary = {}

func _ready() -> void:
    process_mode = Node.PROCESS_MODE_ALWAYS
    var file := FileAccess.open(CATALOG_PATH, FileAccess.READ)
    if file != null:
        var parsed = JSON.parse_string(file.get_as_text())
        if parsed is Dictionary:
            messages = parsed
    var russian := Translation.new()
    russian.locale = "ru"
    for source in messages:
        russian.add_message(source, messages[source])
    TranslationServer.add_translation(russian)
    TranslationServer.set_locale(language)
    get_tree().node_added.connect(_on_node_added)
    print("[nx-locale] Russian messages loaded: ", messages.size())

func set_language(value: String) -> void:
    language = "ru" if value == "ru" else "en"
    TranslationServer.set_locale(language)
    refresh_item_names()
    language_changed.emit()

func text(source: String) -> String:
    if language != "ru":
        return source
    return str(messages.get(source, source))

func refresh_item_names() -> void:
    var items = get_node_or_null("/root/ItemMap")
    if items == null:
        return
    var resources = items.get("id_to_resource")
    if not resources is Dictionary:
        return
    for id in resources:
        var item: Resource = resources[id]
        if not item.has_meta("nx_original_display_name"):
            item.set_meta("nx_original_display_name", item.get("display_name"))
        var original := str(item.get_meta("nx_original_display_name"))
        item.set("display_name", text(original))

func _on_node_added(node: Node) -> void:
    if node is Control:
        _ensure_cyrillic.call_deferred(node)

func _ensure_cyrillic(node: Node) -> void:
    if not is_instance_valid(node) or not node is Control:
        return
    var control := node as Control
    var font := control.get_theme_font("normal_font" if node is RichTextLabel else "font")
    if font == null or font == ThemeDB.fallback_font or font.has_char(0x0416):
        return
    var id := font.get_instance_id()
    if _font_seen.has(id):
        return
    var fallbacks: Array[Font] = font.fallbacks
    if not fallbacks.has(ThemeDB.fallback_font):
        fallbacks.append(ThemeDB.fallback_font)
        font.fallbacks = fallbacks
    _font_seen[id] = true
