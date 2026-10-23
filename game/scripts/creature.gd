class_name Creature
extends Touchable
## A creature in the meadow, drawn as a live 3D model (creature_view.gd; a fox, a unicorn or a collie): an idle loop when sitting, a walk cycle when moving,
## and one-shot clips for eating, being petted (happy), the hunger cue, lying down to sleep, sleeping, waking and
## turning round (half way, sitting or standing, from one side's view to the other's). The clips keep the timings the
## rendered frames had, and their events (bites, the sigh) still count in those frames.
## Touch: tap to pet, drag to walk it somewhere. main.gd also calls it to a tapped spot and hands it food. It looks at a
## finger on the meadow (or the apple it carries) while it isn't busy, and wears things from the basket (wardrobe.gd).
## A baby grows up (grow_up): from its hatching size to an adult's over a few minutes, with a little moment halfway and
## when it is grown. Every creature has its own name (pet_name; the child's first one keeps Game.creature_name).
## In the evening it yawns as dusk falls; the baby (or the child's only creature) gets sleepy first and curls up at
## SLEEPY_AT, the others at night. A tap on a sleeping creature tucks it in under a blanket; a second tap wakes it.

signal petted
signal ate
signal clip_finished
signal arrived                         ## a walk ended (dragged, called or wandering)

## Its points (head, mouth, the top of its head) come from the model's places, wherever the clip has put them; its
## shadow, walk stride, eating dip and size to touch come with the model too (render pixels, 80 to a model unit).
const WALK_SPEED := 120.0
const GROUND := Rect2(120, 525, 1808, 205) ## where it may walk (world): the meadow, the path and the pond
const MEADOW_AREA := Rect2(120, 525, 784, 205)   ## each place's always-visible ground: it wanders within one
const POND_AREA := Rect2(1144, 525, 784, 205)
const LOOPS := ["idle", "walk", "sleep"]
const CLIP_FRAMES := {"eat": 16, "happy": 16, "hunger": 20, "liedown": 20, "turn_sit": 13, "turn_stand": 13, "yawn": 20}
const SLEEPY_AT := 18.6                    ## island hour: the baby (or the child's only creature) curls up
const TAG_ABOVE := 90.0                    ## the name tag's gap above the top of the head (past the ears), render pixels

var temperament := "playful"
var base_scale := 0.5
var traits := Traits.defaults()           ## coat and glow colours (the model's shaders recolour it)
var voice := 1.0                       ## pitch of its sounds: babies squeak higher
var pet_name := ""                     ## its name (the child's first creature uses Game.creature_name instead)
var who := "first"                     ## for the log: first, second, baby1, baby2...
var tag: NameTag
var growing := false                   ## a baby growing up (grow_up)
var grow_seconds := 180.0
var grow_age := 0.0
var _grow := []                        ## [from scale, to scale, from voice, stage reached: 0 baby, 1 young, 2 grown]
var tucked := false                    ## asleep under a blanket
var blanket: Blanket
var _next_sleepy_cue := 0.0
var shows_needs := true                ## variant A's hunger cue: only the child's first creature shows it
var follow: Creature = null            ## a baby potters about near this parent
var home = null                        ## Vector2: stays near here when it wanders (the second adult by the nest)
var meadow: Node2D                     ## main.gd: effects layer, the tree, island time, food on the ground, the finger
var worn := {}                         ## place -> the id of what it wears there

var body := Node2D.new()               ## lift and tilt, pivot at the feet
var squash := Node2D.new()             ## squash and stretch, times the depth scale
var look: CreatureView                      ## the live fox, in render pixels round its ground point
var shadow := Sprite2D.new()

var lift := 0.0                        ## animated by tweens
var tilt := 0.0
var squash_v := Vector2.ONE
var facing := 1.0

