class_name ParentUI
extends CanvasLayer
## Everything for grown-ups, behind a parental gate: a quiet corner button (press and hold), a question a young child
## can't read, then the parent area (name, needs variant, temperament, island-time speed, new session, log file).
## Tapping the creature's name tag goes through the same gate straight to the name field.
## The storybook (open_book) shows the session's story (story.gd, story_text.gd): a cover, a page per moment, an end.

signal new_session_requested
signal time_speed_changed(speed: float)
signal second_fox_requested
signal compare_requested

const WORDS := ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine"]
const HOLD_SECONDS := 1.2
const INK := Color(0.29, 0.18, 0.28)
const ACCENT := Color(0.85, 0.34, 0.5)
const CORNER := 90.0                   ## the corner button's size (screen pixels): easy for a grown-up's finger to find

var blocking := false               ## true while a gate or panel is open: the meadow ignores touches
var corner := Control.new()
var _hold := 0.0
var _holding := false
var _modal: Control
var _name_edit: LineEdit
var _naming: Creature = null           ## whose name the field edits (null: the child's first creature, Game.creature_name)
var _time_speed := 1.0
var story: Story                       ## main.gd sets it
var _book_font: FontVariation
var _book_title: FontVariation
var _book_seen := {}                   ## the pages looked at since the book was opened (for the log)
var _swipe_from = null
var book_at := -1                      ## the page open in the storybook (-1: closed)
var book_photo: Control                ## its picture (a swipe on it turns the page)


func _ready() -> void:
	layer = 10
	corner.custom_minimum_size = Vector2(CORNER, CORNER)
	corner.size = Vector2(CORNER, CORNER)
	corner.mouse_filter = Control.MOUSE_FILTER_STOP
	corner.gui_input.connect(_corner_input)
	corner.draw.connect(_draw_corner)
	add_child(corner)
	get_viewport().size_changed.connect(_place_corner)
	_place_corner()


func corner_rect() -> Rect2:
	return Rect2(corner.position, corner.size).grow(10)


func _place_corner() -> void:
	corner.position = Vector2(get_viewport().get_visible_rect().size.x - CORNER - 12, 10)


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
	var r := CORNER * 0.4
	corner.draw_circle(c, r + 2.0, Color(INK, 0.12), true, -1.0, true)
	corner.draw_circle(c, r, Color(1, 1, 1, 0.62), true, -1.0, true)
	for i in 3:
		corner.draw_circle(c + Vector2((i - 1) * r * 0.42, 0), r * 0.13, Color(INK, 0.6), true, -1.0, true)
	if _hold > 0.0:
		corner.draw_arc(c, r + 4.0, -PI / 2, -PI / 2 + TAU * _hold / HOLD_SECONDS, 48, ACCENT, 6.0, true)


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
	for state in ["normal", "hover", "pressed", "focus", "disabled"]:
		var sb := StyleBoxFlat.new()
		sb.set_corner_radius_all(14)
		sb.set_content_margin_all(10)
		sb.bg_color = ACCENT if on else Color(0.95, 0.9, 0.9)
		if state == "disabled":
			sb.bg_color = Color(0.95, 0.9, 0.9, 0.45)
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
	b.add_theme_color_override("font_disabled_color", Color(INK, 0.3))
	b.pressed.connect(cb)
	box.add_child(b)
	return b


func _row(box: Control) -> HBoxContainer:
	var r := HBoxContainer.new()
	r.add_theme_constant_override("separation", 10)
	box.add_child(r)
	return r


