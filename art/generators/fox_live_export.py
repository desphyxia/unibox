"""Exports the fox as a live 3D model for the game (the real-time comparison, rounds 21-22): the same model fox3d.py
renders, without the hair strands, simplified to a small triangle budget, in four poses the game blends between
(sit, stand, down = lying like a sphinx, sleep = curled up), plus what the game needs to grow shell fur and to play
every clip (walk legs, head, ears, tails, foxfire, breathing, blinks).

How the poses match up: the simplified sitting fox is the one mesh; each of its points gets a place in every pose.
  body      the fused body is rebuilt per pose from the same building blocks (fox3d.body_parts); a point keeps its spot
            on its nearest block and is then laid onto that pose's fused surface
  tails     the same rings in every pose, so a point keeps its spot on the same triangle
  ribbon    the same, by object
  head      head, face, ears, flower: carried rigidly by the head's own placement in each pose
  foxfire   carried rigidly to that pose's flame (a flame a pose lacks shrinks to nothing)
Colours and fur length stay with the skin (sticky, like paint); the fur's combed direction is carried the same way.

Per vertex (attributes): sitting position and normal, colour (alpha: how much lighter the fur tips are), CUSTOM0 = part
(0 body 1 head 2 ear 3 tail 4 fire), place along the tail, which one, blink piece; CUSTOM1 = glows, emission, vertex id.
Per vertex, per pose (a float texture, 17 texels a vertex): position + fur lift, normal + fur droop, fur vector (combed
direction times length), breathing push + head blend at the neck; then the walk's leg weight (leg, weight, place).
Godot's axes: x, z, -y of Blender's.

Run:  blender -b --factory-startup -P fox_live_export.py -- OUT.bin
Writes OUT.bin (attributes, indices, pose texture) and OUT.json (layout, rig per pose, walk legs)."""
import bpy, bmesh, sys, os, json, math
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["FOX_NOFUR"] = "1"
os.environ["FOX_NOGROUND"] = "1"
import fox3d as F
import seahorse3d as K
from seahorse3d import srgb

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = argv[0] if argv else "fox_live.bin"
ss = F.ss
P = F.EMBER
POSES = ["sit", "stand", "down", "sleep"]
TEX_W = 256                                 ## vertices per texture row
TPV = 17                                    ## texels per vertex
# triangle budget per object kind (the sitting fox is about 150 thousand triangles before this)
BUDGET = {"body": 1800, "head": 1200, "tail": 300, "ear": 200, "ear_in": 100, "fire": 160, "fire_halo": 90, "petal": 50,
          "ribbon": 300, "leaf": 40, "eye_base": 220, "eye_iris": 220, "eye_pupil": 120, "lid": 140, "lowlid": 100, "lash": 60,
          "mouth": 200, "mark": 120, "nose": 160, "bell": 120, "stamen": 60, "sparkle": 16, "eye_glint": 40, "nose_glint": 30,
          "bell_glint": 30, "bell_slot": 40, "fcentre": 40, "star": 40}
OTHER = 200                                 ## any other piece
EPS = 0.03


def g(v):
    v = np.asarray(v, np.float64)
    return np.stack([v[..., 0], v[..., 2], -v[..., 1]], -1)


def lighten(c, k):
    return c + (1 - c) * k


def mesh_arrays(ob, world=True):
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
    if world:
        M = np.array(ob.matrix_world)
        co = co @ M[:3, :3].T + M[:3, 3]
    return co, tri, col


def vnormals(V, T):
    fn = np.cross(V[T[:, 1]] - V[T[:, 0]], V[T[:, 2]] - V[T[:, 0]])
    n = np.zeros_like(V)
    for k in range(3):
        np.add.at(n, T[:, k], fn)
    return n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)


def decimate(V, T, target):
    """a simpler copy of a triangle mesh (Blender's collapse decimation)"""
    if len(T) <= target:
        return V.copy(), T.copy()
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
    return V2, T2


