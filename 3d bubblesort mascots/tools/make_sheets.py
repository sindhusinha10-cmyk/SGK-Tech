#!/usr/bin/env python3
"""
make_sheets.py — produce every PNG deliverable from the rigged characters.

    python3 make_sheets.py            # everything
    python3 make_sheets.py roster     # one sheet (roster|views|silhouettes|strip)

Sheets
    shots/roster_sheet.png      all five on array slots, labels drawn like the site
    shots/views_<id>.png        orthographic front / side / back per character
    shots/silhouettes.png       solid-black silhouette test, front + 3/4 rows
    shots/animation_strip.png   idle → glance → hop apex → squash landing per character
"""

import gc
import math
import os
import sys
import time

import numpy as np
from PIL import Image, ImageDraw

import clips
import creatures
import render as R
import rig
import textures

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SHOTS = os.path.join(ROOT, "shots")
IDS = ["kiln", "ribb", "zag", "glim", "rumble"]

_cache = {}


def get(cid):
    if cid not in _cache:
        ch = creatures.BUILDERS[cid]()
        joints, weights = rig.compute_weights(ch.mesh, ch.skel)
        tex = {}
        for m in ch.mats.values():
            k = m.get("texture")
            if k and k not in tex:
                tex[k] = textures.KINDS[k]().astype(np.float32)
        fns = clips.build_clip_fns(ch)
        _cache[cid] = dict(ch=ch, joints=joints, weights=weights, tex=tex, fns=fns)
    return _cache[cid]


def material_table(cid):
    entry = get(cid)
    ch = entry["ch"]
    out = []
    for key in ch.mesh.face_mat:
        m = ch.mats[key]
        out.append({
            "albedo": np.array(m["color"], dtype=np.float32),
            "rough": float(m.get("roughness", 0.5)),
            "metal": float(m.get("metallic", 0.0)),
            "emissive": np.array(m.get("emissive", (0, 0, 0)), dtype=np.float32),
            "alpha": float(m.get("alpha", 1.0)),
            "texture": entry["tex"].get(m.get("texture")),
        })
    return out


def posed(cid, clip, t):
    """Skinned world-space geometry for one character at one clip time."""
    e = get(cid)
    ch = e["ch"]
    pose = e["fns"][clip][1](t)
    v, n = rig.deform(ch.mesh, ch.skel, pose, e["joints"], e["weights"])
    return v.astype(np.float32), n.astype(np.float32), ch


def draw_char(scene, cid, clip, t, offset=(0.0, 0.0, 0.0)):
    v, n, ch = posed(cid, clip, t)
    v = v + np.array(offset, dtype=np.float32)
    mats = material_table(cid)
    scene.add_mesh(v, n, ch.mesh.uv.astype(np.float32), ch.mesh.f, mats)


def label(img, xy, text, size=26, fill=(238, 233, 224), anchor="mm", bold=False):
    d = ImageDraw.Draw(img)
    d.text(xy, text, font=R.font(size, bold), fill=fill, anchor=anchor)


# ------------------------------------------------------------------- roster
def sheet_roster():
    W, H = 1680, 1000
    sc = R.Scene(W, H, ss=2)
    spacing = 1.14
    sc.camera(R.look_at((0.0, 1.28, 6.9), (0.0, 0.70, 0.0), fov=math.radians(30),
                        aspect=W / H))
    sc.draw_background(grid=spacing, shadow_softness=10)
    for i, cid in enumerate(IDS):
        x = (i - 2) * spacing
        draw_char(sc, cid, "Idle", 0.55 + i * 0.09, offset=(x, 0, 0))
    img = sc.to_image().convert("RGB")

    # slot pads + numbers, drawn exactly the way the website does it: the number
    # is page text anchored to the `badge` bone, never baked into the model.
    d = ImageDraw.Draw(img, "RGBA")
    for i, cid in enumerate(IDS):
        ch = get(cid)["ch"]
        anchor = ch.skel.rest_pos("badge")
        world = np.array([(i - 2) * spacing + anchor[0], anchor[1] + 0.0, anchor[2]], dtype=np.float64)
        eye = sc.cam_eye
        V, P = sc.V, sc.P
        ph = np.append(world, 1.0)
        clip = (P @ (V @ ph))
        ndc = clip[:3] / clip[3]
        sx = (ndc[0] * 0.5 + 0.5) * W
        sy = (1.0 - (ndc[1] * 0.5 + 0.5)) * H
        val = [7, 3, 9, 1, 5][i]
        d.text((sx, sy), str(val), font=R.font(38, True), fill=(46, 38, 30, 240), anchor="mm")
    label(img, (24, 30), "BUBBLE-SORT SQUAD — roster", size=34, anchor="la", bold=True,
          fill=(240, 236, 228))
    label(img, (24, 74), "five original creature mascots · 14-bone shared core rig · "
                         "8 clips each · blank chest badges for runtime numbers",
          size=20, anchor="la", fill=(168, 168, 178))
    for i, cid in enumerate(IDS):
        ch = get(cid)["ch"]
        x = W * (i + 0.5) / len(IDS)
        label(img, (x, H - 34), "%s · %s" % (ch.name, ch.role.replace("The ", "")),
              size=21, anchor="mm", fill=(226, 220, 210))
    out = os.path.join(SHOTS, "roster_sheet.png")
    img.save(out)
    print("wrote", out, img.size)


