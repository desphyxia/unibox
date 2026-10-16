extends SceneTree

# usage: -- in.svg out.png scale [x y w h]
func _init():
	var args = OS.get_cmdline_user_args()
	var f = FileAccess.open(args[0], FileAccess.READ)
	var svg = f.get_as_text()
	var img = Image.new()
	var err = img.load_svg_from_string(svg, float(args[2]) if args.size() > 2 else 1.0)
	print("load err=", err, " size=", img.get_size())
	if args.size() >= 7:
		img = img.get_region(Rect2i(int(args[3]), int(args[4]), int(args[5]), int(args[6])))
	img.save_png(args[1])
	quit()
