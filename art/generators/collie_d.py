"""Border collie D, "the garden collie": the dog in the painting the user shared, as one detailed 3D model. A grown
black-and-white border collie standing in three-quarter view: amber eyes looking at the camera, semi-pricked ears whose
tips fold forward and out along a slanted crease, an open smile with the tongue out, a narrow white blaze widening over
the muzzle, a big white ruff of long locks, white legs and paws and a long glossy black coat. Made from code only, with
no hand-drawn art: the skin is one fused signed distance field (anatomical primitives, blended), the ears are thin
shaped shells, and the coat is about a million and a half strands grown on the skin, combed, kept clear of the body and
gathered into clumps and locks. With --garden it stands on a stone path in a 3D garden like the painting's: grass
blades, a hillside, a pond and a little waterfall, rocks, bushes in blossom and flowers, under a soft sun.

Axes (Blender): x forward, y across (+y the near side, toward the camera), z up; ground z = 0; the withers are about 1.
Run:   blender -b --factory-startup -P collie_d.py -- OUTDIR [--quick | --preview] [--skin] [--clay] [--head] [--garden] [view ...]
       --quick    a light coat, small and fast      --preview  the full coat, rendered small
       --skin     the bare sculpt, no fur           --clay     grey, for judging shape
       --head     only the head (fast face work)    --garden   the garden round it (for hero and face)
       views: hero face (the garden shots); dside dfront dback (turnaround); hface head front side top back ear flank
Renders on the GPU (OptiX) when there is one."""
import bpy, math, os, sys, time
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import unicorn2 as Ub
from unicorn2_shape import ellipsoid, round_cone, squash, smin, smax, rot, sample, surface_nets

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0] if argv else "collie_d_out")
QUICK = "--quick" in argv
PREVIEW = "--preview" in argv                                # the full coat, rendered small and fast
GARDEN = "--garden" in argv                                  # set in a garden (path, grass, rocks, flowers, far hills)
SKIN = "--skin" in argv
CLAY = "--clay" in argv
HEAD_ONLY = "--head" in argv
VIEWS = [a for a in argv[1:] if not a.startswith("--")] or ["hero"]
hexc, mix, smooth = Ub.hexc, Ub.mix, Ub.smooth
T0 = time.time()


def log(*a):
    print("[%6.1fs]" % (time.time() - T0), *a, flush=True)


def unit(v):
    v = np.asarray(v, np.float64)
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def grad(fn, P, h=4e-4):
    P = np.atleast_2d(np.asarray(P, np.float64))
    g = np.zeros_like(P)
    for i in range(3):
        e = np.zeros(3)
        e[i] = h
        g[:, i] = (fn(P + e) - fn(P - e)) / (2 * h)
    return g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-12)


def project(fn, P, steps=3):
    P = np.atleast_2d(np.asarray(P, np.float64)).copy()
    for _ in range(steps):
        P -= grad(fn, P) * fn(P)[:, None]
    return P


def ray_hit(fn, o, d, lo=0.0, hi=1.0):
    """the first surface point along a ray from inside"""
    o, d = np.asarray(o, np.float64), unit(d)
    for _ in range(50):
        m = (lo + hi) / 2
        if fn((o + d * m)[None])[0] < 0:
            lo = m
        else:
            hi = m
    return o + d * lo


def frame_ellipsoid(P, c, R, radii):
    """an ellipsoid with its own axes (rows of R)"""
    return ellipsoid((P - c) @ np.asarray(R).T, np.zeros(3), radii)


# ================================================================== the head (head-local: modelled straight)
HEAD_C = np.array([0.73, 0.0, 1.25])                          # the skull's centre, in the world
HS = 1.3                                                     # the head a little big, as in the painting
HEAD_R = rot((0, 0, 1), 15.0) @ rot((0, 1, 0), 9.0) @ rot((1, 0, 0), 10.0)   # a little toward us, nose down, a tilt


def to_world(L):
    return HEAD_C + (np.asarray(L) * HS) @ HEAD_R.T


def to_head(P):
    return ((np.asarray(P) - HEAD_C) @ HEAD_R) / HS


def hdir(v):
    return np.asarray(v) @ HEAD_R.T


NOSE = (np.array([0.242, 0.0, -0.03]), np.array([0.029, 0.037, 0.026]))
JAW_HINGE = np.array([-0.04, 0.0, -0.088])
JAW_OPEN = rot((0, 1, 0), 21.0)                              # the jaw dropped open in a smile


def upper(L):
    """skull, brows, cheeks, muzzle, upper lips and the nose pad"""
    d = ellipsoid(L, np.array([-0.035, 0.0, 0.026]), (0.145, 0.134, 0.108))
    d = smin(d, ellipsoid(L, np.array([0.04, 0.0, 0.02]), (0.085, 0.1, 0.075)), 0.06)            # forehead
    d = smin(d, ellipsoid(L, np.array([-0.16, 0.0, 0.05]), (0.05, 0.06, 0.06)), 0.05)            # occiput
    for s in (1, -1):
        d = smin(d, ellipsoid(L, np.array([0.072, 0.047 * s, 0.05]), (0.045, 0.04, 0.03)), 0.03)  # brows
        d = smin(d, ellipsoid(L, np.array([-0.01, 0.088 * s, -0.035]), (0.09, 0.068, 0.07)), 0.06)  # cheekbones
    d = smin(d, squash(round_cone, L, 0.95, (0.06, 0.0, -0.03), (0.218, 0.0, -0.054), 0.07, 0.037), 0.05)   # muzzle
    for s in (1, -1):                                         # upper lips, hanging over the jaw, rising at the back
        d = smin(d, round_cone(L, np.array([0.02, 0.054 * s, -0.06]), np.array([0.183, 0.033 * s, -0.072]), 0.024, 0.03), 0.03)
    d = smin(d, ellipsoid(L, NOSE[0], NOSE[1]), 0.015)
    return d


def jaw_closed(L):
    return JAW_HINGE + (L - JAW_HINGE) @ JAW_OPEN               # a point, in the closed jaw's frame


def lower(L):
    Q = jaw_closed(L)
    d = squash(round_cone, Q, 0.95, (0.0, 0.0, -0.122), (0.18, 0.0, -0.124), 0.038, 0.022)
    return smin(d, ellipsoid(Q, np.array([0.14, 0.0, -0.137]), (0.045, 0.029, 0.02)), 0.03)        # chin


def head_raw(L):
    return smin(upper(L), lower(L), 0.012)


# ------------------------------------------------------------------ eyes
EYE_R = 0.029
EYE_HALF = (0.033, 0.0195)                                    # the lids' opening: half width, half height


def eye_frame(side):
    E = ray_hit(upper, np.array([0.02, 0.0, 0.012]), np.array([0.78, 0.58 * side, 0.08]))
    n = unit(grad(upper, E)[0] * 0.5 + unit(np.array([0.8, 0.55 * side, 0.05])) * 0.5)
    u = np.array([1.0, 0.0, 0.0]) - n * n[0]
    u = unit(u)                                               # along the lids, toward the nose
    v = np.cross(n, u)
    if v[2] < 0:
        v = -v
    return E, n, u, v


EYES = {s: eye_frame(s) for s in (1, -1)}


def almond(a, b):
    """the lids' opening in the eye's plane (a toward the nose, b up): <0 inside"""
    A, B = EYE_HALF
    b = b + 0.06 * a                                          # the outer corner a touch lower: a soft look
    x = np.clip(np.abs(a) / A, 0.0, 1.0)
    top = B * (1.0 - x ** 2.0) ** 0.55
    bot = B * 0.85 * (1.0 - x ** 2.0) ** 0.75
    return np.maximum(np.abs(a) - A, np.abs(b) - np.where(b >= 0, top, bot))


def head_sdf(L):
    d = head_raw(L)
    for s in (1, -1):
        E, n, u, v = EYES[s]
        q = L - E
        sock = np.maximum(almond(q @ u, q @ v), np.maximum(q @ n - 0.03, -(q @ n) - 0.03))
        d = smax(d, -sock, 0.006)
    for s in (1, -1):                                         # nostrils
        d = smax(d, -ellipsoid(L, NOSE[0] + np.array([0.03, 0.017 * s, -0.004]), (0.01, 0.008, 0.007)), 0.004)
    return d


# ------------------------------------------------------------------ ears: thin cupped shells, the tips folding forward and out
EAR_H, EAR_W, EAR_T = 0.25, 0.1, 0.01
EAR_FOLD, EAR_FOLD_AT = float(os.environ.get("EAR_FOLD", "130")), float(os.environ.get("EAR_FOLD_AT", "0.5"))
EAR_CREASE = float(os.environ.get("EAR_CREASE", "30"))       # the fold's crease runs on a slant, so the tip falls out
EAR_LEAN, EAR_TURN = float(os.environ.get("EAR_LEAN", "0.8")), float(os.environ.get("EAR_TURN", "0.9"))                               # how far the ear leans out, how far its opening turns out


def ear_frame(side):
    base = ray_hit(upper, np.array([-0.04, 0.0, 0.02]), np.array([-0.2, 0.85 * side, 0.62]))
    up = unit(np.array([-0.15, EAR_LEAN * side, 1.0]))
    fwd = np.array([1.0, EAR_TURN * side, -0.1])
    fwd = unit(fwd - up * (fwd @ up))
    acr = np.cross(up, fwd)                                   # +side: toward the back... fixed below
    if acr[0] > 0:
        acr = -acr
    tipdir = unit(fwd * 0.4 + np.array([0.0, side, 0.0]) * 0.75 - up * 0.62)
    return base, up, fwd, acr, tipdir


EARS = {s: ear_frame(s) for s in (1, -1)}


def rodrigues(v, k, a):
    k = unit(k)
    return v * np.cos(a) + np.cross(k, v) * np.sin(a) + np.outer(v @ k, k) * (1 - np.cos(a)) if v.ndim == 2 else \
        v * np.cos(a) + np.cross(k, v) * np.sin(a) + k * (k @ v) * (1 - np.cos(a))


def ear_sheet(side, nu=28, nv=40):
    """points of the ear's mid-surface on a (u across, v up) grid, its normals (forward, out of the cup) and frames"""
    base, up, fwd, acr, tipdir = EARS[side]
    vs = np.linspace(-0.2, 1.0, nv)
    us = np.linspace(-1.0, 1.0, nu)
    axis = rodrigues(unit(np.cross(up, fwd)), fwd, math.radians(EAR_CREASE) * side)   # the fold's crease, slanted
    spine, U_, N_ = [], [], []
    p = base + up * EAR_H * vs[0]                             # v = 0 at the skin; below it, buried in the head
    dv = vs[1] - vs[0]
    for v in vs:
        w = smooth(EAR_FOLD_AT - 0.14, EAR_FOLD_AT + 0.22, v)
        ang = math.radians(EAR_FOLD) * w
        dirn = rodrigues(up, axis, ang)
        spine.append(p.copy())
        U_.append(rodrigues(acr, axis, ang))
        N_.append(rodrigues(fwd, axis, ang))
        p = p + dirn * EAR_H * dv
    spine, U_, N_ = np.array(spine), np.array(U_), np.array(N_)
    vv = np.clip(vs, 0, 1)
    hw = EAR_W * np.clip(1.0 - vv, 0, 1) ** 0.85 * (1.0 + 0.4 * vv)
    hw = np.maximum(hw, 0.004)
    P = np.zeros((nv, nu, 3))
    Nrm = np.zeros((nv, nu, 3))
    for j in range(nv):
        cup = 0.028 * (1 - 0.65 * vv[j]) * (us ** 2)           # the edges come forward: a cup
        P[j] = spine[j] + U_[j] * (us * hw[j])[:, None] + N_[j] * cup[:, None]
        Nrm[j] = N_[j]
    return P, Nrm, vs, us, hw


