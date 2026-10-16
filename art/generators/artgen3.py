"""Unicorn study 3: unified silhouette, ribbon-built limbs and hair, profile head with one big eye.
Usage: python artgen3.py OUTDIR
Writes pastel-uni.svg and paint-uni.svg (viewBox 0 0 800 700)."""
import sys, os, math, random

OUT = sys.argv[1]
W, H = 800, 700


# ---------------------------------------------------------------- geometry helpers
def cr(pts):
    """Catmull-Rom through pts -> cubic bezier segments (string, starts after an M at pts[0])."""
    out = []
    n = len(pts)
    for i in range(n - 1):
        p0 = pts[i - 1] if i > 0 else pts[i]
        p1, p2 = pts[i], pts[i + 1]
        p3 = pts[i + 2] if i + 2 < n else pts[i + 1]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        out.append(f"C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}")
    return "".join(out)


def bez(p0, p1, p2, p3, n=14):
    pts = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
        pts.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return pts


def normals(pts):
    ns = []
    for i in range(len(pts)):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        L = math.hypot(dx, dy) or 1
        ns.append((-dy / L, dx / L))
    return ns


def ribbon(pts, widths):
    ns = normals(pts)
    left = [(p[0] + n[0] * w / 2, p[1] + n[1] * w / 2) for p, n, w in zip(pts, ns, widths)]
    right = [(p[0] - n[0] * w / 2, p[1] - n[1] * w / 2) for p, n, w in zip(pts, ns, widths)]
    d = f"M{left[0][0]:.1f} {left[0][1]:.1f}" + cr(left)
    d += f"L{right[-1][0]:.1f} {right[-1][1]:.1f}" + cr(right[::-1]) + "Z"
    return d


def lock_widths(n, w0, bulge=0.25, tip=True):
    ws = []
    for i in range(n + 1):
        t = i / n
        w = w0 * (0.55 + 0.45 * math.sin(min(1, t * 3) * math.pi / 2)) * (1 - t ** 1.7) if tip else w0
        ws.append(max(w * (1 + bulge * math.sin(t * math.pi)), 0.01))
    return ws


def limb(points):
    """points: [(x, y, w)] -> ribbon path through the joints."""
    pts = [(p[0], p[1]) for p in points]
    ws = [p[2] for p in points]
    return ribbon(pts, ws)


def star(x, y, r, fill, op=1.0):
    k = 0.16
    return (f'<path d="M{x} {y-r} Q{x+r*k} {y-r*k} {x+r} {y} Q{x+r*k} {y+r*k} {x} {y+r} '
            f'Q{x-r*k} {y+r*k} {x-r} {y} Q{x-r*k} {y-r*k} {x} {y-r} Z" fill="{fill}" opacity="{op}"/>')


# ---------------------------------------------------------------- the creature
SIL = ("M235 330 C262 308 322 322 380 336 C420 344 456 338 482 322 "
       "C512 302 526 252 540 206 C548 184 556 166 574 152 "
       "C598 130 648 140 674 172 C696 196 716 222 724 246 "
       "C732 262 724 282 702 288 C686 292 672 292 660 288 "
       "C645 301 626 308 610 302 C596 298 586 296 578 304 "
       "C568 328 568 358 570 390 C572 424 552 452 522 472 "
       "C504 490 474 492 440 490 C390 484 330 492 276 486 "
       "C246 472 220 436 220 394 C220 364 222 344 235 330 Z")

# legs: (x, y, width) joints, top hidden under the body
HIND_NEAR = [(282, 396, 62), (288, 478, 46), (268, 540, 28), (272, 574, 21), (272, 587, 22)]
HIND_FAR = [(340, 396, 50), (346, 486, 38), (340, 540, 25), (344, 574, 20), (344, 586, 21)]
FRONT_FAR = [(506, 400, 46), (512, 496, 30), (510, 552, 22), (512, 574, 19), (512, 586, 20)]
FRONT_NEAR = [(484, 404, 52), (506, 496, 34), (500, 540, 24), (494, 560, 20), (494, 574, 21)]


