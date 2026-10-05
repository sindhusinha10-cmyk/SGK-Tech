"""
creatures — the five Bubble-Sort Mascots (Indian Culture & Heritage Set).

High-fidelity anatomical and expressive rebuild matching `heritage_roster_final.png`:
  1. Gaja   — Chubby cheerful biped baby elephant, curved lifted trunk, wide floppy cupped ears with pink hollows.
  2. Mayur  — Plump chick, 3-feather crown, expansive curved 11-feather fan with concentric eye-spots.
  3. Diya   — Earthen pinched-lip lamp bowl, fluid twisting S-curve flame with hot core, cheek ember, hugging hands.
  4. Patra  — Spiral rolled manuscript parchment, torn/curling edges, open hollow top coil, holding miniature brass-tipped scroll rods.
  5. Kumbha — Ornate golden Kalasha brass pot with engraved neck relief, lanceolate mango leaves cupping a pointed fibrous coconut.

All follow the strict design & rigging requirements:
  * Y-up, front = +Z, ground at Y=0, one shared 14-bone core skeleton + extras
  * Blank un-deformed badge plate on chest for runtime number projection
  * Open, expressive, happy eyes (arched upper lid, circular glint highlight)
  * Unique silhouettes, materials, heights, and appendage mechanics
"""

import math
import numpy as np

import clips
from mlib import (TAU, Mesh, Part, arc_tube, capsule, flat_normals, hex_poly, lathe,
                  ngon_prism, plate, rounded_rect_poly, sphere, superellipsoid, torus, tube)
from rig import Bone, Skeleton, core_bones


# --------------------------------------------------------------------- colour
def srgb(h):
    """sRGB hex -> linear RGB tuple (glTF baseColorFactor is linear)."""
    if isinstance(h, str):
        h = int(h.lstrip("#"), 16)
    out = []
    for shift in (16, 8, 0):
        c = ((h >> shift) & 0xFF) / 255.0
        out.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return tuple(out)


def shared_mats():
    return {
        "eye_dark": dict(color=srgb("#16161D"), roughness=0.08, metallic=0.0),
        "eye_glint": dict(color=srgb("#FFFFFF"), roughness=0.20, metallic=0.0,
                          emissive=tuple(c * 0.90 for c in srgb("#FFF9EE"))),
        "badge": dict(color=srgb("#F8F4EA"), roughness=0.50, metallic=0.0, texture="matte"),
        "badge_rim": dict(color=srgb("#D4A548"), roughness=0.28, metallic=0.88, texture=None),
        "pop": dict(color=srgb("#6FD9BE"), roughness=0.30, metallic=0.15,
                    emissive=tuple(c * 0.30 for c in srgb("#6FD9BE"))),
    }


def mat_bone(name, parent, offset, dirv=(0, 1, 0), length=0.10, radius=0.16, group="extra"):
    return Bone(name, parent, offset, w_dir=dirv, w_len=length, w_radius=radius, group=group)


def probe_z(parts, x, y, z_start=3.0):
    o = np.array([x, y, z_start], dtype=np.float64)
    d = np.array([0.0, 0.0, -1.0])
    best = None
    for p in parts:
        if len(p.f) == 0:
            continue
        v0 = p.v[p.f[:, 0]]; v1 = p.v[p.f[:, 1]]; v2 = p.v[p.f[:, 2]]
        e1 = v1 - v0; e2 = v2 - v0
        pv = np.cross(d, e2)
        det = np.einsum("ij,ij->i", e1, pv)
        ok = np.abs(det) > 1e-12
        if not ok.any():
            continue
        inv = np.zeros_like(det)
        inv[ok] = 1.0 / det[ok]
        tv = o[None, :] - v0
        u = np.einsum("ij,ij->i", tv, pv) * inv
        qv = np.cross(tv, e1)
        vv = np.einsum("ij,j->i", qv, d) * inv
        t = np.einsum("ij,ij->i", e2, qv) * inv
        m = ok & (u >= 0) & (u <= 1) & (vv >= 0) & (u + vv <= 1) & (t > 1e-6)
        if m.any():
            z = z_start - float(t[m].min())
            if best is None or z > best:
                best = z
    return best


def eye_pair(shell, cx, cy, rx, ry, rz, M, lid=(1.10, 0.40, 0.70), lid_lift=1.45,
             proud=0.76, yaw=0.0, glint=0.36, brow_lift=0.0, lid_mat="lid"):
    """
    Open, cheerful, appealing mascot eyes.
    The eyelids sit comfortably arched above the iris in rest pose so the character looks
    wide-eyed, curious, and friendly rather than sleepy or droopy.
    """
    parts = []
    for side, sgn, bone in (("L", -1.0, "eyeL"), ("R", 1.0, "eyeR")):
        zf = probe_z(shell, sgn * cx, cy)
        if zf is None:
            zf = 0.25
        cz = zf - rz * (1.0 - proud)
        e = sphere(rx, ry, rz, seg=26, rings=16, name="eye" + side, mat="eye_dark")
        e.move(sgn * cx, cy, cz)
        if yaw:
            e.rotate(ry=sgn * yaw)
        e.tag(bone)
        parts.append(e)

        # Primary glint highlight (top corner)
        g = sphere(rx * glint, ry * glint, rz * (glint * 0.8), seg=14, rings=8,
                   name="glint" + side, mat="eye_glint")
        g.move(sgn * (cx - 0.28 * rx), cy + 0.32 * ry, cz + rz * 0.82)
        g.tag(bone)
        parts.append(g)

        # Secondary cute mini catchlight
        g2 = sphere(rx * glint * 0.45, ry * glint * 0.45, rz * glint * 0.4, seg=10, rings=6,
                    name="glint2" + side, mat="eye_glint")
        g2.move(sgn * (cx + 0.25 * rx), cy - 0.28 * ry, cz + rz * 0.84)
        g2.tag(bone)
        parts.append(g2)

        # Arched upper eyelid flap
        lr, ly, lz = rx * lid[0], ry * lid[1], rz * lid[2]
        lidp = superellipsoid(lr, ly, lz, e1=0.55, e2=0.55, seg=20, rings=12,
                              name="lid" + side, mat=lid_mat)
        lidp.move(sgn * cx, cy + lid_lift * ry + brow_lift, cz + lz * 0.22)
        lidp.tag("lid" + side)
        parts.append(lidp)
    return parts


def conform_plate(shell, poly, y, thickness=0.014, proud=0.009, mat="badge",
                  rim_mat="badge_rim", rim=1.12, rim_proud=0.006,
                  name="badge", cx=0.0, bone="badge"):
    c = (sum(px for px, _ in poly) / len(poly), sum(py for _, py in poly) / len(poly))
    lcx, lcy = c
    off = float(cx)
    span_x = max(abs(px - lcx) for px, _ in poly) or 0.05
    span_y = max(abs(py - lcy) for _, py in poly) or 0.05

    def surf(px, py):
        best = None
        for dx in (0.0, -0.22, 0.22):
            for dy in (0.0, -0.22, 0.22):
                z = probe_z(shell, off + px + dx * span_x, py + dy * span_y)
                if z is not None and (best is None or z > best):
                    best = z
        return best if best is not None else 0.3

    def build(outline, half_z, base_z, material, pname):
        v, n, uv, f = [], [], [], []
        v.append((off + lcx, y + lcy, surf(lcx, y + lcy) + base_z))
        n.append((0, 0, 1)); uv.append((0.5, 0.5))
        ring = []
        for (px, py) in outline:
            ring.append(len(v))
            v.append((off + px, y + py, surf(px, y + py) + base_z))
            n.append((0, 0, 1))
            uv.append(((px - lcx) * 1.2 + 0.5, (py - lcy) * 1.2 + 0.5))
        for i, ri in enumerate(ring):
            f.append([0, ri, ring[(i + 1) % len(ring)]])
        back = []
        for (px, py) in outline:
            back.append(len(v))
            v.append((off + px, y + py, surf(px, y + py) + base_z - half_z * 2))
            n.append((0, 0, -1))
            uv.append(((px - lcx) * 1.2 + 0.5, (py - lcy) * 1.2 + 0.5))
        bi = len(v)
        v.append((off + lcx, y + lcy, surf(lcx, y + lcy) + base_z - half_z * 2))
        n.append((0, 0, -1)); uv.append((0.5, 0.5))
        for i, ri in enumerate(back):
            f.append([bi, back[(i + 1) % len(back)], ri])
        for i, ri in enumerate(ring):
            j = (i + 1) % len(ring)
            f.append([ri, back[j], ring[j]])
            f.append([ri, back[i], back[j]])
        p = Part(pname, material, v, n, uv, f)
        p.tag(bone)
        return p

    parts = []
    if rim_mat and rim > 0.0:
        rim_poly = [(px * rim, py * rim) for px, py in poly]
        parts.append(build(rim_poly, thickness * 0.35, rim_proud, rim_mat, name + "_rim"))
    parts.append(build(poly, thickness * 0.5, proud, mat, name + "_face"))
    return parts


def mirrored(part_fn):
    res_pos = part_fn(1.0)
    res_neg = part_fn(-1.0)
    out = []
    for item in (res_pos, res_neg):
        if isinstance(item, list):
            out.extend(item)
        else:
            out.append(item)
    return out


