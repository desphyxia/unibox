# Prototype art

All art is generated as code (SVG). No person draws or cleans up the art (user decision, 2026-10-16). The chosen look is **soft pastel**.

**Quality bar:** `quality-bar.md` sets the round 5 unicorn as the minimum level of detail and ambition, and keeps the register of open weak parts. Read it before drawing anything new.

## Layout
- `generators/` Python scripts that write SVG files. Run `python artgen3.py OUTDIR` (standard library only).
  - `artgen.py` round 1: three styles (soft pastel, bold graphic, painterly), scene and trait variants.
  - `artgen2.py` round 2: detailed foal, pastel and painterly.
  - `artgen3.py` round 3: full unicorn built from one body outline plus tapered ribbons for limbs and hair; colour variants; head close-up.
  - `artgen5.py` round 5 (current): round 4 plus a rebuilt wing (arm with three feather rows; raised and folded forms), a lying sleeping pose, and a fix for the head's coat gradient. Same usage.
  - `artgen4.py` round 4: a rig. A pose is a body outline, crest and throat curves, four leg chains, a head placement and hair directions. Poses: stand, walk, sleep; mirrored front-view portrait; traits: wings, bobbed mane, star/spot/sock patterns; colour sets. No SVG filters.
- `tools/svgtest.gd` loads an SVG with Godot's own loader and saves a PNG (`godot --headless -s svgtest.gd -- in.svg out.png scale`), to check how Godot renders it.
- `samples/` generated SVG output for each round. Text only; screenshots and videos are not committed.

## Notes
- Round 5 samples (`samples/round5-wings-sleep/`) were loaded in Godot 4.7.2's loader and matched the browser. Winged images are 150-220 KB each.
- Round 4 SVGs were loaded in Godot 4.7.2's SVG loader and matched the browser, after one fix: a clip path holding several shapes was clipped wrongly, so all clip shapes are merged into one path with consistent winding. Not yet tested in a running scene or on a device.
- Round 3 and earlier used blur filters; round 4 uses radial gradients instead.
- These are sketches to judge direction, not production assets.
