"""The meadow rendered in 3D, so the scene matches the live 3D creatures (round 37). Made from code only, like the
creatures: Blender builds the meadow (a soft green rise with grass and pastel flowers, a sandy path, green hills along
its far edge, hazy lilac hills beyond, a pastel sky) and the props a child touches, and renders them with the same light
as the creatures (the game's creature lights: from the left, above and in front).

The camera reproduces the 2D meadow's layout exactly, so nothing in the game moves: a long lens, about 20 model units
up and tilted down about 6 degrees (the creatures' own camera is tilted 9), placed so a creature's size at the front and
the back of the walkable ground (Creature.GROUND, scale 1.12 to 0.86) is what perspective gives there. World
coordinates are the game's meadow pixels (1x; the pictures are made at 2x for Retina screens).

Each picture keeps the canvas and origin of the drawing it replaces (game/art/meadow/*.svg), so the game only loads a
different file:  meadow.png (x -512..1536, y -128..896), tree.png, nest_back.png, nest_front.png, egg.png,
lantern.png, sign.png, basket.png. The props cast their shadows into the backdrop but are drawn separately (the game
sorts them with the creatures). The things that move (apple.png and the things to wear in the basket, wear_crown.png,
wear_scarf.png, wear_bow.png) are made where they first sit, centred on their own point, without shadows, and with no
grass round them.

Run:  blender -b --factory-startup -P meadow3d.py -- OUT_DIR [--quick] [part ...]
      parts: backdrop tree nest egg lantern sign basket wear apple (default: all)      --quick  fewer grass blades, half size"""
import os, sys, math, json, time
import bpy
import numpy as np
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = os.path.abspath(argv[0] if argv else "meadow3d_out")
QUICK = "--quick" in argv
PARTS = [a for a in argv[1:] if not a.startswith("--")] or ["backdrop", "tree", "nest", "egg", "lantern", "sign", "basket", "wear", "apple"]
sys.argv = [sys.argv[0], "--", "unused", "--quick"]          # collie_d.py (shared helpers) reads its options from here
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collie_d as D
Ub = D.Ub
hexc, mix, smooth, unit, log = D.hexc, D.mix, D.smooth, D.unit, D.log
rng = np.random.default_rng(37)

# ================================================================== the camera that reproduces the meadow's layout
F = 5000.0                                                    # focal length, world pixels
X0, Y0, WPX, HPX = -512.0, -128.0, 3584.0, 1024.0             # the whole picture (meadow and pond) in world pixels
CX, CY = X0 + WPX / 2, Y0 + HPX / 2
S_FRONT, S_BACK, Y_FRONT, Y_BACK = 44.8, 34.4, 730.0, 525.0   # px per model unit at the walkable ground's front and back


def _solve():
    zc1, zc2 = F / S_FRONT, F / S_BACK
    a1, a2 = (Y_FRONT - CY) * zc1 / F, (Y_BACK - CY) * zc2 / F
    th = math.atan2(a1 - a2, zc2 - zc1)
    return th, a1 * math.cos(th) + zc1 * math.sin(th)


TH, CAM_H = _solve()
CAM = np.array([0.0, 0.0, CAM_H])
FWD = np.array([0.0, math.cos(TH), -math.sin(TH)])
RIGHT = np.array([1.0, 0.0, 0.0])
UPV = np.array([0.0, math.sin(TH), math.cos(TH)])


def project(P):
    """3D points to world pixels (x, y), and pixels per model unit there"""
    q = np.atleast_2d(P) - CAM
    zc = q @ FWD
    return np.stack([CX + F * (q @ RIGHT) / zc, CY - F * (q @ UPV) / zc], 1), F / zc


def ground_ray(X, Y, z=0.0):
    """the point at height z under world pixel (X, Y)"""
    X, Y = np.atleast_1d(X).astype(float), np.atleast_1d(Y).astype(float)
    d = FWD[None] + RIGHT[None] * ((X - CX) / F)[:, None] - UPV[None] * ((Y - CY) / F)[:, None]
    t = (z - CAM_H) / d[:, 2]
    return CAM[None] + d * t[:, None]


def on_ground(X, Y):
    """the point on the terrain under world pixel (X, Y) (a few steps: the ground is not quite flat)"""
    P = ground_ray(X, Y)
    for _ in range(4):
        P = ground_ray(X, Y, height(P[:, 0], P[:, 1]))
    P[:, 2] = height(P[:, 0], P[:, 1])
    return P


# ================================================================== the land
G_EDGE = 170.0                                                # where the meadow falls away behind its low hills


def noise(x, y, scale, seed, octaves=3):
    r = np.random.default_rng(seed)
    out = np.zeros_like(x, dtype=float)
    amp = 1.0
    for _ in range(octaves):
        for _ in range(3):
            k = r.normal(0, 1, 2)
            k = k / np.linalg.norm(k) * (2 * np.pi / scale) * r.uniform(0.7, 1.3)
            out += amp * np.sin(x * k[0] + y * k[1] + r.uniform(0, 6.3))
        amp *= 0.5
        scale *= 0.5
    return out / 3.5


def height(x, g):
    """the meadow: nearly flat where creatures walk, a soft rise toward the back, green hills along the far edge, then
    falling away (so the sky and the far hills show above it, as in the painted meadow)"""
    x, g = np.asarray(x, float), np.asarray(g, float)
    # (with this low camera the flat ground at depth 157 is at the painted floor's top, y 470, and at 172 at y 416:
    # so the hills are low, and just behind them the land drops out of sight)
    h = 0.2 * noise(x, g, 30.0, 1)
    hills = 1.3 + 0.9 * noise(x, g * 0.3, 60.0, 2, 2) + 0.5 * np.sin(x * 0.05 + 1.0)
    h += np.clip(hills, 0.4, None) * smooth(152.0, 164.0, g)
    h -= 0.06 * np.clip(g - G_EDGE, 0, None) ** 2
    return h


