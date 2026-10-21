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
	main.time.hour = 22.0
	await wait(0.5)
	await shot("night")
	await wait(3.5)
	await shot("asleep")
	await tap(w(c.position + Vector2(20, -60)))
	await wait(1.6)
	await shot("woken")
	print("AUTOPLAY DONE log=", ProjectSettings.globalize_path(Log.path))
	get_tree().quit()


func w(p: Vector2) -> Vector2:
	## meadow coordinates to screen coordinates
	return main.world.get_global_transform_with_canvas() * p


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
	e.position = p
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
	e.position = p
	Input.parse_input_event(e)
	await get_tree().process_frame
	await get_tree().process_frame


func tap(p: Vector2) -> void:
	await press(p)
	await wait(0.06)
	await release(p)
