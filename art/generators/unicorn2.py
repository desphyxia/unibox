"""A new unicorn, built from scratch as one 3D model and rendered in Blender (headless, Cycles). Direction: a chibi
watercolour unicorn (a stock picture the user shared, used as direction only; nothing is copied or traced): a big
round head with a long spiral horn, huge dark-blue almond eyes with lashes, white freckles, a small muzzle and a smile,
tall ears with blue insides, a pink-peach-lilac mane and tail in flowing locks, a flower crown, a flower garland on the
hip, rose cuffs above silver hooves, a pale aqua coat fading to lilac legs with glitter, one foreleg raised.

Everything here is new (none of unicorn3d.py, artgen5.py or their helpers):
  unicorn2_shape.py  the body as one signed distance field, meshed by surface nets
  this file          eyes in real sockets, lids and lashes, ears, the spiral horn, hair locks draped over the body,
                     flowers, hooves, freckles, glitter, colours, lights and cameras
Run:   blender -b --factory-startup -P unicorn2.py -- OUTDIR [--quick] [--clay] [--hair v1|v2] [view ...]
       views: hero side front back head
       --hair v1  the first hair: one solid ribbon a lock (kept for comparison)
       --game     with v2: the hair at game density (fewer segments round and along each strand)
       --hair v2  hair a game can draw too: locks that split into wisps toward the end, stray strands, combed flow,
                  and a strand shader (a shine along the hair, fine lengthwise grooves and streaks, lighter tips,
                  darker under-layers, light through thin edges) using only per-vertex data and per-pixel noise
"""
import bpy, bmesh, math, os, sys, random
import numpy as np
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import unicorn2_shape as U

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = argv[0] if argv else "unicorn2_out"
QUICK = "--quick" in argv
CLAY = "--clay" in argv
HAIR_STYLE = argv[argv.index("--hair") + 1] if "--hair" in argv else "v1"
GAME_LOD = "--game" in argv                                     # v2 hair at a density the game could draw live
VIEWS = [a for a in argv[1:] if not a.startswith("--") and a not in ("v1", "v2")] or ["hero"]
os.makedirs(OUT, exist_ok=True)
rnd = random.Random(7)
H = 0.03 if QUICK else 0.014                                   # the body's grid spacing


def hexc(h, a=1.0):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return np.array([x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c] + [a])


def mix(a, b, t):
    t = np.clip(t, 0.0, 1.0)
    if np.ndim(t) == 1:
        t = t[:, None]
    return a * (1 - t) + b * t


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ scene
def setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 24 if QUICK else 128
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.render.film_transparent = True
    sc.view_settings.view_transform = "Filmic"
    sc.view_settings.look = "None"
    sc.view_settings.exposure = -0.2
    w = bpy.data.worlds.new("world")
    sc.world = w
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs["Color"].default_value = (0.93, 0.94, 1.0, 1)
    bg.inputs["Strength"].default_value = 0.55
    return sc


MATS = {}


def material(name, rough=0.5, sss=0.0, sheen=0.0, spec=0.4, coat=0.0, emit=0.0, metal=0.0, film=0.0, color=None):
    """a Principled material coloured by the vertex colour attribute "Col" (or a plain colour)"""
    if name in MATS:
        return MATS[name]
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    bs = nt.nodes["Principled BSDF"]
    if CLAY and name not in ("eye", "glint", "dark"):
        bs.inputs["Base Color"].default_value = (0.5, 0.5, 0.52, 1)
        bs.inputs["Roughness"].default_value = 0.6
        MATS[name] = m
        return m
    if color is None:
        at = nt.nodes.new("ShaderNodeAttribute")
        at.attribute_name = "Col"
        nt.links.new(at.outputs["Color"], bs.inputs["Base Color"])
        if emit > 0:
            nt.links.new(at.outputs["Color"], bs.inputs["Emission Color"])
    else:
        bs.inputs["Base Color"].default_value = tuple(color)
        if emit > 0:
            bs.inputs["Emission Color"].default_value = tuple(color)
    bs.inputs["Roughness"].default_value = rough
    bs.inputs["Subsurface Weight"].default_value = sss
    bs.inputs["Subsurface Radius"].default_value = (0.5, 0.32, 0.36)
    bs.inputs["Subsurface Scale"].default_value = 0.08
    bs.inputs["Sheen Weight"].default_value = sheen
    bs.inputs["Specular IOR Level"].default_value = spec
    bs.inputs["Coat Weight"].default_value = coat
    bs.inputs["Coat Roughness"].default_value = 0.05
    bs.inputs["Metallic"].default_value = metal
    bs.inputs["Emission Strength"].default_value = emit
    if film > 0 and "Thin Film Thickness" in bs.inputs:
        bs.inputs["Thin Film Thickness"].default_value = film
        bs.inputs["Thin Film IOR"].default_value = 1.35
    MATS[name] = m
    return m


def add_mesh(name, V, T, cols, mat, normals=None, smooth_shade=True, attrs=None):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in np.asarray(V, np.float64)], [], [tuple(int(i) for i in t) for t in T])
    me.update()
    if cols is not None:
        cols = np.asarray(cols, np.float64)
        if cols.shape[1] == 3:
            cols = np.concatenate([cols, np.ones((len(cols), 1))], 1)
        a = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
        a.data.foreach_set("color", cols.astype(np.float32).ravel())
    for an, arr in (attrs or {}).items():
        arr = np.asarray(arr, np.float32)
        at = me.attributes.new(an, "FLOAT_VECTOR", "POINT")
        at.data.foreach_set("vector", arr.ravel())
    if smooth_shade:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    if normals is not None:
        me.normals_split_custom_set_from_vertices([tuple(n) for n in normals])
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    me.materials.append(mat)
    return ob


def grid_faces(nu, nv, wrap_v=False):
    F = []
    for i in range(nu - 1):
        for j in range(nv if wrap_v else nv - 1):
            j2 = (j + 1) % nv
            a, b, c, d = i * nv + j, i * nv + j2, (i + 1) * nv + j2, (i + 1) * nv + j
            F += [(a, b, c), (a, c, d)]
    return F


# ------------------------------------------------------------------ the body
def build_body():
    F, o = U.sample(U.sdf, (-2.0, -1.3, 0.1), (3.3, 1.45, 6.25), H)
    V, T = U.surface_nets(F, o, H)
    V = U.project(U.sdf, V, 2)
    N = U.grad(U.sdf, V)
    cols = coat_colours(V, N)
    return add_mesh("body", V, T, cols, material("coat", rough=0.5, sss=0.18, sheen=0.35, spec=0.3), N)


COAT_TOP = hexc("#f6fcfe")
COAT_MID = hexc("#e2f3f9")
COAT_SHADE = hexc("#c4e1f1")
LEG_HI = hexc("#d4e8f6")
LEG_LO = hexc("#d0c8f3")
HOOF_RIM = hexc("#b1a2e4")
BLUSH = hexc("#ffb9cd")


