#!/usr/bin/env python3
"""
render_blender_shots.py — render the verification sheets straight out of the .blend files.

    blender --background --python blender/render_blender_shots.py -- models blender/source shots

This is the honest evidence sheet for the deliverable: Cycles renders the *native
Blender scenes* produced by make_blend.py (which themselves came from the shipped
GLBs), so the pictures come from a completely different renderer than the ones in
`shots/` produced by the pipeline's own software renderer.

Writes:

    shots/blender_roster.png     all five, on 1.10 m array slots, with the array value
                                 drawn as live text projected onto each `badge` bone
                                 (demonstrating the runtime label workflow)
    shots/blender_views_<id>.png front / side / back, orthographic, per character
    shots/blender_poses_<id>.png the five required performance beats, per character

Numbers are drawn *after* rendering, in screen space, from the projected badge
position — nothing numeric is ever baked into a model or a texture.
"""

import math
import os
import sys
import tempfile

import bpy
from bpy_extras.object_utils import world_to_camera_view
from PIL import Image, ImageDraw, ImageFont

FONT_DIR = "/usr/share/fonts/truetype/dejavu/"

IDS = ["gaja", "mayur", "diya", "patra", "kumbha"]

# the array values used in the roster picture, and the poses in the performance sheet
VALUES = {"gaja": 8, "mayur": 3, "diya": 1, "patra": 5, "kumbha": 9}
POSES = [("Idle", 0.0, "1 · IDLE"), ("GlanceR", 0.45, "2 · GLANCE RIGHT"),
         ("Hop", 0.36, "3 · HOP APEX"), ("Land", 0.18, "4 · LAND"),
         ("Success", 0.62, "5 · SUCCESS")]

VIEW_W, VIEW_H = 460, 600
POS_W, POS_H = 420, 560
ROSTER_W, ROSTER_H = 1600, 620
SAMPLES = 24


def font(size, bold=False):
    try:
        return ImageFont.truetype(
            FONT_DIR + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), size)
    except Exception:
        return ImageFont.load_default()


def argv_after_dashdash():
    if "--" in sys.argv:
        return sys.argv[sys.argv.index("--") + 1:]
    return []


def use_cycles(w, h, samples=SAMPLES, transparent=False):
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    sc.cycles.samples = samples
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 6
    sc.cycles.transparent_max_bounces = 8
    sc.render.resolution_x = w
    sc.render.resolution_y = h
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = transparent
    sc.render.image_settings.file_format = "PNG"
    sc.view_settings.view_transform = "Filmic" if "Filmic" in \
        [v.name for v in sc.view_settings.bl_rna.properties["view_transform"].enum_items] else "Standard"
    sc.view_settings.view_transform = "Standard"
    sc.view_settings.look = "None"
    return sc


def render_to(path):
    bpy.context.scene.render.filepath = path
    bpy.ops.render.render(write_still=True)
    return path


def aim(obj, at):
    dx, dy, dz = at[0] - obj.location[0], at[1] - obj.location[1], at[2] - obj.location[2]
    obj.rotation_euler = (math.atan2(math.hypot(dx, dy), -dz), 0.0, math.atan2(-dx, dy))


def make_camera(name, loc, at, ortho=None, lens=50.0):
    data = bpy.data.cameras.new(name + "_data")
    if ortho is not None:
        data.type = "ORTHO"
        data.ortho_scale = ortho
    else:
        data.lens = lens
    cam = bpy.data.objects.new(name, data)
    cam.location = loc
    aim(cam, at)
    bpy.context.collection.objects.link(cam)
    return cam


def mesh_bounds(arm):
    """World bounds of the skinned mesh, in the rest pose."""
    xs, ys, zs = [], [], []
    for ob in bpy.data.objects:
        if ob.type != "MESH" or ob.parent is not arm:
            continue
        for v in ob.data.vertices:
            co = ob.matrix_world @ v.co
            xs.append(co.x)
            ys.append(co.y)
            zs.append(co.z)
    return (min(xs), min(ys), min(zs)), (max(xs), max(ys), max(zs))


