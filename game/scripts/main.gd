extends Node2D
## The playable meadow (step 1 of the prototype): an egg in a nest at dawn; tap or rub it to hatch a fox; pet it, walk
## it, call it, feed it apples from the tree; a parent can name it through the gate. Island time runs from dawn
## to dusk in about ten minutes. A few minutes in, a second fox comes to the nest; bring yours over and an egg appears,
## the child picks the baby's colours from its parents and hatches it (breeding.gd, trait_picker.gd). Follows
## docs/first-ten-minutes.md. The creatures are live 3D models (creature_view.gd).
## Two places side by side: the meadow (world x 0..1024) and, along the sandy path, the pond (x 1024..2048). The view
## slides to whichever place the child's creature is in; signposts by the path send it there (travel()).

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
var creature: Creature                      ## the child's first creature (hatched from the first egg)
var creatures: Array[Creature] = []         ## every creature in the meadow
var breeding: Breeding
var picker: TraitPicker                     ## open while the child chooses a new egg's traits
var compare: CompareView                    ## the 3D fox check and speed test (from the parent area)
var _selected: Creature                     ## the creature touched last: a tap on the meadow calls this one
var tag: NameTag
var time: IslandTime
var ui: ParentUI
var sky: SkyButton                          ## the sun or moon in the corner: switches between day and night
var _spots_used := {}
var _active: Touchable = null
var _ground_press = null
var _finger := -1                           ## the touch being followed; Safari numbers touches arbitrarily, not from 0
var finger = null                           ## Vector2: where that finger is on the meadow while it is down (creatures look)
var wardrobe: Wardrobe                      ## the basket of things to wear
var pond: Pond
var decor: DecorBasket                      ## the basket of things to place, at the pond
var area := "meadow"                        ## the place in view
var pan := 0.0                              ## how far east the view has slid (0 the meadow, 1024 the pond)
var _pan_tween: Tween
var _travel_to := ""                        ## a signpost sent the creature here: the view waits for it
var _away_for := 0.0                        ## how long the followed creature has been in the other place
const PLACES := {"meadow": 0.0, "pond": 1024.0}


func _ready() -> void:
	randomize()
	_build_world()
	_warm_up()
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
	time.switched.connect(func(night: bool):
		if night:
			for c in creatures:
				c.bedtime())
	breeding = Breeding.new()
	breeding.main = self
	add_child(breeding)
	ui.second_fox_requested.connect(func(): breeding.arrive_now())
	ui.compare_requested.connect(open_compare)
	Game.name_changed.connect(func(n): if tag: tag.set_text(n))
	Game.settings_changed.connect(func(): if creature: creature.temperament = Game.temperament)
	get_viewport().size_changed.connect(_layout)
	_layout()
	_start_session()


func _warm_up() -> void:
	## a tiny fox drawn out of sight for a moment: the model loads and the 3D shaders are built now, while the egg waits,
	## not with a stutter when it hatches
	var warm := CreatureView.new(4.0)
	warm.position = Vector2(-5000, -5000)
	add_child(warm)
	get_tree().create_timer(0.6).timeout.connect(warm.queue_free)


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
	for b in [["meadow", Vector2(-512, -128)], ["meadow_east", Vector2(1536, -128)]]:
		var back := Sprite2D.new()
		back.texture = load("res://art/meadow/%s.svg" % b[0])
		back.centered = false
		back.scale = Vector2.ONE * 0.5            # drawn at 2x for sharp Retina screens
		back.position = b[1]
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
	wardrobe = Wardrobe.new()
	wardrobe.meadow = self
	world.add_child(wardrobe)
	# the pond, its signposts and its basket of things to place
	pond = Pond.new()
	world.add_child(pond)
	pond.tapped.connect(_on_water_tapped)
	for sp in [Signpost.new("pond", Vector2(944, 560)), Signpost.new("meadow", Vector2(1104, 592))]:
		world.add_child(sp)
		sp.pressed.connect(travel)
	decor = DecorBasket.new()
	decor.meadow = self
	world.add_child(decor)
	fx.z_index = 60
	world.add_child(fx)
	overlay.z_index = 80
	world.add_child(overlay)


