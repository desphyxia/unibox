shader_type spatial;
// The live fox's skin, eyes, ribbon and foxfire. `surface`: 0 lit (vertex colour), 1 glossy, 2 glowing.
render_mode diffuse_lambert_wrap, specular_schlick_ggx, cull_disabled;   // some decals face inward, as in Blender
#include "res://compare/fox_rig.gdshaderinc"

uniform int surface = 0;              // 0 lit, 1 glossy, 2 glowing (not "kind": the rig has a local of that name)

varying float emit;

void vertex() {
	int id = int(CUSTOM1.z + 0.5);
	vec3 pos; vec3 nrm; vec3 comb; vec3 br; float wh; float ll; float dl;
	pose_fetch(id, pos, nrm, comb, br, wh, ll, dl);
	vec4 leg = tx(id, 16);
	vec3 p = rig_move(pos, br, wh, CUSTOM0, leg);
	vec3 q = rig_move(pos + nrm * 0.05, br, wh, CUSTOM0, leg);
	NORMAL = normalize(q - p);
	VERTEX = rig_hidden(CUSTOM0) ? vec3(0.0) : p;
	emit = CUSTOM1.y;
}

void fragment() {
	vec3 c = trait_colour(COLOR.rgb);
	ALBEDO = c;
	ROUGHNESS = surface == 1 ? 0.18 : 0.62;
	SPECULAR = surface == 1 ? 0.8 : 0.25;
	RIM = 0.1;
	RIM_TINT = 0.6;
	if (surface == 2) {
		EMISSION = c * emit;
	}
}
