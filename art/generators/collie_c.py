"""Border collie C, "the fluffy young collie": a tricolour puppy (black, white and tan) standing on all fours, tail up,
head tilted. A sculpted body wears a coat of soft hair locks (flattened tapering ribbons laid down by gravity over the
body), the way a game can draw fur cheaply. Direction: two collie pictures the user shared (used as direction only,
nothing copied or traced). Built from scratch; it shares only generic helpers (the scene, the mesher and the shape
primitives) with the other generators.

Axes (Blender): x forward, y across (+y the near side, toward the camera), z up; ground z = 0.
Run:   blender -b --factory-startup -P collie_c.py -- OUTDIR [--quick] [--clay] [--bare] [view ...]
       views: hero head front side      --bare leaves the locks off (to judge the sculpt)"""
import bpy, math, os, sys
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import unicorn2 as Ub
from unicorn2_shape import ellipsoid, round_cone, smin, smax, rot, sample, surface_nets, project, grad

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "collie_c_out"
QUICK = "--quick" in argv
CLAY = "--clay" in argv
BARE = "--bare" in argv
VIEWS = [a for a in argv[1:] if not a.startswith("--")] or ["hero"]
H = 0.022 if QUICK else 0.01
hexc, mix, smooth = Ub.hexc, Ub.mix, Ub.smooth
Ub.CLAY = CLAY

# ------------------------------------------------------------------ the head, in its own frame (origin: the skull's centre)
HEAD_C = np.array([1.0, 0.0, 1.86])
HEAD_R = rot((0, 0, 1), 26.0) @ rot((1, 0, 0), -12.0) @ rot((0, 1, 0), -6.0)   # toward the viewer, a puppy's head tilt


def to_world(L):
    return HEAD_C + np.asarray(L) @ HEAD_R.T


def to_head(P):
    return (np.asarray(P) - HEAD_C) @ HEAD_R


def hdir(v):
    return np.asarray(v) @ HEAD_R.T


SKULL = (np.zeros(3), (0.5, 0.47, 0.45))
MUZZLE = (np.array([0.47, 0.0, -0.17]), (0.27, 0.25, 0.18))
NOSE = (np.array([0.715, 0.0, -0.075]), np.array([0.075, 0.098, 0.062]))
EYE_R = 0.1


def head_base(L):
    d = ellipsoid(L, *SKULL)
    d = smin(d, ellipsoid(L, np.array([0.2, 0.0, -0.14]), (0.36, 0.45, 0.3)), 0.2)      # round puppy cheeks
    d = smin(d, ellipsoid(L, np.array([0.3, 0.0, 0.08]), (0.26, 0.3, 0.24)), 0.16)     # the brow and a soft stop
    d = smin(d, ellipsoid(L, *MUZZLE), 0.16)
    d = smin(d, ellipsoid(L, np.array([0.45, 0.0, -0.3]), (0.18, 0.16, 0.08)), 0.08)   # the chin
    return d


def ray_hit(fn, o, d, lo=0.0, hi=2.0):
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
    E = ray_hit(head_base, np.array([0.05, 0.0, 0.05]), np.array([0.86, 0.44 * side, 0.1]))
    n = grad(head_base, E[None])[0]
    return E, n


EYES = {s: eye_spot(s) for s in (1, -1)}


def eye_centre(side):
    E, n = EYES[side]
    return E - n * (EYE_R * 0.55)


