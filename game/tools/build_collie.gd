extends SceneTree
## Builds the border collie the game draws (creatures/collie/collie.scn) from its Blender export (art/exports/
## collie_live.bin and .json, made by art/generators/collie_live_export.py from collie D, collie_d.py), with
## tools/creature_builder.gd. Like the new unicorn it is one standing model with a skeleton (body, two neck bones, head,
## ears, the lower jaw, three bones down each leg, four along the tail) and skin weights from the export; every clip is written here
## as bone turns, for a dog:
##   idle (breathing, an ear flick, a slow wag), walk (a four-beat walk), eat (head down to the ground, nibbling), happy
##   (little bounces on the front paws and a fast wag), hunger (looks up, then sighs), liedown (sits back on its hind
##   legs, then slides its front legs forward to lie like a sphinx), sleep (the head down on the front paws), wake,
##   yawn, and the half turns.
##   godot --headless --path . -s res://tools/build_collie.gd

const B := preload("res://tools/creature_builder.gd")
const OUT := "res://creatures/collie/collie.scn"
const FPS := 30.0
const TURN_DEG := 100.0
const CLIPS := {
	"idle": [2.0, true], "walk": [0.9, true], "eat": [16.0 / 12.0, false], "happy": [16.0 / 14.0, false],
	"hunger": [20.0 / 12.0, false], "liedown": [20.0 / 12.0, false], "sleep": [16.0 / 12.0, true],
	"yawn": [20.0 / 12.0, false],
	"wake": [20.0 / 15.0, false], "turn_r": [13.0 / 22.0, false], "turn_l": [13.0 / 22.0, false],
	"turn_stand_r": [13.0 / 28.0, false], "turn_stand_l": [13.0 / 28.0, false],
}
const ACROSS := Vector3(0, 0, 1)       ## legs and neck bend about this (toward the viewer); +: forward and up
const LEGS := ["nh", "nf", "fh", "ff"]  ## near hind, near front, far hind, far front
const WALK_OFF := {"nh": 0.0, "nf": 0.25, "fh": 0.5, "ff": 0.75}   ## a four-beat walk
const STANCE := 0.62

var meta: Dictionary
var bones := []
var bone := {}


