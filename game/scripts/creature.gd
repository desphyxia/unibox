class_name Creature
extends Touchable
## A creature in the meadow, played from rendered animations: an idle loop when sitting, a walk cycle when moving, and
## one-shot clips for eating, being petted (happy), the hunger cue, dozing off, sleeping and turning round. Every
## animation is rendered facing each way ("eat" and "eat_left"); the turns run the whole way round, from one side's rest
## pose to the other's ("turn_sit" from the right, "turn_sit_left" from the left). Without left frames it mirrors.
## Touch: tap to pet, drag to walk it somewhere. main.gd also calls it to a tapped spot and hands it food.

signal petted
signal ate
signal clip_finished

## Points on the sitting fox, in render pixels of the 640-wide frames (facing right). The creature's origin is the
## anchor from anim.json: the same ground point in every animation, so the clips line up.
const FEET_R := Vector2(297, 517)
const MOUTH_R := Vector2(437, 222)
const EAT_DROP := Vector2(-4, 44)          ## how far the mouth moves when the head dips to eat, render pixels
const HEAD_R := Vector2(387, 196)
const TOP_R := 61.0
const WALK_SPEED := 120.0
const GROUND := Rect2(120, 525, 784, 205)  ## where it may walk (world), inside the always-visible area
const LOOPS := ["idle", "walk", "sleep"]

var temperament := "playful"
var base_scale := 0.5
var meadow: Node2D                     ## main.gd: effects layer, the tree, island time, food on the ground

var body := Node2D.new()               ## lift and tilt, pivot at the feet
var squash := Node2D.new()             ## squash and stretch, times the depth scale
var flip := Node2D.new()               ## mirrors the right-facing frames, only when there are no left ones
var sprite := AnimatedSprite2D.new()
var ghost := Sprite2D.new()            ## the previous frame, fading out: softens the change into and out of sleep
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
var turning := false
var asleep := false
var food_target: Node2D = null         ## an apple on the ground it is walking to
var _clip := {}                        ## the one-shot clip playing: anim, seq (frame numbers), i, t, fps, events, face
var _hop := 0.0
var _walk_amount := 0.0
var _idle_for := 0.0
var _next_wander := 6.0
var _press_at := Vector2.ZERO
var _press_ms := 0
var _dragging := false
var _drag_offset := Vector2.ZERO
var _react_tween: Tween
var _still_for := 0.0
var _stay_awake_until := 0.0

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
	squash.add_child(ghost)
	ghost.centered = false
	ghost.visible = false
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


func _at(r: Vector2) -> Vector2:
	## a point on the sitting fox (render pixels) in the meadow, for the way it faces now
	var d := r - FEET_R + _ref
	return position + Vector2(d.x * facing, d.y) * depth_scale() + Vector2(0, -lift)


func head_world() -> Vector2:
	return _at(HEAD_R)


func mouth_world() -> Vector2:
	return _at(MOUTH_R)


func top_world() -> Vector2:
	## curled up asleep the head is much lower; while lying down or getting up the tag follows it down or up
	var curled := 0.0
	if asleep and _base() == "sleep":
		curled = 190.0
	elif _base() == "liedown":
		curled = 190.0 * smoothstep(0.0, 1.0, float(sprite.frame) / maxf(1.0, sprite.sprite_frames.get_frame_count(sprite.animation) - 1))
	return position + Vector2(0, (TOP_R + curled - FEET_R.y + _ref.y) * depth_scale() - lift)


func hit_test(p: Vector2) -> bool:
	var s := depth_scale()
	var c := position + Vector2((10 + _ref.x) * facing, -235 + _ref.y) * s
	if asleep:
		c = position + Vector2((40 + _ref.x) * facing, -110 + _ref.y) * s
	var d := (p - c) / (Vector2(165, 250 if not asleep else 140) * s)
	return d.length() <= 1.0


# ------------------------------------------------------------------ touch
func touch_begin(p: Vector2) -> void:
	_press_at = p
	_press_ms = Time.get_ticks_msec()
	_dragging = false
	_drag_offset = position - p


func touch_move(p: Vector2) -> void:
	if asleep or busy:
		return
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


# ------------------------------------------------------------------ clips
func _has(anim: String) -> bool:
	return anims.has(anim)


