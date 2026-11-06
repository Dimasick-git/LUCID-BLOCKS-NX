"""Local PFS0/NCA reader with content and filesystem hash checks."""
import hashlib,struct
from cryptography.hazmat.primitives.ciphers import Cipher,algorithms,modes
TITLE=0x0100963461C50000
def sha(data):return hashlib.sha256(data).digest()
def pfs(read, size):
    magic,count,strings,_=struct.unpack('<4sIII',read(0,16));assert magic==b'PFS0' and 0<count<1000
    start=16+24*count+strings; names=read(16+24*count,strings); entries={}
    for i in range(count):
        offset,length,name,_=struct.unpack('<QQII',read(16+i*24,24))
        name=names[name:].split(b'\0',1)[0].decode();assert '/' not in name and name not in entries
        assert start+offset+length<=size
        entries[name]=(start+offset,length)
    return entries

class Nca:
    def __init__(self,file,base,size,keys):
        self.file,self.base,self.size=file,base,size
        raw=self.raw(0,0xc00);key=bytes.fromhex(keys['header_key'])
        self.header=b''.join(Cipher(algorithms.AES(key),modes.XTS(i.to_bytes(16,'big'))).decryptor().update(raw[i*512:(i+1)*512]) for i in range(6))
        h=self.header;assert h[0x200:0x204]==b'NCA3' and struct.unpack_from('<Q',h,0x208)[0]==size
        assert struct.unpack_from('<Q',h,0x210)[0]==TITLE
        self.sections=[]
        for i in range(4):
            start,end=struct.unpack_from('<II',h,0x240+i*16)
            if not end:continue
            fh=h[0x400+i*512:0x600+i*512];assert sha(fh)==h[0x280+i*32:0x2a0+i*32]
            assert start<end and end*512<=size
            self.sections.append((start*512,end*512,fh))
        generation=max(h[0x206],h[0x220]);slot=max(generation-1,0)
        kaek=bytes.fromhex(keys[f'key_area_key_application_{slot:02x}'])
        area=Cipher(algorithms.AES(kaek),modes.ECB()).decryptor().update(h[0x300:0x340]);self.key=area[32:48]
    def raw(self,offset,size):
        assert offset>=0 and offset+size<=self.size
        self.file.seek(self.base+offset);data=self.file.read(size);assert len(data)==size;return data
    def read(self,section,offset,size):
        start,end,fh=section;assert offset>=0 and start+offset+size<=end
        if fh[4]==1:return self.raw(start+offset,size)
        assert fh[4]==3
        at=start+offset;aligned=at&~15;skip=at-aligned
        iv=fh[0x140:0x148][::-1]+(aligned//16).to_bytes(8,'big')
        dec=Cipher(algorithms.AES(self.key),modes.CTR(iv)).decryptor()
        return dec.update(self.raw(aligned,size+skip))[skip:]
    def romfs(self,section):
        fh=section[2];assert fh[3]==3 and fh[8:12]==b'IVFC'
        levels=[struct.unpack_from('<QQII',fh,0x18+24*i)[:3] for i in range(6)]
        offset,length,_=levels[0]
        assert sha(self.read(section,offset,length))==fh[0xc8:0xe8], 'IVFC master hash'
        for level in range(1,6):
            po,ps,_=levels[level-1];parent=self.read(section,po,ps)
            co,cs,power=levels[level];block=1<<power;assert block==0x4000
            number=0
            for at in range(0,cs,4*1024*1024):
                data=self.read(section,co+at,min(cs-at,4*1024*1024))
                for pos in range(0,len(data),block):
                    piece=data[pos:pos+block];piece+=b'\0'*(block-len(piece))
                    assert sha(piece)==parent[number*32:(number+1)*32], f'IVFC level {level+1} block {number}'
                    number+=1
        return levels[5][0],levels[5][1]
    def pfs(self,section):
        fh=section[2];assert fh[3]==2
        block=struct.unpack_from('<I',fh,0x28)[0]
        ho,hs,po,ps=struct.unpack_from('<4Q',fh,0x30)
        table=self.read(section,ho,hs);assert sha(table)==fh[8:40], 'PFS master hash'
        for i,at in enumerate(range(0,ps,block)):
            assert sha(self.read(section,po+at,min(block,ps-at)))==table[i*32:(i+1)*32], 'PFS block hash'
        return po,ps,pfs(lambda offset,size:self.read(section,po+offset,size),ps)

