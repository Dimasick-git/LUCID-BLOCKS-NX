"""Validate retrievable program binaries and restored output on a desktop GPU."""
import ctypes as C
import json
from pathlib import Path
import moderngl

ctx = moderngl.create_standalone_context(require=330)
dll = C.WinDLL('opengl32')
dll.wglGetProcAddress.argtypes = [C.c_char_p]
dll.wglGetProcAddress.restype = C.c_void_p
def gl(name, result, *args):
    address = dll.wglGetProcAddress(name.encode())
    assert address and address > 3, name
    return C.WINFUNCTYPE(result, *args)(address)

uint, integer, ptr = C.c_uint, C.c_int, C.c_void_p
create_shader = gl('glCreateShader', uint, uint)
shader_source = gl('glShaderSource', None, uint, integer, C.POINTER(C.c_char_p), C.POINTER(integer))
compile_shader = gl('glCompileShader', None, uint)
create_program = gl('glCreateProgram', uint)
attach = gl('glAttachShader', None, uint, uint)
parameter = gl('glProgramParameteri', None, uint, uint, integer)
link = gl('glLinkProgram', None, uint)
get = gl('glGetProgramiv', None, uint, uint, C.POINTER(integer))
binary = gl('glGetProgramBinary', None, uint, integer, C.POINTER(integer), C.POINTER(uint), ptr)
restore = gl('glProgramBinary', None, uint, uint, ptr, integer)
use = gl('glUseProgram', None, uint)
gen_vao = gl('glGenVertexArrays', None, integer, C.POINTER(uint))
bind_vao = gl('glBindVertexArray', None, uint)
dll.glDrawArrays.argtypes = [uint, integer, integer]
program = create_program()
for kind, source in [(0x8B31, b'#version 330\nvoid main(){vec2 p=vec2((gl_VertexID<<1)&2,gl_VertexID&2);gl_Position=vec4(p*2.-1.,0.,1.);}'),
                     (0x8B30, b'#version 330\nout vec4 color;void main(){color=vec4(.25,.5,.75,1.);}')]:
    shader = create_shader(kind)
    text = C.c_char_p(source)
    shader_source(shader, 1, C.byref(text), None)
    compile_shader(shader)
    attach(program, shader)
parameter(program, 0x8257, 1)  # GL_PROGRAM_BINARY_RETRIEVABLE_HINT before link.
link(program)
status = integer()
get(program, 0x8B82, C.byref(status)); assert status.value == 1
size = integer()
get(program, 0x8741, C.byref(size)); assert size.value > 0
data = C.create_string_buffer(size.value)
written, format_id = integer(), uint()
binary(program, size.value, C.byref(written), C.byref(format_id), data)
assert written.value > 0
loaded = create_program()
restore(loaded, format_id.value, data, written.value)
get(loaded, 0x8B82, C.byref(status)); assert status.value == 1
fbo = ctx.simple_framebuffer((1, 1)); fbo.use()
ctx.viewport = (0, 0, 1, 1)
vao = uint(); gen_vao(1, C.byref(vao)); bind_vao(vao.value)
outputs = []
for selected in [program, loaded]:
    use(selected); dll.glDrawArrays(4, 0, 3)
    outputs.append(fbo.read(components=4))
assert outputs[0] == outputs[1]
assert all(abs(actual-expected) <= 1 for actual, expected in zip(outputs[0], [64,128,191,255]))
report = {'passed': True, 'renderer': ctx.info['GL_RENDERER'], 'binary_bytes': written.value,
          'binary_restore_linked': True, 'restored_pixel_matches': True, 'console_verified': False}
Path('C:/Users/dimas/lucid-build/reports/program-binary-desktop-gpu.json').write_text(json.dumps(report, indent=2)+'\n')
print(json.dumps(report, indent=2))
