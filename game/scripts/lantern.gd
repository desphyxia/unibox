class_name Lantern
extends Node2D
## A lantern on a post in the meadow: dark by day, glowing warm from dusk (docs/first-ten-minutes.md, minute 8-10).

var meadow: Node2D
var _glow := Sprite2D.new()
var _lit := Sprite2D.new()                       ## the lantern with its lamp lit, faded in as night falls
var _t := 0.0


func _ready() -> void:
	_glow.texture = Fx.glow_texture(Color(1.0, 0.86, 0.5, 0.9), 256)
	_glow.position = Vector2(0, -86)                 # the lamp, in meadow3d's lantern
	_glow.modulate.a = 0.0
	add_child(_glow)
	var s := Sprite2D.new()
	s.texture = load("res://art/meadow3d/lantern.png")
	s.centered = false
	s.scale = Vector2.ONE * 0.5
	s.offset = -Vector2(40, 136) * 2.0
	add_child(s)
	_lit.texture = load("res://art/meadow3d/lantern_lit.png")
	_lit.centered = false
	_lit.scale = s.scale
	_lit.offset = s.offset
	_lit.modulate.a = 0.0
	add_child(_lit)


func _process(delta: float) -> void:
	_t += delta
	var dark: float = meadow.time.darkness() if meadow and meadow.time else 0.0
	_glow.modulate.a = dark * (0.82 + 0.08 * sin(_t * 3.0 + position.x))
	_glow.scale = Vector2.ONE * (1.3 + 0.4 * dark)
	Lantern.light_up(_lit, dark, meadow)


static func light_up(lit: CanvasItem, dark: float, meadow: Node2D) -> void:
	## fade a lit lantern in, and keep the night's tint off it, so its lamp shines in the dark
	var c := Color.WHITE
	if meadow and meadow.time and meadow.time.tint:
		var t: Color = meadow.time.tint.color
		c = Color(1.0 / maxf(t.r, 0.2), 1.0 / maxf(t.g, 0.2), 1.0 / maxf(t.b, 0.2))
	lit.modulate = Color(c.r, c.g, c.b, clampf(dark * 1.3, 0.0, 1.0))