var _anim := "idle"                    ## the loop or clip playing (turn_sit, turn_stand; liedown also when waking)
var target = null                      ## Vector2 to walk to, or null
var speed_factor := 1.0
var busy := false                      ## reacting or eating: stands still
var turning := false
var asleep := false
var food_target: Node2D = null         ## an apple on the ground it is walking to
var _drink_at = null                   ## Vector2: the shore spot it is walking to, to drink
var _play_with: Node2D = null          ## a ball it is running after
var _glance = null                     ## Vector2: something to look at for a moment (ripples)
var _glance_until := 0.0
var thirsty := false
var _thirst_at := -1.0                 ## when it next gets thirsty at the pond (set when it first gets there)
var _next_thirst_cue := 0.0
var _clip := {}                        ## the one-shot clip playing: t, dur, fps, frames, fired, events, face
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


func setup(temper: String, world_scale: float, picture_scale := -1.0) -> void:
	## picture_scale: the largest size it will be shown at (a baby that will grow), so its picture stays sharp
	temperament = temper
	base_scale = world_scale
	touch_priority = 20
	shadow.texture = Fx.glow_texture(Color(0.32, 0.24, 0.42, 0.34), 256)
	add_child(shadow)
	add_child(body)
	body.add_child(squash)
	blanket = Blanket.new()
	blanket.creature = self
	add_child(blanket)
	# the picture is made at the largest size it is shown (nearest the front of the meadow)
	look = CreatureView.new(CreatureView.RENDER_PPU * maxf(world_scale, picture_scale) * 1.12 * CreatureView.sharpness)
	look.model.auto_next = false
	look.model.shells = 6 if world_scale >= 0.45 else 4   ## small foxes (babies) need fewer fur layers
	look.model.facing = facing
	squash.add_child(look)
	_play("idle")
	look.model.random_start = true              ## not every fox breathing in step
	_next_wander = _wander_gap()


func set_traits(t: Dictionary) -> void:
	traits = t.duplicate()
	look.model.set_traits(traits)


func _sfx(id: String, pitch := 1.0, vary := 0.06, db := 0.0) -> void:
	Sfx.play(id, pitch * voice, vary, db)


func depth_scale() -> float:
	## a little bigger nearer the front of the meadow
	return base_scale * lerpf(0.86, 1.12, clampf(inverse_lerp(GROUND.position.y, GROUND.end.y, position.y), 0.0, 1.0))


func _point(place: String, otherwise: Vector2) -> Vector2:
	## a place on the model (its own space) in the meadow; `otherwise` (render pixels from the feet) until it is drawn
	if not look or not look.model.is_inside_tree():
		return position + Vector2(otherwise.x * facing, otherwise.y) * depth_scale()
	var g := look.to_global(look.to_picture(look.model.point(place)))
	return meadow.world.to_local(g) if meadow else g


func _info(key: String, otherwise):
	return look.model.get_meta(key, otherwise) if look else otherwise


func head_world() -> Vector2:
	return _point("middle", Vector2(50, -320))


func mouth_world() -> Vector2:
	return _point("mouth", Vector2(100, -280))


func top_world() -> Vector2:
	## above the top of the head (and its ears), wherever the clip has it: lying down, the tag comes down with it
	return _point("head", Vector2(0, -440)) - Vector2(0, TAG_ABOVE * depth_scale())


func hit_test(p: Vector2) -> bool:
	## an oval from the feet to the top of the head
	var s := depth_scale()
	var top := _point("head", Vector2(0, -440))
	var c := (position + top) / 2.0
	var touch: Vector2 = _info("touch", Vector2(165, 250))
	var d := (p - c) / Vector2(touch.x * s, maxf((position.y - top.y) / 2.0 + 30.0 * s, 70.0 * s))
	return d.length() <= 1.0


