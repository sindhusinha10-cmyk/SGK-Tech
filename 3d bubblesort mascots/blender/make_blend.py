#!/usr/bin/env python3
"""
make_blend.py — build the native Blender source files from the shipped GLBs.

    blender --background --python blender/make_blend.py -- models blender/source
    python3 blender/make_blend.py            # also works via the `bpy` PyPI module

Writes, per character:

    <out>/<id>.blend      skinned mesh + armature + all eight clips as actions on
                          NLA tracks + studio lights + a README text datablock
    <out>/bubblesort_squad_roster.blend
                          all five on 1.10 m array slots, ready to animate by hand

and one machine-readable report:

    specs/blender_verification.json

That report is a *second, independent* verification of the GLBs: it is produced by
Blender's own glTF importer, not by the pipeline that wrote the files, so it is
evidence rather than a restatement.

Axis note: glTF is Y-up with the characters facing +Z. Blender is Z-up and its glTF
importer maps glTF (x, y, z) -> Blender (x, -z, y). So inside these .blend files each
character stands on Z = 0 and **faces -Y**, which is exactly Blender's front view.
Re-export with `+Y Up` enabled and the round trip is lossless — do not rotate the
objects by hand.
"""

import json
import math
import os
import sys

import bpy

CORE_BONES = ["root", "hips", "spine", "chest", "neck", "head",
              "lidL", "lidR", "eyeL", "eyeR", "badge", "legL", "legR", "base"]

CLIP_ORDER = ["Idle", "GlanceL", "GlanceR", "Crouch", "Hop", "Land", "NoSwap", "Success"]

IDS = ["gaja", "mayur", "diya", "patra", "kumbha"]

SLOT_PITCH = 1.10          # metres between array slots, matches index.html and the sheets
FPS = 30

BLEND_README = """BUBBLE-SORT SQUAD - {cid} - Blender source
==========================================================

Built by blender/make_blend.py from models/{cid}.glb.
Do not edit this text datablock; edit blender/make_blend.py.

CONVENTIONS
  * Units .......... metres, unit scale 1.0, {fps} fps
  * Standing on .... Z = 0 (origin is on the ground, centred on the array slot)
  * Facing ......... -Y  (Blender front view; this is +Z in glTF space)
  * Scale .......... one shared scale for all five characters, sizes vary by design
  * Re-export ...... File > Export > glTF 2.0, +Y Up ON, Skinning ON

RIG
  * Armature ....... {arm}
  * Bones .......... {nbones}
  * Core bones ..... {core} (identical names in every character)
  * Extras ......... {extras}
  * `badge` is a MOUNT POINT, not a deform bone: it is deliberately unweighted so a
    runtime number label can be parented to it without ever deforming.

ANIMATION
  * Every clip is a real action (fake user set) AND an NLA track, one track per clip.
    Tracks are muted except Idle so the file opens on an idle pose.
  * All clips are IN PLACE: the root bone never translates horizontally. The website
    owns left/right travel and tweens the slot position during a swap.
  * hop apex clearance is authored so the feet never pass through Z = 0.

CLIPS   {clips}

NUMBER DISPLAY
  Put the array value on the blank badge plate, or parent a label object to the
  `badge` bone. See specs/badge_label.md.
"""


def argv_after_dashdash():
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1:]
    return []


def clear_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    for ob in list(bpy.data.objects):
        bpy.data.objects.remove(ob, do_unlink=True)


def import_glb(path):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    return [o for o in bpy.data.objects if o not in before]


def find(objs, kind):
    for o in objs:
        if o.type == kind:
            return o
    return None


def rename_actions(arm):
    """Give every imported action its clean clip name and make it survive the save."""
    named = {}
    for action in bpy.data.actions:
        for clip in CLIP_ORDER:
            if clip.lower() in action.name.lower():
                action.name = clip
                action.use_fake_user = True
                named[clip] = action
                break
    return [named[c] for c in CLIP_ORDER if c in named]


def push_to_nla(arm, actions):
    """One muted NLA track per clip; Idle left live so the file opens idle."""
    if arm.animation_data is None:
        arm.animation_data_create()
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
    return ad


