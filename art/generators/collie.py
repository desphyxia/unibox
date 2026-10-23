"""A border collie, the third land creature: one 3D model in three coat variants, rendered in Blender (headless, Cycles)
with real strand fur. Direction: two pictures the user shared (a storybook border collie sitting in a meadow and a
painted tricolour portrait); used as direction only, nothing copied or traced.

  A  classic tricolour: black, white and tan, a navy collar with a silver tag
  B  red tricolour: chocolate brown, copper tan and white
  C  blue merle tricolour: marbled blue-grey with black patches, tan points, white; one blue eye and one brown

Shared: a white blaze, muzzle, ruff and chest, white paws and a white tail tip; tan eyebrow dots, cheeks and leg trim;
semi-pricked ears with folding tips; a long feathered coat (big ruff, feathered legs, britches, a plumed tail); warm
eyes; an open-mouthed smile with a tongue. The body is one signed distance field (collie_shape.py); the fur is about
a quarter of a million clumped hair strands grown from it, each coloured by the coat underneath.
Run:   blender -b --factory-startup -P collie.py -- OUTDIR [--quick] [--clay] [--variant A|B|C|all] [view ...]
       views: hero head side lineup"""
import bpy, math, os, sys
import numpy as np
from mathutils import Vector
from mathutils.kdtree import KDTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import unicorn2 as Ub                                          # shared helpers: scene, materials, meshes, tubes
import collie_shape as C

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "collie_out"
QUICK = "--quick" in argv
CLAY = "--clay" in argv
VARIANTS = ["A", "B", "C"] if "--variant" not in argv or argv[argv.index("--variant") + 1] == "all" else [argv[argv.index("--variant") + 1]]
VIEWS = [a for a in argv[1:] if not a.startswith("--") and a not in ("A", "B", "C", "all")] or ["hero"]
H = 0.024 if QUICK else 0.011
FUR_COUNT = 30000 if QUICK else 240000
hexc, mix, smooth = Ub.hexc, Ub.mix, Ub.smooth

PALETTES = {
    "A": {"dark": "#15120f", "dark2": "#2a2522", "white": "#f7f3ec", "tan": "#b8692f", "eye": ("#7a3d16", "#c07a35"), "eye2": None,
          "blaze": 0.055, "collar": True},
    "B": {"dark": "#4a2618", "dark2": "#6a3a24", "white": "#f6f0e8", "tan": "#d08a4a", "eye": ("#8a5a1c", "#d5a050"), "eye2": None,
          "blaze": 0.085, "collar": False},
    "C": {"dark": "#8a94a6", "dark2": "#1b1b22", "white": "#f7f5f2", "tan": "#c17a3c", "eye": ("#6a3a16", "#b8732f"),
          "eye2": ("#3d79b8", "#a8d4f2"), "blaze": 0.12, "collar": False, "merle": True},
}


# ------------------------------------------------------------------ value noise (for merle patches and fur variety)
def vnoise(P, scale, seed=0):
    rng = np.random.default_rng(seed)
    perm = rng.random(4096)
    Q = P * scale
    i = np.floor(Q).astype(np.int64)
    f = Q - i
    f = f * f * (3 - 2 * f)

    def h(a, b, c):
        return perm[(a * 73856093 ^ b * 19349663 ^ c * 83492791) % 4096]
    out = 0.0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (f[:, 0] if dx else 1 - f[:, 0]) * (f[:, 1] if dy else 1 - f[:, 1]) * (f[:, 2] if dz else 1 - f[:, 2])
                out = out + w * h(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz)
    return out


