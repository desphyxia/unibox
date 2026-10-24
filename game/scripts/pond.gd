class_name Pond
extends Node2D
## The pond: the second place, at the end of the sandy path east of the meadow (world x 1024..2048). The water is an
## oval; creatures never walk into it (shore() moves a spot in front of it). A tap on the water makes ripples and a
## soft bloop, and main.gd sends a creature to drink there; shimmer() makes the water glint (variant A's thirst cue).

signal tapped(p: Vector2)

const CENTRE := Vector2(1620, 596)       ## the middle of the water, world coordinates
const RX := 272.0                        ## the water's half width and half depth, on screen
const RY := 72.0

var _ripples := []                       ## [position, age, size]
var _shimmer := 0.0
var _t := 0.0


func _ready() -> void:
	position = CENTRE                          # (the water itself is in the backdrop, meadow_east.png)


static func contains(p: Vector2, margin := 0.0) -> bool:
	## on the water (margin: this much round it too)
	var d := p - CENTRE
	return pow(d.x / (RX + margin), 2.0) + pow(d.y / (RY + margin * 0.45), 2.0) <= 1.0


static func _front(x: float, extra := 0.0) -> float:
	## the water's front edge at x (where its shore is nearest the viewer)
	var dx := clampf(x - CENTRE.x, -RX * 0.999, RX * 0.999)
	return CENTRE.y + RY * sqrt(1.0 - pow(dx / RX, 2.0)) + extra


static func shore(p: Vector2) -> Vector2:
	## a spot for a creature's feet: p itself if it is dry, or the shore in front of the water there
	if not contains(p, 34.0):
		return p
	var x := clampf(p.x, CENTRE.x - RX - 30.0, CENTRE.x + RX + 30.0)
	if absf(x - CENTRE.x) >= RX:
		return Vector2(x, maxf(p.y, CENTRE.y + 20.0))
	return Vector2(x, _front(x, 20.0))


static func drink_spot(p: Vector2) -> Vector2:
	## where a creature stands to drink near p: on the front shore, its head over the water
	var x := clampf(p.x, CENTRE.x - RX * 0.75, CENTRE.x + RX * 0.75)
	return Vector2(x, _front(x, 14.0))


func ripple(p: Vector2, size := 1.0) -> void:
	_ripples.append([p - position, 0.0, size])
	queue_redraw()


func shimmer(seconds := 3.0) -> void:
	_shimmer = maxf(_shimmer, seconds)


func tap(p: Vector2) -> void:
	ripple(p)
	ripple(p + Vector2(randf_range(-10, 10), 2), 0.6)
	Sfx.play("bloop", randf_range(0.9, 1.15), 0.05, -3.0)
	Log.event("water_tap")
	tapped.emit(p)


func _process(delta: float) -> void:
	_t += delta
	_shimmer = maxf(0.0, _shimmer - delta)
	for r in _ripples:
		r[1] += delta
	_ripples = _ripples.filter(func(r): return r[1] < 1.6)
	if not _ripples.is_empty() or _shimmer > 0.0:
		queue_redraw()


func _draw() -> void:
	# ripples: rings spreading out on the water, flattened like the water
	for r in _ripples:
		var age: float = r[1]
		for k in 2:
			var a := age - k * 0.25
			if a <= 0.0:
				continue
			var rad: float = (10.0 + a * 62.0) * r[2]
			var alpha := 0.75 * (1.0 - a / 1.35)
			if alpha <= 0.0:
				continue
			draw_set_transform(r[0], 0.0, Vector2(1.0, 0.34))
			draw_arc(Vector2.ZERO, rad, 0.0, TAU, 40, Color(1, 1, 1, alpha), 3.0, true)
	draw_set_transform(Vector2.ZERO)
	# the shimmer: glints twinkling across the water
	if _shimmer > 0.0:
		var fade := clampf(_shimmer, 0.0, 1.0)
		for i in 9:
			var a := TAU * i / 9.0 + 0.7
			var pos := Vector2(cos(a) * RX * 0.62 * (0.4 + 0.6 * fposmod(i * 0.37, 1.0)), sin(a) * RY * 0.5)
			var tw := 0.5 + 0.5 * sin(_t * 5.0 + i * 1.9)
			var c := Color(1, 1, 0.95, 0.85 * tw * fade)
			draw_line(pos - Vector2(9, 0) * tw, pos + Vector2(9, 0) * tw, c, 2.5, true)
			draw_line(pos - Vector2(0, 6) * tw, pos + Vector2(0, 6) * tw, c, 2.5, true)
