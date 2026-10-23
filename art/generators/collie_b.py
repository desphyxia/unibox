"""Border collie B, "the storybook collie": a grown tricolour collie (black, white and generous tan) sitting upright, with
a real strand coat: short and fine on the face, a big white ruff and chest, feathered legs, britches and a plume of a
tail. Direction: the two collie pictures the user shared (the storybook meadow collie and the painted portrait), used as
direction only, nothing copied or traced. Built from scratch with its own shape; it shares only generic helpers (the
scene, the mesher and the shape primitives) with the other generators.

Axes (Blender): x forward, y across (+y the near side), z up; ground z = 0.
Run:   blender -b --factory-startup -P collie_b.py -- OUTDIR [--quick] [--skin] [view ...]
       --skin  the bare sculpt, no fur (fast, for the face)
       views: hero head side front"""
import bpy, math, os, sys
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import unicorn2 as Ub
from unicorn2_shape import sphere, ellipsoid, round_cone, squash, smin, smax, rot, sample, surface_nets, project, grad

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "collie_b_out"
QUICK = "--quick" in argv
SKIN = "--skin" in argv
VIEWS = [a for a in argv[1:] if not a.startswith("--")] or ["hero"]
H = 0.02 if QUICK else 0.009
STRANDS = 50000 if QUICK else 330000
hexc, mix, smooth = Ub.hexc, Ub.mix, Ub.smooth

# ------------------------------------------------------------------ the head, built straight, then turned as one
PIVOT = np.array([0.05, 0.0, 3.3])
TURN = rot((0, 0, 1), 18.0) @ rot((0, 1, 0), -6.0) @ rot((1, 0, 0), 6.0)


HS = 1.15                                                       # the head a little big, as a storybook dog's is


DROP = np.array([0.0, 0.0, -0.32])


def to_world(L):
    return PIVOT + DROP + (np.asarray(L) - PIVOT) @ TURN.T * HS


def to_head(P):
    return PIVOT + (P - DROP - PIVOT) @ TURN / HS


def hdir(v):
    return np.asarray(v) @ TURN.T


SKULL = (np.array([0.0, 0.0, 3.62]), np.array([0.5, 0.43, 0.42]))
NOSE = (np.array([0.93, 0.0, 3.42]), np.array([0.072, 0.092, 0.064]))
JAW_HINGE = np.array([0.22, 0.0, 3.32])
JAW_OPEN = rot((0, 1, 0), 7.0)                               # the lower jaw dropped open in a smile


def upper(L):
    d = ellipsoid(L, SKULL[0], SKULL[1])
    d = smin(d, ellipsoid(L, np.array([0.3, 0.0, 3.62]), (0.3, 0.33, 0.27)), 0.15)        # brow and stop
    d = smin(d, ellipsoid(L, np.array([0.2, 0.0, 3.43]), (0.34, 0.41, 0.24)), 0.15)       # cheeks
    d = smin(d, squash(round_cone, L, 0.9, (0.36, 0.0, 3.47), (0.8, 0.0, 3.39), 0.21, 0.14), 0.12)    # muzzle
    d = smin(d, ellipsoid(L, NOSE[0], NOSE[1]), 0.04)
    return d


def lower(L):
    Q = JAW_HINGE + (L - JAW_HINGE) @ JAW_OPEN                  # the jaw, in its closed position
    return squash(round_cone, Q, 0.8, (0.3, 0.0, 3.29), (0.66, 0.0, 3.3), 0.15, 0.075)


def head_raw(L):
    return smin(upper(L), lower(L), 0.05)


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


EYE_R = 0.096
EYE_HALF = (0.112, 0.072)


def eye_frame(side):
    E = ray_hit(upper, np.array([0.1, 0.0, 3.62]), np.array([0.55, 0.42 * side, 0.08]))
    n = grad(upper, E[None])[0]
    u = np.array([1.0, 0.0, 0.0]) - n * n[0]
    u /= np.linalg.norm(u)
    v = np.cross(n, u)
    if v[2] < 0:
        v = -v
    return E, n, u, v


EYES = {s: eye_frame(s) for s in (1, -1)}


def almond(u, v):
    a, b = EYE_HALF
    v = v + 0.15 * u
    x = np.clip(np.abs(u) / a, 0.0, 1.0)
    top = b * (1.0 - x ** 2.2) ** 0.55
    bot = b * 0.85 * (1.0 - x ** 2.0) ** 0.65
    return np.maximum(np.abs(u) - a, np.abs(v) - np.where(v >= 0, top, bot))


