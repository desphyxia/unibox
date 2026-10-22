extends RefCounted
## Turns a creature's Blender export into the model the game draws, the same way for every kind of creature:
##   - a standard Skeleton3D (bones with rest positions) and a Skin binding the mesh to it,
##   - meshes whose vertices carry up to four bone weights, with the poses (and anything else that is a change of shape,
##     like breathing) as blend shapes,
##   - every clip baked into an Animation (bone positions, rotations and scales, blend shape weights, and values such as
##     eyes_closed on the root), from a function that says where each bone moves the vertices at a given moment,
##   - one scene (root script creatures/creature_model.gd) holding it all, saved compressed.
## The creature's own tool (tools/build_fox.gd) supplies the vertices, bones, weights and motion.
##
## Vertex table (Dictionary of packed arrays, one entry a vertex):
##   pos, nrm, tan (PackedVector3Array: rest position, normal, fur direction; only the fur direction's part along the
##     surface is kept as the tangent, since Godot keeps tangents flat on the surface), col (PackedColorArray),
##   c0, c1, c2, c3 (PackedFloat32Array, four a vertex: CUSTOM0..3), bones (PackedInt32Array, four a vertex),
##   weights (PackedFloat32Array, four a vertex), shapes ({name: {"pos", "nrm", "tan"}}: the vertices in that shape).

const CUSTOM_FLAGS := (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM0_SHIFT) \
	| (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM1_SHIFT) \
	| (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM2_SHIFT) \
	| (Mesh.ARRAY_CUSTOM_RGBA_FLOAT << Mesh.ARRAY_FORMAT_CUSTOM3_SHIFT)


static func make_mesh(table: Dictionary, surfaces: Array, shape_names: Array) -> ArrayMesh:
	## one surface for each list of triangles (indices into the table); each surface keeps only the vertices it uses
	var m := ArrayMesh.new()
	m.blend_shape_mode = Mesh.BLEND_SHAPE_MODE_NORMALIZED   ## shapes are whole targets: base * (1 - sum) + shape * weight
	for n in shape_names:
		m.add_blend_shape(n)
	for tris in surfaces:
		var used := {}
		var order := PackedInt32Array()
		for i in tris:
			if not used.has(i):
				used[i] = order.size()
				order.append(i)
		var index := PackedInt32Array()
		index.resize(tris.size())
		for k in tris.size():
			index[k] = used[tris[k]]
		var a := _arrays(table, order, table["pos"], table["nrm"], table["tan"])
		a[Mesh.ARRAY_INDEX] = index
		var shapes := []
		for n in shape_names:
			var s: Dictionary = table["shapes"][n]
			var b := _arrays(table, order, s["pos"], s["nrm"], s["tan"], true)
			shapes.append(b)
		# (Godot's attribute compression crashes on this mix of custom data, bones and blend shapes, so it stays off)
		m.add_surface_from_arrays(Mesh.PRIMITIVE_TRIANGLES, a, shapes, {}, CUSTOM_FLAGS)
	return m


static func _arrays(t: Dictionary, order: PackedInt32Array, pos: PackedVector3Array, nrm: PackedVector3Array,
		tan: PackedVector3Array, shape_only := false) -> Array:
	var n := order.size()
	var p := PackedVector3Array()
	var q := PackedVector3Array()
	var g := PackedFloat32Array()
	p.resize(n)
	q.resize(n)
	g.resize(n * 4)
	for k in n:
		var i := order[k]
		p[k] = pos[i]
		q[k] = nrm[i]
		var d := tan[i] - nrm[i] * tan[i].dot(nrm[i])     # along the surface
		if d.length() < 1e-6:
			d = nrm[i].cross(Vector3.UP if absf(nrm[i].y) < 0.9 else Vector3.RIGHT)   # any direction across the normal
		d = d.normalized()
		g[k * 4] = d.x
		g[k * 4 + 1] = d.y
		g[k * 4 + 2] = d.z
		g[k * 4 + 3] = 1.0
	var a := []
	a.resize(Mesh.ARRAY_MAX)
	a[Mesh.ARRAY_VERTEX] = p
	a[Mesh.ARRAY_NORMAL] = q
	a[Mesh.ARRAY_TANGENT] = g
	if shape_only:
		return a
	var col := PackedColorArray()
	col.resize(n)
	var cs := [PackedFloat32Array(), PackedFloat32Array(), PackedFloat32Array(), PackedFloat32Array()]
	var bones := PackedInt32Array()
	var weights := PackedFloat32Array()
	for arr in cs:
		arr.resize(n * 4)
	bones.resize(n * 4)
	weights.resize(n * 4)
	for k in n:
		var i := order[k]
		col[k] = t["col"][i]
		for j in 4:
			for c in 4:
				cs[c][k * 4 + j] = t[["c0", "c1", "c2", "c3"][c]][i * 4 + j]
			bones[k * 4 + j] = t["bones"][i * 4 + j]
			weights[k * 4 + j] = t["weights"][i * 4 + j]
	a[Mesh.ARRAY_COLOR] = col
	a[Mesh.ARRAY_CUSTOM0] = cs[0]
	a[Mesh.ARRAY_CUSTOM1] = cs[1]
	a[Mesh.ARRAY_CUSTOM2] = cs[2]
	a[Mesh.ARRAY_CUSTOM3] = cs[3]
	a[Mesh.ARRAY_BONES] = bones
	a[Mesh.ARRAY_WEIGHTS] = weights
	return a