func _side(anim: String) -> String:
	## the frames for the way it faces now
	if facing < 0 and anims.has(anim + "_left"):
		return anim + "_left"
	return anim


func _base() -> String:
	## the animation playing, whichever way it faces
	return String(sprite.animation).trim_suffix("_left")


func _place_frames(name: String) -> void:
	var info: Dictionary = anims[name]
	sprite.offset = -Vector2(info["anchor"][0], info["anchor"][1])
	flip.scale.x = -1.0 if facing < 0 and not name.ends_with("_left") else 1.0


func _begin(anim: String, seq: Array, fps: float, events := {}, face := 0.0) -> void:
	## anim is the exact frames to play (already "_left" or not); face, if set, is the way it faces once the clip ends
	sprite.stop()
	sprite.animation = anim
	_place_frames(anim)
	sprite.frame = seq[0]
	_clip = {"anim": anim, "seq": seq, "i": 0, "t": 0.0, "fps": fps, "events": events, "face": face}
	if events.has(0):
		events[0].call()


func play_clip(anim: String, fps := 12.0, reverse := false, events := {}) -> void:
	## plays a one-shot clip and waits for it; events are {frame index: Callable}
	var name := _side(anim)
	var seq := range(sprite.sprite_frames.get_frame_count(name))
	if reverse:
		seq.reverse()
	_begin(name, seq, fps, events)
	await clip_finished


func _step_clip(delta: float) -> void:
	_clip["t"] += delta * _clip["fps"]
	while not _clip.is_empty() and _clip["t"] >= 1.0:
		_clip["t"] -= 1.0
		_clip["i"] += 1
		var seq: Array = _clip["seq"]
		if _clip["i"] >= seq.size():
			var face: float = _clip["face"]
			_clip = {}
			if face != 0.0:
				facing = face
			clip_finished.emit()
			# nothing chained another clip: back to the right loop
			if _clip.is_empty() and (face != 0.0 or not LOOPS.has(_base())):
				_play("sleep" if asleep else ("walk" if target != null and not busy else "idle"), true)
			return
		sprite.frame = seq[_clip["i"]]
		var ev: Dictionary = _clip["events"]
		if ev.has(_clip["i"]):
			ev[_clip["i"]].call()


func _fade_out_current(time := 0.18) -> void:
	## leave the frame on screen as it is and fade it away over what comes next
	ghost.texture = sprite.sprite_frames.get_frame_texture(sprite.animation, sprite.frame)
	ghost.offset = sprite.offset
	ghost.scale = Vector2(flip.scale.x, 1)
	ghost.modulate.a = 1.0
	ghost.visible = true
	var t := create_tween()
	t.tween_property(ghost, "modulate:a", 0.0, time)
	t.tween_callback(func(): ghost.visible = false)


func turn_to(f: float) -> void:
	## turn round on the spot, through facing the camera: a rendered clip from this side's rest pose to the other side's
	if f == facing or turning:
		return
	var standing := _base() == "walk"
	var anim := ("turn_stand" if standing else "turn_sit") + ("" if facing > 0 else "_left")
	if not _has(anim) or (f < 0 and not _has("idle_left")):
		# no turn rendered for this side: flip over quickly
		facing = f
		_play(_base() if LOOPS.has(_base()) else "idle", true)
		var tw := create_tween()
		tw.tween_property(self, "squash_v:x", 1.0, 0.16).from(0.2)
		return
	turning = true
	_begin(anim, range(sprite.sprite_frames.get_frame_count(anim)), 28.0 if standing else 22.0, {}, f)
	await clip_finished
	turning = false


func _settle() -> void:
	## let a turn already under way finish first
	while turning:
		await clip_finished


func face_toward(x: float) -> void:
	if absf(x - position.x) < 6:
		return
	var f := signf(x - position.x)
	if f != facing:
		turn_to(f)


func _crossfade_to_loop(anim: String) -> void:
	_fade_out_current(0.45)
	_play(anim, true)