# the mouth: the philtrum down from the nose, then a curve out to each side with the corners turning up, a little open
def smile_pts(n=30):
    o = np.array([0.42, 0.0, -0.18])
    pts = []
    for t in np.linspace(0, 1, 6):
        pts.append(ray_hit(head_base, o, np.array([0.75, 0.0, -0.14 - 0.09 * t]) - o))
    for sgn in (1, -1):
        for t in np.linspace(0, 1, n // 2):
            y = 0.16 * t
            x = 0.74 - 0.12 * t ** 1.5
            z = -0.235 - 0.02 * np.sin(np.pi * t) + 0.05 * t ** 2.2
            pts.append(ray_hit(head_base, o, np.array([x, y * sgn, z]) - o))
    return np.array(pts)


SMILE = smile_pts()
MOUTH_OPEN = (np.array([0.715, 0.0, -0.245]), np.array([0.05, 0.075, 0.03]))


def seg_dist(P, pts):
    d = np.full(len(P), 9.0)
    segs = [(pts[i], pts[i + 1]) for i in range(5)]
    m = (len(pts) - 6) // 2
    for k in (0, 1):
        side = pts[6 + k * m: 6 + (k + 1) * m]
        segs += [(pts[5], side[0])] + [(side[i], side[i + 1]) for i in range(m - 1)]
    for a, b in segs:
        ab = b - a
        t = np.clip(((P - a) @ ab) / (ab @ ab), 0, 1)
        d = np.minimum(d, np.linalg.norm(P - (a + t[:, None] * ab), axis=1))
    return d


def head_carved(L):
    d = head_base(L)
    near = np.linalg.norm(L - np.array([0.68, 0.0, -0.22]), axis=1) < 0.35
    if near.any():
        s = np.full(len(L), 9.0)
        s[near] = seg_dist(L[near], SMILE)
        d = smax(d, -(s - 0.012), 0.008)
        d = smax(d, -ellipsoid(L, *MOUTH_OPEN), 0.02)
    return d


# ------------------------------------------------------------------ ears: soft puppy ears, a short rise then flopping down
def flat_cone(P, a, b, ra, rb, nrm, thick):
    """a round cone squashed along nrm: a soft leaf"""
    def sq(X):
        X = np.atleast_2d(X)
        return X + ((X @ nrm) * (1 / thick - 1))[:, None] * nrm[None]
    return round_cone(sq(P), sq(a)[0], sq(b)[0], ra, rb) * thick


def ear_geo(side):
    base = ray_hit(head_base, np.zeros(3), np.array([-0.12, 0.62 * side, 0.78]))
    hinge = base + np.array([0.04, 0.1 * side, 0.07])
    tip = hinge + np.array([0.12, 0.13 * side, -0.34])
    nrm = np.array([0.05, 1.0 * side, 0.32])
    nrm /= np.linalg.norm(nrm)
    return base, hinge, tip, nrm


EARS = {s: ear_geo(s) for s in (1, -1)}


def ear_sdf(L, side):
    base, hinge, tip, nrm = EARS[side]
    up_n = np.array([0.0, 0.35 * side, 1.0])
    up_n /= np.linalg.norm(up_n)
    d = flat_cone(L, base - (hinge - base) * 0.3, hinge, 0.15, 0.15, up_n, 0.4)
    d = smin(d, flat_cone(L, hinge, tip, 0.16, 0.07, nrm, 0.28), 0.06)
    return d


def head_sdf(L):
    d = head_carved(L)
    for s in (1, -1):
        d = smin(d, ear_sdf(L, s), 0.05)
    return d


# ------------------------------------------------------------------ the body (world): a round puppy, standing
NECK = (np.array([0.52, 0.0, 1.12]), np.array([0.92, 0.0, 1.68]))
TAIL = np.array([(-0.95, 0.0, 1.05), (-1.25, 0.02, 1.22), (-1.43, 0.05, 1.5), (-1.43, 0.08, 1.8), (-1.3, 0.1, 1.98)])


def body_sdf(P):
    d = ellipsoid(P, np.array([0.36, 0.0, 1.0]), (0.56, 0.48, 0.5))                         # chest
    d = smin(d, ellipsoid(P, np.array([-0.5, 0.0, 0.97]), (0.6, 0.46, 0.46)), 0.35)          # tummy and rump
    d = smin(d, round_cone(P, NECK[0], NECK[1], 0.36, 0.3), 0.2)
    for s in (1, -1):
        d = smin(d, round_cone(P, np.array([0.48, 0.26 * s, 0.75]), np.array([0.54, 0.27 * s, 0.15]), 0.2, 0.16), 0.12)
        d = smin(d, ellipsoid(P, np.array([0.65, 0.28 * s, 0.095]), (0.2, 0.155, 0.095)), 0.06)    # front paws
        d = smin(d, ellipsoid(P, np.array([-0.55, 0.31 * s, 0.72]), (0.4, 0.22, 0.38)), 0.18)      # thighs
        d = smin(d, round_cone(P, np.array([-0.62, 0.29 * s, 0.6]), np.array([-0.64, 0.28 * s, 0.15]), 0.18, 0.15), 0.1)
        d = smin(d, ellipsoid(P, np.array([-0.53, 0.28 * s, 0.095]), (0.2, 0.155, 0.095)), 0.06)   # hind paws
    return d


def tail_curve(m=40):
    t = np.linspace(0, 1, len(TAIL))
    s = np.linspace(0, 1, m)
    c = np.stack([np.interp(s, t, TAIL[:, k]) for k in range(3)], 1)
    for _ in range(4):
        c[1:-1] = (c[:-2] + 2 * c[1:-1] + c[2:]) / 4
    return c


TC = tail_curve()


def tail_sdf(P):
    d = np.full(len(P), 9.0)
    m = len(TC)
    for i in range(m - 1):
        r1, r2 = 0.1 - 0.05 * i / m, 0.1 - 0.05 * (i + 1) / m
        d = smin(d, round_cone(P, TC[i], TC[i + 1], r1, r2), 0.03)
    return d


def parts(P):
    h = head_sdf(to_head(P))
    b = body_sdf(P)
    t = tail_sdf(P)
    return h, b, t


def sdf(P):
    h, b, t = parts(P)
    return smin(smin(b, t, 0.08), h, 0.16)


# ------------------------------------------------------------------ colours
BLACK, BLACK2 = hexc("#18141a"), hexc("#2f282c")
WHITE, WHITE2 = hexc("#fbf8f2"), hexc("#e4ddd4")
TAN, TAN2 = hexc("#8f4c22"), hexc("#b06a34")
EAR_SKIN = hexc("#6a4542")


def colours(V, N):
    h, b, t = parts(V)
    L = to_head(V)
    n = len(V)
    head = smooth(0.04, -0.04, h - np.minimum(b, t))
    tail = (t < b) & (head < 0.5)
    x, y, z = L[:, 0], L[:, 1], L[:, 2]
    c = mix(np.tile(BLACK, (n, 1)), BLACK2, smooth(0.0, 0.9, N[:, 2]) * 0.5)
    # the face: tan brow dots and cheeks, a white blaze widening into a white muzzle and chin
    for s in (1, -1):
        E, nn = EYES[s]
        d = np.linalg.norm((L - (E + np.array([-0.03, 0.01 * s, 0.13]))) / np.array([0.07, 0.06, 0.045]), axis=1)
        c = mix(c, TAN, smooth(1.0, 0.6, d) * head)
        q = L - np.array([0.36, 0.3 * s, -0.12])
        q = np.stack([q[:, 0] * 0.9 + q[:, 2] * 0.43, q[:, 1], q[:, 2] * 0.9 - q[:, 0] * 0.43], 1)
        d = np.linalg.norm(q / np.array([0.2, 0.14, 0.12]), axis=1)
        c = mix(c, mix(TAN, TAN2, 0.3), smooth(1.0, 0.5, d) * head)
    bw = 0.03 + 0.03 * smooth(0.0, -0.3, x) + 0.17 * smooth(0.5, 0.62, x) * smooth(0.12, 0.0, z)
    blaze = smooth(bw + 0.02, bw - 0.015, np.abs(y)) * smooth(-0.1, 0.0, z) * smooth(0.5, 0.42, z) * (x > -0.25)
    muz = smooth(0.38, 0.46, x) * smooth(0.27, 0.2, np.abs(y)) * smooth(0.0, -0.06, z)
    chin = smooth(-0.24, -0.3, z) * smooth(0.25, 0.4, x)
    w = np.maximum(blaze, np.maximum(muz, chin)) * head
    # the body: a white collar right round the neck, the chest and tummy, the legs, the tail tip; tan above the paws
    a, bb = NECK
    ax = (bb - a) / np.linalg.norm(bb - a)
    tn = np.clip(((V - a) @ ax) / np.linalg.norm(bb - a), -1, 2)
    body = (1 - head) * (~tail)
    w = np.maximum(w, body * smooth(0.1, 0.25, tn) * smooth(0.85, 0.7, tn))
    front = smooth(0.15, 0.45, N[:, 0]) * smooth(0.3, 0.55, V[:, 0])
    w = np.maximum(w, body * front * smooth(1.6, 1.45, V[:, 2]))
    w = np.maximum(w, body * smooth(-0.25, -0.55, N[:, 2]) * smooth(0.9, 0.75, V[:, 2]))
    w = np.maximum(w, body * smooth(0.42, 0.34, V[:, 2]))
    tanleg = body * smooth(0.34, 0.42, V[:, 2]) * smooth(0.58, 0.5, V[:, 2]) * (np.abs(V[:, 1]) > 0.12)
    tanleg *= (np.abs(V[:, 0] - 0.53) < 0.25) | (np.abs(V[:, 0] + 0.62) < 0.25)
    if tail.any():
        k = np.argmin(np.linalg.norm(V[tail][:, None] - TC[None], axis=2), 1)
        wt = np.zeros(n)
        wt[tail] = smooth(0.8, 0.88, k / (len(TC) - 1))
        w = np.maximum(w, wt)
    wc = mix(np.tile(WHITE, (n, 1)), WHITE2, smooth(0.2, -0.7, N[:, 2]) * 0.45)
    c = mix(c, TAN, tanleg * 0.9)
    c = mix(c, wc, w)
    sm = seg_dist(L, SMILE)
    c = mix(c, hexc("#3a2a2e"), smooth(0.03, 0.012, sm) * head)
    # the ears: dark outside, soft brown skin inside
    for s in (1, -1):
        base, hinge, tip, nrm = EARS[s]
        e = (ear_sdf(L, s) < head_carved(L) + 0.01) & (np.linalg.norm(L - hinge, axis=1) < 0.45)
        inside = e & (((L - hinge) @ nrm) < -0.01)
        c = mix(c, EAR_SKIN, inside * 0.85)
    return c


# ------------------------------------------------------------------ hair locks
def lock_roots(V, T, N, rng, count):
    """roots for the coat's locks: area-weighted over the surface, with what each region's lock looks like"""
    A = np.linalg.norm(np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]]), axis=1) / 2
    tri = rng.choice(len(T), count, p=A / A.sum())
    r1, r2 = rng.random(count), rng.random(count)
    s1 = np.sqrt(r1)
    R = V[T[tri, 0]] * (1 - s1)[:, None] + V[T[tri, 1]] * (s1 * (1 - r2))[:, None] + V[T[tri, 2]] * (s1 * r2)[:, None]
    R = project(sdf, R, 2)
    Nr = grad(sdf, R)
    h, b, t = parts(R)
    L = to_head(R)
    head = h < np.minimum(b, t)
    tail = (t < b) & ~head
    x, y, z = L[:, 0], L[:, 1], L[:, 2]
    n = len(R)
    ln = np.full(n, 0.27)
    wd = np.full(n, 0.052)
    lift = np.full(n, 0.12)
    comb = np.tile(np.array([-1.0, 0.0, -0.45]), (n, 1))
    keep = np.ones(n, bool)
    # the head: a fluffy crown combed back, cheek fluff sweeping back, nothing on the face itself
    crown = head & (z > 0.05) & (x < -0.22)
    cheek = head & (np.abs(y) > 0.3) & (z < 0.08) & (x < -0.02)
    earm = np.zeros(n, bool)
    for s in (1, -1):
        earm |= head & (ear_sdf(L, s) < head_carved(L)) & (np.linalg.norm(L - EARS[s][1], axis=1) < 0.45)
    keep &= ~head | ((crown | cheek) & ~earm & (rng.random(n) < 0.45))
    ln = np.where(head, 0.1, ln)
    wd = np.where(head, 0.04, wd)
    lift = np.where(head, 0.02, lift)
    comb = np.where(head[:, None], hdir(np.array([-1.0, 0.0, -0.3]))[None], comb)
    cheek_dir = np.stack([np.full(n, -0.9), np.sign(y) * 0.2, np.full(n, -0.45)], 1) @ HEAD_R.T
    comb = np.where(cheek[:, None], cheek_dir, comb)
    ln = np.where(cheek, 0.13, ln)
    # the ears: a short fringe along their hanging edge
    for s in (1, -1):
        base, hinge, tip, nrm = EARS[s]
        e = head & (ear_sdf(L, s) < head_carved(L)) & (np.linalg.norm(L - hinge, axis=1) < 0.45)
        ln = np.where(e, 0.07, ln)
        wd = np.where(e, 0.04, wd)
        lift = np.where(e, 0.05, lift)
        comb = np.where(e[:, None], hdir((tip - hinge) / np.linalg.norm(tip - hinge))[None], comb)
    # the ruff: long, fluffy, standing out and falling down the front of the chest
    a, bb = NECK
    ax = (bb - a) / np.linalg.norm(bb - a)
    tn = ((R - a) @ ax) / np.linalg.norm(bb - a)
    ruff = ~head & ~tail & (tn > -0.25) & (tn < 1.1)
    ln = np.where(ruff, 0.32 + 0.12 * smooth(-0.2, 0.6, Nr[:, 0]), ln)
    wd = np.where(ruff, 0.06, wd)
    lift = np.where(ruff, 0.3, lift)
    comb = np.where(ruff[:, None], np.array([-0.2, 0.0, -1.0])[None], comb)
    # the tummy: a fringe hanging down
    belly = ~head & ~tail & (Nr[:, 2] < -0.35) & (R[:, 2] > 0.5)
    ln = np.where(belly, 0.26, ln)
    comb = np.where(belly[:, None], np.array([-0.3, 0.0, -1.0])[None], comb)
    # legs: short and sleek, feathered at the back of the front legs, britches on the hind legs
    leg = ~head & ~tail & (R[:, 2] < 0.62)
    ln = np.where(leg, 0.07 + 0.12 * smooth(0.0, -0.7, Nr[:, 0]) * smooth(0.25, 0.5, R[:, 2]), ln)
    wd = np.where(leg, 0.04, wd)
    lift = np.where(leg, 0.06, lift)
    ln = np.where(leg & (R[:, 2] < 0.36), 0.06, ln)          # short and tidy down to the paws
    wd = np.where(leg & (R[:, 2] < 0.36), 0.032, wd)
    comb = np.where(leg[:, None], np.array([-0.2, 0.0, -1.0])[None], comb)
    brit = ~head & ~tail & (R[:, 0] < -0.55) & (R[:, 2] > 0.35) & (R[:, 2] < 0.9) & (Nr[:, 0] < -0.2)
    ln = np.where(brit, 0.26, ln)
    keep &= R[:, 2] > 0.17
    # the tail: a plume combed toward its tip, longest in the middle
    k = np.argmin(np.linalg.norm(R[:, None] - TC[None], axis=2), 1)
    Tg = np.gradient(TC, axis=0)
    td = Tg[k] / np.linalg.norm(Tg[k], axis=1, keepdims=True)
    comb = np.where(tail[:, None], td + np.array([0, 0, -0.25]), comb)
    ln = np.where(tail, 0.2 + 0.26 * np.sin(np.pi * np.clip(k / len(TC) * 1.05, 0, 1)), ln)
    wd = np.where(tail, 0.06, wd)
    lift = np.where(tail, 0.3, lift)
    ln = ln * rng.uniform(0.8, 1.2, n)
    wd = wd * rng.uniform(0.85, 1.15, n)
    comb = comb - Nr * np.sum(comb * Nr, 1, keepdims=True)
    comb /= np.maximum(np.linalg.norm(comb, axis=1, keepdims=True), 1e-9)
    grav = np.where(tail, 1.0, np.where(head, 0.5, 1.4))
    return R[keep], Nr[keep], ln[keep], wd[keep], lift[keep], comb[keep], grav[keep]


