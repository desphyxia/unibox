class_name CompareView
extends CanvasLayer
## Side by side, for deciding how creatures are made: on the left the fox as it is in the game now (rendered frames), on
## the right the same fox as a live 3D model with shell fur (live_fox.gd), at the same size and camera angle. Buttons:
## every clip the game has (both foxes play it together), close-up, fewer or more fur layers, the colour traits (both
## recolour), back. Drag the live fox to turn it any way. The corner shows frames per second, so it can be judged on the iPad and iPhone.
## Speed test runs through set-ups one after another (no 3D, fur on and off, edge smoothing, the 3D drawn over the whole
## screen or only round the foxes, five foxes as in the game) and lists the frames per second of each.
## The 3D is drawn only in a box round the live foxes, as the game would, not over the whole screen.
## Opened from the parent area; the meadow waits underneath.

signal closed

const PPU := 40.0                       ## screen pixels per model unit at the game's size (640-wide renders at half size)
const INK := Color(0.29, 0.18, 0.28)
const ACCENT := Color(0.85, 0.34, 0.5)
const SPRITE_MB := 30.7                 ## the fox's frames as downloaded (art/tools/size_report.py)

var frames: SpriteFrames
var anim_info := {}
var root := Control.new()
var sprite := AnimatedSprite2D.new()
var box := SubViewportContainer.new()
var view := SubViewport.new()
var cam := Camera3D.new()
var fit_view := true                     ## the 3D box only round the foxes (false: the whole screen)
var crowd: Array[Node3D] = []            ## extra live foxes for the speed test (holders, each with a LiveFox)
## where they stand (screen fractions) and their size: the second adult and three babies
const CROWD := [[0.3, 0.7, 1.0], [0.52, 0.9, 0.68], [0.13, 0.92, 0.68], [0.55, 0.58, 0.68]]
var fox: LiveFox
var spin := Node3D.new()                 ## the drag turns this; the fox's own turns happen inside it
var sprite_facing := 1.0
var _sprite_clip := "idle"
var _zoom := 1.0
var _turn := 0.0                         ## the live fox's own turn, radians
var _auto_turn := false
var _traits_i := 0
var _fps := Label.new()
var _layers_btn: Button
var _fps_avg := 60.0
const LOOKS := [["apricot", "pink"], ["sky", "violet"], ["snow", "blue"], ["mint", "gold"], ["cocoa", "green"], ["lilac", "pink"]]


func _init(p_frames: SpriteFrames, infos: Dictionary) -> void:
	frames = p_frames
	anim_info = infos


func _ready() -> void:
	layer = 20
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_STOP
	root.gui_input.connect(_gui_input)
	add_child(root)
	var bg := TextureRect.new()
	bg.texture = load("res://art/meadow/meadow.svg")
	bg.set_anchors_preset(Control.PRESET_FULL_RECT)
	bg.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_COVERED
	bg.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	bg.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(bg)
	# the rendered fox
	sprite.sprite_frames = frames
	sprite.centered = false
	sprite.play("idle")
	var a: Array = anim_info["idle"]["anchor"]
	sprite.offset = -Vector2(a[0], a[1])
	root.add_child(sprite)
	# the live one, in its own little 3D world drawn over the meadow
	box.stretch = true
	box.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.add_child(box)
	view.own_world_3d = true
	view.transparent_bg = true
	view.msaa_3d = Viewport.MSAA_4X
	box.add_child(view)
	_build_3d()
	_build_ui()
	_apply_look()
	get_viewport().size_changed.connect(_layout)
	_layout()
	Log.event("compare_opened")