def coat_colours(V, N):
    p = U.parts(V)
    names = list(p)
    D = np.stack([p[k] for k in names], 1)
    which = np.array(names)[np.argmin(D, 1)]
    up = N[:, 2]
    c = mix(COAT_MID, COAT_TOP, smooth(-0.1, 0.8, up))
    c = mix(c, COAT_SHADE, smooth(0.1, -0.8, up) * 0.8)
    # the legs fade to lilac toward the hooves
    leg = np.isin(which, list(U.LEGS))
    z = V[:, 2]
    lc = mix(LEG_LO, LEG_HI, smooth(0.45, 1.9, z))
    c = np.where(leg[:, None], mix(c, lc, smooth(1.75, 0.9, z)), c)
    c = mix(c, HOOF_RIM, smooth(0.55, 0.32, z)[:, None] * leg[:, None])
    # the belly is a little bluer
    c = mix(c, COAT_SHADE, (smooth(2.0, 1.65, z) * (~leg) * 0.5))
    # the face: a blush on the cheek below the eye, blue shade under the jaw
    L = U.world_to_head(V)
    head = which == "head"
    for s in (1, -1):
        E, n, u, v = U.EYES[s]
        bc = E - v * 0.42 - u * 0.05 + n * 0.0
        d = np.linalg.norm(L - bc, axis=1)
        c = mix(c, BLUSH, (smooth(0.32, 0.0, d) * 0.75 * head))
    sm = U.SMILE if U.SMILE is not None else None
    if sm is not None:
        ds = np.full(len(V), 9.0)
        near = np.linalg.norm(L - np.array([2.72, 0.0, 3.95]), axis=1) < 0.8
        if near.any():
            ds[near] = U._smile_dist(L[near])
        c = mix(c, hexc("#a9a0d6"), smooth(0.04, 0.02, ds) * head * 0.85)
    cN, rN = U.NOSTRIL
    dn = np.linalg.norm((L - cN) / np.array(rN), axis=1)
    c = mix(c, hexc("#bdb1df"), smooth(1.5, 1.0, dn) * head * 0.8)
    return c


# ------------------------------------------------------------------ shared shapes
def tube(pts, radii, ring=12, up=None, close_ends=True):
    """a tube along points, radius per point; returns (V, T)"""
    pts = np.asarray(pts, np.float64)
    n = len(pts)
    T_ = np.gradient(pts, axis=0)
    T_ /= np.maximum(np.linalg.norm(T_, axis=1, keepdims=True), 1e-9)
    ref = np.array(up if up is not None else (0.0, 0.0, 1.0))
    V = []
    prev = None
    for i in range(n):
        t = T_[i]
        a = ref - t * (ref @ t) if prev is None else prev - t * (prev @ t)
        if np.linalg.norm(a) < 1e-6:
            a = np.cross(t, [1.0, 0, 0])
        a /= np.linalg.norm(a)
        prev = a
        b = np.cross(t, a)
        for k in range(ring):
            th = 2 * np.pi * k / ring
            V.append(pts[i] + (a * np.cos(th) + b * np.sin(th)) * radii[i])
    F = grid_faces(n, ring, wrap_v=True)
    V = np.array(V)
    if close_ends:
        V = np.vstack([V, pts[0], pts[-1]])
        c0, c1 = len(V) - 2, len(V) - 1
        for k in range(ring):
            F.append((c0, (k + 1) % ring, k))
            F.append((c1, (n - 1) * ring + k, (n - 1) * ring + (k + 1) % ring))
    return V, F


def uv_sphere(c, r, nu=48, nv=32):
    V = []
    for i in range(nv + 1):
        ph = np.pi * i / nv
        for j in range(nu):
            th = 2 * np.pi * j / nu
            V.append(c + r * np.array([np.sin(ph) * np.cos(th), np.sin(ph) * np.sin(th), np.cos(ph)]))
    return np.array(V), grid_faces(nv + 1, nu, wrap_v=True)


def head_surface(L, off=0.0):
    """head-local points pulled onto the uncarved head, then lifted off it"""
    L = np.atleast_2d(np.asarray(L, np.float64))
    P = U.project(U._head_raw, L, 4)
    return P + U.grad(U._head_raw, P) * off


# ------------------------------------------------------------------ eyes
IRIS_TOP = hexc("#16205c")
IRIS_MID = hexc("#2c48a6")
IRIS_LOW = hexc("#86b2ec")
PUPIL = hexc("#090c2c")
SCLERA = hexc("#eef3ff")
DARK = hexc("#1f2152")


def build_eyes():
    dark = material("dark", rough=0.45, spec=0.3, color=DARK)
    for side in (1, -1):
        E, n, u, v = U.EYES[side]
        c, R = U.eye_ball(side)
        # the gaze: a little forward, toward the viewer
        look = n + u * 0.32
        look /= np.linalg.norm(look)
        up = v - look * (v @ look)
        up /= np.linalg.norm(up)
        Vs, Fs = uv_sphere(np.zeros(3), R, 64, 40)
        d = Vs / R
        cosang = d @ look
        h = d @ up                                            # -1 bottom .. 1 top
        iris = smooth(np.cos(np.radians(49)), np.cos(np.radians(46)), cosang)
        pupil = smooth(np.cos(np.radians(21)), np.cos(np.radians(18)), cosang)
        ring = smooth(np.cos(np.radians(41)), np.cos(np.radians(47)), cosang) * iris
        ic = mix(IRIS_MID, IRIS_TOP, smooth(-0.1, 0.55, h / R * R))
        ic = mix(ic, IRIS_LOW, smooth(-0.05, -0.55, h) * 0.9)
        ic = mix(ic, IRIS_TOP, ring * 0.7)
        ic = mix(ic, PUPIL, pupil)
        col = mix(SCLERA, ic, iris)
        W = U.head_to_world(c + Vs)
        add_mesh("eye", W, Fs, col, material("eye", rough=0.25, spec=0.6, coat=1.0))
        # highlights: a big one up and forward, a small one low and back
        for (du, dv, rr) in ((0.34, 0.42, 0.095), (-0.3, -0.36, 0.045)):
            dirn = look + u * du * 0.9 + up * dv * 0.9
            dirn /= np.linalg.norm(dirn)
            gc = c + dirn * (R + 0.006)
            gn = dirn
            ga = np.cross(gn, up); ga /= np.linalg.norm(ga)
            gb = np.cross(ga, gn)
            Vg = [gc]
            for k in range(20):
                th = 2 * np.pi * k / 20
                Vg.append(gc + ga * np.cos(th) * rr * 1.1 + gb * np.sin(th) * rr * 0.85)
            Fg = [(0, k + 1, (k + 1) % 20 + 1) for k in range(20)]
            add_mesh("glint", U.head_to_world(np.array(Vg)), Fg, None, material("glint", emit=4.0, color=(1, 1, 1, 1)))
        # the upper lid line: along the almond's top edge, thin at the front, thick at the back, flicking up
        a, b = U.EYE_HALF
        us = np.linspace(a * 0.98, -a * 1.0, 34)
        x = np.abs(us) / a
        top = b * 1.08 * (1.0 - np.clip(x, 0, 1) ** 2.2) ** 0.62 - 0.16 * us
        lid = [E + u * uu + v * (tt + 0.012) for uu, tt in zip(us, top)]
        for k in range(1, 6):                                  # the flick past the back corner
            q = k / 5
            lid.append(E + u * (-a - 0.09 * q) + v * (0.16 * a + 0.03 + 0.1 * q * q))
        lid = head_surface(np.array(lid), 0.016)
        m = len(lid)
        rad = np.array([0.006 + 0.03 * smooth(0.0, 0.75, k / (m - 1)) * (1 - 0.7 * smooth(0.85, 1.0, k / (m - 1))) for k in range(m)])
        Vt, Ft = tube(lid, rad, 8)
        add_mesh("lid", U.head_to_world(Vt), Ft, None, dark)
        # lashes from the back third, sweeping up and back
        for (t0, ln, bend) in ((0.62, 0.17, 0.5), (0.74, 0.21, 0.65), (0.86, 0.24, 0.8), (0.97, 0.2, 0.9)):
            k0 = int(t0 * (len(us) - 1))
            root = lid[k0]
            nrm = U.grad(U._head_raw, root[None])[0]
            pts = []
            for s_ in np.linspace(0, 1, 9):
                pts.append(root + v * ln * s_ * (1 - 0.3 * s_) - u * ln * bend * s_ * s_ * 0.8 + nrm * ln * 0.55 * s_)
            Vt, Ft = tube(np.array(pts), np.linspace(0.016, 0.002, 9), 6)
            add_mesh("lash", U.head_to_world(Vt), Ft, None, dark)
        # a faint lower lid
        us2 = np.linspace(a * 0.8, -a * 0.85, 22)
        x2 = np.abs(us2) / a
        bot = -(b * 0.86 * (1.0 - np.clip(x2, 0, 1) ** 2.0) ** 0.75) - 0.16 * us2
        low = head_surface(np.array([E + u * uu + v * (bb - 0.01) for uu, bb in zip(us2, bot)]), 0.008)
        Vt, Ft = tube(low, 0.006 + 0.008 * np.sin(np.linspace(0, np.pi, len(low))), 6)
        add_mesh("lowlid", U.head_to_world(Vt), Ft, None, material("lowlid", rough=0.5, color=hexc("#7f86c8")))