def ear_mesh(side):
    """a closed shell: the front (inside) and back sheets, stitched round the rim"""
    P, Nrm, vs, us, hw = ear_sheet(side)
    nv, nu = P.shape[:2]
    taper = (1 - 0.6 * np.clip(vs, 0, 1) ** 2)[:, None, None]
    edge = (0.12 + 0.88 * np.sqrt(np.clip(1 - np.abs(us) ** 2.5, 0, 1)))[None, :, None]
    t = EAR_T * 0.5 * taper * edge
    front = (P + Nrm * t).reshape(-1, 3)
    back = (P - Nrm * t).reshape(-1, 3)
    V = np.vstack([front, back])
    F = []
    idx = lambda j, i: j * nu + i
    off = nv * nu
    for j in range(nv - 1):
        for i in range(nu - 1):
            a, b, c, d = idx(j, i), idx(j, i + 1), idx(j + 1, i + 1), idx(j + 1, i)
            F += [(a, b, c), (a, c, d), (a + off, c + off, b + off), (a + off, d + off, c + off)]
    for j in range(nv - 1):                                   # the side rims
        for i in (0, nu - 1):
            a, b = idx(j, i), idx(j + 1, i)
            if i == 0:
                F += [(a, a + off, b + off), (a, b + off, b)]
            else:
                F += [(a, b + off, a + off), (a, b, b + off)]
    for i in range(nu - 1):                                   # the tip
        a, b = idx(nv - 1, i), idx(nv - 1, i + 1)
        F += [(a, b + off, a + off), (a, b, b + off)]
    return V, np.array(F), P, Nrm


# ------------------------------------------------------------------ the head's colours (head-local)
BLACK = hexc("#0c0b0e")
BLACK_SKIN = hexc("#17161b")
WHITE = hexc("#f2eee6")
WHITE_SHADE = hexc("#d9d3c8")


def lip_lines(L):
    """distance to the upper lip's edge and to the lower lip's edge (head-local), and the mouth-inside mask"""
    x, y, z = L[:, 0], L[:, 1], L[:, 2]
    zu = -0.102 + 0.022 * smooth(0.12, 0.0, x)                # upper lip edge, rising to the corner
    Q = jaw_closed(L)
    zl = -0.1 + 0.015 * smooth(0.08, 0.0, Q[:, 0])
    du = np.abs(z - zu)
    dl = np.abs(Q[:, 2] - zl)
    inside = (z < zu - 0.004) & (Q[:, 2] > zl + 0.004) & (x > 0.0)
    return du, dl, inside, Q


def head_colours(L, N):
    x, y, z = L[:, 0], L[:, 1], L[:, 2]
    n = len(L)
    c = np.tile(BLACK_SKIN, (n, 1))
    # the blaze: narrow up over the forehead and crown, widening over the stop onto the muzzle
    half = 0.011 + 0.004 * smooth(-0.05, 0.1, x) + 0.058 * smooth(0.13, 0.205, x) ** 1.2
    yc = 0.006 * np.sin(x * 25.0)
    blaze = smooth(half + 0.006, half - 0.004, np.abs(y - yc)) * smooth(-0.09, -0.04, x) * smooth(-0.02, 0.03, z + 0.1 * (x - 0.1))
    # the muzzle: white on the top and sides from below the eyes forward, and round the mouth
    edge = 0.142 - 2.0 * np.clip(-0.035 - z, 0, None)                                     # its back edge slants down and back to the mouth corner
    muz = smooth(edge - 0.004, edge + 0.014, x) * smooth(0.03, 0.008, z)
    du, dl, inside, Q = lip_lines(L)
    lowj = smooth(-0.09, -0.11, Q[:, 2]) * smooth(-0.02, 0.04, Q[:, 0])          # the chin and lower jaw
    w = np.clip(np.maximum(np.maximum(blaze, muz), lowj), 0, 1)
    c = mix(c, WHITE, w)
    # leather and lips
    lips_u = smooth(0.016, 0.009, du) * smooth(-0.01, 0.02, x)
    lips_l = smooth(0.014, 0.008, dl) * smooth(-0.01, 0.02, Q[:, 0])
    c = mix(c, hexc("#141114"), np.maximum(lips_u, lips_l))
    c = np.where(inside[:, None], hexc("#4a1c22"), c)
    nd = np.linalg.norm((L - NOSE[0]) / NOSE[1], axis=1)
    c = mix(c, hexc("#141215"), smooth(1.25, 1.0, nd))
    return c, w


# ================================================================== the body (world)
FRONT_STEP = {1: 0.05, -1: -0.02}                            # the near front leg a step forward
HIND_STEP = {1: -0.06, -1: 0.01}                             # the near hind leg a step back
NECK_A, NECK_B = np.array([0.3, 0.0, 0.82]), np.array([0.58, 0.0, 1.11])
TAIL_PTS = np.array([(-0.58, 0.0, 0.84), (-0.68, 0.0, 0.72), (-0.74, 0.01, 0.53), (-0.75, 0.03, 0.36),
                     (-0.71, 0.06, 0.25), (-0.64, 0.09, 0.21)])


def curve(pts, m=48):
    t = np.linspace(0, 1, len(pts))
    s = np.linspace(0, 1, m)
    c = np.stack([np.interp(s, t, pts[:, k]) for k in range(3)], 1)
    for _ in range(8):
        c[1:-1] = (c[:-2] + 2 * c[1:-1] + c[2:]) / 4
    return c


TAIL = curve(TAIL_PTS, 40)


def tail_sdf(P):
    d = np.full(len(P), 9.0)
    m = len(TAIL)
    for i in range(m - 1):
        r1 = 0.05 * (1 - i / m) + 0.022
        r2 = 0.05 * (1 - (i + 1) / m) + 0.022
        d = np.minimum(d, round_cone(P, TAIL[i], TAIL[i + 1], r1, r2))
    return d


def paw_sdf(P, c):
    c = np.asarray(c, np.float64)
    d = ellipsoid(P, c + np.array([-0.008, 0, 0.002]), (0.05, 0.043, 0.03))
    for yy in (-0.029, -0.0105, 0.0105, 0.029):                # four toes, with soft grooves between
        tc = c + np.array([0.036 - 0.3 * abs(yy), yy, -0.007])
        d = smin(d, ellipsoid(P, tc, (0.024, 0.0135, 0.021)), 0.008)
    return d


def body_parts(P):
    t = ellipsoid(P, np.array([0.17, 0.0, 0.7]), (0.34, 0.19, 0.27))                           # ribcage, deep
    t = smin(t, ellipsoid(P, np.array([0.42, 0.0, 0.65]), (0.12, 0.15, 0.19)), 0.1)             # chest front
    for s in (1, -1):                                                                          # shoulder blades
        t = smin(t, round_cone(P, np.array([0.25, 0.085 * s, 0.9]), np.array([0.42, 0.125 * s, 0.62]), 0.07, 0.085), 0.08)
    t = smin(t, round_cone(P, np.array([0.0, 0.0, 0.76]), np.array([-0.36, 0.0, 0.77]), 0.19, 0.165), 0.15)   # loin
    t = smin(t, ellipsoid(P, np.array([-0.45, 0.0, 0.78]), (0.19, 0.16, 0.16)), 0.12)          # croup
    neck = round_cone(P, NECK_A, NECK_B, 0.18, 0.12)
    fl = hl = paw = np.full(len(P), 9.0)
    for s in (1, -1):
        dx = FRONT_STEP[s]
        a = round_cone(P, np.array([0.42 + dx, 0.12 * s, 0.6]), np.array([0.33 + dx, 0.11 * s, 0.44]), 0.075, 0.058)
        a = smin(a, round_cone(P, np.array([0.33 + dx, 0.11 * s, 0.45]), np.array([0.35 + dx, 0.097 * s, 0.13]), 0.066, 0.048), 0.04)
        a = smin(a, round_cone(P, np.array([0.35 + dx, 0.097 * s, 0.13]), np.array([0.38 + dx, 0.095 * s, 0.05]), 0.04, 0.036), 0.02)
        fl = np.minimum(fl, a)
        paw = np.minimum(paw, paw_sdf(P, (0.4 + dx, 0.095 * s, 0.032)))
        dx = HIND_STEP[s]
        b = ellipsoid(P, np.array([-0.42 + dx, 0.1 * s, 0.63]), (0.16, 0.075, 0.19))
        b = smin(b, round_cone(P, np.array([-0.44 + dx, 0.1 * s, 0.74]), np.array([-0.3 + dx, 0.11 * s, 0.44]), 0.11, 0.07), 0.06)
        b = smin(b, round_cone(P, np.array([-0.3 + dx, 0.11 * s, 0.44]), np.array([-0.5 + dx, 0.1 * s, 0.18]), 0.065, 0.036), 0.04)
        b = smin(b, round_cone(P, np.array([-0.5 + dx, 0.1 * s, 0.18]), np.array([-0.47 + dx, 0.1 * s, 0.05]), 0.034, 0.031), 0.02)
        hl = np.minimum(hl, b)
        paw = np.minimum(paw, paw_sdf(P, (-0.45 + dx, 0.1 * s, 0.031)))
    return {"torso": t, "neck": neck, "fleg": fl, "hleg": hl, "paw": paw, "tail": tail_sdf(P)}


def body_join(p):
    d = smin(p["torso"], p["neck"], 0.12)
    d = smin(d, p["fleg"], 0.07)
    d = smin(d, p["hleg"], 0.09)
    d = smin(d, p["paw"], 0.025)
    return smin(d, p["tail"], 0.05)


def body_sdf(P):
    return body_join(body_parts(P))


PARTS = ["head", "torso", "neck", "fleg", "hleg", "paw", "tail"]


def classify(P):
    """which part each point belongs to (an index into PARTS), with the parts' distances"""
    p = body_parts(P)
    p["head"] = head_raw(to_head(P)) * HS
    D = np.stack([p[k] for k in PARTS], 1)
    return np.argmin(D, 1), p


def neck_front(P):
    """-1 at the back of the neck, +1 at the throat"""
    a = unit(NECK_B - NECK_A)
    f = unit(np.array([a[2], 0.0, -a[0]]))
    q = P - NECK_A
    q = q - np.outer(q @ a, a)
    return (q @ f) / np.maximum(np.linalg.norm(q, axis=1), 1e-9)


def tail_t(P):
    k = np.argmin(np.linalg.norm(P[:, None, :] - TAIL[None, ::2, :], axis=2), 1)
    return k / (len(TAIL[::2]) - 1)


