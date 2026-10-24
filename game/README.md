# Meadow prototype (step 1)

The first playable slice of `docs/first-ten-minutes.md`, with one creature (the fox or the unicorn) in one place (the
meadow).
Godot 4.7.2, Mobile renderer, landscape or portrait, iPad first. The creatures are live 3D models drawn into the 2D
meadow (see "Live 3D foxes" below).

## What a child can do
- **Choose a creature:** at dawn three soap bubbles float over the nest, each with a live creature inside (fox, unicorn,
  collie). Tap one: it gives a happy hop, the other bubbles drift away, and the chosen one floats into the egg. No
  words needed. (A facilitator can fix the kind instead, in the parent area.)
- **Hatch the egg:** tap it (or rub across it) four times. It glows to invite a touch and wobbles if left alone.
- **Pet the fox:** tap it. It answers with a chirp, hearts and a reaction that fits its temperament (calm, playful or curious).
- **Walk it:** drag it, or tap anywhere on the meadow to call it over.
- **Feed it:** drag an apple from the tree to its mouth, or drop one near it on the grass and it walks over to eat.
  Apples grow back.
- **Name tag:** the paw tag above the fox opens the parental gate, then a name field for a grown-up.
- **Dress up:** the basket in the bottom-right corner holds a flower crown, a scarf and a bow. Drag one onto a fox and
  it wears it (crown on its head, scarf round its neck, bow on a tail); it stays on through walking, turning, eating and
  sleeping. Drag it off to take it back; a tap on it pats the fox as usual.
- **The pond:** a signpost by the sandy path (a drop of water on it) sends the fox along the path to the pond, and the
  view slides there with it; the signpost at the pond (the apple tree on it) leads back. Tap the water: ripples spread,
  creatures nearby look, and the fox walks to the shore, drinks and splashes. A basket at the pond holds a flowering
  plant, a lantern (it glows at night) and a ball: drag them onto the grass, anywhere; tap the plant and it sways, tap
  the ball and it rolls, and a fox runs after it. Creatures never walk into the water.
- **It looks at you:** while a finger is on the meadow (or carries an apple), a fox that isn't busy turns its head to
  look at it.
- **A second fox and an egg:** about four minutes after the hatch, an adult fox in other colours trots in and sits by
  the nest, and the nest glows. Bring your fox over (drag it, or tap the meadow next to the other one): the two sit
  either side of the nest, greet each other, and an egg appears. The trait picker opens: the parents stand at the
  sides and the baby in the middle; between them, for coat colour and then glow colour (tail tips and foxfire), the
  button on a parent's side gives the baby that parent's colour, and the baby changes at once. The big tick closes
  it; tap or rub the egg to hatch a small baby fox in those colours, which keeps close to your fox. The nest glows
  again 40 seconds later, up to three babies. A tap on the meadow calls whichever fox was touched last.
- **Babies grow up:** over about three minutes of island time (faster with the demo speed) a baby grows to an adult's
  size; halfway and when grown it stretches up with sparkles and a chirp, its voice gets lower, and grown it gets an
  adult's fur.
- **Every creature has a name tag:** the second adult and each baby get their own paw tag; tapping one opens the
  parental gate, then a name field for that creature. Tags over creatures standing close together stack up.

Variant A (visible needs): about a minute after hatching, the fox looks at the tree and sighs, and the apples
bounce and glow. It repeats every 22 seconds until the fox is fed, then comes back after 150 seconds. Nothing bad
happens if it's ignored. At the pond it gets thirsty a little while after it
arrives: it looks at the water and sighs, and the water glints, until it has a drink. Variant B shows no cues.

