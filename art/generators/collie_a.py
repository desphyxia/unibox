"""Border collie A, "the toy collie": a chibi tricolour collie (black, white and tan) built as one sculpted shape, its
fluffy coat sculpted into the shape itself as soft pointed tufts (ruff, cheeks, chest, crown, tail, leg feathers)
instead of strands, finished with a velvety coat material. Direction: two collie pictures the user shared (used as
direction only, nothing copied or traced). Built from scratch; it shares only generic helpers (the scene, the mesher
and the shape primitives) with the other generators.

Axes (Blender): x forward, y across (+y the near side, toward the camera), z up; ground z = 0.
Run:   blender -b --factory-startup -P collie_a.py -- OUTDIR [--quick] [--clay] [--head-only] [view ...]
       views: hero head front side"""
import bpy, math, os, sys
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import unicorn2 as Ub
from unicorn2_shape import sphere, ellipsoid, round_cone, smin, smax, rot, sample, surface_nets, project, grad

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "collie_a_out"
QUICK = "--quick" in argv
CLAY = "--clay" in argv
HEAD_ONLY = "--head-only" in argv
VIEWS = [a for a in argv[1:] if not a.startswith("--")] or ["hero"]
H = 0.024 if QUICK else 0.011
hexc, mix, smooth = Ub.hexc, Ub.mix, Ub.smooth
Ub.CLAY = CLAY

# ------------------------------------------------------------------ the head (head-local; turned as a whole later)
PIVOT = np.array([0.2, 0.0, 2.35])
TURN = rot((0, 0, 1), 16.0) @ rot((0, 1, 0), -3.0) @ rot((1, 0, 0), 8.0)     # toward the viewer, chin up, a tilt


DROP = np.array([0.0, 0.0, -0.5])                              # the head sits low on a short neck (chibi)


def to_world(L):
    return PIVOT + DROP + (np.asarray(L) - PIVOT) @ TURN.T


def to_head(P):
    return PIVOT + (P - DROP - PIVOT) @ TURN


def hdir(v):
    return np.asarray(v) @ TURN.T


CRAN = (np.array([0.25, 0.0, 3.0]), np.array([0.86, 0.82, 0.8]))
MUZZLE = (np.array([1.02, 0.0, 2.68]), np.array([0.5, 0.42, 0.32]))
NOSE = (np.array([1.5, 0.0, 2.8]), np.array([0.12, 0.155, 0.1]))
EYE_R = 0.235


def head_base(L):
    c, r = CRAN
    d = ellipsoid(L, c, r)
    d = smin(d, ellipsoid(L, np.array([0.66, 0.0, 3.1]), (0.48, 0.56, 0.46)), 0.28)    # the brow and stop
    d = smin(d, ellipsoid(L, np.array([0.55, 0.0, 2.6]), (0.5, 0.66, 0.42)), 0.25)     # full cheeks
    d = smin(d, ellipsoid(L, MUZZLE[0], MUZZLE[1]), 0.28)
    d = smin(d, ellipsoid(L, np.array([1.02, 0.0, 2.44]), (0.34, 0.3, 0.16)), 0.12)    # the chin
    return d


def ray_hit(fn, o, d, lo=0.0, hi=3.0):
    o = np.asarray(o, np.float64)
    d = np.asarray(d, np.float64) / np.linalg.norm(d)
    for _ in range(60):
        m = (lo + hi) / 2
        if fn((o + d * m)[None])[0] < 0:
            lo = m
        else:
            hi = m
    return o + d * lo


def eye_spot(side):
    """where an eye sits on the head and its outward direction (head-local)"""
    c, _ = CRAN
    E = ray_hit(head_base, c, np.array([0.86, 0.46 * side, 0.12]))
    n = grad(head_base, E[None])[0]
    return E, n


EYES = {s: eye_spot(s) for s in (1, -1)}


def eye_centre(side):
    E, n = EYES[side]
    return E - n * (EYE_R * 0.62)                              # a big dome standing out of the face


