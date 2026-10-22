class_name TraitPicker
extends CanvasLayer
## The trait choice for a new egg, with no words: the two parents stand at the sides, the baby in the middle, and between
## them a row of buttons for each trait (coat colour, then glow colour). The button on a parent's side gives the baby
## that parent's colour; the baby changes at once. The big tick in the middle hatches the egg. main.gd sends the touches.

signal chosen(traits: Dictionary, sources: Dictionary)

const INK := Color(0.29, 0.18, 0.28)
const CHIP_R := 44.0

var parents: Array = []                ## [Creature, Creature]: left and right
var pick := {"coat": 0, "glow": 1}     ## which parent each trait comes from: one from each to start with
var root := Control.new()
var _baby := CreatureView.new(34.0)         ## live foxes, like the ones in the meadow
var _shown: Array = []                 ## the parents
var _chips := []                       ## [type, parent index, centre, radius]
var _tick := Vector2.ZERO
var _t := 0.0
var _pop := {}                         ## chip key -> pop amount, for a little bounce when tapped
var _baby_pop := 0.0
var _open := 0.0
var _done := false


func _init(p_parents: Array) -> void:
	parents = p_parents


func _ready() -> void:
	layer = 8
	root.set_anchors_preset(Control.PRESET_FULL_RECT)
	root.mouse_filter = Control.MOUSE_FILTER_IGNORE
	root.draw.connect(_draw_root)
	add_child(root)
	for i in 2:
		var s := CreatureView.new(36.0)
		s.model.facing = 1.0 if i == 0 else -1.0     ## both face the baby
		s.model.shells = 4
		s.model.set_traits(parents[i].traits)
		root.add_child(s)
		_shown.append(s)
	_baby.model.shells = 4
	root.add_child(_baby)
	_update_baby()
	get_viewport().size_changed.connect(_layout)
	_layout()
	Sfx.play("chime", 1.1, 0.0, -4.0)


func _view() -> Vector2:
	return root.get_viewport_rect().size


func _layout() -> void:
	var v := _view()
	var cx := v.x / 2.0
	var u := minf(v.x / 1024.0, v.y / 768.0)        ## the picker is laid out for 1024x768 and scaled to fit
	var side := minf(v.x * 0.5 - 90.0 * u, 350.0 * u)
	for i in 2:
		_shown[i].position = Vector2(cx + (side if i == 1 else -side), v.y * 0.6)
		_shown[i].scale = Vector2.ONE * 0.44 * u
	_baby.position = Vector2(cx, v.y * 0.5)
	_chips.clear()
	for row in Traits.TYPES.size():
		var y := v.y * (0.63 + 0.135 * row)
		for i in 2:
			_chips.append([Traits.TYPES[row], i, Vector2(cx + (1 if i == 1 else -1) * 112.0 * u, y), CHIP_R * u])
	_tick = Vector2(cx, v.y * (0.63 + 0.135 * 2))
	_tick.y = minf(_tick.y, v.y - 60.0 * u)


func baby_traits() -> Dictionary:
	var t := {}
	for type in Traits.TYPES:
		t[type] = parents[pick[type]].traits[type]
	return t


func _update_baby() -> void:
	_baby.model.set_traits(baby_traits())


# ------------------------------------------------------------------ touch (from main.gd)
func touch(p: Vector2) -> void:
	if _done or _open < 0.6:
		return
	for c in _chips:
		if p.distance_to(c[2]) <= c[3] * 1.25:
			if pick[c[0]] != c[1]:
				pick[c[0]] = c[1]
				_update_baby()
				Log.event("trait_chosen", "%s=parent%d" % [c[0], c[1] + 1])
				Sfx.play("pop", 1.0 + 0.15 * c[1], 0.03)
				Sfx.play("sparkle", 1.2, 0.05, -8.0)
				_baby_pop = 1.0
			else:
				Sfx.play("pop", 0.9, 0.03, -6.0)
			_pop["%s%d" % [c[0], c[1]]] = 1.0
			return
	if p.distance_to(_tick) <= 60.0 * _u():
		confirm()


