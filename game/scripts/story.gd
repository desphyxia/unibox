class_name Story
extends Node
## The storybook's record of this session (docs/storybook.md). The first time something happens (the hatch, the first
## meal, dressing up, a drink at the pond, the ball, the rainbow, the friend, the egg, each baby, bedtime) main.gd and
## the creatures call moment(): it notes what happened and, a moment later, takes a picture of the screen round it. The
## parent area turns these into pages. Kept in memory only, for this session; a new session starts an empty one.
## The picture is cut out and shrunk on the graphics chip (a small viewport drawing that part of the screen), so only a
## 640x480 picture is read back, not the whole screen: the read-back is what could make the game stutter.

signal changed

const SHOT := Vector2(560, 420)        ## the picture's size round the moment, in meadow units (4:3)
const WIDE := Vector2(720, 540)        ## for two creatures together
const PICTURE := Vector2i(640, 480)    ## stored picture, pixels (kept as a JPEG)
const MAX_PAGES := 20
const RETRY := 0.5                     ## the view is busy (the parent area, the trait picker): try again this much later
const TRIES := 24

var main: Node2D
var pages: Array[Dictionary] = []     ## in order: key, who, facts, hour, seconds, jpg (empty until taken)
var tally := {}                        ## how often: pets, apples, drinks, balls, things worn, things placed
var day := 1                           ## island days so far (a new one each time the hour wraps round midnight)
var _last_hour := -1.0
var grab_ms: Array[float] = []         ## main-thread time of each picture (the speed check)
var _queue: Array[Dictionary] = []    ## pictures waiting: page, who, at, size, due, tries
var _cam: SubViewport
var _cut: Sprite2D
var _shooting := false
var _tasks: Array[int] = []            ## JPEGs being made on worker threads (each must be waited for, once done)

const TALLY := {"creature_tap": "pets", "food_given": "apples", "drink": "drinks", "play_ball": "balls",
	"item_worn": "worn", "decor_placed": "placed"}


func _ready() -> void:
	Log.logged.connect(_on_logged)
	_cam = SubViewport.new()
	_cam.size = PICTURE
	_cam.disable_3d = true
	_cam.transparent_bg = false
	_cam.render_target_update_mode = SubViewport.UPDATE_DISABLED
	add_child(_cam)
	_cut = Sprite2D.new()
	_cut.centered = false
	_cut.region_enabled = true
	var opaque := ShaderMaterial.new()           # the screen's own alpha would let the fur's edges show through
	opaque.shader = Shader.new()
	opaque.shader.code = "shader_type canvas_item;
render_mode blend_disabled;
void fragment() { COLOR = vec4(texture(TEXTURE, UV).rgb, 1.0); }
"
	_cut.material = opaque
	_cam.add_child(_cut)


func has(key: String) -> bool:
	return not page(key).is_empty()


func page(key: String) -> Dictionary:
	for p in pages:
		if p["key"] == key:
			return p
	return {}


func moment(key: String, who: Creature = null, facts := {}, delay := 1.0, at = null, size := SHOT) -> void:
	## the first time it happens: note it, and take its picture delay seconds later (when the action is under way);
	## at: a meadow point to centre on instead of the creature
	if has(key) or pages.size() >= MAX_PAGES or main == null:
		return
	var p := {"key": key, "who": who.who if who else "", "facts": facts.duplicate(), "hour": main.time.hour,
		"day": day, "seconds": Log.seconds(), "jpg": PackedByteArray()}
	pages.append(p)
	Log.event("story_page", key)
	_take(p, who, at, size, delay)
	changed.emit()


func update(key: String, facts := {}, who: Creature = null, delay := -1.0, at = null, size := SHOT) -> void:
	## more about a moment already noted (another thing worn, the blanket over it): adds the facts, and with a delay
	## takes its picture again (the newest one wins)
	var p := page(key)
	if p.is_empty():
		return
	p["facts"].merge(facts, true)
	if delay >= 0.0:
		_take(p, who, at, size, delay)
	changed.emit()


