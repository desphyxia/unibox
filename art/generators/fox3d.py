"""Fox spirit (kitsune) as one 3D model, rendered from any camera (Blender, headless). Same pipeline as unicorn3d.py.

A chibi fox built directly in 3D: a fused body (spine, legs and haunches as one smoothed surface), a big head lofted
from a skull and a pointed muzzle, tall cupped ears, flat almond eyes painted onto the face, one mouth traced round
the muzzle. Fluff is made of stylised fur clumps (cheek ruffs, chest bib, ear tufts, the tails). As a spirit it has
three flame-tipped tails, a rose face marking, floating foxfire and a ribbon with a bell. Everything is deliberately
unequal left to right: head turn and tilt, ears, tails, bow, flower, fire.

Usage: blender -b -P fox3d.py -- OUTDIR [--quick] [pose:view ...]
       poses: sit stand play sleep      views: side three front back      a view can be zoomed: front@x,z,ortho
       traits: --tails=N (1-9)
"""
import bpy, bmesh, math, os, sys, random
import numpy as np
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import seahorse3d as K
import unicorn3d as U
from seahorse3d import srgb, lin, mix, smooth, grad, loft, ellipsoid, tube, material
from unicorn3d import add_object

GROUND_Z = 0.42
MUZZLE_TIP = 1.6                                           # head-local x of the nose tip
NEAR = -1                                                   # the camera side in the side and three-quarter views
X, Y, Z = Vector((1, 0, 0)), Vector((0, 1, 0)), Vector((0, 0, 1))

EMBER = dict(
    label="Ember fox spirit", seed=11,
    coat=[(0, "#ffc59a"), (0.5, "#ffa877"), (1, "#f58c63")],            # apricot: light on the flanks, deeper on the back
    cream="#fff7ee", cream_shade="#f4dccd",
    sock=[(0, "#f6a07c"), (0.5, "#c88aa8"), (1, "#9a7cb6")],             # stockings: apricot into soft plum
    ear_in="#ffc9d2", ear_tip="#9a7cb6",
    nose="#5a3a64", blush="#ff9cb0", blush_o=0.7,
    iris_g=[(0, "#a6f3e4"), (0.5, "#22a597"), (1, "#0d4458")], pupil="#0a1d28", lash="#3a2340",
    mark="#ff6f9a", mark_tip="#ffc58f",
    fire=[(0, "#fff4fb"), (0.3, "#ffb8e2"), (0.7, "#e58ce0"), (1, "#a58bff")],
    tip_glow="#ffd9ef",
    ribbon="#ff8fb5", ribbon_dark="#e2668f", bell="#ffd36b",
    petal_a="#ffc9dc", petal_b="#ff9fc4", petal_c="#fff1f6", leaf_a="#cfe9bd", leaf_b="#9fd3a6",
)


# ------------------------------------------------------------------ small helpers
def catmull(ctrl, n):
    """smooth curve through the control points (Vectors), n points"""
    pts = [ctrl[0]] + list(ctrl) + [ctrl[-1]]
    out = []
    segs = len(ctrl) - 1
    for i in range(n):
        u = i / (n - 1) * segs
        k = min(int(u), segs - 1)
        t = u - k
        p0, p1, p2, p3 = pts[k], pts[k + 1], pts[k + 2], pts[k + 3]
        t2, t3 = t * t, t * t * t
        out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    return out


def resample(pts, n):
    """evenly spaced points along a polyline"""
    d = [0.0]
    for a, b in zip(pts, pts[1:]):
        d.append(d[-1] + (b - a).length)
    L = d[-1]
    out, j = [], 0
    for i in range(n):
        s = L * i / (n - 1)
        while j < len(d) - 2 and d[j + 1] < s:
            j += 1
        t = (s - d[j]) / max(d[j + 1] - d[j], 1e-9)
        out.append(pts[j].lerp(pts[j + 1], t))
    return out


def smax(a, b, k):
    h = max(0.0, min(1.0, 0.5 + 0.5 * (b - a) / k))
    return a * (1 - h) + b * h + k * h * (1 - h)


def smin(a, b, k):
    return -smax(-a, -b, k)


def spow(x, e):
    return math.copysign(abs(x) ** e, x)


def fuse(parts, attach, voxel=0.024, smooth_iter=3):
    """parts (verts, faces) -> one smoothed surface (voxel union, joins smoothed). Returns verts, faces, normals (numpy)."""
    verts, faces = [], []
    for v, f in parts:
        base = len(verts)
        verts.extend(v)
        faces.extend([tuple(i + base for i in fc) for fc in f])
    me = bpy.data.meshes.new("raw")
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    ob = bpy.data.objects.new("raw", me)
    bpy.context.collection.objects.link(ob)
    md = ob.modifiers.new("vox", "REMESH")
    md.mode, md.voxel_size, md.adaptivity = "VOXEL", voxel, 0.0
    dg = bpy.context.evaluated_depsgraph_get()
    me2 = bpy.data.meshes.new_from_object(ob.evaluated_get(dg))
    bpy.data.objects.remove(ob)
    ob2 = bpy.data.objects.new("fused", me2)
    bpy.context.collection.objects.link(ob2)
    n = len(me2.vertices)
    co = np.empty(n * 3, dtype=np.float32)
    me2.vertices.foreach_get("co", co)
    co = co.reshape(n, 3)
    w = np.zeros(n, dtype=np.float32)
    for a, rad in attach:
        d = np.linalg.norm(co - np.array(a, dtype=np.float32), axis=1)
        w = np.maximum(w, np.clip((rad - d) / (rad * 0.5), 0.0, 1.0))
    vg = ob2.vertex_groups.new(name="joins")
    for val in (0.25, 0.5, 0.75, 1.0):
        idx = np.nonzero((w > val - 0.25) & (w <= val))[0].tolist()
        if idx:
            vg.add(idx, val, "REPLACE")
    m1 = ob2.modifiers.new("sm_all", "LAPLACIANSMOOTH")
    m1.iterations, m1.lambda_factor, m1.use_volume_preserve = smooth_iter, 0.35, True
    m2 = ob2.modifiers.new("sm_joins", "LAPLACIANSMOOTH")
    m2.iterations, m2.lambda_factor, m2.use_volume_preserve, m2.vertex_group = 14, 0.8, True, "joins"
    m3 = ob2.modifiers.new("sm_final", "LAPLACIANSMOOTH")
    m3.iterations, m3.lambda_factor, m3.use_volume_preserve = 2, 0.3, True
    dg = bpy.context.evaluated_depsgraph_get()
    me3 = bpy.data.meshes.new_from_object(ob2.evaluated_get(dg))
    bpy.data.objects.remove(ob2)
    n = len(me3.vertices)
    co = np.empty(n * 3, dtype=np.float32)
    nr = np.empty(n * 3, dtype=np.float32)
    me3.vertices.foreach_get("co", co)
    me3.vertices.foreach_get("normal", nr)
    faces = [tuple(p.vertices) for p in me3.polygons]
    bpy.data.meshes.remove(me3)
    return co.reshape(n, 3), faces, nr.reshape(n, 3)


