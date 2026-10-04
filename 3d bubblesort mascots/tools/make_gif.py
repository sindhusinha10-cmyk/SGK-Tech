#!/usr/bin/env python3
"""
make_gif.py — a short animated test render: the five mascots actually performing
a bubble sort pass on the array [7, 3, 9, 1, 5].

Every frame is rendered from the rigged geometry through the same clip functions
that were baked into the GLBs:
  * neighbours GlanceL / GlanceR at each comparison
  * Hop (in place) while the slot translation carries them past each other
  * NoSwap when a pair is already in order, Land on touchdown
  * Success once the array is sorted, Idle otherwise

    python3 make_gif.py            -> shots/bubblesort_rehearsal.gif
"""

import gc
import math
import os
import sys

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

SPACING = 1.10
FPS = 12
CLIP_LEN = {"Idle": 4.0, "GlanceL": 0.9, "GlanceR": 0.9, "Crouch": 0.5,
            "Hop": 0.72, "Land": 0.5, "NoSwap": 0.95, "Success": 1.25}

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
        _cache[cid] = dict(ch=ch, joints=joints, weights=weights, tex=tex,
                           fns=clips.build_clip_fns(ch))
    return _cache[cid]


def mats_for(cid):
    e = get(cid)
    out = []
    for key in e["ch"].mesh.face_mat:
        m = e["ch"].mats[key]
        out.append(dict(albedo=np.array(m["color"], np.float32),
                        rough=float(m.get("roughness", 0.5)),
                        metal=float(m.get("metallic", 0.0)),
                        emissive=np.array(m.get("emissive", (0, 0, 0)), np.float32),
                        alpha=float(m.get("alpha", 1.0)),
                        texture=e["tex"].get(m.get("texture"))))
    return out


def draw(cid, clip, t, offset):
    e = get(cid)
    pose = e["fns"][clip][1](t)
    v, n = rig.deform(e["ch"].mesh, e["ch"].skel, pose, e["joints"], e["weights"])
    return v.astype(np.float32) + np.array(offset, np.float32), n.astype(np.float32)


# --------------------------------------------------------------- sort script
def bubble_sort_events(values):
    """Produce the timeline of a bubble sort: compares, swaps, pass ends."""
    arr = list(values)
    events = []
    t = [0.20]

    def ev(kind, dur, **kw):
        events.append(dict(kind=kind, t=round(t[0], 4), dur=dur, **kw))
        t[0] += dur + 0.10

    n = len(arr)
    for p in range(n - 1):
        swapped_any = False
        for i in range(n - 1 - p):
            a, b = i, i + 1
            ev("compare", 0.85, a=a, b=b)
            if arr[a] > arr[b]:
                ev("swap", 1.30, a=a, b=b)
                arr[a], arr[b] = arr[b], arr[a]
                swapped_any = True
            else:
                ev("noswap", 0.95, a=a, b=b)
        if not swapped_any:
            break
    ev("sorted", 1.25)
    return events, arr


def build_timeline(values):
    """Turn events into per-character (clip, local time, x) samples."""
    events, sorted_arr = bubble_sort_events(values)
    total = max(e["t"] + e["dur"] for e in events) + 0.25

    # which array slot does each character value occupy at time t?
    order = list(values)
    moves = []                                    # (start, dur, from_slot, to_slot)
    for e in events:
        if e["kind"] == "swap":
            a, b = e["a"], e["b"]
            moves.append((e["t"], e["dur"] * 0.55, a, b))
            moves.append((e["t"] + e["dur"] * 0.45, e["dur"] * 0.55, b, a))
    return events, moves, order, total