func collect(key: String, list: String, value, who: Creature = null, delay := 1.2, at = null, size := SHOT) -> void:
	## a moment that gathers: the things worn, the things placed, who was tucked in. The first one notes the moment;
	## each new one joins its list and the picture is taken again
	if not has(key):
		moment(key, who, {list: [value]}, delay, at, size)
		return
	var l: Array = page(key)["facts"].get(list, [])
	if not l.has(value):
		l.append(value)
	update(key, {list: l}, who, delay, at, size)


func creature_of(who: String) -> Creature:
	for c in main.creatures:
		if is_instance_valid(c) and c.who == who:
			return c
	return null


func _on_logged(ev: String, _detail: String) -> void:
	if TALLY.has(ev):
		tally[TALLY[ev]] = tally.get(TALLY[ev], 0) + 1


# ------------------------------------------------------------------ pictures
func _take(p: Dictionary, who: Creature, at, size: Vector2, delay: float) -> void:
	_queue = _queue.filter(func(q): return q["page"] != p)        # a newer picture of the same moment replaces it
	_queue.append({"page": p, "who": who, "at": at, "size": size, "due": Log.seconds() + delay, "tries": 0})


func babies() -> int:
	return main.breeding.babies if main and main.breeding else 0


func _process(_delta: float) -> void:
	if main and main.time:
		if main.time.hour < _last_hour - 1.0:
			day += 1
		_last_hour = main.time.hour
	if _shooting or _queue.is_empty():
		return
	var now := Log.seconds()
	for q in _queue:
		if q["due"] > now:
			continue
		var centre = q["at"]
		if centre == null and is_instance_valid(q["who"]):
			var c: Creature = q["who"]
			centre = (c.position + c.head_world()) / 2.0
		var rect := _screen_rect(centre, q["size"]) if centre != null else Rect2()
		var why := "" if rect.has_area() else "off screen at %s, view %.0f" % [centre, main.pan]
		if why == "" and not _view_free():
			why = "view busy"
		if why == "":
			_queue.erase(q)
			_shoot(q["page"], rect)
			return
		q["tries"] += 1
		q["due"] = now + RETRY
		if q["tries"] >= TRIES:                   # never in view: the page keeps no picture
			_queue.erase(q)
			Log.event("story_no_picture", "%s,%s" % [q["page"]["key"], why])
		return


func _view_free() -> bool:
	return not main.ui.blocking and main.picker == null and main.compare == null and main.world.visible


func _to_px() -> Transform2D:
	return get_viewport().get_final_transform() * main.world.get_global_transform_with_canvas()


func _screen_rect(centre: Vector2, size: Vector2) -> Rect2:
	## the part of the screen's picture (pixels) showing size round centre (meadow units), or none when the centre is
	## off screen (the creature is in the other place)
	var to_px := _to_px()
	var a: Vector2 = to_px * (centre - size / 2.0)
	var b: Vector2 = to_px * (centre + size / 2.0)
	var r := Rect2(a, b - a).abs()
	var screen := Rect2(Vector2.ZERO, Vector2(get_viewport().get_texture().get_size()))
	if not screen.grow(-0.05 * screen.size.x).has_point(to_px * centre):
		return Rect2()
	# slide it fully onto the screen, keeping its size where it fits
	r.size = r.size.min(screen.size)
	r.position = r.position.clamp(Vector2.ZERO, screen.size - r.size)
	return r


func _buttons_in(rect: Rect2) -> Array[CanvasItem]:
	## the corner buttons (the sun or moon, the grown-ups' button) that would show in the picture
	var out: Array[CanvasItem] = []
	var px := get_viewport().get_final_transform()
	for b: Control in [main.sky, main.ui.corner]:
		if b and b.is_visible_in_tree() and rect.intersects(px * b.get_global_rect()):
			out.append(b)
	return out


