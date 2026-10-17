"""Sea-horse rig, round 8 (third pass on the first non-unicorn creature).

Same ideas as the unicorn rig (artgen5.py), different skeleton: a pose is a spine (x, y, width joints,
head to tail-tip, sampled into one tapered ribbon that includes the curled tail), a head placement,
a belly bump and fin ranges along the spine. Traits are layers: dorsal fin, back ridge, flowing crest,
tail fin, snout length, coat pattern. Views: idle, swim, sleep (side), front and back.
The front and back views take their widths from the side view's body and head depth (set between a
too-wide and a too-thin version), so the views describe one animal. `main` renders one style in all views. Soft pastel, no outlines, no SVG filters.

Usage: python seahorse.py OUTDIR   (standard library only; imports helpers from artgen5.py)
"""
import sys, os, math, random
from artgen5 import spl, cr, closed, bez, normals, ribbon, limb, lock_widths, hair_curve, star, mixhex

W, H = 800, 700
K = 8  # dense samples per spine span


def tangents(pts):
    out = []
    for i in range(len(pts)):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
        out.append(((b[0] - a[0]) / L, (b[1] - a[1]) / L))
    return out


def ellipse_pts(cx, cy, rx, ry, rot=0, n=16):
    r = math.radians(rot)
    return [(cx + rx * math.cos(2 * math.pi * i / n) * math.cos(r) - ry * math.sin(2 * math.pi * i / n) * math.sin(r),
             cy + rx * math.cos(2 * math.pi * i / n) * math.sin(r) + ry * math.sin(2 * math.pi * i / n) * math.cos(r)) for i in range(n)]


# head outline in head-local coordinates: origin = skull centre, snout to the right
HEAD_PTS = [(-48, -6), (-40, -42), (-6, -62), (34, -54), (70, -30), (108, -8), (146, 4), (164, 17), (150, 31), (110, 35),
            (78, 47), (52, 66), (8, 72), (-32, 56), (-50, 28)]
SNOUT = {"short": 0.7, "normal": 1.0, "long": 1.28}


def sx(x, f):
    """stretch the snout: x positions beyond the cheek (x > 60) scale by f"""
    return x if x <= 60 else 60 + (x - 60) * f


POSES = {
    "idle": dict(
        head=(432, 170, 8, 1.0), eye="open", coat_y=(150, 660),
        spine=[(410, 214, 60), (396, 262, 74), (396, 320, 108), (408, 384, 116), (404, 444, 92), (386, 500, 64), (366, 548, 46),
               (358, 596, 36), (380, 636, 29), (424, 648, 24), (458, 624, 20), (452, 590, 16), (424, 578, 12), (408, 598, 9),
               (420, 618, 6), (436, 608, 3)],
        tail_from=6, belly=(436, 372, 60, 78, -4), dorsal=(3.1, 5.9), ridge=(0.5, 3.0),
        pect=dict(at=(402, 276), ang=196, spread=30, length=104), ring_to=7.5),
    "swim": dict(
        head=(506, 250, 16, 1.0), eye="open", coat_y=(200, 600),
        spine=[(476, 290, 62), (442, 328, 76), (414, 376, 104), (386, 428, 112), (342, 472, 90), (292, 500, 64), (242, 514, 46),
               (196, 506, 36), (160, 476, 29), (148, 434, 24), (172, 408, 19), (204, 418, 14), (206, 444, 9), (188, 452, 4)],
        tail_from=6, belly=(432, 410, 58, 76, -30), dorsal=(3.0, 5.8), ridge=(0.4, 3.0),
        pect=dict(at=(430, 320), ang=214, spread=30, length=104), ring_to=7.0),
    "sleep": dict(
        head=(470, 320, 26, 1.0), eye="closed", coat_y=(260, 620), zzz=True,
        spine=[(440, 356, 60), (414, 404, 76), (398, 462, 104), (402, 520, 112), (430, 568, 92), (476, 596, 66), (530, 600, 48),
               (574, 582, 36), (590, 544, 30), (568, 518, 24), (538, 528, 18), (532, 554, 12), (554, 564, 6)],
        tail_from=6, belly=(436, 494, 58, 70, 8), dorsal=(3.0, 5.5), ridge=(0.5, 2.9),
        pect=dict(at=(418, 420), ang=198, spread=30, length=96), ring_to=6.5),
}


def shift_pose(pose, dy):
    pose["head"] = (pose["head"][0], pose["head"][1] + dy) + tuple(pose["head"][2:])
    pose["spine"] = [(x, y + dy, w) for x, y, w in pose["spine"]]
    b = pose["belly"]
    pose["belly"] = (b[0], b[1] + dy) + tuple(b[2:])
    pose["pect"]["at"] = (pose["pect"]["at"][0], pose["pect"]["at"][1] + dy)
    pose["coat_y"] = (pose["coat_y"][0] + dy, pose["coat_y"][1] + dy)


shift_pose(POSES["sleep"], -78)
POSES["sleep"]["fin_len"] = 78