def char_state(val, t, events, moves, values):
    """Position (in slots) and clip for one character value at time t."""
    slot = values.index(val) if val in values else 0
    slots = list(values)
    # walk the swaps up to time t, tracking each character's slot
    pos = {v: i for i, v in enumerate(values)}
    # rebuild state by replaying the deterministic timeline
    arr = list(values)
    for e in events:
        if e["kind"] == "swap" and e["t"] <= t:
            a, b = e["a"], e["b"]
            arr[a], arr[b] = arr[b], arr[a]
    # where is `val` right now, and is it mid-flight?
    x = None
    clip, ct = "Idle", (t % CLIP_LEN["Idle"])
    for e in events:
        if e["kind"] == "swap":
            a, b = e["a"], e["b"]
            t0 = e["t"]
            if t0 <= t < t0 + e["dur"]:
                # the two participants of this swap
                before = list(values)
                for e2 in events:
                    if e2 is e or e2["t"] > t0:
                        break
                    if e2["kind"] == "swap":
                        before[e2["a"]], before[e2["b"]] = before[e2["b"]], before[e2["a"]]
                va = before[a]
                vb = before[b]
                u = (t - t0) / e["dur"]
                arc = math.sin(min(max(u, 0.0), 1.0) * math.pi) * 0.10
                for vv, src, dst, uu in ((va, a, b, min(u / 0.55, 1.0)),
                                         (vb, b, a, max((u - 0.45) / 0.55, 0.0))):
                    if vv != val:
                        continue
                    e00 = clips.ease_out(min(max(uu, 0.0), 1.0))
                    x = src + (dst - src) * e00
                    ct = t - t0 if vv == va else max(t - (t0 + e["dur"] * 0.45), 0.0)
                    clip = "Hop" if ct < 0.72 else "Land"
                    return x - 2.0, clip, min(ct, CLIP_LEN["Land"] - 1e-3) if clip == "Land" else min(ct, 0.7199)
        if e["kind"] in ("compare", "noswap") and e["t"] <= t < e["t"] + e["dur"]:
            if val in (arr[e["a"]], arr[e["b"]]) or val in (values[e["a"]], values[e["b"]]):
                # one of the two participants looks at the other
                if val in (arr[e["a"]], arr[e["b"]]):
                    ct = t - e["t"]
                    clip = "NoSwap" if e["kind"] == "noswap" else (
                        "GlanceL" if val == arr[e["a"]] else "GlanceR")
                    return None, clip, min(ct, CLIP_LEN[clip] - 1e-3)
        if e["kind"] == "sorted" and e["t"] <= t < e["t"] + e["dur"]:
            ct = t - e["t"] + (val % 3) * 0.14
            return None, "Success", min(ct, CLIP_LEN["Success"] - 1e-3)
    # default: standing in its current slot
    if x is None:
        idx = arr.index(val) if val in arr else pos[val]
        x = idx - 2.0
        clip, ct = "Idle", (t % CLIP_LEN["Idle"])
    return x, clip, ct


