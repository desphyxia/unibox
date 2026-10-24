class_name StoryText
## The storybook's words (docs/storybook.md): fixed sentences with a few wordings each, filled in with the names, the
## kind, the colours, the temperament and the island time. Never generated, and only about what happened.
## A page keeps its wording while the book is open (the choice comes from the moment itself), and the names are read
## when the book is opened, so a name given later shows on every page.

const NUMBERS := ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven",
	"twelve", "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty"]
const THINGS := {"crown": "a crown", "scarf": "a scarf", "bow": "a bow", "plant": "a flowering plant",
	"lantern": "a lantern", "ball": "a ball"}
## what each kind's two traits are called (the second is the fox's glowing tail tips, the unicorn's mane, the collie's
## white parts)
const TRAIT_WORDS := {
	"fox": {"coat": "coat", "glow": "glow"},
	"unicorn": {"coat": "coat", "glow": "mane"},
	"collie": {"coat": "coat", "glow": "markings"},
}
const TEMPERS := {
	"calm": ["A calm little %s from the very first moment.", "A gentle, calm little %s."],
	"playful": ["A playful little %s, ready for fun.", "A bouncy, playful little %s."],
	"curious": ["A curious little %s, keen to see everything.", "A curious little %s, nose first into the world."],
}

var story: Story


func _init(s: Story) -> void:
	story = s


# ------------------------------------------------------------------ names and words
func kind_word() -> String:
	return Game.kind


func name_of(who: String) -> String:
	## the creature's name, or a description when it has none
	if who == "first" or who == "":
		return Game.creature_name if Game.creature_name != "" else "the little %s" % kind_word()
	var c := story.creature_of(who)
	if c and c.pet_name != "":
		return c.pet_name
	if who == "second":
		return "the friend"
	if who.begins_with("baby"):
		var n := who.trim_prefix("baby").to_int()
		return "the baby" if story.babies() <= 1 else "the %s baby" % ["first", "second", "third", "fourth"][clampi(n - 1, 0, 3)]
	return "a %s" % kind_word()


func trait_phrase(traits: Dictionary) -> String:
	## "a mint coat and a gold glow"
	var w: Dictionary = TRAIT_WORDS.get(Game.kind, TRAIT_WORDS["fox"])
	var second: String = "%s %s" % [traits["glow"], w["glow"]]
	return "a %s %s and %s" % [traits["coat"], w["coat"], second if w["glow"].ends_with("s") else _a(second)]


func inherited(traits: Dictionary, from: Dictionary) -> String:
	## "Pip's mint coat and Bramble's gold glow", or "Bramble's gold coat and blue glow" when both came from one parent
	var w: Dictionary = TRAIT_WORDS.get(Game.kind, TRAIT_WORDS["fox"])
	var parents := ["first", "second"]
	var a: String = name_of(parents[from.get("coat", 0)])
	var b: String = name_of(parents[from.get("glow", 0)])
	if from.get("coat", 0) == from.get("glow", 0):
		return "%s %s %s and %s %s" % [_own(a), traits["coat"], w["coat"], traits["glow"], w["glow"]]
	return "%s %s %s and %s %s %s" % [_own(a), traits["coat"], w["coat"], _own(b), traits["glow"], w["glow"]]


func when(hour: float) -> String:
	if hour < 7.0:
		return "at dawn"
	if hour < 11.0:
		return "in the morning"
	if hour < 14.0:
		return "around midday"
	if hour < 17.5:
		return "in the afternoon"
	if hour < 20.0:
		return "as the sun set"
	return "in the night"


static func number(n: int) -> String:
	return NUMBERS[n] if n >= 0 and n < NUMBERS.size() else str(n)


static func times(n: int) -> String:
	return "once" if n == 1 else ("twice" if n == 2 else "%s times" % number(n))


static func listing(items: Array) -> String:
	## "a crown, a scarf and a bow"
	var words: Array = items.map(func(i): return THINGS.get(i, i))
	if words.size() <= 1:
		return "".join(words)
	return ", ".join(words.slice(0, words.size() - 1)) + " and " + words[-1]


static func cap(s: String) -> String:
	return s.left(1).to_upper() + s.substr(1) if s != "" else s


static func _own(n: String) -> String:
	return n + ("'" if n.ends_with("s") else "'s")


static func _a(word: String) -> String:
	return ("an " if word.left(1).to_lower() in ["a", "e", "i", "o", "u"] else "a ") + word


func _pick(p: Dictionary, options: Array) -> String:
	return options[absi(hash(p["key"] + str(p["seconds"]))) % options.size()]


# ------------------------------------------------------------------ the pages
func cover_title() -> String:
	return "%s story" % cap(_own(name_of("first")))


func cover_line() -> String:
	var days := story.day
	var span := "one day" if days <= 1 else "%s days" % number(days)
	return "A %s %s, and %s on the island." % [Game.temperament, kind_word(), span]


