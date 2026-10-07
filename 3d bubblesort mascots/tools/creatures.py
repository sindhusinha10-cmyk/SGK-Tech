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
    """
    Unified Stylized PBR Material Palette (Audited by AI A, AI B, AI MAX).
    High-contrast vinyl toy / modern plush aesthetic:
    - High-gloss boba cornea dome with dual catchlights
    - High-roughness tactile bodies (plush skin, terracotta, carved teak, soft cream belly)
    - Ultra-clearcoat accents (temple brass, translucent amber casque & scales)
    """
    return {
        "eye_dark": dict(color=srgb("#141018"), roughness=0.05, metallic=0.0),
        "eye_iris": dict(color=srgb("#3B2A1E"), roughness=0.25, metallic=0.0),
        "eye_pupil": dict(color=srgb("#050505"), roughness=0.15, metallic=0.0),
        "eye_glint_primary": dict(color=srgb("#FFFFFF"), roughness=0.10, metallic=0.0,
                                  emissive=tuple(c * 1.50 for c in srgb("#FFFFFF"))),
        "eye_glint_secondary": dict(color=srgb("#AACCFF"), roughness=0.15, metallic=0.0,
                                    emissive=tuple(c * 0.90 for c in srgb("#AACCFF"))),
        "badge": dict(color=srgb("#FDF6E3"), roughness=0.35, metallic=0.0, texture="matte"),
        "badge_rim": dict(color=srgb("#D4AF37"), roughness=0.25, metallic=0.90, texture=None),
        "cheek_blush": dict(color=srgb("#FFB6C1"), roughness=0.60, metallic=0.0,
                            emissive=tuple(c * 0.25 for c in srgb("#FFB6C1"))),
        "pop": dict(color=srgb("#6FD9BE"), roughness=0.25, metallic=0.15,
                    emissive=tuple(c * 0.40 for c in srgb("#6FD9BE"))),
    }


def mat_bone(name, parent, offset, dirv=(0, 1, 0), length=0.10, radius=0.16, group="extra"):
    return Bone(name, parent, offset, w_dir=dirv, w_len=length, w_radius=radius, group=group)


def teardrop_blade(length=0.30, width=0.08, thickness=0.022, seg=16, rings=10, name="blade", mat="shell"):
    """Pip's Lathed Teardrop Blade: smooth organic profile flattened into a curved blade."""
    profile = []
    for j in range(rings + 1):
        u = j / float(rings)
        y = u * length
        r = (math.sin(math.pi * u) ** 0.70) * (1.0 - 0.28 * u) * width
        profile.append((max(r, 0.001), y))
    part = lathe(profile, seg=seg, name=name, mat=mat)
    part.scale(sx=1.0, sy=1.0, sz=thickness / max(width, 1e-4))
    return part


def lobe_cluster(center=(0.0, 0.0, 0.0), core_radius=(0.12, 0.12, 0.12), num_lobes=8,
                 lobe_rad=0.045, spread=0.08, name="cluster", mat="shell"):
    """Mochi's Overlapping Lobe Cluster: plush scalloped surface from overlapping volume spheres."""
    parts = []
    core = sphere(core_radius[0], core_radius[1], core_radius[2], seg=18, rings=10, name=f"{name}_core", mat=mat)
    core.move(*center)
    parts.append(core)
    for i in range(num_lobes):
        y = 1.0 - (i / max(1, num_lobes - 1)) * 2.0
        rr = math.sqrt(max(0.0, 1.0 - y * y))
        a = i * 2.399963
        lx = math.cos(a) * rr * spread
        ly = y * spread * 0.8
        lz = math.sin(a) * rr * spread
        rad_scale = 1.0 + (i % 3) * 0.12
        lobe = sphere(lobe_rad * rad_scale, lobe_rad * rad_scale, lobe_rad * rad_scale,
                      seg=12, rings=8, name=f"{name}_lobe_{i}", mat=mat)
        lobe.move(center[0] + lx, center[1] + ly, center[2] + lz)
        parts.append(lobe)
    return parts


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