# ------------------------------------------------------------------ wearing things
func wear(id: String) -> String:
	## put it on; returns what was worn at that place before ("" if nothing), which goes back to the basket
	var place: String = Wardrobe.ITEMS[id]["place"]
	var old: String = worn.get(place, "")
	worn[place] = id
	look.model.wear(place, Wardrobe.model(id, look.model.place_size(place)))
	Log.event("item_worn", id)
	_sfx("chirp2", 1.1)
	Fx.sparkles(meadow.fx, worn_at(place), 6, 40)
	return old


func take_off(place: String) -> void:
	worn.erase(place)
	look.model.take_off(place)


func worn_at(place: String) -> Vector2:
	## where the place is on screen now, in meadow coordinates
	var g := look.to_global(look.to_picture(look.model.worn_point(place)))
	return meadow.world.to_local(g) if meadow else g


func _look_around() -> void:
	## look at a finger on the meadow (or what it carries) while awake and not busy with a clip, or glance at ripples
	if not look.model.look:
		return
	var f = meadow.finger if meadow else null
	if f == null and _glance != null and _age < _glance_until:
		f = _glance
	var on := f != null and not asleep and _clip.is_empty() and (f as Vector2).distance_to(head_world()) < 700.0
	if on:
		look.look_toward(look.to_local(meadow.world.to_global(f)))
	look.model.look.looking = on


# ------------------------------------------------------------------ places and the pond
static func area_at(x: float) -> String:
	return "pond" if x >= 1024.0 else "meadow"


static func area_rect(x: float) -> Rect2:
	return POND_AREA if area_at(x) == "pond" else MEADOW_AREA


func glance(p: Vector2, seconds := 1.6) -> void:
	## look at something for a moment (ripples on the water)
	_glance = p
	_glance_until = _age + seconds


func drink_at(p: Vector2) -> void:
	## walk to the shore nearest p and drink
	if asleep:
		await wake()
	food_target = null
	_play_with = null
	_drink_at = Pond.drink_spot(p)
	face_toward(_drink_at.x)
	walk_to(_drink_at, 1.1)


func drink() -> void:
	## the head dips to the water, three slurps with ripples, then a happy splash
	_drink_at = null
	busy = true
	target = null
	Log.event("drink", who)
	await _settle()
	var pond: Pond = meadow.pond
	var lap := func(i: int):
		_sfx("slurp", 1.0 + 0.06 * i, 0.04)
		pond.ripple(mouth_world() + Vector2(0, 22), 0.55)
	await play_clip("eat", 12.0, false, {4: lap.bind(0), 7: lap.bind(1), 10: lap.bind(2)})
	thirsty = false
	_thirst_at = _age + 150.0
	await splash()
	busy = false


func splash() -> void:
	## a happy hop with drops of water flying up
	_sfx("splash", 1.0, 0.06)
	meadow.pond.ripple(mouth_world() + Vector2(0, 26), 1.3)
	Fx.sparkles(meadow.fx, mouth_world() + Vector2(0, -10), 9, 70, Color(0.7, 0.88, 1.0))
	var t := create_tween()
	t.tween_property(self, "lift", 26.0, 0.17).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	t.tween_property(self, "lift", 0.0, 0.15).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	await play_clip("happy", 14.0)


func thirst_cue() -> void:
	## variant A at the pond: it turns to the water, looks and sighs, and the water glints
	busy = true
	await _settle()
	meadow.pond.shimmer(3.5)
	Log.event("need_cue", "thirst")
	var tx: float = Pond.CENTRE.x
	if absf(tx - position.x) > 60 and signf(tx - position.x) != facing:
		await turn_to(signf(tx - position.x))
	await play_clip("hunger", 12.0, false, {9: func(): _sfx("sigh")})
	busy = false


func chase(ball: Node2D, at: Vector2) -> void:
	## run after a rolling ball, then play with it
	if asleep or busy:
		return
	_play_with = ball
	_drink_at = null
	food_target = null
	face_toward(at.x)
	walk_to(at + Vector2(-60.0 * signf(at.x - position.x + 0.01), 6), 1.5)


