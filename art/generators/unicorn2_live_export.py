"""The new unicorn (unicorn2.py) for the game: built standing (all four hooves down, head straight) at game density,
with closed eyes too, then given a skeleton and skin weights and written in the format game/tools/build_unicorn.gd
reads (the same as unicorn_live_export.py wrote for the first unicorn).

Bones (Godot axes): root, body, neck_0..2, head, ear_0 (near) and ear_1, for each leg (nh, nf, fh, ff) upper, lower and
hoof, and tail_0..3. Weights: the body by which part of the shape each point belongs to (body, neck, head, a leg),
softly, then along that part's bones; the hair by the nearest neck or tail bones; everything on the head by the head;
the ears by their bones; hooves and rose cuffs by their leg. No fur (the coat is smooth).
Per vertex: position, normal, colour, emission, blink piece (1 shown open, 2 shown closed), trait (1 coat, 2 mane),
fur (none), four bones and weights.

Run:  blender -b --factory-startup -P unicorn2_live_export.py -- ../exports/unicorn2_live.bin"""
import os, sys, json, math
os.environ["UNI2_STAND"] = "1"
import bpy, bmesh
import numpy as np

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = argv[0] if argv else "unicorn2_live.bin"
sys.argv = [sys.argv[0], "--", "unused", "--game"]          # unicorn2.py reads its options from here
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unicorn2 as G
import unicorn2_shape as U

SCALE = 0.8                                                 # the game's unicorn about the fox's size
BODY_TRIS = 9000                                            # the sculpted body is simplified to this


# Blender's x, z, y: the model's near side (+y here, with the garland, freckles and crown) toward the game's camera,
# which looks from Godot's +z. That is a mirror, so triangles are turned round too.
def g(v):
    v = np.asarray(v, np.float64)
    return np.stack([v[..., 0], v[..., 2], v[..., 1]], -1) * SCALE


def gd(v):
    v = np.asarray(v, np.float64)
    return np.stack([v[..., 0], v[..., 2], v[..., 1]], -1)


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
    if ca is not None:
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


def decimate(ob, target):
    tris = sum(len(p.vertices) - 2 for p in ob.data.polygons)
    if tris <= target:
        return
    mod = ob.modifiers.new("d", "DECIMATE")
    mod.ratio = target / tris
    bpy.context.view_layer.objects.active = ob
    with bpy.context.temp_override(object=ob):
        bpy.ops.object.modifier_apply(modifier=mod.name)


# ------------------------------------------------------------------ build it
G.setup()
body = G.build_body()
G.build_eyes()
G.build_closed_eyes()
G.build_ears()
G.build_horn()
G.build_hooves()
G.build_hair()
G.build_flowers()
G.build_sparkle(body)
decimate(body, BODY_TRIS)

# ------------------------------------------------------------------ the skeleton (Blender axes here; written in Godot's)
bones = []
idx = {}


def bone(name, parent, at):
    idx[name] = len(bones)
    bones.append({"name": name, "parent": parent, "at": np.asarray(at, np.float64)})


NECK = [np.array(p) for p, r in U.NECK]
HEAD_AT = U.HEAD_PIVOT + np.array([0.06, 0.0, 0.25])
bone("root", "", (0, 0, 0))
bone("body", "root", (0.0, 0.0, 2.35))
bone("neck_0", "body", NECK[0])
bone("neck_1", "neck_0", NECK[1])
bone("neck_2", "neck_1", (NECK[2] + NECK[3]) / 2 - np.array([0.0, 0.0, 0.1]))
bone("head", "neck_2", HEAD_AT)
for i, (b, axis) in enumerate(G.EAR_BASES):                  # 0: the near ear (+y)
    bone("ear_%d" % i, "head", U.head_to_world(b))
LEG_PTS = {}
for leg, j in U.LEGS.items():
    pts = [np.array(p) for p, r in j]
    LEG_PTS[leg] = pts
    bone("leg_%s_upper" % leg, "body", pts[0])
    bone("leg_%s_lower" % leg, "leg_%s_upper" % leg, pts[2])
    bone("leg_%s_hoof" % leg, "leg_%s_lower" % leg, pts[3])