def hoof_path(joints):
    (x1, y1, _), (x2, y2, w2) = joints[-2], joints[-1]
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1
    dx, dy = dx / L, dy / L
    pts = [(x2 - dx * 6, y2 - dy * 6), (x2 + dx * 6, y2 + dy * 6), (x2 + dx * 16, y2 + dy * 16)]
    return ribbon(pts, [w2 + 1, w2 + 7, w2 + 9])


def build(P, uid, view=None):
    u = uid
    rnd = random.Random(P.get("seed", 4))
    ol = P.get("ol")
    stroke = (f'stroke="{ol}" stroke-width="{P["ow"]}" stroke-linejoin="round" stroke-linecap="round"' if ol else "")
    defs = []

    def lg(id_, stops, x1=0, y1=0, x2=0, y2=1):
        s = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
        defs.append(f'<linearGradient id="{u}{id_}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{s}</linearGradient>')

    def rg(id_, stops, cx=0.5, cy=0.4, r=0.7, fx=None, fy=None):
        s = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
        f = f' fx="{fx}" fy="{fy}"' if fx is not None else ""
        defs.append(f'<radialGradient id="{u}{id_}" cx="{cx}" cy="{cy}" r="{r}"{f}>{s}</radialGradient>')

    lg("bg", P["bg"])
    lg("coat", P["coat"], 0.3, 0, 0.7, 1)
    lg("legcoat", P["legcoat"], 0, 0, 1, 0)
    lg("farleg", P["farleg"], 0, 0, 1, 0)
    lg("horn", P["horn_g"], 0, 0, 0, 1)
    lg("hoof", P["hoof_g"], 0, 0, 0, 1)
    for i, hair in enumerate(P["hair"]):
        lg(f"hair{i}", hair, 0, 0, 1, 1)
    rg("iris", P["iris_g"], 0.5, 0.35, 0.75)
    rg("ground", [(0, P["ground1"]), (1, P["ground2"])], 0.5, 0.5, 0.6)
    for r in (3, 6, 10, 18):
        defs.append(f'<filter id="{u}b{r}" filterUnits="userSpaceOnUse" x="-100" y="-100" width="1000" height="900"><feGaussianBlur stdDeviation="{r}"/></filter>')
    defs.append(f'<clipPath id="{u}csil"><path d="{SIL}"/></clipPath>')
    hornp = "M622 156 C638 112 660 70 686 26 C682 78 672 122 660 166 Z"
    defs.append(f'<clipPath id="{u}chorn"><path d="{hornp}"/></clipPath>')
    if P.get("paint"):
        defs.append(
            f'<filter id="{u}wc" x="-5%" y="-5%" width="110%" height="110%" color-interpolation-filters="sRGB">'
            f'<feTurbulence type="fractalNoise" baseFrequency="0.02" numOctaves="3" seed="7" result="n"/>'
            f'<feDisplacementMap in="SourceGraphic" in2="n" scale="6" xChannelSelector="R" yChannelSelector="G" result="d"/>'
            f'<feTurbulence type="fractalNoise" baseFrequency="0.6" numOctaves="3" seed="3" result="g"/>'
            f'<feColorMatrix in="g" type="matrix" values="0 0 0 0 0.45  0 0 0 0 0.36  0 0 0 0 0.28  0 0 0 0.45 -0.1" result="grain"/>'
            f'<feComposite in="grain" in2="d" operator="in" result="grainIn"/>'
            f'<feMerge><feMergeNode in="d"/><feMergeNode in="grainIn"/></feMerge></filter>')
        defs.append(
            f'<filter id="{u}paper" x="0" y="0" width="100%" height="100%">'
            f'<feTurbulence type="fractalNoise" baseFrequency="0.8" numOctaves="2" seed="11"/>'
            f'<feColorMatrix type="matrix" values="0 0 0 0 0.5  0 0 0 0 0.4  0 0 0 0 0.3  0 0 0 0.4 -0.08"/></filter>')
        defs.append(
            f'<filter id="{u}blotch" x="0" y="0" width="100%" height="100%">'
            f'<feTurbulence type="fractalNoise" baseFrequency="0.005" numOctaves="2" seed="21"/>'
            f'<feColorMatrix type="matrix" values="0 0 0 0 0.55  0 0 0 0 0.35  0 0 0 0 0.3  0 0 0 0.9 -0.35"/></filter>')
    wc = f'filter="url(#{u}wc)"' if P.get("paint") else ""
    vb = view or f"0 -30 {W} {H+30}"
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" role="img" aria-label="{P["label"]}">']
    s.append("<defs>" + "".join(defs) + "</defs>")
    s.append(f'<rect x="0" y="-30" width="{W}" height="{H+30}" fill="url(#{u}bg)"/>')
    if P.get("paint"):
        s.append(f'<rect x="0" y="-30" width="{W}" height="{H+30}" filter="url(#{u}blotch)" opacity="0.35" style="mix-blend-mode:multiply"/>')
    # soft background: far hills, ground band, shadow, flowers
    s.append(f'<path d="M0 560 C120 500 260 520 380 556 C500 590 640 520 800 540 L800 700 L0 700 Z" fill="{P["hill1"]}" opacity="0.75"/>')
    s.append(f'<path d="M0 596 C140 566 300 586 420 590 C560 594 680 570 800 584 L800 700 L0 700 Z" fill="{P["hill2"]}"/>')
    s.append(f'<ellipse cx="385" cy="606" rx="250" ry="16" fill="{P["shadow"]}" opacity="{P["shadow_o"]}" filter="url(#{u}b10)"/>')
    for fx, fy, fr, fc in ((90, 640, 9, P["flower1"]), (160, 660, 7, P["flower2"]), (640, 636, 9, P["flower2"]), (720, 662, 8, P["flower1"]),
                           (560, 668, 6, P["flower1"]), (40, 676, 6, P["flower2"]), (330, 672, 7, P["flower2"]), (470, 650, 6, P["flower1"])):
        petals = "".join(f'<circle cx="{fx + fr*0.8*math.cos(a*math.pi/2.5):.1f}" cy="{fy + fr*0.8*math.sin(a*math.pi/2.5):.1f}" r="{fr*0.55:.1f}" fill="{fc}"/>' for a in range(5))
        s.append(f'<g>{petals}<circle cx="{fx}" cy="{fy}" r="{fr*0.45:.1f}" fill="{P["flower_c"]}"/></g>')

    s.append(f'<g {wc}>')

    def hair_lock(p0, p1, p2, p3, w0, idx, n=16, op=1.0):
        pts = bez(p0, p1, p2, p3, n)
        return f'<path d="{ribbon(pts, lock_widths(n, w0))}" fill="url(#{u}hair{idx})" {stroke} opacity="{op}"/>'

    def strand(p0, p1, p2, p3, wd=2.4, op=0.6):
        pts = bez(p0, p1, p2, p3, 14)
        return f'<path d="M{pts[0][0]:.1f} {pts[0][1]:.1f}{cr(pts)}" fill="none" stroke="{P["strand"]}" stroke-width="{wd}" stroke-linecap="round" opacity="{op}"/>'

    UP = -34
    # ---- tail (behind everything)
    s.append(f'<g transform="translate(0 {UP})">')
    roots = [(232, 336), (226, 346), (224, 358)]
    specs = [
        ((-70, 8), (-100, 110), (-40, 230), 46, 0),
        ((-80, 20), (-130, 130), (-100, 250), 42, 1),
        ((-60, 14), (-60, 120), (10, 240), 38, 2),
        ((-90, 30), (-150, 100), (-150, 200), 34, 0),
        ((-50, 24), (-30, 130), (50, 210), 30, 1),
    ]
    for i, (a, b, c, w, idx) in enumerate(specs):
        r = roots[i % 3]
        s.append(hair_lock(r, (r[0] + a[0], r[1] + a[1]), (r[0] + b[0], r[1] + b[1]), (r[0] + c[0], r[1] + c[1]), w, idx))
    for a, b, c in ((-62, -90, -36), (-72, -118, -90), (-50, -50, 6)):
        s.append(strand((228, 344), (228 + a, 352), (228 + b, 344 + 110), (228 + c, 344 + 200)))
    # ---- far ear (behind head)
    s.append(f'<g transform="translate(22 -6) rotate(8 596 152)">'
             f'<path d="M586 160 C566 124 566 94 576 70 C600 92 614 124 616 154 Z" fill="url(#{u}farleg)" {stroke}/>'
             f'<path d="M588 150 C576 122 576 100 582 84 C598 100 606 122 608 146 Z" fill="{P["ear_in"]}" opacity="0.7"/></g>')
    s.append('</g>')

    # ---- far legs
    for joints in (HIND_FAR, FRONT_FAR):
        s.append(f'<path d="{limb(joints)}" fill="url(#{u}farleg)" {stroke}/>')
        s.append(f'<path d="{hoof_path(joints)}" fill="url(#{u}hoof)" {stroke} opacity="0.9"/>')
    # ---- near legs
    for joints in (HIND_NEAR, FRONT_NEAR):
        s.append(f'<path d="{limb(joints)}" fill="url(#{u}legcoat)" {stroke}/>')
        s.append(f'<path d="{hoof_path(joints)}" fill="url(#{u}hoof)" {stroke}/>')
        x, y, w = joints[-2]
        s.append(f'<ellipse cx="{x}" cy="{y}" rx="{w*0.5}" ry="5" fill="{P["fetlock"]}" opacity="0.5" filter="url(#{u}b3)"/>')

    s.append(f'<g transform="translate(0 {UP})">')
    # ---- body + neck + head silhouette
    s.append(f'<path d="{SIL}" fill="url(#{u}coat)" {stroke}/>')
    s.append(f'<g clip-path="url(#{u}csil)">')
    sh = P["shade"]
    s.append(f'<ellipse cx="380" cy="504" rx="210" ry="60" fill="{sh}" opacity="0.75" filter="url(#{u}b18)"/>')
    s.append(f'<ellipse cx="562" cy="384" rx="26" ry="110" fill="{sh}" opacity="0.5" filter="url(#{u}b18)"/>')
    s.append(f'<ellipse cx="224" cy="420" rx="26" ry="70" fill="{sh}" opacity="0.5" filter="url(#{u}b18)"/>')
    s.append(f'<path d="M470 352 C492 400 488 444 472 474" fill="none" stroke="{sh}" stroke-width="16" opacity="0.4" filter="url(#{u}b10)"/>')
    s.append(f'<path d="M310 356 C276 390 276 440 296 478" fill="none" stroke="{sh}" stroke-width="16" opacity="0.4" filter="url(#{u}b10)"/>')
    s.append(f'<ellipse cx="320" cy="338" rx="120" ry="14" fill="{P["hi"]}" opacity="0.9" filter="url(#{u}b6)"/>')
    s.append(f'<ellipse cx="530" cy="262" rx="10" ry="56" fill="{P["hi"]}" opacity="0.7" filter="url(#{u}b6)" transform="rotate(14 530 262)"/>')
    s.append(f'<ellipse cx="622" cy="164" rx="46" ry="9" fill="{P["hi"]}" opacity="0.85" filter="url(#{u}b6)" transform="rotate(14 622 164)"/>')
    s.append(f'<ellipse cx="642" cy="272" rx="26" ry="18" fill="{P["blush"]}" opacity="{P["blush_o"]}" filter="url(#{u}b10)"/>')
    s.append(f'<ellipse cx="640" cy="304" rx="80" ry="12" fill="{sh}" opacity="0.7" filter="url(#{u}b6)"/>')
    s.append('</g>')
    # cutie mark on the haunch
    s.append(f'<g transform="translate(290 410) rotate(-12)">{star(0, 0, 20, P["mark"], 0.95)}{star(0, 0, 8, "#ffffff", 0.9)}</g>')
    # muzzle details
    s.append(f'<ellipse cx="711" cy="259" rx="6" ry="4.4" fill="{P["nostril"]}" opacity="0.9" transform="rotate(-20 711 259)"/>')
    s.append(f'<path d="M714 280 C704 291 686 291 672 283" fill="none" stroke="{P["nostril"]}" stroke-width="3" stroke-linecap="round"/>')
    s.append(f'<path d="M672 283 q-5 -3 -6 -8" fill="none" stroke="{P["nostril"]}" stroke-width="2.4" stroke-linecap="round"/>')

    # ---- near ear
    s.append(f'<path d="M584 162 C562 122 560 90 570 62 C598 88 614 122 618 156 Z" fill="url(#{u}legcoat)" {stroke}/>')
    s.append(f'<path d="M586 152 C572 122 570 98 576 78 C594 98 604 124 608 148 Z" fill="{P["ear_in"]}" opacity="0.85"/>')

    # ---- mane: a base along the crest, then locks swept back over the neck
    crest = bez((574, 150), (540, 196), (532, 282), (484, 322), 20)
    for k in range(15):
        c = crest[int(1 + k * 1.25)]
        wave = 1 if k % 2 == 0 else -1
        grow = 1 + k * 0.045
        p0 = (c[0] + 3, c[1] - 3)
        p1 = (c[0] - 26, c[1] - 8)
        p2 = (c[0] - (70 + rnd.uniform(0, 20)) * grow + wave * 18, c[1] + 40 + k * 2)
        p3 = (c[0] - (58 + rnd.uniform(0, 20)) * grow - wave * 26, c[1] + 108 + k * 6 + rnd.uniform(0, 22))
        s.append(hair_lock(p0, p1, p2, p3, 48 - k * 0.7, (k + 1) % 3))
        if k % 3 == 0:
            s.append(strand((c[0] - 2, c[1]), (c[0] - 26, c[1] - 4), (p2[0] + 8, p2[1] - 2), (p3[0] + 10, p3[1] - 10)))

    # crest cover: hides the lock roots so the mane edge reads as one smooth line
    s.append(f'<path d="{ribbon([(p[0] + 2, p[1] - 1) for p in crest], [24 * min(1.0, (20 - i) / 6 + 0.04, i / 2 + 0.5) for i in range(21)])}" fill="url(#{u}hair0)" {stroke}/>')
    s.append(strand((574, 150), (545, 190), (536, 270), (488, 318), 3, 0.5))

    # ---- eye (profile, one big eye, built once)
    cx, cy, rx, ry = 636, 224, 19, 26
    eye = []
    eye.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{P["eye_white"]}" stroke="{P["lid_shadow"]}" stroke-opacity="0.45" stroke-width="1.6"/>')
    eye.append(f'<ellipse cx="{cx+2}" cy="{cy+3}" rx="{rx*0.84}" ry="{ry*0.86}" fill="url(#{u}iris)"/>')
    eye.append(f'<ellipse cx="{cx+3}" cy="{cy+5}" rx="{rx*0.42}" ry="{ry*0.5}" fill="{P["pupil"]}"/>')
    eye.append(f'<ellipse cx="{cx+9}" cy="{cy-9}" rx="{rx*0.32}" ry="{ry*0.26}" fill="#fff"/>')
    eye.append(f'<circle cx="{cx-4}" cy="{cy+14}" r="{rx*0.16}" fill="#fff" opacity="0.9"/>')
    P0 = (cx - rx - 1, cy - 3); C0 = (cx - 2, cy - ry - 7); P2 = (cx + rx + 1, cy - 5)
    eye.append(f'<path d="M{P0[0]} {P0[1]} Q{C0[0]} {C0[1]} {P2[0]} {P2[1]} L{P2[0]} {cy-ry*0.4} L{P0[0]} {cy-ry*0.4} Z" fill="{P["lid_shadow"]}" opacity="0.16"/>')
    eye.append(f'<path d="M{P0[0]} {P0[1]} Q{C0[0]} {C0[1]} {P2[0]} {P2[1]}" fill="none" stroke="{P["lash"]}" stroke-width="4.4" stroke-linecap="round"/>')

    def lid(t):
        a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t * t
        x = a * P0[0] + b * C0[0] + c * P2[0]
        y = a * P0[1] + b * C0[1] + c * P2[1]
        dx = 2 * (1 - t) * (C0[0] - P0[0]) + 2 * t * (P2[0] - C0[0])
        dy = 2 * (1 - t) * (C0[1] - P0[1]) + 2 * t * (P2[1] - C0[1])
        L = math.hypot(dx, dy)
        return x, y, dy / L, -dx / L   # outward normal (up)
    for t, ln, bend in ((0.04, 13, -5), (0.2, 10, -3), (0.38, 7, -1)):
        x, y, nx, ny = lid(t)
        ex, ey = x + nx * ln + bend, y + ny * ln
        eye.append(f'<path d="M{x:.1f} {y:.1f} Q{x + nx * ln * 0.4 + bend * 1.2:.1f} {y + ny * ln * 0.6:.1f} {ex:.1f} {ey:.1f}" fill="none" stroke="{P["lash"]}" stroke-width="2.6" stroke-linecap="round"/>')
    eye.append(f'<path d="M{cx-rx+8} {cy+ry-2} Q{cx} {cy+ry+3} {cx+rx-6} {cy+ry-3}" fill="none" stroke="{P["lash"]}" stroke-width="1.6" stroke-linecap="round" opacity="0.5"/>')
    s.append("".join(eye))

    # ---- horn
    s.append(f'<path d="{hornp}" fill="url(#{u}horn)" {stroke}/>')
    s.append(f'<g clip-path="url(#{u}chorn)">')
    for i in range(7):
        y = 160 - i * 20
        s.append(f'<path d="M{604} {y+14} Q{650} {y-10} {700} {y-22}" fill="none" stroke="{P["horn_line"]}" stroke-width="5" opacity="0.65"/>')
    s.append(f'<path d="M640 150 C652 112 666 74 684 34" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" opacity="0.55"/>')
    s.append('</g>')
    s.append(f'<path d="M640 152 C652 122 664 90 678 54" fill="none" stroke="{P["glow"]}" stroke-width="10" opacity="0.35" filter="url(#{u}b6)"/>')

    # ---- forelock over the forehead
    fl = [((590, 142), (630, 112), (676, 130), (668, 176), 34, 1),
          ((598, 140), (640, 126), (690, 156), (654, 204), 28, 0),
          ((582, 146), (610, 108), (660, 100), (686, 138), 24, 2)]
    for p0, p1, p2, p3, w, idx in fl:
        s.append(hair_lock(p0, p1, p2, p3, w, idx, n=14))
    s.append('</g>')
    s.append('</g>')

    # sparkles
    for x, y, r, op in ((706, 74, 13, 0.95), (732, 120, 8, 0.8), (644, 34, 9, 0.85), (600, 22, 6, 0.7), (740, 40, 7, 0.7), (170, 150, 10, 0.7), (110, 230, 6, 0.6)):
        s.append(star(x, y, r, P["spark"], op))
    if P.get("paint"):
        s.append(f'<rect x="0" y="-30" width="{W}" height="{H+30}" filter="url(#{u}paper)" opacity="0.5" style="mix-blend-mode:multiply" pointer-events="none"/>')
    s.append("</svg>")
    return "".join(s)


