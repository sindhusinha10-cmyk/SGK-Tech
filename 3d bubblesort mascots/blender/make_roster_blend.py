import os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)
MODELS = os.path.join(REPO, "models")
SOURCE = os.path.join(HERE, "source")
os.makedirs(SOURCE, exist_ok=True)

import bpy

# Setup clean scene
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.fps = 30
scene.render.fps_base = 1.0

# Lighting
bpy.ops.object.light_add(type='SUN', location=(5, -5, 10))
sun = bpy.context.active_object
sun.data.energy = 3.5

bpy.ops.object.light_add(type='POINT', location=(-4, -3, 3))
fill = bpy.context.active_object
fill.data.energy = 150

# Camera
bpy.ops.object.camera_add(location=(0, -8.5, 2.2), rotation=(1.45, 0, 0))
bpy.context.scene.camera = bpy.context.active_object

# Order of 8 characters
order = ["gaja", "diya", "kumbha", "grantha", "dhanesh", "salya", "mayur", "patra"]
spacing = 1.25
start_x = -((len(order) - 1) * spacing) / 2.0

for i, name in enumerate(order):
    glb_path = os.path.join(MODELS, f"{name}.glb")
    if not os.path.exists(glb_path):
        continue
    # Import
    bpy.ops.import_scene.gltf(filepath=glb_path)
    # The imported objects are selected
    imported = list(bpy.context.selected_objects)
    # Find root armature / root object
    root = None
    for obj in imported:
        if obj.parent is None:
            root = obj
            break
    if root:
        root.location.x = start_x + i * spacing
        root.name = f"Mascot_{name.capitalize()}"

# Save roster.blend
out_path = os.path.join(SOURCE, "roster.blend")
bpy.ops.wm.save_as_mainfile(filepath=out_path)
print(f"Saved roster scene: {out_path} ({os.path.getsize(out_path)/1024:.1f} KB)")

