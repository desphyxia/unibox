extends SceneTree
## Builds the fox the game draws (creatures/fox/fox.scn) from its Blender export (art/exports/fox_live.bin and .json,
## made by art/generators/fox_live_export.py), with tools/creature_builder.gd:
##   - bones: root, body, head, two ears, six along each of the three tails, hip, knee and paw for each leg (the paw
##     lifts so a folding leg never pushes it into the ground), three foxfires,
##     and neck helpers (how far a neck point turns with the head differs by pose: not at all sitting, about half
##     standing; for each other pose a helper turns with the head, and one against it, as much as that pose is showing);
##   - blend shapes: standing, lying like a sphinx, curled up asleep (the sitting fox is the rest shape), and breathing
##     (the sitting chest's breath, used awake, and the curled-up one, used asleep);
##   - every clip baked from the motion curves the Blender renders used (FoxRig, WalkRig, ReactRig in fox3d.py): idle,
##     walk, eat, happy, hunger, liedown, sleep, wake, yawn, and the half turns sitting and standing from either side;
##   - places on the fox (the top of the head, the ribbon round the neck and a tail near its tip, where things are worn;
##     the mouth; the head's middle), each with the bone that carries it and where it sits in every pose, and the
##     head's pivot in each pose and which way it faces, for looking at things;
##   - what the game needs to place it in the meadow: its shadow in each pose, its walk's stride, how far the mouth dips
##     to eat, how big it is to touch.
## Then it checks the skinned fox against those curves, vertex by vertex, and prints the largest gap per clip.
##   godot --headless --path . -s res://tools/build_fox.gd

const B := preload("res://tools/creature_builder.gd")
const OUT := "res://creatures/fox/fox.scn"
const FPS := 30.0
const TAIL_BONES := 6
const TURN_DEG := 100.0                ## the left-facing view is the fox turned this far
const POSES := ["sit", "stand", "down", "sleep"]
const SHAPES := ["stand", "down", "sleep", "breath", "breath_curled"]
const ACROSS := Vector3(0, 0, -1)      ## Blender's y axis: the legs swing about it
## seconds and looping, from the rendered clips' frames and the game's playback rates
const CLIPS := {
	"idle": [2.0, true], "walk": [1.0, true], "eat": [16.0 / 12.0, false], "happy": [16.0 / 14.0, false],
	"hunger": [20.0 / 12.0, false], "liedown": [20.0 / 12.0, false], "sleep": [16.0 / 12.0, true],
	"yawn": [20.0 / 12.0, false],
	"wake": [20.0 / 15.0, false], "turn_r": [13.0 / 22.0, false], "turn_l": [13.0 / 22.0, false],
	"turn_stand_r": [13.0 / 28.0, false], "turn_stand_l": [13.0 / 28.0, false],
}

var meta: Dictionary
var rig: Dictionary
var walk: Dictionary
var n := 0
var kind := PackedInt32Array()
var which := PackedInt32Array()
var tail_t := PackedFloat32Array()
var blink := PackedFloat32Array()
var glow := PackedFloat32Array()
var emit := PackedFloat32Array()
var surface := PackedFloat32Array()
var col := PackedColorArray()
var pos := []                          ## per pose: PackedVector3Array
var nrm := []
var comb := []
var br := []
var wh := []                           ## per pose: PackedFloat32Array (how much a neck point turns with the head)
var lift_l := PackedFloat32Array()
var droop_l := PackedFloat32Array()
var leg := PackedVector3Array()        ## leg, weight, place down the leg
var tris := {}
var bones := []
var bone := {}
var vw := []                           ## per vertex: {bone: weight}
const PAW_FROM := 0.8                  ## how far down a leg the paw bone takes over (fully by PAW_FULL)
const PAW_FULL := 0.92
const NECK_GAIN := 3.0                 ## the neck helpers turn this many times as far, with weights this many times smaller
var neck_gain := NECK_GAIN
var head_share := PackedFloat32Array() ## per vertex: how much of it turns with the head itself
var paws := []                         ## per leg: the vertices low on it, to keep above the ground while walking


