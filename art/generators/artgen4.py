"""Unicorn rig, round 4.

A pose is a small set of numbers: closed body outline, crest and throat curves for the neck,
four leg chains, a head placement and hair directions. The unicorn is drawn from a pose, a palette
and a set of trait layers (wings, mane style, coat pattern). Everything is plain SVG:
flat fills with one shared gradient (no outlines, so overlapping shapes merge), soft shading from
radial gradients (no filters), clip paths for shading.

Usage: python artgen4.py OUTDIR   (standard library only)
"""
import sys, os, math, random

W, H = 800, 700


# ------------------------------------------------------------------ geometry helpers
def spl(pts, per=6):
    """Uniform Catmull-Rom through pts (tuples of any length), sampled `per` times per span."""
    out = []
    n = len(pts)
    for i in range(n - 1):
        p0, p1, p2, p3 = pts[max(i - 1, 0)], pts[i], pts[i + 1], pts[min(i + 2, n - 1)]
        for k in range(per):
            t = k / per
            out.append(tuple(
                0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t * t
                       + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t ** 3) for j in range(len(p1))))
    out.append(tuple(pts[-1]))
    return out


def area(pts):
    """Signed polygon area (positive = clockwise on screen). Clip paths with several sub-paths only act as a
    union when every sub-path winds the same way."""
    return sum(pts[i][0] * pts[(i + 1) % len(pts)][1] - pts[(i + 1) % len(pts)][0] * pts[i][1] for i in range(len(pts))) / 2


def cr(pts):
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


def closed(pts):
    """Closed smooth outline through pts."""
    if area(pts) < 0:
        pts = pts[::-1]
    n = len(pts)
    d = f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"
    for i in range(n):
        p0, p1, p2, p3 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        d += f"C{c1[0]:.1f} {c1[1]:.1f} {c2[0]:.1f} {c2[1]:.1f} {p2[0]:.1f} {p2[1]:.1f}"
    return d + "Z"


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
    if area(left + right[::-1]) < 0:
        left, right = right, left
    d = f"M{left[0][0]:.1f} {left[0][1]:.1f}" + cr(left)
    d += f"L{right[-1][0]:.1f} {right[-1][1]:.1f}" + cr(right[::-1]) + "Z"
    return d


def limb(ctrl, per=6):
    dense = spl(ctrl, per)
    return ribbon([(p[0], p[1]) for p in dense], [p[2] for p in dense])


def lock_widths(n, w0):
    ws = []
    for i in range(n + 1):
        t = i / n
        w = w0 * (0.14 + 0.86 * math.sin(min(1.0, t * 1.9) * math.pi / 2)) * (1 - t ** 1.8)
        ws.append(max(w * (1 + 0.2 * math.sin(t * math.pi)), 0.01))
    return ws


def hair_curve(root, ang, length, amp, phase, droop, n=18):
    a = math.radians(ang)
    dx, dy = math.cos(a), math.sin(a)
    px, py = -dy, dx
    pts = []
    for i in range(n + 1):
        s = i / n
        off = amp * math.sin(phase + s * 2.4 * math.pi) * s ** 0.8
        pts.append((root[0] + dx * length * s + px * off, root[1] + dy * length * s + py * off + droop * s * s))
    return pts


def star(x, y, r, fill, op=1.0, rot=0):
    k = 0.16
    return (f'<path transform="rotate({rot} {x} {y})" d="M{x} {y-r} Q{x+r*k} {y-r*k} {x+r} {y} Q{x+r*k} {y+r*k} {x} {y+r} '
            f'Q{x-r*k} {y+r*k} {x-r} {y} Q{x-r*k} {y-r*k} {x} {y-r} Z" fill="{fill}" opacity="{op}"/>')


# ------------------------------------------------------------------ poses (side view, facing right, ground y=600)
BODY_STAND = [(246, 392), (256, 350), (290, 330), (340, 332), (400, 340), (458, 328), (500, 338), (530, 374),
              (540, 420), (524, 456), (480, 466), (420, 456), (362, 448), (306, 452), (262, 436)]

POSES = {
    "stand": dict(
        dy=0, head=(572, 152, -4, 1.0), eye="open",
        crest=[(572, 152), (538, 200), (528, 282), (476, 322)],
        throat=[(542, 424), (566, 376), (562, 332), (576, 298)],
        far=dict(
            fh=[(332, 402, 70), (348, 454, 50), (334, 500, 38), (326, 530, 27), (330, 560, 19), (333, 578, 22), (333, 592, 19)],
            ff=[(516, 412, 58), (526, 462, 42), (532, 514, 29), (533, 548, 20), (534, 574, 23), (534, 592, 19)]),
        near=dict(
            nh=[(292, 396, 92), (314, 452, 64), (286, 500, 44), (274, 530, 30), (278, 560, 21), (281, 578, 24), (281, 593, 21)],
            nf=[(490, 408, 70), (498, 462, 48), (500, 516, 33), (500, 548, 22), (501, 574, 25), (501, 593, 22)]),
        tail=dict(root=(256, 366), ang=130, length=240, droop=70),
        mane_front=116, mane_back=158, shadow=(385, 604, 250, 16)),
    "walk": dict(
        dy=-6, head=(576, 158, -10, 1.0), eye="open",
        crest=[(576, 158), (542, 204), (530, 282), (478, 316)],
        throat=[(544, 418), (568, 374), (566, 334), (580, 304)],
        far=dict(
            fh=[(334, 396, 70), (356, 450, 50), (372, 500, 38), (358, 536, 27), (356, 566, 19), (357, 583, 22), (357, 593, 19)],
            ff=[(508, 406, 58), (506, 458, 42), (486, 512, 29), (474, 548, 20), (470, 574, 23), (470, 592, 19)]),
        near=dict(
            nh=[(292, 390, 92), (296, 446, 64), (258, 494, 44), (226, 526, 30), (206, 552, 21), (198, 568, 24), (194, 579, 21)],
            nf=[(492, 402, 70), (518, 454, 48), (556, 486, 34), (548, 520, 23), (540, 546, 24), (537, 562, 21)]),
        tail=dict(root=(256, 360), ang=170, length=240, droop=-10),
        mane_front=128, mane_back=166, shadow=(380, 604, 250, 16)),
    "sleep": dict(
        dy=112, head=(612, 432, 16, 1.0), eye="closed", neck_light=(540, 420),
        crest=[(612, 432), (586, 396), (528, 396), (468, 438)],
        throat=[(538, 548), (552, 560), (562, 566), (572, 566)],
        far=dict(
            fh=[(336, 510, 70), (360, 562, 52), (342, 582, 36), (372, 590, 22), (410, 592, 20)],
            ff=[(524, 520, 58), (566, 566, 32), (606, 586, 20), (644, 592, 18)]),
        near=dict(
            nh=[(294, 508, 92), (334, 560, 64), (280, 580, 40), (330, 592, 24), (372, 593, 22)],
            nf=[(500, 522, 70), (548, 568, 38), (588, 588, 22), (626, 593, 20)]),
        tail=dict(root=(256, 366), ang=168, length=230, droop=26),
        mane_front=74, mane_back=150, shadow=(410, 598, 290, 18), no_hoof_tufts=True, zzz=True,
        extra_shade=[(470, 520, 30, 70, 0, 0.6), (352, 566, 56, 24, 0, 0.6), (524, 556, 46, 24, 0, 0.6), (566, 572, 50, 18, 0, 0.6), (300, 505, 28, 60, 0, 0.45), (420, 560, 90, 20, 0, 0.5)]),
}