def path_line():
    """the sandy path's middle, from the nest's right toward the pond (world pixels, as the painted path)"""
    pts = np.array([(660, 622), (820, 626), (990, 592), (1185, 576), (1320, 566), (1440, 555), (1560, 546), (1700, 560)], float)
    t = np.linspace(0, 1, len(pts))
    s = np.linspace(0, 1, 200)
    c = np.stack([np.interp(s, t, pts[:, 0]), np.interp(s, t, pts[:, 1])], 1)
    for _ in range(12):
        c[1:-1] = (c[:-2] + 2 * c[1:-1] + c[2:]) / 4
    return on_ground(c[:, 0], c[:, 1])


PATH = None


def path_dist(P):
    """distance to the path's middle (model units, measured on the ground) and the path's half width there"""
    P = np.atleast_2d(P)
    d = np.full(len(P), 1e9)
    for i in range(0, len(P), 100000):
        q = P[i:i + 100000, None, :2] - PATH[None, :, :2]
        d[i:i + 100000] = np.sqrt((q ** 2).sum(2)).min(1)
    half = 2.2 + 0.4 * noise(P[:, 0], P[:, 1], 20.0, 9)
    start = smooth(-6.0, 0.0, P[:, 0] - PATH[0, 0])              # the path fades in by the nest
    return d, half * start + 1e-3


def build_land():
    t0 = time.time()
    n_x, n_g = (360, 300) if not QUICK else (200, 160)
    gs = np.concatenate([np.linspace(96, 172, int(n_g * 0.8)), np.linspace(172.5, 215, n_g - int(n_g * 0.8))])
    us = np.linspace(-1, 1, n_x)
    V = []
    for g in gs:
        half = 1792 * (g * math.cos(TH) + CAM_H * math.sin(TH)) / F + 12
        V.append(np.stack([us * half, np.full(n_x, g), np.zeros(n_x)], 1))
    V = np.concatenate(V)
    V[:, 2] = height(V[:, 0], V[:, 1])
    Fc = np.array(Ub.grid_faces(len(gs), n_x))
    x, g = V[:, 0], V[:, 1]
    col = mix(np.tile(hexc("#c4e4ae"), (len(V), 1)), hexc("#ddf1c6"), np.clip(0.5 + noise(x, g, 18.0, 3), 0, 1)[:, None])
    col = mix(col, hexc("#a9d394"), (smooth(0.1, 0.6, noise(x, g, 7.0, 4)) * 0.45)[:, None])
    col = mix(col, hexc("#c6e6b0"), smooth(152, 168, g)[:, None] * 0.6)           # the hills a little lighter
    d, half = path_dist(V)
    sand = smooth(half + 0.6, half - 0.5, d)
    col = mix(col, hexc("#f2dfc2"), sand[:, None])
    D.mesh("land", V, Fc, col, D.principled("land", rough=0.95, spec=0.15))
    log("land", len(V), "points, %.1fs" % (time.time() - t0))
    return V


def build_far_hills():
    """hazy lilac and blue hills far off, their tops where the painted ones were (about y 330 to 400)"""
    B = D.Batch()
    for k, (cx, w, top_y, colr) in enumerate(((-700, 900, 372, "#c9bdee"), (-80, 1000, 356, "#b9d4ee"),
                                              (700, 1100, 344, "#cbbff0"), (1500, 1000, 360, "#b7d7ea"),
                                              (2300, 1000, 350, "#c9bdee"), (3000, 900, 368, "#b9d4ee"))):
        g = 700.0 + 60 * k % 180
        n = 120
        xs_px = np.linspace(cx - w, cx + w, n)
        P_top = ground_ray(xs_px, np.full(n, float(top_y)))       # rays through the wanted tops...
        tt = (g - CAM[1]) / (P_top[:, 1] - CAM[1])                 # ...cut at depth g
        top = CAM[None] + (P_top - CAM[None]) * tt[:, None]
        prof = np.sin(np.linspace(0, np.pi, n)) ** 0.7
        base_z = -140.0
        zt = base_z + (top[:, 2] - base_z) * prof + 2.0 * noise(top[:, 0], np.full(n, g), 90.0, 10 + k, 2)
        rows = 8
        Vh, Fh = [], []
        for r in range(rows):
            f = r / (rows - 1)
            ring = np.stack([top[:, 0], np.full(n, g + 40 * (1 - f)), base_z + (zt - base_z) * f], 1)
            Vh.append(ring)
        Vh = np.concatenate(Vh)
        Fh = np.array(Ub.grid_faces(rows, n))
        c = mix(np.tile(hexc(colr), (len(Vh), 1)), hexc("#f2eef8"), 0.22) * 0.8
        B.add(Vh, Fh, c)
    m = D.principled("farhills", rough=1.0, spec=0.0)
    bs = m.node_tree.nodes["Principled BSDF"]
    at = m.node_tree.nodes.new("ShaderNodeAttribute")
    at.attribute_name = "Col"
    m.node_tree.links.new(at.outputs["Color"], bs.inputs["Emission Color"])
    bs.inputs["Emission Strength"].default_value = 0.35          # haze: they are lit by the sky as much as the sun
    B.build("farhills", m)


def build_grass(V):
    t0 = time.time()
    nb = 1500000 if not QUICK else 220000
    # spread over the visible ground, denser near the front where blades are big on screen
    X = rng.uniform(X0, X0 + WPX, nb * 2)
    Y = 470 + (900 - 470) * rng.random(nb * 2) ** 0.8
    P = on_ground(X, Y)
    d, half = path_dist(P)
    keep = (d > half + 0.2 * rng.random(len(P))) & (P[:, 1] < 176)
    for ax, ay, r in ((512, 600, 3.4), (190, 500, 1.6)):     # bare round the nest and under the tree's foot
        c = on_ground(np.array([ax]), np.array([ay]))[0]
        keep &= np.hypot(P[:, 0] - c[0], P[:, 1] - c[1]) > r
    R = P[keep][:nb]
    nb = len(R)
    K = 4
    ln = rng.uniform(0.25, 0.6, nb) * (1 + 0.5 * (rng.random(nb) < 0.12))
    lean = unit(np.stack([rng.normal(0, 1, nb), rng.normal(0, 1, nb) - 0.3, np.zeros(nb)], 1))
    tilt = rng.uniform(0.1, 0.5, nb)
    sg = np.linspace(0, 1, K)
    Pg = (R[:, None, :] + np.array([0, 0, 1.0])[None, None] * (ln[:, None] * sg[None])[..., None]
          + lean[:, None, :] * (ln * tilt)[:, None, None] * (sg ** 2)[None, :, None])
    rad = (0.03 * rng.uniform(0.7, 1.3, nb))[:, None] * (1 - sg[None]) ** 0.8 + 0.002
    gc = mix(np.tile(hexc("#acd89a"), (nb, 1)), hexc("#ddf0c8"), rng.random(nb)[:, None])
    gc = mix(gc, hexc("#e9f3c8"), (rng.random(nb) < 0.1)[:, None] * 0.5)
    D.make_curves("grass", Pg, rad, gc, D.grass_material())
    log("grass", nb, "blades, %.1fs" % (time.time() - t0))