def body_white(P, N, part):
    """how white the coat is at each body point (0 black .. 1 white)"""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    w = np.zeros(len(P))
    nf = neck_front(P)
    collar = smooth(-0.55, -0.3, nf - 0.25 * smooth(0.98, 1.12, z)) * smooth(0.8, 0.88, z)       # the ruff round the neck
    chest = smooth(0.4, 0.46, x + 0.08 * smooth(0.6, 0.35, z) - 0.25 * np.abs(y)) * smooth(0.95, 0.85, z)   # the bib
    w = np.maximum(collar, chest) * np.isin(part, [1, 2])
    w = np.maximum(w, (part == 3) * smooth(0.5, 0.44, z - 0.2 * N[:, 0]))                       # the front legs
    w = np.maximum(w, (part == 4) * smooth(0.26, 0.2, z))                                       # the hind feet
    w = np.maximum(w, (part == 5) * 1.0)                                                        # paws
    w = np.maximum(w, (part == 6) * smooth(0.72, 0.82, tail_t(P)))                              # the tail's tip
    return np.clip(w, 0, 1)


def skin_colours(P, N):
    part, _ = classify(P)
    L = to_head(P)
    hc, hw = head_colours(L, None)
    bw = body_white(P, N, part)
    bc = mix(np.tile(BLACK_SKIN, (len(P), 1)), WHITE, bw[:, None])
    head = (part == 0)[:, None]
    return np.where(head, hc, bc), part


def body_groom(P, N, part):
    """per root (world): length, lift, gravity, comb direction and a clump class"""
    x, y, z = P[:, 0], P[:, 1], P[:, 2]
    n = len(P)
    sd = np.where(y >= 0, 1.0, -1.0)
    one = np.ones(n)
    V3 = lambda a, b, c: np.stack([a * one, b * one, c * one], 1)
    sidev = smooth(0.7, 0.1, N[:, 2])                         # 0 along the back, 1 down the sides
    ln = 0.12 + 0.05 * sidev
    lift = np.full(n, 0.04)
    comb = V3(-1.0, 0.0, -0.3) * (1 - sidev[:, None]) + V3(-0.55, 0.0, -1.0) * sidev[:, None]
    kind = np.zeros(n, int)                                   # 0 coat, 1 ruff, 2 short, 3 feathers, 4 tail
    torso, neck, fleg, hleg, paw, tail = (part == 1), (part == 2), (part == 3), (part == 4), (part == 5), (part == 6)
    belly = torso & (N[:, 2] < -0.45)
    ln = np.where(belly, 0.16, ln)
    comb = np.where(belly[:, None], V3(-0.25, 0.0, -1.0), comb)
    kind = np.where(belly, 3, kind)
    # the ruff: the throat, the front of the neck and the chest, long and falling in locks
    nf = neck_front(P)
    ruff = (neck | torso) & (body_white(P, N, part) > 0.5) & (z > 0.5)          # the ruff is exactly the white
    rl = 0.1 + 0.1 * smooth(0.55, 0.75, z) + 0.12 * smooth(0.8, 1.0, z)
    ln = np.where(ruff, rl, ln)
    lift = np.where(ruff, 0.14, lift)
    comb = np.where(ruff[:, None], unit(V3(0.25, 0.0, -1.0) + np.stack([0 * one, 0.35 * sd, 0 * one], 1)), comb)
    kind = np.where(ruff, 1, kind)
    mane = neck & ~ruff
    ln = np.where(mane, 0.13 + 0.05 * smooth(0.95, 1.1, z), ln)
    lift = np.where(mane, 0.25, lift)
    comb = np.where(mane[:, None], V3(-1.0, 0.0, -0.12), comb)
    # front legs: short and sleek in front, feathered behind
    upper = fleg & (z > 0.48)
    ln = np.where(upper, 0.06, ln)
    low = fleg & ~upper
    feather = low & (N[:, 0] < -0.15) & (z > 0.16)
    ln = np.where(low, 0.05, ln)
    lift = np.where(low, 0.3, lift)
    comb = np.where(low[:, None], V3(0.05, 0.0, -1.0), comb)
    kind = np.where(low, 2, kind)
    ln = np.where(feather, 0.04 + 0.1 * smooth(0.16, 0.42, z), ln)
    comb = np.where(feather[:, None], V3(-0.5, 0.0, -1.0), comb)
    kind = np.where(feather, 3, kind)
    # hind legs: britches on the thighs, short below the hock
    thigh = hleg & (z > 0.38)
    brit = thigh & (N[:, 0] < -0.1)
    ln = np.where(thigh, 0.085, ln)
    ln = np.where(brit, 0.15, ln)
    comb = np.where(thigh[:, None], V3(-0.5, 0.0, -1.0), comb)
    kind = np.where(brit, 3, kind)
    shank = hleg & ~thigh
    ln = np.where(shank, np.where(N[:, 0] < -0.2, 0.035, 0.016) * (1 - 0.4 * smooth(0.24, 0.1, z)), ln)
    lift = np.where(shank, 0.1, lift)
    comb = np.where(shank[:, None], V3(-0.2, 0.0, -1.0), comb)
    kind = np.where(shank, 2, kind)
    # paws: very short, a little tuft over the toes
    ln = np.where(paw, 0.008, ln)
    lift = np.where(paw, 0.25, lift)
    comb = np.where(paw[:, None], V3(1.0, 0.0, -0.5), comb)
    kind = np.where(paw, 2, kind)
    # the tail: a plume combed toward the tip, longest underneath
    tt = tail_t(P)
    ti = np.clip((tt * (len(TAIL) - 1)).astype(int), 0, len(TAIL) - 2)
    tdir = unit(TAIL[ti + 1] - TAIL[ti])
    under = smooth(0.0, -0.8, N[:, 0])
    ln = np.where(tail, (0.1 + 0.09 * under) * (0.7 + 0.5 * np.sin(np.pi * np.clip(tt * 1.1, 0, 1))), ln)
    lift = np.where(tail, 0.35, lift)
    comb = np.where(tail[:, None], unit(tdir + V3(0, 0, -0.4)), comb)
    kind = np.where(tail, 4, kind)
    grav = 0.4 + 7.0 * ln
    grav = np.where(kind == 1, 0.8 + 6.0 * ln, grav)
    return ln, lift, comb, grav, kind


KINDS = {  # points per strand, root radius, [(clump radius, strength, shape)], wave, wave freq, frizz, density
    0: (14, 0.0012, [(0.024, 0.42, 2.0), (0.008, 0.2, 1.5)], 0.03, 0.6, 0.003, 0.7),
    1: (18, 0.0012, [(0.045, 0.45, 1.7), (0.012, 0.25, 1.5)], 0.18, 0.7, 0.005, 1.0),
    2: (6, 0.0008, [(0.008, 0.45, 1.5)], 0.0, 1.0, 0.015, 1.0),
    3: (12, 0.001, [(0.02, 0.5, 1.6), (0.007, 0.25, 1.2)], 0.06, 0.9, 0.01, 0.75),
    4: (14, 0.001, [(0.025, 0.5, 1.6), (0.008, 0.25, 1.2)], 0.06, 0.8, 0.01, 0.85),
}


def wobble(P, rng, scale=0.09, terms=9):
    """smooth spatial noise in about [-1, 1] (sum of waves in random directions)"""
    out = np.zeros(len(P))
    for _ in range(terms):
        k = unit(rng.normal(0, 1, 3)) * (2 * np.pi / scale) * rng.uniform(0.6, 1.4)
        out += np.sin(P @ k + rng.uniform(0, 2 * np.pi))
    return out / np.sqrt(terms / 2)


def body_fur(coat, R, N, part, field, rng):
    ln, lift, comb, grav, kind = body_groom(R, N, part)
    ln = ln * np.clip(1 + 0.18 * wobble(R, rng) * np.isin(kind, [0, 1, 3, 4]), 0.75, 1.35)
    comb = unit(comb - N * np.sum(comb * N, 1, keepdims=True))
    ln = ln * rng.uniform(0.8, 1.2, len(R))
    w = body_white(R, N, part)
    hc = HAIR_BLACK[None] * (1 - w)[:, None] + HAIR_WHITE[None] * w[:, None]
    hc = hc * rng.uniform(0.8, 1.15, (len(R), 1))
    for k, (K, r0, clumps, wave, freq, frizz, dens) in KINDS.items():
        m = (kind == k) & (rng.random(len(R)) < dens)
        if not m.any():
            continue
        P = grow(R[m], N[m], comb[m], ln[m], lift[m], grav[m], K, field)
        for i, (cr, cs, csh) in enumerate(clumps):
            P = clump(P, N[m], cr, cs, csh, rng, wave=wave if i == 0 else 0.0, freq=freq, frizz=frizz if i == len(clumps) - 1 else 0.0)
        P = settle(P, field)
        coat.add(P, strand_radius(len(P), K, r0, rng), hc[m])
        log("body fur kind", k, int(m.sum()))


# ================================================================== scene helpers
def mesh(name, V, T, cols=None, mat=None, normals=None, attrs=None):
    V = np.ascontiguousarray(V, np.float32)
    T = np.ascontiguousarray(T, np.int32)
    me = bpy.data.meshes.new(name)
    me.vertices.add(len(V))
    me.vertices.foreach_set("co", V.ravel())
    me.loops.add(T.size)
    me.loops.foreach_set("vertex_index", T.ravel())
    me.polygons.add(len(T))
    me.polygons.foreach_set("loop_start", np.arange(0, T.size, 3, dtype=np.int32))
    me.update(calc_edges=True)
    me.polygons.foreach_set("use_smooth", np.ones(len(T), bool))
    if cols is not None:
        cols = np.asarray(cols, np.float32)
        if cols.shape[1] == 3:
            cols = np.concatenate([cols, np.ones((len(cols), 1), np.float32)], 1)
        a = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
        a.data.foreach_set("color", cols.ravel())
    for an, arr in (attrs or {}).items():
        at = me.attributes.new(an, "FLOAT", "POINT")
        at.data.foreach_set("value", np.asarray(arr, np.float32).ravel())
    if normals is not None:
        me.normals_split_custom_set_from_vertices(np.asarray(normals, np.float32))
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    if mat is not None:
        me.materials.append(mat)
    return ob