# ------------------------------------------------------------------ the coat's colours
def coat(V, N, pal):
    """the coat colour at points V (world) with normals N, for one palette"""
    dark, white, tan = hexc(pal["dark"]), hexc(pal["white"]), hexc(pal["tan"])
    n = len(V)
    p = C.parts(V)
    names = list(p)
    which = np.array(names)[np.argmin(np.stack([p[k] for k in names], 1), 1)]
    L = C.world_to_head(V)
    head = (which == "head").astype(float)
    c = np.tile(dark, (n, 1))
    if pal.get("merle"):
        m = vnoise(V, 2.4, 3)
        fine = vnoise(V, 7.0, 4)
        patch = smooth(0.62, 0.7, m)
        c = mix(c, hexc(pal["dark2"]), np.maximum(patch, smooth(0.78, 0.86, fine) * 0.7))
        c = mix(c, hexc("#c3c9d4"), smooth(0.25, 0.12, m) * 0.5)
    else:
        c = mix(c, hexc(pal["dark2"]), vnoise(V, 5.0, 2) * 0.35)
    # tan points: eyebrow dots, cheeks, the inner ear base, the backs of the legs, under the tail
    for s in (1, -1):
        E, nn, u, v = C.EYES[s]
        d = np.linalg.norm(L - (E + v * 0.21 + u * 0.01 + nn * 0.02), axis=1)
        c = mix(c, tan, smooth(0.085, 0.055, d) * head)
        d = np.linalg.norm((L - np.array([0.86, 0.38 * s, 3.08])) / np.array([0.26, 0.2, 0.2]), axis=1)
        c = mix(c, tan, smooth(1.0, 0.6, d) * head)
    z = V[:, 2]
    legs = np.isin(which, ["nf", "ff", "nh", "fh"]).astype(float)
    c = mix(c, tan, legs * smooth(1.45, 1.2, z) * smooth(0.5, 0.75, z) * smooth(0.1, -0.5, N[:, 0]))
    c = mix(c, tan, (which == "body") * smooth(0.5, 0.25, z) * smooth(-0.9, -1.2, V[:, 0]) * 0.8)
    # white: the blaze, the muzzle and chin, the ruff and chest, the front legs and all four paws
    w = np.zeros(n)
    bw = pal["blaze"] + 0.05 * smooth(0.75, 0.45, L[:, 0]) + 0.14 * smooth(1.45, 1.62, L[:, 0])
    w = np.maximum(w, head * smooth(bw + 0.02, bw - 0.01, np.abs(L[:, 1])) * smooth(3.0, 3.15, L[:, 2]))
    side_ok = smooth(0.16 + 0.25 * smooth(1.5, 1.7, L[:, 0]), 0.08 + 0.25 * smooth(1.5, 1.7, L[:, 0]), np.abs(L[:, 1]))
    w = np.maximum(w, head * smooth(1.42, 1.54, L[:, 0]) * smooth(3.3, 3.2, L[:, 2]) * side_ok)
    w = np.maximum(w, head * smooth(3.06, 2.98, L[:, 2]) * smooth(0.75, 0.9, L[:, 0]))
    ruff = (np.isin(which, ["neck", "body"]) * smooth(-0.1, 0.35, N[:, 0]) * smooth(0.95, 1.2, z) * smooth(2.95, 2.6, z)
            * smooth(-0.05, 0.2, V[:, 0]))
    collar = (which == "neck") * smooth(2.15, 2.3, z) * smooth(2.65, 2.5, z) * smooth(-0.8, -0.2, N[:, 0])
    w = np.maximum(w, ruff)
    w = np.maximum(w, collar * 0.9)
    w = np.maximum(w, legs * smooth(1.25, 1.05, z) * np.isin(which, ["nf", "ff"]) * smooth(-0.35, 0.05, N[:, 0]))
    w = np.maximum(w, legs * smooth(0.36, 0.22, z))
    c = mix(c, white, w)
    # the nose is black; the open mouth is dark inside, the lips black
    nose_d = np.linalg.norm((L - C.NOSE[0]) / C.NOSE[1], axis=1)
    c = mix(c, hexc("#141214"), smooth(1.35, 1.0, nose_d) * head)
    m_d = np.linalg.norm((L - C.MOUTH[0]) / (np.array(C.MOUTH[1]) * np.array([1.0, 1.0, 1.6])), axis=1)
    c = mix(c, hexc("#1a1214"), smooth(1.5, 1.15, m_d) * head)
    c = mix(c, hexc("#5a2430"), smooth(1.1, 0.9, m_d) * head)
    return c