# the mouth: a small smile under the nose, the two halves curving out from the philtrum, slightly open in the middle
def smile_pts(n=40):
    """a small dog mouth under the nose: the philtrum down from the nose, then a curve out to each side, the corners
    turning up into a smile"""
    pts = []
    o = np.array([0.9, 0.0, 2.62])
    for t in np.linspace(0, 1, 8):                       # the philtrum
        pts.append(ray_hit(head_base, o, np.array([1.5, 0.0, 2.69 - 0.1 * t]) - o))
    half = []
    for t in np.linspace(0, 1, n // 2):
        y = 0.21 * t
        x = 1.47 - 0.17 * t ** 1.6
        z = 2.59 - 0.035 * np.sin(np.pi * t) + 0.055 * t ** 2.4
        half.append((x, y, z))
    for sgn in (1, -1):
        for (x, y, z) in half:
            pts.append(ray_hit(head_base, o, np.array([x, y * sgn, z]) - o))
    return np.array(pts)


SMILE = None
MOUTH_OPEN = (np.array([1.42, 0.0, 2.565]), np.array([0.07, 0.1, 0.04]))


def seg_dist(P, pts):
    d = np.full(len(P), 9.0)
    segs = [(pts[i], pts[i + 1]) for i in range(7)]                     # the philtrum
    m = (len(pts) - 8) // 2
    for k in (0, 1):
        side = pts[8 + k * m: 8 + (k + 1) * m]
        segs += [(pts[7], side[0])] + [(side[i], side[i + 1]) for i in range(m - 1)]
    for a, b in segs:
        ab = b - a
        t = np.clip(((P - a) @ ab) / (ab @ ab), 0, 1)
        d = np.minimum(d, np.linalg.norm(P - (a + t[:, None] * ab), axis=1))
    return d


def head_carved(L):
    global SMILE
    if SMILE is None:
        SMILE = smile_pts()
    d = head_base(L)
    near = np.linalg.norm(L - np.array([1.3, 0.0, 2.6]), axis=1) < 0.6
    if near.any():
        s = np.full(len(L), 9.0)
        s[near] = seg_dist(L[near], SMILE)
        d = smax(d, -(s - 0.018), 0.012)
        c, r = MOUTH_OPEN
        d = smax(d, -ellipsoid(L, c, r), 0.03)
    return d


# ------------------------------------------------------------------ ears: big, semi-pricked, the tips folding forward
def ear_frame(side):
    c, _ = CRAN
    base = ray_hit(head_base, c, np.array([-0.15, 0.6 * side, 0.8]))
    up = np.array([-0.05, 0.4 * side, 1.0])
    up /= np.linalg.norm(up)
    fwd = np.array([1.0, 0.15 * side, 0.0])
    fwd -= up * (fwd @ up)
    fwd /= np.linalg.norm(fwd)
    return base, up, fwd, np.cross(up, fwd)


EARS = {s: ear_frame(s) for s in (1, -1)}
EAR_H, EAR_W, FOLD = 0.9, 0.36, 0.56


def frame_ellipsoid(P, c, axes, radii):
    q = (P - c) @ np.array(axes).T
    return ellipsoid(q, np.zeros(3), radii)


def ear_parts(side):
    """the ear as an upright cupped lower part and a tip folding forward over it, in world-free head-local terms"""
    base, up, fwd, acr = EARS[side]
    f = EAR_H * FOLD
    lower_c = base + up * (f * 0.5)
    hinge = base + up * f
    ang = np.radians(58.0)
    tip_dir = up * np.cos(ang) + fwd * np.sin(ang)        # the tip leans forward and down
    tip_n = fwd * np.cos(ang) - up * np.sin(ang)
    tip_c = hinge + tip_dir * (EAR_H - f) * 0.48 + tip_n * 0.02
    return base, up, fwd, acr, lower_c, hinge, tip_c, tip_dir, tip_n


def ear_sdf(L, side):
    base, up, fwd, acr, lower_c, hinge, tip_c, tip_dir, tip_n = ear_parts(side)
    f = EAR_H * FOLD
    lower = frame_ellipsoid(L, lower_c, (acr, up, fwd), (EAR_W, f * 0.62, 0.075))
    tip = frame_ellipsoid(L, tip_c, (acr, tip_dir, tip_n), (EAR_W * 0.6, (EAR_H - f) * 0.7, 0.055))
    d = smin(lower, tip, 0.1)
    cup = frame_ellipsoid(L, lower_c + fwd * 0.07 + up * 0.03, (acr, up, fwd), (EAR_W * 0.7, f * 0.48, 0.05))
    return smax(d, -cup, 0.03)


# ------------------------------------------------------------------ fur tufts: soft pointed clumps blended into the shape
TUFTS = []                                                       # (root, tip, root radius, kind) head-local or world


def tuft_ring(fn, centre_fn, n, length, radius, comb, rng, jitter=0.25, kind="coat"):
    for _ in range(n):
        p, dirn = centre_fn(rng)
        root = project(fn, p[None], 4)[0]
        nn = grad(fn, root[None])[0]
        d = nn * 0.22 + comb + rng.normal(0, jitter * 0.6, 3)
        d /= np.linalg.norm(d)
        ln = length * rng.uniform(0.75, 1.2)
        TUFTS.append((root - nn * radius * 0.6, root + d * ln, radius * rng.uniform(0.8, 1.2), kind))


def tufts_sdf(P, items):
    d = np.full(len(P), 9.0)
    for a, b, r, _ in items:
        lo = np.minimum(a, b) - r - 0.05
        hi = np.maximum(a, b) + r + 0.05
        m = np.all((P >= lo) & (P <= hi), axis=1)
        if not m.any():
            continue
        x = round_cone(P[m], a, b, r, r * 0.38)
        d[m] = smin(d[m], x, 0.08)
    return d


# ------------------------------------------------------------------ the body (world)
def body_base(P):
    chest = ellipsoid(P, np.array([0.1, 0.0, 1.05]), (0.66, 0.64, 0.78))
    rump = ellipsoid(P, np.array([-0.38, 0.0, 0.6]), (0.68, 0.7, 0.6))
    d = smin(chest, rump, 0.35)
    for s in (1, -1):
        d = smin(d, round_cone(P, np.array([0.36, 0.28 * s, 0.8]), np.array([0.48, 0.3 * s, 0.2]), 0.19, 0.16), 0.12)
        d = smin(d, ellipsoid(P, np.array([0.58, 0.31 * s, 0.12]), (0.25, 0.18, 0.13)), 0.08)        # front paws
        d = smin(d, ellipsoid(P, np.array([-0.36, 0.48 * s, 0.5]), (0.5, 0.29, 0.42)), 0.2)          # haunches
        d = smin(d, ellipsoid(P, np.array([0.1, 0.57 * s, 0.11]), (0.26, 0.18, 0.12)), 0.1)          # hind paws
    d = smin(d, round_cone(P, np.array([0.12, 0.0, 1.55]), np.array([0.18, 0.0, 2.0]), 0.48, 0.44), 0.25)   # neck
    return d


TAIL = np.array([(-0.95, 0.0, 0.45), (-1.25, 0.12, 0.22), (-1.32, 0.45, 0.13), (-1.12, 0.76, 0.12), (-0.8, 0.9, 0.18)])


def tail_curve(m=30):
    t = np.linspace(0, 1, len(TAIL))
    s = np.linspace(0, 1, m)
    c = np.stack([np.interp(s, t, TAIL[:, k]) for k in range(3)], 1)
    for _ in range(5):
        c[1:-1] = (c[:-2] + 2 * c[1:-1] + c[2:]) / 4
    return c


def tail_sdf(P):
    c = tail_curve()
    d = np.full(len(P), 9.0)
    m = len(c)
    for i in range(m - 1):
        r1 = 0.2 * (1 - i / m) + 0.1
        r2 = 0.2 * (1 - (i + 1) / m) + 0.1
        d = smin(d, round_cone(P, c[i], c[i + 1], r1, r2), 0.05)
    return d


def make_tufts(rng):
    """every tuft, from the base shapes: placed by region (counts and sizes are the coat's look)"""
    TUFTS.clear()
    hb = head_base
    c, r = CRAN
    # the crown and back of the head: small, combed back
    def crown(rng):
        a = rng.uniform(-np.pi, np.pi)
        e = rng.uniform(0.1, 1.2)
        d = np.array([-0.4 + 0.5 * np.cos(e), np.sin(a) * 0.8, np.cos(a) * 0.6 + 0.5])
        return c + d * 0.6, d
    tuft_ring(hb, crown, 34 if not QUICK else 20, 0.18, 0.11, np.array([-0.9, 0.0, -0.3]), rng, jitter=0.12, kind="head")
    # the cheeks: big fluffy clumps fanning out and back below the eyes
    for s in (1, -1):
        def cheek(rng, s=s):
            p = np.array([0.35 + rng.uniform(-0.25, 0.15), (0.72 + rng.uniform(-0.05, 0.1)) * s, 2.5 + rng.uniform(-0.25, 0.2)])
            return p, None
        tuft_ring(hb, cheek, 16 if not QUICK else 10, 0.3, 0.14, np.array([-0.8, 0.3 * s, -0.5]), rng, jitter=0.12, kind="head")
    TUFTS_head = list(TUFTS)
    TUFTS.clear()
    # the bib: three rows of big soft scallops down the front of the neck and chest
    for row, (z, n, ln, r) in enumerate(((1.75, 7, 0.36, 0.2), (1.38, 6, 0.32, 0.19), (1.02, 5, 0.26, 0.17))):
        for k in range(n):
            a = (k - (n - 1) / 2) / ((n - 1) / 2) * 1.05
            p = np.array([0.15 + 0.62 * np.cos(a), 0.6 * np.sin(a), z + 0.04 * rng.normal()])
            root = project(body_base, p[None], 4)[0]
            nn = grad(body_base, root[None])[0]
            d = nn * 0.35 + np.array([0.15, 0.25 * np.sin(a), -1.0])
            d /= np.linalg.norm(d)
            TUFTS.append((root - nn * 0.08, root + d * ln * rng.uniform(0.9, 1.1), r * rng.uniform(0.9, 1.1), "bib"))
    # the coat over the back and sides: broad, short lobes combed down and back
    for k in range(26 if not QUICK else 18):
        a = rng.uniform(0.9, 2 * np.pi - 0.9)
        p = np.array([-0.2 + 0.7 * np.cos(a), 0.68 * np.sin(a), rng.uniform(0.75, 1.75)])
        root = project(body_base, p[None], 4)[0]
        nn = grad(body_base, root[None])[0]
        d = nn * 0.3 + np.array([-0.5, 0.0, -1.0])
        d /= np.linalg.norm(d)
        TUFTS.append((root - nn * 0.08, root + d * rng.uniform(0.22, 0.32), rng.uniform(0.15, 0.19), "coat"))
    # the tail: clumps all along it, longer in the middle, pointing toward its tip
    tc = tail_curve(60)
    T_ = np.gradient(tc, axis=0)
    for _ in range(90 if not QUICK else 45):
        i = rng.integers(2, len(tc) - 2)
        a = rng.uniform(0, 2 * np.pi)
        side = np.cross(T_[i], [0, 0, 1.0]); side /= np.linalg.norm(side) + 1e-9
        up = np.cross(side, T_[i] / np.linalg.norm(T_[i]))
        out = side * np.cos(a) + up * np.sin(a)
        root = tc[i] + out * 0.12
        d = T_[i] / np.linalg.norm(T_[i]) * 0.9 + out * 0.6
        d /= np.linalg.norm(d)
        ln = 0.35 * np.sin(np.pi * (i / len(tc)) ** 0.8) + 0.12
        TUFTS.append((root - out * 0.04, root + d * ln, 0.1, "tail"))
    world = list(TUFTS)
    TUFTS.clear()
    return TUFTS_head, world


HEAD_TUFTS, BODY_TUFTS = [], []


def head_full(L):
    d = head_carved(L)
    d = smin(d, tufts_sdf(L, HEAD_TUFTS), 0.05)
    for s in (1, -1):
        d = smin(d, ear_sdf(L, s), 0.07)
    return d


def sdf(P):
    L = to_head(P)
    d = head_full(L)
    if HEAD_ONLY:
        return smax(d, P[:, 2] - 99, 0.01)
    b = smin(body_base(P), tufts_sdf(P, BODY_TUFTS), 0.05)
    b = smin(b, tail_sdf(P), 0.1)
    return smin(d, b, 0.25)


def base_sdf(P):
    """the shape before tufts (for colours: a tuft takes the colour of the coat it grows from)"""
    L = to_head(P)
    d = smin(head_base(L), ear_sdf(L, 1), 0.07)
    d = smin(d, ear_sdf(L, -1), 0.07)
    if HEAD_ONLY:
        return d
    return smin(d, smin(body_base(P), tail_sdf(P), 0.1), 0.25)


# ------------------------------------------------------------------ colours
BLACK, BLACK2 = hexc("#141113"), hexc("#2b2527")
WHITE, WHITE2 = hexc("#fbf8f2"), hexc("#e9e3db")
TAN, TAN2 = hexc("#a85a2a"), hexc("#c98448")
NOSE_C = hexc("#18151a")


def colours(V, N):
    """the tricolour coat. Each point is coloured from where it grows: pulled back onto the base shape"""
    B = project(base_sdf, V, 3)
    L = to_head(B)
    n = len(V)
    c = mix(np.tile(BLACK, (n, 1)), BLACK2, smooth(0.0, 0.8, N[:, 2]) * 0.6)
    hd = smin(head_base(L), smin(ear_sdf(L, 1), ear_sdf(L, -1), 0.07), 0.07)
    if HEAD_ONLY:
        head = np.ones(n)
    else:
        bd = smin(body_base(B), tail_sdf(B), 0.1)
        head = smooth(0.05, -0.05, hd - bd)
    y, x, z = L[:, 1], L[:, 0], L[:, 2]
    # tan: big eyebrow spots, the cheeks below the eyes
    for s in (1, -1):
        E, nn = EYES[s]
        brow = E + np.array([-0.05, 0.03 * s, 0.31])
        d = np.linalg.norm((L - brow) / np.array([0.15, 0.13, 0.09]), axis=1)
        c = mix(c, TAN, smooth(1.0, 0.6, d) * head)
        ck = np.array([0.72, 0.52 * s, 2.58])
        d = np.linalg.norm((L - ck) / np.array([0.34, 0.26, 0.24]), axis=1)
        c = mix(c, mix(TAN, TAN2, 0.3), smooth(1.0, 0.55, d) * head)
    # white: a blaze up the middle of the face widening over the muzzle, the muzzle and chin
    bw = 0.055 + 0.04 * smooth(0.5, 0.1, x) + 0.3 * smooth(0.9, 1.2, x)
    blaze = smooth(bw + 0.03, bw - 0.02, np.abs(y)) * smooth(2.45, 2.6, z) * smooth(3.7, 3.5, z)
    muz = smooth(0.92, 1.05, x) * smooth(0.5 + 0.1 * smooth(1.2, 1.5, x), 0.38, np.abs(y)) * smooth(2.95, 2.83, z)
    chin = smooth(2.6, 2.45, z) * smooth(0.6, 0.85, x)
    w = np.maximum(blaze, np.maximum(muz, chin)) * head
    sm = seg_dist(L, SMILE) if SMILE is not None else np.full(n, 9.0)
    if not HEAD_ONLY:
        body = 1 - head
        # the bib: the front of the neck and chest; the front legs; the paws; the tail tip
        front = smooth(0.35, 0.65, (B[:, 0] - 0.1) / (np.abs(B[:, 1]) + 0.35))
        w = np.maximum(w, body * front * smooth(0.55, 0.8, B[:, 2]))
        w = np.maximum(w, body * smooth(0.3, 0.2, B[:, 2]))
        legs = body * smooth(0.95, 0.75, B[:, 2]) * smooth(0.2, 0.32, B[:, 0]) * smooth(0.5, 0.36, np.abs(B[:, 1]))
        w = np.maximum(w, legs)
        tc = tail_curve(60)
        dt = np.linalg.norm(B[:, None, :] - tc[None, -14:, :], axis=2).min(1)
        w = np.maximum(w, body * smooth(0.3, 0.2, dt))
        c = mix(c, TAN, body * smooth(0.7, 0.5, B[:, 2]) * smooth(0.25, 0.35, B[:, 2]) * smooth(0.1, -0.3, B[:, 0])
                * (np.abs(B[:, 1]) > 0.3))
    wc = mix(np.tile(WHITE, (n, 1)), WHITE2, smooth(0.2, -0.6, N[:, 2]) * 0.5)
    c = mix(c, wc, w)
    c = mix(c, hexc("#3a2a2e"), smooth(0.04, 0.018, sm) * head)              # the smile line
    # inside the ears: soft brown skin, tan fluff at the base
    for s in (1, -1):
        base, up, fwd, acr = EARS[s]
        q = L - base
        u, v, ww = q @ up, q @ acr, q @ fwd
        f = EAR_H * FOLD
        inner = (smooth(0.0, 0.04, ww) * smooth(EAR_W * 0.72, EAR_W * 0.45, np.abs(v)) * smooth(0.0, 0.08, u)
                 * smooth(f + 0.02, f - 0.12, u))
        skin = mix(np.tile(hexc("#6e4a46"), (n, 1)), TAN, smooth(0.3, 0.05, u) * 0.8)
        c = mix(c, skin, inner * (np.linalg.norm(L - base, axis=1) < EAR_H * 1.1))
    return c


# ------------------------------------------------------------------ eyes, nose, mouth parts
def build_face():
    dark = Ub.material("lid", rough=0.45, spec=0.3, color=hexc("#0f0c0d"))
    for side in (1, -1):
        c = eye_centre(side)
        E, n = EYES[side]
        look = n + np.array([0.3, -0.12 * side, 0.02])
        look /= np.linalg.norm(look)
        up = np.array([0.0, 0.0, 1.0]) - look * look[2]
        up /= np.linalg.norm(up)
        Vs, Fs = Ub.uv_sphere(np.zeros(3), EYE_R, 64, 40)
        d = Vs / EYE_R
        ca = d @ look
        h = d @ up
        iris = smooth(np.cos(np.radians(60)), np.cos(np.radians(57)), ca)
        pupil = smooth(np.cos(np.radians(33)), np.cos(np.radians(30)), ca)
        rim = smooth(np.cos(np.radians(51)), np.cos(np.radians(58)), ca) * iris
        ic = mix(hexc("#d08a3e"), hexc("#5a2c10"), smooth(-0.55, 0.45, h))
        ic = mix(ic, hexc("#2a1306"), rim * 0.85)
        ic = mix(ic, hexc("#080506"), pupil)
        col = mix(hexc("#2a1a14"), ic, iris)
        Ub.add_mesh("eye", to_world(c + Vs), Fs, col, Ub.material("eye", rough=0.12, spec=0.7, coat=1.0))
        for du, dv, rr in ((0.45, 0.5, 0.075), (-0.35, -0.42, 0.032), (0.1, 0.62, 0.025)):
            a = np.cross(look, up)
            dirn = look + a * du * 0.6 + up * dv * 0.6
            dirn /= np.linalg.norm(dirn)
            gc = c + dirn * (EYE_R + 0.003)
            ga = np.cross(dirn, up); ga /= np.linalg.norm(ga)
            gb = np.cross(ga, dirn)
            Vg = [gc] + [gc + (ga * np.cos(t) + gb * np.sin(t) * 0.8) * rr for t in np.linspace(0, 2 * np.pi, 18, endpoint=False)]
            Ub.add_mesh("glint", to_world(np.array(Vg)), [(0, k + 1, (k + 1) % 18 + 1) for k in range(18)], None,
                        Ub.material("glint", emit=5.0, color=(1, 1, 1, 1)))
        # a soft dark upper lid hugging the top of the eye
        ring = []
        for t in np.linspace(np.radians(15), np.radians(165), 30):
            a = np.cross(look, up)
            p = c + (np.cos(t) * a + np.sin(t) * up) * (EYE_R * 1.01) * np.array([1, 1, 1]) + look * EYE_R * 0.2
            ring.append(p)
        ring = np.array(ring)
        rad = 0.012 + 0.016 * np.sin(np.linspace(0, np.pi, len(ring)))
        Vt, Ft = Ub.tube(ring, rad, 8)
        Ub.add_mesh("lid", to_world(Vt), Ft, None, dark)
    # the nose: a rounded triangle of glossy leather with nostrils, a highlight on top
    c, r = NOSE
    Vn, Fn = Ub.uv_sphere(np.zeros(3), 1.0, 48, 28)
    sh = Vn.copy()
    sh[:, 1] *= 1.0 - 0.28 * np.clip(-Vn[:, 2], 0, 1)            # narrower at the bottom
    sh[:, 2] += 0.12 * (1 - Vn[:, 1] ** 2) * (Vn[:, 2] > 0)
    Vn = sh * np.array(r) + c
    cn = np.tile(NOSE_C, (len(Vn), 1))
    for s in (1, -1):
        dd = np.linalg.norm((Vn - (c + np.array([0.12, 0.065 * s, -0.01]))) / np.array([0.04, 0.035, 0.03]), axis=1)
        cn = mix(cn, hexc("#030203"), smooth(1.4, 0.8, dd))
    cn = mix(cn, hexc("#4a3f46"), smooth(0.04, 0.12, Vn[:, 2] - c[2]) * 0.55)
    Ub.add_mesh("nose", to_world(Vn), Fn, cn, Ub.material("nose", rough=0.25, spec=0.6, coat=0.6))
    # the tongue: a little pink tongue just peeking out of the open middle of the smile
    mc, mr = MOUTH_OPEN
    Vt, Ft = Ub.uv_sphere(np.zeros(3), 1.0, 28, 14)
    q = Vt * np.array([0.12, 0.11, 0.045])
    q[:, 2] -= 0.05 * np.clip(q[:, 0] / 0.12 + 0.3, 0, 1.3) ** 2
    ct = mix(np.tile(hexc("#ef8fa3"), (len(q), 1)), hexc("#d46a85"), smooth(0.02, -0.06, q[:, 0]))
    Ub.add_mesh("tongue", to_world(q + mc + np.array([0.05, 0.0, -0.01])), Ft, ct,
                Ub.material("tongue", rough=0.35, sss=0.3, spec=0.45, coat=0.2))


# ------------------------------------------------------------------ scene
VIEWS_AT = {"hero": (34.0, 6.0, (0.2, 0.0, 1.62), 3.9), "head": (30.0, 3.0, (0.6, 0.0, 2.5), 3.0),
            "front": (80.0, 3.0, (0.4, 0.0, 1.62), 3.9), "side": (0.0, 3.0, (0.0, 0.0, 1.62), 3.9)}


def camera(view):
    az, el, focus, size = VIEWS_AT[view]
    cam = bpy.data.cameras.new("cam")
    cam.type = "ORTHO"
    cam.ortho_scale = size
    ob = bpy.data.objects.new("cam", cam)
    bpy.context.collection.objects.link(ob)
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    ob.location = Vector(focus) + d * 30
    ob.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob
    return ob


def lights():
    def area(name, loc, size, energy, col):
        L = bpy.data.lights.new(name, "AREA")
        L.size, L.energy, L.color = size, energy, col
        ob = bpy.data.objects.new(name, L)
        bpy.context.collection.objects.link(ob)
        ob.location = loc
        ob.rotation_euler = (Vector((0.3, 0, 2.0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    area("key", (5, 6.5, 7), 6, 850, (1.0, 0.96, 0.9))
    area("fill", (6, -4, 3), 7, 260, (0.92, 0.95, 1.0))
    area("rim", (-5, -2, 6), 4, 520, (1.0, 0.95, 0.88))
    area("bounce", (2, 3, -2), 6, 90, (1.0, 0.98, 0.92))


def main():
    os.makedirs(OUT, exist_ok=True)
    sc = Ub.setup()
    sc.view_settings.exposure = -0.05
    rng = np.random.default_rng(5)
    global HEAD_TUFTS, BODY_TUFTS
    HEAD_TUFTS, BODY_TUFTS = make_tufts(rng)
    lo, hi = ((-0.9, -1.3, 1.05), (2.0, 1.3, 3.8)) if HEAD_ONLY else ((-1.9, -1.4, 0.0), (2.0, 1.5, 3.8))
    F, o = sample(sdf, lo, hi, H)
    V, T = surface_nets(F, o, H)
    V = project(sdf, V, 2)
    N = grad(sdf, V)
    col = colours(V, N)
    Ub.add_mesh("coat", V, T, col, Ub.material("coat", rough=0.7, sss=0.12, sheen=1.0, spec=0.22), N)
    build_face()
    lights()
    res = 520 if QUICK else 1200
    sc.render.resolution_x = res
    sc.render.resolution_y = res
    for v in VIEWS:
        cam = camera(v)
        sc.render.filepath = os.path.join(OUT, v + ".png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam)
        print("rendered", v)


if __name__ == "__main__":
    main()