pastel = dict(
    label="Soft pastel unicorn, ambitious study",
    bg=[(0, "#e4dafc"), (0.5, "#f9e1ef"), (0.82, "#fdeadf"), (1, "#fff3dc")],
    hill1="#cfe9dc", hill2="#bfe3d0", ground1="#c9ecd8", ground2="#a9dcc0", ground_o=0.95, shadow="#5d8579", shadow_o=0.4,
    coat=[(0, "#ffffff"), (0.55, "#fff2f7"), (1, "#f4d5e5")],
    legcoat=[(0, "#fff7fa"), (0.6, "#fbe6ef"), (1, "#eec9dc")],
    farleg=[(0, "#f6dce8"), (1, "#e6bfd5")],
    horn_g=[(0, "#fff8cf"), (0.55, "#ffe08a"), (1, "#f2b955")], horn_line="#e19c3a", glow="#fff3a8",
    hoof_g=[(0, "#ecdcf8"), (1, "#c3a6e6")],
    hair=[[(0, "#efe6ff"), (0.5, "#b9a2f5"), (1, "#8e72e0")],
          [(0, "#ffe0f2"), (0.55, "#eaaeea"), (1, "#b98bf0")],
          [(0, "#dff3ff"), (0.55, "#a9d3f8"), (1, "#8cb0ee")]],
    iris_g=[(0, "#c0adff"), (0.5, "#7a5fe0"), (1, "#3a2984")],
    pupil="#1c1244", eye_white="#ffffff", lash="#3a2a6e", lid_shadow="#7b5fc4", nostril="#c4809f",
    blush="#ff9fc0", blush_o=0.8, ear_in="#ffc4d8", shade="#f0bfd8", hi="#ffffff", strand="#ffffff", spark="#fff3a8",
    fetlock="#e6b6cf", mark="#c9a6f7", flower1="#ffd1e6", flower2="#fff0a8", flower_c="#f4a6c9", ol=None, seed=4)

