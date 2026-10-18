"""Meadow backdrop for the 3D unicorn renders: the scene the 2D unicorn (artgen5.py) is drawn on, without the creature.
The contact shadow comes from the 3D render itself (a shadow catcher), so none is painted here.
Usage: python backdrop_unicorn.py OUT.svg"""
import sys, math
import artgen5 as A

P = A.pastel
W, H = 800, 700
stops = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in P["bg"])
o = [f'<defs><linearGradient id="bgu" x1="0" y1="-30" x2="0" y2="700" gradientUnits="userSpaceOnUse">{stops}</linearGradient></defs>',
     f'<rect x="0" y="-30" width="{W}" height="{H + 30}" fill="url(#bgu)"/>',
     f'<path d="M0 560 C120 500 260 520 380 556 C500 590 640 520 800 540 L800 700 L0 700 Z" fill="{P["hill1"]}" opacity="0.75"/>',
     f'<path d="M0 596 C140 566 300 586 420 590 C560 594 680 570 800 584 L800 700 L0 700 Z" fill="{P["hill2"]}"/>']
for fx, fy, fr, fc in ((90, 640, 9, P["flower1"]), (160, 660, 7, P["flower2"]), (640, 636, 9, P["flower2"]), (720, 662, 8, P["flower1"]),
                       (560, 668, 6, P["flower1"]), (40, 676, 6, P["flower2"]), (330, 672, 7, P["flower2"]), (470, 650, 6, P["flower1"])):
    petals = "".join(f'<circle cx="{fx + fr * 0.8 * math.cos(a * math.pi / 2.5):.1f}" cy="{fy + fr * 0.8 * math.sin(a * math.pi / 2.5):.1f}" r="{fr * 0.55:.1f}" fill="{fc}"/>' for a in range(5))
    o.append(f'<g>{petals}<circle cx="{fx}" cy="{fy}" r="{fr * 0.45:.1f}" fill="{P["flower_c"]}"/></g>')
for x, y, r, op in ((170, 150, 10, 0.7), (110, 230, 6, 0.6), (700, 120, 9, 0.8), (640, 60, 7, 0.7), (60, 90, 8, 0.7)):
    o.append(A.star(x, y, r, P["spark"], op))
open(sys.argv[1], "w", encoding="utf-8").write(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -30 {W} {H + 30}">' + "".join(o) + "</svg>")
