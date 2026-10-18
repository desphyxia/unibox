"""Watercolour-style backdrop for the round-11 unicorn: cream paper, crisp-edged colour washes with a pooled rim, drips and speckles.
Flat SVG, gradients only (no filters). Usage: python backdrop_bloom.py OUT.svg"""
import sys, math, random

rnd = random.Random(7)
W, H, Y0 = 800, 730, -30


def blob(cx, cy, rx, ry, jitter=0.18, n=9):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n + rnd.uniform(-0.15, 0.15)
        k = 1 + rnd.uniform(-jitter, jitter)
        pts.append((cx + math.cos(a) * rx * k, cy + math.sin(a) * ry * k))
    d = f"M{(pts[0][0] + pts[-1][0]) / 2:.1f} {(pts[0][1] + pts[-1][1]) / 2:.1f}"
    for i in range(n):
        p, q = pts[i], pts[(i + 1) % n]
        d += f" Q{p[0]:.1f} {p[1]:.1f} {(p[0] + q[0]) / 2:.1f} {(p[1] + q[1]) / 2:.1f}"
    return d + " Z"


parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 {Y0} {W} {H}">', "<defs>",
         '<radialGradient id="lift" cx="0.5" cy="0.45" r="0.6"><stop offset="0" stop-color="#ffffff" stop-opacity="0.55"/><stop offset="1" stop-color="#ffffff" stop-opacity="0"/></radialGradient>',
         '<linearGradient id="drip" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#ff9fc4" stop-opacity="0.75"/><stop offset="1" stop-color="#ff9fc4" stop-opacity="0.2"/></linearGradient>',
         '<radialGradient id="grass" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#cfe9d8" stop-opacity="0.95"/><stop offset="1" stop-color="#cfe9d8" stop-opacity="0"/></radialGradient>',
         "</defs>", f'<rect x="0" y="{Y0}" width="{W}" height="{H}" fill="#fffaf6"/>']
washes = [("#ffc9a0", 150, 150, 190, 140), ("#cdb8f4", 670, 130, 170, 140), ("#ffb3cf", 700, 440, 150, 190), ("#b4e6ee", 90, 460, 160, 160),
          ("#ffeaa0", 400, 30, 210, 90), ("#ffd2b0", 580, 300, 120, 100), ("#b4e6ee", 330, 640, 230, 70), ("#ffb3cf", 110, 650, 140, 60), ("#e3d4fb", 270, 330, 110, 90)]
for i, (col, cx, cy, rx, ry) in enumerate(washes):
    parts[1:1] = []
    gid = f"wg{i}"
    parts.insert(2, f'<radialGradient id="{gid}" cx="0.5" cy="0.5" r="0.55"><stop offset="0" stop-color="{col}" stop-opacity="0.6"/><stop offset="0.6" stop-color="{col}" stop-opacity="0.38"/><stop offset="1" stop-color="{col}" stop-opacity="0.12"/></radialGradient>')
    d = blob(cx, cy, rx, ry, 0.14)
    parts.append(f'<path d="{d}" fill="url(#{gid})" stroke="{col}" stroke-opacity="0.32" stroke-width="1.6"/>')
parts.append('<ellipse cx="400" cy="602" rx="330" ry="52" fill="url(#grass)"/>')
for x, y, h, w in ((86, 560, 90, 7), (112, 576, 52, 5), (664, 520, 100, 8), (700, 540, 60, 5), (230, 40, 58, 6)):
    parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{w / 2}" fill="url(#drip)"/><circle cx="{x + w / 2}" cy="{y + h}" r="{w * 0.75:.1f}" fill="#ff9fc4" fill-opacity="0.6"/>')
cols = ["#ffb3cf", "#ffc9a0", "#cdb8f4", "#b4e6ee", "#ffe39a"]
for i in range(90):
    x, y = rnd.uniform(10, 790), rnd.uniform(-20, 660)
    r = rnd.choice([1.2, 1.8, 2.5, 3.5, 5, 7])
    parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r}" fill="{rnd.choice(cols)}" fill-opacity="{rnd.uniform(0.4, 0.85):.2f}"/>')
for x, y, s in ((120, 80, 9), (690, 60, 8), (60, 330, 7), (740, 290, 9), (330, 20, 6)):
    parts.append(f'<path d="M{x} {y - s} Q{x + s * 0.2} {y - s * 0.2} {x + s} {y} Q{x + s * 0.2} {y + s * 0.2} {x} {y + s} Q{x - s * 0.2} {y + s * 0.2} {x - s} {y} Q{x - s * 0.2} {y - s * 0.2} {x} {y - s} Z" fill="#fff3a8" fill-opacity="0.95"/>')
parts.append("</svg>")
open(sys.argv[1] if len(sys.argv) > 1 else "backdrop_bloom.svg", "w", encoding="utf-8").write("".join(parts))
