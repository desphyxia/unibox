"""The unicorn for live 3D in the game: one standing model with a skeleton, built by unicorn3d.py.

Unlike the fox (fox_live_export.py, four separately built poses matched point for point), the unicorn is exported once,
standing, with bones from its own pose numbers and skin weights; game/tools/build_unicorn.gd then makes every pose and
clip by turning the bones. Parts:
  body      the fused torso, neck and legs (weighted to body, neck, leg bones by distance, each leg only on its side)
  head      head, horn, face, eyes, forelock (head bone); ears and their insides (ear bones)
  mane      the hair sheets on the neck (neck bones and head, by distance along the crest)
  tail      the tail locks (tail bones, by place along the tail)
  hoof      hooves (each leg's lowest bone)
Eyes: the open eye pieces and the closed lids are both built; the game shows one set (blink piece 1 open, 2 closed).
Fur: short shell fur on the coat (body and head, none on the muzzle), combed down and back; none on hair or hooves.
Traits: each vertex says which trait recolours it: 1 coat (body, head, ears), 2 mane (mane, tail, forelock), 0 none.

Per vertex: position, normal, colour (alpha: how much lighter the fur tips are), surface (0 lit, 1 glossy, 2 glowing),
emission, blink piece, trait group, fur (lift length, droop length, combed vector), four bones and weights.
Godot's axes: x, z, -y of Blender's.

Run:  blender -b --factory-startup -P unicorn_live_export.py -- ../exports/unicorn_live.bin
Then game/tools/build_unicorn.gd turns it into the model the game draws."""
import bpy, bmesh, sys, os, json, math
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import unicorn3d as U
import seahorse3d as K
import artgen5 as A

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = argv[0] if argv else "unicorn_live.bin"
S = U.S

BUDGET = {"body": 3200, "head": 1400, "hair_sheet": 520, "lock": 110, "ribbon": 160, "horn": 300, "ear": 160,
          "ear_in": 80, "hoof": 140, "eye_base": 160, "eye_iris": 160, "eye_pupil": 90, "eye_glint": 30, "eye_glint2": 24,
          "lid": 120, "lowlid": 70, "lash": 40, "mouth": 120, "nostril": 70, "star": 60}
OTHER = 160
SKIP = ("sparkle", "ground", "shadow", "wing", "petal", "leaf", "fcentre", "stamen")
EYE_OPEN = ("eye_base", "eye_iris", "eye_pupil", "eye_glint", "eye_glint2", "lid", "lash", "lowlid")


def g(v):
    v = np.asarray(v, np.float64)
    return np.stack([v[..., 0], v[..., 2], -v[..., 1]], -1)


def base(name):
    return name.split(".")[0]


class UniLive(U.Uni3D):
    """the standing unicorn, with the closed eyes built as well (for blinking)"""

    def build_face(self):
        before = set(o.name for o in bpy.data.objects)
        self.pose["eye"] = "open"
        super().build_face()
        self.blink_open = [o for o in bpy.data.objects if o.name not in before and base(o.name) in EYE_OPEN]
        before = set(o.name for o in bpy.data.objects)
        for sgn in (-1, 1):
            C, out_, ex, ez = self.head_frame(640, 207, sgn, 0.7)
            tau = math.radians(14)
            ex2 = ex * math.cos(tau) - ez * math.sin(tau)
            ez2 = ez * math.cos(tau) + ex * math.sin(tau)
            k = 1.0 if sgn == U.NEAR else 0.93
            self.eye_closed(C, out_, ex2, ez2, 0.25 * self.hs * k, 0.22 * self.hs * k)
        self.blink_closed = [o for o in bpy.data.objects if o.name not in before]


