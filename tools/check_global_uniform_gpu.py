"""Desktop GPU check of the exact Switch integer-texture uniform fetch.

This validates the storage algorithm, not execution on Tegra/Horizon.
Requires moderngl==5.12.0 in the local build venv.
"""
from pathlib import Path
import array, json, re, struct
import moderngl

BUILD = Path('C:/Users/dimas/lucid-build')
source = (BUILD/'godot-switch-upstream/drivers/gles3/shaders/scene.glsl').read_text()
function = re.search(r'vec4 lucid_global_uniform\(uint index\) \{[^}]+\}', source)[0]
indices = [0, 255, 256, 1023, 1024, 4095, 65535, 262143]
patterns = [0, 1, 0xffffffff, 0x80000000, 0x3f800000, 0xbf800000, 0x7fc12345, 0x00800000]
data = array.array('I', [0]) * (256*1024*4)
for i, index in enumerate(indices):
    data[index*4:index*4+4] = array.array('I', [patterns[(i+j)%len(patterns)] for j in range(4)])
ctx = moderngl.create_standalone_context(require=330)
texture = ctx.texture((256,1024),4,data.tobytes(),dtype='u4')
texture.filter = (moderngl.NEAREST,moderngl.NEAREST)
texture.repeat_x = False; texture.repeat_y = False
program = ctx.program(vertex_shader='''#version 330
void main() {
    vec2 p = vec2((gl_VertexID << 1) & 2, gl_VertexID & 2);
    gl_Position = vec4(p * 2.0 - 1.0, 0.0, 1.0);
}''', fragment_shader='''#version 330
uniform usampler2D lucid_global_values;
uniform uint positions[8];
layout(location=0) out uvec4 result;
'''+function+'''
void main() { result = floatBitsToUint(lucid_global_uniform(positions[int(gl_FragCoord.x)])); }
''')
program['lucid_global_values'] = 0
program['positions'].write(struct.pack('<8I', *indices))
output = ctx.texture((8,1),4,dtype='u4')
framebuffer = ctx.framebuffer([output]); framebuffer.use()
ctx.viewport = (0,0,8,1)
vao = ctx.vertex_array(program, [])

def check():
    texture.use(0); vao.render(vertices=3)
    actual = struct.unpack('<32I', framebuffer.read(components=4,dtype='u4'))
    expected = tuple(component for index in indices for component in data[index*4:index*4+4])
    assert actual == expected, (actual,expected)

check()
# Partial dirty-region upload crossing a row boundary, including final row.
for index in [255,256,262143]:
    first = (index // 1024)*1024
    count = min(1024,256*1024-first)
    data[index*4:index*4+4] = array.array('I',[0xdeadbeef,17,0x3e800000,0])
    texture.write(data[first*4:(first+count)*4].tobytes(),viewport=(0,first//256,256,count//256))
check()
report = {'passed': True, 'backend':'desktop OpenGL', 'renderer':ctx.info['GL_RENDERER'],
    'storage':'RGBA32UI 256x1024', 'integer_and_float_bits_preserved':True,
    'last_index_verified':262143, 'partial_dirty_region_upload_verified':True,
    'console_verified':False}
(BUILD/'reports/global-uniform-desktop-gpu.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