def drape(R, N, ln, lift, comb, grav, m=12):
    """centre lines: out along the comb, lifted off the skin, bending under gravity, sliding over the body"""
    d = N * lift[:, None] + comb
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    p = R + N * 0.004
    P = [p.copy()]
    for i in range(m - 1):
        t = (i + 1) / (m - 1)
        ds = ln / (m - 1)
        d = d + np.array([0, 0, -1.0])[None] * (grav * ds * 2.2 * smooth(0.1, 0.6, t))[:, None]
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        q = p + d * ds[:, None]
        f = sdf(q)
        want = 0.012 + 0.02 * t
        hit = f < want
        if hit.any():
            g = grad(sdf, q[hit])
            q[hit] += g * (want - f[hit])[:, None]
            dd = d[hit] - g * np.sum(d[hit] * g, 1, keepdims=True)
            d[hit] = dd / np.maximum(np.linalg.norm(dd, axis=1, keepdims=True), 1e-9)
        p = q
        P.append(p.copy())
    return np.stack(P, 1)


def lock_meshes(C, N0, wd, cols, rng, ring=8, thick=0.24):
    """every lock as one flattened tapering tube: wide side lying on the body, a pointed soft tip"""
    nl, m, _ = C.shape
    T_ = np.gradient(C, axis=1)
    T_ /= np.maximum(np.linalg.norm(T_, axis=2, keepdims=True), 1e-9)
    Nn = np.repeat(N0[:, None], m, 1)
    Nn = Nn - T_ * np.sum(Nn * T_, 2, keepdims=True)
    Nn /= np.maximum(np.linalg.norm(Nn, axis=2, keepdims=True), 1e-9)
    Bn = np.cross(T_, Nn)
    t = np.linspace(0, 1, m)
    ph = rng.uniform(0, 6.28, nl)[:, None]
    fq = rng.uniform(0.7, 1.3, nl)[:, None]
    C = C + Bn * (wd[:, None] * 0.7 * np.sin(2 * np.pi * fq * t[None] + ph) * smooth(0.0, 0.6, t)[None])[:, :, None]
    w = (0.55 + 0.45 * np.sin(np.pi * np.minimum(1.0, t * 1.6))) * (1 - 0.94 * smooth(0.45, 1.0, t) ** 1.2)
    W = wd[:, None] * w[None] + 0.003
    th = 2 * np.pi * np.arange(ring) / ring
    cu = 0.25                                                   # a slight curl of the ribbon's edges toward the skin
    V = (C[:, :, None] + Bn[:, :, None] * (W[:, :, None, None] * np.cos(th)[None, None, :, None])
         + Nn[:, :, None] * (W[:, :, None, None] * (thick * np.sin(th) - cu * np.cos(th) ** 2 + cu * 0.5)[None, None, :, None]))
    V = V.reshape(-1, 3)
    shade = 0.9 + 0.1 * (np.sin(th)[None, None, :] * 0.5 + 0.5)
    tipl = smooth(0.5, 1.0, t)[None, :, None]
    jit = rng.uniform(0.9, 1.06, nl)[:, None, None]
    Cc = cols[:, None, None, :3] * (shade * (0.92 + 0.12 * tipl) * jit)[..., None]
    Cc = np.concatenate([np.clip(Cc, 0, 1), np.ones(Cc.shape[:3] + (1,))], 3).reshape(-1, 4)
    F = []
    base_faces = np.array(Ub.grid_faces(m, ring, wrap_v=True))
    for i in range(nl):
        F.append(base_faces + i * m * ring)
    return V, np.concatenate(F), Cc