def armature_of():
    for ob in bpy.data.objects:
        if ob.type == "ARMATURE":
            return ob
    return None


def mute_all_tracks(arm):
    if arm.animation_data is None:
        arm.animation_data_create()
    for t in arm.animation_data.nla_tracks:
        t.mute = True


def set_pose(arm, clip, frame):
    """Put one clip on the armature and evaluate it at one frame."""
    mute_all_tracks(arm)
    act = bpy.data.actions.get(clip)
    if act is None:
        raise RuntimeError("no action named %r" % clip)
    arm.animation_data.action = act
    bpy.context.scene.frame_set(int(round(frame)))
    return act


def project(scene, cam, world_co):
    co = world_to_camera_view(scene, cam, world_co)
    w = scene.render.resolution_x
    h = scene.render.resolution_y
    return co.x * w, (1.0 - co.y) * h, co.z


def badge_screen_pos(scene, cam, arm, bone="badge"):
    pb = arm.pose.bones.get(bone)
    if pb is None:
        return None
    return project(scene, cam, arm.matrix_world @ pb.head)


def compose(paths, labels, out, title=None, cols=None, paper=(24, 26, 31),
            pad=8, title_h=44, sub=None):
    cols = cols or len(paths)
    rows = int(math.ceil(len(paths) / float(cols)))
    tiles = [Image.open(p).convert("RGB") for p in paths]
    tw, th = tiles[0].size
    W = cols * tw + pad * (cols + 1)
    H = rows * th + pad * (rows + 1) + title_h
    sheet = Image.new("RGB", (W, H), paper)
    d = ImageDraw.Draw(sheet)
    if title:
        d.text((pad + 6, 12), title, font=font(24, True), fill=(238, 233, 225))
    if sub:
        d.text((W - pad - 6, 20), sub, font=font(16), fill=(150, 155, 168), anchor="ra")
    for i, img in enumerate(tiles):
        r, c = divmod(i, cols)
        x = pad + c * (tw + pad)
        y = title_h + pad + r * (th + pad)
        sheet.paste(img, (x, y))
        if labels and i < len(labels) and labels[i]:
            d.rectangle([x + 6, y + 6, x + 6 + 11 * len(labels[i]) + 16, y + 34],
                        fill=(18, 19, 23))
            d.text((x + 14, y + 13), labels[i], font=font(15, True), fill=(235, 228, 215))
    sheet.save(out)
    return out


# ------------------------------------------------------------------ the sheets
def shot_roster(source, outdir, tmp, values):
    """All five together, with live-projected numbers on the badge bones."""
    bpy.ops.wm.open_mainfile(filepath=os.path.join(source, "bubblesort_squad_roster.blend"))
    scene = use_cycles(ROSTER_W, ROSTER_H, samples=32)
    # orthographic, wide enough for all five 1.10 m slots: 4 * 1.10 = 4.4 m of array
    cam = make_camera("CAM_roster", (0.0, -9.0, 1.46), (0.0, 0.0, 0.58), ortho=5.40)
    scene.camera = cam
    path = render_to(os.path.join(tmp, "blender_roster_raw.png"))

    img = Image.open(path).convert("RGB")
    d = ImageDraw.Draw(img)
    W, H = img.size
    for arm in [o for o in bpy.data.objects if o.type == "ARMATURE"]:
        key = arm.name.replace("_armature", "")
        hit = badge_screen_pos(scene, cam, arm)
        if not hit:
            continue
        x, y, depth = hit
        if depth <= 0 or not (0 <= x <= W and 0 <= y <= H):
            continue
        # the value is drawn as live screen-space text on the blank badge plate:
        # exactly what the runtime does, and nothing is baked into the model.
        d.text((x, y), str(values.get(key, 0)), font=font(38, True),
               fill=(46, 38, 30), anchor="mm", stroke_width=2,
               stroke_fill=(252, 249, 243))
    final = os.path.join(outdir, "blender_roster.png")
    img.save(final)
    return final