# ------------------------------------------------------------------ the body
def build_body(pal):
    F, o = C.sample(C.sdf, (-1.6, -0.95, 0.0), (2.0, 0.95, 4.0), H)
    V, T = C.surface_nets(F, o, H)
    V = C.project(C.sdf, V, 2)
    N = C.grad(C.sdf, V)
    col = coat(V, N, pal)
    ob = Ub.add_mesh("body", V, T, col, Ub.material("skin", rough=0.6, sss=0.15, sheen=0.3, spec=0.3), N)
    return ob, V, T, N


# ------------------------------------------------------------------ eyes, nose, mouth
def head_surface(L, off=0.0):
    L = np.atleast_2d(np.asarray(L, np.float64))
    P = C.project(C._head_raw, L, 4)
    return P + C.grad(C._head_raw, P) * off


def build_face(pal):
    dark = Ub.material("lidrim", rough=0.4, spec=0.4, color=hexc("#120e0d"))
    for side in (1, -1):
        E, n, u, v = C.EYES[side]
        c, R = C.eye_ball(side)
        look = n + u * 0.22
        look /= np.linalg.norm(look)
        up = v - look * (v @ look)
        up /= np.linalg.norm(up)
        Vs, Fs = Ub.uv_sphere(np.zeros(3), R, 64, 40)
        d = Vs / R
        ca = d @ look
        h = d @ up
        cols = pal["eye2"] if (pal["eye2"] and side == 1) else pal["eye"]
        deep, light = hexc(cols[0]), hexc(cols[1])
        iris = smooth(np.cos(np.radians(47)), np.cos(np.radians(44)), ca)
        pupil = smooth(np.cos(np.radians(24)), np.cos(np.radians(21)), ca)
        ring = smooth(np.cos(np.radians(40)), np.cos(np.radians(46)), ca) * iris
        ic = mix(light, deep, smooth(-0.6, 0.6, h))
        streak = vnoise(Vs * 3, 6.0, 9)
        ic = ic * (0.85 + 0.3 * streak)[:, None]
        ic = mix(ic, hexc("#140c08"), ring * 0.8)
        ic = mix(ic, hexc("#070505"), pupil)
        col = mix(hexc("#e9e0d4"), ic, iris)
        col[:, 3] = 1
        Ub.add_mesh("eye", C.head_to_world(c + Vs), Fs, col, Ub.material("eye", rough=0.25, spec=0.6, coat=1.0))
        # a highlight
        for (du, dv, rr) in ((0.3, 0.42, 0.045), (-0.25, -0.3, 0.02)):
            dirn = look + u * du + up * dv
            dirn /= np.linalg.norm(dirn)
            gc = c + dirn * (R + 0.004)
            ga = np.cross(dirn, up); ga /= np.linalg.norm(ga)
            gb = np.cross(ga, dirn)
            Vg = [gc] + [gc + ga * np.cos(t) * rr + gb * np.sin(t) * rr * 0.8 for t in np.linspace(0, 2 * np.pi, 16, endpoint=False)]
            Fg = [(0, k + 1, (k + 1) % 16 + 1) for k in range(16)]
            Ub.add_mesh("glint", C.head_to_world(np.array(Vg)), Fg, None, Ub.material("glint", emit=4.0, color=(1, 1, 1, 1)))
        # the dark rim round the whole eye
        a, b = C.EYE_HALF
        ts = np.linspace(0, 2 * np.pi, 48)
        ring_pts = []
        for t in ts:
            uu = a * 1.02 * np.cos(t)
            x = min(abs(uu) / a, 1.0)
            lim = b * (1.0 - x ** 2.4) ** 0.6 if np.sin(t) >= 0 else -b * 0.92 * (1.0 - x ** 2.0) ** 0.7
            ring_pts.append(E + u * uu + v * (lim * 1.02 - 0.12 * uu))
        ring_pts = head_surface(np.array(ring_pts), 0.008)
        Vt, Ft = Ub.tube(ring_pts, np.full(len(ring_pts), 0.009), 6)
        Ub.add_mesh("lidrim", C.head_to_world(Vt), Ft, None, dark)
    # the nose: glossy black leather over the shape's nose, with nostrils
    c, r = C.NOSE
    Vn, Fn = Ub.uv_sphere(np.zeros(3), 1.0, 40, 24)
    Vn = Vn * (np.array(r) * 1.06) + c
    cn = np.tile(hexc("#1a1617"), (len(Vn), 1))
    for s in (1, -1):
        dd = np.linalg.norm((Vn - (c + np.array([0.11, 0.055 * s, 0.0]))) / np.array([0.04, 0.03, 0.028]), axis=1)
        cn = mix(cn, hexc("#050404"), smooth(1.4, 0.9, dd))
    cn = mix(cn, hexc("#3a3236"), smooth(0.05, 0.1, Vn[:, 2] - c[2]) * 0.6)     # lighter on top
    Ub.add_mesh("nose", C.head_to_world(Vn), Fn, cn, Ub.material("nose", rough=0.32, spec=0.6, coat=0.3))
    # the tongue, resting on the lower jaw and lolling a little out of the front
    tc, tr = C.TONGUE
    Vt, Ft = Ub.uv_sphere(np.zeros(3), 1.0, 32, 16)
    q = Vt.copy()
    q[:, 2] *= 1.0 - 0.35 * np.exp(-(q[:, 1] / 0.25) ** 2)                      # a groove down the middle
    q = q * np.array(tr)
    q[:, 2] -= 0.2 * np.clip(q[:, 0] / tr[0] + 0.2, 0, 1.2) ** 2                # the tip hangs down over the lip
    ct = mix(np.tile(hexc("#e58f9f"), (len(q), 1)), hexc("#c46a7c"), smooth(0.4, -0.6, q[:, 0] / tr[0]))
    Ub.add_mesh("tongue", C.head_to_world(q + tc + np.array([0.12, 0, 0.01])), Ft, ct, Ub.material("tongue", rough=0.4, sss=0.35, spec=0.4, coat=0.15))
    # teeth: the upper canines
    for s in (1, -1):
        base = np.array([1.38, 0.115 * s, 3.0])
        pts = np.array([base, base + np.array([0.005, 0.0, -0.035]), base + np.array([0.01, 0.0, -0.07])])
        Vt, Ft = Ub.tube(pts, np.array([0.022, 0.016, 0.003]), 8)
        Ub.add_mesh("tooth", C.head_to_world(Vt), Ft, None, Ub.material("tooth", rough=0.3, spec=0.5, color=hexc("#fbf6ec")))


