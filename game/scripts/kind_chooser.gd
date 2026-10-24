class_name KindChooser
extends Touchable
## The first choice of the session (docs/concept-state.md 12: "the child meets and chooses a first creature"): at dawn
## three soap bubbles float over the nest, each holding a live creature (fox, unicorn, collie) breathing and looking
## about. No words: the child taps one. That creature gives a happy hop, the other bubbles drift up and pop, and the
## chosen bubble floats down into the egg with a sparkle; the egg glows and can be hatched. Game.kind is set then, so
## the hatchling, the second adult and the babies are all that kind. Log event: kind_chosen (the kind).

signal chosen(kind: String)

const KINDS := ["fox", "unicorn", "collie"]
const SPOTS := [Vector2(300, 392), Vector2(512, 352), Vector2(724, 392)]   ## the bubbles' centres (meadow units)
const R := 118.0                                 ## a bubble's radius
const LOOK_SCALE := 0.35                         ## the creatures inside, as a share of their render size
const FEET := Vector2(0, 92)                     ## a creature's ground point, from its bubble's centre

var meadow: Node2D
var egg_at := Vector2.ZERO                       ## where the chosen bubble goes (the egg, meadow units)
var _bubbles := []                               ## [{kind, node, view, phase, gone}]
var _t := 0.0
var _done := false
var _shine: GradientTexture2D


func _ready() -> void:
	touch_priority = 40                          ## above the egg and the creatures
	z_index = 50
	_shine = Fx.glow_texture(Color(1, 1, 1, 0.9), 64)
	for i in KINDS.size():
		var k: String = KINDS[i]
		var node := Node2D.new()
		node.position = SPOTS[i]
		add_child(node)
		var glow := Sprite2D.new()                 # a soft light inside the bubble, behind the creature
		glow.texture = Fx.glow_texture(Color(1.0, 0.97, 0.88, 0.75), 256)
		glow.scale = Vector2.ONE * (R * 2.0 / 256.0) * 1.05
		node.add_child(glow)
		var view := CreatureView.new(CreatureView.RENDER_PPU * LOOK_SCALE * 1.15, k)
		view.scale = Vector2.ONE * LOOK_SCALE
		view.position = FEET
		view.model.facing = 1.0 if i < 1 else -1.0           # the outer ones turn in toward the middle
		view.model.random_start = true
		node.add_child(view)
		view.model.set_traits(Traits.defaults(k))
		view.model.play("idle")
		var rim := _Rim.new()                      # the bubble's skin, drawn over the creature
		rim.r = R
		rim.shine = _shine
		node.add_child(rim)
		node.scale = Vector2.ONE * 0.01            # they grow in, one after another
		var t := create_tween()
		t.tween_interval(0.5 + 0.35 * i)
		t.tween_property(node, "scale", Vector2.ONE, 0.55).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
		t.parallel().tween_callback(func(): Sfx.play("bloop", 1.1 + 0.12 * i, 0.03, -4.0)).set_delay(0.1)
		_bubbles.append({"kind": k, "node": node, "view": view, "phase": i * 2.1, "gone": false})


func hit_test(p: Vector2) -> bool:
	return not _done and _bubble_at(p) >= 0


func _bubble_at(p: Vector2) -> int:
	var here := world_pos()
	for i in _bubbles.size():
		var b: Dictionary = _bubbles[i]
		var n: Node2D = b["node"]
		if not b["gone"] and n.scale.x > 0.5 and (p - (here + n.position)).length() <= R * 1.05:
			return i
	return -1


func touch_begin(p: Vector2) -> void:
	var i := _bubble_at(p)
	if i >= 0:
		var n: Node2D = _bubbles[i]["node"]
		var t := create_tween()
		t.tween_property(n, "scale", Vector2(1.08, 0.94), 0.08)
		t.tween_property(n, "scale", Vector2.ONE, 0.18).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)


func touch_end(p: Vector2) -> void:
	var i := _bubble_at(p)
	if i >= 0:
		choose(i)