func _close() -> void:
	book_at = -1
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
	var pages := story.pages.size() if story else 0
	var sb := _button(box, "Storybook (%s)" % ("%d %s" % [pages, "page" if pages == 1 else "pages"] if pages > 0 else "starts at the hatch"), func(): open_book(0), true)
	sb.custom_minimum_size.y = 60
	_label(box, "Creature's name", 18)
	_name_field(box)
	_label(box, "Needs (playtest variant)", 18)
	var r1 := _row(box)
	for v in [["A", "A: visible needs"], ["B", "B: no visible needs"]]:
		var b := _button(r1, v[1], func(): _apply_setting("variant", v[0]), Game.variant == v[0])
		b.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_label(box, "First creature (from the next session)", 18)
	var rc := _row(box)
	var cb := _button(rc, "Child picks", func(): _apply_setting("pick", "child"), Game.pick == "child")
	cb.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	for h in Game.HABITATS:                 # then one row per habitat that has a creature to offer
		var kinds: Array = Game.kinds_in(h, KindChooser.KINDS)
		if kinds.is_empty():
			continue
		var rk := _row(box)
		var hl := _label(rk, Game.HABITAT_NAMES[h], 16)
		hl.custom_minimum_size.x = 120
		for k in kinds:
			var b := _button(rk, k.capitalize(), func(): _apply_setting("pick", k), Game.pick == k)
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
		if story and not story.pages.is_empty():
			_confirm_new_session()
			return
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


func _confirm_new_session() -> void:
	## the book lives only in this session: say so before it goes
	var box := _panel_box(560)
	_label(box, "Start a new session?", 26, ACCENT)
	var words := StoryText.new(story)
	_label(box, "This clears %s storybook (%d pages). It isn't kept anywhere else." % [words._own(words.name_of("first")), story.pages.size()], 19)
	var row := _row(box)
	var keep := _button(row, "Keep playing", _close)
	keep.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var look := _button(row, "Open the storybook", func(): open_book(0))
	look.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var go := _button(box, "Clear it and start a new session", func():
		Log.event("storybook_cleared", "pages=%d" % story.pages.size())
		_close()
		new_session_requested.emit(), true)
	go.size_flags_horizontal = Control.SIZE_EXPAND_FILL


# ------------------------------------------------------------------ the storybook
func _fonts() -> void:
	if _book_font:
		return
	var f: FontFile = load("res://fonts/MeadowBook.ttf")
	f.fallbacks = [ThemeDB.fallback_font]      # names in other scripts still show
	var wght := TextServerManager.get_primary_interface().name_to_tag("wght")
	_book_font = FontVariation.new()
	_book_font.base_font = f
	_book_font.variation_opentype = {wght: 420}
	_book_title = FontVariation.new()
	_book_title.base_font = f
	_book_title.variation_opentype = {wght: 640}


func _book_text(box: Control, text: String, size: int, title := false, width := 0.0) -> Label:
	var l := _label(box, text, size)
	l.add_theme_font_override("font", _book_title if title else _book_font)
	l.add_theme_constant_override("line_spacing", 4)
	l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER if title else HORIZONTAL_ALIGNMENT_LEFT
	if width > 0.0:
		l.custom_minimum_size.x = width
		l.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	return l


func book_pages() -> int:
	## the cover, a page per moment, and the end (just the cover while the story hasn't begun)
	return 1 if story == null or story.pages.is_empty() else story.pages.size() + 2


