"""
critters — v2 concept pass: five tech-themed creatures with different BODY PLANS.

This is a concept exploration, not part of the shipped v1 roster. It reuses the v1
pipeline (mlib primitives, rig, clips, renderer) so that whatever the user picks can
be rigged, baked and exported by exactly the same tools, with the same 14-bone core
and the same eight clips.

WHAT IS DIFFERENT FROM v1
    v1 is five *objects* (pot, basket, crystal, droplet, loaf). Read together they
    feel like a set of household mascots. This pass is five *creatures* of clearly
    different kinds, each carrying a computing idea, so the roster reads like a
    collectible family instead:

        volt    BIPED      a squat capacitor buddy; amber can, glowing filament tuft
        chip    QUADRUPED  a microchip on four gold pins; low wafer slab, lit die
        bug     HEXAPOD    a debug beetle; domed carapace, circuit traces, antennae
        wisp    FLOATING   a packet spirit; faceted lantern, inner core, tail
        spool   SEGMENTED  an iteration coil; stacked rings, threaded beads

WHAT IS DELIBERATELY THE SAME (so they still read as one family)
    the shared eye construction, the blank cream badge plate, one celadon pop
    accent, the same ground contact and lighting intent, the same 14-bone core
    skeleton and the same eight clip names.

Originality: nothing here is derived from an existing character, franchise or asset
pack. The forms come from non-character objects (capacitor, chip, beetle, lantern,
coil) and the only nod to the monster-taming genre is its *design language* --
bold readable silhouettes, one clear idea per creature, big expressive eyes.
"""

import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
if os.path.join(ROOT, "tools") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "tools"))

import clips                                                     # noqa: E402
from mlib import (TAU, arc_tube, capsule, circle_poly, flat_normals, hex_poly,  # noqa: E402
                  lathe, ngon_prism, plate, rounded_rect_poly, sphere,
                  superellipsoid, torus, trapezoid_poly, tube)
from rig import Bone, Skeleton, core_bones                        # noqa: E402
from creatures import (Char, badge_plate, conform_plate, eye_pair, eye_ring,  # noqa: E402
                       facet, mat_bone, mirrored, probe_z, shared_mats, srgb)


