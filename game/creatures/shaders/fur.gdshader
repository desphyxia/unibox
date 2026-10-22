shader_type spatial;
// Shell fur: the furry skin and, over it, thin copies of it (layer height CUSTOM2.w, 0 at the skin to 1 at the tips),
// which creature_model.gd stacks in one mesh already lifted along the fur, so the skeleton and blend shapes carry the
// layers too. Holes cut by a small stored noise texture make the layers read as strands and tufts; on renderers that
// can, the strand edges are smoothed (alpha to coverage).
render_mode diffuse_lambert_wrap, specular_schlick_ggx, cull_disabled, alpha_to_coverage_and_one;
#include "res://creatures/shaders/creature.gdshaderinc"

uniform float strand_freq = 70.0;
uniform float tuft_freq = 9.0;
uniform float root_shade = 0.74;      // how much darker the fur is deep down (a short coat barely is)
uniform sampler3D noise : filter_linear, repeat_enable;   // creature_model.gd: 32 cells each way, red strands, green tufts
const float NOISE_CELLS = 32.0;

varying vec3 root;
varying float tip;
varying float glow;
varying float fur_len;
varying vec3 base;
varying float h;

void vertex() {
	root = CUSTOM2.xyz;
	h = CUSTOM2.w;
	tip = COLOR.a;
	glow = CUSTOM1.x;
	base = trait_colour(COLOR.rgb, CUSTOM3.x);
	fur_len = length(vec2(CUSTOM0.z, CUSTOM1.w));   // the fur's length outward and along the surface
}

void fragment() {
	// looked up, not computed: a little more contrast stands in for the smooth steps a computed noise has
	float strands = clamp((texture(noise, root * (strand_freq / NOISE_CELLS)).r - 0.5) * 1.25 + 0.5, 0.0, 1.0);
	float tufts = clamp((texture(noise, (root * tuft_freq + vec3(7.1)) / NOISE_CELLS).g - 0.5) * 1.25 + 0.5, 0.0, 1.0);
	float keep = strands * 0.7 + tufts * 0.45;
	// no fur where the length runs out (face, eyes, nose); thinner where it is short
	float need = mix(0.12, 1.05, pow(h, 0.85)) + (1.0 - smoothstep(0.004, 0.03, fur_len)) * 2.0;
	ALPHA = h < 0.001 ? 1.0 : smoothstep(need - 0.06, need + 0.06, keep);   // the skin itself is whole
	ALPHA_SCISSOR_THRESHOLD = 0.5;
	ALPHA_ANTIALIASING_EDGE = 0.45;
	vec3 tipc = base + (vec3(1.0) - base) * tip * 0.5;
	ALBEDO = h < 0.001 ? base : mix(base, tipc, h) * mix(root_shade, 1.0, h);
	ROUGHNESS = 0.6;
	SPECULAR = 0.2;
	RIM = 0.15;
	RIM_TINT = 0.7;
	BACKLIGHT = vec3(0.12) * h;
	if (glow > 0.5 && h > 0.001) {
		EMISSION = tipc * 0.45;
	}
}
