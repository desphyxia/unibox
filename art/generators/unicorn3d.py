"""Unicorn as one 3D model, rendered from any camera (Blender, headless). Same idea as seahorse3d.py.

The pose numbers (body outline, neck curves, four leg chains, head placement, wing arm, tail) are the ones from
artgen5.py, the 2D unicorn. Here they become geometry: a lofted torso, neck and head, tapered leg tubes with hooves,
a spiral horn, ears, hair locks for mane, tail and forelock, and feathered wings. Hair and wings are projected onto the
body surface, so they hug the animal from every side. Every view is just a camera.

Usage: blender -b -P unicorn3d.py -- OUTDIR [--quick] [pose:view ...]
       poses: stand walk sleep      views: side three front back
"""
import bpy, bmesh, math, os, sys, random, re
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import artgen5 as A
import seahorse3d as K
from seahorse3d import srgb, lin, mix, smooth, grad, add_object, loft, ellipsoid, tube, bezier, material

_RAW_ADD = add_object
_CAPTURE = []                                              # while a list is on this stack, every new object is also put in it


def add_object(*a, **k):
    ob = _RAW_ADD(*a, **k)
    if _CAPTURE:
        _CAPTURE[-1].append(ob)
    return ob


S = 0.01
Y = Vector((0, 1, 0))
NEAR = -1                                                  # the side the camera sees in the side and three-quarter views; the mane falls over it
GROUND_Z = 0.42
TRAITS = dict(wings=False, flowers=True)

# palette inspired by the round-11 reference: aqua-white coat fading to lavender legs, pink-to-peach mane, pearl horn, dark blue eyes
BLOOM = A.variant(
    A.pastel, label="Bloom unicorn",
    coat=[(0, "#f1fafc"), (0.35, "#dcf0f6"), (0.7, "#cad6f2"), (1, "#ad97df")],
    shade="#b3b8e8", blush="#ff9db6", blush_o=0.85, ear_in="#f9cadd",
    horn_g=[(0, "#fffaf1"), (0.55, "#f7e5d6"), (1, "#e8c7b3")], horn_line="#d9a58b", glow="#fff3dc",
    hoof_g=[(0, "#e2e6f2"), (1, "#8f9bbf")],
    hair=[[(0, "#ffdbe8"), (0.5, "#f6b3cf"), (1, "#e8a2cc")],
          [(0, "#ffe6d2"), (0.5, "#fcc5b5"), (1, "#f2a3b8")],
          [(0, "#f7d3f1"), (0.5, "#dba8ec"), (1, "#b78fe2")]],
    wing=[(0, "#ffffff"), (0.5, "#fdebf4"), (1, "#e3c3f2")], wing_cov="#fff4f9", wing_edge="#cf9fe4",
    iris_g=[(0, "#7f96e2"), (0.5, "#33449f"), (1, "#161b58")], pupil="#0a0e30", lash="#231d4f", nostril="#c07c9d", mark="#c9a6f7",
    petal_a="#ffcf94", petal_b="#f6a6c9", petal_c="#ffe3b0", leaf_a="#cfe9bd", leaf_b="#9fd3a6")


def chibify(name):
    """The round-11 proportions from the flat rig's pose numbers: shorter, rounder body with a deeper chest, shorter legs,
    a thicker neck and a bigger head. Returns (pose, torso outline)."""
    import copy
    pose = copy.deepcopy(A.POSES["walk" if name == "prance" else name])
    if name == "prance":                                       # proud pose: one foreleg lifted high, the lower leg folded back
        pose["near"]["nf"] = [(492, 402, 70), (540, 424, 52), (596, 432, 40), (602, 470, 27), (598, 504, 25), (600, 520, 22)]
        pose["head"] = (pose["head"][0] + 2, pose["head"][1] - 2, -2, pose["head"][3])
    lying = pose["dy"] >= 100
    tx = lambda x: 540 - (540 - x) * 0.84
    ty = lambda y: y if y <= 330 else 330 + (y - 330) * 1.10
    Y0 = ty(466)

    def tl(p):                                              # leg points: (x, y, width)
        x, y, w = p
        if lying:
            return (tx(x), y, w * 1.25)
        return (tx(x), (ty(y) if y <= 466 else Y0 + (y - 466) * 0.86), w * 1.28)
    for grp in ("near", "far"):
        pose[grp] = {k: [tl(p) for p in v] for k, v in pose[grp].items()}
    body = [(tx(x), ty(y)) for x, y in A.BODY_STAND]
    pose["crest"] = [(tx(x), ty(y)) for x, y in pose["crest"]]
    pose["throat"] = [(tx(x), ty(y)) for x, y in pose["throat"]]
    if not lying:                                           # the neck is thicker where it meets the head
        pose["throat"][2] = (pose["throat"][2][0] + 4, pose["throat"][2][1] + 8)
        pose["throat"][3] = (pose["throat"][3][0] + 8, pose["throat"][3][1] + 26)
    hx, hy, ha, hs = pose["head"]
    pose["head"] = (tx(hx), ty(hy), ha + (0 if lying else 3), hs * 1.2)
    pose["yaw"], pose["roll"] = (-4, 0) if lying else (-9, 3)
    t = pose["tail"]
    pose["tail"] = dict(t, root=(tx(t["root"][0]), ty(t["root"][1])), length=t["length"] * 0.95)
    if lying:
        pose["dy"] -= 8                                       # the deeper belly would sink into the ground
    return pose, body


def P3(x, y, lat=0.0):
    return Vector(((x - 400) * S, lat * S, (640 - y) * S))


def D3(dx, dy):
    return Vector((dx, 0.0, -dy))


# ------------------------------------------------------------------ outlines
def closed_poly(pts, per=14):
    n = len(pts)
    poly = []
    for i in range(n):
        p0, p1, p2, p3 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
        c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
        c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
        for k in range(per):
            t = k / per
            a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
            poly.append((a * p1[0] + b * c1[0] + c * c2[0] + d * p2[0], a * p1[1] + b * c1[1] + c * c2[1] + d * p2[1]))
    return poly


def path_poly(d, per=14):
    """sample an absolute SVG path made of M, C, L, Z"""
    tok = re.findall(r"[MCLZ]|-?\d+(?:\.\d+)?", d)
    pts, cur, cmd, i = [], None, None, 0
    while i < len(tok):
        t = tok[i]
        if t in "MCLZ":
            cmd = t
            i += 1
            continue
        if cmd in ("M", "L"):
            cur = (float(tok[i]), float(tok[i + 1]))
            pts.append(cur)
            i += 2
        elif cmd == "C":
            q = [float(v) for v in tok[i:i + 6]]
            p0, p1, p2, p3 = cur, (q[0], q[1]), (q[2], q[3]), (q[4], q[5])
            for k in range(1, per + 1):
                u = k / per
                a, b, c, e = (1 - u) ** 3, 3 * (1 - u) ** 2 * u, 3 * (1 - u) * u * u, u ** 3
                pts.append((a * p0[0] + b * p1[0] + c * p2[0] + e * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + e * p3[1]))
            cur = p3
            i += 6
    return pts


def slice_at(poly, x):
    ys = []
    for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
        if (x0 - x) * (x1 - x) <= 0 and x0 != x1:
            ys.append(y0 + (y1 - y0) * (x - x0) / (x1 - x0))
    return (min(ys), max(ys)) if ys else (0, 0)


def loft_rings(specs, segs, colfn):
    """specs: (centre, axis a, radius a, axis b, radius b) per ring. Returns verts, faces, colours, ring list."""
    rings, cols = [], []
    for i, (c, a, ra, b, rb) in enumerate(specs):
        ring, cc = [], []
        for k in range(segs):
            th = 2 * math.pi * k / segs
            p = c + a * (ra * math.cos(th)) + b * (rb * math.sin(th))
            ring.append(p)
            cc.append(lin(colfn(i, th, p)))
        rings.append(ring)
        cols.append(cc)
    verts, faces = loft(rings)
    flat = [c for r in cols for c in r]
    for end in (0, len(rings) - 1):
        cen = sum((v for v in rings[end]), Vector()) / segs
        idx = len(verts)
        verts.append(cen)
        flat.append(cols[end][0])
        for k in range(segs):
            k2 = (k + 1) % segs
            faces.append((idx, end * segs + k2, end * segs + k) if end == 0 else (idx, end * segs + k, end * segs + k2))
    return verts, faces, flat


def smooth_list(v, w=3, passes=2):
    """moving average, keeping the ends"""
    for _ in range(passes):
        out = []
        for i in range(len(v)):
            lo, hi = max(0, i - w), min(len(v), i + w + 1)
            out.append(sum(v[lo:hi]) / (hi - lo))
        v = out
    return v


def smooth_over(raw, w=3, passes=2):
    """smoothed profile that never dips more than a little below the raw one (so the body cannot poke through)"""
    sm = smooth_list(raw, w, passes)
    return [m + 0.85 * max(0.0, r - m) for m, r in zip(sm, raw)]


def tangents2d(pts):
    out = []
    for i in range(len(pts)):
        a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
        L = math.hypot(b[0] - a[0], b[1] - a[1]) or 1
        out.append(((b[0] - a[0]) / L, (b[1] - a[1]) / L))
    return out