def build_flowers():
    """pastel flowers dotted in the grass: little five-petal ones near, dots further off"""
    near, dots = Ub.Bouquet(), D.Batch()
    cols = [("#ffb3cf", "#ffe0ea"), ("#ffc9a0", "#ffe6d0"), ("#cdb8f4", "#ebe2fb"), ("#ffffff", "#f6f2ea"),
            ("#ffe39a", "#fff3cc"), ("#b9e3f0", "#e2f4fa")]
    X = rng.uniform(X0, X0 + WPX, 30000)
    Y = 470 + 430 * rng.random(30000) ** 0.9
    P = on_ground(X, Y)
    d, half = path_dist(P)
    patch = noise(P[:, 0], P[:, 1], 14.0, 21, 2)              # flowers grow in patches, a few on their own
    want = rng.random(len(P)) < np.where(patch > 0.25, 0.25, 0.012)
    for i in np.nonzero((d > half + 0.4) & want)[0]:
        if np.hypot(X[i] - 512, (Y[i] - 600) * 2.2) < 190 or P[i, 1] > 168:
            continue
        a, b = cols[rng.integers(0, len(cols))]
        c = P[i] + np.array([0, 0, rng.uniform(0.25, 0.55)])
        if P[i, 1] < 150 and rng.random() < 0.35:
            Ub.flower(near, c, unit(np.array([0, -0.5, 1.0]) + rng.normal(0, 0.15, 3)), rng.uniform(0.12, 0.2), 5,
                      (hexc(a), hexc(b), hexc(a) * 0.85), 1)
        else:
            Vp, Fp = D.sphere_mesh(8, 4)
            Vp[:, 2] *= 0.5
            dots.add(Vp * rng.uniform(0.09, 0.16) + c, Fp, hexc(a) * rng.uniform(0.92, 1.05))
    near.build("flowers")
    dots.build("flowerdots", D.principled("flowerdot", rough=0.6, spec=0.2, sss=0.1))


def build_pebbles():
    B = D.Batch()
    for p in PATH[::3]:
        for _ in range(3):
            q = p + np.array([rng.normal(0, 1.4), rng.normal(0, 1.4), 0])
            r = rng.uniform(0.1, 0.28)
            Vs, Fs = D.stone_mesh(r, r * 0.8, r * 0.45, rng, (16, 8))
            q[2] = height(q[0], q[1]) + r * 0.1
            B.add(Vs + q, Fs, hexc("#e2cba8") * rng.uniform(0.9, 1.08))
    B.build("pebbles", D.principled("pebble", rough=0.8, spec=0.2))


# ================================================================== the props (each its own picture)
def at_px(x, y):
    return on_ground(np.array([float(x)]), np.array([float(y)]))[0]


def build_tree():
    """the apple tree: a warm trunk with two boughs, a soft round canopy of clustered leaves, blossom"""
    foot = at_px(190, 500)
    s = project(foot)[1][0]                                    # px per unit here
    H = 423 / s                                                # as tall as the painted tree
    B, bl = D.Batch(), D.Batch()
    trunk = np.array([foot + np.array([0, 0, -0.3]), foot + np.array([0.15, 0, H * 0.3]), foot + np.array([-0.2, 0, H * 0.5])])
    Vt, Ft = Ub.tube(trunk, np.array([0.8, 0.6, 0.48]) * (H / 12.6), 16)
    ct = mix(np.tile(hexc("#c89f80"), (len(Vt), 1)), hexc("#e2bfa2"), smooth(-0.5, 0.8, unit(Vt - trunk[1])[:, 0])[:, None] * 0.6)
    B.add(Vt, Ft, ct)
    for dx in (-1, 1):
        b = np.array([foot + np.array([0, 0, H * 0.36]), foot + np.array([dx * 1.6, 0, H * 0.48]), foot + np.array([dx * 2.8, 0.4, H * 0.56])])
        Vb, Fb = Ub.tube(b, np.array([0.36, 0.26, 0.16]) * (H / 12.6), 10)
        B.add(Vb, Fb, hexc("#c99f80"))
    c0 = foot + np.array([0, 0.3, H * 0.66])
    sc_ = H / 12.6
    crown = [(np.zeros(3), np.array([4.9, 3.6, 3.9]))]            # one big soft crown, a few bumps on its outline
    for k in range(9):
        a_ = 2 * np.pi * k / 9 + rng.uniform(-0.2, 0.2)
        d = np.array([np.cos(a_) * 3.6, rng.uniform(-0.6, 0.6), np.sin(a_) * 2.7])
        crown.append((d, np.full(3, rng.uniform(1.8, 2.4))))
    for d, rad in crown:
        Vl, Fl = D.blob_mesh(1.0, rng, (48, 24), 0.05)
        Vl = Vl * rad * sc_
        cc = c0 + d * sc_
        n_ = unit(Vl)
        up = smooth(-0.8, 0.9, n_[:, 2] - 0.3 * n_[:, 1])
        nz = noise(Vl[:, 0] * 3 + cc[0], Vl[:, 2] * 3 + Vl[:, 1], 2.0, 31, 2)   # leafy mottling
        cl = mix(np.tile(hexc("#9fd092"), (len(Vl), 1)), hexc("#d3edbd"), up[:, None] * 0.9)
        cl = mix(cl, hexc("#8cc184"), smooth(0.1, 0.5, nz)[:, None] * 0.35)
        B.add(Vl + cc, Fl, cl)
        for _ in range(int(14 * np.prod(rad) ** (1 / 3) / 2)):  # blossom on the outside
            dd = unit(rng.normal(0, 1, 3) + np.array([0, -0.9, 0.5]))
            p = cc + dd * rad * sc_ * 1.0
            Vp, Fp = D.sphere_mesh(10, 5)
            bl.add(Vp * np.array([1, 1, 0.5]) * 0.17 * sc_ + p, Fp, hexc(["#ffd0e0", "#ffffff", "#ffc2d6"][rng.integers(0, 3)]))
    B.build("tree", D.principled("treem", rough=0.8, spec=0.2, sheen=0.3))
    bl.build("treeblossom", D.principled("blossomm", rough=0.5, spec=0.3, sss=0.2))
    return ["tree", "treeblossom"]