# ------------------------------------------------------------------ shared drawing context
class Doc:
    """Holds the defs and the small drawing helpers every view uses."""

    def __init__(self, P, uid):
        self.P, self.uid = P, uid
        self.defs, self.grads = [], {}

    def lg(self, id_, stops, x1=0, y1=0, x2=0, y2=1, units=False):
        s = "".join(f'<stop offset="{a}" stop-color="{c}"/>' for a, c in stops)
        extra = ' gradientUnits="userSpaceOnUse"' if units else ""
        self.defs.append(f'<linearGradient id="{self.uid}{id_}" x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}"{extra}>{s}</linearGradient>')

    def base(self, coat_y):
        P = self.P
        self.lg("bg", P["bg"], 0, -30, 0, 700, units=True)
        self.lg("coat", P["coat"], 0, coat_y[0], 0, coat_y[1], units=True)
        self.lg("fin", P["fin_g"], 0, 0, 1, 0)
        for i, hair in enumerate(P["hair"]):
            self.lg(f"hair{i}", hair, 0, 0, 1, 1)
        self.defs.append(f'<radialGradient id="{self.uid}iris" cx="0.5" cy="0.35" r="0.75">' + "".join(f'<stop offset="{a}" stop-color="{c}"/>' for a, c in P["iris_g"]) + "</radialGradient>")

    def blob(self, cx, cy, rx, ry, color, op, rot=0):
        gid = self.grads.get(color)
        if gid is None:
            gid = f"{self.uid}bl{len(self.grads)}"
            self.grads[color] = gid
            self.defs.append(f'<radialGradient id="{gid}"><stop offset="0" stop-color="{color}" stop-opacity="1"/>'
                             f'<stop offset="0.55" stop-color="{color}" stop-opacity="0.55"/><stop offset="1" stop-color="{color}" stop-opacity="0"/></radialGradient>')
        return f'<ellipse cx="{cx:.1f}" cy="{cy:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="url(#{gid})" opacity="{op}" transform="rotate({rot} {cx:.1f} {cy:.1f})"/>'

    def lock(self, curve, w0, idx, op=1.0):
        return f'<path d="{ribbon(curve, lock_widths(len(curve) - 1, w0))}" fill="url(#{self.uid}hair{idx})" opacity="{op}"/>'

    def strand(self, curve, wd=2.0, op=0.6):
        return f'<path d="M{curve[0][0]:.1f} {curve[0][1]:.1f}{cr(curve)}" fill="none" stroke="#ffffff" stroke-width="{wd}" stroke-linecap="round" opacity="{op}"/>'

    def fan(self, items, op=0.8, ray_op=0.4, veil=True, base=False):
        """items: (root, ang_deg, length, amp, phase); roots run along the fin base, in order.
        The veil has a pale inner layer (so it reads as a membrane with a deeper edge); `base` adds a darker
        band along the roots, where the fin joins the body."""
        out = []
        curves = [hair_curve(r, a, L, amp, ph, 10, 14) for (r, a, L, amp, ph) in items]
        if veil:
            pts, inner = [], []
            for i, c in enumerate(curves):
                r0 = c[0]
                pts.append(c[-1])
                inner.append((r0[0] + (c[-1][0] - r0[0]) * 0.52, r0[1] + (c[-1][1] - r0[1]) * 0.52))
                if i < len(curves) - 1:
                    dip = ((c[10][0] + curves[i + 1][10][0]) / 2, (c[10][1] + curves[i + 1][10][1]) / 2)   # scallop dip between rays
                    pts.append(dip)
                    rm = ((r0[0] + curves[i + 1][0][0]) / 2, (r0[1] + curves[i + 1][0][1]) / 2)
                    inner.append((rm[0] + (dip[0] - rm[0]) * 0.46, rm[1] + (dip[1] - rm[1]) * 0.46))
            roots = [(r[0], r[1]) for (r, a, L, amp, ph) in items[::-1]]
            out.append(f'<path d="{closed(pts + roots)}" fill="url(#{self.uid}fin)" opacity="{op}"/>')
            out.append(f'<path d="{closed(inner + roots)}" fill="#ffffff" opacity="0.26"/>')
        for c in curves:
            ws = [3.4 * (1 - (j / 14)) + 0.6 for j in range(15)]
            out.append(f'<path d="{ribbon(c, ws)}" fill="{self.P["ray"]}" opacity="{ray_op}"/>')
        if base and len(items) > 2:
            rts = [(r[0], r[1]) for (r, a, L, amp, ph) in items]
            out.append(f'<path d="{ribbon(spl(rts, 4), [9.0 * math.sin(math.pi * j / (len(spl(rts, 4)) - 1)) ** 0.6 + 1.5 for j in range(len(spl(rts, 4)))])}" fill="{self.P["ray"]}" opacity="0.38"/>')
        return "".join(out)

    def stripes(self, dense, k0, k1, sag=0.12, reach=0.64):
        """Soft bands across a tapered body or tail. dense = (x, y, width) samples. Band thickness and spacing
        follow the local width, so they stay even from the chest to the tail tip."""
        pts = [(p[0], p[1]) for p in dense]
        nr, tg = normals(pts), tangents(pts)
        out, last, k = [], dense[k0], k0
        acc = 0.0
        while k < k1:
            p = dense[k]
            if k > k0:
                acc += math.hypot(p[0] - dense[k - 1][0], p[1] - dense[k - 1][1])
            w = p[2]
            period = max(16.0, min(48.0, w * 0.46))
            if acc >= period:
                acc = 0.0
                n, t = nr[k], tg[k]
                a = (p[0] + n[0] * w * reach, p[1] + n[1] * w * reach)
                b = (p[0] - n[0] * w * reach, p[1] - n[1] * w * reach)
                m = (p[0] + t[0] * w * sag, p[1] + t[1] * w * sag)
                cc = spl([a, m, b], 6)
                thick = max(4.0, min(22.0, period * 0.5))
                prof = [0.62 + 0.38 * math.sin(math.pi * i / (len(cc) - 1)) for i in range(len(cc))]
                out.append(f'<path d="{ribbon(cc, [thick * 1.9 * q for q in prof])}" fill="{self.P["mark"]}" opacity="0.14"/>')
                out.append(f'<path d="{ribbon(cc, [thick * 1.25 * q for q in prof])}" fill="{self.P["mark"]}" opacity="0.2"/>')
                out.append(f'<path d="{ribbon(cc, [thick * 0.7 * q for q in prof])}" fill="{self.P["mark"]}" opacity="0.34"/>')
            k += 1
        return "".join(out)

    def fin_at(self, at, ang, spread, length, n=7, gap=6, op=0.92):
        """A small fan whose rays leave a short base line at `at`, centred on direction `ang`."""
        a = math.radians(ang + 90)
        items = []
        for q in range(n):
            u = q / (n - 1)
            off = (q - (n - 1) / 2) * gap
            root = (at[0] + math.cos(a) * off, at[1] + math.sin(a) * off)
            items.append((root, ang - spread + 2 * spread * u, length * (0.72 + 0.28 * math.sin(u * math.pi)), 2.5 * (1 if q % 2 else -1), q * 0.8))
        return self.fan(items, op, 0.42)

    def eye(self, cx, cy, rx, ry, ts, side=True, closed_eye=False):
        P, uid = self.P, self.uid
        d = []
        if closed_eye:
            d.append(f'<path d="M{cx - rx - 2} {cy - 2} Q{cx} {cy + ry * 0.75} {cx + rx + 2} {cy - 4}" fill="none" stroke="{P["lash"]}" stroke-width="4.4" stroke-linecap="round"/>')
            for t_, ln in ((0.08, 12), (0.24, 10), (0.4, 8)):
                x = (cx - rx - 2) * (1 - t_) ** 2 + 2 * (1 - t_) * t_ * cx + (cx + rx + 2) * t_ * t_
                y = (cy - 2) * (1 - t_) ** 2 + 2 * (1 - t_) * t_ * (cy + ry * 0.75) + (cy - 4) * t_ * t_
                d.append(f'<path d="M{x:.1f} {y:.1f} q-3 {ln * 0.6:.1f} -{ln * 0.5:.1f} {ln:.1f}" fill="none" stroke="{P["lash"]}" stroke-width="2.4" stroke-linecap="round"/>')
            return "".join(d)
        ox, hx_ = (2, 9) if side else (-2, 5)
        d.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{rx}" ry="{ry}" fill="{P["eye_white"]}" stroke="{P["lid_shadow"]}" stroke-opacity="0.45" stroke-width="1.6"/>')
        d.append(f'<ellipse cx="{cx + ox}" cy="{cy + 3}" rx="{rx * 0.84}" ry="{ry * 0.86}" fill="url(#{uid}iris)"/>')
        d.append(f'<ellipse cx="{cx + ox + 1}" cy="{cy + 5}" rx="{rx * 0.42}" ry="{ry * 0.5}" fill="{P["pupil"]}"/>')
        d.append(f'<ellipse cx="{cx + hx_}" cy="{cy - 9}" rx="{rx * 0.32}" ry="{ry * 0.26}" fill="#fff"/>')
        d.append(f'<circle cx="{cx - 5 if side else cx - 8}" cy="{cy + 14}" r="{rx * 0.16}" fill="#fff" opacity="0.9"/>')
        P0, C0, P2 = (cx - rx - 1, cy - 3), (cx - 2, cy - ry - 7), (cx + rx + 1, cy - 5)
        d.append(f'<path d="M{P0[0]} {P0[1]} Q{C0[0]} {C0[1]} {P2[0]} {P2[1]}" fill="none" stroke="{P["lash"]}" stroke-width="4.4" stroke-linecap="round"/>')
        for t_, ln, bend in ts:
            a_, b_, c_ = (1 - t_) ** 2, 2 * (1 - t_) * t_, t_ * t_
            x = a_ * P0[0] + b_ * C0[0] + c_ * P2[0]
            y = a_ * P0[1] + b_ * C0[1] + c_ * P2[1]
            dx = 2 * (1 - t_) * (C0[0] - P0[0]) + 2 * t_ * (P2[0] - C0[0])
            dyy = 2 * (1 - t_) * (C0[1] - P0[1]) + 2 * t_ * (P2[1] - C0[1])
            L = math.hypot(dx, dyy)
            nx, ny = dyy / L, -dx / L
            d.append(f'<path d="M{x:.1f} {y:.1f} Q{x + nx * ln * 0.4 + bend * 1.2:.1f} {y + ny * ln * 0.6:.1f} {x + nx * ln + bend:.1f} {y + ny * ln:.1f}" fill="none" stroke="{P["lash"]}" stroke-width="2.6" stroke-linecap="round"/>')
        return "".join(d)


