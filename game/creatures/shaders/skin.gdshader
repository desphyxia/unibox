shader_type spatial;
// A creature's skin, eyes, ribbon and glowing parts (and the skin under its fur). Each vertex says which surface it is
// (CUSTOM1.z): 0 lit (vertex colour), 1 glossy, 2 glowing. The trait colours are worked out per vertex.
render_mode diffuse_lambert_wrap, specular_schlick_ggx, cull_disabled;   // some decals face inward, as in Blender
#include "res://creatures/shaders/creature.gdshaderinc"

varying float emit;
varying float surf;
varying vec3 col;

void vertex() {
	if (hidden_piece(CUSTOM0.w)) {
		VERTEX = vec3(0.0);
	}
	emit = CUSTOM1.y;
	surf = CUSTOM1.z;
	col = trait_colour(COLOR.rgb);
}

void fragment() {
	bool glossy = surf > 0.5 && surf < 1.5;
	ALBEDO = col;
	ROUGHNESS = glossy ? 0.18 : 0.62;
	SPECULAR = glossy ? 0.8 : 0.25;
	RIM = 0.1;
	RIM_TINT = 0.6;
	if (surf > 1.5) {
		EMISSION = col * emit;
	}
}
