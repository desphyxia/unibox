class_name ParentUI
extends CanvasLayer
## Everything for grown-ups, behind a parental gate: a quiet corner button (press and hold), a question a young child
## can't read, then the parent area (name, needs variant, temperament, island-time speed, new session, log file).
## Tapping the creature's name tag goes through the same gate straight to the name field.

signal new_session_requested
signal time_speed_changed(speed: float)
signal second_fox_requested
signal compare_requested

const WORDS := ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
const HOLD_SECONDS := 1.2
const INK := Color(0.29, 0.18, 0.28)
const ACCENT := Color(0.85, 0.34, 0.5)

var blocking := false               ## true while a gate or panel is open: the meadow ignores touches
var corner := Control.new()
var _hold := 0.0
var _holding := false
var _modal: Control
var _name_edit: LineEdit
var _naming: Creature = null           ## whose name the field edits (null: the child's first creature, Game.creature_name)
var _time_speed := 1.0


func _ready() -> void:
	layer = 10
	corner.custom_minimum_size = Vector2(56, 56)
	corner.size = Vector2(56, 56)
	corner.mouse_filter = Control.MOUSE_FILTER_STOP
	corner.gui_input.connect(_corner_input)
	corner.draw.connect(_draw_corner)
	add_child(corner)
	get_viewport().size_changed.connect(_place_corner)
	_place_corner()


func corner_rect() -> Rect2:
	return Rect2(corner.position, corner.size).grow(10)


func _place_corner() -> void:
	corner.position = Vector2(get_viewport().get_visible_rect().size.x - 68, 12)


func _corner_input(e: InputEvent) -> void:
	if e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT:
		_holding = e.pressed
		if not e.pressed:
			_hold = 0.0
			corner.queue_redraw()


func _process(delta: float) -> void:
	if _holding and _modal == null:
		_hold += delta
		corner.queue_redraw()
		if _hold >= HOLD_SECONDS:
			_holding = false
			_hold = 0.0
			corner.queue_redraw()
			gate(open_panel)


func _draw_corner() -> void:
	var c := corner.size / 2.0
	corner.draw_circle(c, 22, Color(1, 1, 1, 0.38))
	for i in 3:
		corner.draw_circle(c + Vector2((i - 1) * 9, 0), 3, Color(INK, 0.45))
	if _hold > 0.0:
		corner.draw_arc(c, 24, -PI / 2, -PI / 2 + TAU * _hold / HOLD_SECONDS, 32, ACCENT, 4.0, true)


# ------------------------------------------------------------------ building blocks
func _panel_box(min_w := 520.0) -> VBoxContainer:
	_close()
	blocking = true
	var dim := ColorRect.new()
	dim.color = Color(0.2, 0.12, 0.22, 0.45)
	dim.set_anchors_preset(Control.PRESET_FULL_RECT)
	dim.mouse_filter = Control.MOUSE_FILTER_STOP
	add_child(dim)
	_modal = dim
	var center := CenterContainer.new()
	center.set_anchors_preset(Control.PRESET_FULL_RECT)
	dim.add_child(center)
	var panel := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(1.0, 0.98, 0.96)
	sb.set_corner_radius_all(22)
	sb.set_content_margin_all(26)
	sb.shadow_color = Color(0.2, 0.1, 0.2, 0.25)
	sb.shadow_size = 18
	panel.add_theme_stylebox_override("panel", sb)
	panel.custom_minimum_size = Vector2(min_w, 0)
	center.add_child(panel)
	# taller than the screen (the parent area on a phone or iPad in landscape): it scrolls with a finger
	var scroll := ScrollContainer.new()
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	panel.add_child(scroll)
	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 14)
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(box)
	var fit := func():
		var want := box.get_combined_minimum_size()
		var room := get_viewport().get_visible_rect().size.y - 110.0
		scroll.custom_minimum_size = Vector2(want.x, minf(want.y, room))
	box.minimum_size_changed.connect(fit)
	fit.call_deferred()
	return box


