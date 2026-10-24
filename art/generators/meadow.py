"""Meadow art for the playable prototype: the backdrop and the props a child touches (apple tree, apple, nest, egg, heart,
sparkle, paw tag icon). Same watercolour language as backdrop_bloom.py: soft washes with a pooled rim, gradients only
(Godot's SVG importer has no filters).

World coordinates: the guaranteed-visible area is 1024x768; the backdrop covers 2048x1024 around it (x -512..1536,
y -128..896) so wider phones and tablets in either orientation see more meadow, never an edge.
Since round 37 the meadow, the pond and the props are rendered in 3D (meadow3d.py); this script still draws the small
things the game uses (heart, sparkle, paw, the two sign pictures) and writes only those. Its other drawings stay here
as the layout the 3D scene follows.
Usage: python meadow.py OUT_DIR"""
import math, os, random, sys

OUT = sys.argv[1] if len(sys.argv) > 1 else "meadow"
os.makedirs(OUT, exist_ok=True)
rnd = random.Random(11)
USED = {"heart.svg", "sparkle.svg", "paw.svg", "icon_water.svg", "icon_tree.svg"}


def blob(cx, cy, rx, ry, jitter=0.16, n=10, rot=0.0):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n + rnd.uniform(-0.12, 0.12) + rot
        k = 1 + rnd.uniform(-jitter, jitter)
        pts.append((cx + math.cos(a) * rx * k, cy + math.sin(a) * ry * k))
    d = f"M{(pts[0][0] + pts[-1][0]) / 2:.1f} {(pts[0][1] + pts[-1][1]) / 2:.1f}"
    for i in range(n):
        p, q = pts[i], pts[(i + 1) % n]
        d += f" Q{p[0]:.1f} {p[1]:.1f} {(p[0] + q[0]) / 2:.1f} {(p[1] + q[1]) / 2:.1f}"
    return d + " Z"


class Svg:
    def __init__(self, x, y, w, h):
        self.box, self.defs, self.body, self.n = (x, y, w, h), [], [], 0

    def grad_id(self):
        self.n += 1
        return f"g{self.n}"

    def wash(self, col, cx, cy, rx, ry, a0=0.6, a1=0.12, jitter=0.16, rim=0.3, n=10, rot=0.0):
        """a watercolour wash: denser middle, pigment pooled at the edge"""
        g = self.grad_id()
        self.defs.append(f'<radialGradient id="{g}" cx="0.5" cy="0.5" r="0.55"><stop offset="0" stop-color="{col}" stop-opacity="{a0}"/>'
                         f'<stop offset="0.65" stop-color="{col}" stop-opacity="{a0 * 0.65:.2f}"/><stop offset="1" stop-color="{col}" stop-opacity="{a1}"/></radialGradient>')
        self.body.append(f'<path d="{blob(cx, cy, rx, ry, jitter, n, rot)}" fill="url(#{g})" stroke="{col}" stroke-opacity="{rim}" stroke-width="1.8"/>')

    def linear(self, stops, x1=0, y1=0, x2=0, y2=1, units=""):
        g = self.grad_id()
        s = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops)
        u = f' gradientUnits="{units}"' if units else ""
        self.defs.append(f'<linearGradient id="{g}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"{u}>{s}</linearGradient>')
        return f"url(#{g})"

    def radial(self, stops, cx=0.5, cy=0.5, r=0.5):
        g = self.grad_id()
        s = "".join(f'<stop offset="{o}" stop-color="{c}" stop-opacity="{a}"/>' for o, c, a in stops)
        self.defs.append(f'<radialGradient id="{g}" cx="{cx}" cy="{cy}" r="{r}">{s}</radialGradient>')
        return f"url(#{g})"

    def add(self, s):
        self.body.append(s)

    def save(self, name):
        if name not in USED:                                   # replaced by the 3D renders (meadow3d.py)
            return
        x, y, w, h = self.box
        open(os.path.join(OUT, name), "w", encoding="utf-8").write(
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="{x} {y} {w} {h}"><defs>{"".join(self.defs)}</defs>{"".join(self.body)}</svg>')
        print("wrote", name)


def flower(s, x, y, r, col, centre="#ffe39a", petals=5, a=0.9):
    rot = rnd.uniform(0, math.pi)
    for i in range(petals):
        t = rot + 2 * math.pi * i / petals
        s.add(f'<ellipse cx="{x + math.cos(t) * r * 0.9:.1f}" cy="{y + math.sin(t) * r * 0.55:.1f}" rx="{r * 0.62:.1f}" ry="{r * 0.42:.1f}" '
              f'transform="rotate({math.degrees(t):.0f} {x + math.cos(t) * r * 0.9:.1f} {y + math.sin(t) * r * 0.55:.1f})" fill="{col}" fill-opacity="{a}"/>')
    s.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r * 0.42:.1f}" fill="{centre}"/>')


