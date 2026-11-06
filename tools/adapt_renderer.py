from pathlib import Path
import difflib,json
r=Path('C:/Users/dimas/lucid-blocks-nx');b=Path('C:/Users/dimas/lucid-build');game=b/'game';changed=[]

def save(rel,s):
 p=game/rel;old=p.read_text(encoding='utf-8');assert s!=old,rel;p.write_text(s,encoding='utf-8');original=(b/'recovered-original'/rel).read_text(encoding='utf-8')
 diff=r/'patches'/Path(rel+'.patch');diff.parent.mkdir(parents=True,exist_ok=True);diff.write_text(''.join(difflib.unified_diff(original.splitlines(True),s.splitlines(True),fromfile='a/'+rel,tofile='b/'+rel)),encoding='utf-8');changed.append(rel)

post=['main/fractal/shader/mandelbulb_sky.gdshader','main/ui/menu/transition/scary_transition.gdshader','main/world/rendering/sky/sun_box.gdshader','main/world/rendering/sky/sky.gdshader']
for rel in post:
 s=(game/rel).read_text()
 if 'nx_depth_texture' in s:continue
 line='uniform sampler2D depth_post_transparent_texture: source_color, filter_nearest;'
 assert s.count(line)==1
 s=s.replace(line,line+'\n// NX: use the renderer depth copy when no compute compositor exists.\n#if CURRENT_RENDERER == RENDERER_COMPATIBILITY\nuniform sampler2D nx_depth_texture: hint_depth_texture, filter_nearest;\n#endif')
 line='float depth = texture(depth_post_transparent_texture, SCREEN_UV).x;'
 assert s.count(line)==1
 s=s.replace(line,'#if CURRENT_RENDERER == RENDERER_COMPATIBILITY\n\tfloat depth = texture(nx_depth_texture, SCREEN_UV).x;\n#else\n\t'+line+'\n#endif')
 line='vec3 ndc = vec3(SCREEN_UV * 2.0 - 1.0, depth);'
 assert s.count(line)==1
 s=s.replace(line,line+'\n#if CURRENT_RENDERER == RENDERER_COMPATIBILITY\n\tndc.z = depth * 2.0 - 1.0;\n#endif')
 save(rel,s)

for rel in ['main/entity/demiurge/hama.gdshader','main/entity/demiurge/hama_solid.gdshader','main/entity/huitzilopochtli/lightning/light.gdshader','main/world/rendering/block_mesh/water_mesh_renderer.gdshader']:
 s=(game/rel).read_text()
 if '// NX: OpenGL depth' in s:continue
 variable='ndc' if 'water_mesh' in rel else 'scene_clip_pos'
 lines=s.splitlines(True);found=0
 for i,line in enumerate(lines):
  if 'vec3 '+variable+' = vec3(SCREEN_UV * 2.0 - 1.0,' in line:
   lines[i]=line+'\t// NX: OpenGL depth is reconstructed in the -1..1 clip range.\n#if CURRENT_RENDERER == RENDERER_COMPATIBILITY\n\t'+variable+'.z = '+variable+'.z * 2.0 - 1.0;\n#endif\n';found+=1
 assert found==1,(rel,found);save(rel,''.join(lines))

for rel in ['main/ui/menu/transition/transition.gd','main/world/rendering/sky/sky_plane.gd']:
 s=(game/rel).read_text()
 if '# NX: RD textures' in s:continue
 start=s.index('\tpost_transparent_texture = Texture2DRD.new()');end=s.index('\n\n',start)
 block=s[start:end];s=s[:start]+'\t# NX: RD textures are only created on RenderingDevice renderers.\n\tif RenderingServer.get_rendering_device() != null:\n'+''.join('\t'+line+'\n' for line in block.splitlines())+s[end:]
 connect='\tRef.player_camera.compositor.compositor_effects[0].depth_texture_recreated.connect(_on_depth_texture_recreated)'
 # Transition's connection is already inside the guarded block. Sky's is separate.
 if rel.endswith('sky_plane.gd'):
  assert s.count('\n'+connect+'\n')==1;s=s.replace('\n'+connect+'\n','\n\tif RenderingServer.get_rendering_device() != null:\n\t'+connect+'\n')
 save(rel,s)
rel='main/autoload/render_checker.gd';s=(game/rel).read_text();s=s.replace('must_warn = rendering_method == "gl_compatibility"','must_warn = rendering_method == "gl_compatibility" and not OS.has_feature("switch")');save(rel,s)
(b/'reports/gles-adaptation.json').write_text(json.dumps({'changed':changed,'shader_gpu_validation':False,'hardware_validation':False},indent=2)+'\n');print('Adapted',len(changed),'renderer resources/scripts')
