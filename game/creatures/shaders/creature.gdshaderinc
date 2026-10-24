// Shared by the creature shaders (skin, fur, halo). Godot's skeleton and blend shapes have already moved each vertex
// before these run. Per vertex, from the creature builder (tools/creature_builder.gd):
//   COLOR = colour, alpha how much lighter the fur tips are
//   TANGENT = the direction the fur is combed along the surface
//   CUSTOM0 = (fur lift length, fur droop length, fur length outward along the normal, blink piece: 1 shown open,
//              2 shown closed)
//   CUSTOM1 = (glows, emission, surface: 0 lit 1 glossy 2 glowing, fur length along the surface)
//   CUSTOM2 = (position at rest, fur layer height): fur strands keep their pattern however the creature moves
//   CUSTOM3 = (which trait recolours it: -1 by hue (the fox), 0 none, 1 coat, 2 glow or mane; the long-haired collie's
//              combed direction packed in one number (fur.gdshader), else 0; -, -)

uniform float eyes_closed = 0.0;

bool hidden_piece(float blink) {
	return (blink > 0.5 && blink < 1.5 && eyes_closed > 0.5) || (blink > 1.5 && eyes_closed < 0.5);
}

// the traits. By hue (the fox): hue bands of the model's own colours get new colours (the apricot coat, the pink-violet
// glow). By part (the unicorn): the coat or the mane takes a new hue, a little more colour and a brightness.
uniform float coat_hue = 0.0;
uniform float coat_sat = 1.0;
uniform float coat_val = 1.0;
uniform float glow_hue = -1.0;
uniform float glow_sat = 1.0;
uniform float colour_fix = 0.0;        // the web (compatibility) renderer has already turned the vertex colours linear
uniform vec4 coat_to = vec4(0.0);      // by part: (hue in turns, added saturation, brightness factor, 1 to recolour)
uniform vec4 mane_to = vec4(0.0);

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

vec3 part_colour(vec3 s, vec4 to) {
	vec3 hsv = rgb2hsv(s);
	return hsv2rgb(vec3(to.x, clamp(hsv.y * 0.6 + to.y, 0.0, 1.0), clamp(hsv.z * to.z, 0.0, 1.0)));
}

vec3 trait_colour(vec3 lin_rgb, float group) {
	vec3 s = pow(clamp(lin_rgb, 0.0, 1.0), vec3(1.0 / 2.2));
	s = colour_fix > 0.5 ? pow(s, vec3(1.0 / 2.2)) : s;
	if (group > -0.5) {
		if (group > 0.5 && group < 1.5 && coat_to.w > 0.5) {
			s = part_colour(s, coat_to);
		} else if (group > 1.5 && mane_to.w > 0.5) {
			s = part_colour(s, mane_to);
		}
		return pow(s, vec3(2.2));
	}
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