def mesh_arrays(ob):
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    me = bpy.data.meshes.new("tmp")
    bm.to_mesh(me)
    bm.free()
    nv = len(me.vertices)
    co = np.empty(nv * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(nv, 3).astype(np.float64)
    tri = np.empty(len(me.polygons) * 3, np.int64)
    me.polygons.foreach_get("vertices", tri)
    tri = tri.reshape(-1, 3)
    col = None
    ca = me.color_attributes.get("Col")
    if ca is not None:
        raw = np.empty(len(ca.data) * 4, np.float32)
        ca.data.foreach_get("color", raw)
        raw = raw.reshape(-1, 4)[:, :3].astype(np.float64)
        if ca.domain == "CORNER":
            lv = np.empty(len(me.loops), np.int64)
            me.loops.foreach_get("vertex_index", lv)
            acc = np.zeros((nv, 3)); cnt = np.zeros(nv)
            np.add.at(acc, lv, raw); np.add.at(cnt, lv, 1)
            col = acc / np.maximum(cnt, 1)[:, None]
        else:
            col = raw
    bpy.data.meshes.remove(me)
    M = np.array(ob.matrix_world)
    co = co @ M[:3, :3].T + M[:3, 3]
    if col is None:                                     # a plain material: its base colour everywhere
        c = (0.8, 0.8, 0.8)
        mat = ob.data.materials[0] if ob.data.materials else None
        if mat and mat.use_nodes:
            for nd in mat.node_tree.nodes:
                if nd.type == "BSDF_PRINCIPLED":
                    c = tuple(nd.inputs["Base Color"].default_value)[:3]
        col = np.tile(np.array(c, np.float64), (len(co), 1))
    return co, tri, col


def vnormals(V, T):
    fn = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    n = np.zeros_like(V)
    for k in range(3):
        np.add.at(n, T[:, k], fn)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def decimate(V, T, C, target):
    """a simpler copy of a triangle mesh; colours follow each kept point from its nearest original point"""
    if len(T) <= target:
        return V.copy(), T.copy(), C.copy()
    me = bpy.data.meshes.new("dec")
    me.from_pydata(V.tolist(), [], T.tolist())
    ob = bpy.data.objects.new("dec", me)
    bpy.context.collection.objects.link(ob)
    mod = ob.modifiers.new("d", "DECIMATE")
    mod.ratio = target / len(T)
    dg = bpy.context.evaluated_depsgraph_get()
    em = ob.evaluated_get(dg).to_mesh()
    bm = bmesh.new()
    bm.from_mesh(em)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    V2 = np.array([tuple(v.co) for v in bm.verts], np.float64)
    T2 = np.array([[v.index for v in f.verts] for f in bm.faces], np.int64)
    bm.free()
    ob.evaluated_get(dg).to_mesh_clear()
    bpy.data.objects.remove(ob)
    bpy.data.meshes.remove(me)
    from mathutils.kdtree import KDTree
    kd = KDTree(len(V))
    for i, p in enumerate(V.tolist()):
        kd.insert(p, i)
    kd.balance()
    C2 = np.array([C[kd.find(p)[1]] for p in V2.tolist()])
    return V2, T2, C2


# ================================================================== the standing unicorn
K.setup_scene(True)
uni = UniLive(U.BLOOM, "stand", dict(wings=False, flowers=False))
pose, dy = uni.pose, uni.dy
head_names = set(o.name for o in uni.head_group)
open_names = set(o.name for o in uni.blink_open)
closed_names = set(o.name for o in uni.blink_closed)


def p3(x, y, lat=0.0):
    return g(np.array(U.P3(x, y + dy, lat)))


# ------------------------------------------------------------------ bones (Godot axes), from the pose numbers
bones = []                                  # name, parent, position


def bone(name, parent, at):
    bones.append({"name": name, "parent": parent, "at": [float(a) for a in at]})


hx, hy = uni.hx, uni.hy
crest = [p3(x, y) for (x, y) in pose["crest"]]          # poll down to the withers
throat = [p3(x, y) for (x, y) in pose["throat"]]        # chest up to the jaw
neck_mid = [(crest[len(crest) - 1 - k] + throat[k]) / 2 for k in range(min(len(crest), len(throat)))]   # withers/chest .. poll/jaw
hips = [p3(*pose["near"]["nh"][0][:2]), p3(*pose["near"]["nf"][0][:2])]
body_c = (hips[0] + hips[1]) / 2 + np.array([0, 0.15, 0])
bone("root", "", [0, 0, 0])
bone("body", "root", body_c)
for k in range(3):
    bone("neck_%d" % k, "body" if k == 0 else "neck_%d" % (k - 1), neck_mid[k])
head_at = p3(hx, hy + 40)                                # the head turns about the top of the neck
bone("head", "neck_2", head_at)
th = math.radians(uni.hang)
head_fwd = np.array([math.cos(th), -math.sin(th), 0.0])  # Godot axes of uni.fwd
for ob in uni.head_group:                                # each ear turns about its base: the lowest fifth of it
    if base(ob.name) == "ear":
        V, _, _ = mesh_arrays(ob)
        V = g(V)
        low = V[np.argsort(V[:, 1])[: max(3, len(V) // 5)]].mean(0)
        bone("ear_%d" % (0 if V[:, 2].mean() > 0 else 1), "head", low)
leg_bones = {}
for side, legs in (("near", pose["near"]), ("far", pose["far"])):
    for key, ctrl in legs.items():
        sgn = -1 if side == "near" else 1
        hind = key.endswith("h")
        off = (34 if hind else 30) * sgn
        joints = [ctrl[0], ctrl[2], ctrl[-3], ctrl[-1]] if hind else [ctrl[0], ctrl[2], ctrl[-3], ctrl[-1]]
        names = []
        for j, nm in enumerate(("upper", "lower", "hoof")):
            x, y = joints[j][0], joints[j][1]
            lat = off * (0.7 if j == 0 else 1.0)
            name = "leg_%s_%s" % (key, nm)
            bone(name, "body" if j == 0 else names[-1], p3(x, y, lat))
            names.append(name)
        leg_bones[key] = {"names": names, "pts": [p3(c[0], c[1], off * (0.7 if i == 0 else 1.0)) for i, c in enumerate(joints)], "side": sgn}
t0 = pose["tail"]
tail_curve = A.hair_curve((t0["root"][0], t0["root"][1] + dy), t0["ang"], t0["length"], 40, 0.6, t0["droop"], 30)
tail_pts = [g(np.array(Vector(((x - 400) * S, -U.NEAR * 0.55 * (k / 30) ** 1.6, (640 - y) * S)))) for k, (x, y) in enumerate(tail_curve)]
for k in range(4):
    bone("tail_%d" % k, "body" if k == 0 else "tail_%d" % (k - 1), tail_pts[int(k * 29 / 4)])
bone_idx = {b["name"]: i for i, b in enumerate(bones)}


def seg_dist(P, a, b):
    ab = b - a
    t = np.clip(((P - a) @ ab) / max(ab @ ab, 1e-12), 0.0, 1.0)
    return np.linalg.norm(P - (a + t[:, None] * ab), axis=1)


def blend_weights(P, segs, tau=0.06, reach=0.22):
    """each point's bones: the nearest segments, softly (segs: [(bone, a, b)])"""
    D = np.stack([seg_dist(P, a, b) for (_, a, b) in segs], 1)
    dmin = D.min(1, keepdims=True)
    W = np.exp(-(D - dmin) / tau) * (D - dmin < reach)
    W /= W.sum(1, keepdims=True)
    return W, [s[0] for s in segs]


# segments for the body: the torso, the neck chain, every leg's bones
torso = [("body", p3(*pose["near"]["nh"][0][:2]) + [0, 0.2, 0], p3(*pose["near"]["nf"][0][:2]) + [0, 0.2, 0])]
neck_segs = [("neck_%d" % k, neck_mid[k], neck_mid[k + 1] if k + 1 < len(neck_mid) else head_at) for k in range(3)]
neck_segs.append(("head", head_at, head_at + (head_at - neck_mid[2]) * 0.5))
leg_segs = {}
for key, lb in leg_bones.items():
    leg_segs[key] = [(lb["names"][j], lb["pts"][j], lb["pts"][j + 1]) for j in range(3)]


# ------------------------------------------------------------------ the parts
groups = {"lit": [], "gloss": [], "emit": []}          # (V, T, C, extra per vertex)
head_pts = []
body_pts = []
GLOSS = ("eye_base", "eye_iris", "eye_pupil", "horn", "hoof")
EMIT = {"eye_glint": 2.5, "eye_glint2": 2.5}
fwd = np.array([1.0, 0.0, 0.0])
counts = {}
for ob in list(bpy.data.objects):
    if ob.type != "MESH" or base(ob.name).startswith(SKIP):
        continue
    nm = base(ob.name)
    V, T, C = mesh_arrays(ob)
    if len(T) == 0:
        continue
    V, T, C = decimate(V, T, C, BUDGET.get(nm if not nm.startswith("hoof") else "hoof", OTHER))
    V = g(V)
    N = vnormals(V, T)
    n = len(V)
    counts[nm] = counts.get(nm, 0) + len(T)
    W = np.zeros((n, 4)); B = np.zeros((n, 4), np.int64)

    def put(weights, names):
        order = np.argsort(-weights, 1)[:, :4]
        for i in range(n):
            ws = weights[i, order[i]]
            ws = ws / max(ws.sum(), 1e-12)
            for j in range(min(4, len(names))):
                B[i, j] = bone_idx[names[order[i, j]]]
                W[i, j] = ws[j]

    trait, fur_len = 0, np.zeros(n)
    if ob.name in head_names:
        if nm in ("ear", "ear_in"):
            side = 0 if V[:, 2].mean() > 0 else 1              # 0: the near ear (toward the camera)
            name = "ear_%d" % side
            put(np.ones((n, 1)), [name if name in bone_idx else "head"])
            trait = 1 if nm == "ear" else 0
            fur_len[:] = 0.02 if nm == "ear" else 0.0
        else:
            put(np.ones((n, 1)), ["head"])
            if nm == "head":
                trait = 1
                # short fur on the head, fading out toward the muzzle
                s_ = (V - head_at) @ head_fwd
                f_ = (s_ - s_.min()) / max(s_.max() - s_.min(), 1e-9)
                fur_len[:] = 0.022 * (1.0 - np.clip((f_ - 0.45) / 0.2, 0.0, 1.0))
                head_pts.append(V)
            elif nm in ("lock", "ribbon"):
                trait = 2
    elif nm == "body":
        trait = 1
        segs = torso + neck_segs[:3] + [s for k in leg_segs for s in leg_segs[k]]
        Wb, names = blend_weights(V, segs)
        # a leg's bones only for points on its side (and below the body's middle)
        for k, lb in leg_bones.items():
            wrong = (np.sign(V[:, 2]) != -lb["side"]) & (np.abs(V[:, 2]) > 0.06)
            for j, (bn, _, _) in enumerate(leg_segs[k]):
                Wb[wrong, names.index(bn)] = 0.0
        Wb /= np.maximum(Wb.sum(1, keepdims=True), 1e-12)
        put(Wb, names)
        fur_len[:] = 0.045
        body_pts.append(V)
    elif nm == "hair_sheet":
        trait = 2
        Wb, names = blend_weights(V, neck_segs, tau=0.12, reach=0.4)
        put(Wb, names)
    elif nm in ("lock", "ribbon"):
        trait = 2
        segs = [("tail_%d" % k, tail_pts[int(k * 29 / 4)], tail_pts[min(29, int((k + 1) * 29 / 4))]) for k in range(4)]
        Wb, names = blend_weights(V, segs, tau=0.15, reach=0.6)
        put(Wb, names)
    elif nm.startswith("hoof"):
        put(np.ones((n, 1)), [leg_bones[nm.split("_")[1]]["names"][2]])
    else:
        Wb, names = blend_weights(V, torso + neck_segs)
        put(Wb, names)
    blink = np.full(n, 1.0 if ob.name in open_names else (2.0 if ob.name in closed_names else 0.0))
    # fur: combed down and back along the surface; lifts a little, droops a little
    want = np.tile(np.array([-0.6, -0.8, 0.0]), (n, 1))
    comb = want - N * (want * N).sum(1, keepdims=True)
    comb /= np.maximum(np.linalg.norm(comb, axis=1, keepdims=True), 1e-9)
    comb *= fur_len[:, None] * 0.9
    lift = fur_len * 0.45
    droop = fur_len * 0.15
    tip = np.where(fur_len > 0, 0.35, 0.0)
    cls = "emit" if nm in EMIT else ("gloss" if nm in GLOSS or nm.startswith("hoof") else "lit")
    emit = EMIT.get(nm, 0.0)
    extra = np.column_stack([np.full(n, emit), blink, np.full(n, trait), lift, droop, comb, B, W])
    groups[cls].append((V, N, C, tip, T, extra))

# ------------------------------------------------------------------ places, ground, camera
ground_y = float(min(V[:, 1].min() for cls in groups for (V, *_r) in groups[cls]))
H = np.concatenate(head_pts)
top = H[np.argsort(-H[:, 1])[:40]].mean(0)               # the crown of the head, between the ears
s_ = (H - head_at) @ head_fwd
front = H[s_ > np.percentile(s_, 92)]
mouth = front[front[:, 1] < np.median(front[:, 1])].mean(0)
half = float(np.abs(H[H[:, 1] > top[1] - 0.45][:, 2] - top[2]).max())
Bd = np.concatenate(body_pts)
axis = neck_mid[2] - neck_mid[0]
L = np.linalg.norm(axis); axis = axis / L
neck_c = neck_mid[0] + axis * L * 0.3
d = Bd - neck_c
along_ = d @ axis
ring = d[np.abs(along_) < 0.08] - np.outer(along_[np.abs(along_) < 0.08], axis)
r_ = np.linalg.norm(ring, axis=1)
neck_r = float(np.median(r_[r_ < 1.2])) if len(r_) else 0.6
tail_c = tail_pts[int(0.55 * 29)]
meta = {
    "bones": bones,
    "groups": {},
    "attr": ["pos3", "nrm3", "col4", "emit", "blink", "trait", "lift", "droop", "comb3", "bones4", "weights4"],
    "camera": {"center": [0.0, 3.0, 0.0], "azimuth": 40.0, "pitch": 9.0, "ortho": 8.0},
    "ground": [0.0, round(ground_y, 4), 0.0],
    "places": {"head": {"bone": "head", "at": top.tolist(), "size": half},
               "mouth": {"bone": "head", "at": mouth.tolist(), "size": 0.1},
               "neck": {"bone": "neck_0", "at": neck_c.tolist(), "size": neck_r, "axis": axis.tolist()},
               "tail": {"bone": "tail_2", "at": tail_c.tolist(), "size": 0.16,
                        "axis": ((tail_pts[int(0.62 * 29)] - tail_pts[int(0.48 * 29)])).tolist()}},
    "head_forward": head_fwd.tolist(),
    "triangles": counts,
}
blob = bytearray()
for cls, parts in groups.items():
    if not parts:
        continue
    V = np.concatenate([p[0] for p in parts]); N = np.concatenate([p[1] for p in parts])
    C = np.concatenate([p[2] for p in parts]); tip = np.concatenate([p[3] for p in parts])
    E = np.concatenate([p[5] for p in parts])
    T = np.concatenate([p[4] + sum(len(q[0]) for q in parts[:i]) for i, p in enumerate(parts)])
    rows = np.column_stack([V, N, C, tip, E]).astype(np.float32)
    meta["groups"][cls] = {"verts": len(V), "stride": rows.shape[1], "tris": len(T), "vert_offset": len(blob)}
    blob += rows.tobytes()
    meta["groups"][cls]["index_offset"] = len(blob)
    blob += T.astype(np.int32).tobytes()
open(out, "wb").write(bytes(blob))
json.dump(meta, open(os.path.splitext(out)[0] + ".json", "w"), indent=1)
print("unicorn:", {k: v["verts"] for k, v in meta["groups"].items()}, "triangles", sum(counts.values()), "bones", len(bones))
