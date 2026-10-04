#!/usr/bin/env python3
"""
sheets.py — render the v2 creature concepts for review.

    python3 sheets.py            # roster + per-character views + silhouettes
    python3 sheets.py roster
    python3 sheets.py views volt
    python3 sheets.py silhouettes

Everything is rendered from the *actual skinned geometry* through the v1 pipeline's
software renderer, so what you see is what would get exported: same skinning, same
clips, same lighting intent. Output lands in ./shots/.
"""

import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
for p in (os.path.join(ROOT, "tools"), HERE):
    if p not in sys.path:
        sys.path.insert(0, p)

import creatures                                                  # noqa: E402
import critters                                                   # noqa: E402
from critters import ORDER                                        # noqa: E402

# register the new creatures with the v1 pipeline, then reuse its helpers
creatures.BUILDERS.update(critters.BUILDERS)

import make_sheets as MS                                          # noqa: E402
import render as R                                                # noqa: E402

SHOTS = os.path.join(HERE, "shots")
MS.SHOTS = SHOTS
IDS = ORDER

TITLE = "TECH CRITTERS — concept v2"
SUBTITLE = ("five creatures, five different body plans · one computing idea each · "
            "same 14-bone core rig and 8 clips as v1 · originals, drawn from "
            "non-character objects")

VALUES = {"volt": 7, "chip": 3, "bug": 9, "wisp": 1, "spool": 5}


def label(img, xy, text, size=26, fill=(238, 233, 224), anchor="mm", bold=False):
    d = ImageDraw.Draw(img)
    d.text(xy, text, font=R.font(size, bold), fill=fill, anchor=anchor)


# ------------------------------------------------------------------- roster
def sheet_roster():
    W, H = 1900, 760
    spacing = 1.16
    sc = R.Scene(W, H, ss=2)
    # a little higher and further back than v1: this roster has a 1.0 m biped and a
    # 0.40 m quadruped in it, so the frame has to hold both.
    sc.camera(R.look_at((0.0, 1.12, 5.25), (0.0, 0.56, 0.0), fov=math.radians(30),
                        aspect=W / float(H)))
    sc.draw_background(grid=spacing, shadow_softness=10)
    for i, cid in enumerate(IDS):
        x = (i - (len(IDS) - 1) / 2.0) * spacing
        MS.draw_char(sc, cid, "Idle", 0.55 + i * 0.09, offset=(x, 0, 0))
    img = sc.to_image().convert("RGB")

    # slot pads + numbers, drawn the way the website does it: page text anchored to
    # the `badge` bone. Nothing numeric is ever baked into a model.
    d = ImageDraw.Draw(img, "RGBA")
    for i, cid in enumerate(IDS):
        ch = MS.get(cid)["ch"]
        anchor = ch.skel.rest_pos("badge")
        x = (i - (len(IDS) - 1) / 2.0) * spacing
        world = np.array([x + anchor[0], anchor[1], anchor[2]], dtype=np.float64)
        clip = sc.P @ (sc.V @ np.append(world, 1.0))
        ndc = clip[:3] / clip[3]
        sx = (ndc[0] * 0.5 + 0.5) * W
        sy = (1.0 - (ndc[1] * 0.5 + 0.5)) * H
        d.text((sx, sy), str(VALUES[cid]), font=R.font(36, True),
               fill=(46, 38, 30, 242), anchor="mm", stroke_width=1,
               stroke_fill=(252, 249, 243, 150))

    label(img, (26, 32), TITLE, size=34, anchor="la", bold=True, fill=(240, 236, 228))
    label(img, (26, 76), SUBTITLE, size=19, anchor="la", fill=(168, 168, 178))
    for i, cid in enumerate(IDS):
        ch = MS.get(cid)["ch"]
        x = W * (i + 0.5) / len(IDS)
        label(img, (x, H - 30), "%s · %s" % (ch.name, ch.role.replace("The ", "")),
              size=20, anchor="mm", fill=(226, 220, 210))
        label(img, (x, H - 8), "%0.2f m · %d tris"
              % (ch.meta["height"], ch.meta["triangles"]),
              size=15, anchor="mm", fill=(150, 150, 162))
    out = os.path.join(SHOTS, "concept_roster.png")
    img.save(out)
    print("wrote", out, img.size)


