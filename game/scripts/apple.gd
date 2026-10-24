class_name Apple
extends Touchable
## An apple: hangs on the tree, can be dragged anywhere, offered to a creature, or dropped on the meadow
## (a creature nearby walks over and eats it).

enum State { ON_TREE, HELD, ON_GROUND, EATEN }

var meadow: Node2D
var state := State.ON_TREE
var spot := -1                    ## which branch spot it grew on, while on the tree
var sprite := Sprite2D.new()
var glow := Sprite2D.new()
var _hint := 0.0


func _ready() -> void:
	touch_priority = 30
	glow.texture = Fx.glow_texture(Color(1.0, 0.82, 0.38, 0.95), 128)
	glow.modulate.a = 0.0
	add_child(glow)
	sprite.texture = load("res://art/meadow3d/apple.png")   # rendered at 2x, centred on the apple
	sprite.scale = Vector2.ONE * 0.5
	add_child(sprite)


func hit_test(p: Vector2) -> bool:
	return state != State.EATEN and p.distance_to(world_pos()) < 46.0 * maxf(scale.x, 0.8)


func touch_begin(p: Vector2) -> void:
	if state == State.ON_TREE:
		meadow.apple_left_tree(self)
	state = State.HELD
	meadow.carry(self)
	z_index = 80
	Sfx.play("pickup")
	var t := create_tween()
	t.tween_property(self, "scale", Vector2.ONE * 1.15, 0.12).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
	touch_move(p)


func touch_move(p: Vector2) -> void:
	if state == State.HELD:
		position = p + Vector2(0, -36)   # just above the finger; the overlay shares world coordinates


func touch_end(_p: Vector2) -> void:
	if state != State.HELD:
		return
	z_index = 0
	meadow.apple_released(self)


func fall_to(ground_y: float) -> void:
	state = State.ON_GROUND
	var t := create_tween()
	var land := Vector2(position.x, maxf(position.y, ground_y))
	t.tween_property(self, "position", land, clampf((land.y - position.y) / 900.0, 0.08, 0.45)).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
	t.parallel().tween_property(self, "scale", Vector2.ONE * 0.9, 0.15)
	t.tween_callback(func(): Sfx.play("drop"))
	t.tween_property(self, "position:y", land.y - 10, 0.1).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	t.tween_property(self, "position:y", land.y, 0.1).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)


func hint(seconds := 3.0) -> void:
	## "look, food": the apple bounces, glows and sparkles for a few seconds
	_hint = seconds
	var t := create_tween()
	for i in 3:
		t.tween_property(sprite, "position:y", -14.0, 0.16).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		t.tween_property(sprite, "position:y", 0.0, 0.16).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_IN)
		t.tween_interval(0.5)
	if meadow:
		Fx.sparkles(meadow.fx, world_pos(), 5, 46, Color(1, 0.9, 0.5))


func _process(delta: float) -> void:
	if _hint > 0.0:
		_hint -= delta
		var pulse := 0.5 + 0.5 * sin(Time.get_ticks_msec() / 1000.0 * TAU / 0.9)
		glow.modulate.a = 0.35 + 0.55 * pulse * clampf(_hint, 0.0, 1.0)
		glow.scale = Vector2.ONE * (1.1 + 0.35 * pulse)
	elif glow.modulate.a > 0.0:
		glow.modulate.a = move_toward(glow.modulate.a, 0.0, delta * 2.0)
