# -*- coding: utf-8 -*-
"""Blender side of the Hexa tag render. Started by tools/hexarender.py.

    blender --background --python tools/hexarender_blender.py --
            --mesh <dir with STL files>
            --parts ring,core[,chain]
            --ut <output PNG>
            [--az -45] [--el 25] [--ljus 1.4] [--px 2400]
"""
import math
import os
import sys

import bpy
from mathutils import Vector

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def flagga(namn, standard):
    return argv[argv.index(namn) + 1] if namn in argv else standard


MESH    = flagga("--mesh", "")
UT      = flagga("--ut", "")
PARTS   = flagga("--parts", "ring,core")
if not MESH or not UT:
    raise SystemExit("--mesh and --ut required. Run tools/hexarender.py.")

AZ      = float(flagga("--az", -45))
EL      = float(flagga("--el", 25))
PX      = int(flagga("--px", 1600))
SAMPLES = int(flagga("--samples", 96))
LINS    = float(flagga("--lins", 85))
LJUS    = float(flagga("--ljus", 1.0))

# tag.py: _COLOR_METAL = Color(0.72, 0.72, 0.76), _COLOR_CHAIN = Color(0.65, 0.65, 0.67)
MATERIAL = {
    "ring":  ((0.72, 0.72, 0.76, 1), 0.15, 0.85),
    "core":  ((0.72, 0.72, 0.76, 1), 0.15, 0.85),
    "chain": ((0.65, 0.65, 0.67, 1), 0.20, 0.90),
}

# ---------------------------------------------------------------- scene
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene

part_names = [p.strip() for p in PARTS.split(",") if p.strip()]
importerade = []

for namn in part_names:
    fil = os.path.join(MESH, namn + ".stl")
    if not os.path.exists(fil):
        print("missing:", fil)
        continue
    fore = set(bpy.data.objects)
    try:
        bpy.ops.wm.stl_import(filepath=fil)
    except AttributeError:
        bpy.ops.import_mesh.stl(filepath=fil)
    nya = [o for o in bpy.data.objects if o not in fore]

    mat = bpy.data.materials.new(namn)
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    farg, rough, metal = MATERIAL.get(namn, ((0.72, 0.72, 0.76, 1), 0.15, 0.85))
    b.inputs["Base Color"].default_value = farg
    b.inputs["Roughness"].default_value = rough
    b.inputs["Metallic"].default_value = metal
    for o in nya:
        o.data.materials.clear()
        o.data.materials.append(mat)
        o.select_set(True)
        bpy.context.view_layer.objects.active = o
        # STL is flat triangles; auto-smooth makes cylinders round but keeps hard edges.
        try:
            bpy.ops.object.shade_auto_smooth(angle=math.radians(30))
        except AttributeError:
            bpy.ops.object.shade_smooth(use_auto_smooth=True,
                                        auto_smooth_angle=math.radians(30))
        o.select_set(False)
    importerade += nya
    print("  %-8s %d objects" % (namn, len(nya)))

if not importerade:
    raise SystemExit("no meshes to render")

# ---------------------------------------------------------- bbox + scale
lo = Vector((1e18, 1e18, 1e18))
hi = Vector((-1e18, -1e18, -1e18))
for o in importerade:
    for h in o.bound_box:
        v = o.matrix_world @ Vector(h)
        lo = Vector(map(min, lo, v))
        hi = Vector(map(max, hi, v))
print("  size %.0f x %.0f x %.0f mm" % (hi.x - lo.x, hi.y - lo.y, hi.z - lo.z))

# Scale to 2 Blender units so lights are at sensible distances.
k = 2.0 / (hi - lo).length
for o in importerade:
    o.scale = (k, k, k)
bpy.context.view_layer.update()
lo = Vector((1e18, 1e18, 1e18))
hi = Vector((-1e18, -1e18, -1e18))
for o in importerade:
    for h in o.bound_box:
        v = o.matrix_world @ Vector(h)
        lo = Vector(map(min, lo, v))
        hi = Vector(map(max, hi, v))
mitt = (lo + hi) / 2
diag = (hi - lo).length

# ------------------------------------------------------------ lighting
def lampa(namn, riktning, energi, storlek):
    d = bpy.data.lights.new(namn, type="AREA")
    d.energy = energi
    d.size = storlek
    o = bpy.data.objects.new(namn, d)
    sc.collection.objects.link(o)
    o.location = mitt + Vector(riktning).normalized() * diag * 2.0
    o.rotation_mode = "QUATERNION"
    o.rotation_quaternion = (mitt - o.location).to_track_quat("-Z", "Y")
    return o


# Key from upper-left, fill from right, rim from behind.
lampa("key",  (-0.55, -0.75, 1.15), 95 * LJUS, diag * 1.6)
lampa("fill", (1.00, -0.45, 0.35),  34 * LJUS, diag * 2.2)
lampa("rim",  (0.35, 1.00, 0.55),   55 * LJUS, diag * 1.2)

varld = bpy.data.worlds.new("world")
sc.world = varld
varld.use_nodes = True
varld.node_tree.nodes["Background"].inputs[0].default_value = (1, 1, 1, 1)
varld.node_tree.nodes["Background"].inputs[1].default_value = 0.30 * LJUS

# ------------------------------------------------------------- camera
kd = bpy.data.cameras.new("camera")
kd.lens = LINS
kam = bpy.data.objects.new("camera", kd)
sc.collection.objects.link(kam)
sc.camera = kam

ra = math.radians(AZ)
re = math.radians(EL)
rikt = Vector((math.cos(re) * math.cos(ra),
               math.cos(re) * math.sin(ra),
               math.sin(re)))

sc.render.resolution_x = PX
sc.render.resolution_y = PX
sc.render.resolution_percentage = 100


def passa():
    """Move camera until the whole tag fits inside the frame with margin."""
    from bpy_extras.object_utils import world_to_camera_view
    mal = 0.455                            # 9 % air around the subject
    avst = diag * 2.2
    kd.ortho_scale = diag * 1.1
    kam.location = mitt + rikt * avst
    kam.rotation_mode = "QUATERNION"
    kam.rotation_quaternion = (mitt - kam.location).to_track_quat("-Z", "Y")
    for _ in range(14):
        bpy.context.view_layer.update()
        varst = 0.0
        for i in range(8):
            h = Vector((lo.x if i & 1 else hi.x,
                        lo.y if i & 2 else hi.y,
                        lo.z if i & 4 else hi.z))
            p = world_to_camera_view(sc, kam, h)
            varst = max(varst, abs(p.x - 0.5), abs(p.y - 0.5))
        if abs(varst - mal) < 0.004:
            break
        avst *= varst / mal
        kam.location = mitt + rikt * avst
    return avst


passa()

# ------------------------------------------------------------ render
sc.render.engine = "CYCLES"
sc.cycles.device = "CPU"
sc.cycles.samples = SAMPLES
sc.cycles.use_denoising = True
sc.cycles.use_adaptive_sampling = True
sc.render.film_transparent = True
sc.render.image_settings.file_format = "PNG"
sc.render.image_settings.color_mode = "RGBA"
sc.render.filepath = os.path.abspath(UT)
sc.view_settings.view_transform = "Standard"      # no filmic tone curve

print("rendering %s  az=%g el=%g %dpx" % (sc.render.filepath, AZ, EL, PX))
bpy.ops.render.render(write_still=True)
print("done")