# -------------------------------------------------------------------- views
def sheet_views(cid):
    ch = MS.get(cid)["ch"]
    h, w, dp = ch.meta["height"], ch.meta["width"], ch.meta["depth"]
    pw, ph = 520, 700
    aspect = pw / float(ph)
    views = [((0, 0, 1), "FRONT  (+Z)", w),
             ((1, 0, 0), "SIDE  (+X)", dp),
             ((0, 0, -1), "BACK  (-Z)", w)]
    strip = Image.new("RGB", (pw * 3, ph), (10, 11, 16))
    for i, (dirv, name, span_x) in enumerate(views):
        view_h = max(h, span_x / aspect) * 1.20
        cam = R.ortho(dirv, (0, h * 0.5, 0), height=view_h, aspect=aspect)
        strip.paste(MS.render_panel(cid, "Idle", 0.55, cam, pw, ph), (pw * i, 0))
    d = ImageDraw.Draw(strip)
    for i, (dirv, name, span_x) in enumerate(views):
        d.text((pw * i + pw // 2, ph - 40), name, font=R.font(23, True),
               fill=(228, 222, 212), anchor="mm")
        if i:
            d.line([(pw * i, 70), (pw * i, ph - 70)], fill=(66, 68, 82), width=2)
    d.text((24, 26), "%s — %s" % (ch.name, ch.blurb), font=R.font(28, True),
           fill=(240, 236, 228), anchor="la")
    d.text((24, 64), "orthographic · %0.2f m tall · front faces +Z · origin on the "
                     "ground · %d triangles · %d joints"
           % (ch.meta["height"], ch.meta["triangles"], ch.meta["joint_count"]),
           font=R.font(19), fill=(170, 170, 180), anchor="la")
    out = os.path.join(SHOTS, "concept_views_%s.png" % cid)
    strip.save(out)
    print("wrote", out, strip.size)


# -------------------------------------------------------------- silhouettes
def sheet_silhouettes():
    def row(dirv, label_txt):
        W, H = 1900, 470
        sc = R.Scene(W, H, ss=2)
        hmax = max(MS.get(c)["ch"].meta["height"] for c in IDS)
        sc.camera(R.ortho(dirv, (0, hmax * 0.5, 0), height=hmax * 1.50,
                          aspect=W / float(H)))
        sc.masks = []
        spacing = 1.22
        black = [{"albedo": np.zeros(3, np.float32), "rough": 1.0, "metal": 0.0,
                  "emissive": np.zeros(3, np.float32), "alpha": 1.0, "texture": None}]
        for i, cid in enumerate(IDS):
            v, n, ch = MS.posed(cid, "Idle", 0.5)
            v = v + np.array([(i - (len(IDS) - 1) / 2.0) * spacing, 0, 0], dtype=np.float32)
            sc.add_mesh(v, n, ch.mesh.uv, ch.mesh.f, black * len(ch.mesh.f))
        im = sc.to_image(silhouette=True).convert("RGB")
        ImageDraw.Draw(im).text((20, 18), label_txt, font=R.font(26, True),
                                fill=(30, 30, 34), anchor="la")
        return im

    top = row((0, 0, 1), "SILHOUETTE TEST — front elevation (solid black)")
    bot = row((0.75, 0.18, 1.0), "SILHOUETTE TEST — three-quarter (solid black)")
    img = Image.new("RGB", (top.width, top.height + bot.height + 8), (255, 255, 255))
    img.paste(top, (0, 0))
    img.paste(bot, (0, top.height + 8))
    out = os.path.join(SHOTS, "concept_silhouettes.png")
    img.save(out)
    print("wrote", out, img.size)


def main():
    os.makedirs(SHOTS, exist_ok=True)
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    cid = sys.argv[2] if len(sys.argv) > 2 else None
    if which in ("all", "roster"):
        sheet_roster()
    if which in ("all", "views"):
        for c in ([cid] if cid else IDS):
            sheet_views(c)
    if which in ("all", "silhouettes"):
        sheet_silhouettes()
    if which in ("all", "poses"):
        sheet_poses()
    return 0




# -------------------------------------------------------------- pose proof
POSES = [("Idle", 0.55, "IDLE"), ("GlanceR", 0.45, "GLANCE"), ("Hop", 0.36, "HOP"),
         ("Land", 0.18, "LAND"), ("Success", 0.62, "SUCCESS")]


def sheet_poses():
    """Prove the concepts are riggable: run the real clips through the real rig.

    Nothing here is faked -- MS.get() builds the skinning weights and the baked clip
    functions exactly as the export pipeline does, then rig.deform() poses the mesh.
    """
    pw, ph = 300, 400
    rows = []
    for cid in IDS:
        ch = MS.get(cid)["ch"]
        h = ch.meta["height"]
        aspect = pw / float(ph)
        row = Image.new("RGB", (pw * len(POSES), ph), (12, 13, 18))
        hop = float(ch.P.get("hop_h", 0.30))
        span = h + hop + 0.16                      # tallest pose + clearance
        for i, (clip, t, name) in enumerate(POSES):
            cam = R.ortho((0.42, 0.12, 1.0), (0, span * 0.46, 0), height=span * 1.10,
                          aspect=aspect)
            row.paste(MS.render_panel(cid, clip, t, cam, pw, ph), (pw * i, 0))
        rows.append((cid, ch, row))

    W = pw * len(POSES)
    sheet = Image.new("RGB", (W, (ph + 30) * len(rows) + 62), (17, 18, 24))
    d = ImageDraw.Draw(sheet)
    d.text((20, 16), "RIG PROOF — the real 8-clip vocabulary on the new body plans",
           font=R.font(27, True), fill=(240, 236, 228), anchor="la")
    d.text((20, 50), "posed by rig.deform() through the same skinning and the same "
                     "baked clip functions the exporter uses",
           font=R.font(17), fill=(158, 158, 170), anchor="la")
    for r, (cid, ch, row) in enumerate(rows):
        y = 62 + r * (ph + 30)
        sheet.paste(row, (0, y))
        for i, (clip, t, name) in enumerate(POSES):
            cx = pw * i + 8
            d.rectangle([cx, y + 6, cx + 74, y + 26], fill=(16, 17, 22))
            d.text((cx + 6, y + 10), name, font=R.font(12, True), fill=(150, 210, 195),
                   anchor="la")
        d.text((8, y + ph + 7), "%s · %s · %0.2f m · %d joints"
               % (ch.name, ch.role.replace("The ", ""), ch.meta["height"],
                  ch.meta["joint_count"]),
               font=R.font(15, True), fill=(214, 208, 198), anchor="la")
        if r:
            d.line([(0, y - 15), (W, y - 15)], fill=(44, 46, 56), width=1)
    out = os.path.join(SHOTS, "concept_rigproof.png")
    sheet.save(out)
    print("wrote", out, sheet.size)


def _main_old():
    pass


if __name__ == "__main__":
    raise SystemExit(main())
