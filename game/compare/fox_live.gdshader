shader_type spatial;
// The live fox's skin, eyes, ribbon and foxfire. `kind`: 0 lit (vertex colour), 1 glossy, 2 glowing, 3 soft halo.
render_mode diffuse_lambert_wrap, specular_schlick_ggx, cull_disabled;   // some decals face inward, as in Blender
#include "res://compare/fox_rig.gdshaderinc"

uniform int kind = 0;

varying float emit;

void vertex() {
	vec3 p = rig_move(VERTEX, CUSTOM1, CUSTOM2);
	vec3 q = rig_move(VERTEX + NORMAL * 0.05, CUSTOM1, CUSTOM2);
	NORMAL = normalize(q - p);
	VERTEX = rig_hidden(CUSTOM1) ? vec3(0.0) : p;
	emit = CUSTOM3.z;
}

void fragment() {
	vec3 c = trait_colour(COLOR.rgb);
	ALBEDO = c;
	ROUGHNESS = kind == 1 ? 0.18 : 0.62;
	SPECULAR = kind == 1 ? 0.8 : 0.25;
	RIM = 0.1;
	RIM_TINT = 0.6;
	if (kind == 2) {
		EMISSION = c * emit;
	}
}
