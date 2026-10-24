extends Node
## Plays the stand-in sound effects (res://sfx, made by art/generators/sfx.py). A small pool so sounds can overlap.

var _streams := {}
var _pool: Array[AudioStreamPlayer] = []
var _next := 0


func _ready() -> void:
	for n in ["chirp", "chirp2", "happy", "sigh", "knock", "crack", "hatch", "pickup", "drop", "munch", "sparkle", "chime", "pop", "splash", "slurp", "bloop", "yawn",
			"collie_chirp", "collie_chirp2", "collie_happy", "collie_sigh", "collie_yawn"]:   # (a kind's own voice: kind_id)
		var s = load("res://sfx/%s.wav" % n)
		if s:
			_streams[n] = s
	for i in 8:
		var p := AudioStreamPlayer.new()
		add_child(p)
		_pool.append(p)


func voiced(kind: String, id: String) -> String:
	## a kind's own version of a creature sound where it has one (the collie's "wuf" for a chirp), else the shared one
	var own := "%s_%s" % [kind, id]
	return own if _streams.has(own) else id


func play(id: String, pitch := 1.0, vary := 0.06, volume_db := 0.0) -> void:
	if not _streams.has(id):
		return
	var p := _pool[_next]
	_next = (_next + 1) % _pool.size()
	p.stream = _streams[id]
	p.pitch_scale = pitch * randf_range(1.0 - vary, 1.0 + vary)
	p.volume_db = volume_db
	p.play()