def head_sdf(L):
    d = head_raw(L)
    for s in (1, -1):
        E, n, u, v = EYES[s]
        q = L - E
        sock = np.maximum(almond(q @ u, q @ v), np.maximum(q @ n - 0.15, -(q @ n) - 0.1))
        d = smax(d, -sock, 0.015)
    # the mouth: the gap between the jaws, carved in
    Lm = L.copy()
    Lm[:, 2] = Lm[:, 2] - 0.55 * np.clip(0.62 - Lm[:, 0], 0, None) ** 2               # corners turning up
    gap = ellipsoid(Lm, np.array([0.5, 0.0, 3.3]), (0.3, 0.12, 0.034))
    gap = smax(gap, -(L[:, 0] - 0.22), 0.02)
    d = smax(d, -gap, 0.02)
    for s in (1, -1):                                           # nostrils
        d = smax(d, -ellipsoid(L, NOSE[0] + np.array([0.07, 0.04 * s, -0.005]), (0.022, 0.016, 0.014)), 0.01)
    return d


# ------------------------------------------------------------------ the body (world)
def body_sdf(P):
    chest = ellipsoid(P, np.array([0.14, 0.0, 1.8]), (0.58, 0.6, 0.72))
    rump = ellipsoid(P, np.array([-0.48, 0.0, 0.95]), (0.64, 0.6, 0.64))
    d = smin(chest, rump, 0.35)
    d = smin(d, squash(round_cone, P, 0.85, (-0.4, 0.0, 1.05), (0.1, 0.0, 1.9), 0.5, 0.44), 0.25)
    d = smin(d, round_cone(P, np.array([0.12, 0.0, 2.25]), np.array([0.05, 0.0, 2.95]), 0.4, 0.33), 0.2)   # neck
    for s in (1, -1):
        d = smin(d, round_cone(P, np.array([0.32, 0.25 * s, 1.4]), np.array([0.36, 0.25 * s, 0.55]), 0.2, 0.145), 0.12)
        d = smin(d, round_cone(P, np.array([0.36, 0.25 * s, 0.55]), np.array([0.39, 0.25 * s, 0.14]), 0.145, 0.12), 0.05)
        d = smin(d, ellipsoid(P, np.array([0.5, 0.25 * s, 0.08]), (0.19, 0.13, 0.08)), 0.05)        # front paws
        d = smin(d, ellipsoid(P, np.array([-0.45, 0.38 * s, 0.72]), (0.55, 0.24, 0.45)), 0.2)         # thighs
        d = smin(d, round_cone(P, np.array([-0.78, 0.38 * s, 0.3]), np.array([-0.05, 0.4 * s, 0.1]), 0.11, 0.08), 0.1)
        d = smin(d, ellipsoid(P, np.array([0.06, 0.4 * s, 0.065]), (0.15, 0.09, 0.065)), 0.05)       # hind paws
    return d


TAIL = np.array([(-1.0, 0.0, 0.6), (-1.32, 0.05, 0.28), (-1.5, 0.3, 0.1), (-1.45, 0.65, 0.07), (-1.15, 0.9, 0.12), (-0.85, 0.98, 0.3)])


def tail_curve(m=40):
    t = np.linspace(0, 1, len(TAIL))
    s = np.linspace(0, 1, m)
    c = np.stack([np.interp(s, t, TAIL[:, k]) for k in range(3)], 1)
    for _ in range(6):
        c[1:-1] = (c[:-2] + 2 * c[1:-1] + c[2:]) / 4
    return c


def tail_sdf(P):
    c = tail_curve()
    d = np.full(len(P), 9.0)
    for i in range(len(c) - 1):
        r1 = 0.1 * (1 - i / len(c)) + 0.035
        r2 = 0.1 * (1 - (i + 1) / len(c)) + 0.035
        d = smin(d, round_cone(P, c[i], c[i + 1], r1, r2), 0.03)
    return d


# ------------------------------------------------------------------ ears: semi-pricked, the top third folding forward
def ear_frame(side):
    base = ray_hit(upper, SKULL[0], np.array([-0.3, 0.55 * side, 0.78]))
    up = np.array([-0.12, 0.3 * side, 1.0])
    up /= np.linalg.norm(up)
    fwd = np.array([1.0, 0.3 * side, 0.0])
    fwd -= up * (fwd @ up)
    fwd /= np.linalg.norm(fwd)
    return base, up, fwd, np.cross(up, fwd)


