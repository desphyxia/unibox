// Shared by the creature shaders (skin, fur, halo). Godot's skeleton and blend shapes have already moved each vertex
// before these run. Per vertex, from the creature builder (tools/creature_builder.gd):
//   COLOR = colour, alpha how much lighter the fur tips are
//   TANGENT = the direction the fur is combed along the surface
//   CUSTOM0 = (fur lift length, fur droop length, fur length outward along the normal, blink piece: 1 shown open,
//              2 shown closed)
//   CUSTOM1 = (glows, emission, surface: 0 lit 1 glossy 2 glowing, fur length along the surface)
//   CUSTOM2 = (position at rest, 0): fur strands keep their pattern however the creature moves

uniform float eyes_closed = 0.0;

bool hidden_piece(float blink) {
	return (blink > 0.5 && blink < 1.5 && eyes_closed > 0.5) || (blink > 1.5 && eyes_closed < 0.5);
}

// the traits: hue bands of the model's own colours get new colours (apricot coat, pink-violet glow)
uniform float coat_hue = 0.0;
uniform float coat_sat = 1.0;
uniform float coat_val = 1.0;
uniform float glow_hue = -1.0;
uniform float glow_sat = 1.0;
uniform float colour_fix = 0.0;        // the web (compatibility) renderer has already turned the vertex colours linear

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

vec3 trait_colour(vec3 lin_rgb) {
	vec3 s = pow(clamp(lin_rgb, 0.0, 1.0), vec3(1.0 / 2.2));
	s = colour_fix > 0.5 ? pow(s, vec3(1.0 / 2.2)) : s;
	vec3 hsv = rgb2hsv(s);
	float deg = hsv.x * 360.0;
	float around_red = mod(deg + 180.0, 360.0) - 180.0;
	float coat = smoothstep(-6.0, 2.0, around_red) * (1.0 - smoothstep(34.0, 44.0, around_red)) * smoothstep(0.1, 0.22, hsv.y);
	s = mix(s, hsv2rgb(vec3(fract(hsv.x + coat_hue), clamp(hsv.y * coat_sat, 0.0, 1.0), clamp(hsv.z * coat_val, 0.0, 1.0))), coat);
	if (glow_hue >= 0.0) {
		float glow = smoothstep(245.0, 262.0, deg) * (1.0 - smoothstep(326.0, 336.0, deg)) * smoothstep(0.03, 0.08, hsv.y);
		s = mix(s, hsv2rgb(vec3(fract(glow_hue + (deg - 300.0) / 360.0 * 0.3), clamp(hsv.y * glow_sat, 0.0, 1.0), hsv.z)), glow);
	}
	return pow(s, vec3(2.2));
}