# ------------------------------------------------------------------ eyes, nose, tongue
def build_face():
    dark = Ub.material("lid", rough=0.5, spec=0.3, color=hexc("#0f0c0d"))
    for side in (1, -1):
        c = eye_centre(side)
        E, n = EYES[side]
        look = n + np.array([0.35, -0.2 * side, 0.05])
        look /= np.linalg.norm(look)
        up = np.array([0.0, 0.0, 1.0]) - look * look[2]
        up /= np.linalg.norm(up)
        Vs, Fs = Ub.uv_sphere(np.zeros(3), EYE_R, 56, 36)
        d = Vs / EYE_R
        ca = d @ look
        hh = d @ up
        iris = smooth(np.cos(np.radians(58)), np.cos(np.radians(55)), ca)
        pupil = smooth(np.cos(np.radians(32)), np.cos(np.radians(29)), ca)
        rim = smooth(np.cos(np.radians(49)), np.cos(np.radians(56)), ca) * iris
        ic = mix(hexc("#b8722e"), hexc("#4a240c"), smooth(-0.55, 0.45, hh))
        ic = mix(ic, hexc("#231005"), rim * 0.85)
        ic = mix(ic, hexc("#070405"), pupil)
        col = mix(hexc("#22150f"), ic, iris)
        Ub.add_mesh("eye", to_world(c + Vs), Fs, col, Ub.material("eye", rough=0.12, spec=0.65, coat=0.9))
        a = np.cross(look, up)
        for du, dv, rr in ((0.45, 0.5, 0.032), (-0.35, -0.42, 0.014)):
            dirn = look + a * du * 0.6 + up * dv * 0.6
            dirn /= np.linalg.norm(dirn)
            gc = c + dirn * (EYE_R + 0.002)
            ga = np.cross(dirn, up); ga /= np.linalg.norm(ga)
            gb = np.cross(ga, dirn)
            Vg = [gc] + [gc + (ga * np.cos(q) + gb * np.sin(q) * 0.8) * rr for q in np.linspace(0, 2 * np.pi, 18, endpoint=False)]
            Ub.add_mesh("glint", to_world(np.array(Vg)), [(0, k + 1, (k + 1) % 18 + 1) for k in range(18)], None,
                        Ub.material("glint", emit=5.0, color=(1, 1, 1, 1)))
        ring = np.array([c + (np.cos(q) * a + np.sin(q) * up) * (EYE_R * 1.0) + look * EYE_R * 0.25
                         for q in np.linspace(np.radians(12), np.radians(168), 30)])
        rad = 0.006 + 0.008 * np.sin(np.linspace(0, np.pi, len(ring)))
        Vt, Ft = Ub.tube(ring, rad, 8)
        Ub.add_mesh("lid", to_world(Vt), Ft, None, dark)
    c, r = NOSE
    Vn, Fn = Ub.uv_sphere(np.zeros(3), 1.0, 44, 26)
    sh = Vn.copy()
    sh[:, 1] *= 1.0 - 0.3 * np.clip(-Vn[:, 2], 0, 1)
    sh[:, 2] += 0.12 * (1 - Vn[:, 1] ** 2) * (Vn[:, 2] > 0)
    Vn = sh * r + c
    cn = np.tile(hexc("#17141a"), (len(Vn), 1))
    for s in (1, -1):
        dd = np.linalg.norm((Vn - (c + np.array([0.07, 0.042 * s, -0.008]))) / np.array([0.025, 0.022, 0.018]), axis=1)
        cn = mix(cn, hexc("#030203"), smooth(1.4, 0.8, dd))
    cn = mix(cn, hexc("#4a3f46"), smooth(0.02, 0.07, Vn[:, 2] - c[2]) * 0.5)
    Ub.add_mesh("nose", to_world(Vn), Fn, cn, Ub.material("nose", rough=0.3, spec=0.55, coat=0.4))
    mc, mr = MOUTH_OPEN
    Vt, Ft = Ub.uv_sphere(np.zeros(3), 1.0, 26, 14)
    q = Vt * np.array([0.065, 0.065, 0.026])
    q[:, 2] -= 0.03 * np.clip(q[:, 0] / 0.065 + 0.3, 0, 1.3) ** 2
    ct = mix(np.tile(hexc("#ef8fa3"), (len(q), 1)), hexc("#d46a85"), smooth(0.01, -0.04, q[:, 0]))
    Ub.add_mesh("tongue", to_world(q + mc + np.array([0.02, 0.0, -0.006])), Ft, ct,
                Ub.material("tongue", rough=0.35, sss=0.3, spec=0.45, coat=0.2))


