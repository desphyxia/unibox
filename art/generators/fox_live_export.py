"""Exports the fox as a live 3D model for the game (the real-time comparison, round 21): the same model fox3d.py
renders, without the hair strands, plus everything the game needs to grow shell fur and move it.

Per vertex: position, normal, colour, the fur at that point (the strand formulas of Fox3D.build_fur: combed direction
times length, how far it stands off the skin, droop, how much lighter the tips are, whether it glows) and which part it
moves with (body with breathing and a blend into the head at the neck, head, ear, tail with its place along the tail,
foxfire, blink pieces). The rig's pivots go in the header. Godot's axes: x, z, -y of Blender's.

Run:  blender -b --factory-startup -P fox_live_export.py -- OUT.bin [--body=12000]
Writes OUT.bin (float32 vertex data, uint32 indices) and OUT.json (layout and rig)."""
import bpy, bmesh, sys, os, json, math
import numpy as np
from mathutils import Vector

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
os.environ["FOX_NOFUR"] = "1"
os.environ["FOX_NOGROUND"] = "1"
import fox3d as F
import seahorse3d as K
from seahorse3d import srgb, lin

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out = argv[0] if argv else "fox_live.bin"
body_tris = next((int(a.split("=")[1]) for a in argv if a.startswith("--body=")), 12000)
ss = F.ss

K.setup_scene(True)
fox = F.Fox3D(F.EMBER, "sit", {})
rig = F.FoxRig(fox)
P = F.EMBER


def g(v):
    v = np.asarray(v, np.float64)
    return np.stack([v[..., 0], v[..., 2], -v[..., 1]], -1)


def lighten(c, k):
    return c + (1 - c) * k


# ---- which part each object moves with
kind_of = {}
for part, obs in fox.parts.items():
    if part == "tails":
        for ti, (ob, n, segs) in enumerate(obs):
            kind_of[ob.name] = ("tail", ti, n, segs)
        continue
    for i, ob in enumerate(obs):
        kind_of[ob.name] = ({"body": "body", "neck": "body", "head": "head", "ears": "ear", "ear_in": "ear"}[part], i % 2 if part in ("ears", "ear_in") else 0)
for k, (base, sz, obs) in enumerate(fox.fire_parts):
    for ob in obs:
        kind_of[ob.name] = ("fire", k)
blink = {ob.name: 1 for ob in fox.blink_open}
blink.update({ob.name: 2 for ob in fox.blink_closed})

# ---- simplify the fused body (about 112 thousand triangles) for the real-time version
tris0 = sum(len(p.vertices) - 2 for p in fox.body.data.polygons)
mod = fox.body.modifiers.new("dec", "DECIMATE")
mod.ratio = min(1.0, body_tris / tris0)
bpy.context.view_layer.objects.active = fox.body
bpy.ops.object.modifier_apply(modifier=mod.name)

CLASSES = {"coat": "lit", "fur": "lit", "earin": "lit", "mark": "lit", "ribbon": "lit", "flower": "lit", "leaf": "lit",
           "mouth": "lit", "dark": "lit", "stamen": "lit", "nose": "gloss", "bell": "gloss", "eyeglass": "gloss",
           "glint": "emit", "spark": "emit", "fire": "emit", "halo": "halo"}
EMIT = {"glint": 2.5, "spark": 1.6, "fire": 0.7}
hx, hy, hz = fox.pose["head"]
hc = np.array([hx, hy, hz])
cream = np.array(srgb(P["cream"]))