# ------------------------------------------------------------------ ears
EAR_IN = hexc("#c2d6f6")
EAR_IN_DEEP = hexc("#d2c6f4")


def build_ears():
    c, r = U.CRANIUM
    for side in (1, -1):
        base = head_surface(U._ray_hit(U._head_raw, c, np.array([-0.12, 0.5 * side, 0.86])))[0]
        n = U.grad(U._head_raw, base[None])[0]
        axis = n * 0.45 + np.array([-0.12, 0.18 * side, 1.0])
        axis /= np.linalg.norm(axis)
        face = np.array([0.85, 0.5 * side, 0.0])
        face -= axis * (face @ axis)
        face /= np.linalg.norm(face)
        across = np.cross(axis, face)
        EAR_BASES.append((base, axis))
        Hh, W = 1.18, 0.32
        nu, nr = 30, 28
        V, C = [], []
        for i in range(nu):
            uu = i / (nu - 1)
            w = W * (1 - uu) ** 0.7 * (0.8 + 0.45 * np.sin(np.pi * uu)) + 0.004
            th_ = 0.07 * (1 - uu) + 0.012
            cup = 0.09 * np.sin(np.pi * min(uu * 1.2, 1.0)) * (1 - uu * 0.6)
            bend = 0.12 * uu * uu                                  # the tip leans back a little
            for k in range(nr):
                th = 2 * np.pi * k / nr
                cx, sy = np.cos(th), np.sin(th)
                if sy >= 0:
                    depth = -th_ * sy                                     # the back is round
                else:
                    depth = th_ * (-sy) * 0.25 + cup * (1 - cx * cx)       # the front is hollow
                p = base - n * 0.12 + axis * (Hh * uu) + across * (w * cx) + face * depth - face * bend
                V.append(p)
                inner = (sy < 0) and (cx * cx < 0.5) and uu < 0.88
                if inner:
                    C.append(mix(EAR_IN, EAR_IN_DEEP, smooth(0.6, 0.0, uu) * smooth(0.72, 0.0, cx * cx)))
                else:
                    C.append(COAT_TOP)
        F = grid_faces(nu, nr, wrap_v=True)
        add_mesh("ear", U.head_to_world(np.array(V)), F, np.array(C), material("ear", rough=0.5, sss=0.25, sheen=0.3, spec=0.3))


# ------------------------------------------------------------------ the horn: a long pearly spiral
HORN_A = hexc("#fff8ee")
HORN_B = hexc("#f4d9c8")
HORN_TIP = hexc("#fffaf3")


def build_horn():
    c, r = U.CRANIUM
    base = U._ray_hit(U._head_raw, c, np.array([0.5, 0.0, 0.86]))
    axis = np.array([0.42, 0.0, 0.91])
    axis /= np.linalg.norm(axis)
    a = np.array([0.0, 1.0, 0.0])
    b = np.cross(axis, a)
    L, R0, turns = 2.45, 0.24, 7.5
    nu, nr = 160, 36
    V, C = [], []
    for i in range(nu):
        t = i / (nu - 1)
        rr = R0 * (1 - t) ** 0.92 + 0.004
        for k in range(nr):
            th = 2 * np.pi * k / nr
            ph = th - 2 * np.pi * turns * t
            ridge = 0.5 + 0.5 * np.cos(ph)
            rad = rr * (0.86 + 0.14 * ridge ** 0.6)
            V.append(base - axis * 0.15 + axis * (L * t) + (a * np.cos(th) + b * np.sin(th)) * rad)
            C.append(mix(mix(HORN_B, HORN_A, ridge ** 0.8), HORN_TIP, smooth(0.6, 1.0, t)))
    F = grid_faces(nu, nr, wrap_v=True)
    V.append(base - axis * 0.15)
    C.append(HORN_B)
    cb = len(V) - 1
    for k in range(nr):
        F.append((cb, (k + 1) % nr, k))
    add_mesh("horn", U.head_to_world(np.array(V)), F, np.array(C), material("horn", rough=0.22, sss=0.2, spec=0.5, coat=0.5, film=380))


# ------------------------------------------------------------------ hooves
HOOF_A = hexc("#d6dbea")
HOOF_B = hexc("#98a0c2")


def build_hooves():
    for name, j in U.LEGS.items():
        (f, rf), (ht, rh) = j[-2], j[-1]
        f, ht = np.array(f), np.array(ht)
        d = ht - f
        d /= np.linalg.norm(d)
        top = ht - d * 0.04
        ln = max(0.3, ht[2] + 0.02) if ht[2] < 0.36 else 0.3
        nu, nr = 14, 32
        a = np.cross(d, [0.0, 1.0, 0.0]); a /= np.linalg.norm(a)
        b = np.cross(d, a)
        V, C = [], []
        for i in range(nu):
            t = i / (nu - 1)
            r = (rh * 1.06) * (1 + 0.3 * t ** 1.4) * (1 - 0.25 * smooth(0.82, 1.0, t))
            for k in range(nr):
                th = 2 * np.pi * k / nr
                toe = 0.05 * t * max(0.0, np.cos(th))                  # the front wall slopes forward
                p = top + d * (ln * t) + a * (np.cos(th) * r + toe) + b * np.sin(th) * r
                V.append(p)
                C.append(mix(HOOF_A, HOOF_B, smooth(0.2, 1.0, t)))
        F = grid_faces(nu, nr, wrap_v=True)
        V.append(top + d * ln)
        C.append(HOOF_B)
        cb = len(V) - 1
        for k in range(nr):
            F.append((cb, (nu - 1) * nr + k, (nu - 1) * nr + (k + 1) % nr))
        add_mesh("hoof", np.array(V), F, np.array(C), material("hoof", rough=0.18, spec=0.7, metal=0.35, coat=0.4))


# ------------------------------------------------------------------ hair: locks that fall and drape over the body
HAIR_ROOT = hexc("#f4a8ca")
HAIR_PINK = hexc("#f9bcd8")
HAIR_PEACH = hexc("#ffdcc8")
HAIR_GOLD = hexc("#ffdcae")
HAIR_LILAC = hexc("#e2bdf0")
HAIR_VIOLET = hexc("#d0aaea")

HORN_AXIS = np.array([0.42, 0.0, 0.91]) / np.linalg.norm([0.42, 0.0, 0.91])


def obstacles(P):
    """what hair can't go through (world points): the body and head as built, the horn and the ears"""
    L = U.world_to_head(P)
    d = U.smin(U.body_sdf(P), U.neck_sdf(P), 0.35)
    for n in U.LEGS:
        d = U.smin(d, U.leg_sdf(P, n), 0.22)
    d = U.smin(d, U._head_raw(L), 0.3)
    c, r = U.CRANIUM
    hb = U._ray_hit(U._head_raw, c, np.array([0.5, 0.0, 0.86]))
    d = np.minimum(d, U.round_cone(L, hb, hb + HORN_AXIS * 2.1, 0.24, 0.05))
    for e in EAR_BASES:
        d = np.minimum(d, U.round_cone(L, e[0], e[0] + e[1] * 0.85, 0.15, 0.04))
    return d


EAR_BASES = []