# ------------------------------------------------------------------ ears: semi-pricked, the tips folding forward
def build_ears(pal, fur):
    c, r = C.SKULL
    dark, tan = hexc(pal["dark"]), hexc(pal["tan"])
    for side in (1, -1):
        base = C._ray_hit(C._head_raw, c, np.array([-0.18, 0.62 * side, 0.76]))
        n = C.grad(C._head_raw, base[None])[0]
        axis = np.array([-0.05, 0.38 * side, 1.0]); axis /= np.linalg.norm(axis)
        face = np.array([1.0, 0.25 * side, 0.0]); face -= axis * (face @ axis); face /= np.linalg.norm(face)
        across = np.cross(axis, face)
        fold_at = 0.6 if not (pal is PALETTES["B"] and side == 1) else 0.95   # B: the near ear stands right up
        Hh, W = 0.66, 0.2
        nu, nr = 36, 24
        V, Cc, inner_pts = [], [], []
        for i in range(nu):
            uu = i / (nu - 1)
            w = W * (1 - uu) ** 0.8 * (0.85 + 0.35 * np.sin(np.pi * uu)) + 0.004
            th_ = 0.05 * (1 - uu) + 0.01
            # the fold: past fold_at the ear bends forward and down about the face axis
            if uu <= fold_at:
                centre = base - n * 0.06 + axis * (Hh * uu)
                ax_u, fc = axis, face
            else:
                k = (uu - fold_at) / (1 - fold_at)
                ang = np.radians(100) * smooth(0.0, 0.5, k)
                pivot = base - n * 0.06 + axis * (Hh * fold_at)
                ax_u = axis * np.cos(ang) + face * np.sin(ang)
                fc = face * np.cos(ang) - axis * np.sin(ang)
                centre = pivot + ax_u * (Hh * (uu - fold_at))
            for kk in range(nr):
                th = 2 * np.pi * kk / nr
                cx, sy = np.cos(th), np.sin(th)
                depth = -th_ * sy if sy >= 0 else th_ * (-sy) * 0.2 + 0.05 * (1 - cx * cx) * (1 - uu)
                p = centre + across * (w * cx) + fc * depth
                V.append(p)
                inner = sy < 0 and cx * cx < 0.6 and uu < 0.85
                Cc.append(mix(hexc("#5a3a3a"), hexc("#7a5050"), uu) if inner else dark)
                if inner and i % 2 == 0:
                    inner_pts.append((p, fc))
        V = np.array(V)
        Ub.add_mesh("ear", C.head_to_world(V), Ub.grid_faces(nu, nr, wrap_v=True), np.array(Cc), Ub.material("earskin", rough=0.55, sss=0.25, spec=0.3))
        # fur on the ear: short on the back, a long fringe on the outer edge, tan tufts inside
        Vw = C.head_to_world(V)
        for i in range(0, nu - 2):
            uu = i / (nu - 1)
            for kk in range(nr):
                th = 2 * np.pi * kk / nr
                if np.sin(th) < 0.1:
                    continue
                p = Vw[i * nr + kk]
                nn = (Vw[i * nr + kk] - C.head_to_world((base + axis * (Hh * min(uu, fold_at)))[None])[0])
                nn /= max(np.linalg.norm(nn), 1e-6)
                edge = abs(np.cos(th)) > 0.75
                ln = 0.16 * (1 - uu) + 0.05 if edge else 0.055
                for _ in range(4 if edge else 2):
                    fur.append((p + np.random.normal(0, 0.004, 3), nn, ln, dark if not edge or uu > 0.25 or np.random.random() < 0.6 else mix(dark, tan, 0.6), 0.25, "ear"))
        for p, fc in inner_pts:
            w_ = C.head_to_world(p[None])[0]
            for _ in range(6):
                fur.append((w_ + np.random.normal(0, 0.012, 3), C.head_dir(-fc + axis * 0.6), 0.17, mix(tan, hexc(pal["white"]), 0.45), 0.6, "ear"))