# ================================================================ 1 · VOLT =====
def build_volt():
    """VOLT — a squat capacitor buddy. Amber can, dark polarity band, live filament."""
    M = dict(shared_mats())
    M.update({
        "can": dict(color=srgb("#E0A33C"), roughness=0.30, metallic=0.35),
        "shell": dict(color=srgb("#C9832A"), roughness=0.42, metallic=0.20),
        "band": dict(color=srgb("#2C2A2E"), roughness=0.38, metallic=0.45),
        "cap": dict(color=srgb("#F4E8CE"), roughness=0.40, metallic=0.04, texture="matte"),
        "lid": dict(color=srgb("#B8832A"), roughness=0.34, metallic=0.30),
        "fil": dict(color=srgb("#6FD9BE"), roughness=0.20, metallic=0.0,
                    emissive=tuple(c * 0.90 for c in srgb("#6FD9BE"))),
    })
    parts, shell = [], []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    # ---- two chunky legs on cream rubber feet
    def leg(sgn):
        lg = ngon_prism(0.100, 8, 0.215, taper=0.95, rot=TAU / 16.0,
                        name="leg", mat="cap")
        lg.move(sgn * 0.128, 0.118, 0.004)
        lg.tag("legL" if sgn < 0 else "legR")
        return lg

    def foot(sgn):
        f = superellipsoid(0.108, 0.050, 0.122, e1=0.55, e2=0.55, seg=20, rings=11,
                           name="foot", mat="band")
        f.move(sgn * 0.128, 0.048, 0.022)
        f.tag("legL" if sgn < 0 else "legR")
        return f

    parts.extend(mirrored(leg))
    parts.extend(mirrored(foot))

    # ---- the can itself (bottom lip, barrel, domed lid)
    body = lathe([(0.180, 0.200), (0.220, 0.246), (0.238, 0.340), (0.242, 0.452),
                  (0.238, 0.566), (0.228, 0.668), (0.208, 0.740), (0.170, 0.782),
                  (0.124, 0.808), (0.066, 0.820), (0.0, 0.824)],
                 seg=30, name="can", mat="can")
    body.tag("hips", "spine", "chest", "neck", "head", "base")
    add(body)

    # ---- cream bottom lip + dark polarity band
    lip = lathe([(0.176, 0.196), (0.206, 0.214), (0.206, 0.248), (0.176, 0.234)],
                seg=30, name="lip", mat="cap")
    lip.tag("base", "hips")
    add(lip, False)

    band = lathe([(0.228, 0.292), (0.252, 0.316), (0.252, 0.360), (0.228, 0.384)],
                 seg=30, name="band", mat="band")
    band.tag("hips")
    add(band, False)

    # ---- celadon collar just under the lid
    collar = lathe([(0.206, 0.690), (0.228, 0.708), (0.228, 0.738), (0.206, 0.756)],
                   seg=30, name="collar", mat="fil")
    collar.tag("chest")
    add(collar, False)

    # ---- little arms
    def arm(sgn):
        pts = [(sgn * 0.208, 0.556, 0.006), (sgn * 0.266, 0.520, 0.042),
               (sgn * 0.290, 0.454, 0.068)]
        a = tube(pts, 0.034, radial=9, name="arm", mat="shell")
        a.tag("armL" if sgn < 0 else "armR")
        return a

    def hand(sgn):
        h = sphere(0.044, 0.044, 0.044, seg=14, rings=9, name="hand", mat="band")
        h.move(sgn * 0.294, 0.438, 0.074)
        h.tag("armL" if sgn < 0 else "armR")
        return h

    parts.extend(mirrored(arm))
    parts.extend(mirrored(hand))

    # ---- filament tuft: two splayed leads + a centre one on the head bone
    for sgn, bone in ((-1.0, "filamentL"), (1.0, "filamentR")):
        pts = [(sgn * 0.022, 0.816, 0.0), (sgn * 0.052, 0.874, 0.012),
               (sgn * 0.092, 0.930, 0.006)]
        f = tube(pts, 0.015, radial=7, name="filament", mat="fil")
        f.tag(bone)
        parts.append(f)
        tipp = sphere(0.024, 0.024, 0.024, seg=14, rings=9, name="tip", mat="fil")
        tipp.move(sgn * 0.094, 0.934, 0.006)
        tipp.tag(bone)
        parts.append(tipp)

    c = tube([(0.0, 0.826, -0.014), (0.0, 0.884, -0.026), (0.0, 0.938, -0.018)],
             0.014, radial=7, name="filament_c", mat="fil")
    c.tag("head")
    parts.append(c)
    ct = sphere(0.022, 0.022, 0.022, seg=14, rings=9, name="tip_c", mat="fil")
    ct.move(0.0, 0.942, -0.018)
    ct.tag("head")
    parts.append(ct)

    # ---- face + badge
    ex, ey = 0.092, 0.628
    parts.extend(eye_pair(shell, ex, ey, 0.058, 0.063, 0.050, M, yaw=0.12,
                          lid=(1.14, 0.60, 0.80)))
    ez = probe_z(shell, ex, ey) or 0.24
    bz = (probe_z(shell, 0.0, 0.432) or 0.24) + 0.013
    parts.extend(conform_plate(shell, rounded_rect_poly(0.116, 0.090, 0.030),
                               0.432, thickness=0.020, proud=0.013, rim=1.13,
                               rim_proud=0.007, name="badge"))

    props = dict(hipY=0.256, spineY=0.402, chestY=0.548, neckY=0.664, headY=0.726,
                 legX=0.128, legY=0.218, baseY=0.052, badgeY=0.432, badgeZ=bz,
                 eyeX=ex, eyeY=ey, eyeZ=ez,
                 r_hips=0.256, r_spine=0.252, r_chest=0.246, r_neck=0.208, r_head=0.196,
                 r_base=0.238, r_leg=0.118, badge_size=[0.21, 0.16])

    bones = [
        mat_bone("armL", "chest", (-0.208, 0.556 - 0.548, 0.006), (0, 1, 0), 0.12, 0.10),
        mat_bone("armR", "chest", (0.208, 0.556 - 0.548, 0.006), (0, 1, 0), 0.12, 0.10),
        mat_bone("filamentL", "head", (-0.022, 0.816 - 0.726, 0.0), (0, 1, 0), 0.13, 0.07),
        mat_bone("filamentR", "head", (0.022, 0.816 - 0.726, 0.0), (0, 1, 0), 0.13, 0.07),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.32, "crouch_d": 0.110, "land_d": 0.135, "squash": 1.05,
              "gaze_yaw": -0.44, "chest_yaw": 0.38, "leg_squash": 0.74, "leg_len": 0.215,
              "up_scale": 1.0, "breath": 0.85, "sway": 0.75, "lid_close": 1.50,
              "eyelead": 0.010})

    def extras(clip, t, dur, ph):
        imp, happy, shake = ph["impact"], ph["happy"], ph["shake"]
        b = ph["breath"]
        filL = {"r": (0.24 * imp + 0.20 * happy - 0.10 * b, 0.0,
                      -0.40 * imp - 0.28 * happy + 0.12 * abs(shake))}
        filR = {"r": (0.24 * imp + 0.20 * happy - 0.10 * b, 0.0,
                      0.40 * imp + 0.28 * happy - 0.12 * abs(shake))}
        armL = {"r": (0.0, 0.0, -0.34 * imp - 0.62 * happy)}
        armR = {"r": (0.0, 0.0, 0.34 * imp + 0.62 * happy)}
        if clip == "Success":
            sc = (1.08, 1.12, 1.08)
            filL["s"] = filR["s"] = sc
            armL["s"] = armR["s"] = (1.10, 1.10, 1.10)
        if clip == "NoSwap":
            armL["r"] = (0.0, 0.0, -0.55 * ph["lean"])
            armR["r"] = (0.0, 0.0, 0.55 * ph["lean"])
        return {"filamentL": filL, "filamentR": filR, "armL": armL, "armR": armR}

    return Char("volt", "Volt", "The Charge Buddy",
                "squat amber capacitor on cream rubber feet, live filament tuft",
                M, P, props, extras, bones, ["#E0A33C", "#2C2A2E", "#F4E8CE", "#6FD9BE"],
                0.95).finish(parts)


