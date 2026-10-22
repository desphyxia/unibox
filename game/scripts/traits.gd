class_name Traits
## The traits a creature can inherit, in the first session two of them: coat colour and glow colour (tail tips and
## foxfire). Both are made by the live fox's shaders recolouring its model's colours (trait_colour in
## creatures/shaders/creature.gdshaderinc), so a new colour costs no download. A baby takes each trait from one of its parents,
## as the child chooses.

const BASE_COAT := Color("ffa877")             ## the rendered apricot, the mid tone of the coat
const BASE_GLOW := Color("f2a0e6")

## coat: hue turn (degrees), saturation and brightness factors
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
## glow: new hue (degrees, below 0 keeps the rendered pink) and a saturation factor
const GLOWS := {
	"pink": [-1.0, 1.0],
	"blue": [205.0, 1.4],
	"gold": [45.0, 1.7],
	"green": [140.0, 1.3],
	"violet": [270.0, 1.3],
}
const TYPES := ["coat", "glow"]
const DEFAULT := {"coat": "apricot", "glow": "pink"}


static func swatch(type: String, value: String) -> Color:
	## the trait's colour, for the trait picker's buttons
	if type == "coat":
		var c: Array = COATS[value]
		return Color.from_hsv(fposmod(BASE_COAT.h + c[0] / 360.0, 1.0), clampf(BASE_COAT.s * c[1], 0, 1), clampf(BASE_COAT.v * c[2], 0, 1))
	var g: Array = GLOWS[value]
	if g[0] < 0.0:
		return BASE_GLOW
	return Color.from_hsv(g[0] / 360.0, clampf(BASE_GLOW.s * g[1], 0, 1), 1.0)


static func other_than(t: Dictionary) -> Dictionary:
	## a second creature that differs from t in every trait
	var out := {}
	for type in TYPES:
		var pool: Array = (COATS if type == "coat" else GLOWS).keys()
		pool.erase(t.get(type, ""))
		out[type] = pool.pick_random()
	return out