def shot_views(source, outdir, tmp, cid):
    """Front / side / back, orthographic, rendered by Cycles in Blender."""
    bpy.ops.wm.open_mainfile(filepath=os.path.join(source, cid + ".blend"))
    arm = armature_of()
    scene = use_cycles(VIEW_W, VIEW_H)
    bmin, bmax = mesh_bounds(arm)
    cxm = (bmin[0] + bmax[0]) / 2.0
    czm = (bmin[2] + bmax[2]) / 2.0
    span = max(bmax[0] - bmin[0], bmax[2] - bmin[2], bmax[1] - bmin[1]) * 1.28
    at = (cxm, 0.0, czm)
    d = 6.0
    cams = [
        ("front", (cxm, -d, czm)),
        ("side", (cxm + d, 0.0, czm)),
        ("back", (cxm, d, czm)),
    ]
    paths, labels = [], []
    for name, loc in cams:
        cam = make_camera("CAM_" + name, loc, at, ortho=span)
        scene.camera = cam
        p = render_to(os.path.join(tmp, "%s_%s.png" % (cid, name)))
        paths.append(p)
        labels.append(name.upper())
    return compose(paths, labels, os.path.join(outdir, "blender_views_%s.png" % cid),
                   title="%s — orthographic views (Blender / Cycles)" % cid.upper(),
                   sub="rendered from blender/source/%s.blend" % cid)


def shot_poses(source, outdir, tmp, cid):
    """The five performance beats, rendered from the native Blender actions."""
    bpy.ops.wm.open_mainfile(filepath=os.path.join(source, cid + ".blend"))
    arm = armature_of()
    scene = use_cycles(POS_W, POS_H, samples=20)
    bmin, bmax = mesh_bounds(arm)
    cxm = (bmin[0] + bmax[0]) / 2.0
    czm = (bmin[2] + bmax[2]) / 2.0
    span = max(bmax[0] - bmin[0], bmax[2] - bmin[2], bmax[1] - bmin[1]) * 1.45
    # a slightly raised three-quarter view reads the pose better than a dead-on one
    cam = make_camera("CAM_pose", (1.3, -5.2, czm + 0.62), (cxm, 0.0, czm + 0.05),
                      ortho=span)
    scene.camera = cam
    paths, labels = [], []
    for clip, t, label in POSES:
        set_pose(arm, clip, t * bpy.context.scene.render.fps)
        paths.append(render_to(os.path.join(tmp, "%s_%s.png" % (cid, clip))))
        labels.append(label)
    return compose(paths, labels, os.path.join(outdir, "blender_poses_%s.png" % cid),
                   title="%s — performance beats (Blender / Cycles)" % cid.upper(),
                   sub="Idle · Glance · Hop · Land · Success")


def main():
    args = argv_after_dashdash()
    here = os.path.dirname(os.path.abspath(__file__))
    root = os.path.dirname(here)
    source = args[1] if len(args) > 1 else os.path.join(here, "source")
    outdir = args[2] if len(args) > 2 else os.path.join(root, "shots")
    os.makedirs(outdir, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="sgk_blender_shots_")

    print("Blender %s" % bpy.app.version_string)
    print("source %s" % source)
    print("out    %s\n" % outdir)

    only = args[3] if len(args) > 3 else None

    made = []
    if only in (None, "roster"):
        made.append(shot_roster(source, outdir, tmp, VALUES))
        print("  roster  -> %s" % os.path.basename(made[-1]))
    if only in (None, "views", "poses", "all") or only in IDS:
        for cid in ([only] if only in IDS else IDS):
            made.append(shot_views(source, outdir, tmp, cid))
            print("  views   -> %s" % os.path.basename(made[-1]))
            made.append(shot_poses(source, outdir, tmp, cid))
            print("  poses   -> %s" % os.path.basename(made[-1]))
    print("\n%d sheets written" % len(made))
    return made


if __name__ == "__main__":
    main()
