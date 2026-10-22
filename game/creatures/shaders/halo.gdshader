shader_type spatial;
// The soft glow round each foxfire: faint, added on top, unlit.
render_mode unshaded, blend_add, depth_draw_never, cull_disabled;
#include "res://creatures/shaders/creature.gdshaderinc"

varying vec3 col;

void vertex() {
	col = trait_colour(COLOR.rgb) * 0.22;
}

void fragment() {
	ALBEDO = col;
}