class Char(object):
    def __init__(self, cid, name, role, blurb, mats, P, props, extras, bones,
                 palette, height):
        self.id = cid
        self.name = name
        self.role = role
        self.blurb = blurb
        self.mats = mats
        self.P = P
        self.props = props
        self.extras = extras
        self.bones = bones
        self.palette = palette
        self.height = height
        self.mesh = None
        self.skel = None
        self.meta = {}

    def finish(self, parts):
        mesh = Mesh()
        for p in parts:
            mesh.add(p)
        lo, hi = mesh.bbox()
        if abs(lo[1]) > 1e-9:
            mesh.v = mesh.v - np.array([0.0, lo[1], 0.0])
            self.meta["ground_shift"] = round(float(lo[1]), 4)
        lo, hi = mesh.bbox()
        self.mesh = mesh
        self.skel = Skeleton(core_bones(self.props) + self.bones)
        self.meta.update({
            "id": self.id, "name": self.name, "role": self.role,
            "height": round(float(hi[1] - lo[1]), 4),
            "width": round(float(hi[0] - lo[0]), 4),
            "depth": round(float(hi[2] - lo[2]), 4),
            "bbox_min": [round(float(x), 4) for x in lo],
            "bbox_max": [round(float(x), 4) for x in hi],
            "triangles": int(mesh.tri_count()),
            "vertices": int(len(mesh.v)),
            "badge_anchor": [round(float(x), 4) for x in self.skel.rest_pos("badge")],
            "badge_size": self.props.get("badge_size", [0.18, 0.11]),
            "clip_order": [c for c, _ in clips.CLIP_SPECS],
            "part_count": len(mesh.parts),
            "joint_count": len(self.skel.bones),
        })
        return self


# ============================================================== 1 · GAJA ======
def build_gaja():
    """
    GAJA — Chubby cheerful biped baby elephant mascot.
    Features: wide cupped floppy ears with pink hollows, joyful lifted 'J' trunk,
    radiant round cheeks, friendly open smile, chubby bipedal toddler legs.
    """
    M = dict(shared_mats())
    M.update({
        "skin": dict(color=srgb("#5A748C"), roughness=0.52, metallic=0.01, texture="ceramic"),
        "skin_light": dict(color=srgb("#7C96AE"), roughness=0.48, metallic=0.01),
        "ear_inner": dict(color=srgb("#E48C76"), roughness=0.55, metallic=0.0),
        "tusk": dict(color=srgb("#FFFDF2"), roughness=0.22, metallic=0.0),
        "mouth_dark": dict(color=srgb("#7E2C2C"), roughness=0.40, metallic=0.0),
        "lid": dict(color=srgb("#50687E"), roughness=0.50, metallic=0.01),
    })
    parts = []
    shell = []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    # Chubby biped legs with rounded toddler feet
    def biped_leg(sgn):
        foot = superellipsoid(0.125, 0.058, 0.145, e1=0.42, e2=0.42, seg=20, rings=10,
                              name="foot", mat="skin")
        foot.move(sgn * 0.190, 0.058, 0.02)
        foot.tag("legL" if sgn < 0 else "legR")

        leg_col = capsule(0.095, 0.190, seg=18, rings=6, name="leg_col", mat="skin")
        leg_col.move(sgn * 0.190, 0.195, 0.0)
        leg_col.tag("legL" if sgn < 0 else "legR")

        # 3 rounded toenails
        toes = []
        for ti, tang in enumerate((-0.26, 0.0, 0.26)):
            toe = sphere(0.024, 0.022, 0.026, seg=10, rings=6, name=f"toe_{ti}", mat="tusk")
            toe.move(sgn * (0.190 + tang * 0.075), 0.024, 0.15)
            toe.tag("legL" if sgn < 0 else "legR")
            toes.append(toe)
        return [foot, leg_col] + toes

    parts.extend(mirrored(biped_leg))

    # Chubby pear-shaped belly
    belly = lathe([(0.170, 0.220), (0.280, 0.310), (0.355, 0.440), (0.365, 0.580),
                   (0.310, 0.720), (0.230, 0.810)], seg=32, name="belly", mat="skin")
    belly.tag("hips", "spine", "chest", "base")
    add(belly)

    # Large expressive domed head with cheeks
    head = sphere(0.335, 0.325, 0.330, seg=32, rings=22, name="head", mat="skin")
    head.move(0.0, 0.960, 0.035)
    head.tag("head", "neck")
    add(head)

    # Cheerful chubby cheeks
    def cheek(sgn):
        ck = sphere(0.085, 0.075, 0.065, seg=14, rings=10, name="cheek", mat="skin_light")
        ck.move(sgn * 0.230, 0.880, 0.240)
        ck.tag("head")
        return ck

    parts.extend(mirrored(cheek))

    # Wide cupped floppy ears flaring outward and back
    def ear(sgn):
        outer = superellipsoid(0.045, 0.240, 0.250, e1=0.55, e2=0.55, seg=20, rings=12,
                               name="ear_outer", mat="skin")
        outer.rotate(rz=sgn * 0.08, ry=sgn * 0.48)
        outer.move(sgn * 0.410, 0.990, -0.060)
        outer.tag("earL" if sgn < 0 else "earR")

        inner = superellipsoid(0.020, 0.200, 0.210, e1=0.55, e2=0.55, seg=18, rings=10,
                               name="ear_inner", mat="ear_inner")
        inner.rotate(rz=sgn * 0.08, ry=sgn * 0.48)
        inner.move(sgn * 0.415, 0.990, -0.045)
        inner.tag("earL" if sgn < 0 else "earR")
        return [outer, inner]

    parts.extend(mirrored(ear))

    # Joyful trunk curving proudly upward in a 'J' trumpet
    trunk_pts = [
        (0.0, 0.900, 0.280),
        (0.0, 0.810, 0.370),
        (0.0, 0.790, 0.490),
        (0.0, 0.920, 0.580),
        (0.0, 1.070, 0.590),
        (0.0, 1.140, 0.550),
    ]
    trunk = tube(trunk_pts, 0.085, radial=16, name="trunk", mat="skin",
                 taper=[1.0, 0.85, 0.72, 0.60, 0.50, 0.45])
    trunk.tag("trunk.01", "trunk.02", "trunk.03", "head")
    add(trunk)

    # Friendly open mouth beneath trunk base
    mouth = superellipsoid(0.055, 0.038, 0.040, e1=0.45, e2=0.45, seg=14, rings=8,
                           name="mouth", mat="mouth_dark")
    mouth.move(0.0, 0.815, 0.295)
    mouth.tag("head")
    parts.append(mouth)

    # Curved joyful tusks pointing forward-outward
    def tusk(sgn):
        t = arc_tube((0.0, 0.855, 0.290), 0.075, 0.2, 1.4, 0.025, steps=10, plane="YZ",
                     radial=8, name="tusk", mat="tusk")
        t.move(sgn * 0.125, 0.0, 0.0)
        t.rotate(ry=sgn * 0.35, rx=0.15)
        t.tag("head")
        return t

    parts.extend(mirrored(tusk))

    # Cute short arms in front
    def arm(sgn):
        a = tube([(sgn * 0.280, 0.690, 0.060),
                  (sgn * 0.310, 0.560, 0.180),
                  (sgn * 0.190, 0.530, 0.260)], 0.065, radial=14, name="arm", mat="skin",
                 taper=[1.0, 0.92, 0.85])
        a.tag("armL" if sgn < 0 else "armR", "chest")
        paw = sphere(0.058, 0.052, 0.058, seg=14, rings=8, name="paw", mat="skin")
        paw.move(sgn * 0.190, 0.530, 0.260)
        paw.tag("armL" if sgn < 0 else "armR", "chest")
        return [a, paw]

    parts.extend(mirrored(arm))

    # Big open expressive eyes
    ex, ey = 0.130, 0.985
    parts.extend(eye_pair(shell, ex, ey, 0.070, 0.078, 0.044, M,
                          lid=(1.10, 0.35, 0.80), lid_lift=1.35, proud=0.80, lid_mat="lid"))

    # Blank cream badge plate on chest
    poly = rounded_rect_poly(0.195, 0.120, 0.034, seg=6)
    parts.extend(conform_plate(shell, poly, 0.520, thickness=0.019, proud=0.013,
                               rim=1.10, rim_proud=0.008, name="badge"))
    pz = (probe_z(shell, 0.0, 0.520) or 0.34) + 0.013

    props = dict(hipY=0.30, spineY=0.48, chestY=0.66, neckY=0.82, headY=0.96,
                 legX=0.190, legY=0.20, baseY=0.06, badgeY=0.520, badgeZ=pz,
                 eyeX=ex, eyeY=ey, eyeZ=(probe_z(shell, ex, ey) or 0.30),
                 r_hips=0.36, r_spine=0.36, r_chest=0.34, r_neck=0.30, r_head=0.34,
                 r_base=0.30, r_leg=0.15, badge_size=[0.195, 0.120])

    bones = [
        mat_bone("trunk.01", "head", (0.0, 0.880 - 0.96, 0.320), (0, 0, 1), 0.12, 0.14),
        mat_bone("trunk.02", "trunk.01", (0.0, -0.04, 0.120), (0, 1, 1), 0.12, 0.12),
        mat_bone("trunk.03", "trunk.02", (0.0, 0.12, 0.080), (0, 1, 0), 0.12, 0.10),
        mat_bone("earL", "head", (-0.410, 0.030, -0.060), (-1, 0, 0), 0.18, 0.20),
        mat_bone("earR", "head", (0.410, 0.030, -0.060), (1, 0, 0), 0.18, 0.20),
        mat_bone("armL", "chest", (-0.280, 0.690 - 0.66, 0.060), (-1, -1, 1), 0.20, 0.14),
        mat_bone("armR", "chest", (0.280, 0.690 - 0.66, 0.060), (1, -1, 1), 0.20, 0.14),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.28, "crouch_d": 0.080, "land_d": 0.095, "squash": 0.85,
              "gaze_yaw": -0.32, "chest_yaw": 0.45, "leg_squash": 0.72, "leg_len": 0.20,
              "up_scale": 1.0, "breath": 1.0, "sway": 0.9, "lid_close": 1.65})

    def extras(clip, t, dur, ph):
        b = ph["breath"]
        lag = ph["lag_up"]
        imp = ph["impact"]
        happy = ph["happy"]
        ear_flap = 0.15 * b + 0.35 * happy + 0.25 * imp - 1.8 * lag
        trunk_wave = 0.20 * b - 2.5 * lag + 0.50 * happy
        out = {
            "earL": {"r": (0.0, 0.0, -ear_flap)},
            "earR": {"r": (0.0, 0.0, ear_flap)},
            "trunk.01": {"r": (0.10 * b - 0.8 * lag, 0.0, 0.15 * ph["gaze"])},
            "trunk.02": {"r": (0.18 * trunk_wave, 0.0, 0.10 * ph["gaze"])},
            "trunk.03": {"r": (0.25 * trunk_wave + 0.40 * happy, 0.0, 0.0)},
            "armL": {"r": (0.15 * b + 0.30 * happy, 0.0, -0.10 * happy)},
            "armR": {"r": (0.15 * b + 0.30 * happy, 0.0, 0.10 * happy)},
        }
        return out

    return Char("gaja", "Gaja", "The Heavyweight Anchor",
                "bipedal baby elephant mascot with floppy ears and curved trunk",
                M, P, props, extras, bones,
                ["#5A748C", "#7C96AE", "#E48C76", "#FFFDF2"], 1.25).finish(parts)


