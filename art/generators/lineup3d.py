"""All creatures in one Blender scene, side by side, under the same light and on the same ground, at their built sizes.

Usage: blender -b -P lineup3d.py -- OUTDIR [--quick] [three|side|front ...]
"""
import bpy, math, os, sys
from mathutils import Vector, Matrix

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import seahorse3d as K
import seahorse as R
import unicorn3d as U
import fox3d as F

GAP = 6.4                                                  # distance between the creatures, across the picture


def build(fn, offset):
    """build one creature at the origin, then slide everything it made to its place in the line"""
    before = set(bpy.data.objects)
    fn()
    T = Matrix.Translation(offset)
    for ob in set(bpy.data.objects) - before:
        if ob.name.startswith("ground"):
            bpy.data.objects.remove(ob)
            continue
        ob.matrix_world = T @ ob.matrix_world


def render(view, out, quick):
    sc = K.setup_scene(quick)
    az = {"side": 0, "three": 30, "front": 90}[view]
    a = math.radians(az)
    across = Vector((math.cos(a), math.sin(a), 0))         # screen right for this camera
    build(lambda: K.Sea3D(R.pastel, "idle", K.STYLE), across * -GAP + Vector((0.4, 0, 0.35)))
    build(lambda: U.Uni3D(U.BLOOM, "stand", U.TRAITS), Vector((0, 0, 0)))
    build(lambda: F.Fox3D(F.EMBER, "sit", {}), across * (GAP * 1.12) + Vector((0.3, 0, 0)))
    me = bpy.data.meshes.new("ground")
    me.from_pydata([(-40, -40, U.GROUND_Z), (40, -40, U.GROUND_Z), (40, 40, U.GROUND_Z), (-40, 40, U.GROUND_Z)], [], [(0, 1, 2, 3)])
    g = bpy.data.objects.new("ground", me)
    bpy.context.collection.objects.link(g)
    g.is_shadow_catcher = True
    sc.render.resolution_x, sc.render.resolution_y = (1200, 500) if quick else (2400, 1000)
    center = Vector((0, 0, 3.05))
    tgt = bpy.data.objects.new("target", None)
    bpy.context.collection.objects.link(tgt)
    tgt.location = center
    cam = K.make_camera(sc, az, center, ortho=GAP * 3.35)
    pitch = math.radians(8)
    cam.location = center + Vector((math.sin(a) * math.cos(pitch), -math.cos(a) * math.cos(pitch), math.sin(pitch))) * 60.0
    cam.rotation_euler = (math.radians(90) - pitch, 0, a)
    cam.data.clip_end = 300
    K.add_lights(cam, tgt)
    for nm, energy, size, color, loc in (("top", 700, 24.0, (1, 1, 1), (0.5, 0.3, 12.0)), ("bounce", 800, 30.0, (1.0, 0.95, 0.95), (1.0, -10.0, 0.9))):
        ld = bpy.data.lights.new(nm, "AREA")
        ld.energy, ld.size, ld.color = energy, size, color
        ob = bpy.data.objects.new(nm, ld)
        bpy.context.collection.objects.link(ob)
        ob.location = loc
        c = ob.constraints.new("TRACK_TO")
        c.target, c.track_axis, c.up_axis = tgt, "TRACK_NEGATIVE_Z", "UP_Y"
    sc.view_settings.exposure = -0.28
    sc.render.filepath = os.path.join(out, f"lineup-{view}.png")
    bpy.ops.render.render(write_still=True)
    print("rendered", sc.render.filepath)


if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out = argv[0]
    quick = "--quick" in argv
    views = [a for a in argv[1:] if not a.startswith("--")] or ["three", "side"]
    for v in views:
        render(v, out, quick)
