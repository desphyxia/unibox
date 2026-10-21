class_name IslandTime
extends Node2D
## The island's own clock (not the real one): a session starts at dawn and reaches dusk after about ten minutes,
## then a short night and a new dawn. Tints the meadow and moves a sun and a moon along an arc behind the meadow.

signal dusk
signal switched(night: bool)           ## the sun or moon button hurried the clock on

const START_HOUR := 6.0
const DAY_RATE := 12.5 / 600.0       ## island hours per second by day: 06:00 -> 18:30 in ten minutes
const NIGHT_RATE := DAY_RATE * 5.0   ## nights pass quickly
## (hour, tint) keys; the tint multiplies the whole meadow
const KEYS := [
	[0.0, Color(0.62, 0.64, 0.86)], [5.0, Color(0.66, 0.66, 0.86)], [6.0, Color(1.0, 0.94, 0.92)], [7.0, Color(1.0, 0.98, 0.96)],
	[11.0, Color(1, 1, 1)], [15.5, Color(1.0, 0.98, 0.94)], [18.0, Color(1.0, 0.86, 0.74)], [19.2, Color(0.9, 0.74, 0.82)],
	[20.5, Color(0.64, 0.65, 0.87)], [24.0, Color(0.62, 0.64, 0.86)]]

var hour := START_HOUR
var speed := 1.0                     ## the parent area can run it faster for a demo
var tint: CanvasModulate
var sun := Sprite2D.new()
var moon := Sprite2D.new()
var stars := Node2D.new()
var _dusk_sent := false
var _skip := {}                        ## a quick run of the clock to night or morning: from, to, t, secs


func _ready() -> void:
	z_index = -9
	sun.texture = Fx.glow_texture(Color(1.0, 0.95, 0.78, 1.0), 256)
	add_child(sun)
	var core := Sprite2D.new()
	core.texture = Fx.glow_texture(Color(1.0, 0.99, 0.92, 1.0), 128)
	core.scale = Vector2.ONE * 0.55
	sun.add_child(core)
	moon.texture = Fx.glow_texture(Color(0.93, 0.94, 1.0, 1.0), 256)
	add_child(moon)
	add_child(stars)
	for i in 40:
		var s := Sprite2D.new()
		s.texture = Fx.SPARKLE
		s.position = Vector2(randf_range(-500, 1530), randf_range(-110, 380))
		s.scale = Vector2.ONE * randf_range(0.12, 0.3)
		stars.add_child(s)


func is_night() -> bool:
	## bedtime for the creatures: from 20:00 to dawn
	return hour >= 20.0 or hour < 5.8


func switching() -> bool:
	return not _skip.is_empty()


func switch_sky() -> void:
	## run the clock on to just after bedtime, or to morning, over a couple of seconds
	if switching():
		return
	var to_night := not is_night()
	var to := 20.4 if to_night else 6.4
	if to < hour:
		to += 24.0
	_skip = {"from": hour, "to": to, "t": 0.0, "secs": 2.4}
	switched.emit(to_night)


func tint_at(h: float) -> Color:
	for i in KEYS.size() - 1:
		var a = KEYS[i]
		var b = KEYS[i + 1]
		if h >= a[0] and h <= b[0]:
			return (a[1] as Color).lerp(b[1], smoothstep(a[0], b[0], h))
	return Color(1, 1, 1)


func _arc(h: float, rise: float, set_: float) -> Vector2:
	var u := (h - rise) / (set_ - rise)
	return Vector2(lerpf(-120.0, 1144.0, u), 440.0 - 360.0 * sin(PI * clampf(u, 0.0, 1.0)))


func _process(delta: float) -> void:
	if switching():
		_skip["t"] += delta
		var u := clampf(_skip["t"] / _skip["secs"], 0.0, 1.0)
		hour = lerpf(_skip["from"], _skip["to"], u * u * (3.0 - 2.0 * u))
		if u >= 1.0:
			_skip = {}
	else:
		var day := hour >= 5.5 and hour < 20.5
		hour += delta * speed * (DAY_RATE if day else NIGHT_RATE)
	if hour >= 24.0:
		hour -= 24.0
	if not _dusk_sent and hour >= 18.0 and hour < 20.0:
		_dusk_sent = true
		dusk.emit()
		Log.event("dusk_reached")
	if hour >= 5.0 and hour < 6.0:
		_dusk_sent = false
	if tint:
		tint.color = tint_at(hour)
	sun.position = _arc(hour, 5.6, 19.4)
	sun.scale = Vector2.ONE * 1.1
	sun.modulate.a = clampf(minf(hour - 5.6, 19.4 - hour) * 1.2, 0.0, 0.9)
	var mh := hour + 24.0 if hour < 12.0 else hour
	moon.position = _arc(mh, 19.0, 30.0)
	moon.scale = Vector2.ONE * 0.6
	moon.modulate.a = clampf(minf(mh - 19.0, 30.0 - mh) * 1.2, 0.0, 0.85)
	stars.modulate.a = clampf(minf(mh - 19.5, 29.5 - mh) * 0.8, 0.0, 0.8)


func clock_text() -> String:
	return "%02d:%02d" % [int(hour), int(fmod(hour, 1.0) * 60.0)]
