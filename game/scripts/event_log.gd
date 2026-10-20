extends Node
## The playtest's local event log (docs/first-ten-minutes.md section 3): one tab-separated line per event, on the device
## only, read by hand. No network, no identifiers: seconds since session start, variant, creature kind, event, detail.

var path := ""
var _file: FileAccess
var _start_ms := 0


func start_session() -> void:
	end_session()
	DirAccess.make_dir_recursive_absolute("user://logs")
	var stamp := Time.get_datetime_string_from_system().replace(":", "").replace("-", "").replace("T", "-")
	path = "user://logs/session-%s.tsv" % stamp
	_file = FileAccess.open(path, FileAccess.WRITE)
	_start_ms = Time.get_ticks_msec()
	if _file:
		_file.store_line("seconds\tvariant\tkind\tevent\tdetail")
	event("session_start", "temperament=" + Game.temperament)


func seconds() -> float:
	return (Time.get_ticks_msec() - _start_ms) / 1000.0


func event(ev: String, detail := "") -> void:
	var line := "%.1f\t%s\t%s\t%s\t%s" % [seconds(), Game.variant, Game.kind, ev, detail]
	print("LOG ", line)
	if _file:
		_file.store_line(line)
		_file.flush()


func read_all() -> String:
	if path == "" or not FileAccess.file_exists(path):
		return "(no log yet)"
	if _file:
		_file.flush()
	return FileAccess.get_file_as_string(path)


func end_session() -> void:
	if _file:
		event("session_end")
		_file.close()
		_file = null


func _notification(what: int) -> void:
	if what == NOTIFICATION_WM_CLOSE_REQUEST or what == NOTIFICATION_APPLICATION_PAUSED:
		if _file:
			event("app_left" if what == NOTIFICATION_APPLICATION_PAUSED else "session_end")
			_file.flush()