# ------------------------------------------------------------------ the underwater scene
def draw_scene(D, glow, fish=True):
    P, uid = D.P, D.uid
    o = [f'<rect x="0" y="-30" width="{W}" height="{H + 30}" fill="url(#{uid}bg)"/>']
    for x0, w0, op in ((120, 70, 0.28), (300, 50, 0.22), (520, 90, 0.2), (700, 46, 0.24)):
        o.append(f'<path d="M{x0} -30 L{x0 + w0} -30 L{x0 + w0 - 150} 640 L{x0 - 170} 640 Z" fill="#ffffff" opacity="{op * 0.45}"/>')
    if fish:                                                     # a pastel school far away
        for fx, fy, fs, fc in ((92, 188, 1.0, P["fish1"]), (130, 214, 0.8, P["fish2"]), (62, 232, 0.7, P["fish1"]), (668, 120, 0.9, P["fish2"]), (708, 146, 0.7, P["fish1"])):
            o.append(f'<g transform="translate({fx} {fy}) scale({fs})" opacity="0.8"><ellipse cx="0" cy="0" rx="17" ry="9" fill="{fc}"/>'
                     f'<path d="M-14 0 L-29 -9 L-29 9 Z" fill="{fc}"/><circle cx="8" cy="-2" r="2.2" fill="#ffffff"/><circle cx="8.4" cy="-2" r="1.1" fill="{P["lash"]}"/></g>')
    o.append(f'<path d="M0 590 C140 540 280 560 420 590 C560 620 680 560 800 574 L800 700 L0 700 Z" fill="{P["sand2"]}" opacity="0.8"/>')
    o.append(f'<path d="M0 626 C150 598 310 620 450 626 C590 632 700 604 800 618 L800 700 L0 700 Z" fill="{P["sand"]}"/>')
    for rx_, ry_, rw, rh, rc in ((250, 640, 54, 30, P["rock"]), (572, 646, 44, 24, P["rock2"])):
        o.append(f'<ellipse cx="{rx_}" cy="{ry_}" rx="{rw}" ry="{rh}" fill="{rc}"/>')
        o.append(D.blob(rx_ - rw * 0.25, ry_ - rh * 0.5, rw * 0.6, rh * 0.4, "#ffffff", 0.7))
    for sxx, sh, c in ((60, 220, P["weed1"]), (96, 160, P["weed2"]), (720, 250, P["weed2"]), (756, 170, P["weed1"]), (690, 130, P["weed1"])):
        for j, off in enumerate((-10, 0, 12)):
            curve = [(sxx + off + 14 * math.sin(i * 0.7 + j), 640 - sh * (0.8 + 0.1 * j) * i / 14) for i in range(15)]
            o.append(f'<path d="{ribbon(curve, [20 - 16 * (i / 14) ** 1.1 for i in range(15)])}" fill="{c}" opacity="{0.8 - j * 0.1}"/>')
    # kelp with leaf blades
    for kx, kh in ((24, 300), (780, 330)):
        stalk = [(kx + 10 * math.sin(i * 0.5), 650 - kh * i / 16) for i in range(17)]
        o.append(f'<path d="{ribbon(stalk, [9 - 5 * i / 16 for i in range(17)])}" fill="{P["weed1"]}" opacity="0.9"/>')
        for i in range(2, 16, 3):
            for side in (-1, 1):
                leaf = hair_curve(stalk[i], 180 if side < 0 else 0, 46, 6, i, -20, 10)
                o.append(f'<path d="{ribbon(leaf, [2 + 12 * math.sin(math.pi * j / 10) for j in range(11)])}" fill="{P["weed2"]}" opacity="0.9"/>')
    # branching coral with polyps
    for cx, cc in ((610, P["coral1"]), (150, P["coral2"])):
        for ang, ln in ((-100, 70), (-70, 56), (-125, 50), (-90, 96)):
            c = hair_curve((cx, 636), ang, ln, 6, cx * 0.01, 0, 12)
            o.append(f'<path d="{ribbon(c, [16 - 10 * (i / 12) for i in range(13)])}" fill="{cc}"/>')
            o.append(f'<circle cx="{c[-1][0]:.1f}" cy="{c[-1][1]:.1f}" r="8" fill="{cc}"/>')
            o.append(f'<circle cx="{c[-1][0]:.1f}" cy="{c[-1][1]:.1f}" r="3.2" fill="#ffffff" opacity="0.7"/>')
    for sxx, syy, r, c in ((396, 672, 20, P["starfish"]), (200, 668, 14, P["starfish"])):          # starfish
        pts = []
        for i in range(10):
            a = -math.pi / 2 + i * math.pi / 5
            rr = r if i % 2 == 0 else r * 0.45
            pts.append((sxx + rr * math.cos(a), syy + rr * math.sin(a)))
        o.append(f'<path d="M{pts[0][0]:.1f} {pts[0][1]:.1f}' + "".join(f"L{x:.1f} {y:.1f}" for x, y in pts[1:]) + f'Z" fill="{c}" stroke="{c}" stroke-width="5" stroke-linejoin="round"/>')
        o.append(f'<circle cx="{sxx}" cy="{syy}" r="{r * 0.16:.1f}" fill="#ffffff" opacity="0.7"/>')
    for sxx, syy, r in ((300, 662, 14), (480, 672, 11), (230, 686, 9)):                              # shells
        o.append(f'<path d="M{sxx - r} {syy} A{r} {r} 0 0 1 {sxx + r} {syy} Z" fill="{P["shell"]}"/>')
        for k in range(-2, 3):
            o.append(f'<path d="M{sxx} {syy} L{sxx + k * r * 0.45:.1f} {syy - r * 0.95:.1f}" stroke="{P["sand2"]}" stroke-width="1.6" opacity="0.6"/>')
    for px, py, pr in ((200, 80, 2.4), (330, 40, 1.8), (560, 70, 2.2), (440, 20, 1.6), (740, 260, 2.2), (30, 400, 2.0), (770, 470, 2.4), (350, 300, 1.6), (120, 470, 2.0)):
        o.append(f'<circle cx="{px}" cy="{py}" r="{pr}" fill="#ffffff" opacity="0.7"/>')
    o.append(D.blob(glow[0], glow[1], 230, 280, "#ffffff", 0.32))
    return o