def tuft(s, x, y, h, col="#9fd39a", a=0.7):
    for k in range(rnd.randint(3, 5)):
        dx = rnd.uniform(-h * 0.5, h * 0.5)
        hh = h * rnd.uniform(0.6, 1.1)
        s.add(f'<path d="M{x + dx * 0.3:.1f} {y:.1f} Q{x + dx * 0.6:.1f} {y - hh * 0.55:.1f} {x + dx:.1f} {y - hh:.1f}" stroke="{col}" stroke-opacity="{a}" '
              f'stroke-width="{rnd.uniform(2.2, 3.4):.1f}" stroke-linecap="round" fill="none"/>')


# ------------------------------------------------------------------ backdrop
b = Svg(-512, -128, 2048, 1024)
b.add(f'<rect x="-512" y="-128" width="3584" height="1024" fill="{b.linear([(0, "#d6ebf7", 1), (0.42, "#f3f0f4", 1), (0.6, "#fff4ea", 1)])}"/>')
# a warm glow low on the horizon where the sun rises
b.add(f'<ellipse cx="760" cy="420" rx="760" ry="300" fill="{b.radial([(0, "#ffe2c4", 0.75), (1, "#ffe2c4", 0)])}"/>')
for cx, cy, rx, ry in ((-250, 70, 220, 55), (140, 30, 170, 42), (520, 95, 240, 50), (930, 40, 200, 46), (1330, 85, 230, 52), (330, -60, 160, 36)):
    b.wash("#ffffff", cx, cy, rx, ry, 0.85, 0.35, 0.22, 0.2, 12)
    b.wash("#e9e2f6", cx + rx * 0.15, cy + ry * 0.45, rx * 0.7, ry * 0.45, 0.35, 0.05, 0.2, 0.0)
# far hills: lilac and blue, then the near green hills
for cx, rx, col in ((-350, 420, "#d8cff1"), (180, 470, "#cfe2f2"), (760, 520, "#ddd3f3"), (1350, 460, "#cde4ef")):
    b.wash(col, cx, 448, rx, 92, 0.7, 0.3, 0.06, 0.25, 14)
for cx, rx, col in ((-420, 380, "#c9e6c0"), (60, 430, "#d4ecc6"), (560, 470, "#c6e5c0"), (1050, 440, "#d2ebc4"), (1480, 360, "#c9e6c0")):
    b.wash(col, cx, 478, rx, 70, 0.85, 0.45, 0.05, 0.3, 14)
# the meadow floor
b.add(f'<rect x="-512" y="470" width="3584" height="426" fill="{b.linear([(0, "#dcefcc", 1), (0.45, "#e6f4d6", 1), (1, "#d3eac2", 1)])}"/>')
for cx, cy, rx, ry, col in ((-200, 560, 380, 70, "#c8e6b6"), (300, 650, 330, 80, "#d7efc2"), (760, 590, 360, 60, "#cbe8b8"), (1250, 640, 380, 90, "#d5edc0"),
                            (100, 800, 420, 90, "#c5e3b3"), (900, 800, 460, 100, "#cfe9bb"), (512, 540, 260, 40, "#e9f6dc")):
    b.wash(col, cx, cy, rx, ry, 0.6, 0.15, 0.12, 0.18, 12)
# a sandy path running off to the right, toward the pond
b.add('<path d="M640 600 C820 610 980 560 1180 548 C1320 540 1440 528 1560 520 L1560 566 C1430 574 1320 590 1190 600 C990 616 830 650 660 640 Z" '
      f'fill="{b.linear([(0, "#f7e8d0", 0.0), (0.25, "#f7e8d0", 0.85), (1, "#f3e0c4", 0.9)], 0, 0, 1, 0)}"/>')