# ============================================================== 2 · MAYUR =====
def build_mayur():
    """
    MAYUR — Peacock chick with vibrant fanned plumage. Pattern comparator.
    Features: 3-feather crown crest, plump round chick body, expansive dual-tier
    emerald & gold tail fan spreading wide and high behind head with vibrant eye-spots.
    """
    M = dict(shared_mats())
    M.update({
        "body_teal": dict(color=srgb("#247285"), roughness=0.35, metallic=0.03),
        "fan_emerald": dict(color=srgb("#239768"), roughness=0.40, metallic=0.06),
        "fan_gold": dict(color=srgb("#E4B74C"), roughness=0.28, metallic=0.70),
        "fan_indigo": dict(color=srgb("#1F2F64"), roughness=0.22, metallic=0.10),
        "beak": dict(color=srgb("#FFF2D0"), roughness=0.28, metallic=0.0),
        "lid": dict(color=srgb("#1D6070"), roughness=0.38, metallic=0.03),
    })
    parts = []
    shell = []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    # Slender bird legs with 3-toed feet
    def bird_leg(sgn):
        leg = capsule(0.026, 0.185, seg=16, rings=8, name="bird_leg", mat="beak")
        leg.move(sgn * 0.115, 0.100, 0.0)
        leg.tag("legL" if sgn < 0 else "legR")

        foot_parts = []
        for fi, f_ang in enumerate((-0.42, 0.0, 0.42)):
            toe = capsule(0.015, 0.085, seg=14, rings=6, name=f"toe_{fi}", mat="beak")
            toe.rotate(ry=f_ang)
            toe.move(sgn * 0.115 + math.sin(f_ang) * 0.040, 0.015, math.cos(f_ang) * 0.040)
            toe.tag("legL" if sgn < 0 else "legR")
            foot_parts.append(toe)
        return [leg] + foot_parts

    parts.extend(mirrored(bird_leg))

    # Round chick body
    body = sphere(0.260, 0.270, 0.260, seg=28, rings=18, name="chick_body", mat="body_teal")
    body.move(0.0, 0.370, 0.0)
    body.tag("hips", "spine", "chest", "base")
    add(body)

    # Cute bird head with cheeks
    head = sphere(0.245, 0.255, 0.245, seg=28, rings=18, name="chick_head", mat="body_teal")
    head.move(0.0, 0.700, 0.030)
    head.tag("head", "neck")
    add(head)

    # 3 distinct curved feather stalks for crown crest
    for ci, c_ang in enumerate((-0.30, 0.0, 0.30)):
        c_stem = tube([(0.0, 0.930, 0.040),
                       (math.sin(c_ang) * 0.085, 1.040, 0.030)], 0.009, radial=8,
                      name=f"crest_stem_{ci}", mat="fan_emerald")
        c_stem.tag("crest.top", "head")
        c_tip = superellipsoid(0.026, 0.046, 0.014, e1=0.45, e2=0.45, seg=12, rings=6,
                               name=f"crest_tip_{ci}", mat="fan_indigo")
        c_tip.rotate(rz=-c_ang)
        c_tip.move(math.sin(c_ang) * 0.085, 1.070, 0.030)
        c_tip.tag("crest.top", "head")

        c_gold = sphere(0.012, 0.012, 0.010, seg=8, rings=6, name=f"crest_gold_{ci}", mat="fan_gold")
        c_gold.move(math.sin(c_ang) * 0.085, 1.070, 0.042)
        c_gold.tag("crest.top", "head")
        parts.extend([c_stem, c_tip, c_gold])

    # Cute rounded triangular wedge beak
    beak = superellipsoid(0.046, 0.038, 0.075, e1=0.38, e2=0.38, seg=14, rings=8,
                          name="beak", mat="beak")
    beak.move(0.0, 0.660, 0.265)
    beak.tag("head")
    add(beak)

    # Small curved side wings
    def wing(sgn):
        w = superellipsoid(0.038, 0.135, 0.175, e1=0.45, e2=0.50, seg=16, rings=10,
                           name="wing", mat="body_teal")
        w.rotate(ry=sgn * 0.32, rz=sgn * 0.22)
        w.move(sgn * 0.260, 0.430, -0.020)
        w.tag("chest")
        return w

    parts.extend(mirrored(wing))

    # Magnificent peacock tail fan (9 fanned feathers, large radius, radial sweep)
    N_FEATHERS = 9
    for fi in range(N_FEATHERS):
        t_frac = fi / (N_FEATHERS - 1)
        theta = -1.35 + t_frac * 2.70
        rad = 0.560
        fx = math.sin(theta) * rad
        fy = 0.500 + math.cos(theta) * (rad * 0.82)
        fz = -0.170

        f_blade = superellipsoid(0.085, 0.230, 0.024, e1=0.45, e2=0.45, seg=14, rings=8,
                                 name=f"feather_{fi}", mat="fan_emerald")
        f_blade.rotate(rz=-theta)
        f_blade.move(fx, fy, fz)
        f_blade.tag("tailFan.L" if theta < -0.1 else ("tailFan.R" if theta > 0.1 else "tailFan_root"))
        parts.append(f_blade)

        # Concentric Gold & Indigo eye-spot
        spot_gold = superellipsoid(0.050, 0.072, 0.014, e1=0.50, e2=0.50, seg=12, rings=6,
                                   name=f"spot_g_{fi}", mat="fan_gold")
        spot_gold.rotate(rz=-theta)
        spot_gold.move(fx * 1.08, fy + math.cos(theta) * 0.08, fz + 0.014)
        spot_gold.tag("tailFan.L" if theta < -0.1 else ("tailFan.R" if theta > 0.1 else "tailFan_root"))

        spot_ind = sphere(0.026, 0.035, 0.012, seg=10, rings=6, name=f"spot_i_{fi}", mat="fan_indigo")
        spot_ind.rotate(rz=-theta)
        spot_ind.move(fx * 1.08, fy + math.cos(theta) * 0.08, fz + 0.022)
        spot_ind.tag("tailFan.L" if theta < -0.1 else ("tailFan.R" if theta > 0.1 else "tailFan_root"))
        parts.extend([spot_gold, spot_ind])

    # Big open expressive eyes
    ex, ey = 0.110, 0.720
    parts.extend(eye_pair(shell, ex, ey, 0.065, 0.072, 0.040, M,
                          lid=(1.10, 0.35, 0.80), lid_lift=1.32, proud=0.80, lid_mat="lid"))

    # Blank cream badge on chest
    poly = rounded_rect_poly(0.170, 0.110, 0.030, seg=6)
    parts.extend(conform_plate(shell, poly, 0.380, thickness=0.018, proud=0.013,
                               rim=1.10, rim_proud=0.008, name="badge"))
    pz = (probe_z(shell, 0.0, 0.380) or 0.26) + 0.013

    props = dict(hipY=0.22, spineY=0.36, chestY=0.50, neckY=0.60, headY=0.72,
                 legX=0.115, legY=0.12, baseY=0.05, badgeY=0.380, badgeZ=pz,
                 eyeX=ex, eyeY=ey, eyeZ=(probe_z(shell, ex, ey) or 0.26),
                 r_hips=0.28, r_spine=0.28, r_chest=0.26, r_neck=0.24, r_head=0.26,
                 r_base=0.24, r_leg=0.08, badge_size=[0.170, 0.110])

    bones = [
        mat_bone("tailFan_root", "hips", (0.0, 0.370 - 0.22, -0.170), (0, 1, 0), 0.24, 0.30),
        mat_bone("tailFan.L", "tailFan_root", (-0.220, 0.180, 0.0), (-1, 1, 0), 0.24, 0.26),
        mat_bone("tailFan.R", "tailFan_root", (0.220, 0.180, 0.0), (1, 1, 0), 0.24, 0.26),
        mat_bone("crest.top", "head", (0.0, 0.930 - 0.72, 0.040), (0, 1, 0), 0.16, 0.14),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.32, "crouch_d": 0.070, "land_d": 0.085, "squash": 0.90,
              "gaze_yaw": -0.38, "chest_yaw": 0.40, "leg_squash": 0.65, "leg_len": 0.16,
              "up_scale": 1.0, "breath": 1.1, "sway": 1.0, "lid_close": 1.60})

    def extras(clip, t, dur, ph):
        b = ph["breath"]
        lag = ph["lag_up"]
        imp = ph["impact"]
        happy = ph["happy"]
        fan_spread = 1.0 + 0.18 * happy - 0.20 * ph["legsq"]
        crest_wobble = 0.20 * b - 3.0 * lag + 0.40 * happy
        out = {
            "tailFan_root": {"s": (fan_spread, fan_spread, 1.0),
                             "r": (0.08 * b - 1.5 * lag, 0.0, 0.10 * ph["shake"])},
            "tailFan.L": {"r": (0.0, 0.0, -0.15 * happy - 0.10 * abs(ph["shake"]))},
            "tailFan.R": {"r": (0.0, 0.0, 0.15 * happy + 0.10 * abs(ph["shake"]))},
            "crest.top": {"r": (0.12 * crest_wobble, 0.0, 0.10 * ph["gaze"])},
        }
        return out

    return Char("mayur", "Mayur", "The Pattern Comparator",
                "peacock chick with radiant emerald-and-gold fanned plumage",
                M, P, props, extras, bones,
                ["#247285", "#239768", "#E4B74C", "#FFF2D0"], 1.15).finish(parts)