def crest_locks(D, f_sn, back=True):
    """Flowing crest in head-local coordinates. Back row: long locks that rise from the crown, arch back and
    fall behind the neck (the same hair the front view shows falling down both sides of the head).
    Front row: a few short locks swept back over the top of the head."""
    out = []
    if back:
        roots = ((34, -52), (14, -60), (-6, -62), (-22, -56), (-36, -46), (-44, -34))
        for q in range(len(roots) - 1, -1, -1):                       # rear locks first, front locks on top
            rx_, ry_ = roots[q]
            ex, ey = -66 - 15 * q, 36 + 24 * q
            c = bez((rx_, ry_), (rx_ + 22 - 5 * q, ry_ - 72), (ex + 74, ey - 118 - 4 * q), (ex, ey), 20)
            c = [(x + 8 * math.sin(i * 0.5 + q * 1.3) * (i / 20), y) for i, (x, y) in enumerate(c)]
            out.append(D.lock(c, 50 - 3 * q, (q + 1) % 3))
            if q % 2 == 0:
                out.append(D.strand([(x + 1, y - 2) for x, y in c[3:17]], 2.2, 0.55))
    else:
        for q, (rx_, ry_, ang, ln, w) in enumerate(((-4, -60, -150, 70, 26), (20, -58, -132, 64, 24), (40, -50, -112, 54, 22))):
            c = hair_curve((rx_, ry_ + 4), ang, ln, 6, q * 1.3 + 0.5, 34, 16)
            out.append(D.lock(c, w, q % 3))
    return "".join(out)