EARS = {s: ear_frame(s) for s in (1, -1)}
EAR_H, EAR_W, FOLD = 0.52, 0.25, 0.58


def frame_ellipsoid(P, c, axes, radii):
    return ellipsoid((P - c) @ np.array(axes).T, np.zeros(3), radii)


def flat_cone(L, frame, a, b, ra, rb, thick=0.28):
    """a round cone in an ear's frame, flattened through its thickness: a soft triangle"""
    acr, up, fwd = frame
    q = np.stack([(L @ acr), (L @ up), (L @ fwd) / thick], 1)
    A = np.array([a @ acr, a @ up, (a @ fwd) / thick])
    Bp = np.array([b @ acr, b @ up, (b @ fwd) / thick])
    return round_cone(q, A, Bp, ra, rb) * thick


def ear_geo(side):
    base, up, fwd, acr = EARS[side]
    f = EAR_H * FOLD
    hinge = base + up * f
    ang = np.radians(128.0)
    td = up * np.cos(ang) + (fwd * 0.9 + acr * 0.42) * np.sin(ang)
    td /= np.linalg.norm(td)
    tn = np.cross(acr, td)
    tn /= np.linalg.norm(tn)
    tip = hinge + td * (EAR_H - f)
    return base, up, fwd, acr, hinge, td, tn, tip


def ear_sdf(L, side):
    base, up, fwd, acr, hinge, td, tn, tip = ear_geo(side)
    lo = flat_cone(L, (acr, up, fwd), base - up * 0.06, hinge, EAR_W, EAR_W * 0.46, 0.22)
    hi = flat_cone(L, (acr, td, tn), hinge + td * 0.01, tip, EAR_W * 0.44, 0.03, 0.3)
    d = smin(lo, hi, 0.05)
    cup = flat_cone(L, (acr, up, fwd), base + up * 0.04 + fwd * 0.035, hinge - up * 0.02 + fwd * 0.02, EAR_W * 0.7, EAR_W * 0.3, 0.2)
    return smax(d, -cup, 0.012)


def sdf(P):
    L = to_head(P)
    d = head_sdf(L)
    for s in (1, -1):
        d = smin(d, ear_sdf(L, s), 0.04)
    d = d * HS
    return smin(d, smin(body_sdf(P), tail_sdf(P), 0.06), 0.15)


def sdf_raw(P):
    L = to_head(P)
    d = head_raw(L)
    for s in (1, -1):
        d = smin(d, ear_sdf(L, s), 0.04)
    d = d * HS
    return smin(d, smin(body_sdf(P), tail_sdf(P), 0.06), 0.15)


# ------------------------------------------------------------------ the coat's colours
BLACK = hexc("#141113")
BLACK2 = hexc("#2c2624")
WHITE = hexc("#fbf9f5")
TAN = hexc("#83461f")
TAN_LIGHT = hexc("#b9763f")


def where(P):
    """which part each point belongs to: head (with ears), body, tail"""
    L = to_head(P)
    h = head_raw(L)
    for s in (1, -1):
        h = smin(h, ear_sdf(L, s), 0.04)
    h = h * HS
    b, t = body_sdf(P), tail_sdf(P)
    return h, b, t, L


