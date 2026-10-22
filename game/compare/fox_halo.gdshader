shader_type spatial;
// The soft glow round each foxfire: faint, added on top, unlit.
render_mode unshaded, blend_add, depth_draw_never, cull_disabled;
#include "res://compare/fox_rig.gdshaderinc"

varying vec3 col;

void vertex() {
	int id = int(CUSTOM1.z + 0.5);
	vec3 pos; vec3 nrm; vec3 comb; vec3 br; float wh; float ll; float dl;
	pose_fetch(id, pos, nrm, comb, br, wh, ll, dl);
	VERTEX = rig_move(pos, br, wh, CUSTOM0, vec4(0.0));
	col = trait_colour(COLOR.rgb) * 0.22;
}

void fragment() {
	ALBEDO = col;
}