# ------------------------------------------------------------------ side views
def build(P, pose_name="idle", traits=None, uid="s", view=None, scene=True):
    traits = dict(dict(fin="veil", ridge=True, crest=True, pattern=None, snout="normal", tail="plain"), **(traits or {}))
    pose = POSES[pose_name]
    f_sn = SNOUT[traits["snout"]]
    D = Doc(P, uid)
    blob = D.blob
    cy0, cy1 = pose["coat_y"]
    D.base((cy0, cy1))

    hx, hy, hang, hs = pose["head"]
    head_t = f"translate({hx} {hy}) rotate({hang}) scale({hs})"

    def to_local(x, y):
        a = -math.radians(hang)
        lx, ly = x - hx, y - hy
        return ((lx * math.cos(a) - ly * math.sin(a)) / hs, (lx * math.sin(a) + ly * math.cos(a)) / hs)
    g0, g1 = to_local(0, cy0), to_local(0, cy1)
    D.lg("coath", P["coat"], g0[0], g0[1], g1[0], g1[1], units=True)

    head_pts = [(sx(x, f_sn), y) for x, y in HEAD_PTS]
    ctrl = pose["spine"]
    dense = spl(ctrl, K)
    nrm = normals([(p[0], p[1]) for p in dense])      # points toward the back (the side away from the belly)
    tan = tangents([(p[0], p[1]) for p in dense])
    body_end = pose["tail_from"] * K
    spine_d = limb(ctrl, K)
    bx_, by_, brx, bry, brot = pose["belly"]
    belly_d = closed(ellipse_pts(bx_, by_, brx, bry, brot))
    D.defs.append(f'<clipPath id="{uid}coatclip"><path d="{spine_d}{belly_d}"/></clipPath>')
    D.defs.append(f'<clipPath id="{uid}headclip"><path d="{closed(head_pts)}"/></clipPath>')

    vb = view or f"0 -30 {W} {H + 30}"
    s = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{vb}" role="img" aria-label="{P["label"]}">']
    o = []
    if scene:
        hxm = sum(p[0] for p in ctrl) / len(ctrl)
        hym = sum(p[1] for p in ctrl) / len(ctrl)
        o.extend(draw_scene(D, (hxm, hym - 30)))

    def spine_fan(c_from, c_to, nr, length, spread, sweep, flutter):
        items = []
        for q in range(nr):
            u = q / (nr - 1)
            k = min(len(dense) - 1, int((c_from + (c_to - c_from) * u) * K))
            p, n, t = dense[k], nrm[k], tan[k]
            root = (p[0] + n[0] * p[2] * 0.30, p[1] + n[1] * p[2] * 0.30)
            phi = math.radians(-spread + 2 * spread * u + sweep)
            d = (n[0] * math.cos(phi) + t[0] * math.sin(phi), n[1] * math.cos(phi) + t[1] * math.sin(phi))
            L = length * (0.72 + 0.28 * math.sin(u * math.pi))
            items.append((root, math.degrees(math.atan2(d[1], d[0])), L, flutter * (1 if q % 2 else -1), q * 0.8))
        return items

    # --- tail fin (behind the tail curl)
    if traits["tail"] == "fin":
        tip, tt = dense[-1], tan[-1]
        base_ang = math.degrees(math.atan2(tt[1], tt[0]))
        o.append(D.fin_at((tip[0], tip[1]), base_ang, 62, 78, 7, 5, 0.85))

    # --- back ridge: small curved spikes down the neck and back
    if traits["ridge"]:
        r0, r1 = pose["ridge"]
        for q in range(11):
            u = q / 10
            k = int((r0 + (r1 - r0) * u) * K)
            p, n, t = dense[k], nrm[k], tan[k]
            root = (p[0] + n[0] * p[2] * 0.34, p[1] + n[1] * p[2] * 0.34)
            phi = math.radians(-34)
            d = (n[0] * math.cos(phi) + t[0] * math.sin(phi), n[1] * math.cos(phi) + t[1] * math.sin(phi))
            ang = math.degrees(math.atan2(d[1], d[0]))
            o.append(D.lock(hair_curve(root, ang, 44 + 16 * math.sin(u * math.pi), 5, q * 1.3, 10, 14), 20, q % 3))

    # --- dorsal fin (behind the body)
    d0, d1 = pose["dorsal"]
    if traits["fin"] == "veil":
        o.append(D.fan(spine_fan(d0, d1, 15, pose.get("fin_len", 96), 16, 32, 3), 0.94, 0.5, base=True))
    elif traits["fin"] == "small":
        o.append(D.fan(spine_fan(d0 + 0.5, d1 - 0.5, 6, 70, 30, 20, 4), 0.84, 0.44, base=True))

    # --- crest, back row (behind the head)
    if traits["crest"]:
        o.append(f'<g transform="{head_t}">{crest_locks(D, f_sn, True)}</g>')

    # --- body: spine ribbon (neck, belly, tail) + belly bump, one fill
    o.append(f'<g fill="url(#{uid}coat)"><path d="{spine_d}"/><path d="{belly_d}"/></g>')
    sh = P["shade"]
    ov = [f'<g clip-path="url(#{uid}coatclip)">']
    # smooth bands along the body: cream belly on the front edge, shade down the back, each built from stacked widths
    k0, k1 = K, body_end
    seg = dense[k0:k1 + 1]
    sn = nrm[k0:k1 + 1]
    n_seg = len(seg)

    def taper(i):
        return min(1.0, i / 26, (n_seg - 1 - i) / 26) ** 1.3

    for off, wf, col, op in ((0.30, 0.62, P["belly"], 0.34), (0.30, 0.42, P["belly"], 0.34), (0.30, 0.24, P["belly"], 0.34)):
        front = [(p[0] - n[0] * p[2] * off, p[1] - n[1] * p[2] * off) for p, n in zip(seg, sn)]
        ov.append(f'<path d="{ribbon(front, [p[2] * wf * taper(i) + 0.1 for i, p in enumerate(seg)])}" fill="{col}" opacity="{op}"/>')
    for off, wf, op in ((0.40, 0.42, 0.28), (0.44, 0.24, 0.30)):
        back = [(p[0] + n[0] * p[2] * off, p[1] + n[1] * p[2] * off) for p, n in zip(seg, sn)]
        ov.append(f'<path d="{ribbon(back, [p[2] * wf * taper(i) + 0.1 for i, p in enumerate(seg)])}" fill="{sh}" opacity="{op}"/>')
    ov.append(blob(bx_ + brx * 0.1, by_, brx * 0.7, bry * 0.8, P["belly"], 0.55, brot))
    ov.append(blob(bx_ - brx * 0.1, by_ - bry * 0.55, brx * 0.6, 12, P["hi"], 0.7, brot))
    for k in range(body_end, len(dense) - 4, 5):                                          # shade on the inside of the tail curl
        p, n = dense[k], nrm[k]
        ov.append(blob(p[0] + n[0] * p[2] * 0.3, p[1] + n[1] * p[2] * 0.3, p[2] * 0.4, p[2] * 0.4, sh, 0.5))
    ring_c = mixhex(P["ring"], sh, 0.2)
    ring_to = int(pose["ring_to"] * K)
    for j, k in enumerate(range(K + 4, ring_to, 5)):
        p, n, t = dense[k], nrm[k], tan[k]
        w = p[2]
        a = (p[0] + n[0] * w * 0.5, p[1] + n[1] * w * 0.5)
        b = (p[0] - n[0] * w * 0.5, p[1] - n[1] * w * 0.5)
        m = (p[0] + t[0] * w * 0.1, p[1] + t[1] * w * 0.1)
        cc = spl([a, m, b], 6)
        ov.append(f'<path d="{ribbon(cc, [4.2 * math.sin(math.pi * i / (len(cc) - 1)) ** 0.7 + 0.2 for i in range(len(cc))])}" fill="{ring_c}" opacity="0.42"/>')
    if traits["pattern"] == "stripes":
        ov.append(D.stripes(dense, K + 10, len(dense) - 10))
    if traits["pattern"] == "stars":
        for k, rr, a in ((3.0, 11, 8), (3.9, 8, -14), (4.6, 12, 20), (5.2, 7, 0)):
            p = dense[int(k * K)]
            ov.append(star(p[0] + 4, p[1], rr, P["mark"], 0.55, a))
    if traits["pattern"] == "spots":
        for k, rr, dxo in ((2.6, 15, 6), (3.3, 12, -10), (4.0, 17, 8), (4.7, 11, -6), (5.3, 9, 4)):
            p = dense[int(k * K)]
            ov.append(blob(p[0] + dxo, p[1], rr, rr * 0.9, P["mark"], 0.4))
    ov.append("</g>")
    o.append("".join(ov))
    o.append(f'<g transform="translate({bx_ + 6:.1f} {by_ + 6:.1f}) rotate(-10)">{star(0, 0, 19, P["mark"], 0.95)}{star(0, 0, 7, "#ffffff", 0.9)}</g>')

    # --- head fill (over the neck join), then the pectoral fin over the body
    o.append(f'<g transform="{head_t}"><path d="{closed(head_pts)}" fill="url(#{uid}coath)"/></g>')
    pc = pose["pect"]
    o.append(D.fin_at(pc["at"], pc["ang"], pc["spread"], pc["length"], 7, 8))

    # --- head details (head-local frame)
    d = [f'<g transform="{head_t}">']
    d.append(f'<g clip-path="url(#{uid}headclip)">')
    d.append(blob(70, 30, 30, 20, P["blush"], P["blush_o"]))
    d.append(blob(sx(96, f_sn), -22, 54 * f_sn ** 0.5, 9, P["hi"], 0.9, 12))
    d.append(blob(sx(106, f_sn), 44, 70 * f_sn ** 0.5, 12, sh, 0.8, 6))
    d.append(blob(-40, 20, 20, 50, sh, 0.45))
    d.append("</g>")
    if traits["crest"]:
        d.append(crest_locks(D, f_sn, False))
    ear = [((-24, -16 + q * 7), -168 + q * 14, 34 - abs(q - 2) * 4, 2, q) for q in range(5)]
    d.append(D.fan(ear, 0.9, 0.4))
    nx_, tipx = sx(148, f_sn), sx(160, f_sn)
    d.append(f'<ellipse cx="{nx_:.1f}" cy="8" rx="5.6" ry="4" fill="{P["nostril"]}" opacity="0.9" transform="rotate(-14 {nx_:.1f} 8)"/>')
    d.append(f'<path d="M{tipx:.1f} 27 C{sx(150, f_sn):.1f} 35 {sx(134, f_sn):.1f} 35 {sx(120, f_sn):.1f} 29" fill="none" stroke="{P["nostril"]}" stroke-width="3" stroke-linecap="round"/>')
    d.append(D.eye(30, -4, 21, 25, ((0.04, 13, -5), (0.2, 10, -3), (0.38, 7, -1)), True, pose["eye"] != "open"))
    for p0, p1, p2, p3, w, idx in (((-6, -58), (24, -80), (62, -64), (58, -34), 26, 1), ((6, -60), (40, -84), (80, -56), (64, -22), 20, 0)):
        d.append(f'<path d="{ribbon(bez(p0, p1, p2, p3, 14), lock_widths(14, w))}" fill="url(#{uid}hair{idx})"/>')
    d.append("</g>")
    o.append("".join(d))

    # --- bubbles and sparkles
    shift = (f_sn - 1) * 100
    bub = [(hx + 190 + shift, hy + 18, 9), (hx + 214 + shift, hy - 14, 6), (hx + 232 + shift, hy - 52, 12), (hx + 206 + shift, hy - 96, 5)]
    if pose.get("zzz"):
        bub = [(hx + 150, hy - 70, 20), (hx + 190, hy - 124, 15), (hx + 218, hy - 166, 11)]
    for bx, by, r in bub:
        o.append(f'<circle cx="{bx}" cy="{by}" r="{r}" fill="#ffffff" fill-opacity="0.25" stroke="#ffffff" stroke-opacity="0.9" stroke-width="2"/>')
        if pose.get("zzz"):
            z = r * 0.45
            o.append(f'<path d="M{bx - z:.1f} {by - z:.1f} L{bx + z:.1f} {by - z:.1f} L{bx - z:.1f} {by + z:.1f} L{bx + z:.1f} {by + z:.1f}" fill="none" stroke="{P["mark"]}" stroke-width="{max(r * 0.16, 1.8):.1f}" stroke-linecap="round" stroke-linejoin="round"/>')
        else:
            o.append(f'<circle cx="{bx - r * 0.35:.1f}" cy="{by - r * 0.35:.1f}" r="{max(r * 0.2, 1.5):.1f}" fill="#ffffff" opacity="0.95"/>')
    for x, y, r, op in ((110, 120, 11, 0.8), (700, 150, 9, 0.8), (640, 60, 7, 0.7), (60, 300, 8, 0.7), (740, 360, 10, 0.7), (180, 520, 7, 0.6)):
        o.append(star(x, y, r, P["spark"], op))
    s.append("<defs>" + "".join(D.defs) + "</defs>")
    s.extend(o)
    s.append("</svg>")
    return "".join(s)