func _initialize() -> void:
	_load()
	_make_bones()
	_make_weights()
	var table := _table()
	var skin_tris := PackedInt32Array()
	var fur_tris := PackedInt32Array()
	for cls in ["lit", "gloss", "emit"]:
		var t: PackedInt32Array = tris[cls]
		for k in range(0, t.size(), 3):
			var tri := [t[k], t[k + 1], t[k + 2]]
			if cls == "lit" and _furry(tri[0]) and _furry(tri[1]) and _furry(tri[2]):
				fur_tris.append_array(tri)
			else:
				skin_tris.append_array(tri)
	var skin_mesh := B.make_mesh(table, [skin_tris, tris["halo"]], SHAPES)
	var fur_mesh := B.make_mesh(table, [fur_tris], SHAPES)
	print("fox: %d vertices, %d bones; skin %d + glow %d triangles, fur %d triangles; neck helpers turn %.2f times" % [n,
		bones.size(), skin_tris.size() / 3, tris["halo"].size() / 3, fur_tris.size() / 3, neck_gain])
	var fires := []
	for f in 3:
		fires.append(bone["fire_%d" % f])
	var anims := []
	for c in CLIPS:
		anims.append(B.bake(c, CLIPS[c][0], FPS, CLIPS[c][1], bones, ["Skeleton3D/Skin", "Skeleton3D/Fur"],
			_frame.bind(c), fires))
	_check()
	var err := B.save_scene(OUT, "Fox", B.make_skeleton(bones), B.make_skin(bones), {"Skin": skin_mesh, "Fur": fur_mesh},
		anims, {"camera": meta["camera"], "ground": meta["ground"], "turn_deg": TURN_DEG, "poses": POSES,
			"pivots": _pivots(), "head_forward": _head_forward(), "neck_gain": neck_gain, "places": _wear_places(),
			"trait_mode": "hue", "kind": "fox",
			# render pixels (80 to a model unit): [x offset, width] facing right, then facing left
			"shadows": {"sit": [Vector2(-41, 282), Vector2(-31, 265)], "stand": [Vector2(-4, 201), Vector2(3, 243)],
				"sleep": [Vector2(30, 194), Vector2(-41, 251)]},
			"walk": {"stride": 88.0, "stance": 0.6}, "eat_drop": Vector2(-4, 44), "touch": Vector2(165, 250),
			"blanket": Vector3(60, 300, 100)})       # asleep, render pixels: from behind the head, back this far, this high
	print("saved %s (%s), %d KB" % [OUT, error_string(err), FileAccess.get_file_as_bytes(OUT).size() / 1024])
	quit()


# ------------------------------------------------------------------ the export
func _load() -> void:
	var base := ProjectSettings.globalize_path("res://").path_join("../art/exports/fox_live").simplify_path()
	meta = JSON.parse_string(FileAccess.get_file_as_string(base + ".json"))
	rig = meta["rig"]
	walk = rig["walk"]
	var blob := FileAccess.get_file_as_bytes(base + ".bin")
	var tx: Dictionary = meta["tex"]
	var tex := blob.slice(int(tx["offset"]), int(tx["offset"]) + int(tx["width"]) * int(tx["height"]) * 16).to_float32_array()
	var width := int(tx["width"])
	var row := int(tx["row"])
	var per := int(tx["per_vertex"])
	var texel := func(vid: int, k: int) -> Vector4:
		var i := ((vid / row) * width + (vid % row) * per + k) * 4
		return Vector4(tex[i], tex[i + 1], tex[i + 2], tex[i + 3])
	for p in 4:
		pos.append(PackedVector3Array())
		nrm.append(PackedVector3Array())
		comb.append(PackedVector3Array())
		br.append(PackedVector3Array())
		wh.append(PackedFloat32Array())
	for cls in ["lit", "gloss", "emit", "halo"]:
		var gi: Dictionary = meta["groups"][cls]
		var cnt: int = gi["verts"]
		var stride: int = gi["stride"]
		var v := blob.slice(gi["vert_offset"], gi["vert_offset"] + cnt * stride * 4).to_float32_array()
		var ind := blob.slice(gi["index_offset"], gi["index_offset"] + int(gi["tris"]) * 12).to_int32_array()
		var first := n
		for i in cnt:
			var o := i * stride
			col.append(Color(v[o + 6], v[o + 7], v[o + 8], v[o + 9]))
			kind.append(int(v[o + 10] + 0.5))
			tail_t.append(v[o + 11])
			which.append(int(v[o + 12] + 0.5))
			blink.append(v[o + 13])
			glow.append(v[o + 14])
			emit.append(v[o + 15])
			surface.append({"lit": 0.0, "gloss": 1.0, "emit": 2.0, "halo": 0.0}[cls])
			var vid := int(v[o + 16] + 0.5)
			for p in 4:
				var a: Vector4 = texel.call(vid, 4 * p)
				var b: Vector4 = texel.call(vid, 4 * p + 1)
				var c: Vector4 = texel.call(vid, 4 * p + 2)
				var d: Vector4 = texel.call(vid, 4 * p + 3)
				pos[p].append(Vector3(a.x, a.y, a.z))
				nrm[p].append(Vector3(b.x, b.y, b.z).normalized())
				comb[p].append(Vector3(c.x, c.y, c.z))
				br[p].append(Vector3(d.x, d.y, d.z))
				wh[p].append(d.w)
				if p == 0:
					lift_l.append(a.w)
					droop_l.append(b.w)
			var lg: Vector4 = texel.call(vid, 16)
			leg.append(Vector3(lg.x, lg.y, lg.z))
			n += 1
		var t := PackedInt32Array()
		for i in ind:
			t.append(i + first)
		tris[cls] = t