def coat(P, N):
    h, b, t, L = where(P)
    head = smooth(0.04, -0.04, h - np.minimum(b, t))
    tail = smooth(0.04, -0.04, t - b) * (1 - head)
    body = 1 - head - tail
    n = len(P)
    c = mix(np.tile(BLACK, (n, 1)), BLACK2, smooth(0.0, 0.8, N[:, 2]) * 0.5)
    x, y, z = L[:, 0], L[:, 1], L[:, 2]
    # tan points on the face: eyebrow spots, the cheeks between the eyes and the white muzzle
    for s in (1, -1):
        E, nn, u, v = EYES[s]
        d = np.linalg.norm((L - (E + v * 0.11 - u * 0.01 + nn * 0.01)) / np.array([0.075, 0.07, 0.05]), axis=1)
        c = mix(c, TAN, smooth(1.0, 0.6, d) * head)
        q = L - np.array([0.36, 0.28 * s, 3.38])
        q = np.stack([q[:, 0] * 0.94 + q[:, 2] * 0.34, q[:, 1], q[:, 2] * 0.94 - q[:, 0] * 0.34], 1)
        d = np.linalg.norm(q / np.array([0.3, 0.16, 0.12]), axis=1)
        c = mix(c, mix(TAN, TAN_LIGHT, 0.25), smooth(1.0, 0.45, d) * head)
    # white: a narrow blaze between the eyes widening down the muzzle; the muzzle and chin
    bw = 0.04 + 0.03 * smooth(0.2, -0.1, x) + 0.12 * smooth(0.5, 0.72, x)
    blaze = smooth(bw + 0.02, bw - 0.01, np.abs(y)) * smooth(3.4, 3.5, z)
    muz = smooth(0.55, 0.66, x) * smooth(0.2 + 0.08 * smooth(0.65, 0.9, x), 0.14, np.abs(y)) * smooth(3.52, 3.44, z)
    chin = smooth(3.31, 3.25, z) * smooth(0.2, 0.4, x)
    w = np.maximum(np.maximum(blaze, muz), chin) * head
    # white ruff and chest, front legs, paws, tail tip; tan on the legs above the white
    front = smooth(-0.1, 0.25, N[:, 0] + 0.15) * smooth(0.9, 1.15, P[:, 2]) * smooth(2.95, 2.7, P[:, 2])
    collar = smooth(2.42, 2.52, P[:, 2]) * smooth(2.85, 2.75, P[:, 2]) * smooth(-0.6, 0.0, N[:, 0] + 0.3)
    legs = smooth(0.95, 0.8, P[:, 2]) * smooth(0.15, 0.28, P[:, 0]) * smooth(0.4, 0.32, np.abs(P[:, 1]))
    paws = smooth(0.24, 0.16, P[:, 2])
    w = np.maximum(w, body * np.maximum(np.maximum(front, collar * 0.9), np.maximum(legs, paws)))
    tc = tail_curve(60)
    dt = np.linalg.norm(P[:, None, :] - tc[None, -16:, :], axis=2).min(1)
    w = np.maximum(w, tail * smooth(0.25, 0.15, dt))
    c = mix(c, TAN, body * smooth(1.25, 1.0, P[:, 2]) * smooth(0.8, 0.95, P[:, 2]) * smooth(0.12, 0.25, P[:, 0])
            * smooth(0.36, 0.28, np.abs(P[:, 1])))
    c = mix(c, TAN, body * smooth(0.55, 0.4, P[:, 2]) * smooth(0.25, 0.32, P[:, 2]) * smooth(-0.3, -0.55, P[:, 0]))
    c = mix(c, WHITE, w)
    # leather: the nose, the lips, inside the mouth
    nd = np.linalg.norm((L - NOSE[0]) / NOSE[1], axis=1)
    c = mix(c, hexc("#151215"), smooth(1.3, 0.95, nd) * head)
    zl = 3.3 + 0.55 * np.clip(0.62 - x, 0, None) ** 2
    lips = smooth(0.05, 0.02, np.abs(z - zl)) * smooth(0.2, 0.28, x) * smooth(0.17, 0.1, np.abs(y))
    c = mix(c, hexc("#1a1316"), lips * head)
    return c, head, tail


# ------------------------------------------------------------------ eyes, nose, tongue, teeth
def surface(L, off=0.0):
    P = project(head_raw, np.atleast_2d(L), 4)
    return P + grad(head_raw, P) * off


