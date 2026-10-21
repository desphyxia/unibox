extends Node
## Close-ups of the live fox's face with parts switched off, to check the eyes.
var out := "user://live_debug"

func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	if args.size() > 0:
		out = args[0]
	var frames := SpriteFrames.new()
	var info := {"idle": JSON.parse_string(FileAccess.get_file_as_string("res://art/creatures/fox/idle/anim.json"))}
	frames.add_animation("idle")
	frames.add_frame("idle", load("res://art/creatures/fox/idle/frame_00.png"))
	var cv := CompareView.new(frames, info)
	add_child(cv)
	await get_tree().create_timer(0.5).timeout
	cv._zoom = 4.0
	cv._layout()
	for step in ["all", "nofur", "nolit"]:
		if step == "nofur":
			cv.fox._fur.visible = false
		if step == "nolit":
			for c in cv.fox.get_children():
				if c is MeshInstance3D and (c.mesh.surface_get_material(0) as ShaderMaterial).get_shader_parameter("kind") == 0:
					c.visible = false
		await get_tree().create_timer(0.3).timeout
		await RenderingServer.frame_post_draw
		get_viewport().get_texture().get_image().save_png("%s/%s.png" % [out, step])
	get_tree().quit()