func _u() -> float:
	var v := _view()
	return minf(v.x / 1024.0, v.y / 768.0)


func chip_at(type: String, parent: int) -> Vector2:
	## for the play-through test
	for c in _chips:
		if c[0] == type and c[1] == parent:
			return c[2]
	return Vector2.ZERO


func tick_at() -> Vector2:
	return _tick


func confirm() -> void:
	if _done:
		return
	_done = true
	var sources := {}
	for type in Traits.TYPES:
		sources[type] = pick[type]
	Log.event("traits_done", ",".join(Traits.TYPES.map(func(k): return "%s=%s" % [k, baby_traits()[k]])))
	Sfx.play("chime", 1.25)
	var t := create_tween()
	t.tween_property(self, "_open", 0.0, 0.3)
	t.tween_callback(func():
		chosen.emit(baby_traits(), sources)
		queue_free())


# ------------------------------------------------------------------ drawing
func _process(delta: float) -> void:
	_t += delta
	if not _done:
		_open = move_toward(_open, 1.0, delta * 3.0)
	for k in _pop.keys():
		_pop[k] = move_toward(_pop[k], 0.0, delta * 4.0)
	_baby_pop = move_toward(_baby_pop, 0.0, delta * 3.0)
	var u := _u()
	var e := _open * _open * (3.0 - 2.0 * _open)
	root.modulate.a = e
	_baby.scale = Vector2.ONE * 0.42 * u * (1.0 + 0.12 * sin(_baby_pop * PI)) * (0.7 + 0.3 * e)
	root.queue_redraw()


func _draw_root() -> void:
	var v := _view()
	var u := _u()
	root.draw_rect(Rect2(Vector2.ZERO, v), Color(0.2, 0.12, 0.24, 0.55))
	var cw := minf(v.x - 24.0, 960.0 * u)
	var card := Rect2(v.x / 2.0 - cw / 2.0, v.y * 0.06, cw, v.y * 0.92)
	var sb := StyleBoxFlat.new()
	sb.bg_color = Color(1.0, 0.975, 0.95)
	sb.set_corner_radius_all(int(44 * u))
	sb.shadow_color = Color(0.2, 0.1, 0.2, 0.25)
	sb.shadow_size = int(20 * u)
	sb.anti_aliasing = true
	root.draw_style_box(sb, card)
	# a soft light behind each figure; the baby's has the colour of its glow
	var glow := Traits.swatch("glow", baby_traits()["glow"])
	for i in 2:
		var at: Vector2 = _shown[i].position + Vector2(0, -95 * u)
		_soft_disc(at, 150.0 * u, Color(Traits.swatch("coat", parents[i].traits["coat"]), 0.28))
	_soft_disc(_baby.position + Vector2(0, -80 * u), 150.0 * u * (1.0 + 0.04 * sin(_t * 2.4)), Color(glow, 0.45))
	# each parent's buttons sit on its side, joined to it by a dotted trail
	for c in _chips:
		var type: String = c[0]
		var i: int = c[1]
		var at: Vector2 = c[2]
		var r: float = c[3] * (1.0 + 0.18 * sin(_pop.get("%s%d" % [type, i], 0.0) * PI))
		var on: bool = pick[type] == i
		var col := Traits.swatch(type, parents[i].traits[type])
		var from: Vector2 = _shown[i].position + Vector2((40.0 if i == 0 else -40.0) * u, -20.0 * u)
		_dots(from, at + Vector2((-r if i == 0 else r), 0), Color(INK, 0.16 if not on else 0.4), u)
		if on:
			root.draw_circle(at, r + 9.0 * u, Color(0.45, 0.78, 0.55), true, -1.0, true)
			root.draw_circle(at, r + 15.0 * u + 3.0 * u * sin(_t * 4.0), Color(0.45, 0.78, 0.55, 0.3), false, 3.0 * u, true)
		else:
			root.draw_circle(at, r + 4.0 * u, Color(INK, 0.14), true, -1.0, true)
		if type == "coat":
			_fluff(at, r, col)
		elif Game.kind == "unicorn":
			_lock(at, r, col)
		else:
			_flame(at, r, col)
		if on:          # a little tick badge on the chosen one
			var b := at + Vector2(r * 0.72, -r * 0.72)
			root.draw_circle(b, 13.0 * u, Color(0.45, 0.78, 0.55), true, -1.0, true)
			root.draw_polyline(PackedVector2Array([b + Vector2(-6, 0) * u, b + Vector2(-1.5, 5) * u, b + Vector2(6.5, -5) * u]), Color.WHITE, 3.5 * u, true)
	# the big tick: hatch with these
	var pulse := 1.0 + 0.06 * sin(_t * 3.2)
	var tr := 46.0 * u * pulse
	root.draw_circle(_tick, tr + 6.0 * u, Color(0.45, 0.78, 0.55, 0.3), true, -1.0, true)
	root.draw_circle(_tick, tr, Color(0.45, 0.78, 0.55), true, -1.0, true)
	root.draw_polyline(PackedVector2Array([_tick + Vector2(-19, 1) * u * pulse, _tick + Vector2(-5, 15) * u * pulse, _tick + Vector2(20, -13) * u * pulse]), Color.WHITE, 9.0 * u, true)