# ============================================================== 3 · DIYA ======
def build_diya():
    """
    DIYA — Terracotta oil lamp with living sculpted flame crest. Traversal pointer.
    Features: Pinch-spout earthen clay bowl, smooth twisting S-curve flame with glowing core,
    warm amber cheek ember, cute hugging clay arms, cheerful smile.
    """
    M = dict(shared_mats())
    M.update({
        "clay": dict(color=srgb("#BD6038"), roughness=0.62, metallic=0.01, texture="ceramic"),
        "clay_dark": dict(color=srgb("#8C4325"), roughness=0.66, metallic=0.01),
        "flame_outer": dict(color=srgb("#FFA31A"), roughness=0.15, metallic=0.0, alpha=0.90,
                            emissive=tuple(c * 1.40 for c in srgb("#FF9800"))),
        "flame_core": dict(color=srgb("#FFF6CC"), roughness=0.10, metallic=0.0,
                           emissive=tuple(c * 2.20 for c in srgb("#FFFDE8"))),
        "ember": dict(color=srgb("#FF6200"), roughness=0.18, metallic=0.0,
                      emissive=tuple(c * 1.60 for c in srgb("#FF7500"))),
        "mouth_dark": dict(color=srgb("#72301A"), roughness=0.45, metallic=0.0),
        "lid": dict(color=srgb("#AD542E"), roughness=0.58, metallic=0.01),
    })
    parts = []
    shell = []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    # 3 stubby clay feet
    for fi, f_ang in enumerate((math.pi * 0.5, math.pi * 1.15, math.pi * 1.85)):
        foot = superellipsoid(0.052, 0.042, 0.052, e1=0.45, e2=0.45, seg=16, rings=8,
                              name=f"clay_foot_{fi}", mat="clay_dark")
        foot.move(math.cos(f_ang) * 0.150, 0.042, math.sin(f_ang) * 0.150)
        foot.tag("base")
        parts.append(foot)

    # Terracotta lamp bowl body
    bowl = lathe([(0.140, 0.035), (0.250, 0.110), (0.315, 0.220), (0.320, 0.340),
                  (0.290, 0.430), (0.270, 0.470), (0.300, 0.500)], seg=38, name="bowl", mat="clay")
    bowl.tag("hips", "spine", "chest", "base")
    add(bowl)

    # Pinched pouring spout at front rim
    spout = superellipsoid(0.065, 0.042, 0.085, e1=0.42, e2=0.42, seg=18, rings=10,
                           name="spout", mat="clay")
    spout.rotate(rx=-0.25)
    spout.move(0.0, 0.505, 0.290)
    spout.tag("head")
    add(spout, False)

    # Chubby clay arms resting on belly
    def arm(sgn):
        a = tube([(sgn * 0.280, 0.330, 0.020),
                  (sgn * 0.320, 0.240, 0.120),
                  (sgn * 0.230, 0.180, 0.200)], 0.045, radial=14, name="clay_arm", mat="clay",
                 taper=[1.0, 0.95, 0.90])
        a.tag("chest")
        return a

    parts.extend(mirrored(arm))

    # Smooth twisting S-curve flame crest
    flame_pts = [
        (0.0, 0.480, 0.0),
        (0.0, 0.580, 0.025),
        (0.035, 0.700, 0.015),
        (-0.025, 0.830, -0.010),
        (-0.010, 0.930, 0.010),
        (0.0, 0.980, 0.0),
    ]
    flame_outer = tube(flame_pts, 0.135, radial=22, name="flame_outer", mat="flame_outer",
                       taper=[0.65, 1.0, 0.92, 0.65, 0.35, 0.08])
    flame_outer.tag("flame_tip", "flame_base", "head")
    add(flame_outer, False)

    flame_inner = tube(flame_pts[:5], 0.085, radial=18, name="flame_core", mat="flame_core",
                       taper=[0.55, 1.0, 0.82, 0.45, 0.12])
    flame_inner.tag("flame_tip", "flame_base", "head")
    add(flame_inner, False)

    # Radiant amber gem on cheek
    ember = sphere(0.026, 0.026, 0.022, seg=16, rings=8, name="ember", mat="ember")
    ember.move(0.195, 0.285, 0.225)
    ember.tag("head")
    parts.append(ember)

    # Sweet open smile on clay bowl
    mouth = superellipsoid(0.045, 0.028, 0.025, e1=0.45, e2=0.45, seg=16, rings=8,
                           name="mouth", mat="mouth_dark")
    mouth.move(0.0, 0.260, 0.315)
    mouth.tag("head")
    parts.append(mouth)

    # Big warm friendly eyes
    ex, ey = 0.110, 0.335
    parts.extend(eye_pair(shell, ex, ey, 0.062, 0.068, 0.040, M,
                          lid=(1.10, 0.35, 0.80), lid_lift=1.35, proud=0.80, lid_mat="lid"))

    # Blank cream badge on lower belly
    poly = rounded_rect_poly(0.180, 0.100, 0.028, seg=6)
    parts.extend(conform_plate(shell, poly, 0.155, thickness=0.018, proud=0.013,
                               rim=1.10, rim_proud=0.008, name="badge"))
    pz = (probe_z(shell, 0.0, 0.155) or 0.29) + 0.013

    props = dict(hipY=0.15, spineY=0.25, chestY=0.35, neckY=0.44, headY=0.55,
                 legX=0.150, legY=0.06, baseY=0.04, badgeY=0.155, badgeZ=pz,
                 eyeX=ex, eyeY=ey, eyeZ=(probe_z(shell, ex, ey) or 0.29),
                 r_hips=0.32, r_spine=0.32, r_chest=0.30, r_neck=0.26, r_head=0.28,
                 r_base=0.28, r_leg=0.08, badge_size=[0.180, 0.100])

    bones = [
        mat_bone("flame_base", "head", (0.0, 0.480 - 0.55, 0.0), (0, 1, 0), 0.18, 0.20),
        mat_bone("flame_tip", "flame_base", (0.0, 0.280, 0.0), (0, 1, 0), 0.18, 0.15),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.24, "crouch_d": 0.055, "land_d": 0.070, "squash": 1.15,
              "gaze_yaw": -0.35, "chest_yaw": 0.45, "legs": False, "leg_squash": 1.0,
              "up_scale": 0.70, "breath": 1.1, "sway": 1.0, "lid_close": 1.75})

    def extras(clip, t, dur, ph):
        b = ph["breath"]
        lag = ph["lag_up"]
        happy = ph["happy"]
        flame_dance = math.sin(TAU * t * 2.5) * 0.15 + 0.10 * b
        out = {
            "flame_base": {"r": (0.08 * b - 1.2 * lag, 0.0, flame_dance)},
            "flame_tip": {"r": (0.15 * b - 2.5 * lag + 0.30 * happy, 0.0, flame_dance * 1.5)},
        }
        return out

    return Char("diya", "Diya", "The Traversal Pointer",
                "sacred terracotta oil lamp with glowing living flame crest",
                M, P, props, extras, bones,
                ["#BD6038", "#FFA31A", "#FFF6CC", "#FF6200"], 0.98).finish(parts)


