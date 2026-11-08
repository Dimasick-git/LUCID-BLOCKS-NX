import tempfile
import unittest
from pathlib import Path
from test_inspect_pck import PckChecks
from inspect_pck import inspect, extract
from patch_pck import patch

class PackAddonTests(unittest.TestCase):
    def test_added_resources_survive_directory_rebuild_and_checksum_readback(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = PckChecks().fixture(d)
            catalog = root/'ru.json'
            catalog.write_text('{"Play":"Играть"}', encoding='utf-8')
            target = root/'result.pck'
            report = patch(original, target, {}, {'NxPort/ru.json':catalog})
            self.assertEqual(report['added'], ['NxPort/ru.json'])
            self.assertEqual(report['entries'], 2)
            for entry in inspect(target)['entries']:
                extract(target, entry, root/'out')
            self.assertEqual((root/'out/NxPort/ru.json').read_bytes(), catalog.read_bytes())
            self.assertEqual((root/'out/main/test.gd').read_bytes(), b'extends Node\n')

    def test_reject_addon_collisions_and_path_escape_before_writing(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            original = PckChecks().fixture(d)
            for bad in ['main/test.gd', 'NxPort/../outside', 'NxPort/C:/escape', 'NxPort\\escape']:
                with self.assertRaises(ValueError):
                    patch(original, root/'out.pck', {}, {bad:original})
                self.assertFalse((root/'out.pck').exists())

if __name__ == '__main__':
    unittest.main()