func _build_3d() -> void:
	var env := Environment.new()
	env.background_mode = Environment.BG_CLEAR_COLOR
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.95, 0.97, 1.0)
	env.ambient_light_energy = 0.32
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	env.tonemap_exposure = 0.85
	var we := WorldEnvironment.new()
	we.environment = env
	view.add_child(we)
	cam.projection = Camera3D.PROJECTION_ORTHOGONAL
	cam.far = 200.0
	view.add_child(cam)
	view.add_child(spin)
	fox = LiveFox.new()
	spin.add_child(fox)
	var r: Dictionary = fox.meta["camera"]
	var tgt := Vector3(r["center"][0], r["center"][1], r["center"][2])
	var az := deg_to_rad(r["azimuth"])
	var pitch := deg_to_rad(r["pitch"])
	# Blender's camera sits at centre + (sin az cos p, -cos az cos p, sin p) * 40; in Godot's axes that is (x, z, -y)
	cam.position = tgt + Vector3(sin(az) * cos(pitch), sin(pitch), cos(az) * cos(pitch)) * 40.0
	cam.look_at(tgt, Vector3.UP)
	# the render's lights, which ride with the camera, plus one from above and a soft bounce from the front
	for l in [[Vector3(-5, 6, 9), 0.85, Color(1.0, 0.96, 0.9)], [Vector3(8, -2, 3), 0.3, Color(0.95, 0.97, 1.0)], [Vector3(6, 4, 2), 0.22, Color(1.0, 0.92, 1.0)]]:
		var d := DirectionalLight3D.new()
		d.light_energy = l[1]
		d.light_color = l[2]
		cam.add_child(d)
		d.look_at_from_position(l[0], Vector3.ZERO, Vector3.UP)
	var top := DirectionalLight3D.new()
	top.light_energy = 0.18
	view.add_child(top)
	top.look_at_from_position(Vector3(0.5, 11, -0.3), Vector3.ZERO, Vector3(0, 0, -1))


func _button(text: String, cb: Callable, on := false) -> Button:
	var b := Button.new()
	b.text = text
	b.custom_minimum_size = Vector2(0, 46)
	b.add_theme_font_size_override("font_size", 17)
	for state in ["normal", "hover", "pressed", "focus"]:
		var sb := StyleBoxFlat.new()
		sb.set_corner_radius_all(12)
		sb.set_content_margin_all(9)
		sb.bg_color = ACCENT if on else Color(1, 0.98, 0.96, 0.92)
		if state == "pressed":
			sb.bg_color = sb.bg_color.darkened(0.12)
		if state == "focus":
			sb.bg_color = Color(0, 0, 0, 0)
		b.add_theme_stylebox_override(state, sb)
	for c in ["font_color", "font_hover_color", "font_pressed_color", "font_focus_color"]:
		b.add_theme_color_override(c, Color.WHITE if on else INK)
	b.pressed.connect(cb)
	return b


var _bar := HFlowContainer.new()
var _cap_l := Label.new()
var _cap_r := Label.new()


func _build_ui() -> void:
	_bar.add_theme_constant_override("h_separation", 8)
	_bar.add_theme_constant_override("v_separation", 8)
	root.add_child(_bar)
	_bar.add_child(_button("Back to the meadow", func(): close(), true))
	_bar.add_child(_button("Close-up", func():
		_zoom = 2.0 if _zoom == 1.0 else 1.0
		_layout()))
	for c in [["Idle", "idle"], ["Walk", "walk"], ["Eat", "eat"], ["Happy", "happy"], ["Hungry", "hunger"], ["Lie down", "liedown"],
			["Wake up", "wake"], ["Turn", "turn"]]:
		_bar.add_child(_button(c[0], play_clip.bind(c[1])))
	_bar.add_child(_button("Spin", func(): _auto_turn = not _auto_turn))
	_layers_btn = _button(_layers_text(), func():
		_set_shells({4: 6, 6: 8, 8: 12, 12: 0, 0: 4}[fox.shells]))
	_bar.add_child(_layers_btn)
	_bar.add_child(_button("Speed test", speed_test))
	_bar.add_child(_button("Colours", func():
		_traits_i = (_traits_i + 1) % LOOKS.size()
		_apply_look()))
	for l in [_fps, _cap_l, _cap_r]:
		l.add_theme_color_override("font_color", INK)
		l.add_theme_color_override("font_outline_color", Color(1, 1, 1, 0.85))
		l.add_theme_constant_override("outline_size", 6)
		l.add_theme_font_size_override("font_size", 17)
		l.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		l.mouse_filter = Control.MOUSE_FILTER_IGNORE
		root.add_child(l)
	_fps.horizontal_alignment = HORIZONTAL_ALIGNMENT_LEFT
	var mb := FileAccess.get_file_as_bytes(LiveFox.DATA + ".bin").size() / 1.0e6
	_cap_l.text = "Rendered frames (in the game now)\nabout %.0f MB for all the fox's clips" % SPRITE_MB
	_cap_r.text = "Live 3D with shell fur\nevery clip computed live, model about %.1f MB" % mb
	sprite.animation_finished.connect(_sprite_done)


