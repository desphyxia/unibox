class_name Creature
extends Touchable
## A creature in the meadow. The rendered idle loop plays all the time; walking, petting reactions and eating are
## stand-in motions (hops, squashes, tilts) until those animations are rendered.
## Touch: tap to pet, drag to walk it somewhere. main.gd also calls it to a tapped spot and hands it food.

signal petted
signal ate

## Points on the sitting fox, in render pixels of the 640-wide frames (facing right). The creature's origin is the
## anchor from anim.json: the same ground point in every animation, so idle and walk line up.
const FEET_R := Vector2(297, 517)
const MOUTH_R := Vector2(437, 222)
const HEAD_R := Vector2(387, 196)
const TOP_R := 61.0
const WALK_SPEED := 120.0
const GROUND := Rect2(120, 525, 784, 205)  ## where it may walk (world), inside the always-visible area

var temperament := "playful"
var base_scale := 0.5
var meadow: Node2D                     ## main.gd: effects layer, the tree, food on the ground

var body := Node2D.new()               ## lift and tilt, pivot at the feet
var squash := Node2D.new()             ## squash and stretch, times the depth scale
var flip := Node2D.new()               ## faces left or right
var sprite := AnimatedSprite2D.new()
var shadow := Sprite2D.new()

var lift := 0.0                        ## animated by tweens
var tilt := 0.0
var squash_v := Vector2.ONE
var facing := 1.0

var anims := {}                        ## name -> anim.json info
var _ref := Vector2.ZERO               ## from the anchor to the sitting fox's feet, frame pixels
var target = null                      ## Vector2 to walk to, or null
var speed_factor := 1.0
var busy := false                      ## reacting or eating: stands still
var food_target: Node2D = null         ## an apple on the ground it is walking to
var _hop := 0.0
var _walk_amount := 0.0
var _idle_for := 0.0
var _next_wander := 6.0
var _press_at := Vector2.ZERO
var _press_ms := 0
var _dragging := false
var _drag_offset := Vector2.ZERO
var _react_tween: Tween

# needs (variant A shows a hunger cue; variant B never does, food is simply there to offer)
var hungry := false
var _hunger_at := 60.0
var _next_cue := 0.0
var _age := 0.0


func setup(frames: SpriteFrames, infos: Dictionary, temper: String, world_scale: float) -> void:
	anims = infos
	temperament = temper
	base_scale = world_scale
	touch_priority = 20
	shadow.texture = Fx.glow_texture(Color(0.32, 0.24, 0.42, 0.34), 256)
	add_child(shadow)
	add_child(body)
	body.add_child(squash)
	squash.add_child(flip)
	flip.add_child(sprite)
	sprite.sprite_frames = frames
	sprite.centered = false
	var idle: Dictionary = anims["idle"]
	_ref = FEET_R - Vector2(idle["render_anchor"][0], idle["render_anchor"][1])
	_play("idle")
	sprite.frame = randi() % frames.get_frame_count("idle")
	_next_wander = _wander_gap()


func depth_scale() -> float:
	## a little bigger nearer the front of the meadow
	return base_scale * lerpf(0.86, 1.12, clampf(inverse_lerp(GROUND.position.y, GROUND.end.y, position.y), 0.0, 1.0))


func head_world() -> Vector2:
	var s := depth_scale()
	var d := HEAD_R - FEET_R + _ref
	return position + Vector2(d.x * facing, d.y) * s + Vector2(0, -lift)


func mouth_world() -> Vector2:
	var s := depth_scale()
	var d := MOUTH_R - FEET_R + _ref
	return position + Vector2(d.x * facing, d.y) * s + Vector2(0, -lift)


func top_world() -> Vector2:
	return position + Vector2(0, (TOP_R - FEET_R.y + _ref.y) * depth_scale() - lift)


func hit_test(p: Vector2) -> bool:
	var s := depth_scale()
	var c := position + Vector2((10 + _ref.x) * facing, -235 + _ref.y) * s
	var d := (p - c) / (Vector2(165, 250) * s)
	return d.length() <= 1.0


# ------------------------------------------------------------------ touch
func touch_begin(p: Vector2) -> void:
	_press_at = p
	_press_ms = Time.get_ticks_msec()
	_dragging = false
	_drag_offset = position - p


func touch_move(p: Vector2) -> void:
	if not _dragging and p.distance_to(_press_at) > 16:
		_dragging = true
		food_target = null
		Log.event("creature_walk", "drag")
	if _dragging:
		walk_to(p + _drag_offset, 1.7)


func touch_end(p: Vector2) -> void:
	if not _dragging and Time.get_ticks_msec() - _press_ms < 600:
		pet(p)
	_dragging = false


# ------------------------------------------------------------------ actions
func walk_to(p: Vector2, speed := 1.0) -> void:
	target = Vector2(clampf(p.x, GROUND.position.x, GROUND.end.x), clampf(p.y, GROUND.position.y, GROUND.end.y))
	speed_factor = speed
	_idle_for = 0.0