# ------------------------------------------------------------------ front and back views
# Widths come from the side view: neck 60-74, chest 104-116 plus the belly bump, skull about 100-110 deep.
TORSO = [(400, 300, 100), (400, 340, 134), (400, 420, 166), (400, 500, 162), (400, 562, 126), (400, 610, 66), (400, 636, 26), (400, 650, 3)]
TAIL_FRONT = [(402, 604, 40), (436, 638, 30), (478, 650, 23), (508, 630, 17), (498, 604, 12), (478, 604, 7), (474, 620, 3)]
SKULL = (400, 244, 88, 104)           # cx, cy, rx, ry: 176 wide, between the thin (132) and the wide (240) fronts; 105 deep in the side view


def _mirror(svg):
    return f'<g>{svg}<g transform="translate(800 0) scale(-1 1)">{svg}</g></g>'


def _width_at(dense, y):
    return min(dense, key=lambda p: abs(p[1] - y))[2]


def _torso(D, o, traits, back=False):
    uid, P = D.uid, D.P
    torso_d = limb(TORSO, 10)
    dense = spl(TORSO, 10)
    D.defs.append(f'<clipPath id="{uid}torsoclip"><path d="{torso_d}"/></clipPath>')
    o.append(f'<path d="{torso_d}" fill="url(#{uid}coat)"/>')
    ov = [f'<g clip-path="url(#{uid}torsoclip)">']
    if not back:
        for wf, op in ((0.8, 0.3), (0.55, 0.3), (0.3, 0.3)):                      # soft cream belly down the middle
            cen = [(p[0], p[1]) for p in dense]
            ov.append(f'<path d="{ribbon(cen, [p[2] * wf * min(1.0, i / 12, (len(dense) - 1 - i) / 12) ** 0.7 + 0.1 for i, p in enumerate(dense)])}" fill="{P["belly"]}" opacity="{op}"/>')
    for sgn in (-1, 1):
        ov.append(blob_e(D, 400 + sgn * 68, 470, 24, 124, P["shade"], 0.5 if not back else 0.65))
    ov.append(blob_e(D, 400, 352, 96, 18, P["hi"], 0.8))
    ring_c = mixhex(P["ring"], P["shade"], 0.2)
    sag = 16 if not back else -12
    for j, y in enumerate(range(366, 630, 26)):
        half = _width_at(dense, y) * 0.47
        cc = spl([(400 - half, y), (400, y + sag), (400 + half, y)], 6)
        ov.append(f'<path d="{ribbon(cc, [4.4 * math.sin(math.pi * i / (len(cc) - 1)) ** 0.7 + 0.2 for i in range(len(cc))])}" fill="{ring_c}" opacity="0.42"/>')
    if traits.get("pattern") == "stripes":                              # same band size as the side view, arcs bow with the belly
        for j, y in enumerate(range(380, 640, 46)):
            half = _width_at(dense, y) * 0.62
            cc = spl([(400 - half, y), (400, y + sag), (400 + half, y)], 6)
            thick = max(7.0, min(22.0, _width_at(dense, y) * 0.16))
            prof = [0.62 + 0.38 * math.sin(math.pi * i / (len(cc) - 1)) for i in range(len(cc))]
            for mul, op in ((1.9, 0.14), (1.25, 0.2), (0.7, 0.34)):
                ov.append(f'<path d="{ribbon(cc, [thick * mul * q for q in prof])}" fill="{P["mark"]}" opacity="{op}"/>')
    if traits.get("pattern") == "stars":
        for x, y, r, a in ((356, 432, 11, 8), (444, 452, 9, -14), (362, 520, 8, 20), (440, 538, 12, 0)):
            ov.append(star(x, y, r, P["mark"], 0.55, a))
    if traits.get("pattern") == "spots":
        for x, y, r in ((360, 430, 14), (442, 450, 11), (366, 516, 12), (438, 540, 10)):
            ov.append(blob_e(D, x, y, r, r, P["mark"], 0.4))
    ov.append("</g>")
    o.append("".join(ov))


def blob_e(D, cx, cy, rx, ry, color, op, rot=0):
    return D.blob(cx, cy, rx, ry, color, op, rot)


def tail_front_extras(D, o, traits):
    """Tail curl and its tail fin, seen from the front or back (drawn behind the torso)."""
    uid, P = D.uid, D.P
    dense = spl(TAIL_FRONT, 8)
    if traits.get("tail") == "fin":
        tip = dense[-1]
        o.append(D.fin_at((tip[0], tip[1]), -50, 54, 78, 7, 5, 0.85))
    D.defs.append(f'<clipPath id="{uid}tailclip"><path d="{limb(TAIL_FRONT, 8)}"/></clipPath>')
    o.append(f'<path d="{limb(TAIL_FRONT, 8)}" fill="url(#{uid}coat)"/>')
    if traits.get("pattern") == "stripes":
        o.append(f'<g clip-path="url(#{uid}tailclip)">{D.stripes(dense, 6, len(dense) - 8, sag=0.0, reach=0.7)}</g>')