func _furry(i: int) -> bool:
	return col[i].a > 0.001 and kind[i] <= 3


static func _v(a) -> Vector3:
	return Vector3(a[0], a[1], a[2])


# ------------------------------------------------------------------ bones and weights
func _add(name: String, parent: String, at: Vector3) -> void:
	bone[name] = bones.size()
	bones.append({"name": name, "parent": bone[parent] if parent != "" else -1, "rest": Transform3D(Basis(), at)})


func _make_bones() -> void:
	var sit: Dictionary = rig["sit"]
	for li in 4:
		var low := PackedInt32Array()
		for i in n:
			if kind[i] == 0 and int(leg[i].x + 0.5) == li and leg[i].y > 0.5 and leg[i].z > PAW_FROM:
				low.append(i)
		paws.append(low)
	_add("root", "", Vector3.ZERO)
	_add("body", "root", Vector3.ZERO)
	_add("head", "body", _v(sit["pivot"]))
	for p in POSES.slice(1):
		for way in ["more", "less"]:
			_add("neck_%s_%s" % [p, way], "body", _v(sit["pivot"]))
	for e in 2:
		_add("ear_%d" % e, "head", _v(sit["ears"][e]["base"]))
	for ti in 3:
		# joints along the tail: the sitting tail's points at that place, averaged
		for k in TAIL_BONES:
			var tk := float(k) / (TAIL_BONES - 1)
			var sum := Vector3.ZERO
			var cnt := 0
			for i in n:
				if kind[i] == 3 and which[i] == ti and absf(tail_t[i] - tk) < 0.6 / (TAIL_BONES - 1):
					sum += pos[0][i]
					cnt += 1
			var at := sum / cnt if cnt > 0 else _v(sit["tails"][ti]["root"])
			_add("tail_%d_%d" % [ti, k], "body" if k == 0 else "tail_%d_%d" % [ti, k - 1], at)
	for li in 4:
		_add("leg_%d_hip" % li, "body", _v(walk["legs"][li]["pivot"]))
		_add("leg_%d_knee" % li, "leg_%d_hip" % li, _v(walk["legs"][li]["knee"]))
		var paw := Vector3.ZERO
		for i in paws[li]:
			paw += pos[1][i]
		_add("leg_%d_paw" % li, "leg_%d_knee" % li, paw / maxi(paws[li].size(), 1))
	for f in 3:
		_add("fire_%d" % f, "root", _v(sit["fires"][f]))


func _make_weights() -> void:
	for i in n:
		# the head itself takes a share as near the sitting pose's as fits (sitting is where the head moves most); the
		# helpers carry how each other pose differs from it, turning with the head or against it
		var best := 0.0
		var best_gap := INF
		for k in 101:
			var a := k / 100.0
			var need := a + (absf(wh[1][i] - a) + absf(wh[2][i] - a) + absf(wh[3][i] - a)) / NECK_GAIN
			if need <= 1.0 + 1e-6 and absf(a - wh[0][i]) < best_gap:
				best_gap = absf(a - wh[0][i])
				best = a
		head_share.append(best)
	for i in n:
		var w := {}
		match kind[i]:
			0:
				var lw := leg[i].y
				var rest := 1.0
				if lw > 1e-4:
					var li := int(leg[i].x + 0.5)
					var kt: float = walk["legs"][li]["kt"]
					var k := smoothstep(kt - 0.08, kt + 0.08, leg[i].z)
					var pw := smoothstep(PAW_FROM, PAW_FULL, leg[i].z)
					w[bone["leg_%d_hip" % li]] = lw * (1.0 - k)
					w[bone["leg_%d_knee" % li]] = lw * k * (1.0 - pw)
					w[bone["leg_%d_paw" % li]] = lw * k * pw
					rest = 1.0 - lw
				var c: float = head_share[i]
				var h := c
				w[bone["head"]] = rest * c
				for p in range(1, 4):
					var d: float = wh[p][i] - c
					if absf(d) > 1e-4:
						w[bone["neck_%s_%s" % [POSES[p], "more" if d > 0.0 else "less"]]] = rest * absf(d) / neck_gain
						h += absf(d) / neck_gain
				w[bone["body"]] = rest * (1.0 - h)
			1:
				w[bone["head"]] = 1.0
			2:
				w[bone["ear_%d" % which[i]]] = 1.0
			3:
				var s := clampf(tail_t[i], 0.0, 1.0) * (TAIL_BONES - 1)
				var k0 := mini(int(s), TAIL_BONES - 2)
				var f := s - k0
				w[bone["tail_%d_%d" % [which[i], k0]]] = 1.0 - f
				w[bone["tail_%d_%d" % [which[i], k0 + 1]]] = f
			_:
				w[bone["fire_%d" % which[i]]] = 1.0
		vw.append(w)


