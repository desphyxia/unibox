shader_type spatial;
// The soft glow round each foxfire: faint, added on top, unlit.
render_mode unshaded, blend_add, depth_draw_never, cull_disabled;
#include "res://compare/fox_rig.gdshaderinc"

void vertex() {
	VERTEX = rig_move(VERTEX, CUSTOM1, CUSTOM2);
}

void fragment() {
	ALBEDO = trait_colour(COLOR.rgb) * 0.22;
}
