class_name CreatureView
extends Node2D
## A live 3D creature (creatures/<kind>/<kind>.scn, run by creatures/creature_model.gd) drawn into the 2D meadow: it
## renders in its own small 3D world, with the camera and lights of the Blender renders, into a picture whose origin is
## the creature's ground point. This node's units are the renders' pixels (80 to a model unit), so a creature scales it
## the way it scaled the rendered frames before. The picture is only redrawn while the creature is on screen.

const RENDER_PPU := 80.0                         ## render pixels per model unit (640-wide frames, 8 units across)
const BOX := Rect2(-5.25, -7.8, 10.5, 9.6)       ## the picture round the ground point, model units (x right, y down)

const SCENES := {"fox": "res://creatures/fox/fox.scn", "unicorn": "res://creatures/unicorn/unicorn.scn",
	"collie": "res://creatures/collie/collie.scn"}

var model: CreatureModel
var view := SubViewport.new()
var cam := Camera3D.new()
var pic := Sprite2D.new()
var ppu := 40.0                                  ## the picture's pixels per model unit: about its size on screen
static var sharpness := 1.0                      ## pictures are made at this times their size in the meadow's units
var _shown := true
var _at := Vector2.ZERO                          ## the ground point in the picture, its pixels


func _init(p_ppu := 40.0, kind := "") -> void:
	ppu = p_ppu
	model = scene(kind).instantiate()


static func scene(kind := "") -> PackedScene:
	## the model for a kind of creature (Game.kind unless given)
	return load(SCENES.get(kind if kind != "" else Game.kind, SCENES["fox"]))


func _ready() -> void:
	view.own_world_3d = true
	view.transparent_bg = true
	view.msaa_3d = Viewport.MSAA_4X
	view.size = Vector2i((BOX.size * ppu).ceil())
	view.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(view)
	_build_world(view, cam, model.get_meta("camera"))
	view.add_child(model)
	# where the ground point lands in the picture
	var g: Array = model.get_meta("ground")
	var gp := Vector3(g[0], g[1], g[2])
	var tgt := cam.global_position + (-cam.global_transform.basis.z) * 40.0
	var rel := cam.global_transform.basis.inverse() * (gp - tgt)
	var size := Vector2(view.size)
	var at := -BOX.position * ppu
	_at = at
	cam.size = size.y / ppu
	cam.h_offset = rel.x - (at.x - size.x / 2.0) / ppu
	cam.v_offset = rel.y + (at.y - size.y / 2.0) / ppu
	pic.texture = view.get_texture()
	pic.centered = false
	pic.offset = -at
	pic.scale = Vector2.ONE * RENDER_PPU / ppu
	pic.material = premultiplied()
	add_child(pic)


func look_toward(local: Vector2) -> void:
	## look at a point given in this node's units (render pixels from the ground point): a point on the picture's plane
	## through the ground point, brought a little toward the viewer, so the creature looks out at a finger on the glass
	var g: Array = model.get_meta("ground")
	var b := cam.global_transform.basis
	var p := Vector3(g[0], g[1], g[2]) + b.x * (local.x / RENDER_PPU) - b.y * (local.y / RENDER_PPU) + b.z * 2.5
	model.look.target = model.global_transform.affine_inverse() * p


func to_picture(model_point: Vector3) -> Vector2:
	## a point on the creature (its own space) in this node's units
	var q := cam.unproject_position(model.global_transform * model_point)
	return (q - _at) * RENDER_PPU / ppu


static func premultiplied() -> CanvasItemMaterial:
	## the 3D picture's soft edges (and the foxfire's added glow) are already mixed with the clear background: draw it
	## as such, or the fur gets a dark fringe and the glow vanishes
	var m := CanvasItemMaterial.new()
	m.blend_mode = CanvasItemMaterial.BLEND_MODE_PREMULT_ALPHA
	return m


static func _build_world(into: Node, camera: Camera3D, r: Dictionary) -> void:
	## the renders' camera (orthographic, 40 degrees round, 9 down) and their lights, which ride with the camera
	var env := Environment.new()
	env.background_mode = Environment.BG_CLEAR_COLOR
	env.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	env.ambient_light_color = Color(0.95, 0.97, 1.0)
	env.ambient_light_energy = 0.32
	env.tonemap_mode = Environment.TONE_MAPPER_LINEAR
	env.tonemap_exposure = 0.85
	var we := WorldEnvironment.new()
	we.environment = env
	into.add_child(we)
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.far = 200.0
	into.add_child(camera)
	var tgt := Vector3(r["center"][0], r["center"][1], r["center"][2])
	var az := deg_to_rad(r["azimuth"])
	var pitch := deg_to_rad(r["pitch"])
	# Blender's camera sits at centre + (sin az cos p, -cos az cos p, sin p) * 40; in Godot's axes that is (x, z, -y)
	camera.position = tgt + Vector3(sin(az) * cos(pitch), sin(pitch), cos(az) * cos(pitch)) * 40.0
	camera.look_at(tgt, Vector3.UP)
	for l in [[Vector3(-5, 6, 9), 0.85, Color(1.0, 0.96, 0.9)], [Vector3(8, -2, 3), 0.3, Color(0.95, 0.97, 1.0)], [Vector3(6, 4, 2), 0.22, Color(1.0, 0.92, 1.0)]]:
		var d := DirectionalLight3D.new()
		d.light_energy = l[1]
		d.light_color = l[2]
		camera.add_child(d)
		d.look_at_from_position(l[0], Vector3.ZERO, Vector3.UP)
	var top := DirectionalLight3D.new()
	top.light_energy = 0.18
	into.add_child(top)
	top.look_at_from_position(Vector3(0.5, 11, -0.3), Vector3.ZERO, Vector3(0, 0, -1))


func _process(_delta: float) -> void:
	var shown := is_visible_in_tree()
	if shown != _shown:
		_shown = shown
		view.render_target_update_mode = SubViewport.UPDATE_ALWAYS if shown else SubViewport.UPDATE_DISABLED
		model.process_mode = Node.PROCESS_MODE_INHERIT if shown else Node.PROCESS_MODE_DISABLED
