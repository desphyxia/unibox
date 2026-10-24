class_name DecorBasket
extends Node2D
## A basket at the pond with three things to place anywhere (docs/first-ten-minutes.md, minutes 3:30-5:00): a
## flowering plant, a lantern (it glows at night) and a ball. Drag one out and let go on the grass: it stays there.
## Drag a placed one to move it. A tap on the plant makes it sway; a tap on the ball rolls it, and a creature nearby
## runs after it; a ball let go near a creature, it plays with.

const AT := Vector2(1940, 704)           ## the basket, in meadow coordinates (bottom right of the pond)
const ITEMS := {
	"plant": {"spot": Vector2(-34, -30), "foot": Vector2(50, 116), "art": "plant"},
	"lantern": {"spot": Vector2(2, -40), "foot": Vector2(40, 136), "art": "lantern"},
	"ball": {"spot": Vector2(36, -24), "foot": Vector2(32, 60), "art": "ball"},
}
const AREA := Rect2(1040, 520, 1000, 245)   ## where things can be placed (the pond's grass)

var meadow: Node2D
var items := {}


func _ready() -> void:
	position = AT
	add_child(Wardrobe.basket_sprite())
	for id in ITEMS:
		var it := DecorItem.new()
		it.id = id
		it.basket = self
		items[id] = it
		add_child(it)
		it.home()


func _draw() -> void:
	draw_set_transform(Vector2(0, -6), 0.0, Vector2(1.0, 0.42))   # its shadow (the pond's backdrop is still drawn)
	draw_circle(Vector2.ZERO, 62.0, Color(0.42, 0.27, 0.16, 0.28))
	draw_set_transform(Vector2.ZERO)


func place(it: DecorItem, p: Vector2) -> void:
	## let go: on the grass it stays (out of the water); over the basket it goes back in
	if p.distance_to(AT + Vector2(0, -10)) < 60.0:
		it.home(true)
		return
	var at := Vector2(clampf(p.x, AREA.position.x, AREA.end.x), clampf(p.y, AREA.position.y, AREA.end.y))
	at = Pond.shore(at)
	it.placed_at(at)
	Log.event("decor_placed", it.id)
	if it.id == "ball":
		meadow.ball_moved(it)


class DecorItem:
	extends Touchable
	## one thing: in the basket, carried by a finger, or standing on the grass (then it sits in the meadow's depth order)

	var id := ""
	var basket: DecorBasket
	var state := "basket"
	var sprite := Sprite2D.new()
	var glow := Sprite2D.new()           ## the lantern's light at night
	var _press := Vector2.ZERO
	var _moved := false

	func _ready() -> void:
		touch_priority = 33
		var info: Dictionary = DecorBasket.ITEMS[id]
		sprite.texture = load("res://art/meadow/%s.svg" % info["art"])
		sprite.centered = false
		sprite.offset = -(info["foot"] as Vector2) * 2.0
		add_child(sprite)
		if id == "lantern":
			glow.texture = Fx.glow_texture(Color(1.0, 0.86, 0.5, 0.9), 256)
			glow.position = Vector2(0, -50)
			glow.modulate.a = 0.0
			glow.show_behind_parent = true
			add_child(glow)

	func _size() -> float:
		return 0.28 if state == "basket" else 0.5

	func home(animate := false) -> void:
		state = "basket"
		if get_parent() != basket:
			reparent(basket)
		z_index = 2
		var spot: Vector2 = DecorBasket.ITEMS[id]["spot"]
		sprite.scale = Vector2.ONE * _size()
		if animate:
			var t := create_tween()
			t.tween_property(self, "position", spot, 0.3).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
			Sfx.play("drop", 1.1, 0.05, -4.0)
		else:
			position = spot

	func placed_at(at: Vector2) -> void:
		state = "placed"
		var world: Node2D = basket.meadow.world
		if get_parent() != world:
			reparent(world)
		z_index = 0
		position = at
		sprite.scale = Vector2.ONE * _size()
		Sfx.play("drop", 0.95, 0.05)
		var t := create_tween()
		t.tween_property(sprite, "scale", Vector2(0.56, 0.44), 0.08)
		t.tween_property(sprite, "scale", Vector2.ONE * 0.5, 0.18).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
		Fx.sparkles(basket.meadow.fx, at + Vector2(0, -20), 5, 40)

	func world_point() -> Vector2:
		## where it is in meadow coordinates
		return world_pos()

	func hit_test(p: Vector2) -> bool:
		var c := world_pos() + Vector2(0, -24 if state == "basket" else -40)
		return p.distance_to(c) < (34.0 if state == "basket" else 52.0)

	func touch_begin(p: Vector2) -> void:
		_press = p
		_moved = false
		if state == "basket":
			_pick_up(p)

	func touch_move(p: Vector2) -> void:
		if state == "placed" and p.distance_to(_press) > 16.0:
			_pick_up(p)
		if state == "held":
			_moved = true
			global_position = basket.meadow.world.to_global(p + Vector2(0, 30))

	func touch_end(p: Vector2) -> void:
		if state == "held":
			basket.place(self, p + Vector2(0, 30))
		elif state == "placed":
			_tapped()

	func _pick_up(p: Vector2) -> void:
		state = "held"
		var overlay: Node2D = basket.meadow.overlay
		reparent(overlay)
		z_index = 85
		sprite.scale = Vector2.ONE * 0.55
		Sfx.play("pickup")
		touch_move(p)

	func _tapped() -> void:
		match id:
			"plant":
				var t := create_tween()
				for a in [0.12, -0.09, 0.05, 0.0]:
					t.tween_property(self, "rotation", a, 0.14).set_trans(Tween.TRANS_SINE)
				Fx.sparkles(basket.meadow.fx, position + Vector2(0, -60), 6, 40, Color(1, 0.85, 0.92))
				Sfx.play("sparkle", 1.2, 0.05, -6.0)
			"lantern":
				var t := create_tween()
				t.tween_property(self, "rotation", 0.1, 0.12)
				t.tween_property(self, "rotation", 0.0, 0.4).set_trans(Tween.TRANS_ELASTIC).set_ease(Tween.EASE_OUT)
				Sfx.play("chime", 1.4, 0.03, -8.0)
			"ball":
				roll()

	func roll() -> void:
		## a kick: it rolls a little way over the grass (never into the water), spinning
		var dir := Vector2(randf_range(-1, 1), randf_range(-0.35, 0.35)).normalized()
		var to := position + dir * randf_range(110, 170)
		to = Vector2(clampf(to.x, DecorBasket.AREA.position.x, DecorBasket.AREA.end.x), clampf(to.y, DecorBasket.AREA.position.y + 60, DecorBasket.AREA.end.y))
		to = Pond.shore(to)
		Sfx.play("pop", 0.8, 0.05)
		var t := create_tween().set_parallel()
		t.tween_property(self, "position", to, 0.7).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		t.tween_property(sprite, "rotation", sprite.rotation + signf(dir.x + 0.01) * TAU * 1.3, 0.7).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		Log.event("ball_rolled")
		basket.meadow.ball_moved(self, to)

	func _process(_delta: float) -> void:
		if id == "lantern":
			var dark: float = basket.meadow.time.darkness() if basket.meadow and basket.meadow.time else 0.0
			var on := dark if state != "basket" else dark * 0.5
			glow.modulate.a = on * (0.8 + 0.08 * sin(Time.get_ticks_msec() / 1000.0 * 3.0))
			glow.scale = Vector2.ONE * (1.4 + 0.3 * on)