# ------------------------------------------------------------------ the tail: a plume lying round the near side, the tip lifting
TAIL = np.array([(-1.18, 0.0, 0.55), (-1.52, 0.05, 0.26), (-1.84, 0.28, 0.13), (-1.97, 0.62, 0.13), (-1.88, 0.92, 0.22), (-1.7, 1.08, 0.38)])


def tail_curve(m=40):
    t = np.linspace(0, 1, len(TAIL))
    s = np.linspace(0, 1, m)
    out = np.stack([np.interp(s, t, TAIL[:, k]) for k in range(3)], 1)
    for _ in range(6):
        out[1:-1] = (out[:-2] + 2 * out[1:-1] + out[2:]) / 4
    return out


def build_tail(pal, fur):
    c = tail_curve(48)
    m = len(c)
    rad = 0.13 * (1 - np.linspace(0, 1, m)) ** 0.8 + 0.035
    Vt, Ft = Ub.tube(c, rad, 16)
    t_ = np.repeat(np.linspace(0, 1, m), 16)
    tc = mix(np.tile(hexc(pal["dark"]), (len(Vt) - 2, 1)), hexc(pal["white"]), smooth(0.62, 0.72, t_))
    tc = np.vstack([tc, hexc(pal["dark"]), hexc(pal["white"])])
    Ub.add_mesh("tail", Vt, Ft, tc, Ub.material("skin", rough=0.6, sss=0.15, sheen=0.3, spec=0.3))
    T_ = np.gradient(c, axis=0)
    T_ /= np.linalg.norm(T_, axis=1, keepdims=True)
    rng = np.random.default_rng(12)
    nstr = 9000 if QUICK else 46000
    for _ in range(nstr):
        s = rng.random() ** 0.85
        i = min(int(s * (m - 1)), m - 2)
        a = np.cross(T_[i], [0, 0, 1.0])
        if np.linalg.norm(a) < 1e-3:
            a = np.array([1.0, 0, 0])
        a /= np.linalg.norm(a)
        b = np.cross(T_[i], a)
        th = rng.uniform(0, 2 * np.pi)
        out = a * np.cos(th) + b * np.sin(th)
        p = c[i] + out * rad[i]
        ln = (0.55 * np.sin(np.pi * min(1.0, s * 1.1 + 0.15)) + 0.2) * rng.uniform(0.8, 1.15)
        col = mix(hexc(pal["dark"]), hexc(pal["white"]), smooth(0.62, 0.72, s))
        if pal.get("merle"):
            col = mix(col, hexc(pal["dark2"]), smooth(0.5, 0.7, vnoise(p[None], 3.0, 5)[0]) * (s < 0.7))
        comb = T_[i] * (0.85 + 0.6 * s) + out * 0.35 * (1 - s) + np.array([0, 0, -0.25])
        fur.append((p, comb / np.linalg.norm(comb), ln, col, 0.15, "tail"))


