"""Lossless, seekable NXZ4 storage for selected PCK resources.

Requires zstandard==0.23.0. The Horizon FileAccessPack adapter unwraps these
blocks through Godot's FileAccessCompressed. Audio/video are left untouched.
"""
from pathlib import Path
import argparse, collections, hashlib, json, struct
import zstandard
from inspect_pck import inspect, MAGIC

BLOCK = 262144
ELIGIBLE = {'.ctex', '.scn', '.mesh', '.res', '.sample', '.cache'}

def encode(data):
    compressor = zstandard.ZstdCompressor(level=3)
    blocks = [compressor.compress(data[at:at+BLOCK]) for at in range(0, len(data)+1, BLOCK)]
    return b'NXZ4'+struct.pack('<III', 2, BLOCK, len(data))+struct.pack('<'+'I'*len(blocks), *map(len, blocks))+b''.join(blocks)+b'NXZ4'

def decode(data):
    assert data[:4] == data[-4:] == b'NXZ4'
    mode, block, total = struct.unpack_from('<III', data, 4)
    assert mode == 2 and block == BLOCK
    count = total//block+1
    sizes = struct.unpack_from('<'+'I'*count, data, 16)
    offset = 16+4*count
    chunks = []
    for index, size in enumerate(sizes):
        expected = min(block, total-index*block)
        chunk = zstandard.ZstdDecompressor().decompress(data[offset:offset+size], max_output_size=block)
        assert len(chunk) == expected
        chunks.append(chunk)
        offset += size
    assert offset == len(data)-4
    return b''.join(chunks)

def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('source', type=Path)
    p.add_argument('output', type=Path)
    a = p.parse_args()
    assert not a.output.exists()
    inventory = inspect(a.source)
    header = bytearray(112)
    struct.pack_into('<6I', header, 0, MAGIC, 3, 4, 6, 0, 2)
    struct.pack_into('<Q', header, 24, 112)
    records, compressed = [], []
    before = collections.Counter()
    after = collections.Counter()
    with a.source.open('rb') as source, a.output.open('xb') as out:
        out.write(header)
        for e in inventory['entries']:
            assert e['flags'] == 0
            source.seek(e['offset'])
            data = source.read(e['size'])
            assert hashlib.md5(data).hexdigest() == e['md5'], e['path']
            suffix = Path(e['path']).suffix
            stored = data
            if suffix in ELIGIBLE and len(data) >= 4096:
                candidate = encode(data)
                if len(candidate) < len(data)*0.9 and len(data)-len(candidate) >= 4096:
                    assert decode(candidate) == data, e['path']
                    stored = candidate
                    compressed.append({'path': e['path'], 'logical_bytes': len(data),
                                       'stored_bytes': len(stored), 'logical_md5': e['md5']})
            out.write(bytes((-out.tell()) % 16))
            offset = out.tell()-112
            out.write(stored)
            records.append((e['path'], offset, len(stored), hashlib.md5(stored).digest()))
            before[suffix] += len(data)
            after[suffix] += len(stored)
        directory = out.tell()
        out.write(struct.pack('<I', len(records)))
        for name, offset, size, checksum in records:
            text = name.encode(); text += bytes((-len(text)) % 4)
            out.write(struct.pack('<I', len(text))+text+struct.pack('<QQ', offset, size)+checksum+struct.pack('<I', 0))
        out.seek(32); out.write(struct.pack('<Q', directory))
    result = inspect(a.output)
    compressed_paths = {e['path']: e for e in compressed}
    with a.output.open('rb') as out:
        for expected, actual in zip(inventory['entries'], result['entries']):
            assert expected['path'] == actual['path']
            out.seek(actual['offset']); data = out.read(actual['size'])
            assert hashlib.md5(data).hexdigest() == actual['md5']
            if actual['path'] in compressed_paths:
                data = decode(data)
            assert hashlib.md5(data).hexdigest() == expected['md5'], actual['path']
    with a.output.open('rb') as out:
        digest = hashlib.file_digest(out, 'sha256').hexdigest()
    report = {'file': str(a.output), 'source_bytes': a.source.stat().st_size,
              'bytes': a.output.stat().st_size, 'sha256': digest,
              'resources': len(records), 'compressed_resources': len(compressed),
              'all_logical_resource_checksums_verified': True, 'block_bytes': BLOCK,
              'compression': 'NXZ4 / Zstandard level 3; independent blocks',
              'audio_video_reencoded': False, 'before_by_extension': dict(before),
              'after_by_extension': dict(after), 'compressed': compressed}
    a.output.with_suffix('.verified.json').write_text(json.dumps(report, indent=2)+'\n')
    print(json.dumps({k: v for k, v in report.items() if k not in ['compressed', 'before_by_extension', 'after_by_extension']}, indent=2))

if __name__ == '__main__':
    main()
