shader_type spatial;
// The live fox's skin, eyes, ribbon and foxfire, in one draw. Each vertex says which surface it is (CUSTOM1.w): 0 lit
// (vertex colour), 1 glossy, 2 glowing. The trait colours are worked out per vertex, not per pixel.
render_mode diffuse_lambert_wrap, specular_schlick_ggx, cull_disabled;   // some decals face inward, as in Blender
#include "res://compare/fox_rig.gdshaderinc"

varying float emit;
varying float surf;
varying vec3 col;

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
	surf = CUSTOM1.w;
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
