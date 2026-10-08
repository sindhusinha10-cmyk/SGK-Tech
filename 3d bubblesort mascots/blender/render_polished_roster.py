import os, sys, math
import bpy

roster_blend = "3d bubblesort mascots/blender/source/roster.blend"
bpy.ops.wm.open_mainfile(filepath=roster_blend)
scene = bpy.context.scene

# Configure Cycles CPU rendering
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'
scene.cycles.samples = 28
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080

# Framing Camera: 35mm lens, positioned back to frame all 8 characters cleanly
cam = scene.camera
if not cam:
    bpy.ops.object.camera_add()
    cam = bpy.context.active_object
    scene.camera = cam

cam.location = (0.0, -11.2, 2.7)
cam.rotation_euler = (math.radians(78), 0, 0)
cam.data.lens = 35

# Clear existing lights to build a clean studio setup
for o in list(scene.objects):
    if o.type == 'LIGHT' or o.name.startswith("Plane") or o.name.startswith("Cyc"):
        bpy.data.objects.remove(o, do_unlink=True)

# Build a smooth studio Cyclorama backdrop (infinity sweep floor and curved back wall)
mesh = bpy.data.meshes.new("CycBackdrop")
obj = bpy.data.objects.new("CycBackdrop", mesh)
scene.collection.objects.link(obj)

verts = [
    (-15.0, -6.0, 0.0),
    ( 15.0, -6.0, 0.0),
    (-15.0,  3.0, 0.0),
    ( 15.0,  3.0, 0.0),
    (-15.0,  5.0, 0.8),
    ( 15.0,  5.0, 0.8),
    (-15.0,  6.0, 2.4),
    ( 15.0,  6.0, 2.4),
    (-15.0,  6.5, 8.0),
    ( 15.0,  6.5, 8.0),
]
faces = [
    (0, 1, 3, 2),
    (2, 3, 5, 4),
    (4, 5, 7, 6),
    (6, 7, 9, 8),
]
mesh.from_pydata(verts, [], faces)
mesh.update()

# Add Subdivision Surface and Shade Smooth for flawless cyc curve
mod = obj.modifiers.new("Subsurf", 'SUBSURF')
mod.levels = 2
mod.render_levels = 2
for p in mesh.polygons:
    p.use_smooth = True

cyc_mat = bpy.data.materials.new(name="CycStudioMat")
cyc_mat.use_nodes = True
bsdf = cyc_mat.node_tree.nodes.get("Principled BSDF")
if bsdf:
    bsdf.inputs['Base Color'].default_value = (0.052, 0.058, 0.075, 1.0)
    bsdf.inputs['Roughness'].default_value = 0.55
obj.data.materials.append(cyc_mat)

# Studio 3-Point Lighting Setup:
# 1. Broad Soft Key Area Light
bpy.ops.object.light_add(type='AREA', location=(4.0, -5.5, 6.5))
key = bpy.context.active_object
key.data.energy = 850
key.data.size = 3.5
key.data.color = (1.0, 0.96, 0.91)
key.rotation_euler = (math.radians(45), math.radians(15), math.radians(-25))

# 2. Gentle Cool Fill Area Light
bpy.ops.object.light_add(type='AREA', location=(-5.0, -5.0, 4.5))
fill = bpy.context.active_object
fill.data.energy = 450
fill.data.size = 4.0
fill.data.color = (0.75, 0.85, 1.0)
fill.rotation_euler = (math.radians(50), math.radians(-15), math.radians(30))

# 3. High-Contrast Rim / Kicker (crucial for Dhanesh and dark silhouettes)
bpy.ops.object.light_add(type='AREA', location=(0.0, 4.0, 5.0))
rim = bpy.context.active_object
rim.data.energy = 700
rim.data.size = 6.0
rim.data.color = (0.88, 0.94, 1.0)
rim.rotation_euler = (math.radians(-50), 0, 0)

out_path = "3d bubblesort mascots/shots/roster_sheet.png"
scene.render.filepath = os.path.abspath(out_path)
scene.render.image_settings.file_format = 'PNG'

print(f"Rendering updated studio roster to {out_path}...")
bpy.ops.render.render(write_still=True)
print(f"Render complete: {out_path} ({os.path.getsize(out_path)/1024:.1f} KB)")