def setup_scene():
    scene = bpy.context.scene
    scene.unit_settings.system = "METRIC"
    scene.unit_settings.scale_length = 1.0
    scene.render.fps = FPS
    scene.frame_start = 1
    scene.frame_end = 1 + int(4.0 * FPS)      # the Idle loop, 4.0 s
    scene.render.film_transparent = False
    return scene


def aim(obj, look_at):
    """Point an object's local -Z at `look_at` (camera/light convention)."""
    dx = look_at[0] - obj.location[0]
    dy = look_at[1] - obj.location[1]
    dz = look_at[2] - obj.location[2]
    obj.rotation_euler = (math.atan2(math.hypot(dx, dy), -dz), 0.0, math.atan2(-dx, dy))
    return obj


def add_studio_lights(aim_at=(0.0, 0.0, 0.62)):
    """A simple three-point rig, matching the reference sheets."""
    made = []
    for name, loc, energy, size, color in (
        ("KEY", (2.4, 3.2, 2.6), 260.0, 2.0, (1.0, 0.96, 0.90)),
        ("FILL", (-3.0, 2.2, 1.4), 80.0, 3.0, (0.62, 0.72, 0.92)),
        ("RIM", (-0.6, -3.4, 2.8), 170.0, 1.4, (0.86, 0.92, 1.0)),
    ):
        data = bpy.data.lights.new(name + "_data", type="AREA")
        data.energy = energy
        data.size = size
        data.color = color
        light = bpy.data.objects.new(name, data)
        light.location = loc
        aim(light, aim_at)
        bpy.context.collection.objects.link(light)
        made.append(light)
    return made


def add_ground(size=14.0):
    """A neutral matte floor with a subtle contact shadow."""
    me = bpy.data.meshes.new("GROUND_mesh")
    h = size / 2.0
    me.from_pydata([(-h, -h, 0.0), (h, -h, 0.0), (h, h, 0.0), (-h, h, 0.0)],
                   [], [(0, 1, 2, 3)])
    me.update()
    ob = bpy.data.objects.new("GROUND", me)
    mat = bpy.data.materials.new("sgk_ground")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = (0.20, 0.22, 0.27, 1.0)
        bsdf.inputs["Roughness"].default_value = 0.9
    ob.data.materials.append(mat)
    bpy.context.collection.objects.link(ob)
    return ob


def add_camera(loc=(0.0, -4.2, 1.5), look_at=(0.0, 0.0, 0.75)):
    data = bpy.data.cameras.new("CAM_data")
    data.lens = 50.0
    cam = bpy.data.objects.new("CAM", data)
    cam.location = loc
    dx, dy, dz = (look_at[0] - loc[0], look_at[1] - loc[1], look_at[2] - loc[2])
    # Blender cameras look down local -Z. With euler order XYZ:
    #   view dir = Rz(phi) . Rx(theta) . (0,0,-1) = (-sin phi, cos phi, -cos theta)
    # so the tilt is atan2(horizontal distance, -dz) and the heading is atan2(-dx, dy).
    cam.rotation_euler = (math.atan2(math.hypot(dx, dy), -dz), 0.0, math.atan2(-dx, dy))
    bpy.context.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    return cam


def world_grey():
    world = bpy.data.worlds.new("sgk_world")
    world.use_nodes = True
    bg = world.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.46, 0.52, 0.62, 1.0)
        bg.inputs[1].default_value = 0.22
    bpy.context.scene.world = world
    return world


def mesh_stats(ob):
    """Triangles, world-space bounds and skinning facts for one mesh object."""
    me = ob.data
    me.calc_loop_triangles()
    tris = len(me.loop_triangles)

    mw = ob.matrix_world
    xs, ys, zs = [], [], []
    for v in me.vertices:
        co = mw @ v.co
        xs.append(co.x)
        ys.append(co.y)
        zs.append(co.z)

    influences = [len(v.groups) for v in me.vertices]
    return {
        "triangles": tris,
        "vertices": len(me.vertices),
        "materials": [m.name for m in me.materials],
        "vertex_groups": len(ob.vertex_groups),
        "max_influences": max(influences) if influences else 0,
        "modifiers": [m.type for m in ob.modifiers],
        "bounds_blender_min": [min(xs), min(ys), min(zs)],
        "bounds_blender_max": [max(xs), max(ys), max(zs)],
        "height_m": max(zs) - min(zs),
        "ground_z": min(zs),
        "front_y": min(ys) if min(ys) < 0 else max(ys),
    }


