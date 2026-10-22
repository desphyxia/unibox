extends Node
## Close-ups of the live fox's face, with and without its fur layers, to check the eyes and the fur.
var out := "user://live_debug"

func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		out = args[0]
	var cv := CompareView.new()
	add_child(cv)
	await get_tree().create_timer(0.5).timeout
	cv._zoom = 4.0
	cv._layout()
	for step in ["all", "nofur"]:
		if step == "nofur":
			cv.fox._fur.visible = false
		await get_tree().create_timer(0.3).timeout
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png("%s/%s.png" % [out, step])
	get_tree().quit()