static func pack_weights(per_vertex: Array) -> Array:
	## [{bone: weight}] -> [bones, weights]: the four biggest, adding up to one
	var bones := PackedInt32Array()
	var weights := PackedFloat32Array()
	for wd in per_vertex:
		var items := []
		for b in wd:
			if wd[b] > 1e-5:
				items.append([b, wd[b]])
		items.sort_custom(func(x, y): return x[1] > y[1])
		items = items.slice(0, 4)
		var total := 0.0
		for it in items:
			total += it[1]
		for j in 4:
			bones.append(items[j][0] if j < items.size() else 0)
			weights.append(items[j][1] / total if j < items.size() else 0.0)
	return [bones, weights]


# ------------------------------------------------------------------ skeleton
## bones: [{"name", "parent" (index or -1), "rest" (Transform3D, in the model's space)}]

static func make_skeleton(bones: Array) -> Skeleton3D:
	var sk := Skeleton3D.new()
	sk.name = "Skeleton3D"
	for b in bones:
		sk.add_bone(b["name"])
	for i in bones.size():
		var b: Dictionary = bones[i]
		sk.set_bone_parent(i, b["parent"])
		sk.set_bone_rest(i, _local(bones, i, b["rest"]))
	sk.reset_bone_poses()
	return sk


static func make_skin(bones: Array) -> Skin:
	var skin := Skin.new()
	for i in bones.size():
		skin.add_bind(i, (bones[i]["rest"] as Transform3D).affine_inverse())
	return skin


static func _local(bones: Array, i: int, global: Transform3D) -> Transform3D:
	var p: int = bones[i]["parent"]
	return global if p < 0 else (bones[p]["rest"] as Transform3D).affine_inverse() * global


# ------------------------------------------------------------------ clips
## frame(time) -> {"move": [Transform3D for each bone: where it carries the vertices from their posed place],
##                  "shapes": {name: weight}, "values": {property: value}}

static func bake(name: String, length: float, fps: float, looping: bool, bones: Array, mesh_paths: Array,
		frame: Callable, scaled_bones := []) -> Animation:
	var a := Animation.new()
	a.resource_name = name
	a.length = length
	a.loop_mode = Animation.LOOP_LINEAR if looping else Animation.LOOP_NONE
	var n := int(ceil(length * fps - 0.001))
	var pos_t := []
	var rot_t := []
	var scl_t := {}
	for i in bones.size():
		var path := NodePath("Skeleton3D:" + String(bones[i]["name"]))
		var tp := a.add_track(Animation.TYPE_POSITION_3D)
		a.track_set_path(tp, path)
		pos_t.append(tp)
		var tr := a.add_track(Animation.TYPE_ROTATION_3D)
		a.track_set_path(tr, path)
		rot_t.append(tr)
		if i in scaled_bones:
			var ts := a.add_track(Animation.TYPE_SCALE_3D)
			a.track_set_path(ts, path)
			scl_t[i] = ts
	var shape_t := {}
	var value_t := {}
	for k in n + 1:
		var tm := minf(k / fps, length)
		var f: Dictionary = frame.call(tm)
		var glob := []
		for i in bones.size():
			glob.append((f["move"][i] as Transform3D) * (bones[i]["rest"] as Transform3D))
		for i in bones.size():
			var p: int = bones[i]["parent"]
			var loc: Transform3D = glob[i] if p < 0 else (glob[p] as Transform3D).affine_inverse() * glob[i]
			a.position_track_insert_key(pos_t[i], tm, loc.origin)
			a.rotation_track_insert_key(rot_t[i], tm, loc.basis.get_rotation_quaternion())
			if scl_t.has(i):
				a.scale_track_insert_key(scl_t[i], tm, loc.basis.get_scale())
		for s in f.get("shapes", {}):
			if not shape_t.has(s):
				shape_t[s] = []
				for mp in mesh_paths:
					var t := a.add_track(Animation.TYPE_BLEND_SHAPE)
					a.track_set_path(t, NodePath("%s:%s" % [mp, s]))
					shape_t[s].append(t)
			for t in shape_t[s]:
				a.blend_shape_track_insert_key(t, tm, f["shapes"][s])
		for v in f.get("values", {}):
			if not value_t.has(v):
				value_t[v] = a.add_track(Animation.TYPE_VALUE)
				a.track_set_path(value_t[v], NodePath(".:" + String(v)))
				a.value_track_set_update_mode(value_t[v], Animation.UPDATE_DISCRETE)
			a.track_insert_key(value_t[v], tm, f["values"][v])
	# every track stays, even where it never moves: the player leaves a bone the clip does not mention where the last
	# clip put it
	a.compress()                        # positions, rotations, scales and blend shapes packed small
	return a