def drape(roots, dirs, lengths, steps=70, gravity=1.6, drift=None, clear=0.05, stiff=0.25):
    """lock centre lines, all locks at once: each starts at its root along its direction, bends under gravity (more
    after the stiff first part) and slides over the body instead of through it"""
    roots = np.asarray(roots, np.float64)
    d = np.asarray(dirs, np.float64)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    lengths = np.asarray(lengths, np.float64)
    drift = np.zeros(3) if drift is None else np.asarray(drift, np.float64)
    n = len(roots)
    P = [roots.copy()]
    p = roots.copy()
    for i in range(steps):
        t = (i + 1) / steps
        ds = lengths / steps
        g = gravity * smooth(stiff * 0.4, stiff + 0.25, t)
        d = d + (np.array([0, 0, -1.0]) * g + drift) * ds[:, None]
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        q = p + d * ds[:, None]
        f = obstacles(q)
        want = clear * (0.6 + 0.6 * t)
        hit = f < want
        if hit.any():
            gn = U.grad(obstacles, q[hit])
            q[hit] += gn * (want - f[hit])[:, None]
            dd = d[hit] - gn * np.sum(d[hit] * gn, 1, keepdims=True)
            d[hit] = dd / np.maximum(np.linalg.norm(dd, axis=1, keepdims=True), 1e-9)
        p = q
        P.append(p.copy())
    return np.stack(P, 1)                                       # (locks, steps+1, 3)


def resample(c, m):
    seg = np.linalg.norm(np.diff(c, axis=0), axis=1)
    s = np.concatenate([[0], np.cumsum(seg)])
    t = np.linspace(0, s[-1], m)
    return np.stack([np.interp(t, s, c[:, k]) for k in range(3)], 1)


def shape_lock(c, wave=0.08, freq=1.3, phase=0.0, curl=0.0, curl_r=0.14, curl_from=0.78, side=None):
    """a gentle S-wave across the lock and, if asked, a curl at its end"""
    m = len(c)
    T_ = np.gradient(c, axis=0)
    T_ /= np.maximum(np.linalg.norm(T_, axis=1, keepdims=True), 1e-9)
    out = U.grad(obstacles, c)
    N = out - T_ * np.sum(out * T_, 1, keepdims=True)
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
    B = np.cross(T_, N)
    t = np.linspace(0, 1, m)
    c = c + B * (wave * np.sin(2 * np.pi * freq * t + phase) * smooth(0.0, 0.5, t))[:, None]
    if curl > 0:
        k0 = int(curl_from * (m - 1))
        p0, t0 = c[k0], T_[k0]
        ax = side if side is not None else -N[k0]                   # curling in toward the body
        ax = ax - t0 * (ax @ t0)
        ax /= np.linalg.norm(ax)
        rest = m - k0
        for j in range(rest):
            q = j / max(rest - 1, 1)
            ph = curl * 2 * np.pi * q
            r = curl_r * (1 - 0.35 * q)
            c[k0 + j] = p0 + r * (np.sin(ph) * t0 + (1 - np.cos(ph)) * ax)
    return c


def lock_mesh(c, width, thick=0.36, ring=24, cols=None, seed=0):
    """a flattened tube along a lock's centre line: wide side facing out from the body, tapering to the tip"""
    m = len(c)
    rng = np.random.default_rng(seed)
    T_ = np.gradient(c, axis=0)
    T_ /= np.maximum(np.linalg.norm(T_, axis=1, keepdims=True), 1e-9)
    out = U.grad(obstacles, c)
    N = out - T_ * np.sum(out * T_, 1, keepdims=True)
    for i in range(1, m):                                     # keep the frame from flipping
        if N[i] @ N[i - 1] < 0:
            N[i] = -N[i]
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
    for _ in range(3):
        N[1:-1] = (N[:-2] + 2 * N[1:-1] + N[2:]) / 4
        N -= T_ * np.sum(N * T_, 1, keepdims=True)
        N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
    B = np.cross(T_, N)
    t = np.linspace(0, 1, m)
    w = width * (0.7 + 0.3 * np.sin(np.pi * np.minimum(1.0, t * 1.4))) * (1 - 0.92 * smooth(0.55, 1.0, t) ** 1.3) + 0.004
    V, C = [], []
    streak_ph = rng.uniform(0, 6.28, 3)
    for i in range(m):
        for k in range(ring):
            th = 2 * np.pi * k / ring
            ridge = 0.78 + 0.22 * np.abs(np.cos(3.0 * th + streak_ph[2]))     # strands bunched along the lock
            V.append(c[i] + B[i] * (w[i] * np.cos(th)) + N[i] * (w[i] * thick * np.sin(th) * ridge))
            streak = 0.5 + 0.5 * np.sin(4 * th + streak_ph[0]) * np.sin(7 * th + streak_ph[1] + t[i] * 4)
            col = cols(t[i]) * (0.92 + 0.1 * streak) * (0.94 + 0.06 * ridge)
            col[3] = 1.0
            C.append(col)
    F = grid_faces(m, ring, wrap_v=True)
    V.append(c[0] - T_[0] * 0.01)
    C.append(cols(0.0))
    cb = len(V) - 1
    for k in range(ring):
        F.append((cb, (k + 1) % ring, k))
    return np.array(V), F, np.array(C)


def hair_colours(kind, seed):
    rng = np.random.default_rng(seed)
    peach_at = rng.uniform(0.42, 0.62)
    peach = rng.uniform(0.1, 0.45)
    tip = HAIR_LILAC if rng.random() < 0.6 else HAIR_VIOLET

    def f(t):
        c = mix(HAIR_ROOT, HAIR_PINK, smooth(0.0, 0.25, t))
        c = mix(c, HAIR_PEACH, smooth(peach_at - 0.2, peach_at, t) * (1 - smooth(peach_at + 0.12, peach_at + 0.3, t)) * peach)
        c = mix(c, tip, smooth(0.7, 1.0, t) * (0.85 if kind != "tail" else 1.0))
        return c.copy()
    return f


def crest_points(n):
    """the mane's roots: along the top of the neck from the poll (between the ears) to the withers, on the surface"""
    pts = []
    c, r = U.CRANIUM
    poll = U.head_to_world(U._ray_hit(U._head_raw, c, np.array([-0.62, 0.0, 0.78])))
    wither = U._ray_hit(U.sdf_uncarved, np.array([0.2, 0.0, 2.5]), np.array([-0.2, 0.0, 1.0]))
    mid = U._ray_hit(U.sdf_uncarved, np.array([0.98, 0.0, 3.4]), np.array([-0.86, 0.0, 0.5]))
    for s in np.linspace(0, 1, n):
        q = (1 - s) ** 2 * poll + 2 * s * (1 - s) * mid + s * s * wither
        pts.append(q)
    P = U.project(obstacles, np.array(pts), 4)
    return P


