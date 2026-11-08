shader_type spatial;
render_mode diffuse_lambert, specular_disabled;
uniform sampler2D skin_texture : source_color, filter_nearest;
uniform vec4 base_color : source_color = vec4(1.0);
uniform vec4 skin_color : source_color = vec4(1.0);
uniform bool has_texture = false;
vec3 rgb2hsv(vec3 c) {
    vec4 K=vec4(0.0,-1.0/3.0,2.0/3.0,-1.0);
    vec4 p=mix(vec4(c.bg,K.wz),vec4(c.gb,K.xy),step(c.b,c.g));
    vec4 q=mix(vec4(p.xyw,c.r),vec4(c.r,p.yzx),step(p.x,c.r));
    float d=q.x-min(q.w,q.y);
    return vec3(abs(q.z+(q.w-q.y)/(6.0*d+0.00001)),d/(q.x+0.00001),q.x);
}
void fragment() {
    vec3 source=base_color.rgb;
    if (has_texture) { source *= texture(skin_texture,UV).rgb; }
    vec3 distance=rgb2hsv(source)-vec3(0.0,0.38,0.58);
    float mask=has_texture ? 1.0-clamp(dot(distance*distance,1.0/vec3(1.47,0.18,1.36)),0.0,1.0) : 1.0;
    ALBEDO=source*mix(vec3(1.0),skin_color.rgb,mask);
    ROUGHNESS=1.0;
}
