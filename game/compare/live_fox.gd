class_name LiveFox
extends Node3D
## The fox as a live 3D model (the comparison with the rendered sprites): the mesh exported by
## art/generators/fox_live_export.py, shell fur grown from the strand formulas, and the idle loop's motions computed every
## frame instead of played from 24 pictures. Its colours take the same traits as the sprites.

const DATA := "res://compare/fox_live"
const LOOP := 2.0                     ## seconds, the same as the rendered idle loop (24 frames at 12 a second)

var shells := 16:
	set(v):
		shells = v
		if _fur:
			_build_shells()
var rig := {}
var _mats: Array[ShaderMaterial] = []
var _fur: MultiMeshInstance3D
var _fur_mesh: ArrayMesh
var _t := 0.0
var _next_blink := 2.4
var _blink_until := -1.0
var triangles := 0                    ## drawn per frame, fur layers included


func _ready() -> void:
	var meta: Dictionary = JSON.parse_string(FileAccess.get_file_as_string(DATA + ".json"))
	var blob := FileAccess.get_file_as_bytes(DATA + ".bin")
	rig = meta["rig"]
	var shaders := {"lit": [preload("res://compare/fox_live.gdshader"), 0], "gloss": [preload("res://compare/fox_live.gdshader"), 1],
		"emit": [preload("res://compare/fox_live.gdshader"), 2], "halo": [preload("res://compare/fox_halo.gdshader"), 3]}
	for cls in meta["groups"]:
		var gi: Dictionary = meta["groups"][cls]
		var arrays := _arrays(blob, gi)
		var mesh := ArrayMesh.new()
		mesh.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, arrays, [], {}, _custom_flags())
		var m := ShaderMaterial.new()
		m.shader = shaders[cls][0]
		if cls != "halo":
			m.set_shader_parameter("kind", shaders[cls][1])
		if cls == "halo":
			m.render_priority = 1
		mesh.surface_set_material(0, m)
		_mats.append(m)
		var mi := MeshInstance3D.new()
		mi.mesh = mesh
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		add_child(mi)
		triangles += int(gi["tris"])
		if cls == "lit":
			_fur_mesh = _furry_part(arrays)
	var fm := ShaderMaterial.new()
	fm.shader = preload("res://compare/fox_fur.gdshader")
	_fur_mesh.surface_set_material(0, fm)
	_mats.append(fm)
	_fur = MultiMeshInstance3D.new()
	_fur.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	add_child(_fur)
	_build_shells()
	var web_renderer := RenderingServer.get_current_rendering_method() == "gl_compatibility"
	for m in _mats:
		_static_uniforms(m)
		m.set_shader_parameter("colour_fix", 1.0 if web_renderer else 0.0)


func _custom_flags() -> int:
	var f := 0
	for k in 4:
		f |= Mesh.ARRAY_CUSTOM_RGBA_FLOAT << (Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT + k * Mesh.ARRAY_FORMAT_CUSTOM_BITS)
	return f


func _arrays(blob: PackedByteArray, gi: Dictionary) -> Array:
	var n: int = gi["verts"]
	var stride: int = gi["stride"]
	var v := blob.slice(gi["vert_offset"], gi["vert_offset"] + n * stride * 4).to_float32_array()
	var ind := blob.slice(gi["index_offset"], gi["index_offset"] + int(gi["tris"]) * 12).to_int32_array()
	var pos := PackedVector3Array()
	var nrm := PackedVector3Array()
	var col := PackedColorArray()
	pos.resize(n)
	nrm.resize(n)
	col.resize(n)
	var cu := [PackedFloat32Array(), PackedFloat32Array(), PackedFloat32Array(), PackedFloat32Array()]
	for c in cu:
		c.resize(n * 4)
	for i in n:
		var o := i * stride
		pos[i] = Vector3(v[o], v[o + 1], v[o + 2])
		nrm[i] = Vector3(v[o + 3], v[o + 4], v[o + 5])
		col[i] = Color(v[o + 6], v[o + 7], v[o + 8], v[o + 9])
		for k in 4:
			var src := o + 10 + k * 4
			var dst := i * 4
			cu[k][dst] = v[src]
			cu[k][dst + 1] = v[src + 1]
			cu[k][dst + 2] = v[src + 2]
			cu[k][dst + 3] = v[src + 3]
	var a := []
	a.resize(Mesh.ARRAY_MAX)
	a[Mesh.ARRAY_VERTEX] = pos
	a[Mesh.ARRAY_NORMAL] = nrm
	a[Mesh.ARRAY_COLOR] = col
	a[Mesh.ARRAY_CUSTOM0] = cu[0]
	a[Mesh.ARRAY_CUSTOM1] = cu[1]
	a[Mesh.ARRAY_CUSTOM2] = cu[2]
	a[Mesh.ARRAY_CUSTOM3] = cu[3]
	a[Mesh.ARRAY_INDEX] = ind
	return a