func _layers_text() -> String:
	return "Fur layers: %d" % fox.shells if fox.shells > 0 else "Fur layers: off"


func _set_shells(n: int) -> void:
	for f in _live_foxes():
		f.shells = n
	_layers_btn.text = _layers_text()


func _live_foxes() -> Array[LiveFox]:
	var out: Array[LiveFox] = [fox]
	for h in crowd:
		out.append(h.get_child(0))
	return out


func _apply_look() -> void:
	var t := {"coat": LOOKS[_traits_i][0], "glow": LOOKS[_traits_i][1]}
	sprite.material = Traits.material(t)
	fox.set_traits(t)


func _layout() -> void:
	var v := root.get_viewport_rect().size
	var ground := Vector2(0, v.y * 0.8)
	var ppu := PPU * _zoom
	sprite.scale = Vector2.ONE * 0.5 * _zoom
	sprite.position = Vector2(v.x * 0.27, ground.y)
	# the live fox's ground point lands at the same height on the right
	var g: Array = fox.meta["ground"]
	var tgt := cam.global_position + (-cam.global_transform.basis.z) * 40.0
	var gp := Vector3(g[0], g[1], g[2])
	var rel := cam.global_transform.basis.inverse() * (gp - tgt)   # where the ground point sits in the camera's plane
	var want := Vector2(v.x * 0.73, ground.y)
	# the speed test's extra foxes: a step across the screen is along the camera's right, a step down is toward the
	# camera on the ground (the camera looks down by its pitch, so nearer foxes also draw in front)
	var spots := [[want, 1.0]]
	var right := cam.global_transform.basis.x
	var toward := Vector3(cam.global_transform.basis.z.x, 0.0, cam.global_transform.basis.z.z).normalized()
	var down := sin(deg_to_rad(float(fox.meta["camera"]["pitch"])))
	for i in crowd.size():
		var c: Array = CROWD[i]
		var at := Vector2(v.x * c[0], v.y * c[1])
		spots.append([at, c[2]])
		var d := (at - want) / ppu
		crowd[i].scale = Vector3.ONE * c[2]
		crowd[i].position = gp + right * d.x + toward * (d.y / down) - gp * c[2]
	# the 3D box: round every live fox (one reaches about 5 units either side of its ground point, 7.5 above, 1.5 below)
	var rect := Rect2(Vector2.ZERO, v)
	if fit_view:
		rect = Rect2()
		for s in spots:
			var u: float = ppu * s[1]
			var r := Rect2(s[0] - Vector2(5.0 * u, 7.5 * u), Vector2(10.0 * u, 9.0 * u))
			rect = r if rect.size == Vector2.ZERO else rect.merge(r)
		rect = rect.intersection(Rect2(Vector2.ZERO, v))
	rect = Rect2(rect.position.floor(), rect.size.ceil())
	box.position = rect.position
	box.size = rect.size
	var mid := rect.get_center()
	cam.size = rect.size.y / ppu
	cam.h_offset = rel.x - (want.x - mid.x) / ppu
	cam.v_offset = rel.y + (want.y - mid.y) / ppu
	_bar.position = Vector2(12, 12)
	_bar.size = Vector2(v.x - 24, 0)
	_fps.position = Vector2(14, v.y - 30)
	for i in 2:
		var l: Label = [_cap_l, _cap_r][i]
		l.size = Vector2(v.x * 0.46, 50)
		l.position = Vector2(v.x * (0.27 if i == 0 else 0.73) - l.size.x / 2.0, ground.y + 14)


func _gui_input(e: InputEvent) -> void:
	# drag anywhere on the right half to turn the live fox (touches arrive here as the mouse)
	if e is InputEventMouseMotion and e.button_mask & MOUSE_BUTTON_MASK_LEFT and e.position.x > root.get_viewport_rect().size.x * 0.5:
		_turn += e.relative.x * 0.012
		_auto_turn = false