func _play_ball() -> void:
	## at the ball: a pat and a happy bounce
	var ball := _play_with
	_play_with = null
	Log.event("play_ball", who)
	if is_instance_valid(ball) and ball.has_method("roll") and randf() < 0.5:
		ball.roll()                        # sometimes it nudges it on
	Fx.hearts(meadow.fx, head_world() + Vector2(0, -30), 2)
	busy = true
	await play_clip("happy", 14.0)
	busy = false


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
		_drink_at = null
		_play_with = null
		Log.event("creature_walk", "drag")
	if _dragging:
		walk_to(p + _drag_offset, 1.7)


func touch_end(p: Vector2) -> void:
	if not _dragging and Time.get_ticks_msec() - _press_ms < 600:
		pet(p)
	_dragging = false


# ------------------------------------------------------------------ clips
func _base() -> String:
	## the loop or clip playing, whichever way it faces
	return _anim


func _begin(anim: String, fps: float, events := {}, face := 0.0, reverse := false) -> void:
	## a one-shot clip at the rendered clip's frame rate; events are {frame index: Callable}; face, if set, is the way
	## it faces once the clip ends (the turns)
	var live: String = {"turn_sit": "turn"}.get(anim, anim)
	if reverse and anim == "liedown":
		live = "wake"
	var dur: float = CLIP_FRAMES[anim] / fps
	look.model.speed = 1.0
	look.model.play(live, dur)
	_anim = anim
	_clip = {"t": 0.0, "dur": dur, "fps": fps, "frames": CLIP_FRAMES[anim], "fired": 0, "events": events, "face": face}
	if events.has(0):
		events[0].call()


func play_clip(anim: String, fps := 12.0, reverse := false, events := {}) -> void:
	## plays a one-shot clip and waits for it
	_begin(anim, fps, events, 0.0, reverse)
	await clip_finished


func _step_clip(delta: float) -> void:
	_clip["t"] += delta
	var ev: Dictionary = _clip["events"]
	var now := mini(int(_clip["t"] * _clip["fps"]), int(_clip["frames"]) - 1)
	while _clip["fired"] < now:
		_clip["fired"] += 1
		if ev.has(_clip["fired"]):
			ev[_clip["fired"]].call()
			if _clip.is_empty():
				return
	if _clip["t"] >= _clip["dur"]:
		var face: float = _clip["face"]
		_clip = {}
		if face != 0.0:
			facing = face
			look.model.facing = face
		clip_finished.emit()
		# nothing chained another clip: back to the right loop
		if _clip.is_empty() and (face != 0.0 or not LOOPS.has(_anim)):
			_play("sleep" if asleep else ("walk" if target != null and not busy else "idle"), true)


func turn_to(f: float) -> void:
	## turn round on the spot, through facing the camera, from this side's view to the other side's
	if f == facing or turning:
		return
	var standing := _anim == "walk"
	turning = true
	_begin("turn_stand" if standing else "turn_sit", 28.0 if standing else 22.0, {}, f)
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


func fall_asleep() -> void:
	## lies down and curls up: sitting, then lying like a sphinx, then curled up, which is where the sleep loop starts
	if asleep:
		return
	asleep = true
	busy = true
	target = null
	await play_clip("liedown", 12.0)
	_play("sleep", true)
	Log.event("creature_sleep", "")
	busy = false


func yawn() -> void:
	## a big sleepy yawn (as dusk falls, and over and over when it is getting sleepy)
	if busy or asleep or turning:
		return
	busy = true
	await play_clip("yawn", 12.0, false, {5: func(): _sfx("yawn", 1.0, 0.05)})
	busy = false


func early_sleeper() -> bool:
	## the baby goes to bed first: every baby, or the child's first creature while it has none
	if follow != null:
		return true
	return meadow != null and meadow.creature == self and (meadow.breeding == null or meadow.breeding.babies == 0)


