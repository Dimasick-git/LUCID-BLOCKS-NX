extends Node
var done := false
func _ready() -> void:
    process_mode = Node.PROCESS_MODE_ALWAYS
func _process(_delta: float) -> void:
    if done: return
    done = true
    var blocks := PackedInt32Array()
    blocks.resize(16384)
    for i in blocks.size(): blocks[i] = 163165934 if i % 7 == 0 else 0
    var chunks := {}
    for i in 32: chunks[Vector3i(i*16,0,-i*16)] = blocks
    var source := {"test_world":{"test_chunk_block":chunks}, "player":{"position":Vector3(1.5,2,-3),"items":PackedInt32Array([2248,1,100])}}
    var started := Time.get_ticks_usec()
    var packed := var_to_bytes(source)
    var zipped := packed.compress(FileAccess.COMPRESSION_GZIP)
    var decoded = bytes_to_var(zipped.decompress_dynamic(64*1024*1024,FileAccess.COMPRESSION_GZIP))
    var binary_usec := Time.get_ticks_usec()-started
    assert(decoded is Dictionary and decoded == source,"snapshot native types survive round trip")
    assert(decoded.test_world.test_chunk_block[Vector3i(16,0,-16)] is PackedInt32Array,"chunk arrays remain packed")
    started = Time.get_ticks_usec()
    var legacy := JSON.stringify(JSON.from_native(source)).to_utf8_buffer()
    var json_usec := Time.get_ticks_usec()-started
    print("NETWORK_PAYLOAD_PASSED binary_bytes=",packed.size()," json_bytes=",legacy.size()," binary_encode_compress_decode_us=",binary_usec," json_encode_us=",json_usec)
    get_tree().quit()
