class_name Breeding
extends Node
## The second adult and the nest (docs/first-ten-minutes.md, minutes 6-10). A few minutes after the first hatch an adult
## of the same kind, in other colours, trots in and settles by the nest, and the nest glows. When the child brings
## their creature over (a walk that ends beside the other one), the two greet each other, hearts rise and an egg appears
## in the nest. The trait picker opens; the child chooses each colour from one parent or the other; then a tap or a rub
## hatches the egg into a baby that keeps close to the child's creature. The nest glows again for another egg later.

const ARRIVE_AFTER := 240.0            ## seconds after the first hatch (about minute 5-6 of a session)
const AGAIN_AFTER := 40.0              ## after a baby hatches, the nest glows again
const MAX_BABIES := 3
const PAIR_DISTANCE := 240.0
const BABY_SCALE := 0.68               ## times the adults' size
const GROW_SECONDS := 180.0            ## a baby grows to an adult's size over this much island time

enum State { NONE, WAITING, ARRIVING, READY, PAIRING, PICKING, EGG, RESTING, DONE }

var main: Node2D                       ## main.gd: creature, nest, fx, frames, spawn_creature(), picker
var state := State.NONE
var partner: Creature
var babies := 0
var _clock := 0.0
var _egg: Egg
var _baby_traits := {}
var _nest_glow := Sprite2D.new()
var _glow_on := 0.0
var _t := 0.0


func _ready() -> void:
	_nest_glow.texture = Fx.glow_texture(Color(1.0, 0.86, 0.95, 0.9), 256)
	_nest_glow.position = Vector2(0, 10)
	_nest_glow.scale = Vector2(2.4, 1.1)
	_nest_glow.modulate.a = 0.0
	main.nest.add_child(_nest_glow)
	main.nest.move_child(_nest_glow, 0)          ## behind the nest's back rim


func start() -> void:
	## the first creature has hatched: the second adult comes along later
	if state == State.NONE:
		state = State.WAITING
		_clock = 0.0


func arrive_now() -> void:
	## the parent area (or a test): don't wait for the second adult
	if state in [State.NONE, State.WAITING] and main.creature:
		_arrive()


func home() -> Vector2:
	return main.NEST_AT + Vector2(200, 45)


func beside() -> Vector2:
	## where the child's creature sits while there is an egg: the other side of the nest, so the egg stays in view
	return main.NEST_AT + Vector2(-200, 45)


func _arrive() -> void:
	state = State.ARRIVING
	var t := Traits.other_than(main.creature.traits)
	partner = main.spawn_creature(t, 1.0, Vector2(main.BASE.x + 220, home().y + 10), "calm", -1.0)
	partner.shows_needs = false
	partner.who = "second"
	main.add_tag(partner)
	partner.home = home()
	partner.voice = 0.92
	partner.walk_to(home(), 0.85)
	partner.arrived.connect(_on_walk_ended.bind(partner))
	main.creature.arrived.connect(_on_walk_ended.bind(main.creature))
	Log.event("second_adult", "%s,%s" % [t["coat"], t["glow"]])
	main.get_tree().create_timer(1.2).timeout.connect(func(): Sfx.play("chirp", 0.9, 0.0, -2.0))


func _on_walk_ended(who: Creature) -> void:
	if state == State.ARRIVING and who == partner:
		state = State.READY
		Sfx.play("chime", 1.0, 0.0, -6.0)
		Fx.sparkles(main.fx, main.NEST_AT + Vector2(0, -30), 8, 90, Color(1, 0.9, 0.97))
		return
	if state != State.READY:
		return
	var a: Creature = main.creature
	if a.position.distance_to(partner.position) < PAIR_DISTANCE and not a.asleep:
		_pair()


