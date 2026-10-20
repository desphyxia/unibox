class_name Egg
extends Touchable
## The glowing egg in the nest. Each tap (or a rub across it) wobbles it with a knock; cracks appear; the fourth
## touch hatches it with a burst of light. It invites a touch by glowing, and by wobbling on its own if left alone.

signal hatched(at: Vector2)

const TAPS_TO_HATCH := 4

var meadow: Node2D
var sprite := Sprite2D.new()
var glow := Sprite2D.new()
var cracks := Node2D.new()
var taps := 0
var _rub := 0.0
var _last := Vector2.ZERO
var _last_knock_ms := 0
var _idle := 0.0
var _t := 0.0
var _done := false


func _ready() -> void:
	touch_priority = 10
	glow.texture = Fx.glow_texture(Color(1.0, 0.93, 0.7, 0.85), 256)
	glow.position = Vector2(0, -72)
	add_child(glow)
	sprite.texture = load("res://art/meadow/egg.svg")
	sprite.centered = false
	sprite.scale = Vector2.ONE * 0.5
	sprite.offset = Vector2(-120, -292)     # texture is drawn at 2x: bottom centre is the origin
	add_child(sprite)
	sprite.add_child(cracks)


func hit_test(p: Vector2) -> bool:
	var d := (p - (world_pos() + Vector2(0, -75))) / Vector2(80, 100)
	return not _done and d.length() <= 1.0


func touch_begin(p: Vector2) -> void:
	_last = p
	_rub = 0.0
	knock()


func touch_move(p: Vector2) -> void:
	_rub += p.distance_to(_last)
	_last = p
	if _rub > 90.0 and Time.get_ticks_msec() - _last_knock_ms > 250:
		_rub = 0.0
		knock()


func knock() -> void:
	if _done:
		return
	_idle = 0.0
	_last_knock_ms = Time.get_ticks_msec()
	taps += 1
	Log.event("egg_tap", str(taps))
	var t := create_tween()
	var k := 0.13 + 0.03 * taps
	for a in [k, -k * 0.8, k * 0.5, -k * 0.25, 0.0]:
		t.tween_property(sprite, "rotation", a, 0.07).set_trans(Tween.TRANS_SINE)
	Sfx.play("knock", 1.0 + taps * 0.06)
	if taps >= 2:
		Sfx.play("crack", 1.0, 0.1, -3.0)
		_add_crack()
	if taps >= TAPS_TO_HATCH:
		t.tween_callback(hatch)


func _add_crack() -> void:
	## a zigzag crack across the shell, a little higher each time (egg texture pixels)
	var line := Line2D.new()
	line.width = 5.0
	line.default_color = Color(0.72, 0.56, 0.56, 0.9)
	line.joint_mode = Line2D.LINE_JOINT_ROUND
	line.position = sprite.offset
	var y := 150.0 - (taps - 2) * 46.0 + randf_range(-10, 10)
	var x := 40.0
	while x <= 200.0:
		line.add_point(Vector2(x, y + (12.0 if int(x / 26.0) % 2 == 0 else -12.0) + randf_range(-4, 4)))
		x += 26.0
	cracks.add_child(line)


func hatch() -> void:
	if _done:
		return
	_done = true
	Sfx.play("hatch")
	var at := world_pos()
	Fx.flash(meadow.fx, at + Vector2(0, -70), Color(1, 0.97, 0.86, 0.95), 3.2)
	Fx.sparkles(meadow.fx, at + Vector2(0, -70), 16, 150, Color(1, 0.95, 0.8))
	var t := create_tween().set_parallel()
	t.tween_property(sprite, "scale", Vector2.ONE * 0.62, 0.12)
	t.tween_property(self, "modulate:a", 0.0, 0.3).set_delay(0.1)
	t.chain().tween_callback(queue_free)
	Log.event("hatch")
	hatched.emit(at)


func _process(delta: float) -> void:
	_t += delta
	_idle += delta
	var pulse := 0.5 + 0.5 * sin(_t * TAU / 1.6)
	glow.modulate.a = 0.45 + 0.45 * pulse
	glow.scale = Vector2.ONE * (1.25 + 0.12 * pulse) * Vector2(1.0, 1.25)
	if _idle > 7.0 and not _done:               # nobody has touched it for a while: a small wobble to invite a tap
		_idle = 0.0
		var t := create_tween()
		for a in [0.06, -0.05, 0.03, 0.0]:
			t.tween_property(sprite, "rotation", a, 0.1).set_trans(Tween.TRANS_SINE)