# ============================================================== 4 · PATRA =====
def build_patra():
    """
    PATRA — Living manuscript parchment scroll creature. Memory Index.
    Features: Curled outer parchment sheet with visible layered paper thickness and torn edges,
    open spiral scroll coil on top, saffron silk sash ribbon with dangling tassels,
    cute hands holding miniature wooden scroll spindles.
    """
    M = dict(shared_mats())
    M.update({
        "parchment": dict(color=srgb("#E4D4B5"), roughness=0.52, metallic=0.0, texture="ceramic"),
        "parchment_dark": dict(color=srgb("#BFA782"), roughness=0.58, metallic=0.0),
        "saffron_silk": dict(color=srgb("#E08B28"), roughness=0.32, metallic=0.12),
        "wood_peg": dict(color=srgb("#62381A"), roughness=0.62, metallic=0.02),
        "rod_brass": dict(color=srgb("#D4A548"), roughness=0.28, metallic=0.82),
        "mouth_dark": dict(color=srgb("#684A28"), roughness=0.50, metallic=0.0),
        "lid": dict(color=srgb("#CFBC99"), roughness=0.48, metallic=0.0),
    })
    parts = []
    shell = []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    # Two carved wooden peg feet
    def peg_leg(sgn):
        leg = capsule(0.040, 0.130, seg=16, rings=8, name="peg_leg", mat="wood_peg")
        leg.move(sgn * 0.115, 0.065, 0.0)
        leg.tag("legL" if sgn < 0 else "legR")
        return leg

    parts.extend(mirrored(peg_leg))

    # Curled parchment cylindrical body with gentle taper
    scroll_body = lathe([(0.195, 0.090), (0.230, 0.220), (0.235, 0.450),
                         (0.230, 0.700), (0.210, 0.900), (0.190, 0.980)],
                        seg=38, name="scroll_body", mat="parchment")
    scroll_body.tag("hips", "spine", "chest", "head", "base")
    add(scroll_body)

    # Outer curled parchment flap wrapping around back and side
    flap_pts = [
        (-0.210, 0.960, 0.050),
        (-0.250, 0.750, -0.050),
        (-0.260, 0.450, -0.080),
        (-0.240, 0.180, -0.050),
        (-0.190, 0.100, 0.020),
    ]
    flap = tube(flap_pts, 0.032, radial=12, name="outer_curled_flap", mat="parchment_dark")
    flap.tag("spine", "chest")
    parts.append(flap)

    # Open curled scroll coil on top (concentric layered spiral rims)
    coil1 = torus(0.145, 0.035, seg_major=32, seg_minor=12, name="coil1", mat="parchment")
    coil1.rotate(rx=math.pi * 0.5)
    coil1.move(0.0, 0.980, 0.0)
    coil1.tag("head", "scroll_curl")

    coil2 = torus(0.085, 0.026, seg_major=24, seg_minor=10, name="coil2", mat="parchment_dark")
    coil2.rotate(rx=math.pi * 0.5)
    coil2.move(0.0, 0.995, 0.0)
    coil2.tag("head", "scroll_curl")
    parts.extend([coil1, coil2])

    # Saffron silk cord sash around waist
    sash = torus(0.236, 0.028, seg_major=34, seg_minor=12, name="sash", mat="saffron_silk")
    sash.move(0.0, 0.520, 0.0)
    sash.tag("spine")
    parts.append(sash)

    # Ribbon bow & hanging tassels
    bow = superellipsoid(0.048, 0.048, 0.038, e1=0.45, e2=0.45, seg=16, rings=8,
                         name="ribbon_knot", mat="saffron_silk")
    bow.move(-0.170, 0.520, 0.170)
    bow.tag("spine")

    tassel1 = capsule(0.014, 0.090, seg=10, rings=6, name="tassel1", mat="saffron_silk")
    tassel1.move(-0.185, 0.440, 0.180)
    tassel1.tag("spine")
    parts.extend([bow, tassel1])

    # Hands holding miniature brass scroll rods
    def scroll_hand(sgn):
        rod = capsule(0.016, 0.180, seg=14, rings=6, name="scroll_rod", mat="rod_brass")
        rod.move(sgn * 0.145, 0.530, 0.230)
        rod.tag("chest")
        hand = sphere(0.035, 0.035, 0.035, seg=14, rings=8, name="hand", mat="parchment")
        hand.move(sgn * 0.145, 0.530, 0.220)
        hand.tag("chest")
        return [rod, hand]

    parts.extend(mirrored(scroll_hand))

    # Friendly cartoon smile
    mouth = superellipsoid(0.042, 0.025, 0.022, e1=0.45, e2=0.45, seg=16, rings=8,
                           name="mouth", mat="mouth_dark")
    mouth.move(0.0, 0.700, 0.230)
    mouth.tag("head")
    parts.append(mouth)

    # Big open cartoon eyes
    ex, ey = 0.100, 0.790
    parts.extend(eye_pair(shell, ex, ey, 0.062, 0.070, 0.038, M,
                          lid=(1.10, 0.35, 0.80), lid_lift=1.35, proud=0.80, lid_mat="lid"))

    # Blank cream badge on lower body
    poly = rounded_rect_poly(0.185, 0.115, 0.030, seg=6)
    parts.extend(conform_plate(shell, poly, 0.260, thickness=0.018, proud=0.013,
                               rim=1.10, rim_proud=0.008, name="badge"))
    pz = (probe_z(shell, 0.0, 0.260) or 0.23) + 0.013

    props = dict(hipY=0.18, spineY=0.38, chestY=0.58, neckY=0.70, headY=0.82,
                 legX=0.115, legY=0.08, baseY=0.06, badgeY=0.260, badgeZ=pz,
                 eyeX=ex, eyeY=ey, eyeZ=(probe_z(shell, ex, ey) or 0.22),
                 r_hips=0.26, r_spine=0.26, r_chest=0.25, r_neck=0.23, r_head=0.25,
                 r_base=0.22, r_leg=0.08, badge_size=[0.185, 0.115])

    bones = [
        mat_bone("scroll_curl", "head", (0.0, 0.980 - 0.82, 0.0), (0, 1, 0), 0.14, 0.16),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.26, "crouch_d": 0.065, "land_d": 0.080, "squash": 0.85,
              "gaze_yaw": -0.32, "chest_yaw": 0.40, "leg_squash": 0.70, "leg_len": 0.14,
              "up_scale": 1.0, "breath": 0.95, "sway": 0.85, "lid_close": 1.60})

    def extras(clip, t, dur, ph):
        b = ph["breath"]
        lag = ph["lag_up"]
        happy = ph["happy"]
        out = {
            "scroll_curl": {"r": (0.06 * b - 1.5 * lag + 0.20 * happy, 0.0, 0.0)},
        }
        return out

    return Char("patra", "Patra", "The Memory Index",
                "living parchment manuscript scroll with saffron sash and wooden pegs",
                M, P, props, extras, bones,
                ["#E4D4B5", "#E08B28", "#62381A", "#D4A548"], 1.18).finish(parts)


# ============================================================== 5 · KUMBHA ====
def build_kumbha():
    """
    KUMBHA — Golden Kalasha pot with mango leaves & coconut. Boundary buffer.
    Features: Ornate traditional Kalasha pot with engraved relief collar, 5 pointed
    lanceolate mango leaves with central fold rib, pointed fibrous brown coconut with husk tuft,
    warm sweet smile, high-polish sacred brass.
    """
    M = dict(shared_mats())
    M.update({
        "brass": dict(color=srgb("#E4B43C"), roughness=0.18, metallic=0.92),
        "brass_dark": dict(color=srgb("#9C6E18"), roughness=0.25, metallic=0.90),
        "mango_leaf": dict(color=srgb("#22883E"), roughness=0.38, metallic=0.03),
        "coconut": dict(color=srgb("#643D1E"), roughness=0.74, metallic=0.02, texture="stone"),
        "mouth_dark": dict(color=srgb("#604010"), roughness=0.35, metallic=0.30),
        "lid": dict(color=srgb("#CCA030"), roughness=0.22, metallic=0.85),
    })
    parts = []
    shell = []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    # Two short golden feet
    def brass_foot(sgn):
        foot = superellipsoid(0.070, 0.048, 0.085, e1=0.42, e2=0.42, seg=20, rings=10,
                              name="brass_foot", mat="brass")
        foot.move(sgn * 0.140, 0.048, 0.0)
        foot.tag("legL" if sgn < 0 else "legR")
        return foot

    parts.extend(mirrored(brass_foot))

    # Lathed ornate Kalasha pot belly
    pot = lathe([(0.140, 0.045), (0.240, 0.110), (0.330, 0.230), (0.355, 0.360),
                 (0.320, 0.500), (0.245, 0.580), (0.195, 0.620), (0.245, 0.660)],
                seg=42, name="kalasha_pot", mat="brass")
    pot.tag("hips", "spine", "chest", "head", "base")
    add(pot)

    # Flared neck rim with engraved ornamental relief ring
    rim = torus(0.225, 0.024, seg_major=38, seg_minor=12, name="neck_rim", mat="brass_dark")
    rim.move(0.0, 0.640, 0.0)
    rim.tag("head")
    parts.append(rim)

    # Short golden arms
    def arm(sgn):
        a = tube([(sgn * 0.325, 0.440, 0.0),
                  (sgn * 0.365, 0.330, 0.06),
                  (sgn * 0.290, 0.250, 0.12)], 0.048, radial=14, name="brass_arm", mat="brass",
                 taper=[1.0, 0.95, 0.90])
        a.tag("chest")
        return a

    parts.extend(mirrored(arm))

    # Pointed textured fibrous coconut nestled in center with tuft
    coconut = superellipsoid(0.130, 0.190, 0.130, e1=0.50, e2=0.50, seg=26, rings=18,
                             name="coconut", mat="coconut")
    coconut.move(0.0, 0.810, 0.0)
    coconut.tag("head", "coconut_top")
    add(coconut, False)

    tuft = cone = tube([(0.0, 0.980, 0.0), (0.0, 1.050, 0.0)], 0.035, radial=10,
                       name="tuft", mat="coconut", taper=[1.0, 0.15])
    tuft.tag("head", "coconut_top")
    parts.append(tuft)

    # 5 pointed lanceolate mango leaves cupping the coconut
    N_LEAVES = 5
    for li in range(N_LEAVES):
        l_ang = li * (TAU / N_LEAVES)
        leaf = superellipsoid(0.070, 0.200, 0.022, e1=0.45, e2=0.45, seg=18, rings=10,
                              name=f"mango_leaf_{li}", mat="mango_leaf")
        leaf.rotate(rx=0.60)
        leaf.rotate(ry=l_ang)
        lx = math.sin(l_ang) * 0.195
        lz = math.cos(l_ang) * 0.195
        leaf.move(lx, 0.740, lz)
        leaf.tag("head", "leaf_crown")
        parts.append(leaf)

    # Sweet open smile on brass belly
    mouth = superellipsoid(0.046, 0.028, 0.024, e1=0.45, e2=0.45, seg=16, rings=8,
                           name="mouth", mat="mouth_dark")
    mouth.move(0.0, 0.315, 0.355)
    mouth.tag("head")
    parts.append(mouth)

    # Big open cheerful eyes
    ex, ey = 0.115, 0.395
    parts.extend(eye_pair(shell, ex, ey, 0.065, 0.072, 0.040, M,
                          lid=(1.10, 0.35, 0.80), lid_lift=1.35, proud=0.80, lid_mat="lid"))

    # Blank cream badge on lower pot belly
    poly = rounded_rect_poly(0.180, 0.105, 0.028, seg=6)
    parts.extend(conform_plate(shell, poly, 0.200, thickness=0.018, proud=0.013,
                               rim=1.10, rim_proud=0.008, name="badge"))
    pz = (probe_z(shell, 0.0, 0.200) or 0.33) + 0.013

    props = dict(hipY=0.18, spineY=0.30, chestY=0.42, neckY=0.54, headY=0.64,
                 legX=0.140, legY=0.08, baseY=0.05, badgeY=0.200, badgeZ=pz,
                 eyeX=ex, eyeY=ey, eyeZ=(probe_z(shell, ex, ey) or 0.32),
                 r_hips=0.34, r_spine=0.34, r_chest=0.32, r_neck=0.26, r_head=0.28,
                 r_base=0.30, r_leg=0.10, badge_size=[0.180, 0.105])

    bones = [
        mat_bone("coconut_top", "head", (0.0, 0.810 - 0.64, 0.0), (0, 1, 0), 0.18, 0.20),
        mat_bone("leaf_crown", "head", (0.0, 0.740 - 0.64, 0.0), (0, 1, 0), 0.14, 0.25),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.25, "crouch_d": 0.060, "land_d": 0.075, "squash": 0.85,
              "gaze_yaw": -0.32, "chest_yaw": 0.45, "leg_squash": 0.75, "leg_len": 0.12,
              "up_scale": 1.0, "breath": 0.95, "sway": 0.80, "lid_close": 1.65})

    def extras(clip, t, dur, ph):
        b = ph["breath"]
        lag = ph["lag_up"]
        happy = ph["happy"]
        out = {
            "coconut_top": {"r": (0.06 * b - 1.2 * lag + 0.20 * happy, 0.0, 0.0)},
            "leaf_crown": {"r": (0.08 * b - 1.6 * lag, 0.0, 0.10 * ph["shake"])},
        }
        return out

    return Char("kumbha", "Kumbha", "The Boundary Buffer",
                "sacred golden Kalasha brass vessel crowned with mango leaves and coconut",
                M, P, props, extras, bones,
                ["#E4B43C", "#9C6E18", "#22883E", "#643D1E"], 1.05).finish(parts)