func _table() -> Dictionary:
	var packed := B.pack_weights(vw)
	var c0 := PackedFloat32Array()
	var c1 := PackedFloat32Array()
	var c2 := PackedFloat32Array()
	var c3 := PackedFloat32Array()
	for i in n:
		# the fur's direction: its part along the normal and its part along the surface (the tangent's direction)
		var out: float = comb[0][i].dot(nrm[0][i])
		var along: float = (comb[0][i] - nrm[0][i] * out).length()
		c0.append_array([lift_l[i], droop_l[i], out, blink[i]])
		c1.append_array([glow[i], emit[i], surface[i], along])
		c2.append_array([pos[0][i].x, pos[0][i].y, pos[0][i].z, 0.0])
		c3.append_array([-1.0, 0.0, 0.0, 0.0])             # traits by hue (the apricot coat, the pink-violet glow)
	var shapes := {}
	for p in range(1, 4):
		shapes[POSES[p]] = {"pos": pos[p], "nrm": nrm[p], "tan": comb[p]}
	for b in [["breath", 0], ["breath_curled", 3]]:
		# breathing: the chest's push, sitting (for every pose awake) and curled up (only the body breathes)
		var bp := PackedVector3Array()
		for i in n:
			bp.append(pos[0][i] + (br[b[1]][i] if kind[i] == 0 else Vector3.ZERO))
		shapes[b[0]] = {"pos": bp, "nrm": nrm[0], "tan": comb[0]}
	return {"pos": pos[0], "nrm": nrm[0], "tan": comb[0], "col": col, "c0": c0, "c1": c1, "c2": c2, "c3": c3,
		"bones": packed[0], "weights": packed[1], "shapes": shapes}


# ------------------------------------------------------------------ the motion curves (ReactRig, WalkRig, FoxRig)
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


func _params(clip: String, u: float, sg: float) -> Dictionary:
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
		"yawn":
			# a big slow breath in with the head tipping back, ears back and eyes shut, then a sleepy sag
			var up := _win(u, 0.05, 0.4, 0.62, 0.9)
			var sag := _win(u, 0.62, 0.8, 0.9, 1.0)
			p.merge({"pitch": d.call(-20) * up + d.call(6) * sag, "roll": d.call(4) * up, "ear": d.call(-14) * up,
				"breath": 0.06 * up - 0.03 * sag, "closed": u >= 0.22 and u < 0.82, "sway": 1.0 - 0.6 * up}, true)
		"liedown", "wake":
			var v := u if clip == "liedown" else 1.0 - u
			p.merge({"pitch": d.call(7) * _win(v, 0.0, 0.12, 0.24, 0.4), "ear": d.call(-10) * _win(v, 0.1, 0.4, 0.72, 1.0),
				"sway": 1.0 - 0.7 * _ss(0.0, 1.0, v), "closed": v >= 0.62}, true)
		"turn", "turn_stand":
			var e := u * u * u * (u * (6.0 * u - 15.0) + 10.0)
			var mid := pow(sin(PI * u), 2.0)
			p.merge({"turn": -d.call(TURN_DEG) * e * sg, "lift": 0.12 * mid, "yaw": -sg * d.call(9) * sin(TAU * u),
				"tail_turn": sg * d.call(12) * sin(TAU * u), "ear": d.call(6) * mid, "sway": 1.0 - mid}, true)
	return p


