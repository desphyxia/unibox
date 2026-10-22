class_name CreatureModel
extends Node3D
## A creature as the game draws it: the scene a creature's build tool makes (tools/build_fox.gd with
## tools/creature_builder.gd): a standard Skeleton3D, a "Skin" mesh (skin, eyes, glowing parts, and a second surface for
## the glow round them) and a "Fur" mesh (the furry skin), both skinned, with the poses as blend shapes, and an
## AnimationPlayer holding every clip. This script adds the shell fur (the Fur mesh stacked with thin copies of itself,
## all in one mesh, so the engine poses it once a frame), the trait colours, the idle blinks and which way it faces,
## and plays the clips, each blending into the next. It can also look at something (head_look.gd turns the head and
## neck after the clip) and wear things at the places the build tool found (the top of the head, the neck, a tail): a
## worn thing follows its place through every clip and pose.
##   idle, walk, eat, happy, hunger, liedown, sleep, wake (loops: idle, walk, sleep), turn and turn_stand (half way
##   round, sitting or standing; the creature then faces the other way)

signal clip_done(name: String)

const LOOPING := ["idle", "walk", "sleep"]
const BLEND := 0.2                     ## seconds one clip blends into the next

var shells := 6:                       ## fur layers over the skin
	set(v):
		shells = v
		if _fur:
			_fur.mesh = _layered(_fur_source, shells)
var facing := 1.0                      ## 1 as built, -1 turned round (the left-facing view)
var speed := 1.0:                      ## how fast the clip plays (the walk keeps pace with the ground this way)
	set(v):
		speed = v
		if _player:
			_player.speed_scale = _clip_scale * speed
var auto_next := true                  ## after a one-shot clip: idle (or sleep after lying down); off when a creature leads
var random_start := false              ## start the idle loop at a random place, so not every creature breathes in step
var clip := "idle"
var eyes_closed := 0.0:                ## set by the clips; the idle blinks are made here
	set(v):
		if v != eyes_closed:
			eyes_closed = v
			for m in _mats:
				m.set_shader_parameter("eyes_closed", v)
var triangles := 0                     ## drawn a frame without the fur layers
var look: HeadLook                     ## set look.target (this creature's own space) and look.looking

var _player: AnimationPlayer
var _skin: MeshInstance3D
var _fur: MeshInstance3D
var _fur_source: ArrayMesh             ## the furry skin as built, one layer
var _mats: Array[ShaderMaterial] = []
var _skin_mat: ShaderMaterial
var _traits := {}
var _clip_scale := 1.0
var _pending := ""
var _pending_seconds := -1.0
var _next_blink := 2.4
var _blink_until := -1.0
var _t := 0.0
var _worn := {}                        ## place -> the Node3D worn there

static var _noise: ImageTexture3D
static var _stacks := {}               ## the stacked fur meshes, by source and layer count, shared by every creature


func _ready() -> void:
	_player = $AnimationPlayer
	_skin = $Skeleton3D/Skin
	_fur = $Skeleton3D/Fur
	_skin_mat = _material(preload("res://creatures/shaders/skin.gdshader"))
	_skin.set_surface_override_material(0, _skin_mat)
	var halo := _material(preload("res://creatures/shaders/halo.gdshader"))
	halo.render_priority = 1
	_skin.set_surface_override_material(1, halo)
	_fur_source = _fur.mesh
	for mi in [_skin, _fur]:
		for s in mi.mesh.get_surface_count():
			triangles += mi.mesh.surface_get_array_index_len(s) / 3
	if _noise == null:
		_noise = _noise_texture()
	var fm := _material(preload("res://creatures/shaders/fur.gdshader"))
	fm.set_shader_parameter("noise", _noise)
	_fur.material_override = fm
	_fur.mesh = _layered(_fur_source, shells)
	_player.animation_finished.connect(_on_finished)
	look = HeadLook.new()
	look.model = self
	$Skeleton3D.add_child(look)
	($Skeleton3D as Skeleton3D).skeleton_updated.connect(_place_worn)
	if not _traits.is_empty():
		set_traits(_traits)
	play(_pending if _pending != "" else clip, _pending_seconds)
	if random_start and clip == "idle":
		_player.seek(randf() * _player.current_animation_length, true)


func _material(shader: Shader) -> ShaderMaterial:
	var m := ShaderMaterial.new()
	m.shader = shader
	m.set_shader_parameter("colour_fix", 1.0 if RenderingServer.get_current_rendering_method() == "gl_compatibility" else 0.0)
	_mats.append(m)
	return m


