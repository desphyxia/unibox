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
uniform float sheen = 0.2;            // the fur's highlight: how strong, and how sharp (a glossy coat, such as the collie's)
uniform float sheen_rough = 0.6;
uniform float streak = 0.0;           // long hair (the collie): the strands drawn this many noise cells long along the combed
                                      // direction (CUSTOM3.y, packed), 0 round dots as the fox and unicorn have
uniform float lock_streak = 0.0;      // the tufts drawn this many of their cells long: locks of hair
uniform float lock_shade = 0.0;       // how much darker the hair is between the locks
uniform float strand_light = 0.0;     // how much lighter or darker one strand is than the next
uniform float silk = 0.0;             // a glossy highlight running across the strands, as on long silky hair
uniform float silk_sharp = 40.0;
uniform vec3 silk_tint = vec3(0.75, 0.82, 0.95);
const vec3 KEY = vec3(-0.4319, 0.5183, 0.7774);   // the key light (creature_view.gd), which rides with the camera
uniform sampler3D noise : filter_linear, repeat_enable;   // creature_model.gd: 32 cells each way, red strands, green tufts
const float NOISE_CELLS = 32.0;

varying vec3 root;
varying float tip;
varying float glow;
varying float fur_len;
varying vec3 base;
varying float h;
varying vec3 comb;
varying vec3 comb_view;

vec3 unpacked_direction(float e) {
	// build_collie.gd's direction in one number: two 256-step coordinates on an octahedron; 0 when there is none
	if (e < 0.0) {
		return vec3(0.0);
	}
	float u = floor(e / 256.0);
	vec2 f = vec2(u, e - u * 256.0) / 255.0 * 2.0 - 1.0;
	vec3 n = vec3(f, 1.0 - abs(f.x) - abs(f.y));
	float t = clamp(-n.z, 0.0, 1.0);
	n.x += n.x >= 0.0 ? -t : t;
	n.y += n.y >= 0.0 ? -t : t;
	return normalize(n);
}

void vertex() {
	root = CUSTOM2.xyz;
	h = CUSTOM2.w;
	tip = COLOR.a;
	glow = CUSTOM1.x;
	base = trait_colour(COLOR.rgb, CUSTOM3.x);
	fur_len = length(vec2(CUSTOM0.z, CUSTOM1.w));   // the fur's length outward and along the surface
	comb = streak > 0.0 ? unpacked_direction(CUSTOM3.y) : vec3(0.0);
	// the combed direction as the creature stands at rest; the bones' turns aren't followed, which the highlight forgives
	comb_view = (MODELVIEW_MATRIX * vec4(comb, 0.0)).xyz;
}

void fragment() {
	// looked up, not computed: a little more contrast stands in for the smooth steps a computed noise has
	vec3 q = root * (strand_freq / NOISE_CELLS);
	vec3 qt = (root * tuft_freq + vec3(7.1)) / NOISE_CELLS;
	float strands;
	float tufts;
	bool long_hair = streak > 0.0 && dot(comb, comb) > 0.25;
	if (long_hair) {
		// long hair: the noise averaged along the hair's direction, so each strand is a long streak, not a dot, and the
		// tufts long locks
		vec3 d = normalize(comb) / NOISE_CELLS;
		vec3 s1 = d * (streak / 3.0);
		vec3 s2 = d * (lock_streak / 3.0);
		strands = clamp(((texture(noise, q - s1).r + texture(noise, q + s1).r) * 0.5 - 0.5) * 1.8 + 0.5, 0.0, 1.0);
		float sum = texture(noise, qt - s2).g + texture(noise, qt).g + texture(noise, qt + s2).g;
		tufts = clamp((sum / 3.0 - 0.5) * 2.1 + 0.5, 0.0, 1.0);
	} else {
		strands = clamp((texture(noise, q).r - 0.5) * 1.25 + 0.5, 0.0, 1.0);
		tufts = clamp((texture(noise, qt).g - 0.5) * 1.25 + 0.5, 0.0, 1.0);
	}
	float keep = strands * 0.7 + tufts * 0.45;
	// no fur where the length runs out (face, eyes, nose); thinner where it is short
	float need = mix(0.12, 1.05, pow(h, 0.85)) + (1.0 - smoothstep(0.004, 0.03, fur_len)) * 2.0;
	ALPHA = h < 0.001 ? 1.0 : smoothstep(need - 0.06, need + 0.06, keep);   // the skin itself is whole
	ALPHA_SCISSOR_THRESHOLD = 0.5;
	ALPHA_ANTIALIASING_EDGE = 0.45;
	vec3 tipc = base + (vec3(1.0) - base) * tip * 0.5;
	ALBEDO = h < 0.001 ? base : mix(base, tipc, h) * mix(root_shade, 1.0, h);
	if (long_hair) {
		// one strand lighter than the next, and darker between the locks (paler gaps in a white coat)
		ALBEDO *= (1.0 + strand_light * (strands * 2.0 - 1.0))
			* mix(1.0 - lock_shade * mix(1.0, 0.35, dot(base, vec3(0.3, 0.55, 0.15))), 1.0, smoothstep(0.2, 0.7, tufts));
	}
	if (silk > 0.0 && long_hair) {
		// the highlight of a strand (as Kajiya and Kay): bright where the strand runs across the half-way direction
		vec3 t = normalize(comb_view);
		vec3 hv = normalize(KEY + VIEW);
		float th = dot(t, hv);
		float hl = pow(sqrt(max(1.0 - th * th, 0.0)), silk_sharp) * max(dot(NORMAL, KEY) * 0.6 + 0.4, 0.0);
		EMISSION += silk_tint * silk * hl * (0.35 + 0.65 * h) * mix(0.5, 1.0, strands) * smoothstep(0.25, 0.8, tufts);
	}
	ROUGHNESS = sheen_rough;
	SPECULAR = sheen;
	RIM = 0.15;
	RIM_TINT = 0.7;
	BACKLIGHT = vec3(0.12) * h;
	if (glow > 0.5 && h > 0.001) {
		EMISSION += tipc * 0.45;
	}
}
