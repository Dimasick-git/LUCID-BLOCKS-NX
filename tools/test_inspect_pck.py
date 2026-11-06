import hashlib,struct,tempfile,unittest
from pathlib import Path
from inspect_pck import inspect,extract,MAGIC
class PckChecks(unittest.TestCase):
    def fixture(self,directory,name='main/test.gd',prefix=b''):
        payload=b'extends Node\n';header=bytearray(112);entry_name=name.encode();md5=hashlib.md5(payload).digest()
        struct.pack_into('<6I',header,0,MAGIC,3,4,6,0,2);struct.pack_into('<QQ',header,24,112,112+len(payload))
        record=struct.pack('<I',len(entry_name))+entry_name+struct.pack('<QQ',0,len(payload))+md5+struct.pack('<I',0)
        pack=bytes(header)+payload+struct.pack('<I',1)+record
        path=Path(directory)/'game.exe';path.write_bytes(prefix+pack+struct.pack('<QI',len(pack),MAGIC) if prefix else pack)
        return path
    def test_raw_and_embedded(self):
        for prefix in (b'',b'MZ' + bytes(62)):
            with tempfile.TemporaryDirectory() as d:
                source=self.fixture(d,prefix=prefix);report=inspect(source)
                self.assertEqual(report['engine'],'4.6.0');self.assertEqual(report['entry_count'],1)
                out=Path(d)/'output';extract(source,report['entries'][0],out)
                self.assertEqual((out/'main/test.gd').read_bytes(),b'extends Node\n')
                with self.assertRaises(FileExistsError):extract(source,report['entries'][0],out)
    def test_traversal_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            source=self.fixture(d,'../escape.gd')
            with self.assertRaises(ValueError):inspect(source)
    def test_corrupt_resource_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            source=self.fixture(d);report=inspect(source)
            with source.open('r+b') as f:f.seek(112);f.write(b'X')
            with self.assertRaises(ValueError):extract(source,report['entries'][0],Path(d)/'out')
    def test_encrypted_directory_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            source=self.fixture(d)
            with source.open('r+b') as f:f.seek(20);f.write(struct.pack('<I',3))
            with self.assertRaises(ValueError):inspect(source)
if __name__=='__main__':unittest.main()