func _pose_weights(clip: String, u: float) -> Vector4:
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


func _blend(w: Vector4, f: Callable) -> Vector3:
	var out := Vector3.ZERO
	for i in 4:
		if w[i] > 0.0:
			out += f.call(rig[POSES[i]]) * w[i]
	return out


func _split(name: String) -> Array:
	## a baked clip's name -> [the motion's name, which way the fox faces as it starts]
	if name.begins_with("turn"):
		return [name.trim_suffix("_r").trim_suffix("_l"), 1.0 if name.ends_with("_r") else -1.0]
	return [name, 1.0]


func _eval(name: String, tm: float) -> Dictionary:
	## every value the motion has at this moment (as the earlier shader rig worked them out each frame)
	var cf := _split(name)
	var clip: String = cf[0]
	var sg: float = cf[1]
	var dur: float = CLIPS[name][0]
	var u := clampf(tm / dur, 0.0, 1.0)
	var c := _params(clip, u, sg)
	var w := _pose_weights(clip, u)
	var ph := 0.0
	match clip:
		"idle":
			ph = TAU * fmod(tm, 2.0) / 2.0
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
		ear0 = deg_to_rad(14.0) * exp(-pow((fmod(tm, 2.0) / 2.0 * 24.0 - 6.0) / 1.2, 2.0))
		ear1 = deg_to_rad(2.5) * sin(ph + 2.0)
	if clip == "walk":
		bob = 0.045 * cos(2.0 * TAU * u)
		lift = bob
		sway = Basis(Vector3.UP, deg_to_rad(1.5) * sin(ph)) * Basis(Vector3.RIGHT, deg_to_rad(1.2) * sin(ph + 0.6)) \
			* Basis(Vector3(0, 0, -1), deg_to_rad(2.2) * sin(2.0 * ph + 0.9))
		ear0 = 0.0
	var th := Vector4.ZERO
	var be := Vector4.ZERO
	if clip == "walk":
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
	var r := {"u": u, "w": w, "lift": lift, "bob": bob, "hb": head * sway, "turn": float(c["turn"]),
		"breath": 0.028 * sin(ph) * k + float(c["breath"]), "closed": c["closed"], "th": th, "be": be,
		"pivot": _blend(w, func(x): return _v(x["pivot"])), "phase": ph, "wag": c["wag"], "wag_cycles": c["wag_cycles"],
		"tail_turn": c["tail_turn"], "ear_a": [ear0, ear1], "walking": clip == "walk"}
	r["ear_b"] = []
	r["ear_ax"] = []
	for e in 2:
		r["ear_b"].append(_blend(w, func(x): return _v(x["ears"][e]["base"])))
		r["ear_ax"].append(_blend(w, func(x): return _v(x["ears"][e]["axis"])).normalized())
	r["tail_root"] = []
	r["tail_amp"] = []
	for ti in 3:
		r["tail_root"].append(_blend(w, func(x): return _v(x["tails"][ti]["root"])))
		r["tail_amp"].append(float(rig["sit"]["tails"][ti]["amp"]) * k)
	r["fire_b"] = []
	r["fire_m"] = []
	for f in 3:
		r["fire_b"].append(_blend(w, func(x): return _v(x["fires"][f]) if f < x["fires"].size() else _v(rig["sit"]["fires"][f])))
		r["fire_m"].append(Vector4(0.05 * sin(ph * 2.0 + 1.7 * f), 0.09 * sin(ph + 2.1 * f), 0.0, 1.0 + 0.06 * sin(3.0 * ph + f)))
	return r


static func _about(c: Vector3, b: Basis) -> Transform3D:
	return Transform3D(Basis(), c) * Transform3D(b, Vector3.ZERO) * Transform3D(Basis(), -c)


func _tail_angle(r: Dictionary, ti: int, t: float) -> float:
	var fi := float(ti)
	return r["tail_amp"][ti] * sin(r["phase"] + 1.3 * fi - 2.4 * t) * pow(t, 1.3) \
		+ r["wag"] * sin(TAU * r["wag_cycles"] * r["u"] + 1.1 * fi - 2.0 * t) * pow(t, 1.2) + r["tail_turn"] * pow(t, 1.5)