for x in range(700, 1540, 46):
    y = 600 - (x - 640) * 0.085 + rnd.uniform(-6, 6)
    b.add(f'<ellipse cx="{x + rnd.uniform(-8, 8):.1f}" cy="{y + 12:.1f}" rx="{rnd.uniform(4, 9):.1f}" ry="{rnd.uniform(2.5, 4.5):.1f}" fill="#e5cfae" fill-opacity="0.6"/>')
# grass tufts and flowers, kept away from the nest in the middle
cols = ["#ffb3cf", "#ffc9a0", "#cdb8f4", "#ffffff", "#ffe39a", "#b9e3f0"]
for i in range(260):
    x, y = rnd.uniform(-500, 1530), rnd.uniform(486, 890)
    if abs(x - 512) < 170 and abs(y - 560) < 80:
        continue
    if rnd.random() < 0.55:
        tuft(b, x, y, rnd.uniform(9, 18) * (0.7 + (y - 470) / 600), rnd.choice(["#9fd39a", "#b2dca4", "#8ccc92"]), rnd.uniform(0.45, 0.8))
    else:
        flower(b, x, y, rnd.uniform(4, 8) * (0.7 + (y - 470) / 500), rnd.choice(cols), a=rnd.uniform(0.7, 0.95))
# floating speckles, as in the round-11 backdrop
for i in range(70):
    x, y = rnd.uniform(-500, 1530), rnd.uniform(-110, 440)
    b.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rnd.choice([1.5, 2.2, 3, 4])}" fill="{rnd.choice(cols[:3] + cols[4:])}" fill-opacity="{rnd.uniform(0.35, 0.7):.2f}"/>')
# ------------------------------------------------------------------ the pond's half of the backdrop
# World x 1024..2048 is the pond's guaranteed-visible area. Its backdrop is drawn into the same picture as the meadow's
# (so hills and washes run on across the join) with its own random numbers, then saved as two halves: meadow.svg
# (x -512..1536) and meadow_east.svg (x 1536..3072).
_meadow_rnd = rnd
rnd = random.Random(23)
for cx, cy, rx, ry in ((1720, 60, 220, 50), (2120, 30, 180, 44), (2520, 90, 240, 52), (2920, 45, 210, 46), (2300, -60, 160, 36)):
    b.wash("#ffffff", cx, cy, rx, ry, 0.85, 0.35, 0.22, 0.2, 12)
    b.wash("#e9e2f6", cx + rx * 0.15, cy + ry * 0.45, rx * 0.7, ry * 0.45, 0.35, 0.05, 0.2, 0.0)
hills_from = len(b.body)
for cx, rx, col in ((1900, 420, "#d8cff1"), (2400, 500, "#cfe2f2"), (2950, 460, "#ddd3f3")):
    b.wash(col, cx, 448, rx, 92, 0.7, 0.3, 0.06, 0.25, 14)
for cx, rx, col in ((1880, 380, "#d4ecc6"), (2350, 460, "#c6e5c0"), (2850, 440, "#d2ebc4")):
    b.wash(col, cx, 478, rx, 70, 0.85, 0.45, 0.05, 0.3, 14)
hills = b.body[hills_from:]                              # behind the grass, as the meadow's own hills are
del b.body[hills_from:]
floor_at = next(k for k, el in enumerate(b.body) if 'x="-512" y="470"' in el)
b.body[floor_at:floor_at] = hills
for cx, cy, rx, ry, col in ((1700, 690, 380, 80, "#d7efc2"), (2150, 600, 360, 60, "#cbe8b8"), (2600, 660, 380, 90, "#d5edc0"),
                            (1800, 810, 420, 90, "#c5e3b3"), (2500, 820, 460, 100, "#cfe9bb")):
    b.wash(col, cx, cy, rx, ry, 0.6, 0.15, 0.12, 0.18, 12)
for i in range(200):
    x, y = rnd.uniform(1540, 3060), rnd.uniform(486, 890)
    if abs(x - 1620) < 300 and 520 < y < 690:            # the pond itself is its own picture
        continue
    if rnd.random() < 0.55:
        tuft(b, x, y, rnd.uniform(9, 18) * (0.7 + (y - 470) / 600), rnd.choice(["#9fd39a", "#b2dca4", "#8ccc92"]), rnd.uniform(0.45, 0.8))
    else:
        flower(b, x, y, rnd.uniform(4, 8) * (0.7 + (y - 470) / 500), rnd.choice(cols), a=rnd.uniform(0.7, 0.95))