func _label(box: Control, text: String, size := 20, color := INK) -> Label:
	var l := Label.new()
	l.text = text
	l.add_theme_font_size_override("font_size", size)
	l.add_theme_color_override("font_color", color)
	l.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	box.add_child(l)
	return l


func _button(box: Control, text: String, cb: Callable, on := false) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(0, 52)
	b.add_theme_font_size_override("font_size", 20)
	for state in ["normal", "hover", "pressed", "focus"]:
		var sb := StyleBoxFlat.new()
		sb.set_corner_radius_all(14)
		sb.set_content_margin_all(10)
		sb.bg_color = ACCENT if on else Color(0.95, 0.9, 0.9)
		if state == "pressed":
			sb.bg_color = sb.bg_color.darkened(0.12)
		if state == "focus":
			sb.bg_color = Color(0, 0, 0, 0)
			sb.border_color = Color(ACCENT, 0.5)
			sb.set_border_width_all(2)
		b.add_theme_stylebox_override(state, sb)
	b.add_theme_color_override("font_color", Color.WHITE if on else INK)
	b.add_theme_color_override("font_hover_color", Color.WHITE if on else INK)
	b.add_theme_color_override("font_pressed_color", Color.WHITE if on else INK)
	b.pressed.connect(cb)
	box.add_child(b)
	return b


func _row(box: Control) -> HBoxContainer:
	var r := HBoxContainer.new()
	r.add_theme_constant_override("separation", 10)
	box.add_child(r)
	return r


func _close() -> void:
	if _modal:
		_modal.queue_free()
		_modal = null
	blocking = false


# ------------------------------------------------------------------ the gate
func gate(on_pass: Callable) -> void:
	## an adult-level question in words; a non-reader can only guess one of four answers
	var a := randi_range(3, 9)
	var b := randi_range(3, 9)
	var answers := [a + b]
	while answers.size() < 4:
		var w := a + b + randi_range(-5, 5)
		if w > 0 and not answers.has(w):
			answers.append(w)
	answers.shuffle()
	var box := _panel_box(460)
	_label(box, "For grown-ups", 26, ACCENT)
	_label(box, "What is %s plus %s?" % [WORDS[a], WORDS[b]], 22)
	var row := _row(box)
	for n in answers:
		var btn := _button(row, str(n), func():
			if n == a + b:
				on_pass.call()
			else:
				_close())
		btn.custom_minimum_size = Vector2(88, 64)
		btn.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_button(box, "Cancel", _close)


# ------------------------------------------------------------------ the parent area
func open_name_only(who: Creature = null) -> void:
	_naming = who
	var box := _panel_box(480)
	var title := "Name the creature"
	if who:
		title = "Name the baby" if who.who.begins_with("baby") else "Name the second %s" % Game.kind
	_label(box, title, 26, ACCENT)
	_name_field(box)
	_button(box, "Done", _close)
	_name_edit.grab_focus()


func _name_field(box: Control) -> void:
	var row := _row(box)
	_name_edit = LineEdit.new()
	_name_edit.text = _naming.pet_name if _naming else Game.creature_name
	_name_edit.placeholder_text = "Type a name"
	_name_edit.max_length = 16
	_name_edit.custom_minimum_size = Vector2(300, 52)
	_name_edit.add_theme_font_size_override("font_size", 22)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color.WHITE
	sb.border_color = Color(ACCENT, 0.45)
	sb.set_border_width_all(2)
	sb.set_corner_radius_all(12)
	sb.set_content_margin_all(10)
	_name_edit.add_theme_stylebox_override("normal", sb)
	_name_edit.add_theme_stylebox_override("focus", sb)
	_name_edit.add_theme_color_override("font_color", INK)
	_name_edit.add_theme_color_override("font_placeholder_color", Color(INK, 0.4))
	_name_edit.add_theme_color_override("caret_color", ACCENT)
	_name_edit.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_name_edit.text_submitted.connect(func(_t): _save_name())
	row.add_child(_name_edit)
	_button(row, "Save", _save_name, true)