func choose(i: int) -> void:
	if _done:
		return
	_done = true
	var b: Dictionary = _bubbles[i]
	var kind: String = b["kind"]
	Game.kind = kind
	Log.event("kind_chosen", kind)
	var view: CreatureView = b["view"]
	view.model.play("happy")
	Sfx.play("happy", 1.05, 0.03)
	var n: Node2D = b["node"]
	Fx.hearts(meadow.fx if meadow else self, world_pos() + n.position + Vector2(0, -40), 3, 50.0)
	# the others drift up and pop
	for j in _bubbles.size():
		if j == i:
			continue
		var o: Dictionary = _bubbles[j]
		o["gone"] = true
		var on: Node2D = o["node"]
		var t := create_tween()
		t.tween_interval(0.25 + 0.15 * j)
		t.tween_property(on, "position", on.position + Vector2(0, -90), 0.6).set_trans(Tween.TRANS_SINE)
		var ov: CreatureView = o["view"]
		t.parallel().tween_method(func(v: float):
			on.modulate.a = v
			ov.modulate = Color(v, v, v, 1.0), 1.0, 0.0, 0.6)       # the picture is premultiplied: its colour fades too
		t.tween_callback(func():
			Sfx.play("pop", 1.2, 0.05, -6.0)
			on.queue_free())
	# the chosen one floats down into the egg
	var t := create_tween()
	t.tween_interval(1.25)
	t.tween_property(n, "position", egg_at - world_pos() + Vector2(0, -80), 1.1).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)
	t.parallel().tween_property(n, "scale", Vector2.ONE * 0.35, 1.1).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN)
	t.tween_callback(func():
		Sfx.play("sparkle", 1.0, 0.0, -2.0)
		Sfx.play("pop", 0.9, 0.0, -4.0)
		Fx.sparkles(meadow.fx if meadow else self, egg_at + Vector2(0, -80), 14, 110, Color(1, 0.95, 0.85))
		Fx.flash(meadow.fx if meadow else self, egg_at + Vector2(0, -80), Color(1, 0.97, 0.86, 0.8), 1.8))
	t.tween_property(n, "scale", Vector2.ONE * 0.01, 0.2)
	t.tween_callback(func():
		chosen.emit(kind)
		queue_free())


func _process(delta: float) -> void:
	_t += delta
	for b in _bubbles:
		if b["gone"] or _done:
			continue
		var n: Node2D = b["node"]
		var i := _bubbles.find(b)
		n.position = SPOTS[i] + Vector2(4.0 * sin(_t * 0.9 + b["phase"]), 7.0 * sin(_t * 1.3 + b["phase"]))


class _Rim extends Node2D:
	## a soap bubble's skin: a faint rainbow edge, a pale film, two highlights
	var r := 100.0
	var shine: Texture2D
	var _t := 0.0

	func _process(delta: float) -> void:
		_t += delta
		queue_redraw()

	func _draw() -> void:
		draw_circle(Vector2.ZERO, r, Color(1, 1, 1, 0.07), true, -1.0, true)
		var cols := [Color(1.0, 0.75, 0.85), Color(0.75, 0.85, 1.0), Color(0.75, 1.0, 0.85), Color(1.0, 0.95, 0.7)]
		for k in 4:
			var a0 := _t * 0.4 + k * TAU / 4.0
			draw_arc(Vector2.ZERO, r - 2.0, a0, a0 + TAU / 4.0 + 0.3, 24, Color(cols[k], 0.55), 4.0, true)
		draw_arc(Vector2.ZERO, r, 0, TAU, 64, Color(1, 1, 1, 0.5), 2.0, true)
		draw_texture_rect(shine, Rect2(Vector2(-0.62, -0.7) * r, Vector2(0.42, 0.3) * r), false, Color(1, 1, 1, 0.75))
		draw_circle(Vector2(0.5, 0.48) * r, r * 0.06, Color(1, 1, 1, 0.45), true, -1.0, true)
