shader_type canvas_item;
// Recolours a rendered creature for its traits, with no extra frames: pixels in the coat's apricot hues get a new
// colour (hue turned, saturation and brightness scaled, so the fur keeps its shading), and the bright pink-violet foxfire
// and glowing tips get one new hue. Eyes, ears, ribbon, blossom, cream and stockings are outside both colour bands.
// The bands match the fox's palette (art/generators/fox3d.py); traits.gd holds the trait values.

uniform float coat_hue = 0.0;          // turns, added to the coat's hue
uniform float coat_sat = 1.0;
uniform float coat_val = 1.0;
uniform float glow_hue = -1.0;         // turns; below 0 keeps the rendered pink
uniform float glow_sat = 1.0;

varying vec4 tint;

vec3 rgb2hsv(vec3 c) {
	vec4 K = vec4(0.0, -1.0 / 3.0, 2.0 / 3.0, -1.0);
	vec4 p = mix(vec4(c.bg, K.wz), vec4(c.gb, K.xy), step(c.b, c.g));
	vec4 q = mix(vec4(p.xyw, c.r), vec4(c.r, p.yzx), step(p.x, c.r));
	float d = q.x - min(q.w, q.y);
	float e = 1.0e-10;
	return vec3(abs(q.z + (q.w - q.y) / (6.0 * d + e)), d / (q.x + e), q.x);
}

vec3 hsv2rgb(vec3 c) {
	vec3 p = abs(fract(c.xxx + vec3(1.0, 2.0 / 3.0, 1.0 / 3.0)) * 6.0 - 3.0);
	return c.z * mix(vec3(1.0), clamp(p - 1.0, 0.0, 1.0), c.y);
}

void vertex() {
	tint = COLOR;
}

void fragment() {
	vec4 t = texture(TEXTURE, UV);
	vec3 hsv = rgb2hsv(t.rgb);
	float deg = hsv.x * 360.0;
	float around_red = mod(deg + 180.0, 360.0) - 180.0;
	vec3 c = t.rgb;
	float coat = smoothstep(-6.0, 2.0, around_red) * (1.0 - smoothstep(34.0, 44.0, around_red)) * smoothstep(0.1, 0.22, hsv.y);
	if (coat > 0.0) {
		vec3 n = hsv2rgb(vec3(fract(hsv.x + coat_hue), clamp(hsv.y * coat_sat, 0.0, 1.0), clamp(hsv.z * coat_val, 0.0, 1.0)));
		c = mix(c, n, coat);
	}
	if (glow_hue >= 0.0) {
		float glow = smoothstep(245.0, 262.0, deg) * (1.0 - smoothstep(326.0, 336.0, deg)) * smoothstep(0.8, 0.92, hsv.z) * smoothstep(0.03, 0.08, hsv.y);
		if (glow > 0.0) {
			// the rendered glow runs pink to violet; squeeze that spread around the new hue so it reads as one colour
			float h = fract(glow_hue + (deg - 300.0) / 360.0 * 0.3);
			vec3 n = hsv2rgb(vec3(h, clamp(hsv.y * glow_sat, 0.0, 1.0), hsv.z));
			c = mix(c, n, glow);
		}
	}
	COLOR = vec4(c, t.a) * tint;
}