def build_hair():
    mat = material("hair", rough=0.36, sss=0.12, sheen=0.55, spec=0.45)
    seed = [100]

    def emit(curves, widths, kind, thick=0.36, layer=0, **shape):
        if HAIR_STYLE == "v2":
            return emit_v2(curves, widths, kind, thick, layer, shape, seed)
        for i, c in enumerate(curves):
            seed[0] += 1
            rng = np.random.default_rng(seed[0])
            cc = resample(c, 70)
            cc = shape_lock(cc, wave=shape.get("wave", 0.07) * rng.uniform(0.6, 1.3), freq=rng.uniform(0.8, 1.5),
                            phase=rng.uniform(0, 6.28), curl=shape.get("curl", [0])[i % len(shape.get("curl", [0]))],
                            curl_r=shape.get("curl_r", 0.13), curl_from=shape.get("curl_from", 0.8))
            V, F, C = lock_mesh(cc, widths[i], thick, cols=hair_colours(kind, seed[0]), seed=seed[0])
            add_mesh(kind, V, F, C, mat)

    # the near side of the mane: locks from the crest, falling over the neck and down past the shoulder
    crest = crest_points(22)
    rng = np.random.default_rng(11)
    roots = crest + np.array([0.0, 0.04, 0.03])
    dirs = np.tile(np.array([-0.2, 1.0, 0.7]), (len(roots), 1)) + rng.normal(0, 0.08, (len(roots), 3))
    lens = np.linspace(2.5, 2.1, len(roots)) * rng.uniform(0.9, 1.1, len(roots))
    curves = drape(roots, dirs, lens, gravity=2.1, drift=np.array([-0.2, 0.3, 0.0]), clear=0.07)
    emit(curves, np.linspace(0.34, 0.3, len(roots)) * rng.uniform(0.9, 1.1, len(roots)), "mane", thick=0.3,
         curl=[0.4, 0.0, 0.0, 0.5, 0.0, 0.0, 0.0], curl_r=0.34, curl_from=0.74, wave=0.06)
    # a second, outer layer over the near side for volume
    roots2 = crest[1::2] + np.array([0.0, 0.1, 0.08])
    curves = drape(roots2, np.tile(np.array([-0.05, 1.0, 1.0]), (len(roots2), 1)), np.linspace(2.0, 1.7, len(roots2)), gravity=1.9,
                   drift=np.array([-0.35, 0.4, 0.0]), clear=0.15)
    emit(curves, np.full(len(roots2), 0.32), "mane", thick=0.3, layer=1, curl=[0.0, 0.45, 0.0, 0.0], curl_r=0.32, curl_from=0.72, wave=0.07)
    # the far side
    roots3 = crest[::2] + np.array([0.0, -0.04, 0.03])
    curves = drape(roots3, np.tile(np.array([-0.15, -1.0, 0.6]), (len(roots3), 1)), np.linspace(2.3, 1.9, len(roots3)), gravity=2.1,
                   drift=np.array([-0.2, -0.3, 0.0]), clear=0.07)
    emit(curves, np.full(len(roots3), 0.34), "mane", thick=0.3, layer=-1, curl=[0.0, 0.5, 0.0], curl_r=0.3, curl_from=0.72, wave=0.06)

    # the forelock: from the crown behind the horn, sweeping forward over the far side of the forehead to the cheek
    c, r = U.CRANIUM
    fl = []
    for k, (dx, dy) in enumerate(((0.12, 0.05), (0.0, -0.14), (-0.1, 0.12), (0.05, -0.3), (-0.16, -0.06), (0.15, -0.22))):
        L = U._ray_hit(U._head_raw, c, np.array([0.1 + dx, dy, 1.0]))
        fl.append(U.head_to_world(L))
    fl = np.array(fl)
    fdirs = np.array([U.head_dir(np.array(v)) for v in ((0.9, -0.5, 0.6), (0.8, -0.8, 0.5), (0.7, -0.6, 0.8), (0.6, -1.0, 0.4),
                                                        (0.3, -0.9, 0.7), (0.9, -0.9, 0.4))])
    curves = drape(fl, fdirs, [1.7, 1.8, 1.6, 1.5, 1.7, 1.55], gravity=2.3, drift=np.array([0.05, -0.2, 0.0]), clear=0.06, stiff=0.3)
    emit(curves, [0.27, 0.29, 0.25, 0.24, 0.27, 0.24], "forelock", thick=0.3, curl=[0.0, 0.0, 0.0, 0.0, 0.35, 0.0], curl_r=0.28, curl_from=0.74)
    # two locks over the near temple, behind the eye, falling to the jaw
    nl = np.array([U.head_to_world(U._ray_hit(U._head_raw, c, np.array([v[0], v[1], 1.0]))) for v in ((0.02, 0.3), (-0.15, 0.38))])
    ndirs = np.array([U.head_dir(np.array(v)) for v in ((-0.2, 1.0, 0.5), (-0.4, 1.0, 0.4))])
    curves = drape(nl, ndirs, [1.3, 1.5], gravity=2.5, drift=np.array([-0.45, 0.2, 0.0]), clear=0.06)
    emit(curves, [0.24, 0.26], "forelock", thick=0.3, layer=1, curl=[0.3, 0.0], curl_r=0.22, curl_from=0.74)

    # the tail: from the top of the rump, a little up and back, then falling in a long soft S, the tips curling out
    base = U._ray_hit(U.sdf_uncarved, np.array([-0.5, 0.0, 2.6]), np.array([-1.0, 0.0, 0.42]))
    rng = np.random.default_rng(5)
    n = 22
    troots = base + np.stack([rng.uniform(-0.06, 0.04, n), rng.uniform(-0.14, 0.14, n), rng.uniform(-0.06, 0.08, n)], 1)
    tdirs = np.stack([np.full(n, -1.0), rng.uniform(-0.2, 0.35, n), rng.uniform(0.2, 0.55, n)], 1)
    curves = drape(troots, tdirs, rng.uniform(2.6, 3.2, n), gravity=2.7, drift=np.array([-0.35, 0.15, 0.0]), clear=0.07, stiff=0.18)
    emit(curves, rng.uniform(0.3, 0.38, n), "tail", thick=0.3, wave=0.1, curl=[0.55, 0.0, 0.4, 0.6, 0.0, 0.0], curl_r=0.36, curl_from=0.72)


# ------------------------------------------------------------------ flowers, leaves and roses
PET_PEACH = hexc("#ffd9b8")
PET_PEACH_EDGE = hexc("#fff0e4")
PET_CORE = hexc("#ffc394")
PET_PINK = hexc("#f6b2d2")
PET_PINK_EDGE = hexc("#fde0ee")
PET_PINK_CORE = hexc("#e690bf")
CENTRE = hexc("#ffcf5c")
STAMEN = hexc("#e08a3c")
LEAF = hexc("#a9d79b")
LEAF_EDGE = hexc("#dff0d2")
LEAF_RIB = hexc("#8cc386")


def frame(n):
    n = np.asarray(n, np.float64) / np.linalg.norm(n)
    a = np.cross(n, [0.0, 0.0, 1.0]) if abs(n[2]) < 0.9 else np.cross(n, [1.0, 0.0, 0.0])
    a /= np.linalg.norm(a)
    return a, np.cross(n, a), n


def petal(L, W, cup=0.25, lift=0.2, nu=12, nv=9, col_base=None, col_edge=None, col_tip=None, notch=0.0, pointed=False):
    """one petal in its own frame: x out along the petal, y across, z up; cupped across, the tip lifting"""
    V, C = [], []
    for i in range(nu):
        u = i / (nu - 1)
        if pointed:
            w = W * np.sin(np.pi * u) ** 0.9 * (1 - 0.3 * u)
        else:
            w = W * np.sqrt(max(0.0, 1 - ((u - 0.56) / 0.56) ** 2)) * (0.35 + 0.65 * smooth(0.0, 0.4, u))
        for j in range(nv):
            v = -1 + 2 * j / (nv - 1)
            x = u * L - notch * L * 0.08 * (1 - v * v) * smooth(0.8, 1.0, u)
            z = cup * w * v * v + lift * L * u * u
            V.append((x, v * w, z))
            c = mix(col_base, col_edge, smooth(0.35, 1.0, u) * 0.8 + 0.2 * abs(v))
            if col_tip is not None:
                c = mix(c, col_tip, smooth(0.75, 1.0, u) * 0.5)
            C.append(c)
    return np.array(V), grid_faces(nu, nv), np.array(C)


def place_local(V, origin, a, b, n, yaw=0.0, tilt=0.0):
    """petal space (x out, y across, z up) -> world, turned about the flower's axis and tilted up from its plane"""
    cy, sy = np.cos(yaw), np.sin(yaw)
    ct, st = np.cos(tilt), np.sin(tilt)
    x, y, z = V[:, 0], V[:, 1], V[:, 2]
    x2 = x * ct - z * st
    z2 = x * st + z * ct
    dirx = a * cy + b * sy
    diry = -a * sy + b * cy
    return origin + np.outer(x2, dirx) + np.outer(y, diry) + np.outer(z2, n)


