# Prototype art

All art is generated as code (SVG). No person draws or cleans up the art (user decision, 2026-10-16). The chosen look is **soft pastel**.

**Quality bar:** `quality-bar.md` sets the round 5 unicorn as the minimum level of detail and ambition, and keeps the register of open weak parts. Read it before drawing anything new.

## Layout
- `generators/` Python scripts that write SVG files. Run `python artgen3.py OUTDIR` (standard library only).
  - `artgen.py` round 1: three styles (soft pastel, bold graphic, painterly), scene and trait variants.
  - `artgen2.py` round 2: detailed foal, pastel and painterly.
  - `artgen3.py` round 3: full unicorn built from one body outline plus tapered ribbons for limbs and hair; colour variants; head close-up.
  - `artgen5.py` round 5 (current): round 4 plus a rebuilt wing (arm with three feather rows; raised and folded forms), a lying sleeping pose, and a fix for the head's coat gradient. Same usage.
  - `seahorse.py` rounds 6-8 (first non-unicorn creature): a spine-ribbon skeleton with a curled tail, fin fans, flowing crest and back ridge; poses idle, swim, sleep; front and back views with widths taken from the side view; traits fin, ridge, crest, tail fin, snout length, pattern (stars, spots, stripes). `main` renders one style (stripes, tail fin, veil fin, crest) in all five views. Imports helpers from `artgen5.py`. Run `python seahorse.py OUTDIR`.
  - `seahorse3d.py` round 9: the sea-horse as one 3D model (body, head, hair, fins, stripes, face), rendered with Blender from any camera. Run `blender -b -P seahorse3d.py -- OUTDIR [--quick] idle:side idle:three idle:front idle:back swim:side sleep:side sleep:three` (Blender 4.5 LTS, headless; pose numbers come from `seahorse.py`). Output is a transparent PNG per view. `backdrop.py OUT.svg` writes the matching underwater scene, which is composited behind.
  - `unicorn3d.py` round 10: the unicorn as one 3D model from the same pose numbers as `artgen5.py` (stand, walk, sleep; side, three-quarter, front, back), wings spread outward, spiral horn, fused body (voxel union), feather-sheet wings, ribbon mane. Needs numpy (ships with Blender). Round 11 look: rounder proportions, Bloom palette, flowers trait, prance pose; `--wings` switches the wing trait on; `backdrop_bloom.py OUT.svg` writes the watercolour backdrop. `UNI_BARE=1` renders body and head only; a view can be zoomed with `front@x,z,ortho`. Run `blender -b -P unicorn3d.py -- OUTDIR [--quick] stand:side ...`. `backdrop_unicorn.py OUT.svg` writes the meadow backdrop.
  - `fox3d.py` round 13: the fox spirit (kitsune) as one 3D model built directly in 3D (poses sit, stand, play, sleep; views side, three, front, back; zoom with `view@x,z,ortho`). Fused body, lofted head with a pointed muzzle, cupped ears, the unicorn's decal eyes, one traced mouth, kitsune markings, foxfire, ribbon with bell, ear flower. Fur is real hair strands (Blender curves, about 300-470 thousand per picture) grown and combed by code with clumping into tufts; `FOX_FUR=0.3` thins it for quick checks, `FOX_NOFUR=1` turns it off. `--tails=N` (1-9) is the tail-count trait. Run `blender -b -P fox3d.py -- OUTDIR [--quick] [--tails=N] sit:three ...`; a full-quality picture takes about 3-5 minutes on the CPU.
  - Animation (round 14): `blender -b -P fox3d.py -- OUTDIR --anim=sit:three --size=640 [--frames=24]` renders a seamless idle loop through `FoxRig` (the model is built once and deformed per frame; fur follows the skin). Set `FOX_NOGROUND=1` for game sprites (no baked shadow). `FOX_SAMPLES` and `FOX_FRAMES=0,6,12` help quick checks. `lineup3d.py` renders all creatures in one scene. The Godot playback test is `prototype/fox-sprite-test`.
  - `artgen4.py` round 4: a rig. A pose is a body outline, crest and throat curves, four leg chains, a head placement and hair directions. Poses: stand, walk, sleep; mirrored front-view portrait; traits: wings, bobbed mane, star/spot/sock patterns; colour sets. No SVG filters.
- `tools/svgtest.gd` loads an SVG with Godot's own loader and saves a PNG (`godot --headless -s svgtest.gd -- in.svg out.png scale`), to check how Godot renders it.
- `samples/` generated SVG output for each round. Text only; screenshots and videos are not committed.

## Notes
- Round 5 samples (`samples/round5-wings-sleep/`) were loaded in Godot 4.7.2's loader and matched the browser. Winged images are 150-220 KB each.
- Round 4 SVGs were loaded in Godot 4.7.2's SVG loader and matched the browser, after one fix: a clip path holding several shapes was clipped wrongly, so all clip shapes are merged into one path with consistent winding. Not yet tested in a running scene or on a device.
- Round 3 and earlier used blur filters; round 4 uses radial gradients instead.
- These are sketches to judge direction, not production assets.
