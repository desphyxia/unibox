# Meadow prototype (step 1)

The first playable slice of `docs/first-ten-minutes.md`, with one creature (the fox) in one place (the meadow).
Godot 4.7.2, Mobile renderer, landscape or portrait, iPad first.

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
- **Compare: rendered fox and live 3D fox**, a side-by-side check for deciding how creatures are made (see below);
- **New session** for the next child: a new egg and a new log.

Each session writes a tab-separated event log on the device. In the parent area, **Show event log** displays it with
a **Copy all** button; this works on the iPad too, where the log sits in the browser's storage. The log holds no
name and no identifiers.

## The live 3D comparison (`compare/`)
The parent area's **Compare** button opens the fox two ways over the meadow: on the left the rendered frames the game
uses now, on the right the same model drawn live in 3D with shell fur (`live_fox.gd`, `fox_live.gdshader`,
`fox_fur.gdshader`, `fox_rig.gdshaderinc`; the model is exported by `art/generators/fox_live_export.py`). Buttons: every
clip (idle, walk, eat, happy, hungry, lie down, wake up, turn; both foxes play it together), spin (or drag the live
fox), close-up, fur layers 4/6/8/12/off, colours (both recolour), speed test, back. The corner shows frames per
second and the live fox's triangles (about 48 thousand with 8 fur layers). The live fox blends four exported poses
(sit, stand, sphinx, curled up) and computes each clip from the same motion curves as the renders. The 3D is drawn only
in a box round the live foxes, not over the whole screen.

**Speed test** runs eight set-ups for about five seconds each, with the foxes walking: no 3D fox, one fox with no fur,
6 fur layers, 6 layers with the 3D over the whole screen, 6 layers without edge smoothing, then five foxes (two adults,
three babies, as in the game) with no fur, 4 layers with 2x smoothing, and 6 layers. It then lists the frames a
second, the slowest frame and the share of frames slower than 20 ms for each, and writes the same to the event log.
A browser never goes above the screen's 60 frames a second, so set-ups that reach 60 show only that they fit.

## Stand-ins
- Rendered: the sitting idle loop, a walk cycle, eating, a happy wiggle, the hunger look and sigh, lying down to
  sleep (played backward to wake), a sleep loop, and turning round (sitting or standing). The walk plays at the speed that keeps a paw on the ground in
  step with the meadow. Every animation is rendered facing each way (folders ending `_left`); a turn
  plays a rendered clip that runs from one side's rest pose round to the other's.
- Trait colours are made in the game by recolouring the rendered frames (`shaders/fur_colour.gdshader`, values in
  `scripts/traits.gd`): the coat's apricot band and the bright foxfire band get new colours, everything else stays.
  Eight coats and five glows, at no extra download. The baby is the adult's frames at about two thirds size.
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