def principled(name, color=None, rough=0.5, spec=0.5, sss=0.0, sss_rad=(0.6, 0.3, 0.25), sss_scale=0.01, coat=0.0,
               sheen=0.0, transmission=0.0, ior=1.45, emit=0.0, alpha=1.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes["Principled BSDF"]
    if CLAY:
        color, sss, coat, sheen = (0.55, 0.55, 0.56, 1.0), 0.0, 0.0, 0.0
        rough = max(rough, 0.55) if transmission == 0 else rough
    if color is None:
        at = nt.nodes.new("ShaderNodeAttribute")
        at.attribute_name = "Col"
        nt.links.new(at.outputs["Color"], bs.inputs["Base Color"])
    else:
        bs.inputs["Base Color"].default_value = tuple(color)[:3] + (1.0,)
    bs.inputs["Roughness"].default_value = rough
    bs.inputs["Specular IOR Level"].default_value = spec
    bs.inputs["Subsurface Weight"].default_value = sss
    bs.inputs["Subsurface Radius"].default_value = sss_rad
    bs.inputs["Subsurface Scale"].default_value = sss_scale
    bs.inputs["Coat Weight"].default_value = coat
    bs.inputs["Coat Roughness"].default_value = 0.03
    bs.inputs["Sheen Weight"].default_value = sheen
    bs.inputs["Transmission Weight"].default_value = transmission
    bs.inputs["IOR"].default_value = ior
    bs.inputs["Alpha"].default_value = alpha
    if emit:
        bs.inputs["Emission Color"].default_value = tuple(color)[:3] + (1.0,)
        bs.inputs["Emission Strength"].default_value = emit
    return m


# ================================================================== the face's parts
def surface_pts(fn, L, off=0.0):
    P = project(fn, L, 4)
    return P + grad(fn, P) * off


def sphere_mesh(nu, nv):
    th = np.linspace(0, np.pi, nv + 1)
    ph = np.linspace(0, 2 * np.pi, nu, endpoint=False)
    T, Ph = np.meshgrid(th, ph, indexing="ij")
    V = np.stack([np.sin(T) * np.cos(Ph), np.sin(T) * np.sin(Ph), np.cos(T)], -1).reshape(-1, 3)
    F = []
    for i in range(nv):
        for j in range(nu):
            a, b = i * nu + j, i * nu + (j + 1) % nu
            c, d = (i + 1) * nu + (j + 1) % nu, (i + 1) * nu + j
            F += [(a, d, c), (a, c, b)]
    return V, np.array(F)


def build_eyes():
    rng = np.random.default_rng(3)
    for side in (1, -1):
        E, n, u, v = EYES[side]
        to_cam = unit((cam_pos("hero") - to_world(E)) @ HEAD_R)     # toward the camera, in the head's frame
        look = unit(n * 0.35 + to_cam * 0.65)
        c = E - n * EYE_R * 0.88
        upv = unit(v - look * (v @ look))
        a = np.cross(upv, look)
        S, F = sphere_mesh(192, 96)
        # the eyeball: iris and pupil painted on, under a clear cornea
        ca = S @ np.array([0, 0, 1.0])
        Rm = np.stack([a, upv, look], 1)                      # local (x a, y up, z look) to head
        Vb = c + (S * EYE_R) @ Rm.T
        ang = np.degrees(np.arccos(np.clip(ca, -1, 1)))
        phi = np.arctan2(S[:, 1], S[:, 0])
        r = ang / 54.0                                        # 0 at the centre, 1 at the iris' edge
        fib = 0.5 + 0.5 * np.sin(phi * 37 + rng.uniform(0, 6)) * np.sin(phi * 13 + 1.3)
        iris = mix(hexc("#b8682a"), hexc("#6a2e10"), smooth(0.4, 0.95, r)[:, None] * 0.9)
        iris = mix(iris, hexc("#e0a048"), (smooth(0.75, 0.45, np.abs(r - 0.55)) * fib * 0.3)[:, None])
        iris = mix(iris, hexc("#6a2e0e"), (smooth(0.4, 0.3, r) * 0.6)[:, None])       # the collarette
        iris = mix(iris, hexc("#2a1206"), (smooth(0.82, 1.0, r))[:, None])            # the dark rim round the iris
        iris = mix(iris, hexc("#5a2a0c"), (smooth(0.1, -0.6, S[:, 1]) * 0.35)[:, None])   # the lid's shadow above
        col = np.where((r < 1.0)[:, None], iris, hexc("#2a1a14"))
        col = mix(col, hexc("#050304"), smooth(0.46, 0.42, r)[:, None])                # the pupil
        mesh("eyeball", to_world(Vb), F, col, principled("eyeball", rough=0.35, spec=0.3))
        # the cornea: a clear dome over the iris
        bulge = 1.0 + 0.09 * smooth(0.55, 1.0, ca) ** 1.5
        Vc = c + (S * EYE_R * 1.03 * bulge[:, None]) @ Rm.T
        mesh("cornea", to_world(Vc), F, None, principled("cornea", color=(1, 1, 1, 1), rough=0.0, spec=0.8,
                                                         transmission=1.0, ior=1.376))
        # lid rims: a dark, slightly glossy rim round the opening
        A, B = EYE_HALF
        pts = []
        for t in np.linspace(0, 2 * np.pi, 72, endpoint=False):
            aa = A * 1.02 * np.cos(t)
            x = min(abs(aa) / A, 1.0)
            lim = B * (1.0 - x ** 2.0) ** 0.55 if np.sin(t) >= 0 else -B * 0.85 * (1.0 - x ** 2.0) ** 0.75
            pts.append(E + u * aa + v * (lim * 1.03 - 0.06 * aa))
        pts = surface_pts(head_raw, np.array(pts + pts[:1]), 0.0015)
        Vt, Ft = Ub.tube(pts, np.full(len(pts), 0.0019), 8)
        mesh("lidrim", to_world(Vt), np.array(Ft), None, principled("lidrim", color=hexc("#070506"), rough=0.55, spec=0.3))


def build_nose():
    c, r = NOSE
    S, F = sphere_mesh(96, 48)
    q = S.copy()
    q[:, 1] *= 1.0 - 0.22 * np.clip(-S[:, 2], 0, 1)          # narrower below
    q[:, 2] -= 0.25 * np.exp(-(S[:, 1] / 0.25) ** 2) * np.clip(-S[:, 2], 0, 1)   # the groove down the middle
    V = c + q * r * np.array([1.04, 1.03, 1.05])
    col = np.tile(hexc("#121014"), (len(V), 1))
    for s in (1, -1):                                         # nostrils: dark commas on the front
        dd = np.linalg.norm((V - (c + np.array([0.028, 0.019 * s, -0.004]))) / np.array([0.01, 0.009, 0.007]), axis=1)
        col = mix(col, hexc("#020102"), smooth(1.5, 0.9, dd)[:, None])
        V += (np.array([-0.005, 0, 0]) * smooth(1.5, 0.6, dd)[:, None])
    col = mix(col, hexc("#3c343c"), (smooth(0.0, 0.6, S[:, 2]) * 0.6)[:, None])
    # a pebbled leather: tiny bumps in the normals' place, as colour variation
    rng = np.random.default_rng(5)
    col *= (0.85 + 0.3 * rng.random(len(V)))[:, None]
    mesh("nose", to_world(V), F, col * 0.4, principled("nose", rough=0.45, spec=0.3, coat=0.12))


def build_mouth():
    """the tongue hanging over the lower lip; small teeth"""
    # the tongue: a long flat spoon from the floor of the mouth, out past the teeth and down over the lip
    m, k = 40, 17
    s = np.linspace(0, 1, m)
    path = []
    lip = JAW_HINGE + (np.array([0.184, 0.004, -0.097]) - JAW_HINGE) @ JAW_OPEN.T   # where it leaves the mouth
    for t in s:
        if t < 0.62:                                          # on the floor of the open jaw
            q = np.array([0.04 + (0.184 - 0.04) * t / 0.62, 0.004, -0.097])
            p = JAW_HINGE + (q - JAW_HINGE) @ JAW_OPEN.T
        else:                                                 # over the lip, falling under its own weight
            a = (t - 0.62) / 0.38 * np.radians(95)
            p = lip + np.array([0.022 * np.sin(a), 0.004 * (t - 0.62), -0.04 * (1 - np.cos(a))])
        path.append(p)
    path = np.array(path)
    for _ in range(4):
        path[1:-1] = (path[:-2] + 2 * path[1:-1] + path[2:]) / 4
    tang = unit(np.gradient(path, axis=0))
    side = np.array([0.0, 1.0, 0.0])
    up = unit(np.cross(tang, side))
    hw = 0.037 * (0.7 + 0.3 * smooth(0.0, 0.5, s)) * np.sqrt(np.clip(1 - smooth(0.8, 1.0, s) ** 2, 0.0, 1)) + 0.004
    th = 0.0065 * (1 - 0.35 * s)
    V, C = [], []
    for i in range(m):
        for j in range(k):
            a = 2 * np.pi * j / k
            yy, zz = np.cos(a), np.sin(a)
            groove = -0.35 * np.exp(-(yy / 0.25) ** 2) * (zz > 0)
            V.append(path[i] + side * yy * hw[i] + up[i] * (zz + groove) * th[i] - up[i] * th[i] * 0.2)
            C.append(mix(hexc("#e58c9e"), hexc("#c4627a"), 0.5 * smooth(0.2, -0.6, zz) + 0.3 * smooth(0.5, 0.0, s[i])))
    V = np.array(V)
    F = []
    for i in range(m - 1):
        for j in range(k):
            a, b, c, d = i * k + j, i * k + (j + 1) % k, (i + 1) * k + (j + 1) % k, (i + 1) * k + j
            F += [(a, b, c), (a, c, d)]
    V = np.vstack([V, path[-1] + tang[-1] * 0.002])
    C.append(C[-1])
    for j in range(k):
        F.append((len(V) - 1, (m - 1) * k + (j + 1) % k, (m - 1) * k + j))
    F = np.array(F)
    # drape it: the hanging part falls a little more under its own weight
    mesh("tongue", to_world(V), F, np.array(C), principled("tongue", rough=0.33, spec=0.5, sss=0.35,
                                                            sss_rad=(0.8, 0.25, 0.25), sss_scale=0.01, coat=0.25))
    # teeth: canines just inside the lips, and a row of small incisors behind the tongue
    tm = principled("tooth", color=hexc("#f6f0e2"), rough=0.25, spec=0.5, coat=0.3)
    for s_ in (1, -1):
        for base, dz, upper_jaw in (((0.165, 0.025 * s_, -0.1), -0.018, True),):
            b = np.array(base)
            if not upper_jaw:
                b = JAW_HINGE + (b - JAW_HINGE) @ JAW_OPEN.T
            pts = np.array([b, b + np.array([0.0, 0.0, dz * 0.55]), b + np.array([0.003, -0.002 * s_, dz])])
            Vt, Ft = Ub.tube(pts, np.array([0.0062, 0.0048, 0.001]), 10)
            mesh("tooth", to_world(Vt), np.array(Ft), None, tm)


# ================================================================== the skin
def skin_sdf(P):
    d = head_sdf(to_head(P)) * HS
    if HEAD_ONLY:
        return d
    return smin(d, body_sdf(P), 0.05)


def build_skin(h):
    if HEAD_ONLY:
        lo, hi = HEAD_C - 0.36, HEAD_C + 0.36
    else:
        lo, hi = np.array([-0.95, -0.36, -0.01]), np.array([1.0, 0.36, 1.5])
    F, o = sample(skin_sdf, lo, hi, h)
    V, T = surface_nets(F, o, h)
    V = project(skin_sdf, V, 2)
    N = grad(skin_sdf, V)
    col, part = skin_colours(V, N)
    log("skin", len(V), "verts")
    mesh("skin", V, T, col * 0.82, principled("skin", rough=0.62, spec=0.35, sss=0.08, sss_scale=0.004), N)
    return V, np.asarray(T), part, Grid(F, o, h)


def build_ears():
    for s in (1, -1):
        V, F, P, Nrm = ear_mesh(s)
        # inside: dark grey skin; outside: black
        nv, nu = P.shape[:2]
        n = len(V) // 2
        col = np.vstack([np.tile(hexc("#110e11"), (n, 1)), np.tile(BLACK_SKIN, (n, 1))])
        mesh("ear", to_world(V), F, col, principled("ear", rough=0.7, spec=0.2, sss=0.1, sss_scale=0.003))


# ================================================================== fur
class Grid:
    """the skin's distance field, sampled: fast lookups (trilinear) for keeping hair clear of the skin"""
    def __init__(self, F, o, h):
        self.F, self.o, self.h = F, np.asarray(o, np.float64), h
        self.n = np.array(F.shape)

    def __call__(self, P):
        g = (np.asarray(P) - self.o) / self.h
        i = np.clip(np.floor(g).astype(np.int64), 0, self.n - 2)
        f = np.clip(g - i, 0.0, 1.0)
        F = self.F
        x, y, z = i[:, 0], i[:, 1], i[:, 2]
        fx, fy, fz = f[:, 0], f[:, 1], f[:, 2]
        c00 = F[x, y, z] * (1 - fx) + F[x + 1, y, z] * fx
        c10 = F[x, y + 1, z] * (1 - fx) + F[x + 1, y + 1, z] * fx
        c01 = F[x, y, z + 1] * (1 - fx) + F[x + 1, y, z + 1] * fx
        c11 = F[x, y + 1, z + 1] * (1 - fx) + F[x + 1, y + 1, z + 1] * fx
        return (c00 * (1 - fy) + c10 * fy) * (1 - fz) + (c01 * (1 - fy) + c11 * fy) * fz

    def grad(self, P):
        return grad(self, P, self.h * 0.7)


def roots_on(V, T, count, rng):
    """random points spread evenly over a triangle mesh"""
    A = np.linalg.norm(np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]]), axis=1)
    tri = rng.choice(len(T), count, p=A / A.sum())
    r1, r2 = rng.random(count), rng.random(count)
    s1 = np.sqrt(r1)
    return (V[T[tri, 0]] * (1 - s1)[:, None] + V[T[tri, 1]] * (s1 * (1 - r2))[:, None]
            + V[T[tri, 2]] * (s1 * r2)[:, None])