def locate(V, T, pts):
    """each point's nearest spot on the mesh: (triangle, barycentric weights, distance along the triangle's normal)"""
    bvh = BVHTree.FromPolygons(V.tolist(), T.tolist())
    fi = np.empty(len(pts), np.int64)
    bc = np.empty((len(pts), 3))
    d = np.empty(len(pts))
    for i, q in enumerate(pts.tolist()):
        loc, nrm, f, dist = bvh.find_nearest(q)
        a, b, c = V[T[f, 0]], V[T[f, 1]], V[T[f, 2]]
        l = np.array(loc)
        v0, v1, v2 = b - a, c - a, l - a
        d00, d01, d11 = v0 @ v0, v0 @ v1, v1 @ v1
        d20, d21 = v2 @ v0, v2 @ v1
        den = max(d00 * d11 - d01 * d01, 1e-18)
        w1 = (d11 * d20 - d01 * d21) / den
        w2 = (d00 * d21 - d01 * d20) / den
        fn = np.cross(v0, v1)
        fn /= max(np.linalg.norm(fn), 1e-12)
        fi[i], bc[i], d[i] = f, (1 - w1 - w2, w1, w2), (np.array(q) - l) @ fn
    return fi, bc, d


def place(V, T, fi, bc, d):
    a, b, c = V[T[fi, 0]], V[T[fi, 1]], V[T[fi, 2]]
    fn = np.cross(b - a, c - a)
    fn /= np.maximum(np.linalg.norm(fn, axis=1, keepdims=True), 1e-12)
    return a * bc[:, :1] + b * bc[:, 1:2] + c * bc[:, 2:3] + fn * d[:, None]


def blocks_of(fox, pose):
    parts = fox.body_parts(pose)[0]
    V, T, base = [], [], 0
    for v, f in parts:
        V.extend([tuple(q) for q in v])
        for fc in f:
            for k in range(1, len(fc) - 1):
                T.append((fc[0] + base, fc[k] + base, fc[k + 1] + base))
        base += len(v)
    return np.array(V, np.float64), np.array(T, np.int64)


def project(fused_bvh, pts):
    out = np.empty_like(pts)
    for i, q in enumerate(pts.tolist()):
        out[i] = fused_bvh.find_nearest(q)[0]
    return out


def build(pose):
    K.setup_scene(True)
    return F.Fox3D(P, pose, {})


# ================================================================== the sitting fox: the mesh itself
fox = build("sit")
rig = F.FoxRig(fox)
kind_of = {}
for part, obs in fox.parts.items():
    if part == "tails":
        for ti, (ob, n, segs) in enumerate(obs):
            kind_of[ob.name] = ("tail", ti)
        continue
    for i, ob in enumerate(obs):
        kind_of[ob.name] = ({"body": "body", "neck": "neck", "head": "head", "ears": "ear", "ear_in": "ear"}[part], i % 2 if part in ("ears", "ear_in") else 0)
for k, (base, sz, obs) in enumerate(fox.fire_parts):
    for ob in obs:
        kind_of[ob.name] = ("fire", k)
blink = {ob.name: 1 for ob in fox.blink_open}
blink.update({ob.name: 2 for ob in fox.blink_closed})
CLASSES = {"coat": "lit", "fur": "lit", "earin": "lit", "mark": "lit", "ribbon": "lit", "flower": "lit", "leaf": "lit",
           "mouth": "lit", "dark": "lit", "stamen": "lit", "nose": "gloss", "bell": "gloss", "eyeglass": "gloss",
           "glint": "emit", "spark": "emit", "fire": "emit", "halo": "halo"}
EMIT = {"glint": 2.5, "spark": 1.6, "fire": 0.7}
hc = np.array(fox.pose["head"])
cream = np.array(srgb(P["cream"]))
sit_blocks = blocks_of(fox, fox.pose)
head_c0, head_R0 = [np.array(x) for x in fox.head_matrix()]
hs0 = fox.hs
fire_sit = [(np.array(tuple(b)), s) for b, s, _ in fox.fire_parts]
sit_spine = rig.spine.copy()