func _furry_part(a: Array) -> ArrayMesh:
	## only the triangles that grow fur get the layers
	var c0: PackedFloat32Array = a[Mesh.ARRAY_CUSTOM0]
	var ind: PackedInt32Array = a[Mesh.ARRAY_INDEX]
	var keep := PackedInt32Array()
	var furry := func(i: int) -> bool:
		return Vector3(c0[i * 4], c0[i * 4 + 1], c0[i * 4 + 2]).length() > 0.004
	for t in range(0, ind.size(), 3):
		if furry.call(ind[t]) or furry.call(ind[t + 1]) or furry.call(ind[t + 2]):
			keep.append_array([ind[t], ind[t + 1], ind[t + 2]])
	var b := a.duplicate()
	b[Mesh.ARRAY_INDEX] = keep
	var m := ArrayMesh.new()
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, b, [], {}, _custom_flags())
	return m


func _build_shells() -> void:
	var mm := MultiMesh.new()
	mm.transform_format = MultiMesh.TRANSFORM_3D
	mm.use_custom_data = true
	mm.use_colors = true                    ## white: the web renderer multiplies by an unset (black) instance colour otherwise
	mm.mesh = _fur_mesh
	mm.instance_count = shells
	for i in shells:
		mm.set_instance_transform(i, Transform3D.IDENTITY)
		mm.set_instance_custom_data(i, Color((i + 1.0) / shells, 0, 0, 0))
		mm.set_instance_color(i, Color.WHITE)
	_fur.multimesh = mm


func fur_triangles() -> int:
	return _fur_mesh.surface_get_array_index_len(0) / 3 * shells


func _v(a) -> Vector3:
	return Vector3(a[0], a[1], a[2])


func _static_uniforms(m: ShaderMaterial) -> void:
	m.set_shader_parameter("pivot", _v(rig["pivot"]))
	for i in 2:
		m.set_shader_parameter("ear_b%d" % i, _v(rig["ears"][i]["base"]))
		m.set_shader_parameter("ear_ax%d" % i, _v(rig["ears"][i]["axis"]).normalized())
	var amp := Vector3.ZERO
	for i in rig["tails"].size():
		m.set_shader_parameter("tail_r%d" % i, _v(rig["tails"][i]["root"]))
		amp[i] = rig["tails"][i]["amp"]
	m.set_shader_parameter("tail_amp", amp)
	for i in rig["fires"].size():
		m.set_shader_parameter("fire_b%d" % i, _v(rig["fires"][i]))


func set_traits(t: Dictionary) -> void:
	var c: Array = Traits.COATS.get(t.get("coat", "apricot"))
	var g: Array = Traits.GLOWS.get(t.get("glow", "pink"))
	for m in _mats:
		m.set_shader_parameter("coat_hue", c[0] / 360.0)
		m.set_shader_parameter("coat_sat", c[1])
		m.set_shader_parameter("coat_val", c[2])
		m.set_shader_parameter("glow_hue", g[0] / 360.0 if g[0] >= 0.0 else -1.0)
		m.set_shader_parameter("glow_sat", g[1])


# ------------------------------------------------------------------ the idle loop (FoxRig.frame), every frame
func _process(delta: float) -> void:
	_t += delta
	var ph := TAU * fmod(_t, LOOP) / LOOP
	var u := fmod(_t, LOOP) / LOOP
	# head: small turns about Blender's z (up), x (along the body) and y (across) axes, in Godot's axes
	var R := Basis(Vector3.UP, deg_to_rad(3.0) * sin(ph + 0.8)) * Basis(Vector3.RIGHT, deg_to_rad(2.6) * sin(ph)) \
		* Basis(Vector3(0, 0, -1), deg_to_rad(1.6) * sin(2.0 * ph))
	var ear0 := deg_to_rad(14.0) * exp(-pow((u * 24.0 - 6.0) / 1.2, 2.0))
	var ear1 := deg_to_rad(2.5) * sin(ph + 2.0)
	if _t > _next_blink:
		_blink_until = _t + 0.14
		_next_blink = _t + randf_range(2.5, 5.0)
	for m in _mats:
		m.set_shader_parameter("head_rot", R)
		m.set_shader_parameter("breath", 0.028 * sin(ph))
		m.set_shader_parameter("phase", ph)
		m.set_shader_parameter("ear_a0", ear0)
		m.set_shader_parameter("ear_a1", ear1)
		m.set_shader_parameter("blinking", 1.0 if _t < _blink_until else 0.0)
		for k in rig["fires"].size():
			# Blender's lift (x, 0, z) is Godot's (x, z, 0)
			var lift := Vector3(0.05 * sin(ph * 2.0 + 1.7 * k), 0.09 * sin(ph + 2.1 * k), 0.0)
			m.set_shader_parameter("fire_m%d" % k, Vector4(lift.x, lift.y, lift.z, 1.0 + 0.06 * sin(3.0 * ph + k)))
