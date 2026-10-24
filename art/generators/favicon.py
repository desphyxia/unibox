"""The game's icon: the browser-tab favicon and the home-screen icon of the web build (Godot uses the project icon for
both). A soft pastel unicorn head in profile on a rounded lilac-to-pink tile. Drawn for small sizes first: one bold
white head shape, a gold horn and a three-colour mane that still read at 16 pixels; the finer touches (horn spiral,
eye shine, blush) only show at the larger sizes. Gradients only, no filters (Godot's SVG importer has none).
Usage: python favicon.py OUT.svg"""
import sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "icon.svg"

DEFS = """<defs>
<linearGradient id="bg" x1="0" y1="0" x2="0.35" y2="1"><stop offset="0" stop-color="#b9a2f5"/><stop offset="0.6" stop-color="#e3a6e0"/><stop offset="1" stop-color="#ffb8cf"/></linearGradient>
<radialGradient id="glow" cx="0.72" cy="0.18" r="0.55"><stop offset="0" stop-color="#ffffff" stop-opacity="0.55"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>
<linearGradient id="coat" x1="0.3" y1="0" x2="0.7" y2="1"><stop offset="0" stop-color="#ffffff"/><stop offset="0.6" stop-color="#fff4f8"/><stop offset="1" stop-color="#f6dbe8"/></linearGradient>
<linearGradient id="horn" x1="0" y1="1" x2="0.6" y2="0"><stop offset="0" stop-color="#f2b955"/><stop offset="0.5" stop-color="#ffe08a"/><stop offset="1" stop-color="#fff8cf"/></linearGradient>
<linearGradient id="m0" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#a98cf2"/><stop offset="1" stop-color="#7d5fdc"/></linearGradient>
<linearGradient id="m1" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#ff9cc8"/><stop offset="1" stop-color="#e46fae"/></linearGradient>
<linearGradient id="m2" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#9fd4fb"/><stop offset="1" stop-color="#6aa6ec"/></linearGradient>
<radialGradient id="iris" cx="0.45" cy="0.35" r="0.75"><stop offset="0" stop-color="#8f74ee"/><stop offset="1" stop-color="#2e2070"/></radialGradient>
</defs>"""

# The head, facing right: back of the neck, poll, forehead, muzzle, chin, jaw, throat.
HEAD = ("M13 64 C12 50 15 33 25 23 C30 18 37 18 41 22 C45 26 49 31 53 36 C57 40 57 46 53 48 "
        "C49 50 44 49 40 47 C37 46 35 48 35 52 L36 64 Z")
EAR = "M25 24 C25 18 27 12 30 9 C33 13 34 18 33 22 Z"
EAR_IN = "M27.5 21 C27.6 17 28.6 14 30 12 C31.3 15 31.6 18 31 20.5 Z"
HORN = "M33 19.5 L49 5 L40 24 Z"
SPIRAL = "M37.6 17.4 L41.4 19.8 M41.4 13.6 L44.2 15.4"
# Mane locks down the back of the neck (lilac behind, pink in the middle, blue on top) and a forelock over the brow.
MANE = [
    ("m0", "M24 21 C15 25 7 37 5 50 C4 56 5 61 7 64 L16 64 C13 52 15 36 26 26 Z"),
    ("m1", "M26 20 C19 26 13 38 12 50 C12 56 13 61 15 64 L21 64 C18 54 19 40 27 29 Z"),
    ("m2", "M26 22 C22 30 20 42 21 52 C21 57 22 61 24 64 L26 64 C25 54 25 42 29 31 Z"),
    ("m1", "M28 20 C31 17 36 17 38 20 C35 21 33 24 33 28 C31 25 29 23 26 24 Z"),
]


def svg():
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">', DEFS,
             '<rect width="64" height="64" rx="14" fill="url(#bg)"/>',
             '<rect width="64" height="64" rx="14" fill="url(#glow)"/>',
             # sparkle up in the sky, right of the horn
             '<path d="M56 13 L57.2 16.8 L61 18 L57.2 19.2 L56 23 L54.8 19.2 L51 18 L54.8 16.8 Z" fill="#ffffff" fill-opacity="0.9"/>',
             f'<path d="{MANE[0][1]}" fill="url(#{MANE[0][0]})"/>',
             f'<path d="{EAR}" fill="url(#coat)" stroke="#6b4fc8" stroke-width="1.4" stroke-linejoin="round"/>',
             f'<path d="{EAR_IN}" fill="#f7b6d2"/>',
             f'<path d="{HEAD}" fill="url(#coat)" stroke="#6b4fc8" stroke-width="1.6" stroke-linejoin="round"/>',
             f'<path d="{MANE[1][1]}" fill="url(#{MANE[1][0]})"/>',
             f'<path d="{MANE[2][1]}" fill="url(#{MANE[2][0]})"/>',
             f'<path d="{HORN}" fill="url(#horn)" stroke="#c98a2e" stroke-width="1.2" stroke-linejoin="round"/>',
             f'<path d="{SPIRAL}" stroke="#d99a3a" stroke-width="0.8" stroke-opacity="0.8" stroke-linecap="round" fill="none"/>',
             f'<path d="{MANE[3][1]}" fill="url(#{MANE[3][0]})"/>',
             # eye, shine, blush, nostril, smile
             '<ellipse cx="40.5" cy="31" rx="2.9" ry="3.6" fill="url(#iris)"/>',
             '<circle cx="41.4" cy="29.6" r="1.1" fill="#ffffff"/>',
             '<ellipse cx="45" cy="40" rx="3.6" ry="2.4" fill="#ff9cc0" fill-opacity="0.55"/>',
             '<ellipse cx="52.4" cy="42.2" rx="0.9" ry="1.3" fill="#a4789a"/>',
             '<path d="M47.6 46.4 C49 47.3 50.6 47.3 51.8 46.6" stroke="#a4789a" stroke-width="0.9" stroke-linecap="round" fill="none"/>',
             '</svg>']
    return "\n".join(parts) + "\n"


if __name__ == "__main__":
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(svg())
    print("wrote", OUT)