func call_to(p: Vector2) -> void:
	## the child tapped the meadow: it looks up, chirps and trots over
	food_target = null
	face_toward(p.x)
	Sfx.play("chirp", 1.1)
	walk_to(p, 1.25)
	Log.event("creature_walk", "call")


func face_toward(x: float) -> void:
	if absf(x - position.x) < 6:
		return
	var f := signf(x - position.x)
	if f == facing:
		return
	facing = f
	var t := create_tween()
	t.tween_property(flip, "scale:x", facing, 0.16).from(-facing * 0.2)


func pet(p: Vector2) -> void:
	Log.event("creature_tap", temperament)
	petted.emit()
	Fx.hearts(meadow.fx, head_world() + Vector2(0, -30), 1 if busy else 3, 36)
	if busy:
		Sfx.play("chirp", 1.2, 0.1, -4.0)
		return
	target = null
	busy = true
	if _react_tween:
		_react_tween.kill()
	var t := create_tween()
	_react_tween = t
	match temperament:
		"calm":
			Sfx.play("chirp", 0.82)
			t.tween_property(self, "squash_v", Vector2(1.06, 0.93), 0.35).set_trans(Tween.TRANS_SINE)
			t.parallel().tween_property(self, "tilt", -0.07 * facing, 0.35).set_trans(Tween.TRANS_SINE)
			t.tween_property(self, "squash_v", Vector2.ONE, 0.5).set_trans(Tween.TRANS_SINE)
			t.parallel().tween_property(self, "tilt", 0.0, 0.5).set_trans(Tween.TRANS_SINE)
		"curious":
			face_toward(p.x)
			Sfx.play("chirp2", 1.15)
			t.tween_property(self, "tilt", 0.16 * facing, 0.22).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
			t.parallel().tween_property(self, "lift", 10.0, 0.22)
			t.tween_interval(0.35)
			t.tween_property(self, "tilt", -0.08 * facing, 0.22).set_trans(Tween.TRANS_SINE)
			t.tween_property(self, "tilt", 0.0, 0.25).set_trans(Tween.TRANS_SINE)
			t.parallel().tween_property(self, "lift", 0.0, 0.25)
			t.tween_callback(func(): Fx.sparkles(meadow.fx, head_world(), 5, 50))
		_:  # playful: two happy hops
			Sfx.play("chirp2")
			for h in [42.0, 22.0]:
				t.tween_property(self, "squash_v", Vector2(1.14, 0.86), 0.07)
				t.tween_property(self, "squash_v", Vector2(0.9, 1.12), 0.08)
				t.parallel().tween_property(self, "lift", h, 0.17).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
				t.tween_property(self, "lift", 0.0, 0.15).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
				t.parallel().tween_property(self, "squash_v", Vector2(1.1, 0.9), 0.15)
			t.tween_property(self, "squash_v", Vector2.ONE, 0.14).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	t.tween_callback(func(): busy = false)


func wants_food_at(p: Vector2) -> bool:
	## a held apple let go over the creature, or right by its mouth
	return hit_test(p) or p.distance_to(mouth_world()) < 90.0


func fetch(apple: Node2D) -> void:
	## an apple dropped near it: walk over and eat it from the ground
	food_target = apple
	face_toward(apple.position.x)
	walk_to(apple.position + Vector2(-(MOUTH_R.x - FEET_R.x + _ref.x) * depth_scale() * signf(apple.position.x - position.x + 0.01), 6), 1.2)


func eat(apple: Node2D, how: String) -> void:
	food_target = null
	target = null
	busy = true
	if _react_tween:
		_react_tween.kill()
	face_toward(apple.world_pos().x if apple is Touchable else apple.position.x)
	apple.z_index = 70
	var t := create_tween()
	_react_tween = t
	t.tween_property(apple, "global_position", meadow.world.to_global(mouth_world()), 0.3).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	t.parallel().tween_property(apple, "scale", apple.scale * 0.7, 0.3)
	for i in 3:
		t.tween_callback(func(): Sfx.play("munch", 1.0 + i * 0.05))
		t.tween_property(self, "squash_v", Vector2(1.05, 0.95), 0.1)
		t.parallel().tween_property(apple, "scale", apple.scale * (0.55 - i * 0.17), 0.1)
		t.tween_property(self, "squash_v", Vector2.ONE, 0.12)
	t.tween_callback(func():
		apple.queue_free()
		Sfx.play("happy")
		Fx.sparkles(meadow.fx, position + Vector2(0, -200) * depth_scale(), 10, 120, Color(1, 0.95, 0.75))
		Fx.hearts(meadow.fx, head_world() + Vector2(0, -30), 2))
	t.tween_property(self, "lift", 18.0, 0.16).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	t.tween_property(self, "lift", 0.0, 0.14).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	t.tween_callback(func():
		busy = false
		hungry = false
		_hunger_at = _age + 150.0
		ate.emit())
	Log.event("food_given", how)


