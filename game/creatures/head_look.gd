class_name HeadLook
extends SkeletonModifier3D
## Turns a creature's head toward something (a finger on the screen, an apple being carried), on top of whatever clip
## is playing: after the animation, it turns the head bone about its pivot, and the neck helpers by their share, so the
## neck follows the way it does in the clips. `amount` eases in and out; the turn is held within MAX_TURN.
## creature_model.gd adds it to the skeleton and sets `target` (in the creature's own space).

const MAX_TURN := deg_to_rad(38.0)
const EASE := 4.0                      ## how fast it starts and stops looking (per second)
const FOLLOW := 6.0                    ## how fast the head follows a moving target

var model: Node3D                      ## the CreatureModel: its pose weights and the head's pivots and forward
var target := Vector3.ZERO
var looking := false
var amount := 0.0
var _turn := Quaternion.IDENTITY       ## the turn last applied, eased toward the wanted one
var _head := -1
var _helpers := []                     ## [bone, pose index, +1 with the head or -1 against it]


func _ready() -> void:
	var sk := get_skeleton()
	_head = sk.find_bone("head")
	var poses: Array = model.get_meta("poses")
	for p in range(1, poses.size()):
		for way in [["more", 1.0], ["less", -1.0]]:
			var b := sk.find_bone("neck_%s_%s" % [poses[p], way[0]])
			if b >= 0:
				_helpers.append([b, p, way[1]])


func _process_modification_with_delta(delta: float) -> void:
	amount = move_toward(amount, 1.0 if looking else 0.0, delta * EASE)
	if amount < 0.001 or _head < 0:
		_turn = Quaternion.IDENTITY
		return
	var sk := get_skeleton()
	var g := sk.get_bone_global_pose(_head)
	var move := g * sk.get_bone_global_rest(_head).affine_inverse()   ## where the clip has carried the head
	var w: Vector4 = model.pose_weights()
	var pivots: Array = model.get_meta("pivots")
	var rest_pivot := Vector3.ZERO
	for i in 4:
		rest_pivot += (pivots[i] as Vector3) * w[i]
	var pivot := move * rest_pivot
	var forward := (move.basis * (model.get_meta("head_forward") as Vector3)).normalized()
	var want := (target - pivot).normalized()
	var q := Quaternion(forward, want) if forward.dot(want) > -0.99 else Quaternion.IDENTITY
	var angle := q.get_angle()
	if angle > MAX_TURN:
		q = Quaternion(q.get_axis().normalized(), MAX_TURN)
	_turn = _turn.slerp(q, clampf(delta * FOLLOW, 0.0, 1.0))
	var turn := Quaternion.IDENTITY.slerp(_turn, amount)
	var axis := turn.get_axis().normalized()
	var by := turn.get_angle()
	if by < 1e-5:
		return
	sk.set_bone_global_pose(_head, _about(pivot, Basis(axis, by)) * g)
	var gain: float = model.get_meta("neck_gain", 1.0)
	for h in _helpers:
		var k: float = w[h[1]] * gain * h[2]
		if absf(k) > 1e-4:
			sk.set_bone_global_pose(h[0], _about(pivot, Basis(axis, by * k)) * sk.get_bone_global_pose(h[0]))


static func _about(c: Vector3, b: Basis) -> Transform3D:
	return Transform3D(Basis(), c) * Transform3D(b, Vector3.ZERO) * Transform3D(Basis(), -c)