static func bake_fk(name: String, length: float, fps: float, looping: bool, bones: Array, frame: Callable,
		mesh_paths := []) -> Animation:
	## a clip written as bone turns: frame(time) -> {"rot": {bone name: Basis, a turn from its rest}, "move": {bone name:
	## Vector3, a shift in its parent's space}, "shapes": {...}, "values": {...}}; bones not named stay at rest
	var rest_local := []
	for i in bones.size():
		var p: int = bones[i]["parent"]
		rest_local.append(bones[i]["rest"] if p < 0 else (bones[p]["rest"] as Transform3D).affine_inverse() * bones[i]["rest"])
	var to_moves := func(tm: float) -> Dictionary:
		var f: Dictionary = frame.call(tm)
		var glob := []
		glob.resize(bones.size())
		for i in bones.size():
			var loc: Transform3D = rest_local[i]
			var nm: String = bones[i]["name"]
			if f.get("rot", {}).has(nm):
				loc.basis = loc.basis * (f["rot"][nm] as Basis)
			if f.get("move", {}).has(nm):
				loc.origin += f["move"][nm]
			var p: int = bones[i]["parent"]
			glob[i] = loc if p < 0 else (glob[p] as Transform3D) * loc
		var moves := []
		for i in bones.size():
			moves.append((glob[i] as Transform3D) * (bones[i]["rest"] as Transform3D).affine_inverse())
		return {"move": moves, "shapes": f.get("shapes", {}), "values": f.get("values", {})}
	return bake(name, length, fps, looping, bones, mesh_paths, to_moves)


# ------------------------------------------------------------------ the scene
static func save_scene(path: String, root_name: String, skeleton: Skeleton3D, skin: Skin, meshes: Dictionary,
		anims: Array, meta: Dictionary) -> int:
	## meshes: {node name: ArrayMesh}, all under the skeleton and bound by the skin
	var root := Node3D.new()
	root.name = root_name
	root.set_script(load("res://creatures/creature_model.gd"))
	root.add_child(skeleton)
	skeleton.owner = root
	for n in meshes:
		var mi := MeshInstance3D.new()
		mi.name = n
		mi.mesh = meshes[n]
		mi.skin = skin
		mi.skeleton = NodePath("..")
		mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
		mi.custom_aabb = AABB(Vector3(-8, -2, -8), Vector3(16, 12, 16))   ## it moves well outside its resting shape
		skeleton.add_child(mi)
		mi.owner = root
	var ap := AnimationPlayer.new()
	ap.name = "AnimationPlayer"
	var lib := AnimationLibrary.new()
	for a in anims:
		lib.add_animation(a.resource_name, a)
	ap.add_animation_library("", lib)
	root.add_child(ap)
	ap.owner = root
	for k in meta:
		root.set_meta(k, meta[k])
	var ps := PackedScene.new()
	var err := ps.pack(root)
	if err == OK:
		err = ResourceSaver.save(ps, path, ResourceSaver.FLAG_COMPRESS)
	root.free()
	return err