func _initialize() -> void:
	var base := ProjectSettings.globalize_path("res://").path_join("../art/exports/collie_live").simplify_path()
	meta = JSON.parse_string(FileAccess.get_file_as_string(base + ".json"))
	var blob := FileAccess.get_file_as_bytes(base + ".bin")
	for b in meta["bones"]:
		bone[b["name"]] = bones.size()
		bones.append({"name": b["name"], "parent": bone[b["parent"]] if b["parent"] != "" else -1,
			"rest": Transform3D(Basis(), _v(b["at"]))})
	var table := {"pos": PackedVector3Array(), "nrm": PackedVector3Array(), "tan": PackedVector3Array(),
		"col": PackedColorArray(), "c0": PackedFloat32Array(), "c1": PackedFloat32Array(), "c2": PackedFloat32Array(),
		"c3": PackedFloat32Array(), "bones": PackedInt32Array(), "weights": PackedFloat32Array(), "shapes": {}}
	var skin_tris := PackedInt32Array()
	var fur_tris := PackedInt32Array()
	var furry := PackedByteArray()
	for cls in ["lit", "gloss", "emit"]:
		if not meta["groups"].has(cls):
			continue
		var gi: Dictionary = meta["groups"][cls]
		var stride: int = gi["stride"]
		var v := blob.slice(gi["vert_offset"], gi["vert_offset"] + int(gi["verts"]) * stride * 4).to_float32_array()
		var ind := blob.slice(gi["index_offset"], gi["index_offset"] + int(gi["tris"]) * 12).to_int32_array()
		var first: int = table["pos"].size()
		for i in int(gi["verts"]):
			var o := i * stride
			var p := Vector3(v[o], v[o + 1], v[o + 2])
			var nr := Vector3(v[o + 3], v[o + 4], v[o + 5]).normalized()
			var comb := Vector3(v[o + 15], v[o + 16], v[o + 17])
			var out := comb.dot(nr)
			table["pos"].append(p)
			table["nrm"].append(nr)
			table["tan"].append(comb)
			table["col"].append(Color(v[o + 6], v[o + 7], v[o + 8], v[o + 9]))
			table["c0"].append_array([v[o + 13], v[o + 14], out, v[o + 11]])
			table["c1"].append_array([0.0, v[o + 10], {"lit": 0.0, "gloss": 1.0, "emit": 2.0}[cls], (comb - nr * out).length()])
			table["c2"].append_array([p.x, p.y, p.z, 0.0])
			table["c3"].append_array([v[o + 12], 0.0, 0.0, 0.0])        # which trait recolours it: 1 the dark coat, 2 the white
			for k in 4:
				table["bones"].append(int(v[o + 18 + k] + 0.5))
				table["weights"].append(v[o + 22 + k])
			furry.append(1 if v[o + 9] > 0.001 else 0)
		for k in range(0, ind.size(), 3):
			var tri := [ind[k] + first, ind[k + 1] + first, ind[k + 2] + first]
			if furry[tri[0]] and furry[tri[1]] and furry[tri[2]]:
				fur_tris.append_array(tri)
			else:
				skin_tris.append_array(tri)
	var meshes := {"Skin": B.make_mesh(table, [skin_tris], []), "Fur": B.make_mesh(table, [fur_tris], [])}
	print("collie: %d vertices, %d bones; skin %d triangles, fur %d triangles" % [table["pos"].size(), bones.size(),
		skin_tris.size() / 3, fur_tris.size() / 3])
	var anims := []
	for c in CLIPS:
		anims.append(B.bake_fk(c, CLIPS[c][0], FPS, CLIPS[c][1], bones, _frame.bind(c)))
	var head_at: Vector3 = bones[bone["head"]]["rest"].origin
	var err := B.save_scene(OUT, "Collie", B.make_skeleton(bones), B.make_skin(bones), meshes,
		anims, {"camera": meta["camera"], "ground": meta["ground"], "turn_deg": TURN_DEG, "poses": ["sit", "stand", "down", "sleep"],
		"pivots": [head_at, head_at, head_at, head_at], "head_forward": _v(meta["head_forward"]), "places": _places(),
		"look_chain": [["neck_0", 0.2], ["neck_1", 0.3]], "trait_mode": "group", "kind": "collie",
		"shadows": {"sit": [Vector2(14, 200), Vector2(-14, 200)], "stand": [Vector2(14, 200), Vector2(-14, 200)],
			"sleep": [Vector2(8, 230), Vector2(-8, 230)]},
		"walk": {"stride": 70.0, "stance": STANCE}, "eat_drop": Vector2(10, 60), "touch": Vector2(175, 230),
		"fur": {"root_shade": 0.95, "strand_freq": 230.0, "tuft_freq": 26.0, "sheen": 0.5, "sheen_rough": 0.42},
		"blanket": Vector3(60, 230, 90)})
	print("saved %s (%s), %d KB" % [OUT, error_string(err), FileAccess.get_file_as_bytes(OUT).size() / 1024])
	quit()


static func _v(a) -> Vector3:
	return Vector3(a[0], a[1], a[2])


func _places() -> Dictionary:
	## where things are worn, the mouth and the head's middle: one place for every pose (the poses are bone turns here)
	var out := {}
	var pl: Dictionary = meta["places"]
	for k in pl:
		var at := _v(pl[k]["at"])
		var basis := Basis()
		if pl[k].has("axis"):
			var ax := _v(pl[k]["axis"]).normalized()
			if k == "neck":                       # y along the neck, x forward
				var x := (Vector3.RIGHT - ax * ax.x).normalized()
				basis = Basis(x, ax, x.cross(ax))
			else:                                 # x along the tail, y up
				var y := (Vector3.UP - ax * ax.y).normalized()
				basis = Basis(ax, y, ax.cross(y))
		var t := Transform3D(basis, at)
		out[k] = {"bone": pl[k]["bone"], "size": float(pl[k]["size"]), "poses": [t, t, t, t]}
	var head: Transform3D = bones[bone["head"]]["rest"]
	out["middle"] = {"bone": "head", "size": 1.0, "poses": [head, head, head, head]}
	return out