func fall_asleep() -> void:
	## lies down and curls up: one rendered clip from the sitting pose to the sleep loop's first frame. Its fur is grown a
	## little differently (it is rebuilt every frame), so a short fade covers the change at each end.
	var clip := "liedown" if _has("liedown") else "doze"
	if asleep or not _has("sleep") or not _has(clip):
		return
	asleep = true
	busy = true
	target = null
	_fade_out_current(0.2)
	await play_clip(clip, 12.0 if clip == "liedown" else 9.0)
	if clip == "liedown":
		_fade_out_current(0.2)
		_play("sleep", true)
	else:
		_crossfade_to_loop("sleep")
	Log.event("creature_sleep", "")
	busy = false


func bedtime() -> void:
	## the child chose night with the moon button: no staying up, it settles down as soon as it is calm
	_stay_awake_until = 0.0


func wake() -> void:
	## from the sleep loop back to sitting: lying down played backward (it uncurls and sits up)
	if not asleep:
		return
	var clip := "liedown" if _has("liedown") else "doze"
	busy = true
	_fade_out_current(0.2 if clip == "liedown" else 0.35)
	await play_clip(clip, 15.0, true)
	asleep = false
	busy = false
	_stay_awake_until = _age + 25.0
	_fade_out_current(0.2)
	_play("idle", true)
	Log.event("creature_wake", "")


# ------------------------------------------------------------------ actions
func walk_to(p: Vector2, speed := 1.0) -> void:
	target = Vector2(clampf(p.x, GROUND.position.x, GROUND.end.x), clampf(p.y, GROUND.position.y, GROUND.end.y))
	speed_factor = speed
	_idle_for = 0.0


func call_to(p: Vector2) -> void:
	## the child tapped the meadow: it looks up, chirps and trots over
	food_target = null
	Sfx.play("chirp", 1.1)
	Log.event("creature_walk", "call")
	if asleep:
		await wake()
	face_toward(p.x)
	walk_to(p, 1.25)


func pet(p: Vector2) -> void:
	Log.event("creature_tap", temperament)
	petted.emit()
	Fx.hearts(meadow.fx, head_world() + Vector2(0, -30), 1 if busy else 3, 36)
	if busy:
		Sfx.play("chirp", 1.2, 0.1, -4.0)
		return
	target = null
	if asleep:
		Sfx.play("chirp", 0.8, 0.05, -4.0)
		await wake()
	busy = true
	await _settle()
	if _react_tween:
		_react_tween.kill()
	var fps := 12.0
	match temperament:
		"calm":
			Sfx.play("chirp", 0.82)
			fps = 9.0
		"curious":
			if absf(p.x - position.x) > 20:
				await turn_to(signf(p.x - position.x))
			Sfx.play("chirp2", 1.15)
			fps = 12.0
			var t := create_tween()
			_react_tween = t
			t.tween_property(self, "tilt", 0.08 * facing, 0.3).set_trans(Tween.TRANS_SINE)
			t.tween_property(self, "tilt", 0.0, 0.5).set_trans(Tween.TRANS_SINE)
		_:  # playful: happy hops while it wiggles
			Sfx.play("chirp2")
			fps = 14.0
			var t := create_tween()
			_react_tween = t
			for h in [30.0, 16.0]:
				t.tween_property(self, "lift", h, 0.17).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
				t.tween_property(self, "lift", 0.0, 0.15).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	if _has("happy"):
		await play_clip("happy", fps)
	if temperament == "curious":
		Fx.sparkles(meadow.fx, head_world(), 5, 50)
	busy = false


func wants_food_at(p: Vector2) -> bool:
	## a held apple let go over the creature, or right by its mouth
	return hit_test(p) or p.distance_to(mouth_world()) < 90.0


func fetch(apple: Node2D) -> void:
	## an apple dropped near it: walk over and eat it from the ground
	if asleep:
		await wake()
	food_target = apple
	face_toward(apple.position.x)
	walk_to(apple.position + Vector2(-(MOUTH_R.x - FEET_R.x + _ref.x) * depth_scale() * signf(apple.position.x - position.x + 0.01), 6), 1.2)


