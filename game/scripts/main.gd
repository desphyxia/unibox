extends Node2D
## The playable meadow (step 1 of the prototype): an egg in a nest at dawn; tap or rub it to hatch a fox; pet it, walk
## it, call it, feed it apples from the tree; a parent can name it through the gate. Island time runs from dawn
## to dusk in about ten minutes. Follows docs/first-ten-minutes.md up to the pond (later steps add the pond,
## dressing and the second egg).

const BASE := Vector2(1024, 768)            ## the area every screen shows; wider or taller screens see more meadow
const NEST_AT := Vector2(512, 600)
const TREE_AT := Vector2(190, 500)
const APPLE_SPOTS := [Vector2(-62, -170), Vector2(28, -200), Vector2(80, -140), Vector2(-30, -240)]   ## on the canopy, from the tree's foot
const CREATURE_SCALE := 0.5
const APPLE_REGROW := 6.0
const MAX_GROUND_APPLES := 5

var world := Node2D.new()                   ## everything in the meadow, sorted by depth
var fx := Node2D.new()                      ## effects above the meadow
var overlay := Node2D.new()                 ## the carried apple and the name tag, above everything
var tree := Node2D.new()
var tree_apples := Node2D.new()
var nest := Node2D.new()
var egg: Egg
var creature: Creature
var tag: NameTag
var time: IslandTime
var ui: ParentUI
var sky: SkyButton                          ## the sun or moon in the corner: switches between day and night
var frames: SpriteFrames
var anim_info := {}                         ## animation name -> its anim.json (anchor, shadow, stride)
var _spots_used := {}
var _active: Touchable = null
var _ground_press = null
var _finger := -1                           ## the touch being followed; Safari numbers touches arbitrarily, not from 0


func _ready() -> void:
	randomize()
	var names := []
	for anim in ["idle", "walk", "sleep", "eat", "happy", "hunger", "doze", "turn_sit", "turn_stand"]:
		names.append_array([anim, anim + "_left"])       ## each also rendered facing left (the turns: from the left)
	frames = _load_frames("res://art/creatures/%s" % Game.kind, names)
	_build_world()
	ui = ParentUI.new()
	add_child(ui)
	ui.new_session_requested.connect(_new_session)
	ui.time_speed_changed.connect(func(s): time.speed = s)
	var sky_layer := CanvasLayer.new()
	sky_layer.layer = 5
	add_child(sky_layer)
	sky = SkyButton.new()
	sky.time = time
	sky_layer.add_child(sky)
	time.switched.connect(func(night: bool): if creature and night: creature.bedtime())
	Game.name_changed.connect(func(n): if tag: tag.set_text(n))
	Game.settings_changed.connect(func(): if creature: creature.temperament = Game.temperament)
	get_viewport().size_changed.connect(_layout)
	_layout()
	_start_session()


func _load_frames(folder: String, names: Array) -> SpriteFrames:
	## each animation is a folder of frames plus anim.json (made by art/tools/pack_anim.py)
	var f := SpriteFrames.new()
	for anim in names:
		var dir: String = "%s/%s" % [folder, anim]
		var meta := FileAccess.get_file_as_string(dir + "/anim.json")
		if meta == "":
			continue
		var info: Dictionary = JSON.parse_string(meta)
		anim_info[anim] = info
		f.add_animation(anim)
		f.set_animation_speed(anim, float(info.get("fps", 12.0)))
		f.set_animation_loop(anim, Creature.LOOPS.has(anim.trim_suffix("_left")))
		var i := 0
		while ResourceLoader.exists("%s/frame_%02d.png" % [dir, i]):
			f.add_frame(anim, load("%s/frame_%02d.png" % [dir, i]))
			i += 1
	f.remove_animation("default")
	return f