def build_face():
    for side in (1, -1):
        E, n, u, v = EYES[side]
        c = E - n * (EYE_R * 0.86)
        look = n + u * 0.55
        look /= np.linalg.norm(look)
        up = v - look * (v @ look)
        up /= np.linalg.norm(up)
        Vs, Fs = Ub.uv_sphere(np.zeros(3), EYE_R, 64, 40)
        d = Vs / EYE_R
        ca, h = d @ look, d @ up
        iris = smooth(np.cos(np.radians(70)), np.cos(np.radians(66)), ca)
        pupil = smooth(np.cos(np.radians(30)), np.cos(np.radians(27)), ca)
        ic = mix(hexc("#a8642a"), hexc("#3a1a08"), smooth(-0.6, 0.5, h))
        ic = mix(ic, hexc("#1c0c04"), smooth(np.cos(np.radians(50)), np.cos(np.radians(60)), ca) * iris * 0.8)
        ic = mix(ic, hexc("#060404"), pupil)
        col = mix(hexc("#1a1210"), ic, iris)
        Ub.add_mesh("eye", to_world(c + Vs), Fs, col, Ub.material("eye", rough=0.16, spec=0.6, coat=0.5))
        for du, dv, rr in ((0.35, 0.45, 0.022), (-0.3, -0.35, 0.009)):
            a = np.cross(look, up)
            dirn = look + a * du * 0.6 + up * dv * 0.6
            dirn /= np.linalg.norm(dirn)
            gc = c + dirn * (EYE_R + 0.002)
            ga = np.cross(dirn, up); ga /= np.linalg.norm(ga)
            gb = np.cross(ga, dirn)
            Vg = [gc] + [gc + (ga * np.cos(t) + gb * np.sin(t) * 0.8) * rr for t in np.linspace(0, 2 * np.pi, 16, endpoint=False)]
            Ub.add_mesh("glint", to_world(np.array(Vg)), [(0, k + 1, (k + 1) % 16 + 1) for k in range(16)], None,
                        Ub.material("glint", emit=5.0, color=(1, 1, 1, 1)))
        # the dark rim of the lids round the whole almond
        a, b = EYE_HALF
        pts = []
        for t in np.linspace(0, 2 * np.pi, 56, endpoint=False):
            uu = a * 1.03 * np.cos(t)
            x = min(abs(uu) / a, 1.0)
            lim = b * (1.0 - x ** 2.2) ** 0.55 if np.sin(t) >= 0 else -b * 0.85 * (1.0 - x ** 2.0) ** 0.65
            pts.append(E + u * uu + v * (lim * 1.04 - 0.15 * uu))
        pts = surface(np.array(pts + pts[:1]), 0.004)
        Vt, Ft = Ub.tube(pts, np.full(len(pts), 0.008), 6)
        Ub.add_mesh("lidrim", to_world(Vt), Ft, None, Ub.material("lidrim", rough=0.4, spec=0.4, color=hexc("#0e0a0a")))
    # nose leather
    c, r = NOSE
    Vn, Fn = Ub.uv_sphere(np.zeros(3), 1.0, 48, 28)
    sh = Vn.copy()
    sh[:, 1] *= 1.0 - 0.25 * np.clip(-Vn[:, 2], 0, 1)
    Vn = sh * np.array(r) * 1.05 + c
    cn = np.tile(hexc("#1a1618"), (len(Vn), 1))
    for s in (1, -1):
        dd = np.linalg.norm((Vn - (c + np.array([0.075, 0.042 * s, -0.008]))) / np.array([0.025, 0.02, 0.018]), axis=1)
        cn = mix(cn, hexc("#030203"), smooth(1.4, 0.8, dd))
    cn = mix(cn, hexc("#4a4046"), smooth(0.03, 0.08, Vn[:, 2] - c[2]) * 0.5)
    Ub.add_mesh("nose", to_world(Vn), Fn, cn, Ub.material("nose", rough=0.42, spec=0.5, coat=0.2))
    # the tongue on the lower jaw, its tip just past the front teeth
    Vt, Ft = Ub.uv_sphere(np.zeros(3), 1.0, 32, 16)
    q = Vt * np.array([0.2, 0.09, 0.03])
    q[:, 2] *= 1.0 - 0.4 * np.exp(-(q[:, 1] / 0.03) ** 2)
    tq = q + np.array([0.5, 0.0, 3.295])
    tq = JAW_HINGE + (tq - JAW_HINGE) @ JAW_OPEN.T
    ct = mix(np.tile(hexc("#e8899c"), (len(q), 1)), hexc("#c05e76"), smooth(0.05, -0.15, q[:, 0]))
    Ub.add_mesh("tongue", to_world(tq), Ft, ct, Ub.material("tongue", rough=0.4, sss=0.3, spec=0.4, coat=0.15))
    # teeth: small canines, upper and lower
    for s in (1, -1):
        for base, dz in ((np.array([0.7, 0.07 * s, 3.322]), -0.026), (np.array([0.62, 0.062 * s, 3.3]), 0.022)):
            if dz > 0:
                base = JAW_HINGE + (base - JAW_HINGE) @ JAW_OPEN.T
            pts = np.array([base, base + np.array([0.0, 0.0, dz * 0.5]), base + np.array([0.004, 0.0, dz])])
            Vt, Ft = Ub.tube(pts, np.array([0.012, 0.009, 0.002]), 8)
            Ub.add_mesh("tooth", to_world(Vt), Ft, None, Ub.material("tooth", rough=0.3, spec=0.5, color=hexc("#fbf6ec")))