func _save_name() -> void:
	var n := _name_edit.text.strip_edges()
	if _naming and is_instance_valid(_naming):
		_naming.set_pet_name(n)
	else:
		Game.set_creature_name(n)
	# the name itself stays out of the log
	Log.event("name_set", "%s,length=%d" % [_naming.who if _naming and is_instance_valid(_naming) else "first", n.length()])
	Sfx.play("chime")
	_close()


func open_panel() -> void:
	_naming = null                         # the parent area's name field is the child's first creature
	var box := _panel_box(620)
	_label(box, "Parent area", 26, ACCENT)
	_label(box, "Creature's name", 18)
	_name_field(box)
	_label(box, "Needs (playtest variant)", 18)
	var r1 := _row(box)
	for v in [["A", "A: visible needs"], ["B", "B: no visible needs"]]:
		var b := _button(r1, v[1], func(): _apply_setting("variant", v[0]), Game.variant == v[0])
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_label(box, "First creature (from the next session)", 18)
	var rk := _row(box)
	for k in [["child", "Child picks"], ["fox", "Fox"], ["unicorn", "Unicorn"], ["collie", "Collie"]]:
		var b := _button(rk, k[1], func(): _apply_setting("pick", k[0]), Game.pick == k[0])
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_label(box, "Temperament", 18)
	var r2 := _row(box)
	for t in Game.TEMPERAMENTS:
		var b := _button(r2, t.capitalize(), func(): _apply_setting("temperament", t), Game.temperament == t)
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_label(box, "Island time", 18)
	var r3 := _row(box)
	for s in [[1.0, "Normal (dusk at 10 min)"], [8.0, "Fast (for a demo)"]]:
		var b := _button(r3, s[1], func():
			_time_speed = s[0]
			time_speed_changed.emit(_time_speed)
			open_panel(), is_equal_approx(_time_speed, s[0]))
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_label(box, "Music", 18)
	var rm := _row(box)
	for m in [[true, "On"], [false, "Off"]]:
		var b := _button(rm, m[1], func():
			Game.music = m[0]
			Game.save()
			Log.event("setting", "music=%s" % ("on" if m[0] else "off"))
			open_panel(), Game.music == m[0])
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var sf := _button(box, "Bring the second %s now (it comes by itself about 4 min after the hatch)" % Game.kind, func():
		_close()
		Log.event("setting", "second_fox=now")
		second_fox_requested.emit())
	sf.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_button(box, "3D creature check and speed test", func():
		_close()
		compare_requested.emit())
	var r4 := _row(box)
	var ns := _button(r4, "New session (next child)", func():
		_close()
		new_session_requested.emit())
	ns.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var cl := _button(r4, "Close", _close, true)
	cl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_button(box, "Show event log", open_log)
	_label(box, "Event log: " + ProjectSettings.globalize_path(Log.path), 13, Color(INK, 0.6))
	Log.event("parent_area_opened")


func open_log() -> void:
	## the session's event log as text, to read or copy out (in a browser the file lives in the browser's storage)
	var box := _panel_box(720)
	_label(box, "Event log (this session)", 26, ACCENT)
	var text := TextEdit.new()
	text.text = Log.read_all()
	text.editable = false
	text.custom_minimum_size = Vector2(660, 340)
	text.add_theme_font_size_override("font_size", 15)
	text.add_theme_color_override("font_readonly_color", INK)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color.WHITE
	sb.set_corner_radius_all(12)
	sb.set_content_margin_all(10)
	text.add_theme_stylebox_override("read_only", sb)
	text.add_theme_stylebox_override("normal", sb)
	box.add_child(text)
	var row := _row(box)
	var status := Label.new()
	var copy_all := func():
		DisplayServer.clipboard_set(text.text)
		status.text = "Copied"
	var cp := _button(row, "Copy all", copy_all, true)
	cp.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var bk := _button(row, "Back", open_panel)
	bk.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	status.add_theme_color_override("font_color", Color(INK, 0.6))
	box.add_child(status)


func _apply_setting(key: String, value: String) -> void:
	Game.set_setting(key, value)
	Log.event("setting", "%s=%s" % [key, value])
	open_panel()
