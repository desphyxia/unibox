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
Every fox is the same 3D model, drawn live (`compare/live_fox.gd`, `fox_live.gdshader`, `fox_fur.gdshader`,
`fox_halo.gdshader`, `fox_rig.gdshaderinc`; exported by `art/generators/fox_live_export.py`). It blends four exported
poses (sit, stand, sphinx, curled up) and computes each clip from the same motion curves the Blender renders used:
idle, walk, eat, happy, hungry, lie down, sleep, wake up, and a half turn sitting or standing. Fur is shell fur: the
furry skin drawn again as 6 thin layers (4 for babies) with holes cut by a small stored noise texture. Coat and glow
colours are worked out by the shaders, so a new colour costs no download. The model is about 1.1 MB to download and is
loaded once for every fox.

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
only that they fit. `godot --path . res://tests/speed_run.tscn -- SECONDS [OUT_DIR]` runs it on a computer.

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
