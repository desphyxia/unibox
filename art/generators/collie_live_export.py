"""Border collie D (collie_d.py) for the game: built standing square at game density, with closed eyes too, a skeleton
and skin weights, written in the format game/tools/build_collie.gd reads (the same as unicorn2_live_export.py writes).

The iPad can't draw the render's million and a half hairs, so the coat is made another way:
  head      the head's own skin (eye sockets, lips, the stretched muzzle), finely meshed, with short shell fur
  coat      the body's skin wrapped in the coat's bulk: a few thousand guide strands are grown with the render's groom
            (the ruff, the long black coat, the leg feathering, the britches, the plumed tail, the cheek fluff) and each
            is given a tapering thickness, so the surface hangs in locks where the hair does; its colour, combed
            direction and skin weights come from the guide strand under each point; short shell fur on top
  parts     eyes (open, and closed: a furred lid with a dark lash line), nose, tongue, teeth and ears as in the render

Bones (Godot axes): root, body, neck_0..1, head, ear_0 (near) and ear_1, for each leg (nf, ff, nh, fh: near or far,
front or hind) upper, lower and paw, and tail_0..3.
Per vertex: position, normal, colour, fur tip lightness, emission, blink piece (1 shown open, 2 shown closed), trait
(1 the dark coat, 2 the white), fur lift, fur droop, fur vector (combed direction times length), four bones and weights.

Run:  blender -b --factory-startup -P collie_live_export.py -- ../exports/collie_live.bin [--preview DIR]
      --preview DIR  also renders the game model in Blender (side and three-quarter), for checking the shape"""
import os, sys, json, math
os.environ["COLLIE_STAND"] = "1"
import bpy, bmesh
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = argv[0] if argv and not argv[0].startswith("--") else "collie_live.bin"
PREVIEW = argv[argv.index("--preview") + 1] if "--preview" in argv else None
sys.argv = [sys.argv[0], "--", "unused", "--quick"]           # collie_d.py reads its options from here
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import collie_d as D
D.HS = 1.5                                                    # the head bigger in the game, so the face reads at its size
from unicorn2_shape import sample, surface_nets, round_cone, smin, smax

SCALE = 2.9                                                   # the game's collie about the fox's size
SHIFT = np.array([0.2, 0.0, 0.0])                             # the dog's middle over the ground point
HEAD_TRIS, COAT_TRIS = 7000, 15000                            # the meshes are simplified to these
GUIDES = 9000                                                 # guide strands for the coat's bulk
BLACK_FUR = D.hexc(os.environ.get("COLLIE_BLACK", "#2b3449"))  # the painting's "black" is a soft navy (its middle
                                                              # tone about #283345); the game's light darkens it
DARK_TIP = float(os.environ.get("COLLIE_TIP", "0.18"))         # the dark fur's tips lighter, blue-grey, where light catches
FORM = float(os.environ.get("COLLIE_FORM", "0.6"))           # how much the shape's ridges lighten and grooves darken
WHITE_FUR = D.hexc("#eeeae1")
rng = np.random.default_rng(11)
log = D.log


# Blender's x, z, y: the near side (+y, the side the render shows) toward the game's camera, which looks from Godot's
# +z. That is a mirror, so triangles are turned round too.
def g(v):
    v = np.asarray(v, np.float64) - SHIFT
    return np.stack([v[..., 0], v[..., 2], v[..., 1]], -1) * SCALE


def gd(v):
    v = np.asarray(v, np.float64)
    return np.stack([v[..., 0], v[..., 2], v[..., 1]], -1)


