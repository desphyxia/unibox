// Moves the live fox like FoxRig in art/generators/fox3d.py: breathing chest blending into the head at the neck, the head
// turning about its pivot, ear flicks, tails bending from the root, bobbing foxfire, blinks. live_fox.gd sets the uniforms
// each frame. Per vertex: CUSTOM1 = (part: 0 body 1 head 2 ear 3 tail 4 fire, place along the tail, which one, blink),
// CUSTOM2 = (breathing push, head blend).
uniform mat3 head_rot = mat3(1.0);
uniform vec3 pivot;
uniform float breath = 0.0;
uniform vec3 ear_b0; uniform vec3 ear_ax0; uniform float ear_a0 = 0.0;
uniform vec3 ear_b1; uniform vec3 ear_ax1; uniform float ear_a1 = 0.0;
uniform vec3 tail_r0; uniform vec3 tail_r1; uniform vec3 tail_r2;
uniform vec3 tail_amp = vec3(0.0);
uniform float phase = 0.0;
uniform vec3 fire_b0; uniform vec3 fire_b1; uniform vec3 fire_b2;
uniform vec4 fire_m0; uniform vec4 fire_m1; uniform vec4 fire_m2;    // lift xyz, scale
uniform float blinking = 0.0;

vec3 rot_axis(vec3 p, vec3 c, vec3 ax, float a) {
	vec3 d = p - c;
	float cs = cos(a);
	float sn = sin(a);
	return c + d * cs + cross(ax, d) * sn + ax * dot(ax, d) * (1.0 - cs);
}

vec3 head_move(vec3 p) {
	return head_rot * (p - pivot) + pivot;
}

vec3 rig_move(vec3 p, vec4 c1, vec4 c2) {
	int kind = int(c1.x + 0.5);
	int which = int(c1.z + 0.5);
	if (kind == 0) {
		vec3 q = p + c2.xyz * breath;
		return mix(q, head_move(q), c2.w);
	} else if (kind == 1) {
		return head_move(p);
	} else if (kind == 2) {
		vec3 q = which == 0 ? rot_axis(p, ear_b0, ear_ax0, -ear_a0) : rot_axis(p, ear_b1, ear_ax1, -ear_a1);
		return head_move(q);
	} else if (kind == 3) {
		vec3 root = which == 0 ? tail_r0 : (which == 1 ? tail_r1 : tail_r2);
		float amp = which == 0 ? tail_amp.x : (which == 1 ? tail_amp.y : tail_amp.z);
		float t = c1.y;
		float a = amp * sin(phase + 1.3 * float(which) - 2.4 * t) * pow(t, 1.3);
		return rot_axis(p, root, vec3(0.0, 1.0, 0.0), a);
	} else {
		vec3 b = which == 0 ? fire_b0 : (which == 1 ? fire_b1 : fire_b2);
		vec4 m = which == 0 ? fire_m0 : (which == 1 ? fire_m1 : fire_m2);
		return (p - b) * vec3(m.w, 1.0 + (m.w - 1.0) * 1.6, m.w) + b + m.xyz;
	}
}

bool rig_hidden(vec4 c1) {
	return (c1.w > 0.5 && c1.w < 1.5 && blinking > 0.5) || (c1.w > 1.5 && blinking < 0.5);
}

// the same hue bands as shaders/fur_colour.gdshader, here on the model's own colours
uniform float coat_hue = 0.0;
uniform float coat_sat = 1.0;
uniform float coat_val = 1.0;
uniform float glow_hue = -1.0;
uniform float glow_sat = 1.0;

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

uniform float colour_fix = 0.0;        // the web (compatibility) renderer has already turned the vertex colours linear

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
