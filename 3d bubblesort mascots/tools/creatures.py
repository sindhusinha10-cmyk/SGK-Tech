"""
creatures — the five Bubble-Sort Mascots (Indian Culture & Heritage Set).

Characters:
  1. Gaja   — Bipedal baby elephant mascot (Heavyweight Anchor)
  2. Mayur  — Peacock chick with tail feather fan (Pattern Comparator)
  3. Diya   — Terracotta oil lamp with living flame (Active Traversal Pointer)
  4. Patra  — Living parchment manuscript scroll (Memory Index)
  5. Kumbha — Sacred Kalasha brass pot with mango leaves & coconut (Array Boundary)

All follow the strict design & rigging requirements:
  * Y-up, front = +Z, ground at Y=0, one shared 14-bone core skeleton + extras
  * Blank un-deformed badge plate on chest for runtime number projection
  * Consistent eyes (dark lens + cream catchlight + lid)
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
        "eye_dark": dict(color=srgb("#15151B"), roughness=0.10, metallic=0.0),
        "eye_glint": dict(color=srgb("#FFF9EE"), roughness=0.25, metallic=0.0,
                          emissive=tuple(c * 0.60 for c in srgb("#FFF1D8"))),
        "badge": dict(color=srgb("#F7F2E8"), roughness=0.52, metallic=0.0, texture="matte"),
        "badge_rim": dict(color=srgb("#C89D46"), roughness=0.30, metallic=0.85, texture=None),
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


def eye_pair(shell, cx, cy, rx, ry, rz, M, lid=(1.15, 0.62, 0.80), lid_lift=1.15,
             proud=0.70, yaw=0.0, glint=0.32, brow_lift=0.0, lid_mat="lid"):
    parts = []
    for side, sgn, bone in (("L", -1.0, "eyeL"), ("R", 1.0, "eyeR")):
        zf = probe_z(shell, sgn * cx, cy)
        if zf is None:
            zf = 0.25
        cz = zf - rz * (1.0 - proud)
        e = sphere(rx, ry, rz, seg=24, rings=14, name="eye" + side, mat="eye_dark")
        e.move(sgn * cx, cy, cz)
        if yaw:
            e.rotate(ry=sgn * yaw)
        e.tag(bone)
        parts.append(e)

        g = sphere(rx * glint, ry * glint, rz * glint, seg=14, rings=8,
                   name="glint" + side, mat="eye_glint")
        g.move(sgn * (cx - 0.25 * rx), cy + 0.25 * ry, cz + rz * 0.85)
        g.tag(bone)
        parts.append(g)

        lr, ly, lz = rx * lid[0], ry * lid[1], rz * lid[2]
        lidp = superellipsoid(lr, ly, lz, e1=0.58, e2=0.58, seg=20, rings=12,
                              name="lid" + side, mat=lid_mat)
        # Position lid comfortably ABOVE the lens so it doesn't look sleepy/sad
        lidp.move(sgn * cx, cy + lid_lift * ly + brow_lift + ry * 0.40, cz + lz * 0.20)
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
    """GAJA — Bipedal baby elephant mascot. Stout, lovable, heavyweight anchor."""
    M = dict(shared_mats())
    M.update({
        "skin": dict(color=srgb("#6D7E90"), roughness=0.55, metallic=0.02, texture="stone"),
        "skin_light": dict(color=srgb("#869BB0"), roughness=0.50, metallic=0.02),
        "ear_inner": dict(color=srgb("#DE8A73"), roughness=0.60, metallic=0.0),
        "tusk": dict(color=srgb("#FFF8E7"), roughness=0.25, metallic=0.0),
        "lid": dict(color=srgb("#667789"), roughness=0.50, metallic=0.02),
    })
    parts = []
    shell = []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    # Upright sturdy biped legs
    def biped_leg(sgn):
        foot = superellipsoid(0.115, 0.055, 0.135, e1=0.45, e2=0.45, seg=24, rings=12,
                              name="foot", mat="skin")
        foot.move(sgn * 0.185, 0.055, 0.02)
        foot.tag("legL" if sgn < 0 else "legR")

        leg_col = capsule(0.088, 0.180, seg=20, rings=8, name="leg_col", mat="skin")
        leg_col.move(sgn * 0.185, 0.185, 0.0)
        leg_col.tag("legL" if sgn < 0 else "legR")

        # Cute rounded toenails
        toes = []
        for ti, tang in enumerate((-0.25, 0.0, 0.25)):
            toe = sphere(0.022, 0.020, 0.024, seg=12, rings=8, name=f"toe_{ti}", mat="tusk")
            toe.move(sgn * (0.185 + tang * 0.07), 0.022, 0.14)
            toe.tag("legL" if sgn < 0 else "legR")
            toes.append(toe)
        return [foot, leg_col] + toes

    parts.extend(mirrored(biped_leg))

    # Round chubby belly & torso
    belly = lathe([(0.170, 0.240), (0.260, 0.320), (0.330, 0.440), (0.340, 0.580),
                   (0.295, 0.720), (0.220, 0.810)], seg=36, name="belly", mat="skin")
    belly.tag("hips", "spine", "chest", "base")
    add(belly)

    # Large domed head
    head = sphere(0.315, 0.305, 0.305, seg=36, rings=24, name="head", mat="skin")
    head.move(0.0, 0.940, 0.035)
    head.tag("head", "neck")
    add(head)

    # Big floppy ears (curved superellipsoids) - spread out wider and rotated pleasantly
    def ear(sgn):
        outer = superellipsoid(0.040, 0.220, 0.240, e1=0.55, e2=0.55, seg=24, rings=14,
                               name="ear_outer", mat="skin")
        outer.rotate(rz=sgn * 0.12, ry=sgn * 0.40)
        outer.move(sgn * 0.380, 0.980, -0.060)
        outer.tag("earL" if sgn < 0 else "earR")

        inner = superellipsoid(0.018, 0.185, 0.200, e1=0.55, e2=0.55, seg=20, rings=12,
                               name="ear_inner", mat="ear_inner")
        inner.rotate(rz=sgn * 0.12, ry=sgn * 0.40)
        inner.move(sgn * 0.385, 0.980, -0.045)
        inner.tag("earL" if sgn < 0 else "earR")
        return [outer, inner]

    parts.extend(mirrored(ear))

    # Curved joyful trunk in front - curving upwards proudly
    trunk_pts = [
        (0.0, 0.900, 0.280),
        (0.0, 0.820, 0.360),
        (0.0, 0.820, 0.450),
        (0.0, 0.940, 0.520),
        (0.0, 1.060, 0.560),
    ]
    trunk = tube(trunk_pts, 0.082, radial=18, name="trunk", mat="skin",
                 taper=[1.0, 0.85, 0.70, 0.58, 0.50])
    trunk.tag("trunk.01", "trunk.02", "trunk.03", "head")
    add(trunk)

    # Tiny rounded tusks
    def tusk(sgn):
        t = arc_tube((0.0, 0.870, 0.280), 0.065, 0.2, 1.2, 0.022, steps=12, plane="YZ",
                     radial=10, name="tusk", mat="tusk")
        t.move(sgn * 0.115, 0.0, 0.0)
        t.rotate(ry=sgn * 0.30)
        t.tag("head")
        return t

    parts.extend(mirrored(tusk))

    # Cute short arms in front
    def arm(sgn):
        a = tube([(sgn * 0.260, 0.680, 0.050),
                  (sgn * 0.280, 0.560, 0.150),
                  (sgn * 0.170, 0.530, 0.220)], 0.062, radial=14, name="arm", mat="skin",
                 taper=[1.0, 0.92, 0.85])
        a.tag("armL" if sgn < 0 else "armR", "chest")
        paw = sphere(0.055, 0.050, 0.055, seg=16, rings=10, name="paw", mat="skin")
        paw.move(sgn * 0.170, 0.530, 0.220)
        paw.tag("armL" if sgn < 0 else "armR", "chest")
        return [a, paw]

    parts.extend(mirrored(arm))

    # Eyes on head
    ex, ey = 0.125, 0.970
    parts.extend(eye_pair(shell, ex, ey, 0.065, 0.072, 0.040, M,
                          lid=(1.10, 0.42, 0.85), lid_lift=1.25, proud=0.76, lid_mat="lid"))

    # Blank cream badge plate on chest
    poly = rounded_rect_poly(0.190, 0.115, 0.032, seg=6)
    parts.extend(conform_plate(shell, poly, 0.520, thickness=0.019, proud=0.013,
                               rim=1.10, rim_proud=0.008, name="badge"))
    pz = (probe_z(shell, 0.0, 0.520) or 0.32) + 0.013

    props = dict(hipY=0.30, spineY=0.48, chestY=0.66, neckY=0.82, headY=0.96,
                 legX=0.185, legY=0.20, baseY=0.06, badgeY=0.520, badgeZ=pz,
                 eyeX=ex, eyeY=ey, eyeZ=(probe_z(shell, ex, ey) or 0.28),
                 r_hips=0.34, r_spine=0.34, r_chest=0.32, r_neck=0.28, r_head=0.32,
                 r_base=0.28, r_leg=0.14, badge_size=[0.190, 0.115])

    bones = [
        mat_bone("trunk.01", "head", (0.0, 0.840 - 0.96, 0.300), (0, 0, 1), 0.10, 0.12),
        mat_bone("trunk.02", "trunk.01", (0.0, -0.02, 0.110), (0, 1, 1), 0.10, 0.10),
        mat_bone("trunk.03", "trunk.02", (0.0, 0.08, 0.080), (0, 1, 0), 0.10, 0.08),
        mat_bone("earL", "head", (-0.360, 0.020, -0.040), (-1, 0, 0), 0.16, 0.18),
        mat_bone("earR", "head", (0.360, 0.020, -0.040), (1, 0, 0), 0.16, 0.18),
        mat_bone("armL", "chest", (-0.260, 0.680 - 0.66, 0.050), (-1, -1, 1), 0.18, 0.12),
        mat_bone("armR", "chest", (0.260, 0.680 - 0.66, 0.050), (1, -1, 1), 0.18, 0.12),
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
                ["#6D7E90", "#869BB0", "#DE8A73", "#FFF8E7"], 1.25).finish(parts)


# ============================================================== 2 · MAYUR =====
def build_mayur():
    """MAYUR — Peacock chick with vibrant feather fan. Visual pattern comparator."""
    M = dict(shared_mats())
    M.update({
        "body_teal": dict(color=srgb("#2B7E8C"), roughness=0.38, metallic=0.04),
        "fan_emerald": dict(color=srgb("#2EA373"), roughness=0.45, metallic=0.08),
        "fan_gold": dict(color=srgb("#E0B24C"), roughness=0.32, metallic=0.60),
        "fan_indigo": dict(color=srgb("#23356A"), roughness=0.25, metallic=0.10),
        "beak": dict(color=srgb("#FFF2D0"), roughness=0.30, metallic=0.0),
        "lid": dict(color=srgb("#236B77"), roughness=0.40, metallic=0.04),
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
        leg = capsule(0.024, 0.180, seg=16, rings=8, name="bird_leg", mat="beak")
        leg.move(sgn * 0.110, 0.100, 0.0)
        leg.tag("legL" if sgn < 0 else "legR")

        foot_parts = []
        for fi, f_ang in enumerate((-0.38, 0.0, 0.38)):
            toe = capsule(0.014, 0.075, seg=12, rings=6, name=f"toe_{fi}", mat="beak")
            toe.rotate(ry=f_ang)
            toe.move(sgn * 0.110 + math.sin(f_ang) * 0.035, 0.014, math.cos(f_ang) * 0.035)
            toe.tag("legL" if sgn < 0 else "legR")
            foot_parts.append(toe)
        return [leg] + foot_parts

    parts.extend(mirrored(bird_leg))

    # Round chick body
    body = sphere(0.245, 0.255, 0.245, seg=32, rings=20, name="chick_body", mat="body_teal")
    body.move(0.0, 0.360, 0.0)
    body.tag("hips", "spine", "chest", "base")
    add(body)

    # Cute bird head
    head = sphere(0.230, 0.240, 0.230, seg=32, rings=20, name="chick_head", mat="body_teal")
    head.move(0.0, 0.680, 0.030)
    head.tag("head", "neck")
    add(head)

    # 3-feather head crest
    for ci, c_ang in enumerate((-0.22, 0.0, 0.22)):
        c_stem = tube([(0.0, 0.900, 0.040),
                       (math.sin(c_ang) * 0.070, 0.990, 0.030)], 0.008, radial=8,
                      name=f"crest_stem_{ci}", mat="fan_emerald")
        c_stem.tag("crest.top", "head")
        c_tip = superellipsoid(0.022, 0.038, 0.012, e1=0.45, e2=0.45, seg=14, rings=8,
                               name=f"crest_tip_{ci}", mat="fan_indigo")
        c_tip.rotate(rz=-c_ang)
        c_tip.move(math.sin(c_ang) * 0.070, 1.020, 0.030)
        c_tip.tag("crest.top", "head")
        parts.extend([c_stem, c_tip])

    # Cute beak
    beak = superellipsoid(0.042, 0.035, 0.065, e1=0.40, e2=0.40, seg=16, rings=10,
                          name="beak", mat="beak")
    beak.move(0.0, 0.640, 0.250)
    beak.tag("head")
    add(beak)

    # Small wings at sides
    def wing(sgn):
        w = superellipsoid(0.035, 0.120, 0.160, e1=0.45, e2=0.50, seg=18, rings=10,
                           name="wing", mat="body_teal")
        w.rotate(ry=sgn * 0.30, rz=sgn * 0.20)
        w.move(sgn * 0.245, 0.420, -0.020)
        w.tag("chest")
        return w

    parts.extend(mirrored(wing))

    # Magnificent peacock tail fan (9 fanned feathers with eye-spots) - larger and wider
    N_FEATHERS = 9
    for fi in range(N_FEATHERS):
        t_frac = fi / (N_FEATHERS - 1)
        theta = -1.25 + t_frac * 2.50  # fan angle
        rad = 0.520
        fx = math.sin(theta) * rad
        fy = 0.460 + math.cos(theta) * (rad * 0.80)
        fz = -0.160

        f_blade = superellipsoid(0.082, 0.220, 0.022, e1=0.45, e2=0.45, seg=16, rings=8,
                                 name=f"feather_{fi}", mat="fan_emerald")
        f_blade.rotate(rz=-theta)
        f_blade.move(fx, fy, fz)
        f_blade.tag("tailFan.L" if theta < -0.1 else ("tailFan.R" if theta > 0.1 else "tailFan_root"))
        parts.append(f_blade)

        # Golden & Indigo eye-spot on feather
        eye_spot = superellipsoid(0.045, 0.065, 0.012, e1=0.50, e2=0.50, seg=12, rings=6,
                                  name=f"spot_{fi}", mat="fan_gold")
        eye_spot.rotate(rz=-theta)
        eye_spot.move(fx * 1.08, fy + math.cos(theta) * 0.08, fz + 0.012)
        eye_spot.tag("tailFan.L" if theta < -0.1 else ("tailFan.R" if theta > 0.1 else "tailFan_root"))
        parts.append(eye_spot)

    # Big expressive eyes
    ex, ey = 0.105, 0.700
    parts.extend(eye_pair(shell, ex, ey, 0.060, 0.068, 0.038, M,
                          lid=(1.10, 0.40, 0.85), lid_lift=1.28, proud=0.78, lid_mat="lid"))

    # Blank cream badge on chest
    poly = rounded_rect_poly(0.165, 0.105, 0.028, seg=6)
    parts.extend(conform_plate(shell, poly, 0.380, thickness=0.018, proud=0.013,
                               rim=1.10, rim_proud=0.008, name="badge"))
    pz = (probe_z(shell, 0.0, 0.380) or 0.24) + 0.013

    props = dict(hipY=0.22, spineY=0.36, chestY=0.50, neckY=0.60, headY=0.72,
                 legX=0.110, legY=0.12, baseY=0.05, badgeY=0.380, badgeZ=pz,
                 eyeX=ex, eyeY=ey, eyeZ=(probe_z(shell, ex, ey) or 0.24),
                 r_hips=0.26, r_spine=0.26, r_chest=0.25, r_neck=0.22, r_head=0.24,
                 r_base=0.22, r_leg=0.08, badge_size=[0.165, 0.105])

    bones = [
        mat_bone("tailFan_root", "hips", (0.0, 0.360 - 0.22, -0.160), (0, 1, 0), 0.20, 0.25),
        mat_bone("tailFan.L", "tailFan_root", (-0.180, 0.150, 0.0), (-1, 1, 0), 0.20, 0.22),
        mat_bone("tailFan.R", "tailFan_root", (0.180, 0.150, 0.0), (1, 1, 0), 0.20, 0.22),
        mat_bone("crest.top", "head", (0.0, 0.900 - 0.72, 0.040), (0, 1, 0), 0.14, 0.12),
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
                ["#2B7E8C", "#2EA373", "#E0B24C", "#FFF2D0"], 1.10).finish(parts)


# ============================================================== 3 · DIYA ======
def build_diya():
    """DIYA — Terracotta oil lamp with living flame crest. Active traversal pointer."""
    M = dict(shared_mats())
    M.update({
        "clay": dict(color=srgb("#C86B43"), roughness=0.65, metallic=0.01, texture="ceramic"),
        "clay_dark": dict(color=srgb("#984B2A"), roughness=0.68, metallic=0.01),
        "flame_outer": dict(color=srgb("#FFAD33"), roughness=0.20, metallic=0.0, alpha=0.88,
                            emissive=tuple(c * 1.25 for c in srgb("#FFA500"))),
        "flame_core": dict(color=srgb("#FFF2B2"), roughness=0.15, metallic=0.0,
                           emissive=tuple(c * 2.00 for c in srgb("#FFFDE0"))),
        "ember": dict(color=srgb("#FF6A00"), roughness=0.20, metallic=0.0,
                      emissive=tuple(c * 1.50 for c in srgb("#FF7A00"))),
        "lid": dict(color=srgb("#B85F38"), roughness=0.60, metallic=0.01),
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
        foot = superellipsoid(0.048, 0.038, 0.048, e1=0.45, e2=0.45, seg=16, rings=8,
                              name=f"clay_foot_{fi}", mat="clay_dark")
        foot.move(math.cos(f_ang) * 0.145, 0.038, math.sin(f_ang) * 0.145)
        foot.tag("base")
        parts.append(foot)

    # Terracotta lamp bowl body with flared rim & pinched lip
    bowl = lathe([(0.140, 0.030), (0.240, 0.110), (0.295, 0.220), (0.300, 0.330),
                  (0.275, 0.420), (0.255, 0.460), (0.285, 0.490)], seg=36, name="bowl", mat="clay")
    bowl.tag("hips", "spine", "chest", "base")
    add(bowl)

    # Chubby clay arms
    def arm(sgn):
        a = tube([(sgn * 0.265, 0.320, 0.0),
                  (sgn * 0.310, 0.240, 0.05),
                  (sgn * 0.240, 0.170, 0.10)], 0.042, radial=12, name="clay_arm", mat="clay")
        a.tag("chest")
        return a

    parts.extend(mirrored(arm))

    # Living sculpted flame crest on top
    flame_pts = [
        (0.0, 0.470, 0.0),
        (0.0, 0.560, 0.020),
        (0.025, 0.680, 0.010),
        (-0.015, 0.790, -0.015),
        (0.0, 0.865, 0.0),
    ]
    flame_outer = tube(flame_pts, 0.125, radial=20, name="flame_outer", mat="flame_outer",
                       taper=[0.60, 1.0, 0.88, 0.55, 0.10])
    flame_outer.tag("flame_tip", "flame_base", "head")
    add(flame_outer, False)

    flame_inner = tube(flame_pts[:4], 0.075, radial=16, name="flame_core", mat="flame_core",
                       taper=[0.50, 1.0, 0.75, 0.20])
    flame_inner.tag("flame_tip", "flame_base", "head")
    add(flame_inner, False)

    # Radiant ember on cheek
    ember = sphere(0.024, 0.024, 0.020, seg=14, rings=8, name="ember", mat="ember")
    ember.move(0.185, 0.280, 0.215)
    ember.tag("head")
    parts.append(ember)

    # Big warm friendly eyes on bowl
    ex, ey = 0.105, 0.315
    parts.extend(eye_pair(shell, ex, ey, 0.058, 0.062, 0.038, M,
                          lid=(1.10, 0.38, 0.85), lid_lift=1.30, proud=0.78, lid_mat="lid"))

    # Blank cream badge on lower belly
    poly = rounded_rect_poly(0.175, 0.095, 0.026, seg=6)
    parts.extend(conform_plate(shell, poly, 0.160, thickness=0.018, proud=0.013,
                               rim=1.10, rim_proud=0.008, name="badge"))
    pz = (probe_z(shell, 0.0, 0.160) or 0.28) + 0.013

    props = dict(hipY=0.15, spineY=0.25, chestY=0.35, neckY=0.44, headY=0.55,
                 legX=0.145, legY=0.06, baseY=0.04, badgeY=0.160, badgeZ=pz,
                 eyeX=ex, eyeY=ey, eyeZ=(probe_z(shell, ex, ey) or 0.27),
                 r_hips=0.30, r_spine=0.30, r_chest=0.28, r_neck=0.24, r_head=0.26,
                 r_base=0.26, r_leg=0.08, badge_size=[0.175, 0.095])

    bones = [
        mat_bone("flame_base", "head", (0.0, 0.470 - 0.55, 0.0), (0, 1, 0), 0.15, 0.18),
        mat_bone("flame_tip", "flame_base", (0.0, 0.220, 0.0), (0, 1, 0), 0.15, 0.14),
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
                ["#C86B43", "#FFAD33", "#FFF2B2", "#FF6A00"], 0.87).finish(parts)


# ============================================================== 4 · PATRA =====
def build_patra():
    """PATRA — Living manuscript parchment scroll creature. Array memory index."""
    M = dict(shared_mats())
    M.update({
        "parchment": dict(color=srgb("#EADBBE"), roughness=0.55, metallic=0.0, texture="ceramic"),
        "saffron_silk": dict(color=srgb("#D8842E"), roughness=0.35, metallic=0.10),
        "wood_peg": dict(color=srgb("#6D4222"), roughness=0.60, metallic=0.02),
        "rod_brass": dict(color=srgb("#C89D46"), roughness=0.30, metallic=0.75),
        "lid": dict(color=srgb("#D4C4A4"), roughness=0.50, metallic=0.0),
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
        leg = capsule(0.038, 0.120, seg=16, rings=8, name="peg_leg", mat="wood_peg")
        leg.move(sgn * 0.110, 0.060, 0.0)
        leg.tag("legL" if sgn < 0 else "legR")
        return leg

    parts.extend(mirrored(peg_leg))

    # Curled parchment cylindrical body
    scroll_body = lathe([(0.190, 0.100), (0.220, 0.220), (0.225, 0.450),
                         (0.220, 0.700), (0.200, 0.900), (0.180, 0.960)],
                        seg=36, name="scroll_body", mat="parchment")
    scroll_body.tag("hips", "spine", "chest", "head", "base")
    add(scroll_body)

    # Curled parchment spiral top layers
    curl_top = torus(0.140, 0.038, seg_major=28, seg_minor=14, name="curl_top", mat="parchment")
    curl_top.rotate(rx=math.pi * 0.5)
    curl_top.move(0.0, 0.960, 0.0)
    curl_top.tag("head", "scroll_curl")
    add(curl_top, False)

    # Saffron silk cord sash around waist
    sash = torus(0.228, 0.028, seg_major=32, seg_minor=12, name="sash", mat="saffron_silk")
    sash.move(0.0, 0.520, 0.0)
    sash.tag("spine")
    parts.append(sash)

    # Ribbon bow & knot
    bow = superellipsoid(0.045, 0.045, 0.035, e1=0.45, e2=0.45, seg=16, rings=8,
                         name="ribbon_knot", mat="saffron_silk")
    bow.move(-0.160, 0.520, 0.160)
    bow.tag("spine")
    parts.append(bow)

    # Little hands holding tiny scroll rods
    def scroll_hand(sgn):
        rod = capsule(0.016, 0.160, seg=12, rings=6, name="scroll_rod", mat="rod_brass")
        rod.move(sgn * 0.140, 0.530, 0.220)
        rod.tag("chest")
        hand = sphere(0.032, 0.032, 0.032, seg=14, rings=8, name="hand", mat="parchment")
        hand.move(sgn * 0.140, 0.530, 0.210)
        hand.tag("chest")
        return [rod, hand]

    parts.extend(mirrored(scroll_hand))

    # Large thoughtful eyes on upper scroll
    ex, ey = 0.095, 0.780
    parts.extend(eye_pair(shell, ex, ey, 0.058, 0.065, 0.036, M,
                          lid=(1.10, 0.40, 0.85), lid_lift=1.28, proud=0.78, lid_mat="lid"))

    # Blank cream badge on lower body
    poly = rounded_rect_poly(0.180, 0.110, 0.028, seg=6)
    parts.extend(conform_plate(shell, poly, 0.260, thickness=0.018, proud=0.013,
                               rim=1.10, rim_proud=0.008, name="badge"))
    pz = (probe_z(shell, 0.0, 0.260) or 0.22) + 0.013

    props = dict(hipY=0.18, spineY=0.38, chestY=0.58, neckY=0.70, headY=0.82,
                 legX=0.110, legY=0.08, baseY=0.06, badgeY=0.260, badgeZ=pz,
                 eyeX=ex, eyeY=ey, eyeZ=(probe_z(shell, ex, ey) or 0.21),
                 r_hips=0.25, r_spine=0.25, r_chest=0.24, r_neck=0.22, r_head=0.24,
                 r_base=0.20, r_leg=0.08, badge_size=[0.180, 0.110])

    bones = [
        mat_bone("scroll_curl", "head", (0.0, 0.960 - 0.82, 0.0), (0, 1, 0), 0.12, 0.15),
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
                ["#EADBBE", "#D8842E", "#6D4222", "#C89D46"], 1.05).finish(parts)


# ============================================================== 5 · KUMBHA ====
def build_kumbha():
    """KUMBHA — Golden Kalasha pot with mango leaves & coconut. Array boundary buffer."""
    M = dict(shared_mats())
    M.update({
        "brass": dict(color=srgb("#DFAC3A"), roughness=0.22, metallic=0.88),
        "brass_dark": dict(color=srgb("#A8781E"), roughness=0.30, metallic=0.85),
        "mango_leaf": dict(color=srgb("#2B8A44"), roughness=0.40, metallic=0.04),
        "coconut": dict(color=srgb("#6A4526"), roughness=0.72, metallic=0.02, texture="stone"),
        "lid": dict(color=srgb("#CE982C"), roughness=0.25, metallic=0.80),
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
        foot = superellipsoid(0.065, 0.045, 0.080, e1=0.45, e2=0.45, seg=18, rings=8,
                              name="brass_foot", mat="brass")
        foot.move(sgn * 0.135, 0.045, 0.0)
        foot.tag("legL" if sgn < 0 else "legR")
        return foot

    parts.extend(mirrored(brass_foot))

    # Plump lathed Kalasha pot body
    pot = lathe([(0.140, 0.040), (0.230, 0.100), (0.315, 0.220), (0.340, 0.350),
                 (0.310, 0.480), (0.240, 0.560), (0.190, 0.600), (0.235, 0.640)],
                seg=40, name="kalasha_pot", mat="brass")
    pot.tag("hips", "spine", "chest", "head", "base")
    add(pot)

    # Flared neck rim with engraved ring
    rim = torus(0.215, 0.022, seg_major=36, seg_minor=12, name="neck_rim", mat="brass_dark")
    rim.move(0.0, 0.620, 0.0)
    rim.tag("head")
    parts.append(rim)

    # Short golden arms
    def arm(sgn):
        a = tube([(sgn * 0.310, 0.420, 0.0),
                  (sgn * 0.350, 0.320, 0.05),
                  (sgn * 0.280, 0.240, 0.10)], 0.045, radial=12, name="brass_arm", mat="brass")
        a.tag("chest")
        return a

    parts.extend(mirrored(arm))

    # Sacred coconut nestled on top
    coconut = superellipsoid(0.125, 0.170, 0.125, e1=0.55, e2=0.55, seg=24, rings=16,
                             name="coconut", mat="coconut")
    coconut.move(0.0, 0.770, 0.0)
    coconut.tag("head", "coconut_top")
    add(coconut, False)

    # 5 glossy mango leaves radiating outward - spread wider and lifted up
    N_LEAVES = 5
    for li in range(N_LEAVES):
        l_ang = li * (TAU / N_LEAVES)
        leaf = superellipsoid(0.065, 0.180, 0.020, e1=0.45, e2=0.45, seg=16, rings=8,
                              name=f"mango_leaf_{li}", mat="mango_leaf")
        leaf.rotate(rx=0.55)
        leaf.rotate(ry=l_ang)
        lx = math.sin(l_ang) * 0.185
        lz = math.cos(l_ang) * 0.185
        leaf.move(lx, 0.720, lz)
        leaf.tag("head", "leaf_crown")
        parts.append(leaf)

    # Warm sweet eyes on brass pot belly
    ex, ey = 0.110, 0.380
    parts.extend(eye_pair(shell, ex, ey, 0.060, 0.066, 0.038, M,
                          lid=(1.10, 0.38, 0.85), lid_lift=1.30, proud=0.78, lid_mat="lid"))

    # Blank cream badge on lower pot belly
    poly = rounded_rect_poly(0.175, 0.100, 0.026, seg=6)
    parts.extend(conform_plate(shell, poly, 0.200, thickness=0.018, proud=0.013,
                               rim=1.10, rim_proud=0.008, name="badge"))
    pz = (probe_z(shell, 0.0, 0.200) or 0.31) + 0.013

    props = dict(hipY=0.18, spineY=0.30, chestY=0.42, neckY=0.54, headY=0.64,
                 legX=0.135, legY=0.08, baseY=0.05, badgeY=0.200, badgeZ=pz,
                 eyeX=ex, eyeY=ey, eyeZ=(probe_z(shell, ex, ey) or 0.30),
                 r_hips=0.32, r_spine=0.32, r_chest=0.30, r_neck=0.24, r_head=0.26,
                 r_base=0.28, r_leg=0.10, badge_size=[0.175, 0.100])

    bones = [
        mat_bone("coconut_top", "head", (0.0, 0.770 - 0.64, 0.0), (0, 1, 0), 0.16, 0.18),
        mat_bone("leaf_crown", "head", (0.0, 0.680 - 0.64, 0.0), (0, 1, 0), 0.12, 0.22),
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
                ["#DFAC3A", "#A8781E", "#2B8A44", "#6A4526"], 0.96).finish(parts)


BUILDERS = {
    "gaja": build_gaja,
    "mayur": build_mayur,
    "diya": build_diya,
    "patra": build_patra,
    "kumbha": build_kumbha,
}