func page_text(i: int) -> String:
	## the words for page i of story.pages
	var p: Dictionary = story.pages[i]
	var f: Dictionary = p["facts"]
	var n := name_of(p["who"])
	var first := name_of("first")
	var lead := ""
	if i > 0 and p.get("day", 1) > story.pages[i - 1].get("day", 1):
		lead = "The next morning, " if p["hour"] < 11.0 else "The next day, "
	var text := ""
	match p["key"]:
		"hatch":
			var taps := number(f.get("taps", 4))
			text = _pick(p, [
				"%s hatched %s, after %s taps on the egg." % [cap(n), when(p["hour"]), taps],
				"After %s taps on the egg, %s hatched %s." % [taps, n, when(p["hour"])],
			])
			var tem: Array = TEMPERS.get(f.get("temperament", "playful"), TEMPERS["playful"])
			text += " " + (_pick(p, tem) % kind_word())
		"meal":
			if f.get("how", "hand") == "ground":
				text = _pick(p, ["%s found an apple in the grass and crunched it all up." % cap(n),
					"An apple lay in the grass, and %s ate every bit." % n])
			else:
				text = _pick(p, ["%s first meal was an apple, carried all the way from the tree." % cap(_own(n)),
					"An apple from the tree, held out just right: %s first meal." % _own(n)])
		"dressed":
			var items: Array = f.get("items", [])
			text = _pick(p, ["Dressing up! %s tried on %s." % [cap(n), listing(items)],
				"%s tried on %s, and looked splendid." % [cap(n), listing(items)]])
		"drink":
			text = _pick(p, ["At the pond, %s had a long drink of cool water." % n,
				"%s found the pond and lapped up a drink." % cap(n)])
		"placed":
			var items: Array = f.get("items", [])
			var verb := "found its place" if items.size() == 1 else "found their places"
			text = "%s %s by the pond." % [cap(listing(items)), verb]
		"ball":
			text = _pick(p, ["%s chased the ball across the grass." % cap(n), "Ball time! %s ran after it, again and again." % cap(n)])
		"rainbow":
			text = _pick(p, ["Rain fell on the island, and then a rainbow came out.",
				"After the rain, a rainbow arched over the %s." % f.get("place", "meadow")])
		"bedtime":
			var tucked: Array = f.get("tucked", [])
			if tucked.has(p["who"]):
				text = "%s, %s curled up and was tucked in under a blanket." % [cap(when(p["hour"])), n]
			elif not tucked.is_empty():
				text = "%s, %s curled up to sleep, and %s was tucked in under a blanket." % [cap(when(p["hour"])), n, name_of(tucked[0])]
			else:
				text = "%s, %s curled up to sleep." % [cap(when(p["hour"])), n]
		"friend":
			var looks := trait_phrase(f)
			if story.creature_of("second") and story.creature_of("second").pet_name != "":
				text = "A friend came to the nest: %s, a %s with %s." % [n, kind_word(), looks]
			else:
				text = "A friend came to the nest: a %s with %s." % [kind_word(), looks]
		"pair":
			text = "%s and %s met by the nest. Hearts, and then an egg!" % [cap(first), name_of("second")]
		"egg":
			text = "A new egg lay in the nest. The baby would have %s." % inherited(f["traits"], f["from"])
		_:
			if p["key"].begins_with("hatch_"):
				if story.has("egg") and story.page("egg")["facts"]["traits"] == f["traits"] and p["who"] == "baby1":
					text = _pick(p, ["Crack! Out came %s, small and new, close by %s." % [n, first],
						"%s hatched, tiny and wobbly, and stayed close to %s." % [cap(n), first]])
				else:
					text = "Another egg hatched: %s, with %s." % [n, inherited(f["traits"], f["from"])]
			elif p["key"].begins_with("grown_"):
				var named := story.creature_of(p["who"]) != null and story.creature_of(p["who"]).pet_name != ""
				text = _pick(p, ["%s grew all the way up, as big as %s now." % [cap(n), first],
					("Little %s grew up." % n) if named else "%s grew and grew, all the way up." % cap(n)])
	if lead != "" and text != "":
		text = lead + (text if _starts_with_name(text) else text.left(1).to_lower() + text.substr(1))
	return text


func _starts_with_name(text: String) -> bool:
	var names := [Game.creature_name]
	for c in story.main.creatures:
		if is_instance_valid(c):
			names.append(c.pet_name)
	for nm in names:
		if nm != "" and text.begins_with(nm):
			return true
	return false


func closing_text() -> String:
	## the last page: what the day added up to (only what happened)
	var t := story.tally
	var bits := []
	if t.get("pets", 0) > 0:
		bits.append("was petted %s" % times(t["pets"]))
	if t.get("apples", 0) > 0:
		bits.append("ate %s %s" % [number(t["apples"]), "apple" if t["apples"] == 1 else "apples"])
	if t.get("drinks", 0) > 0:
		bits.append("had %s %s at the pond" % [number(t["drinks"]), "drink" if t["drinks"] == 1 else "drinks"])
	if t.get("balls", 0) > 0:
		bits.append("played ball %s" % times(t["balls"]))
	var family := story.babies()
	var text := ""
	if not bits.is_empty():
		var said: String = ", ".join(bits.slice(0, bits.size() - 1)) + " and " + bits[-1] if bits.size() > 1 else bits[0]
		text = "Along the way, %s %s." % [name_of("first"), said]
	if family > 0:
		text += (" " if text != "" else "") + "The family grew by %s." % ("one baby" if family == 1 else "%s babies" % number(family))
	return text if text != "" else "And that was the day."
