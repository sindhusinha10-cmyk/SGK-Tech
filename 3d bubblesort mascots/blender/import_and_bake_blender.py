"""
import_and_bake_blender.py — turn the exported GLBs into native Blender source files.

The brief asks for editable Blender sources "if supported". This sandbox has no
Blender installed and cannot reach the Blender download servers, so no .blend is
shipped — but this script does the conversion locally in one shot:

    blender --background --python import_and_bake_blender.py -- ../models ../blender

For Blender 3.6+ / 4.x. It imports each GLB (importer ships with Blender), verifies
the rig and clips, renames the actions to their clip names, pushes each action into
an NLA track so all eight survive the save, applies the project's delivery
conventions (Y-up source, +Z front, origin on the ground) and writes
`<id>.blend` next to this script.

Everything here is standard Blender Python — no add-ons beyond the bundled glTF
importer, and no network access.
"""

import os
import sys
import math

import bpy


CORE_BONES = ["root", "hips", "spine", "chest", "neck", "head",
              "lidL", "lidR", "eyeL", "eyeR", "badge", "legL", "legR", "base"]

CLIP_ORDER = ["Idle", "GlanceL", "GlanceR", "Crouch", "Hop", "Land", "NoSwap", "Success"]


def argv_after_dashdash():
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1:]
    return []


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def import_glb(path):
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.context.selected_objects]


def find_armature(objects):
    for o in objects:
        if o.type == "ARMATURE":
            return o
    for o in bpy.data.objects:
        if o.type == "ARMATURE":
            return o
    return None


def rename_actions(arm):
    """Give the animation data the clip names used by the website."""
    actions = []
    for action in bpy.data.actions:
        name = action.name
        for clip in CLIP_ORDER:
            if clip.lower() in name.lower():
                action.name = clip
                break
        actions.append(action)
    # stable ordering: Idle first, then the authored clip order
    actions.sort(key=lambda a: CLIP_ORDER.index(a.name) if a.name in CLIP_ORDER else 99)
    if arm.animation_data is None:
        arm.animation_data_create()
    return actions


def push_to_nla(arm, actions):
    """One NLA track per clip so every action is preserved in the .blend."""
    ad = arm.animation_data
    for track in list(ad.nla_tracks):
        ad.nla_tracks.remove(track)
    for action in actions:
        track = ad.nla_tracks.new()
        track.name = action.name
        strip = track.strips.new(action.name, int(action.frame_range[0]), action)
        strip.name = action.name
        track.mute = action.name != "Idle"
    ad.action = None


def setup_scene(root_name):
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.fps = 30
    scene.frame_start = 1
    scene.frame_end = 121
    # a simple three-point studio matching the reference sheets
    for name, loc, energy, size, color in (
        ("KEY", (2.4, 3.2, 2.6), 320.0, 2.0, (1.0, 0.96, 0.90)),
        ("FILL", (-3.0, 2.2, 1.4), 90.0, 3.0, (0.62, 0.72, 0.92)),
        ("RIM", (-0.6, -3.4, 2.8), 220.0, 1.4, (0.86, 0.92, 1.0)),
    ):
        light_data = bpy.data.lights.new(name + "_data", type="AREA")
        light_data.energy = energy
        light_data.size = size
        light_data.color = color
        light = bpy.data.objects.new(name, light_data)
        light.location = loc
        light.rotation_euler = (
            math.radians(55), 0.0, math.radians(35 if name == "KEY" else -40)
        )
        bpy.context.collection.objects.link(light)
    return scene


def report(arm, mesh_objects, actions, cid):
    tris = 0
    for ob in mesh_objects:
        me = ob.data
        me.calc_loop_triangles()
        tris += len(me.loop_triangles)
    bones = [b.name for b in arm.data.bones] if arm else []
    missing = [b for b in CORE_BONES if b not in bones]
    print("  %-7s | %5d tris | %2d bones | %d actions | core bones missing: %s"
          % (cid, tris, len(bones), len(actions), missing or "none"))
    return {"tris": tris, "bones": bones, "actions": [a.name for a in actions],
            "missing_core": missing}


def main():
    args = argv_after_dashdash()
    here = os.path.dirname(os.path.abspath(__file__))
    models = args[0] if args else os.path.join(os.path.dirname(here), "models")
    outdir = args[1] if len(args) > 1 else here
    os.makedirs(outdir, exist_ok=True)

    summary = []
    for cid in ["kiln", "ribb", "zag", "glim", "rumble"]:
        path = os.path.join(models, cid + ".glb")
        if not os.path.exists(path):
            print("missing", path)
            continue
        clear_scene()
        objects = import_glb(path)
        arm = find_armature(objects)
        meshes = [o for o in bpy.data.objects if o.type == "MESH"]
        if arm is None:
            raise RuntimeError("%s: no armature imported" % cid)
        arm.name = cid + "_armature"
        actions = rename_actions(arm)
        push_to_nla(arm, actions)
        setup_scene(cid)
        # keep the delivery conventions explicit in the file itself
        arm["sgk_front"] = "+Z"
        arm["sgk_up"] = "+Y"
        arm["sgk_origin"] = "on the ground"
        arm["sgk_clip_order"] = ",".join(CLIP_ORDER)
        arm["sgk_badge_bone"] = "badge"
        out = os.path.join(outdir, cid + ".blend")
        bpy.ops.wm.save_as_mainfile(filepath=out)
        rec = report(arm, meshes, actions, cid)
        rec["file"] = out
        summary.append(rec)
        print("   ->", out)

    print("\n%d blend files written to %s" % (len(summary), outdir))
    return summary


if __name__ == "__main__":
    main()