# ------------------------------------------------------------------ fur
def coat_layout(R, N, rng):
    """per root: length, lift and combing direction for each part of the coat"""
    h, b, t, L = where(R)
    head = h < np.minimum(b, t)
    tail = (t < b) & ~head
    x, y, z = L[:, 0], L[:, 1], L[:, 2]
    n = len(R)
    ln = np.full(n, 0.17)
    lift = np.full(n, 0.2)
    comb = np.tile(np.array([-0.6, 0.0, -1.0]), (n, 1))
    # the face: very short on the muzzle and round the eyes, longer over the skull and at the cheeks' edge
    hl = 0.022 + 0.03 * smooth(0.45, 0.1, x) + 0.06 * smooth(0.2, -0.25, x)
    hl += 0.07 * smooth(0.33, 0.43, np.abs(y)) * smooth(3.5, 3.3, z) * smooth(0.45, 0.2, x)            # cheek fluff
    ln = np.where(head, hl, ln)
    lift = np.where(head, 0.18, lift)
    comb = np.where(head[:, None], hdir(np.array([-1.0, 0.0, -0.2]))[None], comb)
    for sd in (1, -1):                                   # the ears: short and sleek, combed toward the tips
        e = head & (ear_sdf(L, sd) < head_raw(L) - 0.005) & (z > 3.7)
        bs, up_, fw, ac, hinge, td_, tn, tip = ear_geo(sd)
        dl = np.where(((L - bs) @ up_ > EAR_H * FOLD)[:, None], td_[None], up_[None])
        dw = hdir(dl)
        ln = np.where(e, 0.045, ln)
        lift = np.where(e, 0.08, lift)
        comb = np.where(e[:, None], dw, comb)
    # ruff and chest: long, standing out, falling down the front; longest at the chest
    ruff = ~head & ~tail & (R[:, 2] > 1.2) & (R[:, 2] < 3.0) & (N[:, 0] > -0.5)
    ln = np.where(ruff, 0.3 + 0.12 * smooth(-0.3, 0.6, N[:, 0]), ln)
    lift = np.where(ruff, 0.55, lift)
    comb = np.where(ruff[:, None], np.array([0.15, 0.0, -1.0])[None], comb)
    # the back of the neck: a thick mane combed back
    mane = ~head & ~tail & (R[:, 2] > 2.1) & (N[:, 0] <= -0.5)
    ln = np.where(mane, 0.25, ln)
    # legs: short on the fronts, feathered behind; britches at the back of the thighs
    fl = ~head & ~tail & (R[:, 2] < 1.6) & (R[:, 0] > 0.2) & (np.abs(R[:, 1]) < 0.32)
    ln = np.where(fl, 0.04 + 0.16 * smooth(0.0, -0.7, N[:, 0]) * smooth(0.3, 0.6, R[:, 2]), ln)
    lift = np.where(fl, 0.12, lift)
    comb = np.where(fl[:, None], np.array([-0.1, 0.0, -1.0])[None], comb)
    brit = ~head & ~tail & (R[:, 0] < -0.5) & (R[:, 2] < 1.2) & (R[:, 2] > 0.2)
    ln = np.where(brit, 0.26, ln)
    ln = np.where(~head & (R[:, 2] < 0.2), 0.02, ln)
    # the tail: a long plume, combed toward its tip
    ln = np.where(tail, 0.3, ln)
    lift = np.where(tail, 0.35, lift)
    tc = tail_curve(80)
    T_ = np.gradient(tc, axis=0)
    k = np.argmin(np.linalg.norm(R[:, None, :] - tc[None], axis=2), 1)
    td = T_[k] / np.linalg.norm(T_[k], axis=1, keepdims=True)
    comb = np.where(tail[:, None], td, comb)
    ln = np.where(tail, 0.12 + 0.3 * np.sin(np.pi * np.clip(k / 80 * 1.1, 0, 1)), ln)
    ln = ln * rng.uniform(0.82, 1.15, n)
    comb = comb - N * np.sum(comb * N, 1, keepdims=True)
    comb /= np.maximum(np.linalg.norm(comb, axis=1, keepdims=True), 1e-9)
    return ln, lift, comb


