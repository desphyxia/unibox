class_name Lantern
extends Node2D
## A lantern on a post in the meadow: dark by day, glowing warm from dusk (docs/first-ten-minutes.md, minute 8-10).

var meadow: Node2D
var _glow := Sprite2D.new()
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


func _process(delta: float) -> void:
	_t += delta
	var dark: float = meadow.time.darkness() if meadow and meadow.time else 0.0
	_glow.modulate.a = dark * (0.82 + 0.08 * sin(_t * 3.0 + position.x))
	_glow.scale = Vector2.ONE * (1.3 + 0.4 * dark)