static func _layered(src: ArrayMesh, layers: int) -> ArrayMesh:
	## the furry skin and `layers` copies of it stacked in one mesh, each copy already lifted to its height along the
	## fur (out along the normal, combed along the surface, drooping a little), in the rest shape and in every blend
	## shape; the skeleton then carries the layers like any other point (the web renderer passes no tangents to a shader,
	## so the fur can't be grown there). Each copy's height (0 the skin, 1 the tips) goes in CUSTOM2.w for the fur
	## shader's holes and colours. Made once for each source and layer count.
	var key := "%s#%d" % [src.resource_path if src.resource_path != "" else str(src.get_instance_id()), layers]
	if _stacks.has(key):
		return _stacks[key]
	var a := src.surface_get_arrays(0)
	if a.is_empty() or a[Mesh.ARRAY_VERTEX] == null:
		return src                         # the engine kept no copy of the mesh: the skin alone, no fur
	var nv: int = (a[Mesh.ARRAY_VERTEX] as PackedVector3Array).size()
	var copies := layers + 1
	var c0: PackedFloat32Array = a[Mesh.ARRAY_CUSTOM0]
	var c1: PackedFloat32Array = a[Mesh.ARRAY_CUSTOM1]
	var out := []
	out.resize(Mesh.ARRAY_MAX)
	out[Mesh.ARRAY_VERTEX] = _lift(a[Mesh.ARRAY_VERTEX], a[Mesh.ARRAY_NORMAL], a[Mesh.ARRAY_TANGENT], c0, c1, layers)
	for k in Mesh.ARRAY_MAX:
		if a[k] == null or k in [Mesh.ARRAY_INDEX, Mesh.ARRAY_CUSTOM2, Mesh.ARRAY_VERTEX]:
			continue
		var arr = a[k].duplicate()
		for c in layers:
			arr.append_array(a[k])
		out[k] = arr
	var c2: PackedFloat32Array = a[Mesh.ARRAY_CUSTOM2]
	var c2_out := PackedFloat32Array()
	var index: PackedInt32Array = a[Mesh.ARRAY_INDEX]
	var index_out := PackedInt32Array()
	for c in copies:
		var h := float(c) / layers if layers > 0 else 0.0
		var part := c2.duplicate()
		for i in nv:
			part[i * 4 + 3] = h
		c2_out.append_array(part)
		var ip := index.duplicate()
		for i in ip.size():
			ip[i] += c * nv
		index_out.append_array(ip)
	out[Mesh.ARRAY_CUSTOM2] = c2_out
	out[Mesh.ARRAY_INDEX] = index_out
	var shapes := []
	for b in src.surface_get_blend_shape_arrays(0):
		var sb := []
		sb.resize(Mesh.ARRAY_MAX)
		sb[Mesh.ARRAY_VERTEX] = _lift(b[Mesh.ARRAY_VERTEX], b[Mesh.ARRAY_NORMAL], b[Mesh.ARRAY_TANGENT], c0, c1, layers)
		for k in [Mesh.ARRAY_NORMAL, Mesh.ARRAY_TANGENT]:
			if b[k] == null:
				continue
			var arr = b[k].duplicate()
			for c in layers:
				arr.append_array(b[k])
			sb[k] = arr
		shapes.append(sb)
	var m := ArrayMesh.new()
	m.blend_shape_mode = src.blend_shape_mode
	for i in src.get_blend_shape_count():
		m.add_blend_shape(src.get_blend_shape_name(i))
	var flags := 0
	for k in 3:
		flags |= Mesh.ARRAY_CUSTOM_RGBA_FLOAT << (Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT + k * Mesh.ARRAY_FORMAT_CUSTOM_BITS)
	m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, out, shapes, {}, flags)
	_stacks[key] = m
	return m


static func _lift(pos: PackedVector3Array, nrm: PackedVector3Array, tan: PackedFloat32Array, c0: PackedFloat32Array,
		c1: PackedFloat32Array, layers: int) -> PackedVector3Array:
	## every copy's points: the skin's, then each layer's, lifted along the fur (as in creatures/shaders/fur.gdshader)
	var out := pos.duplicate()
	for c in range(1, layers + 1):
		var h := float(c) / layers
		var rise := 1.0 - (1.0 - h) * (1.0 - h)
		var comb_k := pow(h, 1.15)
		var drop := h * h
		var part := pos.duplicate()
		for i in pos.size():
			var n := nrm[i]
			var t := Vector3(tan[i * 4], tan[i * 4 + 1], tan[i * 4 + 2])
			part[i] = pos[i] + n * (c0[i * 4] * rise + c0[i * 4 + 2] * comb_k) + t * (c1[i * 4 + 3] * comb_k) \
				- Vector3(0.0, c0[i * 4 + 1] * drop, 0.0)
		out.append_array(part)
	return out