def build_nest():
    """a woven nest: a bowl of straw, built as a back half (behind the egg) and a front rim (in front of it)"""
    c = at_px(512, 600)
    s = project(c)[1][0]
    R = 106 / s
    back, front = D.Batch(), D.Batch()
    bowl_V, bowl_F = D.sphere_mesh(48, 24)
    bowl_V = bowl_V * np.array([R * 0.92, R * 0.92, R * 0.45])
    keep = bowl_V[:, 2] <= 0.02
    bowl_V[:, 2] = np.minimum(bowl_V[:, 2], 0.02)
    bowl_V = bowl_V + c + np.array([0, 0, R * 0.42])
    back.add(bowl_V, bowl_F, mix(np.tile(hexc("#9b7454"), (len(bowl_V), 1)), hexc("#c49a72"), smooth(-1, 1, rng.normal(0, 1, len(bowl_V)))[:, None] * 0.5))
    strands = 520 if not QUICK else 200
    for k in range(strands):                                   # the rim: straws wound round, each a bent tube
        a0 = rng.uniform(0, 2 * np.pi)
        span = rng.uniform(0.5, 1.1)
        hgt = rng.uniform(0.15, 0.95)
        ts = np.linspace(0, span, 7)
        rr = R * (0.86 + 0.14 * hgt) + rng.normal(0, 0.05)
        pts = np.stack([np.cos(a0 + ts) * rr, np.sin(a0 + ts) * rr * 0.98, R * 0.42 * hgt + 0.12 * np.sin(ts * 6 + k)], 1) + c
        Vs, Fs = Ub.tube(pts, np.full(7, R * rng.uniform(0.045, 0.07)), 6)
        col = hexc(["#f0d3a6", "#d6a97c", "#e6c191", "#b98a62"][rng.integers(0, 4)]) * rng.uniform(0.9, 1.08)
        mid = a0 + span / 2
        (front if np.sin(mid) < 0 else back).add(Vs, Fs, col)  # toward the camera (-y): the front rim
    m = D.principled("nestm", rough=0.85, spec=0.2, sheen=0.4)
    back.build("nest_back", m)
    front.build("nest_front", m)
    return c, R


def build_egg(c, R):
    """the egg, pastel spotted, sitting in the bowl"""
    s = project(c)[1][0]
    h = 128 / s
    Sv, Sf = D.sphere_mesh(64, 32)
    q = Sv.copy()
    q[:, 2] = Sv[:, 2]
    w = 1.0 - 0.18 * smooth(-0.2, 1.0, Sv[:, 2])                 # narrower at the top
    V = np.stack([q[:, 0] * w * h * 0.4, q[:, 1] * w * h * 0.4, (q[:, 2] + 1) * h * 0.5], 1)
    V = V + c + np.array([0, -0.35, -R * 0.05])
    col = mix(np.tile(hexc("#fff6ee"), (len(V), 1)), hexc("#f4dccf"), smooth(-0.2, -1.0, Sv[:, 2])[:, None] * 0.5)
    for (dx, dz, r, cc) in ((-0.5, 0.25, 0.18, "#ffc2d6"), (0.35, 0.55, 0.14, "#cdb8f4"), (0.5, -0.1, 0.2, "#ffd7a8"),
                            (-0.45, -0.45, 0.16, "#b9e3f0"), (0.05, -0.75, 0.12, "#ffc2d6"), (0.0, 0.1, 0.1, "#ffe39a"),
                            (0.2, 0.85, 0.1, "#b9e3f0")):
        dirn = unit(np.array([dx, -0.85, dz]))
        dd = np.arccos(np.clip(unit(Sv) @ dirn, -1, 1))
        col = mix(col, hexc(cc) * 0.85, smooth(r * 1.15, r * 0.85, dd)[:, None])
    D.mesh("egg", V, Sf, col, D.principled("eggm", rough=0.35, spec=0.4, sss=0.25, sss_scale=0.2, coat=0.2))


def build_lanterns():
    names = []
    for i, (x, y) in enumerate(((372, 548), (836, 552))):
        foot = at_px(x, y)
        s = project(foot)[1][0]
        u = 1.0 / s                                            # units per painted pixel
        B, glass = D.Batch(), D.Batch()
        Vp, Fp = Ub.tube(np.array([foot + np.array([0, 0, -0.2]), foot + np.array([0, 0, 66 * u])]), np.full(2, 4.5 * u), 10)
        B.add(Vp, Fp, hexc("#a88a70"))
        top = foot + np.array([0, 0, 66 * u])
        Vb, Fb = D.sphere_mesh(24, 12)                           # the frame: a rounded box, cream, with a pink roof
        box = np.sign(Vb) * np.abs(Vb) ** 0.4 * np.array([20 * u, 20 * u, 22 * u])
        B.add(box + top + np.array([0, 0, 20 * u]), Fb, hexc("#fff3d6"))
        roof = np.sign(Vb) * np.abs(Vb) ** 0.7 * np.array([26 * u, 26 * u, 12 * u])
        roof[:, 2] = np.maximum(roof[:, 2], 0)
        B.add(roof + top + np.array([0, 0, 40 * u]), Fb, hexc("#e8a6b8"))
        Vr, Fr = Ub.tube(np.array([top + np.array([-4 * u, 0, 50 * u]), top + np.array([0, 0, 56 * u]), top + np.array([4 * u, 0, 50 * u])]), np.full(3, 1.5 * u), 8)
        B.add(Vr, Fr, hexc("#c99a6a"))
        Vg, Fg = D.sphere_mesh(16, 8)
        glass.add(Vg * np.array([15 * u, 15 * u, 17 * u]) + top + np.array([0, -6 * u, 20 * u]), Fg, hexc("#ffe7a8"))
        B.build("lantern%d" % i, D.principled("lanternm", rough=0.6, spec=0.3))
        glass.build("lanternglass%d" % i, D.principled("lanternglass", color=hexc("#ffe2a0"), rough=0.3, emit=0.6))
        names.append(["lantern%d" % i, "lanternglass%d" % i])
    return names


