class_name SkyButton
extends Control
## The sun or the moon in the top-left corner. Tap the sun and the island hurries on to night (the creature goes to
## sleep); tap the moon and morning comes. main.gd routes the taps here; the drawing is all code.

const SIZE := 84.0
const SUN := Color(1.0, 0.8, 0.28)
const SUN_CORE := Color(1.0, 0.92, 0.55)
const MOON := Color(0.97, 0.95, 0.82)
const NIGHT_DISC := Color(0.3, 0.32, 0.55, 0.55)
const DAY_DISC := Color(1, 1, 1, 0.42)

var time: IslandTime
var _m := 0.0                          ## 0 shows the sun, 1 the moon
var _spin := 0.0
var _pop := 1.0


func _ready() -> void:
	size = Vector2(SIZE, SIZE)
	mouse_filter = Control.MOUSE_FILTER_IGNORE        ## main.gd routes the touches
	get_viewport().size_changed.connect(_place)
	_place()
	if time:
		_m = 1.0 if time.is_night() else 0.0


func _place() -> void:
	position = Vector2(12, 12)


func hit(screen: Vector2) -> bool:
	return Rect2(position, size).grow(12).has_point(screen)


func tap() -> void:
	if time == null or time.switching():
		return
	var to_night := not time.is_night()
	time.switch_sky()
	Log.event("sky_switch", "night" if to_night else "day")
	Sfx.play("chime" if to_night else "sparkle", 0.9 if to_night else 1.1, 0.03, -3.0)
	var t := create_tween()
	t.tween_property(self, "_pop", 0.82, 0.08)
	t.tween_property(self, "_pop", 1.0, 0.3).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)


func _process(delta: float) -> void:
	if time == null:
		return
	var goal := 1.0 if time.is_night() else 0.0
	_m = move_toward(_m, goal, delta * 2.2)
	_spin += delta * 0.25
	queue_redraw()


func _draw() -> void:
	var c := size / 2.0
	var e := _m * _m * (3.0 - 2.0 * _m)
	draw_circle(c, SIZE * 0.5, DAY_DISC.lerp(NIGHT_DISC, e), true, -1.0, true)
	# the two swap with a little turn: the sun shrinks away as the moon grows, and back
	var s_sun := (1.0 - e) * _pop
	var s_moon := e * _pop
	if s_sun > 0.02:
		draw_set_transform(c, _spin - e * 1.5, Vector2.ONE * s_sun)
		for i in 8:
			var a := TAU * i / 8.0
			var d := Vector2(cos(a), sin(a))
			draw_line(d * 22.0, d * 31.0, SUN, 6.0, true)
			draw_circle(d * 31.0, 3.0, SUN, true, -1.0, true)
			draw_circle(d * 22.0, 3.0, SUN, true, -1.0, true)
		draw_circle(Vector2.ZERO, 17.0, SUN, true, -1.0, true)
		draw_circle(Vector2(-4, -4), 9.0, SUN_CORE, true, -1.0, true)
	if s_moon > 0.02:
		draw_set_transform(c, (1.0 - e) * -1.5, Vector2.ONE * s_moon)
		var moon := _crescent(24.0, 13.0, -0.7)
		draw_colored_polygon(moon, MOON)
		moon.append(moon[0])
		draw_polyline(moon, MOON, 1.0, true)      ## a soft edge
		for st in [[Vector2(14, -14), 3.2], [Vector2(20, 6), 2.2]]:
			_star(st[0], st[1])
	draw_set_transform(Vector2.ZERO)


func _crescent(r: float, off: float, ang: float) -> PackedVector2Array:
	## a disc of radius r with an equal disc, shifted by off toward ang, cut away
	var al := acos(clampf(off / (2.0 * r), -1.0, 1.0))
	var dir := Vector2(cos(ang), sin(ang))
	var inner := dir * off
	var pts := PackedVector2Array()
	var n := 28
	for i in n + 1:
		var a := lerpf(al, TAU - al, float(i) / n) + ang
		pts.append(Vector2(cos(a), sin(a)) * r)
	for i in range(1, n):
		var a := lerpf(PI + al, PI - al, float(i) / n) + ang
		pts.append(inner + Vector2(cos(a), sin(a)) * r)
	return pts


func _star(p: Vector2, r: float) -> void:
	var pts := PackedVector2Array()
	for i in 8:
		var a := TAU * i / 8.0 - PI / 2.0
		pts.append(p + Vector2(cos(a), sin(a)) * (r * 2.2 if i % 2 == 0 else r * 0.7))
	draw_colored_polygon(pts, MOON)
	pts.append(pts[0])
	draw_polyline(pts, MOON, 1.0, true)