static func release_shared() -> void:
	## let go of the shared fur meshes and noise (when the game closes), so nothing is left over at exit
	_stacks.clear()
	_noise = null


func fur_triangles() -> int:
	return _fur_source.surface_get_array_index_len(0) / 3 * shells if _fur_source else 0


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


func set_traits(t: Dictionary) -> void:
	_traits = t.duplicate()                ## kept for _ready when set before the creature is in the scene
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
	if not _player:
		_pending = name
		_pending_seconds = seconds
		return
	var anim := name
	if name == "turn" or name == "turn_stand":
		anim = name + ("_r" if facing > 0 else "_l")
	var a := _player.get_animation(anim)
	_clip_scale = a.length / seconds if seconds > 0.0 else 1.0
	_player.speed_scale = _clip_scale * speed
	# blend from the last clip, but not out of a turn: it ends exactly on the other side's rest pose, as the facing flips
	var from := String(_player.current_animation if _player.current_animation != "" else _player.assigned_animation)
	var blend := 0.0 if from == "" or from.begins_with("turn") else BLEND
	if from == anim:
		_player.seek(0.0, true)
	else:
		_player.play(anim, blend)
	if name == "idle":
		eyes_closed = 0.0


# ------------------------------------------------------------------ wearing things
func places() -> Array:
	return (get_meta("wear", {}) as Dictionary).keys()


func place_size(place: String) -> float:
	## how big the place is (the head's half width, the neck's radius, the tail's radius), for sizing what goes there
	return float(get_meta("wear")[place]["size"])


func wear(place: String, thing: Node3D) -> void:
	take_off(place)
	_worn[place] = thing
	$Skeleton3D.add_child(thing)
	_place_worn()


func take_off(place: String) -> void:
	if _worn.has(place):
		(_worn[place] as Node3D).queue_free()
		_worn.erase(place)


func worn_point(place: String) -> Vector3:
	## where the place is now, in this creature's own space
	return place_transform(place).origin


func place_transform(place: String) -> Transform3D:
	## the place as the clip, the pose and any look have moved it: its bone's move, applied to the place in the
	## current pose (blended between the poses as their blend shapes are)
	var info: Dictionary = get_meta("wear")[place]
	var sk: Skeleton3D = $Skeleton3D
	var b := sk.find_bone(info["bone"])
	var move := sk.get_bone_global_pose(b) * sk.get_bone_global_rest(b).affine_inverse()
	var w := pose_weights()
	var poses: Array = info["poses"]
	var at := Vector3.ZERO
	var q := Quaternion(0, 0, 0, 0)
	var first := (poses[0] as Transform3D).basis.get_rotation_quaternion()
	for i in 4:
		if w[i] <= 0.0:
			continue
		var t: Transform3D = poses[i]
		at += t.origin * w[i]
		var qi := t.basis.get_rotation_quaternion()
		if qi.dot(first) < 0.0:
			qi = -qi
		q += qi * w[i]
	return move * Transform3D(Basis(q.normalized()), at)


func _place_worn() -> void:
	for place in _worn:
		(_worn[place] as Node3D).transform = place_transform(place)


func progress() -> float:
	## how far through the clip, 0 to 1 (a loop's place in its cycle)
	if not _player or _player.current_animation == "":
		return 0.0
	return clampf(_player.current_animation_position / _player.current_animation_length, 0.0, 1.0)


func pose_weights() -> Vector4:
	## sit, stand, lying down, curled up asleep: from the blend shapes
	if not _skin:
		return Vector4(1, 0, 0, 0)
	var s := _skin.get_blend_shape_value(0)
	var d := _skin.get_blend_shape_value(1)
	var c := _skin.get_blend_shape_value(2)
	return Vector4(maxf(0.0, 1.0 - s - d - c), s, d, c)


func _on_finished(anim: StringName) -> void:
	if not auto_next:
		return                             # held on its last frame; the creature decides what comes next
	var done := clip
	if done.begins_with("turn"):
		facing = -facing
	play("sleep" if done == "liedown" else "idle")
	clip_done.emit(done)


func _process(delta: float) -> void:
	_t += delta
	var turn_deg: float = get_meta("turn_deg", 100.0)
	rotation.y = 0.0 if facing > 0 else -deg_to_rad(turn_deg)
	if clip == "idle":
		if _t > _next_blink:
			_blink_until = _t + 0.14
			_next_blink = _t + randf_range(2.5, 5.0)
		eyes_closed = 1.0 if _t < _blink_until else 0.0