def build_sign():
    """a wooden signpost with an arrow board pointing right (the game mirrors it); built at the right-hand signpost"""
    foot = at_px(944, 560)
    s = project(foot)[1][0]
    u = 1.0 / s
    B = D.Batch()
    Vp, Fp = Ub.tube(np.array([foot + np.array([0, 0, -0.2]), foot + np.array([0, 0, 106 * u])]), np.full(2, 6 * u), 10)
    B.add(Vp, Fp, hexc("#c69a7f"))
    # the board: a flattened rounded slab with a pointed right end
    Vb, Fb = D.sphere_mesh(32, 16)
    q = np.sign(Vb) * np.abs(Vb) ** 0.35
    q[:, 0] = np.where(q[:, 0] > 0.55, 0.55 + (q[:, 0] - 0.55) * (1.0 - np.abs(q[:, 2]) * 1.2), q[:, 0])
    board = q * np.array([52 * u, 5 * u, 24 * u]) + foot + np.array([12 * u, -6 * u, 100 * u])
    cb = mix(np.tile(hexc("#f0d3a6"), (len(Vb), 1)), hexc("#e2b886"), smooth(0.5, -0.5, q[:, 2])[:, None])
    B.add(board, Fb, cb)
    B.build("sign", D.principled("signm", rough=0.7, spec=0.2))
    return foot


def ring(c, rx, ry, r, n=48, tilt=0.0, wave=0.0, waves=0, phase=0.0):
    """a closed tube round the point c, radii rx (sideways) and ry (in depth), tipped toward the camera by `tilt`"""
    a = np.linspace(0, 2 * np.pi, n + 1)
    rr = 1.0 + wave * np.sin(a * waves + phase)
    pts = np.stack([np.cos(a) * rx * rr, np.sin(a) * ry * rr, np.zeros_like(a)], 1)
    ct, st = math.cos(tilt), math.sin(tilt)
    pts = pts @ np.array([[1, 0, 0], [0, ct, st], [0, -st, ct]])   # tip the far side up, so it shows as a ring
    return Ub.tube(pts + c, np.full(len(pts), r), 10, close_ends=False)


def outward(name):
    """make every face of a made-up object face outward (mirrored parts and tube ends come out mixed)"""
    import bmesh
    me = bpy.data.objects[name].data
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()


def at_plane(x, y, depth):
    """the point at this depth (model y) seen at world pixel (x, y)"""
    d = FWD + RIGHT * ((x - CX) / F) - UPV * ((y - CY) / F)
    return CAM + d * ((depth - CAM[1]) / d[1])


BASKET_AT = (950, 704)                                         # Wardrobe.AT
WEAR_SPOTS = {"crown": (-36, -26), "scarf": (0, -40), "bow": (36, -26)}   # Wardrobe.ITEMS spots, from the basket


def build_basket():
    """a round woven basket with a handle: rows of willow wound over and under the stakes, a thick rim"""
    foot = at_px(BASKET_AT[0], BASKET_AT[1] + 10)
    s = project(foot)[1][0]
    u = 1.0 / s
    B = D.Batch()
    Hb, Rt, Rb, dep = 32 * u, 58 * u, 44 * u, 0.8
    rows = 7
    for k in range(rows):                                      # the weave: each row waves over and under the stakes
        t = (k + 0.5) / rows
        z, rad = Hb * t, Rb + (Rt - Rb) * t
        Vr, Fr = ring(foot + np.array([0, 0, z]), rad, rad * dep, Hb / rows * 0.62, 96, 0.0, 0.035, 16, k * np.pi)
        B.add(Vr, Fr, hexc(["#e8bb80", "#ddaa70"][k % 2]) * rng.uniform(0.95, 1.05))
    for k in range(16):                                        # the stakes between
        a = 2 * np.pi * k / 16
        p0 = foot + np.array([np.cos(a) * Rb, np.sin(a) * Rb * dep, 0.0])
        p1 = foot + np.array([np.cos(a) * Rt, np.sin(a) * Rt * dep, Hb])
        Vs, Fs = Ub.tube(np.array([p0, p1]), np.full(2, 2.2 * u), 8)
        B.add(Vs, Fs, hexc("#d0a06a"))
    Vd, Fd = D.sphere_mesh(32, 16)                              # the floor inside, a little shaded
    Vd = Vd * np.array([Rt * 0.97, Rt * dep * 0.97, 2 * u]) + foot + np.array([0, 0, Hb * 0.55])
    B.add(Vd, Fd, hexc("#b08a60"))
    Vc, Fc = D.sphere_mesh(32, 16)                              # the bottom
    B.add(Vc * np.array([Rb, Rb * dep, 2 * u]) + foot + np.array([0, 0, 1 * u]), Fc, hexc("#b98652"))
    Vr, Fr = ring(foot + np.array([0, 0, Hb]), Rt, Rt * dep, 5 * u, 96)
    B.add(Vr, Fr, hexc("#d8a872"))
    a =np.linspace(np.pi * 0.06, np.pi * 0.94, 40)               # the handle, an arch across
    pts = np.stack([np.cos(a) * 52 * u, np.zeros_like(a), Hb + np.sin(a) * 54 * u - 6 * u], 1) + foot
    Vh, Fh = Ub.tube(pts, np.full(len(pts), 3.6 * u), 10)
    B.add(Vh, Fh, hexc("#cc9a64"))
    for k in range(10):                                        # a ribbon wound round it
        t = np.linspace(0, 1, 12)
        aa = a[0] + (a[-1] - a[0]) * (k + t) / 10
        q = np.stack([np.cos(aa) * 52 * u, np.zeros_like(aa), Hb + np.sin(aa) * 54 * u - 6 * u], 1) + foot
        nrm = np.stack([np.cos(aa), np.zeros_like(aa), np.sin(aa)], 1)
        side = np.cross(nrm, np.array([0, 1.0, 0]))
        q = q + (nrm * np.cos(t * 2 * np.pi)[:, None] + np.array([0, 1.0, 0]) * np.sin(t * 2 * np.pi)[:, None]) * 3.7 * u
        Vt, Ft = Ub.tube(q, np.full(12, 1.2 * u), 6)
        B.add(Vt, Ft, hexc("#ecc38a"))
    B.build("basket", D.principled("basketm", rough=0.8, spec=0.2, sheen=0.3))
    return foot, u