func _layout() -> void:
	var view := get_viewport_rect().size
	world.position = ((view - BASE) / 2.0).floor() - Vector2(roundf(pan), 0)
	if time:
		time.view_x = pan


# ------------------------------------------------------------------ the two places
func show_place(to: String, quick := false) -> void:
	## slide the view to a place
	if to == area and not quick:
		return
	area = to
	Log.event("area", to)
	if _pan_tween:
		_pan_tween.kill()
	if quick:
		pan = PLACES[to]
		_layout()
		return
	_pan_tween = create_tween()
	_pan_tween.tween_method(func(v: float):
		pan = v
		_layout(), pan, PLACES[to], 1.3).set_trans(Tween.TRANS_SINE).set_ease(Tween.EASE_IN_OUT)


func travel(to: String) -> void:
	## a signpost: the child's creature (the one touched last) walks along the path there, and the view goes with it
	var c := _selected if is_instance_valid(_selected) else creature
	show_place(to)
	if c == null:
		return
	_travel_to = to
	var entry := Vector2(1190, 650) if to == "pond" else Vector2(860, 640)
	c.call_to(entry)


func _follow_view(delta: float) -> void:
	## the view follows the child's creature from one place to the other (after a moment, so a walk near the path end
	## doesn't swing it about)
	var c := _selected if is_instance_valid(_selected) else creature
	if c == null or not is_instance_valid(c):
		return
	var where := Creature.area_at(c.position.x)
	if _travel_to != "":
		if where == _travel_to:
			_travel_to = ""
		return
	_away_for = _away_for + delta if where != area else 0.0
	if _away_for > 0.6:
		_away_for = 0.0
		show_place(where)


func _process(delta: float) -> void:
	_follow_view(delta)


func _on_water_tapped(p: Vector2) -> void:
	## ripples: creatures at the pond look; the child's creature (the one touched last) goes and drinks
	var c := _selected if is_instance_valid(_selected) else creature
	for o in creatures:
		if is_instance_valid(o) and Creature.area_at(o.position.x) == "pond" and o.position.distance_to(p) < 520.0:
			o.glance(p)
	if c and not c.busy and Creature.area_at(c.position.x) == "pond":
		c.drink_at(p)


func ball_moved(ball: Node2D, to = null) -> void:
	## the ball was put down or rolled: the nearest creature that isn't busy runs after it
	var at: Vector2 = to if to != null else ball.position
	var chaser := _nearest(at, func(o: Creature): return not o.busy and not o.asleep and o.position.distance_to(at) < 460.0)
	if chaser:
		chaser.chase(ball, at)


func _start_session() -> void:
	Log.start_session()
	Sfx.play("sparkle", 0.8, 0.0, -6.0)
	# a test entry for checking the web build from a computer: the page address ending in #check opens the 3D fox check
	# in close-up (children never see it; there is no link to it)
	if OS.has_feature("web") and str(JavaScriptBridge.eval("window.location.hash")) == "#check":
		get_tree().create_timer(1.0).timeout.connect(func():
			open_compare()
			compare._zoom = 2.0
			compare._layout()
			var f: CreatureModel = compare.fox
			print("WEB CHECK fur layers built: %s (drawn %d triangles from %d)" % [f._fur.mesh != f._fur_source,
				f._fur.mesh.surface_get_array_index_len(0) / 3, f._fur_source.surface_get_array_index_len(0) / 3]))


func _new_session() -> void:
	## the next child: forget the creature, start again at dawn with a new egg and a new log
	Log.end_session()
	Game.new_session()
	get_tree().reload_current_scene()