# ============================================================== 6 · GRANTHA ===
def build_grantha():
    """
    GRANTHA — Ancient Vedic Palm-Leaf Manuscript creature. State & Swap Counter.
    Features: Rectangular bound palm-leaf manuscript stack between carved teak wood covers,
    braided saffron silk cord with twin brass jingle bells, ornate peacock feather quill pen,
    carved wooden feet, blank cream title badge plate.
    """
    M = dict(shared_mats())
    M.update({
        "teak_wood": dict(color=srgb("#5A2E14"), roughness=0.55, metallic=0.02, texture="ceramic"),
        "palm_leaf": dict(color=srgb("#E2CEAB"), roughness=0.68, metallic=0.0),
        "cord_red": dict(color=srgb("#BA2B25"), roughness=0.38, metallic=0.08),
        "bell_brass": dict(color=srgb("#DDAA33"), roughness=0.25, metallic=0.88),
        "quill_teal": dict(color=srgb("#1B6878"), roughness=0.35, metallic=0.08),
        "quill_gold": dict(color=srgb("#D4A548"), roughness=0.28, metallic=0.65),
        "quill_shaft": dict(color=srgb("#FFF8E7"), roughness=0.22, metallic=0.0),
        "mouth_dark": dict(color=srgb("#4A220C"), roughness=0.45, metallic=0.0),
        "lid": dict(color=srgb("#5A2E14"), roughness=0.55, metallic=0.02),
    })
    parts = []
    shell = []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    # Two carved wooden feet
    def wood_foot(sgn):
        f = superellipsoid(0.065, 0.045, 0.090, e1=0.42, e2=0.42, seg=18, rings=8,
                           name="wood_foot", mat="teak_wood")
        f.move(sgn * 0.125, 0.045, 0.0)
        f.tag("legL" if sgn < 0 else "legR")
        return f

    parts.extend(mirrored(wood_foot))

    # Bottom carved wooden manuscript cover
    bottom_cover = superellipsoid(0.240, 0.025, 0.170, e1=0.28, e2=0.28, seg=24, rings=8,
                                  name="bottom_cover", mat="teak_wood")
    bottom_cover.move(0.0, 0.105, 0.0)
    bottom_cover.tag("base", "hips")
    add(bottom_cover)

    # Thick stack of rectangular palm-leaf / birch-bark folio leaves
    leaf_stack = superellipsoid(0.225, 0.320, 0.155, e1=0.25, e2=0.25, seg=26, rings=16,
                                name="leaf_stack", mat="palm_leaf")
    leaf_stack.move(0.0, 0.445, 0.0)
    leaf_stack.tag("hips", "spine", "chest", "head")
    add(leaf_stack)

    # Top carved wooden manuscript cover
    top_cover = superellipsoid(0.240, 0.025, 0.170, e1=0.28, e2=0.28, seg=24, rings=8,
                               name="top_cover", mat="teak_wood")
    top_cover.move(0.0, 0.785, 0.0)
    top_cover.tag("head", "cover_top")
    add(top_cover)

    # Braided red silk cord bound vertically around manuscript
    cord = torus(0.180, 0.016, seg_major=32, seg_minor=8, name="binding_cord", mat="cord_red")
    cord.rotate(rx=math.pi * 0.5)
    cord.move(-0.080, 0.450, 0.0)
    cord.tag("spine")
    parts.append(cord)

    # Traditional cord knot and dangling bells
    knot = sphere(0.030, 0.030, 0.025, seg=12, rings=8, name="cord_knot", mat="cord_red")
    knot.move(-0.080, 0.810, 0.120)
    knot.tag("head", "cord_tassel")
    parts.append(knot)

    def tassel_bell(sgn):
        stem = capsule(0.008, 0.075, seg=8, rings=4, name="bell_stem", mat="cord_red")
        stem.move(-0.080 + sgn * 0.025, 0.740, 0.135)
        stem.tag("head", "cord_tassel")
        bell = sphere(0.022, 0.022, 0.022, seg=12, rings=8, name="brass_bell", mat="bell_brass")
        bell.move(-0.080 + sgn * 0.025, 0.700, 0.135)
        bell.tag("head", "cord_tassel")
        return [stem, bell]

    parts.extend(mirrored(tassel_bell))

    # Ornate peacock feather quill pen tucked into the top binding
    quill_shaft = capsule(0.009, 0.380, seg=10, rings=4, name="quill_shaft", mat="quill_shaft")
    quill_shaft.rotate(rz=-0.35, rx=0.15)
    quill_shaft.move(0.120, 0.950, -0.040)
    quill_shaft.tag("head", "quill_pen")
    parts.append(quill_shaft)

    # Peacock feather vane
    quill_vane = superellipsoid(0.055, 0.120, 0.012, e1=0.45, e2=0.45, seg=16, rings=8,
                                name="quill_vane", mat="quill_teal")
    quill_vane.rotate(rz=-0.35, rx=0.15)
    quill_vane.move(0.180, 1.050, -0.050)
    quill_vane.tag("head", "quill_pen")
    parts.append(quill_vane)

    quill_eye = sphere(0.024, 0.035, 0.015, seg=12, rings=6, name="quill_eye", mat="quill_gold")
    quill_eye.rotate(rz=-0.35, rx=0.15)
    quill_eye.move(0.185, 1.060, -0.045)
    quill_eye.tag("head", "quill_pen")
    parts.append(quill_eye)

    # Cute short book-holding arms
    def book_arm(sgn):
        a = tube([(sgn * 0.220, 0.420, 0.020),
                  (sgn * 0.240, 0.350, 0.120),
                  (sgn * 0.160, 0.330, 0.160)], 0.040, radial=12, name="book_arm", mat="teak_wood",
                 taper=[1.0, 0.92, 0.85])
        a.tag("chest")
        paw = sphere(0.038, 0.035, 0.038, seg=12, rings=8, name="book_paw", mat="teak_wood")
        paw.move(sgn * 0.160, 0.330, 0.160)
        paw.tag("chest")
        return [a, paw]

    parts.extend(mirrored(book_arm))

    # Open friendly mouth
    mouth = superellipsoid(0.040, 0.024, 0.020, e1=0.45, e2=0.45, seg=14, rings=6,
                           name="mouth", mat="mouth_dark")
    mouth.move(0.0, 0.490, 0.160)
    mouth.tag("head")
    parts.append(mouth)

    # Big open expressive cartoon eyes
    ex, ey = 0.095, 0.585
    parts.extend(eye_pair(shell, ex, ey, 0.055, 0.065, 0.035, M,
                          lid=(1.10, 0.35, 0.80), lid_lift=1.35, proud=0.80, lid_mat="lid"))

    # Blank cream badge plate on lower stack
    poly = rounded_rect_poly(0.170, 0.100, 0.025, seg=6)
    parts.extend(conform_plate(shell, poly, 0.260, thickness=0.016, proud=0.012,
                               rim=1.10, rim_proud=0.008, name="badge"))
    pz = (probe_z(shell, 0.0, 0.260) or 0.16) + 0.012

    props = dict(hipY=0.18, spineY=0.35, chestY=0.52, neckY=0.64, headY=0.72,
                 legX=0.125, legY=0.06, baseY=0.04, badgeY=0.260, badgeZ=pz,
                 eyeX=ex, eyeY=ey, eyeZ=(probe_z(shell, ex, ey) or 0.16),
                 r_hips=0.24, r_spine=0.24, r_chest=0.24, r_neck=0.22, r_head=0.24,
                 r_base=0.20, r_leg=0.08, badge_size=[0.170, 0.100])

    bones = [
        mat_bone("cover_top", "head", (0.0, 0.785 - 0.72, 0.0), (0, 1, 0), 0.12, 0.18),
        mat_bone("cord_tassel", "head", (-0.080, 0.700 - 0.72, 0.135), (0, -1, 0), 0.10, 0.12),
        mat_bone("quill_pen", "head", (0.120, 0.950 - 0.72, -0.040), (0.2, 0.9, -0.2), 0.25, 0.14),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.27, "crouch_d": 0.065, "land_d": 0.080, "squash": 0.88,
              "gaze_yaw": -0.32, "chest_yaw": 0.38, "leg_squash": 0.72, "leg_len": 0.14,
              "up_scale": 1.0, "breath": 0.95, "sway": 0.85, "lid_close": 1.60})

    def extras(clip, t, dur, ph):
        b = ph["breath"]
        lag = ph["lag_up"]
        happy = ph["happy"]
        imp = ph["impact"]
        clap = 0.05 * imp - 0.08 * lag + 0.10 * happy
        out = {
            "cover_top": {"r": (clap, 0.0, 0.0)},
            "cord_tassel": {"r": (0.08 * b - 2.0 * lag + 0.30 * happy, 0.0, 0.15 * ph["shake"])},
            "quill_pen": {"r": (0.12 * b - 2.5 * lag + 0.40 * happy, 0.0, -0.10 * lag)},
        }
        return out

    return Char("grantha", "Grantha", "The Memory Logger",
                "Vedic palm-leaf manuscript mascot with carved teak covers, red cord and peacock quill",
                M, P, props, extras, bones,
                ["#5A2E14", "#E2CEAB", "#BA2B25", "#1B6878"], 1.15).finish(parts)