def build_wear(foot, u):
    """the three things to wear, each sitting in the basket at its spot (Wardrobe.ITEMS), the 3D models' colours"""
    depth = foot[1]
    names = {}
    for id_, (sx, sy) in WEAR_SPOTS.items():
        c = at_plane(BASKET_AT[0] + sx, BASKET_AT[1] + sy, depth)
        B = D.Batch()
        if id_ == "crown":
            tilt = 0.55
            Vr, Fr = ring(c, 20 * u, 20 * u, 3 * u, 64, tilt)
            B.add(Vr, Fr, hexc("#8cc78a"))
            fl = ["#f7a8c8", "#c9a8f0", "#fff1c9", "#ffc3a0", "#a8d8f5"]
            ct, st = math.cos(tilt), math.sin(tilt)
            for k in range(7):
                a = 2 * np.pi * k / 7 + 0.3
                p = np.array([np.cos(a) * 20 * u, np.sin(a) * 20 * u, 0.0]) @ np.array([[1, 0, 0], [0, ct, st], [0, -st, ct]]) + c
                Vf, Ff = D.sphere_mesh(16, 8)
                for j in range(5):                              # five round petals and a yellow middle
                    b = 2 * np.pi * j / 5 + a
                    off = np.array([np.cos(b), -0.4, np.sin(b)]) * 4.0 * u
                    B.add(Vf * np.array([3.6, 2.4, 3.6]) * u + p + off, Ff, hexc(fl[k % 5]))
                B.add(Vf * 2.4 * u + p + np.array([0, -2.5 * u, 0]), Ff, hexc("#ffe08a"))
                b = a + np.pi / 7
                q = np.array([np.cos(b) * 21 * u, np.sin(b) * 21 * u, 0.0]) @ np.array([[1, 0, 0], [0, ct, st], [0, -st, ct]]) + c
                B.add(Vf * np.array([4.5, 1.5, 2.2]) * u + q, Ff, hexc("#7fbf7a"))
        elif id_ == "scarf":
            tilt = 0.5
            for dz, col in ((-5.5, "#c9a8f0"), (-2.7, "#fff1c9"), (0.0, "#c9a8f0"), (2.7, "#fff1c9"), (5.5, "#c9a8f0")):
                Vr, Fr = ring(c + np.array([0, 0, dz * u]), 18 * u, 18 * u, 3.4 * u, 64, tilt)   # a knitted band, striped
                B.add(Vr, Fr, hexc(col))
            Vb, Fb = D.sphere_mesh(24, 12)                       # the loose end hanging down in front
            q = np.sign(Vb) * np.abs(Vb) ** 0.4
            end = q * np.array([6.5 * u, 2.5 * u, 14 * u]) + c + np.array([12 * u, -16 * u, -12 * u])
            B.add(end, Fb, hexc("#c9a8f0"))
            Vs, Fs = D.sphere_mesh(16, 6)
            for j in range(4):                                   # its fringe
                B.add(Vs * np.array([1.2, 1.2, 3.2]) * u + c + np.array([(8 + 2.8 * j) * u, -17 * u, -28 * u]), Fs, hexc("#fff1c9"))
            Vt, Ft = Ub.tube(np.array([c + np.array([6 * u, -18.6 * u, -6 * u]), c + np.array([18.5 * u, -18.6 * u, -6 * u])]), np.full(2, 1.4 * u), 6)
            B.add(Vt, Ft, hexc("#fff1c9"))
        else:                                                  # the bow, facing the camera
            Vk, Fk = D.sphere_mesh(20, 10)
            B.add(Vk * np.array([6, 4.5, 6]) * u + c, Fk, hexc("#f58fb6"))
            for side in (-1, 1):
                a = np.linspace(0, 2 * np.pi, 49)
                lp = np.stack([side * (11 + 11 * np.cos(a + np.pi)) * u * 0.95, np.zeros_like(a), np.sin(a) * 8.5 * u], 1)
                lp[:, 0] *= 1.0
                Vl, Fl = Ub.tube(lp + c + np.array([side * 1.5 * u, 0.5 * u, 1.5 * u]), np.full(49, 3.6 * u), 10, close_ends=False)
                B.add(Vl, Fl, hexc("#f7a8c8"))
                tl = np.array([c + np.array([side * 1 * u, -1 * u, -2 * u]), c + np.array([side * 6 * u, -1.5 * u, -12 * u]),
                               c + np.array([side * 10 * u, -1 * u, -20 * u])])
                Vt, Ft = Ub.tube(tl, np.array([3.2, 3.0, 2.6]) * u, 10)
                B.add(Vt * np.array([1, 1, 1]), Ft, hexc("#f58fb6"))
        B.build("wear_" + id_, D.principled("wearm", rough=0.6, spec=0.3, sheen=0.4))
        names[id_] = (BASKET_AT[0] + sx, BASKET_AT[1] + sy)
    return names