tc = np.mean([G.resample(c, 40) for c in G.TAIL_CURVES], axis=0)
TAIL_PTS = [tc[int(k * 39 / 4)] for k in range(5)]
for k in range(4):
    bone("tail_%d" % k, "body" if k == 0 else "tail_%d" % (k - 1), TAIL_PTS[k])


def seg_dist(P, a, b):
    ab = b - a
    t = np.clip(((P - a) @ ab) / max(ab @ ab, 1e-12), 0.0, 1.0)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)


def soft(D, tau):
    W = np.exp(-(D - D.min(1, keepdims=True)) / tau)
    return W / W.sum(1, keepdims=True)


NECK_SEGS = [("neck_0", NECK[0], NECK[1]), ("neck_1", NECK[1], NECK[2]), ("neck_2", NECK[2], HEAD_AT)]
TAIL_SEGS = [("tail_%d" % k, TAIL_PTS[k], TAIL_PTS[k + 1]) for k in range(4)]


def leg_segs(leg):
    p = LEG_PTS[leg]
    return [("leg_%s_upper" % leg, p[0], p[1]), ("leg_%s_upper" % leg, p[1], p[2]), ("leg_%s_lower" % leg, p[2], p[3]),
            ("leg_%s_hoof" % leg, p[3], p[4] - np.array([0, 0, 0.3]))]


def along(V, segs, tau):
    D = np.stack([seg_dist(V, a, b) for (_, a, b) in segs], 1)
    W = soft(D, tau)
    out = {}
    for k, (name, _, _) in enumerate(segs):
        out[name] = out.get(name, 0) + W[:, k]
    return out


def body_weights(V):
    """the sculpted surface: softly by part, then along the part's bones"""
    p = U.parts(V)
    names = ["body", "neck", "head"] + list(U.LEGS)
    D = np.stack([p[k] for k in names], 1)
    Pw = soft(D, 0.05)
    out = {"body": Pw[:, 0], "head": Pw[:, 2]}
    for name, w in along(V, NECK_SEGS, 0.12).items():
        out[name] = out.get(name, 0) + Pw[:, 1] * w
    for k, leg in enumerate(U.LEGS):
        for name, w in along(V, leg_segs(leg), 0.06).items():
            out[name] = out.get(name, 0) + Pw[:, 3 + k] * w
    return out


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


def weights_for(name, V, ob):
    n = len(V)
    if name == "body" or name == "glitter":
        return body_weights(V)
    if name in ("eye", "glint", "lid", "lash", "lowlid", "lidclosed", "lineclosed", "lashclosed", "horn", "freckles", "forelock") \
            or name.startswith("crown"):
        return {"head": np.ones(n)}
    if name == "ear":
        c = V.mean(0)
        i = 0 if c[1] > 0 else 1
        return {"ear_%d" % i: np.ones(n)}
    if name == "mane":
        w = along(V, NECK_SEGS + [("head", HEAD_AT, HEAD_AT + np.array([0.3, 0, 0.5]))], 0.18)
        return w
    if name == "tail":
        return along(V, TAIL_SEGS, 0.15)
    if name == "hoof" or name.startswith("cuffs"):
        # by the nearest leg's lower bones, point by point
        out = {}
        Dl = np.stack([seg_dist(V, LEG_PTS[l][2], LEG_PTS[l][4] - np.array([0, 0, 0.3])) for l in U.LEGS], 1)
        which = np.argmin(Dl, 1)
        for k, leg in enumerate(U.LEGS):
            m = which == k
            for bn, w in along(V, leg_segs(leg)[2:], 0.04).items():
                out[bn] = out.get(bn, 0) + w * m
        return out
    if name.startswith("garland"):
        return {"body": np.ones(n)}
    return body_weights(V)


GLOSS = ("eye", "horn", "hoof")
EMIT = {"glint": 2.5, "freckles": 0.5, "glitter": 1.2}
BLINK = {"eye": 1, "glint": 1, "lid": 1, "lash": 1, "lowlid": 1, "lidclosed": 2, "lineclosed": 2, "lashclosed": 2}