# ------------------------------------------------------------------ the collar (A): navy, with a silver tag
def build_collar():
    a, b = np.array([0.28, 0.0, 2.1]), np.array([0.52, 0.0, 2.88])
    centre = a + (b - a) * 0.38
    axis = (b - a) / np.linalg.norm(b - a)
    e1 = np.cross(axis, [0, 1.0, 0]); e1 /= np.linalg.norm(e1)
    e2 = np.cross(axis, e1)
    R = 0.5 + 0.12
    pts = np.array([centre + (e1 * np.cos(t) + e2 * np.sin(t)) * R for t in np.linspace(0, 2 * np.pi, 72)])
    V, F = Ub.tube(pts, np.full(len(pts), 0.045), 10, close_ends=False)
    Ub.add_mesh("collar", V, F, None, Ub.material("collar", rough=0.45, spec=0.4, color=hexc("#22325c")))
    front = centre + e1 * R * (1 if e1[0] > 0 else -1)
    ring = front + np.array([0.05, 0.0, -0.06])
    V, F = Ub.tube(np.array([ring + np.array([0.0, np.cos(t), np.sin(t)]) * 0.035 for t in np.linspace(0, 2 * np.pi, 20)]), np.full(20, 0.008), 6)
    Ub.add_mesh("ring", V, F, None, Ub.material("silver", rough=0.15, spec=0.9, metal=1.0, color=hexc("#c9ccd4")))
    tag_c = ring + np.array([0.03, 0.0, -0.11])
    Vt = [tag_c + np.array([0.012 * k, 0, 0]) + np.array([0, np.cos(t), np.sin(t) * 1.3]) * 0.065
          for k in (-1, 1) for t in np.linspace(0, 2 * np.pi, 24, endpoint=False)]
    Ft = [(i, (i + 1) % 24, 24 + (i + 1) % 24) for i in range(24)] + [(i, 24 + (i + 1) % 24, 24 + i) for i in range(24)]
    Vt.append(tag_c - np.array([0.013, 0, 0])); Vt.append(tag_c + np.array([0.013, 0, 0]))
    for i in range(24):
        Ft.append((48, (i + 1) % 24, i))
        Ft.append((49, 24 + i, 24 + (i + 1) % 24))
    Ub.add_mesh("tag", np.array(Vt), Ft, None, Ub.material("silver", rough=0.15, spec=0.9, metal=1.0, color=hexc("#c9ccd4")))
    return centre, axis, R


# ------------------------------------------------------------------ fur
def tangent(comb, N):
    t = comb - N * np.sum(comb * N, 1, keepdims=True)
    return t / np.maximum(np.linalg.norm(t, axis=1, keepdims=True), 1e-9)