def verify(cid, objs, arm, actions):
    """Facts read back out of the imported data, for specs/blender_verification.json."""
    mesh = find(objs, "MESH")
    for o in objs:
        if o.type == "MESH" and o.parent is arm:
            mesh = o
            break

    stats = mesh_stats(mesh)

    bones = [b.name for b in arm.data.bones]
    extras = [b for b in bones if b not in CORE_BONES]

    clips = []
    for a in actions:
        start, end = a.frame_range
        clips.append({
            "name": a.name,
            "frame_start": start,
            "frame_end": end,
            "seconds": round((end - start) / FPS, 4),
            "fcurves": len(a.fcurves),
            "fake_user": bool(a.use_fake_user),
            "on_nla": any(t.name == a.name for t in arm.animation_data.nla_tracks),
        })

    badge = arm.data.bones.get("badge")
    badge_head = None
    if badge is not None:
        # Blender (x, y, z) -> glTF (x, z, -y)
        h = badge.head_local
        badge_head = [round(h.x, 4), round(h.z, 4), round(-h.y, 4)]

    return {
        "id": cid,
        "mesh_object": mesh.name,
        "armature": arm.name,
        "bones": bones,
        "bone_count": len(bones),
        "core_bones_missing": [b for b in CORE_BONES if b not in bones],
        "extra_bones": extras,
        "badge_bone": "badge" in bones,
        "badge_anchor_gltf": badge_head,
        "clips": clips,
        "clip_names": [c["name"] for c in clips],
        "clips_missing": [c for c in CLIP_ORDER if c not in [x["name"] for x in clips]],
        "images": [i.name for i in bpy.data.images if i.name != "Render Result"],
        "node_groups": [g.name for g in bpy.data.node_groups],
        **stats,
    }


def save_text(name, body):
    text = bpy.data.texts.new(name)
    text.write(body)


def build_one(cid, models, outdir):
    clear_scene()
    # fps must be 30 *before* the import: the glTF importer converts clip times to
    # frames using the scene fps, so importing at Blender's default 24 would stretch
    # every duration by 30/24.
    setup_scene()
    objs = import_glb(os.path.join(models, cid + ".glb"))
    arm = find(objs, "ARMATURE")
    if arm is None:
        raise RuntimeError("%s: nothing in the file imported as an armature" % cid)
    arm.name = cid + "_armature"
    mesh = None
    for o in objs:
        if o.type == "MESH" and o.parent is arm:
            mesh = o
    if mesh is not None:
        mesh.name = cid + "_mesh"
        mesh.data.name = cid

    actions = rename_actions(arm)
    push_to_nla(arm, actions)
    add_studio_lights()
    add_ground()
    add_camera()
    world_grey()

    bones = [b.name for b in arm.data.bones]
    arm["sgk_id"] = cid
    arm["sgk_up"] = "+Y (glTF); Blender is Z-up - characters stand on Z=0"
    arm["sgk_front"] = "+Z (glTF) / -Y (Blender front view)"
    arm["sgk_origin"] = "on the ground, centred on the array slot"
    arm["sgk_units"] = "metres, unit scale 1.0, %d fps" % FPS
    arm["sgk_clip_order"] = ",".join(CLIP_ORDER)
    arm["sgk_badge_bone"] = "badge"
    arm["sgk_slot_pitch"] = SLOT_PITCH
    arm["sgk_root_motion"] = "in place - the runtime translates the slot"

    save_text("README", BLEND_README.format(
        cid=cid, fps=FPS, arm=arm.name, nbones=len(bones),
        core=", ".join(CORE_BONES),
        extras=", ".join([b for b in bones if b not in CORE_BONES]) or "(none)",
        clips=", ".join(CLIP_ORDER)))

    rec = verify(cid, objs, arm, actions)
    out = os.path.join(outdir, cid + ".blend")
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    rec["file"] = os.path.relpath(out, os.path.dirname(outdir)).replace(os.sep, "/")
    rec["bytes"] = os.path.getsize(out)
    return rec