def crest_front(D):
    """Front crest: a tuft on top and long locks that rise, arch and fall down both sides of the head (right half only)."""
    cx0, cy0, rx0, ry0 = SKULL
    out = []
    n = 6
    for q in range(n):                                    # side falls, outer locks first (they sit behind)
        u = (n - 1 - q) / (n - 1)
        th = math.radians(8 + 72 * u)
        rx_, ry_ = cx0 + rx0 * 0.9 * math.sin(th), cy0 - ry0 * 0.9 * math.cos(th)
        ex, ey = cx0 + 100 + 44 * u, 300 + 64 * u
        c = bez((rx_, ry_), (rx_ + 20 + 26 * u, ry_ - 58 + 20 * u), (ex + 26, ey - 120), (ex, ey), 18)
        c = [(x + 7 * math.sin(i * 0.55 + q) * (i / 18), y) for i, (x, y) in enumerate(c)]       # gentle wave
        out.append(D.lock(c, 32 - 2 * q, (q + 1) % 3))
        if q % 2 == 0:
            out.append(D.strand([(x - 2, y) for x, y in c[2:15]], 2.0, 0.5))
    for q, (dx, ang, ln, w) in enumerate(((0, -90, 76, 26), (14, -78, 72, 24), (30, -62, 64, 22))):   # tuft on top
        c = hair_curve((cx0 + dx, cy0 - ry0 + 14), ang, ln, 7, q * 1.2, 26, 16)
        out.append(D.lock(c, w, q % 3))
    return "".join(out)


def portrait(P, uid="sp", traits=None):
    """Front view: symmetrical shapes written out directly, right-hand details mirrored."""
    traits = dict(dict(fin="veil", crest=True, pattern=None, tail="plain"), **(traits or {}))
    D = Doc(P, uid)
    D.base((150, 660))
    o = draw_scene(D, (400, 360))
    lock, fan = D.lock, D.fan
    cx0, cy0, rx0, ry0 = SKULL
    # dorsal fin seen end-on: a slim collar behind the head and shoulders
    if traits["fin"] != "none":
        L0 = 150 if traits["fin"] == "veil" else 100
        items = [((400.0, 330.0), -90.0, L0, 0.0, 0.0)] + [((400 + (q - 6) * 7, 330), -194 + 208 * q / 12, L0 * (0.9 - 0.3 * (q - 6) / 6) + (8 if q % 2 else 0), 5 * (1 if q % 2 else -1), q * 0.7) for q in range(7, 13)]
        o.append(_mirror(fan(items, 0.8, 0.4)))
    if traits["crest"]:
        o.append(_mirror(crest_front(D)))
    tail_front_extras(D, o, traits)
    _torso(D, o, traits)
    o.append(f'<g transform="translate(400 468)">{star(0, 0, 22, P["mark"], 0.95)}{star(0, 0, 8, "#ffffff", 0.9)}</g>')
    # pectoral fins out to the sides, level with the chest
    o.append(_mirror(D.fin_at((476, 384), 12, 30, 104, 7, 8)))
    # head: skull, then the snout seen end-on
    skull = ellipse_pts(cx0, cy0, rx0, ry0, 0, 20)
    D.defs.append(f'<clipPath id="{uid}skullclip"><path d="{closed(skull)}"/></clipPath>')
    o.append(f'<path d="{closed(skull)}" fill="url(#{uid}coat)"/>')
    o.append(f'<g clip-path="url(#{uid}skullclip)">' + D.blob(400, 150, 80, 12, P["hi"], 0.9) + D.blob(400, 342, 100, 16, P["shade"], 0.7)
             + _mirror(D.blob(460, 290, 26, 16, P["blush"], P["blush_o"])) + _mirror(D.blob(480, 230, 18, 84, P["shade"], 0.45)) + "</g>")
    o.append(f'<path d="{closed(ellipse_pts(400, 312, 40, 44, 0, 18))}" fill="url(#{uid}coat)"/>')
    o.append(D.blob(400, 296, 28, 14, P["hi"], 0.9))
    o.append(D.blob(400, 344, 38, 10, P["shade"], 0.55))
    o.append(_mirror(f'<ellipse cx="413" cy="308" rx="5" ry="7" fill="{P["nostril"]}" opacity="0.85"/>'))
    o.append(f'<path d="M380 338 C391 351 409 351 420 338" fill="none" stroke="{P["nostril"]}" stroke-width="3.2" stroke-linecap="round"/>')
    ear = [((478 + q * 2, 204 + q * 9), -30 + q * 22, 38 - abs(q - 2) * 5, 2, q) for q in range(5)]
    o.append(_mirror(fan(ear, 0.9, 0.4)))
    o.append(_mirror(D.eye(450, 240, 20, 26, ((0.9, 13, 5), (0.76, 10, 3), (0.6, 7, 1)), side=False)))
    o.append(_mirror(lock(bez((404, 150), (434, 126), (478, 148), (480, 198), 14), 28, 1)))
    o.append(_mirror(lock(bez((404, 156), (428, 140), (456, 168), (456, 212), 14), 20, 0)))
    for x, y, r, op in ((100, 110, 12, 0.85), (700, 130, 9, 0.8), (150, 300, 8, 0.7), (660, 330, 10, 0.7)):
        o.append(star(x, y, r, P["spark"], op))
    for bx, by, r in ((590, 410, 9), (612, 380, 6), (630, 330, 12)):
        o.append(f'<circle cx="{bx}" cy="{by}" r="{r}" fill="#ffffff" fill-opacity="0.25" stroke="#ffffff" stroke-opacity="0.9" stroke-width="2"/>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -30 {W} {H + 30}" role="img" aria-label="{P["label"]}, front view">'
            + "<defs>" + "".join(D.defs) + "</defs>" + "".join(o) + "</svg>")


def mane_back(D):
    """Back crest: the front view's locks seen from behind. They start at a parting on the crown and fall over both
    sides of the skull and down onto the shoulders (right half only)."""
    cx0, cy0, rx0, ry0 = SKULL
    out = []
    n = 6
    for q in range(n):                                    # outer locks first
        u = (n - 1 - q) / (n - 1)
        th = math.radians(10 + 66 * u)
        rx_, ry_ = cx0 + rx0 * 0.92 * math.sin(th), cy0 - ry0 * 0.92 * math.cos(th)
        ex, ey = cx0 + 16 + 118 * u, 318 + 82 * u
        c = bez((cx0 + 6 + 10 * u, cy0 - ry0 + 6), (rx_ + 30, ry_ - 6), (ex + 18, ey - 100), (ex, ey), 18)
        c = [(x + 6 * math.sin(i * 0.55 + q) * (i / 18), y) for i, (x, y) in enumerate(c)]
        out.append(D.lock(c, 34 - 2 * q, (q + 1) % 3))
        if q % 2 == 0:
            out.append(D.strand([(x - 3, y) for x, y in c[2:15]], 2.0, 0.5))
    centre = []                                           # the middle of the back of the head, drawn first so the side locks lie over it
    for q, (dx, ang, ln, w) in enumerate(((0, 90, 196, 58), (16, 83, 176, 46))):
        centre.append(D.lock(hair_curve((cx0 + dx, cy0 - ry0 + 8), ang, ln, 6, q * 1.4, 4, 18), w, q))
    out = centre + out
    for q, (dx, ang, ln, w) in enumerate(((0, -90, 70, 24), (14, -76, 66, 22))):          # little tuft peeking over the crown
        out.append(D.lock(hair_curve((cx0 + dx, cy0 - ry0 + 14), ang, ln, 6, q * 1.2, 26, 16), w, q % 3))
    return "".join(out)