func _build_world() -> void:
	add_child(world)
	world.add_to_group("world")
	world.y_sort_enabled = true
	# sky above and meadow below the painted backdrop, for very tall or wide screens
	for r in [[Rect2(-3000, -3000, 7000, 2874), Color("d6ebf7")], [Rect2(-3000, 894, 7000, 3000), Color("d3eac2")]]:
		var c := ColorRect.new()
		c.position = r[0].position
		c.size = r[0].size
		c.color = r[1]
		c.z_index = -11
		c.mouse_filter = Control.MOUSE_FILTER_IGNORE
		world.add_child(c)
	var back := Sprite2D.new()
	back.texture = load("res://art/meadow/meadow.svg")
	back.centered = false
	back.scale = Vector2.ONE * 0.5                # drawn at 2x for sharp Retina screens
	back.position = Vector2(-512, -128)
	back.z_index = -10
	world.add_child(back)
	time = IslandTime.new()
	world.add_child(time)
	var tint := CanvasModulate.new()
	add_child(tint)
	time.tint = tint
	# the apple tree, with apples on the canopy
	tree.position = TREE_AT
	world.add_child(tree)
	var ts := Sprite2D.new()
	ts.texture = load("res://art/meadow/tree.svg")
	ts.centered = false
	ts.scale = Vector2.ONE * 0.5
	ts.offset = Vector2(-400, -940)               # foot of the trunk is the origin (texture at 2x)
	tree.add_child(ts)
	tree.add_child(tree_apples)
	for i in APPLE_SPOTS.size():
		_grow_apple(i, false)
	# the nest; the egg sits between its back and its woven front rim
	nest.position = NEST_AT
	world.add_child(nest)
	for part in ["back", "egg", "front"]:
		if part == "egg":
			egg = Egg.new()
			egg.meadow = self
			egg.position = Vector2(0, 22)
			nest.add_child(egg)
			egg.hatched.connect(_on_hatched)
			continue
		var s := Sprite2D.new()
		s.texture = load("res://art/meadow/nest_%s.svg" % part)
		s.centered = false
		s.scale = Vector2.ONE * 0.5
		s.offset = Vector2(-240, -100)
		nest.add_child(s)
	fx.z_index = 60
	world.add_child(fx)
	overlay.z_index = 80
	world.add_child(overlay)


func _layout() -> void:
	var view := get_viewport_rect().size
	world.position = ((view - BASE) / 2.0).floor()


func _start_session() -> void:
	Log.start_session()
	Sfx.play("sparkle", 0.8, 0.0, -6.0)


func _new_session() -> void:
	## the next child: forget the creature, start again at dawn with a new egg and a new log
	Log.end_session()
	Game.new_session()
	get_tree().reload_current_scene()


# ------------------------------------------------------------------ hatching and the creature
func _on_hatched(at: Vector2) -> void:
	creature = Creature.new()
	creature.meadow = self
	creature.setup(frames, anim_info, Game.temperament, CREATURE_SCALE)
	world.add_child(creature)
	creature.appear(at + Vector2(0, 24))
	tag = NameTag.new()
	tag.follow = creature
	overlay.add_child(tag)
	tag.position = creature.position + Vector2(0, -200)
	tag.set_text(Game.creature_name)
	tag.pressed.connect(func():
		Log.event("name_tag_opened")
		ui.gate(ui.open_name_only))


func tree_position() -> Vector2:
	return tree.position


func hint_food() -> void:
	for a in get_tree().get_nodes_in_group("touchable"):
		if a is Apple and a.state != Apple.State.HELD:
			a.hint(3.5)


# ------------------------------------------------------------------ apples
func _grow_apple(spot: int, pop := true) -> void:
	var a := Apple.new()
	a.meadow = self
	a.spot = spot
	a.position = APPLE_SPOTS[spot]
	tree_apples.add_child(a)
	_spots_used[spot] = a
	if pop:
		a.scale = Vector2.ONE * 0.1
		var t := a.create_tween()
		t.tween_property(a, "scale", Vector2.ONE, 0.4).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
		Sfx.play("pop", 0.9, 0.05, -8.0)