class Bouquet:
    """collects petals and leaves into a few meshes (one material each)"""

    def __init__(self):
        self.parts = {"petal": [], "leaf": [], "centre": []}

    def add(self, kind, V, F, C):
        self.parts[kind].append((V, F, C))

    def build(self, tag):
        mats = {"petal": material("petal", rough=0.45, sss=0.08, sheen=0.4, spec=0.3),
                "leaf": material("leaf", rough=0.5, sss=0.2, sheen=0.2, spec=0.3),
                "centre": material("centre", rough=0.55, spec=0.3)}
        for kind, items in self.parts.items():
            if not items:
                continue
            Vs, Fs, Cs, base = [], [], [], 0
            for V, F, C in items:
                Vs.append(V)
                Fs += [(f[0] + base, f[1] + base, f[2] + base) for f in F]
                Cs.append(C)
                base += len(V)
            add_mesh(tag + "_" + kind, np.vstack(Vs), Fs, np.vstack(Cs), mats[kind])


def flower(bq, c, n, R, petals=6, colours=None, layers=2, rot=0.0):
    base, edge, core = colours or (PET_PEACH, PET_PEACH_EDGE, PET_CORE)
    a, b, n = frame(n)
    for layer in range(layers):
        k = petals if layer == 0 else petals
        for i in range(k):
            yaw = rot + 2 * np.pi * (i + 0.5 * layer) / k + rnd.uniform(-0.12, 0.12)
            L = R * (1.0 if layer == 0 else 0.6) * rnd.uniform(0.94, 1.05)
            V, F, C = petal(L, L * 0.6, cup=0.18, lift=0.1 + 0.2 * layer, col_base=core, col_edge=edge, col_tip=base, notch=1.0)
            W = place_local(V, c + n * (0.015 * layer), a, b, n, yaw, np.radians(6 + 18 * layer))
            bq.add("petal", W, F, C)
    # the centre: a little dome with stamens
    Vd, Fd = uv_sphere(np.zeros(3), R * 0.22, 16, 10)
    Vd[:, 2] *= 0.55
    Wd = c + n * (R * 0.06) + np.outer(Vd[:, 0], a) + np.outer(Vd[:, 1], b) + np.outer(Vd[:, 2], n)
    bq.add("centre", Wd, Fd, np.tile(CENTRE, (len(Wd), 1)))
    for i in range(14):
        ang = rnd.uniform(0, 2 * np.pi)
        rr = R * rnd.uniform(0.08, 0.2)
        p = c + n * (R * 0.16) + (a * np.cos(ang) + b * np.sin(ang)) * rr
        Vs_, Fs_ = uv_sphere(p, R * 0.028, 6, 4)
        bq.add("centre", Vs_, Fs_, np.tile(STAMEN, (len(Vs_), 1)))


def leaf(bq, c, n, direction, L, W, twist=0.0):
    a, b, n = frame(n)
    d = np.asarray(direction, np.float64)
    d -= n * (d @ n)
    d /= np.linalg.norm(d)
    yaw = np.arctan2(d @ b, d @ a)
    V, F, C = petal(L, W, cup=0.15, lift=-0.05, col_base=LEAF, col_edge=LEAF_EDGE, pointed=True)
    # a darker midrib
    nv = 9
    for i in range(len(C)):
        if i % nv == nv // 2:
            C[i] = mix(C[i], LEAF_RIB, 0.7)
    bq.add("leaf", place_local(V, c, a, b, n, yaw, np.radians(8 + twist)), F, C)


def rose(bq, c, n, R, colours=None):
    base, edge, core = colours or (PET_PINK, PET_PINK_EDGE, PET_PINK_CORE)
    a, b, n = frame(n)
    k = 11
    for i in range(k):
        q = i / (k - 1)
        yaw = i * np.radians(137.5)
        L = R * (0.35 + 0.65 * q)
        tilt = np.radians(75 - 55 * q)                         # the inner petals stand up, the outer ones open
        V, F, C = petal(L, L * 0.7, cup=0.6 - 0.3 * q, lift=0.1, col_base=mix(core, base, q), col_edge=edge)
        bq.add("petal", place_local(V, c + n * (R * 0.25 * (1 - q)), a, b, n, yaw, tilt), F, C)


def surface_at(fn, o, d):
    p = U._ray_hit(fn, o, d)
    return p, U.grad(fn, p[None])[0]


def build_flowers():
    rnd.seed(3)
    # the crown: a big peach flower on top of the head on the near side, by the horn, with leaves and a pink bud
    c, r = U.CRANIUM
    L, nL = surface_at(U._head_raw, c, np.array([0.42, 0.42, 0.8]))
    top = U.head_to_world(L + nL * 0.22)
    tn = U.head_dir(nL + np.array([0.15, 0.25, 0.25]))
    bq = Bouquet()
    flower(bq, top, tn, 0.58, petals=6, colours=(hexc("#ffc9c0"), PET_PEACH_EDGE, PET_CORE))
    for ang, ln in ((2.2, 0.36), (3.4, 0.3), (-0.6, 0.32)):
        a_, b_, n_ = frame(tn)
        dirn = a_ * np.cos(ang) + b_ * np.sin(ang)
        leaf(bq, top - tn * 0.03 + dirn * 0.3, tn, dirn, ln * 1.3, ln * 0.55, twist=10)
    a_, b_, n_ = frame(tn)
    rose(bq, top + (a_ * np.cos(1.0) + b_ * np.sin(1.0)) * 0.55 - tn * 0.04, tn, 0.2)
    bq.build("crown")
    # the garland on the hip: a peach flower between two pink ones, with buds and leaves along the back
    bq = Bouquet()
    spots = [((-0.5, 0.0, 2.45), (0.0, 0.62, 0.8), 0.52, "peach"), ((-0.12, 0.0, 2.45), (0.05, 0.55, 0.85), 0.4, "pink"),
             ((-0.88, 0.0, 2.5), (-0.1, 0.62, 0.8), 0.4, "pink")]
    for o, d, R, kind in spots:
        p, nn = surface_at(U.sdf_uncarved, np.array(o), np.array(d))
        p = p + nn * 0.1
        nn = nn + np.array([0.0, 0.35, 0.1])
        if kind == "peach":
            flower(bq, p, nn, R, petals=6, colours=(hexc("#ffc9c0"), PET_PEACH_EDGE, PET_CORE))
        else:
            flower(bq, p, nn, R, petals=5, colours=(PET_PINK, PET_PINK_EDGE, PET_PINK_CORE), rot=0.4)
    for o, d in (((-0.3, 0.0, 2.4), (0.1, 0.7, 0.7)), ((-0.68, 0.0, 2.45), (-0.05, 0.7, 0.72)), ((-1.0, 0.0, 2.45), (-0.4, 0.6, 0.7))):
        p, nn = surface_at(U.sdf_uncarved, np.array(o), np.array(d))
        rose(bq, p + nn * 0.1, nn + np.array([0, 0.3, 0]), 0.17)
    for o, d, dirn in (((-0.05, 0.0, 2.4), (0.15, 0.55, 0.8), (1.0, 0.2, -0.3)), ((-0.6, 0.0, 2.4), (0.0, 0.85, 0.5), (0.1, 0.3, -1.0)),
                       ((-1.1, 0.0, 2.45), (-0.5, 0.5, 0.7), (-1.0, 0.2, -0.4)), ((-0.35, 0.0, 2.45), (0.0, 0.45, 0.9), (0.4, -0.2, 0.6)),
                       ((-0.8, 0.0, 2.45), (-0.1, 0.8, 0.55), (-0.5, 0.4, -0.8))):
        p, nn = surface_at(U.sdf_uncarved, np.array(o), np.array(d))
        leaf(bq, p + nn * 0.07, nn, np.array(dirn), 0.44, 0.19, twist=5)
    bq.build("garland")
    # rose cuffs above the hooves
    bq = Bouquet()
    for name, j in U.LEGS.items():
        (f, rf), (ht, rh) = j[-2], j[-1]
        f = np.array(f)
        d = np.array(ht) - np.array(j[-3][0])
        d /= np.linalg.norm(d)
        a_, b_, _ = frame(d)
        for k in range(8):
            ang = 2 * np.pi * k / 8 + rnd.uniform(-0.1, 0.1)
            out = a_ * np.cos(ang) + b_ * np.sin(ang)
            p = f - d * 0.03 + out * (rf + 0.05)
            rose(bq, p, out + d * -0.1, 0.13, colours=(hexc("#f8bcd8"), hexc("#fde6f1"), hexc("#ec9cc6")))
            if k % 2 == 0:
                leaf(bq, p + d * 0.06, out, d, 0.16, 0.07)
    bq.build("cuffs")