for i in range(50):
    x, y = rnd.uniform(1540, 3060), rnd.uniform(-110, 440)
    b.add(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rnd.choice([1.5, 2.2, 3, 4])}" fill="{rnd.choice(cols[:3] + cols[4:])}" fill-opacity="{rnd.uniform(0.35, 0.7):.2f}"/>')
rnd = _meadow_rnd
b.save("meadow.svg")
b.box = (1536, -128, 1536, 1024)
b.save("meadow_east.svg")

# ------------------------------------------------------------------ apple tree (origin: foot of the trunk at 200, 470)
t = Svg(0, 0, 400, 480)
t.add(f'<ellipse cx="200" cy="468" rx="120" ry="14" fill="{t.radial([(0, "#7a6a98", 0.25), (1, "#7a6a98", 0)])}"/>')
t.add(f'<path d="M176 470 C182 400 180 330 168 270 L196 262 C204 320 214 380 230 470 Z" fill="{t.linear([(0, "#b98d74", 1), (1, "#d8ae90", 1)], 0, 0, 1, 0)}"/>')
t.add('<path d="M184 330 C160 300 132 286 104 282 L108 270 C140 272 168 290 192 316 Z" fill="#c69a7f"/>')
t.add('<path d="M196 300 C222 268 252 252 286 246 L288 258 C258 266 230 282 206 312 Z" fill="#c69a7f"/>')
t.add(f'<path d="{blob(200, 175, 168, 128, 0.08, 14)}" fill="#a6d79c"/>')   # an opaque base so the sky never shows through
for cx, cy, rx, ry, col in ((200, 170, 170, 130, "#a8dba0"), (110, 220, 110, 84, "#b7e2a6"), (295, 215, 104, 86, "#9fd59c"),
                            (200, 110, 120, 86, "#c2e8b0"), (150, 160, 80, 60, "#d3efc0"), (255, 150, 70, 56, "#b0dfa4")):
    t.wash(col, cx, cy, rx, ry, 0.95, 0.65, 0.12, 0.45, 12)
for i in range(18):                                   # blossom dots
    a, r = rnd.uniform(0, 2 * math.pi), rnd.uniform(20, 150)
    flower(t, 200 + math.cos(a) * r, 175 + math.sin(a) * r * 0.65, rnd.uniform(4, 6.5), rnd.choice(["#ffd0e0", "#ffffff", "#ffc2d6"]))
t.save("tree.svg")

# ------------------------------------------------------------------ apple (64x64, centre 32,36)
a = Svg(0, 0, 64, 64)
a.add(f'<path d="M32 18 C20 10 6 16 6 34 C6 50 18 60 32 58 C46 60 58 50 58 34 C58 16 44 10 32 18 Z" fill="{a.radial([(0, "#ff9aa6", 1), (0.7, "#ff6f82", 1), (1, "#e9576e", 1)], 0.38, 0.4, 0.62)}"/>')
a.add('<ellipse cx="21" cy="28" rx="6" ry="9" fill="#ffffff" fill-opacity="0.55" transform="rotate(-20 21 28)"/>')
a.add('<path d="M32 19 C32 13 33 9 36 5" stroke="#9c6f58" stroke-width="3.2" stroke-linecap="round" fill="none"/>')
a.add('<path d="M35 10 C42 2 52 4 54 8 C48 14 40 14 35 10 Z" fill="#8fd18c"/>')
a.save("apple.svg")

