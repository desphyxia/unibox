# Meadow prototype (step 1)

The first playable slice of `docs/first-ten-minutes.md`, with one creature (the fox) in one place (the meadow).
Godot 4.7.2, Mobile renderer, landscape or portrait, iPad first. The creatures are live 3D models drawn into the 2D
meadow (see "Live 3D foxes" below).

## What a child can do
- **Hatch the egg:** tap it (or rub across it) four times. It glows to invite a touch and wobbles if left alone.
- **Pet the fox:** tap it. It answers with a chirp, hearts and a reaction that fits its temperament (calm, playful or curious).
- **Walk it:** drag it, or tap anywhere on the meadow to call it over.
- **Feed it:** drag an apple from the tree to its mouth, or drop one near it on the grass and it walks over to eat.
  Apples grow back.
- **Name tag:** the paw tag above the fox opens the parental gate, then a name field for a grown-up.
- **Dress up:** the basket in the bottom-right corner holds a flower crown, a scarf and a bow. Drag one onto a fox and
  it wears it (crown on its head, scarf round its neck, bow on a tail); it stays on through walking, turning, eating and
  sleeping. Drag it off to take it back; a tap on it pats the fox as usual.
- **It looks at you:** while a finger is on the meadow (or carries an apple), a fox that isn't busy turns its head to
  look at it.
- **A second fox and an egg:** about four minutes after the hatch, an adult fox in other colours trots in and sits by
  the nest, and the nest glows. Bring your fox over (drag it, or tap the meadow next to the other one): the two sit
  either side of the nest, greet each other, and an egg appears. The trait picker opens: the parents stand at the
  sides and the baby in the middle; between them, for coat colour and then glow colour (tail tips and foxfire), the
  button on a parent's side gives the baby that parent's colour, and the baby changes at once. The big tick closes
  it; tap or rub the egg to hatch a small baby fox in those colours, which keeps close to your fox. The nest glows
  again 40 seconds later, up to three babies. A tap on the meadow calls whichever fox was touched last.

Variant A (visible needs): about a minute after hatching, the fox looks at the tree and sighs, and the apples
bounce and glow. It repeats every 22 seconds until the fox is fed, then comes back after 150 seconds. Nothing bad
happens if it's ignored. Variant B shows no cues.

Island time runs from dawn to dusk in about ten minutes, then has a short night. At night the fox dozes off and
sleeps until dawn; a tap wakes it. The sun or moon in the top-left corner switches between day and night.

## For the facilitator
Press and hold the dots in the top-right corner, answer the grown-ups question, and the parent area opens. In it:
- the creature's name;
- variant A or B;
- temperament;
- island-time speed (fast for demos);
- **Bring the second fox now**, instead of waiting about four minutes after the hatch;
- **3D fox check and speed test**, the live fox on its own with every clip, and a speed test (see below);
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

**3D fox check** (parent area): the live fox alone, as big as in the game, with buttons for every clip, close-up, spin
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
- The meadow art is drawn from code (`art/generators/meadow.py`).
- The sounds are synthesised (`art/generators/sfx.py`).
- There's no music yet.

## Running
- **Desktop:** open the folder in Godot 4.7.2 and press Play. The mouse acts as a finger.
- **iPad, without a Mac:** open https://desphyxia.github.io/unibox/ in Safari. Every push that changes `game/`
  rebuilds that page (`.github/workflows/pages.yml`).
- **Local web build:** export the "Web" preset to `build/web`, run `python serve_web.py`, and open the printed
  address on the same Wi-Fi. Sound is off this way, because a home network serves plain http.
- **Automated check:** `godot --path . res://tests/autoplay.tscn -- OUT_DIR` plays through the session with simulated
  touches and saves a screenshot at each step.
