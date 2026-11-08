shader_type spatial;
render_mode diffuse_lambert, specular_disabled;
uniform sampler2D block_texture : source_color, filter_nearest;
void fragment() {
    float face=clamp(floor(UV2.y+0.5),0.0,5.0);
    vec4 color=texture(block_texture,vec2((face+UV.x)/6.0,UV.y));
    if (color.a<0.1) { discard; }
    ALBEDO=color.rgb;
    ROUGHNESS=1.0;
}
