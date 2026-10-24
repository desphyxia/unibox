class_name Wardrobe
extends Node2D
## A basket of things to wear in the corner of the meadow: a flower crown (the top of the head), a scarf (the neck) and
## a bow (a tail). Drag one onto a creature and it wears it: a small 3D model at that place on the live fox, which
## follows it through every clip and pose (creature_model.gd). Drag a worn thing off to take it back; a tap on it pets
## the creature as usual. Each thing is here once. The models are made in code, like the meadow art.

const AT := Vector2(950, 704)            ## the basket, in meadow coordinates (at the edge of where creatures walk)
const ITEMS := {
	"crown": {"place": "head", "spot": Vector2(-36, -26)},
	"scarf": {"place": "neck", "spot": Vector2(0, -40)},
	"bow": {"place": "tail", "spot": Vector2(36, -26)},
}
const INK := Color(0.29, 0.18, 0.28)
const FLOWERS := [Color("f7a8c8"), Color("c9a8f0"), Color("fff1c9"), Color("ffc3a0"), Color("a8d8f5")]

var meadow: Node2D
var items := {}                          ## id -> WearItem


func _ready() -> void:
	position = AT
	z_index = 0
	add_child(basket_sprite("basket"))
	for id in ITEMS:
		var it := WearItem.new()
		it.id = id
		it.wardrobe = self
		items[id] = it
		add_child(it)
		it.home()


static func basket_sprite(art: String) -> Sprite2D:
	## the woven basket with a handle, rendered in 3D where it stands (art/generators/meadow3d.py); its origin is the
	## basket's place
	var s := Sprite2D.new()
	s.texture = load("res://art/meadow3d/%s.png" % art)
	s.centered = false
	s.scale = Vector2.ONE * 0.5
	s.offset = Vector2(-160, -192)               # texture at 2x
	return s


func release(it: WearItem, p: Vector2) -> void:
	## let go over a creature (its body or near its head): it wears it; anywhere else it goes back to the basket
	var c: Creature = meadow._nearest(p, func(c: Creature): return c.hit_test(p) or c.head_world().distance_to(p) < 130.0)
	if c == null:
		it.home(true)
		return
	var old: String = c.wear(it.id)
	it.worn_by(c)
	if old != "" and items.has(old):
		items[old].home(true)


static func model(id: String, size: float) -> Node3D:
	## the thing in 3D, made for a place of this size (the head's half width, the neck's or the tail's radius)
	var root := Node3D.new()
	match id:
		"crown":
			var r := size * 0.5
			root.add_child(_part(_torus(r, 0.08), Color("8cc78a")))
			for k in 7:
				var a := TAU * k / 7.0
				var f := _part(_sphere(0.22), FLOWERS[k % FLOWERS.size()])
				f.position = Vector3(cos(a) * r, 0.1, sin(a) * r)
				f.scale = Vector3(1.0, 0.62, 1.0)
				root.add_child(f)
				var c := _part(_sphere(0.09), Color("ffe08a"))
				c.position = f.position + Vector3(0, 0.12, 0)
				root.add_child(c)
				var leaf := _part(_sphere(0.13), Color("7fbf7a"))
				var b := a + TAU / 14.0
				leaf.position = Vector3(cos(b) * r, 0.02, sin(b) * r)
				leaf.scale = Vector3(1.5, 0.35, 0.8)
				leaf.rotation.y = -b
				root.add_child(leaf)
		"scarf":
			var r := size * 1.04
			root.add_child(_part(_torus(r, 0.2), Color("c9a8f0")))
			for y in [-0.12, 0.12]:
				var stripe := _part(_torus(r + 0.01, 0.06), Color("fff1c9"))
				stripe.position.y = y
				root.add_child(stripe)
			var end := _part(_box(Vector3(0.5, 1.0, 0.16)), Color("c9a8f0"))
			end.position = Vector3(r * 0.85, -0.55, r * 0.55)
			end.rotation = Vector3(0.0, -0.9, 0.18)
			root.add_child(end)
			for k in 4:
				var fringe := _part(_box(Vector3(0.08, 0.2, 0.08)), Color("fff1c9"))
				fringe.position = end.position + end.basis * Vector3(-0.18 + 0.12 * k, -0.58, 0.0)
				root.add_child(fringe)
		"bow":
			var s := size / 0.19 * 2.4
			var knot := _part(_sphere(0.07 * s), Color("f58fb6"))
			root.add_child(knot)
			for side in [-1.0, 1.0]:
				var loop := _part(_torus(0.12 * s, 0.035 * s), Color("f7a8c8"))
				loop.position = Vector3(0.0, 0.03 * s, 0.15 * s * side)
				loop.rotation = Vector3(PI / 2.0, 0.0, 0.35 * side)
				loop.scale = Vector3(1.0, 1.0, 0.6)
				root.add_child(loop)
				var tail := _part(_box(Vector3(0.05, 0.2, 0.06) * s), Color("f58fb6"))
				tail.position = Vector3(0.0, -0.12 * s, 0.07 * s * side)
				tail.rotation.x = 0.4 * side
				root.add_child(tail)
	return root


