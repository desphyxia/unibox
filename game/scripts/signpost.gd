class_name Signpost
extends Touchable
## A wooden signpost by the path, with a picture of where it leads (a drop of water to the pond, the apple tree back to
## the meadow). A tap sends the child's creature there, and the view follows (main.gd travel()).

signal pressed(to: String)

var to := "pond"                        ## where it leads: "pond" or "meadow"
var _sprite := Sprite2D.new()
var _icon := Sprite2D.new()
var _t := 0.0


func _init(p_to: String, at: Vector2) -> void:
	to = p_to
	position = at


func _ready() -> void:
	touch_priority = 25
	var left := to == "meadow"
	_sprite.texture = load("res://art/meadow3d/sign.png")
	_sprite.centered = false
	_sprite.scale = Vector2(-0.5 if left else 0.5, 0.5)
	_sprite.offset = -Vector2(40, 146) * 2.0
	add_child(_sprite)
	_icon.texture = load("res://art/meadow/icon_water.svg" if to == "pond" else "res://art/meadow/icon_tree.svg")
	_icon.scale = Vector2.ONE * 0.36
	_icon.position = Vector2(-8.0 if left else 8.0, -100)
	add_child(_icon)


func hit_test(p: Vector2) -> bool:
	return Rect2(position + Vector2(-60, -150), Vector2(120, 160)).has_point(p)


func touch_end(p: Vector2) -> void:
	if hit_test(p):
		Sfx.play("pop", 1.1, 0.03)
		var t := create_tween()
		t.tween_property(self, "rotation", 0.08 if to == "pond" else -0.08, 0.08)
		t.tween_property(self, "rotation", 0.0, 0.25).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
		pressed.emit(to)


func _process(delta: float) -> void:
	_t += delta
	_icon.position.y = -100 + sin(_t * 2.4) * 2.5          # the picture bobs a little, to invite a tap