groups = {"lit": [], "gloss": [], "emit": []}
counts = {}
COAT = np.array([G.COAT_TOP[:3], G.COAT_MID[:3], G.COAT_SHADE[:3], G.LEG_HI[:3], G.LEG_LO[:3]])
for ob in list(bpy.data.objects):
    if ob.type != "MESH":
        continue
    name = ob.name.split(".")[0]
    V, T, C = mesh_arrays(ob)
    if len(T) == 0:
        continue
    T = T[:, ::-1].copy()
    counts[name] = counts.get(name, 0) + len(T)
    n = len(V)
    wd = weights_for(name, V, ob)
    B, W = pack(wd, n)
    Vg = g(V)
    fn = np.cross(Vg[T[:, 1]] - Vg[T[:, 0]], Vg[T[:, 2]] - Vg[T[:, 0]])
    N = np.zeros_like(Vg)
    for k in range(3):
        np.add.at(N, T[:, k], fn)
    if name == "body":
        N = gd(U.grad(U.sdf, V))
    N /= np.maximum(np.linalg.norm(N, axis=1, keepdims=True), 1e-12)
    # which trait recolours it: the coat (where the colour is the coat's own), the mane (all the hair), else nothing
    trait = np.zeros(n)
    if name in ("body", "ear", "lidclosed"):
        dmin = np.min(np.linalg.norm(C[:, None, :] - COAT[None], axis=2), 1)
        trait = np.where(dmin < 0.08, 1.0, 0.0)
    if name in ("mane", "forelock", "tail"):
        trait[:] = 2.0
    cls = "emit" if name in EMIT else ("gloss" if name in GLOSS else "lit")
    rows = np.column_stack([Vg, N, C, np.zeros(n), np.full(n, EMIT.get(name, 0.0)), np.full(n, BLINK.get(name, 0)), trait,
                            np.zeros((n, 5)), B, W]).astype(np.float32)
    groups[cls].append((rows, T))

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

# places: the top of the head, the mouth, the neck, the tail; the ground; the camera the game draws with
c, r = U.CRANIUM
top = U.head_to_world(U._ray_hit(U._head_raw, c, np.array([-0.1, 0.0, 1.0])))
mouth = U.head_to_world(np.array([3.0, 0.0, 3.95]))
neck_c = NECK[0] * 0.45 + NECK[1] * 0.55
neck_axis = gd(NECK[2] - NECK[0])
neck_r = float(np.median(np.abs(U.neck_sdf(neck_c[None] + np.array([[0, s, 0] for s in np.linspace(0.2, 1.0, 40)])) )) * 0 + 0.55)
tail_c = tc[int(0.55 * 39)]
tail_axis = gd(tc[int(0.62 * 39)] - tc[int(0.48 * 39)])
hooves = min(float(np.min(p[0][:, 1])) for cls in groups for p in groups[cls])
meta.update({
    "attr": ["pos3", "nrm3", "col3", "tip", "emit", "blink", "trait", "lift", "droop", "comb3", "bones4", "weights4"],
    "camera": {"center": [0.0, 3.0 * SCALE, 0.0], "azimuth": 40.0, "pitch": 9.0, "ortho": 8.0},
    "ground": [0.0, round(hooves, 4), 0.0],
    "places": {"head": {"bone": "head", "at": g(top).tolist(), "size": 0.85 * SCALE},
               "mouth": {"bone": "head", "at": g(mouth).tolist(), "size": 0.1},
               "neck": {"bone": "neck_0", "at": g(neck_c).tolist(), "size": 0.58 * SCALE, "axis": neck_axis.tolist()},
               "tail": {"bone": "tail_2", "at": g(tail_c).tolist(), "size": 0.18 * SCALE, "axis": tail_axis.tolist()}},
    "head_forward": gd(U.head_dir(np.array([1.0, 0.0, -0.1]))).tolist(),
    "lie_drop": round(float((2.35 - 0.66 - 0.12) * SCALE), 3),
    "tail_lie": 0.25,
    "triangles": counts,
})
open(out, "wb").write(bytes(blob))
json.dump(meta, open(os.path.splitext(out)[0] + ".json", "w"), indent=1)
print("unicorn2:", {k: v["verts"] for k, v in meta["groups"].items()}, "triangles", sum(counts.values()), "bones", len(bones))
print("by part:", sorted(counts.items(), key=lambda x: -x[1]))