Island time runs from dawn to dusk in about ten minutes, then has a short night. Around minute 8 a soft rain shower
passes (the light dims, drops ripple the pond, the creatures look up), and a rainbow follows it. As dusk falls the
lanterns light and every creature yawns; the baby (or the child's creature, while it has none) gets sleepy first and
curls up a little after 18:30 island time, the others at 20:00. In variant A the sleepy one yawns now and then and
sleepy z's drift up before it curls up. A tap on a sleeping creature tucks it in under a patchwork blanket; the next
tap wakes it. Everyone wakes at dawn. The sun or moon in the top-left corner switches between day and night.

## For the facilitator
Press and hold the round button with three dots in the top-right corner (about a second), answer the grown-ups question, and the parent area opens. In it:
- the creature's name;
- variant A or B;
- temperament;
- island-time speed (fast for demos);
- music on or off;
- **Bring the second fox now**, instead of waiting about four minutes after the hatch;
- **First creature: Child picks, Fox, Unicorn or Collie**, for the next session. "Child picks" (the default) shows the
  three bubbles at the start; a fixed kind skips them and the egg hatches that kind. The second adult and the babies are
  the same kind. The collie's traits are its dark coat and its white parts (paw buttons in the trait picker);
- **3D creature check and speed test**, the live creature on its own with every clip, and a speed test (see below);
- **New session** for the next child: a new egg and a new log.

Each session writes a tab-separated event log on the device. In the parent area, **Show event log** displays it with
a **Copy all** button; this works on the iPad too, where the log sits in the browser's storage. The log holds no
name and no identifiers.

## Live 3D foxes
Every fox is the same 3D model, a standard Godot scene (`creatures/fox/fox.scn`): a Skeleton3D with 44 bones (body,
head, ears, six along each tail, hip, knee and paw for each leg, the foxfires, and neck helpers), a skinned "Skin" and
"Fur" mesh with the four poses (sit, stand, sphinx, curled up) and the breathing as blend shapes, and an
AnimationPlayer with every clip: idle, walk, eat, happy, hungry, lie down, sleep, wake up, and a half turn sitting or
standing from either side. `creatures/creature_model.gd` runs it: it plays the clips (each blending into the next over
0.2 seconds, except out of a turn), adds the fur layers, the trait colours and the idle blinks, and turns the fox to
face either way. `creatures/head_look.gd` (a skeleton modifier) turns the head and neck toward something after the
clip. Things to wear (`scripts/wardrobe.gd`, made in code) sit at places the build found on the fox, the top of the
head, the ribbon round the neck and a tail near its tip, each carried by its bone and placed for every pose. Fur is shell fur: the furry skin plus 6 thin copies
of it (4 for babies) stacked in one mesh and lifted along the fur when the game starts, so the skeleton carries them
(the web renderer gives shaders no tangents, so the fur can't be grown in the shader), with holes cut by a small stored
noise texture (`creatures/shaders/`). Coat
and glow colours are worked out by the shaders, so a new colour costs no download. The fox is about 1.1 MB to download.

**The unicorn** (`creatures/unicorn/unicorn.scn`, about 1.3 MB) is the new one built from scratch
(`art/generators/unicorn2.py`, with the v1 hair): `art/generators/unicorn2_live_export.py` builds it standing, at game
density (about 52 thousand triangles, 28 thousand of them hair; no fur layers, its coat is smooth), with closed eyes for
blinking, a skeleton (body, three neck bones, head, ears, three bones down each leg, four along the tail) and skin
weights, scaled to about the fox's size and mirrored so its decorated side (garland, freckles, crown) faces the game's
camera. `tools/build_unicorn.gd` writes every clip as bone turns: idle, a four-beat walk, a nibble, a little prance,
looking up and sighing, lying down, sleeping, a yawn, and the half turns. Its coat and mane are its two traits,
recoloured by part, with eight coats and six manes in `scripts/traits.gd`. (The first, placeholder unicorn still builds
with `UNICORN=1` from `art/exports/unicorn_live`.) `tests/clip_sheet.tscn -- OUT_DIR unicorn` photographs every clip,
and `tests/autoplay.tscn -- OUT_DIR unicorn` plays the whole session with it.

**Building a creature:** `art/generators/fox_live_export.py` (Blender) exports the fox's mesh in its four poses with
its fur and rig data to `art/exports/`; then `godot --headless --path . -s res://tools/build_fox.gd` builds the scene in
about three seconds, with `tools/creature_builder.gd` doing the parts every creature shares (skin weights, blend
shapes, skeleton, baking clips into animations, saving). The clips are baked from the same motion curves the Blender
renders used, and the build checks the skinned fox against those curves vertex by vertex: the average gap is under a
hundredth of a screen pixel, the largest about two pixels at a few neck points (eating) and a slightly higher paw in
mid-step.

In the meadow each fox renders in its own small 3D world into a picture round its feet (`scripts/fox_view.gd`), which
the creature (`scripts/creature.gd`) moves, scales for depth, squashes and sorts like any 2D thing, so the nest, apples
and night tint work as before. A tiny fox is drawn out of sight at start-up so the model loads and the 3D shaders are
built before the egg hatches. On the native-app renderer the fur's strand edges are smoothed; the web build can't do
that, so its fur is a little grainier than the app's will be.

**3D creature check** (parent area): the live creature alone, as big as in the game, with buttons for every clip, close-up, spin
(or drag it), fur layers 4/6/8/12/off, colours and the speed test. The meadow's own foxes stop drawing while it is open.

**Speed test** runs eight set-ups for about five seconds each, with the foxes walking: no 3D fox, one fox with no fur,
6 fur layers, 6 layers with the 3D over the whole screen, 6 layers without edge smoothing, then five foxes (two adults,
three babies, as in the game) with no fur, 4 layers with 2x smoothing, and 6 layers. It then lists, for each, the
frames a second, the slowest frame, the share of frames slower than 20 ms, the time the game code takes a frame and
the draw calls a frame, and writes the same to the event log. Little game-code time in a slow set-up means the
graphics chip is the limit. A browser never goes above the screen's 60 frames a second, so set-ups that reach 60 show
only that they fit. `godot --path . res://tests/speed_run.tscn -- SECONDS [OUT_DIR]` runs it on a computer (without the 60 frame cap).

## Stand-ins
- The fox's motions are the curves from the Blender renders, now computed live. The walk plays at the speed that
  keeps a paw on the ground in step with the meadow. Switching between loops (walking to sitting) still jumps; a short
  squash hides it.
- Trait colours (values in `scripts/traits.gd`): the coat's apricot band and the bright foxfire band get new colours,
  everything else stays. Eight coats and five glows. The baby is the adult model at about two thirds size.
- The meadow and the pond are rendered in 3D from code with the creatures' light (`art/generators/meadow3d.py`,
  Blender): the sky, hills, grass, flowers, path and the pond (water, lily pads, bulrushes, stones) as one backdrop
  saved as two halves (`art/meadow3d/meadow.png` and `meadow_east.png`, both imported as WebP at quality 0.9: the
  grass is too noisy for the graphics-chip formats to pack small, so these two are about 2 MB to download instead of
  about 19), and the tree, nest, egg, lanterns, signposts, baskets, apples and the things
  to wear and to place as their own pictures, each with the canvas and origin of the drawing it replaced, so nothing
  in the game moved. The fixed props cast their shadows into the backdrop; the plant and lantern to place carry their
  own soft shadow, and the ball gets one from the game (it spins). The game draws the ripples and glints on the water.
  At dusk the lanterns fade over to pictures of them lit (`lantern_lit.png`, `lantern2_lit.png`, paper shades glowing
  amber), which the night's tint is kept off, so they shine in the dark.
  The signposts' pictures (a drop of water, a little apple tree; `icon_water.png`, `icon_tree.png`) are rendered the
  same way, without shadows, as they bob on the boards. Only the heart, sparkle and paw are still drawings
  (`art/generators/meadow.py`).
- The sounds are synthesised (`art/generators/sfx.py`). The collie has its own voice (`sfx/collie_*.wav`: a soft
  "wuf" for the chirp, little yips, happy yips with a pant, a sigh through the nose, a squeaky yawn); a creature plays
  its kind's own version of a sound where there is one (`Sfx.voiced`), else the shared one.
- The music is made from code (`art/generators/music.py`): a day tune (76 beats a minute: a warm pad, a soft bass and a
  music-box melody over Fmaj7, Dm7, Bbmaj7, Csus4, Fmaj7, Am7, Bbmaj7, C7) and a slower, lower night lullaby on the
  same chords, each a seamless loop of 16 bars. `scripts/music.gd` plays both and crossfades them with island time (the
  lullaby comes in as dusk falls), a little softer under the rain. About 1 MB together (22 kHz, compressed).

## Running
- **Desktop:** open the folder in Godot 4.7.2 and press Play. The mouse acts as a finger.
- **iPad, without a Mac:** open https://desphyxia.github.io/unibox/ in Safari. Every push that changes `game/`
  rebuilds that page (`.github/workflows/pages.yml`).
- **Local web build:** export the "Web" preset to `build/web`, run `python serve_web.py`, and open the printed
  address on the same Wi-Fi. Sound is off this way, because a home network serves plain http.
- **Automated check:** `godot --path . res://tests/autoplay.tscn -- OUT_DIR [fox|unicorn|collie]` plays through the session (choosing that kind's bubble first) with simulated
  touches and saves a screenshot at each step. `godot --path . res://tests/turn_check.tscn -- [fox|unicorn|collie]`
  turns a creature round sitting and standing and prints how far its picture moves each frame, so a jump when a turn
  ends shows up as one big step.
