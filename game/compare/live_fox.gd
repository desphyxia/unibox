class_name LiveFox
extends Node3D
## The fox as a live 3D model, as the game draws it (scripts/fox_view.gd puts one in the meadow): the mesh exported by
## art/generators/fox_live_export.py in four poses, shell fur grown from the strand formulas, and every clip computed
## each frame from the same curves the Blender renders used (FoxRig, WalkRig and ReactRig in fox3d.py). Its colours
## take the traits. The model is loaded once and shared by every fox; each fox has its own materials.
##   idle, walk (in place), eat, happy, hunger, liedown (sit -> sphinx -> curled), sleep, wake (lying down backward),
##   turn and turn_stand (half way round on the spot, sitting or standing; the fox then faces the other way)

signal clip_done(name: String)

const DATA := "res://compare/fox_live"
const CLIPS := {                      ## seconds, from the rendered clips' frames and the game's playback rates
	"idle": 2.0, "walk": 1.0, "eat": 16.0 / 12.0, "happy": 16.0 / 14.0, "hunger": 20.0 / 12.0, "liedown": 20.0 / 12.0,
	"sleep": 16.0 / 12.0, "wake": 20.0 / 15.0, "turn": 13.0 / 22.0, "turn_stand": 13.0 / 28.0,
}
const LOOPING := ["idle", "walk", "sleep"]
const TURN_DEG := 100.0               ## the renders' left-facing view is the fox turned this far (fox3d.TURN_DEG)

var shells := 6:
	set(v):
		shells = v
		if _fur:
			_build_shells()
var meta := {}
var rig := {}
var clip := "idle"
var facing := 1.0                     ## 1 as rendered, -1 turned round (the left-facing view)
var speed := 1.0                      ## how fast the clip plays (the walk keeps pace with the ground this way)
var auto_next := true                 ## after a one-shot clip: idle (or sleep after lying down); off when a creature leads
var triangles := 0                    ## drawn per frame without the fur layers
var _dur := 2.0                       ## the clip's length in seconds (idle's to start)
var _traits := {}
var _mats: Array[ShaderMaterial] = []
var _fur: MultiMeshInstance3D
var _t := 0.0
var _idle_t := 0.0
var _next_blink := 2.4
var _blink_until := -1.0

## the model, shared by every live fox: loaded once
static var _shared := {}


static func shared() -> Dictionary:
	if not _shared.is_empty():
		return _shared
	var m: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(DATA + ".json"))
	var blob := FileAccess.get_file_as_bytes(DATA + ".bin")
	var tx: Dictionary = m["tex"]
	var img := Image.create_from_data(int(tx["width"]), int(tx["height"]), false, Image.FORMAT_RGBAF,
		blob.slice(int(tx["offset"]), int(tx["offset"]) + int(tx["width"]) * int(tx["height"]) * 16))
	# the skin, eyes, ribbon and foxfire are one mesh (one draw); which surface each vertex is goes in CUSTOM1.w
	var parts := []
	var tris := 0
	var fur_src := []
	for cls in ["lit", "gloss", "emit"]:
		var a := _arrays(blob, m["groups"][cls], {"lit": 0.0, "gloss": 1.0, "emit": 2.0}[cls])
		parts.append(a)
		tris += int(m["groups"][cls]["tris"])
		if cls == "lit":
			fur_src = a
	var skin := ArrayMesh.new()
	skin.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, _join(parts), [], {}, _custom_flags())
	var halo := ArrayMesh.new()
	halo.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, _arrays(blob, m["groups"]["halo"], 0.0), [], {}, _custom_flags())
	tris += int(m["groups"]["halo"]["tris"])
	_shared = {"meta": m, "tex": ImageTexture.create_from_image(img), "skin": skin, "halo": halo,
		"fur": _furry_part(fur_src), "tris": tris, "noise": _noise_texture(),
		"web": RenderingServer.get_current_rendering_method() == "gl_compatibility"}
	return _shared