# ------------------------------------------------------------------ scene
VIEWS_AT = {"hero": (55.0, 8.0, (0.05, 0.0, 1.12), 3.6), "head": (52.0, 5.0, tuple(to_world([0.15, 0.0, -0.05])), 1.55),
            "front": (88.0, 4.0, (0.4, 0.0, 1.15), 3.1), "side": (0.0, 3.0, (-0.1, 0.0, 1.1), 3.9)}


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
        ob.rotation_euler = (Vector((0.3, 0, 1.4)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    area("key", (6, 6, 7), 6, 900, (1.0, 0.96, 0.9))
    area("fill", (7, -3, 3), 7, 280, (0.92, 0.95, 1.0))
    area("rim", (-5, -2, 6), 4, 560, (1.0, 0.95, 0.88))
    area("bounce", (2, 3, -2), 6, 90, (1.0, 0.98, 0.92))


def main():
    os.makedirs(OUT, exist_ok=True)
    sc = Ub.setup()
    sc.view_settings.exposure = -0.05
    rng = np.random.default_rng(11)
    F, o = sample(sdf, (-1.85, -0.85, 0.0), (1.95, 0.85, 2.6), H)
    V, T = surface_nets(F, o, H)
    V = project(sdf, V, 2)
    N = grad(sdf, V)
    col = colours(V, N)
    coat = Ub.material("coat", rough=0.85, sss=0.1, sheen=0.9, spec=0.12)
    Ub.add_mesh("body", V, T, col, coat, N)
    if not BARE:
        R, Nr, ln, wd, lift, comb, grav = lock_roots(V, np.array(T), N, rng, 3600 if QUICK else 7500)
        C = drape(R, Nr, ln, lift, comb, grav, m=10 if QUICK else 14)
        cols = colours(R, Nr)
        Vl, Fl, Cl = lock_meshes(C, Nr, wd, cols, rng)
        Ub.add_mesh("locks", Vl, [tuple(f) for f in Fl], Cl, Ub.material("locks", rough=0.62, sss=0.08, sheen=0.8, spec=0.22))
        print("locks", len(R), "verts", len(Vl))
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