def body_fur(V, T, pal, rng, collar):
    """roots spread over the body by area, with a length, a lift and a combing direction for each part of the coat"""
    A = np.linalg.norm(np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]]), axis=1) / 2
    tri = rng.choice(len(T), FUR_COUNT, p=A / A.sum())
    r1, r2 = rng.random(FUR_COUNT), rng.random(FUR_COUNT)
    s1 = np.sqrt(r1)
    R = V[T[tri, 0]] * (1 - s1)[:, None] + V[T[tri, 1]] * (s1 * (1 - r2))[:, None] + V[T[tri, 2]] * (s1 * r2)[:, None]
    N = C.grad(C.sdf, R)
    p = C.parts(R)
    names = list(p)
    which = np.array(names)[np.argmin(np.stack([p[k] for k in names], 1), 1)]
    L = C.world_to_head(R)
    z = R[:, 2]
    # no fur on the nose, the eyes, in the mouth, or under the paws
    keep = np.ones(len(R), bool)
    keep &= np.linalg.norm((L - C.NOSE[0]) / C.NOSE[1], axis=1) > 1.25
    keep &= np.linalg.norm((L - C.MOUTH[0]) / (np.array(C.MOUTH[1]) * np.array([1.05, 1.05, 2.4])), axis=1) > 1.0
    for s in (1, -1):
        E, n, u, v = C.EYES[s]
        q = L - E
        keep &= C.almond(q @ u, q @ v) > 0.025
    keep &= ~((z < 0.06) & (N[:, 2] < -0.3))
    R, N, which, L, z = R[keep], N[keep], which[keep], L[keep], z[keep]
    n = len(R)
    head = which == "head"
    ln = np.full(n, 0.26)
    lift = np.full(n, 0.25)
    comb = np.tile(np.array([-0.55, 0.0, -1.0]), (n, 1))
    # the head: short on the face and muzzle, fluffy cheeks, longer behind
    hl = 0.045 + 0.02 * smooth(1.0, 0.7, L[:, 0]) - 0.02 * smooth(1.0, 1.12, L[:, 0])
    hl += 0.08 * smooth(0.3, 0.42, np.abs(L[:, 1])) * smooth(3.35, 3.15, L[:, 2]) * smooth(1.05, 0.85, L[:, 0])
    hl += 0.1 * smooth(0.55, 0.3, L[:, 0])
    ln = np.where(head, hl, ln)
    lift = np.where(head, 0.2, lift)
    comb = np.where(head[:, None], C.head_dir(np.array([-1.0, 0.0, -0.25]))[None], comb)
    # the neck and ruff: long, standing out, falling down over the chest
    neck = which == "neck"
    bib = (which == "body") & (N[:, 0] > 0.2) & (z > 0.95) & (z < 2.4)
    ln = np.where(neck, 0.44 - 0.1 * smooth(0.0, -0.6, N[:, 0]), ln)
    ln = np.where(bib, 0.4, ln)
    lift = np.where(neck | bib, 0.45, lift)
    comb = np.where((neck | bib)[:, None], np.array([0.15, 0.0, -1.0])[None], comb)
    # the belly hangs; the rump is a little shorter
    ln = np.where((which == "body") & (N[:, 2] < -0.4), 0.32, ln)
    ln = np.where((which == "body") & (R[:, 0] < -0.6) & (N[:, 2] > 0.3), 0.22, ln)
    # legs: short in front, feathered behind; britches on the hind legs; short paws
    fl = np.isin(which, ["nf", "ff"])
    ln = np.where(fl, 0.04 + 0.2 * smooth(0.1, -0.6, N[:, 0]) * smooth(0.4, 0.8, z), ln)
    hl_ = np.isin(which, ["nh", "fh"])
    ln = np.where(hl_, np.where(z > 0.45, 0.2 + 0.14 * smooth(0.1, -0.6, N[:, 0]), 0.05), ln)
    legs = fl | hl_
    lift = np.where(legs, 0.15, lift)
    comb = np.where(legs[:, None], np.array([-0.15, 0.0, -1.0])[None], comb)
    ln = np.where(z < 0.22, 0.025, ln)
    # the collar presses the fur flat under it
    if collar is not None:
        cc, ax, Rc = collar
        along = (R - cc) @ ax
        ln = np.where(np.abs(along) < 0.08, np.minimum(ln, 0.08), ln)
    ln *= rng.uniform(0.8, 1.15, n)
    col = coat(R, N, pal)[:, :3]
    return R, N, tangent(comb, N), ln, lift, col