# ------------------------------------------------------------------ hatching and the creature
func spawn_creature(traits: Dictionary, size: float, at: Vector2, temper: String, face := 1.0, grows_to := -1.0) -> Creature:
	## size, grows_to: times an adult's size (grows_to: the size it will grow to, so its picture is made for that)
	var c := Creature.new()
	c.meadow = self
	c.facing = face
	c.setup(temper, CREATURE_SCALE * size, CREATURE_SCALE * grows_to)
	c.set_traits(traits)
	c.position = at
	world.add_child(c)
	creatures.append(c)
	return c


func open_compare() -> void:
	if compare:
		return
	compare = CompareView.new()
	world.visible = false                   # the meadow's foxes stop drawing, so the speed test measures its own
	compare.closed.connect(func():
		compare = null
		world.visible = true)
	add_child(compare)


func open_picker(parents: Array, done: Callable) -> void:
	picker = TraitPicker.new(parents)
	picker.chosen.connect(func(t, src):
		picker = null
		done.call(t, src))
	add_child(picker)


func _on_hatched(at: Vector2) -> void:
	creature = spawn_creature(Traits.defaults(), 1.0, at + Vector2(0, 24), Game.temperament)
	_selected = creature
	creature.appear(at + Vector2(0, 24))
	breeding.start()
	tag = add_tag(creature)
	tag.set_text(Game.creature_name)


func add_tag(c: Creature) -> NameTag:
	## a paw tag over a creature; tapping it opens the parental gate, then a name field for that creature
	var t := NameTag.new()
	t.follow = c
	c.tag = t
	overlay.add_child(t)
	t.position = c.position + Vector2(0, -200)
	t.pressed.connect(func():
		Log.event("name_tag_opened", c.who)
		ui.gate(func(): ui.open_name_only(null if c == creature else c)))
	return t


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


func _nearest(p: Vector2, ok: Callable) -> Creature:
	var best: Creature = null
	for c in creatures:
		if is_instance_valid(c) and ok.call(c) and (best == null or c.position.distance_to(p) < best.position.distance_to(p)):
			best = c
	return best


func apple_released(a: Apple) -> void:
	var eater := _nearest(a.position, func(c): return not c.busy and c.wants_food_at(a.position))
	if eater:
		a.state = Apple.State.EATEN
		eater.eat(a, "hand")
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
	var landing := Vector2(a.position.x, ground_y)
	var fetcher := _nearest(landing, func(c): return not c.busy and c.position.distance_to(landing) < 260.0)
	if fetcher:
		get_tree().create_timer(0.5).timeout.connect(func(): if is_instance_valid(a) and a.state == Apple.State.ON_GROUND: fetcher.fetch(a))


# ------------------------------------------------------------------ touch routing
func _exit_tree() -> void:
	CreatureModel.release_shared()


func _notification(what: int) -> void:
	if what == NOTIFICATION_APPLICATION_FOCUS_OUT or what == NOTIFICATION_WM_WINDOW_FOCUS_OUT:
		_finger = -1                                # a lift we never heard about must not lock out the next touch
		finger = null
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
	if ui.blocking or compare:
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
		if picker:                                  ## the trait choice takes every touch while it is open
			if e.pressed:
				picker.touch(e.position)
			_finger = -1
			_active = null
			return
		if e.pressed and _finger == -1 and sky.hit(e.position):
			sky.tap()                               ## its lift is then ignored: no finger is being followed
			return
		var p := _to_world(e.position)
		finger = p if e.pressed else null
		if e.pressed:
			_finger = e.index
			_active = _pick(p)
			if _active is Creature:
				_selected = _active
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
	elif e is InputEventScreenDrag and e.index == _finger:
		finger = _to_world(e.position)
		if _active and is_instance_valid(_active):
			_active.touch_move(finger)


func _ground_tap(p: Vector2) -> void:
	## a tap on the meadow calls the creature over; before hatching it just makes a little sparkle; on the water, ripples
	if Pond.contains(p, 6.0):
		pond.tap(p)
		return
	Fx.sparkles(fx, p, 5, 30, Color(1, 0.97, 0.85))
	var c := _selected if is_instance_valid(_selected) else creature
	if c and not c.busy and p.y > Creature.GROUND.position.y - 60:
		c.call_to(p)
