# NXZ4 resource storage

NSP01 keeps the existing Godot PCK directory and paths. Selected resources are wrapped in a seekable NXZ4 envelope. The Horizon-only adapter in `PackedSourcePCK::get_file()` detects the wrapper and uses Godot's `FileAccessCompressed` reader.

The wrapper is lossless. Each decoded resource must match the logical input's MD5; the builder verifies all 7,522 resources after writing the pack. Audio streams and movies are not re-encoded or wrapped.

| Field | Encoding |
| --- | --- |
| Magic | `NXZ4`, four bytes |
| Compression mode | little-endian uint32, `2` (Zstandard) |
| Block size | little-endian uint32, `262144` |
| Logical size | little-endian uint32 |
| Compressed block sizes | uint32 array, `logical_size / block_size + 1` entries |
| Blocks | independent Zstandard frames, level 3 |
| Footer | `NXZ4` |

The final block may contain zero bytes, matching Godot's compressed-file convention. The directory checksum covers stored bytes; the build report separately records checksums of decoded resources. Resources are wrapped only when the saving is at least 10% and 4 KiB.

The reader validates the mode, block size, table bounds and a 512 MiB resource limit before opening the decompressor. Only the current compressed block and its output buffer are needed for seeking. A custom Horizon runtime is required; an unmodified Godot executable cannot open this storage wrapper transparently.

`tools/compress_game_pack.py` requires `zstandard==0.23.0`. The complete logical pack remains a separate local build input. Neither pack belongs in Git.
