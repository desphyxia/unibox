shader_type spatial;
// Shell fur: the furry skin drawn again as thin layers lifted along each point's fur (its combed direction, length, lift
// and droop, from the strand formulas in fox3d.py), with holes cut by noise so the layers read as strands and tufts. The
// layer height comes from the MultiMesh instance (INSTANCE_CUSTOM.x, 0 at the skin to 1 at the tips).
render_mode diffuse_lambert_wrap, specular_schlick_ggx, cull_disabled;
#include "res://compare/fox_rig.gdshaderinc"

uniform float strand_freq = 70.0;
uniform float tuft_freq = 9.0;

varying vec3 root;
varying float h;
varying float tip;
varying float glow;
varying float fur_len;

float hash3(vec3 p) {
	p = fract(p * 0.3183099 + vec3(0.1, 0.2, 0.3));
	p *= 17.0;
	return fract(p.x * p.y * p.z * (p.x + p.y + p.z));
}

float vnoise(vec3 x) {
	vec3 i = floor(x);
	vec3 f = fract(x);
	f = f * f * (3.0 - 2.0 * f);
	return mix(mix(mix(hash3(i), hash3(i + vec3(1, 0, 0)), f.x), mix(hash3(i + vec3(0, 1, 0)), hash3(i + vec3(1, 1, 0)), f.x), f.y),
			   mix(mix(hash3(i + vec3(0, 0, 1)), hash3(i + vec3(1, 0, 1)), f.x), mix(hash3(i + vec3(0, 1, 1)), hash3(i + vec3(1, 1, 1)), f.x), f.y), f.z);
}

void vertex() {
	h = INSTANCE_CUSTOM.x;
	root = VERTEX;
	tip = COLOR.a;
	glow = CUSTOM3.y;
	vec3 off = NORMAL * CUSTOM0.w * (1.0 - (1.0 - h) * (1.0 - h)) + CUSTOM0.xyz * pow(h, 1.15) - vec3(0.0, 1.0, 0.0) * CUSTOM3.x * h * h;
	float L = length(CUSTOM0.xyz);
	vec3 p = rig_move(VERTEX + off, CUSTOM1, CUSTOM2);
	vec3 q = rig_move(VERTEX + off + NORMAL * 0.05, CUSTOM1, CUSTOM2);
	NORMAL = normalize(q - p);
	fur_len = L;
	VERTEX = rig_hidden(CUSTOM1) ? vec3(0.0) : p;
}

void fragment() {
	float strands = vnoise(root * strand_freq);
	float tufts = vnoise(root * tuft_freq + vec3(7.1));
	float keep = strands * 0.7 + tufts * 0.45;
	// no fur where the length runs out (face, eyes, nose); thinner where it is short
	float need = mix(0.12, 1.05, pow(h, 0.85)) + (1.0 - smoothstep(0.004, 0.03, fur_len)) * 2.0;
	if (keep < need) {
		discard;
	}
	vec3 base = trait_colour(COLOR.rgb);
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
