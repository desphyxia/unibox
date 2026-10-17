"""Sea-horse as one 3D model, rendered from any camera (Blender, headless).

Why: in the 2D rigs (seahorse.py) every view is drawn by its own code, so the same hair, fin or stripe looks
different in different views. Here the creature exists once, as geometry, and a view is only a camera.
The pose numbers (spine joints, head placement, belly bump, fin ranges) are the ones from seahorse.py;
the front and back widths come from a lateral-width table, so the three views cannot drift apart.

Everything is generated: a tapered elliptical tube for body and tail, a lofted head, hair locks as flat tubes,
fins as ray fans with a membrane, eyes from ellipsoids, stripes and shading as vertex colours.
No outlines. Soft light, pastel colours, transparent background (the underwater backdrop is a separate image).

Usage: blender -b -P seahorse3d.py -- OUTDIR [--quick] [pose:view ...]
       poses: idle swim sleep      views: side front back three (three-quarter)
"""
import bpy, bmesh, math, os, sys, random
from mathutils import Vector, Matrix
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import seahorse as R                       # the 2D rig: pose numbers, head outline, palettes
from artgen5 import spl, mixhex

S = 0.01                                   # one 2D pixel = 0.01 world units
K = 8
STYLE = dict(fin="veil", ridge=True, crest=True, tail="fin", snout="normal", pattern="stripes")