def build_roster(models, outdir, records):
    """All five on 1.10 m array slots - the file to hand to an animator."""
    clear_scene()
    scene = setup_scene()
    world_grey()   # fps 30 is set here, before any GLB is imported
    add_studio_lights()
    add_ground(size=16.0)

    pitch = SLOT_PITCH
    n = len(IDS)
    for i, cid in enumerate(IDS):
        x = (i - (n - 1) / 2.0) * pitch
        objs = import_glb(os.path.join(models, cid + ".glb"))
        arm = find(objs, "ARMATURE")
        actions = rename_actions(arm)
        push_to_nla(arm, actions)
        for o in objs:
            if o.parent is None:
                o.location.x += x
        # slot marker: a thin pad under each character, matching index.html
        pad = bpy.data.meshes.new("slot_%d_mesh" % i)
        s = pitch * 0.42
        verts = [(-s, -s, 0), (s, -s, 0), (s, s, 0), (-s, s, 0)]
        pad.from_pydata(verts, [], [(0, 1, 2, 3)])
        pad.update()
        padob = bpy.data.objects.new("slot_%d" % i, pad)
        padob.location = (x, 0.0, -0.005)
        bpy.context.collection.objects.link(padob)

    add_camera(loc=(0.0, -4.6, 1.45), look_at=(0.0, 0.0, 0.72))
    scene.frame_end = 121

    out = os.path.join(outdir, "bubblesort_squad_roster.blend")
    bpy.ops.wm.save_as_mainfile(filepath=out, compress=True)
    return {
        "file": os.path.relpath(out, os.path.dirname(outdir)).replace(os.sep, "/"),
        "bytes": os.path.getsize(out),
        "slot_pitch_m": pitch,
        "characters": IDS,
        "arms": sorted([o.name for o in bpy.data.objects if o.type == "ARMATURE"]),
    }


def main():
    args = argv_after_dashdash()
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    models = args[0] if args else os.path.join(root, "models")
    outdir = args[1] if len(args) > 1 else os.path.join(here, "source")
    specs = os.path.join(root, "specs")
    os.makedirs(outdir, exist_ok=True)

    print("Blender %s" % bpy.app.version_string)
    print("models  : %s" % models)
    print("output  : %s\n" % outdir)

    records = []
    for cid in IDS:
        path = os.path.join(models, cid + ".glb")
        if not os.path.exists(path):
            print("  !! missing %s" % path)
            continue
        rec = build_one(cid, models, outdir)
        records.append(rec)
        print("  %-7s %5d tris  %2d bones  %d clips  badge:%s  -> %s"
              % (cid, rec["triangles"], rec["bone_count"], len(rec["clips"]),
                 "yes" if rec["badge_bone"] else "NO", os.path.basename(rec["file"])))

    roster = build_roster(models, outdir, records)

    report = {
        "generator": "blender/make_blend.py",
        "blender_version": bpy.app.version_string,
        "note": ("Independent verification: these numbers are read back by Blender's own "
                 "glTF importer from the shipped GLBs, not by the pipeline that wrote them."),
        "fps": FPS,
        "slot_pitch_m": SLOT_PITCH,
        "axis_convention": {
            "gltf": "Y up, characters face +Z",
            "blender": "Z up, characters stand on Z=0 and face -Y",
            "importer_mapping": "gltf (x, y, z) -> blender (x, -z, y)",
        },
        "models": records,
        "roster": roster,
    }
    os.makedirs(specs, exist_ok=True)
    rpath = os.path.join(specs, "blender_verification.json")
    with open(rpath, "w") as fh:
        json.dump(report, fh, indent=1)
    print("\n  roster  -> %s" % os.path.basename(roster["file"]))
    print("  report  -> %s" % os.path.relpath(rpath, root))
    return report


if __name__ == "__main__":
    main()