class Coat:
    """strands gathered per batch, made into hair objects at the end (one per point count)"""
    def __init__(self):
        self.P, self.R, self.C = [], [], []

    def add(self, P, rad, col):
        self.P.append(P)
        self.R.append(rad)
        self.C.append(col)

    def build(self, name="fur"):
        total = 0
        for K in sorted({p.shape[1] for p in self.P}):
            P = np.concatenate([p for p in self.P if p.shape[1] == K])
            R = np.concatenate([r for r, p in zip(self.R, self.P) if p.shape[1] == K])
            C = np.concatenate([c for c, p in zip(self.C, self.P) if p.shape[1] == K])
            make_hair("%s%d" % (name, K), P, R, C)
            total += len(P)
        log("fur:", total, "strands")


def grow(R, N, comb, ln, lift, grav, K, field, clear=0.0012):
    """strands from roots R: out along the skin's normal by `lift`, along `comb`, bending under gravity, kept clear"""
    n = len(R)
    seg = ln / (K - 1)
    P = np.zeros((n, K, 3))
    P[:, 0] = R
    d = unit(N * lift[:, None] + comb * (1 - lift)[:, None])
    down = np.array([0.0, 0.0, -1.0])
    for k in range(1, K):
        d = unit(d + comb * 0.12 + down * (grav / (K - 1))[:, None])
        p = P[:, k - 1] + d * seg[:, None]
        if field is not None:
            want = clear + ln * lift * 0.35 * (k / (K - 1))
            dist = field(p)
            bad = dist < want
            if bad.any():
                p[bad] += field.grad(p[bad]) * (want[bad] - dist[bad])[:, None]
                p[bad] = P[bad, k - 1] + unit(p[bad] - P[bad, k - 1]) * seg[bad, None]
                d[bad] = unit(p[bad] - P[bad, k - 1])
        P[:, k] = p
    return P


def nearest(points, centres):
    from mathutils.kdtree import KDTree
    kd = KDTree(len(centres))
    for i, c in enumerate(centres):
        kd.insert(c, i)
    kd.balance()
    return np.array([kd.find(p)[1] for p in points], np.int64)


def clump(P, N, radius, strength, shape, rng, wave=0.0, freq=1.0, frizz=0.0):
    """gather strands into clumps: each pulls toward its clump's centre strand, more toward the tip"""
    n, K = P.shape[:2]
    R = P[:, 0]
    cell = radius * 1.7
    key = np.floor((R + rng.uniform(0, cell, 3)) / cell).astype(np.int64)
    perm = rng.permutation(n)
    _, first = np.unique(key[perm], axis=0, return_index=True)
    centres = perm[first]
    ci = centres[nearest(R, R[centres])]
    s = np.linspace(0, 1, K)
    w = (strength * s ** shape)[None, :, None] * rng.uniform(0.75, 1.0, (n, 1, 1))
    Q = P + (P[ci] - P) * w
    L = np.linalg.norm(P[:, -1] - P[:, 0], axis=1)
    if wave:
        ph = rng.uniform(0, 2 * np.pi, n)[ci]
        tang = unit(P[ci, -1] - P[ci, 0])
        side = unit(np.cross(tang, N[ci]) + 1e-9)
        Q += side[:, None] * (wave * L)[:, None, None] * (np.sin(s[None] * freq * 2 * np.pi + ph[:, None]) * s[None])[:, :, None]
    if frizz:
        Q += rng.normal(0, 1, (n, K, 3)) * (frizz * L)[:, None, None] * (s ** 2)[None, :, None]
    return Q


def settle(P, field, clear=0.001):
    """push any point of the strands that ended up under the skin back out"""
    n, K = P.shape[:2]
    F = P[:, 1:].reshape(-1, 3).copy()
    d = field(F)
    bad = d < clear
    if bad.any():
        F[bad] += field.grad(F[bad]) * (clear - d[bad])[:, None]
    P[:, 1:] = F.reshape(n, K - 1, 3)
    return P


def strand_radius(n, K, r0, rng):
    s = np.linspace(0, 1, K)
    return r0 * rng.uniform(0.8, 1.2, n)[:, None] * (1 - s[None]) ** 0.7 + 0.00012


def hair_material():
    m = bpy.data.materials.new("fur")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    hb = nt.nodes.new("ShaderNodeBsdfHairPrincipled")
    hb.parametrization = "COLOR"
    if CLAY:
        hb.inputs["Color"].default_value = (0.5, 0.5, 0.5, 1)
    else:
        at = nt.nodes.new("ShaderNodeAttribute")
        at.attribute_name = "fcol"
        nt.links.new(at.outputs["Color"], hb.inputs["Color"])
    hb.inputs["Roughness"].default_value = float(os.environ.get("HAIR_ROUGH", "0.3"))
    hb.inputs["Radial Roughness"].default_value = 0.55
    hb.inputs["Coat"].default_value = 0.05
    hb.inputs["IOR"].default_value = float(os.environ.get("HAIR_IOR", "1.42"))
    hb.inputs["Random Roughness"].default_value = 0.2
    nt.links.new(hb.outputs[0], out.inputs["Surface"])
    return m


HAIR_MAT = []


def make_hair(name, P, rad, col):
    n, K = P.shape[0], P.shape[1]
    cv = bpy.data.hair_curves.new(name)
    cv.add_curves([K] * n)
    cv.position_data.foreach_set("vector", P.astype(np.float32).reshape(-1))
    ra = cv.attributes.get("radius") or cv.attributes.new("radius", "FLOAT", "POINT")
    ra.data.foreach_set("value", rad.astype(np.float32).reshape(-1))
    C = np.broadcast_to(col[:, None, :3], (n, K, 3))
    ca = cv.attributes.new("fcol", "FLOAT_COLOR", "POINT")
    ca.data.foreach_set("color", np.concatenate([C, np.ones((n, K, 1))], 2).astype(np.float32).reshape(-1))
    ob = bpy.data.objects.new(name, cv)
    bpy.context.collection.objects.link(ob)
    if not HAIR_MAT:
        HAIR_MAT.append(hair_material())
    cv.materials.append(HAIR_MAT[0])
    return ob


HAIR_BLACK = np.array([0.005, 0.0065, 0.012])
HAIR_WHITE = np.array([0.76, 0.72, 0.63])


def hair_colour(c, rng):
    """the hair's colour from the skin's colour under it (white or black), with a little variety"""
    w = np.clip((c[:, :3].mean(1) - BLACK_SKIN[:3].mean()) / (WHITE[:3].mean() - BLACK_SKIN[:3].mean()), 0, 1)
    w = smooth(0.35, 0.65, w)
    col = HAIR_BLACK[None] * (1 - w)[:, None] + HAIR_WHITE[None] * w[:, None]
    return col * rng.uniform(0.8, 1.15, (len(c), 1))


def head_groom(L):
    """per root (head-local): length, lift, gravity and the comb direction"""
    x, y, z = L[:, 0], L[:, 1], L[:, 2]
    sd = np.where(y >= 0, 1.0, -1.0)
    n = len(L)
    one = np.ones(n)
    ln = np.full(n, 0.012)
    lift = np.full(n, 0.05)
    comb = np.stack([-one, 0.15 * sd, -0.15 * one], 1)
    muz = smooth(0.125, 0.17, x)
    ln = ln * (1 - muz) + 0.0065 * muz
    comb = comb * (1 - muz[:, None]) + np.stack([-one, 0.3 * sd, -0.1 * one], 1) * muz[:, None]
    crown = smooth(0.03, -0.12, x) * smooth(0.0, 0.08, z)
    ln += 0.018 * crown
    lift += 0.06 * crown
    cheek = smooth(0.05, 0.08, np.abs(y)) * smooth(0.05, -0.02, z) * smooth(0.11, 0.06, x)
    back = smooth(0.06, -0.1, x)
    ln += cheek * (0.012 + 0.1 * back)
    lift += cheek * (0.2 + 0.2 * back)
    comb = comb * (1 - cheek[:, None]) + np.stack([-0.7 * one, 0.5 * sd, -0.6 * one], 1) * cheek[:, None]
    throat = smooth(-0.09, -0.13, z) * smooth(0.08, 0.0, x)
    ln += throat * 0.05 * smooth(0.06, -0.1, x)
    comb = comb * (1 - throat[:, None]) + np.array([-1.0, 0.0, -0.3])[None] * throat[:, None]
    for s in (1, -1):                                         # round the eyes, the hair turns away from them
        E = EYES[s][0]
        q = L - E
        dist = np.linalg.norm(q, axis=1)
        k = smooth(0.06, 0.025, dist)
        comb = comb + unit(q) * k[:, None] * 1.2
        ln = ln * (1 - 0.35 * smooth(0.05, 0.03, dist))
    grav = 0.15 + 8.0 * ln
    return ln, lift, comb, grav


def lip_mask(L):
    du, dl, inside, Q = lip_lines(L)
    return inside | (du < 0.012) | (dl < 0.011)


def head_fur(coat, R, N, field, rng):
    L = to_head(R)
    keep = np.linalg.norm((L - NOSE[0]) / NOSE[1], axis=1) > 1.15
    for s in (1, -1):
        E, n, u, v = EYES[s]
        q = L - E
        keep &= almond(q @ u, q @ v) > 0.004
    keep &= ~lip_mask(L)
    R, L, N = R[keep], L[keep], N[keep]
    ln, lift, comb, grav = head_groom(L)
    comb = hdir(comb)
    comb = unit(comb - N * np.sum(comb * N, 1, keepdims=True))
    ln *= rng.uniform(0.8, 1.2, len(R))
    col, _ = head_colours(L, None)
    hc = hair_colour(col, rng)
    K = 6
    P = grow(R, N, comb, ln, lift, grav, K, field)
    P = clump(P, N, 0.006, 0.4, 1.5, rng, frizz=0.015)
    P = settle(P, field)
    coat.add(P, strand_radius(len(P), K, 0.0007, rng), hc)
    log("head fur", len(P))


