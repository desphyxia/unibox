class_name NameTag
extends Touchable
## A small tag floating above the creature: a paw until a parent names it, then the paw plus the name.
## Tapping it opens the parental gate and the name field (never blocks play). Tags over creatures standing close
## together stack up instead of covering each other.

signal pressed

const PAW := preload("res://art/meadow/paw.svg")

var follow: Creature
var text := ""
var font: Font
var _t := 0.0
var _size := Vector2(52, 52)


func _ready() -> void:
	touch_priority = 40
	z_index = 90
	add_to_group("name_tags")
	font = ThemeDB.fallback_font


func set_text(s: String) -> void:
	text = s
	queue_redraw()


func hit_test(p: Vector2) -> bool:
	return Rect2(position - _size / 2.0, _size).grow(14).has_point(p)


func touch_end(p: Vector2) -> void:
	if hit_test(p):
		Sfx.play("pop")
		pressed.emit()


func _process(delta: float) -> void:
	_t += delta
	if follow and is_instance_valid(follow):
		var top := follow.top_world()
		var goal := Vector2(follow.position.x, top.y - 34)
		# step above any earlier tag it would cover
		for t in get_tree().get_nodes_in_group("name_tags"):
			if t == self or t.get_instance_id() > get_instance_id() or not t.visible:
				continue
			var other := t as NameTag
			if absf(goal.x - other.position.x) < (_size.x + other._size.x) / 2.0 + 8.0 and absf(goal.y - other.position.y) < _size.y + 6.0:
				goal.y = other.position.y - _size.y - 8.0
		position = position.lerp(goal + Vector2(0, sin(_t * 2.2) * 4.0), minf(1.0, delta * 10.0))


func _draw() -> void:
	var fs := 24
	var tw := font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs).x if text != "" else 0.0
	_size = Vector2(52 + (tw + 14 if text != "" else 0), 52)
	var r := Rect2(-_size / 2.0, _size)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(1, 1, 1, 0.92)
	sb.set_corner_radius_all(26)
	sb.shadow_color = Color(0.35, 0.25, 0.45, 0.18)
	sb.shadow_size = 6
	sb.shadow_offset = Vector2(0, 3)
	draw_style_box(sb, r)
	draw_texture_rect(PAW, Rect2(r.position + Vector2(8, 8), Vector2(36, 36)), false, Color(1, 1, 1, 0.9 if text != "" else 0.55))
	if text != "":
		draw_string(font, r.position + Vector2(50, 34), text, HORIZONTAL_ALIGNMENT_LEFT, -1, fs, Color(0.35, 0.2, 0.33))