func _pair() -> void:
	state = State.PAIRING
	var a: Creature = main.creature
	var b := partner
	Log.event("nest_pair")
	for c in [a, b]:
		c.target = null
		c.food_target = null
	if b.asleep:
		await b.wake()
	for c in [a, b]:
		c.busy = true
	await a._settle()
	await b._settle()
	# each to its own side of the nest, then they greet across it
	a.busy = false
	b.busy = false
	a.home = beside()
	a.walk_to(beside(), 1.1)
	b.walk_to(home(), 1.1)
	var waited := 0.0
	while (a.target != null or b.target != null) and waited < 6.0:
		await main.get_tree().process_frame
		waited += main.get_process_delta_time()
	for c in [a, b]:
		c.target = null
		c.busy = true
	a.face_toward(b.position.x)
	b.face_toward(a.position.x)
	while a.turning or b.turning:
		await main.get_tree().process_frame
	var mid: Vector2 = (a.head_world() + b.head_world()) / 2.0
	Sfx.play("happy", 1.0)
	Fx.hearts(main.fx, mid + Vector2(0, -10), 5, 50)
	b.play_clip("happy", 12.0)
	await a.play_clip("happy", 12.0)
	Fx.hearts(main.fx, mid + Vector2(0, -30), 3, 30)
	for c in [a, b]:
		c.busy = false
	_lay_egg()


func _lay_egg() -> void:
	_egg = Egg.new()
	_egg.meadow = main
	_egg.locked = true
	_egg.position = Vector2(0, 22)
	main.nest.add_child(_egg)
	main.nest.move_child(_egg, 2)                # between the nest's back and its woven front rim
	_egg.hatched.connect(_on_baby_hatched)
	_egg.scale = Vector2.ONE * 0.2
	var t := _egg.create_tween()
	t.tween_property(_egg, "scale", Vector2.ONE, 0.45).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	Sfx.play("sparkle", 0.9)
	Fx.flash(main.fx, main.NEST_AT + Vector2(0, -50), Color(1, 0.95, 0.98, 0.8), 2.2)
	Fx.sparkles(main.fx, main.NEST_AT + Vector2(0, -50), 12, 110, Color(1, 0.92, 0.98))
	state = State.PICKING
	await main.get_tree().create_timer(1.1).timeout
	main.open_picker([main.creature, partner], _on_traits_chosen)


func _on_traits_chosen(t: Dictionary, _sources: Dictionary) -> void:
	_baby_traits = t
	state = State.EGG
	_egg.locked = false
	_egg.glow.self_modulate = Traits.swatch("glow", t["glow"]).lightened(0.35)
	_egg.sprite.self_modulate = Color(1, 1, 1).lerp(Traits.swatch("coat", t["coat"]).lightened(0.5), 0.35)


func _on_baby_hatched(at: Vector2) -> void:
	var baby: Creature = main.spawn_creature(_baby_traits, BABY_SCALE, at + Vector2(0, 24), main.creature.temperament, 1.0, 1.0)
	baby.follow = main.creature
	baby.voice = 1.38
	baby.shows_needs = false
	baby.appear(at + Vector2(0, 24), Vector2(-110 if main.creature.position.x < at.x else 110, 60))
	baby._next_wander = 2.0
	babies += 1
	baby.who = "baby%d" % babies
	baby.grow_up(main.CREATURE_SCALE, GROW_SECONDS)
	main.add_tag(baby)
	Log.event("egg_hatch_second", "%s,%s" % [_baby_traits["coat"], _baby_traits["glow"]])
	_egg = null
	main.creature.home = null
	if babies >= MAX_BABIES:
		state = State.DONE
	else:
		state = State.RESTING
		_clock = 0.0


func _process(delta: float) -> void:
	_t += delta
	_clock += delta
	match state:
		State.WAITING:
			var night: bool = main.time.is_night()
			if _clock >= ARRIVE_AFTER and not night:
				_arrive()
		State.RESTING:
			if _clock >= AGAIN_AFTER:
				state = State.READY
	# the nest glows while it waits for the two of them
	_glow_on = move_toward(_glow_on, 1.0 if state == State.READY else 0.0, delta * 1.5)
	_nest_glow.modulate.a = _glow_on * (0.55 + 0.3 * sin(_t * TAU / 1.8))