func open_book(i := 0) -> void:
	## one page as a spread: the picture on the left, the words on the right (the game is always landscape)
	_fonts()
	var first_open := _modal == null or not _modal.has_meta("book")
	if first_open:
		_book_seen = {}
		Log.event("storybook_opened", "pages=%d" % (story.pages.size() if story else 0))
	var total := book_pages()
	i = clampi(i, 0, total - 1)
	_book_seen[i] = true
	var words := StoryText.new(story)
	var view := get_viewport().get_visible_rect().size
	const TEXT_W := 300.0
	var ph := minf(420.0, view.y - 280.0)
	var pw := minf(ph / 0.75, view.x - 160.0 - TEXT_W)
	ph = pw * 0.75
	var box := _panel_box(pw + TEXT_W + 40.0)
	_modal.set_meta("book", true)
	book_at = i
	var top := _row(box)
	var tl := _label(top, "Storybook", 16, Color(ACCENT, 0.9))
	tl.autowrap_mode = TextServer.AUTOWRAP_OFF
	tl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var pn := _label(top, "%d of %d" % [i + 1, total], 16, Color(INK, 0.55))
	pn.autowrap_mode = TextServer.AUTOWRAP_OFF
	var spread := HBoxContainer.new()
	spread.add_theme_constant_override("separation", 22)
	box.add_child(spread)
	var pic: Texture2D = null
	var title := ""
	var text := ""
	if story == null or story.pages.is_empty():
		title = "Storybook"
		text = "The story begins when the egg hatches. Every first moment after that gets a page with its own picture."
	elif i == 0:
		title = words.cover_title()
		pic = _cover_picture()
		text = words.cover_line()
	elif i == total - 1:
		title = "The end, for now"
		pic = _last_picture()
		text = words.closing_text()
	else:
		pic = story.picture(story.pages[i - 1])
		text = words.page_text(i - 1)
	book_photo = _photo(pic, Vector2(pw, ph), i)
	spread.add_child(book_photo)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 14)
	col.alignment = BoxContainer.ALIGNMENT_CENTER
	col.custom_minimum_size.x = TEXT_W
	spread.add_child(col)
	if title != "":
		var t := _book_text(col, title, 32, true, TEXT_W)
		t.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	if text != "":
		_book_text(col, text, 23, false, TEXT_W)
	var nav := _row(box)
	var back := _button(nav, "Previous", func(): open_book(i - 1))
	back.disabled = i == 0
	back.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var next := _button(nav, "Next", func(): open_book(i + 1), i < total - 1)
	next.disabled = i >= total - 1
	next.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var done := _button(nav, "Close", func():
		Log.event("storybook_closed", "seen=%d of %d" % [_book_seen.size(), total])
		open_panel())
	done.size_flags_horizontal = Control.SIZE_EXPAND_FILL


func _photo(tex, size: Vector2, i: int) -> Control:
	## the picture, framed like a print pasted in a book; a swipe turns the page
	var frame := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color.WHITE
	sb.set_content_margin_all(8)
	sb.set_corner_radius_all(6)
	sb.shadow_color = Color(0.25, 0.12, 0.2, 0.18)
	sb.shadow_size = 8
	sb.shadow_offset = Vector2(0, 3)
	frame.add_theme_stylebox_override("panel", sb)
	frame.size_flags_horizontal = Control.SIZE_SHRINK_CENTER
	var r := TextureRect.new()
	r.texture = tex if tex else _blank_print()
	r.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	r.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	r.custom_minimum_size = size
	r.mouse_filter = Control.MOUSE_FILTER_IGNORE
	frame.add_child(r)
	frame.mouse_filter = Control.MOUSE_FILTER_STOP
	frame.gui_input.connect(func(e: InputEvent):
		if e is InputEventMouseButton and e.button_index == MOUSE_BUTTON_LEFT:
			if e.pressed:
				_swipe_from = e.position
			elif _swipe_from != null:
				var dx: float = e.position.x - _swipe_from.x
				_swipe_from = null
				if absf(dx) > 70.0:
					open_book(i + (1 if dx < 0.0 else -1)))
	return frame


func _blank_print() -> Texture2D:
	var g := GradientTexture2D.new()
	g.gradient = Gradient.new()
	g.gradient.set_color(0, Color(0.98, 0.93, 0.9))
	g.gradient.set_color(1, Color(0.93, 0.95, 0.88))
	g.fill_to = Vector2(1, 1)
	return g


func _cover_picture() -> Texture2D:
	## the child's first creature: dressed up if it was, else hatched, else its latest picture
	for key in ["dressed", "hatch"]:
		var d := story.page(key)
		if not d.is_empty() and not d["jpg"].is_empty():
			return story.picture(d)
	for k in range(story.pages.size() - 1, -1, -1):
		var p: Dictionary = story.pages[k]
		if p["who"] == "first" and not p["jpg"].is_empty():
			return story.picture(p)
	return _last_picture()


func _last_picture() -> Texture2D:
	for k in range(story.pages.size() - 1, -1, -1):
		if not story.pages[k]["jpg"].is_empty():
			return story.picture(story.pages[k])
	return null