# ================================================================ 2 · CHIP =====
def build_chip():
    """CHIP — a microchip on four gold pins. Low wafer slab, lit die on the back."""
    M = dict(shared_mats())
    M.update({
        "wafer": dict(color=srgb("#333A52"), roughness=0.44, metallic=0.10,
                      texture="matte"),
        "wafer2": dict(color=srgb("#3E4763"), roughness=0.50, metallic=0.08,
                       texture="matte"),
        "pin": dict(color=srgb("#C9A24A"), roughness=0.26, metallic=0.95),
        "die": dict(color=srgb("#7BE8CE"), roughness=0.18, metallic=0.0,
                    emissive=tuple(c * 0.95 for c in srgb("#8CF0D8"))),
        "seam": dict(color=srgb("#1B1F2C"), roughness=0.36, metallic=0.20),
        "lid": dict(color=srgb("#2A3145"), roughness=0.38, metallic=0.12),
    })
    parts, shell = [], []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    # ---- four gold pins, planted on the ground under the slab
    def pins_for(sgn, bone):
        out = []
        for zc in (-0.135, 0.135):
            pg = ngon_prism(0.040, 4, 0.150, taper=0.96, rot=math.pi / 4.0,
                            name="pin", mat="pin")
            pg.move(sgn * 0.196, 0.075, zc)
            pg.tag(bone)
            out.append(pg)
            pad = ngon_prism(0.056, 4, 0.030, taper=0.90, rot=math.pi / 4.0,
                             name="pinpad", mat="seam")
            pad.move(sgn * 0.196, 0.017, zc)
            pad.tag(bone)
            out.append(pad)
        return out

    parts.extend(pins_for(-1.0, "legL"))
    parts.extend(pins_for(1.0, "legR"))

    # ---- the slab
    slab = superellipsoid(0.300, 0.190, 0.232, e1=0.80, e2=0.80, seg=44, rings=22,
                          name="wafer", mat="wafer")
    slab.move(0.0, 0.332, 0.0)
    slab.tag("hips", "spine", "chest", "base")
    add(slab)

    # ---- lit die sitting proud on TOP, with its outline and the pin-1 dot
    die_rim = plate(rounded_rect_poly(0.152, 0.118, 0.026), 0.016, bevel=0.006,
                    name="die_rim", mat="seam")
    die_rim.rotate(rx=-math.pi / 2.0)
    die_rim.move(0.0, 0.516, -0.028)
    die_rim.tag("spine", "chest")
    parts.append(die_rim)

    diep = plate(rounded_rect_poly(0.128, 0.096, 0.022), 0.022, bevel=0.008,
                 name="die", mat="die")
    diep.rotate(rx=-math.pi / 2.0)
    diep.move(0.0, 0.522, -0.028)
    diep.tag("spine", "chest")
    parts.append(diep)

    p1 = plate(circle_poly(0.024, 14), 0.012, bevel=0.004, name="pin1", mat="die")
    p1.rotate(rx=-math.pi / 2.0)
    p1.move(-0.212, 0.508, 0.148)
    p1.tag("spine")
    parts.append(p1)

    # ---- one glowing trace strip across the front, above the eyes
    parts.extend(conform_plate(shell, trapezoid_poly(0.360, 0.360, 0.014), 0.470,
                               thickness=0.010, proud=0.006, rim_mat=None,
                               mat="die", name="trace"))

    # ---- face + badge on the front face
    ex, ey = 0.116, 0.386
    parts.extend(eye_pair(shell, ex, ey, 0.060, 0.062, 0.052, M, yaw=0.10,
                          lid=(1.16, 0.62, 0.80)))
    ez = probe_z(shell, ex, ey) or 0.23
    bz = (probe_z(shell, 0.0, 0.232) or 0.23) + 0.012
    parts.extend(conform_plate(shell, rounded_rect_poly(0.104, 0.076, 0.024),
                               0.232, thickness=0.018, proud=0.012, rim=1.14,
                               rim_proud=0.006, name="badge"))

    props = dict(hipY=0.230, spineY=0.318, chestY=0.396, neckY=0.452, headY=0.478,
                 legX=0.196, legY=0.150, baseY=0.030, badgeY=0.232, badgeZ=bz,
                 eyeX=ex, eyeY=ey, eyeZ=ez,
                 r_hips=0.290, r_spine=0.285, r_chest=0.280, r_neck=0.200, r_head=0.200,
                 r_base=0.270, r_leg=0.105, badge_size=[0.19, 0.14])

    bones = [
        mat_bone("pinFL", "hips", (-0.196, 0.150 - 0.230, -0.135), (0, 1, 0), 0.09, 0.08),
        mat_bone("pinFR", "hips", (0.196, 0.150 - 0.230, -0.135), (0, 1, 0), 0.09, 0.08),
        mat_bone("pinBL", "hips", (-0.196, 0.150 - 0.230, 0.135), (0, 1, 0), 0.09, 0.08),
        mat_bone("pinBR", "hips", (0.196, 0.150 - 0.230, 0.135), (0, 1, 0), 0.09, 0.08),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.26, "crouch_d": 0.080, "land_d": 0.100, "squash": 1.20,
              "gaze_yaw": -0.42, "chest_yaw": 0.34, "leg_squash": 0.66, "leg_len": 0.150,
              "up_scale": 1.0, "breath": 0.70, "sway": 0.85, "lid_close": 1.55,
              "eyelead": 0.009})

    def extras(clip, t, dur, ph):
        imp, happy = ph["impact"], ph["happy"]
        out = {}
        for nm, sgn in (("pinFL", -1.0), ("pinFR", 1.0), ("pinBL", -1.0), ("pinBR", 1.0)):
            r = [0.0, 0.0, 0.0]
            r[0] = 0.30 * imp + 0.22 * happy          # fore/aft splay on impact
            r[1] = sgn * (0.10 * happy)
            out[nm] = {"r": tuple(r)}
            if clip == "Success":
                out[nm]["s"] = (1.0, 1.10, 1.0)
        return out

    return Char("chip", "Chip", "The Wafer Index",
                "low indigo microchip on four gold pins, lit die on the back",
                M, P, props, extras, bones, ["#333A52", "#C9A24A", "#1B1F2C", "#7BE8CE"],
                0.52).finish(parts)