groups = {}
for ob in bpy.data.objects:
    if ob.type != "MESH" or ob.hide_render and ob.name not in blink:
        continue
    mat = ob.active_material.name.rstrip(".0123456789") if ob.active_material else "coat"
    cls = CLASSES.get(mat, "lit")
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    bm.verts.ensure_lookup_table()
    me = bpy.data.meshes.new("tmp")
    bm.to_mesh(me)
    bm.free()
    nv = len(me.vertices)
    co = np.empty(nv * 3, np.float32)
    me.vertices.foreach_get("co", co)
    co = co.reshape(nv, 3).astype(np.float64)
    nr = np.empty(nv * 3, np.float32)
    me.vertices.foreach_get("normal", nr)
    nr = nr.reshape(nv, 3).astype(np.float64)
    M = np.array(ob.matrix_world)
    co = co @ M[:3, :3].T + M[:3, 3]
    nr = nr @ np.linalg.inv(M[:3, :3])
    nr /= np.maximum(np.linalg.norm(nr, axis=1, keepdims=True), 1e-9)
    idx = np.empty(len(me.polygons) * 3, np.int64)
    me.polygons.foreach_get("vertices", idx)
    # colour: the vertex colours (linear), or the material's own colour
    col = np.ones((nv, 3))
    ca = me.color_attributes.get("Col")
    bsdf = next((n for n in ob.active_material.node_tree.nodes if n.type == "BSDF_PRINCIPLED"), None) if ob.active_material else None
    if ca is not None and bsdf is not None and bsdf.inputs["Base Color"].is_linked:
        raw = np.empty(len(ca.data) * 4, np.float32)
        ca.data.foreach_get("color", raw)
        raw = raw.reshape(-1, 4)[:, :3].astype(np.float64)
        if ca.domain == "CORNER":
            lv = np.empty(len(me.loops), np.int64)
            me.loops.foreach_get("vertex_index", lv)
            acc = np.zeros((nv, 3))
            cnt = np.zeros(nv)
            np.add.at(acc, lv, raw)
            np.add.at(cnt, lv, 1)
            col = acc / np.maximum(cnt, 1)[:, None]
        else:
            col = raw
    elif bsdf is not None:
        col = np.tile(np.array(bsdf.inputs["Base Color"].default_value)[:3], (nv, 1))
    bpy.data.meshes.remove(me)

    kind = kind_of.get(ob.name, ("body", 0))
    comb = np.zeros((nv, 3))
    L = np.zeros(nv)
    lift = np.zeros(nv)
    droop = np.zeros(nv)
    tip = np.zeros(nv)
    glow = np.zeros(nv)
    kcode = {"body": 0, "head": 1, "ear": 2, "tail": 3, "fire": 4}[kind[0]]
    part_i = kind[1]
    tpar = np.zeros(nv)
    breath = np.zeros((nv, 3))
    wh = np.zeros(nv)
    srgb_col = np.clip(col, 0, 1) ** (1 / 2.2)                 # strand formulas mix colours in sRGB; shells do too
    furry = mat in ("coat", "fur") and kind[0] in ("body", "head", "ear", "tail")
    if kind[0] == "body":
        sp = rig.spine
        d2 = ((co[:, None, :] - sp[None, ::2, :]) ** 2).sum(-1)
        j = np.argmin(d2, axis=1) * 2
        u = j / (len(sp) - 1)
        radial = co - sp[j]
        w = np.exp(-((u - 0.55) / 0.3) ** 2) * ss(1.2, 0.6, np.linalg.norm(radial, axis=1))
        breath = radial * w[:, None]
        wh = ss(1.55, 0.95, np.linalg.norm(co - rig.hc, axis=1) / fox.hs)
        if furry and ob == fox.body:
            rel = co - hc
            dist = np.linalg.norm(rel, axis=1)
            n = nr
            bib = ss(0.1, 0.55, n[:, 0] * 0.8 - n[:, 2] * 0.5) * ss(-0.75, -1.15, rel[:, 2]) * ss(-2.4, -1.6, rel[:, 2]) * ss(0.8, 0.35, np.abs(co[:, 1]))
            nape = ss(-1.5, -0.7, rel[:, 2]) * ss(0.2, -0.3, rel[:, 0] / np.maximum(dist, 1e-6)) * ss(1.9, 1.2, dist)
            low = ss(1.25, 0.7, co[:, 2])
            rib_d = np.abs((co - fox.ribbon_c) @ fox.ribbon_axis)
            rib = ss(0.26, 0.1, rib_d) * ss(1.2, 0.6, np.linalg.norm(co - fox.ribbon_c, axis=1))
            L = (0.075 + 0.36 * bib + 0.16 * nape - 0.045 * low) * (1 - 0.8 * rib) * ss(0.85, 1.05, dist / fox.hs)
            c = np.tile(np.array([-0.55, 0.0, -1.0]), (nv, 1))
            c = c * (1 - bib[:, None]) + np.array([0.35, 0.0, -1.0]) * bib[:, None]
            c[:, 1] += n[:, 1] * 0.5
            comb = c
            lift = 0.18 + 0.25 * bib + 0.2 * nape
            droop = 0.15 * bib
            srgb_col = srgb_col * (1 - bib[:, None]) + cream * bib[:, None]
            tip = 0.3 + 0.4 * bib
            srgb_col = lighten(srgb_col, 0.1)
    elif kind[0] == "head" and furry and ob == fox.head:
        lp = fox.head_local(co)
        rl = np.maximum(np.linalg.norm(lp, axis=1), 1e-6)
        cheek = ss(0.4, 0.6, np.abs(lp[:, 1]) / rl) * ss(0.3, -0.1, lp[:, 2]) * ss(0.65, 0.15, lp[:, 0]) * ss(-0.95, -0.45, lp[:, 0])
        behind = ss(0.05, -0.35, lp[:, 0] - 0.25 * ss(0.6, 0.95, lp[:, 2]))
        present = np.maximum(behind, ss(0.05, 0.3, cheek))
        for ec, er in fox.no_fur:
            present *= ss(er * 0.9, er * 1.15, np.linalg.norm(co - np.array(ec), axis=1))
        side = np.sign(lp[:, 1])
        crown = ss(0.75, 0.95, lp[:, 2]) * ss(-0.3, 0.1, lp[:, 0]) * ss(0.45, 0.1, lp[:, 1] * -F.NEAR + 0.1)
        L = (0.045 * (1 - cheek) + 0.52 * cheek + 0.12 * crown) * present
        one = np.ones(nv)
        d_loc = np.tile(np.array([-1.0, 0.0, 0.0]), (nv, 1))
        d_loc = d_loc * (1 - cheek[:, None]) + np.stack([-0.75 * one, side * 0.85, -0.6 * one], 1) * cheek[:, None]
        d_loc = d_loc * (1 - crown[:, None]) + np.array([0.9, F.NEAR * 0.35, 0.55]) * crown[:, None]
        comb = fox.head_dirs(d_loc)
        lift = 0.05 + 0.45 * cheek + 0.5 * crown
        droop = 0.1 * cheek
        srgb_col = lighten(srgb_col * (1 - cheek[:, None] * 0.7) + cream * cheek[:, None] * 0.7, 0.08)
        tip = 0.04 + 0.4 * cheek
    elif kind[0] == "ear" and furry:
        L = np.full(nv, 0.035)
        comb = fox.ear_axis_world(co)
        lift = np.full(nv, 0.1)
        tip = np.full(nv, 0.1)
    elif kind[0] == "tail":
        ti, n_r, segs = kind[1], kind[2], kind[3]
        cl, radii, rad, R, ground = fox.tail_cores[ti]
        cla = np.array([tuple(q) for q in cl])
        ring = np.minimum(np.arange(nv) // segs, n_r - 1)
        t = ring / (n_r - 1)
        tpar = t
        tg = cla[np.minimum(ring + 1, n_r - 1)] - cla[np.maximum(ring - 1, 0)]
        tg /= np.maximum(np.linalg.norm(tg, axis=1, keepdims=True), 1e-9)
        radial = co - cla[ring]
        radial /= np.maximum(np.linalg.norm(radial, axis=1, keepdims=True), 1e-9)
        if furry:
            L = 0.14 + 0.95 * np.array([rad(q) for q in t])
            c = tg + radial * 0.55
            tipdir = cla[-1] - cla[-5]
            tipdir /= np.linalg.norm(tipdir)
            flame_pt = cla[-1] + tipdir * 0.42 + np.array([0, 0, 0.08])
            tipw = ss(0.78, 0.97, t)
            to_tip = flame_pt - co
            dist = np.linalg.norm(to_tip, axis=1)
            comb = c / np.linalg.norm(c, axis=1, keepdims=True) * (1 - tipw[:, None]) + (to_tip / dist[:, None]) * tipw[:, None]
            L = L * (1 - tipw) + dist * 1.02 * tipw
            lift = np.full(nv, 0.2)
            droop = np.full(nv, 0.05)
            srgb_col = srgb_col + (1 - srgb_col) * 0.06
            tip = 0.15 + 0.3 * ss(0.6, 0.9, t)
            glow = (t > 0.84).astype(np.float64)
    # the strands' comb: along the skin, normalised (Fox3D.strands)
    if L.max() > 0:
        comb = comb - nr * (comb * nr).sum(1, keepdims=True) * 0.85
        comb /= np.maximum(np.linalg.norm(comb, axis=1, keepdims=True), 1e-6)
    lin_col = np.clip(srgb_col, 0, 1) ** 2.2
    bl = blink.get(ob.name, 0)
    emit = EMIT.get(mat, 0.0)
    rec = dict(pos=g(co), nrm=g(nr), col=np.concatenate([lin_col, tip[:, None]], 1),
               c0=np.concatenate([g(comb * L[:, None]), (L * lift)[:, None]], 1),
               c1=np.stack([np.full(nv, kcode), tpar, np.full(nv, part_i), np.full(nv, bl)], 1),
               c2=np.concatenate([g(breath), wh[:, None]], 1),
               c3=np.stack([L * droop, glow, np.full(nv, emit), np.zeros(nv)], 1),
               idx=idx)
    groups.setdefault(cls, []).append(rec)

# ---- write
meta = {"layout": ["pos3", "nrm3", "col4", "c0_4", "c1_4", "c2_4", "c3_4"], "groups": {}}
blob = bytearray()
for cls, recs in groups.items():
    off = 0
    parts = {k: [] for k in ("pos", "nrm", "col", "c0", "c1", "c2", "c3", "idx")}
    for r in recs:
        for k in ("pos", "nrm", "col", "c0", "c1", "c2", "c3"):
            parts[k].append(r[k])
        parts["idx"].append(r["idx"] + off)
        off += len(r["pos"])
    vert = np.concatenate([np.concatenate(parts[k], 0) for k in ("pos", "nrm", "col", "c0", "c1", "c2", "c3")], 1).astype(np.float32)
    ind = np.concatenate(parts["idx"]).astype(np.uint32)
    meta["groups"][cls] = dict(verts=len(vert), tris=len(ind) // 3, vert_offset=len(blob), stride=vert.shape[1])
    blob += vert.tobytes()
    meta["groups"][cls]["index_offset"] = len(blob)
    blob += ind.tobytes()
    print(cls, len(vert), "verts", len(ind) // 3, "tris")

rigd = dict(pivot=g(rig.pivot).tolist(), head=g(rig.hc).tolist(),
            ears=[dict(base=g(b).tolist(), axis=g(ax).tolist()) for b, ax in rig.ears],
            tails=[dict(root=g(r).tolist(), amp=a) for r, a in zip(rig.tail_roots, rig.tail_amp)],
            fires=[g(b).tolist() for b, sz, it in rig.fires],
            camera=dict(center=g([-0.3, 0, 3.05]).tolist(), azimuth=40.0, pitch=9.0, ortho=8.0),
            ground=g([0, 0, F.GROUND_Z]).tolist())
meta["rig"] = rigd
open(out, "wb").write(bytes(blob))
json.dump(meta, open(os.path.splitext(out)[0] + ".json", "w"), indent=1)
print("wrote", out, len(blob), "bytes")