# ------------------------------------------------------------------ freckles and glitter
def disc(c, n, r, seg=12):
    a, b, n = frame(n)
    V = [c] + [c + (a * np.cos(2 * np.pi * k / seg) + b * np.sin(2 * np.pi * k / seg)) * r for k in range(seg)]
    F = [(0, k + 1, (k + 1) % seg + 1) for k in range(seg)]
    return np.array(V), F


def build_sparkle(body_ob):
    rng = np.random.default_rng(9)
    Vs, Fs, base = [], [], 0
    # freckles: white dots on the cheek, below and behind the eye
    E, n, u, v = U.EYES[1]
    for k in range(7):
        p = E - u * rng.uniform(0.15, 0.55) - v * rng.uniform(0.3, 0.62)
        P = head_surface(p[None], 0.006)[0]
        nn = U.grad(U._head_raw, P[None])[0]
        V, F = disc(P, nn, rng.uniform(0.022, 0.046))
        Vs.append(U.head_to_world(V))
        Fs += [(f[0] + base, f[1] + base, f[2] + base) for f in F]
        base += len(V)
    add_mesh("freckles", np.vstack(Vs), Fs, None, material("freckle", rough=0.4, emit=0.5, color=(1, 1, 1, 1)))
    # glitter over the near side of the body and legs
    me = body_ob.data
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get("co", co)
    co = co.reshape(-1, 3)
    N = U.grad(U.sdf, co[::7])
    co = co[::7]
    keep = (N[:, 1] > 0.15) & (co[:, 2] < 3.3) & (co[:, 2] > 0.6)
    co, N = co[keep], N[keep]
    pick = rng.choice(len(co), min(70, len(co)), replace=False)
    Vs, Fs, base = [], [], 0
    for i in pick:
        V, F = disc(co[i] + N[i] * 0.004, N[i], rng.uniform(0.006, 0.013), 8)
        Vs.append(V)
        Fs += [(f[0] + base, f[1] + base, f[2] + base) for f in F]
        base += len(V)
    add_mesh("glitter", np.vstack(Vs), Fs, None, material("glitter", rough=0.2, emit=1.2, color=(1, 1, 1, 1)))


# ------------------------------------------------------------------ hair v2
HAIR_TRIS = [0]


def frames(c):
    """tangent, outward normal (away from the body, kept from flipping and smoothed) and binormal along a centre line"""
    T_ = np.gradient(c, axis=0)
    T_ /= np.maximum(np.linalg.norm(T_, axis=1, keepdims=True), 1e-9)
    out = U.grad(obstacles, c)
    N = out - T_ * np.sum(out * T_, 1, keepdims=True)
    for i in range(1, len(c)):
        if N[i] @ N[i - 1] < 0:
            N[i] = -N[i]
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
    for _ in range(4):
        N[1:-1] = (N[:-2] + 2 * N[1:-1] + N[2:]) / 4
        N -= T_ * np.sum(N * T_, 1, keepdims=True)
        N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-9)
    return T_, N, np.cross(T_, N)


def smooth_line(c, passes=6):
    c = c.copy()
    for _ in range(passes):
        c[1:-1] = (c[:-2] + 2 * c[1:-1] + c[2:]) / 4
    return c


def strand_mesh(c, w, thick, cols, ring, shade):
    """a flattened tube along c with width w (per point); also the data the strand shader needs per vertex:
    Tan = along the hair, Hst = (cos, sin round the lock, place along it)"""
    T_, N, B = frames(c)
    m = len(c)
    t = np.linspace(0, 1, m)
    V, C, TA, HS = [], [], [], []
    for i in range(m):
        for k in range(ring):
            th = 2 * np.pi * k / ring
            V.append(c[i] + B[i] * (w[i] * np.cos(th)) + N[i] * (w[i] * thick * np.sin(th)))
            col = cols(t[i]) * shade
            col[3] = 1.0
            C.append(col)
            TA.append(T_[i])
            HS.append((np.cos(th), np.sin(th), t[i]))
    F = grid_faces(m, ring, wrap_v=True)
    V.append(c[0] - T_[0] * 0.01)
    C.append(cols(0.0) * shade)
    C[-1][3] = 1.0
    TA.append(T_[0])
    HS.append((0.0, 0.0, 0.0))
    cb = len(V) - 1
    for k in range(ring):
        F.append((cb, (k + 1) % ring, k))
    return np.array(V), F, np.array(C), np.array(TA), np.array(HS)


def taper(m, tip_from=0.5, swell=0.25):
    t = np.linspace(0, 1, m)
    return (1 + swell * np.sin(np.pi * np.minimum(1.0, t * 1.6))) * (1 - smooth(tip_from, 1.0, t) ** 0.85) + 0.012