APPLE_AT = (700, 690)                                          # where the apple is made: front of the walkable ground


def build_apple():
    """an apple, glossy red with a lighter cheek, a stem and a leaf; made once, near the front, and drawn anywhere"""
    g = at_px(*APPLE_AT)
    s = project(g)[1][0]
    u = 2.0 / s                                                # (the painted apple was drawn at half size, shown at 2x)
    r = 13 * u
    c = g + np.array([0, 0, r])
    Sv, Sf = D.sphere_mesh(48, 24)
    z = Sv[:, 2]
    rho = np.sqrt(Sv[:, 0] ** 2 + Sv[:, 1] ** 2)
    zz = z - 0.28 * np.exp(-(rho / 0.32) ** 2) * np.sign(z) * (np.abs(z) > 0.2)   # dimples top and bottom
    w = 1.04 - 0.1 * smooth(-0.9, 0.9, z)                        # a little wider at the shoulders
    V = np.stack([Sv[:, 0] * w * 1.06, Sv[:, 1] * w, zz * 0.93], 1) * r + c
    light = smooth(-0.3, 0.9, unit(Sv) @ unit(np.array([-0.6, -0.5, 0.6])))
    col = mix(np.tile(hexc("#f45f72"), (len(V), 1)), hexc("#ff9aa6"), light[:, None] * 0.7)
    col = mix(col, hexc("#ffd27a"), smooth(0.85, 1.0, unit(Sv) @ unit(np.array([0.3, -0.8, 0.5])))[:, None] * 0.35)
    D.mesh("apple", V, Sf, col, D.principled("applem", rough=0.3, spec=0.5, coat=0.4))
    B = D.Batch()
    top = c + np.array([0, 0, r * 0.68])
    Vs, Fs = Ub.tube(np.array([top, top + np.array([0.6 * u, 0, 5 * u]), top + np.array([2.5 * u, 0, 9 * u])]), np.full(3, 1.3 * u), 8)
    B.add(Vs, Fs, hexc("#9c6f58"))
    Vl, Fl = D.sphere_mesh(20, 10)
    lv = Vl * np.array([5.5, 1.2, 2.6]) * u
    ang = 0.45
    lv = lv @ np.array([[math.cos(ang), 0, math.sin(ang)], [0, 1, 0], [-math.sin(ang), 0, math.cos(ang)]])
    B.add(lv + top + np.array([6 * u, -0.5 * u, 6.5 * u]), Fl, hexc("#7fbf6a"))
    B.build("applestem", D.principled("stemm", rough=0.6, spec=0.3))
    return ["apple", "applestem"], project(c)[0][0]


# ================================================================== light, sky, render
def light_and_sky():
    sc = bpy.context.scene
    back = -FWD
    L = unit(-5 * RIGHT + 6 * UPV + 9 * back)                  # the game's creature key light, in this camera's frame
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy, sun.angle, sun.color = 2.6, math.radians(25), (1.0, 0.96, 0.9)
    ob = bpy.data.objects.new("sun", sun)
    bpy.context.collection.objects.link(ob)
    ob.rotation_euler = (-Vector(L)).to_track_quat("-Z", "Y").to_euler()
    w = sc.world
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    mixs = nt.nodes.new("ShaderNodeMixShader")
    lp = nt.nodes.new("ShaderNodeLightPath")
    amb = nt.nodes.new("ShaderNodeBackground")                  # what lights the scene: a soft bright sky
    amb.inputs["Color"].default_value = (0.85, 0.9, 1.0, 1)
    amb.inputs["Strength"].default_value = 1.6
    sky = nt.nodes.new("ShaderNodeBackground")                  # what the camera sees: the pastel gradient
    sky.inputs["Strength"].default_value = 1.4                  # (the view is set a little dark for the lit ground)
    tc = nt.nodes.new("ShaderNodeTexCoord")
    sep = nt.nodes.new("ShaderNodeSeparateXYZ")
    nt.links.new(tc.outputs["Window"], sep.inputs[0])
    ramp = nt.nodes.new("ShaderNodeValToRGB")
    cr = ramp.color_ramp
    stops = [(0.0, "#ffe9d6"), (0.4, "#ffe9d6"), (0.58, "#f6eef4"), (1.0, "#cfe6f6")]   # window y: 0 bottom, 1 top
    cr.elements[0].position, cr.elements[0].color = stops[0][0], tuple(hexc(stops[0][1])[:3]) + (1,)
    cr.elements[1].position, cr.elements[1].color = stops[-1][0], tuple(hexc(stops[-1][1])[:3]) + (1,)
    for p, c in stops[1:-1]:
        e = cr.elements.new(p)
        e.color = tuple(hexc(c)[:3]) + (1,)
    nt.links.new(sep.outputs["Y"], ramp.inputs["Fac"])
    # soft clouds high up: noise in the picture's own coordinates, stretched sideways
    mapn = nt.nodes.new("ShaderNodeMapping")
    mapn.inputs["Scale"].default_value = (2.0, 4.5, 1.0)
    nt.links.new(tc.outputs["Window"], mapn.inputs["Vector"])
    nz = nt.nodes.new("ShaderNodeTexNoise")
    nz.inputs["Scale"].default_value = 2.5
    nz.inputs["Detail"].default_value = 1.5
    nt.links.new(mapn.outputs["Vector"], nz.inputs["Vector"])
    band = nt.nodes.new("ShaderNodeMapRange")                    # clouds only in the top part
    band.inputs["From Min"].default_value, band.inputs["From Max"].default_value = 0.72, 0.9
    nt.links.new(sep.outputs["Y"], band.inputs["Value"])
    cl = nt.nodes.new("ShaderNodeMapRange")
    cl.inputs["From Min"].default_value, cl.inputs["From Max"].default_value = 0.52, 0.66
    nt.links.new(nz.outputs["Fac"], cl.inputs["Value"])
    mul = nt.nodes.new("ShaderNodeMath")
    mul.operation = "MULTIPLY"
    nt.links.new(cl.outputs["Result"], mul.inputs[0])
    nt.links.new(band.outputs["Result"], mul.inputs[1])
    mixc = nt.nodes.new("ShaderNodeMix")
    mixc.data_type = "RGBA"
    nt.links.new(mul.outputs[0], mixc.inputs["Factor"])
    nt.links.new(ramp.outputs["Color"], mixc.inputs["A"])
    mixc.inputs["B"].default_value = (1.0, 1.0, 1.0, 1)
    nt.links.new(mixc.outputs["Result"], sky.inputs["Color"])
    nt.links.new(lp.outputs["Is Camera Ray"], mixs.inputs["Fac"])
    nt.links.new(amb.outputs["Background"], mixs.inputs[1])
    nt.links.new(sky.outputs["Background"], mixs.inputs[2])
    nt.links.new(mixs.outputs["Shader"], out.inputs["Surface"])
    sc.view_settings.view_transform = "Standard"              # plain colours: the pastels stay as chosen
    sc.view_settings.look = "None"
    sc.view_settings.exposure = -0.35