func _process(delta: float) -> void:
	if _auto_turn:
		_turn += delta * TAU / 4.0
	spin.rotation.y = _turn
	_fps_avg = lerpf(_fps_avg, 1.0 / maxf(delta, 0.0001), 0.05)
	if _testing:
		_fps.text = _status
		return
	_fps.text = "%.0f frames a second · live fox draws %dk triangles (%dk of them fur layers)" % [_fps_avg,
		(fox.triangles + fox.fur_triangles()) / 1000, fox.fur_triangles() / 1000]


# ------------------------------------------------------------------ speed test
## name, live foxes (0 = no 3D at all), fur layers, edge smoothing (MSAA samples), 3D only round the foxes
const SPEED_TESTS := [
	["No 3D fox", 0, 0, 4, true],
	["1 fox, no fur", 1, 0, 4, true],
	["1 fox, 6 fur layers", 1, 6, 4, true],
	["1 fox, 6 layers, 3D over the whole screen", 1, 6, 4, false],
	["1 fox, 6 layers, no edge smoothing", 1, 6, 0, true],
	["5 foxes, no fur", 5, 0, 4, true],
	["5 foxes, 4 layers, 2x smoothing", 5, 4, 2, true],
	["5 foxes, 6 layers", 5, 6, 4, true],
]
const SETTLE := 1.0                      ## seconds before measuring (new shaders get built in the first frames)
var test_seconds := 4.0                  ## measured per set-up
var results := []                        ## [name, frames a second, slowest frame ms, % of frames slower than 20 ms]
var _testing := false
var _status := ""
var _result_panel: PanelContainer


func speed_test() -> void:
	if _testing:
		return
	_testing = true
	_bar.visible = false
	_auto_turn = false
	_turn = 0.0
	if _result_panel:
		_result_panel.queue_free()
		_result_panel = null
	var keep := [fox.shells, view.msaa_3d]
	fox.play("walk")                     # the walk moves the most (legs, tails, head) and never ends
	_sprite_play("walk")
	results.clear()
	for i in SPEED_TESTS.size():
		var t: Array = SPEED_TESTS[i]
		_status = "Speed test %d of %d: %s" % [i + 1, SPEED_TESTS.size(), t[0]]
		_setup(t)
		await get_tree().create_timer(SETTLE).timeout
		var n := 0
		var worst := 0.0
		var slow := 0
		var t0 := Time.get_ticks_usec()
		var last := t0
		while last - t0 < int(test_seconds * 1.0e6):
			await get_tree().process_frame
			var now := Time.get_ticks_usec()
			var ms := (now - last) / 1000.0
			last = now
			n += 1
			worst = maxf(worst, ms)
			slow += 1 if ms > 20.0 else 0
		results.append([t[0], n / ((last - t0) / 1.0e6), worst, 100.0 * slow / maxi(n, 1)])
	_setup(["", 1, keep[0], {Viewport.MSAA_DISABLED: 0, Viewport.MSAA_2X: 2, Viewport.MSAA_4X: 4}.get(keep[1], 4), true])
	fox.play("idle")
	_sprite_play("idle")
	_testing = false
	_bar.visible = true
	_show_results()


func _setup(t: Array) -> void:
	var count: int = t[1]
	var extra := 4 if count == 5 else 0
	while crowd.size() < extra:
		_add_crowd_fox()
	while crowd.size() > extra:
		crowd.pop_back().queue_free()
	box.visible = count > 0
	view.render_target_update_mode = SubViewport.UPDATE_ALWAYS if count > 0 else SubViewport.UPDATE_DISABLED
	for n in [sprite, _cap_l, _cap_r]:
		n.visible = count < 5            # five foxes fill the screen as in the game
	_set_shells(t[2])
	view.msaa_3d = {0: Viewport.MSAA_DISABLED, 2: Viewport.MSAA_2X, 4: Viewport.MSAA_4X}[t[3]]
	fit_view = t[4]
	_layout()