func sleepy_time() -> bool:
	## when it goes to sleep: at night, or from SLEEPY_AT for the one that goes first
	if meadow == null or meadow.time == null:
		return false
	var h: float = meadow.time.hour
	return meadow.time.is_night() or (early_sleeper() and h >= SLEEPY_AT and h < 23.9)


func tuck_in() -> void:
	## a tap on it asleep: a blanket over it, a little sigh of comfort
	tucked = true
	blanket.cover()
	_sfx("sigh", 1.25, 0.05, -6.0)
	Sfx.play("chime", 1.3, 0.03, -8.0)
	Fx.hearts(meadow.fx, head_world() + Vector2(0, -20), 2, 30)
	Log.event("tuck_in", who)


func bedtime() -> void:
	## the child chose night with the moon button: no staying up, it settles down as soon as it is calm
	_stay_awake_until = 0.0


func wake() -> void:
	## from the sleep loop back to sitting: lying down played backward (it uncurls and sits up)
	if not asleep:
		return
	busy = true
	if tucked:
		tucked = false
		blanket.uncover()
	await play_clip("liedown", 15.0, true)
	asleep = false
	busy = false
	_stay_awake_until = _age + 25.0
	_play("idle", true)
	Log.event("creature_wake", "")


# ------------------------------------------------------------------ actions
func walk_to(p: Vector2, speed := 1.0) -> void:
	target = Pond.shore(Vector2(clampf(p.x, GROUND.position.x, GROUND.end.x), clampf(p.y, GROUND.position.y, GROUND.end.y)))
	speed_factor = speed
	_idle_for = 0.0


func call_to(p: Vector2) -> void:
	## the child tapped the meadow: it looks up, chirps and trots over
	food_target = null
	_drink_at = null
	_play_with = null
	_sfx("chirp", 1.1)
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
		_sfx("chirp", 1.2, 0.1, -4.0)
		return
	target = null
	if asleep:
		if not tucked:                       # the first tap tucks it in; the next wakes it
			tuck_in()
			return
		_sfx("chirp", 0.8, 0.05, -4.0)
		await wake()
	busy = true
	await _settle()
	if _react_tween:
		_react_tween.kill()
	var fps := 12.0
	match temperament:
		"calm":
			_sfx("chirp", 0.82)
			fps = 9.0
		"curious":
			if absf(p.x - position.x) > 20:
				await turn_to(signf(p.x - position.x))
			_sfx("chirp2", 1.15)
			fps = 12.0
			var t := create_tween()
			_react_tween = t
			t.tween_property(self, "tilt", 0.08 * facing, 0.3).set_trans(Tween.TRANS_SINE)
			t.tween_property(self, "tilt", 0.0, 0.5).set_trans(Tween.TRANS_SINE)
		_:  # playful: happy hops while it wiggles
			_sfx("chirp2")
			fps = 14.0
			var t := create_tween()
			_react_tween = t
			for h in [30.0, 16.0]:
				t.tween_property(self, "lift", h, 0.17).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
				t.tween_property(self, "lift", 0.0, 0.15).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
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
	var reach := absf(mouth_world().x - position.x)            # stand so the mouth is over it
	walk_to(apple.position + Vector2(-reach * signf(apple.position.x - position.x + 0.01), 6), 1.2)


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
	var drop: Vector2 = _info("eat_drop", Vector2(-4, 44))   # how far the mouth dips to eat
	var mouth_down := mouth_world() + Vector2(drop.x * facing, drop.y) * s
	var t := create_tween()
	_react_tween = t
	t.tween_property(apple, "global_position", meadow.world.to_global(mouth_down), 0.28).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	t.parallel().tween_property(apple, "scale", apple.scale * 0.7, 0.28)
	var base_scale_apple: Vector2 = apple.scale * 0.7
	var bite := func(i: int):
		_sfx("munch", 1.0 + i * 0.05)
		if is_instance_valid(apple):
			var tb := create_tween()
			tb.tween_property(apple, "scale", base_scale_apple * (0.7 - i * 0.25), 0.08)
	var gone := func():
		if is_instance_valid(apple):
			apple.queue_free()
	await play_clip("eat", 12.0, false, {4: bite.bind(0), 7: bite.bind(1), 10: bite.bind(2), 11: gone})
	_sfx("happy")
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
	await play_clip("hunger", 12.0, false, {9: func(): _sfx("sigh")})
	busy = false


