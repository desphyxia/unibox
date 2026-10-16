# Prototype art

All art is generated as code (SVG). No person draws or cleans up the art (user decision, 2026-10-16). The chosen look is **soft pastel**.

## Layout
- `generators/` Python scripts that write SVG files. Run `python artgen3.py OUTDIR` (standard library only).
  - `artgen.py` round 1: three styles (soft pastel, bold graphic, painterly), scene and trait variants.
  - `artgen2.py` round 2: detailed foal, pastel and painterly.
  - `artgen3.py` round 3: full unicorn built from one body outline plus tapered ribbons for limbs and hair; colour variants; head close-up.
- `samples/` generated SVG output for each round. Text only; screenshots and videos are not committed.

## Notes
- Shading in the pastel version uses SVG blur filters. Godot's SVG renderer may not support filters (from documentation, untested), so final art would be rendered to PNG layers.
- These are sketches to judge direction, not production assets.