def ss(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def area_of(ob):
    return sum(p.area for p in ob.data.polygons)


def seg_dist(p, a, b):
    ab = b - a
    t = max(0.0, min(1.0, (p - a).dot(ab) / max(ab.dot(ab), 1e-9)))
    return (p - (a + ab * t)).length, t


# ------------------------------------------------------------------ poses
def pose_data(name):
    """all pose numbers in world units: x forward (the fox faces +x), y lateral (NEAR = -1 is the camera side), z up"""
    g = GROUND_Z
    if name == "sit":
        return dict(
            spine=[(-0.42, 0, 1.2, 0.86, 0.84), (-0.2, 0, 1.62, 0.8, 0.8), (0.06, 0, 2.08, 0.7, 0.7), (0.24, 0, 2.5, 0.6, 0.6), (0.36, 0, 2.86, 0.5, 0.5)],
            head=(0.52, 0.0, 3.86), head_rot=(-4, -13, 7), hs=1.0,             # pitch (nose down +), yaw (toward the camera -), roll
            fore={-1: [(0.3, -0.4, 2.3, 0.3), (0.5, -0.42, 1.5, 0.25), (0.64, -0.44, 0.78, 0.2), (0.78, -0.45, g + 0.13, 0.19)],
                  1: [(0.26, 0.4, 2.3, 0.3), (0.44, 0.42, 1.5, 0.25), (0.56, 0.44, 0.78, 0.2), (0.68, 0.45, g + 0.13, 0.19)]},
            haunch={-1: ((-0.32, -0.6, 1.08), (0.8, 0.42, 0.66)), 1: ((-0.34, 0.6, 1.08), (0.78, 0.42, 0.64))},
            hind={-1: [(-0.12, -0.84, 0.72, 0.21), (0.16, -0.88, g + 0.14, 0.18), (0.44, -0.9, g + 0.12, 0.17)],
                  1: [(-0.14, 0.84, 0.72, 0.21), (0.12, 0.88, g + 0.14, 0.18), (0.4, 0.9, g + 0.12, 0.17)]},
            tail_root=(-1.05, 0.0, 0.92),
            tails=[  # (control points, max radius, lies on ground)
                ([(-0.75, -0.05, 0.95), (-1.25, -0.35, 0.8), (-1.55, -0.62, 0.75), (-1.2, -1.25, 0.7), (-0.2, -1.5, 0.7), (0.75, -1.25, 0.72), (1.3, -0.72, 0.8), (1.42, -0.42, 1.1)], 0.5, True),
                ([(-0.75, 0.05, 1.05), (-1.25, 0.1, 1.2), (-1.6, 0.15, 1.45), (-2.0, 0.2, 2.3), (-1.85, 0.25, 3.2), (-1.35, 0.25, 3.8), (-0.95, 0.15, 3.95), (-0.82, 0.1, 3.72)], 0.56, False),
                ([(-0.75, 0.1, 0.98), (-1.2, 0.35, 1.0), (-1.65, 0.75, 1.1), (-2.35, 1.1, 1.55), (-2.75, 1.05, 2.25), (-2.62, 0.85, 2.85), (-2.32, 0.7, 2.98)], 0.46, False),
            ],
            eye="open", ribbon=True,
            fire=[(-0.25, -0.9, 4.7, 0.30), (1.6, -1.35, 2.5, 0.24), (-2.1, 0.9, 4.1, 0.2)],
        )
    if name == "stand":
        return dict(
            spine=[(-0.95, 0, 1.95, 0.66, 0.66), (-0.5, 0, 2.0, 0.72, 0.7), (0.0, 0, 2.05, 0.74, 0.72), (0.45, 0, 2.22, 0.66, 0.66), (0.72, 0, 2.6, 0.52, 0.52)],
            head=(1.02, 0.0, 3.55), head_rot=(-2, -14, 6), hs=1.0,
            fore={-1: [(0.5, -0.36, 2.0, 0.28), (0.64, -0.4, 1.3, 0.22), (0.74, -0.42, 0.72, 0.19), (0.82, -0.43, g + 0.13, 0.18)],
                  1: [(0.42, 0.36, 2.0, 0.28), (0.4, 0.4, 1.3, 0.22), (0.36, 0.42, 0.72, 0.19), (0.42, 0.43, g + 0.13, 0.18)]},
            haunch={-1: ((-0.85, -0.42, 1.8), (0.6, 0.36, 0.62)), 1: ((-0.88, 0.42, 1.8), (0.58, 0.36, 0.6))},
            hind={-1: [(-0.85, -0.5, 1.45, 0.26), (-0.62, -0.52, 0.95, 0.2), (-0.92, -0.52, 0.66, 0.18), (-0.86, -0.52, g + 0.13, 0.18)],
                  1: [(-0.9, 0.5, 1.45, 0.26), (-1.05, 0.52, 0.95, 0.2), (-1.3, 0.52, 0.7, 0.18), (-1.2, 0.52, g + 0.13, 0.18)]},
            tail_root=(-1.45, 0.0, 2.1),
            tails=[
                ([(-1.45, -0.05, 2.1), (-2.0, -0.25, 2.35), (-2.45, -0.4, 3.0), (-2.5, -0.38, 3.75), (-2.2, -0.3, 4.15), (-1.9, -0.22, 4.1)], 0.52, False),
                ([(-1.45, 0.05, 2.15), (-2.05, 0.18, 2.75), (-2.25, 0.3, 3.65), (-1.95, 0.35, 4.4), (-1.55, 0.3, 4.6), (-1.32, 0.25, 4.38)], 0.56, False),
                ([(-1.45, 0.12, 2.05), (-2.1, 0.55, 2.05), (-2.75, 0.8, 2.4), (-3.1, 0.82, 3.0), (-3.05, 0.7, 3.5), (-2.82, 0.6, 3.6)], 0.46, False),
            ],
            eye="open", ribbon=True,
            fire=[(0.35, -0.95, 5.0, 0.28), (2.2, -1.1, 1.05, 0.22), (-3.3, 0.9, 4.2, 0.2)],
        )
    if name == "play":                                          # play bow: chest down on the forearms, rump and tails up
        return dict(
            spine=[(-0.95, 0, 2.12, 0.62, 0.62), (-0.5, 0, 1.98, 0.7, 0.68), (0.0, 0, 1.65, 0.72, 0.7), (0.42, 0, 1.28, 0.66, 0.62), (0.75, 0, 1.25, 0.52, 0.5)],
            head=(1.12, 0.0, 2.12), head_rot=(-10, -16, 11), hs=1.0,
            fore={-1: [(0.6, -0.38, 1.3, 0.28), (0.86, -0.42, 0.76, 0.22), (1.3, -0.45, g + 0.17, 0.19), (1.66, -0.46, g + 0.13, 0.18)],
                  1: [(0.55, 0.38, 1.3, 0.28), (0.78, 0.42, 0.76, 0.22), (1.18, 0.45, g + 0.17, 0.19), (1.5, 0.46, g + 0.13, 0.18)]},
            haunch={-1: ((-0.85, -0.42, 1.95), (0.58, 0.36, 0.6)), 1: ((-0.88, 0.42, 1.95), (0.56, 0.36, 0.58))},
            hind={-1: [(-0.85, -0.5, 1.6, 0.26), (-0.6, -0.52, 1.05, 0.2), (-0.86, -0.52, 0.7, 0.18), (-0.78, -0.52, g + 0.13, 0.18)],
                  1: [(-0.9, 0.5, 1.6, 0.26), (-0.72, 0.52, 1.05, 0.2), (-1.0, 0.52, 0.7, 0.18), (-0.92, 0.52, g + 0.13, 0.18)]},
            tail_root=(-1.4, 0.0, 2.3),
            tails=[
                ([(-1.1, -0.05, 2.2), (-1.6, -0.2, 2.6), (-1.85, -0.35, 3.4), (-1.6, -0.4, 4.2), (-1.1, -0.3, 4.5), (-0.85, -0.2, 4.3)], 0.52, False),
                ([(-1.1, 0.05, 2.25), (-1.7, 0.2, 2.9), (-2.25, 0.35, 3.6), (-2.6, 0.4, 4.3), (-2.5, 0.35, 4.8), (-2.25, 0.3, 4.85)], 0.5, False),
                ([(-1.1, 0.1, 2.15), (-1.8, 0.5, 2.3), (-2.5, 0.8, 2.6), (-3.0, 0.85, 3.15), (-3.1, 0.75, 3.65), (-2.9, 0.65, 3.8)], 0.44, False),
            ],
            eye="open", ribbon=True,
            fire=[(2.35, -0.6, 0.95, 0.22), (-0.3, -0.9, 4.7, 0.26), (-3.4, 0.9, 4.6, 0.2)],
        )
    if name == "sleep":                                         # curled up, chin on the big tail
        return dict(
            spine=[(-0.95, 0.15, 1.02, 0.6, 0.6), (-0.45, 0.3, 1.1, 0.74, 0.66), (0.1, 0.25, 1.1, 0.74, 0.66), (0.55, 0.05, 1.05, 0.62, 0.6), (0.82, -0.2, 1.05, 0.5, 0.5)],
            head=(1.12, -0.5, 1.42), head_rot=(14, -32, -10), hs=1.0,
            fore={-1: [(0.75, -0.38, 0.9, 0.22), (1.15, -0.62, 0.62, 0.19), (1.55, -0.75, g + 0.14, 0.17), (1.85, -0.78, g + 0.13, 0.16)],
                  1: [(0.72, 0.15, 0.9, 0.22), (1.12, 0.05, 0.6, 0.19), (1.45, -0.05, g + 0.14, 0.17), (1.72, -0.08, g + 0.13, 0.16)]},
            haunch={-1: ((-0.55, -0.32, 1.0), (0.62, 0.42, 0.55)), 1: ((-0.6, 0.62, 1.0), (0.6, 0.38, 0.52))},
            hind={-1: [(-0.4, -0.62, 0.72, 0.2), (-0.05, -0.85, g + 0.15, 0.17), (0.3, -0.9, g + 0.13, 0.16)],
                  1: [(-0.42, 0.85, 0.72, 0.2), (-0.1, 1.0, g + 0.15, 0.17), (0.25, 1.02, g + 0.13, 0.16)]},
            tail_root=(-1.3, 0.1, 0.95),
            tails=[
                ([(-1.3, 0.05, 0.92), (-1.75, -0.5, 0.8), (-1.45, -1.25, 0.75), (-0.5, -1.55, 0.75), (0.55, -1.45, 0.75), (1.4, -1.25, 0.78), (2.0, -0.7, 0.8)], 0.55, True),
                ([(-1.3, 0.15, 1.0), (-1.85, 0.55, 1.15), (-1.95, 1.2, 1.2), (-1.3, 1.55, 1.2), (-0.4, 1.6, 1.15), (0.35, 1.35, 1.0)], 0.48, True),
                ([(-1.32, 0.1, 1.1), (-1.9, 0.0, 1.55), (-2.1, 0.15, 2.05), (-1.85, 0.35, 2.35), (-1.55, 0.35, 2.3)], 0.42, False),
            ],
            eye="closed", ribbon=True,
            fire=[(-0.7, -0.6, 2.95, 0.24), (2.55, -0.6, 1.55, 0.2)],
        )
    raise ValueError(name)


# ------------------------------------------------------------------ the creature
class Fox3D:
    # the unicorn's tested face decals and flower, shared
    decal_disc = U.Uni3D.decal_disc
    surf_pt = U.Uni3D.surf_pt
    ellipse_loop = staticmethod(U.Uni3D.ellipse_loop)
    flower = U.Uni3D.flower
    bvh_of = U.Uni3D.bvh_of

    def __init__(self, P, pose_name, traits):
        self.P, self.traits, self.pose_name = P, traits, pose_name
        self.pose = pose_data(pose_name)
        self.rnd = random.Random(P.get("seed", 11))
        m = lambda n, **kw: material(n, **kw)
        self.mat_coat = m("coat", rough=0.66, sss=0.22, spec=0.22, sheen=0.6)
        self.mat_fur = m("fur", rough=0.6, sss=0.18, spec=0.25, sheen=0.7)
        self.mat_ear = m("earin", rough=0.55, sss=0.35, spec=0.2)
        self.mat_nose = m("nose", rough=0.18, vc=False, color=srgb(P["nose"]), spec=0.8)
        self.mat_dark = m("dark", rough=0.35, vc=False, color=srgb(P["lash"]), spec=0.5)
        self.mat_mouth = m("mouth", rough=0.5, vc=False, color=mix(srgb(P["nose"]), srgb(P["cream_shade"]), 0.25))
        self.mat_glint = m("glint", rough=0.2, vc=False, color=(1, 1, 1), emit=6.0)
        self.mat_eyeglass = m("eyeglass", rough=0.12, spec=0.9)
        self.mat_mark = m("mark", rough=0.45, spec=0.3)
        self.mat_fire = m("fire", rough=0.4, emit=0.7, spec=0.1, sss=0.3)
        self.mat_halo = m("halo", rough=0.4, emit=0.5, alpha=0.14, spec=0.0)
        self.mat_ribbon = m("ribbon", rough=0.38, sss=0.15, spec=0.45, sheen=0.4)
        self.mat_bell = m("bell", rough=0.18, vc=False, color=srgb(P["bell"]), spec=1.0)
        self.mat_flower = m("flower", rough=0.45, sss=0.35, spec=0.25, sheen=0.3)
        self.mat_leaf = m("leaf", rough=0.5, sss=0.25, spec=0.2)
        self.mat_stamen = m("stamen", rough=0.4, vc=False, color=srgb("#f0a45c"), spec=0.3)
        self.mat_spark = m("spark", rough=0.3, vc=False, color=srgb("#fff3c4"), emit=3.0)
        self.hs = self.pose["hs"]
        self.n_tails = max(1, min(9, traits.get("tails", 3)))
        self.fur_blocks = {}                               # hair strands, made into one curves object per material at the end
        self.nrng = np.random.default_rng(P.get("seed", 11))
        self.fur_density = float(os.environ.get("FOX_FUR", "1.0"))
        self.mat_hair = self.hair_material("hair")
        self.mat_hair_glow = self.hair_material("hairglow", emit=0.45)
        self.no_fur = []                                   # (centre, radius): eyes, marks and nose stay clear of fur
        self.blink_open, self.blink_closed = [], []         # eye pieces swapped for a blink (animation only)
        self.parts = {}                                    # part name -> objects, for the rig
        mark = lambda: set(bpy.data.objects)
        m0 = mark()
        self.build_body()
        m1 = mark()
        self.build_head()
        self.build_ears()
        self.head_bvh = self.bvh_of([ob for ob in self.head_objs])
        self.bvh = self.head_bvh                            # the face decals project onto this
        self.build_face()
        m2 = mark()
        self.build_tails()
        m3 = mark()
        self.ribbon_c, self.ribbon_axis = np.array([0, 0, -50.0]), np.array([0, 0, 1.0])
        if self.pose.get("ribbon"):
            self.build_ribbon()
        m4 = mark()
        if traits.get("flowers", True):
            self.build_flower()
        m5 = mark()
        if not os.environ.get("FOX_NOFUR"):
            self.build_fur()
            self.flush_fur()
        m6 = mark()
        self.fire_parts = []
        self.build_fire()
        if not os.environ.get("FOX_NOGROUND"):                # game sprites: no baked ground shadow, the game draws its own
            self.build_ground()
        ears = [o for o in self.head_objs if o.name.startswith("ear")]
        ear_in = [o for o in (m2 - m1) if o.name.startswith("ear_in")]
        self.parts = dict(body=[self.body], head=[o for o in (m2 - m1) | (m5 - m4) if o not in ears and o not in ear_in],
                          ears=ears, ear_in=sorted(ear_in, key=lambda o: o.name), tails=self.tail_objs, neck=list(m4 - m3))

    # ---------------------------------------------------------- head frame
    def head_matrix(self):
        hx, hy, hz = self.pose["head"]
        pitch, yaw, roll = [math.radians(a) for a in self.pose["head_rot"]]
        R = Matrix.Rotation(yaw, 3, "Z") @ Matrix.Rotation(pitch, 3, "Y") @ Matrix.Rotation(roll, 3, "X")
        return Vector((hx, hy, hz)), R

    def Hp(self, x, y, z):
        """head-local point (head radius ~1, x toward the nose, z up) -> world"""
        c, R = self.head_matrix()
        return c + R @ (Vector((x, y, z)) * self.hs)

    def Hd(self, x, y, z):
        c, R = self.head_matrix()
        return (R @ Vector((x, y, z))).normalized()

    # ---------------------------------------------------------- body
    def coat_at(self, p, n, legs):
        """coat colour at world point p with normal n: apricot back and flanks, cream bib and belly, plum stockings"""
        P = self.P
        c = grad(P["coat"], 0.35 + 0.65 * max(0.0, n.z) - 0.25 * max(0.0, -n.z))
        # cream underside and bib: facing forward-down on the chest, down on the belly
        hx, hy, hz = self.pose["head"]
        bib = smooth(0.15, 0.6, n.x * 0.8 - n.z * 0.5) * smooth(hz - 0.2, hz - 1.6, p.z) * smooth(0.75, 0.35, abs(p.y))
        belly = smooth(-0.25, -0.7, n.z)
        w = max(bib, belly)
        c = mix(c, mix(srgb(P["cream"]), srgb(P["cream_shade"]), max(0.0, -n.z) * 0.6), w)
        # stockings: lower legs fade into soft plum
        best = 0.0
        for chain, top in legs:
            for a, b in zip(chain, chain[1:]):
                d, t = seg_dist(p, a, b)
                if d < 0.45:
                    best = max(best, smooth(top, top - 0.75, p.z))
        if best > 0:
            c = mix(c, grad(P["sock"], 0.2 + 0.8 * best), best)
        # soft colour drifts so the coat is not one flat colour
        n1 = math.sin(p.x * 2.3 + p.z * 1.7) * math.sin(p.z * 2.9 - p.y * 2.1)
        c = mix(c, srgb("#ffd3c0") if n1 > 0 else srgb("#ffb48e"), 0.08 * abs(n1))
        return c

    def build_body(self):
        pose = self.pose
        parts, attach = [], []
        sp = [Vector(s[:3]) for s in pose["spine"]]
        rads = [(s[3], s[4]) for s in pose["spine"]]
        dense = catmull(sp, 18)
        for i, c in enumerate(dense):                      # a chain of overlapping ellipsoids makes a soft, round body
            u = i / (len(dense) - 1) * (len(sp) - 1)
            k = min(int(u), len(sp) - 2)
            t = u - k
            rl = rads[k][0] * (1 - t) + rads[k + 1][0] * t
            rv = rads[k][1] * (1 - t) + rads[k + 1][1] * t
            tg = (dense[min(i + 1, len(dense) - 1)] - dense[max(i - 1, 0)]).normalized()
            up = (Z - tg * Z.dot(tg)).normalized()
            v, f = ellipsoid(c, tg * (max(rl, rv) * 0.75), Y * rl, up * rv, 20, 12)
            parts.append((v, f))
        self.spine_pts = dense
        legs = []
        for sgn, chain in list(pose["fore"].items()) + list(pose["hind"].items()):
            pts = [Vector(q[:3]) for q in chain]
            rr = [q[3] for q in chain]
            dl = catmull(pts, 14)
            rl = []
            for i in range(14):
                u = i / 13 * (len(pts) - 1)
                k = min(int(u), len(pts) - 2)
                t = u - k
                rl.append(rr[k] * (1 - t) + rr[k + 1] * t)
            rings = tube(dl, rl, segs=14, up=X)
            v, f = loft(rings)
            parts.append((v, f))
            # paw: a soft oval pad with a rounded toe
            end, prev = dl[-1], dl[-3]
            fwd = Vector((end.x - prev.x, end.y - prev.y, 0))
            fwd = X if fwd.length < 0.05 else fwd.normalized()
            if abs(end.z - GROUND_Z) < 0.4:
                pc = Vector((end.x, end.y, GROUND_Z + rl[-1] * 0.85)) + fwd * 0.08
                v, f = ellipsoid(pc, fwd * (rl[-1] * 1.45), fwd.cross(Z).normalized() * (rl[-1] * 1.15), Z * (rl[-1] * 0.92), 16, 10)
                parts.append((v, f))
            else:
                v, f = ellipsoid(end, X * rl[-1], Y * rl[-1], Z * rl[-1], 12, 8)
                parts.append((v, f))
            v, f = ellipsoid(dl[0], X * rl[0], Y * rl[0], Z * rl[0], 12, 8)
            parts.append((v, f))
            attach.append((tuple(dl[0]), 0.9))
            legs.append((dl, (dl[0].z + dl[-1].z) / 2 + 0.25))
        for sgn, (c, r) in pose["haunch"].items():
            v, f = ellipsoid(Vector(c), X * r[0], Y * r[1], Z * r[2], 22, 14)
            parts.append((v, f))
            attach.append((c, 1.2))
        # neck: a short thick column from the chest into the head, hidden by the ruff
        hc = Vector(pose["head"])
        top = sp[-1]
        for t in (0.25, 0.5, 0.75):
            c = top.lerp(hc, t)
            r = 0.5 - 0.06 * t
            v, f = ellipsoid(c, X * r, Y * r * 1.05, Z * r, 14, 10)
            parts.append((v, f))
        attach.append((tuple(top), 1.0))
        co, faces, nr = fuse(parts, attach)
        self.legs = legs
        cols = []
        for p, n in zip(co.tolist(), nr.tolist()):
            cols.append(lin(self.coat_at(Vector(p), Vector(n), legs)))
        verts = [Vector(p) for p in co.tolist()]
        self.body = add_object("body", verts, faces, cols, self.mat_coat)
        self.body_co, self.body_nr = co, nr
        self.body_bvh = BVHTree.FromPolygons([tuple(v) for v in verts], faces)
        print("body fused:", len(verts), "vertices")

    # ---------------------------------------------------------- head
    @staticmethod
    def head_profile(x):
        """(top, bottom, half-width) of the head section at local x: a round skull, a clear stop under the eyes,
        then a fox muzzle that narrows to a fine point"""
        s = max(0.0, 1 - ((x + 0.04) / 0.98) ** 2)
        sk_t, sk_b, sk_w = 0.06 + math.sqrt(s) * 0.96, 0.02 - math.sqrt(s) * 0.86, math.sqrt(s) * 1.06
        if x < 0.35:
            return sk_t, sk_b, sk_w
        u = min(1.0, (x - 0.35) / (MUZZLE_TIP - 0.35))
        cap = math.sqrt(max(0.0, 1 - ((x - (MUZZLE_TIP - 0.14)) / 0.14) ** 2)) if x > MUZZLE_TIP - 0.14 else 1.0
        mz_t = 0.36 - 0.34 * u ** 0.9                       # bridge falls gently to the nose
        mz_b = -0.58 + 0.34 * u ** 1.1                     # jaw rises to the chin
        mz_w = 0.56 * (1 - u) ** 0.95 + 0.11
        mid = (mz_t + mz_b) / 2
        mz_t, mz_b = mid + (mz_t - mid) * (0.3 + 0.7 * cap), mid + (mz_b - mid) * (0.3 + 0.7 * cap)
        mz_w *= cap
        return smax(sk_t, mz_t, 0.2), smin(sk_b, mz_b, 0.2), smax(sk_w, mz_w, 0.22)

    def build_head(self):
        P = self.P
        xs = [-1.02 + (MUZZLE_TIP + 1.02) * (0.5 - 0.5 * math.cos(math.pi * k / 72)) for k in range(73)]
        segs = 44
        rings, cols = [], []
        self.head_objs = []
        for x in xs:
            top, bot, wid = self.head_profile(x)
            hh = max((top - bot) / 2, 0.004)
            zc = (top + bot) / 2
            wid = max(wid, 0.004)
            ring = []
            for k in range(segs):
                th = 2 * math.pi * k / segs                # 0 = top, pi = bottom
                cz, sy = math.cos(th), math.sin(th)
                # rounder on top, a broad flat jaw underneath; full cheeks low on the sides
                e = 0.85 if cz > 0 else 0.7
                cheek = 1 + 0.16 * smooth(-0.5, 0.35, x) * smooth(0.95, 0.45, x) * max(0.0, -cz + 0.3) ** 1.2
                y = spow(sy, e) * wid * cheek
                z = zc + spow(cz, e) * hh
                ring.append(self.Hp(x, y, z))
                cols.append(lin(self.head_color(x, y, z, cz)))
            rings.append(ring)
        v, f = loft(rings)
        # close the ends
        n = len(v)
        v.append(self.Hp(xs[0] - 0.001, 0, self.head_profile(xs[0])[0] * 0.5 + self.head_profile(xs[0])[1] * 0.5))
        v.append(self.Hp(xs[-1] + 0.001, 0, sum(self.head_profile(xs[-1])[:2]) / 2))
        cols.append(cols[0])
        cols.append(cols[-segs])
        for k in range(segs):
            f.append((n, (k + 1) % segs, k))
            f.append((n + 1, (len(xs) - 1) * segs + k, (len(xs) - 1) * segs + (k + 1) % segs))
        self.head = add_object("head", v, f, cols, self.mat_coat)
        self.head_objs.append(self.head)
        # nose: a small glossy button on the muzzle tip
        tip_t, tip_b, _ = self.head_profile(MUZZLE_TIP - 0.07)
        nc = self.Hp(MUZZLE_TIP - 0.05, 0, tip_t - 0.04)
        fwd, up, side = self.Hd(1, 0, 0), self.Hd(0, 0, 1), self.Hd(0, 1, 0)
        nv, nf = ellipsoid(nc, fwd * 0.13 * self.hs, side * 0.16 * self.hs, up * 0.11 * self.hs, 18, 12)
        nv = [p + up * 0.04 * self.hs * max(0.0, (p - nc).dot(up) / (0.11 * self.hs)) ** 2 for p in nv]       # flatter, wider top like a fox nose
        self.nose = add_object("nose", nv, nf, None, self.mat_nose)
        gv, gf = ellipsoid(nc + up * 0.07 * self.hs + fwd * 0.06 * self.hs - side * 0.05 * self.hs, fwd * 0.03 * self.hs, side * 0.045 * self.hs, up * 0.02 * self.hs, 10, 6)
        add_object("nose_glint", gv, gf, None, self.mat_glint)

    def head_color(self, x, y, z, cz):
        """apricot crown and bridge; cream cheeks, muzzle and chin; a soft blush low on the cheeks"""
        P = self.P
        c = grad(P["coat"], 0.4 + 0.5 * max(0.0, cz))
        # the fox mask line: from under the eye it runs forward along the muzzle side, so the upper lip and cheeks are cream
        line = 0.0 - 0.16 * smooth(0.5, MUZZLE_TIP, x) + 0.06 * smooth(-0.6, 0.2, x) - 0.35 * smooth(0.0, -0.9, x)
        w = smooth(line + 0.08, line - 0.1, z) * smooth(-0.7, -0.1, x + 0.3 * abs(y))
        w = max(w, smooth(-0.1, -0.5, cz) * smooth(-0.8, 0.2, x))
        c = mix(c, srgb(P["cream"]), w)
        d = ((x - 0.4) / 0.24) ** 2 + ((z + 0.2) / 0.18) ** 2
        c = mix(c, srgb(P["blush"]), P["blush_o"] * math.exp(-d) * min(1.0, abs(y) / 0.5))
        # kitsune eyeshadow: a rose sweep from the outer corner of each eye back toward the ear
        u_ = (x - 0.3) * 0.8 + (z - 0.4) * 0.6
        v_ = -(x - 0.3) * 0.6 + (z - 0.4) * 0.8
        e = (u_ / 0.3) ** 2 + (v_ / 0.11) ** 2
        c = mix(c, srgb(P["mark"]), 0.75 * math.exp(-e * 1.4) * smooth(0.35, 0.6, abs(y)))
        return c

    def head_hit(self, target, d):
        """surface point and outward normal of the head where a ray toward target along -d lands"""
        bvh = BVHTree.FromObject(self.head, bpy.context.evaluated_depsgraph_get())
        hit = bvh.ray_cast(target + d * 2.0, -d)
        if hit[0] is None:
            return target, d
        nn = hit[1] if hit[1].dot(d) > 0 else -hit[1]
        return hit[0], nn.normalized()

    # ---------------------------------------------------------- ears
    def build_ears(self):
        P = self.P
        specs = {NEAR: dict(base=(-0.12, 0.6, 0.8), tip=(-0.3, 0.98, 2.12), splay=0.0, w=0.62),
                 -NEAR: dict(base=(-0.16, 0.6, 0.8), tip=(-0.42, 1.18, 1.92), splay=0.25, w=0.6)}     # the far ear tilts out a little more
        self.ear_tips = {}
        for sgn, s in specs.items():
            b = Vector((s["base"][0], sgn * s["base"][1], s["base"][2]))
            t = Vector((s["tip"][0], sgn * s["tip"][1], s["tip"][2]))
            axis = (t - b)
            L = axis.length
            axis.normalize()
            facing = Vector((1, sgn * 0.35, 0.1))                      # the open side of the ear faces forward and a little out
            facing = (facing - axis * facing.dot(axis)).normalized()
            across = axis.cross(facing).normalized()
            n = 22
            segs = 24
            rings, cols, inner_rings = [], [], []
            for i in range(n + 1):
                u = i / n
                w = s["w"] * (1 - u) ** 0.85 * (1 + 0.25 * math.sin(math.pi * u) ** 2) + 0.012
                dep = 0.24 * (1 - u) ** 1.1 + 0.01
                c = b + axis * (L * u) - facing * (0.08 * math.sin(math.pi * u))   # the ear leans back a little in its middle
                ring = []
                for k in range(segs):
                    th = 2 * math.pi * k / segs
                    a_ = math.cos(th)
                    bz = math.sin(th)
                    cup = -0.55 * dep * (1 - a_ * a_) if bz > 0 else 0.0      # the front face is hollowed into a cup
                    ring.append(c + across * (a_ * w) + facing * (bz * dep * 0.5 + cup * 0.6))
                    tipc = smooth(0.62, 0.85, u + 0.08 * abs(a_))
                    base_c = grad(P["coat"], 0.55 + 0.3 * u)
                    cols.append(lin(mix(base_c, srgb(P["ear_tip"]), tipc)))
                rings.append([self.Hp(*p) for p in ring])
                # the pink inner ear lies in the cup
                if u < 0.86:
                    wi = w * 0.68
                    ci = c + facing * (dep * 0.2) + axis * 0.0
                    inner_rings.append([self.Hp(*(ci + across * (math.cos(2 * math.pi * k / 12) * wi) + facing * (math.sin(2 * math.pi * k / 12) * dep * 0.12 - 0.04 * dep)))
                                        for k in range(12)])
            v, f = loft(rings)
            ob = add_object("ear", v, f, cols, self.mat_coat)
            self.head_objs.append(ob)
            v, f = loft(inner_rings)
            ci = []
            for i, r in enumerate(inner_rings):
                u = i / max(1, len(inner_rings) - 1)
                ci.extend([lin(mix(srgb(P["ear_in"]), srgb("#ffe3e6"), u * 0.6))] * len(r))
            add_object("ear_in", v, f, ci, self.mat_ear)
            self.ear_tips[sgn] = (b, t, axis, facing, across, L, s["w"])

    # ---------------------------------------------------------- face
    @staticmethod
    def eye_outline(n=26):
        """fox almond: the outer corner lifts high, the inner corner dips toward the nose; a fuller lower curve for a young face"""
        def bz(p0, p1, p2, p3, t):
            a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
            return (a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1])
        O, I = (-1.0, 0.3), (0.95, -0.2)
        top = [bz(O, (-0.7, 1.08), (0.4, 1.1), I, t / n) for t in range(n + 1)]
        bot = [bz(I, (0.62, -0.95), (-0.62, -0.86), O, t / n) for t in range(1, n)]
        return top, bot

    def eye_frame(self, sgn):
        target = self.Hp(0.5, sgn * 0.5, 0.22)
        d = self.Hd(0.8, sgn * 0.62, 0.14)
        C, out = self.head_hit(target, d)
        fwd = self.Hd(1, 0, 0)
        ex = (fwd - out * fwd.dot(out)).normalized()
        ez = out.cross(ex)
        if ez.dot(self.Hd(0, 0, 1)) < 0:
            ez = -ez
        return C, out, ex, ez

    def build_face(self):
        P, hs = self.P, self.hs
        closed = self.pose["eye"] != "open"
        for sgn in (-1, 1):
            C, out, ex, ez = self.eye_frame(sgn)
            tau = math.radians(16)
            ex2 = ex * math.cos(tau) - ez * math.sin(tau)
            ez2 = ez * math.cos(tau) + ex * math.sin(tau)
            k = 1.0 if sgn == NEAR else 0.95
            rx, ry = 0.29 * hs * k, 0.31 * hs * k
            self.no_fur.append((tuple(C), 0.4 * hs))
            if closed:
                U.Uni3D.eye_closed(self, C, out, ex2, ez2, rx, ry * 0.9)
            else:
                b0 = set(bpy.data.objects)
                U.Uni3D.eye_open(self, C, out, ex2, ez2, rx, ry, sgn)
                b1 = set(bpy.data.objects)
                U.Uni3D.eye_closed(self, C, out, ex2, ez2, rx, ry * 0.9)
                b2 = set(bpy.data.objects)
                self.blink_open += list(b1 - b0)
                self.blink_closed += list(b2 - b1)
                for ob in b2 - b1:
                    ob.hide_render = True
        # forehead flame: one flame that leans to the near side, not a mirrored emblem
        C, out = self.head_hit(self.Hp(0.45, 0.0, 0.72), self.Hd(0.55, 0, 1))
        self.no_fur.append((tuple(C), 0.28 * hs))
        up = self.Hd(0, 0, 1)
        ex = (up - out * up.dot(out)).normalized()        # along the flame, up the forehead
        ez = out.cross(ex)
        flame = []
        for q in range(48):
            t = 2 * math.pi * q / 48
            u_ = math.cos(t)                                # 1 = tip (up the forehead), -1 = the round bottom
            v_ = 0.62 * math.sin(t) * math.sin(t / 2) ** 1.6
            v_ += 0.3 * ((u_ + 1) / 2) ** 2.5 * NEAR
            flame.append((u_, v_))
        self.decal_disc("mark", C, out, ex, ez, 0.2 * hs, 0.2 * hs, flame, 1.0, 0.006 * hs,
                        lambda u, v, r: mix(srgb(P["mark"]), srgb(P["mark_tip"]), smooth(-0.4, 0.9, u) * 0.85), self.mat_mark)
        self.build_mouth()
        # glitter freckles on the near cheek, two on the far
        for sgn, cnt in ((NEAR, 4), (-NEAR, 2)):
            for i in range(cnt):
                tgt = self.Hp(0.36 + 0.09 * math.cos(i * 2.1) + 0.04 * i, sgn * 0.7, -0.2 + 0.07 * math.sin(i * 2.7))
                p, nn = self.head_hit(tgt, self.Hd(0.35, sgn * 1.0, 0.0))
                v, f = ellipsoid(p + nn * 0.006, X * 0.012, Y * 0.012, Z * 0.012, 8, 6)
                add_object("sparkle", v, f, None, self.mat_glint)

    def build_mouth(self):
        """one mouth: from the nose a short line down, then one smile running back along both sides of the muzzle"""
        hs = self.hs
        top_t, top_b, _ = self.head_profile(MUZZLE_TIP - 0.2)
        centre = self.Hp(MUZZLE_TIP - 0.26, 0, top_b + 0.1)
        fwd, up, side = self.Hd(1, 0, 0), self.Hd(0, 0, 1), self.Hd(0, 1, 0)
        bvh = BVHTree.FromObject(self.head, bpy.context.evaluated_depsgraph_get())
        pts = []
        n_m = 50
        for q in range(n_m + 1):
            t = -1 + 2 * q / n_m
            sgn = NEAR if t < 0 else -NEAR
            a = abs(t)
            phi = math.radians(a * (96 if t < 0 else 86))
            d = (fwd * math.cos(phi) + side * sgn * math.sin(phi)).normalized()
            lift = (-0.045 * math.sin(math.pi * min(1.0, a / 0.5)) * (1 if a < 0.5 else 0) + 0.05 * smooth(0.6, 1.0, a) - 0.012) * hs
            back = 0.36 * smooth(0.2, 1.0, a) * hs
            origin = centre + up * lift - fwd * back
            hit = bvh.ray_cast(origin + d * 1.5, -d)
            if hit[0] is None:
                continue
            nn = hit[1] if hit[1].dot(d) > 0 else -hit[1]
            pts.append(hit[0] + nn * 0.008)
        for _ in range(2):
            pts = [pts[0]] + [(pts[i - 1] + pts[i] * 2 + pts[i + 1]) / 4 for i in range(1, len(pts) - 1)] + [pts[-1]]
        m_ = len(pts)
        rad = [0.017 * hs * (0.35 + 0.65 * math.sin(math.pi * k / (m_ - 1)) ** 0.4) for k in range(m_)]
        rings = tube(pts, rad, segs=6, up=up)
        v, f = loft(rings)
        add_object("mouth", v, f, None, self.mat_mouth)
        # the short line from the nose down to the middle of the smile
        mid = pts[m_ // 2]
        nose_b = self.Hp(MUZZLE_TIP - 0.1, 0, top_t - 0.14)
        hit = bvh.ray_cast(nose_b + fwd * 1.0, -fwd)
        nb = hit[0] + fwd * 0.008 if hit[0] is not None else nose_b
        line = [nb.lerp(mid, s / 6) for s in range(7)]
        line = [p + fwd * 0.02 * math.sin(math.pi * s / 6) for s, p in enumerate(line)]
        rings = tube(line, [0.015 * hs] * 7, segs=6, up=side)
        v, f = loft(rings)
        add_object("mouth", v, f, None, self.mat_mouth)

    # ---------------------------------------------------------- fur clumps
    # ---------------------------------------------------------- fur: real strands, combed by code
    def strands(self, key, roots, nrm, comb, L, lift, clump, cell, c_root, c_tip, droop=0.0, K=7, rad0=0.0042, jitter=0.14, bind=(0, 0), bind_t=None):
        """grow N hair strands from roots. comb: the direction they are brushed along the surface; lift: how far they stand off
        it; clump: how strongly neighbouring strands gather into tufts (cells of size `cell`)"""
        N = len(roots)
        if N == 0:
            return
        rng = self.nrng
        nrm = nrm / np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
        comb = comb + rng.normal(0, jitter, (N, 3))
        comb = comb - nrm * (comb * nrm).sum(1, keepdims=True) * 0.85
        comb /= np.maximum(np.linalg.norm(comb, axis=1, keepdims=True), 1e-6)
        L = np.broadcast_to(np.asarray(L, dtype=np.float64), (N,)) * (0.72 + 0.56 * rng.random(N))
        sv = np.linspace(0, 1, K)
        lift = np.broadcast_to(np.asarray(lift, dtype=np.float64), (N,))
        droop = np.broadcast_to(np.asarray(droop, dtype=np.float64), (N,))
        zup = np.array([0, 0, 1.0])

        def curve(r, n_, c_, l_):
            return (r[:, None, :] - n_[:, None, :] * 0.006
                    + n_[:, None, :] * (l_ * lift)[:, None, None] * (1 - (1 - sv) ** 2)[None, :, None]
                    + c_[:, None, :] * l_[:, None, None] * (sv ** 1.15)[None, :, None]
                    - zup[None, None, :] * (l_ * droop)[:, None, None] * (sv ** 2)[None, :, None])
        Pp = curve(roots, nrm, comb, L)
        clump = np.broadcast_to(np.asarray(clump, dtype=np.float64), (N,))
        if clump.max() > 0:
            keys = np.floor(roots / cell).astype(np.int64)
            _, inv = np.unique(keys, axis=0, return_inverse=True)
            inv = inv.ravel()
            m = inv.max() + 1
            cnt = np.bincount(inv, minlength=m)[:, None].astype(np.float64)
            gsum = lambda a: np.stack([np.bincount(inv, a[:, k], minlength=m) for k in range(3)], 1) / cnt
            gr, gn, gc = gsum(roots), gsum(nrm), gsum(comb)
            gn /= np.maximum(np.linalg.norm(gn, axis=1, keepdims=True), 1e-6)
            gc /= np.maximum(np.linalg.norm(gc, axis=1, keepdims=True), 1e-6)
            gl = np.bincount(inv, L, minlength=m) / cnt[:, 0]
            G = curve(gr[inv], gn[inv], gc[inv], gl[inv] * 1.05)
            G = G + (roots - gr[inv])[:, None, :] * (1 - sv)[None, :, None]
            w = clump[:, None, None] * (sv ** 1.4)[None, :, None]
            Pp = Pp * (1 - w) + G * w
        R = rad0 * (1 - 0.82 * sv)[None, :] * np.ones((N, 1))
        c_root = np.broadcast_to(np.asarray(c_root, dtype=np.float64), (N, 3))
        c_tip = np.broadcast_to(np.asarray(c_tip, dtype=np.float64), (N, 3))
        C = c_root[:, None, :] * (1 - sv)[None, :, None] + c_tip[:, None, :] * sv[None, :, None]
        kind = np.full(N, bind[0], np.int8)
        idx = np.full(N, bind[1], np.int8)
        tt = np.zeros(N, np.float32) if bind_t is None else np.asarray(bind_t, np.float32)
        self.fur_blocks.setdefault((key, K), []).append((Pp.astype(np.float32), R.astype(np.float32), C.astype(np.float32), kind, idx, tt))

    def flush_fur(self):
        mats = {"fur": self.mat_hair, "glow": self.mat_hair_glow}
        total = 0
        self.fur_objs = []
        for (key, K), blocks in self.fur_blocks.items():
            Pp = np.concatenate([b[0] for b in blocks])
            R = np.concatenate([b[1] for b in blocks])
            C = np.concatenate([b[2] for b in blocks])
            N = len(Pp)
            total += N
            cv = bpy.data.hair_curves.new(f"fur_{key}")
            cv.add_curves([K] * N)
            cv.position_data.foreach_set("vector", Pp.reshape(-1))
            ra = cv.attributes.get("radius") or cv.attributes.new("radius", "FLOAT", "POINT")
            ra.data.foreach_set("value", R.reshape(-1))
            ca = cv.attributes.new("fcol", "FLOAT_COLOR", "POINT")
            ca.data.foreach_set("color", np.concatenate([C, np.ones((N, K, 1), np.float32)], 2).reshape(-1))
            ob = bpy.data.objects.new(f"fur_{key}", cv)
            bpy.context.collection.objects.link(ob)
            cv.materials.append(mats[key])
            self.fur_objs.append((ob, Pp, np.concatenate([b[3] for b in blocks]), np.concatenate([b[4] for b in blocks]), np.concatenate([b[5] for b in blocks])))
        print("fur strands:", total)

    def hair_material(self, name, emit=0.0):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
        at = nt.nodes.new("ShaderNodeAttribute")
        at.attribute_name = "fcol"
        nt.links.new(at.outputs["Color"], bsdf.inputs["Base Color"])
        bsdf.inputs["Roughness"].default_value = 0.6
        bsdf.inputs["Sheen Weight"].default_value = 0.8
        bsdf.inputs["Sheen Tint"].default_value = (1.0, 0.97, 0.95, 1.0)
        bsdf.inputs["Specular IOR Level"].default_value = 0.25
        bsdf.inputs["Subsurface Weight"].default_value = 0.35
        bsdf.inputs["Subsurface Radius"].default_value = (0.6, 0.4, 0.35)
        nt.links.new(at.outputs["Color"], bsdf.inputs["Emission Color"])
        bsdf.inputs["Emission Strength"].default_value = 0.16 + emit
        nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
        return m

    @staticmethod
    def mesh_arrays(ob):
        me = ob.data
        me.calc_loop_triangles()
        n = len(me.vertices)
        co = np.empty(n * 3, np.float32)
        nr = np.empty(n * 3, np.float32)
        me.vertices.foreach_get("co", co)
        me.vertices.foreach_get("normal", nr)
        tris = np.empty(len(me.loop_triangles) * 3, np.int64)
        me.loop_triangles.foreach_get("vertices", tris)
        col = np.ones(n * 4, np.float32)
        if "Col" in me.color_attributes:
            me.color_attributes["Col"].data.foreach_get("color", col)
        M = np.array(ob.matrix_world)
        co = co.reshape(n, 3) @ M[:3, :3].T + M[:3, 3]
        nr = nr.reshape(n, 3) @ M[:3, :3].T
        return co.astype(np.float64), nr.astype(np.float64), tris.reshape(-1, 3), col.reshape(n, 4)[:, :3].astype(np.float64)

    def sample(self, ob, N):
        """N random points spread evenly over a mesh: positions, normals, colours"""
        co, nr, tris, col = self.mesh_arrays(ob)
        a, b, c = co[tris[:, 0]], co[tris[:, 1]], co[tris[:, 2]]
        area = 0.5 * np.linalg.norm(np.cross(b - a, c - a), axis=1)
        pick = self.nrng.choice(len(tris), N, p=area / area.sum())
        u, v = self.nrng.random(N), self.nrng.random(N)
        flip = u + v > 1
        u[flip], v[flip] = 1 - u[flip], 1 - v[flip]
        w = 1 - u - v
        T = tris[pick]
        mixa = lambda A: A[T[:, 0]] * w[:, None] + A[T[:, 1]] * u[:, None] + A[T[:, 2]] * v[:, None]
        p, n, cc = mixa(co), mixa(nr), mixa(col)
        n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
        return p, n, cc, area.sum()

    def head_local(self, p):
        c, R = self.head_matrix()
        return (p - np.array(c)) @ np.array(R) / self.hs

    def head_dirs(self, d_local):
        c, R = self.head_matrix()
        return d_local @ np.array(R).T

    def build_fur(self):
        P = self.P
        cream = np.array(srgb(P["cream"]))
        lighten = lambda c, k: c + (1 - c) * k
        dens = self.fur_density
        # ---- body: plush short fur, a long cream bib, a collar of fluff round the neck
        p, n, c, area = self.sample(self.body, int(110000 * dens))
        hx, hy, hz = self.pose["head"]
        hc = np.array([hx, hy, hz])
        far_head = np.linalg.norm(p - hc, axis=1) > 0.95 * self.hs
        p, n, c = p[far_head], n[far_head], c[far_head]
        rel = p - hc
        dist = np.linalg.norm(rel, axis=1)
        bib = ss(0.1, 0.55, n[:, 0] * 0.8 - n[:, 2] * 0.5) * ss(-0.75, -1.15, rel[:, 2]) * ss(-2.4, -1.6, rel[:, 2]) * ss(0.8, 0.35, np.abs(p[:, 1]))
        nape = ss(-1.5, -0.7, rel[:, 2]) * ss(0.2, -0.3, rel[:, 0] / np.maximum(dist, 1e-6)) * ss(1.9, 1.2, dist)
        low = ss(1.25, 0.7, p[:, 2])                                   # lower legs and paws: short and sleek
        rib_d = np.abs((p - self.ribbon_c) @ self.ribbon_axis)
        rib = ss(0.26, 0.1, rib_d) * ss(1.2, 0.6, np.linalg.norm(p - self.ribbon_c, axis=1))
        L = (0.075 + 0.36 * bib + 0.16 * nape - 0.045 * low) * (1 - 0.8 * rib)
        comb = np.tile(np.array([-0.55, 0.0, -1.0]), (len(p), 1))
        comb = comb * (1 - bib[:, None]) + np.array([0.35, 0.0, -1.0]) * bib[:, None]
        comb[:, 1] += n[:, 1] * 0.5
        c = c * (1 - bib[:, None]) + cream * bib[:, None]
        self.strands("fur", p, n, comb, L, 0.18 + 0.25 * bib + 0.2 * nape, 0.25 + 0.55 * bib + 0.35 * nape, 0.11, lighten(c, 0.1), lighten(c, 0.3 + 0.4 * bib[:, None]), droop=0.15 * bib)
        # ---- head: very short on the face, long tufted cheek ruffs, a little crown tuft; none on the eyes, nose, mouth or mark
        p, n, c, area = self.sample(self.head, int(70000 * dens))
        lp = self.head_local(p)
        keep = np.ones(len(p), bool)
        for ec, er in self.no_fur:
            keep &= np.linalg.norm(p - np.array(ec), axis=1) > er
        rl = np.maximum(np.linalg.norm(lp, axis=1), 1e-6)
        cheek = ss(0.4, 0.6, np.abs(lp[:, 1]) / rl) * ss(0.3, -0.1, lp[:, 2]) * ss(0.65, 0.15, lp[:, 0]) * ss(-0.95, -0.45, lp[:, 0])
        behind = ss(0.05, -0.35, lp[:, 0] - 0.25 * ss(0.6, 0.95, lp[:, 2]))      # the face stays smooth; fur starts behind the eyes
        keep = (self.nrng.random(len(p)) < np.maximum(behind, ss(0.05, 0.3, cheek))) & keep
        p, n, c, lp, cheek = p[keep], n[keep], c[keep], lp[keep], cheek[keep]
        side = np.sign(lp[:, 1])
        muzzle = ss(0.35, 0.75, lp[:, 0])
        crown = ss(0.75, 0.95, lp[:, 2]) * ss(-0.3, 0.1, lp[:, 0]) * ss(0.45, 0.1, lp[:, 1] * -NEAR + 0.1)
        L = 0.045 * (1 - cheek) + 0.52 * cheek + 0.12 * crown
        one = np.ones_like(side)
        d_loc = np.tile(np.array([-1.0, 0.0, 0.0]), (len(p), 1))
        d_loc = d_loc * (1 - cheek[:, None]) + np.stack([-0.75 * one, side * 0.85, -0.6 * one], 1) * cheek[:, None]
        d_loc = d_loc * (1 - crown[:, None]) + np.array([0.9, NEAR * 0.35, 0.55]) * crown[:, None]
        comb = self.head_dirs(d_loc)
        cc = c * (1 - cheek[:, None] * 0.7) + cream * cheek[:, None] * 0.7
        cc = lighten(cc, 0.08)
        self.strands("fur", p, n, comb, L, 0.05 + 0.45 * cheek + 0.5 * crown, 0.1 + 0.75 * cheek + 0.6 * crown, 0.08, cc, lighten(cc, 0.04 + 0.4 * cheek[:, None]),
                     droop=0.1 * cheek, rad0=0.0032, bind=(1, 0))
        # ---- ears: short fur on the back combed toward the tip, long cream tufts spilling out of the cup
        for ei, ob in enumerate([o for o in self.head_objs if o.name.startswith("ear")]):
            p, n, c, area = self.sample(ob, int(9000 * dens))
            self.strands("fur", p, n, self.ear_axis_world(p), 0.035, 0.1, 0.1, 0.05, c, lighten(c, 0.1), rad0=0.0032, bind=(2, ei))
        cvec, Rm = self.head_matrix()
        for ei, (sgn, (b, t, axis, facing, across, Lr, w)) in enumerate(self.ear_tips.items()):
            N = int(700 * dens)
            u = self.nrng.random(N) * 0.4 + 0.03
            a = self.nrng.uniform(-0.75, 0.75, N)
            loc = (np.array(b)[None, :] + np.array(axis)[None, :] * (Lr * u)[:, None] + np.array(across)[None, :] * (a * w * (1 - u) * 0.85)[:, None]
                   + np.array(facing)[None, :] * 0.05)
            roots = self.head_dirs(loc) * self.hs + np.array(cvec)
            nn = np.tile(self.head_dirs(np.array(facing)[None, :]), (N, 1))
            dd = self.head_dirs(np.array(axis)[None, :] * 0.9 + np.array(facing)[None, :] * 0.2) + self.head_dirs(np.array(across)[None, :]) * a[:, None] * 0.45
            Lx = (0.12 + 0.14 * (1 - u)) * self.hs
            self.strands("fur", roots, nn, dd, Lx, 0.15, 0.75, 0.06, np.tile(lighten(np.array(srgb(P["ear_in"])), 0.3), (N, 1)), np.tile(lighten(cream, 0.5), (N, 1)), rad0=0.003, bind=(2, ei))
        # ---- tails
        for ti, (cl, radii, rad, R, ground) in enumerate(self.tail_cores):
            self.tail_fur(cl, radii, rad, R, ground, ti)

    def ear_axis_world(self, p):
        """comb direction on an ear: toward its tip"""
        out = np.zeros_like(p)
        cvec, _ = self.head_matrix()
        side = np.sign(self.head_local(p)[:, 1])
        for sgn, (b, t, axis, facing, across, Lr, w) in self.ear_tips.items():
            tw = self.head_dirs(np.array(t)[None, :])[0] * self.hs + np.array(cvec)
            sel = side == sgn
            out[sel] = tw - p[sel]
        return out

    def tail_fur(self, cl, radii, rad, R, ground, ti=0):
        """dense fur combed toward the tip, flaring out where the tail is thick; at the tip it gathers into a curling flame"""
        P, rng = self.P, self.nrng
        cream, glow = srgb(P["cream"]), srgb(P["tip_glow"])
        cla = np.array([tuple(q) for q in cl])
        n = len(cla)
        seglen = np.linalg.norm(np.diff(cla, axis=0), axis=1)
        length = seglen.sum()
        N = int(52000 * self.fur_density * length / 3.0 * (R / 0.5) ** 1.5)
        rr = np.array(radii)
        wts = (rr[:-1] + rr[1:]) * seglen
        seg = rng.choice(n - 1, N, p=wts / wts.sum())
        f = rng.random(N)
        t = (seg + f) / (n - 1)
        cen = cla[seg] * (1 - f)[:, None] + cla[seg + 1] * f[:, None]
        tg = cla[seg + 1] - cla[seg]
        tg /= np.linalg.norm(tg, axis=1, keepdims=True)
        ref = np.where(np.abs(tg[:, 2:3]) < 0.9, np.array([[0, 0, 1.0]]), np.array([[1.0, 0, 0]]))
        u = np.cross(tg, ref)
        u /= np.linalg.norm(u, axis=1, keepdims=True)
        w = np.cross(tg, u)
        a = rng.uniform(0, 2 * np.pi, N)
        radial = u * np.cos(a)[:, None] + w * np.sin(a)[:, None]
        keep = ~(radial[:, 2] < -0.45) if ground else np.ones(N, bool)
        t, cen, tg, radial, seg = t[keep], cen[keep], tg[keep], radial[keep], seg[keep]
        roots = cen + radial * rr[seg][:, None] * 0.97
        grid = np.linspace(0, 1, 50)
        rt = np.interp(t, grid, np.array([rad(q) for q in grid]))
        L = 0.14 + 0.95 * rt
        comb = tg + radial * 0.55
        # the tip: strands from the last part of the tail gather to a point beyond the end
        tipdir = cla[-1] - cla[-5]
        tipdir /= np.linalg.norm(tipdir)
        flame_pt = cla[-1] + tipdir * 0.42 + np.array([0, 0, 0.08])
        tipw = ss(0.78, 0.97, t)
        to_tip = flame_pt - roots
        dist = np.linalg.norm(to_tip, axis=1)
        comb = comb * (1 - tipw[:, None]) + (to_tip / dist[:, None]) * tipw[:, None]
        L = L * (1 - tipw) + dist * 1.02 * tipw
        g60 = np.linspace(0, 1, 60)
        col = np.array([self.tail_color(q, cream, glow) for q in g60])
        ci = lambda q: np.stack([np.interp(q, g60, col[:, k]) for k in range(3)], 1)
        c0 = ci(t)
        c1 = ci(np.minimum(1.0, t + 0.1 + 0.2 * tipw))
        c0 = c0 + (1 - c0) * 0.06
        c1 = c1 + (1 - c1) * (0.15 + 0.3 * ss(0.6, 0.9, t)[:, None])
        clump = 0.62 + 0.3 * tipw
        glowing = t > 0.84
        for sel, key in ((~glowing, "fur"), (glowing, "glow")):
            self.strands(key, roots[sel], radial[sel], comb[sel], L[sel], 0.2, clump[sel], 0.15, c0[sel], c1[sel], droop=0.05, K=9, rad0=0.0045, jitter=0.12,
                         bind=(3, ti), bind_t=t[sel])

    def build_tails(self):
        P, rnd = self.P, self.rnd
        cream = srgb(P["cream"])
        glow = srgb(P["tip_glow"])
        tails = self.pose["tails"]
        order = [0, 1, 2, 1, 1, 1, 1, 1, 1][: self.n_tails]
        self.tail_tips = []
        self.tail_cores = []
        self.tail_objs = []
        for ti in range(self.n_tails):
            ctrl, R, ground = tails[order[ti]]
            ctrl = [Vector(c) for c in ctrl]
            if ti >= 3:                                         # extra tails (trait): copies of the raised tail, fanned out sideways like a peacock
                k = ti - 2
                sg = 1 if k % 2 else -1
                ctrl, R, ground = tails[1]
                ctrl = [Vector(c) for c in ctrl]
                M = Matrix.Rotation(sg * 0.18 * (1 + k // 2), 3, "Z") @ Matrix.Rotation(sg * 0.42 * (1 + k // 2), 3, "X")
                root = ctrl[0]
                ctrl = [root + M @ (c - root) * (0.88 - 0.04 * k) for c in ctrl]
                R *= 0.85
            cl = resample(catmull(ctrl, 120), 70)
            n = len(cl)

            def rad(t):
                return R * (0.32 + 0.68 * math.sin(min(1.0, t / 0.55) * math.pi / 2) ** 1.3) * (1 - smooth(0.62, 1.0, t) ** 1.4 * 0.92)
            if ground:                                           # a tail lying on the ground rests on it
                cl = [Vector((p.x, p.y, max(p.z, GROUND_Z + rad(i / (n - 1)) * 0.78))) for i, p in enumerate(cl)]
            radii = [rad(i / (n - 1)) * 0.62 for i in range(n)]
            rings = tube(cl, radii, flat=0.9 if not ground else 0.78, segs=18, up=Z)
            v, f = loft(rings)
            cols = []
            for i in range(n):
                t = i / (n - 1)
                c = self.tail_color(t, cream, glow)
                cols.extend([lin(c)] * 18)
            self.tail_objs.append((add_object("tail", v, f, cols, self.mat_coat), n, 18))
            self.tail_cores.append((cl, radii, rad, R, ground))
            tip, tg = cl[-1], (cl[-1] - cl[-4]).normalized()
            self.tail_tips.append((tip, tg))

    def tail_color(self, t, cream, glow):
        P = self.P
        c = grad(P["coat"], 0.75 - 0.3 * t)
        c = mix(c, cream, smooth(0.66, 0.82, t))
        return mix(c, glow, smooth(0.86, 1.0, t) * 0.7)

    # ---------------------------------------------------------- ribbon, bell, flower
    def build_ribbon(self):
        """a soft ribbon round the neck, under the cheek fluff, with the bow on the near side and a little bell"""
        P = self.P
        hc = Vector(self.pose["head"])
        top = Vector(self.pose["spine"][-1][:3])
        c = top.lerp(hc, 0.3)
        axis = (hc - top).normalized()
        self.ribbon_c, self.ribbon_axis = np.array(c), np.array(axis)
        u = axis.cross(Y).normalized()
        w = axis.cross(u).normalized()
        pts = []
        bvh = self.bvh_of([self.body])
        for q in range(48):
            a = 2 * math.pi * q / 48
            d = (u * math.cos(a) + w * math.sin(a))
            hit = bvh.ray_cast(c + d * 2.0, -d)
            p = hit[0] + d * 0.06 if hit[0] is not None else c + d * 0.55
            pts.append(p)
        for _ in range(3):
            pts = [(pts[i - 1] + pts[i] * 2 + pts[(i + 1) % 48]) / 4 for i in range(48)]
        pts.append(pts[0])
        rings = tube(pts, [0.1] * len(pts), flat=0.3, bref=lambda p: axis, segs=10)
        v, f = loft(rings)
        cols = [lin(mix(srgb(P["ribbon"]), srgb(P["ribbon_dark"]), 0.25 * (k in (4, 5, 6)))) for _ in rings for k in range(10)]
        add_object("ribbon", v, f, cols, self.mat_ribbon)
        # the bow sits on the near side, toward the front
        a_bow = math.radians(-60 if NEAR < 0 else 60)
        dbow = (u * math.cos(a_bow) + w * math.sin(a_bow)).normalized()
        best = min(pts, key=lambda p: -(p - c).normalized().dot(dbow))
        kc = best + dbow * 0.05
        out = dbow
        upb = (axis - out * axis.dot(out)).normalized()
        sideb = upb.cross(out).normalized()
        v, f = ellipsoid(kc, sideb * 0.09, upb * 0.08, out * 0.06, 12, 8)
        add_object("ribbon", v, f, [lin(srgb(P["ribbon_dark"]))] * len(v), self.mat_ribbon)
        for s, (ang, ln) in enumerate(((0.35, 0.36), (-0.25, 0.32))):          # two loops, not the same size
            sg = 1 if s == 0 else -1
            loop = []
            for q in range(25):
                t = 2 * math.pi * q / 24
                x_ = (1 - math.cos(t)) / 2 * ln
                y_ = math.sin(t) * ln * 0.36
                loop.append(kc + sideb * (sg * x_) + upb * (y_ + ang * x_) + out * (0.04 * math.sin(t / 2)))
            rings = tube(loop, [0.05] * len(loop), flat=0.35, bref=lambda p: out, segs=8)
            v, f = loft(rings)
            add_object("ribbon", v, f, [lin(mix(srgb(P["ribbon"]), (1, 1, 1), 0.1 * (k in (0, 1, 7))) ) for _ in rings for k in range(8)], self.mat_ribbon)
        for s, (dx, ln) in enumerate(((0.06, 0.42), (-0.05, 0.34))):            # the two ends hang down, one longer
            tail = [kc + sideb * (dx * q / 6 + 0.02) - upb * (ln * q / 6) + out * (0.03 * math.sin(q / 6 * math.pi)) for q in range(7)]
            rings = tube(tail, [0.048 * (1 - 0.2 * q / 6) for q in range(7)], flat=0.3, bref=lambda p: out, segs=8)
            v, f = loft(rings)
            add_object("ribbon", v, f, [lin(srgb(P["ribbon"]))] * len(v), self.mat_ribbon)
        # bell at the front, a little off the middle
        a_b = math.radians(-12 * NEAR * -1)
        db = (u * math.cos(a_b) + w * math.sin(a_b)).normalized()
        bp = max(pts, key=lambda p: (p - c).normalized().dot(Vector((1, 0, -0.6)).normalized() + db * 0.0)) + Vector((0.06, NEAR * 0.05, -0.1))
        v, f = ellipsoid(bp, X * 0.11, Y * 0.11, Z * 0.105, 18, 12)
        add_object("bell", v, f, None, self.mat_bell)
        v, f = ellipsoid(bp + Vector((0.09, 0, -0.04)), X * 0.02, Y * 0.06, Z * 0.012, 10, 6)
        add_object("bell_slot", v, f, None, self.mat_dark)
        v, f = ellipsoid(bp + Vector((0.05, -0.05, 0.06)), X * 0.02, Y * 0.02, Z * 0.015, 8, 6)
        add_object("bell_glint", v, f, None, self.mat_glint)

    def build_flower(self):
        """a small blossom tucked at the base of the near ear"""
        b, t, axis, facing, across, L, w = self.ear_tips[NEAR]
        bvh = self.bvh_of(self.head_objs)
        tgt = self.Hp(*(b + axis * 0.08 + facing * 0.25 - across * 0.15))
        out = self.Hd(0.35, NEAR * 0.8, 0.5)
        hit = bvh.ray_cast(tgt + out * 1.5, -out)
        if hit[0] is None:
            return
        nn = hit[1] if hit[1].dot(out) > 0 else -hit[1]
        self.flower(hit[0] + nn * 0.02, (nn + self.Hd(0.3, 0, 0.3)).normalized(), 0.3, 1, 0.4, 2)

    # ---------------------------------------------------------- foxfire
    def flame(self, base, size, lean, name="fire"):
        """a kitsunebi: a flame of cool spirit fire, wide and soft at the bottom, splitting into a tall curling tongue and two
        small ones; pale pink at the root, lilac at the tips, inside a faint halo"""
        P = self.P
        side = lean.cross(Z).normalized() if lean.length > 1e-3 else Y
        tongues = [(1.0, 0.0, 1.0, 1.0), (0.55, 0.5, -0.7, 0.62), (0.42, -0.55, 0.8, 0.55)]    # (height, offset across, sway, width)
        for scale, mat, nm, cshift in ((1.0, self.mat_fire, name, 0.0), (1.35, self.mat_halo, name + "_halo", 0.2)):
            for hgt, acr, curl, wid in tongues:
                n = 22
                pts, rr = [], []
                for i in range(n):
                    t = i / (n - 1)
                    sway = math.sin(t * math.pi * 1.4) * 0.4 * curl
                    p = base + Z * (size * (2.7 * hgt * t)) + side * (size * (acr * t * 0.9 + sway * t)) + lean * (size * 0.7 * t ** 2 * hgt)
                    pts.append(p)
                    bulb = math.sin(min(1.0, (t + 0.08) * 2.6) * math.pi / 2) ** 0.5            # round at the bottom
                    rr.append(size * wid * scale * bulb * (1 - t) ** 1.15 * (0.62 + 0.38 * math.cos(t * math.pi / 2)) + 0.003)
                if scale != 1.0:
                    pts = [base + (p - base) * 1.1 - Z * size * 0.12 for p in pts]
                rings = tube(pts, rr, segs=14, up=X)
                v, f = loft(rings)
                v.append(pts[0] - Z * rr[1] * 0.4)
                nb = len(v) - 1
                for k in range(14):
                    f.append((nb, (k + 1) % 14, k))
                cols = [lin(grad(P["fire"], min(1.0, cshift + 0.1 + 0.9 * (i / (n - 1)) ** 0.8 * (0.6 + 0.4 * hgt)))) for i in range(n) for _ in range(14)]
                cols.append(lin(grad(P["fire"], cshift)))
                add_object(nm, v, f, cols, mat)
        for k in range(3):                                  # sparkles drifting off it
            a = 2.3 * k + 0.6
            sp = base + Vector((math.cos(a) * size * 1.8, math.sin(a) * size * 1.2, size * (2.9 + 0.8 * k)))
            self.star(sp, size * (0.34 - 0.08 * k))

    def star(self, c, s):
        """a four-point sparkle, in two crossed planes so it shows from every side"""
        for ax in (X, Y):
            verts, faces = [c], []
            for k in range(8):
                a = math.pi * k / 4
                r = s if k % 2 == 0 else s * 0.26
                verts.append(c + ax * (math.cos(a) * r) + Z * (math.sin(a) * r))
            for k in range(8):
                faces.append((0, 1 + k, 1 + (k + 1) % 8))
            add_object("star", verts, faces, None, self.mat_spark)

    def build_fire(self):
        for k, (x, y, z, s) in enumerate(self.pose["fire"]):
            lean = Vector((0.5 if k % 2 else -0.6, 0, 0)) + Vector((0, 0.2, 0))
            b0 = set(bpy.data.objects)
            self.flame(Vector((x, y, z)), s, lean)
            self.fire_parts.append((Vector((x, y, z)), s, list(set(bpy.data.objects) - b0)))

    def build_ground(self):
        me = bpy.data.meshes.new("ground")
        me.from_pydata([(-30, -30, GROUND_Z), (30, -30, GROUND_Z), (30, 30, GROUND_Z), (-30, 30, GROUND_Z)], [], [(0, 1, 2, 3)])
        ob = bpy.data.objects.new("ground", me)
        bpy.context.collection.objects.link(ob)
        ob.is_shadow_catcher = True


# ------------------------------------------------------------------ rig: smooth weights on the built model, for looping animation
def _rot(axis, ang):
    axis = np.asarray(axis, np.float64)
    axis = axis / np.linalg.norm(axis)
    x, y, z = axis
    c, s_, C = math.cos(ang), math.sin(ang), 1 - math.cos(ang)
    return np.array([[c + x * x * C, x * y * C - z * s_, x * z * C + y * s_],
                     [y * x * C + z * s_, c + y * y * C, y * z * C - x * s_],
                     [z * x * C - y * s_, z * y * C + x * s_, c + z * z * C]])


class FoxRig:
    """Moves the finished fox without rebuilding it: every surface point and fur strand follows the head, ears, tails, breathing
    chest or foxfire it belongs to, with smooth weights where parts meet. Fur strands move with the skin they grow from, so they
    never jump between frames. All motions are periodic over the loop."""

    def __init__(self, fox):
        self.fox = fox
        hx, hy, hz = fox.pose["head"]
        self.hc = np.array([hx, hy, hz])
        top = np.array(fox.pose["spine"][-1][:3])
        self.pivot = top + (self.hc - top) * 0.45
        self.spine = np.array([tuple(p) for p in fox.spine_pts])
        self.meshes = []                                    # (object, rest coords, kind, extra)
        for part, obs in fox.parts.items():
            if part == "tails":
                for ti, (ob, n, segs) in enumerate(obs):
                    co = self.co(ob)
                    t = (np.arange(len(co)) // segs) / max(n - 1, 1)
                    self.meshes.append((ob, co, "tail", (ti, np.minimum(t, 1.0))))
                continue
            for i, ob in enumerate(obs):
                if ob.type != "MESH":
                    continue
                kind = {"body": "body", "neck": "body", "head": "head", "ears": "ear", "ear_in": "ear"}[part]
                self.meshes.append((ob, self.co(ob), kind, i % 2 if kind == "ear" else None))
        self.fires = [(np.array(tuple(base)), sz, [(ob, self.co(ob)) for ob in obs if ob.type == "MESH"]) for base, sz, obs in fox.fire_parts]
        self.tail_roots = [np.array(tuple(c[0][0])) for c in fox.tail_cores]
        self.tail_amp = [math.radians(4.0 if c[4] else 8.0) for c in fox.tail_cores]
        self.ears = []
        for sgn, (b, t, axis, facing, across, Lr, w) in fox.ear_tips.items():
            self.ears.append((np.array(tuple(fox.Hp(*b))), np.array(tuple(fox.Hd(*across)))))
        self.fur = getattr(fox, "fur_objs", [])

    @staticmethod
    def co(ob):
        n = len(ob.data.vertices)
        a = np.empty(n * 3, np.float32)
        ob.data.vertices.foreach_get("co", a)
        return a.reshape(n, 3).astype(np.float64)

    # ---- the motions at loop phase ph (0..2pi)
    def head_tf(self, ph):
        R = _rot((0, 0, 1), math.radians(3.0) * math.sin(ph + 0.8)) @ _rot((1, 0, 0), math.radians(2.6) * math.sin(ph)) \
            @ _rot((0, 1, 0), math.radians(1.6) * math.sin(2 * ph))
        return lambda p: (p - self.pivot) @ R.T + self.pivot

    def ear_tf(self, ei, f, nfr):
        b, ax = self.ears[ei]
        # the near ear gives a quick flick early in the loop; the far ear only sways gently
        if ei == 0:
            u = (f / nfr) * 24.0
            ang = math.radians(14) * math.exp(-((u - 6.0) / 1.2) ** 2)
        else:
            ang = math.radians(2.5) * math.sin(2 * math.pi * f / nfr + 2.0)
        R = _rot(ax, -ang)
        return lambda p: (p - b) @ R.T + b

    def tail_tf(self, ti, ph):
        root, amp = self.tail_roots[ti], self.tail_amp[ti]

        def tf(p, t):
            a = amp * np.sin(ph + 1.3 * ti - 2.4 * t) * t ** 1.3
            c, s_ = np.cos(a), np.sin(a)
            d = p - root
            out = d.copy()
            out[:, 0] = d[:, 0] * c - d[:, 1] * s_
            out[:, 1] = d[:, 0] * s_ + d[:, 1] * c
            return out + root
        return tf

    def body_tf(self, ph, H):
        """breathing (the chest swells a little) plus a smooth blend into the head motion near the neck"""
        sp = self.spine
        breath = 0.028 * math.sin(ph)

        def tf(p):
            d2 = ((p[:, None, :] - sp[None, ::2, :]) ** 2).sum(-1)
            j = np.argmin(d2, axis=1) * 2
            u = j / (len(sp) - 1)
            radial = p - sp[j]
            w = np.exp(-((u - 0.55) / 0.3) ** 2) * ss(1.2, 0.6, np.linalg.norm(radial, axis=1))
            q = p + radial * (breath * w)[:, None]
            wh = ss(1.55, 0.95, np.linalg.norm(p - self.hc, axis=1) / self.fox.hs)
            return q + (H(q) - q) * wh[:, None]
        return tf

    def frame(self, f, nfr):
        ph = 2 * math.pi * f / nfr
        H = self.head_tf(ph)
        B = self.body_tf(ph, H)
        for ob, co, kind, extra in self.meshes:
            if kind == "body":
                new = B(co)
            elif kind == "head":
                new = H(co)
            elif kind == "ear":
                new = H(self.ear_tf(extra, f, nfr)(co))
            else:
                ti, t = extra
                new = self.tail_tf(ti, ph)(co, t)
            ob.data.vertices.foreach_set("co", new.astype(np.float32).ravel())
            ob.data.update()
        for k, (base, sz, items) in enumerate(self.fires):
            lift = np.array([0.05 * math.sin(ph * 2 + 1.7 * k), 0.0, 0.09 * math.sin(ph + 2.1 * k)])
            sc = 1 + 0.06 * math.sin(3 * ph + k)
            for ob, co in items:
                new = (co - base) * np.array([sc, sc, 1 + 0.1 * math.sin(3 * ph + k)]) + base + lift
                ob.data.vertices.foreach_set("co", new.astype(np.float32).ravel())
                ob.data.update()
        for ob, P0, kind, idx, tt in self.fur:
            N, K, _ = P0.shape
            new = P0.astype(np.float64).copy()
            sel = kind == 0
            if sel.any():
                roots = new[sel, 0, :]
                new[sel] += (B(roots) - roots)[:, None, :]
            sel = kind == 1
            if sel.any():
                new[sel] = H(new[sel].reshape(-1, 3)).reshape(-1, K, 3)
            for ei in range(len(self.ears)):
                sel = (kind == 2) & (idx == ei)
                if sel.any():
                    new[sel] = H(self.ear_tf(ei, f, nfr)(new[sel].reshape(-1, 3))).reshape(-1, K, 3)
            for ti in range(len(self.tail_roots)):
                sel = (kind == 3) & (idx == ti)
                if sel.any():
                    t = (tt[sel][:, None] + 0.08 * np.linspace(0, 1, K)[None, :]).reshape(-1)
                    new[sel] = self.tail_tf(ti, ph)(new[sel].reshape(-1, 3), np.minimum(t, 1.0)).reshape(-1, K, 3)
            ob.data.position_data.foreach_set("vector", new.astype(np.float32).ravel())
            ob.data.update_tag()
        closed = f in self.blink_frames(nfr)
        for ob in self.fox.blink_open:
            ob.hide_render = closed
        for ob in self.fox.blink_closed:
            ob.hide_render = not closed

    @staticmethod
    def blink_frames(nfr):
        a = int(round(nfr * 15 / 24))
        return {a, a + 1}


class WalkRig(FoxRig):
    """A walk cycle on the standing fox, in place (the game moves the sprite). Each leg swings from its shoulder or hip in a
    four-beat walk (hind near, fore near, hind far, fore far). In the stance part of a step the paw moves back at a steady
    speed, so a paw on the ground does not slide against the meadow; in the swing part the lower leg folds and the paw lifts.
    Skin, ruff and fur near each leg follow it with smooth weights; the body bobs twice per cycle."""

    STANCE = 0.6
    OFFSETS = (0.25, 0.75, 0.0, 0.5)          # fore near, fore far, hind near, hind far

    def __init__(self, fox, stride=1.1):
        super().__init__(fox)
        P = fox.pose
        self.stride = stride
        chains = list(P["fore"].items()) + list(P["hind"].items())
        self.legs = []
        for li, ((sgn, chain), (dl, top)) in enumerate(zip(chains, fox.legs)):
            pts = np.array([tuple(v) for v in dl])
            hind = li >= 2
            pivot = np.array(P["haunch"][sgn][0]) if hind else pts[0] + np.array([0, 0, 0.1])
            poly = np.vstack([pivot, pts])
            seg = np.linalg.norm(np.diff(poly, axis=0), axis=1)
            tpar = np.concatenate([[0.0], np.cumsum(seg)]) / seg.sum()
            kn = int(len(poly) * 0.58)
            h = pivot[2] - pts[-1][2]
            A = math.asin(min(0.85, stride / (2 * h)))
            self.legs.append(dict(poly=poly, t=tpar, pivot=pivot, knee=poly[kn], kt=tpar[kn], A=A, r=max(q[3] for q in chain),
                                  bend=0.75 if hind else 0.95, off=self.OFFSETS[li]))
        # leg weights at rest, for the skin and for each fur strand's root
        self.mesh_w = {}
        for k, (ob, co, kind, extra) in enumerate(self.meshes):
            if kind == "body":
                self.mesh_w[k] = self.leg_weights(co)
        self.fur_w = []
        for ob, P0, kind, idx, tt in self.fur:
            w = np.zeros((len(P0), 3))
            sel = kind == 0
            if sel.any():
                w[sel] = self.leg_weights(P0[sel, 0, :].astype(np.float64))
            self.fur_w.append(w)

    def leg_weights(self, p):
        """per point: (leg index, weight, position along the leg 0 hip .. 1 paw)"""
        best_d = np.full(len(p), 1e9)
        best_t = np.zeros(len(p))
        best_l = np.zeros(len(p))
        for li, L in enumerate(self.legs):
            poly, tp = L["poly"], L["t"]
            for j in range(len(poly) - 1):
                a, b = poly[j], poly[j + 1]
                ab = b - a
                u = np.clip(((p - a) @ ab) / max(ab @ ab, 1e-9), 0, 1)
                d = np.linalg.norm(p - (a + u[:, None] * ab), axis=1)
                better = d < best_d
                best_d[better] = d[better]
                best_t[better] = tp[j] + u[better] * (tp[j + 1] - tp[j])
                best_l[better] = li
        r = np.array([self.legs[int(i)]["r"] for i in best_l])
        w = ss(r + 0.34, r + 0.1, best_d) * ss(0.1, 0.42, best_t)
        return np.stack([best_l, w, best_t], axis=1)

    def leg_angles(self, L, u):
        """swing angle at the hip and extra fold at the knee, for cycle position u (0..1)"""
        q = (u + L["off"]) % 1.0
        A = L["A"]
        if q < self.STANCE:                                 # paw on the ground, moving back steadily
            return -A + 2 * A * q / self.STANCE, 0.0
        s = (q - self.STANCE) / (1 - self.STANCE)          # paw in the air, swinging forward
        return A - 2 * A * (0.5 - 0.5 * math.cos(math.pi * s)), L["bend"] * math.sin(math.pi * s)

    def apply_legs(self, p, W, u, bob):
        out = p.copy()
        li_all = W[:, 0].astype(int)
        for li, L in enumerate(self.legs):
            sel = (li_all == li) & (W[:, 1] > 1e-4)
            if not sel.any():
                continue
            th, be = self.leg_angles(L, u)
            R1 = _rot((0, 1, 0), th)
            q = p[sel]
            q1 = (q - L["pivot"]) @ R1.T + L["pivot"]
            knee = (L["knee"] - L["pivot"]) @ R1.T + L["pivot"]
            R2 = _rot((0, 1, 0), be)
            q2 = (q1 - knee) @ R2.T + knee
            k = ss(L["kt"] - 0.08, L["kt"] + 0.08, W[sel, 2])[:, None]
            q1 = q1 + (q2 - q1) * k
            w = W[sel, 1][:, None]
            # the paws stay on the ground while the body bobs
            moved = q + (q1 - q) * w - np.array([0, 0, bob]) * (w * W[sel, 2][:, None])
            # nothing goes through the ground: a folding lower leg can otherwise push a paw below it
            moved[:, 2] = np.maximum(moved[:, 2], np.minimum(q[:, 2], GROUND_Z))
            out[sel] = moved
        return out

    def frame(self, f, nfr):
        u = f / nfr
        ph = 2 * math.pi * u
        bob = 0.045 * math.cos(4 * math.pi * u)
        lift = np.array([0, 0, bob])
        R = _rot((0, 0, 1), math.radians(1.5) * math.sin(ph)) @ _rot((1, 0, 0), math.radians(1.2) * math.sin(ph + 0.6)) \
            @ _rot((0, 1, 0), math.radians(2.2) * math.sin(2 * ph + 0.9))
        H = lambda p: (p - self.pivot) @ R.T + self.pivot + lift
        B0 = self.body_tf(ph, lambda p: (p - self.pivot) @ R.T + self.pivot)
        B = lambda p: B0(p) + lift
        for k, (ob, co, kind, extra) in enumerate(self.meshes):
            if kind == "body":
                new = self.apply_legs(B(co), self.mesh_w[k], u, bob)
            elif kind == "head":
                new = H(co)
            elif kind == "ear":
                new = H(self.ear_tf(extra, 0, nfr)(co))
            else:
                ti, t = extra
                new = self.tail_tf(ti, ph)(co, t) + lift
            ob.data.vertices.foreach_set("co", new.astype(np.float32).ravel())
            ob.data.update()
        for k, (base, sz, items) in enumerate(self.fires):
            fl = np.array([0.05 * math.sin(ph + 1.7 * k), 0.0, 0.08 * math.sin(ph + 2.1 * k)]) + lift
            sc = 1 + 0.06 * math.sin(2 * ph + k)
            for ob, co in items:
                new = (co - base) * np.array([sc, sc, 1 + 0.1 * math.sin(2 * ph + k)]) + base + fl
                ob.data.vertices.foreach_set("co", new.astype(np.float32).ravel())
                ob.data.update()
        for (ob, P0, kind, idx, tt), W in zip(self.fur, self.fur_w):
            N, K, _ = P0.shape
            new = P0.astype(np.float64).copy()
            sel = kind == 0
            if sel.any():
                roots = new[sel, 0, :]
                moved = new[sel] + (B(roots) - roots)[:, None, :]
                Wp = np.repeat(W[sel], K, axis=0)
                new[sel] = self.apply_legs(moved.reshape(-1, 3), Wp, u, bob).reshape(-1, K, 3)
            sel = kind == 1
            if sel.any():
                new[sel] = H(new[sel].reshape(-1, 3)).reshape(-1, K, 3)
            for ei in range(len(self.ears)):
                sel = (kind == 2) & (idx == ei)
                if sel.any():
                    new[sel] = H(self.ear_tf(ei, 0, nfr)(new[sel].reshape(-1, 3))).reshape(-1, K, 3)
            for ti in range(len(self.tail_roots)):
                sel = (kind == 3) & (idx == ti)
                if sel.any():
                    t = (tt[sel][:, None] + 0.08 * np.linspace(0, 1, K)[None, :]).reshape(-1)
                    new[sel] = (self.tail_tf(ti, ph)(new[sel].reshape(-1, 3), np.minimum(t, 1.0)) + lift).reshape(-1, K, 3)
            ob.data.position_data.foreach_set("vector", new.astype(np.float32).ravel())
            ob.data.update_tag()
        for ob in self.fox.blink_open:                      # eyes open the whole walk
            ob.hide_render = False
        for ob in self.fox.blink_closed:
            ob.hide_render = True


def anchor_px(sc, cam, p):
    """where a world point lands in the rendered frame, in pixels from the top left"""
    from bpy_extras.object_utils import world_to_camera_view
    v = world_to_camera_view(sc, cam, Vector(p))
    return (v.x * sc.render.resolution_x, (1 - v.y) * sc.render.resolution_y)


def stage(sc, view, zoom=None):
    """camera and lights shared by stills and animation"""
    center = Vector((-0.3, 0, 3.05)) if zoom is None else Vector((zoom[0], 0, zoom[1]))
    tgt = bpy.data.objects.new("target", None)
    bpy.context.collection.objects.link(tgt)
    tgt.location = center
    az = {"side": 0, "front": 90, "back": -90, "three": 40}[view]
    cam = K.make_camera(sc, az, center, ortho=8.0 if zoom is None else zoom[2])
    pitch = math.radians(9)
    a = math.radians(az)
    cam.location = center + Vector((math.sin(a) * math.cos(pitch), -math.cos(a) * math.cos(pitch), math.sin(pitch))) * 40.0
    cam.rotation_euler = (math.radians(90) - pitch, 0, a)
    K.add_lights(cam, tgt)
    for nm, energy, size, color, loc in (("top", 420, 12.0, (1, 1, 1), (0.5, 0.3, 11.0)), ("bounce", 480, 16.0, (1.0, 0.95, 0.93), (1.0, -8.0, 0.9))):
        ld = bpy.data.lights.new(nm, "AREA")
        ld.energy, ld.size, ld.color = energy, size, color
        ob = bpy.data.objects.new(nm, ld)
        bpy.context.collection.objects.link(ob)
        ob.location = loc
        c = ob.constraints.new("TRACK_TO")
        c.target, c.track_axis, c.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
    sc.view_settings.exposure = -0.25
    return cam


def render_anim(P, pose, view, out, size, nfr, traits, motion="idle"):
    """a seamless loop of nfr frames at game size. idle: breathing, head sway, an ear flick, a blink, tails swaying, foxfire
    bobbing. walk: a walk cycle in place (WalkRig). Also writes anchor.json: where the fox's ground origin lands in the frame,
    the same for every pose and motion seen from one view, so the game can swap animations without the fox jumping."""
    sc = K.setup_scene(False)
    sc.cycles.samples = int(os.environ.get("FOX_SAMPLES", "64"))
    sc.render.resolution_x, sc.render.resolution_y = size, int(round(size * 0.913))
    fox = Fox3D(P, pose, traits or {})
    rig = WalkRig(fox) if motion == "walk" else FoxRig(fox)
    cam = stage(sc, view)
    d = os.path.join(out, f"{pose}-{view}-{motion}")
    os.makedirs(d, exist_ok=True)
    import json
    bpy.context.view_layer.update()                    # so the camera's placement is applied before projecting
    ax, ay = anchor_px(sc, cam, (0.0, 0.0, GROUND_Z))
    json.dump(dict(anchor=[ax, ay], size=[sc.render.resolution_x, sc.render.resolution_y], frames=nfr, motion=motion,
                   stride_px=(rig.stride * size / 8.0 if motion == "walk" else 0.0)), open(os.path.join(d, "anchor.json"), "w"))
    only = os.environ.get("FOX_FRAMES")
    frames = [int(x) for x in only.split(",")] if only else range(nfr)
    for f in frames:
        rig.frame(f, nfr)
        sc.render.filepath = os.path.join(d, f"frame_{f:02d}.png")
        bpy.ops.render.render(write_still=True)
        print("rendered", sc.render.filepath)


def render_job(P, pose, view, out, quick, traits=None, tag=""):
    sc = K.setup_scene(quick)
    Fox3D(P, pose, traits or {})
    zoom = None
    if "@" in view:
        view, zz = view.split("@")
        zoom = [float(v) for v in zz.split(",")]
    center = Vector((-0.3, 0, 3.05)) if zoom is None else Vector((zoom[0], 0, zoom[1]))
    tgt = bpy.data.objects.new("target", None)
    bpy.context.collection.objects.link(tgt)
    tgt.location = center
    az = {"side": 0, "front": 90, "back": -90, "three": 40}[view]
    cam = K.make_camera(sc, az, center, ortho=8.0 if zoom is None else zoom[2])
    pitch = math.radians(9)
    a = math.radians(az)
    cam.location = center + Vector((math.sin(a) * math.cos(pitch), -math.cos(a) * math.cos(pitch), math.sin(pitch))) * 40.0
    cam.rotation_euler = (math.radians(90) - pitch, 0, a)
    K.add_lights(cam, tgt)
    for nm, energy, size, color, loc in (("top", 420, 12.0, (1, 1, 1), (0.5, 0.3, 11.0)), ("bounce", 480, 16.0, (1.0, 0.95, 0.93), (1.0, -8.0, 0.9))):
        ld = bpy.data.lights.new(nm, "AREA")
        ld.energy, ld.size, ld.color = energy, size, color
        ob = bpy.data.objects.new(nm, ld)
        bpy.context.collection.objects.link(ob)
        ob.location = loc
        c = ob.constraints.new("TRACK_TO")
        c.target, c.track_axis, c.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
    hide = os.environ.get("FOX_HIDE")
    if hide:
        for ob in bpy.data.objects:
            if ob.name.startswith(tuple(hide.split(","))):
                ob.hide_render = True
    sc.view_settings.exposure = -0.25
    sc.render.filepath = os.path.join(out, f"{pose}-{view}{tag}{'-z%d' % round(zoom[0] * 10) if zoom else ''}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", sc.render.filepath)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = argv[0]
    quick = "--quick" in argv
    traits = {}
    tag = ""
    for a in argv:
        if a.startswith("--tails="):
            traits["tails"] = int(a.split("=")[1])
            tag = f"-t{traits['tails']}"
    anim = [a.split("=", 1)[1] for a in argv if a.startswith("--anim=")]
    walk = [a.split("=", 1)[1] for a in argv if a.startswith("--walk=")]
    if walk:
        size = next((int(a.split("=")[1]) for a in argv if a.startswith("--size=")), 640)
        nfr = next((int(a.split("=")[1]) for a in argv if a.startswith("--frames=")), 12)
        for job in walk:
            pose, view = job.split(":", 1)
            render_anim(EMBER, pose, view, out, size, nfr, traits, "walk")
        sys.exit(0)
    if anim:
        size = next((int(a.split("=")[1]) for a in argv if a.startswith("--size=")), 640)
        nfr = next((int(a.split("=")[1]) for a in argv if a.startswith("--frames=")), 24)
        for job in anim:
            pose, view = job.split(":", 1)
            render_anim(EMBER, pose, view, out, size, nfr, traits)
        sys.exit(0)
    jobs = [a for a in argv[1:] if ":" in a] or ["sit:side", "sit:three", "sit:front", "sit:back", "stand:side", "stand:three", "play:side", "play:three", "sleep:side", "sleep:three"]
    for job in jobs:
        pose, view = job.split(":", 1)
        render_job(EMBER, pose, view, out, quick, traits, tag)