func set_pet_name(n: String) -> void:
	pet_name = n.strip_edges().left(16)
	if tag:
		tag.set_text(pet_name)


# ------------------------------------------------------------------ growing up
const STAGES := ["baby", "young", "grown"]


func grow_up(to_scale: float, seconds: float) -> void:
	## grow from its size now to to_scale over this many seconds of island time (faster when island time runs fast)
	growing = true
	grow_seconds = seconds
	grow_age = 0.0
	_grow = [base_scale, to_scale, voice, 0]


func stage() -> String:
	return STAGES[_grow[3]] if growing or not _grow.is_empty() else "grown"


func _grow_step(delta: float) -> void:
	var speed: float = meadow.time.speed if meadow and meadow.time else 1.0
	grow_age = minf(grow_age + delta * speed, grow_seconds)
	var k := smoothstep(0.0, 1.0, grow_age / grow_seconds)
	base_scale = lerpf(_grow[0], _grow[1], k)
	voice = lerpf(_grow[2], 1.0, k)
	var reached := 2 if grow_age >= grow_seconds else (1 if grow_age >= grow_seconds * 0.5 else 0)
	if reached > _grow[3]:
		_grow[3] = reached
		_grew(STAGES[reached])
	if reached == 2:
		growing = false


func _grew(to_stage: String) -> void:
	## a little moment: it stretches up, sparkles and chirps (a bit deeper each time)
	Log.event("creature_grew", "%s=%s" % [who, to_stage])
	if to_stage == "grown":
		look.model.shells = 6                  # an adult's fur
	if asleep:
		return
	_sfx("happy", 0.95)
	Fx.sparkles(meadow.fx, head_world(), 10, 90, Color(1, 0.95, 0.8))
	var t := create_tween()
	t.tween_property(self, "squash_v", Vector2(0.9, 1.14), 0.18).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	t.tween_property(self, "squash_v", Vector2.ONE, 0.3).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)


func appear(from: Vector2, hop := Vector2(120, 50)) -> void:
	## hatched: pops out of the egg, then hops clear of the nest
	position = from
	busy = true
	squash_v = Vector2(0.2, 0.2)
	var t := create_tween()
	t.tween_property(self, "squash_v", Vector2(1.1, 0.92), 0.35).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	t.tween_property(self, "squash_v", Vector2.ONE, 0.25)
	t.tween_callback(func(): _sfx("happy"))
	t.tween_interval(0.5)
	t.tween_callback(func():
		busy = false
		walk_to(from + hop, 0.8))


func _play(anim: String, quiet := false) -> void:
	## start a loop; a small squash softens the change from walking to sitting
	_anim = anim
	look.model.speed = 1.0
	look.model.play(anim)
	if anim == "idle" and not busy and not quiet:
		var t := create_tween()
		t.tween_property(self, "squash_v", Vector2(1.05, 0.95), 0.07)
		t.tween_property(self, "squash_v", Vector2.ONE, 0.12)


func _wander_gap() -> float:
	if follow:
		return randf_range(2.5, 5.0)
	match temperament:
		"calm":
			return randf_range(10.0, 16.0)
		"curious":
			return randf_range(5.0, 9.0)
	return randf_range(4.0, 8.0)