paint = dict(
    label="Painterly storybook unicorn, ambitious study",
    bg=[(0, "#f4e2c6"), (0.7, "#ecd0b6"), (1, "#d7c59f")],
    hill1="#b9b78f", hill2="#a3ab7d", ground1="#a9b98c", ground2="#8ea272", ground_o=0.9, shadow="#46301f", shadow_o=0.38,
    coat=[(0, "#fbf3e6"), (0.55, "#f0e2cd"), (1, "#d6bc9c")],
    legcoat=[(0, "#f9eedd"), (0.6, "#ecd9c0"), (1, "#d3b794")],
    farleg=[(0, "#e3cfb2"), (1, "#cdb08e")],
    horn_g=[(0, "#f4d58f"), (0.55, "#d9a24f"), (1, "#a8742e")], horn_line="#8f5f24", glow="#fbe3a2",
    hoof_g=[(0, "#9a6a46"), (1, "#5c3b25")],
    hair=[[(0, "#c78aa0"), (0.5, "#a45f7e"), (1, "#74405c")],
          [(0, "#e3adba"), (0.6, "#c07a93"), (1, "#8e506b")],
          [(0, "#ebc57e"), (0.6, "#c7954a"), (1, "#8f6a3a")]],
    iris_g=[(0, "#9a6a58"), (0.5, "#5b3a31"), (1, "#2a1a17")],
    pupil="#1b100e", eye_white="#fbf3e6", lash="#3a2a24", lid_shadow="#5b3a31", nostril="#8e5a4a",
    blush="#d88b9a", blush_o=0.75, ear_in="#d7a0a5", shade="#c9ab86", hi="#fffaf0", strand="#f7e7d4", spark="#fbe3a2",
    fetlock="#bf9d78", mark="#c07a93", flower1="#e3adba", flower2="#ebc57e", flower_c="#8f6a3a", ol="#4a3426", ow=1.6, paint=True, seed=4)

