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

Variant A (visible needs): about a minute after hatching, the fox looks at the tree and sighs, and the apples
bounce and glow. It repeats every 22 seconds until the fox is fed, then comes back after 150 seconds. Nothing bad
happens if it's ignored. Variant B shows no cues.

Island time runs from dawn to dusk in about ten minutes, then has a short night.

## For the facilitator
Press and hold the dots in the top-right corner, answer the grown-ups question, and the parent area opens. In it:
- the creature's name;
- variant A or B;
- temperament;
- island-time speed (fast for demos);
- **New session** for the next child: a new egg and a new log.

Each session writes a tab-separated event log on the device. In the parent area, **Show event log** displays it with
a **Copy all** button; this works on the iPad too, where the log sits in the browser's storage. The log holds no
name and no identifiers.

## Stand-ins
- Rendered: the sitting idle loop and a walk cycle. The walk plays at the speed that keeps a paw on the ground in
  step with the meadow. Reactions and eating are still squashes, hops and tilts of the idle loop.
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