func _moves(r: Dictionary) -> Array:
	## where each bone carries the vertices from their posed (blend-shaped) place
	var turn := Transform3D(Basis(Vector3.UP, r["turn"]), Vector3.ZERO)
	var up := Transform3D(Basis(), Vector3(0, r["lift"], 0))
	var base := turn * up
	var hm := _about(r["pivot"], r["hb"])
	var m := []
	m.resize(bones.size())
	m[bone["root"]] = base
	m[bone["body"]] = base
	m[bone["head"]] = base * hm
	var hq: Quaternion = (r["hb"] as Basis).get_rotation_quaternion()
	var w: Vector4 = r["w"]
	for p in range(1, 4):
		for way in [1.0, -1.0]:
			var turn_by: float = hq.get_angle() * w[p] * neck_gain * way
			var nb := Basis(hq.get_axis().normalized(), turn_by) if absf(turn_by) > 1e-7 else Basis()
			m[bone["neck_%s_%s" % [POSES[p], "more" if way > 0.0 else "less"]]] = base * _about(r["pivot"], nb)
	for e in 2:
		m[bone["ear_%d" % e]] = base * hm * _about(r["ear_b"][e], Basis(r["ear_ax"][e], -r["ear_a"][e]))
	for ti in 3:
		for k in TAIL_BONES:
			var tk := float(k) / (TAIL_BONES - 1)
			m[bone["tail_%d_%d" % [ti, k]]] = base * _about(r["tail_root"][ti], Basis(Vector3.UP, _tail_angle(r, ti, tk)))
	for li in 4:
		var hip := base
		var knee := base
		var paw := base
		if r["walking"]:
			var pv := _v(walk["legs"][li]["pivot"])
			var r1 := _about(pv, Basis(ACROSS, r["th"][li]))
			var kn: Vector3 = r1 * _v(walk["legs"][li]["knee"])
			var r2 := _about(kn, Basis(ACROSS, r["be"][li])) * r1
			# the walk's bob lifts the body; the legs give it back so the paws stay on the ground
			hip = turn * Transform3D(Basis(), Vector3(0, -r["bob"] * 0.3, 0)) * r1 * up
			knee = turn * Transform3D(Basis(), Vector3(0, -r["bob"] * 0.75, 0)) * r2 * up
			# a folding leg never pushes a paw into the ground: lift the lower leg by the deepest dip
			var ground: float = walk["ground"][1]
			var dip := 0.0
			for i in paws[li]:
				var v: Vector3 = pos[1][i]
				var y := (Transform3D(Basis(), Vector3(0, -r["bob"] * 0.75, 0)) * r2 * up * v).y
				dip = maxf(dip, minf(v.y + r["lift"], ground) - y)
			paw = turn * Transform3D(Basis(), Vector3(0, dip, 0)) * Transform3D(Basis(), Vector3(0, -r["bob"] * 0.75, 0)) * r2 * up
		m[bone["leg_%d_hip" % li]] = hip
		m[bone["leg_%d_knee" % li]] = knee
		m[bone["leg_%d_paw" % li]] = paw
	for f in 3:
		var b: Vector3 = r["fire_b"][f]
		var fm: Vector4 = r["fire_m"][f]
		var s := fm.w
		m[bone["fire_%d" % f]] = base * Transform3D(Basis(), b + Vector3(fm.x, fm.y, fm.z)) \
			* Transform3D(Basis.from_scale(Vector3(s, 1.0 + (s - 1.0) * 1.6, s)), Vector3.ZERO) * Transform3D(Basis(), -b)
	return m


func _frame(tm: float, name: String) -> Dictionary:
	var r := _eval(name, tm)
	var w: Vector4 = r["w"]
	var f := {"move": _moves(r), "shapes": {"stand": w.y, "down": w.z, "sleep": w.w}}
	f["shapes"]["breath"] = r["breath"] * (w.x + w.y + w.z)
	f["shapes"]["breath_curled"] = r["breath"] * w.w
	if _split(name)[0] != "idle":      # the idle blinks are left to the game, at random
		f["values"] = {"eyes_closed": 1.0 if r["closed"] else 0.0}
	return f


# ------------------------------------------------------------------ looking and wearing
func _pivots() -> Array:
	var out := []
	for p in POSES:
		out.append(_v(rig[p]["pivot"]))
	return out


func _pick(test: Callable) -> PackedInt32Array:
	var out := PackedInt32Array()
	for i in n:
		if test.call(i):
			out.append(i)
	return out


func _most(idx: PackedInt32Array, key: Callable, count: int) -> PackedInt32Array:
	## the `count` points of idx with the biggest key (sitting)
	var arr := Array(idx)
	arr.sort_custom(func(a, b): return key.call(pos[0][a]) > key.call(pos[0][b]))
	return PackedInt32Array(arr.slice(0, count))