def fur_roots(V, T, rng, count):
    A = np.linalg.norm(np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]]), axis=1) / 2
    tri = rng.choice(len(T), count, p=A / A.sum())
    r1, r2 = rng.random(count), rng.random(count)
    s1 = np.sqrt(r1)
    R = V[T[tri, 0]] * (1 - s1)[:, None] + V[T[tri, 1]] * (s1 * (1 - r2))[:, None] + V[T[tri, 2]] * (s1 * r2)[:, None]
    L = to_head(R)
    keep = np.linalg.norm((L - NOSE[0]) / NOSE[1], axis=1) > 1.3                  # no fur on the nose
    for s in (1, -1):                                                              # nor on the eyes
        E, n, u, v = EYES[s]
        q = L - E
        keep &= almond(q @ u, q @ v) > 0.018
    keep &= ~((np.abs(L[:, 2] - 3.27) < 0.045) & (L[:, 0] > 0.3) & (np.abs(L[:, 1]) < 0.14))     # nor in the mouth
    keep &= R[:, 2] > 0.02
    # none on the ears' insides (their own fur is added along the edges)
    for s in (1, -1):                                       # the ears get their own fur
        base, up, fwd, acr = EARS[s]
        q = L - base
        inner = (ear_sdf(L, s) < head_raw(L) - 0.005) & (q @ fwd > 0.0) & (q @ up < EAR_H * FOLD * 0.95) & (L[:, 2] > 3.7)
        keep &= ~inner
    return R[keep]