func _ready() -> void:
	var sh := shared()
	meta = sh["meta"]
	rig = meta["rig"]
	triangles = sh["tris"]
	for part in [["skin", preload("res://compare/fox_live.gdshader"), 0], ["halo", preload("res://compare/fox_halo.gdshader"), 1]]:
		var m := ShaderMaterial.new()
		m.shader = part[1]
		m.render_priority = part[2]
		_mats.append(m)
		var mi := MeshInstance3D.new()
		mi.mesh = sh[part[0]]
		mi.material_override = m
		mi.custom_aabb = AABB(Vector3(-8, -2, -8), Vector3(16, 12, 16))   ## it moves well outside its sitting shape
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mi)
	var fm := ShaderMaterial.new()
	fm.shader = preload("res://compare/fox_fur.gdshader")
	fm.set_shader_parameter("noise", sh["noise"])
	_mats.append(fm)
	_fur = MultiMeshInstance3D.new()
	_fur.material_override = fm
	_fur.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	_fur.custom_aabb = AABB(Vector3(-8, -2, -8), Vector3(16, 12, 16))
	add_child(_fur)
	_build_shells()
	var tx: Dictionary = meta["tex"]
	var walk: Dictionary = rig["walk"]
	var pivots := PackedVector3Array()
	var knees := PackedVector3Array()
	var kt := Vector4.ZERO
	for i in 4:
		pivots.append(_v(walk["legs"][i]["pivot"]))
		knees.append(_v(walk["legs"][i]["knee"]))
		kt[i] = walk["legs"][i]["kt"]
	for m in _mats:
		m.set_shader_parameter("pose_tex", sh["tex"])
		m.set_shader_parameter("tex_row", int(tx["row"]))
		m.set_shader_parameter("per_vertex", int(tx["per_vertex"]))
		m.set_shader_parameter("colour_fix", 1.0 if sh["web"] else 0.0)
		m.set_shader_parameter("leg_pivot", pivots)
		m.set_shader_parameter("leg_knee", knees)
		m.set_shader_parameter("leg_kt", kt)
		m.set_shader_parameter("ground_y", float(walk["ground"][1]))
	if not _traits.is_empty():
		set_traits(_traits)
	_apply(0.0)


static func _custom_flags() -> int:
	var f := 0
	for k in 2:
		f |= Mesh.ARRAY_CUSTOM_RGBA_FLOAT << (Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT + k * Mesh.ARRAY_FORMAT_CUSTOM_BITS)
	return f


static func _arrays(blob: PackedByteArray, gi: Dictionary, surface: float) -> Array:
	var n: int = gi["verts"]
	var stride: int = gi["stride"]
	var v := blob.slice(gi["vert_offset"], gi["vert_offset"] + n * stride * 4).to_float32_array()
	var ind := blob.slice(gi["index_offset"], gi["index_offset"] + int(gi["tris"]) * 12).to_int32_array()
	var pos := PackedVector3Array()
	var nrm := PackedVector3Array()
	var col := PackedColorArray()
	var c0 := PackedFloat32Array()
	var c1 := PackedFloat32Array()
	pos.resize(n)
	nrm.resize(n)
	col.resize(n)
	c0.resize(n * 4)
	c1.resize(n * 4)
	for i in n:
		var o := i * stride
		pos[i] = Vector3(v[o], v[o + 1], v[o + 2])
		nrm[i] = Vector3(v[o + 3], v[o + 4], v[o + 5])
		col[i] = Color(v[o + 6], v[o + 7], v[o + 8], v[o + 9])
		for k in 4:
			c0[i * 4 + k] = v[o + 10 + k]
			c1[i * 4 + k] = v[o + 14 + k]
		c1[i * 4 + 3] = surface
	var a := []
	a.resize(Mesh.ARRAY_MAX)
	a[Mesh.ARRAY_VERTEX] = pos
	a[Mesh.ARRAY_NORMAL] = nrm
	a[Mesh.ARRAY_COLOR] = col
	a[Mesh.ARRAY_CUSTOM0] = c0
	a[Mesh.ARRAY_CUSTOM1] = c1
	a[Mesh.ARRAY_INDEX] = ind
	return a


static func _join(parts: Array) -> Array:
	var out := []
	out.resize(Mesh.ARRAY_MAX)
	var pos := PackedVector3Array()
	var nrm := PackedVector3Array()
	var col := PackedColorArray()
	var c0 := PackedFloat32Array()
	var c1 := PackedFloat32Array()
	var ind := PackedInt32Array()
	for a in parts:
		var base := pos.size()
		pos.append_array(a[Mesh.ARRAY_VERTEX])
		nrm.append_array(a[Mesh.ARRAY_NORMAL])
		col.append_array(a[Mesh.ARRAY_COLOR])
		c0.append_array(a[Mesh.ARRAY_CUSTOM0])
		c1.append_array(a[Mesh.ARRAY_CUSTOM1])
		for i in a[Mesh.ARRAY_INDEX]:
			ind.append(i + base)
	out[Mesh.ARRAY_VERTEX] = pos
	out[Mesh.ARRAY_NORMAL] = nrm
	out[Mesh.ARRAY_COLOR] = col
	out[Mesh.ARRAY_CUSTOM0] = c0
	out[Mesh.ARRAY_CUSTOM1] = c1
	out[Mesh.ARRAY_INDEX] = ind
	return out