func _add_crowd_fox() -> void:
	var h := Node3D.new()
	var f := LiveFox.new()
	f.shells = fox.shells
	h.add_child(f)
	view.add_child(h)
	crowd.append(h)
	var look: Array = LOOKS[(_traits_i + crowd.size()) % LOOKS.size()]
	f.set_traits({"coat": look[0], "glow": look[1]})
	f.facing = -1.0 if crowd.size() % 2 == 1 else 1.0
	f.play("walk")


func _show_results() -> void:
	var lines := PackedStringArray()
	var p := PanelContainer.new()
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(1, 0.98, 0.96, 0.97)
	sb.set_corner_radius_all(16)
	sb.set_content_margin_all(18)
	p.add_theme_stylebox_override("panel", sb)
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 10)
	p.add_child(col)
	var win := get_window().size
	var head := "Speed test · %s · %s · screen %d×%d" % [OS.get_name(), RenderingServer.get_video_adapter_name(), win.x, win.y]
	lines.append(head)
	var grid := GridContainer.new()
	grid.columns = 4
	grid.add_theme_constant_override("h_separation", 22)
	grid.add_theme_constant_override("v_separation", 4)
	var cells := ["", "frames a second", "slowest frame", "frames slower than 20 ms"]
	for r in results:
		cells.append_array([r[0], "%.0f" % r[1], "%.0f ms" % r[2], "%.0f%%" % r[3]])
		lines.append("%s: %.0f fps, slowest %.0f ms, %.0f%% slow" % [r[0], r[1], r[2], r[3]])
	for i in cells.size():
		var l := Label.new()
		l.text = cells[i]
		l.add_theme_color_override("font_color", INK)
		l.add_theme_font_size_override("font_size", 15 if i < 4 else 16)
		if i % 4 > 0:
			l.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
		grid.add_child(l)
	for txt in [head, "", "Tap to close"]:
		if txt == "":
			col.add_child(grid)
			continue
		var l := Label.new()
		l.text = txt
		l.add_theme_color_override("font_color", INK if txt == head else ACCENT)
		l.add_theme_font_size_override("font_size", 16)
		col.add_child(l)
	root.add_child(p)
	p.gui_input.connect(func(e: InputEvent):
		if e is InputEventMouseButton and e.pressed:
			p.queue_free()
			_result_panel = null)
	_result_panel = p
	p.grow_horizontal = Control.GROW_DIRECTION_BOTH
	p.grow_vertical = Control.GROW_DIRECTION_BOTH
	p.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	Log.event("speed_test", " | ".join(lines))
	print("SPEED ", " | ".join(lines))


# ------------------------------------------------------------------ clips, on both foxes at once
const SPRITE_FPS := {"idle": 12.0, "walk": 12.0, "eat": 12.0, "happy": 14.0, "hunger": 12.0, "liedown": 12.0, "sleep": 12.0,
	"wake": 15.0, "turn": 22.0}


func play_clip(name: String) -> void:
	if name == "wake" and fox.clip != "sleep":
		return
	if fox.clip == "sleep" and name != "wake":
		return                           # asleep: only waking up
	fox.play(name)
	_sprite_play(name)


func _sprite_name(name: String) -> String:
	var n: String = {"wake": "liedown", "turn": "turn_sit"}.get(name, name)
	var left := n + "_left"
	return left if sprite_facing < 0 and frames.has_animation(left) else n


func _sprite_play(name: String) -> void:
	_sprite_clip = name
	var anim := _sprite_name(name)
	sprite.animation = anim
	var a: Array = anim_info[anim]["anchor"]
	sprite.offset = -Vector2(a[0], a[1])
	sprite.speed_scale = SPRITE_FPS[name] / frames.get_animation_speed(anim)
	if name == "wake":
		sprite.play_backwards(anim)
	else:
		sprite.play(anim)


func _sprite_done() -> void:
	match _sprite_clip:
		"liedown":
			_sprite_play("sleep")
		"turn":
			sprite_facing = -sprite_facing
			_sprite_play("idle")
		"idle", "walk", "sleep":
			pass
		_:
			_sprite_play("idle")


func close() -> void:
	Log.event("compare_closed")
	closed.emit()
	queue_free()