# ================================================================= 3 · BUG =====
def build_bug():
    """BUG — a debug beetle. Domed carapace, circuit traces, six copper legs."""
    M = dict(shared_mats())
    M.update({
        "cara": dict(color=srgb("#9FB27E"), roughness=0.42, metallic=0.05,
                     texture="matte"),
        "cara2": dict(color=srgb("#B4C48F"), roughness=0.48, metallic=0.04),
        "belly": dict(color=srgb("#EFE6D2"), roughness=0.55, metallic=0.0,
                      texture="matte"),
        "leg": dict(color=srgb("#B5713F"), roughness=0.36, metallic=0.55),
        "trace": dict(color=srgb("#6FD9BE"), roughness=0.18, metallic=0.0,
                      emissive=tuple(c * 0.95 for c in srgb("#8CF0D8"))),
        "seam": dict(color=srgb("#3B3F2E"), roughness=0.40, metallic=0.10),
        "lid": dict(color=srgb("#8C9E6B"), roughness=0.44, metallic=0.05),
    })
    parts, shell = [], []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    # ---- six legs, three per side
    def legs_side(sgn, bone):
        out = []
        for zc in (-0.180, 0.000, 0.180):
            pts = [(sgn * 0.160, 0.250, zc),
                   (sgn * 0.250, 0.138, zc + 0.010),
                   (sgn * 0.286, 0.032, zc + 0.024)]
            t = tube(pts, 0.032, radial=8, name="leg", mat="leg")
            t.tag(bone)
            out.append(t)
            f = sphere(0.032, 0.026, 0.032, seg=12, rings=8, name="tarsus", mat="seam")
            f.move(sgn * 0.286, 0.040, zc + 0.024)
            f.tag(bone)
            out.append(f)
        return out

    parts.extend(legs_side(-1.0, "legL"))
    parts.extend(legs_side(1.0, "legR"))

    # ---- domed carapace
    dome = superellipsoid(0.252, 0.170, 0.300, e1=0.62, e2=0.58, seg=40, rings=20,
                          name="carapace", mat="cara")
    dome.move(0.0, 0.360, -0.010)
    dome.tag("hips", "spine", "chest", "base")
    add(dome)

    # ---- cream belly plate
    belly = superellipsoid(0.212, 0.082, 0.244, e1=0.70, e2=0.62, seg=28, rings=14,
                           name="belly", mat="belly")
    belly.move(0.0, 0.214, 0.006)
    belly.tag("hips", "spine", "base")
    add(belly, False)

    # ---- wing seam down the spine
    seam = plate(trapezoid_poly(0.030, 0.022, 0.470), 0.016, bevel=0.006,
                 name="seam", mat="seam")
    seam.rotate(rx=-math.pi / 2.0)
    seam.move(0.0, 0.520, -0.020)
    seam.tag("hips", "spine", "chest", "head")
    parts.append(seam)

    # ---- circuit traces: a glowing chevron on the forehead, two glowing studs.
    # conform_plate does the surface work, so nothing is buried in the curvature.
    for yy, wid, mat in ((0.428, 0.150, "trace"), (0.396, 0.104, "trace")):
        parts.extend(conform_plate(shell, trapezoid_poly(wid, wid * 0.72, 0.014), yy,
                                   thickness=0.010, proud=0.006, rim_mat=None,
                                   mat=mat, name="circuit"))

    for sgn in (-1.0, 1.0):
        sx, sy = sgn * 0.164, 0.452
        sz = probe_z(shell, sx, sy)
        stud = sphere(0.044, 0.022, 0.044, seg=14, rings=9, name="stud", mat="trace")
        stud.move(sx, sy, (sz if sz is not None else 0.20) - 0.008)
        stud.tag("chest", "spine")
        parts.append(stud)

    # a trace running along the crest of the carapace, front to back
    ridge = tube([(0.0, 0.502, 0.238), (0.0, 0.528, 0.120), (0.0, 0.532, -0.040),
                  (0.0, 0.516, -0.192), (0.0, 0.478, -0.290)],
                 0.019, radial=7, name="ridge_trace", mat="trace")
    ridge.tag("chest", "spine", "hips")
    parts.append(ridge)

    # ---- antennae with lit tips
    for sgn, bone in ((-1.0, "antennaL"), (1.0, "antennaR")):
        pts = [(sgn * 0.070, 0.486, 0.196), (sgn * 0.126, 0.568, 0.268),
               (sgn * 0.190, 0.646, 0.300)]
        a = tube(pts, 0.017, radial=7, name="antenna", mat="leg")
        a.tag(bone)
        parts.append(a)
        tip = sphere(0.030, 0.030, 0.030, seg=14, rings=9, name="ant_tip", mat="trace")
        tip.move(sgn * 0.192, 0.650, 0.302)
        tip.tag(bone)
        parts.append(tip)

    # ---- face on the front of the dome
    ex, ey = 0.100, 0.384
    parts.extend(eye_ring(shell, ex, ey, 0.078, 0.080, mat="seam",
                          thickness=0.014, proud=0.004))
    parts.extend(eye_pair(shell, ex, ey, 0.064, 0.068, 0.056, M, yaw=0.14,
                          lid=(1.14, 0.58, 0.80)))
    ez = probe_z(shell, ex, ey) or 0.26
    bz = (probe_z(shell, 0.0, 0.248) or 0.25) + 0.012
    parts.extend(conform_plate(shell, hex_poly(0.074), 0.248, thickness=0.018,
                               proud=0.012, rim=1.14, rim_proud=0.007, name="badge"))

    props = dict(hipY=0.230, spineY=0.312, chestY=0.384, neckY=0.426, headY=0.448,
                 legX=0.160, legY=0.140, baseY=0.036, badgeY=0.248, badgeZ=bz,
                 eyeX=ex, eyeY=ey, eyeZ=ez,
                 r_hips=0.250, r_spine=0.250, r_chest=0.240, r_neck=0.190, r_head=0.190,
                 r_base=0.235, r_leg=0.105, badge_size=[0.17, 0.15])

    bones = [
        mat_bone("antennaL", "head", (-0.070, 0.486 - 0.448, 0.196), (0, 1, 0), 0.12, 0.08),
        mat_bone("antennaR", "head", (0.070, 0.486 - 0.448, 0.196), (0, 1, 0), 0.12, 0.08),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.32, "crouch_d": 0.090, "land_d": 0.112, "squash": 1.10,
              "gaze_yaw": -0.46, "chest_yaw": 0.30, "leg_squash": 0.70, "leg_len": 0.140,
              "up_scale": 1.0, "breath": 0.80, "sway": 0.85, "lid_close": 1.50,
              "eyelead": 0.010})

    def extras(clip, t, dur, ph):
        imp, happy, shake = ph["impact"], ph["happy"], ph["shake"]
        b = ph["breath"]
        aL = {"r": (0.34 * imp + 0.26 * happy - 0.10 * b, 0.0,
                    -0.20 * happy + 0.14 * shake)}
        aR = {"r": (0.34 * imp + 0.26 * happy - 0.10 * b, 0.0,
                    0.20 * happy - 0.14 * shake)}
        if clip == "Success":
            sc = (1.0, 1.14, 1.0)
            aL["s"] = aR["s"] = sc
        return {"antennaL": aL, "antennaR": aR}

    return Char("bug", "Bug", "The Debug Beetle",
                "sage carapace with circuit traces and antennae, six copper legs",
                M, P, props, extras, bones, ["#9FB27E", "#B5713F", "#3B3F2E", "#6FD9BE"],
                0.66).finish(parts)