# ------------------------------------------------------------------ nest: a back half behind the egg, a front rim in front
for part in ("back", "front"):
    n = Svg(0, 0, 240, 110)
    if part == "back":
        n.add(f'<ellipse cx="120" cy="50" rx="106" ry="30" fill="{n.radial([(0, "#8f6a50", 1), (0.7, "#a9805f", 1), (1, "#d9ad80", 1)])}"/>')
    else:
        # a deep woven rim: the egg sits inside the bowl, not on a mat
        n.add(f'<path d="M8 48 C8 30 232 30 232 48 C236 92 196 108 120 108 C44 108 4 92 8 48 C30 70 210 70 232 48 Z" fill="{n.linear([(0, "#ecc99a", 1), (0.6, "#d6a97c", 1), (1, "#b98a62", 1)])}"/>')
        for i in range(34):                            # woven straws
            x0 = rnd.uniform(16, 224)
            y0 = 66 + 30 * math.sin(math.pi * (x0 - 16) / 208) + rnd.uniform(-8, 8)
            n.add(f'<path d="M{x0:.1f} {y0:.1f} q{rnd.uniform(-26, 26):.1f} {rnd.uniform(-8, 8):.1f} {rnd.uniform(-40, 40):.1f} {rnd.uniform(-4, 4):.1f}" '
                  f'stroke="{rnd.choice(["#f0d3a6", "#b88a62", "#e6c191"])}" stroke-width="{rnd.uniform(2, 3.4):.1f}" stroke-linecap="round" fill="none" stroke-opacity="0.9"/>')
    n.save(f"nest_{part}.svg")