# ============================================================== 7 · DHANESH ===
def build_dhanesh():
    """
    DHANESH — Great Indian Hornbill mascot. Precision Comparator Pointer.
    Features: Glossy jet-black body, bright white underbelly and neck ruffle,
    magnificent curved golden-yellow bill with prominent arched casque helmet on top,
    expressive ruby-rimmed eyes, fanned black & white banded tail, folded wings.
    """
    M = dict(shared_mats())
    M.update({
        "feather_black": dict(color=srgb("#1C1D24"), roughness=0.45, metallic=0.04),
        "feather_white": dict(color=srgb("#F4F2EC"), roughness=0.50, metallic=0.01),
        "casque_gold": dict(color=srgb("#E59E24"), roughness=0.28, metallic=0.35),
        "bill_ivory": dict(color=srgb("#F0D8A8"), roughness=0.32, metallic=0.08),
        "bill_accent": dict(color=srgb("#962818"), roughness=0.35, metallic=0.10),
        "mouth_dark": dict(color=srgb("#3A1810"), roughness=0.45, metallic=0.0),
        "lid": dict(color=srgb("#1C1D24"), roughness=0.45, metallic=0.04),
    })
    parts = []
    shell = []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    # Bird legs with 3 front toes and 1 back toe
    def bird_leg(sgn):
        leg = capsule(0.028, 0.220, seg=16, rings=8, name="leg_col", mat="casque_gold")
        leg.move(sgn * 0.120, 0.110, 0.0)
        leg.tag("legL" if sgn < 0 else "legR")

        toes = []
        for fi, f_ang in enumerate((-0.40, 0.0, 0.40)):
            toe = capsule(0.014, 0.090, seg=12, rings=6, name=f"toe_{fi}", mat="casque_gold")
            toe.rotate(ry=f_ang)
            toe.move(sgn * 0.120 + math.sin(f_ang) * 0.045, 0.014, math.cos(f_ang) * 0.045)
            toe.tag("legL" if sgn < 0 else "legR")
            toes.append(toe)
        return [leg] + toes

    parts.extend(mirrored(bird_leg))

    # Plump upright bird body (lathe)
    body = lathe([(0.120, 0.180), (0.240, 0.280), (0.295, 0.440), (0.280, 0.620),
                  (0.210, 0.780), (0.160, 0.880)], seg=32, name="hornbill_body", mat="feather_black")
    body.tag("hips", "spine", "chest", "base")
    add(body)

    # White chest bib / underbelly
    bib = superellipsoid(0.180, 0.240, 0.090, e1=0.45, e2=0.45, seg=20, rings=10,
                         name="white_bib", mat="feather_white")
    bib.move(0.0, 0.480, 0.210)
    bib.tag("spine", "chest")
    parts.append(bib)

    # Sleek rounded head and neck
    head = sphere(0.200, 0.220, 0.210, seg=28, rings=18, name="hornbill_head", mat="feather_black")
    head.move(0.0, 0.980, 0.040)
    head.tag("head", "neck")
    add(head)

    # White neck ruff collar
    ruff = torus(0.170, 0.035, seg_major=28, seg_minor=10, name="neck_ruff", mat="feather_white")
    ruff.move(0.0, 0.860, 0.020)
    ruff.tag("neck")
    parts.append(ruff)

    # Massive curved Hornbill Bill (upper + lower mandible)
    bill_upper_pts = [
        (0.0, 0.990, 0.180),
        (0.0, 0.960, 0.360),
        (0.0, 0.900, 0.540),
        (0.0, 0.800, 0.660),
    ]
    bill_upper = tube(bill_upper_pts, 0.065, radial=16, name="bill_upper", mat="bill_ivory",
                      taper=[1.0, 0.85, 0.60, 0.20])
    bill_upper.tag("head", "beak_tip")
    add(bill_upper, False)

    bill_lower_pts = [
        (0.0, 0.930, 0.180),
        (0.0, 0.910, 0.340),
        (0.0, 0.860, 0.490),
        (0.0, 0.790, 0.630),
    ]
    bill_lower = tube(bill_lower_pts, 0.050, radial=14, name="bill_lower", mat="bill_accent",
                      taper=[1.0, 0.80, 0.55, 0.18])
    bill_lower.tag("head", "beak_tip")
    parts.append(bill_lower)

    # Arched Golden Casque Helmet sitting proudly on top of head & bill
    casque_pts = [
        (0.0, 1.060, -0.040),
        (0.0, 1.140, 0.120),
        (0.0, 1.150, 0.320),
        (0.0, 1.080, 0.480),
        (0.0, 1.020, 0.540),
    ]
    casque = tube(casque_pts, 0.075, radial=16, name="casque_horn", mat="casque_gold",
                  taper=[0.55, 1.0, 0.95, 0.60, 0.15])
    casque.tag("head", "casque_horn")
    add(casque, False)

    # Folded wings on sides
    def wing(sgn):
        w = superellipsoid(0.055, 0.280, 0.180, e1=0.48, e2=0.48, seg=18, rings=10,
                           name="wing", mat="feather_black")
        w.rotate(rx=0.25, rz=-sgn * 0.12)
        w.move(sgn * 0.280, 0.520, -0.040)
        w.tag("wingL" if sgn < 0 else "wingR", "chest")
        tip = superellipsoid(0.035, 0.100, 0.080, e1=0.45, e2=0.45, seg=12, rings=8,
                             name="wing_tip", mat="feather_white")
        tip.rotate(rx=0.30, rz=-sgn * 0.12)
        tip.move(sgn * 0.290, 0.320, -0.120)
        tip.tag("wingL" if sgn < 0 else "wingR", "chest")
        return [w, tip]

    parts.extend(mirrored(wing))

    # Long banded tail extending downward at back
    tail = superellipsoid(0.120, 0.320, 0.035, e1=0.45, e2=0.45, seg=18, rings=10,
                          name="tail", mat="feather_black")
    tail.rotate(rx=-0.25)
    tail.move(0.0, 0.280, -0.250)
    tail.tag("hips", "tail_long")
    parts.append(tail)

    tail_band = superellipsoid(0.125, 0.090, 0.038, e1=0.45, e2=0.45, seg=18, rings=8,
                               name="tail_band", mat="feather_white")
    tail_band.rotate(rx=-0.25)
    tail_band.move(0.0, 0.240, -0.270)
    tail_band.tag("hips", "tail_long")
    parts.append(tail_band)

    # Big open expressive mascot eyes
    ex, ey = 0.115, 0.985
    parts.extend(eye_pair(shell, ex, ey, 0.055, 0.062, 0.035, M,
                          lid=(1.10, 0.35, 0.80), lid_lift=1.35, proud=0.80, lid_mat="lid"))

    # Blank cream badge on lower chest bib
    poly = rounded_rect_poly(0.170, 0.100, 0.026, seg=6)
    parts.extend(conform_plate(shell, poly, 0.350, thickness=0.016, proud=0.012,
                               rim=1.10, rim_proud=0.008, name="badge"))
    pz = (probe_z(shell, 0.0, 0.350) or 0.27) + 0.012

    props = dict(hipY=0.22, spineY=0.44, chestY=0.66, neckY=0.84, headY=0.98,
                 legX=0.120, legY=0.08, baseY=0.04, badgeY=0.350, badgeZ=pz,
                 eyeX=ex, eyeY=ey, eyeZ=(probe_z(shell, ex, ey) or 0.18),
                 r_hips=0.28, r_spine=0.28, r_chest=0.26, r_neck=0.20, r_head=0.22,
                 r_base=0.18, r_leg=0.08, badge_size=[0.170, 0.100])

    bones = [
        mat_bone("casque_horn", "head", (0.0, 1.150 - 0.98, 0.220), (0, 0.3, 0.9), 0.25, 0.18),
        mat_bone("beak_tip", "head", (0.0, 0.850 - 0.98, 0.550), (0, -0.2, 0.9), 0.20, 0.14),
        mat_bone("wingL", "chest", (-0.280, 0.520 - 0.66, -0.040), (-0.4, -0.8, -0.2), 0.26, 0.16),
        mat_bone("wingR", "chest", (0.280, 0.520 - 0.66, -0.040), (0.4, -0.8, -0.2), 0.26, 0.16),
        mat_bone("tail_long", "hips", (0.0, 0.280 - 0.22, -0.250), (0, -0.9, -0.3), 0.28, 0.16),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.34, "crouch_d": 0.075, "land_d": 0.085, "squash": 0.92,
              "gaze_yaw": -0.40, "chest_yaw": 0.38, "leg_squash": 0.65, "leg_len": 0.18,
              "up_scale": 1.0, "breath": 1.10, "sway": 1.05, "lid_close": 1.60})

    def extras(clip, t, dur, ph):
        b = ph["breath"]
        lag = ph["lag_up"]
        happy = ph["happy"]
        flap = 0.25 * ph.get("air", 0.0) + 0.20 * happy
        dip = 0.12 * b - 1.8 * lag + 0.30 * happy
        out = {
            "casque_horn": {"r": (dip * 0.8, 0.0, 0.0)},
            "beak_tip": {"r": (dip, 0.0, 0.0)},
            "wingL": {"r": (0.0, 0.0, -flap)},
            "wingR": {"r": (0.0, 0.0, flap)},
            "tail_long": {"r": (-0.15 * lag + 0.20 * happy, 0.0, 0.10 * ph["shake"])},
        }
        return out

    return Char("dhanesh", "Dhanesh", "The Precision Comparator",
                "Great Indian Hornbill mascot with golden arched casque helmet, ivory bill, black-and-white plumage",
                M, P, props, extras, bones,
                ["#1C1D24", "#F4F2EC", "#E59E24", "#F0D8A8"], 1.38).finish(parts)