# ================================================================ 4 · WISP =====
def build_wisp():
    """WISP — a packet spirit. Faceted lantern around a bright core, tail swept back."""
    M = dict(shared_mats())
    M.update({
        "glass": dict(color=srgb("#B0A0E2"), roughness=0.12, metallic=0.0, alpha=0.86),
        "glass2": dict(color=srgb("#C6B8F0"), roughness=0.16, metallic=0.0, alpha=0.92),
        "core": dict(color=srgb("#FFF6D8"), roughness=0.18, metallic=0.0,
                     emissive=tuple(c * 1.45 for c in srgb("#FFF6D8"))),
        "mote": dict(color=srgb("#7BE2C6"), roughness=0.20, metallic=0.0,
                     emissive=tuple(c * 0.95 for c in srgb("#7BE2C6"))),
        "rim": dict(color=srgb("#2A2233"), roughness=0.30, metallic=0.10),
        "tailc": dict(color=srgb("#8E7BC6"), roughness=0.22, metallic=0.06, alpha=0.80),
        "lid": dict(color=srgb("#9885CE"), roughness=0.20, metallic=0.0, alpha=0.90),
    })
    parts, shell = [], []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    # ---- faceted lantern body. It hovers: the lowest solid part is well clear of
    # the ground and the tail tapers to a point behind it, so nothing reads as a leg.
    body = lathe([(0.0, 0.300), (0.078, 0.344), (0.148, 0.430), (0.188, 0.548),
                  (0.194, 0.668), (0.168, 0.768), (0.106, 0.848), (0.0, 0.890)],
                 seg=8, name="lantern", mat="glass", flat=True)
    body.tag("hips", "spine", "chest", "neck", "head", "base")
    add(body)

    # ---- bright core inside, large enough to glow through the shell
    core = sphere(0.086, 0.104, 0.086, seg=22, rings=14, name="core", mat="core")
    core.move(0.0, 0.632, 0.0)
    core.tag("core", "chest")
    parts.append(core)

    # ---- four motes orbiting just outside the shell, tagged to the whisker bones
    # motes tucked against the shell so they read as orbiting the lantern rather
    # than as separate objects floating in space
    for sgn, bone, yy, zz in ((-1.0, "whiskerL", 0.706, 0.052),
                              (1.0, "whiskerR", 0.706, 0.052),
                              (-1.0, "whiskerL", 0.470, 0.128),
                              (1.0, "whiskerR", 0.470, 0.128)):
        mo = sphere(0.032, 0.032, 0.032, seg=16, rings=10, name="mote", mat="mote")
        mo.move(sgn * 0.212, yy, zz)
        mo.tag(bone, "chest")
        parts.append(mo)

    # ---- tail: swept BACK and down, tapering to a point. Reading as a tail rather
    # than a leg is the whole reason it does not hang straight down.
    tail = tube([(0.0, 0.312, -0.052), (0.008, 0.252, -0.164), (0.0, 0.196, -0.268),
                 (-0.018, 0.152, -0.360)],
                0.052, radial=9, name="tail", mat="tailc",
                taper=[1.0, 0.74, 0.44, 0.16])
    tail.tag("tailA", "base")
    parts.append(tail)

    # ---- a small crest above the head, so the top of the silhouette is not bare
    crest = lathe([(0.0, 0.858), (0.052, 0.888), (0.070, 0.918), (0.040, 0.952),
                   (0.0, 0.964)], seg=8, name="crest", mat="glass2", flat=True)
    crest.tag("head")
    parts.append(crest)

    # ---- face. The dark rim ring goes down FIRST so the lens keeps its contrast
    # against a translucent body.
    ex, ey = 0.084, 0.662
    parts.extend(eye_ring(shell, ex, ey, 0.082, 0.086, mat="rim",
                          thickness=0.016, proud=0.006))
    parts.extend(eye_pair(shell, ex, ey, 0.064, 0.068, 0.058, M, yaw=0.16,
                          lid=(1.16, 0.60, 0.80), proud=0.78))
    ez = probe_z(shell, ex, ey) or 0.19
    bz = (probe_z(shell, 0.0, 0.452) or 0.19) + 0.014
    parts.extend(conform_plate(shell, hex_poly(0.082), 0.452, thickness=0.018,
                               proud=0.013, rim=1.13, rim_proud=0.008, name="badge"))

    props = dict(hipY=0.448, spineY=0.540, chestY=0.620, neckY=0.712, headY=0.772,
                 legX=0.090, legY=0.300, baseY=0.278, badgeY=0.452, badgeZ=bz,
                 eyeX=ex, eyeY=ey, eyeZ=ez,
                 r_hips=0.200, r_spine=0.205, r_chest=0.205, r_neck=0.165, r_head=0.165,
                 r_base=0.175, r_leg=0.090, badge_size=[0.17, 0.17])

    bones = [
        mat_bone("core", "chest", (0.0, 0.632 - 0.620, 0.0), (0, 1, 0), 0.10, 0.14),
        mat_bone("whiskerL", "chest", (-0.212, 0.700 - 0.620, 0.070), (0, 1, 0), 0.10, 0.10),
        mat_bone("whiskerR", "chest", (0.212, 0.700 - 0.620, 0.070), (0, 1, 0), 0.10, 0.10),
        mat_bone("tailA", "base", (0.0, 0.312 - 0.278, -0.052), (0, -1, 0), 0.12, 0.09),
        mat_bone("tailB", "tailA", (0.0, 0.196 - 0.312, -0.216), (0, -1, 0), 0.12, 0.09),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.26, "crouch_d": 0.086, "land_d": 0.100, "squash": 1.18,
              "gaze_yaw": -0.44, "chest_yaw": 0.36, "legs": False, "leg_squash": 1.0,
              "leg_len": 0.070, "up_scale": 0.88, "breath": 1.30, "sway": 1.05,
              "lid_close": 1.50, "eyelead": 0.010})

    def extras(clip, t, dur, ph):
        imp, happy, shake, b = ph["impact"], ph["happy"], ph["shake"], ph["breath"]
        corep = {"s": (1.0 + 0.12 * happy + 0.05 * b, 1.0 + 0.18 * happy + 0.07 * b,
                       1.0 + 0.12 * happy + 0.05 * b)}
        wl = {"r": (0.30 * imp + 0.20 * happy - 0.10 * b, 0.0, -0.28 * happy - 0.16 * shake)}
        wr = {"r": (0.30 * imp + 0.20 * happy - 0.10 * b, 0.0, 0.28 * happy + 0.16 * shake)}
        a = {"r": (0.36 * imp - 0.26 * b, 0.12 * math.sin(t * 2.2),
                   -0.18 * happy - 0.14 * shake)}
        bb = {"r": (0.32 * imp + 0.26 * happy - 0.20 * b, 0.0,
                    0.26 * math.sin(t * 1.9) + 0.18 * shake)}
        return {"core": corep, "whiskerL": wl, "whiskerR": wr, "tailA": a, "tailB": bb}

    return Char("wisp", "Wisp", "The Packet Spirit",
                "faceted lilac lantern around a bright core, tail swept back, hovers",
                M, P, props, extras, bones, ["#B0A0E2", "#FFF6D8", "#8E7BC6", "#7BE2C6"],
                0.89).finish(parts)