# ------------------------------------------------------------------ the creature
class Uni3D:
    def __init__(self, P, pose_name, traits):
        self.P, self.traits = P, traits
        self.pose, self.body_pts = chibify(pose_name)
        self.dy = self.pose["dy"]
        self.rnd = random.Random(P.get("seed", 5))
        m = lambda n, **kw: material(n, **kw)
        self.mat_coat = m("coat", rough=0.62, sss=0.25, spec=0.25)
        self.mat_hair = m("hair", rough=0.45, sss=0.1, spec=0.3, sheen=0.4)
        self.mat_wing = m("wing", rough=0.5, sss=0.25, spec=0.2, sheen=0.3)
        self.mat_horn = m("horn", rough=0.3, sss=0.1, spec=0.6)
        self.mat_hoof = m("hoof", rough=0.22, spec=0.8)
        self.mat_dark = m("dark", rough=0.35, vc=False, color=srgb(P["lash"]), spec=0.5)
        self.mat_iris = m("iris", rough=0.2, vc=False, color=srgb(P["iris_g"][1][1]), spec=0.6)
        self.mat_iris2 = m("iris2", rough=0.2, vc=False, color=srgb(P["iris_g"][0][1]), spec=0.6)
        self.mat_pupil = m("pupil", rough=0.2, vc=False, color=srgb(P["pupil"]), spec=0.6)
        self.mat_white = m("eyewhite", rough=0.3, vc=False, color=srgb(P["eye_white"]), spec=0.5)
        self.mat_glint = m("glint", rough=0.2, vc=False, color=(1, 1, 1), emit=6.0)
        self.mat_nostril = m("nostril", rough=0.5, vc=False, color=srgb(P["nostril"]))
        self.mat_mark = m("mark", rough=0.5, vc=False, color=srgb(P["mark"]), spec=0.4)
        self.mat_ear = m("earin", rough=0.55, vc=False, color=srgb(P["ear_in"]), sss=0.3)
        self.mat_eyeglass = m("eyeglass", rough=0.12, spec=0.9)
        self.mat_nostril_vc = m("nostril_vc", rough=0.5, spec=0.2)
        self.mat_flower = m("flower", rough=0.45, sss=0.35, spec=0.25, sheen=0.3)
        self.mat_leaf = m("leaf", rough=0.5, sss=0.25, spec=0.2)
        self.mat_stamen = m("stamen", rough=0.4, vc=False, color=srgb("#f0a45c"), spec=0.3)
        self.geo_v, self.geo_f = [], []                     # the coat parts together, for projecting hair and wings onto the body
        hx, hy, hang, hs = self.pose["head"]
        self.hx, self.hy, self.hang, self.hs = hx, hy, hang, hs
        th = math.radians(hang)
        self.fwd = Vector((math.cos(th), 0, -math.sin(th)))
        self.upv = Vector((math.sin(th), 0, math.cos(th)))
        self.body_parts, self.attach, self.pasterns = [], [], []
        self.build_torso()
        self.build_neck()
        self.build_legs()
        self.fuse_body()
        bare = bool(os.environ.get("UNI_BARE"))             # UNI_BARE=1: body and head only, for checking the surface
        self.head_group = []
        _CAPTURE.append(self.head_group)                     # everything on the head is built straight, then turned as one piece
        self.build_head()
        self.build_horn_and_ears()
        self.bvh = BVHTree.FromPolygons([tuple(v) for v in self.geo_v], self.geo_f)
        self.build_face()
        if not bare:
            self.build_bangs()
            if traits.get("flowers"):
                self.build_crown()
        self.sparkles_head()
        _CAPTURE.pop()
        self.pose_head()
        if not bare:
            self.build_hair()
            if traits.get("wings"):
                self.build_wings()
        self.build_decals()
        if traits.get("flowers"):
            self.build_flowers()
        self.sparkles()
        self.build_ground()

    # ---------------------------------------------------------- helpers
    def hp(self, x, y):
        """head-local 2D point (the 2D rig's head frame) -> canvas 2D point"""
        a = math.radians(self.hang)
        lx, ly = (x - 574) * self.hs, (y - 152) * self.hs
        return (self.hx + lx * math.cos(a) - ly * math.sin(a), self.hy + lx * math.sin(a) + ly * math.cos(a))

    def H(self, x, y, lat=0.0):
        """head-local 2D point plus lateral pixels -> world"""
        cx, cy = self.hp(x, y)
        return P3(cx, cy, lat * self.hs)

    @staticmethod
    def mottle(c, p, amount=0.16):
        """soft blotches of pink, aqua and lilac in the coat, like watercolour washes"""
        n1 = math.sin(p[0] * 2.9 + p[2] * 2.1) * math.sin(p[2] * 3.3 - p[0] * 1.7 + p[1] * 3.1)
        n2 = math.sin(p[0] * 5.3 - p[2] * 4.1 + 1.3) * math.sin(p[2] * 4.7 + p[1] * 4.3)
        tint = srgb("#ffd9e8") if n1 > 0 else srgb("#d4f1f4")
        c = mix(c, tint, amount * abs(n1) ** 0.8)
        return mix(c, srgb("#e3dcf8"), amount * 0.8 * max(0.0, n2))

    def coat_color(self, z, shade_w=0.0):
        P = self.P
        y_px = 640 - z * 100
        t = (y_px - (300 + self.dy)) / 260.0
        c = grad(P["coat"], t)
        return mix(c, srgb(P["shade"]), shade_w)

    def add_coat(self, name, verts, faces, cols):
        base = len(self.geo_v)
        self.geo_v.extend(verts)
        self.geo_f.extend([tuple(i + base for i in f) for f in faces])
        ob = add_object(name, verts, faces, cols, self.mat_coat)
        return ob

    def surface_lat(self, x, z, sgn):
        """lateral position (positive, world units) of the body surface at world (x, z) on side sgn; None if the ray misses"""
        h = self.bvh.ray_cast(Vector((x, sgn * 4.0, z)), Vector((0, -sgn, 0)))
        return None if h[0] is None else abs(h[0].y)

    def lat_at(self, x, z, sgn):
        """smooth lateral position of the body surface at world (x, z): torso and neck as analytic ellipse sections, so hair and wings
        follow the body without ray-cast noise. Off the body it flares outward gently."""
        X, Yp = x / S + 400, 640 - z / S
        best, dist = 0.0, 1e9
        poly = self.torso_poly
        if self._tx0 <= X <= self._tx1:
            top, bot = slice_at(poly, X)
            vr = (bot - top) / 2
            if vr > 1:
                u = (Yp - (top + bot) / 2) / vr
                if abs(u) < 1:
                    best = max(best, 0.84 * vr * math.sqrt(1 - u * u) * S)
                    dist = 0.0
                else:
                    dist = min(dist, (abs(u) - 1) * vr * S)
        else:
            dist = min(dist, (self._tx0 - X if X < self._tx0 else X - self._tx1) * S)
        P_ = self._nc
        d2 = (P_[:, 0] - X) ** 2 + (P_[:, 1] - Yp) ** 2
        i = int(np.argmin(d2))
        t = self._nt[i]
        dn = abs((X - P_[i, 0]) * t[1] - (Yp - P_[i, 1]) * t[0])
        r = self._nr[i]
        s_ = dn / r
        if s_ < 1:
            best = max(best, 0.92 * r * math.sqrt(1 - s_ * s_) * S)
            dist = 0.0
        else:
            dist = min(dist, (dn - r) * S)
        return best + 0.14 * dist if dist > 0 else best

    # ---------------------------------------------------------- torso
    def build_torso(self):
        dy = self.dy
        poly = closed_poly([(x, y + dy) for x, y in self.body_pts], 14)
        xmin, xmax = min(p[0] for p in poly) + 0.5, max(p[0] for p in poly) - 0.5
        xs = [xmin + (xmax - xmin) * (0.5 - 0.5 * math.cos(math.pi * k / 56)) for k in range(57)]
        specs = []
        for x in xs:
            top, bot = slice_at(poly, x)
            c = P3(x, (top + bot) / 2)
            vr = (bot - top) / 2
            specs.append((c, Vector((0, 0, 1)), vr * S, Y, vr * 0.84 * S))

        def col(i, th, p):
            under = max(0.0, -math.sin(th))
            return self.coat_color(p.z, under ** 1.3 * 0.55)
        v, f, c = loft_rings(specs, 40, col)
        self.body_parts.append((v, f))
        self.torso_poly = poly

    # ---------------------------------------------------------- neck
    def build_neck(self):
        pose = self.pose
        crest = A.bez(*pose["crest"], 20)
        throat = A.bez(*pose["throat"], 20)[::-1]
        centers = [((a[0] + b[0]) / 2, (a[1] + b[1]) / 2) for a, b in zip(crest, throat)]
        tg = tangents2d(centers)
        specs = []
        for i, (c, t) in enumerate(zip(centers, tg)):
            r = math.hypot(crest[i][0] - throat[i][0], crest[i][1] - throat[i][1]) / 2 * 0.95
            specs.append((P3(*c), D3(-t[1], t[0]), r * S, Y, r * 0.92 * S))

        self.neck_c = list(centers)
        self.neck_r = [math.hypot(crest[i][0] - throat[i][0], crest[i][1] - throat[i][1]) / 2 * 0.95 for i in range(len(centers))]
        c_last, t_last = centers[-1], tg[-1]
        r_last = specs[-1][2]
        for j in range(1, 9):
            cj = (c_last[0] + t_last[0] * 12 * j, c_last[1] + t_last[1] * 12 * j)
            rj = r_last * (1 - 0.025 * j)
            specs.append((P3(*cj), D3(-t_last[1], t_last[0]), rj, Y, rj * 0.92))
            self.neck_c.append(cj)
            self.neck_r.append(rj / S)

        def col(i, th, p):
            under = max(0.0, -math.sin(th))
            return self.coat_color(p.z, under ** 1.3 * 0.3)
        v, f, c = loft_rings(specs, 32, col)
        self.body_parts.append((v, f))
        self.crest, self.crest_n = crest, tangents2d(crest)
        pts, rr = [], []
        for i in range(len(self.neck_c) - 1):
            for q in range(4):
                f_ = q / 4
                pts.append((self.neck_c[i][0] + (self.neck_c[i + 1][0] - self.neck_c[i][0]) * f_, self.neck_c[i][1] + (self.neck_c[i + 1][1] - self.neck_c[i][1]) * f_))
                rr.append(self.neck_r[i] + (self.neck_r[i + 1] - self.neck_r[i]) * f_)
        self._nc = np.array(pts)
        self._nr = np.array(rr)
        self._nt = np.array(tangents2d(pts))
        xs_ = [p[0] for p in self.torso_poly]
        self._tx0, self._tx1 = min(xs_) + 0.5, max(xs_) - 0.5

    # ---------------------------------------------------------- legs
    @staticmethod
    def leg_shape(f, hind):
        """radius multiplier along a leg (0 = top): flared thigh/forearm, soft knee or hock, slim cannon, round fetlock"""
        g = lambda c, w: math.exp(-((f - c) / w) ** 2)
        top = 0.6 + 0.4 * smooth(0.0, 0.22, f) + 0.16 * g(0.3, 0.12)
        return top * (1 + 0.09 * g(0.47 if not hind else 0.42, 0.07)) * (1 - 0.06 * g(0.68, 0.1)) * (1 + 0.07 * g(0.86, 0.05))

    def build_legs(self):
        P = self.P
        for key, ctrl in list(self.pose["near"].items()) + list(self.pose["far"].items()):
            sgn = -1 if key in self.pose["near"] else 1
            hind = key.endswith("h")
            off = (34 if hind else 30) * sgn
            dense = A.spl(ctrl, 8)
            pts = [(p[0], p[1]) for p in dense]
            tg = tangents2d(pts)
            specs = []
            n = len(dense)
            for i, (p, t) in enumerate(zip(dense, tg)):
                r = p[2] / 2 * self.leg_shape(i / (n - 1), hind)
                lat = off * (1.0 - 0.35 * max(0.0, 1 - i / (n * 0.35)))       # legs tuck in toward the body at the top
                specs.append((P3(p[0], p[1], lat), D3(-t[1], t[0]), r * S, Y, r * 0.86 * S))
            v, f, c = loft_rings(specs, 20, lambda i, th, p: (1, 1, 1))
            self.body_parts.append((v, f))
            self.pasterns.append(specs[int(0.84 * (n - 1))])
            for k in (0, n // 10, n // 5):                     # where this leg joins the body: the fillet is smoothed here
                self.attach.append(P3(dense[k][0], dense[k][1], off * 0.7))
            # thigh / shoulder mass, so the leg grows out of the body instead of being stuck on
            w0 = ctrl[0][2] / 2
            cen = P3(ctrl[0][0] + (2 if hind else 0), ctrl[0][1] + (10 if hind else 4), off * 0.62)
            sx, sz = (0.95, 0.96) if hind else (0.95, 1.0)
            v, f = ellipsoid(cen, Vector((1, 0, 0)) * (w0 * sx * S), Vector((0, 0, 1)) * (w0 * sz * S), Y * (w0 * 0.62 * S), 24, 16)
            self.body_parts.append((v, f))
            self.attach.append(cen)
            self.attach.append(cen + Vector((0, 0, 0.25)))
            # hoof
            (x1, y1, _), (x2, y2, w2) = ctrl[-2], ctrl[-1]
            L = math.hypot(x2 - x1, y2 - y1) or 1
            dx, dyv = (x2 - x1) / L, (y2 - y1) / L
            hp_ = [(x2 - dx * 8, y2 - dyv * 8), (x2 + dx * 3, y2 + dyv * 3), (x2 + dx * 14, y2 + dyv * 14), (x2 + dx * 22, y2 + dyv * 22)]
            hw = [w2 - 2, w2 + 2, w2 + 9, w2 + 12]
            dh = A.spl([(a, b, w) for (a, b), w in zip(hp_, hw)], 5)
            tg2 = tangents2d([(p[0], p[1]) for p in dh])
            nh = len(dh)
            specs = []
            for q, (p, t) in enumerate(zip(dh, tg2)):
                fq = q / (nh - 1)
                toe = 11 * fq ** 1.6                                              # the front wall slopes forward to the toe
                specs.append((P3(p[0] + toe, p[1], off), D3(-t[1], t[0]), p[2] / 2 * S, Y, p[2] / 2 * 0.9 * S))
            hc = lambda i, th, p: mix(grad(P["hoof_g"], 0.15 + 0.7 * (i / max(1, nh - 1))), (1, 1, 1), 0.25 * max(0.0, math.cos(th - 0.6)) ** 6)
            v, f, c = loft_rings(specs, 16, hc)
            add_object("hoof_" + key, v, f, c, self.mat_hoof)

    def fuse_body(self):
        """torso, neck, legs and thigh masses become one surface: voxel union, then the joins are smoothed so nothing looks stuck on"""
        verts, faces = [], []
        for v, f in self.body_parts:
            base = len(verts)
            verts.extend(v)
            faces.extend([tuple(i + base for i in fc) for fc in f])
        me = bpy.data.meshes.new("bodyraw")
        me.from_pydata([tuple(v) for v in verts], [], faces)
        me.update()
        bm = bmesh.new()
        bm.from_mesh(me)
        if bm.calc_volume(signed=True) < 0:             # make sure the shells are outward facing before the union
            bmesh.ops.reverse_faces(bm, faces=bm.faces)
        bm.to_mesh(me)
        bm.free()
        ob = bpy.data.objects.new("bodyraw", me)
        bpy.context.collection.objects.link(ob)
        md = ob.modifiers.new("vox", "REMESH")
        md.mode, md.voxel_size, md.adaptivity = "VOXEL", 0.026, 0.0
        dg = bpy.context.evaluated_depsgraph_get()
        me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
        bpy.data.objects.remove(ob)
        ob2 = bpy.data.objects.new("bodyfuse", me2)
        bpy.context.collection.objects.link(ob2)
        n = len(me2.vertices)
        co = np.empty(n * 3, dtype=np.float32)
        me2.vertices.foreach_get("co", co)
        co = co.reshape(n, 3)
        w = np.zeros(n, dtype=np.float32)
        for a in self.attach:
            d = np.linalg.norm(co - np.array([a.x, a.y, a.z], dtype=np.float32), axis=1)
            w = np.maximum(w, np.clip((1.6 - d) / 0.8, 0.0, 1.0))
        vg = ob2.vertex_groups.new(name="joins")
        for val in (0.25, 0.5, 0.75, 1.0):
            idx = np.nonzero((w > val - 0.25) & (w <= val))[0].tolist()
            if idx:
                vg.add(idx, val, "REPLACE")
        m1 = ob2.modifiers.new("sm_all", "LAPLACIANSMOOTH")
        m1.iterations, m1.lambda_factor, m1.use_volume_preserve = 3, 0.35, True
        m2 = ob2.modifiers.new("sm_joins", "LAPLACIANSMOOTH")
        m2.iterations, m2.lambda_factor, m2.use_volume_preserve, m2.vertex_group = 14, 0.8, True, "joins"
        m3 = ob2.modifiers.new("sm_final", "LAPLACIANSMOOTH")
        m3.iterations, m3.lambda_factor, m3.use_volume_preserve = 2, 0.3, True
        dg = bpy.context.evaluated_depsgraph_get()
        me3 = bpy.data.meshes.new_from_object(ob2.evaluated_get(dg))
        bpy.data.objects.remove(ob2)
        n = len(me3.vertices)
        co = np.empty(n * 3, dtype=np.float32)
        nr = np.empty(n * 3, dtype=np.float32)
        me3.vertices.foreach_get("co", co)
        me3.vertices.foreach_get("normal", nr)
        co, nr = co.reshape(n, 3), nr.reshape(n, 3)
        verts = [Vector(c) for c in co.tolist()]
        faces = [tuple(p.vertices) for p in me3.polygons]
        cols = []
        for c, nn in zip(co.tolist(), nr.tolist()):
            under = max(0.0, -nn[2])
            cols.append(lin(self.mottle(self.coat_color(c[2], under ** 1.3 * 0.5), c)))
        self.body = self.add_coat("body", verts, faces, cols)
        self.body_bvh = BVHTree.FromPolygons([tuple(v) for v in verts], faces)
        print("body fused:", n, "vertices")

    # ---------------------------------------------------------- head
    def pose_head(self):
        """turn and tilt the finished head about the top of the neck, so it is not a perfect side-on or front-on object"""
        piv = P3(self.hx, self.hy, 0)
        yaw, roll = math.radians(self.pose.get("yaw", 0)), math.radians(self.pose.get("roll", 0))
        M = Matrix.Translation(piv) @ Matrix.Rotation(yaw, 4, "Z") @ Matrix.Rotation(roll, 4, "X") @ Matrix.Translation(-piv)
        for ob in self.head_group:
            ob.matrix_world = M @ ob.matrix_world

    def build_head(self):
        self.head_poly = path_poly("M574 152 C592 134 622 122 652 128 C682 134 704 170 719 206 C727 224 733 240 727 254 C721 268 708 277 692 281 "
                                   "C678 287 664 296 650 300 C634 306 614 308 598 304 C588 312 574 312 562 298 L566 196 Z", 14)
        poly = self.head_poly
        xmin, xmax = min(p[0] for p in poly) + 0.5, max(p[0] for p in poly) - 0.5
        xs = [xmin + (xmax - xmin) * (0.5 - 0.5 * math.cos(math.pi * k / 50)) for k in range(51)]
        specs = []
        self.head_rings = []
        for x in xs:
            top, bot = slice_at(poly, x)
            vr = (bot - top) / 2
            cy = (top + bot) / 2
            lat = vr * (0.98 if x < 585 else 0.98 - 0.36 * smooth(585, 640, x) - 0.36 * smooth(640, 700, x) + 0.2 * smooth(688, 724, x))
            lat = max(lat, 6)
            self.head_rings.append((x, cy, vr, lat))
            specs.append((self.H(x, cy), self.upv, vr * self.hs * S, Y, lat * self.hs * S))

        def col(i, th, p):
            under = max(0.0, -math.cos(th))                 # ring angle 0 is the top of the head, pi the underside
            c = self.coat_color(p.z, under ** 1.3 * 0.5)
            x, cy, vr, lat = self.head_rings[i]
            # cheek blush on both sides
            ly = cy - vr * math.cos(th)
            dx, dz = (x - 640) / 30.0, (ly - 264) / 24.0
            c = mix(c, srgb(self.P["blush"]), math.exp(-(dx * dx + dz * dz)) * abs(math.sin(th)) * 0.9 * self.P["blush_o"])
            return self.mottle(c, p, 0.10)
        v, f, c = loft_rings(specs, 36, col)
        self.head = self.add_coat("head", v, f, c)

    def head_surface(self, x, ly, sgn):
        """world point on the head's side at head-local x and height ly"""
        best = min(self.head_rings, key=lambda r: abs(r[0] - x))
        _, cy, vr, lat = best
        s_ = max(-0.85, min(0.85, (ly - cy) / vr))
        return self.H(x, cy + vr * s_, sgn * lat * math.sqrt(1 - s_ * s_))

    # ---------------------------------------------------------- horn and ears
    def build_horn_and_ears(self):
        P = self.P
        base, tip = (641, 160), (686, 26)
        n = 36
        pts2 = [(base[0] + (tip[0] - base[0]) * t / n - 16 * math.sin(math.pi * t / n) * (1 - t / n), base[1] + (tip[1] - base[1]) * t / n) for t in range(n + 1)]
        tg = tangents2d(pts2)
        specs = []
        for i, (p, t) in enumerate(zip(pts2, tg)):
            u = i / n
            r = 20 * (1 - u) ** 0.85 + 0.6
            # the ring is perpendicular to the horn axis; the ribs twist along the length
            specs.append((self.H(p[0], p[1]), None, r, None, u))
        verts, faces, cols = [], [], []
        segs = 32
        rings = []
        for i, (c, _, r, _, u) in enumerate(specs):
            t2 = tg[i]
            ax = self.upv * 0 + Vector((-t2[1], 0, -t2[0]))        # 2D normal of the axis, in world
            ax = D3(-t2[1], t2[0]).normalized()
            ring = []
            for k in range(segs):
                th = 2 * math.pi * k / segs
                ridge = 0.5 + 0.5 * math.cos(th - 2 * math.pi * 6.5 * u)
                rr = r * (1 + 0.12 * ridge ** 1.5) * self.hs
                ring.append(c + ax * (rr * S * math.cos(th)) + Y * (rr * S * math.sin(th)))
                col = mix(grad(P["horn_g"], 1 - u * 0.9), srgb(P["horn_line"]), (1 - ridge) * 0.5)
                cols.append(lin(col))
            rings.append(ring)
        verts, faces = loft(rings)
        self.horn = add_object("horn", verts, faces, cols, self.mat_horn)
        # ears: a near and a far ear, splayed a little outward
        for sgn in (-1, 1):
            for inner in (False, True):
                base = (598 + (4 if inner else 0), 158 - (0 if inner else 0))
                tipp = (570 + (3 if inner else 0) + (6 if sgn < 0 else -10), 64 + (14 if inner else 0) + (0 if sgn < 0 else 6))
                ctr = [(base[0], base[1]), (base[0] - 18, (base[1] + tipp[1]) / 2 + 6), (tipp[0] + 8, tipp[1] + 22), tipp]
                pts = A.bez(*ctr, 16)
                world = []
                for i, (x, y) in enumerate(pts):
                    lat = sgn * ((30 + 26 * (i / 16)) if sgn < 0 else (28 + 14 * (i / 16))) + (sgn * 2 if inner else 0)
                    world.append(self.H(x, y, lat))
                rad = []
                for i in range(len(world)):
                    u = i / (len(world) - 1)
                    w = (22 * math.sin(min(1.0, u * 1.6) * math.pi / 2) * (1 - u ** 1.6) ** 0.7 + 0.5) * (0.62 if inner else 1.0)
                    rad.append(w * self.hs * S)
                rings = tube(world, rad, flat=0.45, segs=8, up=Y)
                v, f = loft(rings)
                if inner:
                    for face in (-1, 1):                  # pink on both faces, so it shows from every side
                        v2 = [p + Y * (face * 0.03 * self.hs) + self.fwd * 0.012 for p in v]
                        add_object("ear_in", v2, f, None, self.mat_ear)
                else:
                    cols = [lin(self.coat_color(p.z)) for p in v]
                    self.add_coat("ear", v, f, cols)

    # ---------------------------------------------------------- face
    def head_frame(self, x, y, sgn, fwd_bias=0.6):
        """point on the head surface at head-local (x, y) on side sgn, with outward normal, forward and up directions lying in the surface"""
        guess = self.head_surface(x, y, sgn)
        n0 = (guess - self.H(x, y)).normalized()
        n0 = (n0 + self.fwd * fwd_bias).normalized()
        hit = self.bvh.ray_cast(guess + n0 * 1.0, -n0)
        if hit[0] is not None:
            C, out = hit[0], hit[1].normalized()
            if out.dot(n0) < 0:
                out = -out
        else:
            C, out = guess, n0
        ex = (self.fwd - out * self.fwd.dot(out)).normalized()
        ez = out.cross(ex)
        if ez.dot(self.upv) < 0:
            ez = -ez
        return C, out, ex, ez

    @staticmethod
    def eye_outline(n=26):
        """the almond of the reference eye in unit coordinates: u towards the nose, v up. Pointed, raised outer corner at the back."""
        def bz(p0, p1, p2, p3, t):
            a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
            return (a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1])
        O, I = (-1.0, 0.16), (0.95, -0.12)
        top = [bz(O, (-0.80, 1.05), (0.30, 1.24), I, t / n) for t in range(n + 1)]
        bot = [bz(I, (0.60, -0.82), (-0.58, -0.74), O, t / n) for t in range(1, n)]
        return top, bot

    @staticmethod
    def ellipse_loop(cu, cv, a, b, n=22):
        return [(cu + a * math.cos(2 * math.pi * k / n), cv + b * math.sin(2 * math.pi * k / n)) for k in range(n)]

    def decal_disc(self, name, C, out, ex, ez, rx, ry, loop, scale, off, colfn, mat, R=5):
        """a flat filled shape painted onto the head surface: every vertex is dropped onto the surface and lifted by `off`"""
        N = len(loop)
        cu = sum(p[0] for p in loop) / N
        cv = sum(p[1] for p in loop) / N
        verts, cols = [], []

        def put(u, v, rr):
            p = C + ex * (u * rx) + ez * (v * ry)
            hit = self.bvh.ray_cast(p + out * 0.7, -out)
            if hit[0] is not None:
                nn = hit[1] if hit[1].dot(out) > 0 else -hit[1]
                q = hit[0] + nn * off
            else:
                q = p + out * off
            verts.append(q)
            cols.append(lin(colfn(u, v, rr)))
        put(cu, cv, 0.0)
        for r in range(1, R + 1):
            s_ = scale * r / R
            for (u, v) in loop:
                put(cu + (u - cu) * s_, cv + (v - cv) * s_, r / R)
        faces = [(0, 1 + k, 1 + (k + 1) % N) for k in range(N)]
        for r in range(1, R):
            b0, b1 = 1 + (r - 1) * N, 1 + r * N
            for k in range(N):
                k2 = (k + 1) % N
                faces.append((b0 + k, b0 + k2, b1 + k2, b1 + k))
        return add_object(name, verts, faces, cols, mat)

    def surf_pt(self, C, out, ex, ez, rx, ry, u, v, off):
        p = C + ex * (u * rx) + ez * (v * ry)
        hit = self.bvh.ray_cast(p + out * 0.7, -out)
        if hit[0] is not None:
            nn = hit[1] if hit[1].dot(out) > 0 else -hit[1]
            return hit[0] + nn * off
        return p + out * off

    def build_face(self):
        P, hs = self.P, self.hs
        closed = self.pose["eye"] != "open"
        for sgn in (-1, 1):
            C, out, ex, ez = self.head_frame(640, 207, sgn, 0.7)
            tau = math.radians(14)                                              # the outer corner sits higher than the inner one
            ex2 = ex * math.cos(tau) - ez * math.sin(tau)
            ez2 = ez * math.cos(tau) + ex * math.sin(tau)
            k = 1.0 if sgn == NEAR else 0.93                                    # the far eye is not an exact copy
            if closed:
                self.eye_closed(C, out, ex2, ez2, 0.25 * hs * k, 0.22 * hs * k)
            else:
                self.eye_open(C, out, ex2, ez2, 0.245 * hs * k, 0.265 * hs * k, sgn)
            # nostril: a comma-shaped opening lying on the side of the muzzle, the near one a little bigger
            Cn, outn, exn, ezn = self.head_frame(713, 240, sgn, 1.2)
            k = 1.0 if sgn == NEAR else 0.82
            rot = math.radians(32)
            ex3 = exn * math.cos(rot) + ezn * math.sin(rot)
            ez3 = ezn * math.cos(rot) - exn * math.sin(rot)
            egg = [(math.cos(t) * (1 + 0.35 * math.cos(t)), math.sin(t) * (0.62 + 0.3 * math.cos(t))) for t in [2 * math.pi * q / 26 for q in range(26)]]
            rim = srgb(P["nostril"])
            deep = mix(rim, (0.35, 0.18, 0.3), 0.55)
            self.decal_disc("nostril", Cn, outn, ex3, ez3, 0.07 * hs * k, 0.05 * hs * k, egg, 1.0, 0.003 * hs,
                            lambda u, v, r: mix(deep, rim, smooth(0.4, 1.0, r)), self.mat_nostril_vc)
        # one mouth: traced round the muzzle at lip height, from the near corner across the front to the far corner; the corners curl up a little
        C0 = self.H(694, 268)
        pts = []
        n_m = 44
        for q in range(n_m + 1):
            t = -1 + 2 * q / n_m                                               # -1 near corner, +1 far corner
            sgn = NEAR if t < 0 else -NEAR
            phi = math.radians(abs(t) * (104 if t < 0 else 92))
            d = (self.fwd * math.cos(phi) + Y * sgn * math.sin(phi)).normalized()
            lift = (-3 + 8 * abs(t) ** 2.4 + (5 * smooth(0.82, 1.0, -t) if t < 0 else 0)) * S * self.hs
            back = (10 * smooth(0.6, 1.0, abs(t))) * S * self.hs                   # the corners run back along the cheek
            origin = C0 + self.upv * lift - self.fwd * back
            hit = self.bvh.ray_cast(origin + d * 1.5, -d)
            if hit[0] is None:
                continue
            nn = hit[1] if hit[1].dot(d) > 0 else -hit[1]
            pts.append(hit[0] + nn * 0.01)
        for _ in range(2):
            pts = [pts[0]] + [(pts[i - 1] + pts[i] * 2 + pts[i + 1]) / 4 for i in range(1, len(pts) - 1)] + [pts[-1]]
        m_ = len(pts)
        rad = [0.016 * hs * (0.35 + 0.65 * math.sin(math.pi * k_ / (m_ - 1)) ** 0.4) for k_ in range(m_)]
        rings = tube(pts, rad, segs=6, up=self.upv)
        v, f = loft(rings)
        add_object("mouth", v, f, None, self.mat_nostril)

    def eye_open(self, C, out, ex, ez, rx, ry, sgn):
        """the reference eye: a flat dark-blue almond with a paler blue lower edge, a big highlight, a thick lid that flicks up at the outer corner, lashes"""
        P, hs = self.P, self.hs
        top, bot = self.eye_outline()
        loop = top + bot
        navy = srgb(P["iris_g"][2][1])
        mid = srgb(P["iris_g"][1][1])
        light = mix(srgb(P["iris_g"][0][1]), (1, 1, 1), 0.25)
        glass = self.mat_eyeglass
        self.decal_disc("eye_base", C, out, ex, ez, rx, ry, loop, 1.0, 0.004 * hs, lambda u, v, r: navy, glass)

        def iris_col(u, v, r):
            t = max(0.0, min(1.0, (v + 0.65) / 1.35))                           # 0 at the bottom edge, 1 at the top
            c = mix(light, mid, smooth(0.0, 0.55, t))
            c = mix(c, navy, smooth(0.45, 1.0, t))
            return mix(c, navy, 0.55 * smooth(0.7, 1.0, r))
        shifted = [(u * 0.93 + 0.05, v * 0.9 - 0.03) for (u, v) in loop]
        self.decal_disc("eye_iris", C, out, ex, ez, rx, ry, shifted, 1.0, 0.007 * hs, iris_col, glass)
        self.decal_disc("eye_pupil", C, out, ex, ez, rx, ry, self.ellipse_loop(0.10, 0.08, 0.30, 0.46), 1.0, 0.010 * hs, lambda u, v, r: srgb(P["pupil"]), glass)
        glint = self.mat_glint
        self.decal_disc("eye_glint", C, out, ex, ez, rx, ry, self.ellipse_loop(0.40, 0.46, 0.2, 0.22), 1.0, 0.014 * hs, lambda u, v, r: (1, 1, 1), glint, R=3)
        self.decal_disc("eye_glint2", C, out, ex, ez, rx, ry, self.ellipse_loop(-0.34, -0.36, 0.085, 0.095), 1.0, 0.014 * hs, lambda u, v, r: (1, 1, 1), glint, R=2)
        # upper lid: a thick dark line along the top edge, flicking up past the outer corner
        n_t = len(top)
        lid = [(u * 1.04, v * 1.04 + 0.02) for (u, v) in top] + []
        flick = [(-1.12, 0.34), (-1.26, 0.52), (-1.34, 0.70)]
        pts_uv = list(reversed(flick)) + [lid[0]] + lid[1:]
        pts_uv = [flick[2], flick[1], flick[0]] + lid
        pts = [self.surf_pt(C, out, ex, ez, rx, ry, u, v, 0.022 * hs) for (u, v) in pts_uv]
        m = len(pts)
        rad = []
        for k in range(m):
            t = k / (m - 1)
            rad.append(0.036 * hs * (0.18 + 0.82 * math.sin(math.pi * min(1.0, (k + 1.5) / (m * 0.6))) ** 0.7) * (1 - 0.65 * smooth(0.7, 1.0, t)) + 0.004)
        rings = tube(pts, rad, segs=6, up=out)
        v, f = loft(rings)
        add_object("lid", v, f, None, self.mat_dark)
        # lashes growing from the outer end of the lid
        for (t0, du, dv, ln) in ((0.04, -0.70, 0.72, 0.62), (0.12, -0.50, 0.86, 0.52), (0.22, -0.30, 0.95, 0.42)):
            u0, v0 = top[int(t0 * (n_t - 1))]
            lp = []
            for q in range(7):
                s_ = q / 6
                lp.append(self.surf_pt(C, out, ex, ez, rx, ry, u0 * 1.04 + du * ln * s_, v0 * 1.04 + 0.02 + dv * ln * s_ - 0.14 * s_ * s_, (0.022 + 0.03 * s_) * hs))
            rings = tube(lp, [0.013 * hs * (1 - q / 6) + 0.002 for q in range(7)], segs=5, up=out)
            v, f = loft(rings)
            add_object("lash", v, f, None, self.mat_dark)
        # a faint lower lid
        lows = [self.surf_pt(C, out, ex, ez, rx, ry, u * 1.03, v * 1.03, 0.014 * hs) for (u, v) in bot[3:-4]]
        rings = tube(lows, [0.008 * hs * (0.3 + 0.7 * math.sin(math.pi * k / (len(lows) - 1))) for k in range(len(lows))], segs=5, up=out)
        v, f = loft(rings)
        add_object("lowlid", v, f, None, self.mat_dark)

    def eye_closed(self, C, out, ex, ez, rx, ry):
        hs = self.hs
        arc = []
        for k in range(18):
            t = k / 17
            a = (-rx - 0.02 * hs) * (1 - t) + (rx + 0.02 * hs) * t
            b = -ry * 0.45 * math.sin(math.pi * t)
            arc.append(C + ex * a + ez * b + out * (0.06 * hs))
        rings = tube(arc, [0.02 * hs * (0.5 + 0.5 * math.sin(math.pi * k / 17) ** 0.6) for k in range(18)], segs=6, up=out)
        v, f = loft(rings)
        add_object("lid", v, f, None, self.mat_dark)
        for t_, ln, bend in ((0.08, 12, 4), (0.24, 10, 3), (0.4, 8, 1)):
            k = int(t_ * 17)
            pts = [arc[k] - ez * (ln * S * hs * s) - ex * (bend * S * hs * s * s) for s in [i / 6 for i in range(7)]]
            rings = tube(pts, [0.014 * hs * (1 - i / 6) + 0.002 for i in range(7)], segs=5, up=out)
            v, f = loft(rings)
            add_object("lash", v, f, None, self.mat_dark)

    # ---------------------------------------------------------- hair
    def lock(self, pts, w_px, palette, flat=0.5, tint=0.0, segs=8, sgn=1):
        n = len(pts) - 1
        radii = []
        for i in range(n + 1):
            t = i / n
            wd = w_px * (0.14 + 0.86 * math.sin(min(1.0, t * 1.9) * math.pi / 2)) * (1 - t ** 3.0) ** 0.45 * (1 + 0.2 * math.sin(t * math.pi))
            radii.append(max(wd / 2 * S, 0.0015))
        rings = tube(pts, radii, flat=flat, bref=lambda p: Vector((0, sgn, 0)), segs=segs)
        v, f = loft(rings)
        cols = []
        for i, ring in enumerate(rings):
            if isinstance(palette, tuple):
                k0, k1, fr = palette
                base_c = mix(grad(self.P["hair"][k0], i / n), grad(self.P["hair"][k1], i / n), fr)
            else:
                base_c = grad(self.P["hair"][palette % 3], i / n)
            c = lin(mix(base_c, (1, 1, 1), tint))
            cols.extend([c] * segs)
        return add_object("lock", v, f, cols, self.mat_hair)

    def ribbon(self, c2d, sgn, w_px, palette, off, bulge=0.012, root_blend=False):
        """a hair ribbon lying on the body: the 2D curve gives its outline from the side, every vertex is laid onto the body surface"""
        n = len(c2d) - 1
        tg = tangents2d(c2d)
        across = [-1.0, -0.5, 0.0, 0.5, 1.0]
        lat = [[0.0] * len(across) for _ in range(n + 1)]
        xz = [[None] * len(across) for _ in range(n + 1)]
        for i, (x, y) in enumerate(c2d):
            t = i / n
            wd = w_px * (0.22 + 0.78 * math.sin(min(1.0, t * 2.2) * math.pi / 2)) * (1 - t ** 2.2) ** 0.75 * (1 + 0.18 * math.sin(t * math.pi))
            hw = max(wd / 2, 0.6)
            nx, ny = tg[i][1], -tg[i][0]
            for k, sv in enumerate(across):
                w3 = P3(x + nx * hw * sv, y + ny * hw * sv)
                xz[i][k] = (w3.x, w3.z)
                lat[i][k] = self.lat_at(w3.x, w3.z, sgn)
        for k in range(len(across)):                                   # smooth along the ribbon so it follows the body without ripples
            col = smooth_over([lat[i][k] for i in range(n + 1)], 3, 2)
            for i in range(n + 1):
                lat[i][k] = col[i]
        for i in range(n + 1):                                         # and across it
            row = smooth_over(lat[i], 1, 2)
            lat[i] = row
        rings, cols = [], []
        for i in range(n + 1):
            top = []
            bl = 0.0 + 1.0 * smooth(0.0, 0.42, i / n) if root_blend else 1.0        # the root of the lock starts on the crest line
            for k, sv in enumerate(across):
                h = 0.004 + bulge * (1 - sv * sv)
                top.append(Vector((xz[i][k][0], sgn * ((lat[i][k] + off) * bl + h), xz[i][k][1])))
            bot = [Vector((xz[i][k][0], sgn * ((lat[i][k] + off) * bl - 0.004), xz[i][k][1])) for k in (3, 2, 1)]
            rings.append(top + bot)
            if isinstance(palette, tuple):
                k0, k1, fr = palette
                base_c = mix(grad(self.P["hair"][k0], i / n), grad(self.P["hair"][k1], i / n), fr)
            else:
                base_c = grad(self.P["hair"][palette % 3], i / n)
            top_c = []
            for sv in across:
                streak = 0.5 + 0.5 * math.cos(sv * 5.5 + i * 0.35)
                top_c.append(lin(mix(base_c, (1, 1, 1), 0.10 * (1 - abs(sv)) + 0.06 * streak)))
            cols.extend(top_c + [lin(mix(base_c, (0.7, 0.55, 0.8), 0.15))] * 3)
        v, f = loft(rings)
        return add_object("ribbon", v, f, cols, self.mat_hair)

    def drape(self, pts2d, sgn, base_off=0.035, grow=0.0):
        """2D hair curve -> 3D points lying on the body side (or flaring outward off the body)"""
        ws = [P3(x, y) for x, y in pts2d]
        lats = smooth_over([self.lat_at(w.x, w.z, sgn) for w in ws], 3, 2)
        return [Vector((w.x, sgn * (lat + base_off + grow * i), w.z)) for i, (w, lat) in enumerate(zip(ws, lats))]

    @staticmethod
    def curl_end(c, turns=1.0, size=9.0, sign=1):
        """continue a 2D curve with a small spiral, so a lock ends in a ringlet"""
        (x0, y0), (x1, y1) = c[-2], c[-1]
        th = math.atan2(y1 - y0, x1 - x0)
        p = (x1, y1)
        out = list(c)
        n = 11
        for j in range(1, n + 1):
            th += sign * turns * 0.42 * (1 + 0.06 * j)
            ln = size * 0.86 ** j
            p = (p[0] + math.cos(th) * ln, p[1] + math.sin(th) * ln)
            out.append(p)
        return out

    def real_crest(self):
        """the top line of the neck as actually built (the lofted neck bulges past the 2D crest outline), found by casting onto the body"""
        pts = []
        for i, (x, y) in enumerate(self.crest):
            nx, ny = self.crest_n[i][1], -self.crest_n[i][0]
            out = Vector((-nx, 0, ny)).normalized()
            p = P3(x, y)
            hit = self.bvh.ray_cast(p + out * 2.0, -out)
            q = hit[0] if hit[0] is not None else p
            pts.append((q.x / S + 400, 640 - q.z / S))
        for _ in range(3):
            pts = [pts[0]] + [((pts[i - 1][0] + 2 * pts[i][0] + pts[i + 1][0]) / 4, (pts[i - 1][1] + 2 * pts[i][1] + pts[i + 1][1]) / 4) for i in range(1, len(pts) - 1)] + [pts[-1]]
        return pts

    def build_hair(self):
        pose, dy, rnd = self.pose, self.dy, self.rnd
        self.hair_bvh = self.bvh_of([self.body] + [ob for ob in self.head_group if ob.name.startswith(("head", "ear"))])   # body and the turned head
        self.crest_r = self.real_crest()
        self.crest_rn = tangents2d(self.crest_r)
        crest, crest_n = self.crest_r, self.crest_rn
        # tail: one flowing S-shape that drifts away to the far side, locks fanned around it, ringlets at some ends
        t0 = pose["tail"]
        n_tail = 11
        N_ = 30
        root0 = (t0["root"][0], t0["root"][1] + dy)
        base = A.hair_curve(root0, t0["ang"], t0["length"], 40, 0.6, t0["droop"], N_)
        btg = tangents2d(base)
        for i in range(n_tail):
            m = int((0.5 + 0.5 * ((i * 5) % 11) / 10.0) * N_)
            c = []
            for k in range(m + 1):
                sfr = k / N_
                off = (i - n_tail // 2) * 7.5 * (0.15 + sfr) + 5 * math.sin(k * 0.5 + i * 1.7) * sfr
                px, py = btg[k][1], -btg[k][0]
                c.append((base[k][0] + px * off, base[k][1] + py * off))
            if i in (1, 3, 6, 8, 10):
                c = self.curl_end(c, 1.0 + 0.3 * rnd.random(), 10.0, 1 if i % 2 else -1)
            nn = len(c)
            lat0 = (i - n_tail // 2) * 0.05
            pts = [Vector(((x - 400) * S, lat0 * (1 + 1.2 * k / nn) - NEAR * 0.55 * (k / nn) ** 1.6 + 0.12 * math.sin(k * 0.28 + i * 0.4), (640 - y) * S))
                   for k, (x, y) in enumerate(c)]
            pos = 2.0 * i / (n_tail - 1)
            pal = (min(int(pos), 1), min(int(pos), 1) + 1, pos - min(int(pos), 1))
            self.lock(pts, 46 - abs(i - n_tail // 2) * 1.8, pal, flat=0.5)
        # mane: one cohesive mass. Three overlapping sheets of hair grow out of the crest and lie over the near side; their lower edges are scalloped into
        # locks, each lock slightly domed with a soft groove between locks. A little hair spills over to the far side near the top of the neck.
        self.hair_sheet(NEAR, 0.0, 1.0, 1.3, 0.06, 7, 0.26, arch=6)
        self.hair_sheet(NEAR, 0.03, 0.97, 1.0, 0.13, 10, 0.30, arch=9)
        self.hair_sheet(NEAR, 0.06, 0.92, 0.72, 0.20, 13, 0.34, arch=12)
        self.hair_sheet(-NEAR, 0.04, 0.80, 0.36, 0.03, 7, 0.30, wave=0.6, arch=6, part=-0.10)

    def hair_sheet(self, sgn, u0, u1, length_f, off, nlocks, depth, wave=1.0, M=96, nv=16, arch=12, part=0.10):
        """a sheet of hair rooted along the crest line: along the crest u0..u1, every column falls in a wavy curve; the sheet starts on the crest centre
        line and settles onto the body surface, so it is continuous from the top of the neck"""
        pose = self.pose
        crest, crest_n = self.crest_r, self.crest_rn
        raw, meta = [], []
        for i in range(M + 1):
            u = u0 + (u1 - u0) * i / M
            kf = u * 19.999
            k0 = min(18, int(kf))
            fr = kf - k0
            px = crest[k0][0] + (crest[k0 + 1][0] - crest[k0][0]) * fr
            py = crest[k0][1] + (crest[k0 + 1][1] - crest[k0][1]) * fr
            nx = crest_n[k0][1] + (crest_n[k0 + 1][1] - crest_n[k0][1]) * fr
            ny = -(crest_n[k0][0] + (crest_n[k0 + 1][0] - crest_n[k0][0]) * fr)
            root = (px - nx * 2, py - ny * 2)
            ang = 90 + 16 * (0.5 - u) + 6 * math.sin(u * 9)                                # falls across the neck side, not along the crest
            frac = ((u - u0) / (u1 - u0) * nlocks) % 1.0
            ends = smooth(u0, u0 + 0.09, u) * smooth(u1, u1 - 0.05, u)            # the mane tapers in at the poll and at the withers
            L = (96 + 70 * u) * length_f * (1 - depth * (1 - math.sin(math.pi * frac) ** 0.8)) * (0.45 + 0.55 * ends)
            c = A.hair_curve(root, ang, L, (30 + 10 * math.sin(u * 5)) * wave, u * 8 + 0.4, 34 * length_f, nv - 1)
            row = []
            for x, y in c:
                w3 = P3(x, y)
                a_ = self.lat_at(w3.x, w3.z, sgn)
                hit = self.hair_bvh.ray_cast(Vector((w3.x, sgn * 4.0, w3.z)), Vector((0, -sgn, 0)))
                row.append(max(a_, abs(hit[0].y)) if hit[0] is not None else a_)     # never inside the real body
            raw.append(row)
            meta.append((u, frac, c, nx, ny, ends))
        lat = [smooth_over(r, 4, 3) for r in raw]
        for j in range(nv):
            col = smooth_over([lat[i][j] for i in range(M + 1)], 4, 3)
            for i in range(M + 1):
                lat[i][j] = col[i]
        top, bot, cols = [], [], []
        cen, nrms = [[None] * nv for _ in range(M + 1)], [[None] * nv for _ in range(M + 1)]
        for i in range(M + 1):
            u, frac, c, nx, ny, ends = meta[i]
            for j in range(nv):
                v = j / (nv - 1)
                w3 = P3(*c[j])
                # the hair parts just past the middle of the crest, arches up over it, then falls down this side onto the body
                b2 = smooth(0.0, 0.32, v)
                bump = 0.03 * math.sin(math.pi * frac) ** 0.8 * smooth(0.08, 0.7, v)  # each lock is slightly domed
                ypos = (1 - b2) * (-part) + b2 * (lat[i][j] + off * (0.4 + 0.6 * ends) + bump)
                lift = arch * math.sin(math.pi * min(1.0, v / 0.42)) * (1 - 0.4 * v) * ends
                ox, oz = -nx * lift * S, ny * lift * S
                h = 0.011
                p = Vector((w3.x + ox, sgn * ypos, w3.z + oz))
                o3 = Vector((-nx, 0, ny)).normalized()
                if v < 0.5:                                                           # near the root: rest on the real neck, never inside it
                    hit = self.hair_bvh.ray_cast(p + o3 * 1.5, -o3)
                    if hit[0] is not None and (hit[0] - p).dot(o3) > -0.012:
                        p = hit[0] + o3 * (0.014 + 0.2 * off)
                nrm = (o3 * (1 - b2) + Y * sgn * b2).normalized()
                cen[i][j], nrms[i][j] = p, nrm
                pos = max(0.0, min(2.0, 2.0 * u))
                kk = min(int(pos), 1)
                cc = mix(grad(self.P["hair"][kk], 0.35 + 0.45 * v), grad(self.P["hair"][kk + 1], 0.35 + 0.45 * v), pos - kk)
                g = math.exp(-(min(frac, 1 - frac) / 0.07) ** 2)                       # groove between locks
                cc = mix(cc, (0.78, 0.55, 0.72), 0.22 * g * smooth(0.1, 0.5, v))
                cc = mix(cc, (1, 1, 1), 0.10 * smooth(0.55, 1.0, v) + 0.05 * math.sin(math.pi * frac))
                cc = mix(cc, (0.8, 0.55, 0.72), 0.08 * (0.5 + 0.5 * math.cos(i * 0.9)))          # fine strands
                sheen = math.exp(-((v - 0.36) / 0.07) ** 2) * (0.6 + 0.4 * math.cos(i * 0.45)) * ends  # a soft band of shine across the hair
                cc = mix(cc, (1, 1, 1), 0.24 * sheen)
                cols.append(lin(cc))
        for _ in range(3):                                                            # soften the root zone, where the hair was lifted onto the neck
            new = [row[:] for row in cen]
            for i in range(1, M):
                for j in range(0, nv // 2):
                    w_ = 1.0 - j / (nv // 2)
                    avg = (cen[i - 1][j] + cen[i][j] * 2 + cen[i + 1][j]) / 4
                    if 0 < j < nv - 1:
                        avg = (avg * 2 + cen[i][j - 1] + cen[i][j + 1]) / 4
                    new[i][j] = cen[i][j].lerp(avg, w_)
            cen = new
        for i in range(M + 1):
            for j in range(nv):
                top.append(cen[i][j] + nrms[i][j] * 0.011)
                bot.append(cen[i][j] - nrms[i][j] * 0.011)
        verts = top + bot
        faces = []
        idx = lambda i, j: i * nv + j
        nb = len(top)
        for i in range(M):
            for j in range(nv - 1):
                faces.append((idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)))
                faces.append((nb + idx(i, j + 1), nb + idx(i + 1, j + 1), nb + idx(i + 1, j), nb + idx(i, j)))
        for i in range(M):
            faces.append((idx(i, 0), nb + idx(i, 0), nb + idx(i + 1, 0), idx(i + 1, 0)))
            faces.append((idx(i + 1, nv - 1), nb + idx(i + 1, nv - 1), nb + idx(i, nv - 1), idx(i, nv - 1)))
        for j in range(nv - 1):
            faces.append((idx(0, j + 1), nb + idx(0, j + 1), nb + idx(0, j), idx(0, j)))
            faces.append((idx(M, j), nb + idx(M, j), nb + idx(M, j + 1), idx(M, j + 1)))
        p0, p1, p2 = verts[faces[0][0]], verts[faces[0][1]], verts[faces[0][3]]
        if (p1 - p0).cross(p2 - p0).y * sgn < 0:
            faces = [tuple(reversed(fc)) for fc in faces]
        return add_object("hair_sheet", verts, faces, cols + cols, self.mat_hair)

    def build_bangs(self):
        """bangs: three long locks that start at the crown and sweep down over the forehead on the near side, one short tuft on the far side"""
        specs = [(NEAR, 602, 680, 66, 28, (1, 2, 0.0), 0.05), (NEAR, 606, 672, 60, 26, (0, 1, 0.7), 0.09), (NEAR, 610, 664, 54, 26, (0, 1, 0.3), 0.13),
                 (NEAR, 600, 654, 46, 24, (0, 0, 0.0), 0.17), (NEAR, 596, 646, 38, 22, (1, 1, 0.0), 0.21), (-NEAR, 606, 650, 38, 20, (0, 1, 0.5), 0.07),
                 (NEAR, 598, 606, 106, 30, (1, 2, 0.3), 0.06), (NEAR, 590, 598, 114, 26, (0, 1, 0.6), 0.1)]          # two long locks framing the face, behind the eye
        for sgn, x0, x1, psi1, w, pal, off in specs:
            pts = []
            for i in range(17):
                u = i / 16
                x = x0 + (x1 - x0) * u ** 0.9 + 6 * math.sin(u * 6.0)
                psi = math.radians(1 + (psi1 - 1) * u ** 1.15)
                best = min(self.head_rings, key=lambda r: abs(r[0] - x))
                _, cy, vr, lat = best
                ly = cy - vr * math.cos(psi)
                surf = self.H(x, ly, sgn * lat * math.sin(psi))
                out = (surf - self.H(x, cy)).normalized()
                pts.append(surf + out * (off + 0.025 * math.sin(u * math.pi)))
            self.lock(pts, w, pal, flat=0.16, sgn=sgn)

    # ---------------------------------------------------------- wings
    def wing_layer(self, sgn, arm, tang, spec, u0, u1, length_f, layer_off, c_base, c_tip, c_edge, nfeath, depth, shoulder, spread, M=84, nv=15):
        """one row of feathers as a smooth sheet: scalloped tips, soft grooves between feathers, lying on the body near the shoulder and opening outward"""
        N = len(arm) - 1
        Lmax, ph0, ph1, dr = spec["len"], spec["phi"][0], spec["phi"][1], spec["droop"]
        raw, meta = [], []
        for i in range(M + 1):
            u = u0 + (u1 - u0) * i / M
            kf = u * N
            k0 = min(N - 1, int(kf))
            fr_ = kf - k0
            rp = (arm[k0][0] + (arm[k0 + 1][0] - arm[k0][0]) * fr_, arm[k0][1] + (arm[k0 + 1][1] - arm[k0][1]) * fr_)
            tx, ty = tang[k0][0] + (tang[k0 + 1][0] - tang[k0][0]) * fr_, tang[k0][1] + (tang[k0 + 1][1] - tang[k0][1]) * fr_
            ln = math.hypot(tx, ty) or 1
            tx, ty = tx / ln, ty / ln
            px, py = ty, -tx
            phi = math.radians(ph0 + (ph1 - ph0) * u ** 1.3)
            ang = math.degrees(math.atan2(py * math.cos(phi) + ty * math.sin(phi), px * math.cos(phi) + tx * math.sin(phi)))
            prof = 0.58 + 0.42 * math.sin(min(1.0, u / 0.7) * math.pi / 2)
            prof *= 1 - 0.34 * max(0.0, (u - 0.88) / 0.12)
            frac = ((u - u0) / (u1 - u0) * nfeath) % 1.0
            L = Lmax * prof * length_f * (1 - depth * (1 - math.sin(math.pi * frac) ** 0.7))
            c = A.hair_curve(rp, ang, L, 0.0, 0.0, dr * (0.6 + u) * length_f, nv - 1)
            raw.append([self.lat_at(P3(x, y).x, P3(x, y).z, sgn) for x, y in c])
            meta.append((u, frac, c))
        lat = [smooth_over(r, 5, 3) for r in raw]                       # along each feather
        for j in range(nv):                                             # and across neighbouring feathers
            col = smooth_over([lat[i][j] for i in range(M + 1)], 2, 2)
            for i in range(M + 1):
                lat[i][j] = col[i]
        top, bot, cols = [], [], []
        for i in range(M + 1):
            u, frac, c = meta[i]
            for j in range(nv):
                v = j / (nv - 1)
                w3 = P3(*c[j])
                d = math.hypot(w3.x - shoulder.x, w3.z - shoulder.z)
                base_lat = lat[i][j] + 0.03 + layer_off + spread * d ** 1.25 * 0.5
                bump = 0.016 * math.sin(math.pi * frac) ** 0.8 * smooth(0.12, 0.8, v)       # each feather is slightly domed
                h = 0.012
                top.append(Vector((w3.x, sgn * (base_lat + bump + h), w3.z)))
                bot.append(Vector((w3.x, sgn * (base_lat + bump - h), w3.z)))
                g = math.exp(-(min(frac, 1 - frac) / 0.07) ** 2)                            # groove between feathers
                cc = mix(srgb(c_base), srgb(c_tip), smooth(0.3, 1.0, v) * 0.85)
                cc = mix(cc, srgb(c_edge), 0.30 * g * smooth(0.12, 0.55, v))
                cc = tuple(x * (1 - 0.07 * g * smooth(0.1, 0.5, v)) for x in cc)
                cols.append(lin(cc))
        verts = top + bot
        faces = []
        idx = lambda i, j: i * nv + j
        nb = len(top)
        for i in range(M):
            for j in range(nv - 1):
                faces.append((idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)))
                faces.append((nb + idx(i, j + 1), nb + idx(i + 1, j + 1), nb + idx(i + 1, j), nb + idx(i, j)))
        for i in range(M):
            faces.append((idx(i, 0), nb + idx(i, 0), nb + idx(i + 1, 0), idx(i + 1, 0)))
            faces.append((idx(i + 1, nv - 1), nb + idx(i + 1, nv - 1), nb + idx(i, nv - 1), idx(i, nv - 1)))
        for j in range(nv - 1):
            faces.append((idx(0, j + 1), nb + idx(0, j + 1), nb + idx(0, j), idx(0, j)))
            faces.append((idx(M, j), nb + idx(M, j), nb + idx(M, j + 1), idx(M, j + 1)))
        # make the top face outward (toward this side)
        p0, p1, p2 = verts[faces[0][0]], verts[faces[0][1]], verts[faces[0][3]]
        if (p1 - p0).cross(p2 - p0).y * sgn < 0:
            faces = [tuple(reversed(fc)) for fc in faces]
        return add_object("wing_layer", verts, faces, cols + cols, self.mat_wing)

    def build_wings(self):
        P, dy = self.P, self.dy
        spec = self.pose.get("wing")
        if not spec:
            return
        root = (456, 338 + dy)
        base = P.get("wing_a", A.mixhex(P["wing"][1][1], P["wing"][2][1], 0.18))
        tip = P.get("wing_b", P["wing"][2][1])
        cov = P["wing_cov"]
        edge = P["wing_edge"]
        ctrl = [(root[0] + a, root[1] + b) for a, b in spec["arm"]]
        N = 40
        arm = A.bez(*ctrl, N)
        tang = tangents2d(arm)
        spread = spec.get("spread", 0.34 if self.pose["dy"] < 100 else 0.1)                 # how far the wing opens outward, per unit of distance from the shoulder
        shoulder = P3(*root)
        folded = self.pose["dy"] >= 100
        for sgn in (-1, 1):
            sp = spread * (1.0 if sgn == NEAR else 0.8)
            self.wing_layer(sgn, arm, tang, spec, 0.06, 1.0, 1.0, 0.0, base, tip, edge, 10, 0.20, shoulder, sp)
            self.wing_layer(sgn, arm, tang, spec, 0.04, 0.94, 0.5, 0.032, A.mixhex(base, cov, 0.6), A.mixhex(tip, cov, 0.35), edge, 9, 0.26, shoulder, sp)
            if not folded:
                self.wing_layer(sgn, arm, tang, spec, 0.02, 0.82, 0.24, 0.064, A.mixhex(cov, "#ffffff", 0.4), A.mixhex(base, cov, 0.55), edge, 8, 0.30, shoulder, sp)
            # leading edge: a smooth arm
            cut = arm[: int(0.96 * N) + 1]
            pts = []
            for i, (x, y) in enumerate(cut):
                w3 = P3(x, y)
                pts.append(Vector((w3.x, sgn * (self.lat_at(w3.x, w3.z, sgn) + 0.075 + sp * math.hypot(w3.x - shoulder.x, w3.z - shoulder.z) ** 1.25 * 0.5), w3.z)))
            rings = tube(pts, [(16 - 10 * (k / len(cut))) * S for k in range(len(cut))], flat=0.6, segs=8, up=Y)
            v, f = loft(rings)
            add_object("wingarm", v, f, [lin(srgb(cov))] * len(v), self.mat_wing)

    # ---------------------------------------------------------- flowers
    def flower(self, c, nrm, size, kind=0, rot=0.0, leaves=3):
        """a five-six petal flower lying on a surface with normal nrm: two rings of cupped petals, a centre with stamens, a few leaves"""
        P = self.P
        nrm = nrm.normalized()
        ref = Vector((0, 0, 1)) if abs(nrm.z) < 0.9 else Vector((1, 0, 0))
        u = nrm.cross(ref).normalized()
        v = nrm.cross(u).normalized()
        pal = ((P["petal_a"], "#ffe2b0"), (P["petal_b"], "#ffdbe9"), (P["petal_c"], "#ffffff"))[kind % 3]
        for ring, (count, sc, tilt, off, wk) in enumerate(((6, 1.0, 0.30, 0.0, 0.64), (5, 0.7, 0.62, 0.5, 0.7))):
            for i in range(count):
                a = rot + 2 * math.pi * (i + off) / count
                rad = u * math.cos(a) + v * math.sin(a)
                axis = (rad * math.cos(tilt) + nrm * math.sin(tilt)).normalized()
                L, W, T = size * sc, size * sc * wk, size * sc * 0.15
                side = nrm.cross(axis).normalized()
                thick = axis.cross(side).normalized()
                cen = c + nrm * (size * (0.04 + 0.05 * ring)) + axis * (L * 0.46)
                vs, fs = ellipsoid(cen, axis * (L / 2), side * (W / 2), thick * (T / 2), 14, 9)
                cols = []
                for p in vs:
                    t = max(0.0, min(1.0, (p - c).dot(axis) / L))
                    cols.append(lin(mix(srgb(pal[1]), srgb(pal[0]), 0.25 + 0.75 * smooth(0.1, 0.95, t))))
                add_object("petal", vs, fs, cols, self.mat_flower)
        vs, fs = ellipsoid(c + nrm * (size * 0.16), u * (size * 0.17), v * (size * 0.17), nrm * (size * 0.12), 12, 8)
        add_object("fcentre", vs, fs, [lin(srgb("#ffe08c"))] * len(vs), self.mat_flower)
        for i in range(9):
            a = 2 * math.pi * i / 9
            q = c + nrm * (size * 0.27) + (u * math.cos(a) + v * math.sin(a)) * (size * 0.1)
            vs, fs = ellipsoid(q, u * (size * 0.025), v * (size * 0.025), nrm * (size * 0.03), 6, 5)
            add_object("stamen", vs, fs, None, self.mat_stamen)
        for i in range(leaves):
            a = rot + 2 * math.pi * (i + 0.5) / leaves + 0.5
            rad = u * math.cos(a) + v * math.sin(a)
            axis = (rad * math.cos(0.12) + nrm * math.sin(0.12)).normalized()
            L, W = size * 1.15, size * 0.5
            side = nrm.cross(axis).normalized()
            thick = axis.cross(side).normalized()
            cen = c + axis * (L * 0.5) - nrm * (size * 0.02)
            vs, fs = ellipsoid(cen, axis * (L / 2), side * (W / 2), thick * (size * 0.05), 14, 9)
            cols = [lin(mix(srgb(P["leaf_a"]), srgb(P["leaf_b"]), max(0.0, min(1.0, (p - c).dot(axis) / L)))) for p in vs]
            add_object("leaf", vs, fs, cols, self.mat_leaf)

    def bvh_of(self, objs):
        verts, faces = [], []
        for ob in objs:
            me = ob.data
            base = len(verts)
            verts.extend([tuple(ob.matrix_world @ v.co) for v in me.vertices])
            faces.extend([tuple(i + base for i in p.vertices) for p in me.polygons])
        return BVHTree.FromPolygons(verts, faces)

    def rest_on(self, bvh, target, out, lift=0.02):
        """the outermost surface point along -out through target (hair or skin), so a flower rests on it"""
        hit = bvh.ray_cast(target + out * 1.5, -out)
        if hit[0] is None:
            return target
        return hit[0] + out * lift

    def build_crown(self):
        """flowers at the base of the horn: a cluster on the near side, one small flower tucked in on the far side"""
        hs = self.hs
        crown_bvh = self.bvh_of([ob for ob in self.head_group if ob.name.startswith(("head", "lock", "ear"))])
        for sgn, x, psi, size, kind, rot in ((NEAR, 606, 44, 0.44, 0, 0.3), (NEAR, 624, 66, 0.22, 1, 1.0), (NEAR, 600, 62, 0.2, 2, 0.1), (-NEAR, 618, 60, 0.17, 1, 1.9)):
            best = min(self.head_rings, key=lambda r: abs(r[0] - x))
            _, cy, vr, lat = best
            ps = math.radians(psi)
            surf = self.H(x, cy - vr * math.cos(ps), sgn * lat * math.sin(ps))
            out = (surf - self.H(x, cy)).normalized()
            self.flower(self.rest_on(crown_bvh, surf, out, 0.03 * size / 0.44), (out + self.upv * 0.4 + self.fwd * 0.2).normalized(), size * hs, kind, rot, 4 if size > 0.2 else 2)

    def build_flowers(self):
        body_bvh = self.bvh_of([ob for ob in bpy.data.objects if ob.type == "MESH" and ob.name.startswith(("body", "hair_sheet", "crest_mane"))])
        # garland on the back: a cluster on the near side, one small flower on the far side
        for sgn, X, dz, size, kind, rot in ((NEAR, 418, 0.3, 0.3, 1, 0.2), (NEAR, 370, 0.34, 0.42, 0, 0.9), (NEAR, 326, 0.38, 0.28, 2, 0.5), (NEAR, 396, 0.62, 0.22, 0, 1.4),
                                            (-NEAR, 352, 0.4, 0.16, 1, 0.7)):
            xw = (X - 400) * S
            top, bot = slice_at(self.torso_poly, X)
            z = (640 - top) * S - dz
            hit = body_bvh.ray_cast(Vector((xw, sgn * 4.0, z)), Vector((0, -sgn, 0)))
            if hit[0] is None:
                continue
            nrm = hit[1] if hit[1].y * sgn > 0 else -hit[1]
            self.flower(hit[0] + nrm * 0.015, (nrm + Vector((0, 0, 0.5))).normalized(), size, kind, rot, 4 if size > 0.2 else 2)
        # cuffs of small flowers above the hooves: each leg has its own count and sizes
        rnd = random.Random(23)
        for k, (c, ax, ra, bb, rb) in enumerate(self.pasterns):
            n = rnd.choice((6, 7, 8))
            a0 = rnd.uniform(0, 6.28)
            for i in range(n):
                a = a0 + 2 * math.pi * i / n
                rad = ax * math.cos(a) + Y * math.sin(a)
                self.flower(c + rad * (max(ra, rb) * 0.98), rad, rnd.uniform(0.1, 0.145), (i + k + rnd.randrange(3)) % 3, a, 0)

    # ---------------------------------------------------------- cutie mark
    def build_decals(self):
        P = self.P
        ctr = P3(334, 420 + self.dy)
        for sgn in (-1, 1):
            hit = self.bvh.ray_cast(ctr + Vector((0, sgn * 3.0, 0)), Vector((0, -sgn, 0)))
            if hit[0] is None:
                continue
            cen, nrm = hit[0], hit[1]
            ax_v = nrm.cross(Vector((0, 0, 1))).normalized()
            ax_u = ax_v.cross(nrm).normalized()
            rot = math.radians(-12)
            for rr, mat, push in ((0.21, self.mat_mark, 0.012), (0.08, self.mat_white, 0.02)):
                verts, faces = [], []
                rings_n, ang_n = 7, 48
                for ri in range(rings_n + 1):
                    for ak in range(ang_n):
                        a_ = 2 * math.pi * ak / ang_n
                        rho = rr * (0.16 + 0.84 * abs(math.cos(2 * (a_ - rot))) ** 3.2) if ri else 0.0
                        rad = rho * (ri / rings_n) if ri else 0.0
                        q = cen + (ax_u * math.cos(a_) + ax_v * math.sin(a_)) * rad
                        h2 = self.bvh.ray_cast(q + nrm * 0.5, -nrm)
                        verts.append((h2[0] + h2[1] * push) if h2[0] is not None else q)
                for ri in range(rings_n):
                    for ak in range(ang_n):
                        a2 = (ak + 1) % ang_n
                        faces.append((ri * ang_n + ak, ri * ang_n + a2, (ri + 1) * ang_n + a2, (ri + 1) * ang_n + ak))
                add_object("star", verts, faces, None, mat)

    def sparkles_head(self):
        """glitter freckles on the cheek: a handful on the near side, two stragglers on the far side"""
        rnd = random.Random(31)
        mat = material("glitter", rough=0.25, vc=False, color=(1, 1, 1), spec=0.8, emit=1.4)
        spots = [(644, 258, 0.034, NEAR), (656, 250, 0.026, NEAR), (664, 266, 0.03, NEAR), (650, 272, 0.022, NEAR), (634, 252, 0.02, NEAR),
                 (668, 248, 0.018, NEAR), (638, 268, 0.02, NEAR), (652, 262, 0.02, -NEAR), (662, 254, 0.016, -NEAR)]
        for x, y, r, sgn in spots:
            x += rnd.uniform(-3, 3)
            y += rnd.uniform(-3, 3)
            p = self.head_surface(x, y, sgn)
            out = (p - self.H(x, y)).normalized()
            v, f = ellipsoid(p + out * 0.002, Vector((r * self.hs, 0, 0)), Vector((0, 0, r * self.hs)), out * (r * self.hs * 0.5), 10, 8)
            add_object("sparkle", v, f, None, mat)

    def sparkles(self):
        """glitter on the body and legs, scattered differently on each side"""
        rnd = random.Random(11)
        mat = material("glitter", rough=0.25, vc=False, color=(1, 1, 1), spec=0.8, emit=1.4)
        for sgn, count in ((NEAR, 16), (-NEAR, 9)):
            for k in range(count):
                x = rnd.uniform(-1.3, 1.1)
                z = rnd.uniform(0.9, 3.3) if k % 3 else rnd.uniform(0.5, 1.6)
                hit = self.bvh.ray_cast(Vector((x, sgn * 4.0, z)), Vector((0, -sgn, 0)))
                if hit[0] is None:
                    continue
                r = rnd.uniform(0.014, 0.03)
                nrm = hit[1] if hit[1].y * sgn > 0 else -hit[1]
                v, f = ellipsoid(hit[0] + nrm * 0.002, Vector((r, 0, 0)), Vector((0, 0, r)), nrm * (r * 0.5), 10, 8)
                add_object("sparkle", v, f, None, mat)

    # ---------------------------------------------------------- ground shadow
    def build_ground(self):
        me = bpy.data.meshes.new("ground")
        me.from_pydata([(-30, -30, GROUND_Z), (30, -30, GROUND_Z), (30, 30, GROUND_Z), (-30, 30, GROUND_Z)], [], [(0, 1, 2, 3)])
        ob = bpy.data.objects.new("ground", me)
        bpy.context.collection.objects.link(ob)
        ob.is_shadow_catcher = True


def render_job(P, pose, view, out, quick, traits=None, tag=""):
    sc = K.setup_scene(quick)
    Uni3D(P, pose, traits or TRAITS)
    zoom = None
    if "@" in view:                                   # e.g. front@2.7,4.4,2.4 : close-up around world x,z with this ortho scale
        view, zz = view.split("@")
        zoom = [float(v) for v in zz.split(",")]
    center = Vector((0, 0, 3.05)) if zoom is None else Vector((zoom[0], 0, zoom[1]))
    tgt = bpy.data.objects.new("target", None)
    bpy.context.collection.objects.link(tgt)
    tgt.location = center
    az = {"side": 0, "front": 90, "back": -90, "three": 40}[view]
    cam = K.make_camera(sc, az, center, ortho=8.0 if zoom is None else zoom[2])
    pitch = math.radians(9)
    a = math.radians(az)
    cam.location = center + Vector((math.sin(a) * math.cos(pitch), -math.cos(a) * math.cos(pitch), math.sin(pitch))) * 40.0
    cam.rotation_euler = (math.radians(90) - pitch, 0, a)
    K.add_lights(cam, tgt)
    top = bpy.data.lights.new("top", "AREA")
    top.energy, top.size = 420, 12.0
    tob = bpy.data.objects.new("top", top)
    bpy.context.collection.objects.link(tob)
    tob.location = (0.5, 0.3, 11.0)
    bnc = bpy.data.lights.new("bounce", "AREA")                # soft light bouncing up from the meadow, so the gap under the belly is not black
    bnc.energy, bnc.size, bnc.color = 520, 16.0, (1.0, 0.95, 0.97)
    bob = bpy.data.objects.new("bounce", bnc)
    bpy.context.collection.objects.link(bob)
    bob.location = (1.0, -8.0, 0.9)
    bc = bob.constraints.new("TRACK_TO")
    bc.target, bc.track_axis, bc.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
    tc = tob.constraints.new("TRACK_TO")
    tc.target, tc.track_axis, tc.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
    hide = os.environ.get("UNI_HIDE")                          # debugging: hide objects whose name starts with any of these (comma separated)
    if hide:
        for ob in bpy.data.objects:
            if ob.name.startswith(tuple(hide.split(","))):
                ob.hide_render = True
    sc.view_settings.exposure = -0.3                           # keep the pale coat from blowing out to plain white
    sc.render.filepath = os.path.join(out, f"{pose}-{view}{tag}{'-z%d' % round(zoom[0] * 10) if zoom else ''}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", sc.render.filepath)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = argv[0]
    quick = "--quick" in argv
    jobs = [a for a in argv[1:] if ":" in a] or ["stand:side", "stand:three", "stand:front", "stand:back", "prance:side", "prance:three", "sleep:side", "sleep:three"]
    for job in jobs:
        pose, view = job.split(":")
        if "--wings" in argv:
            render_job(BLOOM, pose, view, out, quick, dict(TRAITS, wings=True), "-wings")
        else:
            render_job(BLOOM, pose, view, out, quick)