static func _furry_part(a: Array) -> ArrayMesh:
	## only the triangles that grow fur get the layers (the fur length is in the pose texture; the body, head, ears and
	## tails are the furry parts, minus the face, which the shader leaves bare)
	var c0: PackedFloat32Array = a[Mesh.ARRAY_CUSTOM0]
	var col: PackedColorArray = a[Mesh.ARRAY_COLOR]
	var ind: PackedInt32Array = a[Mesh.ARRAY_INDEX]
	var keep := PackedInt32Array()
	var furry := func(i: int) -> bool:
		return col[i].a > 0.001 and int(c0[i * 4] + 0.5) <= 3
	for t in range(0, ind.size(), 3):
		if furry.call(ind[t]) and furry.call(ind[t + 1]) and furry.call(ind[t + 2]):
			keep.append_array([ind[t], ind[t + 1], ind[t + 2]])
	var b := a.duplicate()
	b[Mesh.ARRAY_INDEX] = keep
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, b, [], {}, _custom_flags())
	return m


static func _noise_texture() -> ImageTexture3D:
	## the fur's strand and tuft noise, made once and looked up instead of computed for every pixel of every layer: a
	## tiling block of random values, red for strands and green for tufts (the texture's smoothing blends between them)
	const N := 32
	var rng := RandomNumberGenerator.new()
	rng.seed = 7
	var layers: Array[Image] = []
	for z in N:
		var d := PackedByteArray()
		d.resize(N * N * 2)
		for i in N * N * 2:
			d[i] = rng.randi() & 255
		layers.append(Image.create_from_data(N, N, false, Image.FORMAT_RG8, d))
	var t := ImageTexture3D.new()
	t.create(Image.FORMAT_RG8, N, N, N, false, layers)
	return t


func _build_shells() -> void:
	_fur.visible = shells > 0
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true
	mm.use_colors = true                    ## white: the web renderer multiplies by an unset (black) instance colour otherwise
	mm.mesh = shared()["fur"]
	mm.instance_count = shells
	for i in shells:
		mm.set_instance_transform(i, Transform3D.IDENTITY)
		mm.set_instance_custom_data(i, Color((i + 1.0) / shells, 0, 0, 0))
		mm.set_instance_color(i, Color.WHITE)
	_fur.multimesh = mm


func fur_triangles() -> int:
	var fm: ArrayMesh = shared()["fur"]
	return fm.surface_get_array_index_len(0) / 3 * shells


static func _v(a) -> Vector3:
	return Vector3(a[0], a[1], a[2])


func set_traits(t: Dictionary) -> void:
	_traits = t.duplicate()                ## kept for _ready when set before the fox is in the scene
	var c: Array = Traits.COATS.get(t.get("coat", "apricot"))
	var g: Array = Traits.GLOWS.get(t.get("glow", "pink"))
	for m in _mats:
		m.set_shader_parameter("coat_hue", c[0] / 360.0)
		m.set_shader_parameter("coat_sat", c[1])
		m.set_shader_parameter("coat_val", c[2])
		m.set_shader_parameter("glow_hue", g[0] / 360.0 if g[0] >= 0.0 else -1.0)
		m.set_shader_parameter("glow_sat", g[1])


# ------------------------------------------------------------------ clips
func play(name: String, seconds := -1.0) -> void:
	## seconds: the clip's length if not its usual one (a calm fox's happy wiggle is slower)
	clip = name
	_t = 0.0
	_dur = seconds if seconds > 0.0 else float(CLIPS[name])


func progress() -> float:
	## how far through the clip, 0 to 1 (a loop's place in its cycle)
	return fmod(_t, _dur) / _dur if LOOPING.has(clip) else clampf(_t / _dur, 0.0, 1.0)


func pose_weights() -> Vector4:
	## sit, stand, lying down, curled up asleep
	return _pose_weights(progress())


func _process(delta: float) -> void:
	_t += delta * speed
	_idle_t += delta
	if auto_next and _t >= _dur and not LOOPING.has(clip):
		var done := clip
		if done.begins_with("turn"):
			facing = -facing
		play("sleep" if done == "liedown" else "idle")
		clip_done.emit(done)
	_apply(delta)


static func _ss(a: float, b: float, x: float) -> float:
	if a == b:
		return 1.0 if x >= b else 0.0
	var t := clampf((x - a) / (b - a), 0.0, 1.0)
	return t * t * (3.0 - 2.0 * t)