def portrait_back(P, uid="sb", traits=None):
    """Back view: the mane hangs over the nape, the dorsal fin runs down the spine as a ruffle."""
    traits = dict(dict(fin="veil", crest=True, pattern=None, tail="plain"), **(traits or {}))
    D = Doc(P, uid)
    D.base((150, 660))
    o = draw_scene(D, (400, 360), fish=True)
    lock, fan = D.lock, D.fan
    cx0, cy0, rx0, ry0 = SKULL
    tail_front_extras(D, o, traits)
    _torso(D, o, traits, back=True)
    # pectoral fins peeking out from behind the chest
    o.append(_mirror(D.fin_at((476, 396), 26, 30, 96, 7, 8)))
    # dorsal fin as a ruffle down the spine, over the torso
    if traits["fin"] != "none":
        ruff = []
        n_r = 7 if traits["fin"] == "veil" else 5
        for q in range(n_r):
            y = 370 + q * (190 / n_r)
            L = (74 if traits["fin"] == "veil" else 46) * (0.8 + 0.2 * math.sin(q / n_r * math.pi))
            items = [((400 + 4, y + j * 3), 14 + j * 12 - 12, L, 3 * (1 if j % 2 else -1), j) for j in range(3)]
            ruff.append(fan(items, 0.85, 0.4))
        o.append(_mirror("".join(ruff)))
        for q in range(8):                                      # ridge plates down the centre
            y = 366 + q * 26
            o.append(f'<path d="M400 {y - 12} C408 {y - 6} 408 {y + 6} 400 {y + 12} C392 {y + 6} 392 {y - 6} 400 {y - 12} Z" fill="url(#{uid}hair{q % 3})" opacity="0.9"/>')
    # skull from behind
    skull = ellipse_pts(cx0, cy0, rx0, ry0, 0, 20)
    D.defs.append(f'<clipPath id="{uid}skullclip"><path d="{closed(skull)}"/></clipPath>')
    o.append(f'<path d="{closed(skull)}" fill="url(#{uid}coat)"/>')
    o.append(f'<g clip-path="url(#{uid}skullclip)">' + _mirror(D.blob(480, 250, 22, 92, P["shade"], 0.6)) + D.blob(400, 160, 70, 12, P["hi"], 0.8) + "</g>")
    ear = [((478 + q * 2, 200 + q * 9), -34 + q * 24, 38 - abs(q - 2) * 5, 2, q) for q in range(5)]
    o.append(_mirror(fan(ear, 0.9, 0.4)))
    if traits["crest"]:
        o.append(_mirror(mane_back(D)))
    for x, y, r, op in ((100, 110, 12, 0.85), (700, 130, 9, 0.8), (150, 300, 8, 0.7), (660, 330, 10, 0.7)):
        o.append(star(x, y, r, P["spark"], op))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 -30 {W} {H + 30}" role="img" aria-label="{P["label"]}, back view">'
            + "<defs>" + "".join(D.defs) + "</defs>" + "".join(o) + "</svg>")


# ------------------------------------------------------------------ palettes
pastel = dict(
    label="Soft pastel sea-horse",
    bg=[(0, "#d4f0f8"), (0.5, "#e1e5fa"), (0.85, "#f9e5ee"), (1, "#fdefdc")],
    sand="#f6e4cc", sand2="#f0d8bf", weed1="#a9dcc4", weed2="#c6ead8", coral1="#ffb9d0", coral2="#ffd3a8", shell="#fff3e6",
    rock="#d6cdee", rock2="#cfe0ee", starfish="#ffb5a7", fish1="#ffd0a8", fish2="#d9c4f7",
    coat=[(0, "#fffbea"), (0.45, "#d9f4ee"), (1, "#a9d9ee")],
    belly="#fff6e0", shade="#9fcfe3", hi="#ffffff", ring="#6fb8d6", mark="#b99af2", spark="#fff3a8",
    fin_g=[(0, "#ffe3f1"), (0.6, "#ead0f9"), (1, "#bda8f6")], ray="#a98adf",
    hair=[[(0, "#fff0c4"), (0.5, "#ffc98a"), (1, "#f79fb0")], [(0, "#ffe0f2"), (0.55, "#f4a8d6"), (1, "#c58cf0")],
          [(0, "#e0f6ff"), (0.55, "#a8d4f6"), (1, "#8cb0ee")]],
    iris_g=[(0, "#b8f0e8"), (0.5, "#3fb0c0"), (1, "#1c5a78")], pupil="#10304a", eye_white="#ffffff", lash="#2a3a6e",
    lid_shadow="#4a8ac4", nostril="#c47a9a", blush="#ff9fc0", blush_o=0.8, seed=3)


def variant(base, **kw):
    d = dict(base)
    d.update(kw)
    return d


ROSE = dict(
    coat=[(0, "#fffaf6"), (0.45, "#ffe6ee"), (1, "#f4bfd6")], shade="#eab0cc", belly="#fff7ea", ring="#d98fb0", mark="#ffd36b",
    fin_g=[(0, "#fff2c8"), (0.6, "#ffd6a0"), (1, "#f7a8b8")], ray="#e08aa0",
    hair=[[(0, "#e4f7ff"), (0.5, "#9fd6f2"), (1, "#5fa8e0")], [(0, "#e6e4ff"), (0.55, "#b4a8f6"), (1, "#8a78e0")],
          [(0, "#dcfbf0"), (0.55, "#9fe3c4"), (1, "#5cc09a")]],
    iris_g=[(0, "#ffd0e0"), (0.5, "#e06a9a"), (1, "#7a2050")], pupil="#2a0f20", lash="#6a2a4e", lid_shadow="#c9559b", blush="#ff8fa8")
LILAC = dict(
    coat=[(0, "#fbf8ff"), (0.45, "#e7defb"), (1, "#c3b4ee")], shade="#bcaee8", belly="#fffaf0", ring="#9d86d8", mark="#7fd6e8",
    fin_g=[(0, "#e0fbff"), (0.6, "#a8e6f2"), (1, "#74c6e0")], ray="#4aa6c8",
    hair=[[(0, "#fff0c4"), (0.5, "#ffd36b"), (1, "#f0a640")], [(0, "#ffe0ea"), (0.55, "#ffa8c0"), (1, "#e8728e")],
          [(0, "#fff6d0"), (0.55, "#ffe08a"), (1, "#f2bc48")]],
    iris_g=[(0, "#d6c8ff"), (0.5, "#7a5fe0"), (1, "#3a2984")], pupil="#1c1244", lash="#3a2a6e", lid_shadow="#7b5fc4")


# One style for every view: same palette, same trait set, so the views can be compared with each other.
STYLE = dict(fin="veil", ridge=True, crest=True, tail="fin", snout="normal", pattern="stripes")


def main(out):
    P = pastel
    files = {name: build(P, name, STYLE, uid=name + "s") for name in ("idle", "swim", "sleep")}
    files["front"] = portrait(P, "sp", STYLE)
    files["back"] = portrait_back(P, "sb", STYLE)
    for name, svg in files.items():
        with open(os.path.join(out, f"{name}.svg"), "w", encoding="utf-8") as fh:
            fh.write(svg)
    print("ok")


if __name__ == "__main__":
    main(sys.argv[1])