# ============================================================== 8 · SALYA =====
def build_salya():
    """
    SALYA — Indian Scaled Pangolin mascot. Armored Ball Spring.
    Features: Rounded biped stance, golden-amber overlapping keratin scales / shingle plates,
    soft cream underbelly, tapered snout with curious twitching nose, curled armored tail
    that uncoils to spring-bounce, blank cream badge on chest armor.
    """
    M = dict(shared_mats())
    M.update({
        "scale_amber": dict(color=srgb("#B87E34"), roughness=0.36, metallic=0.20),
        "scale_edge": dict(color=srgb("#DEAA55"), roughness=0.32, metallic=0.25),
        "skin_belly": dict(color=srgb("#E2CEAB"), roughness=0.55, metallic=0.01),
        "claw_dark": dict(color=srgb("#4A321E"), roughness=0.40, metallic=0.10),
        "nose_pink": dict(color=srgb("#D47265"), roughness=0.48, metallic=0.0),
        "mouth_dark": dict(color=srgb("#553518"), roughness=0.45, metallic=0.0),
        "lid": dict(color=srgb("#B87E34"), roughness=0.38, metallic=0.18),
    })
    parts = []
    shell = []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    # Chubby biped feet with digging claws
    def pangolin_foot(sgn):
        f = superellipsoid(0.080, 0.048, 0.115, e1=0.42, e2=0.42, seg=18, rings=8,
                           name="pangolin_foot", mat="scale_amber")
        f.move(sgn * 0.140, 0.048, 0.02)
        f.tag("legL" if sgn < 0 else "legR")

        toes = []
        for ti, tang in enumerate((-0.25, 0.0, 0.25)):
            toe = capsule(0.015, 0.055, seg=10, rings=4, name=f"claw_{ti}", mat="claw_dark")
            toe.rotate(rx=0.30)
            toe.move(sgn * (0.140 + tang * 0.050), 0.025, 0.125)
            toe.tag("legL" if sgn < 0 else "legR")
            toes.append(toe)
        return [f] + toes

    parts.extend(mirrored(pangolin_foot))

    # Chubby pear-shaped torso
    body = lathe([(0.140, 0.140), (0.240, 0.240), (0.310, 0.380), (0.315, 0.540),
                  (0.260, 0.680), (0.190, 0.780)], seg=32, name="pangolin_body", mat="skin_belly")
    body.tag("hips", "spine", "chest", "base")
    add(body)

    # Shingled dorsal armor plates covering back and crown (tiered pinecone scales)
    for si, sy, ssz, srx in [
        (0, 0.780, 0.240, 0.35),
        (1, 0.680, 0.290, 0.25),
        (2, 0.540, 0.320, 0.10),
        (3, 0.380, 0.310, -0.05),
        (4, 0.240, 0.270, -0.20),
    ]:
        scale_plate = superellipsoid(0.240 - si * 0.015, 0.090, 0.120, e1=0.38, e2=0.38,
                                     seg=20, rings=8, name=f"dorsal_scale_{si}", mat="scale_amber")
        scale_plate.rotate(rx=srx)
        scale_plate.move(0.0, sy, -0.080 - si * 0.030)
        scale_plate.tag("spine" if si < 3 else "hips")
        parts.append(scale_plate)

        # Scale golden rim highlight
        scale_rim = torus(0.210 - si * 0.015, 0.014, seg_major=24, seg_minor=8,
                          name=f"scale_rim_{si}", mat="scale_edge")
        scale_rim.rotate(rx=srx + 0.2)
        scale_rim.move(0.0, sy - 0.02, -0.090 - si * 0.030)
        scale_rim.tag("spine" if si < 3 else "hips")
        parts.append(scale_rim)

    # Scaled helmet hood over head
    hood = superellipsoid(0.220, 0.140, 0.190, e1=0.40, e2=0.40, seg=22, rings=10,
                          name="scale_hood", mat="scale_amber")
    hood.rotate(rx=0.20)
    hood.move(0.0, 0.900, -0.030)
    hood.tag("head", "scale_hood")
    add(hood)

    # Friendly snout and head
    snout_pts = [
        (0.0, 0.860, 0.120),
        (0.0, 0.840, 0.250),
        (0.0, 0.810, 0.380),
        (0.0, 0.780, 0.450),
    ]
    snout = tube(snout_pts, 0.090, radial=16, name="snout", mat="skin_belly",
                 taper=[1.0, 0.85, 0.60, 0.35])
    snout.tag("head")
    add(snout, False)

    # Cute rounded nose button
    nose = sphere(0.032, 0.026, 0.026, seg=12, rings=8, name="nose", mat="nose_pink")
    nose.move(0.0, 0.780, 0.465)
    nose.tag("head")
    parts.append(nose)

    # Muscular curled armored tail at back (key spring physics anatomy!)
    tail_pts = [
        (0.0, 0.220, -0.160),
        (0.0, 0.140, -0.320),
        (0.0, 0.180, -0.460),
        (0.0, 0.320, -0.480),
        (0.0, 0.420, -0.360),
    ]
    tail = tube(tail_pts, 0.100, radial=16, name="tail_curl", mat="scale_amber",
                taper=[1.0, 0.85, 0.70, 0.50, 0.25])
    tail.tag("hips", "tail_curl.01", "tail_curl.02")
    parts.append(tail)

    # Short curved front paws
    def pangolin_arm(sgn):
        a = tube([(sgn * 0.220, 0.540, 0.050),
                  (sgn * 0.250, 0.440, 0.160),
                  (sgn * 0.150, 0.380, 0.220)], 0.045, radial=12, name="pangolin_arm", mat="scale_amber",
                 taper=[1.0, 0.90, 0.80])
        a.tag("armL" if sgn < 0 else "armR", "chest")
        paw = sphere(0.040, 0.035, 0.040, seg=12, rings=8, name="paw", mat="skin_belly")
        paw.move(sgn * 0.150, 0.380, 0.220)
        paw.tag("armL" if sgn < 0 else "armR", "chest")
        return [a, paw]

    parts.extend(mirrored(pangolin_arm))

    # Sweet open mouth
    mouth = superellipsoid(0.038, 0.022, 0.020, e1=0.45, e2=0.45, seg=14, rings=6,
                           name="mouth", mat="mouth_dark")
    mouth.move(0.0, 0.740, 0.360)
    mouth.tag("head")
    parts.append(mouth)

    # Big open expressive mascot eyes
    ex, ey = 0.105, 0.850
    parts.extend(eye_pair(shell, ex, ey, 0.055, 0.062, 0.035, M,
                          lid=(1.10, 0.35, 0.80), lid_lift=1.35, proud=0.80, lid_mat="lid"))

    # Blank cream badge on lower chest
    poly = rounded_rect_poly(0.165, 0.095, 0.025, seg=6)
    parts.extend(conform_plate(shell, poly, 0.250, thickness=0.016, proud=0.012,
                               rim=1.10, rim_proud=0.008, name="badge"))
    pz = (probe_z(shell, 0.0, 0.250) or 0.28) + 0.012

    props = dict(hipY=0.18, spineY=0.34, chestY=0.52, neckY=0.68, headY=0.82,
                 legX=0.140, legY=0.06, baseY=0.04, badgeY=0.250, badgeZ=pz,
                 eyeX=ex, eyeY=ey, eyeZ=(probe_z(shell, ex, ey) or 0.25),
                 r_hips=0.30, r_spine=0.30, r_chest=0.28, r_neck=0.22, r_head=0.24,
                 r_base=0.22, r_leg=0.08, badge_size=[0.165, 0.095])

    bones = [
        mat_bone("tail_curl.01", "hips", (0.0, 0.180 - 0.18, -0.320), (0, -0.3, -0.9), 0.20, 0.18),
        mat_bone("tail_curl.02", "tail_curl.01", (0.0, 0.280 - 0.18, -0.160), (0, 0.8, 0.2), 0.18, 0.14),
        mat_bone("scale_hood", "head", (0.0, 0.900 - 0.82, -0.030), (0, 0.8, -0.4), 0.18, 0.18),
        mat_bone("armL", "chest", (-0.220, 0.540 - 0.52, 0.050), (-0.4, -0.8, 0.4), 0.20, 0.12),
        mat_bone("armR", "chest", (0.220, 0.540 - 0.52, 0.050), (0.4, -0.8, 0.4), 0.20, 0.12),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.30, "crouch_d": 0.085, "land_d": 0.100, "squash": 1.10,
              "gaze_yaw": -0.35, "chest_yaw": 0.40, "leg_squash": 0.60, "leg_len": 0.14,
              "up_scale": 1.0, "breath": 1.0, "sway": 0.90, "lid_close": 1.60})

    def extras(clip, t, dur, ph):
        b = ph["breath"]
        lag = ph["lag_up"]
        happy = ph["happy"]
        air = ph.get("air", 0.0)
        crouch = max(0.0, -ph.get("up", 0.0) / 0.10)
        # Tight ball curl during jump and crouch
        tail_spring = 0.50 * crouch - 0.80 * air + 0.30 * happy
        out = {
            "tail_curl.01": {"r": (tail_spring, 0.0, 0.0)},
            "tail_curl.02": {"r": (tail_spring * 1.3, 0.0, 0.0)},
            "scale_hood": {"r": (0.08 * b - 1.2 * lag, 0.0, 0.0)},
            "armL": {"r": (0.2 * air - 0.1 * happy, 0.0, -0.15 * lag)},
            "armR": {"r": (0.2 * air - 0.1 * happy, 0.0, 0.15 * lag)},
        }
        return out

    return Char("salya", "Salya", "The Invariance Defense",
                "Indian Scaled Pangolin mascot with amber keratin pinecone armor and spring curl tail",
                M, P, props, extras, bones,
                ["#B87E34", "#DEAA55", "#E2CEAB", "#D47265"], 0.92).finish(parts)


BUILDERS = {
    "gaja": build_gaja,
    "mayur": build_mayur,
    "diya": build_diya,
    "patra": build_patra,
    "kumbha": build_kumbha,
    "grantha": build_grantha,
    "dhanesh": build_dhanesh,
    "salya": build_salya,
}
