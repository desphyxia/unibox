class_name Music
extends Node
## The background music (res://music, made by art/generators/music.py): a day loop and a night lullaby, both playing
## all the time and crossfaded with island time (the lullaby comes in as dusk falls and goes at dawn). Softer under the
## rain. The parent area can turn it off (Game.music). On the web it starts with the first touch, as browsers require.

const DAY_DB := -11.0
const NIGHT_DB := -12.0

var meadow: Node2D
var _day := AudioStreamPlayer.new()
var _night := AudioStreamPlayer.new()
var _level := 0.0                        ## fades in at the start


func _ready() -> void:
	for p in [[_day, "day"], [_night, "night"]]:
		var s := load("res://music/%s.wav" % p[1]) as AudioStreamWAV
		if s == null:
			continue
		s = s.duplicate()
		s.loop_mode = AudioStreamWAV.LOOP_FORWARD
		s.loop_begin = 0
		s.loop_end = int(s.get_length() * s.mix_rate)
		(p[0] as AudioStreamPlayer).stream = s
		(p[0] as AudioStreamPlayer).volume_db = -80.0
		add_child(p[0])
		(p[0] as AudioStreamPlayer).play()


func _process(delta: float) -> void:
	_level = move_toward(_level, 1.0 if Game.music else 0.0, delta / 4.0)
	var dark: float = meadow.time.darkness() if meadow and meadow.time else 0.0
	var rain: float = meadow.weather.amount if meadow and meadow.weather else 0.0
	var under := 1.0 - 0.35 * rain
	_day.volume_db = _db((1.0 - dark) * _level * under) + DAY_DB
	_night.volume_db = _db(dark * _level * under) + NIGHT_DB


static func _db(v: float) -> float:
	return linear_to_db(maxf(v, 0.0001))