# ------------------------------------------------------------------ the clips, as bone turns
static func _ss(a: float, b: float, x: float) -> float:
	var t := clampf((x - a) / (b - a), 0.0, 1.0)
	return t * t * (3.0 - 2.0 * t)


static func _win(u: float, a: float, b: float, c: float, d: float) -> float:
	return _ss(a, b, u) * (1.0 - _ss(c, d, u))


static func _ease(x: float) -> float:
	x = clampf(x, 0.0, 1.0)
	return x * x * (3.0 - 2.0 * x)


static func _r(axis: Vector3, a: float) -> Basis:
	return Basis(axis, a)


func _add(f: Dictionary, b: String, rot: Basis) -> void:
	f["rot"][b] = f["rot"].get(b, Basis()) * rot


func _jaw(f: Dictionary, close: float) -> void:
	## the mouth: 1 shut, 0 as modelled (a smile), below 0 wider (-1 about twice as open)
	var ax := _v(meta["jaw_axis"]).normalized()
	_add(f, "jaw", _r(ax, deg_to_rad(float(meta["jaw_open"])) * close))


func _wag(f: Dictionary, ph: float, amount: float, lift := 0.0) -> void:
	## the tail swings side to side (about the up axis), each bone a little after the one before
	for t in 4:
		_add(f, "tail_%d" % t, _r(Vector3.UP, amount * sin(ph - 0.7 * t)) * _r(ACROSS, -lift * (1.0 if t == 0 else 0.3)))


func _lying(f: Dictionary, sit: float, down: float, rest: float) -> void:
	## lying down like a dog: sit (0 to 1) drops the hind end onto folded hind legs; down (0 to 1) slides the front
	## legs forward and lowers the chest to the ground; rest (0 to 1) lays the head on the front paws
	var drop := float(meta.get("lie_drop", 1.2))
	f["move"]["body"] = Vector3(0.05 * down, -drop * (0.45 * sit + 0.55 * down), 0.0)
	_add(f, "body", _r(ACROSS, 0.28 * sit * (1.0 - down)))          # sitting: the chest up, the hind end down
	for side in ["n", "f"]:
		_add(f, "leg_%sh_upper" % side, _r(ACROSS, 1.05 * sit))      # the thigh forward under the belly
		_add(f, "leg_%sh_lower" % side, _r(ACROSS, -2.05 * sit))     # the hock folded back
		_add(f, "leg_%sh_paw" % side, _r(ACROSS, 1.0 * sit))         # the foot flat on the ground
		_add(f, "leg_%sf_upper" % side, _r(ACROSS, -0.28 * sit * (1.0 - down) + 1.25 * down))   # the forelegs forward
		_add(f, "leg_%sf_lower" % side, _r(ACROSS, 0.25 * down))
		_add(f, "leg_%sf_paw" % side, _r(ACROSS, -0.1 * down))
	# the neck stays up while it lies down, then lowers until the chin rests on the paws
	_add(f, "neck_0", _r(ACROSS, -0.28 * sit * (1.0 - down) - 0.62 * rest))
	_add(f, "neck_1", _r(ACROSS, -0.42 * rest))
	_add(f, "head", _r(ACROSS, 0.42 * rest) * _r(Vector3.RIGHT, 0.08 * rest))
	_jaw(f, 0.9 * rest)
	_add(f, "ear_0", _r(Vector3.RIGHT, 0.25 * rest))
	_add(f, "ear_1", _r(Vector3.RIGHT, -0.25 * rest))
	var lift := float(meta.get("tail_lie", 0.6))       # the tail lifts to lie along the ground behind, and curls round
	for t in 4:
		_add(f, "tail_%d" % t, _r(Vector3.UP, -0.35 * rest) * _r(ACROSS, (-0.9 if t == 0 else -0.15) * maxf(sit, down) * lift))


