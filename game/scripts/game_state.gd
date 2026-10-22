extends Node
## Settings the facilitator sets in the parent area, plus the creature's name. Saved on the device only.

signal name_changed(new_name: String)
signal settings_changed

const SAVE_PATH := "user://prototype.cfg"
const TEMPERAMENTS := ["calm", "playful", "curious"]

var variant := "A"            ## "A": visible needs (cues), "B": no visible needs
var kind := "fox"             ## the kind of creature that hatches: "fox" or "unicorn" (creatures/<kind>/)
var temperament := "playful"
var creature_name := ""
var music := true             ## the background music (the parent area can turn it off)


func _ready() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(SAVE_PATH) == OK:
		variant = cfg.get_value("session", "variant", variant)
		kind = cfg.get_value("session", "kind", kind)
		temperament = cfg.get_value("session", "temperament", temperament)
		creature_name = cfg.get_value("creature", "name", "")
		music = cfg.get_value("session", "music", music)


func save() -> void:
	var cfg := ConfigFile.new()
	cfg.set_value("session", "variant", variant)
	cfg.set_value("session", "kind", kind)
	cfg.set_value("session", "temperament", temperament)
	cfg.set_value("session", "music", music)
	cfg.set_value("creature", "name", creature_name)
	cfg.save(SAVE_PATH)


func set_creature_name(n: String) -> void:
	creature_name = n.strip_edges().left(16)
	save()
	name_changed.emit(creature_name)


func set_setting(key: String, value: String) -> void:
	set(key, value)
	save()
	settings_changed.emit()


## A new child: forget the creature (one session per child); keep the facilitator's settings.
func new_session() -> void:
	creature_name = ""
	save()