# ------------------------------------------------------------------ small helpers
def srgb(h):
    v = [int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    return tuple(((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92 for c in v)


def lin(c, a=1.0):
    return (c[0], c[1], c[2], a)


def mix(a, b, t):
    t = max(0.0, min(1.0, t))
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))


def smooth(e0, e1, x):
    t = max(0.0, min(1.0, (x - e0) / (e1 - e0)))
    return t * t * (3 - 2 * t)


def grad(stops, t):
    t = max(0.0, min(1.0, t))
    for (o0, c0), (o1, c1) in zip(stops, stops[1:]):
        if t <= o1:
            return mix(srgb(c0), srgb(c1), (t - o0) / max(o1 - o0, 1e-6))
    return srgb(stops[-1][1])


def P3(x, y, lat=0.0):
    """2D pose pixel (x right, y down) plus a lateral offset in pixels -> world (X forward-ish, Y lateral, Z up)."""
    return Vector(((x - 400) * S, lat * S, (640 - y) * S))


def D3(dx, dy):
    return Vector((dx, 0.0, -dy))


# ------------------------------------------------------------------ mesh building
def add_object(name, verts, faces, cols, mat, smooth_shade=True):
    me = bpy.data.meshes.new(name)
    me.from_pydata([tuple(v) for v in verts], [], faces)
    me.update()
    if cols is not None:
        attr = me.color_attributes.new("Col", "FLOAT_COLOR", "POINT")
        flat = []
        for c in cols:
            flat.extend(c if len(c) == 4 else (c[0], c[1], c[2], 1.0))
        attr.data.foreach_set("color", flat)
    if smooth_shade:
        me.polygons.foreach_set("use_smooth", [True] * len(me.polygons))
    ob = bpy.data.objects.new(name, me)
    bpy.context.collection.objects.link(ob)
    ob.data.materials.append(mat)
    return ob


def loft(rings, close_ring=True):
    """Quads between consecutive rings (each a list of Vectors). Returns verts, faces."""
    verts, faces = [], []
    m = len(rings[0])
    for r in rings:
        verts.extend(r)
    for i in range(len(rings) - 1):
        for j in range(m):
            j2 = (j + 1) % m if close_ring else j + 1
            if not close_ring and j == m - 1:
                continue
            faces.append((i * m + j, i * m + j2, (i + 1) * m + j2, (i + 1) * m + j))
    return verts, faces


def ellipsoid(center, ax, ay, az, nu=20, nv=12):
    verts, faces = [], []
    for v in range(nv + 1):
        phi = math.pi * v / nv
        for u in range(nu):
            th = 2 * math.pi * u / nu
            x, y, z = math.sin(phi) * math.cos(th), math.sin(phi) * math.sin(th), math.cos(phi)
            verts.append(center + ax * x + ay * y + az * z)
    for v in range(nv):
        for u in range(nu):
            u2 = (u + 1) % nu
            faces.append((v * nu + u, v * nu + u2, (v + 1) * nu + u2, (v + 1) * nu + u))
    return verts, faces


def tube(points, radii, flat=1.0, bref=None, segs=8, up=None):
    """Swept tube along `points`. flat<1 squashes it into a ribbon whose broad side is along `bref(point)` x tangent.
    Returns a list of rings (lists of Vectors)."""
    n = len(points)
    T = []
    for i in range(n):
        a, b = points[max(i - 1, 0)], points[min(i + 1, n - 1)]
        t = (b - a)
        T.append(t.normalized() if t.length > 1e-9 else Vector((1, 0, 0)))
    rings, u_prev = [], None
    for i in range(n):
        if bref is not None:
            u = T[i].cross(bref(points[i]))
            if u.length < 1e-6:
                u = T[i].cross(Vector((0, 0, 1)))
        elif u_prev is None:
            u = T[i].cross(up if up is not None else Vector((0, 1, 0)))
            if u.length < 1e-6:
                u = T[i].cross(Vector((0, 0, 1)))
        else:
            u = u_prev - T[i] * u_prev.dot(T[i])
        u = u.normalized()
        u_prev = u
        v = T[i].cross(u).normalized()
        r = max(radii[i], 1e-4)
        ring = [points[i] + u * (r * math.cos(2 * math.pi * k / segs)) + v * (r * flat * math.sin(2 * math.pi * k / segs)) for k in range(segs)]
        rings.append(ring)
    return rings


def bezier(p0, p1, p2, p3, n):
    out = []
    for i in range(n + 1):
        t = i / n
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
        out.append(p0 * a + p1 * b + p2 * c + p3 * d)
    return out


# ------------------------------------------------------------------ materials
def material(name, rough=0.5, alpha=1.0, sss=0.0, vc=True, color=None, emit=0.0, spec=0.35, sheen=0.0):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    bsdf.inputs["Roughness"].default_value = rough
    bsdf.inputs["Alpha"].default_value = alpha
    bsdf.inputs["Subsurface Weight"].default_value = sss
    bsdf.inputs["Subsurface Radius"].default_value = (0.5, 0.35, 0.3)
    bsdf.inputs["Specular IOR Level"].default_value = spec
    bsdf.inputs["Sheen Weight"].default_value = sheen
    if vc:
        node = nt.nodes.new("ShaderNodeVertexColor")
        node.layer_name = "Col"
        nt.links.new(node.outputs["Color"], bsdf.inputs["Base Color"])
        if emit:
            nt.links.new(node.outputs["Color"], bsdf.inputs["Emission Color"])
            bsdf.inputs["Emission Strength"].default_value = emit
    else:
        bsdf.inputs["Base Color"].default_value = lin(color)
        if emit:
            bsdf.inputs["Emission Color"].default_value = lin(color)
            bsdf.inputs["Emission Strength"].default_value = emit
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    return m


# ------------------------------------------------------------------ the creature
class Sea3D:
    def __init__(self, P, pose_name, traits):
        self.P, self.pose_name, self.traits = P, pose_name, traits
        self.pose = R.POSES[pose_name]
        self.f_sn = R.SNOUT[traits["snout"]]
        self.mat_coat = material("coat", rough=0.62, sss=0.25, spec=0.25)
        self.mat_hair = material("hair", rough=0.45, sss=0.1, spec=0.3, sheen=0.4)
        self.mat_fin = material("fin", rough=0.5, alpha=0.95, sss=0.2, spec=0.2)
        self.mat_ray = material("ray", rough=0.5, alpha=0.9, spec=0.2)
        self.mat_dark = material("dark", rough=0.35, vc=False, color=srgb(P["lash"]), spec=0.5)
        self.mat_iris = material("iris", rough=0.2, vc=False, color=srgb(P["iris_g"][1][1]), spec=0.6)
        self.mat_iris2 = material("iris2", rough=0.2, vc=False, color=srgb(P["iris_g"][0][1]), spec=0.6)
        self.mat_pupil = material("pupil", rough=0.2, vc=False, color=srgb(P["pupil"]), spec=0.6)
        self.mat_white = material("eyewhite", rough=0.3, vc=False, color=srgb(P["eye_white"]), spec=0.5)
        self.mat_glint = material("glint", rough=0.2, vc=False, color=(1, 1, 1), emit=6.0)
        self.mat_nostril = material("nostril", rough=0.5, vc=False, color=srgb(P["nostril"]))
        self.mat_mark = material("mark", rough=0.5, vc=False, color=srgb(P["mark"]), spec=0.4)
        self.objects = []
        self.build_spine()
        self.build_body()
        self.build_head()
        if traits["crest"]:
            self.build_hair()
        self.build_fins()
        self.build_face()
        self.build_decals()

    # ---------------------------------------------------------- spine
    def build_spine(self):
        pose = self.pose
        ctrl = pose["spine"]
        dense = spl(ctrl, 10)
        xy = [(p[0], p[1]) for p in dense]
        # arc-length resample so the rings are evenly spaced (fine enough for stripes)
        arc = [0.0]
        for i in range(1, len(dense)):
            arc.append(arc[-1] + math.hypot(xy[i][0] - xy[i - 1][0], xy[i][1] - xy[i - 1][1]))
        step = 2.4
        n = int(arc[-1] / step)
        self.rings = []
        j = 0
        for i in range(n + 1):
            s = min(i * step, arc[-1])
            while j < len(arc) - 2 and arc[j + 1] < s:
                j += 1
            t = (s - arc[j]) / max(arc[j + 1] - arc[j], 1e-9)
            p0, p1 = dense[j], dense[j + 1]
            x, y, w = (p0[k] + (p1[k] - p0[k]) * t for k in range(3))
            u = (j + t) / 10.0
            self.rings.append(dict(x=x, y=y, w=w, u=u, s=s))
        pts = [(r["x"], r["y"]) for r in self.rings]
        for i, r in enumerate(self.rings):
            a, b = pts[max(i - 1, 0)], pts[min(i + 1, len(pts) - 1)]
            dx, dy = b[0] - a[0], b[1] - a[1]
            L = math.hypot(dx, dy) or 1
            r["t"] = (dx / L, dy / L)
            r["n"] = (-dy / L, dx / L)                    # points to the back, as in the 2D rig
        # the belly bump: how far the bump ellipse reaches beyond the tube on the belly side
        bx, by, brx, bry, brot = pose["belly"]
        c, s_ = math.cos(math.radians(-brot)), math.sin(math.radians(-brot))
        front = []
        for r in self.rings:
            px, py = r["x"] - bx, r["y"] - by
            dx, dy = -r["n"][0], -r["n"][1]
            lx, ly = px * c - py * s_, px * s_ + py * c
            ldx, ldy = dx * c - dy * s_, dx * s_ + dy * c
            A = ldx * ldx / brx ** 2 + ldy * ldy / bry ** 2
            B = 2 * (lx * ldx / brx ** 2 + ly * ldy / bry ** 2)
            C = lx * lx / brx ** 2 + ly * ly / bry ** 2 - 1
            disc = B * B - 4 * A * C
            tfar = (-B + math.sqrt(disc)) / (2 * A) if (disc > 0 and C <= 0) else 0.0   # only rings whose middle is inside the bump
            front.append(max(r["w"] / 2, min(tfar, r["w"] / 2 + 80)))
        sm = []
        for i in range(len(front)):
            lo, hi = max(0, i - 6), min(len(front), i + 7)
            sm.append(sum(front[lo:hi]) / (hi - lo))
        for r, f in zip(self.rings, sm):
            r["rf"] = max(f, r["w"] / 2)
            r["rb"] = r["w"] / 2

    LAT = [(0, 40), (1, 46), (1.7, 50), (2.3, 67), (3.0, 78), (3.6, 83), (5, 81), (6.3, 63), (7.3, 36), (8, 20), (9, 0)]

    def lateral(self, u, ra):
        t = self.LAT
        v = t[-1][1]
        for (u0, v0), (u1, v1) in zip(t, t[1:]):
            if u <= u1:
                v = v0 + (v1 - v0) * (u - u0) / (u1 - u0)
                break
        return max(v, ra * 0.98)

    def center3(self, r):
        """world point of the middle of the cross-section, with the in-plane normal (to the back) and the lateral axis"""
        shift = (r["rf"] - r["rb"]) / 2
        cx, cy = r["x"] - r["n"][0] * shift, r["y"] - r["n"][1] * shift
        return P3(cx, cy), D3(*r["n"]), Vector((0, 1, 0)), (r["rf"] + r["rb"]) / 2 * S, self.lateral(r["u"], (r["rf"] + r["rb"]) / 2) * S

    # ---------------------------------------------------------- body colours
    def stripes(self):
        """stripe centres and half-thicknesses along the arc, spaced by the local width (same rule as the 2D rig)"""
        out, acc, last = [], 0.0, None
        for i, r in enumerate(self.rings):
            if i < 4 or i > len(self.rings) - 5:
                continue
            if last is not None:
                acc += r["s"] - last
            last = r["s"]
            period = max(16.0, min(48.0, r["w"] * 0.46))
            if acc >= period:
                acc = 0.0
                out.append((r["s"], max(4.0, min(22.0, period * 0.5)) * 0.5))
        return out

    def coat_color(self, y_px, theta, i, ring_t):
        P, pose = self.P, self.pose
        cy0, cy1 = pose["coat_y"]
        col = grad(P["coat"], (y_px - cy0) / (cy1 - cy0))
        r = self.rings[i]
        n = len(self.rings)
        body_end = pose["tail_from"] * 10
        taper = min(1.0, i / 12.0, max(0.0, (n - 1 - i)) / 14.0) ** 1.2
        belly = max(0.0, -math.cos(theta) - 0.05) / 0.95
        back = max(0.0, math.cos(theta) - 0.05) / 0.95
        col = mix(col, srgb(P["belly"]), belly ** 1.1 * 0.5 * taper)
        col = mix(col, srgb(P["shade"]), back ** 1.2 * 0.3 * taper)
        return col

    # ---------------------------------------------------------- body
    def build_body(self):
        P = self.P
        rings3, cols = [], []
        segs = 48
        stripes = self.stripes() if self.traits["pattern"] == "stripes" else []
        ring_c = srgb(mixhex(P["ring"], P["shade"], 0.2))
        mark = srgb(P["mark"])
        ring_to = self.pose["ring_to"]
        for i, r in enumerate(self.rings):
            C, N, Y, ra, rb = self.center3(r)
            ring, ccol = [], []
            Tz = D3(*r["t"]).z
            level = smooth(0.9, 0.98, abs(Tz))              # on the upright trunk keep stripes level in the picture, not square to the tilted axis
            for k in range(segs):
                th = 2 * math.pi * k / segs
                p = C + N * (ra * math.cos(th)) + Y * (rb * math.sin(th))
                ring.append(p)
                yy = 640 - p.z * 100
                s_here = r["s"] + level * ((p.z - C.z) * 100.0) / Tz if Tz else r["s"]
                sw = 0.0
                for sc, hh in stripes:
                    sw = max(sw, 1.0 - smooth(hh - 1.6, hh + 1.6, abs(s_here - sc)))
                ph = (s_here / 24.0) % 1.0                    # thin bony ring lines on the neck and body
                rw = 1.0 - smooth(0.0, 0.12, min(ph, 1 - ph)) if (3 < i and r["u"] < ring_to) else 0.0
                c = self.coat_color(yy, th, i, 0)
                c = mix(c, ring_c, rw * 0.22)
                c = mix(c, mark, sw * 0.5)
                ccol.append(lin(c))
            rings3.append(ring)
            cols.append(ccol)
        # close both ends with a point
        first = sum((v for v in rings3[0]), Vector()) / segs
        last = sum((v for v in rings3[-1]), Vector()) / segs
        verts, faces = loft(rings3)
        flat_cols = [c for rc in cols for c in rc]
        nv = len(verts)
        verts.append(first)
        verts.append(last)
        flat_cols.append(cols[0][0])
        flat_cols.append(cols[-1][0])
        for k in range(segs):
            k2 = (k + 1) % segs
            faces.append((nv, k2, k))
            faces.append((nv + 1, (len(rings3) - 1) * segs + k, (len(rings3) - 1) * segs + k2))
        self.body = add_object("body", verts, faces, flat_cols, self.mat_coat)
        self.objects.append(self.body)

    # ---------------------------------------------------------- head
    def head_frame(self):
        hx, hy, hang, hs = self.pose["head"]
        th = math.radians(hang)
        self.hs = hs
        self.fwd = Vector((math.cos(th), 0, -math.sin(th)))
        self.upv = Vector((math.sin(th), 0, math.cos(th)))
        self.lat = Vector((0, 1, 0))
        self.hc = P3(hx, hy)

    def H(self, lx, lz, lat=0.0):
        """head-local pixels (forward, up, lateral) -> world"""
        return self.hc + (self.fwd * lx + self.upv * lz + self.lat * lat) * (S * self.hs)

    def outline(self):
        pts = [(R.sx(x, self.f_sn), y) for x, y in R.HEAD_PTS]
        n = len(pts)
        poly = []
        for i in range(n):
            p0, p1, p2, p3 = pts[(i - 1) % n], pts[i], pts[(i + 1) % n], pts[(i + 2) % n]
            c1 = (p1[0] + (p2[0] - p0[0]) / 6, p1[1] + (p2[1] - p0[1]) / 6)
            c2 = (p2[0] - (p3[0] - p1[0]) / 6, p2[1] - (p3[1] - p1[1]) / 6)
            for k in range(14):
                t = k / 14
                a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3
                poly.append((a * p1[0] + b * c1[0] + c * c2[0] + d * p2[0], a * p1[1] + b * c1[1] + c * c2[1] + d * p2[1]))
        return poly

    def slice_at(self, poly, x):
        ys = []
        for (x0, y0), (x1, y1) in zip(poly, poly[1:] + poly[:1]):
            if (x0 - x) * (x1 - x) <= 0 and x0 != x1:
                ys.append(y0 + (y1 - y0) * (x - x0) / (x1 - x0))
        return (min(ys), max(ys)) if ys else (0, 0)

    LATH = [(-52, 10), (-44, 52), (-30, 72), (-6, 86), (30, 88), (60, 74), (90, 50), (120, 36), (150, 26), (166, 16)]

    def head_lat(self, x, vr):
        t = self.LATH
        v = t[-1][1]
        xx = x / 1.0
        # the snout is stretched by sx(): undo the stretch to read the table
        if x > 60:
            xx = 60 + (x - 60) / self.f_sn
        for (x0, v0), (x1, v1) in zip(t, t[1:]):
            if xx <= x1:
                v = v0 + (v1 - v0) * (xx - x0) / (x1 - x0)
                break
        return min(v, 1.18 * vr + 6) if x > 40 else v

    def build_head(self):
        P = self.P
        self.head_frame()
        poly = self.outline()
        xmin, xmax = min(p[0] for p in poly) + 0.5, max(p[0] for p in poly) - 0.5
        xs = [xmin + (xmax - xmin) * (0.5 - 0.5 * math.cos(math.pi * k / 54)) for k in range(55)]
        segs = 40
        rings, cols, self.head_rings = [], [], []
        cy0, cy1 = self.pose["coat_y"]
        for x in xs:
            top, bot = self.slice_at(poly, x)
            zc, vr = -(top + bot) / 2, (bot - top) / 2
            L = self.head_lat(x, vr)
            self.head_rings.append((x, zc, vr, L))
            ring, cc = [], []
            for k in range(segs):
                ph = 2 * math.pi * k / segs
                lat, z = L * math.cos(ph), zc + vr * math.sin(ph)
                p = self.H(x, z, lat)
                ring.append(p)
                yy = 640 - p.z * 100
                c = grad(P["coat"], (yy - cy0) / (cy1 - cy0))
                under = max(0.0, -math.sin(ph))
                c = mix(c, srgb(P["belly"]), under * 0.25)
                # blush on both cheeks (near the side surface, below the eye, in front of the cheek)
                dx, dz = (x - 70) / 30.0, (z - (-30)) / 20.0
                side = abs(math.cos(ph))
                c = mix(c, srgb(P["blush"]), math.exp(-(dx * dx + dz * dz)) * side * 0.8 * P["blush_o"])
                cc.append(lin(c))
            rings.append(ring)
            cols.append(cc)
        verts, faces = loft(rings)
        flat = [c for rc in cols for c in rc]
        nv = len(verts)
        for end, ri in ((0, 0), (1, len(rings) - 1)):
            cen = sum((v for v in rings[ri]), Vector()) / segs
            verts.append(cen)
            flat.append(cols[ri][0])
            for k in range(segs):
                k2 = (k + 1) % segs
                a, b = ri * segs + k, ri * segs + k2
                faces.append((nv + end, b, a) if end == 0 else (nv + end, a, b))
        self.head = add_object("head", verts, faces, flat, self.mat_coat)
        self.objects.append(self.head)
        self.xs_head = xs

    def head_surface(self, x, phi):
        """world point on the head surface at head-local x and angle phi (0 = side, +90 = top, -90 = underside)"""
        best = min(self.head_rings, key=lambda r: abs(r[0] - x))
        _, zc, vr, L = best
        return self.H(x, zc + vr * math.sin(phi), L * math.cos(phi))

    # ---------------------------------------------------------- hair
    def hair_color(self, idx, t):
        if isinstance(idx, tuple):                       # a blend of two of the three hair gradients
            k0, k1, f = idx
            return mix(grad(self.P["hair"][k0], t), grad(self.P["hair"][k1], t), f)
        return grad(self.P["hair"][idx % 3], t)

    @staticmethod
    def hair_blend(pos):
        """pos 0..2 runs peach -> pink/violet -> blue; locks near the middle of the head are peach, outer locks blue"""
        pos = max(0.0, min(2.0, pos))
        k0 = min(int(pos), 1)
        return (k0, k0 + 1, pos - k0)

    def lock(self, pts, w, idx, radial_center, segs=8, flat=0.55, tint=0.0):
        n = len(pts) - 1
        radii = []
        for i in range(n + 1):
            t = i / n
            wd = w * (0.14 + 0.86 * math.sin(min(1.0, t * 1.9) * math.pi / 2)) * (1 - t ** 3.0) ** 0.45 * (1 + 0.2 * math.sin(t * math.pi))
            radii.append(max(wd / 2 * S, 0.0015))
        rings = tube(pts, radii, flat=flat, bref=lambda p: (p - radial_center).normalized(), segs=segs)
        verts, faces = loft(rings)
        cols = []
        for i, ring in enumerate(rings):
            c = lin(mix(self.hair_color(idx, i / n), (1, 1, 1), tint))
            cols.extend([c] * segs)
        return add_object("lock", verts, faces, cols, self.mat_hair)

    def build_hair(self):
        """One head of hair for every view: locks rise from the crown, arch back and hang round the back of the head.
        Locks at the sides hang behind the eye, so the side view keeps the face clear; from the front they fall beside
        the head; from behind they cover the back of the skull and the neck."""
        hs = self.hs
        S_ = S * hs
        centre = self.H(0, 0, 0)
        cap_c = self.H(-26, 24, 0)
        v, f = ellipsoid(cap_c, self.fwd * 0.56 * hs, self.lat * 0.68 * hs, self.upv * 0.52 * hs, 28, 16)
        cols = [lin(self.hair_color(self.hair_blend(0.95), 0.42 - 0.22 * max(-1.0, min(1.0, (p - cap_c).dot(self.upv) / (0.52 * hs))))) for p in v]
        self.objects.append(add_object("haircap", v, f, cols, self.mat_hair))
        angles = list(range(-112, 113, 8))
        for layer, (rad, drop, wmul) in enumerate(((1.0, 1.0, 1.0), (0.6, 0.7, 0.9))):
            for j, a in enumerate(angles):
                if layer == 1 and j % 2 == 0:
                    continue
                psi = math.radians(a)
                cpsi, spsi = math.cos(psi), math.sin(psi)
                root = self.H(-10 - 24 * cpsi, 58 - 26 * abs(spsi) - 6 * layer, 56 * spsi)
                h1, h2 = 0.5 + 0.5 * math.sin(j * 2.3 + layer), 0.5 + 0.5 * math.sin(j * 1.7 + 2 * layer + 1)
                end = self.H(-70 - 38 * cpsi * rad - 26 * h1, -62 - 82 * drop - 46 * h2 + 18 * abs(spsi), 118 * spsi * rad + 12 * spsi)
                c1 = root + (self.upv * 62 + self.fwd * (-8) + self.lat * (28 * spsi)) * S_
                c2 = end + (self.upv * 120 + self.fwd * 54 + self.lat * (-8 * spsi)) * S_
                pts = bezier(root, c1, c2, end, 26)
                pts = [p + (self.lat * (7 * math.sin(i * 0.45 + j * 1.3)) + self.fwd * (6 * math.sin(i * 0.38 + j * 0.9 + 1))) * (S_ * i / 26)
                       for i, p in enumerate(pts)]
                w = 40 * wmul
                hb = self.hair_blend(abs(a) / 112.0 * 2.0 + 0.25 * layer)
                self.objects.append(self.lock(pts, w, hb, centre))
                if j % 2 == 0 and layer == 0:                                      # a bright strand riding on top of the lock
                    hi = [p + (p - centre).normalized() * (0.012 * hs) for p in pts[2:23]]
                    self.objects.append(self.lock(hi, 10, hb, centre, tint=0.75, flat=0.5))
        # a pompadour of locks swept up and back from the forehead
        for q, dx in enumerate((0, 24, -24, 46, -46)):
            root = self.H(30 - abs(dx) * 0.35, 58 - abs(dx) * 0.2, dx * 0.9)
            up, fw = self.upv * S_, self.fwd * S_
            pts = bezier(root, root + up * 46 + fw * 22, root + up * 76 - fw * 26, root + up * 34 - fw * 96, 16)
            pts = [p + self.lat * (S_ * dx * 0.22 * (i / 16)) for i, p in enumerate(pts)]
            self.objects.append(self.lock(pts, 56 - abs(dx) * 0.3, self.hair_blend(abs(dx) / 46.0 * 1.4), centre, flat=0.8))

    # ---------------------------------------------------------- fins
    def fan3(self, rays, ruffle=0.0, op_scale=1.0, base_band=False):
        """rays: list of (root, direction (unit), length, amp, phase). Builds ray tubes plus a membrane with scalloped edge."""
        P = self.P
        M = 12
        curves = []
        for q, (root, d, L, amp, ph) in enumerate(rays):
            perp = Vector((-d.z, 0, d.x))
            pts = []
            for j in range(M + 1):
                s = j / M
                off = amp * S * math.sin(ph + s * 2.4 * math.pi) * s ** 0.8
                lat = ruffle * S * (1 if q % 2 else -1) * s ** 1.3 * 40
                pts.append(root + d * (L * S * s) + perp * off + Vector((0, lat, 0)) + Vector((0, 0, -0.1 * s * s * S * 10)))
            curves.append(pts)
        fin_lo, fin_hi = srgb(P["fin_g"][0][1]), srgb(P["fin_g"][-1][1])
        ray_c = srgb(P["ray"])
        verts, faces, cols = [], [], []

        def add_pt(p, c):
            verts.append(p)
            cols.append(lin(c))
            return len(verts) - 1
        for q in range(len(curves) - 1):
            a, b = curves[q], curves[q + 1]
            idx = []
            for j in range(M + 1):
                s = j / M
                mid = (a[j] + b[j]) / 2
                scal = 1.0 if s < 0.55 else 1 - 0.30 * ((s - 0.55) / 0.45) ** 1.4
                rm = (a[0] + b[0]) / 2
                mid = rm + (mid - rm) * scal
                c = mix(mix(fin_lo, srgb("#e3cdfa"), min(1.0, s * 1.6)), fin_hi, max(0.0, s - 0.35) * 1.4)
                c = mix(c, srgb("#ffffff"), 0.28 * (1 - s) ** 1.5)
                idx.append((add_pt(a[j], c), add_pt(mid, c), add_pt(b[j], c)))
            for j in range(M):
                for (k0, k1) in ((0, 1), (1, 2)):
                    faces.append((idx[j][k0], idx[j][k1], idx[j + 1][k1], idx[j + 1][k0]))
        out = []
        if verts:
            out.append(add_object("fin", verts, faces, cols, self.mat_fin))
        # rays
        for pts in curves:
            radii = [0.011 * (1 - j / M) + 0.003 for j in range(M + 1)]
            rings = tube(pts, radii, flat=0.5, segs=4, up=Vector((0, 1, 0)))
            v, f = loft(rings)
            out.append(add_object("ray", v, f, [lin(ray_c)] * len(v), self.mat_ray))
        if base_band:
            roots = [c[0] for c in curves]
            if len(roots) > 2:
                radii = [0.03 * math.sin(math.pi * i / (len(roots) - 1)) ** 0.6 + 0.008 for i in range(len(roots))]
                rings = tube(roots, radii, flat=0.8, segs=6, up=Vector((0, 1, 0)))
                v, f = loft(rings)
                out.append(add_object("finbase", v, f, [lin(mix(ray_c, srgb("#ffffff"), 0.2))] * len(v), self.mat_ray))
        self.objects.extend(out)
        return out

    def spine_ring(self, u):
        """the ring whose spine parameter is nearest u"""
        return min(self.rings, key=lambda r: abs(r["u"] - u))

    def build_fins(self):
        pose, tr = self.pose, self.traits
        hs = self.hs
        # dorsal fin
        if tr["fin"] != "none":
            d0, d1 = pose["dorsal"]
            if tr["fin"] == "small":
                d0, d1, nr, length, spread, sweep, flut = d0 + 0.5, d1 - 0.5, 8, 66, 16, 32, 3
            else:
                nr, length, spread, sweep, flut = 15, pose.get("fin_len", 96), 16, 32, 3
            rays = []
            for q in range(nr):
                u = q / (nr - 1)
                r = self.spine_ring(d0 + (d1 - d0) * u)
                C, N, Y, ra, rb = self.center3(r)
                T = D3(*r["t"])
                phi = math.radians(-spread + 2 * spread * u + sweep)
                d = (N * math.cos(phi) + T * math.sin(phi)).normalized()
                L = length * (0.72 + 0.28 * math.sin(u * math.pi))
                rays.append((C + N * ra * 0.82, d, L, flut * (1 if q % 2 else -1), q * 0.8))
            self.fan3(rays, ruffle=0.6, base_band=True)
        # ridge spikes
        if tr["ridge"]:
            r0, r1 = pose["ridge"]
            for q in range(11):
                u = q / 10
                r = self.spine_ring(r0 + (r1 - r0) * u)
                C, N, Y, ra, rb = self.center3(r)
                T = D3(*r["t"])
                phi = math.radians(-34)
                d = (N * math.cos(phi) + T * math.sin(phi)).normalized()
                root = C + N * ra * 0.9
                L = (44 + 16 * math.sin(u * math.pi)) * S
                pts = [root + d * (L * s) + Vector((0, 0, 0)) + (N * (0.05 * math.sin(q + s * 6) * s)) for s in [i / 10 for i in range(11)]]
                radii = [0.05 * (1 - (i / 10)) ** 0.9 + 0.003 for i in range(11)]
                rings = tube(pts, radii, flat=0.5, segs=6, up=Vector((0, 1, 0)))
                v, f = loft(rings)
                c = lin(grad(self.P["hair"][q % 3], 0.4 + 0.5 * u))
                self.objects.append(add_object("ridge", v, f, [c] * len(v), self.mat_hair))
        # pectoral fins, one each side, rooted on the body side at the neck
        pc = pose["pect"]
        r = self.spine_ring(self.u_for_y(pc["at"][1]))
        C, N, Y, ra, rb = self.center3(r)
        for sgn in (-1, 1):
            rays = []
            a0 = math.radians(pc["ang"])
            for q in range(7):
                uu = q / 6
                off = (q - 3) * 8
                ang = a0 - math.radians(pc["spread"]) + 2 * math.radians(pc["spread"]) * uu
                d2 = D3(math.cos(ang), math.sin(ang))
                d = (d2 + Vector((0, 0.95 * sgn, 0))).normalized()
                perp = Vector((-d2.z, 0, d2.x))
                root = C + Y * sgn * rb * 0.86 + perp * off * S
                L = pc["length"] * 1.15 * (0.72 + 0.28 * math.sin(uu * math.pi))
                rays.append((root, d, L, 2.5 * (1 if q % 2 else -1), q * 0.8))
            self.fan3(rays, ruffle=0.12)
        # tail fin at the tip
        if tr["tail"] == "fin":
            r = self.rings[-1]
            C, N, Y, ra, rb = self.center3(r)
            T = D3(*r["t"])
            base = math.degrees(math.atan2(T.z, T.x))
            rays = []
            for q in range(7):
                uu = q / 6
                ang = math.radians(base - 62 + 124 * uu)
                d = Vector((math.cos(ang), 0, math.sin(ang)))
                perp = Vector((-d.z, 0, d.x))
                rays.append((C + perp * (q - 3) * 5 * S, d, 78 * (0.72 + 0.28 * math.sin(uu * math.pi)), 2.5 * (1 if q % 2 else -1), q * 0.8))
            self.fan3(rays, ruffle=0.4)

    def u_for_y(self, y):
        return min(self.rings, key=lambda r: abs(r["y"] - y))["u"]

    # ---------------------------------------------------------- face
    def build_face(self):
        P, hs = self.P, self.hs
        closed_eye = self.pose["eye"] != "open"
        # ear fins behind the eye
        for sgn in (-1, 1):
            rays = []
            for q in range(5):
                ang = math.radians(-168 + q * 14)
                d = (self.fwd * math.cos(ang) + self.upv * (-math.sin(ang))).normalized()
                root = self.H(-24 - q * 0, 16 - q * 7, sgn * 62)
                d = (d + self.lat * 0.4 * sgn).normalized()
                rays.append((root, d, (34 - abs(q - 2) * 4) * hs, 2, q))
            self.fan3(rays, ruffle=0.1)
        # eyes
        tilt = math.radians(42)
        x_e = 52
        best = min(self.head_rings, key=lambda r: abs(r[0] - x_e))
        _, zc, vr, L = best
        for sgn in (-1, 1):
            out = (self.lat * sgn * math.cos(tilt) + self.fwd * math.sin(tilt)).normalized()
            ex = (self.fwd * math.cos(tilt) - self.lat * sgn * math.sin(tilt)).normalized()
            ez = self.upv
            C = self.H(x_e, 4, sgn * L * 0.9) - out * 0.0
            rx, ry = 0.27 * hs, 0.31 * hs
            if not closed_eye:
                parts = [
                    (C, rx, ry, 0.10 * hs, self.mat_white, 0.0, 0.0, 0.0),
                    (C, rx * 0.86, ry * 0.88, 0.075 * hs, self.mat_iris, 0.045 * hs, 0.02, -0.03),
                    (C, rx * 0.62, ry * 0.64, 0.06 * hs, self.mat_iris2, 0.062 * hs, 0.02, -0.02),
                    (C, rx * 0.4, ry * 0.5, 0.05 * hs, self.mat_pupil, 0.078 * hs, 0.025, -0.035),
                ]
                for cen, ax_, az_, ao_, mat, off, sx_, sz_ in parts:
                    cc = cen + out * off + ex * (sx_ * hs) + ez * (sz_ * hs)
                    v, f = ellipsoid(cc, ex * ax_, ez * az_, out * ao_, 28, 18)
                    self.objects.append(add_object("eye", v, f, None, mat))
                for off, dx, dz, rr in ((0.115, 0.09, 0.09, 0.062), (0.105, -0.05, -0.14, 0.032)):
                    cc = C + out * (off * hs) + ex * (dx * hs) + ez * (dz * hs)
                    v, f = ellipsoid(cc, ex * rr * hs, ez * rr * hs, out * rr * hs * 0.6, 12, 8)
                    self.objects.append(add_object("glint", v, f, None, self.mat_glint))
                # upper lid line and lashes
                P0, C0, P2 = (-rx / S / hs - 1, 3), (-2, ry / S / hs + 7), (rx / S / hs + 1, 5)
                lid = []
                for k in range(18):
                    t = k / 17
                    a, b = (1 - t) ** 2 * P0[0] + 2 * (1 - t) * t * C0[0] + t * t * P2[0], (1 - t) ** 2 * P0[1] + 2 * (1 - t) * t * C0[1] + t * t * P2[1]
                    depth = 0.10 * hs * math.sqrt(max(0.02, 1 - (a * S / rx) ** 2 - (b * S / ry) ** 2)) + 0.012
                    lid.append(C + ex * (a * S * hs) + ez * (b * S * hs) + out * depth)
                rings = tube(lid, [0.022 * hs * (0.5 + 0.5 * math.sin(math.pi * k / 17) ** 0.6) for k in range(18)], flat=1.0, segs=6, up=out)
                v, f = loft(rings)
                self.objects.append(add_object("lid", v, f, None, self.mat_dark))
                for t_, ln, bend in ((0.04, 13, 5), (0.2, 10, 3), (0.38, 7, 1)):
                    k = int(t_ * 17)
                    base = lid[k]
                    dirv = (lid[min(k + 1, 17)] - lid[max(k - 1, 0)]).normalized()
                    nrm = (ez - dirv * dirv.dot(ez)).normalized()
                    pts = [base + nrm * (ln * S * hs * s) - ex * (bend * S * hs * s * s) for s in [i / 6 for i in range(7)]]
                    rings = tube(pts, [0.014 * hs * (1 - i / 6) + 0.002 for i in range(7)], flat=1.0, segs=5, up=out)
                    v, f = loft(rings)
                    self.objects.append(add_object("lash", v, f, None, self.mat_dark))
            else:
                arc = []
                for k in range(18):
                    t = k / 17
                    a = (-rx / S / hs - 2) * (1 - t) + (rx / S / hs + 2) * t
                    b = -ry / S / hs * 0.45 * math.sin(math.pi * t) + (1 - t) * 0.0
                    arc.append(C + ex * (a * S * hs) + ez * (b * S * hs) + out * (0.06 * hs))
                rings = tube(arc, [0.02 * hs * (0.5 + 0.5 * math.sin(math.pi * k / 17) ** 0.6) for k in range(18)], segs=6, up=out)
                v, f = loft(rings)
                self.objects.append(add_object("lid", v, f, None, self.mat_dark))
                for t_, ln, bend in ((0.08, 12, 4), (0.24, 10, 3), (0.4, 8, 1)):
                    k = int(t_ * 17)
                    base = arc[k]
                    pts = [base - ez * (ln * S * hs * s) - ex * (bend * S * hs * s * s) for s in [i / 6 for i in range(7)]]
                    rings = tube(pts, [0.014 * hs * (1 - i / 6) + 0.002 for i in range(7)], segs=5, up=out)
                    v, f = loft(rings)
                    self.objects.append(add_object("lash", v, f, None, self.mat_dark))

    # ---------------------------------------------------------- decals: nostrils, mouth, chest star
    def build_decals(self):
        P, hs = self.P, self.hs
        bpy.context.view_layer.update()
        deps = bpy.context.evaluated_depsgraph_get()
        bvh_h = BVHTree.FromObject(self.head, deps)
        bvh_b = BVHTree.FromObject(self.body, deps)

        def project(bvh, p, d, push=0.006):
            hit = bvh.ray_cast(p, d)
            if hit[0] is None:
                return None
            return hit[0] + hit[1] * push
        sn = lambda x: R.sx(x, self.f_sn)
        for sgn in (-1, 1):
            # nostril: a small dark ellipse on the side of the snout tip
            c0 = self.H(sn(146), 8, 0)
            start = c0 + self.lat * sgn * 1.0
            hit = project(bvh_h, start, -self.lat * sgn, 0.0)
            if hit is not None:
                v, f = ellipsoid(hit, self.fwd * 0.056 * hs, self.upv * 0.04 * hs, self.lat * sgn * 0.02 * hs, 12, 8)
                self.objects.append(add_object("nostril", v, f, None, self.mat_nostril))
            # mouth line along the lower side of the snout
            pts = []
            for k in range(14):
                t = k / 13
                x = sn(161 - 30 * t)
                z = -(27 + 8 * math.sin(t * math.pi * 0.9) - 0 * t) + 2
                o = self.H(x, z, 0) + self.lat * sgn * 1.0
                h = project(bvh_h, o, -self.lat * sgn, 0.004)
                if h is not None:
                    pts.append(h)
            if len(pts) > 3:
                rings = tube(pts, [0.016 * hs] * len(pts), segs=6, up=self.upv)
                v, f = loft(rings)
                self.objects.append(add_object("mouth", v, f, None, self.mat_nostril))
        # cutie-mark star on each flank, on the belly bump
        bx, by, brx, bry, brot = self.pose["belly"]
        ctr = P3(bx + 4, by + 2)
        for sgn in (-1, 1):
            hit = bvh_b.ray_cast(ctr + Vector((0, 3.0 * sgn, 0)), Vector((0, -sgn, 0)))
            if hit[0] is None:
                continue
            cen, nrm = hit[0], hit[1]
            up = Vector((0, 0, 1))
            ax_v = nrm.cross(up).normalized()
            ax_u = ax_v.cross(nrm).normalized()
            rot = math.radians(-10)
            for rr, mat, push in ((0.21, self.mat_mark, 0.012), (0.082, self.mat_white, 0.02)):
                verts, faces = [], []
                rings_n, ang_n = 7, 48
                for ri in range(rings_n + 1):
                    for ak in range(ang_n):
                        a_ = 2 * math.pi * ak / ang_n
                        k_ = 0.16
                        rho = rr * (k_ + (1 - k_) * abs(math.cos(2 * (a_ - rot))) ** 3.2) if ri else 0.0
                        rad = rho * (ri / rings_n) if ri else 0.0
                        q = cen + (ax_u * math.cos(a_) + ax_v * math.sin(a_)) * rad
                        h2 = bvh_b.ray_cast(q + nrm * 0.5, -nrm)
                        verts.append((h2[0] + h2[1] * push) if h2[0] is not None else q)
                for ri in range(rings_n):
                    for ak in range(ang_n):
                        a2 = (ak + 1) % ang_n
                        faces.append((ri * ang_n + ak, ri * ang_n + a2, (ri + 1) * ang_n + a2, (ri + 1) * ang_n + ak))
                self.objects.append(add_object("star", verts, faces, None, mat))


# ------------------------------------------------------------------ scene, lights, cameras, render
def setup_scene(quick):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = 12 if quick else 128
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = "OPENIMAGEDENOISE"
    except Exception:
        pass
    sc.render.resolution_x, sc.render.resolution_y = (500, 456) if quick else (1000, 913)
    sc.render.film_transparent = True
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    sc.cycles.max_bounces = 6
    w = bpy.data.worlds.new("w")
    w.use_nodes = True
    bg = w.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.95, 0.97, 1.0, 1)
    bg.inputs[1].default_value = 0.68
    sc.world = w
    return sc


