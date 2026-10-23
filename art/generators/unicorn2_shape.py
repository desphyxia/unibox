"""The shape of the new unicorn (unicorn2.py), as one signed distance field: body, neck, legs and head are blended
primitives (ellipsoids and round cones joined with smooth minimums), so the animal is one fused surface with no seams.
Eye sockets, the nostril and the smile are carved into it. numpy only, so it runs inside Blender or outside.

Axes (Blender): x forward (toward the head), y across (+y is the near side, toward the hero camera), z up; ground z = 0.
The head is modelled straight ("head-local" coordinates) and then turned toward the viewer and tilted (HEAD_*).

surface_nets() turns a sampled field into a mesh (a vertex in every cell the surface crosses, a quad across every
crossing edge), and project() pulls vertices exactly onto the surface."""
import os
import numpy as np

STAND = bool(os.environ.get("UNI2_STAND"))                   # the game's rest pose: head straight, all four hooves down

# ------------------------------------------------------------------ primitives
def _len(v):
    return np.sqrt(np.sum(v * v, axis=-1))


def sphere(P, c, r):
    return _len(P - c) - r


def ellipsoid(P, c, rad):
    q = P - c
    rad = np.asarray(rad, np.float64)
    k0 = _len(q / rad)
    k1 = _len(q / (rad * rad))
    return k0 * (k0 - 1.0) / np.maximum(k1, 1e-9)


def round_cone(P, a, b, r1, r2):
    """a capsule whose radius runs from r1 at a to r2 at b (exact distance)"""
    a = np.asarray(a, np.float64)
    b = np.asarray(b, np.float64)
    ba = b - a
    l2 = ba @ ba
    rr = r1 - r2
    a2 = l2 - rr * rr
    il2 = 1.0 / l2
    pa = P - a
    y = pa @ ba
    z = y - l2
    q = pa * l2 - y[:, None] * ba
    x2 = np.sum(q * q, axis=-1)
    y2 = y * y * l2
    z2 = z * z * l2
    k = np.sign(rr) * rr * rr * x2
    d_end = np.sqrt(x2 + z2) * il2 - r2
    d_start = np.sqrt(x2 + y2) * il2 - r1
    d_mid = (np.sqrt(np.maximum(x2 * a2 * il2, 0.0)) + y * rr) * il2 - r1
    return np.where(np.sign(z) * a2 * z2 > k, d_end, np.where(np.sign(y) * a2 * y2 < k, d_start, d_mid))


def squash(fn, P, sy, *args):
    """a primitive narrowed across (y) by sy: evaluated in stretched space, distance scaled back (close enough)"""
    Q = P * np.array([1.0, 1.0 / sy, 1.0])
    return fn(Q, *args) * sy


def smin(a, b, k):
    h = np.maximum(k - np.abs(a - b), 0.0) / k
    return np.minimum(a, b) - h * h * k * 0.25


def smax(a, b, k):
    return -smin(-a, -b, k)


