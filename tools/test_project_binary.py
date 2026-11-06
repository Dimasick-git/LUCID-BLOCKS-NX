"""Protect binary project settings and dependency-sensitive autoload order."""
import struct
import unittest
from project_binary import patch, unpack, variant

def fixture(entries):
    data = bytearray(b'ECFG' + struct.pack('<I', len(entries)))
    for name, value in entries:
        text = name.encode()
        data += struct.pack('<I', len(text)) + text
        data += struct.pack('<I', len(value)) + value
    return bytes(data)

class ProjectBinaryTests(unittest.TestCase):
    def test_features_first_without_reordering_autoload_dependencies(self):
        opaque = bytes.fromhex('1b00000004000000deadbeef')
        original = fixture([('autoload/Ref', variant('*res://ref.gd')),
            ('autoload/ItemMap', variant('*res://items.gd')),
            ('input/move', opaque), ('_custom_features', variant('steam'))])
        settings = unpack(patch(original, {'_custom_features':'switch', 'new/int':2}))
        self.assertEqual(list(settings), ['_custom_features', 'autoload/Ref',
            'autoload/ItemMap', 'input/move', 'new/int'])
        self.assertEqual(settings['input/move'], opaque)
        self.assertEqual(settings['new/int'], variant(2))

    def test_variant_alignment_and_types(self):
        self.assertEqual(variant(True), struct.pack('<II', 1, 1))
        self.assertEqual(variant(-10), struct.pack('<Ii', 2, -10))
        encoded = variant('NX')
        self.assertEqual(encoded, struct.pack('<II',4,2)+b'NX\x00\x00')

    def test_invalid_and_duplicate_settings_rejected(self):
        for invalid in [b'bad!', fixture([('a', b'')])+b'trailing',
                        fixture([('a', b''), ('a', b'')])]:
            with self.assertRaises(ValueError):
                unpack(invalid)

if __name__ == '__main__':
    unittest.main()