def hoof(ctrl):
    (x1, y1, _), (x2, y2, w2) = ctrl[-2], ctrl[-1]
    dx, dy = x2 - x1, y2 - y1
    L = math.hypot(dx, dy) or 1
    dx, dy = dx / L, dy / L
    pts = [(x2 - dx * 8, y2 - dy * 8), (x2 + dx * 4, y2 + dy * 4), (x2 + dx * 15, y2 + dy * 15)]
    return ribbon(pts, [w2 + 1, w2 + 7, w2 + 9])


# ------------------------------------------------------------------ the drawing
def build(P, pose_name="stand", traits=None, uid="u", view=None, scene=True):
    traits = dict(dict(wings=None, mane="flow", pattern=None, socks=False), **(traits or {}))
    pose = POSES[pose_name]
    rnd = random.Random(P.get("seed", 5))
    dy = pose["dy"]
    defs, grads = [], {}

    def lg(id_, stops, x1=0, y1=0, x2=0, y2=1, units=None):
        s = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
        extra = f' gradientUnits="userSpaceOnUse"' if units else ""
        defs.append(f'<linearGradient id="{uid}{id_}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"{extra}>{s}</linearGradient>')

    def blob(cx, cy, rx, ry, color, op, rot=0):
        gid = grads.get(color)
        if gid is None:
            gid = f"{uid}bl{len(grads)}"
            grads[color] = gid
            defs.append(f'<radialGradient id="{gid}"><stop offset="0" stop-color="{color}" stop-opacity="1"/>'
                        f'<stop offset="0.55" stop-color="{color}" stop-opacity="0.55"/><stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>')
        return f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="url(#{gid})" opacity="{op}" transform="rotate({rot} {cx:.1f} {cy:.1f})"/>'

    lg("bg", P["bg"], 0, -30, 0, 700, units=True)
    lg("coat", P["coat"], 0, 300 + dy, 0, 560 + dy, units=True)
    lg("farleg", P["farleg"], 0, 0, 1, 0)
    lg("horn", P["horn_g"], 0, 0, 0, 1)
    lg("hoof", P["hoof_g"], 0, 0, 0, 1)
    lg("wing", P["wing"], 0, 0, 1, 1)
    for i, hair in enumerate(P["hair"]):
        lg(f"hair{i}", hair, 0, 0, 1, 1)
    defs.append(f'<radialGradient id="{uid}iris" cx="0.5" cy="0.35" r="0.75">' + "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in P["iris_g"]) + "</radialGradient>")

    hx, hy, hang, hs = pose["head"]
    head_t = f'translate({hx} {hy}) rotate({hang}) scale({hs}) translate(-574 -152)'

    HEAD = ("M574 152 C598 130 648 140 674 172 C696 196 716 222 724 246 C732 264 724 282 702 288 C686 292 672 292 660 288 "
            "C645 301 626 308 610 302 C596 298 586 296 578 304 C566 316 556 318 540 300 L548 200 Z")
    crest = bez(*pose["crest"], 20)
    throat = bez(*pose["throat"], 12)
    def hp(x, y):
        """head-local point -> canvas point"""
        a = math.radians(hang)
        lx, ly = (x - 574) * hs, (y - 152) * hs
        return (hx + lx * math.cos(a) - ly * math.sin(a), hy + lx * math.sin(a) + ly * math.cos(a))
    neck_poly = crest + [(470, 380 + dy), (500, 440 + dy)] + throat + [hp(596, 284), hp(600, 200), hp(590, 160)]
    if area(neck_poly) < 0:
        neck_poly = neck_poly[::-1]
    neck_d = f"M{neck_poly[0][0]:.1f} {neck_poly[0][1]:.1f}" + cr(neck_poly) + "Z"
    body_pts = [(x, y + dy) for x, y in BODY_STAND]
    body_d = closed(body_pts)

    # --- clip shapes (union of the coat parts)
    near_paths = [limb(c) for c in pose["near"].values()]
    clip_shapes = [body_d, neck_d] + near_paths
    defs.append(f'<clipPath id="{uid}coatclip"><path d="{"".join(clip_shapes)}"/></clipPath>')
    defs.append(f'<clipPath id="{uid}headclip"><path d="{HEAD}"/></clipPath>')
    hornp = "M622 156 C638 112 660 70 686 26 C682 78 672 122 660 166 Z"
    defs.append(f'<clipPath id="{uid}hornclip"><path d="{hornp}"/></clipPath>')

    vb = view or f"0 -30 {W} {H + 30}"
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" role="img" aria-label="{P["label"]}">']
    body_s = []

    # --- scene
    if scene:
        body_s.append(f'<rect x="0" y="-30" width="{W}" height="{H + 30}" fill="url(#{uid}bg)"/>')
        body_s.append(f'<path d="M0 560 C120 500 260 520 380 556 C500 590 640 520 800 540 L800 700 L0 700 Z" fill="{P["hill1"]}" opacity="0.75"/>')
        body_s.append(f'<path d="M0 596 C140 566 300 586 420 590 C560 594 680 570 800 584 L800 700 L0 700 Z" fill="{P["hill2"]}"/>')
        sx, sy, srx, sry = pose["shadow"]
        body_s.append(blob(sx, sy, srx, sry, P["shadow"], P["shadow_o"]))
        for fx, fy, fr, fc in ((90, 640, 9, P["flower1"]), (160, 660, 7, P["flower2"]), (640, 636, 9, P["flower2"]), (720, 662, 8, P["flower1"]),
                               (560, 668, 6, P["flower1"]), (40, 676, 6, P["flower2"]), (330, 672, 7, P["flower2"]), (470, 650, 6, P["flower1"])):
            petals = "".join(f'<circle cx="{fx + fr*0.8*math.cos(a*math.pi/2.5):.1f}" cy="{fy + fr*0.8*math.sin(a*math.pi/2.5):.1f}" r="{fr*0.55:.1f}" fill="{fc}"/>' for a in range(5))
            body_s.append(f'<g>{petals}<circle cx="{fx}" cy="{fy}" r="{fr*0.45:.1f}" fill="{P["flower_c"]}"/></g>')

    def lock(curve, w0, idx, op=1.0):
        ws = lock_widths(len(curve) - 1, w0)
        return f'<path d="{ribbon(curve, ws)}" fill="url(#{uid}hair{idx})" opacity="{op}"/>'

    def strand(curve, wd=2.2, op=0.6):
        return f'<path d="M{curve[0][0]:.1f} {curve[0][1]:.1f}{cr(curve)}" fill="none" stroke="{P["strand"]}" stroke-width="{wd}" stroke-linecap="round" opacity="{op}"/>'

    # --- wings (behind: the far wing)
    def wing(root, far):
        o = []
        base_ang = P.get("wing_ang", 206)
        n1 = 10
        edge = P["wing_edge"]
        for i in range(n1):
            tt = i / (n1 - 1)
            ang = base_ang + 78 * tt
            L = (250 - 120 * tt) * (0.88 if far else 1.0)
            c = hair_curve(root, ang, L, 10 * (1 if i % 2 else -1), 0.6, 26 + 18 * tt, 16)
            ws = [max(1.0, 46 * (0.5 + 0.5 * math.sin(min(1, (j / 16) * 2.0) * math.pi / 2)) * (1 - (j / 16) ** 3.4)) for j in range(17)]
            o.append(f'<path d="{ribbon(c, ws)}" fill="url(#{uid}wing)" stroke="{edge}" stroke-opacity="0.45" stroke-width="1.4"/>')
        for i in range(9):
            tt = i / 8
            ang = base_ang + 74 * tt + 4
            L = 130 - 40 * tt
            c = hair_curve((root[0] + 6, root[1] + 2), ang, L, 6, 1.2, 12, 12)
            ws = [max(1.0, 38 * (0.5 + 0.5 * math.sin(min(1, (j / 12) * 2.0) * math.pi / 2)) * (1 - (j / 12) ** 3.2)) for j in range(13)]
            o.append(f'<path d="{ribbon(c, ws)}" fill="{P["wing_cov"]}" stroke="{edge}" stroke-opacity="0.35" stroke-width="1.2"/>')
        arm = hair_curve((root[0] + 4, root[1] + 4), base_ang + 8, 120, 4, 0.2, 0, 12)
        o.append(f'<path d="{ribbon(arm, [34 - 14 * (j / 12) for j in range(13)])}" fill="{P["wing_cov"]}" stroke="{edge}" stroke-opacity="0.4" stroke-width="1.2"/>')
        o.append(blob(root[0] - 4, root[1] + 6, 40, 30, P["wing_cov"], 0.95))
        if far:
            o.append(f'<rect x="-100" y="-100" width="1000" height="900" fill="{P["farleg"][1][1]}" opacity="0.18"/>' if False else "")
        return "".join(o)

    wroot = (440, 338 + dy)
    if traits["wings"]:
        body_s.append(wing((wroot[0] + 30, wroot[1] - 4), True))

    # --- far mane layer and tail
    cr_pts = crest
    t0 = pose["tail"]
    tail_locks = []
    n_tail = 7 if traits["mane"] != "bob" else 6
    for i in range(n_tail):
        ang = t0["ang"] + (i - n_tail / 2) * 7 + rnd.uniform(-5, 5)
        length = t0["length"] * (0.7 + 0.3 * rnd.random()) * (0.62 if traits["mane"] == "bob" else 1)
        root = (t0["root"][0] + rnd.uniform(-4, 4), t0["root"][1] + dy + (i - 3) * 5)
        c = hair_curve(root, ang, length, 26 + rnd.uniform(0, 14), rnd.uniform(0, 2), t0["droop"], 20)
        tail_locks.append(lock(c, 50 - abs(i - 3) * 3, i % 3))
    body_s.extend(tail_locks)
    t_root = (t0["root"][0], t0["root"][1] + dy)
    body_s.append(strand(hair_curve(t_root, t0["ang"] - 6, t0["length"] * 0.82, 22, 0.4, t0["droop"], 16), 2.4, 0.5))
    body_s.append(strand(hair_curve(t_root, t0["ang"] + 8, t0["length"] * 0.7, 18, 1.4, t0["droop"], 16), 2.0, 0.45))

    crest_n = normals(crest)

    def mane_locks(layer):
        out = []
        n = 5 if layer == "back" else 11
        for k in range(n):
            t = 0.02 + k * (0.9 / (n - 1))
            ci = int(t * 20)
            c0 = (crest[ci][0] - crest_n[ci][0] * 7, crest[ci][1] - crest_n[ci][1] * 7)
            if layer == "back":
                ang = pose["mane_back"] + rnd.uniform(-8, 8)
                length = (80 + 50 * t + rnd.uniform(0, 24)) * (0.7 if traits["mane"] == "bob" else 1)
                curve = hair_curve((c0[0] + 2, c0[1] + 2), ang, length, 22, k * 0.9, 24, 18)
                out.append(lock(curve, 30 - k * 1.2, 0, 0.9))
            else:
                ang = pose["mane_front"] + rnd.uniform(-4, 4) + (k % 2) * 5
                length = (66 + 56 * t + rnd.uniform(0, 26)) * (0.62 if traits["mane"] == "bob" else 1)
                amp = 14 + rnd.uniform(0, 8)
                curve = hair_curve((c0[0] - 2, c0[1] + 4), ang, length, amp, k * 1.3, 20, 18)
                out.append(lock(curve, 44 - k * 0.8, (k + 1) % 3))
                if k % 3 == 0:
                    out.append(strand(hair_curve((c0[0] - 2, c0[1] + 6), ang, length * 0.85, amp * 0.8, k * 1.3 + 0.2, 20, 14), 2.2, 0.6))
        return "".join(out)

    body_s.append(mane_locks("back"))

    # --- far ear
    head_far_ear = (f'<g transform="{head_t}"><g transform="translate(22 -6) rotate(8 596 152)">'
                    f'<path d="M586 160 C566 124 566 94 576 70 C600 92 614 124 616 154 Z" fill="url(#{uid}farleg)"/>'
                    f'<path d="M588 150 C576 122 576 100 582 84 C598 100 606 122 608 146 Z" fill="{P["ear_in"]}" opacity="0.7"/></g></g>')
    body_s.append(head_far_ear)

    # --- far legs
    def leg_extras(ctrl, far):
        if pose.get("no_hoof_tufts"):
            return f'<path d="{hoof(ctrl)}" fill="url(#{uid}hoof)"/>'
        o = f'<path d="{hoof(ctrl)}" fill="url(#{uid}hoof)" opacity="{0.9 if far else 1}"/>'
        x, y, w = ctrl[-2]
        a = ctrl[-3]
        # fetlock feather: a short tuft of mane-coloured hair over the pastern
        curve = hair_curve((x - w * 0.2, y - 8), 112, 30, 2, 0.4, 0, 8)
        ws = lock_widths(8, w * 0.7)
        o += f'<path d="{ribbon(curve, ws)}" fill="url(#{uid}hair{1 if not far else 2})" opacity="{0.7 if far else 0.85}"/>'
        return o

    for ctrl in pose["far"].values():
        body_s.append(f'<path d="{limb(ctrl)}" fill="url(#{uid}farleg)"/>')
        body_s.append(leg_extras(ctrl, True))

    # --- coat union: body, neck, near legs, head (same fill, no outlines)
    body_s.append(f'<g fill="url(#{uid}coat)"><path d="{body_d}"/><path d="{neck_d}"/>' + "".join(f'<path d="{d}"/>' for d in near_paths)
                  + f'<g transform="{head_t}"><path d="{HEAD}"/></g></g>')
    sh = P["shade"]
    ov = [f'<g clip-path="url(#{uid}coatclip)">']
    ov.append(blob(390, 466 + dy, 190, 44, sh, 0.85))                       # belly
    ov.append(blob(540, 392 + dy, 30, 90, sh, 0.55))                        # chest front
    ov.append(blob(250, 400 + dy, 26, 60, sh, 0.5))                         # rump back
    ov.append(blob(466, 396 + dy, 28, 66, sh, 0.5, 8))                      # behind the shoulder
    ov.append(blob(318, 408 + dy, 44, 70, sh, 0.5, -10))                    # haunch crease
    ov.append(blob(330, 334 + dy, 130, 15, P["hi"], 0.95))                  # back light
    ov.append(blob(302, 350 + dy, 40, 22, P["hi"], 0.8))                    # croup light
    ov.append(blob(505, 360 + dy, 22, 40, P["hi"], 0.55, 20))               # shoulder light
    nl = pose.get("neck_light", (530, 262))
    ov.append(blob(nl[0], nl[1], 12, 58, P["hi"], 0.7, 12))                 # neck light
    for (ex, ey, erx, ery, erot, eop) in pose.get("extra_shade", []):
        ov.append(blob(ex, ey, erx, ery, sh, eop, erot))
    for ctrl in list(pose["near"].values()):
        for k in (1, 2, 3):
            x, y, w = ctrl[k]
            ov.append(blob(x + w * 0.3, y, w * 0.3, 20 + w * 0.3, sh, 0.35))   # soft shade on the front of limbs
    if traits["socks"]:
        for ctrl in pose["near"].values():
            x, y, w = ctrl[-3]
            ov.append(blob(x, y + 30, w * 0.9, 40, P["sock"], 0.9))
    if traits["pattern"] == "stars":
        for (sx, sy, sr, sa) in ((345, 380, 11, 10), (398, 360, 8, -14), (440, 392, 12, 20), (372, 418, 7, 0), (312, 440, 8, 8)):
            ov.append(star(sx, sy + dy, sr, P["mark"], 0.5, sa))
    if traits["pattern"] == "spots":
        for (sx, sy, sr) in ((350, 372, 17), (410, 352, 13), (445, 398, 19), (380, 424, 12), (330, 430, 11), (492, 420, 10)):
            ov.append(blob(sx, sy + dy, sr, sr * 0.9, P["mark"], 0.38))
    ov.append("</g>")
    body_s.append("".join(ov))
    # cutie mark
    body_s.append(f'<g transform="translate(292 {410 + dy}) rotate(-12)">{star(0, 0, 21, P["mark"], 0.95)}{star(0, 0, 8, "#ffffff", 0.9)}</g>')

    for ctrl in pose["near"].values():
        body_s.append(leg_extras(ctrl, False))

    # near wing (over the body)
    if traits["wings"]:
        body_s.append(wing(wroot, False))

    # --- front mane locks over the neck
    body_s.append(mane_locks("front"))

    # --- head details (local frame = head outline frame)
    h = [f'<g transform="{head_t}">']
    h.append(f'<g clip-path="url(#{uid}headclip)">')
    h.append(blob(642, 272, 28, 20, P["blush"], P["blush_o"]))
    h.append(blob(630, 168, 52, 12, P["hi"], 0.9, 14))
    h.append(blob(640, 306, 84, 14, sh, 0.8))
    h.append(blob(566, 250, 24, 60, sh, 0.5))
    h.append("</g>")
    h.append(f'<ellipse cx="711" cy="259" rx="6" ry="4.4" fill="{P["nostril"]}" opacity="0.9" transform="rotate(-20 711 259)"/>')
    h.append(f'<path d="M714 280 C704 291 686 291 672 283" fill="none" stroke="{P["nostril"]}" stroke-width="3" stroke-linecap="round"/>')
    h.append(f'<path d="M672 283 q-5 -3 -6 -8" fill="none" stroke="{P["nostril"]}" stroke-width="2.4" stroke-linecap="round"/>')
    h.append(f'<path d="M584 162 C562 122 560 90 570 62 C598 88 614 122 618 156 Z" fill="url(#{uid}coat)"/>')
    h.append(f'<path d="M586 152 C572 122 570 98 576 78 C594 98 604 124 608 148 Z" fill="{P["ear_in"]}" opacity="0.85"/>')
    cx, cy, rx, ry = 636, 224, 19, 26
    if pose["eye"] == "open":
        h.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{P["eye_white"]}" stroke="{P["lid_shadow"]}" stroke-opacity="0.45" stroke-width="1.6"/>')
        h.append(f'<ellipse cx="{cx+2}" cy="{cy+3}" rx="{rx*0.84}" ry="{ry*0.86}" fill="url(#{uid}iris)"/>')
        h.append(f'<ellipse cx="{cx+3}" cy="{cy+5}" rx="{rx*0.42}" ry="{ry*0.5}" fill="{P["pupil"]}"/>')
        h.append(f'<ellipse cx="{cx+9}" cy="{cy-9}" rx="{rx*0.32}" ry="{ry*0.26}" fill="#fff"/>')
        h.append(f'<circle cx="{cx-4}" cy="{cy+14}" r="{rx*0.16}" fill="#fff" opacity="0.9"/>')
        P0 = (cx - rx - 1, cy - 3); C0 = (cx - 2, cy - ry - 7); P2 = (cx + rx + 1, cy - 5)
        h.append(f'<path d="M{P0[0]} {P0[1]} Q{C0[0]} {C0[1]} {P2[0]} {P2[1]} L{P2[0]} {cy-ry*0.4} L{P0[0]} {cy-ry*0.4} Z" fill="{P["lid_shadow"]}" opacity="0.16"/>')
        h.append(f'<path d="M{P0[0]} {P0[1]} Q{C0[0]} {C0[1]} {P2[0]} {P2[1]}" fill="none" stroke="{P["lash"]}" stroke-width="4.4" stroke-linecap="round"/>')

        def lid(t):
            a, b, c = (1 - t) ** 2, 2 * (1 - t) * t, t * t
            x = a * P0[0] + b * C0[0] + c * P2[0]
            y = a * P0[1] + b * C0[1] + c * P2[1]
            dx = 2 * (1 - t) * (C0[0] - P0[0]) + 2 * t * (P2[0] - C0[0])
            dyy = 2 * (1 - t) * (C0[1] - P0[1]) + 2 * t * (P2[1] - C0[1])
            L = math.hypot(dx, dyy)
            return x, y, dyy / L, -dx / L
        for t, ln, bend in ((0.04, 13, -5), (0.2, 10, -3), (0.38, 7, -1)):
            x, y, nx, ny = lid(t)
            h.append(f'<path d="M{x:.1f} {y:.1f} Q{x + nx * ln * 0.4 + bend * 1.2:.1f} {y + ny * ln * 0.6:.1f} {x + nx * ln + bend:.1f} {y + ny * ln:.1f}" fill="none" stroke="{P["lash"]}" stroke-width="2.6" stroke-linecap="round"/>')
        h.append(f'<path d="M{cx-rx+8} {cy+ry-2} Q{cx} {cy+ry+3} {cx+rx-6} {cy+ry-3}" fill="none" stroke="{P["lash"]}" stroke-width="1.6" stroke-linecap="round" opacity="0.5"/>')
    else:  # closed, asleep: a downward-curving lid line with lashes
        h.append(f'<path d="M{cx-rx-2} {cy-2} Q{cx} {cy+ry*0.75} {cx+rx+2} {cy-4}" fill="none" stroke="{P["lash"]}" stroke-width="4.4" stroke-linecap="round"/>')
        for t, ln in ((0.08, 12), (0.24, 10), (0.4, 8)):
            x = (cx - rx - 2) * (1 - t) ** 2 + 2 * (1 - t) * t * cx + (cx + rx + 2) * t * t
            y = (cy - 2) * (1 - t) ** 2 + 2 * (1 - t) * t * (cy + ry * 0.75) + (cy - 4) * t * t
            h.append(f'<path d="M{x:.1f} {y:.1f} q-3 {ln*0.6:.1f} -{ln*0.5:.1f} {ln:.1f}" fill="none" stroke="{P["lash"]}" stroke-width="2.4" stroke-linecap="round"/>')
    # horn
    h.append(f'<path d="{hornp}" fill="url(#{uid}horn)"/>')
    h.append(f'<g clip-path="url(#{uid}hornclip)">')
    for i in range(7):
        y = 160 - i * 20
        h.append(f'<path d="M604 {y+14} Q650 {y-10} 700 {y-22}" fill="none" stroke="{P["horn_line"]}" stroke-width="5" opacity="0.65"/>')
    h.append(f'<path d="M640 150 C652 112 666 74 684 34" fill="none" stroke="#fff" stroke-width="4" stroke-linecap="round" opacity="0.55"/>')
    h.append("</g>")
    h.append(blob(676, 56, 26, 40, P["glow"], 0.7, 14))
    # forelock
    for p0, p1, p2, p3, w, idx in (((590, 142), (630, 112), (676, 130), (668, 176), 34, 1),
                                   ((598, 140), (640, 126), (690, 156), (654, 204), 28, 0),
                                   ((582, 146), (610, 108), (660, 100), (686, 138), 24, 2)):
        pts = bez(p0, p1, p2, p3, 14)
        h.append(f'<path d="{ribbon(pts, lock_widths(14, w))}" fill="url(#{uid}hair{idx})"/>')
    h.append("</g>")
    body_s.append("".join(h))

    if pose.get("zzz"):
        for k, (ox, oy, sz) in enumerate(((66, -70, 20), (94, -106, 15), (116, -134, 11))):
            zx, zy = hx + ox, hy + oy
            body_s.append(f'<path d="M{zx} {zy} L{zx + sz} {zy} L{zx} {zy + sz} L{zx + sz} {zy + sz}" fill="none" stroke="{P["mark"]}" stroke-width="{3.4 - k * 0.5}" stroke-linecap="round" stroke-linejoin="round" opacity="0.85"/>')
    # sparkles
    hx_, hy_ = hx, hy
    for ox, oy, r, op in ((132, -78, 13, 0.95), (160, -34, 8, 0.8), (72, -118, 9, 0.85), (28, -130, 6, 0.7), (168, -112, 7, 0.7)):
        body_s.append(star(hx_ + ox, hy_ + oy, r, P["spark"], op))
    for x, y, r, op in ((170, 150, 10, 0.7), (110, 230, 6, 0.6)):
        body_s.append(star(x, y, r, P["spark"], op))

    s.append("<defs>" + "".join(defs) + "</defs>")
    s.extend(body_s)
    s.append("</svg>")
    return "".join(s)


pastel = dict(
    label="Soft pastel unicorn",
    bg=[(0, "#e4dafc"), (0.5, "#f9e1ef"), (0.82, "#fdeadf"), (1, "#fff3dc")],
    hill1="#cfe9dc", hill2="#bfe3d0", shadow="#5d8579", shadow_o=0.45,
    coat=[(0, "#ffffff"), (0.55, "#fff2f7"), (1, "#f4d5e5")],
    farleg=[(0, "#f6dce8"), (1, "#e6bfd5")],
    horn_g=[(0, "#fff8cf"), (0.55, "#ffe08a"), (1, "#f2b955")], horn_line="#e19c3a", glow="#fff3a8",
    hoof_g=[(0, "#ecdcf8"), (1, "#c3a6e6")],
    hair=[[(0, "#efe6ff"), (0.5, "#b9a2f5"), (1, "#8e72e0")],
          [(0, "#ffe0f2"), (0.55, "#eaaeea"), (1, "#b98bf0")],
          [(0, "#dff3ff"), (0.55, "#a9d3f8"), (1, "#8cb0ee")]],
    wing=[(0, "#ffffff"), (0.5, "#ece3ff"), (1, "#c3adf3")], wing_cov="#f4eeff", wing_edge="#9f86e0",
    iris_g=[(0, "#c0adff"), (0.5, "#7a5fe0"), (1, "#3a2984")],
    pupil="#1c1244", eye_white="#ffffff", lash="#3a2a6e", lid_shadow="#7b5fc4", nostril="#c4809f",
    blush="#ff9fc0", blush_o=0.8, ear_in="#ffc4d8", shade="#f0bfd8", hi="#ffffff", strand="#ffffff", spark="#fff3a8",
    mark="#c9a6f7", sock="#f6d4ea", flower1="#ffd1e6", flower2="#fff0a8", flower_c="#f4a6c9", seed=5)


def variant(base, **kw):
    d = dict(base)
    d.update(kw)
    return d


MINT = dict(
    coat=[(0, "#ffffff"), (0.55, "#effbf4"), (1, "#cdeede")], farleg=[(0, "#d4f0e1"), (1, "#b4dfc9")], shade="#b9e3cd",
    blush="#ffb3a8", mark="#ff9fb3", sock="#ffe2d6",
    hair=[[(0, "#ffe9c4"), (0.5, "#ffbf80"), (1, "#f59a62")], [(0, "#ffd9d2"), (0.55, "#ff9fa0"), (1, "#e8727f")],
          [(0, "#fff3c4"), (0.6, "#ffd96b"), (1, "#f2b23e")]],
    wing=[(0, "#ffffff"), (0.5, "#dff5e9"), (1, "#a9dcc2")], wing_cov="#ecf9f2", wing_edge="#6fbf98",
    horn_g=[(0, "#ffffff"), (0.55, "#d9f3ff"), (1, "#a9d6f2")], horn_line="#7fb9de", glow="#d9f3ff",
    iris_g=[(0, "#9fe0c0"), (0.5, "#3fae85"), (1, "#176047")], pupil="#0f2f26", lash="#1f4a3c", lid_shadow="#3fae85",
    ear_in="#ffd0c8", hoof_g=[(0, "#fbe6d4"), (1, "#e8bfa0")])
LILAC = dict(
    coat=[(0, "#fbf8ff"), (0.55, "#ece3fb"), (1, "#d3c2f0")], farleg=[(0, "#dccff3"), (1, "#c3b0e8")], shade="#cdbcf0",
    blush="#f7a6d4", mark="#6fd0e6", sock="#cfe9fb",
    hair=[[(0, "#d9fbff"), (0.5, "#79d6e8"), (1, "#3fa7c9")], [(0, "#e4f6ff"), (0.55, "#9ad3f5"), (1, "#5d9fe0")],
          [(0, "#e8ffe9"), (0.6, "#9fe3b8"), (1, "#5cc08a")]],
    wing=[(0, "#ffffff"), (0.5, "#dbf0ff"), (1, "#9fcff0")], wing_cov="#e8f6ff", wing_edge="#62a8d8",
    horn_g=[(0, "#ffeefc"), (0.55, "#ffc4ee"), (1, "#f090d0")], horn_line="#d86bb8", glow="#ffd6f4",
    iris_g=[(0, "#9fe9f2"), (0.5, "#2fb0c9"), (1, "#115a77")], pupil="#0c2a3a", lash="#2e2a6e", lid_shadow="#6f5fc4",
    ear_in="#f0c4f0", hoof_g=[(0, "#d8f1fb"), (1, "#a6d0e6")])
PEACH = dict(
    coat=[(0, "#fffaf2"), (0.55, "#ffeedd"), (1, "#f8d3b6")], farleg=[(0, "#f6dcc2"), (1, "#eabf9c")], shade="#f2c6a4",
    blush="#ff8f9f", mark="#9a7be8", sock="#ffd9e3",
    hair=[[(0, "#f4e3ff"), (0.5, "#c58ff0"), (1, "#8c55d6")], [(0, "#ffd6ea"), (0.55, "#f08cc0"), (1, "#c9559b")],
          [(0, "#dcd6ff"), (0.6, "#a79bf0"), (1, "#6f63d6")]],
    wing=[(0, "#fffaf0"), (0.5, "#ffe6d0"), (1, "#f2bc98")], wing_cov="#ffefe0", wing_edge="#d98f66",
    horn_g=[(0, "#fffbe0"), (0.55, "#ffe9a0"), (1, "#f7c75c")], horn_line="#e3a73c", glow="#fff3a8",
    iris_g=[(0, "#ffd29a"), (0.5, "#d98a3c"), (1, "#7a3f12")], pupil="#2a1408", lash="#5a2d44", lid_shadow="#c9559b",
    ear_in="#ffc0cc", hoof_g=[(0, "#ffe1ec"), (1, "#f0b0c8")])


def portrait(P, uid="pt"):
    """Front view, head and shoulders. The right half is drawn once and mirrored, so both sides match exactly."""
    defs = []

    def lg(id_, stops, x1=0, y1=0, x2=0, y2=1):
        s = "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in stops)
        defs.append(f'<linearGradient id="{uid}{id_}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}">{s}</linearGradient>')

    grads = {}

    def blob(cx, cy, rx, ry, color, op, rot=0):
        gid = grads.get(color)
        if gid is None:
            gid = f"{uid}bl{len(grads)}"
            grads[color] = gid
            defs.append(f'<radialGradient id="{gid}"><stop offset="0" stop-color="{color}" stop-opacity="1"/>'
                        f'<stop offset="0.55" stop-color="{color}" stop-opacity="0.55"/><stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>')
        return f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="url(#{gid})" opacity="{op}" transform="rotate({rot} {cx:.1f} {cy:.1f})"/>'

    lg("bg", P["bg"])
    lg("coat", P["coat"], 0, 0.1, 0, 1)
    lg("horn", P["horn_g"])
    for i, hair in enumerate(P["hair"]):
        lg(f"hair{i}", hair, 0, 0, 1, 1)
    defs.append(f'<radialGradient id="{uid}iris" cx="0.5" cy="0.35" r="0.75">' + "".join(f'<stop offset="{o}" stop-color="{c}"/>' for o, c in P["iris_g"]) + "</radialGradient>")
    mx = lambda x: 600 - x

    R = [(374, 142), (428, 196), (450, 270), (444, 338), (424, 396), (394, 440), (360, 470), (326, 486)]
    head_pts = [(300, 132)] + R + [(300, 492)] + [(mx(x), y) for x, y in reversed(R)]
    head_d = closed(head_pts)
    defs.append(f'<clipPath id="{uid}hc"><path d="{head_d}"/></clipPath>')
    horn_d = "M268 156 C280 100 292 52 300 4 C308 52 320 100 332 156 Z"
    defs.append(f'<clipPath id="{uid}hn"><path d="{horn_d}"/></clipPath>')

    def both(svg_right):
        return svg_right + f'<g transform="translate(600 0) scale(-1 1)">{svg_right}</g>'

    def lock(curve, w0, idx):
        return f'<path d="{ribbon(curve, lock_widths(len(curve) - 1, w0))}" fill="url(#{uid}hair{idx})"/>'

    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 600 640" role="img" aria-label="Soft pastel unicorn, front view">']
    body = [f'<rect width="600" height="640" fill="url(#{uid}bg)"/>']
    body.append(blob(300, 300, 280, 300, "#ffffff", 0.55))
    # back mane
    back = ""
    for k in range(6):
        c = hair_curve((410 - k * 6, 150 + k * 14), 84 + k * 2, 300 + k * 18, 26, k * 0.8, 10, 20)
        back += lock(c, 52 - k * 3, [0, 2, 1][k % 3])
    body.append(both(back))
    # ears (behind head)
    ear = (f'<path d="M376 172 C410 122 440 74 464 36 C482 92 474 152 438 204 Z" fill="url(#{uid}coat)"/>'
           f'<path d="M392 168 C416 132 436 98 454 70 C464 112 458 150 432 188 Z" fill="{P["ear_in"]}" opacity="0.85"/>')
    body.append(both(ear))
    # neck and chest
    body.append(f'<path d="M120 640 C140 556 214 508 250 462 L350 462 C386 508 460 556 480 640 Z" fill="url(#{uid}coat)"/>')
    body.append(blob(300, 510, 70, 40, P["shade"], 0.7))
    body.append(blob(180, 600, 70, 60, P["shade"], 0.4))
    body.append(blob(420, 600, 70, 60, P["shade"], 0.4))
    # front mane draped on both shoulders
    front = ""
    for k in range(7):
        c = hair_curve((404 - k * 5, 190 + k * 16), 74 + k * 3, 250 + k * 14, 22, k * 1.1 + 0.4, 16, 20)
        front += lock(c, 46 - k * 2.5, [1, 0, 2][k % 3])
    body.append(both(front))
    # head
    body.append(f'<path d="{head_d}" fill="url(#{uid}coat)"/>')
    h = [f'<g clip-path="url(#{uid}hc)">']
    h.append(blob(300, 436, 84, 38, P["hi"], 0.85))
    h.append(blob(300, 494, 150, 20, P["shade"], 0.85))
    h.append(blob(300, 470, 74, 12, P["shade"], 0.45))
    h.append(blob(430, 330, 24, 110, P["shade"], 0.5))
    h.append(blob(170, 330, 24, 110, P["shade"], 0.5))
    h.append(blob(300, 175, 110, 18, P["hi"], 0.9))
    h.append(blob(392, 380, 40, 26, P["blush"], P["blush_o"]))
    h.append(blob(208, 380, 40, 26, P["blush"], P["blush_o"]))
    h.append("</g>")
    # muzzle: nostrils and smile
    h.append(f'<ellipse cx="274" cy="428" rx="8" ry="6" fill="{P["nostril"]}" opacity="0.9" transform="rotate(20 274 428)"/>')
    h.append(f'<ellipse cx="326" cy="428" rx="8" ry="6" fill="{P["nostril"]}" opacity="0.9" transform="rotate(-20 326 428)"/>')
    h.append(f'<path d="M266 456 Q283 474 300 463 Q317 474 334 456" fill="none" stroke="{P["nostril"]}" stroke-width="3.4" stroke-linecap="round" stroke-linejoin="round"/>')
    # one eye drawn once, placed twice (mirrored)
    eye = []
    ex, ey, erx, ery = 372, 290, 34, 42
    eye.append(f'<ellipse cx="{ex}" cy="{ey}" rx="{erx}" ry="{ery}" fill="{P["eye_white"]}" stroke="{P["lid_shadow"]}" stroke-opacity="0.45" stroke-width="2"/>')
    eye.append(f'<ellipse cx="{ex-1}" cy="{ey+4}" rx="{erx*0.8}" ry="{ery*0.86}" fill="url(#{uid}iris)"/>')
    eye.append(f'<ellipse cx="{ex-1}" cy="{ey+7}" rx="{erx*0.4}" ry="{ery*0.48}" fill="{P["pupil"]}"/>')
    eye.append(f'<ellipse cx="{ex+9}" cy="{ey-12}" rx="{erx*0.3}" ry="{ery*0.24}" fill="#fff"/>')
    eye.append(f'<circle cx="{ex-12}" cy="{ey+20}" r="{erx*0.14}" fill="#fff" opacity="0.9"/>')
    lid = (ex - erx - 1, ey - 8), (ex + 2, ey - ery - 12), (ex + erx + 2, ey - 6)
    eye.append(f'<path d="M{lid[0][0]} {lid[0][1]} Q{lid[1][0]} {lid[1][1]} {lid[2][0]} {lid[2][1]}" fill="none" stroke="{P["lash"]}" stroke-width="6" stroke-linecap="round"/>')
    for tt, ln, bend in ((0.82, 18, 8), (0.64, 14, 5), (0.46, 10, 3)):
        a, b, c = (1 - tt) ** 2, 2 * (1 - tt) * tt, tt * tt
        x = a * lid[0][0] + b * lid[1][0] + c * lid[2][0]
        y = a * lid[0][1] + b * lid[1][1] + c * lid[2][1]
        eye.append(f'<path d="M{x:.1f} {y:.1f} q{ln*0.5:.1f} -{ln*0.3:.1f} {ln*0.5 + bend:.1f} -{ln:.1f}" fill="none" stroke="{P["lash"]}" stroke-width="3.2" stroke-linecap="round"/>')
    h.append(both("".join(eye)))
    # horn, forelock
    h.append(f'<path d="{horn_d}" fill="url(#{uid}horn)"/>')
    h.append(f'<g clip-path="url(#{uid}hn)">')
    for i in range(8):
        y = 164 - i * 22
        h.append(f'<path d="M250 {y+16} Q300 {y-12} 350 {y-26}" fill="none" stroke="{P["horn_line"]}" stroke-width="6" opacity="0.65"/>')
    h.append(f'<path d="M296 150 C298 100 300 50 301 16" fill="none" stroke="#fff" stroke-width="5" stroke-linecap="round" opacity="0.55"/>')
    h.append("</g>")
    h.append(blob(300, 40, 38, 52, P["glow"], 0.7))
    h.append(both(lock(bez((304, 126), (350, 118), (398, 160), (384, 222), 14), 40, 1) + lock(bez((304, 134), (340, 150), (362, 190), (342, 234), 14), 30, 0)))
    body.append("".join(h))
    for x, y, r, op in ((98, 90, 13, 0.9), (520, 120, 9, 0.85), (60, 220, 7, 0.7), (548, 260, 11, 0.8), (150, 40, 8, 0.7), (460, 30, 7, 0.7)):
        body.append(star(x, y, r, P["spark"], op))
    s.append("<defs>" + "".join(defs) + "</defs>")
    s.extend(body)
    s.append("</svg>")
    return "".join(s)



def main(out):
    jobs = {
        "stand": (pastel, "stand", {}),
        "walk": (pastel, "walk", {}),
        "sleep": (pastel, "sleep", {}),
        "mint-wings-walk": (variant(pastel, **MINT), "walk", dict(wings=True, pattern="stars")),
        "mint-wings": (variant(pastel, **MINT), "stand", dict(wings=True, pattern="stars")),
        "lilac-bob": (variant(pastel, **LILAC), "stand", dict(mane="bob", pattern="spots")),
        "peach-socks": (variant(pastel, **PEACH), "stand", dict(socks=True)),
    }
    for name, (P, pose, traits) in jobs.items():
        with open(os.path.join(out, f"{name}.svg"), "w", encoding="utf-8") as fh:
            fh.write(build(P, pose, traits, uid=name.replace("-", "")))
    # the sleeping pose sits low in the frame, so also write a cropped version for display
    with open(os.path.join(out, "sleep-crop.svg"), "w", encoding="utf-8") as fh:
        fh.write(build(pastel, "sleep", {}, uid="sleepc", view="0 270 800 430"))
    with open(os.path.join(out, "portrait.svg"), "w", encoding="utf-8") as fh:
        fh.write(portrait(pastel))
    with open(os.path.join(out, "portrait-mint.svg"), "w", encoding="utf-8") as fh:
        fh.write(portrait(variant(pastel, **MINT), uid="ptm"))
    print("ok")


if __name__ == "__main__":
    main(sys.argv[1])