def camera():
    sc = bpy.context.scene
    cam = bpy.data.cameras.new("cam")
    cam.sensor_fit = "HORIZONTAL"
    cam.sensor_width = 36.0
    cam.lens = F * 36.0 / WPX
    cam.clip_start, cam.clip_end = 1.0, 5000.0
    ob = bpy.data.objects.new("cam", cam)
    bpy.context.collection.objects.link(ob)
    ob.location = Vector(CAM)
    ob.rotation_euler = Vector(FWD).to_track_quat("-Z", "Y").to_euler()
    sc.camera = ob
    k = 1 if QUICK else 2
    sc.render.resolution_x, sc.render.resolution_y = int(WPX * k), int(HPX * k)
    sc.render.resolution_percentage = 100


def render_box(name, x, y, w, h, show, transparent=True, hide=()):
    """render the world-pixel box (x, y, w, h) with only the objects named in `show` seen by the camera, and those
    in `hide` left out altogether (so they neither shade it nor stand in its way)"""
    sc = bpy.context.scene
    for ob in bpy.data.objects:
        if ob.type in ("MESH", "CURVES"):
            ob.visible_camera = show is None or ob.name in show
            ob.hide_render = ob.name in hide
    sc.render.use_border = True
    sc.render.use_crop_to_border = True
    sc.render.border_min_x = (x - X0) / WPX
    sc.render.border_max_x = (x + w - X0) / WPX
    sc.render.border_max_y = 1.0 - (y - Y0) / HPX
    sc.render.border_min_y = 1.0 - (y + h - Y0) / HPX
    sc.render.film_transparent = transparent
    sc.render.filepath = os.path.join(OUT, name + ".png")
    t0 = time.time()
    bpy.ops.render.render(write_still=True)
    log("rendered", name, "%.0fs" % (time.time() - t0))


def main():
    global PATH
    os.makedirs(OUT, exist_ok=True)
    sc = D.setup()
    sc.cycles.samples = 64 if QUICK else 192
    camera()
    light_and_sky()
    PATH = path_line()
    log("camera: %.2f up, tilted %.2f degrees, focal %.1f mm" % (CAM_H, math.degrees(TH), F * 36.0 / WPX))
    V = build_land()
    build_far_hills()
    build_grass(V)
    build_flowers()
    build_pebbles()
    props = {}
    props["tree"] = build_tree()
    nest_c, nest_r = build_nest()
    props["nest_back"], props["nest_front"] = ["nest_back"], ["nest_front"]
    build_egg(nest_c, nest_r)
    props["egg"] = ["egg"]
    lan = build_lanterns()
    build_sign()
    props["sign"] = ["sign"]
    bfoot, bu = build_basket()
    props["basket"] = ["basket"]
    wear = build_wear(bfoot, bu)
    for id_ in wear:
        props["wear_" + id_] = ["wear_" + id_]
    props["apple"], apple_px = build_apple()
    for n in ["basket", "apple", "applestem"] + ["wear_" + i for i in wear]:
        outward(n)
    loose = {"nest_back", "nest_front", "egg", "apple", "applestem"} | {"wear_" + i for i in wear}
    prop_names = {n for v in props.values() for n in v} | {n for l in lan for n in l}
    for ob in bpy.data.objects:                               # props are drawn separately; their shadows stay
        if ob.name in prop_names:
            ob.visible_camera = False
        if ob.name in loose:                                  # (not the nest's: the ground under it shows between straws;
            ob.visible_shadow = False                         # nor things that move)
    if "backdrop" in PARTS:
        render_box("meadow", -512, -128, 2048, 1024, {o.name for o in bpy.data.objects if o.name not in prop_names}, False)
    # each prop on the canvas of the drawing it replaces (world-pixel box from its origin)
    boxes = {"tree": (190, 500, 400, 480, 200, 470), "nest_back": (512, 600, 240, 110, 120, 50),
             "nest_front": (512, 600, 240, 110, 120, 50), "egg": (512, 622, 120, 150, 60, 146),
             "lantern": (372, 548, 80, 140, 40, 136), "sign": (944, 560, 120, 150, 40, 146),
             "basket": (BASKET_AT[0], BASKET_AT[1], 160, 124, 80, 96),
             "apple": (apple_px[0], apple_px[1], 96, 96, 48, 48)}
    for id_, (x, y) in wear.items():                          # each 64 x 64, centred on its spot
        boxes["wear_" + id_] = (x, y, 64, 64, 32, 32)
    show = dict(props, lantern=lan[0])
    for name, (ax, ay, w, h, ox, oy) in boxes.items():
        part = name.split("_")[0]
        if part in PARTS or name in PARTS:
            hide = set()
            if name in ("basket", "apple") or name.startswith("wear_"):   # loose things: no grass round them
                hide = {o.name for o in bpy.data.objects if o.type == "CURVES" or o.name in ("grass", "flowers", "flowerdots", "pebbles")}
            if name.startswith("wear_"):                       # (and nothing of the basket in their way)
                hide |= {"basket"} | {"wear_" + i for i in wear if "wear_" + i != name}
            render_box(name, ax - ox, ay - oy, w, h, set(show[name]), hide=hide)


main()
