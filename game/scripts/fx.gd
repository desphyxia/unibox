class_name Fx
## Small one-shot effects: rising hearts, sparkles, a soft flash. Each cleans itself up.

const HEART := preload("res://art/meadow/heart.svg")
const SPARKLE := preload("res://art/meadow/sparkle.svg")


static func glow_texture(color: Color, size := 128) -> GradientTexture2D:
	var g := Gradient.new()
	g.set_color(0, color)
	g.set_color(1, Color(color, 0.0))
	var t := GradientTexture2D.new()
	t.gradient = g
	t.fill = GradientTexture2D.FILL_RADIAL
	t.fill_from = Vector2(0.5, 0.5)
	t.fill_to = Vector2(1.0, 0.5)
	t.width = size
	t.height = size
	return t


static func hearts(parent: Node, pos: Vector2, n := 3, spread := 40.0) -> void:
	for i in n:
		var s := Sprite2D.new()
		s.texture = HEART
		s.scale = Vector2.ONE * 0.1
		s.position = pos + Vector2(randf_range(-spread, spread), randf_range(-10, 10))
		parent.add_child(s)
		var size := randf_range(0.42, 0.62)
		var t := s.create_tween()
		t.tween_interval(i * 0.12)
		t.tween_property(s, "scale", Vector2.ONE * size, 0.22).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
		t.parallel().tween_property(s, "position", s.position + Vector2(randf_range(-30, 30), -110 - randf() * 40), 1.3).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_OUT)
		t.parallel().tween_property(s, "modulate:a", 0.0, 0.5).set_delay(0.8)
		t.tween_callback(s.queue_free)


static func sparkles(parent: Node, pos: Vector2, n := 8, radius := 70.0, color := Color(1, 1, 1)) -> void:
	for i in n:
		var s := Sprite2D.new()
		s.texture = SPARKLE
		s.modulate = color
		s.position = pos
		s.scale = Vector2.ONE * 0.05
		parent.add_child(s)
		var a := TAU * i / n + randf_range(-0.3, 0.3)
		var d := radius * randf_range(0.6, 1.1)
		var size := randf_range(0.35, 0.7)
		var t := s.create_tween().set_parallel()
		t.tween_property(s, "position", pos + Vector2(cos(a), sin(a) * 0.8) * d, 0.6).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
		t.tween_property(s, "scale", Vector2.ONE * size, 0.25)
		t.tween_property(s, "rotation", randf_range(-1.5, 1.5), 0.8)
		t.tween_property(s, "modulate:a", 0.0, 0.45).set_delay(0.4)
		t.chain().tween_callback(s.queue_free)


static func flash(parent: Node, pos: Vector2, color := Color(1, 0.98, 0.9, 0.95), size := 3.0) -> void:
	var s := Sprite2D.new()
	s.texture = glow_texture(color, 256)
	s.position = pos
	s.scale = Vector2.ONE * 0.2
	parent.add_child(s)
	var t := s.create_tween().set_parallel()
	t.tween_property(s, "scale", Vector2.ONE * size, 0.5).set_trans(Tween.TRANS_QUAD).set_ease(Tween.EASE_OUT)
	t.tween_property(s, "modulate:a", 0.0, 0.7).set_delay(0.15)
	t.chain().tween_callback(s.queue_free)
