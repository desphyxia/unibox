class_name Weather
extends Node2D
## One gentle rain shower a session (docs/first-ten-minutes.md: "a soft rain at some point after minute 8"): when
## island time reaches RAIN_AT, the light dims a little, soft rain falls over whichever place is in view (with its
## sound), drops ripple the pond, the creatures look up, and when it stops a rainbow fades in over the sky and away.
## main.gd adds it to the meadow (the rainbow sits in the sky behind everything) and a layer for the falling rain.

signal rain_started
signal rain_stopped

const RAIN_AT := 16.0                    ## island hour (06:00 + 8 minutes at 1.25 island hours a minute)
const DIM := Color(0.86, 0.88, 0.97)     ## the light under the rain clouds
const DROPS := 140

var meadow: Node2D
var rain_seconds := 32.0                 ## how long it rains (a test makes it shorter)
var raining := false
var amount := 0.0                        ## how heavy, easing in and out (0 to 1)
var rainbow := 0.0                       ## how strong the rainbow is (0 to 1)
var done := false                        ## it has rained this session
var _left := 0.0
var _rainbow_left := 0.0
var _drops: Array[Vector3] = []          ## x, y in the screen (0..1), speed
var _layer := CanvasLayer.new()
var _fall := Node2D.new()
var _sound := AudioStreamPlayer.new()


func _ready() -> void:
	z_index = -9                         # the rainbow is in the sky, behind the hills
	_layer.layer = 3                     # the rain falls over the meadow, under the corner buttons
	add_child(_layer)
	_fall.draw.connect(_draw_rain)
	_layer.add_child(_fall)
	var s := load("res://sfx/rain.wav") as AudioStreamWAV
	if s:
		s = s.duplicate()
		s.loop_mode = AudioStreamWAV.LOOP_FORWARD
		s.loop_begin = 0
		s.loop_end = int(s.get_length() * s.mix_rate)
		_sound.stream = s
	_sound.volume_db = -60.0
	add_child(_sound)
	for i in DROPS:
		_drops.append(Vector3(randf(), randf(), randf_range(0.8, 1.3)))


func start_rain() -> void:
	if raining:
		return
	raining = true
	done = true
	_left = rain_seconds
	if _sound.stream:
		_sound.play()
	Log.event("rain_start")
	rain_started.emit()


func _stop_rain() -> void:
	raining = false
	_rainbow_left = 26.0
	Log.event("rain_end")
	rain_stopped.emit()


func _process(delta: float) -> void:
	var time: IslandTime = meadow.time if meadow else null
	if not done and time and not time.switching() and time.hour >= RAIN_AT and time.hour < 18.0:
		start_rain()
	if raining:
		_left -= delta
		if _left <= 0.0:
			_stop_rain()
	amount = move_toward(amount, 1.0 if raining else 0.0, delta / 3.0)
	_rainbow_left = maxf(0.0, _rainbow_left - delta)
	rainbow = move_toward(rainbow, 1.0 if _rainbow_left > 3.0 else 0.0, delta / 3.0)
	if time:
		time.weather_dim = Color.WHITE.lerp(DIM, amount)
	if _sound.playing:
		_sound.volume_db = linear_to_db(maxf(amount, 0.0005)) - 4.0
		if amount <= 0.0 and not raining:
			_sound.stop()
	# drops on the pond
	if amount > 0.1 and meadow and meadow.pond and randf() < amount * delta * 9.0:
		var a := randf() * TAU
		var r := sqrt(randf()) * 0.9
		meadow.pond.ripple(Pond.CENTRE + Vector2(cos(a) * Pond.RX * r, sin(a) * Pond.RY * r), randf_range(0.3, 0.55))
	# falling
	for i in _drops.size():
		var d := _drops[i]
		d.y += delta * 1.1 * d.z
		d.x -= delta * 0.08 * d.z
		if d.y > 1.05:
			d = Vector3(randf() * 1.1, -0.05, randf_range(0.8, 1.3))
		if d.x < -0.05:
			d.x += 1.1
		_drops[i] = d
	if amount > 0.0:
		_fall.queue_redraw()
	elif _fall.visible:
		_fall.queue_redraw()
	if rainbow > 0.0 or _was_rainbow:
		queue_redraw()
	_was_rainbow = rainbow > 0.0


var _was_rainbow := false


func _draw_rain() -> void:
	if amount <= 0.0:
		return
	var v := _fall.get_viewport_rect().size
	var col := Color(0.92, 0.95, 1.0, 0.55 * amount)
	var n := int(DROPS * clampf(amount, 0.0, 1.0))
	for i in n:
		var d := _drops[i]
		var p := Vector2(d.x * v.x, d.y * v.y)
		_fall.draw_line(p, p + Vector2(-5.0, 22.0) * d.z, col, 2.0, true)


func _draw() -> void:
	## the rainbow: soft bands in an arch over whichever place is in view
	if rainbow <= 0.0:
		return
	var view_x: float = meadow.pan if meadow else 0.0
	var c := Vector2(view_x + 620.0, 520.0)
	var bands := [Color("ff9aa6"), Color("ffc89a"), Color("fff1a0"), Color("bfe8a8"), Color("a8d8f5"), Color("cdb8f4")]
	for i in bands.size():
		var r := 430.0 - i * 13.0
		draw_arc(c, r, PI * 1.05, PI * 1.95, 64, Color(bands[i], 0.42 * rainbow), 13.0, true)