func _centroid(p: int, idx: PackedInt32Array) -> Vector3:
	var c := Vector3.ZERO
	for i in idx:
		c += pos[p][i]
	return c / maxi(idx.size(), 1)


static func _frame3(a: Vector3, b: Vector3, c: Vector3) -> Basis:
	## a frame from three points: x along a to b, y toward c across it
	var x := (b - a).normalized()
	var y := c - a
	y = (y - x * y.dot(x)).normalized()
	return Basis(x, y, x.cross(y))


func _follow(groups: Array, at_sit: Transform3D) -> Array:
	## a place in every pose, moving with three groups of points as if they were one rigid piece
	var f := []
	for p in 4:
		var c := [_centroid(p, groups[0]), _centroid(p, groups[1]), _centroid(p, groups[2])]
		f.append(Transform3D(_frame3(c[0], c[1], c[2]), c[0]))
	var out := []
	for p in 4:
		out.append((f[p] as Transform3D) * (f[0] as Transform3D).affine_inverse() * at_sit)
	return out


func _head_forward() -> Vector3:
	var head := _pick(func(i): return kind[i] == 1)
	return (_centroid(0, _most(head, func(v): return v.x, 40)) - _v(rig["sit"]["pivot"])).normalized()


func _wear_places() -> Dictionary:
	# the head is rigid in every pose: its snout, its crown and one cheek carry the place on top of the head
	var head := _pick(func(i): return kind[i] == 1)
	var snout := _most(head, func(v): return v.x, 40)
	var crown := _most(head, func(v): return v.y, 40)
	var cheek := _most(head, func(v): return v.z, 40)
	var top := _centroid(0, crown)
	var skull := _pick(func(i): return kind[i] == 1 and pos[0][i].y > top.y - 0.45)
	var half := 0.0
	for i in skull:
		half = maxf(half, absf(pos[0][i].z - top.z))
	# the ribbon round the neck: pink points near the neck, in three groups round the ring
	var piv := _v(rig["sit"]["pivot"])
	var ribbon := _pick(func(i): return kind[i] == 0 and surface[i] == 0.0 and col[i].r > 0.85 and col[i].g < 0.45 		and col[i].b > 0.35 and pos[0][i].distance_to(piv + Vector3(0, -0.5, 0)) < 0.9)
	# its middle: the middle of its box (the bow at the back holds most of the points, so not their average)
	var lo := Vector3.INF
	var hi := -Vector3.INF
	for i in ribbon:
		lo = lo.min(pos[0][i])
		hi = hi.max(pos[0][i])
	var rc := (lo + hi) / 2.0
	var sectors := [PackedInt32Array(), PackedInt32Array(), PackedInt32Array()]
	for i in ribbon:
		var d: Vector3 = pos[0][i] - rc
		sectors[int(fposmod(atan2(d.z, d.x) / TAU * 3.0, 3.0))].append(i)
	var ring := _frame3(_centroid(0, sectors[0]), _centroid(0, sectors[1]), _centroid(0, sectors[2]))
	var up := ring.z if ring.z.y > 0.0 else -ring.z
	var fwd := (Vector3.RIGHT - up * up.x).normalized()
	var neck_r := ((hi.x - lo.x) + (hi.z - lo.z)) / 4.0
	# a tail near its tip: the first tail's points from 0.74 to 0.9 along it
	var near := _pick(func(i): return kind[i] == 3 and which[i] == 0 and tail_t[i] > 0.74 and tail_t[i] < 0.78)
	var far := _pick(func(i): return kind[i] == 3 and which[i] == 0 and tail_t[i] > 0.86 and tail_t[i] < 0.9)
	var both := near.duplicate()
	both.append_array(far)
	var upper := _most(both, func(v): return v.y, maxi(both.size() / 4, 3))
	var mid := _pick(func(i): return kind[i] == 3 and which[i] == 0 and tail_t[i] > 0.78 and tail_t[i] < 0.86)
	var tc := _centroid(0, mid)
	var along := (_centroid(0, far) - _centroid(0, near)).normalized()
	var tail_r := 0.0
	for i in mid:
		var d: Vector3 = pos[0][i] - tc
		tail_r += (d - along * d.dot(along)).length()
	tail_r /= maxi(mid.size(), 1)
	var t_up := (Vector3.UP - along * along.y).normalized()
	# the mouth: the lower half of the snout's front
	var front := _most(head, func(v): return v.x, 120)
	var mid_y := _centroid(0, front).y
	var mouth := PackedInt32Array()
	for i in front:
		if pos[0][i].y < mid_y:
			mouth.append(i)
	var mouth_at := _centroid(0, mouth)
	var middle := []
	for p in 4:
		middle.append(Transform3D(Basis(), _v(rig[POSES[p]]["pivot"])))
	return {
		"mouth": {"bone": "head", "size": 0.1, "poses": _follow([snout, crown, cheek], Transform3D(Basis(), mouth_at))},
		"middle": {"bone": "head", "size": 1.0, "poses": middle},
		"head": {"bone": "head", "size": half, "poses": _follow([snout, crown, cheek], Transform3D(Basis(), top + Vector3(0, -0.05, 0)))},
		"neck": {"bone": "body", "size": neck_r, "poses": _follow(sectors, Transform3D(Basis(fwd, up, fwd.cross(up)), rc))},
		"tail": {"bone": "tail_0_4", "size": tail_r, "poses": _follow([near, far, upper],
			Transform3D(Basis(along, t_up, along.cross(t_up)), tc + t_up * tail_r * 0.8))},
	}