def build_fur(coat, V, T, vpart, field, rng, total, head_total):
    Th = T[(vpart[T] == 0).all(1)]
    R = roots_on(V, Th, head_total, rng)
    head_fur(coat, R, field.grad(R), field, rng)
    if not HEAD_ONLY:
        R = roots_on(V, T, total, rng)
        N = field.grad(R)
        part, _ = classify(R)
        b = part != 0
        body_fur(coat, R[b], N[b], part[b], field, rng)


def bilinear(G, us, vs, u, v):
    """G sampled on the (vs, us) grid, read at (u, v)"""
    fi = np.clip((v - vs[0]) / (vs[-1] - vs[0]) * (len(vs) - 1), 0, len(vs) - 1.001)
    fj = np.clip((u - us[0]) / (us[-1] - us[0]) * (len(us) - 1), 0, len(us) - 1.001)
    i, j = fi.astype(int), fj.astype(int)
    a, b = (fi - i)[:, None], (fj - j)[:, None]
    return G[i, j] * (1 - a) * (1 - b) + G[i + 1, j] * a * (1 - b) + G[i, j + 1] * (1 - a) * b + G[i + 1, j + 1] * a * b


def ear_fur(coat, rng, count):
    for side in (1, -1):
        P, Nrm, vs, us, hw = ear_sheet(side)
        dP = np.gradient(P, axis=0)                           # along the ear, toward the tip
        dU = np.gradient(P, axis=1)
        n = count
        u = rng.uniform(-1, 1, n)
        v = rng.uniform(-0.1, 1.0, n)
        pos = bilinear(P, us, vs, u, v)
        nrm = unit(bilinear(Nrm, us, vs, u, v))
        alongv = unit(bilinear(dP, us, vs, u, v))
        acrossu = unit(bilinear(dU, us, vs, u, v))
        half = EAR_T * 0.5
        sg = np.sign(u)[:, None]
        groups = [
            # the back: short, sleek, combed toward the tip
            (pos - nrm * half, -nrm, alongv, 0.02 * (1 + 0.8 * smooth(0.3, 0.0, v)), np.full(n, 0.22), HAIR_BLACK,
             np.ones(n, bool)),
            # the edges: a fringe sticking out sideways and up
            (pos, acrossu * sg, unit(acrossu * sg * 0.6 + alongv * 0.8), rng.uniform(0.02, 0.045, n) * (1 - 0.4 * v),
             np.full(n, 0.4), HAIR_BLACK, np.abs(u) > 0.86),
            # inside: wisps from the lower cup, rising up and out over the opening
            (pos + nrm * half, nrm, unit(alongv + acrossu * sg * 0.6 + nrm * 0.3), rng.uniform(0.025, 0.05, n) * (1 - v),
             np.full(n, 0.35), HAIR_BLACK * 3.0, (v < 0.5) & (np.abs(u) < 0.85) & (rng.random(n) < 0.6)),
            # inside: a short fine coat over the whole face of the ear
            (pos + nrm * half, nrm, unit(alongv + acrossu * sg * 0.4), rng.uniform(0.01, 0.02, n), np.full(n, 0.15),
             HAIR_BLACK * 2.0, rng.random(n) < 0.8),
        ]
        for R, Nn, comb, ln, lift, col, m in groups:
            R, Nn, comb, ln, lift = R[m], Nn[m], comb[m], ln[m], lift[m]
            K = 5
            Pw = grow(to_world(R), hdir(Nn), hdir(comb), ln, lift, 0.4 + 6 * ln, K, None)
            Pw = clump(Pw, hdir(Nn), 0.005, 0.3, 1.5, rng, frizz=0.05)
            cc = np.tile(col, (len(R), 1)) * rng.uniform(0.8, 1.2, (len(R), 1))
            coat.add(Pw, strand_radius(len(R), K, 0.0006, rng), cc)
    log("ear fur done")


# ================================================================== the garden (only with --garden)
def noise2(u, v, rng, octaves=4, base=4.0):
    """smooth value noise on [0,1]^2 (numpy), roughly in [-1, 1]"""
    out = np.zeros_like(u)
    amp, f = 1.0, base
    for _ in range(octaves):
        n = int(f) + 2
        G = rng.uniform(-1, 1, (n + 1, n + 1))
        x, y = u * f, v * f
        i, j = np.clip(x.astype(int), 0, n - 1), np.clip(y.astype(int), 0, n - 1)
        fx, fy = x - i, y - j
        fx, fy = fx * fx * (3 - 2 * fx), fy * fy * (3 - 2 * fy)
        a = G[i, j] * (1 - fx) + G[i + 1, j] * fx
        b = G[i, j + 1] * (1 - fx) + G[i + 1, j + 1] * fx
        out += (a * (1 - fy) + b * fy) * amp
        amp *= 0.5
        f *= 2.0
    return out / 1.9


def stone_mesh(rx, ry, rz, rng, res=(40, 20)):
    S, F = sphere_mesh(*res)
    q = S.copy()
    q[:, 2] = np.sign(S[:, 2]) * np.abs(S[:, 2]) ** 0.45                # flat on top, rounded at the edges
    d = unit(S)
    bump = sum(np.sin(d @ unit(rng.normal(0, 1, 3)) * rng.uniform(2, 5) + rng.uniform(0, 6)) for _ in range(5)) / 5
    q = q * (1 + 0.08 * bump)[:, None]
    return q * np.array([rx, ry, rz]), F


G_O = np.array([0.17, 0.0, 0.0])                            # the garden is laid out round the dog


def g_axes():
    """away from the hero camera, and to its right, along the ground"""
    fwd = unit((G_O - cam_pos("hero")) * np.array([1, 1, 0]))
    return fwd, np.array([fwd[1], -fwd[0], 0.0])


def g_at(f, l):
    fwd, right = g_axes()
    return G_O + np.outer(np.atleast_1d(f), fwd) + np.outer(np.atleast_1d(l), right)


def g_fl(P):
    fwd, right = g_axes()
    q = (np.asarray(P) - G_O)[..., :2]
    return q @ fwd[:2], q @ right[:2]


POND = (1.9, -1.15, 0.8, 0.42)                              # (f, l, radius along, radius across)


def ground_h(P, rng_noise=None):
    """the ground's height: flat round the dog, a hillside rising behind, a hollow for the pond"""
    f, l = g_fl(P)
    h = 0.12 * np.clip(f - 1.4, 0, None) ** 1.5 + 0.05 * np.clip(np.abs(l) - 1.8, 0, None) ** 1.5
    h += 0.04 * np.sin(f * 1.7 + 1.0) * np.sin(l * 1.3) * smooth(0.5, 2.0, np.hypot(f, l))
    pf, pl, pa, pb = POND
    pd = ((f - pf) / pa) ** 2 + ((l - pl) / pb) ** 2
    h = h * (1 - smooth(1.6, 0.9, pd)) + (0.12 * max(pf - 1.4, 0) ** 1.5 - 0.05) * smooth(1.6, 0.9, pd)
    return h - 0.012


PATH_FL = np.array([(-2.6, -0.9), (-1.3, -0.5), (-0.2, -0.12), (0.57, 0.36), (1.5, 0.85), (2.6, 1.2), (3.7, 1.35),
                    (4.9, 1.85), (6.2, 2.1)])


def path_curve():
    c = curve(np.concatenate([PATH_FL, np.zeros((len(PATH_FL), 1))], 1), 120)
    P = g_at(c[:, 0], c[:, 1])
    P[:, 2] = ground_h(P)
    return P


def path_dist(xy):
    P = path_curve()
    xy = np.asarray(xy)[:, :2]
    out = np.empty(len(xy))
    for i in range(0, len(xy), 200000):
        out[i:i + 200000] = np.linalg.norm(xy[i:i + 200000, None, :] - P[None, :, :2], axis=2).min(1)
    return out


def blob_mesh(r, rng, res=(48, 24), rough=0.12):
    S, F = sphere_mesh(*res)
    d = unit(S)
    bump = sum(np.sin(d @ unit(rng.normal(0, 1, 3)) * rng.uniform(3, 8) + rng.uniform(0, 6)) for _ in range(7)) / 7
    return S * (r * (1 + rough * bump))[:, None] if np.ndim(r) else S * r * (1 + rough * bump)[:, None], F


class Batch:
    """many little meshes gathered into one object"""
    def __init__(self):
        self.V, self.F, self.C, self.n = [], [], [], 0

    def add(self, V, F, C):
        self.V.append(V)
        self.F.append(np.asarray(F) + self.n)
        C = np.asarray(C)
        self.C.append(np.broadcast_to(C[:3], (len(V), 3)) if C.ndim == 1 else C[:, :3])
        self.n += len(V)

    def build(self, name, mat):
        if self.V:
            mesh(name, np.vstack(self.V), np.vstack(self.F), np.vstack(self.C), mat)