# =============================================================== 5 · SPOOL =====
def build_spool():
    """SPOOL — an iteration coil. Cream core, steel rings hugging it, one live ring."""
    M = dict(shared_mats())
    M.update({
        "core": dict(color=srgb("#EDE7DA"), roughness=0.46, metallic=0.04,
                     texture="matte"),
        "ring": dict(color=srgb("#8A939F"), roughness=0.28, metallic=0.80),
        "ring2": dict(color=srgb("#69727E"), roughness=0.32, metallic=0.75),
        "live": dict(color=srgb("#6FD9BE"), roughness=0.16, metallic=0.0,
                     emissive=tuple(c * 1.10 for c in srgb("#7BE2C6"))),
        "brass": dict(color=srgb("#C08A46"), roughness=0.24, metallic=0.90),
        "lid": dict(color=srgb("#767F8B"), roughness=0.30, metallic=0.60),
    })
    parts, shell = [], []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    # ---- cream core that the coil is wrapped around: body + head are one solid
    core = superellipsoid(0.140, 0.232, 0.132, e1=0.72, e2=0.72, seg=32, rings=18,
                          name="core", mat="core")
    core.move(0.0, 0.280, 0.0)
    core.tag("hips", "spine", "chest", "base")
    add(core)

    head = superellipsoid(0.172, 0.170, 0.164, e1=0.60, e2=0.60, seg=34, rings=18,
                          name="head", mat="core")
    head.move(0.0, 0.630, 0.0)
    head.tag("neck", "head")
    add(head)

    # ---- cream base so the coil rests on the ground
    base = superellipsoid(0.116, 0.046, 0.108, e1=0.70, e2=0.70, seg=24, rings=12,
                          name="foot", mat="core")
    base.move(0.0, 0.042, 0.0)
    base.tag("base", "hips")
    add(base, False)

    # ---- three coil rings hugging the core; the middle one is the live ring
    for y, matv, bone in ((0.112, "ring", "coilA"), (0.208, "live", "coil"),
                          (0.304, "ring", "coilB")):
        r = torus(0.176, 0.040, seg_major=32, seg_minor=11, name="ring", mat=matv)
        r.move(0.0, y, 0.0)
        r.tag(bone, "spine")
        add(r)

    r2 = torus(0.168, 0.034, seg_major=30, seg_minor=10, name="ring", mat="ring2")
    r2.move(0.0, 0.392, 0.0)
    r2.tag("coilB", "chest")
    add(r2, False)

    # ---- brass terminal on top with a celadon bead: the coil's live end
    term = lathe([(0.030, 0.790), (0.036, 0.812), (0.036, 0.856), (0.026, 0.872)],
                 seg=10, name="terminal", mat="brass")
    term.tag("head")
    parts.append(term)

    bead = sphere(0.048, 0.048, 0.048, seg=18, rings=11, name="bead", mat="live")
    bead.move(0.0, 0.906, 0.0)
    bead.tag("head")
    parts.append(bead)

    # ---- two little arms off the chest
    def arm(sgn):
        pts = [(sgn * 0.126, 0.404, 0.034), (sgn * 0.208, 0.378, 0.078),
               (sgn * 0.254, 0.322, 0.104)]
        a = tube(pts, 0.028, radial=8, name="arm", mat="ring2")
        a.tag("armL" if sgn < 0 else "armR")
        return a

    def hand(sgn):
        h = sphere(0.038, 0.038, 0.038, seg=14, rings=9, name="hand", mat="brass")
        h.move(sgn * 0.258, 0.306, 0.108)
        h.tag("armL" if sgn < 0 else "armR")
        return h

    parts.extend(mirrored(arm))
    parts.extend(mirrored(hand))

    # ---- face + badge, both on the big cream head
    ex, ey = 0.068, 0.700
    parts.extend(eye_pair(shell, ex, ey, 0.060, 0.064, 0.052, M, yaw=0.14,
                          lid=(1.15, 0.60, 0.80)))
    ez = probe_z(shell, ex, ey) or 0.20
    bz = (probe_z(shell, 0.0, 0.552) or 0.20) + 0.013
    parts.extend(conform_plate(shell, hex_poly(0.070), 0.552, thickness=0.018,
                               proud=0.012, rim=1.14, rim_proud=0.007, name="badge"))

    props = dict(hipY=0.190, spineY=0.330, chestY=0.470, neckY=0.560, headY=0.600,
                 legX=0.100, legY=0.070, baseY=0.042, badgeY=0.552, badgeZ=bz,
                 eyeX=ex, eyeY=ey, eyeZ=ez,
                 r_hips=0.185, r_spine=0.185, r_chest=0.185, r_neck=0.190, r_head=0.190,
                 r_base=0.180, r_leg=0.090, badge_size=[0.15, 0.13])

    bones = [
        mat_bone("coil", "spine", (0.0, 0.208 - 0.330, 0.0), (0, 1, 0), 0.08, 0.20),
        mat_bone("coilA", "hips", (0.0, 0.112 - 0.190, 0.0), (0, 1, 0), 0.08, 0.20),
        mat_bone("coilB", "chest", (0.0, 0.340 - 0.470, 0.0), (0, 1, 0), 0.08, 0.20),
        mat_bone("armL", "chest", (-0.126, 0.404 - 0.470, 0.034), (0, 1, 0), 0.10, 0.09),
        mat_bone("armR", "chest", (0.126, 0.404 - 0.470, 0.034), (0, 1, 0), 0.10, 0.09),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.30, "crouch_d": 0.128, "land_d": 0.148, "squash": 1.45,
              "gaze_yaw": -0.44, "chest_yaw": 0.34, "legs": False, "leg_squash": 1.0,
              "leg_len": 0.070, "up_scale": 0.90, "breath": 1.15, "sway": 0.80,
              "lid_close": 1.50, "eyelead": 0.009})

    def extras(clip, t, dur, ph):
        imp, happy, shake, b = ph["impact"], ph["happy"], ph["shake"], ph["breath"]
        # the coil presses and releases while the core bounces inside it
        sq = 1.0 - 0.10 * imp - 0.05 * happy
        wid = 1.0 + 0.09 * imp + 0.04 * happy + 0.02 * b
        out = {}
        for nm in ("coil", "coilA", "coilB"):
            out[nm] = {"s": (wid, sq, wid),
                       "r": (0.0, 0.0, 0.26 * shake)}
        armL = {"r": (0.0, 0.0, -0.32 * imp - 0.58 * happy)}
        armR = {"r": (0.0, 0.0, 0.32 * imp + 0.58 * happy)}
        if clip == "Success":
            armL["s"] = armR["s"] = (1.10, 1.10, 1.10)
        out["armL"] = armL
        out["armR"] = armR
        return out

    return Char("spool", "Spool", "The Iteration Coil",
                "cream core wrapped in steel coil rings, one live celadon ring",
                M, P, props, extras, bones, ["#8A939F", "#C08A46", "#EDE7DA", "#6FD9BE"],
                0.80).finish(parts)


# ================================================================ registry ====
BUILDERS = {
    "volt": build_volt,
    "chip": build_chip,
    "bug": build_bug,
    "wisp": build_wisp,
    "spool": build_spool,
}

ORDER = ["volt", "chip", "bug", "wisp", "spool"]


def report():
    """Build all five and print a quick sanity table (no rendering)."""
    print("%-8s %7s %6s %6s %6s %6s  %s" %
          ("id", "tris", "joints", "height", "width", "depth", "badge"))
    for cid in ORDER:
        ch = BUILDERS[cid]()
        m = ch.meta
        print("%-8s %7d %6d %6.3f %6.3f %6.3f  %s" %
              (cid, m["triangles"], m["joint_count"], m["height"], m["width"],
               m["depth"], [round(v, 3) for v in m["badge_anchor"]]))
    return 0


if __name__ == "__main__":
    raise SystemExit(report())