# ------------------------------------------------------------------ the check
func _old(i: int, v: Vector3, r: Dictionary) -> Vector3:
	## where the earlier shader rig (before the skeleton) put this vertex, from its posed place v
	var up := Vector3(0, r["lift"], 0)
	var hm := _about(r["pivot"], r["hb"])
	var w: Vector4 = r["w"]
	var out := v
	match kind[i]:
		0:
			var h := 0.0
			for p in 4:
				h += wh[p][i] * w[p]
			var q := v.lerp(hm * v, h) + up
			out = q
			var lw: float = leg[i].y if r["walking"] else 0.0
			if lw > 1e-4:
				var li := int(leg[i].x + 0.5)
				var pv := _v(walk["legs"][li]["pivot"])
				var r1 := _about(pv, Basis(ACROSS, r["th"][li]))
				var q1 := r1 * q
				var kn: Vector3 = r1 * _v(walk["legs"][li]["knee"])
				var q2 := _about(kn, Basis(ACROSS, r["be"][li])) * q1
				var kt: float = walk["legs"][li]["kt"]
				q1 = q1.lerp(q2, smoothstep(kt - 0.08, kt + 0.08, leg[i].z))
				out = q + (q1 - q) * lw - Vector3(0, r["bob"], 0) * (lw * leg[i].z)
				out.y = maxf(out.y, minf(q.y, float(walk["ground"][1])))
		1:
			out = hm * v + up
		2:
			var e := which[i]
			out = hm * _about(r["ear_b"][e], Basis(r["ear_ax"][e], -r["ear_a"][e])) * v + up
		3:
			out = _about(r["tail_root"][which[i]], Basis(Vector3.UP, _tail_angle(r, which[i], tail_t[i]))) * v + up
		_:
			var b: Vector3 = r["fire_b"][which[i]]
			var fm: Vector4 = r["fire_m"][which[i]]
			out = (v - b) * Vector3(fm.w, 1.0 + (fm.w - 1.0) * 1.6, fm.w) + b + Vector3(fm.x, fm.y, fm.z) + up
	return Basis(Vector3.UP, r["turn"]) * out


func _check() -> void:
	## the skinned fox (blend shapes, then bones) against the curves, at five moments of every clip
	for name in CLIPS:
		var worst := 0.0
		var worst_kind := -1
		var total := 0.0
		var count := 0
		for s in 5:
			var tm: float = CLIPS[name][0] * s / 4.0
			var r := _eval(name, tm)
			var mv := _moves(r)
			var w: Vector4 = r["w"]
			for i in n:
				var v: Vector3 = pos[0][i] * w.x + pos[1][i] * w.y + pos[2][i] * w.z + pos[3][i] * w.w
				if kind[i] == 0:
					v += (br[0][i] * w.x + br[1][i] * w.y + br[2][i] * w.z + br[3][i] * w.w) * r["breath"]
				var skinned := Vector3.ZERO
				for b in vw[i]:
					skinned += (mv[b] as Transform3D) * v * vw[i][b]
				var gap := skinned.distance_to(_old(i, v, r))
				total += gap
				count += 1
				if gap > worst:
					worst = gap
					worst_kind = kind[i]
		print("check %-13s largest gap %.4f (part %d), average %.5f model units (1 unit = 40 screen pixels)" % [name, worst,
			worst_kind, total / count])