def build_garden(rng):
    t0 = time.time()
    fwd, right = g_axes()
    # the ground and the hillside behind, mottled meadow greens, the path's earth showing through
    n = 400 if not QUICK else 220
    g = np.linspace(-10, 10, n)
    X, Y = np.meshgrid(g, g, indexing="ij")
    V = np.stack([X.ravel(), Y.ravel(), np.zeros(n * n)], 1)
    V[:, 2] = ground_h(V)
    F = np.array(Ub.grid_faces(n, n))
    f, l = g_fl(V)
    uu, vv = (V[:, 0] + 10) / 20, (V[:, 1] + 10) / 20
    nz = noise2(uu, vv, rng, 5, 8.0)
    col = mix(np.tile(hexc("#4a6224"), (len(V), 1)), hexc("#9aab4a"), np.clip(0.5 + 1.2 * nz, 0, 1)[:, None])
    col = mix(col, hexc("#3b5020"), (smooth(0.1, 0.5, noise2(uu, vv, rng, 4, 14.0)) * 0.5)[:, None])
    col = mix(col, hexc("#c3be6a"), (smooth(0.2, 0.6, noise2(uu, vv, rng, 3, 20.0)) * 0.35)[:, None])
    pd = path_dist(V)
    col = mix(col, hexc("#8a7a57"), smooth(0.5, 0.28, pd)[:, None])
    pf, pl, pa, pb = POND
    pond = ((f - pf) / pa) ** 2 + ((l - pl) / pb) ** 2
    col = mix(col, hexc("#5d5a4a"), smooth(1.25, 1.0, pond)[:, None])
    mesh("ground", V, F, col, principled("ground", rough=0.95, spec=0.2))
    # the pond: still water in its hollow, rocks round its back, a little fall of water from a ledge
    k = 96
    ring = np.array([g_at(pf + pa * 1.02 * np.cos(t), pl + pb * 1.02 * np.sin(t))[0] for t in np.linspace(0, 2 * np.pi, k, endpoint=False)])
    wz = 0.12 * max(pf - 1.4, 0) ** 1.5 - 0.045
    Vw = np.vstack([g_at(pf, pl), ring])
    Vw[:, 2] = wz
    Fw = np.array([(0, 1 + i, 1 + (i + 1) % k) for i in range(k)])
    water = principled("water", color=hexc("#3f6f80"), rough=0.04, spec=0.8, coat=0.3)
    mesh("pond", Vw, Fw, None, water)
    rocks = Batch()
    def rock(c, r, squash=0.7, tint=None):
        Vr, Fr = blob_mesh(r, rng, (40, 20), 0.18)
        Vr[:, 2] *= squash
        Vr = Vr + c
        top = smooth(-0.2, 0.9, unit(Vr - c)[:, 2])
        cr = mix(np.tile(hexc("#6d6a62") if tint is None else tint, (len(Vr), 1)), hexc("#a29e92"), top[:, None] * 0.6)
        cr = mix(cr, hexc("#5d7034"), (smooth(0.6, 0.95, unit(Vr - c)[:, 2]) * 0.5)[:, None])
        rocks.add(Vr, Fr, cr * (0.85 + 0.3 * rng.random(len(Vr)))[:, None])
    for t in np.linspace(-0.4, 3.6, 12):                     # rocks round the pond's far side
        p = g_at(pf + pa * 1.05 * np.cos(t), pl + pb * 1.15 * np.sin(t))[0]
        if np.cos(t) > -0.3:
            p[2] = ground_h(p[None])[0]
            rock(p, rng.uniform(0.12, 0.26))
    ledge = g_at(pf + pa * 0.95, pl - 0.05)[0]
    ledge[2] = ground_h(ledge[None])[0]
    for j, (df, dl, r) in enumerate(((0.15, -0.3, 0.32), (0.25, 0.25, 0.3), (0.4, 0.0, 0.36), (0.3, -0.55, 0.25))):
        rock(ledge + fwd * df + right * dl + np.array([0, 0, r * 0.55]), r, 0.85)
    fall = Batch()
    for j in range(14):                                      # the falling water: fine bright threads over the ledge
        top = ledge + right * (-0.2 + 0.03 * j + rng.normal(0, 0.006)) - fwd * 0.05 + np.array([0, 0, 0.44])
        pts = np.array([top + np.array([0, 0, -0.47 * t]) - fwd * 0.12 * t ** 2 for t in np.linspace(0, 1, 10)])
        Vt, Ft = Ub.tube(pts, np.linspace(0.004, 0.008, 10) * rng.uniform(0.7, 1.3), 6)
        fall.add(Vt, Ft, hexc("#dfeef5"))
    fall.build("waterfall", principled("fallwater", color=hexc("#dceaf0"), rough=0.1, spec=0.6, transmission=0.6, ior=1.33))
    # the path's stones, climbing with the ground
    P = path_curve()
    seg = np.linalg.norm(np.diff(P[:, :2], axis=0), axis=1)
    cum = np.concatenate([[0], np.cumsum(seg)])
    stones = Batch()
    s = 0.0
    while s < cum[-1]:
        i = int(np.clip(np.searchsorted(cum, s) - 1, 0, len(P) - 2))
        tng = unit((P[i + 1] - P[i]) * np.array([1, 1, 0]))
        nrm = np.array([-tng[1], tng[0], 0.0])
        far = smooth(2.0, 6.0, s)
        for side in ((-1, 1) if rng.random() < 0.55 else (0,)):
            rx, ry = rng.uniform(0.17, 0.25), rng.uniform(0.13, 0.19)
            p = P[i] + nrm * side * rng.uniform(0.11, 0.19) + np.array([rng.normal(0, 0.03), rng.normal(0, 0.03), 0])
            p[2] = ground_h(p[None])[0]
            Vs, Fs = stone_mesh(rx, ry, 0.03, rng)
            Vs = Vs @ rot((0, 0, 1), rng.uniform(0, 180)).T + p + np.array([0, 0, -0.012])
            cs = mix(np.tile(hexc("#a39478"), (len(Vs), 1)), hexc("#7d725e"), rng.random()) * (0.88 + 0.24 * rng.random(len(Vs)))[:, None]
            stones.add(Vs, Fs, cs)
        s += rng.uniform(0.34, 0.44)
    for _ in range(50):                                      # pebbles
        i = rng.integers(0, len(P))
        p = P[i] + np.array([rng.normal(0, 0.4), rng.normal(0, 0.4), 0])
        p[2] = ground_h(p[None])[0]
        r = rng.uniform(0.025, 0.07)
        Vs, Fs = stone_mesh(r, r * 0.8, r * 0.6, rng, (16, 8))
        stones.add(Vs + p + np.array([0, 0, r * 0.15]), Fs, hexc("#8f887a") * rng.uniform(0.75, 1.1))
    for (ff, ll, r) in ((1.6, 2.1, 0.5), (2.6, 2.8, 0.6), (1.2, 3.0, 0.4), (3.6, 3.4, 0.55), (0.9, -2.6, 0.35),
                        (3.0, 0.2, 0.3), (4.4, 0.6, 0.45)):
        p = g_at(ff, ll)[0]
        p[2] = ground_h(p[None])[0] + r * 0.25
        rock(p, r, 0.72, hexc("#77736a"))
    stones.build("stones", principled("stone", rough=0.8, spec=0.25))
    # bushes in blossom on the slopes: leafy mounds dotted with pink flowers
    leaves, blossom = Batch(), Batch()
    bushes = [(4.2, 2.6, 0.45), (5.6, 3.4, 0.55), (4.8, 4.4, 0.4), (6.6, -2.8, 0.5), (7.4, 2.0, 0.6), (8.0, -1.4, 0.65),
              (3.2, -2.7, 0.35), (6.2, 4.8, 0.5), (9.0, 0.6, 0.7)]
    for _ in range(26):
        ff = rng.uniform(3.0, 9.5)
        ll = rng.uniform(-4.5, 5.5)
        if abs(ll - np.interp(ff, PATH_FL[:, 0], PATH_FL[:, 1])) > 0.8:
            bushes.append((ff, ll, rng.uniform(0.2, 0.45)))
    for _ in range(18):
        ff, ll = rng.uniform(2.5, 8.0), rng.uniform(-4.0, 5.0)
        if abs(ll - np.interp(ff, PATH_FL[:, 0], PATH_FL[:, 1])) > 0.6:
            p = g_at(ff, ll)[0]
            r = rng.uniform(0.1, 0.3)
            p[2] = ground_h(p[None])[0] + r * 0.2
            rock(p, r, 0.7, hexc("#7a766c"))
    for ff, ll, r in bushes:
        c = g_at(ff, ll)[0]
        c[2] = ground_h(c[None])[0] + r * 0.45
        for _ in range(6):
            cc = c + rng.normal(0, r * 0.3, 3) * np.array([1, 1, 0.5])
            rr = r * rng.uniform(0.45, 0.7)
            Vb, Fb = blob_mesh(rr, rng, (32, 16), 0.2)
            Vb[:, 2] *= 0.8
            sh = smooth(-0.6, 0.8, unit(Vb)[:, 2])
            cb = mix(np.tile(hexc("#2f4a1e"), (len(Vb), 1)), hexc("#6f8f3a"), sh[:, None] * 0.8)
            leaves.add(Vb + cc, Fb, cb * (0.55 + 0.7 * rng.random(len(Vb)))[:, None])
            pinks = (hexc("#e88aae"), hexc("#f6c4d8"), hexc("#d76a98"))
            for _ in range(int(14 * rr / 0.3)):                 # clusters of small flowers
                d0 = unit(rng.normal(0, 1, 3) * np.array([1, 1, 0.6]) + np.array([0, 0, 0.6]))
                pc = pinks[rng.integers(0, 3)]
                for _ in range(rng.integers(6, 14)):
                    d = unit(d0 + rng.normal(0, 0.18, 3))
                    p = cc + d * rr * np.array([1, 1, 0.8]) * 1.01
                    Vp, Fp = sphere_mesh(8, 4)
                    Vp[:, 2] *= 0.6
                    blossom.add(Vp * rng.uniform(0.01, 0.018) + p, Fp, pc * rng.uniform(0.85, 1.1))
    for ff, ll, hgt in ((10.5, -1.6, 2.0), (11.0, 2.6, 2.4), (10.2, 4.6, 1.9), (9.6, -4.2, 2.2)):
        base = g_at(ff, ll)[0]
        base[2] = ground_h(base[None])[0]
        Vt, Ft = Ub.tube(np.array([base, base + np.array([0, 0, hgt * 0.5]), base + np.array([0, 0, hgt * 0.75])]),
                         np.array([0.12, 0.09, 0.06]), 10)
        leaves.add(Vt, Ft, hexc("#5a4632"))
        for _ in range(9):
            cc = base + np.array([0, 0, hgt * 0.8]) + rng.normal(0, 1, 3) * np.array([0.55, 0.55, 0.4]) * hgt * 0.4
            Vb, Fb = blob_mesh(hgt * rng.uniform(0.18, 0.28), rng, (32, 16), 0.2)
            sh = smooth(-0.6, 0.8, unit(Vb)[:, 2])
            cb = mix(np.tile(hexc("#34502a"), (len(Vb), 1)), hexc("#7d9a48"), sh[:, None] * 0.8)
            leaves.add(Vb + cc, Fb, cb * (0.6 + 0.6 * rng.random(len(Vb)))[:, None])
    leaves.build("bushes", principled("bush", rough=0.75, spec=0.2, sheen=0.3))
    rocks.build("rocks", principled("rock", rough=0.85, spec=0.2))
    blossom.build("blossom", principled("blossom", rough=0.5, spec=0.3, sss=0.2))
    # grass: blades all over the near meadow, thinner up the slope; none on the path or under the paws
    nb = 200000 if QUICK else 1100000
    ff = rng.uniform(-3.5, 4.5, nb * 2)
    ll = rng.uniform(-3.6, 3.6, nb * 2) * (1 + 0.25 * np.clip(ff, 0, None))
    keep = rng.random(nb * 2) < (1 - 0.6 * smooth(1.5, 4.5, ff))
    R = g_at(ff[keep], ll[keep])
    pond = ((g_fl(R)[0] - pf) / pa) ** 2 + ((g_fl(R)[1] - pl) / pb) ** 2
    ok = (path_dist(R) > 0.3 + 0.12 * rng.random(len(R))) & (pond > 1.15)
    for px, py in [(0.4 + FRONT_STEP[s_], 0.095 * s_) for s_ in (1, -1)] + [(-0.45 + HIND_STEP[s_], 0.1 * s_) for s_ in (1, -1)]:
        ok &= np.hypot(R[:, 0] - px, R[:, 1] - py) > 0.09
    R = R[ok][:nb]
    R[:, 2] = ground_h(R)
    nb = len(R)
    K = 5
    ln = rng.uniform(0.04, 0.12, nb) * (1 + 0.7 * smooth(0.6, 1.0, rng.random(nb)))
    lean = unit(np.stack([rng.normal(0, 1, nb), rng.normal(0, 1, nb), np.zeros(nb)], 1))
    tilt = rng.uniform(0.1, 0.6, nb)
    sg = np.linspace(0, 1, K)
    Pg = (R[:, None, :] + np.array([0, 0, 1.0])[None, None] * (ln[:, None] * sg[None])[..., None]
          + lean[:, None, :] * (ln * tilt)[:, None, None] * (sg ** 2)[None, :, None])
    rad = (0.0028 * rng.uniform(0.7, 1.3, nb))[:, None] * (1 - sg[None]) ** 0.8 + 0.0002
    gc = mix(np.tile(hexc("#4b6620"), (nb, 1)), hexc("#a6b64c"), rng.random(nb)[:, None])
    gc = mix(gc, hexc("#d9d07a"), (rng.random(nb) < 0.08)[:, None] * 0.6)
    make_curves("grass", Pg, rad, gc, grass_material())
    # little meadow flowers dotted in the grass, white and yellow
    dots = Batch()
    for _ in range(700 if not QUICK else 200):
        f_, l_ = rng.uniform(-1.5, 5.0), rng.uniform(-3.5, 3.5)
        p = g_at(f_, l_)[0]
        if path_dist(p[None])[0] < 0.4:
            continue
        p[2] = ground_h(p[None])[0] + rng.uniform(0.05, 0.12)
        Vp, Fp = sphere_mesh(8, 4)
        Vp[:, 2] *= 0.4
        dots.add(Vp * rng.uniform(0.012, 0.022) + p, Fp, (hexc("#f8f4ea"), hexc("#f2cf55"), hexc("#e9a3c3"))[rng.integers(0, 3)])
    dots.build("meadowflowers", principled("meadowflower", rough=0.5, spec=0.3))
    # flowers in the frame's lower corners: pink roses on the right, blue and orange ones on the left
    bq = Ub.Bouquet()
    d = -fwd
    blue = (hexc("#7fa6dc"), hexc("#c3d6f2"), hexc("#4e78bc"))
    orange = (hexc("#ee7a3c"), hexc("#f8b27c"), hexc("#c8521e"))
    for k in range(9):
        p = g_at(-rng.uniform(0.7, 1.3), rng.uniform(0.45, 0.85))[0]
        h = rng.uniform(0.08, 0.3)
        c = p + np.array([0, 0, h])
        Ub.rose(bq, c, unit(np.array([0, 0, 1.0]) + d * 0.5 + rng.normal(0, 0.15, 3)), rng.uniform(0.07, 0.12))
        Vt, Ft = Ub.tube(np.array([p, p + np.array([0, 0, h * 0.5]), c]), np.full(3, 0.006), 6)
        bq.add("leaf", Vt, Ft, np.tile(Ub.LEAF_RIB, (len(Vt), 1)))
        for j in range(3):
            Ub.leaf(bq, p + np.array([0, 0, h * rng.uniform(0.2, 0.6)]), np.array([0, 0, 1.0]),
                    rng.normal(0, 1, 3) * np.array([1, 1, 0]), 0.1, 0.035)
    for k in range(10):
        p = g_at(-rng.uniform(0.6, 1.3), -rng.uniform(0.55, 0.95))[0]
        h = rng.uniform(0.12, 0.42)
        c = p + np.array([0, 0, h])
        Ub.flower(bq, c, unit(np.array([0, 0, 1.0]) + d * 0.6 + rng.normal(0, 0.2, 3)), rng.uniform(0.04, 0.07), 5,
                  blue if k % 3 else orange, 1)
        Vt, Ft = Ub.tube(np.array([p, p + np.array([0.01, 0, h * 0.5]), c]), np.full(3, 0.004), 6)
        bq.add("leaf", Vt, Ft, np.tile(Ub.LEAF_RIB, (len(Vt), 1)))
        Ub.leaf(bq, p + np.array([0, 0, h * 0.3]), np.array([0, 0, 1.0]), rng.normal(0, 1, 3) * np.array([1, 1, 0]), 0.09, 0.03)
    bq.build("garden")
    log("garden built in %.1fs" % (time.time() - t0))