def variant(base, **kw):
    d = dict(base)
    d.update(kw)
    return d


VARIANTS = {
    "var-mint": dict(
        coat=[(0, "#ffffff"), (0.55, "#effbf4"), (1, "#cdeede")], legcoat=[(0, "#f6fffa"), (0.6, "#dcf5e8"), (1, "#bfe6d1")],
        farleg=[(0, "#d4f0e1"), (1, "#b4dfc9")], shade="#b9e3cd", blush="#ffb3a8", mark="#ff9fb3",
        hair=[[(0, "#ffe9c4"), (0.5, "#ffbf80"), (1, "#f59a62")], [(0, "#ffd9d2"), (0.55, "#ff9fa0"), (1, "#e8727f")],
              [(0, "#fff3c4"), (0.6, "#ffd96b"), (1, "#f2b23e")]],
        horn_g=[(0, "#ffffff"), (0.55, "#d9f3ff"), (1, "#a9d6f2")], horn_line="#7fb9de", glow="#d9f3ff",
        iris_g=[(0, "#9fe0c0"), (0.5, "#3fae85"), (1, "#176047")], pupil="#0f2f26", lash="#1f4a3c", lid_shadow="#3fae85",
        ear_in="#ffd0c8", hoof_g=[(0, "#fbe6d4"), (1, "#e8bfa0")], fetlock="#a8d8c0"),
    "var-lilac": dict(
        coat=[(0, "#fbf8ff"), (0.55, "#ece3fb"), (1, "#d3c2f0")], legcoat=[(0, "#f6f1ff"), (0.6, "#e2d6f7"), (1, "#c9b6ec")],
        farleg=[(0, "#dccff3"), (1, "#c3b0e8")], shade="#cdbcf0", blush="#f7a6d4", mark="#6fd0e6",
        hair=[[(0, "#d9fbff"), (0.5, "#79d6e8"), (1, "#3fa7c9")], [(0, "#e4f6ff"), (0.55, "#9ad3f5"), (1, "#5d9fe0")],
              [(0, "#e8ffe9"), (0.6, "#9fe3b8"), (1, "#5cc08a")]],
        horn_g=[(0, "#ffeefc"), (0.55, "#ffc4ee"), (1, "#f090d0")], horn_line="#d86bb8", glow="#ffd6f4",
        iris_g=[(0, "#9fe9f2"), (0.5, "#2fb0c9"), (1, "#115a77")], pupil="#0c2a3a", lash="#2e2a6e", lid_shadow="#6f5fc4",
        ear_in="#f0c4f0", hoof_g=[(0, "#d8f1fb"), (1, "#a6d0e6")], fetlock="#bba6e2"),
    "var-peach": dict(
        coat=[(0, "#fffaf2"), (0.55, "#ffeedd"), (1, "#f8d3b6")], legcoat=[(0, "#fff6ea"), (0.6, "#fbe2cb"), (1, "#f2c6a2")],
        farleg=[(0, "#f6dcc2"), (1, "#eabf9c")], shade="#f2c6a4", blush="#ff8f9f", mark="#9a7be8",
        hair=[[(0, "#f4e3ff"), (0.5, "#c58ff0"), (1, "#8c55d6")], [(0, "#ffd6ea"), (0.55, "#f08cc0"), (1, "#c9559b")],
              [(0, "#dcd6ff"), (0.6, "#a79bf0"), (1, "#6f63d6")]],
        horn_g=[(0, "#fffbe0"), (0.55, "#ffe9a0"), (1, "#f7c75c")], horn_line="#e3a73c", glow="#fff3a8",
        iris_g=[(0, "#ffd29a"), (0.5, "#d98a3c"), (1, "#7a3f12")], pupil="#2a1408", lash="#5a2d44", lid_shadow="#c9559b",
        ear_in="#ffc0cc", hoof_g=[(0, "#ffe1ec"), (1, "#f0b0c8")], fetlock="#f0b890"),
}

if __name__ == "__main__":
    for key, P in (("pastel", pastel), ("paint", paint)):
        with open(os.path.join(OUT, f"{key}-uni.svg"), "w", encoding="utf-8") as fh:
            fh.write(build(P, key + "u"))
    for key, kw in VARIANTS.items():
        with open(os.path.join(OUT, f"pastel-{key}.svg"), "w", encoding="utf-8") as fh:
            fh.write(build(variant(pastel, **kw), "p" + key.replace("-", "")))
    # close-ups of the head for checking
    with open(os.path.join(OUT, "pastel-head.svg"), "w", encoding="utf-8") as fh:
        fh.write(build(pastel, "pheadu", view="520 -30 260 340"))
    print("ok")