def unit(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def mesh_arrays(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("tmp")
    bm.to_mesh(me)
    bm.free()
    n = len(me.vertices)
    co = np.empty(n * 3)
    me.vertices.foreach_get("co", co)
    tri = np.empty(len(me.polygons) * 3, np.int64)
    me.polygons.foreach_get("vertices", tri)
    col = None
    ca = me.color_attributes.get("Col")
    if ca is not None and ca.domain == "POINT":
        raw = np.empty(len(ca.data) * 4, np.float32)
        ca.data.foreach_get("color", raw)
        col = raw.reshape(-1, 4)[:, :3].astype(np.float64)
    if col is None:
        c = (0.8, 0.8, 0.8)
        m = ob.data.materials[0] if ob.data.materials else None
        if m and m.use_nodes:
            bs = m.node_tree.nodes.get("Principled BSDF")
            if bs:
                c = tuple(bs.inputs["Base Color"].default_value)[:3]
        col = np.tile(np.array(c), (n, 1))
    bpy.data.meshes.remove(me)
    return co.reshape(-1, 3), tri.reshape(-1, 3), col


def simplified(V, T, target):
    """a mesh cut down to about `target` triangles (Blender's decimate), as arrays"""
    me = bpy.data.meshes.new("dec")
    me.from_pydata(V.tolist(), [], T.tolist())
    ob = bpy.data.objects.new("dec", me)
    bpy.context.collection.objects.link(ob)
    if len(T) > target:
        mod = ob.modifiers.new("d", "DECIMATE")
        mod.ratio = target / len(T)
        bpy.context.view_layer.objects.active = ob
        with bpy.context.temp_override(object=ob):
            bpy.ops.object.modifier_apply(modifier=mod.name)
    V2, T2, _ = mesh_arrays(ob)
    bpy.data.objects.remove(ob)
    return V2, T2


def check_box(F):
    """a sampled surface must not reach the edge of its box, or it is cut open there"""
    rim = min(F[[0, -1]].min(), F[:, [0, -1]].min(), F[:, :, [0, -1]].min())
    if rim < 0:
        raise SystemExit("a surface reaches the edge of its box (%.4f): make the box bigger" % rim)


# ================================================================== the head: its own skin, finely meshed
def head_world_sdf(P):
    return D.head_sdf(D.to_head(P)) * D.HS


def build_head():
    lo, hi = D.HEAD_C - 0.45, D.HEAD_C + np.array([0.66, 0.45, 0.45])
    h = 0.0045
    F, o = sample(head_world_sdf, lo, hi, h)
    check_box(F)
    V, T = surface_nets(F, o, h)
    V, T = simplified(D.project(head_world_sdf, V, 2), np.asarray(T), HEAD_TRIS)
    V = D.project(head_world_sdf, V, 2)
    log("head", len(T), "triangles")
    return V, T


# ================================================================== the coat: the body's skin wrapped in the hair's bulk
KIND_R = {0: (0.014, 0.009), 1: (0.026, 0.013), 3: (0.014, 0.008), 4: (0.024, 0.012), 9: (0.014, 0.008)}   # root, tip
KIND_LEN = {0: 0.8, 1: 1.0, 3: 0.6, 4: 1.0}                   # the bulk a little shorter than the hair (it lies flatter)


def guides(V, T, part, field):
    """guide strands over the body (and the long hair of the head), grown with the render's groom"""
    body = T[(part[T] != 0).all(1)]
    R = D.roots_on(V, body, GUIDES, rng)
    N = field.grad(R)
    pr, _ = D.classify(R)
    m = pr != 0
    R, N, pr = R[m], N[m], pr[m]
    ln, lift, comb, grav, kind = D.body_groom(R, N, pr)
    ln = ln * np.clip(1 + 0.18 * D.wobble(R, rng) * np.isin(kind, [0, 1, 3, 4]), 0.75, 1.35) * rng.uniform(0.85, 1.15, len(R))
    comb = unit(comb - N * np.sum(comb * N, 1, keepdims=True))
    keep = kind != 2                                          # short hair (lower legs, paws) adds no bulk
    ln = ln * np.vectorize(lambda k: KIND_LEN.get(int(k), 1.0))(kind)
    R, N, pr, ln, lift, comb, grav, kind = (a[keep] for a in (R, N, pr, ln, lift, comb, grav, kind))
    K = 9
    P = D.grow(R, N, comb, ln, lift, grav, K, field)
    P = D.settle(P, field)
    white = D.body_white(R, N, pr)
    # the head's long hair: the cheek fluff below the ears, the crown and the throat
    headT = T[(part[T] == 0).all(1)]
    Rh = D.roots_on(V, headT, 2500, rng)
    Lh = D.to_head(Rh)
    lnh, lifth, combh, gravh = D.head_groom(Lh)
    mh = (lnh > 0.024) & (Lh[:, 2] < 0.02)                    # the cheeks and throat, not the crown
    Rh, Lh, lnh, lifth, combh, gravh = Rh[mh], Lh[mh], lnh[mh], lifth[mh], combh[mh], gravh[mh]
    Nh = field.grad(Rh)
    combh = D.hdir(combh)
    combh = unit(combh - Nh * np.sum(combh * Nh, 1, keepdims=True))
    Ph = D.settle(D.grow(Rh, Nh, combh, lnh * D.HS, lifth, gravh, K, field), field)
    _, wh = D.head_colours(Lh, None)
    log("guides", len(P), "body,", len(Ph), "head")
    return (np.concatenate([P, Ph]), np.concatenate([R, Rh]), np.concatenate([kind, np.full(len(Ph), 9)]),
            np.concatenate([white, wh]), np.concatenate([pr, np.zeros(len(Ph), int)]))


def splat(Pg, kind, lo, shape, h):
    """the distance to the nearest guide's tapering round cone on a grid, and which guide and segment it is"""
    F = np.full(shape, 9.0, np.float32)
    ID = np.full(shape, -1, np.int64)
    n, K = Pg.shape[:2]
    for i in range(n):
        r0, r1 = KIND_R[int(kind[i])]
        rad = r0 + (r1 - r0) * np.linspace(0, 1, K)
        for k in range(K - 1):
            a, b, ra, rb = Pg[i, k], Pg[i, k + 1], rad[k], rad[k + 1]
            m = max(ra, rb) + 2 * h
            i0 = np.maximum(np.floor((np.minimum(a, b) - m - lo) / h).astype(int), 0)
            i1 = np.minimum(np.ceil((np.maximum(a, b) + m - lo) / h).astype(int) + 1, np.array(shape))
            if (i1 <= i0).any():
                continue
            xs = lo[0] + h * np.arange(i0[0], i1[0])
            ys = lo[1] + h * np.arange(i0[1], i1[1])
            zs = lo[2] + h * np.arange(i0[2], i1[2])
            X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
            Q = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
            d = round_cone(Q, a, b, ra, rb).reshape(X.shape).astype(np.float32)
            sub = F[i0[0]:i1[0], i0[1]:i1[1], i0[2]:i1[2]]
            better = d < sub
            sub[better] = d[better]
            ids = ID[i0[0]:i1[0], i0[1]:i1[1], i0[2]:i1[2]]
            ids[better] = i * (K - 1) + k
    return F, ID


def blur(F):
    out = F.copy()
    for ax in range(3):
        a = np.moveaxis(out, ax, 0)
        b = a.copy()
        b[1:-1] = 0.25 * a[:-2] + 0.5 * a[1:-1] + 0.25 * a[2:]
        out = np.moveaxis(b, 0, ax)
    return out


def build_coat():
    Vs, Ts, part, field = skin_for_growing()
    Pg, Rg, kind, white, gpart = guides(Vs, Ts, part, field)
    lo, hi = np.array([-1.05, -0.5, -0.02]), np.array([1.45, 0.5, 1.85])
    h = 0.0075
    shape = tuple(np.round((hi - lo) / h).astype(int) + 1)
    Fe, ID = splat(Pg, kind, lo, shape, h)
    xs, ys, zs = (lo[k] + h * np.arange(shape[k]) for k in range(3))
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    Q = np.stack([X.ravel(), Y.ravel(), Z.ravel()], 1)
    Fb = D.body_sdf(Q).reshape(shape).astype(np.float32)
    Fh = head_world_sdf(Q).reshape(shape).astype(np.float32)
    F = smin(Fb, Fe, 0.025)
    for _ in range(3):
        F = blur(F)
    F = np.maximum(F, -(Fh + 0.012))                          # hollow inside the head: the head has its own mesh
    check_box(F)
    V, T = surface_nets(F, lo, h)
    V, T = simplified(V, np.asarray(T), COAT_TRIS)
    log("coat", len(T), "triangles")
    # what each point of the coat comes from: the guide segment nearest it (or the bare skin)
    gi = np.clip(np.round((V - lo) / h).astype(int), 0, np.array(shape) - 1)
    sid = ID[gi[:, 0], gi[:, 1], gi[:, 2]]
    near_guide = (sid >= 0) & (Fe[gi[:, 0], gi[:, 1], gi[:, 2]] < Fb[gi[:, 0], gi[:, 1], gi[:, 2]] + 0.01)
    K = Pg.shape[1]
    gidx, seg = np.maximum(sid, 0) // (K - 1), np.maximum(sid, 0) % (K - 1)
    sdir = unit(Pg[gidx, seg + 1] - Pg[gidx, seg])
    return dict(V=V, T=T, near=near_guide, guide=gidx, sdir=sdir, white=white, groot=Rg, gpart=gpart, gkind=kind)


def skin_for_growing():
    """the plain skin (head and body) at a modest density, and its sampled distance field, to grow the guides on"""
    F, o = sample(D.skin_sdf, np.array([-0.95, -0.4, -0.01]), np.array([1.45, 0.4, 1.8]), 0.008)
    check_box(F)
    V, T = surface_nets(F, o, 0.008)
    V = D.project(D.skin_sdf, V, 2)
    part, _ = D.classify(V)
    return V, np.asarray(T), part, D.Grid(F, o, 0.008)


# ================================================================== the eyes, closed: a furred lid and a lash line
def build_closed_eyes():
    for side in (1, -1):
        E, n, u, v = D.EYES[side]
        A, B = D.EYE_HALF
        c = E - n * D.EYE_R * 0.88
        S, F = D.sphere_mesh(40, 20)
        Vl = c + S * D.EYE_R * 1.06
        q = Vl - E
        a, b = q @ u, q @ v
        keep = (q @ n > -0.012) & (D.almond(a, b) < 0.004)
        idx = -np.ones(len(Vl), int)
        idx[keep] = np.arange(keep.sum())
        Fk = F[keep[F].all(1)]
        D.mesh("lidclosed", D.to_world(Vl[keep]), idx[Fk], np.tile(BLACK_FUR, (int(keep.sum()), 1)), None)
        pts = []                                          # the lash line: a gentle smile across the lower half
        for t in np.linspace(-1, 1, 24):
            pts.append(E + u * A * 0.95 * t + v * (-B * 0.25 - B * 0.22 * (1 - t * t)))
        pts = D.surface_pts(lambda L: D.head_raw(L) - 0.0, np.array(pts), 0.0)
        pts = c + unit(pts - c) * D.EYE_R * 1.1
        Vt, Ft = D.Ub.tube(pts, np.full(len(pts), 0.0022), 6)
        D.mesh("lineclosed", D.to_world(Vt), np.array(Ft), np.tile(D.hexc("#050407"), (len(Vt), 1)), None)


# ================================================================== the skeleton (Blender axes here; written in Godot's)
bones, idx = [], {}


def bone(name, parent, at):
    idx[name] = len(bones)
    bones.append({"name": name, "parent": parent, "at": np.asarray(at, np.float64)})


HEAD_AT = np.array([0.6, 0.0, 1.15])
NECK_MID = (D.NECK_A + D.NECK_B) / 2
bone("root", "", (0, 0, 0))
bone("body", "root", (0.05, 0.0, 0.75))
bone("neck_0", "body", D.NECK_A)
bone("neck_1", "neck_0", NECK_MID)
bone("head", "neck_1", HEAD_AT)
bone("jaw", "head", D.to_world(D.JAW_HINGE))                 # the lower jaw: it closes in sleep, opens for a yawn
for i, s in enumerate((1, -1)):                              # 0: the near ear (+y)
    bone("ear_%d" % i, "head", D.to_world(D.EARS[s][0]))
LEG_PTS = {}
for side, s in (("n", 1), ("f", -1)):
    LEG_PTS[side + "f"] = [np.array(p) for p in ((0.42, 0.12 * s, 0.62), (0.33, 0.11 * s, 0.44), (0.35, 0.097 * s, 0.13),
                                                 (0.4, 0.095 * s, 0.0))]
    LEG_PTS[side + "h"] = [np.array(p) for p in ((-0.44, 0.1 * s, 0.72), (-0.3, 0.11 * s, 0.44), (-0.5, 0.1 * s, 0.18),
                                                 (-0.45, 0.1 * s, 0.0))]
for leg, p in LEG_PTS.items():
    bone("leg_%s_upper" % leg, "body", p[0])
    bone("leg_%s_lower" % leg, "leg_%s_upper" % leg, p[1])
    bone("leg_%s_paw" % leg, "leg_%s_lower" % leg, p[2])
TAIL_PTS = [D.TAIL[int(k * (len(D.TAIL) - 1) / 4)] for k in range(5)]
for k in range(4):
    bone("tail_%d" % k, "body" if k == 0 else "tail_%d" % (k - 1), TAIL_PTS[k])


def seg_dist(P, a, b):
    ab = b - a
    t = np.clip(((P - a) @ ab) / max(ab @ ab, 1e-12), 0.0, 1.0)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)


def soft(Dm, tau):
    W = np.exp(-(Dm - Dm.min(1, keepdims=True)) / tau)
    return W / W.sum(1, keepdims=True)


NECK_SEGS = [("neck_0", D.NECK_A, NECK_MID), ("neck_1", NECK_MID, HEAD_AT)]
TAIL_SEGS = [("tail_%d" % k, TAIL_PTS[k], TAIL_PTS[k + 1]) for k in range(4)]


def leg_segs(leg):
    p = LEG_PTS[leg]
    return [("leg_%s_upper" % leg, p[0], p[1]), ("leg_%s_lower" % leg, p[1], p[2]), ("leg_%s_paw" % leg, p[2], p[3])]


def along(V, segs, tau):
    Dm = np.stack([seg_dist(V, a, b) for (_, a, b) in segs], 1)
    W = soft(Dm, tau)
    o = {}
    for k, (name, _, _) in enumerate(segs):
        o[name] = o.get(name, 0) + W[:, k]
    return o


def skin_weights(V):
    """points of the skin: softly by part (head, body, neck, a leg, the tail), then along that part's bones"""
    p = D.body_parts(V)
    p["head"] = head_world_sdf(V)
    near = V[:, 1] >= 0
    names = ["head", "torso", "neck", "fleg", "hleg", "paw", "tail"]
    Pw = soft(np.stack([p[k] for k in names], 1), 0.03)
    o = {"head": Pw[:, 0], "body": Pw[:, 1]}
    for name, w in along(V, NECK_SEGS, 0.08).items():
        o[name] = o.get(name, 0) + Pw[:, 2] * w
    for k, key in ((3, "f"), (4, "h")):
        for side, m in (("n", near), ("f", ~near)):
            for name, w in along(V, leg_segs(side + key), 0.04).items():
                o[name] = o.get(name, 0) + Pw[:, k] * w * m
    front = V[:, 0] > 0                                       # paws: by the nearest leg's paw bone
    for side, m in (("n", near), ("f", ~near)):
        o["leg_%sf_paw" % side] = o.get("leg_%sf_paw" % side, 0) + Pw[:, 5] * (m & front)
        o["leg_%sh_paw" % side] = o.get("leg_%sh_paw" % side, 0) + Pw[:, 5] * (m & ~front)
    for name, w in along(V, TAIL_SEGS, 0.06).items():
        o[name] = o.get(name, 0) + Pw[:, 6] * w
    return o


def pack(wd, n):
    names = list(wd)
    W = np.stack([np.broadcast_to(np.asarray(wd[k], np.float64), (n,)) for k in names], 1)
    order = np.argsort(-W, 1)[:, :4]
    B = np.zeros((n, 4))
    WW = np.zeros((n, 4))
    for j in range(min(4, len(names))):
        B[:, j] = [idx[names[o]] for o in order[:, j]]
        WW[:, j] = W[np.arange(n), order[:, j]]
    WW /= np.maximum(WW.sum(1, keepdims=True), 1e-9)
    return B, WW


# ================================================================== build it all
D.setup()
_sphere = D.sphere_mesh
D.sphere_mesh = lambda nu, nv: _sphere(min(nu, 48), min(nv, 24))   # game-density eyes
D.build_eyes()
build_closed_eyes()
D.build_nose()
D.build_mouth()
D.EAR_T = 0.024                                               # thicker ears: the game has no ear hair to fill them
D.build_ears()
for ob in list(bpy.data.objects):                             # no cornea: the game draws the eye glossy instead
    if ob.type == "MESH" and ob.name.split(".")[0] in ("cornea",):
        bpy.data.objects.remove(ob)
Vh, Th = build_head()
coat = build_coat()

GLOSS = ("eyeball", "nose", "tongue", "tooth", "lidrim")
EMIT = {"catchlight": 2.0}
BLINK = {"eyeball": 1, "catchlight": 1, "lidrim": 1, "lidclosed": 2, "lineclosed": 2}
groups = {"lit": [], "gloss": [], "emit": []}
counts = {}


def add(name, V, T, C, N, wd, fur_len, comb, tip, trait, lift=0.4, droop=0.15):
    """one part's rows: V and comb in Blender's axes (comb a direction), fur_len per point (0: none)"""
    T = T[:, ::-1].copy()
    n = len(V)
    B, W = pack(wd, n)
    Vg = g(V)
    Ng = unit(gd(N))
    cg = unit(gd(comb))
    cg = unit(cg - Ng * np.sum(cg * Ng, 1, keepdims=True) * 0.85) * (fur_len * SCALE)[:, None]
    L = fur_len * SCALE
    cls = "emit" if name in EMIT else ("gloss" if name in GLOSS else "lit")
    rows = np.column_stack([Vg, Ng, C, np.where(fur_len > 0, tip, 0.0), np.full(n, EMIT.get(name, 0.0)),
                            np.full(n, BLINK.get(name, 0)), trait, L * lift, L * droop, cg, B, W]).astype(np.float32)
    groups[cls].append((rows, T))
    counts[name] = counts.get(name, 0) + len(T)


def form_shade(V, T, amount, smooth_steps=3):
    """a colour factor from the shape: above 1 on ridges (the tops of locks and folds), below 1 in grooves between them"""
    n = len(V)
    S = np.zeros((n, 3))
    cnt = np.zeros(n)
    for a, b in ((0, 1), (1, 2), (2, 0)):
        np.add.at(S, T[:, a], V[T[:, b]])
        np.add.at(S, T[:, b], V[T[:, a]])
        np.add.at(cnt, T[:, a], 1)
        np.add.at(cnt, T[:, b], 1)
    fn = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    N = np.zeros_like(V)
    for k in range(3):
        np.add.at(N, T[:, k], fn)
    N = unit(N)
    lap = S / np.maximum(cnt, 1)[:, None] - V                 # toward the neighbours' middle
    c = -np.sum(lap * N, 1)                                   # + on a ridge, - in a groove
    for _ in range(smooth_steps):                             # soften it over the neighbours
        Sc = np.zeros(n)
        for a, b in ((0, 1), (1, 2), (2, 0)):
            np.add.at(Sc, T[:, a], c[T[:, b]])
            np.add.at(Sc, T[:, b], c[T[:, a]])
        c = 0.5 * c + 0.5 * Sc / np.maximum(cnt, 1)
    c = c / max(np.percentile(np.abs(c), 90), 1e-9)
    return 1.0 + amount * np.tanh(c)


TOP = float(os.environ.get("COLLIE_TOP", "0.55"))             # the dark coat lighter where it faces the light
KEY = unit(np.array([0.45, 0.35, 1.0]))                         # from above, a little in front and on the near side


def top_light(N, amount):
    """a soft light baked into the dark fur, as the painting's blue-grey on the neck, shoulder and back"""
    return 1.0 + amount * D.smooth(-0.2, 0.95, N @ KEY)


def dark_or_white(C):
    """trait group from the colour: 1 the dark coat, 2 the white, 0 neither (lips, mouth)"""
    db = np.linalg.norm(C - BLACK_FUR[:3], axis=1)
    dw = np.linalg.norm(C - WHITE_FUR[:3], axis=1)
    return np.where(dw < 0.25, 2.0, np.where(db < 0.12, 1.0, 0.0))


def jaw_share(L):
    """how much a point of the head belongs to the lower jaw (nearer its surface than the upper's)"""
    return D.smooth(0.004, -0.004, D.lower(L) - D.upper(L))


# the head
Lh = D.to_head(Vh)
Nh = D.grad(head_world_sdf, Vh)
Ch, wh = D.head_colours(Lh, None)
wsm = D.smooth(0.35, 0.65, wh)
plain = D.mix(np.tile(D.BLACK_SKIN, (len(Vh), 1)), D.WHITE, wh[:, None])[:, :3]    # where the colour is the fur's own
furry = np.linalg.norm(Ch[:, :3] - plain, axis=1) < 0.01
Ch = np.where(furry[:, None], BLACK_FUR[None, :3] * (1 - wsm)[:, None] + WHITE_FUR[None, :3] * wsm[:, None], Ch[:, :3])
lnh, _, combh, _ = D.head_groom(Lh)
furh = np.where(D.lip_mask(Lh) | (D.nose_body(Lh) < 0.003), 0.0, np.clip(lnh * D.HS * 0.45, 0.003, 0.012))
wj = jaw_share(Lh)
trh = dark_or_white(Ch)
Ch = Ch * np.where(trh == 1.0, form_shade(Vh, Th, FORM * 0.5) * top_light(Nh, TOP * 0.6), 1.0)[:, None]
tiph = np.where(trh == 1.0, DARK_TIP, 0.12)
add("head", Vh, Th, Ch, Nh, {"head": 1.0 - wj, "jaw": wj}, furh, D.hdir(combh), tiph, trh, lift=0.3, droop=0.1)

# the coat
Vc, Tc = coat["V"], coat["T"]
Nc = np.zeros_like(Vc)
fn = np.cross(Vc[Tc[:, 1]] - Vc[Tc[:, 0]], Vc[Tc[:, 2]] - Vc[Tc[:, 0]])
for k in range(3):
    np.add.at(Nc, Tc[:, k], fn)
Nc = unit(Nc)
pc, _ = D.classify(Vc)
wskin = D.body_white(Vc, Nc, pc)
wguide = coat["white"][coat["guide"]]
wc = np.where(coat["near"], wguide, wskin)
wc = D.smooth(0.35, 0.65, wc)
Cc = BLACK_FUR[None, :3] * (1 - wc)[:, None] + WHITE_FUR[None, :3] * wc[:, None]
# weights: a point over a guide moves with the guide's root; a bare one with the skin under it
wroot = skin_weights(coat["groot"])
wbare = skin_weights(Vc)
wd = {}
for k in set(wroot) | set(wbare):
    a = np.asarray(wroot.get(k, 0.0), np.float64)
    a = a[coat["guide"]] if a.ndim else np.full(len(Vc), float(a))
    b = np.asarray(wbare.get(k, 0.0), np.float64)
    b = b if b.ndim else np.full(len(Vc), float(b))
    wd[k] = np.where(coat["near"], a, b)
combc = np.where(coat["near"][:, None], coat["sdir"], np.array([-1.0, 0.0, -0.4]))
furc = np.where(coat["near"], 0.014, 0.007)
shade = form_shade(Vc, Tc, FORM) * top_light(Nc, TOP)
Cc = Cc * np.where(wc > 0.5, 1.0 + (form_shade(Vc, Tc, FORM) - 1.0) * 0.35, shade)[:, None]   # the white: shape only
add("coat", Vc, Tc, Cc, Nc, wd, furc, combc, np.where(wc > 0.5, 0.15, DARK_TIP), np.where(wc > 0.5, 2.0, 1.0),
    lift=0.35, droop=0.2)

# the face's parts and the ears
for ob in list(bpy.data.objects):
    if ob.type != "MESH":
        continue
    name = ob.name.split(".")[0]
    if name in ("skin",) or name.startswith("fur"):
        continue
    V, T, C = mesh_arrays(ob)
    V = np.asarray(V)
    if len(T) == 0:
        continue
    cap = {"nose": 1600, "ear": 1800}.get(name)
    if cap and len(T) > cap:                                  # simplified, keeping colours by the nearest old point
        V2, T2 = simplified(V, T, cap)
        from mathutils.kdtree import KDTree
        kd = KDTree(len(V))
        for i, p in enumerate(V):
            kd.insert(p, i)
        kd.balance()
        C = C[[kd.find(p)[1] for p in V2]]
        V, T = V2, T2
    fn = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    N = np.zeros_like(V)
    for k in range(3):
        np.add.at(N, T[:, k], fn)
    N = unit(N)
    n = len(V)
    if name == "ear":
        i = 0 if V.mean(0)[1] > 0 else 1
        C = np.where((C.mean(1) < 0.03)[:, None], BLACK_FUR[None, :3], C)
        C = np.where(np.arange(n)[:, None] < n // 2, C * 0.7, C)        # the inside of the ear a little darker
        add(name, V, T, C, N, {"ear_%d" % i: np.ones(n)}, np.full(n, 0.006), np.tile([0.0, 0.0, 1.0], (n, 1)), DARK_TIP,
            np.ones(n), lift=0.3, droop=0.0)
    elif name == "lidclosed":
        add(name, V, T, C, N, {"head": np.ones(n)}, np.full(n, 0.004), np.tile([-1.0, 0.0, -0.3], (n, 1)), 0.1,
            np.ones(n))
    elif name == "tongue":
        add(name, V, T, C, N, {"jaw": np.ones(n)}, np.zeros(n), np.tile([1.0, 0.0, 0.0], (n, 1)), 0.0, np.zeros(n))
    else:
        add(name, V, T, C, N, {"head": np.ones(n)}, np.zeros(n), np.tile([1.0, 0.0, 0.0], (n, 1)), 0.0, np.zeros(n))

blob = bytearray()
meta = {"bones": [{"name": b["name"], "parent": b["parent"], "at": g(b["at"]).tolist()} for b in bones], "groups": {}}
for cls, parts in groups.items():
    if not parts:
        continue
    rows = np.concatenate([p[0] for p in parts])
    base, Ts = 0, []
    for r, T in parts:
        Ts.append(T + base)
        base += len(r)
    T = np.concatenate(Ts)
    meta["groups"][cls] = {"verts": len(rows), "stride": rows.shape[1], "tris": len(T), "vert_offset": len(blob)}
    blob += rows.tobytes()
    meta["groups"][cls]["index_offset"] = len(blob)
    blob += T.astype(np.int32).tobytes()

# places: the top of the head, the mouth, the neck (a collar), the tail; the ground
top = D.to_world(D.ray_hit(D.head_raw, np.array([-0.02, 0.0, 0.0]), np.array([-0.1, 0.0, 1.0])))
mouth = D.to_world(np.array([0.16, 0.0, -0.1]))
neck_c = D.NECK_A * 0.35 + D.NECK_B * 0.65
neck_axis = gd(D.NECK_B - D.NECK_A)
tail_c = D.TAIL[int(0.4 * (len(D.TAIL) - 1))]
tail_axis = gd(D.TAIL[int(0.47 * (len(D.TAIL) - 1))] - D.TAIL[int(0.33 * (len(D.TAIL) - 1))])
feet = min(float(np.min(p[0][:, 1])) for cls in groups for p in groups[cls])
meta.update({
    "attr": ["pos3", "nrm3", "col3", "tip", "emit", "blink", "trait", "lift", "droop", "comb3", "bones4", "weights4"],
    "camera": {"center": [0.0, 2.6, 0.0], "azimuth": 40.0, "pitch": 9.0, "ortho": 8.0},
    "ground": [0.0, round(feet, 4), 0.0],
    "places": {"head": {"bone": "head", "at": g(top).tolist(), "size": 0.3 * SCALE},
               "mouth": {"bone": "head", "at": g(mouth).tolist(), "size": 0.1},
               "neck": {"bone": "neck_1", "at": g(neck_c).tolist(), "size": 0.2 * SCALE, "axis": neck_axis.tolist()},
               "tail": {"bone": "tail_1", "at": g(tail_c).tolist(), "size": 0.06 * SCALE, "axis": tail_axis.tolist()}},
    "head_forward": gd(D.hdir(np.array([1.0, 0.0, -0.1]))).tolist(),
    "jaw_axis": gd(D.hdir(np.array([0.0, 1.0, 0.0]))).tolist(),   # turning about it by + closes the mouth (the mirror)
    "jaw_open": 12.0,
    "lie_drop": round(float(0.42 * SCALE), 3),
    "tail_lie": 0.6,
    "triangles": counts,
})
os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
open(out, "wb").write(bytes(blob))
json.dump(meta, open(os.path.splitext(out)[0] + ".json", "w"), indent=1)
print("collie:", {k: v["verts"] for k, v in meta["groups"].items()}, "triangles", sum(counts.values()), "bones", len(bones))
print("by part:", sorted(counts.items(), key=lambda x: -x[1]))


# ================================================================== a look at it in Blender (--preview DIR)
if PREVIEW:
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob)
    vc = bpy.data.materials.new("vc")
    vc.use_nodes = True
    at = vc.node_tree.nodes.new("ShaderNodeAttribute")
    at.attribute_name = "Col"
    bs = vc.node_tree.nodes["Principled BSDF"]
    vc.node_tree.links.new(at.outputs["Color"], bs.inputs["Base Color"])
    bs.inputs["Roughness"].default_value = 0.6
    for cls, parts in groups.items():
        for rows, T in parts:
            V = rows[:, 0:3].astype(np.float64)
            Vb = np.stack([V[:, 0], V[:, 2], V[:, 1]], 1)
            D.mesh("m", Vb, T[:, ::-1], rows[:, 6:9], vc)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.samples = 48
    sc.render.film_transparent = True
    sc.render.resolution_x = sc.render.resolution_y = 900
    sun = bpy.data.lights.new("sun", "SUN")
    sun.energy = 3.5
    so = bpy.data.objects.new("sun", sun)
    so.rotation_euler = (math.radians(50), 0, math.radians(30))
    bpy.context.collection.objects.link(so)
    sc.world = bpy.data.worlds.new("w")
    sc.world.use_nodes = True
    sc.world.node_tree.nodes["Background"].inputs["Strength"].default_value = 0.8
    for vname, az, el in (("side", 0.0, 4.0), ("three", 40.0, 9.0), ("face", 30.0, 6.0)):
        cam = bpy.data.cameras.new("c")
        cam.type = "ORTHO"
        cam.ortho_scale = 7.0 if vname != "face" else 3.0
        co = bpy.data.objects.new("c", cam)
        bpy.context.collection.objects.link(co)
        a, e = math.radians(az), math.radians(el)
        tgt = np.array([0.0, 0.0, 2.6]) if vname != "face" else g(D.to_world(np.array([0.05, 0, 0])))[[0, 2, 1]]
        pos = tgt + np.array([math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)]) * 20
        from mathutils import Vector
        co.location = Vector(pos)
        co.rotation_euler = (Vector(tgt) - Vector(pos)).to_track_quat("-Z", "Y").to_euler()
        sc.camera = co
        sc.render.filepath = os.path.join(os.path.abspath(PREVIEW), vname + ".png")
        bpy.ops.render.render(write_still=True)