def add_lights(cam, target):
    def area(name, loc, energy, size, color=(1, 1, 1)):
        ld = bpy.data.lights.new(name, "AREA")
        ld.energy, ld.size, ld.color = energy, size, color
        ob = bpy.data.objects.new(name, ld)
        bpy.context.collection.objects.link(ob)
        ob.parent = cam
        ob.location = loc
        tc = ob.constraints.new("TRACK_TO")
        tc.target, tc.track_axis, tc.up_axis = target, "TRACK_NEGATIVE_Z", "UP_Y"
        return ob
    area("key", (-5, 6, 9), 2100, 6, (1.0, 0.96, 0.9))
    area("fill", (8, -2, 3), 1300, 8, (0.95, 0.97, 1.0))
    area("rim", (6, 4, 2), 900, 5, (1.0, 0.92, 1.0))


def make_camera(sc, az_deg, center, ortho=8.0):
    cd = bpy.data.cameras.new("cam")
    cd.type = "ORTHO"
    cd.ortho_scale = ortho
    cam = bpy.data.objects.new("cam", cd)
    bpy.context.collection.objects.link(cam)
    a = math.radians(az_deg)
    R_ = 40.0
    cam.location = center + Vector((math.sin(a) * R_, -math.cos(a) * R_, 0))
    cam.rotation_euler = (math.radians(90), 0, a)
    cd.clip_end = 200
    sc.camera = cam
    return cam


def render_job(P, pose, view, out, quick, traits=None):
    sc = setup_scene(quick)
    sea = Sea3D(P, pose, traits or STYLE)
    center = Vector((0, 0, 3.05))
    tgt = bpy.data.objects.new("target", None)
    bpy.context.collection.objects.link(tgt)
    tgt.location = center
    az = {"side": 0, "front": 90, "back": -90, "three": 40, "threeback": -140}[view]
    cam = make_camera(sc, az, center)
    add_lights(cam, tgt)
    sc.render.filepath = os.path.join(out, f"{pose}-{view}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", sc.render.filepath)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = argv[0]
    quick = "--quick" in argv
    jobs = [a for a in argv[1:] if ":" in a] or ["idle:side", "idle:front", "idle:back", "idle:three", "swim:side", "sleep:side"]
    for job in jobs:
        pose, view = job.split(":")
        render_job(R.pastel, pose, view, out, quick)