# ------------------------------------------------------------------ every frame
func _process(delta: float) -> void:
	_age += delta
	if growing:
		_grow_step(delta)
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
	if _clip.is_empty() and not asleep:
		if moving:
			_still_for = 0.0
			if _anim != "walk":
				_play("walk")
			# cycles per second so a paw on the ground keeps pace with the meadow
			var v := WALK_SPEED * speed_factor
			var walk: Dictionary = _info("walk", {"stride": 88.0, "stance": 0.6})
			look.model.speed = clampf(walk["stance"] * v / (walk["stride"] * depth_scale()), 0.4, 3.0)
		else:
			_still_for += delta
			if _anim == "walk" and _still_for > 0.12 and target == null:
				_play("idle")
	var s := depth_scale()
	body.position.y = -lift
	body.rotation = tilt
	squash.scale = squash_v * s
	look.model.facing = facing                  # a turn changes facing only as it ends
	_look_around()
	# the shadow follows the pose: sitting (or lying like a sphinx), standing, curled up
	var w := look.model.pose_weights()
	var side := 0 if facing > 0 else 1
	var shadows: Dictionary = _info("shadows", {})
	var sh := Vector2(0, 220)
	if not shadows.is_empty():
		sh = shadows["sit"][side] * (w.x + w.z) + shadows["stand"][side] * w.y + shadows["sleep"][side] * w.w
	shadow.scale = Vector2(sh.y, sh.y * 0.17) / 256.0 * s * (1.0 - clampf(lift / 160.0, 0.0, 0.35))
	shadow.position = Vector2(sh.x, -4) * s
	var calm := target == null and not busy and not turning and not _dragging and _clip.is_empty()
	# bedtime: it dozes off at night (the baby a little earlier) and wakes at dawn
	var night := sleepy_time()
	if asleep:
		if not night and not busy:
			wake()
		return
	if night and calm and _age > _stay_awake_until:
		fall_asleep()
		return
	# variant A: getting sleepy before it curls up, it yawns now and then and sleepy z's drift up
	if Game.variant == "A" and early_sleeper() and calm and meadow and meadow.time and _age >= _next_sleepy_cue:
		var h: float = meadow.time.hour
		if h >= 18.0 and h < SLEEPY_AT:
			_next_sleepy_cue = _age + 7.0
			Fx.zz(meadow.fx, head_world() + Vector2(20.0 * facing, -40))
			Log.event("need_cue", "sleepy")
			yawn()
			return
	# idle life: wander a little now and then
	if calm:
		_idle_for += delta
		if _idle_for > _next_wander:
			_idle_for = 0.0
			_next_wander = _wander_gap()
			var p := position + Vector2(randf_range(-220, 220), randf_range(-60, 60))
			var rect := area_rect(position.x)
			if follow and is_instance_valid(follow):
				p = follow.position + Vector2(randf_range(-170, 170), randf_range(-30, 50))
				rect = area_rect(follow.position.x)
			elif home != null:
				p = home + Vector2(randf_range(-90, 90), randf_range(-25, 25))
				rect = area_rect(home.x)
			p = Vector2(clampf(p.x, rect.position.x, rect.end.x), clampf(p.y, rect.position.y, rect.end.y))
			walk_to(p, 0.55 if temperament == "calm" else 0.75)
	# needs: only variant A shows a cue
	if Game.variant == "A" and shows_needs and not hungry and _age > _hunger_at:
		hungry = true
		_next_cue = _age
	if hungry and Game.variant == "A" and shows_needs and calm and _age >= _next_cue:
		_next_cue = _age + 22.0
		hunger_cue()
		return
	# thirst: only at the pond; it first gets thirsty a little while after it arrives there
	if meadow and meadow.pond and area_at(position.x) == "pond":
		if _thirst_at < 0.0:
			_thirst_at = _age + 12.0
		if not thirsty and _age > _thirst_at:
			thirsty = true
			_next_thirst_cue = _age
	if thirsty and Game.variant == "A" and shows_needs and calm and _age >= _next_thirst_cue and area_at(position.x) == "pond":
		_next_thirst_cue = _age + 22.0
		thirst_cue()