# -------------------------------------------------------------------- views
def render_panel(cid, clip, t, cam, W, H, ss=2, floor=False, grid=0.0, shadow=0,
                 bg=((0.105, 0.112, 0.132), (0.045, 0.048, 0.062)), offset=(0, 0, 0)):
    """One framed render of one character in one pose."""
    sc = R.Scene(W, H, ss=ss)
    sc.bg_top = np.array(bg[0], dtype=np.float32)
    sc.bg_bot = np.array(bg[1], dtype=np.float32)
    sc.camera(cam)
    if floor:
        sc.draw_background(grid=grid, shadow_softness=shadow)
    else:
        sc.draw_background(shadow_softness=0)
    draw_char(sc, cid, clip, t, offset=offset)
    return sc.to_image().convert("RGB")


def sheet_views(cid):
    ch = get(cid)["ch"]
    h = ch.meta["height"]
    w = ch.meta["width"]
    d = ch.meta["depth"]
    pw, ph = 520, 700
    aspect = pw / float(ph)
    views = [((0, 0, 1), "FRONT  (+Z)", w), ((1, 0, 0), "SIDE  (+X)", d), ((0, 0, -1), "BACK  (-Z)", w)]
    strip = Image.new("RGB", (pw * 3, ph), (10, 11, 16))
    for i, (dirv, name, span_x) in enumerate(views):
        # fit both the height and the silhouette width into the panel
        view_h = max(h, span_x / aspect) * 1.18
        cam = R.ortho(dirv, (0, h * 0.5, 0), height=view_h, aspect=aspect)
        strip.paste(render_panel(cid, "Idle", 0.55, cam, pw, ph), (pw * i, 0))
    d = ImageDraw.Draw(strip)
    for i, (dirv, name, span_x) in enumerate(views):
        d.text((pw * i + pw // 2, ph - 40), name, font=R.font(23, True),
               fill=(228, 222, 212), anchor="mm")
        if i:
            d.line([(pw * i, 70), (pw * i, ph - 70)], fill=(66, 68, 82), width=2)
    d.text((24, 26), "%s — %s" % (ch.name, ch.blurb), font=R.font(28, True),
           fill=(240, 236, 228), anchor="la")
    d.text((24, 64), "orthographic · %0.2f m tall · front faces +Z · origin on the ground · "
                     "%d triangles · %d joints" % (ch.meta["height"], ch.meta["triangles"],
                                                   ch.meta["joint_count"]),
           font=R.font(19), fill=(170, 170, 180), anchor="la")
    out = os.path.join(SHOTS, "views_%s.png" % cid)
    strip.save(out)
    print("wrote", out, strip.size)


# -------------------------------------------------------------- silhouettes
def sheet_silhouettes():
    def row(angle_kind, height_pad, label_txt):
        W, H = 1680, 460
        sc = R.Scene(W, H, ss=2)
        hmax = max(get(c)["ch"].meta["height"] for c in IDS)
        sc.camera(R.ortho((0, 0, 1) if angle_kind == "front" else (0.75, 0.18, 1.0),
                          (0, hmax * 0.5, 0), height=hmax * 1.45, aspect=W / H))
        sc.masks = []
        spacing = 1.14
        for i, cid in enumerate(IDS):
            v, n, ch = posed(cid, "Idle", 0.5)
            v = v + np.array([(i - 2) * spacing, -ch.meta["bbox_min"][1], 0], dtype=np.float32)
            sc.add_mesh(v, n, ch.mesh.uv, ch.mesh.f,
                        [{"albedo": np.zeros(3, np.float32), "rough": 1.0, "metal": 0.0,
                          "emissive": np.zeros(3, np.float32), "alpha": 1.0,
                          "texture": None} for _ in ch.mesh.f])
        im = sc.to_image(silhouette=True).convert("RGB")
        d = ImageDraw.Draw(im)
        d.text((20, 18), label_txt, font=R.font(26, True), fill=(30, 30, 34), anchor="la")
        return im

    top = row("front", 1.0, "SILHOUETTE TEST — front elevation (solid black)")
    bot = row("3q", 1.0, "SILHOUETTE TEST — three-quarter (solid black)")
    W = top.width
    img = Image.new("RGB", (W, top.height + bot.height + 8), (255, 255, 255))
    img.paste(top, (0, 0))
    img.paste(bot, (0, top.height + 8))
    out = os.path.join(SHOTS, "silhouettes.png")
    img.save(out)
    print("wrote", out, img.size)


# ---------------------------------------------------------------- anim strip
def sheet_strip():
    poses = [("Idle", 0.60, "1 · IDLE  (breathing, blink)"),
             ("GlanceL", 0.60, "2 · GLANCE LEFT  (compare)"),
             ("Hop", 0.34, "3 · HOP  (apex, in place)"),
             ("Land", 0.07, "4 · LAND  (squash + rebound)"),
             ("Success", 0.14, "5 · SUCCESS  (double pop)")]
    pw, ph = 420, 560
    W, H = pw * len(poses), ph * len(IDS)
    img = Image.new("RGB", (W, H), (12, 14, 18))
    for r, cid in enumerate(IDS):
        for c, (clip, t, _) in enumerate(poses):
            cell = R.Scene(pw, ph, ss=1)
            hmax = get(cid)["ch"].meta["height"]
            cell.camera(R.look_at((0.95, hmax * 0.62 + 0.30, 2.35), (0.0, hmax * 0.50, 0.0),
                                  fov=math.radians(30), aspect=pw / ph))
            cell.draw_background(grid=0.0, shadow_softness=5)
            draw_char(cell, cid, clip, t)
            img.paste(cell.to_image().convert("RGB"), (c * pw, r * ph))
            del cell
            gc.collect()
    d = ImageDraw.Draw(img)
    for c, (clip, t, txt) in enumerate(poses):
        d.text((c * pw + pw // 2, 14), txt, font=R.font(21, True), fill=(236, 230, 220), anchor="ma")
    for r, cid in enumerate(IDS):
        ch = get(cid)["ch"]
        d.text((10, r * ph + ph - 26), ch.name, font=R.font(22, True), fill=(226, 220, 210), anchor="la")
        d.line([(0, r * ph), (W, r * ph)], fill=(38, 40, 50), width=2)
    d.line([(0, 0), (0, H)], fill=(38, 40, 50), width=2)
    out = os.path.join(SHOTS, "animation_strip.png")
    img.save(out)
    print("wrote", out, img.size)


def quick(cid, view="front", clip="Idle", t=0.55):
    """Fast single-panel render for design iteration:  python3 make_sheets.py q kiln front"""
    ch = get(cid)["ch"]
    h = ch.meta["height"]
    W, H = 620, 760
    dirs = {"front": (0, 0, 1), "side": (1, 0, 0), "back": (0, 0, -1),
            "3q": (0.72, 0.10, 0.90), "hero": (0.55, 0.22, 0.85)}
    d = dirs[view]
    cam = R.ortho(d, (0, h * 0.5, 0), height=h * 1.22, aspect=W / H)
    img = render_panel(cid, clip, float(t), cam, W, H, ss=1)
    dd = ImageDraw.Draw(img)
    dd.text((16, 14), "%s · %s @ %.2fs" % (cid, clip, float(t)), font=R.font(22, True),
            fill=(235, 230, 222), anchor="la")
    os.makedirs(SHOTS, exist_ok=True)
    out = os.path.join(SHOTS, "_quick_%s.png" % cid)
    img.save(out)
    print("wrote", out)


def main():
    os.makedirs(SHOTS, exist_ok=True)
    args = sys.argv[1:] or ["roster", "views", "silhouettes", "strip"]
    if args[0] == "q":
        quick(*args[1:])
        return
    t0 = time.time()
    if "roster" in args:
        sheet_roster()
    if "views" in args:
        for cid in IDS:
            sheet_views(cid)
    if "silhouettes" in args:
        sheet_silhouettes()
    if "strip" in args:
        sheet_strip()
    print("done in %.1fs" % (time.time() - t0))


if __name__ == "__main__":
    main()
