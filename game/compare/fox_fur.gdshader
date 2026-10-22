shader_type spatial;
// Shell fur: the furry skin drawn again as thin layers lifted along each point's fur (its combed direction, length, lift
// and droop, from the strand formulas in fox3d.py), with holes cut by noise so the layers read as strands and tufts. The
// layer height comes from the MultiMesh instance (INSTANCE_CUSTOM.x, 0 at the skin to 1 at the tips). Kept cheap for
// tablets: the noise is a small stored texture and the colours are worked out per vertex.
render_mode diffuse_lambert_wrap, specular_schlick_ggx, cull_disabled, alpha_to_coverage_and_one;
#include "res://compare/fox_rig.gdshaderinc"

uniform float strand_freq = 70.0;
uniform float tuft_freq = 9.0;
uniform sampler3D noise : filter_linear, repeat_enable;   // live_fox.gd: 32 cells each way, red strands, green tufts
const float NOISE_CELLS = 32.0;

varying vec3 root;
varying float h;
varying float tip;
varying float glow;
varying float fur_len;
varying vec3 base;

void vertex() {
	h = INSTANCE_CUSTOM.x;
	int id = int(CUSTOM1.z + 0.5);
	vec3 pos; vec3 nrm; vec3 comb; vec3 br; float wh; float ll; float dl;
	pose_fetch(id, pos, nrm, comb, br, wh, ll, dl);
	vec4 leg = tx(id, 16);
	root = VERTEX;                        // the sitting position: strands keep their pattern in every pose
	tip = COLOR.a;
	glow = CUSTOM1.x;
	base = trait_colour(COLOR.rgb);       // per vertex, not per pixel of every layer
	vec3 off = nrm * ll * (1.0 - (1.0 - h) * (1.0 - h)) + comb * pow(h, 1.15) - vec3(0.0, 1.0, 0.0) * dl * h * h;
	fur_len = length(comb);
	vec3 p = rig_move(pos + off, br, wh, CUSTOM0, leg);
	vec3 q = rig_move(pos + off + nrm * 0.05, br, wh, CUSTOM0, leg);
	NORMAL = normalize(q - p);
	VERTEX = rig_hidden(CUSTOM0) ? vec3(0.0) : p;
}

void fragment() {
	// looked up, not computed: a little more contrast stands in for the smooth steps the computed noise had
	float strands = clamp((texture(noise, root * (strand_freq / NOISE_CELLS)).r - 0.5) * 1.25 + 0.5, 0.0, 1.0);
	float tufts = clamp((texture(noise, (root * tuft_freq + vec3(7.1)) / NOISE_CELLS).g - 0.5) * 1.25 + 0.5, 0.0, 1.0);
	float keep = strands * 0.7 + tufts * 0.45;
	// no fur where the length runs out (face, eyes, nose); thinner where it is short
	float need = mix(0.12, 1.05, pow(h, 0.85)) + (1.0 - smoothstep(0.004, 0.03, fur_len)) * 2.0;
	// soft strand edges: with edge smoothing on, the smoothing samples cover a strand's edge in part (alpha to coverage)
	ALPHA = smoothstep(need - 0.06, need + 0.06, keep);
	ALPHA_SCISSOR_THRESHOLD = 0.5;
	ALPHA_ANTIALIASING_EDGE = 0.45;
	vec3 tipc = base + (vec3(1.0) - base) * tip * 0.5;
	ALBEDO = mix(base, tipc, h) * mix(0.74, 1.0, h);
	ROUGHNESS = 0.6;
	SPECULAR = 0.2;
	RIM = 0.15;
	RIM_TINT = 0.7;
	BACKLIGHT = vec3(0.12) * h;
	if (glow > 0.5) {
		EMISSION = tipc * 0.45;
	}
}