def rot(axis, deg):
    a = np.radians(deg)
    c, s = np.cos(a), np.sin(a)
    x, y, z = axis
    return np.array([[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
                     [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
                     [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]])


# ------------------------------------------------------------------ the head's turn
HEAD_PIVOT = np.array([1.22, 0.0, 3.85])                     # top of the neck
HEAD_YAW = 0.0 if STAND else 22.0                            # toward the viewer (+y)
HEAD_PITCH = 7.0                                             # nose down a little
HEAD_ROLL = 0.0 if STAND else -7.0                           # a sweet tilt
HEAD_M = rot((0, 0, 1), HEAD_YAW) @ rot((0, 1, 0), HEAD_PITCH) @ rot((1, 0, 0), HEAD_ROLL)


def head_to_world(L):
    return HEAD_PIVOT + (np.asarray(L) - HEAD_PIVOT) @ HEAD_M.T


def world_to_head(P):
    return HEAD_PIVOT + (P - HEAD_PIVOT) @ HEAD_M


def head_dir(v):
    return np.asarray(v) @ HEAD_M.T


# ------------------------------------------------------------------ the eyes (head-local)
CRANIUM = (np.array([1.42, 0.0, 4.72]), np.array([1.02, 0.92, 0.98]))
EYE_HALF = (0.37, 0.3)                                       # the almond's half width and half height
EYE_DEPTH = 0.36


def _head_raw(L):
    """the head before carving, head-local points"""
    c, r = CRANIUM
    cran = ellipsoid(L, c, r)
    fore = sphere(L, np.array([1.85, 0.0, 4.95]), 0.68)
    jaw = ellipsoid(L, np.array([1.74, 0.0, 4.24]), (0.8, 0.66, 0.56))
    cheek = ellipsoid(L, np.array([1.66, 0.0, 4.42]), (0.66, 0.76, 0.52))
    muz = squash(round_cone, L, 0.82, (2.0, 0.0, 4.32), (2.72, 0.0, 4.04), 0.56, 0.41)
    d = smin(cran, fore, 0.32)
    d = smin(d, jaw, 0.3)
    d = smin(d, cheek, 0.25)
    d = smin(d, muz, 0.24)
    return d


def _ray_hit(fn, o, d, lo=0.0, hi=2.5):
    """where a ray from inside the shape leaves it (bisection on fn)"""
    o = np.asarray(o, np.float64)
    d = np.asarray(d, np.float64) / np.linalg.norm(d)
    for _ in range(60):
        m = (lo + hi) / 2
        if fn((o + d * m)[None])[0] < 0:
            lo = m
        else:
            hi = m
    return o + d * lo


def _grad(fn, p, h=1e-3):
    p = np.asarray(p, np.float64)
    e = np.eye(3) * h
    g = np.array([(fn((p + e[i])[None])[0] - fn((p - e[i])[None])[0]) / (2 * h) for i in range(3)])
    return g / np.linalg.norm(g)


def _eye_frame(side):
    """(centre on the uncarved head, outward normal, forward-along-face, up-along-face) for one eye, head-local"""
    c, _ = CRANIUM
    d = np.array([0.55, 0.78 * side, -0.12])
    E = _ray_hit(_head_raw, c, d)
    n = _grad(_head_raw, E)
    u = np.array([1.0, 0.0, 0.0]) - n * n[0]
    u /= np.linalg.norm(u)
    v = np.cross(n, u) * side                                # up on both sides
    if v[2] < 0:
        v = -v
    return E, n, u, v


EYES = {s: _eye_frame(s) for s in (1, -1)}


def almond(u, v):
    """2D distance-ish to the eye's almond outline (u forward, v up, in units of the half sizes' scale)"""
    a, b = EYE_HALF
    # the back corner lifts: shear v by u
    v = v + 0.16 * u
    x = np.clip(np.abs(u) / a, 0.0, 1.0)
    top = b * 1.08 * (1.0 - x ** 2.2) ** 0.62                 # a rounder upper lid
    bot = b * 0.86 * (1.0 - x ** 2.0) ** 0.75
    lim = np.where(v >= 0, top, bot)
    return np.maximum(np.abs(u) - a, np.abs(v) - lim)


def _socket(L, side):
    E, n, u, v = EYES[side]
    q = L - E
    du, dv, dn = q @ u, q @ v, q @ n
    a2 = almond(du, dv)
    return np.maximum(a2, np.maximum(dn - 0.4, -dn - EYE_DEPTH))


def eye_ball(side):
    """(centre, radius) of the eyeball: it fills the socket up to just under the head's surface"""
    E, n, u, v = EYES[side]
    R = 0.42
    return E - n * (R + 0.012), R


# ------------------------------------------------------------------ the smile and the nostril (head-local)
def smile_curve(n=40):
    """the mouth line: round the front of the muzzle from the far corner to the near corner, the corners curling up"""
    pts = []
    for i in range(n):
        t = -1 + 2 * i / (n - 1)
        ang = np.radians(t * 72)
        p = np.array([2.72 + 0.41 * np.cos(ang) * 0.92, 0.41 * np.sin(ang) * 0.82, 3.9 + 0.06 * abs(t) ** 2.5])
        pts.append(p)
    return np.array(pts)


SMILE = None


def _smile_dist(L):
    global SMILE
    if SMILE is None:
        raw = smile_curve()
        SMILE = np.array([_ray_hit(_head_raw, np.array([2.45, 0.0, 4.05]), p - np.array([2.45, 0.0, 4.05])) for p in raw])
    d = np.full(len(L), 9.0)
    for i in range(len(SMILE) - 1):
        a, b = SMILE[i], SMILE[i + 1]
        ab = b - a
        t = np.clip(((L - a) @ ab) / (ab @ ab), 0, 1)
        d = np.minimum(d, _len(L - (a + t[:, None] * ab)))
    return d


NOSTRIL = (np.array([3.03, 0.19, 4.2]), (0.06, 0.035, 0.04))


def head_sdf(L):
    d = _head_raw(L)
    for s in (1, -1):
        d = smax(d, -_socket(L, s), 0.045)
    near = _len(L - np.array([2.72, 0.0, 3.95])) < 0.8       # only round the muzzle
    if near.any():
        sd = np.full(len(L), 9.0)
        sd[near] = _smile_dist(L[near])
        d = smax(d, -(sd - 0.022), 0.02)
    c, r = NOSTRIL
    d = smax(d, -ellipsoid(L, c, r), 0.02)
    return d


# ------------------------------------------------------------------ body, neck, legs (world)
LEGS = {
    # name: joints [(point, radius)] from the shoulder or hip down to the top of the hoof
    "ff": [((0.8, -0.34, 2.2), 0.34), ((0.92, -0.4, 1.5), 0.2), ((0.9, -0.42, 0.94), 0.16), ((0.9, -0.42, 0.47), 0.135),
           ((0.92, -0.42, 0.3), 0.15)],
    "nf": [((0.82, 0.34, 2.2), 0.34), ((1.14, 0.4, 1.66), 0.2), ((1.38, 0.43, 1.28), 0.16), ((1.22, 0.43, 0.78), 0.135),
           ((1.12, 0.43, 0.58), 0.15)],
    "fh": [((-0.72, -0.36, 2.3), 0.46), ((-0.56, -0.4, 1.7), 0.28), ((-0.96, -0.42, 1.08), 0.17), ((-0.88, -0.42, 0.47), 0.135),
           ((-0.88, -0.42, 0.3), 0.15)],
    "nh": [((-0.72, 0.36, 2.3), 0.46), ((-0.54, 0.4, 1.68), 0.28), ((-1.04, 0.42, 1.05), 0.17), ((-1.02, 0.42, 0.47), 0.135),
           ((-1.02, 0.42, 0.3), 0.15)],
}


if STAND:                                                    # the raised near foreleg stands like the far one
    LEGS["nf"] = [((x, -y, z), r) for (x, y, z), r in LEGS["ff"]]


def leg_sdf(P, name):
    j = LEGS[name]
    d = None
    for (a, ra), (b, rb) in zip(j[:-1], j[1:]):
        x = round_cone(P, np.array(a), np.array(b), ra, rb)
        d = x if d is None else smin(d, x, 0.08)
    # a little fetlock knob
    f, rf = j[-2]
    d = smin(d, sphere(P, np.array(f), rf * 1.08), 0.05)
    # thigh and shoulder masses, so the legs grow out of the body
    top, rt = j[0]
    big = ellipsoid(P, np.array(top) + np.array([0.04, 0.0, -0.22]), (rt * 1.05, rt * 0.75, rt * 1.45))
    return smin(d, big, 0.2)


def body_sdf(P):
    b = ellipsoid(P, np.array([0.0, 0.0, 2.35]), (1.05, 0.7, 0.66))
    chest = ellipsoid(P, np.array([0.62, 0.0, 2.42]), (0.62, 0.66, 0.7))
    rump = ellipsoid(P, np.array([-0.68, 0.0, 2.45]), (0.66, 0.7, 0.68))
    return smin(smin(b, chest, 0.3), rump, 0.3)


NECK = [((0.6, 0.0, 2.75), 0.6), ((0.96, 0.0, 3.35), 0.55), ((1.2, 0.0, 3.85), 0.52), ((1.34, 0.0, 4.25), 0.5)]


def neck_sdf(P):
    d = None
    for (a, ra), (b, rb) in zip(NECK[:-1], NECK[1:]):
        x = squash(round_cone, P, 0.86, a, b, ra, rb)
        d = x if d is None else smin(d, x, 0.12)
    return d


def parts(P):
    """every part's distance (for colours): body, neck, head, and each leg"""
    out = {"body": body_sdf(P), "neck": neck_sdf(P), "head": head_sdf(world_to_head(P))}
    for n in LEGS:
        out[n] = leg_sdf(P, n)
    return out


def sdf(P):
    p = parts(P)
    d = smin(p["body"], p["neck"], 0.35)
    for n in LEGS:
        d = smin(d, p[n], 0.22)
    d = smin(d, p["head"], 0.3)
    return d


def sdf_uncarved(P):
    """the same with the eyes, smile and nostril not carved (to place things on the face)"""
    L = world_to_head(P)
    p = parts(P)
    d = smin(p["body"], p["neck"], 0.35)
    for n in LEGS:
        d = smin(d, p[n], 0.22)
    return smin(d, _head_raw(L), 0.3)


def grad(fn, P, h=2e-3):
    P = np.asarray(P, np.float64)
    g = np.zeros_like(P)
    for i in range(3):
        e = np.zeros(3)
        e[i] = h
        g[:, i] = (fn(P + e) - fn(P - e)) / (2 * h)
    return g / np.maximum(np.linalg.norm(g, axis=1, keepdims=True), 1e-12)


def project(fn, P, steps=3, off=0.0):
    """pull points onto the surface fn = off"""
    P = np.asarray(P, np.float64).copy()
    for _ in range(steps):
        f = fn(P) - off
        P -= grad(fn, P) * f[:, None]
    return P


# ------------------------------------------------------------------ surface nets
def sample(fn, lo, hi, h, band=4):
    """fn on a grid of spacing h; only points near the surface are worked out exactly (a coarse pass first)"""
    xs = np.arange(lo[0], hi[0] + h, h)
    ys = np.arange(lo[1], hi[1] + h, h)
    zs = np.arange(lo[2], hi[2] + h, h)
    H = h * band
    cx = np.arange(lo[0] - H, hi[0] + 2 * H, H)
    cy = np.arange(lo[1] - H, hi[1] + 2 * H, H)
    cz = np.arange(lo[2] - H, hi[2] + 2 * H, H)
    CX, CY, CZ = np.meshgrid(cx, cy, cz, indexing="ij")
    C = fn(np.stack([CX.ravel(), CY.ravel(), CZ.ravel()], -1)).reshape(CX.shape)
    def trilinear(G, idx):
        i = [np.clip(np.floor(x).astype(np.int64), 0, n - 2) for x, n in zip(idx, G.shape)]
        f = [np.clip(x - ii, 0.0, 1.0) for x, ii in zip(idx, i)]
        out = 0.0
        for dx in (0, 1):
            for dy in (0, 1):
                for dz in (0, 1):
                    w = (f[0] if dx else 1 - f[0]) * (f[1] if dy else 1 - f[1]) * (f[2] if dz else 1 - f[2])
                    out = out + w * G[i[0] + dx, i[1] + dy, i[2] + dz]
        return out
    F = np.empty((len(xs), len(ys), len(zs)), np.float32)
    X, Y = np.meshgrid(xs, ys, indexing="ij")
    for k, z in enumerate(zs):
        P = np.stack([X.ravel(), Y.ravel(), np.full(X.size, z)], -1)
        idx = [(P[:, 0] - cx[0]) / H, (P[:, 1] - cy[0]) / H, (P[:, 2] - cz[0]) / H]
        rough = trilinear(C, idx)
        near = np.abs(rough) < H * 1.9
        out = rough.copy()
        if near.any():
            out[near] = fn(P[near])
        F[:, :, k] = out.reshape(X.shape)
    return F, np.array(lo, np.float64)


def surface_nets(F, origin, h):
    """a mesh of the surface F = 0: (vertices, triangles); triangles face outward (F > 0 outside)"""
    nx, ny, nz = F.shape
    inside = F < 0
    ncell = (nx - 1, ny - 1, nz - 1)
    cid = lambda i, j, k: (i * ncell[1] + j) * ncell[2] + k
    total = ncell[0] * ncell[1] * ncell[2]
    acc = np.zeros((total, 3))
    cnt = np.zeros(total)
    edges = []
    for ax in range(3):
        sl0 = [slice(None)] * 3
        sl1 = [slice(None)] * 3
        sl0[ax] = slice(0, -1)
        sl1[ax] = slice(1, None)
        a = F[tuple(sl0)]
        b = F[tuple(sl1)]
        cross = inside[tuple(sl0)] != inside[tuple(sl1)]
        I = np.nonzero(cross)
        fa = a[I].astype(np.float64)
        fb = b[I].astype(np.float64)
        t = fa / (fa - fb)
        pos = np.stack(I, -1).astype(np.float64)
        pos[:, ax] += t
        lower_in = inside[tuple(sl0)][I]
        edges.append((ax, np.stack(I, -1), lower_in))
        o1, o2 = [x for x in range(3) if x != ax]
        for d1 in (0, 1):
            for d2 in (0, 1):
                c = np.stack(I, -1).copy()
                c[:, o1] -= d1
                c[:, o2] -= d2
                ok = (c[:, o1] >= 0) & (c[:, o2] >= 0) & (c[:, o1] < ncell[o1]) & (c[:, o2] < ncell[o2]) & (c[:, ax] < ncell[ax])
                ids = cid(c[ok, 0], c[ok, 1], c[ok, 2])
                for q in range(3):
                    acc[:, q] += np.bincount(ids, weights=pos[ok, q], minlength=total)
                cnt += np.bincount(ids, minlength=total)
    active = np.nonzero(cnt > 0)[0]
    vmap = -np.ones(total, np.int64)
    vmap[active] = np.arange(len(active))
    V = acc[active] / cnt[active, None] * h + origin
    tris = []
    for ax, I, lower_in in edges:
        b_, c_ = [(1, 2), (2, 0), (0, 1)][ax]                # b x c = ax
        ok = (I[:, b_] >= 1) & (I[:, c_] >= 1) & (I[:, b_] < ncell[b_] + 1) & (I[:, c_] < ncell[c_] + 1) & (I[:, ax] < ncell[ax])
        I = I[ok]
        li = lower_in[ok]
        quad = []
        for db, dc in ((1, 1), (0, 1), (0, 0), (1, 0)):
            c = I.copy()
            c[:, b_] -= db
            c[:, c_] -= dc
            valid = (c[:, b_] < ncell[b_]) & (c[:, c_] < ncell[c_])
            c = np.where(valid[:, None], c, 0)
            quad.append(np.where(valid, vmap[cid(c[:, 0], c[:, 1], c[:, 2])], -1))
        q = np.stack(quad, -1)
        good = np.all(q >= 0, axis=1)
        q = q[good]
        li = li[good]
        q[~li] = q[~li][:, ::-1]                              # outside at the lower end: the other way round
        tris.append(q[:, [0, 1, 2]])
        tris.append(q[:, [0, 2, 3]])
    return V, np.concatenate(tris)
