extends Node
## Plays through the meadow with simulated touches and saves a screenshot at each step, to check the build.
## Run (needs a window, not --headless):  godot --path . res://tests/autoplay.tscn -- OUT_DIR

var main: Node2D
var out := "user://autoplay"
var step := 0
const FINGER := 4127                       ## Safari gives touches large arbitrary numbers, not 0


func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		out = args[0]
	DirAccess.make_dir_recursive_absolute(out)
	Game.variant = "A"
	Game.temperament = "playful"
	Game.creature_name = ""
	main = load("res://main.tscn").instantiate()
	add_child(main)
	await wait(1.5)
	await shot("egg")
	for i in 4:
		await tap(w(Vector2(512, 545)))
		await wait(0.35)
		if i == 1:
			await shot("egg-cracked")
	await wait(0.15)
	await shot("hatch-burst")
	await wait(2.6)
	await shot("hatched")
	var c = main.creature
	await tap(w(c.position + Vector2(0, -110)))
	await wait(0.22)
	await shot("pet")
	await wait(1.2)
	# carry an apple from the tree to the creature's mouth
	var apple_at := w(Vector2(190, 500) + Vector2(-62, -170))
	await press(apple_at)
	var dest: Vector2 = w(c.mouth_world() + Vector2(0, 30))
	for k in 12:
		await drag(apple_at.lerp(dest, (k + 1) / 12.0))
	await shot("carry")
	await release(dest)
	await wait(0.7)
	await shot("eat")
	await wait(1.6)
	# drop an apple on the grass near it: it walks over and eats it
	apple_at = w(Vector2(190, 500) + Vector2(28, -200))
	await press(apple_at)
	var drop := w(c.position + Vector2(-170, 10))
	for k in 10:
		await drag(apple_at.lerp(drop + Vector2(0, -60), (k + 1) / 10.0))
	await release(drop + Vector2(0, -60))
	await wait(1.2)
	await shot("fetch")
	await wait(2.5)
	# call it to a spot on the meadow
	await tap(w(Vector2(820, 660)))
	await wait(0.9)
	await shot("walk")
	await wait(2.5)
	# call it back to the left: it turns round first
	await tap(w(Vector2(300, 650)))
	for k in 4:
		await wait(0.13)
		await shot("turn-%d" % k)
	await wait(2.5)
	# variant A: the hunger cue
	c._hunger_at = 0.0
	c.hungry = false
	c.target = null
	await wait(1.4)
	await shot("hunger-cue")
	await wait(2.5)
	# the name tag opens the gate
	await tap(w(main.tag.position))
	await wait(0.4)
	await shot("gate")
	main.ui._close()
	Game.set_creature_name("Pip")
	await wait(0.4)
	await shot("named")
	# dress up: the crown, the scarf and the bow from the basket onto the fox
	await wait(1.5)
	for id in ["crown", "scarf", "bow"]:
		var from := w(Wardrobe.AT + Wardrobe.ITEMS[id]["spot"])
		var to := w(c.head_world() + Vector2(0, 40))
		await press(from)
		for k in 10:
			await drag(from.lerp(to, (k + 1) / 10.0))
		await release(to)
		await wait(0.5)
	print("WORN ", c.worn)
	await shot("dressed")
	# a finger held up and behind it: it looks round at it, and follows it
	var fp := w(c.head_world() + Vector2(-300.0 * c.facing, -160))
	await press(fp)
	await wait(0.9)
	await shot("look-finger")
	for k in 12:
		await drag(fp + Vector2(50.0 * c.facing * k, 60.0))
	await wait(0.4)
	await shot("look-follow")
	await release(fp + Vector2(50.0 * c.facing * 11, 60.0))
	await wait(0.6)
	# walking and turning round dressed
	await tap(w(Vector2(250 if c.position.x > 500 else 780, 640)))
	await wait(0.5)
	await shot("dressed-walk")
	await wait(3.0)
	# take the bow off again: drag it back to the basket
	var bow_at := w(c.worn_at("tail"))
	await press(bow_at)
	var basket := w(Wardrobe.AT)
	for k in 10:
		await drag(bow_at.lerp(basket, (k + 1) / 10.0))
	await release(basket)
	await wait(0.5)
	print("WORN after ", c.worn)
	await shot("bow-off")
	main.ui.open_panel()
	await wait(0.3)
	await shot("parent-area")
	main.ui.open_log()
	await wait(0.3)
	await shot("event-log")
	main.ui._close()
	main.time.hour = 18.4
	await wait(0.5)
	await shot("dusk")
	# the sun button hurries on to night; the creature dozes off
	await tap(main.sky.position + main.sky.size / 2.0)
	await wait(1.2)
	await shot("sky-switching")
	await wait(1.6)
	await shot("night")
	await wait(3.5)
	await shot("asleep")
	await tap(w(c.position + Vector2(20, -60)))
	await wait(1.6)
	await shot("woken")
	# the moon button brings the morning
	await wait(1.0)
	await tap(main.sky.position + main.sky.size / 2.0)
	await wait(3.0)
	await shot("morning")
	# turn back to the right, standing
	await tap(w(Vector2(850, 640)))
	for k in 4:
		await wait(0.1)
		await shot("turn-back-%d" % k)
	await wait(1.5)
	# the second fox comes to the nest (the parent area's button, instead of waiting four minutes)
	main.breeding.arrive_now()
	await wait(2.0)
	await shot("second-fox-arriving")
	await until(func(): return main.breeding.state != Breeding.State.ARRIVING, 15.0)
	await wait(0.5)
	await shot("second-fox-waiting")
	# bring ours over: an egg appears and the trait choice opens
	var pt: Creature = main.breeding.partner
	if main.breeding.state == Breeding.State.READY:
		await tap(w(pt.position + Vector2(-190, 8)))
	await until(func(): return main.breeding.state == Breeding.State.PAIRING, 12.0)
	await wait(0.9)
	await shot("pairing")
	await until(func(): return main.picker != null, 12.0)
	await wait(0.2)
	await shot("egg-and-picker-opening")
	await wait(0.8)
	await shot("picker")
	await tap(main.picker.chip_at("coat", 1))
	await wait(0.5)
	await shot("picker-coat-from-2")
	await tap(main.picker.chip_at("glow", 0))
	await wait(0.5)
	await shot("picker-glow-from-1")
	await tap(main.picker.chip_at("glow", 1))
	await wait(0.4)
	await tap(main.picker.tick_at())
	await wait(0.8)
	await shot("egg-ready")
	for i in 4:
		await tap(w(Vector2(512, 545)))
		await wait(0.35)
	await wait(0.2)
	await shot("baby-hatch")
	await wait(2.5)
	await shot("baby")
	await wait(6.0)
	await shot("family")
	# the comparison: rendered fox and live 3D fox
	main.open_compare()
	await wait(1.5)
	await shot("compare")
	for cl in [["walk", 0.45], ["eat", 0.6], ["happy", 0.45], ["hunger", 0.55], ["liedown", 0.85], ["sleep-loop", 1.6], ["wake", 0.6], ["turn", 0.3]]:
		if cl[0] != "sleep-loop":
			main.compare.play_clip(cl[0])
		await wait(cl[1])
		await shot("compare-" + cl[0])
		await wait(1.8)
	main.compare.play_clip("idle")
	main.compare._zoom = 2.0
	main.compare._layout()
	await wait(0.6)
	await shot("compare-close")
	main.compare._turn = 1.4
	await wait(0.4)
	await shot("compare-turned")
	main.compare._zoom = 1.0
	main.compare._turn = 0.0
	main.compare._traits_i = 1
	main.compare._apply_look()
	main.compare._layout()
	await wait(0.4)
	await shot("compare-colours")
	print("COMPARE ", main.compare._fps.text)
	# the speed test, shortened
	main.compare.test_seconds = 0.8
	main.compare.speed_test()
	await until(func(): return main.compare._status.begins_with("Speed test 8"), 30.0)
	await wait(0.9)
	await shot("compare-crowd")
	await until(func(): return not main.compare._testing, 30.0)
	await wait(0.3)
	await shot("compare-speed")
	main.compare.close()
	await wait(0.3)
	print("AUTOPLAY DONE log=", ProjectSettings.globalize_path(Log.path))
	get_tree().quit()