def grass_material():
    m = bpy.data.materials.new("grass")
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes["Principled BSDF"]
    at = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_name = "fcol"
    nt.links.new(at.outputs["Color"], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.55
    bs.inputs["Subsurface Weight"].default_value = 0.0
    bs.inputs["Transmission Weight"].default_value = 0.0
    bs.inputs["Specular IOR Level"].default_value = 0.3
    return m


def make_curves(name, P, rad, col, mat):
    n, K = P.shape[0], P.shape[1]
    cv = bpy.data.hair_curves.new(name)
    cv.add_curves([K] * n)
    cv.position_data.foreach_set("vector", P.astype(np.float32).reshape(-1))
    ra = cv.attributes.get("radius") or cv.attributes.new("radius", "FLOAT", "POINT")
    ra.data.foreach_set("value", rad.astype(np.float32).reshape(-1))
    C = np.broadcast_to(np.asarray(col)[:, None, :3], (n, K, 3))
    ca = cv.attributes.new("fcol", "FLOAT_COLOR", "POINT")
    ca.data.foreach_set("color", np.concatenate([C, np.ones((n, K, 1))], 2).astype(np.float32).reshape(-1))
    ob = bpy.data.objects.new(name, cv)
    bpy.context.collection.objects.link(ob)
    cv.materials.append(mat)
    return ob


def garden_lights():
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 2.2
    sun.angle = math.radians(6)
    sun.color = (1.0, 0.94, 0.82)
    ob = bpy.data.objects.new("sun", sun)
    bpy.context.collection.objects.link(ob)
    ob.rotation_euler = (-Vector((1.0, -0.15, 1.05))).to_track_quat("-Z", "Y").to_euler()
    L = bpy.data.lights.new("fill", "AREA")
    L.size, L.energy, L.color = 6.0, 260, (0.85, 0.92, 1.0)
    ob = bpy.data.objects.new("fill", L)
    bpy.context.collection.objects.link(ob)
    ob.location = cam_pos("hero") + np.array([0, 0, 1.5])
    ob.rotation_euler = (Vector((0.2, 0, 0.8)) - Vector(ob.location)).to_track_quat("-Z", "Y").to_euler()
    w = bpy.context.scene.world.node_tree.nodes["Background"]
    w.inputs["Color"].default_value = (0.75, 0.84, 0.95, 1)
    w.inputs["Strength"].default_value = 0.7


# ================================================================== scene
VIEWS_AT = {   # azimuth from +y toward +x, elevation, focus, distance, focal length (mm)
    "face": (56.0, 5.0, "hface", 2.0, 85.0),
    "head": (38.0, 6.0, None, 1.5, 85.0),
    "hface": (54.0, 8.0, "hface", 1.9, 85.0),
    "front": (88.0, 3.0, None, 1.3, 85.0),
    "side": (0.0, 2.0, None, 1.4, 85.0),
    "top": (60.0, 70.0, None, 1.5, 85.0),
    "back": (200.0, 10.0, None, 1.5, 85.0),
    "hero": (58.0, 6.0, (0.17, 0.0, 0.72), 4.7, 70.0),
    "flank": (15.0, 12.0, (-0.1, 0.0, 0.72), 1.9, 70.0),
    "ear": (60.0, 8.0, "ear", 0.75, 85.0),
    "dside": (0.0, 4.0, (0.02, 0.0, 0.66), 4.6, 70.0),
    "dfront": (90.0, 6.0, (0.1, 0.0, 0.66), 4.6, 70.0),
    "dback": (215.0, 12.0, (0.0, 0.0, 0.62), 4.6, 70.0),
}


def cam_pos(view):
    az, el, focus, dist, lens = VIEWS_AT[view]
    a, e = math.radians(az), math.radians(el)
    d = np.array([math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)])
    return np.asarray(focus if isinstance(focus, tuple) else to_world(np.array([0.06, 0.0, -0.01]))) + d * dist


def camera(view):
    az, el, focus, dist, lens = VIEWS_AT[view]
    named = {"hface": lambda: to_world(np.array([0.0, 0.0, 0.06])), "ear": lambda: to_world(ear_sheet(1)[0][20, 14]),
             None: lambda: to_world(np.array([0.06, 0.0, -0.01]))}
    focus = Vector(named[focus]() if focus is None or isinstance(focus, str) else focus)
    cam = bpy.data.cameras.new("cam")
    cam.lens = lens
    cam.sensor_width = 36
    ob = bpy.data.objects.new("cam", cam)
    bpy.context.collection.objects.link(ob)
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    ob.location = focus + d * dist
    ob.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob
    if GARDEN:
        cam.dof.use_dof = True
        cam.dof.focus_distance = dist
        cam.dof.aperture_fstop = 1.6 if view == "hero" else 5.0
    return ob


def lights():
    def area(name, loc, target, size, energy, col):
        L = bpy.data.lights.new(name, "AREA")
        L.size, L.energy, L.color = size, energy, col
        ob = bpy.data.objects.new(name, L)
        bpy.context.collection.objects.link(ob)
        ob.location = loc
        ob.rotation_euler = (Vector(target) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    tgt = (0.3, 0.0, 0.9)
    area("key", (4.0, 3.2, 4.2), tgt, 3.0, 900, (1.0, 0.93, 0.82))       # warm, high, from the front left of the view
    area("fill", (1.0, 5.0, 1.4), tgt, 5.0, 160, (0.85, 0.92, 1.0))      # soft and cool from the camera's side
    area("rim", (-3.5, -2.0, 3.5), tgt, 2.5, 700, (1.0, 0.95, 0.88))     # a bright edge from behind
    area("ground", (1.0, 1.5, -1.5), tgt, 4.0, 60, (0.8, 0.95, 0.6))     # green bounce from the grass


def setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    prefs = bpy.context.preferences.addons["cycles"].preferences
    try:
        prefs.compute_device_type = "OPTIX"
        prefs.get_devices()
        for d in prefs.devices:
            d.use = d.type == "OPTIX"
        sc.cycles.device = "GPU"
        log("rendering on", [d.name for d in prefs.devices if d.use])
    except Exception as e:
        sc.cycles.device = "CPU"
        log("GPU unavailable", e)
    sc.cycles.samples = 64 if QUICK or PREVIEW else 512
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02 if QUICK else 0.006
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 24
    sc.cycles.diffuse_bounces = 4
    sc.cycles.glossy_bounces = 8
    sc.cycles.transmission_bounces = 24
    sc.cycles.transparent_max_bounces = 24
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.look = "AgX - Medium High Contrast" if not CLAY else "None"
    sc.view_settings.exposure = 0.0
    w = bpy.data.worlds.new("world")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.78, 0.86, 0.95, 1)
    bg.inputs["Strength"].default_value = 0.5
    return sc


def main():
    os.makedirs(OUT, exist_ok=True)
    sc = setup()
    for s_ in (1, -1):
        log("eye", s_, EYES[s_][0].round(3), "ear base", EARS[s_][0].round(3))
    h = (0.004 if QUICK else 0.0022) if HEAD_ONLY else (0.007 if QUICK else 0.003)
    V, T, vpart, field = build_skin(h)
    build_ears()
    if not SKIN:
        rng = np.random.default_rng(11)
        coat = Coat()
        build_fur(coat, V, T, vpart, field, rng, 420000 if QUICK else 1600000, 90000 if QUICK else 320000)
        ear_fur(coat, rng, 8000 if QUICK else 30000)
        coat.build()
    build_eyes()
    build_nose()
    build_mouth()
    if GARDEN:
        build_garden(np.random.default_rng(21))
        garden_lights()
        sc.render.film_transparent = False
    else:
        lights()
    res = 640 if QUICK else (900 if PREVIEW else 1600)
    for v in VIEWS:
        sc.render.resolution_x = int(res * (0.75 if v == "hero" else 1.0))     # the hero is a portrait, like the picture
        sc.render.resolution_y = res
        cam = camera(v)
        sc.render.filepath = os.path.join(OUT, v + ".png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam)
        log("rendered", v)


if __name__ == "__main__":
    main()