func eat(apple: Node2D, how: String) -> void:
	food_target = null
	target = null
	busy = true
	Log.event("food_given", how)
	if _react_tween:
		_react_tween.kill()
	apple.z_index = 70
	if asleep:
		await wake()
	busy = true
	await _settle()
	var ax: float = apple.world_pos().x if apple is Touchable else apple.position.x
	if absf(ax - position.x) > 6 and signf(ax - position.x) != facing:
		await turn_to(signf(ax - position.x))
	if not is_instance_valid(apple):
		busy = false
		return
	var s := depth_scale()
	var mouth_down := mouth_world() + Vector2(EAT_DROP.x * facing, EAT_DROP.y) * s
	var t := create_tween()
	_react_tween = t
	t.tween_property(apple, "global_position", meadow.world.to_global(mouth_down), 0.28).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	t.parallel().tween_property(apple, "scale", apple.scale * 0.7, 0.28)
	var base_scale_apple: Vector2 = apple.scale * 0.7
	var bite := func(i: int):
		Sfx.play("munch", 1.0 + i * 0.05)
		if is_instance_valid(apple):
			var tb := create_tween()
			tb.tween_property(apple, "scale", base_scale_apple * (0.7 - i * 0.25), 0.08)
	var gone := func():
		if is_instance_valid(apple):
			apple.queue_free()
	if _has("eat"):
		await play_clip("eat", 12.0, false, {4: bite.bind(0), 7: bite.bind(1), 10: bite.bind(2), 11: gone})
	else:
		for i in 3:
			bite.call(i)
			await get_tree().create_timer(0.22).timeout
		gone.call()
	Sfx.play("happy")
	Fx.sparkles(meadow.fx, position + Vector2(0, -200) * depth_scale(), 10, 120, Color(1, 0.95, 0.75))
	Fx.hearts(meadow.fx, head_world() + Vector2(0, -30), 2)
	var th := create_tween()
	th.tween_property(self, "lift", 18.0, 0.16).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	th.tween_property(self, "lift", 0.0, 0.14).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	await th.finished
	busy = false
	hungry = false
	_hunger_at = _age + 150.0
	ate.emit()


func hunger_cue() -> void:
	## variant A: it turns to the apple tree, looks up at it and sighs; main.gd makes the apples glow
	busy = true
	await _settle()
	meadow.hint_food()
	Log.event("need_cue", "hunger")
	var tx: float = meadow.tree_position().x
	if absf(tx - position.x) > 6 and signf(tx - position.x) != facing:
		await turn_to(signf(tx - position.x))
	if _has("hunger"):
		await play_clip("hunger", 12.0, false, {9: func(): Sfx.play("sigh")})
	else:
		Sfx.play("sigh")
		await get_tree().create_timer(1.4).timeout
	busy = false


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


func _play(anim: String, quiet := false) -> void:
	## start a loop around the shared anchor; a small squash hides the change from walking to sitting
	var name := _side(anim)
	_place_frames(name)
	sprite.speed_scale = 1.0
	sprite.play(name)
	if anim == "idle" and not busy and not quiet:
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
	if not _clip.is_empty():
		_step_clip(delta)
	var moving := false
	if target != null and not busy and not turning and not asleep:
		var d: Vector2 = target - position
		if absf(d.x) > 3 and signf(d.x) != facing:
			face_toward(position.x + d.x)
		if not turning:
			var step := WALK_SPEED * speed_factor * delta
			if d.length() <= step:
				position = target
				target = null
				_arrive()
			else:
				position += d.normalized() * step
				moving = true
	var has_walk := _has("walk")
	if has_walk and _clip.is_empty() and not asleep:
		if moving:
			_still_for = 0.0
			if _base() != "walk":
				_play("walk")
			var w: Dictionary = anims["walk"]
			# cycles per second so a paw on the ground keeps pace with the meadow
			var v := WALK_SPEED * speed_factor
			sprite.speed_scale = clampf(w["stance"] * v / (w["stride"] * depth_scale()), 0.4, 3.0)
		else:
			_still_for += delta
			if _base() == "walk" and _still_for > 0.12 and target == null:
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
	shadow.position = Vector2(info["shadow"][0] * flip.scale.x, -4) * s
	var calm := target == null and not busy and not turning and not _dragging and _clip.is_empty()
	# bedtime: it dozes off at night and wakes at dawn
	var night: bool = meadow != null and meadow.time != null and meadow.time.is_night()
	if asleep:
		if not night and not busy:
			wake()
		return
	if night and calm and _age > _stay_awake_until:
		fall_asleep()
		return
	# idle life: wander a little now and then
	if calm:
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
	if hungry and Game.variant == "A" and calm and _age >= _next_cue:
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