func _soft_disc(at: Vector2, r: float, col: Color) -> void:
	for k in 6:
		var f := 1.0 - k / 6.0
		root.draw_circle(at, r * f, Color(col, col.a * 0.22), true, -1.0, true)


func _dots(a: Vector2, b: Vector2, col: Color, u: float) -> void:
	var n := int(a.distance_to(b) / (16.0 * u))
	for k in range(1, n):
		root.draw_circle(a.lerp(b, float(k) / n), 3.0 * u, col, true, -1.0, true)


func _fluff(at: Vector2, r: float, col: Color) -> void:
	## a round tuft of fur in the coat colour, lighter on top
	for k in 10:
		var a := TAU * k / 10.0
		root.draw_circle(at + Vector2(cos(a), sin(a)) * r * 0.66, r * 0.34, col.darkened(0.06), true, -1.0, true)
	root.draw_circle(at, r * 0.72, col, true, -1.0, true)
	root.draw_circle(at + Vector2(-0.22, -0.26) * r, r * 0.32, col.lightened(0.28), true, -1.0, true)


func _lock(at: Vector2, r: float, col: Color) -> void:
	## a curl of mane in the mane colour
	var pts := PackedVector2Array()
	for k in 24:
		var t := k / 23.0
		pts.append(at + Vector2(-0.35 + 0.5 * sin(t * PI * 1.3), -0.75 + 1.4 * t) * r)
	root.draw_polyline(pts, col, r * 0.42, true)
	root.draw_circle(pts[pts.size() - 1] + Vector2(0.1, -0.05) * r, r * 0.24, col, true, -1.0, true)
	root.draw_polyline(pts.slice(2, 14), col.lightened(0.45), r * 0.1, true)


func _flame(at: Vector2, r: float, col: Color) -> void:
	## a foxfire drop in the glow colour, with a pale core
	var pts := PackedVector2Array()
	for k in 33:
		var a := TAU * k / 32.0
		var w := sin(a)
		var y := -cos(a)
		var p := Vector2(w * 0.62, y * 0.62 + 0.18)
		if y < 0.0:                     # draw the top up into a point
			p = Vector2(w * 0.62 * (1.0 + y * 0.85), -0.18 + y * 0.92)
		pts.append(at + p * r)
	root.draw_colored_polygon(pts, col)
	root.draw_circle(at + Vector2(0, 0.2) * r, r * 0.3, col.lightened(0.6), true, -1.0, true)