func _frame(tm: float, name: String) -> Dictionary:
	var dur: float = CLIPS[name][0]
	var u := clampf(tm / dur, 0.0, 1.0)
	var clip := name.trim_suffix("_r").trim_suffix("_l")
	var sg := -1.0 if name.ends_with("_l") else 1.0
	var ph := TAU * u
	var f := {"rot": {}, "move": {}, "values": {}}
	var closed := false
	match clip:
		"idle":
			f["move"]["body"] = Vector3(0, 0.012 * sin(ph), 0)
			_add(f, "neck_0", _r(ACROSS, 0.02 * sin(ph + 0.5)))
			_add(f, "head", _r(Vector3.UP, 0.05 * sin(ph)) * _r(ACROSS, 0.03 * sin(ph + 1.0)))
			_add(f, "ear_0", _r(Vector3.RIGHT, 0.35 * exp(-pow((u * 24.0 - 6.0) / 1.2, 2.0))))
			_add(f, "ear_1", _r(Vector3.RIGHT, -0.06 * sin(ph + 2.0)))
			_wag(f, 2.0 * ph, 0.16)
		"walk":
			for leg in LEGS:
				var q := fmod(u + WALK_OFF[leg], 1.0)
				var th := 0.0
				var bend := 0.0
				var a := 0.34
				if q < STANCE:
					th = a - 2.0 * a * q / STANCE
				else:
					var s := (q - STANCE) / (1.0 - STANCE)
					th = -a + 2.0 * a * (0.5 - 0.5 * cos(PI * s))
					bend = sin(PI * s)
				var hind: bool = leg.ends_with("h")
				_add(f, "leg_%s_upper" % leg, _r(ACROSS, th))
				if hind:
					_add(f, "leg_%s_lower" % leg, _r(ACROSS, -0.55 * bend))
					_add(f, "leg_%s_paw" % leg, _r(ACROSS, 0.75 * bend))
				else:
					_add(f, "leg_%s_lower" % leg, _r(ACROSS, 0.2 * bend))
					_add(f, "leg_%s_paw" % leg, _r(ACROSS, -1.1 * bend))
			f["move"]["body"] = Vector3(0, 0.025 * cos(2.0 * ph), 0)
			_add(f, "neck_1", _r(ACROSS, 0.04 * sin(2.0 * ph + 1.0)))
			_add(f, "head", _r(ACROSS, -0.03 * sin(2.0 * ph + 1.0)))
			_wag(f, ph, 0.14)
		"eat":
			var down := _win(u, 0.0, 0.22, 0.78, 1.0)
			var chewing := _win(u, 0.22, 0.3, 0.7, 0.78)
			var chew := sin(TAU * 3.0 * (u - 0.22) / 0.56)
			_add(f, "neck_0", _r(ACROSS, -0.45 * down))
			_add(f, "neck_1", _r(ACROSS, -0.35 * down))
			_add(f, "head", _r(ACROSS, -0.35 * down + 0.06 * chew * chewing) * _r(Vector3.RIGHT, 0.04 * chew * chewing))
			_jaw(f, (0.5 + 0.5 * chew) * chewing)
			for side in ["n", "f"]:                                  # the front legs splay a little to reach
				_add(f, "leg_%sf_upper" % side, _r(ACROSS, 0.1 * down))
			_add(f, "ear_0", _r(Vector3.RIGHT, -0.15 * down))
			_add(f, "ear_1", _r(Vector3.RIGHT, 0.15 * down))
			_wag(f, 2.0 * ph, 0.12 * down)
			closed = u >= 0.3 and u < 0.7
		"happy":
			var w := _win(u, 0.0, 0.14, 0.72, 1.0)
			var hop := absf(sin(2.0 * ph)) * w
			f["move"]["body"] = Vector3(0, 0.12 * hop, 0)
			_add(f, "body", _r(ACROSS, 0.08 * hop))
			_add(f, "neck_1", _r(ACROSS, 0.12 * w * sin(2.0 * ph)))
			_add(f, "head", _r(Vector3.RIGHT, 0.15 * sin(2.0 * ph) * w) * _r(ACROSS, 0.08 * w))
			for side in ["n", "f"]:
				var lift := maxf(0.0, sin(2.0 * ph + (0.0 if side == "n" else PI))) * w
				_add(f, "leg_%sf_upper" % side, _r(ACROSS, 0.5 * lift))
				_add(f, "leg_%sf_paw" % side, _r(ACROSS, -0.9 * lift))
			_wag(f, 6.0 * ph, 0.5 * w, 0.25 * w)
			_add(f, "ear_0", _r(Vector3.RIGHT, -0.15 * w))
			_add(f, "ear_1", _r(Vector3.RIGHT, 0.15 * w))
			closed = u >= 0.12 and u < 0.8
		"hunger":
			var look := _win(u, 0.0, 0.18, 0.42, 0.58)
			var sigh := _win(u, 0.5, 0.64, 0.8, 1.0)
			var inhale := _win(u, 0.36, 0.46, 0.5, 0.62)
			f["move"]["body"] = Vector3(0, 0.04 * inhale - 0.03 * sigh, 0)
			_add(f, "neck_1", _r(ACROSS, 0.18 * look - 0.15 * sigh))
			_add(f, "head", _r(ACROSS, 0.25 * look - 0.2 * sigh))
			_add(f, "ear_0", _r(Vector3.RIGHT, 0.15 * look - 0.3 * sigh))
			_add(f, "ear_1", _r(Vector3.RIGHT, -0.15 * look + 0.3 * sigh))
			for t in 4:                                              # the tail droops with the sigh
				_add(f, "tail_%d" % t, _r(ACROSS, 0.12 * sigh))
			closed = u >= 0.64 and u < 0.76
		"yawn":
			var up := _win(u, 0.05, 0.4, 0.62, 0.9)
			var sag := _win(u, 0.62, 0.8, 0.9, 1.0)
			f["move"]["body"] = Vector3(0, 0.04 * up - 0.03 * sag, 0)
			_add(f, "neck_1", _r(ACROSS, 0.16 * up - 0.08 * sag))
			_add(f, "head", _r(ACROSS, 0.32 * up - 0.1 * sag) * _r(Vector3.RIGHT, 0.06 * up))
			_jaw(f, -1.6 * _win(u, 0.12, 0.38, 0.6, 0.82))
			_add(f, "ear_0", _r(Vector3.RIGHT, -0.3 * up))
			_add(f, "ear_1", _r(Vector3.RIGHT, 0.3 * up))
			closed = u >= 0.22 and u < 0.82
		"liedown", "wake":
			var v := u if clip == "liedown" else 1.0 - u
			_lying(f, _ease((v - 0.0) / 0.4), _ease((v - 0.3) / 0.4), _ease((v - 0.6) / 0.4))
			closed = v >= 0.75
		"sleep":
			_lying(f, 1.0, 1.0, 1.0)
			f["move"]["body"] += Vector3(0, 0.012 * sin(ph), 0)
			_add(f, "neck_0", _r(ACROSS, 0.012 * sin(ph)))
			closed = true
		"turn", "turn_stand":
			var e := u * u * u * (u * (6.0 * u - 15.0) + 10.0)
			var mid := pow(sin(PI * u), 2.0)
			_add(f, "root", _r(Vector3.UP, -deg_to_rad(TURN_DEG) * e * sg))
			f["move"]["body"] = Vector3(0, 0.08 * mid, 0)
			_add(f, "head", _r(Vector3.UP, -sg * 0.15 * sin(TAU * u)))
			_wag(f, TAU * u, sg * 0.2)
	if clip != "idle":
		f["values"]["eyes_closed"] = 1.0 if closed else 0.0
	return f
