extends Node2D
## Plays the pre-rendered fox idle loop over the island backdrop, the way the game would show a creature,
## and reports what it costs: texture memory, frame rate, file sizes.

const FPS := 12.0
var sprite: AnimatedSprite2D
var label: Label
var t := 0.0
var reported := false
var folder := "res://fox"
var back: Sprite2D
var shadow: Sprite2D
var off := Vector2.ZERO
var sh := Vector3(320, 500, 280)

func _ready() -> void:
	back = Sprite2D.new()
	back.texture = load("res://backdrop.svg")
	back.centered = false
	add_child(back)
	var frames := SpriteFrames.new()
	frames.add_animation("idle")
	frames.set_animation_speed("idle", FPS)
	frames.set_animation_loop("idle", true)
	var i := 0
	while ResourceLoader.exists("%s/frame_%02d.png" % [folder, i]):
		frames.add_frame("idle", load("%s/frame_%02d.png" % [folder, i]))
		i += 1
	frames.remove_animation("default")
	sprite = AnimatedSprite2D.new()
	sprite.sprite_frames = frames
	sprite.animation = "idle"
	var meta := FileAccess.open(folder + "/offset.txt", FileAccess.READ)
	if meta:
		var parts := meta.get_as_text().strip_edges().split(" ")
		off = Vector2(float(parts[0]), float(parts[1]))
		if parts.size() >= 5:
			sh = Vector3(float(parts[2]), float(parts[3]), float(parts[4]))
	# one soft shadow drawn by the game, so every creature sits on any ground the same way
	var g := Gradient.new()
	g.set_color(0, Color(0.32, 0.24, 0.42, 0.32))
	g.set_color(1, Color(0.32, 0.24, 0.42, 0.0))
	var gt := GradientTexture2D.new()
	gt.gradient = g
	gt.fill = GradientTexture2D.FILL_RADIAL
	gt.fill_from = Vector2(0.5, 0.5)
	gt.fill_to = Vector2(1.0, 0.5)
	gt.width = 256
	gt.height = 256
	shadow = Sprite2D.new()
	shadow.texture = gt
	shadow.scale = Vector2(sh.z / 256.0, sh.z * 0.2 / 256.0)
	add_child(shadow)
	sprite.centered = false
	add_child(sprite)
	sprite.play("idle")
	label = Label.new()
	label.position = Vector2(16, 12)
	label.add_theme_color_override("font_color", Color(0.25, 0.18, 0.3))
	add_child(label)
	print("frames loaded: ", i, " from ", folder)
	get_viewport().size_changed.connect(layout)
	layout()

## fit the scene to whatever screen it gets (iPad landscape or portrait, any browser window)
func layout() -> void:
	var view := get_viewport_rect().size
	var s := maxf(view.x / back.texture.get_width(), view.y / back.texture.get_height())
	back.scale = Vector2(s, s)
	back.position = (view - back.texture.get_size() * s) / 2.0
	var origin := view / 2.0 + Vector2(0, 8) - Vector2(320, 292)
	shadow.position = origin + Vector2(sh.x, sh.y)
	sprite.position = origin + off

func _process(delta: float) -> void:
	t += delta
	var tex_mb := Performance.get_monitor(Performance.RENDER_TEXTURE_MEM_USED) / 1048576.0
	label.text = "Fox idle loop: %d frames at %d fps   |   texture memory %.1f MB   |   %d fps" % [sprite.sprite_frames.get_frame_count("idle"), FPS, tex_mb, Engine.get_frames_per_second()]
	if t > 3.0 and not reported:
		reported = true
		print("REPORT folder=", folder, " texture_mem_MB=", snappedf(tex_mb, 0.1), " static_mem_MB=", snappedf(Performance.get_monitor(Performance.MEMORY_STATIC) / 1048576.0, 0.1), " fps=", Engine.get_frames_per_second())