def emit_v2(curves, widths, kind, thick, layer, shape, seed):
    """each lock: a smoothed, combed centre line; toward its end it splits into sub-locks that fan apart and end in
    fine wisps; a couple of stray strands drift off its edges"""
    mat = hair_material_v2()
    shade = {1: 1.05, 0: 1.0, -1: 0.86}[layer]
    curls = shape.get("curl", [0])
    parts = []
    n = len(curves)
    for i, c in enumerate(curves):
        seed[0] += 1
        rng = np.random.default_rng(seed[0])
        cc = resample(c, 80)
        # neighbours wave together, as combed hair does
        cc = shape_lock(cc, wave=shape.get("wave", 0.07) * 0.8, freq=1.05, phase=1.6 * i / max(n - 1, 1),
                        curl=curls[i % len(curls)] * 0.75, curl_r=shape.get("curl_r", 0.3) * 1.25, curl_from=shape.get("curl_from", 0.74))
        cc = smooth_line(cc)
        T_, N, B = frames(cc)
        W = widths[i]
        cols = hair_colours(kind, seed[0])
        t = np.linspace(0, 1, len(cc))
        k_sub = 3 if W > 0.26 else 2
        split = rng.uniform(0.42, 0.55)
        fan = smooth(split, 1.0, t)
        for j in range(k_sub):
            side = (j - (k_sub - 1) / 2) / max((k_sub - 1) / 2, 1)
            off = side * W * 0.42 * (0.35 + 0.65 * fan)               # side by side, then spreading apart
            lift = rng.uniform(-0.3, 0.3) * W * fan
            sub = cc + B * off[:, None] + N * lift[:, None]
            ln = rng.uniform(0.82, 1.0) if j != (k_sub // 2) else 1.0
            mm = max(8, int(len(sub) * ln))
            ns, rs = (24, 7) if GAME_LOD else (64, 16)
            sub = resample(sub[:mm], ns)
            w = W * (0.58 if k_sub == 3 else 0.7) * taper(ns, tip_from=rng.uniform(0.35, 0.55))
            parts.append(strand_mesh(sub, w, thick * 0.9, cols, rs, shade * rng.uniform(0.95, 1.04)))
        # a body under the split, so the lock reads as one near its root
        nc, rc = (14, 8) if GAME_LOD else (40, 18)
        core = resample(cc[: int(len(cc) * (split + 0.2))], nc)
        w = W * 0.85 * taper(nc, tip_from=0.6, swell=0.15)
        parts.append(strand_mesh(core, w, thick, cols, rc, shade * 0.97))
        # stray strands off the edges
        for j in range(0 if kind == "forelock" else 1):
            side = rng.choice([-1, 1])
            st = cc + B * (side * W * rng.uniform(0.45, 0.65) * (0.4 + 0.6 * fan))[:, None]
            st = st + N * (W * 0.25 * np.sin(np.pi * t * rng.uniform(1.0, 2.0)) * fan)[:, None]
            a0 = int(len(st) * rng.uniform(0.2, 0.4))
            nst, rst = (10, 4) if GAME_LOD else (30, 6)
            st = resample(st[a0: int(len(st) * rng.uniform(0.85, 1.0))], nst)
            parts.append(strand_mesh(st, np.full(nst, 0.014) * taper(nst, 0.4, 0.0), 1.0, cols, rst, shade * 1.06))
    Vs, Fs, Cs, Ts, Hs, base = [], [], [], [], [], 0
    for V, F, C, TA, HS in parts:
        Vs.append(V)
        Fs += [(f[0] + base, f[1] + base, f[2] + base) for f in F]
        Cs.append(C)
        Ts.append(TA)
        Hs.append(HS)
        base += len(V)
    HAIR_TRIS[0] += len(Fs)
    add_mesh(kind, np.vstack(Vs), Fs, np.vstack(Cs), mat, attrs={"Tan": np.vstack(Ts), "Hst": np.vstack(Hs)})


def hair_material_v2():
    """the strand shader: anisotropic shine along the hair (the tangent attribute), fine lengthwise streaks and grooves
    from noise stretched along it (Hst), lighter tips, a little light through the thin edges. All of it is per-vertex
    data plus per-pixel noise, which a game shader can do as well."""
    if "hair2" in MATS:
        return MATS["hair2"]
    m = bpy.data.materials.new("hair2")
    m.use_nodes = True
    nt = m.node_tree
    nd, ln = nt.nodes, nt.links
    bs = nd["Principled BSDF"]
    col = nd.new("ShaderNodeAttribute"); col.attribute_name = "Col"
    tan = nd.new("ShaderNodeAttribute"); tan.attribute_name = "Tan"
    hst = nd.new("ShaderNodeAttribute"); hst.attribute_name = "Hst"
    # streak coordinates: many strands round the lock, few changes along it
    sep = nd.new("ShaderNodeSeparateXYZ")
    ln.new(hst.outputs["Vector"], sep.inputs[0])
    comb = nd.new("ShaderNodeCombineXYZ")
    for i, (ax, k) in enumerate((("X", 7.0), ("Y", 7.0), ("Z", 1.2))):
        mul = nd.new("ShaderNodeMath"); mul.operation = "MULTIPLY"; mul.inputs[1].default_value = k
        ln.new(sep.outputs[ax], mul.inputs[0])
        ln.new(mul.outputs[0], comb.inputs[i])
    fine = nd.new("ShaderNodeTexNoise"); fine.inputs["Scale"].default_value = 6.0; fine.inputs["Detail"].default_value = 3.0
    ln.new(comb.outputs[0], fine.inputs["Vector"])
    broad = nd.new("ShaderNodeTexNoise"); broad.inputs["Scale"].default_value = 1.6; broad.inputs["Detail"].default_value = 1.0
    ln.new(comb.outputs[0], broad.inputs["Vector"])
    # colour: the vertex colour, brightened and darkened in streaks
    ramp = nd.new("ShaderNodeMapRange")
    ramp.inputs["From Min"].default_value = 0.3; ramp.inputs["From Max"].default_value = 0.7
    ramp.inputs["To Min"].default_value = 0.9; ramp.inputs["To Max"].default_value = 1.12
    ln.new(fine.outputs["Fac"], ramp.inputs["Value"])
    ramp2 = nd.new("ShaderNodeMapRange")
    ramp2.inputs["From Min"].default_value = 0.3; ramp2.inputs["From Max"].default_value = 0.7
    ramp2.inputs["To Min"].default_value = 0.93; ramp2.inputs["To Max"].default_value = 1.06
    ln.new(broad.outputs["Fac"], ramp2.inputs["Value"])
    m1 = nd.new("ShaderNodeVectorMath"); m1.operation = "SCALE"
    ln.new(col.outputs["Color"], m1.inputs[0]); ln.new(ramp.outputs[0], m1.inputs["Scale"])
    m2 = nd.new("ShaderNodeVectorMath"); m2.operation = "SCALE"
    ln.new(m1.outputs[0], m2.inputs[0]); ln.new(ramp2.outputs[0], m2.inputs["Scale"])
    ln.new(m2.outputs[0], bs.inputs["Base Color"])
    # grooves between strands
    bump = nd.new("ShaderNodeBump"); bump.inputs["Strength"].default_value = 0.35; bump.inputs["Distance"].default_value = 0.02
    ln.new(fine.outputs["Fac"], bump.inputs["Height"])
    ln.new(bump.outputs["Normal"], bs.inputs["Normal"])
    # the shine runs along the hair
    ln.new(tan.outputs["Vector"], bs.inputs["Tangent"])
    bs.inputs["Anisotropic"].default_value = 0.85
    bs.inputs["Roughness"].default_value = 0.33
    bs.inputs["Specular IOR Level"].default_value = 0.55
    bs.inputs["Sheen Weight"].default_value = 0.45
    bs.inputs["Coat Weight"].default_value = 0.15
    bs.inputs["Subsurface Weight"].default_value = 0.22
    bs.inputs["Subsurface Radius"].default_value = (0.6, 0.35, 0.45)
    bs.inputs["Subsurface Scale"].default_value = 0.05
    MATS["hair2"] = m
    return m


# ------------------------------------------------------------------ lights and cameras
def lights():
    def area(name, loc, target, size, energy, col):
        L = bpy.data.lights.new(name, "AREA")
        L.size = size
        L.energy = energy
        L.color = col
        ob = bpy.data.objects.new(name, L)
        bpy.context.collection.objects.link(ob)
        ob.location = loc
        d = Vector(target) - Vector(loc)
        ob.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
    area("key", (6, 9, 11), (0.6, 0, 3.4), 7, 1100, (1.0, 0.97, 0.94))
    area("fill", (8, -6, 5), (0.6, 0, 3.4), 9, 260, (0.92, 0.95, 1.0))
    area("rim", (-7, -3, 8), (0.6, 0, 3.6), 5, 700, (1.0, 0.93, 1.0))
    area("bounce", (2, 4, -3), (0.6, 0, 2.0), 8, 100, (1.0, 0.95, 0.98))


VIEWS_AT = {
    # azimuth from +y (the near side) toward the front (+x), elevation, focus, ortho size
    "hero": (32.0, 6.0, (0.6, 0.0, 3.4), 8.0),
    "side": (0.0, 3.0, (0.45, 0.0, 3.5), 8.6),
    "front": (88.0, 4.0, (0.9, 0.0, 3.5), 8.0),
    "back": (200.0, 8.0, (0.2, 0.0, 3.5), 8.6),
    "head": (36.0, 4.0, (1.85, 0.0, 4.9), 3.6),
}


def camera(view):
    az, el, focus, size = VIEWS_AT[view]
    cam = bpy.data.cameras.new("cam")
    cam.type = "ORTHO"
    cam.ortho_scale = size
    ob = bpy.data.objects.new("cam", cam)
    bpy.context.collection.objects.link(ob)
    a, e = math.radians(az), math.radians(el)
    d = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    ob.location = Vector(focus) + d * 40
    ob.rotation_euler = (-d).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.camera = ob
    return ob


def main():
    sc = setup()
    body = build_body()
    build_eyes()
    build_ears()
    build_horn()
    build_hooves()
    build_hair()
    if HAIR_STYLE == "v2":
        print("hair v2: %d triangles" % HAIR_TRIS[0])
    build_flowers()
    build_sparkle(body)
    lights()
    res = 520 if QUICK else 1300
    sc.render.resolution_x = res
    sc.render.resolution_y = res
    for v in VIEWS:
        cam = camera(v)
        sc.render.filepath = os.path.join(OUT, v + ".png")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam)
        print("rendered", v)


main()