func apple_left_tree(a: Apple) -> void:
	_spots_used.erase(a.spot)
	var spot := a.spot
	a.spot = -1
	get_tree().create_timer(APPLE_REGROW).timeout.connect(func(): if not _spots_used.has(spot): _grow_apple(spot))


func carry(a: Apple) -> void:
	a.reparent(overlay)


func apple_released(a: Apple) -> void:
	if creature and not creature.busy and creature.wants_food_at(a.position):
		a.state = Apple.State.EATEN
		creature.eat(a, "hand")
		return
	# dropped on the meadow: it falls to the grass and stays there
	a.reparent(world)
	var ground_y := clampf(a.position.y + 40.0, Creature.GROUND.position.y, Creature.GROUND.end.y)
	a.fall_to(ground_y)
	var on_ground := get_tree().get_nodes_in_group("touchable").filter(func(n): return n is Apple and n.state == Apple.State.ON_GROUND)
	if on_ground.size() > MAX_GROUND_APPLES:
		var oldest: Apple = on_ground[0]
		var t := oldest.create_tween()
		t.tween_property(oldest, "modulate:a", 0.0, 0.5)
		t.tween_callback(oldest.queue_free)
	if creature and not creature.busy:
		var landing := Vector2(a.position.x, ground_y)
		if landing.distance_to(creature.position) < 260.0:
			get_tree().create_timer(0.5).timeout.connect(func(): if is_instance_valid(a) and a.state == Apple.State.ON_GROUND: creature.fetch(a))


# ------------------------------------------------------------------ touch routing
func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT or what == NOTIFICATION_WM_WINDOW_FOCUS_OUT:
		_finger = -1                                # a lift we never heard about must not lock out the next touch
		_active = null
		_ground_press = null


func _to_world(screen: Vector2) -> Vector2:
	return world.get_global_transform_with_canvas().affine_inverse() * screen


func _pick(p: Vector2) -> Touchable:
	var best: Touchable = null
	for n in get_tree().get_nodes_in_group("touchable"):
		var t := n as Touchable
		if t == null or not t.is_visible_in_tree() or not t.hit_test(p):
			continue
		if best == null or t.touch_priority > best.touch_priority or (t.touch_priority == best.touch_priority and t.global_position.y > best.global_position.y):
			best = t
	return best


func _unhandled_input(e: InputEvent) -> void:
	if ui.blocking:
		_active = null
		_finger = -1
		return
	if e is InputEventScreenTouch:
		if e.pressed:
			if _finger != -1 and _finger != e.index:
				return                              # a second finger while one is down
		elif e.index != _finger:
			return
		if ui.corner_rect().has_point(e.position):
			_finger = -1
			return
		if e.pressed and _finger == -1 and sky.hit(e.position):
			sky.tap()                               ## its lift is then ignored: no finger is being followed
			return
		var p := _to_world(e.position)
		if e.pressed:
			_finger = e.index
			_active = _pick(p)
			_ground_press = null if _active else p
			if _active:
				_active.touch_begin(p)
		else:
			if _active and is_instance_valid(_active):
				_active.touch_end(p)
			elif _ground_press != null and p.distance_to(_ground_press) < 24.0:
				_ground_tap(p)
			_active = null
			_ground_press = null
			_finger = -1
	elif e is InputEventScreenDrag and e.index == _finger and _active and is_instance_valid(_active):
		_active.touch_move(_to_world(e.position))


func _ground_tap(p: Vector2) -> void:
	## a tap on the meadow calls the creature over; before hatching it just makes a little sparkle
	Fx.sparkles(fx, p, 5, 30, Color(1, 0.97, 0.85))
	if creature and not creature.busy and p.y > Creature.GROUND.position.y - 60:
		creature.call_to(p)