func look_up(seconds := 2.5) -> void:
	## the rain: it looks up at the sky
	glance(head_world() + Vector2(60.0 * facing, -420), seconds)


func _arrive() -> void:
	if _drink_at != null and position.distance_to(_drink_at) < 14.0:
		drink()
		return
	if _play_with and is_instance_valid(_play_with):
		_play_ball()
		return
	if food_target and is_instance_valid(food_target):
		var apple := food_target
		food_target = null
		if absf(apple.position.x - mouth_world().x) < 90 and absf(apple.position.y - position.y) < 60:
			eat(apple, "ground")
			return
	arrived.emit()
	var t := create_tween()
	t.tween_property(self, "squash_v", Vector2(1.05, 0.95), 0.08)
	t.tween_property(self, "squash_v", Vector2.ONE, 0.15)


class Blanket:
	extends Node2D
	## a patchwork blanket over a sleeping creature, from its tail to just behind its head

	var creature: Creature
	var amount := 0.0
	var _tween: Tween

	func _ready() -> void:
		visible = false
		z_index = 1

	func cover() -> void:
		visible = true
		if _tween:
			_tween.kill()
		_tween = create_tween()
		_tween.tween_property(self, "amount", 1.0, 0.45).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)

	func uncover() -> void:
		if _tween:
			_tween.kill()
		_tween = create_tween()
		_tween.tween_property(self, "amount", 0.0, 0.3)
		_tween.tween_callback(func(): visible = false)

	func _process(_delta: float) -> void:
		if visible:
			queue_redraw()

	func _draw() -> void:
		if amount <= 0.01:
			return
		var s := creature.depth_scale() / 0.5
		var f := creature.facing
		var head := creature.head_world() - creature.position
		var size: Vector3 = creature.look.model.get_meta("blanket", Vector3(60, 300, 100))   # render pixels
		var ds := creature.depth_scale()
		var near := head.x - f * size.x * ds         # from just behind the head
		var far := head.x - f * size.y * ds          # back over the body
		var x0 := minf(near, far)
		var x1 := maxf(near, far)
		var top := -size.z * ds * amount
		var bottom := 4.0 * s
		# a soft dome: highest over the middle of the body, tucked down at both ends
		var edge := PackedVector2Array()
		for k in 25:
			var t := k / 24.0
			var bump := sin(PI * t)
			edge.append(Vector2(lerpf(x0, x1, t), lerpf(bottom - 6.0 * s, top, pow(bump, 0.4)) + sin(t * 22.0) * 1.5 * s))
		var pts := edge.duplicate()
		for k in range(24, -1, -1):
			var t := k / 24.0
			pts.append(Vector2(lerpf(x0 - 4.0 * s, x1 + 4.0 * s, t), bottom + sin(PI * t) * 5.0 * s))
		draw_colored_polygon(pts, Color("f7c6d9"))
		# patchwork: soft squares in a row along the middle, and white stitches by the edge
		var cols := [Color("fbe3a8"), Color("c9e4f5"), Color("d9cdf4"), Color("cfeac0")]
		for i in 4:
			var t := (i + 0.5) / 4.0
			var c := Vector2(lerpf(x0, x1, t), lerpf(bottom, top, pow(sin(PI * t), 0.4)) * 0.45)
			var hw := (x1 - x0) / 11.0
			draw_rect(Rect2(c - Vector2(hw, hw * 0.8), Vector2(hw * 2.0, hw * 1.6)), Color(cols[i], 0.9), true)
		draw_polyline(edge, Color("e79bb8"), 3.0 * s, true)
		for k in range(2, 23, 2):
			var a := edge[k] + Vector2(0, 6.0 * s)
			draw_line(a, a + Vector2(5.0 * s, 0), Color(1, 1, 1, 0.85), 1.5, true)