# ------------------------------------------------------------------ egg (120x150, centre bottom 60,146)
e = Svg(0, 0, 120, 150)
e.add(f'<path d="M60 4 C26 4 6 58 6 92 C6 126 30 146 60 146 C90 146 114 126 114 92 C114 58 94 4 60 4 Z" fill="{e.radial([(0, "#fffdf8", 1), (0.7, "#fff1e6", 1), (1, "#f4dccf", 1)], 0.4, 0.38, 0.7)}"/>')
for cx, cy, r, col in ((40, 60, 9, "#ffc2d6"), (78, 46, 7, "#cdb8f4"), (84, 92, 11, "#ffd7a8"), (36, 108, 8, "#b9e3f0"), (62, 124, 6, "#ffc2d6"), (58, 82, 5, "#ffe39a")):
    e.add(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{col}" fill-opacity="0.85"/>')
e.add('<ellipse cx="40" cy="40" rx="9" ry="16" fill="#ffffff" fill-opacity="0.7" transform="rotate(-18 40 40)"/>')
e.save("egg.svg")

# ------------------------------------------------------------------ small things
h = Svg(0, 0, 48, 44)
h.add(f'<path d="M24 42 C10 32 2 24 2 14 C2 6 8 2 14 2 C19 2 22 5 24 9 C26 5 29 2 34 2 C40 2 46 6 46 14 C46 24 38 32 24 42 Z" fill="{h.radial([(0, "#ffb3cf", 1), (1, "#ff7aa8", 1)], 0.4, 0.35, 0.7)}"/>')
h.add('<ellipse cx="14" cy="12" rx="4" ry="6" fill="#ffffff" fill-opacity="0.6" transform="rotate(-30 14 12)"/>')
h.save("heart.svg")
s = Svg(0, 0, 40, 40)
s.add('<path d="M20 0 Q22 18 40 20 Q22 22 20 40 Q18 22 0 20 Q18 18 20 0 Z" fill="#fff6c2"/>')
s.save("sparkle.svg")
p = Svg(0, 0, 48, 48)
for cx, cy, rx, ry in ((14, 18, 5.5, 7), (24, 12, 5.5, 7), (34, 18, 5.5, 7)):
    p.add(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="#d9577f"/>')
p.add('<path d="M24 24 C14 24 10 34 12 38 C14 43 20 40 24 40 C28 40 34 43 36 38 C38 34 34 24 24 24 Z" fill="#d9577f"/>')
p.save("paw.svg")


# the water: an oval pool with a soft muddy shore, lily pads and reeds (600x200; the game places its centre, 300,92, at
# world 1620,608)
w = Svg(0, 0, 600, 200)
w.add(f'<ellipse cx="300" cy="96" rx="292" ry="86" fill="{w.radial([(0, "#c9b89c", 0.0), (0.82, "#d9c6a4", 0.55), (1, "#cdb890", 0.0)])}"/>')
w.add(f'<ellipse cx="300" cy="92" rx="272" ry="72" fill="{w.linear([(0, "#9fd0e8", 1), (0.5, "#b9def0", 1), (1, "#d3ecf6", 1)])}"/>')
w.add(f'<ellipse cx="300" cy="80" rx="250" ry="54" fill="{w.radial([(0, "#e6f6fb", 0.8), (1, "#e6f6fb", 0)], 0.45, 0.35, 0.6)}"/>')
w.add('<path d="M40 92 C80 30 520 30 560 92" stroke="#7fb6d4" stroke-opacity="0.45" stroke-width="3" fill="none"/>')
for cx, cy, r in ((150, 104, 22), (196, 120, 15), (430, 88, 26), (470, 112, 16), (330, 128, 14)):
    a0 = rnd.uniform(0, 6.28)
    x1, y1 = cx + math.cos(a0) * r, cy + math.sin(a0) * r * 0.45
    x2, y2 = cx + math.cos(a0 + 0.5) * r, cy + math.sin(a0 + 0.5) * r * 0.45
    w.add(f'<path d="M{cx} {cy} L{x1:.1f} {y1:.1f} A{r} {r * 0.45:.1f} 0 1 1 {x2:.1f} {y2:.1f} Z" fill="#9fd39a" fill-opacity="0.95"/>')
    w.add(f'<ellipse cx="{cx - r * 0.2:.1f}" cy="{cy - r * 0.1:.1f}" rx="{r * 0.45:.1f}" ry="{r * 0.16:.1f}" fill="#c7ebb8" fill-opacity="0.7"/>')
for cx, cy in ((436, 82), (150, 98)):
    flower(w, cx, cy, 9, "#ffc2d6", "#fff1b0", 6)
for x0, side in ((30, -1), (60, -1), (548, 1), (575, 1)):
    for k in range(4):
        x = x0 + rnd.uniform(-10, 10)
        hgt = rnd.uniform(60, 110)
        w.add(f'<path d="M{x:.1f} 120 Q{x + side * 8:.1f} {120 - hgt * 0.5:.1f} {x + side * rnd.uniform(4, 16):.1f} {120 - hgt:.1f}" stroke="#8ccc92" stroke-width="4" stroke-linecap="round" fill="none"/>')
        if k % 2 == 0:
            w.add(f'<ellipse cx="{x + side * 12:.1f}" cy="{120 - hgt * 0.8:.1f}" rx="5" ry="13" fill="#b98d74"/>')
for cx, cy in ((80, 150), (540, 146), (300, 176), (210, 168), (400, 170)):
    w.add(f'<ellipse cx="{cx}" cy="{cy}" rx="{rnd.uniform(10, 16):.1f}" ry="{rnd.uniform(6, 9):.1f}" fill="#d8d2e6"/>')
    w.add(f'<ellipse cx="{cx - 3}" cy="{cy - 3}" rx="5" ry="3" fill="#ffffff" fill-opacity="0.6"/>')
w.save("pond.svg")

# a wooden signpost with an arrow board (120x150, foot at 40,146); the arrow points right; the game mirrors it
g = Svg(0, 0, 120, 150)
g.add(f'<ellipse cx="40" cy="146" rx="26" ry="5" fill="{g.radial([(0, "#7a6a98", 0.25), (1, "#7a6a98", 0)])}"/>')
g.add(f'<rect x="34" y="40" width="12" height="106" rx="5" fill="{g.linear([(0, "#c69a7f", 1), (1, "#b98d74", 1)], 0, 0, 1, 0)}"/>')
g.add(f'<path d="M8 22 L92 22 L114 46 L92 70 L8 70 Q2 46 8 22 Z" fill="{g.linear([(0, "#f0d3a6", 1), (1, "#e2b886", 1)])}" stroke="#b98a62" stroke-width="3"/>')
for y in (34, 46, 58):
    g.add(f'<path d="M14 {y} L{86 + (6 if y == 46 else 0)} {y}" stroke="#d3a776" stroke-width="1.5" stroke-opacity="0.7"/>')
g.save("sign.svg")

# small pictures on the signs: a drop of water (to the pond) and the apple tree (to the meadow), 48x48
dw = Svg(0, 0, 48, 48)
dw.add(f'<path d="M24 4 C30 16 40 24 40 32 C40 41 33 46 24 46 C15 46 8 41 8 32 C8 24 18 16 24 4 Z" fill="{dw.radial([(0, "#d3ecf6", 1), (1, "#7fb6d4", 1)], 0.4, 0.45, 0.7)}"/>')
dw.add('<ellipse cx="18" cy="30" rx="3.5" ry="6" fill="#ffffff" fill-opacity="0.7"/>')
dw.save("icon_water.svg")
it = Svg(0, 0, 48, 48)
it.add('<rect x="21" y="26" width="6" height="18" rx="2" fill="#b98d74"/>')
it.add(f'<circle cx="24" cy="20" r="16" fill="{it.radial([(0, "#c2e8b0", 1), (1, "#8fcf8a", 1)], 0.4, 0.35, 0.7)}"/>')
for cx, cy in ((16, 18), (30, 14), (28, 26)):
    it.add(f'<circle cx="{cx}" cy="{cy}" r="4" fill="#ff7a8c"/>')
it.save("icon_tree.svg")

# things to place: a flowering plant in a pot (100x120, foot 50,116), a lantern (80x140, foot 40,136), a ball (64x64)
pl = Svg(0, 0, 100, 120)
pl.add(f'<ellipse cx="50" cy="114" rx="30" ry="6" fill="{pl.radial([(0, "#7a6a98", 0.25), (1, "#7a6a98", 0)])}"/>')
pl.add(f'<path d="M26 74 L74 74 L68 112 Q50 118 32 112 Z" fill="{pl.linear([(0, "#f2b8a0", 1), (1, "#d98f7a", 1)], 0, 0, 1, 0)}"/>')
pl.add('<rect x="22" y="68" width="56" height="10" rx="4" fill="#f6c8b2"/>')
for a, ln in ((-0.5, 34), (-0.15, 46), (0.25, 40), (0.6, 30)):
    x2, y2 = 50 + math.sin(a) * ln, 70 - math.cos(a) * ln
    mx, my = 50 + math.sin(a) * ln * 0.55, 70 - math.cos(a) * ln * 0.55
    pl.add(f'<path d="M50 70 Q{50 + math.sin(a) * ln * 0.3:.1f} {70 - math.cos(a) * ln * 0.6:.1f} {x2:.1f} {y2:.1f}" stroke="#8ccc92" stroke-width="3.4" stroke-linecap="round" fill="none"/>')
    pl.add(f'<ellipse cx="{mx:.1f}" cy="{my:.1f}" rx="9" ry="4.5" transform="rotate({math.degrees(a) - 40:.0f} {mx:.1f} {my:.1f})" fill="#a6d79c"/>')
    flower(pl, x2, y2, 9, rnd.choice(["#ffb3cf", "#cdb8f4", "#ffc9a0"]), "#ffe39a", 5)
pl.save("plant.svg")
la = Svg(0, 0, 80, 140)
la.add(f'<ellipse cx="40" cy="134" rx="22" ry="5" fill="{la.radial([(0, "#7a6a98", 0.25), (1, "#7a6a98", 0)])}"/>')
la.add('<rect x="37" y="70" width="6" height="66" rx="3" fill="#a88a70"/>')
la.add('<path d="M24 34 L56 34 L60 74 L20 74 Z" fill="#fff3d6" stroke="#c99a6a" stroke-width="3"/>')
la.add(f'<path d="M28 40 L52 40 L54 68 L26 68 Z" fill="{la.radial([(0, "#fffbe8", 1), (1, "#ffd98a", 1)], 0.5, 0.55, 0.6)}"/>')
la.add('<path d="M20 34 Q40 14 60 34 Z" fill="#e8a6b8" stroke="#c98a9e" stroke-width="2"/>')
la.add('<circle cx="40" cy="18" r="5" fill="none" stroke="#c99a6a" stroke-width="3"/>')
la.add('<rect x="18" y="72" width="44" height="6" rx="3" fill="#e8a6b8"/>')
la.save("lantern.svg")
ba = Svg(0, 0, 64, 64)
ba.add(f'<circle cx="32" cy="32" r="28" fill="{ba.radial([(0, "#fff4e0", 1), (1, "#f2dcc0", 1)], 0.38, 0.35, 0.7)}"/>')
ba.add('<path d="M6 26 Q32 40 58 26 L59 34 Q32 48 5 34 Z" fill="#9fc9f0"/>')
ba.add('<path d="M14 10 Q22 32 14 54 L20 57 Q29 32 21 7 Z" fill="#ffb3cf"/>')
ba.add('<path d="M50 10 Q42 32 50 54 L44 57 Q35 32 43 7 Z" fill="#ffe39a"/>')
ba.add('<ellipse cx="22" cy="18" rx="6" ry="4" fill="#ffffff" fill-opacity="0.7" transform="rotate(-30 22 18)"/>')
ba.save("ball.svg")
