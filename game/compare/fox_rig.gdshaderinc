// Poses and motions for the live fox, as the renders do them in art/generators/fox3d.py. Each vertex has a place in four
// poses (sit, stand, down, sleep) in pose_tex; pose_w blends them (lying down runs sit -> down -> sleep). On top: the
// chest breathing and the neck blending into the head (FoxRig.body_tf), the head turning about its pivot, ear turns, tails
// swaying and wagging from the root, foxfire bobbing, the walk's legs swinging from hip and shoulder (WalkRig), a lift,
// and blinks. live_fox.gd sets the uniforms every frame.
// Attributes: CUSTOM0 = (part: 0 body 1 head 2 ear 3 tail 4 fire, place along the tail, which one, blink piece),
// CUSTOM1 = (glows, emission, vertex id, -).

uniform sampler2D pose_tex : filter_nearest;
uniform int tex_row = 256;
uniform int per_vertex = 17;
uniform vec4 pose_w = vec4(1.0, 0.0, 0.0, 0.0);

uniform vec3 head_x = vec3(1.0, 0.0, 0.0);      // the head turn, by columns (a mat3 uniform read wrongly in the
uniform vec3 head_y = vec3(0.0, 1.0, 0.0);      // MultiMesh fur shader)
uniform vec3 head_z = vec3(0.0, 0.0, 1.0);
uniform vec3 pivot;
uniform float breath = 0.0;
uniform float lift = 0.0;
uniform vec3 ear_b0; uniform vec3 ear_ax0; uniform float ear_a0 = 0.0;
uniform vec3 ear_b1; uniform vec3 ear_ax1; uniform float ear_a1 = 0.0;
uniform vec3 tail_r0; uniform vec3 tail_r1; uniform vec3 tail_r2;
uniform vec3 tail_amp = vec3(0.0);       // sway amplitude per tail (already times the clip's sway)
uniform float phase = 0.0;
uniform float wag = 0.0;
uniform float wag_cycles = 2.0;
uniform float clip_u = 0.0;
uniform float tail_turn = 0.0;
uniform vec3 fire_b0; uniform vec3 fire_b1; uniform vec3 fire_b2;
uniform vec4 fire_m0; uniform vec4 fire_m1; uniform vec4 fire_m2;    // lift xyz, scale
uniform float eyes_closed = 0.0;
// the walk
uniform float walk_w = 0.0;
uniform vec3 leg_pivot[4];
uniform vec3 leg_knee[4];
uniform vec4 leg_th = vec4(0.0);
uniform vec4 leg_be = vec4(0.0);
uniform vec4 leg_kt = vec4(0.5);
uniform float bob = 0.0;
uniform float ground_y = 0.42;

const vec3 ACROSS = vec3(0.0, 0.0, -1.0);   // Blender's y axis: the legs swing about it

vec4 tx(int id, int k) {
	return texelFetch(pose_tex, ivec2((id % tex_row) * per_vertex + k, id / tex_row), 0);
}

// this vertex in the blended pose: position, normal, fur vector, breathing push, head blend, fur lift and droop
void pose_fetch(int id, out vec3 pos, out vec3 nrm, out vec3 comb, out vec3 br, out float wh, out float lift_l, out float droop_l) {
	pos = vec3(0.0); nrm = vec3(0.0); comb = vec3(0.0); br = vec3(0.0); wh = 0.0; lift_l = 0.0; droop_l = 0.0;
	for (int i = 0; i < 4; i++) {
		float w = pose_w[i];
		if (w < 0.0001) {
			continue;
		}
		vec4 a = tx(id, 4 * i);
		vec4 b = tx(id, 4 * i + 1);
		vec4 c = tx(id, 4 * i + 2);
		vec4 d = tx(id, 4 * i + 3);
		pos += a.xyz * w; lift_l += a.w * w;
		nrm += b.xyz * w; droop_l += b.w * w;
		comb += c.xyz * w;
		br += d.xyz * w; wh += d.w * w;
	}
	nrm = normalize(nrm + vec3(0.0, 1e-5, 0.0));
}

vec3 rot_axis(vec3 p, vec3 c, vec3 ax, float a) {
	vec3 d = p - c;
	float cs = cos(a);
	float sn = sin(a);
	return c + d * cs + cross(ax, d) * sn + ax * dot(ax, d) * (1.0 - cs);
}

vec3 head_move(vec3 p) {
	return mat3(head_x, head_y, head_z) * (p - pivot) + pivot;
}

vec3 legs_move(vec3 p, vec4 L) {
	int li = int(L.x + 0.5);
	float w = L.y * walk_w;
	if (w < 0.0001) {
		return p;
	}
	vec3 pv = leg_pivot[li];
	float th = leg_th[li];
	vec3 q1 = rot_axis(p, pv, ACROSS, th);
	vec3 kn = rot_axis(leg_knee[li], pv, ACROSS, th);
	vec3 q2 = rot_axis(q1, kn, ACROSS, leg_be[li]);
	float k = smoothstep(leg_kt[li] - 0.08, leg_kt[li] + 0.08, L.z);
	q1 = mix(q1, q2, k);
	vec3 moved = p + (q1 - p) * w - vec3(0.0, bob, 0.0) * (w * L.z);
	moved.y = max(moved.y, min(p.y, ground_y));     // a folding leg never pushes a paw into the ground
	return moved;
}

vec3 rig_move(vec3 p, vec3 br, float wh, vec4 c0, vec4 leg) {
	int kind = int(c0.x + 0.5);
	int which = int(c0.z + 0.5);
	vec3 up = vec3(0.0, lift, 0.0);
	if (kind == 0) {
		vec3 q = p + br * breath;
		q = mix(q, head_move(q), wh);
		return legs_move(q + up, leg);
	} else if (kind == 1) {
		return head_move(p) + up;
	} else if (kind == 2) {
		vec3 q = which == 0 ? rot_axis(p, ear_b0, ear_ax0, -ear_a0) : rot_axis(p, ear_b1, ear_ax1, -ear_a1);
		return head_move(q) + up;
	} else if (kind == 3) {
		vec3 root = which == 0 ? tail_r0 : (which == 1 ? tail_r1 : tail_r2);
		float amp = which == 0 ? tail_amp.x : (which == 1 ? tail_amp.y : tail_amp.z);
		float t = c0.y;
		float fi = float(which);
		float a = amp * sin(phase + 1.3 * fi - 2.4 * t) * pow(t, 1.3)
			+ wag * sin(6.2831853 * wag_cycles * clip_u + 1.1 * fi - 2.0 * t) * pow(t, 1.2) + tail_turn * pow(t, 1.5);
		return rot_axis(p, root, vec3(0.0, 1.0, 0.0), a) + up;
	} else {
		vec3 b = which == 0 ? fire_b0 : (which == 1 ? fire_b1 : fire_b2);
		vec4 m = which == 0 ? fire_m0 : (which == 1 ? fire_m1 : fire_m2);
		return (p - b) * vec3(m.w, 1.0 + (m.w - 1.0) * 1.6, m.w) + b + m.xyz + up;
	}
}

bool rig_hidden(vec4 c0) {
	return (c0.w > 0.5 && c0.w < 1.5 && eyes_closed > 0.5) || (c0.w > 1.5 && eyes_closed < 0.5);
}

// the same hue bands as shaders/fur_colour.gdshader, here on the model's own colours
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
