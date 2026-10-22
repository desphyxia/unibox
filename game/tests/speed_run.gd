extends Node
## Runs the 3D fox check's speed test straight away and prints the table (no playthrough first):
##   godot --path . res://tests/speed_run.tscn [-- SECONDS_PER_SETUP [OUT_DIR]]
## With OUT_DIR it also saves a picture of the five foxes and of the results.

func _ready() -> void:
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)   # measure past the screen's 60
	var args := OS.get_cmdline_user_args()
	var main: Node = load("res://main.tscn").instantiate()
	add_child(main)
	await get_tree().create_timer(1.0).timeout
	main.open_compare()
	if args.size() > 0:
		main.compare.test_seconds = float(args[0])
	main.compare.speed_test()
	var shot := args.size() > 1
	while main.compare._testing:
		await get_tree().create_timer(0.2).timeout
		if shot and main.compare._status.begins_with("Speed test 8"):
			shot = false
			await get_tree().create_timer(0.9).timeout
			await _save(args[1] + "/crowd.png")
	if args.size() > 1:
		await get_tree().create_timer(0.3).timeout
		await _save(args[1] + "/results.png")
	get_tree().quit()


func _save(path: String) -> void:
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(path)