def grow(R, N, Tg, ln, lift, col, rng, K=6, radius=0.0042):
    """strands: up off the skin, along the combing direction, sagging a little, gathered into clumps at their tips"""
    n = len(R)
    s = np.linspace(0, 1, K)
    up = 1 - (1 - s) ** 2
    B = np.cross(N, Tg)
    wave = rng.uniform(0, 6.28, n)
    P = (R[:, None] + N[:, None] * (ln * lift)[:, None, None] * up[None, :, None]
         + Tg[:, None] * ln[:, None, None] * s[None, :, None]
         - np.array([0, 0, 1.0])[None, None] * (ln * 0.18)[:, None, None] * (s ** 2)[None, :, None]
         + B[:, None] * (ln * 0.06)[:, None, None] * np.sin(s[None, :] * 3.0 + wave[:, None])[:, :, None])
    # clumps: every strand's tip is pulled toward the tip of the nearest of a few thousand clump strands
    nc = max(1, n // 22)
    ci = rng.choice(n, nc, replace=False)
    kd = KDTree(nc)
    for k, i in enumerate(ci):
        kd.insert(R[i], k)
    kd.balance()
    near = np.array([ci[kd.find(r)[1]] for r in R])
    pull = 0.5 * s ** 1.6
    P += (P[near] - P) * pull[None, :, None] * (np.linalg.norm(R - R[near], axis=1) < 0.12)[:, None, None]
    rad = np.tile(radius * (1 - s) + 0.0006, (n, 1))
    warm = np.array([0.03, 0.018, 0.01])
    C_ = col[:, None] * (0.82 + 0.18 * s)[None, :, None] + warm[None, None] * s[None, :, None]
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
    hb.inputs["Roughness"].default_value = 0.38
    hb.inputs["Radial Roughness"].default_value = 0.45
    hb.inputs["Coat"].default_value = 0.15
    if "Random Roughness" in hb.inputs:
        hb.inputs["Random Roughness"].default_value = 0.2
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
    cv.materials.append(hair_material() if not CLAY else Ub.material("clayhair"))
    return n


# ------------------------------------------------------------------ cameras and lights
VIEWS_AT = {"hero": (36.0, 7.0, (0.15, 0.0, 1.95), 4.9), "head": (32.0, 5.0, (1.0, 0.1, 3.35), 1.9),
            "side": (0.0, 4.0, (0.0, 0.0, 1.95), 5.0)}


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
        ob.rotation_euler = (Vector((0.2, 0, 2.0)) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    area("key", (4.5, 6.5, 7.5), 5, 900, (1.0, 0.95, 0.88))
    area("fill", (6, -4, 3), 6, 220, (0.9, 0.95, 1.0))
    area("rim", (-5, -2, 6), 4, 420, (1.0, 0.94, 0.86))
    area("bounce", (1.5, 3, -2), 6, 60, (0.95, 1.0, 0.9))


def main():
    os.makedirs(OUT, exist_ok=True)
    for vk in VARIANTS:
        pal = PALETTES[vk]
        Ub.MATS.clear()
        sc = Ub.setup()
        sc.view_settings.exposure = -0.1
        rng = np.random.default_rng(21)
        body, V, T, N = build_body(pal)
        build_face(pal)
        fur = []
        build_ears(pal, fur)
        build_tail(pal, fur)
        collar = build_collar() if pal["collar"] else None
        R, Nn, Tg, ln, lift, col = body_fur(V, T, pal, rng, collar)
        P, rad, cc = grow(R, Nn, Tg, ln, lift, col, rng)
        total = make_hair("fur", P, rad, cc)
        if fur:
            Re = np.array([f[0] for f in fur])
            Te = np.array([f[1] for f in fur])
            Te = Te / np.maximum(np.linalg.norm(Te, axis=1, keepdims=True), 1e-9)
            ln_e = np.array([f[2] for f in fur])
            ce = np.array([np.asarray(f[3])[:3] for f in fur])
            le = np.array([f[4] for f in fur])
            P2, r2, c2 = grow(Re, np.tile(np.array([0, 0, 1.0]), (len(Re), 1)), Te, ln_e, le * 0.3, ce, rng, radius=0.0038)
            total += make_hair("fur_extra", P2, r2, c2)
        print("variant", vk, "fur strands", total)
        lights()
        res = 500 if QUICK else 1200
        sc.render.resolution_x = res
        sc.render.resolution_y = res
        for v in VIEWS:
            cam = camera(v)
            sc.render.filepath = os.path.join(OUT, "%s_%s.png" % (vk, v))
            bpy.ops.render.render(write_still=True)
            bpy.data.objects.remove(cam)
            print("rendered", vk, v)


main()
