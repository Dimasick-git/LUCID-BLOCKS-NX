"""Patch selected project.binary values while preserving opaque Variant payloads."""
import struct

def unpack(data):
    if data[:4]!=b'ECFG':raise ValueError('project.binary header')
    count=struct.unpack_from('<I',data,4)[0];at=8;settings={}
    if count>100000:raise ValueError('Setting count budget')
    for _ in range(count):
        length=struct.unpack_from('<I',data,at)[0];at+=4
        if length>4096 or at+length+4>len(data):raise ValueError('Setting name bounds')
        name=data[at:at+length].decode('utf-8');at+=length;length=struct.unpack_from('<I',data,at)[0];at+=4
        if at+length>len(data) or name in settings:raise ValueError('Setting value bounds/duplicate')
        settings[name]=data[at:at+length];at+=length
    if at!=len(data):raise ValueError('Trailing project settings')
    return settings

def variant(value):
    if isinstance(value,bool):return struct.pack('<II',1,int(value))
    if isinstance(value,int):return struct.pack('<Ii',2,value)
    if isinstance(value,str):
        text=value.encode('utf-8');return struct.pack('<II',4,len(text))+text+bytes((-len(text))%4)
    raise TypeError(type(value))

def patch(data,overrides,remove_prefixes=()):
    settings=unpack(data)
    settings={name:value for name,value in settings.items() if not any(name.startswith(prefix) for prefix in remove_prefixes)}
    for name,value in overrides.items():settings[name]=variant(value)
    out=bytearray(b'ECFG'+struct.pack('<I',len(settings)))
    # Godot requires custom features to load before feature-overridden settings.
    # Autoload insertion order determines singleton initialization order.
    # Sorting all keys makes ItemMap run before Ref and crashes native calls.
    names=(["_custom_features"] if "_custom_features" in settings else []) + [name for name in settings if name != "_custom_features"]
    for name in names:
        encoded=name.encode('utf-8');out+=struct.pack('<I',len(encoded))+encoded+struct.pack('<I',len(settings[name]))+settings[name]
    unpack(out)
    return bytes(out)
