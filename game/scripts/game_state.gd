extends Node
## Settings the facilitator sets in the parent area, plus the creature's name. Saved on the device only.

signal name_changed(new_name: String)
signal settings_changed

const SAVE_PATH := "user://prototype.cfg"
const TEMPERAMENTS := ["calm", "playful", "curious"]

## Where each kind of creature lives. Amphibious is for animals at home both on land and in water (frogs, crocodiles,
## seals, penguins). Every kind belongs to exactly one habitat; a habitat can be empty until its first creature is made.
const HABITATS := ["land", "sea", "air", "amphibious"]
const HABITAT_NAMES := {"land": "Land", "sea": "Sea", "air": "Air", "amphibious": "Amphibious"}
const KIND_HABITAT := {
	"fox": "land",
	"unicorn": "land",         # its wings are an optional trait, so it stays a land creature
	"collie": "land",
}

var variant := "A"            ## "A": visible needs (cues), "B": no visible needs
var kind := "fox"             ## this session's kind of creature: "fox", "unicorn" or "collie" (creatures/<kind>/)
var pick := "child"           ## who decides it: "child" (three bubbles at the start) or a kind the facilitator sets
var temperament := "playful"
var creature_name := ""
var music := true             ## the background music (the parent area can turn it off)


func _ready() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(SAVE_PATH) == OK:
		variant = cfg.get_value("session", "variant", variant)
		kind = cfg.get_value("session", "kind", kind)
		pick = cfg.get_value("session", "pick", pick)
		temperament = cfg.get_value("session", "temperament", temperament)
		creature_name = cfg.get_value("creature", "name", "")
		music = cfg.get_value("session", "music", music)


func save() -> void:
	var cfg := ConfigFile.new()
	cfg.set_value("session", "variant", variant)
	cfg.set_value("session", "kind", kind)
	cfg.set_value("session", "pick", pick)
	cfg.set_value("session", "temperament", temperament)
	cfg.set_value("session", "music", music)
	cfg.set_value("creature", "name", creature_name)
	cfg.save(SAVE_PATH)


static func habitat_of(k: String) -> String:
	## the habitat a kind of creature lives in ("land" for a kind not listed yet)
	return KIND_HABITAT.get(k, "land")


static func kinds_in(habitat: String, among: Array = []) -> Array:
	## the kinds (from among, in its order; every listed kind if empty) that live in a habitat
	if among.is_empty():
		among = KIND_HABITAT.keys()
	return among.filter(func(k): return habitat_of(k) == habitat)


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