func _shoot(p: Dictionary, rect: Rect2) -> void:
	## draws that part of a frame into the small viewport, then reads the small picture back. The corner buttons are
	## left out of that one frame if they would show. Viewports inside the game draw before the screen does, so the
	## small one copies the frame before.
	_shooting = true
	var hidden := _buttons_in(rect)
	if not hidden.is_empty():
		for b in hidden:
			b.visible = false
		await RenderingServer.frame_post_draw
		if not is_instance_valid(main):
			return
	_cut.texture = get_viewport().get_texture()
	_cut.region_rect = rect
	_cut.scale = Vector2(PICTURE) / rect.size
	_cam.render_target_update_mode = SubViewport.UPDATE_ONCE
	await get_tree().process_frame
	for b in hidden:
		b.visible = true
	await RenderingServer.frame_post_draw
	var t0 := Time.get_ticks_usec()
	var rd := RenderingServer.get_rendering_device()
	if rd:
		# the graphics-chip renderers (the desktop, the iPad app): read back without waiting for the chip
		var tex := RenderingServer.texture_get_rd_texture(_cam.get_texture().get_rid())
		var fmt := rd.texture_get_format(tex)
		if fmt.format == RenderingDevice.DATA_FORMAT_R8G8B8A8_UNORM or fmt.format == RenderingDevice.DATA_FORMAT_R8G8B8A8_SRGB:
			rd.texture_get_data_async(tex, 0, func(data: PackedByteArray):
				_cut.texture = null
				_shooting = false
				_encode(p, Image.create_from_data(fmt.width, fmt.height, false, Image.FORMAT_RGBA8, data)))
			grab_ms.append((Time.get_ticks_usec() - t0) / 1000.0)
			return
	# the web build (no graphics-chip access): a plain read-back of the small picture
	var img := _cam.get_texture().get_image()
	grab_ms.append((Time.get_ticks_usec() - t0) / 1000.0)
	_cut.texture = null
	_shooting = false
	_encode(p, img)


func _encode(p: Dictionary, img: Image) -> void:
	if img == null or img.is_empty():
		return
	img.convert(Image.FORMAT_RGB8)
	var out := [PackedByteArray()]
	var id := WorkerThreadPool.add_task(func(): out[0] = img.save_jpg_to_buffer(0.86))
	_tasks.append(id)
	while not WorkerThreadPool.is_task_completed(id):
		await get_tree().process_frame
	WorkerThreadPool.wait_for_task_completion(id)
	_tasks.erase(id)
	_stored(p, out[0])


func _exit_tree() -> void:
	for id in _tasks:
		WorkerThreadPool.wait_for_task_completion(id)
	_tasks.clear()


func _stored(p: Dictionary, jpg: PackedByteArray) -> void:
	p["jpg"] = jpg
	changed.emit()


func picture(p: Dictionary) -> ImageTexture:
	## a page's picture, or null if it has none (yet)
	if p["jpg"].is_empty():
		return null
	var img := Image.new()
	if img.load_jpg_from_buffer(p["jpg"]) != OK:
		return null
	return ImageTexture.create_from_image(img)


func save_pictures(dir: String) -> void:
	## for checks: each page's picture and a list of the pages
	DirAccess.make_dir_recursive_absolute(dir)
	var lines := []
	for i in pages.size():
		var p := pages[i]
		var name := "%02d-%s.jpg" % [i + 1, p["key"]]
		if not p["jpg"].is_empty():
			var f := FileAccess.open(dir.path_join(name), FileAccess.WRITE)
			f.store_buffer(p["jpg"])
		lines.append("%s\twho=%s\thour=%.2f\tt=%.1f\t%s\t%s" % [name, p["who"], p["hour"], p["seconds"],
			JSON.stringify(p["facts"]), "picture" if not p["jpg"].is_empty() else "NO PICTURE"])
	lines.append("tally " + JSON.stringify(tally))
	lines.append("grab ms " + str(grab_ms))
	FileAccess.open(dir.path_join("pages.txt"), FileAccess.WRITE).store_string("\n".join(lines) + "\n")
