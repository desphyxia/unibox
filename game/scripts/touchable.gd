class_name Touchable
extends Node2D
## Something a finger can press: main.gd hit-tests every node in the "touchable" group, picks the one on top
## (highest priority, then nearest the front) and sends it the press, the drags and the release, in world coordinates.

var touch_priority := 0


func _enter_tree() -> void:
	add_to_group("touchable")


func hit_test(_p: Vector2) -> bool:
	return false


func touch_begin(_p: Vector2) -> void:
	pass


func touch_move(_p: Vector2) -> void:
	pass


func touch_end(_p: Vector2) -> void:
	pass


## where this node is in meadow (world) coordinates, the space touches arrive in
func world_pos() -> Vector2:
	var w := get_tree().get_first_node_in_group("world") as Node2D
	return w.to_local(global_position) if w else global_position