objs = []
for ob in list(bpy.data.objects):
    if ob.type != "MESH" or (ob.hide_render and ob.name not in blink):
        continue
    name = ob.name.rstrip(".0123456789")
    mat = ob.active_material.name.rstrip(".0123456789") if ob.active_material else "coat"
    kind = kind_of.get(ob.name, ("head", 0))
    V0, T0, C0 = mesh_arrays(ob)
    if C0 is None:
        bsdf = next((n for n in ob.active_material.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None)
        C0 = np.tile(np.array(bsdf.inputs["Base Color"].default_value)[:3], (len(V0), 1))
    key = "tail" if kind[0] == "tail" else ("body" if ob == fox.body else name)
    V, T = decimate(V0, T0, BUDGET.get(key, OTHER))
    fi, bc, d = locate(V0, T0, V)
    col = C0[T0[fi, 0]] * bc[:, :1] + C0[T0[fi, 1]] * bc[:, 1:2] + C0[T0[fi, 2]] * bc[:, 2:3]
    objs.append(dict(name=ob.name, mat=mat, cls=CLASSES.get(mat, "lit"), kind=kind, V=V, T=T, col=col, V0=V0, T0=T0,
                     blink=blink.get(ob.name, 0), body=ob == fox.body, head=ob == fox.head,
                     tail_n=next((n for o2, n, s in fox.parts["tails"] if o2 == ob), 0),
                     tail_segs=next((s for o2, n, s in fox.parts["tails"] if o2 == ob), 0)))

# ---- fur at each point, from the strand formulas (as in Fox3D.build_fur), in the sitting pose
for o in objs:
    V, mat, kind = o["V"], o["mat"], o["kind"]
    nv = len(V)
    nr = vnormals(V, o["T"])
    comb = np.zeros((nv, 3)); L = np.zeros(nv); lift = np.zeros(nv); droop = np.zeros(nv); tip = np.zeros(nv)
    glow = np.zeros(nv); tpar = np.zeros(nv)
    srgb_col = np.clip(o["col"], 0, 1) ** (1 / 2.2)
    furry = mat in ("coat", "fur")
    if o["body"]:
        rel = V - hc
        dist = np.linalg.norm(rel, axis=1)
        n = nr
        bib = ss(0.1, 0.55, n[:, 0] * 0.8 - n[:, 2] * 0.5) * ss(-0.75, -1.15, rel[:, 2]) * ss(-2.4, -1.6, rel[:, 2]) * ss(0.8, 0.35, np.abs(V[:, 1]))
        nape = ss(-1.5, -0.7, rel[:, 2]) * ss(0.2, -0.3, rel[:, 0] / np.maximum(dist, 1e-6)) * ss(1.9, 1.2, dist)
        low = ss(1.25, 0.7, V[:, 2])
        rib_d = np.abs((V - fox.ribbon_c) @ fox.ribbon_axis)
        rib = ss(0.26, 0.1, rib_d) * ss(1.2, 0.6, np.linalg.norm(V - fox.ribbon_c, axis=1))
        L = (0.075 + 0.36 * bib + 0.16 * nape - 0.045 * low) * (1 - 0.8 * rib) * ss(0.85, 1.05, dist / fox.hs)
        c = np.tile(np.array([-0.55, 0.0, -1.0]), (nv, 1))
        c = c * (1 - bib[:, None]) + np.array([0.35, 0.0, -1.0]) * bib[:, None]
        c[:, 1] += n[:, 1] * 0.5
        comb, lift, droop = c, 0.18 + 0.25 * bib + 0.2 * nape, 0.15 * bib
        srgb_col = lighten(srgb_col * (1 - bib[:, None]) + cream * bib[:, None], 0.1)
        tip = 0.3 + 0.4 * bib
    elif o["head"] and furry:
        lp = fox.head_local(V)
        rl = np.maximum(np.linalg.norm(lp, axis=1), 1e-6)
        cheek = ss(0.4, 0.6, np.abs(lp[:, 1]) / rl) * ss(0.3, -0.1, lp[:, 2]) * ss(0.65, 0.15, lp[:, 0]) * ss(-0.95, -0.45, lp[:, 0])
        behind = ss(0.05, -0.35, lp[:, 0] - 0.25 * ss(0.6, 0.95, lp[:, 2]))
        present = np.maximum(behind, ss(0.05, 0.3, cheek))
        for ec, er in fox.no_fur:
            present *= ss(er * 0.9, er * 1.15, np.linalg.norm(V - np.array(ec), axis=1))
        side = np.sign(lp[:, 1])
        crown = ss(0.75, 0.95, lp[:, 2]) * ss(-0.3, 0.1, lp[:, 0]) * ss(0.45, 0.1, lp[:, 1] * -F.NEAR + 0.1)
        L = (0.045 * (1 - cheek) + 0.52 * cheek + 0.12 * crown) * present
        one = np.ones(nv)
        d_loc = np.tile(np.array([-1.0, 0.0, 0.0]), (nv, 1))
        d_loc = d_loc * (1 - cheek[:, None]) + np.stack([-0.75 * one, side * 0.85, -0.6 * one], 1) * cheek[:, None]
        d_loc = d_loc * (1 - crown[:, None]) + np.array([0.9, F.NEAR * 0.35, 0.55]) * crown[:, None]
        comb, lift, droop = fox.head_dirs(d_loc), 0.05 + 0.45 * cheek + 0.5 * crown, 0.1 * cheek
        srgb_col = lighten(srgb_col * (1 - cheek[:, None] * 0.7) + cream * cheek[:, None] * 0.7, 0.08)
        tip = 0.04 + 0.4 * cheek
    elif kind[0] == "ear" and furry:
        L, comb, lift, tip = np.full(nv, 0.035), fox.ear_axis_world(V), np.full(nv, 0.1), np.full(nv, 0.1)
    elif kind[0] == "tail":
        ti = kind[1]
        cl, radii, rad, R, ground = fox.tail_cores[ti]
        cla = np.array([tuple(q) for q in cl])
        n_r = len(cla)
        # place along the tail from the nearest core point (the simplified mesh has lost the ring order)
        dd = np.linalg.norm(V[:, None, :] - cla[None, :, :], axis=2)
        ring = np.argmin(dd, axis=1)
        t = ring / (n_r - 1)
        tpar = t
        tg = cla[np.minimum(ring + 1, n_r - 1)] - cla[np.maximum(ring - 1, 0)]
        tg /= np.maximum(np.linalg.norm(tg, axis=1, keepdims=True), 1e-9)
        radial = V - cla[ring]
        radial /= np.maximum(np.linalg.norm(radial, axis=1, keepdims=True), 1e-9)
        if furry:
            L = 0.14 + 0.95 * np.array([rad(q) for q in t])
            c = tg + radial * 0.55
            tipdir = cla[-1] - cla[-5]
            tipdir /= np.linalg.norm(tipdir)
            flame_pt = cla[-1] + tipdir * 0.42 + np.array([0, 0, 0.08])
            tipw = ss(0.78, 0.97, t)
            to_tip = flame_pt - V
            dist = np.linalg.norm(to_tip, axis=1)
            comb = c / np.linalg.norm(c, axis=1, keepdims=True) * (1 - tipw[:, None]) + (to_tip / dist[:, None]) * tipw[:, None]
            L = L * (1 - tipw) + dist * 1.02 * tipw
            lift, droop = np.full(nv, 0.2), np.full(nv, 0.05)
            srgb_col = srgb_col + (1 - srgb_col) * 0.06
            tip = 0.15 + 0.3 * ss(0.6, 0.9, t)
            glow = (t > 0.84).astype(np.float64)
    if L.max() > 0:
        comb = comb - nr * (comb * nr).sum(1, keepdims=True) * 0.85
        comb /= np.maximum(np.linalg.norm(comb, axis=1, keepdims=True), 1e-6)
    o.update(L=L, lift=lift, droop=droop, tip=tip, glow=glow, tpar=tpar, comb=comb, srgb=srgb_col)
    # where each point (and a point a little way along its fur) sits, to carry both into the other poses
    tipp = V + comb * EPS
    if o["body"]:
        BV, BT = sit_blocks
        o["loc"] = locate(BV, BT, V)
        o["loc_tip"] = locate(BV, BT, tipp)
    elif kind[0] in ("tail", "neck"):
        o["loc"] = locate(o["V0"], o["T0"], V)
        o["loc_tip"] = locate(o["V0"], o["T0"], tipp)
    o["tipp"] = tipp


def breathing(spine, hcen, hs, V):
    """FoxRig.body_tf's weights: the chest's push outward, and how much a point follows the head"""
    d2 = ((V[:, None, :] - spine[None, ::2, :]) ** 2).sum(-1)
    j = np.argmin(d2, axis=1) * 2
    u = j / (len(spine) - 1)
    radial = V - spine[j]
    w = np.exp(-((u - 0.55) / 0.3) ** 2) * ss(1.2, 0.6, np.linalg.norm(radial, axis=1))
    return radial * w[:, None], ss(1.55, 0.95, np.linalg.norm(V - hcen, axis=1) / hs)


def rig_info(fox, rig):
    c, R = [np.array(x) for x in fox.head_matrix()]
    return dict(pivot=g(rig.pivot).tolist(), head=g(rig.hc).tolist(),
                ears=[dict(base=g(b).tolist(), axis=g(ax / np.linalg.norm(ax)).tolist()) for b, ax in rig.ears],
                tails=[dict(root=g(r).tolist(), amp=a) for r, a in zip(rig.tail_roots, rig.tail_amp)],
                fires=[g(b).tolist() for b, sz, it in rig.fires])


# ================================================================== every pose: where each point goes
per_pose = {}
rigs = {}
walk = None
for pose in POSES:
    if pose == "sit":
        fx, rg = fox, rig
    else:
        fx = build(pose)
        rg = F.FoxRig(fx)
    if pose != "sit":
        BVx, BTx = blocks_of(fx, fx.pose)
        fused = mesh_arrays(fx.body)
        fused_bvh = BVHTree.FromPolygons(fused[0].tolist(), fused[1].tolist())
        tails_x = [mesh_arrays(ob) for ob, n, s in fx.parts["tails"]]
        named = {ob.name: ob for ob in bpy.data.objects if ob.type == "MESH"}
        hcx, hRx = [np.array(x) for x in fx.head_matrix()]
        k_head = fx.hs / hs0
        fires_x = [(np.array(tuple(b)), s) for b, s, _ in fx.fire_parts]
    res = []
    for o in objs:
        V = o["V"]
        if pose == "sit":
            pos, tipp = V.copy(), o["tipp"].copy()
        elif o["body"]:
            pos = project(fused_bvh, place(BVx, BTx, *o["loc"]))
            tipp = project(fused_bvh, place(BVx, BTx, *o["loc_tip"]))
        elif o["kind"][0] == "tail":
            V0x, T0x, _ = tails_x[o["kind"][1]]
            pos, tipp = place(V0x, T0x, *o["loc"]), place(V0x, T0x, *o["loc_tip"])
        elif o["kind"][0] == "neck" and o["name"] in named and len(mesh_arrays(named[o["name"]])[0]) == len(o["V0"]):
            V0x, T0x, _ = mesh_arrays(named[o["name"]])
            pos, tipp = place(V0x, T0x, *o["loc"]), place(V0x, T0x, *o["loc_tip"])
        elif o["kind"][0] == "fire":
            k = o["kind"][1]
            b0, s0 = fire_sit[k]
            if k < len(fires_x):
                bx, sx = fires_x[k]
                pos, tipp = bx + (V - b0) * (sx / s0), bx + (o["tipp"] - b0) * (sx / s0)
            else:                                           # this pose has no such flame: it shrinks away
                pos, tipp = np.tile(b0, (len(V), 1)), np.tile(b0, (len(V), 1))
        else:                                               # head, face, ears, flower (and a ribbon that differs): rigid
            M = hRx @ head_R0.T * k_head
            pos = (V - head_c0) @ M.T + hcx
            tipp = (o["tipp"] - head_c0) @ M.T + hcx
        nrm = vnormals(pos, o["T"])
        combv = tipp - pos
        combv = combv / np.maximum(np.linalg.norm(combv, axis=1, keepdims=True), 1e-9) * o["L"][:, None]
        if o["kind"][0] in ("body", "neck"):
            br, wh = breathing(rg.spine, rg.hc, fx.hs, pos)
        else:
            br, wh = np.zeros_like(pos), np.zeros(len(pos))
        res.append(dict(pos=pos, nrm=nrm, comb=combv, br=br, wh=wh))
        if pose == "stand" and o["kind"][0] in ("body", "neck"):
            if walk is None:
                walk = F.WalkRig(fx)
            o["leg"] = walk.leg_weights(pos)
    per_pose[pose] = res
    rigs[pose] = rig_info(fx, rg)
    if pose == "stand":
        if walk is None:
            walk = F.WalkRig(fx)
        rigs["walk"] = dict(stance=walk.STANCE, ground=g([0, 0, F.GROUND_Z]).tolist(), legs=[
            dict(pivot=g(L["pivot"]).tolist(), knee=g(L["knee"]).tolist(), kt=L["kt"], A=L["A"], bend=L["bend"], off=L["off"])
            for L in walk.legs])
    print("pose", pose, "done")

# ================================================================== write
groups = {}
vid = 0
for oi, o in enumerate(objs):
    nv = len(o["V"])
    kcode = {"body": 0, "neck": 0, "head": 1, "ear": 2, "tail": 3, "fire": 4}[o["kind"][0]]
    lin_col = np.clip(o["srgb"], 0, 1) ** 2.2
    sit = per_pose["sit"][oi]
    attr = np.concatenate([g(sit["pos"]), g(sit["nrm"]), lin_col, o["tip"][:, None],
                           np.stack([np.full(nv, kcode), o["tpar"], np.full(nv, o["kind"][1]), np.full(nv, o["blink"])], 1),
                           np.stack([o["glow"], np.full(nv, EMIT.get(o["mat"], 0.0)), vid + np.arange(nv), np.zeros(nv)], 1)], 1)
    tex = []
    for pose in POSES:
        r = per_pose[pose][oi]
        tex += [np.concatenate([g(r["pos"]), (o["L"] * o["lift"])[:, None]], 1), np.concatenate([g(r["nrm"]), (o["L"] * o["droop"])[:, None]], 1),
                np.concatenate([g(r["comb"]), np.zeros((nv, 1))], 1), np.concatenate([g(r["br"]), r["wh"][:, None]], 1)]
    leg = o.get("leg")
    tex.append(np.concatenate([leg, np.zeros((nv, 1))], 1) if leg is not None else np.zeros((nv, 4)))
    G = groups.setdefault(o["cls"], dict(attr=[], idx=[], tex=[], base=0))
    G["attr"].append(attr)
    G["idx"].append(o["T"] + G["base"])
    G["tex"].append(np.stack(tex, 1))           # (nv, TPV, 4)
    G["base"] += nv
    vid += nv
# one texture for every vertex of every group, in vertex-id order
alltex = np.concatenate([t for G in groups.values() for t in G["tex"]], 0)
# the vertex ids above were assigned in object order; regroup by class keeps each group's ids, so lay the texture by id
order = np.concatenate([a[:, 16] for G in groups.values() for a in G["attr"]]).astype(np.int64)
tex_by_id = np.zeros_like(alltex)
tex_by_id[order] = alltex
rows = (vid + TEX_W - 1) // TEX_W
img = np.zeros((rows, TEX_W * TPV, 4), np.float32)
for i in range(vid):
    img[i // TEX_W, (i % TEX_W) * TPV:(i % TEX_W + 1) * TPV] = tex_by_id[i]

meta = {"attr": ["pos3", "nrm3", "col4", "c0_4", "c1_4"], "groups": {}, "poses": POSES, "tex": dict(width=TEX_W * TPV, height=rows, per_vertex=TPV, row=TEX_W)}
blob = bytearray()
for cls, G in groups.items():
    attr = np.concatenate(G["attr"], 0).astype(np.float32)
    ind = np.concatenate(G["idx"], 0).astype(np.uint32).ravel()
    meta["groups"][cls] = dict(verts=len(attr), tris=len(ind) // 3, vert_offset=len(blob), stride=attr.shape[1])
    blob += attr.tobytes()
    meta["groups"][cls]["index_offset"] = len(blob)
    blob += ind.tobytes()
    print(cls, len(attr), "verts", len(ind) // 3, "tris")
meta["tex"]["offset"] = len(blob)
blob += img.tobytes()
meta["rig"] = rigs
meta["camera"] = dict(center=g([-0.3, 0, 3.05]).tolist(), azimuth=40.0, pitch=9.0, ortho=8.0)
meta["ground"] = g([0, 0, F.GROUND_Z]).tolist()
open(out, "wb").write(bytes(blob))
json.dump(meta, open(os.path.splitext(out)[0] + ".json", "w"), indent=1)
print("wrote", out, len(blob), "bytes,", vid, "vertices")