static func _part(mesh: Mesh, colour: Color) -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	mi.mesh = mesh
	var m := StandardMaterial3D.new()
	m.albedo_color = colour
	m.roughness = 0.75
	m.rim_enabled = true
	m.rim = 0.12
	mi.material_override = m
	mi.cast_shadow = GeometryInstance3D.SHADOW_CASTING_SETTING_OFF
	return mi


static func _torus(r: float, thick: float) -> TorusMesh:
	var t := TorusMesh.new()
	t.inner_radius = r - thick
	t.outer_radius = r + thick
	t.rings = 32
	t.ring_segments = 10
	return t


static func _sphere(r: float) -> SphereMesh:
	var s := SphereMesh.new()
	s.radius = r
	s.height = r * 2.0
	s.radial_segments = 12
	s.rings = 6
	return s


static func _box(size: Vector3) -> BoxMesh:
	var b := BoxMesh.new()
	b.size = size
	return b


class WearItem:
	extends Touchable
	## one thing to wear: in the basket, carried by a finger, or worn (then hidden here, and drawn on the creature)

	var id := ""
	var wardrobe: Wardrobe
	var state := "basket"
	var wearer: Creature
	var _press := Vector2.ZERO
	var _moved := false
	var _sprite := Sprite2D.new()

	func _ready() -> void:
		touch_priority = 35
		_sprite.texture = load("res://art/meadow3d/wear_%s.png" % id)   # rendered in 3D, at 2x, centred on its spot
		_sprite.scale = Vector2.ONE * 0.5
		add_child(_sprite)

	func place() -> String:
		return Wardrobe.ITEMS[id]["place"]

	func home(animate := false) -> void:
		state = "basket"
		wearer = null
		_sprite.visible = true
		z_index = 2
		var spot: Vector2 = Wardrobe.ITEMS[id]["spot"]
		if animate:
			var t := create_tween()
			t.tween_property(self, "position", spot, 0.3).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
			Sfx.play("drop", 1.1, 0.05, -4.0)
		else:
			position = spot

	func worn_by(c: Creature) -> void:
		state = "worn"                         # drawn on the creature now, not here (but still there to be touched)
		wearer = c
		_sprite.visible = false             # drawn on the creature now

	func hit_test(p: Vector2) -> bool:
		match state:
			"basket":
				return p.distance_to(world_pos()) < 32.0
			"worn":
				return is_instance_valid(wearer) and p.distance_to(wearer.worn_at(place())) < 52.0 * wearer.depth_scale() * 2.0
		return false

	func touch_begin(p: Vector2) -> void:
		_press = p
		_moved = false
		if state == "basket":
			_pick_up(p)

	func touch_move(p: Vector2) -> void:
		if state == "worn" and p.distance_to(_press) > 16.0:
			wearer.take_off(place())
			Log.event("item_off", id)
			_pick_up(p)
		if state == "held":
			_moved = true
			position = p + Vector2(0, -30) - wardrobe.position   # just above the finger (the basket's space)

	func touch_end(p: Vector2) -> void:
		if state == "held":
			z_index = 2
			wardrobe.release(self, p)
		elif state == "worn" and is_instance_valid(wearer):
			wearer.pet(p)                      # a tap on what it wears is a pat

	func _pick_up(p: Vector2) -> void:
		state = "held"
		wearer = null
		_sprite.visible = true
		z_index = 85
		Sfx.play("pickup")
		var t := create_tween()
		t.tween_property(self, "scale", Vector2.ONE * 1.2, 0.12).set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
		t.tween_property(self, "scale", Vector2.ONE, 0.1)
		touch_move(p)
