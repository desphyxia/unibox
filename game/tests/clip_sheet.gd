extends Node
## Pictures of a creature's clips in the 3D check, one each, to look over a new animal:
##   godot --path . res://tests/clip_sheet.tscn -- OUT_DIR [KIND]

func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	var out := args[0]
	if args.size() > 1:
		Game.kind = args[1]
	var main: Node = load("res://main.tscn").instantiate()
	add_child(main)
	await get_tree().create_timer(1.0).timeout
	main.open_compare()
	var cv = main.compare
	await get_tree().create_timer(1.0).timeout
	await _shot(out + "/idle.png")
	for c in [["walk", 0.4], ["eat", 0.55], ["happy", 0.35], ["hunger", 0.4], ["liedown", 0.9], ["sleep", 1.0], ["wake", 0.7]]:
		if c[0] != "sleep":
			cv.play_clip(c[0])
		await get_tree().create_timer(c[1]).timeout
		await _shot(out + "/%s.png" % c[0])
		await get_tree().create_timer(1.5).timeout
	cv.play_clip("idle")
	cv._zoom = 2.0
	cv._layout()
	await get_tree().create_timer(0.5).timeout
	await _shot(out + "/close.png")
	cv.play_clip("liedown")
	await get_tree().create_timer(2.5).timeout
	await _shot(out + "/close-sleep.png")
	for t in [["side", -0.7], ["front", 1.2]]:      # the sleeping pose from the side and from the front
		cv._turn = t[1]
		await get_tree().create_timer(0.3).timeout
		await _shot(out + "/close-sleep-%s.png" % t[0])
	get_tree().quit()


func _shot(p: String) -> void:
	await RenderingServer.frame_post_draw
	get_viewport().get_texture().get_image().save_png(p)