def grow(R, N, comb, ln, lift, col, rng, K=7, radius=0.0032):
    n = len(R)
    s = np.linspace(0, 1, K)
    up = 1 - (1 - s) ** 2
    B = np.cross(N, comb)
    ph = rng.uniform(0, 6.28, n)
    P = (R[:, None] + N[:, None] * (ln * lift)[:, None, None] * up[None, :, None]
         + comb[:, None] * ln[:, None, None] * s[None, :, None]
         - np.array([0, 0, 1.0])[None, None] * (ln * 0.15)[:, None, None] * (s ** 2)[None, :, None]
         + B[:, None] * (ln * 0.07)[:, None, None] * np.sin(s[None] * 3.2 + ph[:, None])[:, :, None])
    nc = max(1, n // 18)
    ci = rng.choice(n, nc, replace=False)
    kd = KDTree(nc)
    for k, i in enumerate(ci):
        kd.insert(R[i], k)
    kd.balance()
    near = np.array([ci[kd.find(r)[1]] for r in R])
    close = (np.linalg.norm(R - R[near], axis=1) < 0.08)[:, None, None]
    P += (P[near] - P) * (0.55 * s ** 1.7)[None, :, None] * close
    rad = np.tile(radius * (1 - s) + 0.0005, (n, 1))
    C_ = col[:, None] * (0.93 + 0.07 * s)[None, :, None]
    return P.astype(np.float32), rad.astype(np.float32), C_.astype(np.float32)


def hair_material():
    m = bpy.data.materials.new("fur")
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    hb = nt.nodes.new("ShaderNodeBsdfHairPrincipled")
    hb.parametrization = "COLOR"
    at = nt.nodes.new("ShaderNodeAttribute")
    at.attribute_name = "fcol"
    nt.links.new(at.outputs["Color"], hb.inputs["Color"])
    hb.inputs["Roughness"].default_value = 0.42
    hb.inputs["Radial Roughness"].default_value = 0.6
    hb.inputs["Coat"].default_value = 0.0
    hb.inputs["IOR"].default_value = 1.45
    nt.links.new(hb.outputs[0], out.inputs["Surface"])
    return m


def make_hair(name, P, rad, col):
    n, K = P.shape[0], P.shape[1]
    cv = bpy.data.hair_curves.new(name)
    cv.add_curves([K] * n)
    cv.position_data.foreach_set("vector", P.reshape(-1))
    ra = cv.attributes.get("radius") or cv.attributes.new("radius", "FLOAT", "POINT")
    ra.data.foreach_set("value", rad.reshape(-1))
    ca = cv.attributes.new("fcol", "FLOAT_COLOR", "POINT")
    ca.data.foreach_set("color", np.concatenate([col, np.ones((n, K, 1), np.float32)], 2).reshape(-1))
    ob = bpy.data.objects.new(name, cv)
    bpy.context.collection.objects.link(ob)
    cv.materials.append(hair_material())
    return n


def ear_fur(rng):
    """a fringe of hair on the ears' edges, short hair on their backs, tan wisps inside"""
    R, D, Ln, C = [], [], [], []
    for side in (1, -1):
        base, up, fwd, acr, hinge, td, tn, tip = ear_geo(side)
        for _ in range(6000 if not QUICK else 2500):
            k = rng.random()
            vv = rng.uniform(-1, 1)
            if k < FOLD:
                t = k / FOLD
                c = base + (hinge - base) * t
                hw = EAR_W * (1 - 0.48 * t)
                p = c + acr * vv * hw
                axis, nrm = up, fwd
            else:
                t = (k - FOLD) / (1 - FOLD)
                c = hinge + (tip - hinge) * t
                p = c + acr * vv * EAR_W * 0.52 * (1 - t)
                axis, nrm = td, tn
            edge = abs(vv) > 0.8
            if edge:
                R.append(p); D.append(acr * np.sign(vv) * 0.7 + axis * 0.6); Ln.append(rng.uniform(0.035, 0.07)); C.append(BLACK[:3])
            if k < FOLD * 0.85 and abs(vv) < 0.55 and rng.random() < 0.5:
                R.append(p + nrm * 0.015); D.append(nrm * 0.6 + axis * 0.7 + acr * vv * 0.3); Ln.append(rng.uniform(0.04, 0.075))
                C.append(mix(TAN, WHITE, 0.3)[:3])
    R = to_world(np.array(R))
    D = np.array([hdir(d) for d in D])
    D /= np.linalg.norm(D, axis=1, keepdims=True)
    return R, D, np.array(Ln), np.array(C)


# ------------------------------------------------------------------ scene
VIEWS_AT = {"hero": (34.0, 6.0, (0.1, 0.0, 2.15), 4.6), "head": (36.0, 5.0, (0.35, 0.0, 3.4), 2.2),
            "front": (85.0, 4.0, (0.3, 0.0, 3.4), 2.2), "side": (0.0, 3.0, (-0.2, 0.0, 1.85), 4.3)}


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
        ob.rotation_euler = (Vector((0.2, 0, 2.2)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    area("key", (5, 6.5, 8), 6, 1100, (1.0, 0.95, 0.86))
    area("fill", (6, -4, 3), 8, 380, (0.9, 0.95, 1.0))
    area("rim", (-5, -2, 6.5), 4, 650, (1.0, 0.94, 0.85))
    area("bounce", (2, 3, -2), 6, 140, (0.95, 1.0, 0.9))


def main():
    os.makedirs(OUT, exist_ok=True)
    sc = Ub.setup()
    sc.view_settings.exposure = -0.4
    sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
    sc.cycles.max_bounces = 32                                  # white hair needs many bounces, or it greys
    sc.cycles.transmission_bounces = 32
    sc.cycles.glossy_bounces = 16
    sc.cycles.diffuse_bounces = 4
    rng = np.random.default_rng(8)
    F, o = sample(sdf, (-1.75, -1.2, 0.0), (1.4, 1.2, 4.9), H)
    V, T = surface_nets(F, o, H)
    V = project(sdf, V, 2)
    N = grad(sdf, V)
    col, _, _ = coat(V, N)
    Ub.add_mesh("skin", V, T, col, Ub.material("skin", rough=0.85, sss=0.1, sheen=0.5, spec=0.12), N)
    build_face()
    if not SKIN:
        R = fur_roots(V, T, rng, STRANDS)
        Nr = grad(sdf_raw, R)
        ln, lift, comb = coat_layout(R, Nr, rng)
        cr, _, _ = coat(R, Nr)
        P, rad, cc = grow(R, Nr, comb, ln, lift, cr[:, :3], rng)
        total = make_hair("fur", P, rad, cc)
        Re, De, Le, Ce = ear_fur(rng)
        P2, r2, c2 = grow(Re, De, De, Le, np.full(len(Re), 0.0), Ce, rng, radius=0.0026)
        total += make_hair("earfur", P2, r2, c2)
        print("fur strands", total)
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
