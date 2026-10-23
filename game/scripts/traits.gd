class_name Traits
## The traits a creature can inherit, in the first session two of them: its coat colour and its glow colour (the fox's
## tail tips and foxfire; the unicorn's mane and tail). The creature shaders recolour the model's own colours
## (trait_colour in creatures/shaders/creature.gdshaderinc), so a new colour costs no download:
##   the fox by hue (its apricot coat and its pink-violet glow get new colours);
##   the unicorn and the collie by part (each vertex says whether it is coat or mane, or the collie's dark coat or its
##   white; that part takes the new colour's hue). The collie's dark coat is nearly black, so its colours brighten it.
## A baby takes each trait from one of its parents, as the child chooses. The kind is Game.kind unless given.

const BASE_COAT := Color("ffa877")             ## the fox's rendered apricot, the mid tone of its coat
const BASE_GLOW := Color("f2a0e6")

## fox coat: hue turn (degrees), saturation and brightness factors
const COATS := {
	"apricot": [0.0, 1.0, 1.0],
	"lilac": [255.0, 0.75, 1.0],
	"mint": [130.0, 0.6, 1.02],
	"snow": [0.0, 0.18, 1.06],
	"berry": [-25.0, 1.0, 0.95],
	"sky": [190.0, 0.7, 1.02],
	"cocoa": [8.0, 0.75, 0.72],
	"gold": [25.0, 1.15, 1.05],
}
## fox glow: new hue (degrees, below 0 keeps the rendered pink) and a saturation factor
const GLOWS := {
	"pink": [-1.0, 1.0],
	"blue": [205.0, 1.4],
	"gold": [45.0, 1.7],
	"green": [140.0, 1.3],
	"violet": [270.0, 1.3],
}
## unicorn coat and mane: new hue (degrees; below 0 keeps the model's own colours), added saturation, brightness factor
const UNICORN_COATS := {
	"pearl": [-1.0, 0.0, 1.0],
	"rose": [340.0, 0.22, 1.0],
	"mint": [150.0, 0.2, 1.0],
	"lilac": [270.0, 0.22, 1.0],
	"sky": [205.0, 0.24, 1.0],
	"peach": [22.0, 0.26, 1.0],
	"butter": [50.0, 0.28, 1.0],
	"storm": [235.0, 0.14, 0.72],
}
const UNICORN_MANES := {
	"candy": [-1.0, 0.0, 1.0],
	"sunset": [22.0, 0.25, 1.0],
	"ocean": [200.0, 0.2, 0.95],
	"meadow": [115.0, 0.15, 0.92],
	"midnight": [255.0, 0.3, 0.72],
	"gold": [45.0, 0.3, 1.0],
}
## collie: the dark coat (new hue, added saturation, brightness factor: the black brightens into the colour) and the white
const COLLIE_COATS := {
	"black": [-1.0, 0.0, 1.0],
	"chocolate": [22.0, 0.45, 2.6],
	"red": [18.0, 0.55, 3.6],
	"blue": [215.0, 0.12, 3.0],
	"lilac": [285.0, 0.12, 3.4],
	"gold": [38.0, 0.55, 4.2],
	"berry": [330.0, 0.4, 3.0],
}
const COLLIE_WHITES := {
	"snow": [-1.0, 0.0, 1.0],
	"cream": [40.0, 0.15, 1.0],
	"peach": [22.0, 0.25, 1.0],
	"pink": [340.0, 0.2, 1.0],
	"mint": [150.0, 0.18, 1.0],
	"sky": [205.0, 0.2, 1.0],
}
const COLLIE_BASE_COAT := Color("2c3242")     ## the collie's own blue-black and white, for the picker's buttons
const COLLIE_BASE_WHITE := Color("eeeae1")
const UNICORN_BASE_COAT := Color("e6f2f8")     ## the unicorn's own pearly coat and candy mane, for the picker's buttons
const UNICORN_BASE_MANE := Color("f6b3cf")
const TYPES := ["coat", "glow"]
const DEFAULT := {"coat": "apricot", "glow": "pink"}
const DEFAULTS := {"fox": {"coat": "apricot", "glow": "pink"}, "unicorn": {"coat": "pearl", "glow": "candy"},
	"collie": {"coat": "black", "glow": "snow"}}
const BY_PART := {"unicorn": [UNICORN_COATS, UNICORN_MANES, UNICORN_BASE_COAT, UNICORN_BASE_MANE],
	"collie": [COLLIE_COATS, COLLIE_WHITES, COLLIE_BASE_COAT, COLLIE_BASE_WHITE]}


static func _kind(kind: String) -> String:
	return kind if kind != "" else Game.kind


static func defaults(kind := "") -> Dictionary:
	return DEFAULTS.get(_kind(kind), DEFAULT).duplicate()


static func values(type: String, kind := "") -> Dictionary:
	## every value a trait can take, for this kind
	var k := _kind(kind)
	if BY_PART.has(k):
		return BY_PART[k][0] if type == "coat" else BY_PART[k][1]
	return COATS if type == "coat" else GLOWS


static func swatch(type: String, value: String, kind := "") -> Color:
	## the trait's colour, for the trait picker's buttons
	var k := _kind(kind)
	if BY_PART.has(k):
		var u: Array = values(type, k).get(value, [-1.0, 0.0, 1.0])
		var own: Color = BY_PART[k][2] if type == "coat" else BY_PART[k][3]
		if u[0] < 0.0:
			return own
		return Color.from_hsv(u[0] / 360.0, clampf(own.s * 0.6 + u[1] + (0.12 if type == "coat" else 0.15), 0, 1), clampf(own.v * u[2], 0, 1))
	if type == "coat":
		var c: Array = COATS[value]
		return Color.from_hsv(fposmod(BASE_COAT.h + c[0] / 360.0, 1.0), clampf(BASE_COAT.s * c[1], 0, 1), clampf(BASE_COAT.v * c[2], 0, 1))
	var g: Array = GLOWS[value]
	if g[0] < 0.0:
		return BASE_GLOW
	return Color.from_hsv(g[0] / 360.0, clampf(BASE_GLOW.s * g[1], 0, 1), 1.0)


static func other_than(t: Dictionary, kind := "") -> Dictionary:
	## a second creature that differs from t in every trait
	var out := {}
	for type in TYPES:
		var pool: Array = values(type, kind).keys()
		pool.erase(t.get(type, ""))
		out[type] = pool.pick_random()
	return out