func hunger_cue() -> void:
	## variant A: it looks over at the apple tree and sighs; main.gd makes the apples glow
	busy = true
	face_toward(meadow.tree_position().x)
	var t := create_tween()
	t.tween_interval(0.25)
	t.tween_callback(func(): Sfx.play("sigh"))
	t.tween_property(self, "squash_v", Vector2(1.04, 0.94), 0.6).set_trans(Tween.TRANS_SINE)
	t.parallel().tween_property(self, "tilt", -0.05 * facing, 0.6).set_trans(Tween.TRANS_SINE)
	t.tween_property(self, "squash_v", Vector2.ONE, 0.8).set_trans(Tween.TRANS_SINE)
	t.parallel().tween_property(self, "tilt", 0.0, 0.8).set_trans(Tween.TRANS_SINE)
	t.tween_callback(func(): busy = false)
	meadow.hint_food()
	Log.event("need_cue", "hunger")


func appear(from: Vector2) -> void:
	## hatched: pops out of the egg, then hops clear of the nest
	position = from
	busy = true
	squash_v = Vector2(0.2, 0.2)
	var t := create_tween()
	t.tween_property(self, "squash_v", Vector2(1.1, 0.92), 0.35).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	t.tween_property(self, "squash_v", Vector2.ONE, 0.25)
	t.tween_callback(func(): Sfx.play("happy"))
	t.tween_interval(0.5)
	t.tween_callback(func():
		busy = false
		walk_to(from + Vector2(120, 50), 0.8))


var _still_for := 0.0


func _play(anim: String) -> void:
	## swap loops around the shared anchor; a small squash hides the change of pose
	var info: Dictionary = anims[anim]
	sprite.offset = -Vector2(info["anchor"][0], info["anchor"][1])
	sprite.speed_scale = 1.0
	sprite.play(anim)
	if anim == "idle" and not busy:
		var t := create_tween()
		t.tween_property(self, "squash_v", Vector2(1.05, 0.95), 0.07)
		t.tween_property(self, "squash_v", Vector2.ONE, 0.12)


func _wander_gap() -> float:
	match temperament:
		"calm":
			return randf_range(10.0, 16.0)
		"curious":
			return randf_range(5.0, 9.0)
	return randf_range(4.0, 8.0)


# ------------------------------------------------------------------ every frame
func _process(delta: float) -> void:
	_age += delta
	var moving := false
	if target != null and not busy:
		var d: Vector2 = target - position
		var step := WALK_SPEED * speed_factor * delta
		if d.length() <= step:
			position = target
			target = null
			_arrive()
		else:
			position += d.normalized() * step
			moving = true
			if absf(d.x) > 3:
				face_toward(position.x + d.x)
	var has_walk := anims.has("walk")
	if has_walk:
		if moving:
			_still_for = 0.0
			if sprite.animation != "walk":
				_play("walk")
			var w: Dictionary = anims["walk"]
			# cycles per second so a paw on the ground keeps pace with the meadow
			var v := WALK_SPEED * speed_factor
			sprite.speed_scale = clampf(w["stance"] * v / (w["stride"] * depth_scale()), 0.4, 3.0)
		else:
			_still_for += delta
			if sprite.animation == "walk" and _still_for > 0.12:
				_play("idle")
	_walk_amount = move_toward(_walk_amount, 1.0 if (moving and not has_walk) else 0.0, delta * 6.0)
	if moving and not has_walk:
		_hop += delta * 10.0 * clampf(speed_factor, 0.8, 1.6)
	var hop := absf(sin(_hop)) * 9.0 * _walk_amount
	var s := depth_scale()
	body.position.y = -(lift + hop)
	body.rotation = tilt + sin(_hop) * 0.045 * _walk_amount
	squash.scale = squash_v * s
	var info: Dictionary = anims[sprite.animation]
	shadow.scale = Vector2(info["shadow"][1], info["shadow"][1] * 0.17) / 256.0 * s * (1.0 - clampf((lift + hop) / 160.0, 0.0, 0.35))
	shadow.position = Vector2(info["shadow"][0] * facing, -4) * s
	# idle life: wander a little now and then
	if target == null and not busy and not _dragging:
		_idle_for += delta
		if _idle_for > _next_wander:
			_idle_for = 0.0
			_next_wander = _wander_gap()
			var p := position + Vector2(randf_range(-220, 220), randf_range(-60, 60))
			walk_to(p, 0.55 if temperament == "calm" else 0.75)
	# needs: only variant A shows a cue
	if Game.variant == "A" and not hungry and _age > _hunger_at:
		hungry = true
		_next_cue = _age
	if hungry and Game.variant == "A" and not busy and target == null and not _dragging and _age >= _next_cue:
		_next_cue = _age + 22.0
		hunger_cue()


func _arrive() -> void:
	if food_target and is_instance_valid(food_target):
		var apple := food_target
		food_target = null
		if absf(apple.position.x - mouth_world().x) < 90 and absf(apple.position.y - position.y) < 60:
			eat(apple, "ground")
			return
	var t := create_tween()
	t.tween_property(self, "squash_v", Vector2(1.05, 0.95), 0.08)
	t.tween_property(self, "squash_v", Vector2.ONE, 0.15)