def render_frame(t, values, events, moves, char_of_value, W, H, bare=False):
    sc = R.Scene(W, H, ss=1)
    sc.camera(R.look_at((0.0, 0.86, 4.4), (0.0, 0.55, 0.0), fov=math.radians(30),
                        aspect=W / H))
    sc.draw_background(grid=SPACING, shadow_softness=4)
    slots = []
    for val in values:
        x_slot, clip, ct = char_state(val, t, events, moves, values)
        cid = char_of_value[val]
        e = get(cid)
        if x_slot is None:
            arr = list(values)
            for ev in events:
                if ev["kind"] == "swap" and ev["t"] <= t:
                    arr[ev["a"]], arr[ev["b"]] = arr[ev["b"]], arr[ev["a"]]
            x_slot = (arr.index(val) if val in arr else 0) - 2.0
        x = x_slot * SPACING
        v, n = draw(cid, clip, ct, (x, 0, 0))
        sc.add_mesh(v, n, e["ch"].mesh.uv.astype(np.float32), e["ch"].mesh.f, mats_for(cid))
        slots.append((cid, val, x, e))
    img = sc.to_image().convert("RGB")
    d = ImageDraw.Draw(img, "RGBA")
    for cid, val, x, e in slots:
        anchor = e["ch"].skel.rest_pos("badge")
        world = np.array([x + anchor[0], anchor[1], anchor[2], 1.0])
        cp = sc.P @ (sc.V @ world)
        ndc = cp[:3] / cp[3]
        sx = (ndc[0] * 0.5 + 0.5) * W
        sy = (1.0 - (ndc[1] * 0.5 + 0.5)) * H
        d.text((sx, sy - 4), str(val), font=R.font(26, True), fill=(46, 38, 30, 245), anchor="mm")
    active = [e for e in events if e["t"] <= t < e["t"] + e["dur"]]
    label = ""
    if active:
        e0 = active[-1]
        if e0["kind"] == "compare":
            label = "comparing pair %d / %d" % (e0["a"] + 1, e0["b"] + 1)
        elif e0["kind"] == "swap":
            label = "swap  ·  hop + land"
        elif e0["kind"] == "noswap":
            label = "already in order  ·  no swap"
        else:
            label = "sorted  ·  success"
    if not bare:
        d.text((14, 12), "bubble-sort rehearsal  ·  clips: Idle / Glance / Hop / Land / NoSwap / Success",
               font=R.font(17, True), fill=(232, 227, 218))
        if label:
            d.text((14, 38), label, font=R.font(22, True), fill=(150, 232, 208))
    else:
        if label:
            d.text((W - 12, 12), label, font=R.font(18, True), fill=(150, 232, 208), anchor="ra")
    del sc
    gc.collect()
    return img


def keysheet(values, events, moves, char_of_value):
    """A tidy contact sheet of the key story beats."""
    W, H = 720, 250
    beats = [("compare", "1 · compare neighbours"),
             ("swap", "2 · swap  (hop, then land)"),
             ("noswap", "3 · already in order"),
             ("sorted", "4 · sorted  (success)")]
    picks = []
    for kind, caption in beats:
        ev = next((e for e in events if e["kind"] == kind), None)
        if ev is None:
            continue
        t = ev["t"] + (ev["dur"] * 0.5 if kind != "swap" else ev["dur"] * 0.55)
        picks.append((t, caption))
    # plus the very first frame
    picks = [(0.05, "0 · the array [7, 3, 9, 1, 5]")] + picks
    cols = 2
    rows = (len(picks) + cols - 1) // cols
    sheet = Image.new("RGB", (W * cols, (H + 34) * rows), (10, 12, 16))
    d = ImageDraw.Draw(sheet)
    for i, (t, caption) in enumerate(picks):
        img = render_frame(t, values, events, moves, char_of_value, W, H, bare=True)
        x = (i % cols) * W
        y = (i // cols) * (H + 34)
        sheet.paste(img, (x, y + 34))
        d.text((x + 12, y + 8), caption, font=R.font(19, True), fill=(236, 230, 220))
        d.rectangle([x, y, x + W - 1, y + H + 33], outline=(38, 40, 50))
    out = os.path.join(SHOTS, "rehearsal_keysheet.png")
    sheet.save(out)
    print("wrote", out, sheet.size)


def main():
    values = [7, 3, 9, 1, 5]
    ids = ["kiln", "ribb", "zag", "glim", "rumble"]
    char_of_value = dict(zip(values, ids))
    events, moves, order, total = build_timeline(values)

    W, H = 960, 330
    if len(sys.argv) > 1 and sys.argv[1] == "sheet":
        keysheet(values, events, moves, char_of_value)
        return
    n_frames = int(total * FPS)
    frames = []
    for f in range(n_frames):
        frames.append(render_frame(f / float(FPS), values, events, moves, char_of_value, W, H))

    out = os.path.join(SHOTS, "bubblesort_rehearsal.gif")
    frames[0].save(out, save_all=True, append_images=frames[1:], duration=int(1000 / FPS),
                   loop=0, optimize=True)
    print("wrote %s  %d frames, %.1fs, %dx%d" % (out, len(frames), total, W, H))


if __name__ == "__main__":
    main()