static func _win(u: float, a: float, b: float, c: float, d: float) -> float:
	return _ss(a, b, u) * (1.0 - _ss(c, d, u))


static func _ease(x: float) -> float:
	x = clampf(x, 0.0, 1.0)
	return x * x * (3.0 - 2.0 * x)


func _params(u: float) -> Dictionary:
	## ReactRig.params: the clip's own curves
	var p := {"pitch": 0.0, "yaw": 0.0, "roll": 0.0, "ear": 0.0, "wag": 0.0, "wag_cycles": 2.0, "breath": 0.0,
		"closed": false, "lift": 0.0, "turn": 0.0, "tail_turn": 0.0, "sway": 1.0}
	var d := func(x: float) -> float: return deg_to_rad(x)
	match clip:
		"eat":
			var down := _win(u, 0.0, 0.22, 0.78, 1.0)
			var chewing := _win(u, 0.22, 0.3, 0.7, 0.78)
			var chew := sin(TAU * 3.0 * (u - 0.22) / 0.56)
			p.merge({"pitch": d.call(22) * down + d.call(4) * chew * chewing, "roll": d.call(2.5) * chew * chewing,
				"ear": d.call(-7) * down, "closed": u >= 0.3 and u < 0.7}, true)
		"happy":
			var w := _win(u, 0.0, 0.14, 0.72, 1.0)
			p.merge({"roll": d.call(10) * sin(2.0 * TAU * u) * w, "yaw": d.call(-5) * w, "pitch": d.call(-6) * w,
				"ear": d.call(-6) * w, "wag": d.call(16) * w, "wag_cycles": 3.0, "closed": u >= 0.12 and u < 0.8,
				"lift": 0.09 * absf(sin(2.0 * TAU * u)) * w}, true)
		"hunger":
			var look := _win(u, 0.0, 0.18, 0.42, 0.58)
			var sigh := _win(u, 0.5, 0.64, 0.8, 1.0)
			var inhale := _win(u, 0.36, 0.46, 0.5, 0.62)
			p.merge({"pitch": d.call(-15) * look + d.call(10) * sigh, "yaw": d.call(-4) * look,
				"ear": d.call(10) * look + d.call(-9) * sigh, "breath": 0.05 * inhale - 0.04 * sigh,
				"closed": u >= 0.64 and u < 0.76}, true)
		"sleep":
			p.merge({"sway": 0.3, "breath": 0.02 * sin(TAU * u), "closed": true}, true)
		"liedown", "wake":
			var v := u if clip == "liedown" else 1.0 - u
			p.merge({"pitch": d.call(7) * _win(v, 0.0, 0.12, 0.24, 0.4), "ear": d.call(-10) * _win(v, 0.1, 0.4, 0.72, 1.0),
				"sway": 1.0 - 0.7 * _ss(0.0, 1.0, v), "closed": v >= 0.62}, true)
		"turn", "turn_stand":
			var e := u * u * u * (u * (6.0 * u - 15.0) + 10.0)
			var sg := facing
			var mid := pow(sin(PI * u), 2.0)
			p.merge({"turn": -d.call(TURN_DEG) * e * sg, "lift": 0.12 * mid, "yaw": -sg * d.call(9) * sin(TAU * u),
				"tail_turn": sg * d.call(12) * sin(TAU * u), "ear": d.call(6) * mid, "sway": 1.0 - mid}, true)
	return p


func _pose_weights(u: float) -> Vector4:
	## sit, stand, down, sleep
	match clip:
		"walk", "turn_stand":
			return Vector4(0, 1, 0, 0)
		"sleep":
			return Vector4(0, 0, 0, 1)
		"liedown", "wake":
			var v := u if clip == "liedown" else 1.0 - u
			var w1 := _ease((v - 0.04) / 0.5)
			var w2 := _ease((v - 0.42) / 0.53)
			return Vector4((1.0 - w1) * (1.0 - w2), 0.0, w1 * (1.0 - w2), w2)
	return Vector4(1, 0, 0, 0)


func _blend(key: String, w: Vector4, f: Callable) -> Vector3:
	var out := Vector3.ZERO
	var poses: Array = meta["poses"]
	for i in 4:
		if w[i] > 0.0:
			out += f.call(rig[poses[i]]) * w[i]
	return out


