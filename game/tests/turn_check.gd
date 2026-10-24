extends Node
## Does a creature jump when it turns round? Hatches one of a kind, then turns it sitting and standing, and follows the
## picture of it frame by frame (where its body is on screen, from the picture's own pixels):
##   godot --path . res://tests/turn_check.tscn -- [KIND]
## prints, a line a frame, the clip, the facing and where the body's middle and its lowest point are, and at the end the
## biggest step between two frames near the end of each turn (a jump) beside the biggest step during it.

var main: Node
var c: Creature
var rows := []


func _ready() -> void:
	var args := OS.get_cmdline_user_args()
	var kind: String = args[0] if args.size() > 0 else "fox"
	Game.pick = kind
	Game.kind = kind
	Game.variant = "B"
	main = load("res://main.tscn").instantiate()
	add_child(main)
	await wait(2.5)
	main.egg.hatch()
	await wait(3.5)
	c = main.creature
	print("TURN %s: hatched at %s facing %s" % [kind, c.position, c.facing])
	# sitting: turn round on the spot
	await watch("sit", func(): c.turn_to(-c.facing), 1.6)
	await wait(0.8)
	await watch("sit-back", func(): c.turn_to(-c.facing), 1.6)
	await wait(0.8)
	# standing: walk one way, then call it back the other way while it walks
	c.call_to(c.position + Vector2(-300.0 * c.facing, 0))
	await wait(1.6)
	await watch("stand", func(): c.call_to(c.position + Vector2(-400.0 * c.facing, 0)), 1.2)
	await wait(2.0)
	get_tree().quit()


func wait(s: float) -> void:
	await get_tree().create_timer(s).timeout


func watch(label: String, start: Callable, seconds: float) -> void:
	rows = []
	start.call()
	var t := 0.0
	while t < seconds:
		await RenderingServer.frame_post_draw
		t += get_process_delta_time()
		rows.append(_measure(t))
	var steps := []
	for i in range(1, rows.size()):
		var a: Dictionary = rows[i - 1]
		var b: Dictionary = rows[i]
		steps.append({"t": b["t"], "d": (b["mid"] as Vector2).distance_to(a["mid"]), "dl": absf(b["low"] - a["low"]),
			"from": a["clip"], "to": b["clip"], "face": b["face"]})
	for s in steps:
		print("  %s %.3f  %-10s -> %-10s face %+.0f  step %.2f px  feet %.2f px" % [label, s["t"], s["from"], s["to"], s["face"], s["d"], s["dl"]])
	var turn_max := 0.0
	var change_max := 0.0
	for s in steps:
		if s["from"] != s["to"] or (s["from"] as String).begins_with("turn") != (s["to"] as String).begins_with("turn"):
			change_max = maxf(change_max, maxf(s["d"], s["dl"]))
		elif (s["from"] as String).begins_with("turn"):
			turn_max = maxf(turn_max, maxf(s["d"], s["dl"]))
	print("TURN %s: biggest step during the turn %.2f px, when it ends %.2f px" % [label, turn_max, change_max])


func _measure(t: float) -> Dictionary:
	## where the creature's body is on screen this frame: the middle of its picture's covered pixels and their lowest row
	var img: Image = c.look.view.get_texture().get_image()
	var w := img.get_width()
	var h := img.get_height()
	var sx := 0.0
	var sy := 0.0
	var n := 0.0
	var low := 0
	for y in range(0, h, 2):
		for x in range(0, w, 2):
			var a := img.get_pixel(x, y).a
			if a > 0.5:
				sx += x
				sy += y
				n += 1.0
				low = maxi(low, y)
	var pic: Sprite2D = c.look.pic
	var xf := pic.get_global_transform_with_canvas()
	var mid := xf * (Vector2(sx, sy) / maxf(n, 1.0) + pic.offset)
	var lowp := xf * (Vector2(0, low) + pic.offset)
	return {"t": t, "mid": mid, "low": lowp.y, "clip": c._base(), "face": c.facing}