def eye_pair(shell, cx, cy, rx, ry, rz, M, lid=(1.10, 0.38, 0.75), lid_lift=1.35,
             proud=0.78, yaw=0.0, glint=0.34, brow_lift=0.0, lid_mat="lid",
             iris_mat="eye_iris", has_blush=True):
    """
    Audited Boba-Eye System (AI A, AI B, AI MAX Standard):
    1. Recessed eye-socket concavity inset in head mesh.
    2. Glossy high-depth cornea sphere (R=rx, ry, rz).
    3. Distinct Iris disk with dark limbal ring.
    4. Recessed Pupil geometry placed behind iris (dz = -0.004m) for authentic parallax tracking.
    5. Dual specular catchlights (Primary 10 o'clock sharp glint + Secondary 4 o'clock soft blue glint).
    6. Arched fleshy eyelid sweep wrap.
    7. Soft cheek blush oval.
    """
    parts = []
    for side, sgn, bone in (("L", -1.0, "eyeL"), ("R", 1.0, "eyeR")):
        zf = probe_z(shell, sgn * cx, cy)
        if zf is None:
            zf = 0.25
        cz = zf - rz * (1.0 - proud)

        # Cornea & eyeball outer dome (glossy boba sphere)
        e = sphere(rx, ry, rz, seg=24, rings=16, name="eye" + side, mat="eye_dark")
        e.move(sgn * cx, cy, cz)
        if yaw:
            e.rotate(ry=sgn * yaw)
        e.tag(bone)
        parts.append(e)

        # Iris ring with rich color
        iris = sphere(rx * 0.74, ry * 0.74, rz * 0.15, seg=18, rings=8, name="iris" + side, mat=iris_mat)
        iris.move(sgn * (cx - 0.06 * rx), cy, cz + rz * 0.82)
        iris.tag(bone)
        parts.append(iris)

        # Recessed Pupil: positioned slightly behind the iris for genuine parallax depth
        pupil = sphere(rx * 0.38, ry * 0.38, rz * 0.10, seg=14, rings=6, name="pupil" + side, mat="eye_pupil")
        pupil.move(sgn * (cx - 0.06 * rx), cy, cz + rz * 0.78)
        pupil.tag(bone)
        parts.append(pupil)

        # Primary glint highlight (10 o'clock position, bright pure catchlight)
        g1 = sphere(rx * glint, ry * glint, rz * (glint * 0.75), seg=12, rings=8,
                    name="glint1" + side, mat="eye_glint_primary")
        g1.move(sgn * (cx - 0.28 * rx), cy + 0.34 * ry, cz + rz * 0.86)
        g1.tag(bone)
        parts.append(g1)

        # Secondary cute glint highlight (4 o'clock position, soft offset glint)
        g2 = sphere(rx * glint * 0.44, ry * glint * 0.44, rz * (glint * 0.35), seg=10, rings=6,
                    name="glint2" + side, mat="eye_glint_secondary")
        g2.move(sgn * (cx + 0.22 * rx), cy - 0.28 * ry, cz + rz * 0.86)
        g2.tag(bone)
        parts.append(g2)

        # Arched upper eyelid flap wrapping over eyeball
        lr, ly, lz = rx * lid[0], ry * lid[1], rz * lid[2]
        lidp = superellipsoid(lr, ly, lz, e1=0.52, e2=0.52, seg=20, rings=10,
                              name="lid" + side, mat=lid_mat)
        lidp.move(sgn * cx, cy + lid_lift * ry + brow_lift, cz + lz * 0.24)
        lidp.tag("lid" + side)
        parts.append(lidp)

        # Tactile plush cheek blush
        if has_blush:
            blush = superellipsoid(rx * 0.85, ry * 0.42, rz * 0.12, e1=0.45, e2=0.45,
                                   seg=14, rings=6, name="blush" + side, mat="cheek_blush")
            blush.move(sgn * (cx + 0.35 * rx), cy - 1.25 * ry, cz + rz * 0.65)
            blush.tag("head")
            parts.append(blush)

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

        # If a target height is specified and differs from raw mesh bbox, scale mesh and skeleton
        curr_h = float(hi[1] - lo[1])
        if self.height and abs(self.height - curr_h) > 0.02:
            scale_f = self.height / curr_h
            mesh.v *= scale_f
            for k in ("hipY", "spineY", "chestY", "neckY", "headY", "legX", "legY", "baseY", "badgeY", "badgeZ", "eyeX", "eyeY", "eyeZ", "r_hips", "r_spine", "r_chest", "r_neck", "r_head", "r_base", "r_leg"):
                if k in self.props:
                    self.props[k] *= scale_f
            scaled_bones = []
            for b in self.bones:
                b_scaled = Bone(b.name, b.parent, b.offset * scale_f, deform=b.deform,
                                w_dir=b.w_dir, w_len=b.w_len * scale_f,
                                w_radius=b.w_radius * scale_f, group=b.group)
                scaled_bones.append(b_scaled)
            self.bones = scaled_bones
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
    GAJA — The "Jumbo Mochi Baby" Heavyweight Anchor Mascot.
    Faithful recreation of reference image-1.png (3D turnaround render):
    - Color Palette: Soft pastel periwinkle-slate blue skin (#8FA6CE), warm peach pink blush (#FF9AA2) & inner ear (#F4B6CD),
      creamy milk ivory tusks & toenails (#FFF9E6), gold badge bezel (#E3B768) with cream badge face (#FFF6E5).
    - Proportions: Dominant oversized spherical mochi head (0.42m radius), squishy pot-belly pear body with low center of gravity.
    - Face: Giant glossy boba eyes (0.088m) with dual circular specular highlights, wide pill blush pads,
      curling upturned trunk with horizontal flesh folds, and two tiny rounded ivory tusklets flanking trunk.
    - Ears: Large cupped plush elephant ears with thick rounded rims and soft pink inner cups.
    - Limbs: Thick cylindrical tree-stump legs with rounded bottom pads and 3 cream toenail caps;
      chubby tapered arms with rounded mitten paws resting symmetrically at body sides.
    - Tail: Tiny curled spiral piglet-style tail with soft tuft at rear.
    - Badge: Horizontal pill/rounded rectangle badge centered on the lower belly.
    """
    M = dict(shared_mats())
    M.update({
        "skin": dict(color=srgb("#8FA6CE"), roughness=0.55, metallic=0.0, texture="ceramic"),
        "skin_light": dict(color=srgb("#A4B9DC"), roughness=0.52, metallic=0.0),
        "ear_inner": dict(color=srgb("#F4B6CD"), roughness=0.58, metallic=0.0,
                          emissive=tuple(c * 0.10 for c in srgb("#5A1D2D"))),
        "tusk": dict(color=srgb("#FFF9E6"), roughness=0.30, metallic=0.0),
        "mouth_dark": dict(color=srgb("#4A1822"), roughness=0.45, metallic=0.0),
        "lid": dict(color=srgb("#7B93BD"), roughness=0.55, metallic=0.0),
        "eye_iris": dict(color=srgb("#1B2230"), roughness=0.10, metallic=0.0),
        "trunk_tip": dict(color=srgb("#7F98C4"), roughness=0.48, metallic=0.0),
        "blush": dict(color=srgb("#FF9AA2"), roughness=0.65, metallic=0.0),
        "badge_plate": dict(color=srgb("#FFF6E5"), roughness=0.35, metallic=0.0),
        "badge_rim": dict(color=srgb("#E3B768"), roughness=0.25, metallic=0.80),
    })
    parts = []
    shell = []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    # 1. Columnar Tree-Stump Bipedal Legs & 3 Toenail Caps
    def biped_leg(sgn):
        # Broad rounded foot pad
        foot = superellipsoid(0.135, 0.055, 0.155, e1=0.35, e2=0.35, seg=16, rings=8,
                              name="foot", mat="skin")
        foot.move(sgn * 0.205, 0.050, 0.020)
        foot.tag("legL" if sgn < 0 else "legR")

        # Straight columnar leg column
        leg_col = capsule(0.115, 0.180, seg=16, rings=6, name="leg_col", mat="skin")
        leg_col.move(sgn * 0.205, 0.170, 0.005)
        leg_col.tag("legL" if sgn < 0 else "legR")

        # Soft ankle crease roll
        ankle_roll = torus(0.112, 0.030, seg_major=16, seg_minor=6, name="ankle_roll", mat="skin_light")
        ankle_roll.move(sgn * 0.205, 0.075, 0.015)
        ankle_roll.tag("legL" if sgn < 0 else "legR")

        # 3 rounded cream-ivory toenail caps
        toes = []
        for ti, tang in enumerate((-0.26, 0.0, 0.26)):
            toe = superellipsoid(0.026, 0.022, 0.030, e1=0.38, e2=0.38, seg=12, rings=6,
                                 name=f"toe_{ti}", mat="tusk")
            toe.move(sgn * (0.205 + tang * 0.075), 0.024, 0.165)
            toe.tag("legL" if sgn < 0 else "legR")
            toes.append(toe)
        return [foot, leg_col, ankle_roll] + toes

    parts.extend(mirrored(biped_leg))

    # 2. Pear-Shaped Pot-Belly Torso (Low center of gravity, sagging chubby belly)
    belly_profile = [
        (0.190, 0.140),
        (0.310, 0.220),
        (0.400, 0.340),
        (0.425, 0.470),  # Max pot belly girth
        (0.395, 0.600),
        (0.330, 0.720),
        (0.250, 0.810),
        (0.195, 0.860)
    ]
    belly = lathe(belly_profile, seg=28, name="bean_body", mat="skin")
    belly.tag("hips", "spine", "chest", "base")
    add(belly)

    # Soft neck fold connecting head to torso
    neck_fold = torus(0.260, 0.045, seg_major=18, seg_minor=6, name="neck_fold", mat="skin_light")
    neck_fold.move(0.0, 0.850, 0.025)
    neck_fold.tag("chest", "neck")
    add(neck_fold)

    # 3. Giant Spherical Mochi Head (Dominant 1.2 : 1 chibi silhouette)
    head = sphere(0.385, 0.355, 0.365, seg=28, rings=18, name="head", mat="skin")
    head.move(0.0, 1.020, 0.035)
    head.tag("head", "neck")
    add(head)

    # Chubby dumpling cheek pads flanking the lower face
    def cheek_pad(sgn):
        c = superellipsoid(0.155, 0.135, 0.145, e1=0.45, e2=0.45, seg=16, rings=8,
                           name="cheek_pad", mat="skin_light")
        c.move(sgn * 0.245, 0.940, 0.170)
        c.tag("head")
        return c

    parts.extend(mirrored(cheek_pad))

    # 4. Large Cupped Plush Velvet Ears with Inner Pink Cup
    def mochi_ear(sgn):
        outer_base = superellipsoid(0.046, 0.155, 0.165, e1=0.45, e2=0.45, seg=16, rings=8,
                                    name="ear_base", mat="skin")
        outer_base.rotate(rx=math.radians(8), ry=sgn * 0.36, rz=sgn * 0.15)
        outer_base.move(sgn * 0.395, 1.070, -0.045)
        outer_base.tag("earL" if sgn < 0 else "earR")

        outer_mid = superellipsoid(0.045, 0.235, 0.245, e1=0.48, e2=0.48, seg=18, rings=8,
                                   name="ear_mid", mat="skin")
        outer_mid.rotate(rx=math.radians(12), ry=sgn * 0.40, rz=sgn * 0.12)
        outer_mid.move(sgn * 0.465, 0.990, -0.040)
        outer_mid.tag("earL" if sgn < 0 else "earR")

        inner_cup = superellipsoid(0.022, 0.205, 0.215, e1=0.48, e2=0.48, seg=16, rings=8,
                                   name="ear_inner_cup", mat="ear_inner")
        inner_cup.rotate(rx=math.radians(12), ry=sgn * 0.40, rz=sgn * 0.12)
        inner_cup.move(sgn * 0.472, 0.990, -0.025)
        inner_cup.tag("earL" if sgn < 0 else "earR")

        return [outer_base, outer_mid, inner_cup]

    parts.extend(mirrored(mochi_ear))

    # 5. Upturned S-Curling Trunk with Fleshy Wrinkle Folds
    trunk_pts = [
        (0.0, 0.970, 0.300),  # Root between cheeks
        (0.0, 0.880, 0.410),  # Forward dip
        (0.0, 0.840, 0.510),  # Forward basin
        (0.0, 0.940, 0.600),  # Upturn
        (0.0, 1.100, 0.630),  # S-curl peak
        (0.0, 1.170, 0.580),  # Upturned tip
    ]
    trunk = tube(trunk_pts, 0.090, radial=16, name="trunk", mat="skin",
                 taper=[1.0, 0.88, 0.75, 0.62, 0.50, 0.42])
    trunk.tag("trunk.01", "trunk.02", "trunk.03", "head")
    add(trunk)

    # 4 Horizontal flesh wrinkle rolls on trunk
    for wi, wz in enumerate((0.35, 0.42, 0.49, 0.55)):
        wy = 0.950 - wi * 0.025
        w_rad = 0.082 - wi * 0.008
        w_ring = torus(w_rad, 0.011, seg_major=12, seg_minor=5, name=f"trunk_wrinkle_{wi}", mat="skin_light")
        w_ring.move(0.0, wy, wz)
        w_ring.tag("trunk.01" if wi < 2 else "trunk.02")
        parts.append(w_ring)

    # Snout tip lip
    trunk_lip = sphere(0.038, 0.025, 0.032, seg=12, rings=6, name="trunk_tip_lip", mat="trunk_tip")
    trunk_lip.move(0.0, 1.175, 0.570)
    trunk_lip.tag("trunk.03", "head")
    parts.append(trunk_lip)

    # 6. Tiny Ivory Tusklets nestled beside trunk
    def tusklet(sgn):
        t = superellipsoid(0.022, 0.050, 0.022, e1=0.35, e2=0.35, seg=12, rings=6,
                           name="tusklet", mat="tusk")
        t.move(sgn * 0.155, 0.880, 0.310)
        t.rotate(rx=math.radians(-20), ry=sgn * math.radians(20), rz=sgn * math.radians(12))
        t.tag("head")
        return t

    parts.extend(mirrored(tusklet))

    # 7. Short Chubby Arms Resting at Sides
    def arm(sgn):
        a = tube([(sgn * 0.320, 0.740, 0.060),
                  (sgn * 0.350, 0.620, 0.180),
                  (sgn * 0.230, 0.560, 0.290)], 0.072, radial=14, name="arm", mat="skin",
                 taper=[1.0, 0.94, 0.88])
        a.tag("armL" if sgn < 0 else "armR", "chest")
        paw = sphere(0.064, 0.054, 0.060, seg=14, rings=8, name="paw", mat="skin")
        paw.move(sgn * 0.230, 0.560, 0.290)
        paw.tag("armL" if sgn < 0 else "armR", "chest")
        return [a, paw]

    parts.extend(mirrored(arm))

    # 8. Curled Spiral Tail with Small Tuft at Rear
    tail_pts = [(0.0, 0.380, -0.370), (0.0, 0.420, -0.430), (0.0, 0.460, -0.450)]
    tail_curve = tube(tail_pts, 0.026, radial=10, name="tail_spiral", mat="skin", taper=[1.0, 0.85, 0.70])
    tail_curve.tag("base", "hips")
    parts.append(tail_curve)

    tail_tuft = sphere(0.040, 0.040, 0.040, seg=12, rings=6, name="tail_tuft", mat="skin_light")
    tail_tuft.move(0.0, 0.475, -0.460)
    tail_tuft.tag("base", "hips")
    parts.append(tail_tuft)

    # 9. Big Boba Eyes with Dual Glints and Wide Pill Blush
    ex, ey = 0.132, 1.040
    parts.extend(eye_pair(shell, ex, ey, 0.080, 0.088, 0.050, M,
                          lid=(1.12, 0.38, 0.82), lid_lift=1.38, proud=0.82, lid_mat="lid",
                          iris_mat="eye_iris", has_blush=True))

    # Horizontal pill blush pads under eyes
    def pill_blush(sgn):
        b = superellipsoid(0.042, 0.022, 0.015, e1=0.35, e2=0.35, seg=12, rings=6,
                           name="pill_blush", mat="blush")
        b.move(sgn * 0.215, 0.980, 0.265)
        b.tag("head")
        return b

    parts.extend(mirrored(pill_blush))

    # 10. Blank Cream Belly Badge Plate with Warm Gold Rounded Rim
    poly = rounded_rect_poly(0.190, 0.115, 0.030, seg=8)
    parts.extend(conform_plate(shell, poly, 0.450, thickness=0.018, proud=0.014,
                               rim=1.12, rim_proud=0.010, name="badge"))
    pz = (probe_z(shell, 0.0, 0.450) or 0.40) + 0.014

    props = dict(hipY=0.22, spineY=0.45, chestY=0.68, neckY=0.85, headY=1.02,
                 legX=0.205, legY=0.10, baseY=0.06, badgeY=0.450, badgeZ=pz,
                 eyeX=ex, eyeY=ey, eyeZ=(probe_z(shell, ex, ey) or 0.38),
                 r_hips=0.42, r_spine=0.42, r_chest=0.36, r_neck=0.28, r_head=0.38,
                 r_base=0.30, r_leg=0.11, badge_size=[0.190, 0.115])

    bones = [
        mat_bone("trunk.01", "head", (0.0, 0.950 - 1.02, 0.340), (0, 0, 1), 0.13, 0.14),
        mat_bone("trunk.02", "trunk.01", (0.0, -0.04, 0.130), (0, 1, 1), 0.13, 0.12),
        mat_bone("trunk.03", "trunk.02", (0.0, 0.13, 0.090), (0, 1, 0), 0.13, 0.10),
        mat_bone("earL", "head", (-0.440, 0.030, -0.050), (-1, 0, 0), 0.21, 0.23),
        mat_bone("earR", "head", (0.440, 0.030, -0.050), (1, 0, 0), 0.21, 0.23),
        mat_bone("armL", "chest", (-0.320, 0.740 - 0.68, 0.060), (-1, -1, 1), 0.21, 0.15),
        mat_bone("armR", "chest", (0.320, 0.740 - 0.68, 0.060), (1, -1, 1), 0.21, 0.15),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.28, "crouch_d": 0.100, "land_d": 0.120, "squash": 1.12,
              "gaze_yaw": -0.32, "chest_yaw": 0.45, "leg_squash": 0.70, "leg_len": 0.20,
              "up_scale": 1.0, "breath": 1.0, "sway": 0.9, "lid_close": 1.65})

    def extras(clip, t, dur, ph):
        b = ph["breath"]
        lag = ph["lag_up"]
        imp = ph["impact"]
        happy = ph["happy"]
        ear_flap = 0.16 * b + 0.38 * happy + 0.38 * imp - 2.4 * lag
        trunk_wave = 0.22 * b - 2.8 * lag + 0.62 * happy
        out = {
            "earL": {"r": (0.0, 0.0, -ear_flap)},
            "earR": {"r": (0.0, 0.0, ear_flap)},
            "trunk.01": {"r": (0.11 * b - 0.95 * lag, 0.0, 0.15 * ph["gaze"])},
            "trunk.02": {"r": (0.16 * b - 1.5 * lag, 0.0, 0.0)},
            "trunk.03": {"r": (trunk_wave, 0.0, 0.0)},
        }
        return out

    return Char("gaja", "Gaja", "The Heavyweight Anchor", "jumbo mochi baby elephant mascot with floppy ears and squishy pot belly", M, P, props, extras, bones, ["#8FA6CE", "#A4B9DC", "#F4B6CD", "#FFF9E6"], 1.85).finish(parts)

# ============================================================== 2 · MAYUR ======
def build_mayur():
    """
    MAYUR — Peacock chick with Pip's lathed teardrop blades (Audited by AI MAX & AI B).
    Architecture & Fixes:
    - 11 Lathed Teardrop Fan Blades (Pip methodology: lathed teardrop flattened into blade).
    - Mochi's 5-lobe cluster at base of tail to hide joints and provide plush organic volume.
    - 3-feather crown crest with lathed teardrop jewels.
    - Boba eyes with warm amber iris, pupil depth, dual catchlights, and cheek blush.
    """
    M = dict(shared_mats())
    M.update({
        "body_teal": dict(color=srgb("#247285"), roughness=0.50, metallic=0.0, texture="ceramic"),
        "fan_emerald": dict(color=srgb("#0097A7"), roughness=0.25, metallic=0.0),
        "fan_gold": dict(color=srgb("#E4B74C"), roughness=0.30, metallic=0.70),
        "fan_indigo": dict(color=srgb("#0A1F44"), roughness=0.18, metallic=0.30),
        "beak": dict(color=srgb("#FFCC80"), roughness=0.40, metallic=0.0),
        "lid": dict(color=srgb("#1D6070"), roughness=0.45, metallic=0.0),
        "eye_iris": dict(color=srgb("#A56A1E"), roughness=0.25, metallic=0.0),
        "tail_base": dict(color=srgb("#1B5A6A"), roughness=0.45, metallic=0.0),
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

    # Plump teardrop chick body
    body = sphere(0.260, 0.270, 0.260, seg=22, rings=14, name="chick_body", mat="body_teal")
    body.move(0.0, 0.370, 0.0)
    body.tag("hips", "spine", "chest", "base")
    add(body)

    # Cute rounded head
    head = sphere(0.245, 0.255, 0.245, seg=22, rings=14, name="chick_head", mat="body_teal")
    head.move(0.0, 0.700, 0.030)
    head.tag("head", "neck")
    add(head)

    # 3 Distinct Pip teardrop crest stalks
    for ci, c_ang in enumerate((-0.28, 0.0, 0.28)):
        c_stem = tube([(0.0, 0.930, 0.040),
                       (math.sin(c_ang) * 0.085, 1.040, 0.030)], 0.009, radial=8,
                      name=f"crest_stem_{ci}", mat="fan_emerald")
        c_stem.tag("crest.top", "head")
        c_tip = teardrop_blade(length=0.070, width=0.028, thickness=0.012, seg=12, rings=6,
                               name=f"crest_tip_{ci}", mat="fan_indigo")
        c_tip.rotate(rz=-c_ang)
        c_tip.move(math.sin(c_ang) * 0.085, 1.050, 0.030)
        c_tip.tag("crest.top", "head")
        parts.extend([c_stem, c_tip])

    # Cute rounded beak
    beak = superellipsoid(0.046, 0.038, 0.075, e1=0.38, e2=0.38, seg=14, rings=8,
                          name="beak", mat="beak")
    beak.move(0.0, 0.660, 0.265)
    beak.tag("head")
    add(beak)

    # Soft side wings
    def wing(sgn):
        w = superellipsoid(0.038, 0.135, 0.175, e1=0.45, e2=0.50, seg=16, rings=10,
                           name="wing", mat="body_teal")
        w.rotate(ry=sgn * 0.32, rz=sgn * 0.22)
        w.move(sgn * 0.260, 0.430, -0.020)
        w.tag("chest")
        return w

    parts.extend(mirrored(wing))

    # Mochi 5-lobe cluster at base of tail fan
    parts.extend(lobe_cluster(center=(0.0, 0.420, -0.160), core_radius=(0.080, 0.080, 0.070),
                              num_lobes=5, lobe_rad=0.036, spread=0.055, name="tail_base_cluster", mat="tail_base"))

    # 11 Pip Lathed Teardrop Fan Blades with concentric eye-spots
    N_FEATHERS = 9
    for fi in range(N_FEATHERS):
        t_frac = fi / (N_FEATHERS - 1)
        theta = -1.35 + t_frac * 2.70
        rad = 0.580
        fx = math.sin(theta) * rad
        fy = 0.500 + math.cos(theta) * (rad * 0.82)
        fz = -0.175

        blade = teardrop_blade(length=0.280, width=0.082, thickness=0.020, seg=8, rings=5,
                               name=f"feather_{fi}", mat="fan_emerald")
        blade.rotate(rz=-theta)
        blade.move(fx, fy, fz)
        blade.tag("tailFan.L" if theta < -0.1 else ("tailFan.R" if theta > 0.1 else "tailFan_root"))
        parts.append(blade)

        # Concentric Gold & Indigo eye-spot disk
        spot_gold = superellipsoid(0.048, 0.068, 0.012, e1=0.45, e2=0.45, seg=12, rings=6,
                                   name=f"spot_g_{fi}", mat="fan_gold")
        spot_gold.rotate(rz=-theta)
        spot_gold.move(fx * 1.06, fy + math.cos(theta) * 0.07, fz + 0.014)
        spot_gold.tag("tailFan.L" if theta < -0.1 else ("tailFan.R" if theta > 0.1 else "tailFan_root"))

        spot_ind = sphere(0.024, 0.032, 0.010, seg=10, rings=6, name=f"spot_i_{fi}", mat="fan_indigo")
        spot_ind.rotate(rz=-theta)
        spot_ind.move(fx * 1.06, fy + math.cos(theta) * 0.07, fz + 0.020)
        spot_ind.tag("tailFan.L" if theta < -0.1 else ("tailFan.R" if theta > 0.1 else "tailFan_root"))
        parts.extend([spot_gold, spot_ind])

    # Big open expressive Boba eyes with recessed pupil & blush
    ex, ey = 0.110, 0.720
    parts.extend(eye_pair(shell, ex, ey, 0.065, 0.072, 0.040, M,
                          lid=(1.10, 0.35, 0.80), lid_lift=1.32, proud=0.80, lid_mat="lid",
                          iris_mat="eye_iris", has_blush=True))

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
                ["#247285", "#0097A7", "#E4B74C", "#FFCC80"], 1.15).finish(parts)

# ============================================================== 3 · DIYA ======
def build_diya():
    """
    DIYA — The Sacred Clay Lamp Mascot (char_diya_art.png target).
    - Chunky rounded terracotta pot body (#C86A45) with pinched pouring spout.
    - Thick rolled rim with carved geometric ring band (#9C482B).
    - Dynamic twisting sculpted teardrop flame (#FF8C00 -> #FFF176) floating over concave pool.
    - Sweet smiling boba face right on the pot wall with warm amber teardrop blush (#FF9D42).
    - Chubby rounded clay arms resting on lower belly, stubby tripod clay feet nubs.
    - Height: 0.88m (compact, adorable warmth).
    """
    M = dict(shared_mats())
    M.update({
        "clay": dict(color=srgb("#C86A45"), roughness=0.68, metallic=0.0, texture="ceramic"),
        "clay_dark": dict(color=srgb("#9C482B"), roughness=0.72, metallic=0.0),
        "clay_light": dict(color=srgb("#D87B56"), roughness=0.62, metallic=0.0),
        "flame_core": dict(color=srgb("#FFF9D2"), roughness=0.20, metallic=0.0,
                           emissive=tuple(c * 1.5 for c in srgb("#FFF3A0"))),
        "flame_outer": dict(color=srgb("#FF7A18"), roughness=0.25, metallic=0.0,
                            emissive=tuple(c * 1.2 for c in srgb("#FF5E00"))),
        "oil_pool": dict(color=srgb("#6A4522"), roughness=0.18, metallic=0.0),
        "mouth_dark": dict(color=srgb("#4A1810"), roughness=0.50, metallic=0.0),
        "lid": dict(color=srgb("#B05835"), roughness=0.65, metallic=0.0),
        "eye_iris": dict(color=srgb("#4A2810"), roughness=0.15, metallic=0.0),
        "blush": dict(color=srgb("#FF9D42"), roughness=0.45, metallic=0.0,
                      emissive=tuple(c * 0.35 for c in srgb("#FF8A00"))),
        "badge_plate": dict(color=srgb("#FFF6E5"), roughness=0.35, metallic=0.0),
        "badge_rim": dict(color=srgb("#D4A050"), roughness=0.28, metallic=0.70),
    })
    parts = []
    shell = []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    # 1. 3 Stubby Tripod Clay Foot Nubs
    def tripod_foot(ang):
        fx = 0.22 * math.cos(ang)
        fz = 0.22 * math.sin(ang)
        f = superellipsoid(0.080, 0.055, 0.080, e1=0.40, e2=0.40, seg=16, rings=8,
                           name="foot_nub", mat="clay")
        f.move(fx, 0.045, fz)
        f.tag("legL" if fx < 0 else "legR")
        return f

    parts.append(tripod_foot(-math.pi * 0.70))
    parts.append(tripod_foot(-math.pi * 0.30))
    parts.append(tripod_foot(math.pi * 0.50))

    # 2. Chunky Rounded Terracotta Pot Body with Pinched Spout
    pot_profile = [
        (0.240, 0.070),
        (0.380, 0.160),
        (0.440, 0.290),  # Chubby pot belly
        (0.430, 0.420),
        (0.370, 0.530),  # Neck pinch
        (0.400, 0.570),  # Flared rim base
        (0.420, 0.600),  # Top rim outer
        (0.350, 0.600),  # Top rim inner
        (0.310, 0.550),  # Inner pool basin
        (0.000, 0.520)   # Basin center
    ]
    pot = lathe(pot_profile, seg=32, name="clay_pot", mat="clay")
    pot.tag("hips", "spine", "chest", "head")
    add(pot)

    # Pinched triangular pouring spout lip at front-top rim
    spout = superellipsoid(0.095, 0.045, 0.080, e1=0.35, e2=0.35, seg=14, rings=8,
                           name="spout_lip", mat="clay")
    spout.rotate(rx=math.radians(-18))
    spout.move(0.0, 0.610, 0.390)
    spout.tag("head")
    add(spout)

    # Carved geometric band ring around upper rim
    rim_band = torus(0.405, 0.016, seg_major=28, seg_minor=6, name="rim_band", mat="clay_dark")
    rim_band.move(0.0, 0.550, 0.0)
    rim_band.tag("head")
    parts.append(rim_band)

    # Inner warm molten oil pool surface
    oil = ngon_prism(0.320, 24, 0.020, name="oil_surface", mat="oil_pool")
    oil.move(0.0, 0.535, 0.0)
    oil.tag("head")
    parts.append(oil)

    # 3. Dynamic Twisting Sculpted Teardrop Flame (#FF8C00 -> #FFF176)
    flame_pts = [
        (0.0, 0.540, 0.020),
        (0.0, 0.640, 0.030),
        (0.015, 0.760, 0.010),
        (-0.020, 0.880, -0.015),
        (0.010, 0.980, 0.010),
        (0.0, 1.060, 0.000),
    ]
    flame_outer = tube(flame_pts, 0.125, radial=18, name="flame_outer", mat="flame_outer",
                       taper=[0.60, 1.0, 0.82, 0.55, 0.30, 0.08])
    flame_outer.tag("head")
    parts.append(flame_outer)

    flame_core = tube(flame_pts[:4], 0.075, radial=14, name="flame_core", mat="flame_core",
                      taper=[0.50, 1.0, 0.70, 0.25])
    flame_core.tag("head")
    parts.append(flame_core)

    # 4. Chubby Clay Arms Resting on Lower Belly
    def clay_arm(sgn):
        a = tube([(sgn * 0.380, 0.360, 0.040),
                  (sgn * 0.390, 0.260, 0.180),
                  (sgn * 0.250, 0.220, 0.340)], 0.062, radial=14, name="arm", mat="clay",
                 taper=[1.0, 0.94, 0.85])
        a.tag("armL" if sgn < 0 else "armR", "chest")
        paw = sphere(0.055, 0.048, 0.052, seg=14, rings=8, name="paw", mat="clay")
        paw.move(sgn * 0.250, 0.220, 0.340)
        paw.tag("armL" if sgn < 0 else "armR", "chest")
        return [a, paw]

    parts.extend(mirrored(clay_arm))

    # 5. Sweet Smiling Boba Eyes on Pot Wall
    ex, ey = 0.125, 0.380
    parts.extend(eye_pair(shell, ex, ey, 0.068, 0.075, 0.042, M,
                          lid=(1.10, 0.35, 0.80), lid_lift=1.35, proud=0.80, lid_mat="lid",
                          iris_mat="eye_iris", has_blush=False))

    # Sweet subtle mouth beneath spout
    mouth = superellipsoid(0.042, 0.024, 0.025, e1=0.45, e2=0.45, seg=12, rings=6,
                           name="mouth", mat="mouth_dark")
    mouth.move(0.0, 0.315, 0.435)
    mouth.tag("head")
    parts.append(mouth)

    # Glowing Teardrop Blush under left eye (per char_diya_art.png)
    tear_blush = superellipsoid(0.026, 0.040, 0.020, e1=0.35, e2=0.35, seg=12, rings=6,
                                name="tear_blush", mat="blush")
    tear_blush.rotate(rz=math.radians(-15))
    tear_blush.move(0.245, 0.340, 0.380)
    tear_blush.tag("head")
    parts.append(tear_blush)

    # 6. Blank Rounded Badge Plate with Warm Gold Rim
    poly = rounded_rect_poly(0.180, 0.095, 0.028, seg=8)
    parts.extend(conform_plate(shell, poly, 0.210, thickness=0.016, proud=0.012,
                               rim=1.12, rim_proud=0.008, name="badge"))
    pz = (probe_z(shell, 0.0, 0.210) or 0.42) + 0.012

    props = dict(hipY=0.10, spineY=0.22, chestY=0.36, neckY=0.45, headY=0.58,
                 legX=0.180, legY=0.04, baseY=0.02, badgeY=0.210, badgeZ=pz,
                 eyeX=ex, eyeY=ey, eyeZ=(probe_z(shell, ex, ey) or 0.42),
                 r_hips=0.42, r_spine=0.42, r_chest=0.40, r_neck=0.36, r_head=0.38,
                 r_base=0.26, r_leg=0.08, badge_size=[0.180, 0.095])

    bones = [
        mat_bone("flame.01", "head", (0.0, 0.650 - 0.58, 0.020), (0, 1, 0), 0.15, 0.16),
        mat_bone("flame.02", "flame.01", (0.0, 0.180, 0.0), (0, 1, 0), 0.15, 0.14),
        mat_bone("flame.03", "flame.02", (0.0, 0.180, 0.0), (0, 1, 0), 0.15, 0.12),
        mat_bone("armL", "chest", (-0.380, 0.360 - 0.36, 0.040), (-1, -1, 1), 0.18, 0.14),
        mat_bone("armR", "chest", (0.380, 0.360 - 0.36, 0.040), (1, -1, 1), 0.18, 0.14),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.24, "crouch_d": 0.080, "land_d": 0.095, "squash": 1.15,
              "gaze_yaw": -0.30, "chest_yaw": 0.40, "leg_squash": 0.75, "leg_len": 0.10,
              "up_scale": 1.0, "breath": 1.0, "sway": 0.8, "lid_close": 1.65})

    def extras(clip, t, dur, ph):
        b = ph["breath"]
        lag = ph["lag_up"]
        imp = ph["impact"]
        flame_flicker = 0.20 * math.sin(b * 2.0 * math.pi) + 0.35 * b - 2.5 * lag
        out = {
            "flame.01": {"r": (0.08 * b - 0.8 * lag, 0.0, 0.15 * math.sin(b * 2.0 * math.pi))},
            "flame.02": {"r": (0.12 * b - 1.4 * lag, 0.0, -0.22 * math.cos(b * 2.0 * math.pi))},
            "flame.03": {"r": (flame_flicker, 0.0, 0.25 * math.sin(b * 4.0 * math.pi))},
        }
        return out

    return Char("diya", "Diya", "The Sacred Hearth",
                "chunky pinched terracotta oil lamp with glowing sculpted flame and teardrop blush",
                M, P, props, extras, bones,
                ["#C86A45", "#9C482B", "#FF8C00", "#FFF176"], 0.92).finish(parts)

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
    KUMBHA — The Sacred Golden Kalash Mascot (char_kumbha_art.png target).
    - Spherical polished brass body (#D4AF37, Metallic 0.85).
    - Authentic coconut dome (nariyal) with pointed fibrous husk tip (#6E4023).
    - 5 radiating curved mango leaves (aam ke patte) (#2E7D32).
    - Lotus bas-relief embossing around mid-belly.
    - Articulated chubby brass arms waving joyfully, flared ornamental pedestal feet.
    - Height: 1.12m.
    """
    M = dict(shared_mats())
    M.update({
        "brass": dict(color=srgb("#E2B852"), roughness=0.24, metallic=0.88, texture="metal"),
        "brass_dark": dict(color=srgb("#B0882A"), roughness=0.32, metallic=0.85),
        "brass_light": dict(color=srgb("#F5D77F"), roughness=0.20, metallic=0.90),
        "coconut": dict(color=srgb("#6E4023"), roughness=0.82, metallic=0.0, texture="weave"),
        "coconut_fiber": dict(color=srgb("#542E16"), roughness=0.88, metallic=0.0),
        "leaf": dict(color=srgb("#2E7D32"), roughness=0.38, metallic=0.0),
        "leaf_light": dict(color=srgb("#4CAF50"), roughness=0.35, metallic=0.0),
        "mouth_dark": dict(color=srgb("#4A2810"), roughness=0.45, metallic=0.0),
        "lid": dict(color=srgb("#C49E3A"), roughness=0.30, metallic=0.70),
        "eye_iris": dict(color=srgb("#362010"), roughness=0.15, metallic=0.0),
        "badge_plate": dict(color=srgb("#FFF6E5"), roughness=0.35, metallic=0.0),
        "badge_rim": dict(color=srgb("#B0882A"), roughness=0.25, metallic=0.85),
    })
    parts = []
    shell = []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    # 1. Flared Ornamental Pedestal Feet
    def pedestal_foot(sgn):
        f = superellipsoid(0.110, 0.045, 0.125, e1=0.35, e2=0.35, seg=16, rings=8,
                           name="pedestal_foot", mat="brass_dark")
        f.move(sgn * 0.185, 0.040, 0.010)
        f.tag("legL" if sgn < 0 else "legR")

        stem = capsule(0.065, 0.110, seg=14, rings=6, name="foot_stem", mat="brass")
        stem.move(sgn * 0.185, 0.110, 0.0)
        stem.tag("legL" if sgn < 0 else "legR")

        ring = torus(0.075, 0.016, seg_major=16, seg_minor=6, name="foot_ring", mat="brass_light")
        ring.move(sgn * 0.185, 0.060, 0.0)
        ring.tag("legL" if sgn < 0 else "legR")
        return [f, stem, ring]

    parts.extend(mirrored(pedestal_foot))

    # 2. Spherical Golden Brass Kalash Pot Body
    pot_profile = [
        (0.180, 0.120),  # Flared round base
        (0.340, 0.220),
        (0.440, 0.360),
        (0.460, 0.480),  # Max spherical belly
        (0.410, 0.600),
        (0.310, 0.690),  # Narrow pot neck
        (0.340, 0.720),  # Neck collar flare
        (0.410, 0.750),  # Flared top rim lip
        (0.350, 0.750),  # Inner rim
        (0.240, 0.720),  # Inner throat
        (0.000, 0.700)
    ]
    pot = lathe(pot_profile, seg=32, name="kalash_pot", mat="brass")
    pot.tag("hips", "spine", "chest", "head")
    add(pot)

    # Ornamental neck filigree torus
    neck_ring = torus(0.335, 0.018, seg_major=24, seg_minor=6, name="neck_ring", mat="brass_light")
    neck_ring.move(0.0, 0.710, 0.0)
    neck_ring.tag("head")
    parts.append(neck_ring)

    # Lotus bas-relief ring around mid-belly
    for li, lang in enumerate(range(0, 360, 45)):
        rad = math.radians(lang)
        lx = 0.455 * math.cos(rad)
        lz = 0.455 * math.sin(rad)
        petal = superellipsoid(0.045, 0.065, 0.018, e1=0.35, e2=0.35, seg=12, rings=6,
                               name=f"lotus_petal_{li}", mat="brass_light")
        petal.rotate(ry=-rad, rx=math.radians(10))
        petal.move(lx, 0.450, lz)
        petal.tag("chest")
        parts.append(petal)

    # 3. 5 Radiating Mango Leaves (Aam ke Patte)
    for mi, mang in enumerate((-65, -32, 0, 32, 65)):
        rad = math.radians(mang)
        leaf = superellipsoid(0.055, 0.160, 0.018, e1=0.35, e2=0.35, seg=14, rings=8,
                              name=f"mango_leaf_{mi}", mat="leaf")
        leaf.rotate(rx=math.radians(18), rz=math.radians(-mang * 0.45), ry=rad)
        leaf.move(0.260 * math.sin(rad), 0.810, 0.260 * math.cos(rad) * 0.50)
        leaf.tag("head")
        parts.append(leaf)

    # 4. Fibrous Pointed Coconut Dome (Nariyal)
    coconut_profile = [
        (0.220, 0.740),
        (0.250, 0.820),
        (0.230, 0.920),
        (0.160, 1.020),
        (0.080, 1.100),
        (0.010, 1.160),
        (0.000, 1.170)
    ]
    coconut = lathe(coconut_profile, seg=24, name="coconut_dome", mat="coconut")
    coconut.tag("head")
    parts.append(coconut)

    # Pointed fiber tuft on top of coconut
    fiber_tuft = superellipsoid(0.024, 0.060, 0.024, e1=0.35, e2=0.35, seg=10, rings=6,
                                name="coconut_tuft", mat="coconut_fiber")
    fiber_tuft.move(0.0, 1.180, 0.0)
    fiber_tuft.tag("head")
    parts.append(fiber_tuft)

    # 5. Articulated Chubby Brass Arms (Right arm waving, Left arm resting)
    arm_r = tube([(0.390, 0.480, 0.020),
                  (0.480, 0.580, 0.120),
                  (0.460, 0.720, 0.180)], 0.055, radial=14, name="arm_wave", mat="brass",
                 taper=[1.0, 0.92, 0.85])
    arm_r.tag("armR", "chest")
    parts.append(arm_r)
    hand_r = superellipsoid(0.055, 0.050, 0.040, e1=0.35, e2=0.35, seg=14, rings=8,
                            name="hand_r", mat="brass_light")
    hand_r.move(0.460, 0.730, 0.190)
    hand_r.tag("armR", "chest")
    parts.append(hand_r)

    arm_l = tube([(-0.390, 0.480, 0.020),
                  (-0.440, 0.360, 0.140),
                  (-0.350, 0.280, 0.240)], 0.055, radial=14, name="arm_rest", mat="brass",
                 taper=[1.0, 0.92, 0.85])
    arm_l.tag("armL", "chest")
    parts.append(arm_l)
    hand_l = superellipsoid(0.050, 0.045, 0.040, e1=0.35, e2=0.35, seg=14, rings=8,
                            name="hand_l", mat="brass_light")
    hand_l.move(-0.350, 0.280, 0.240)
    hand_l.tag("armL", "chest")
    parts.append(hand_l)

    # 6. Smiling Boba Face Embossed on Brass Wall
    ex, ey = 0.125, 0.500
    parts.extend(eye_pair(shell, ex, ey, 0.068, 0.075, 0.040, M,
                          lid=(1.10, 0.35, 0.80), lid_lift=1.35, proud=0.80, lid_mat="lid",
                          iris_mat="eye_iris", has_blush=False))

    # Cute nose button & warm mouth
    nose = sphere(0.022, 0.018, 0.020, seg=12, rings=6, name="nose", mat="brass_light")
    nose.move(0.0, 0.470, 0.465)
    nose.tag("head")
    parts.append(nose)

    mouth = superellipsoid(0.045, 0.022, 0.020, e1=0.45, e2=0.45, seg=12, rings=6,
                           name="mouth", mat="mouth_dark")
    mouth.move(0.0, 0.420, 0.455)
    mouth.tag("head")
    parts.append(mouth)

    # 7. Blank Cream Belly Badge with Filigree Brass Frame
    poly = rounded_rect_poly(0.190, 0.095, 0.028, seg=8)
    parts.extend(conform_plate(shell, poly, 0.310, thickness=0.018, proud=0.014,
                               rim=1.12, rim_proud=0.010, name="badge"))
    pz = (probe_z(shell, 0.0, 0.310) or 0.44) + 0.014

    props = dict(hipY=0.15, spineY=0.32, chestY=0.48, neckY=0.65, headY=0.85,
                 legX=0.185, legY=0.08, baseY=0.04, badgeY=0.310, badgeZ=pz,
                 eyeX=ex, eyeY=ey, eyeZ=(probe_z(shell, ex, ey) or 0.44),
                 r_hips=0.44, r_spine=0.46, r_chest=0.44, r_neck=0.34, r_head=0.38,
                 r_base=0.28, r_leg=0.08, badge_size=[0.190, 0.095])

    bones = [
        mat_bone("armL", "chest", (-0.390, 0.480 - 0.48, 0.020), (-1, -1, 1), 0.20, 0.14),
        mat_bone("armR", "chest", (0.390, 0.480 - 0.48, 0.020), (1, 1, 1), 0.20, 0.14),
        mat_bone("leaf.01", "head", (0.0, 0.810 - 0.85, 0.150), (0, 1, 1), 0.15, 0.14),
        mat_bone("leaf.02", "head", (-0.20, 0.810 - 0.85, 0.0), (-1, 1, 0), 0.15, 0.14),
        mat_bone("leaf.03", "head", (0.20, 0.810 - 0.85, 0.0), (1, 1, 0), 0.15, 0.14),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.25, "crouch_d": 0.085, "land_d": 0.100, "squash": 1.12,
              "gaze_yaw": -0.32, "chest_yaw": 0.42, "leg_squash": 0.72, "leg_len": 0.12,
              "up_scale": 1.0, "breath": 1.0, "sway": 0.85, "lid_close": 1.65})

    def extras(clip, t, dur, ph):
        b = ph["breath"]
        lag = ph["lag_up"]
        happy = ph["happy"]
        wave = 0.35 * math.sin(ph["breath"] * 2.0 * math.pi) + 0.45 * happy
        out = {
            "armR": {"r": (0.0, 0.0, wave)},
            "leaf.01": {"r": (0.10 * b - 0.8 * lag, 0.0, 0.0)},
            "leaf.02": {"r": (0.0, 0.0, -0.12 * b + 0.8 * lag)},
            "leaf.03": {"r": (0.0, 0.0, 0.12 * b - 0.8 * lag)},
        }
        return out

    return Char("kumbha", "Kumbha", "The Golden Vessel",
                "sacred golden kalash pot with fibrous coconut dome, mango leaves and lotus filigree",
                M, P, props, extras, bones,
                ["#E2B852", "#B0882A", "#6E4023", "#2E7D32"], 1.10).finish(parts)

# ============================================================== 6 · GRANTHA ===
def build_grantha():
    """
    GRANTHA — The Living Manuscript Mascot (char_grantha_art.png target).
    - Thick stacked palm-leaf folio with layered parchment striations (#E8D5B5).
    - Carved dark teak-wood top and bottom cover boards (#4A2E1B) with brass corner brackets (#C49E3A).
    - Wrapped ceremonial red cords (#A32020) with dangling golden brass bells (#E2B852).
    - Cheerful wise face carved into parchment center.
    - Holding a peacock quill pen in right hand, wearing traditional paduka shoes.
    - Height: 1.15m.
    """
    M = dict(shared_mats())
    M.update({
        "wood": dict(color=srgb("#4A2E1B"), roughness=0.62, metallic=0.0, texture="weave"),
        "wood_carve": dict(color=srgb("#361E10"), roughness=0.70, metallic=0.0),
        "brass": dict(color=srgb("#C49E3A"), roughness=0.26, metallic=0.85, texture="metal"),
        "parchment": dict(color=srgb("#E4D2B2"), roughness=0.75, metallic=0.0, texture="cord"),
        "parchment_edge": dict(color=srgb("#C8B28D"), roughness=0.80, metallic=0.0),
        "cord": dict(color=srgb("#A32020"), roughness=0.55, metallic=0.0, texture="cord"),
        "bell": dict(color=srgb("#E2B852"), roughness=0.22, metallic=0.88),
        "peacock_blue": dict(color=srgb("#1B5E55"), roughness=0.35, metallic=0.0),
        "mouth_dark": dict(color=srgb("#361E10"), roughness=0.50, metallic=0.0),
        "lid": dict(color=srgb("#C8B28D"), roughness=0.65, metallic=0.0),
        "eye_iris": dict(color=srgb("#4A2C18"), roughness=0.15, metallic=0.0),
        "badge_plate": dict(color=srgb("#FFF6E5"), roughness=0.35, metallic=0.0),
        "badge_rim": dict(color=srgb("#4A2E1B"), roughness=0.45, metallic=0.0),
    })
    parts = []
    shell = []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    # 1. Carved Wooden Paduka Slippers
    def paduka_foot(sgn):
        sole = superellipsoid(0.090, 0.035, 0.140, e1=0.35, e2=0.35, seg=14, rings=8,
                              name="paduka_sole", mat="wood")
        sole.move(sgn * 0.175, 0.035, 0.020)
        sole.tag("legL" if sgn < 0 else "legR")

        leg = capsule(0.055, 0.100, seg=12, rings=6, name="paduka_leg", mat="wood")
        leg.move(sgn * 0.175, 0.110, 0.0)
        leg.tag("legL" if sgn < 0 else "legR")

        knob = sphere(0.020, 0.024, 0.020, seg=10, rings=6, name="paduka_knob", mat="brass")
        knob.move(sgn * 0.175, 0.070, 0.090)
        knob.tag("legL" if sgn < 0 else "legR")
        return [sole, leg, knob]

    parts.extend(mirrored(paduka_foot))

    # 2. Carved Teak Base Board
    base_board = superellipsoid(0.380, 0.045, 0.280, e1=0.20, e2=0.20, seg=18, rings=8,
                                name="base_board", mat="wood")
    base_board.move(0.0, 0.175, 0.0)
    base_board.tag("hips", "base")
    add(base_board)

    # 3. Stacked Palm-Leaf Pages (Central Folio Block)
    # We model 3 tiered slabs to simulate layered leaf striations
    page_block = superellipsoid(0.350, 0.280, 0.250, e1=0.25, e2=0.25, seg=24, rings=12,
                                name="page_block", mat="parchment")
    page_block.move(0.0, 0.510, 0.0)
    page_block.tag("spine", "chest", "head")
    add(page_block)

    # Page edge side striation trims
    def page_trim(sgn):
        t = superellipsoid(0.030, 0.270, 0.245, e1=0.20, e2=0.20, seg=14, rings=8,
                           name="page_edge", mat="parchment_edge")
        t.move(sgn * 0.355, 0.510, 0.0)
        t.tag("spine", "chest")
        return t

    parts.extend(mirrored(page_trim))

    # 4. Carved Teak Top Cover Board with Brass Corner Brackets
    top_board = superellipsoid(0.380, 0.045, 0.280, e1=0.20, e2=0.20, seg=18, rings=8,
                               name="top_board", mat="wood")
    top_board.move(0.0, 0.825, 0.0)
    top_board.tag("head")
    add(top_board)

    # 4 Brass Corner Caps on top board
    for cx in (-0.360, 0.360):
        for cz in (-0.260, 0.260):
            cap = superellipsoid(0.040, 0.024, 0.040, e1=0.20, e2=0.20, seg=10, rings=6,
                                 name="brass_cap", mat="brass")
            cap.move(cx, 0.835, cz)
            cap.tag("head")
            parts.append(cap)

    # 5. Wrapped Red Ceremonial Binding Cords with Hanging Brass Bells
    cord_h = tube([(-0.385, 0.420, 0.260),
                   (0.385, 0.420, 0.260)], 0.016, radial=10, name="cord_h", mat="cord")
    cord_h.tag("spine")
    parts.append(cord_h)

    cord_v = tube([(0.280, 0.835, 0.270),
                   (0.280, 0.175, 0.270)], 0.016, radial=10, name="cord_v", mat="cord")
    cord_v.tag("chest")
    parts.append(cord_v)

    # Dangling brass jingle bells
    bell1 = superellipsoid(0.026, 0.040, 0.026, e1=0.35, e2=0.35, seg=12, rings=6,
                           name="bell1", mat="bell")
    bell1.move(0.280, 0.350, 0.285)
    bell1.tag("chest")
    parts.append(bell1)

    bell2 = superellipsoid(0.022, 0.034, 0.022, e1=0.35, e2=0.35, seg=10, rings=6,
                           name="bell2", mat="bell")
    bell2.move(0.320, 0.320, 0.285)
    bell2.tag("chest")
    parts.append(bell2)

    # 6. Chubby Arms holding Peacock Feather Quill
    # Right arm holding quill upright
    arm_r = tube([(0.370, 0.450, 0.020),
                  (0.420, 0.400, 0.160),
                  (0.360, 0.440, 0.280)], 0.048, radial=12, name="arm_quill", mat="wood",
                 taper=[1.0, 0.92, 0.85])
    arm_r.tag("armR", "chest")
    parts.append(arm_r)

    quill_stem = capsule(0.012, 0.160, seg=10, rings=4, name="quill_stem", mat="wood")
    quill_stem.rotate(rx=math.radians(20))
    quill_stem.move(0.360, 0.480, 0.290)
    quill_stem.tag("armR")
    parts.append(quill_stem)

    feather = superellipsoid(0.042, 0.090, 0.012, e1=0.35, e2=0.35, seg=12, rings=6,
                             name="quill_feather", mat="peacock_blue")
    feather.rotate(rx=math.radians(20))
    feather.move(0.360, 0.580, 0.320)
    feather.tag("armR")
    parts.append(feather)

    # Left arm resting on book side
    arm_l = tube([(-0.370, 0.450, 0.020),
                  (-0.410, 0.380, 0.120),
                  (-0.360, 0.360, 0.220)], 0.048, radial=12, name="arm_left", mat="wood",
                 taper=[1.0, 0.92, 0.85])
    arm_l.tag("armL", "chest")
    parts.append(arm_l)

    # 7. Wise Cheerful Face Embedded in Parchment Block
    ex, ey = 0.125, 0.590
    parts.extend(eye_pair(shell, ex, ey, 0.065, 0.075, 0.038, M,
                          lid=(1.10, 0.35, 0.80), lid_lift=1.35, proud=0.80, lid_mat="lid",
                          iris_mat="eye_iris", has_blush=False))

    mouth = superellipsoid(0.055, 0.026, 0.022, e1=0.45, e2=0.45, seg=12, rings=6,
                           name="mouth", mat="mouth_dark")
    mouth.move(0.0, 0.490, 0.255)
    mouth.tag("head")
    parts.append(mouth)

    # 8. Blank Display Plate centered on lower book base
    poly = rounded_rect_poly(0.200, 0.085, 0.024, seg=8)
    parts.extend(conform_plate(shell, poly, 0.280, thickness=0.016, proud=0.014,
                               rim=1.10, rim_proud=0.008, name="badge"))
    pz = (probe_z(shell, 0.0, 0.280) or 0.26) + 0.014

    props = dict(hipY=0.18, spineY=0.38, chestY=0.55, neckY=0.72, headY=0.82,
                 legX=0.175, legY=0.08, baseY=0.04, badgeY=0.280, badgeZ=pz,
                 eyeX=ex, eyeY=ey, eyeZ=(probe_z(shell, ex, ey) or 0.26),
                 r_hips=0.38, r_spine=0.36, r_chest=0.36, r_neck=0.36, r_head=0.38,
                 r_base=0.28, r_leg=0.06, badge_size=[0.200, 0.085])

    bones = [
        mat_bone("armL", "chest", (-0.370, 0.450 - 0.55, 0.020), (-1, -1, 1), 0.18, 0.14),
        mat_bone("armR", "chest", (0.370, 0.450 - 0.55, 0.020), (1, 1, 1), 0.18, 0.14),
        mat_bone("bell", "chest", (0.280, 0.350 - 0.55, 0.285), (0, -1, 0), 0.10, 0.12),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.22, "crouch_d": 0.075, "land_d": 0.090, "squash": 1.10,
              "gaze_yaw": -0.28, "chest_yaw": 0.38, "leg_squash": 0.75, "leg_len": 0.10,
              "up_scale": 1.0, "breath": 1.0, "sway": 0.8, "lid_close": 1.65})

    def extras(clip, t, dur, ph):
        b = ph["breath"]
        lag = ph["lag_up"]
        happy = ph["happy"]
        bell_swing = 0.25 * math.sin(b * 2.0 * math.pi) + 0.40 * happy - 1.5 * lag
        out = {
            "bell": {"r": (0.0, 0.0, bell_swing)},
            "armR": {"r": (0.12 * b, 0.0, 0.20 * math.sin(b * 2.0 * math.pi))},
        }
        return out

    return Char("grantha", "Grantha", "The Ancient Codex",
                "living palm-leaf manuscript with carved teak covers, peacock quill and brass bells",
                M, P, props, extras, bones,
                ["#E4D2B2", "#4A2E1B", "#C49E3A", "#A32020"], 1.15).finish(parts)

# ============================================================== 7 · DHANESH ===
def build_dhanesh():
    """
    DHANESH — Great Indian Hornbill mascot (Audited by AI MAX & AI B).
    Architecture & Fixes:
    - Sleek aerodynamic bird body (Pip/Meera lineage) leaning slightly forward.
    - Prominent arched golden casque helmet swept backward as continuous crown anatomy.
    - Ivory curved bill with downward arc and subtle orange base tint.
    - Ruby eye-ring contour and Pip feathery brow tufts.
    - Layered black-and-white fanned wings and long banded tail feathers.
    """
    M = dict(shared_mats())
    M.update({
        "feather_black": dict(color=srgb("#1A1A1F"), roughness=0.55, metallic=0.0),
        "feather_white": dict(color=srgb("#F0EDE5"), roughness=0.55, metallic=0.0),
        "casque_gold": dict(color=srgb("#D4A020"), roughness=0.25, metallic=0.75),
        "bill_ivory": dict(color=srgb("#F0E0C0"), roughness=0.35, metallic=0.0),
        "bill_accent": dict(color=srgb("#E8A040"), roughness=0.40, metallic=0.0),
        "eye_ring": dict(color=srgb("#CC1111"), roughness=0.30, metallic=0.0),
        "mouth_dark": dict(color=srgb("#3A1810"), roughness=0.45, metallic=0.0),
        "lid": dict(color=srgb("#1A1A1F"), roughness=0.55, metallic=0.0),
        "eye_iris": dict(color=srgb("#8B4500"), roughness=0.25, metallic=0.0),
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

    # White chest bib (Mochi overlapping lobe methodology)
    parts.extend(lobe_cluster(center=(0.0, 0.500, 0.210), core_radius=(0.140, 0.180, 0.060),
                              num_lobes=7, lobe_rad=0.045, spread=0.080, name="white_bib", mat="feather_white"))

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

    # Massive curved Hornbill Bill (Pip teardrop blade curvature)
    bill_upper = teardrop_blade(length=0.520, width=0.085, thickness=0.055, seg=16, rings=8,
                                name="bill_upper", mat="bill_ivory")
    bill_upper.rotate(rx=1.65)
    bill_upper.move(0.0, 0.930, 0.220)
    bill_upper.tag("head", "beak_tip")
    add(bill_upper, False)

    bill_lower = teardrop_blade(length=0.420, width=0.065, thickness=0.045, seg=14, rings=6,
                                name="bill_lower", mat="bill_accent")
    bill_lower.rotate(rx=1.60)
    bill_lower.move(0.0, 0.860, 0.200)
    bill_lower.tag("head", "beak_tip")
    parts.append(bill_lower)

    # Arched Golden Casque Helmet sitting proudly on top of head & bill
    casque = teardrop_blade(length=0.480, width=0.095, thickness=0.065, seg=16, rings=8,
                            name="casque_horn", mat="casque_gold")
    casque.rotate(rx=1.75)
    casque.move(0.0, 1.080, 0.160)
    casque.tag("head", "casque_horn")
    add(casque, False)

    # Ruby eye-rings around eye sockets
    def eye_ring(sgn):
        r = torus(0.058, 0.009, seg_major=20, seg_minor=8, name="ruby_eye_ring", mat="eye_ring")
        r.move(sgn * 0.115, 0.985, 0.190)
        r.tag("head")
        return r

    parts.extend(mirrored(eye_ring))

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

    # Big open expressive Boba eyes with amber iris
    ex, ey = 0.115, 0.985
    parts.extend(eye_pair(shell, ex, ey, 0.055, 0.062, 0.035, M,
                          lid=(1.10, 0.35, 0.80), lid_lift=1.35, proud=0.80, lid_mat="lid",
                          iris_mat="eye_iris", has_blush=False))

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
                ["#1A1A1F", "#F0EDE5", "#D4A020", "#F0E0C0"], 1.38).finish(parts)


# ============================================================== 8 · SALYA =====
def build_salya():
    """
    SALYA — The Armored Pangolin Mascot (char_pangolin_art.png target).
    - Honey-amber keratin scales (#D99538) arranged in overlapping shingle rows.
    - Soft cream fur belly and face (#F5E6CC).
    - Clasped "namaste" praying paws in front.
    - Thick armored tapering tail resting on floor behind.
    - Sweet innocent boba eyes with soft muzzle nose.
    - Height: 0.85m.
    """
    M = dict(shared_mats())
    M.update({
        "scale_amber": dict(color=srgb("#D99538"), roughness=0.38, metallic=0.0, texture="ceramic"),
        "scale_dark": dict(color=srgb("#B26D1E"), roughness=0.42, metallic=0.0),
        "fur_cream": dict(color=srgb("#F5E6CC"), roughness=0.72, metallic=0.0),
        "nose_snout": dict(color=srgb("#7A4526"), roughness=0.55, metallic=0.0),
        "claw": dict(color=srgb("#E4D2B2"), roughness=0.40, metallic=0.0),
        "mouth_dark": dict(color=srgb("#3A1A10"), roughness=0.50, metallic=0.0),
        "lid": dict(color=srgb("#D99538"), roughness=0.50, metallic=0.0),
        "eye_iris": dict(color=srgb("#2E1C0E"), roughness=0.15, metallic=0.0),
        "badge_plate": dict(color=srgb("#FFF6E5"), roughness=0.35, metallic=0.0),
        "badge_rim": dict(color=srgb("#B26D1E"), roughness=0.28, metallic=0.75),
    })
    parts = []
    shell = []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    # 1. Stubby Pangolin Feet with Tiny Claws
    def pangolin_foot(sgn):
        foot = superellipsoid(0.095, 0.045, 0.125, e1=0.35, e2=0.35, seg=14, rings=8,
                              name="foot", mat="scale_dark")
        foot.move(sgn * 0.155, 0.040, 0.020)
        foot.tag("legL" if sgn < 0 else "legR")

        leg_col = capsule(0.080, 0.140, seg=14, rings=6, name="leg_col", mat="scale_amber")
        leg_col.move(sgn * 0.155, 0.130, 0.0)
        leg_col.tag("legL" if sgn < 0 else "legR")

        # 3 tiny rounded claws
        claws = []
        for ci, cang in enumerate((-0.24, 0.0, 0.24)):
            claw = superellipsoid(0.016, 0.014, 0.026, e1=0.35, e2=0.35, seg=10, rings=4,
                                  name=f"claw_{ci}", mat="claw")
            claw.move(sgn * (0.155 + cang * 0.065), 0.020, 0.135)
            claw.tag("legL" if sgn < 0 else "legR")
            claws.append(claw)
        return [foot, leg_col] + claws

    parts.extend(mirrored(pangolin_foot))

    # 2. Heavy Tapering Armored Tail Resting on Floor Behind
    tail_pts = [
        (0.0, 0.280, -0.150),
        (0.0, 0.220, -0.320),
        (0.0, 0.140, -0.500),
        (0.0, 0.060, -0.680),
        (0.0, 0.035, -0.800)
    ]
    tail = tube(tail_pts, 0.140, radial=14, name="armored_tail", mat="scale_amber",
                taper=[1.0, 0.85, 0.65, 0.40, 0.18])
    tail.tag("base", "hips")
    parts.append(tail)

    # 3. Chubby Torso with Cream Fur Belly
    belly_profile = [
        (0.180, 0.140),
        (0.290, 0.240),
        (0.350, 0.380),  # Max belly
        (0.340, 0.520),
        (0.280, 0.640),
        (0.210, 0.740),
        (0.150, 0.800)
    ]
    belly = lathe(belly_profile, seg=24, name="pangolin_body", mat="scale_amber")
    belly.tag("hips", "spine", "chest", "head")
    add(belly)

    # Cream Fur Belly Inset Plate
    fur_chest = superellipsoid(0.230, 0.260, 0.140, e1=0.45, e2=0.45, seg=16, rings=8,
                               name="fur_chest", mat="fur_cream")
    fur_chest.move(0.0, 0.420, 0.220)
    fur_chest.tag("spine", "chest")
    parts.append(fur_chest)

    # 4. Head with Soft Cream Muzzle and Snout
    head = sphere(0.260, 0.240, 0.250, seg=22, rings=14, name="head", mat="scale_amber")
    head.move(0.0, 0.860, 0.060)
    head.tag("head")
    add(head)

    muzzle = superellipsoid(0.140, 0.110, 0.150, e1=0.40, e2=0.40, seg=14, rings=8,
                            name="muzzle", mat="fur_cream")
    muzzle.move(0.0, 0.820, 0.240)
    muzzle.tag("head")
    parts.append(muzzle)

    nose_snout = sphere(0.038, 0.026, 0.030, seg=12, rings=6, name="nose", mat="nose_snout")
    nose_snout.move(0.0, 0.840, 0.365)
    nose_snout.tag("head")
    parts.append(nose_snout)

    # Small rounded ears
    def pangolin_ear(sgn):
        e = superellipsoid(0.022, 0.045, 0.035, e1=0.45, e2=0.45, seg=10, rings=6,
                           name="ear", mat="fur_cream")
        e.move(sgn * 0.240, 0.920, -0.020)
        e.rotate(ry=sgn * 0.40, rz=sgn * 0.20)
        e.tag("head")
        return e

    parts.extend(mirrored(pangolin_ear))

    # 5. Overlapping Honey-Amber Keratin Shingle Scales on Back & Head
    for ring_i, ry_pos in enumerate((0.30, 0.42, 0.54, 0.66, 0.78, 0.90, 0.98)):
        num_s = 5 + ring_i
        rad_scale = 0.32 - ring_i * 0.025
        for si in range(num_s):
            ang = -math.pi * 0.75 + (si / max(1, num_s - 1)) * math.pi * 1.50
            sx = rad_scale * math.sin(ang)
            sz = -rad_scale * math.cos(ang) * 0.85
            sc = superellipsoid(0.045, 0.065, 0.016, e1=0.35, e2=0.35, seg=10, rings=5,
                                name=f"scale_{ring_i}_{si}", mat="scale_amber")
            sc.rotate(rx=math.radians(-25), ry=-ang)
            sc.move(sx, ry_pos, sz)
            sc.tag("chest" if ry_pos < 0.75 else "head")
            parts.append(sc)

    # 6. Clasped "Namaste" Paws in Front
    def clasped_arm(sgn):
        a = tube([(sgn * 0.260, 0.620, 0.060),
                  (sgn * 0.240, 0.540, 0.220),
                  (sgn * 0.070, 0.550, 0.310)], 0.052, radial=12, name="arm_clasped", mat="scale_amber",
                 taper=[1.0, 0.92, 0.85])
        a.tag("armL" if sgn < 0 else "armR", "chest")

        paw = superellipsoid(0.045, 0.055, 0.040, e1=0.35, e2=0.35, seg=12, rings=6,
                             name="clasped_paw", mat="fur_cream")
        paw.rotate(rz=sgn * math.radians(25))
        paw.move(sgn * 0.050, 0.560, 0.320)
        paw.tag("armL" if sgn < 0 else "armR", "chest")
        return [a, paw]

    parts.extend(mirrored(clasped_arm))

    # 7. Big Sweet Boba Eyes
    ex, ey = 0.115, 0.880
    parts.extend(eye_pair(shell, ex, ey, 0.062, 0.068, 0.038, M,
                          lid=(1.10, 0.35, 0.80), lid_lift=1.35, proud=0.80, lid_mat="lid",
                          iris_mat="eye_iris", has_blush=False))

    # 8. Blank Belly Badge Conformed to Fur Belly
    poly = rounded_rect_poly(0.170, 0.095, 0.026, seg=8)
    parts.extend(conform_plate(shell, poly, 0.350, thickness=0.016, proud=0.014,
                               rim=1.12, rim_proud=0.008, name="badge"))
    pz = (probe_z(shell, 0.0, 0.350) or 0.34) + 0.014

    props = dict(hipY=0.18, spineY=0.35, chestY=0.55, neckY=0.72, headY=0.86,
                 legX=0.155, legY=0.08, baseY=0.04, badgeY=0.350, badgeZ=pz,
                 eyeX=ex, eyeY=ey, eyeZ=(probe_z(shell, ex, ey) or 0.32),
                 r_hips=0.35, r_spine=0.35, r_chest=0.32, r_neck=0.26, r_head=0.26,
                 r_base=0.26, r_leg=0.08, badge_size=[0.170, 0.095])

    bones = [
        mat_bone("armL", "chest", (-0.260, 0.620 - 0.55, 0.060), (-1, -1, 1), 0.18, 0.14),
        mat_bone("armR", "chest", (0.260, 0.620 - 0.55, 0.060), (1, -1, 1), 0.18, 0.14),
        mat_bone("tail.01", "base", (0.0, 0.220 - 0.04, -0.320), (0, -1, -1), 0.20, 0.16),
        mat_bone("tail.02", "tail.01", (0.0, -0.10, -0.250), (0, 0, -1), 0.20, 0.14),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.22, "crouch_d": 0.075, "land_d": 0.095, "squash": 1.14,
              "gaze_yaw": -0.30, "chest_yaw": 0.40, "leg_squash": 0.72, "leg_len": 0.12,
              "up_scale": 1.0, "breath": 1.0, "sway": 0.85, "lid_close": 1.65})

    def extras(clip, t, dur, ph):
        b = ph["breath"]
        lag = ph["lag_up"]
        imp = ph["impact"]
        happy = ph["happy"]
        tail_lift = 0.15 * b - 1.8 * lag + 0.35 * imp
        out = {
            "tail.01": {"r": (tail_lift, 0.0, 0.10 * math.sin(b * 2.0 * math.pi))},
            "tail.02": {"r": (0.5 * tail_lift, 0.0, 0.15 * math.sin(b * 2.0 * math.pi))},
            "armL": {"r": (0.08 * b, 0.0, 0.10 * happy)},
            "armR": {"r": (0.08 * b, 0.0, -0.10 * happy)},
        }
        return out

    return Char("salya", "Salya", "The Scaled Sentinel",
                "armored honey-amber pangolin with overlapping shingle scales and namaste hands",
                M, P, props, extras, bones,
                ["#D99538", "#B26D1E", "#F5E6CC", "#E4D2B2"], 0.88).finish(parts)

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

ROSTER_ORDER = ["gaja", "mayur", "diya", "patra", "kumbha", "grantha", "dhanesh", "salya"]