func w(p: Vector2) -> Vector2:
	## meadow coordinates to screen coordinates
	return main.world.get_global_transform_with_canvas() * p


func until(cond: Callable, limit: float) -> void:
	var t := 0.0
	while not cond.call() and t < limit:
		await wait(0.1)
		t += 0.1
	if not cond.call():
		push_error("autoplay: timed out waiting")


func wait(s: float) -> void:
	await get_tree().create_timer(s).timeout


func shot(name: String) -> void:
	await RenderingServer.frame_post_draw
	step += 1
	var path := "%s/%02d-%s.png" % [out, step, name]
	get_viewport().get_texture().get_image().save_png(path)
	print("shot ", path)


func _touch(p: Vector2, pressed: bool) -> void:
	var e := InputEventScreenTouch.new()
	e.index = FINGER
	e.position = get_viewport().get_screen_transform() * p      ## the window's pixels (other than the game's at other sizes)
	e.pressed = pressed
	Input.parse_input_event(e)


func press(p: Vector2) -> void:
	_touch(p, true)
	await get_tree().process_frame


func release(p: Vector2) -> void:
	_touch(p, false)
	await get_tree().process_frame


func drag(p: Vector2) -> void:
	var e := InputEventScreenDrag.new()
	e.index = FINGER
	e.position = get_viewport().get_screen_transform() * p
	Input.parse_input_event(e)
	await get_tree().process_frame
	await get_tree().process_frame


func tap(p: Vector2) -> void:
	await press(p)
	await wait(0.06)
	await release(p)