func _apply(_delta: float) -> void:
	var u := progress()
	var c := _params(u)
	var w := _pose_weights(u)
	# the idle phase: the idle loop's own cycle while idle, one cycle over eat/happy/hunger/sleep, held for the others
	var ph := 0.0
	match clip:
		"idle":
			ph = TAU * fmod(_idle_t, 2.0) / 2.0
		"walk", "eat", "happy", "hunger", "sleep":
			ph = TAU * u
	var k: float = c["sway"]
	var head := Basis(Vector3.UP, c["yaw"]) * Basis(Vector3.RIGHT, c["roll"]) * Basis(Vector3(0, 0, -1), c["pitch"])
	var sway := Basis(Vector3.UP, deg_to_rad(3.0) * k * sin(ph + 0.8)) * Basis(Vector3.RIGHT, deg_to_rad(2.6) * k * sin(ph)) \
		* Basis(Vector3(0, 0, -1), deg_to_rad(1.6) * k * sin(2.0 * ph))
	var lift: float = c["lift"]
	var bob := 0.0
	var ear0: float = c["ear"]
	var ear1: float = c["ear"] + deg_to_rad(2.5) * sin(ph + 2.0) * k
	if clip == "idle":
		ear0 = deg_to_rad(14.0) * exp(-pow((fmod(_idle_t, 2.0) / 2.0 * 24.0 - 6.0) / 1.2, 2.0))
		ear1 = deg_to_rad(2.5) * sin(ph + 2.0)
	if clip == "walk":
		bob = 0.045 * cos(2.0 * TAU * u)
		lift = bob
		sway = Basis(Vector3.UP, deg_to_rad(1.5) * sin(ph)) * Basis(Vector3.RIGHT, deg_to_rad(1.2) * sin(ph + 0.6)) \
			* Basis(Vector3(0, 0, -1), deg_to_rad(2.2) * sin(2.0 * ph + 0.9))
		ear0 = 0.0
	var closed: bool = c["closed"]
	if not closed and clip in ["idle"]:
		if _idle_t > _next_blink:
			_blink_until = _idle_t + 0.14
			_next_blink = _idle_t + randf_range(2.5, 5.0)
		closed = _idle_t < _blink_until
	var pivot := _blend("pivot", w, func(r): return _v(r["pivot"]))
	var walk: Dictionary = rig["walk"]
	var th := Vector4.ZERO
	var be := Vector4.ZERO
	for i in 4:
		var L: Dictionary = walk["legs"][i]
		var q := fmod(u + float(L["off"]), 1.0)
		var A: float = L["A"]
		var st: float = walk["stance"]
		if q < st:
			th[i] = -A + 2.0 * A * q / st
		else:
			var s := (q - st) / (1.0 - st)
			th[i] = A - 2.0 * A * (0.5 - 0.5 * cos(PI * s))
			be[i] = float(L["bend"]) * sin(PI * s)
	# every value once, then into each material
	var hb := head * sway
	var par := {"pose_w": w, "head_x": hb.x, "head_y": hb.y, "head_z": hb.z, "pivot": pivot,
		"breath": 0.028 * sin(ph) * k + float(c["breath"]), "lift": lift, "ear_a0": ear0, "ear_a1": ear1,
		"phase": ph, "wag": c["wag"], "wag_cycles": c["wag_cycles"], "clip_u": u, "tail_turn": c["tail_turn"],
		"eyes_closed": 1.0 if closed else 0.0, "walk_w": w.y if clip == "walk" else 0.0, "leg_th": th, "leg_be": be,
		"bob": bob}
	for e in 2:
		par["ear_b%d" % e] = _blend("", w, func(r): return _v(r["ears"][e]["base"]))
		par["ear_ax%d" % e] = _blend("", w, func(r): return _v(r["ears"][e]["axis"])).normalized()
	var amp := Vector3.ZERO
	for ti in 3:
		par["tail_r%d" % ti] = _blend("", w, func(r): return _v(r["tails"][ti]["root"]))
		amp[ti] = float(rig["sit"]["tails"][ti]["amp"]) * k
	par["tail_amp"] = amp
	for f in 3:
		par["fire_b%d" % f] = _blend("", w, func(r): return _v(r["fires"][f]) if f < r["fires"].size() else _v(rig["sit"]["fires"][f]))
		var fl := Vector3(0.05 * sin(ph * 2.0 + 1.7 * f), 0.09 * sin(ph + 2.1 * f), 0.0)
		par["fire_m%d" % f] = Vector4(fl.x, fl.y, fl.z, 1.0 + 0.06 * sin(3.0 * ph + f))
	for m in _mats:
		for key in par:
			m.set_shader_parameter(key, par[key])
	# the whole fox turns about its ground point; facing round is the renders' left view
	var base_turn := 0.0 if facing > 0 else -deg_to_rad(TURN_DEG)
	rotation.y = base_turn + float(c["turn"])
