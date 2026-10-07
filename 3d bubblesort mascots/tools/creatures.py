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

    return Char("gaja", "Gaja", "The Heavyweight Anchor",
                "jumbo mochi baby elephant mascot with floppy ears and squishy pot belly",
                M, P, props, extras, bones,
                ["#8FA6CE", "#A4B9DC", "#F4B6CD", "#FFF9E6"], 1.30).finish(parts)

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
    DIYA — Terracotta oil lamp with living sculpted flame crest (Audited by AI MAX & AI B).
    Architecture & Fixes:
    - Handcrafted earthen bowl with pinched pouring spout and soft rounded rim.
    - 3 Nested Translucent Flame Lobes (Core, Mantle, Outer) built with Pip's lathed teardrops.
    - Warm glowing amber cheek ember with emissive subsurface warmth.
    - Cute hugging clay arms pulled organically from the body.
    - Boba eyes with warm amber iris, pupil depth, dual catchlights, and blush.
    """
    M = dict(shared_mats())
    M.update({
        "clay": dict(color=srgb("#C86A4A"), roughness=0.85, metallic=0.0, texture="ceramic",
                     emissive=tuple(c * 0.12 for c in srgb("#4A1A00"))),
        "clay_dark": dict(color=srgb("#8C4325"), roughness=0.88, metallic=0.0),
        "flame_outer": dict(color=srgb("#FF4400"), roughness=0.25, metallic=0.0, alpha=0.85,
                            emissive=tuple(c * 0.90 for c in srgb("#FF8C1A"))),
        "flame_mantle": dict(color=srgb("#FF8C00"), roughness=0.20, metallic=0.0, alpha=0.90,
                             emissive=tuple(c * 1.60 for c in srgb("#FF7500"))),
        "flame_core": dict(color=srgb("#FFF4D6"), roughness=0.10, metallic=0.0,
                           emissive=tuple(c * 2.80 for c in srgb("#FFE9A8"))),
        "ember": dict(color=srgb("#FF6A2B"), roughness=0.30, metallic=0.0,
                      emissive=tuple(c * 1.80 for c in srgb("#FF4500"))),
        "mouth_dark": dict(color=srgb("#602512"), roughness=0.50, metallic=0.0),
        "lid": dict(color=srgb("#A85533"), roughness=0.75, metallic=0.0),
        "eye_iris": dict(color=srgb("#FF8C00"), roughness=0.25, metallic=0.0),
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

    # Terracotta lamp bowl body (lathe with thick hand-crafted rounded rim)
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

    # 3 Nested Pip Lathed Teardrop Flame Lobes (Core, Mantle, Outer)
    flame_outer = teardrop_blade(length=0.480, width=0.140, thickness=0.085, seg=18, rings=10,
                                 name="flame_outer", mat="flame_outer")
    flame_outer.move(0.0, 0.510, 0.0)
    flame_outer.tag("flame_tip", "flame_base", "head")
    add(flame_outer, False)

    flame_mantle = teardrop_blade(length=0.380, width=0.105, thickness=0.065, seg=16, rings=8,
                                  name="flame_mantle", mat="flame_mantle")
    flame_mantle.move(0.0, 0.520, 0.005)
    flame_mantle.tag("flame_tip", "flame_base", "head")
    add(flame_mantle, False)

    flame_core = teardrop_blade(length=0.250, width=0.070, thickness=0.045, seg=14, rings=6,
                                name="flame_core", mat="flame_core")
    flame_core.move(0.0, 0.530, 0.010)
    flame_core.tag("flame_tip", "flame_base", "head")
    add(flame_core, False)

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

    # Big warm friendly Boba eyes with amber iris & blush
    ex, ey = 0.110, 0.335
    parts.extend(eye_pair(shell, ex, ey, 0.062, 0.068, 0.040, M,
                          lid=(1.10, 0.35, 0.80), lid_lift=1.35, proud=0.80, lid_mat="lid",
                          iris_mat="eye_iris", has_blush=True))

    # Blank cream badge on lower belly
    poly = rounded_rect_poly(0.180, 0.100, 0.028, seg=6)
    parts.extend(conform_plate(shell, poly, 0.155, thickness=0.018, proud=0.013,
                               rim=1.10, rim_proud=0.008, name="badge"))
    pz = (probe_z(shell, 0.0, 0.155) or 0.29) + 0.013

    props = dict(hipY=0.15, spineY=0.25, chestY=0.35, neckY=0.44, headY=0.55,
                 legX=0.150, legY=0.06, baseY=0.04, badgeY=0.155, badgeZ=pz,
                 eyeX=ex, eyeY=ey, eyeZ=(probe_z(shell, ex, ey) or 0.30),
                 r_hips=0.32, r_spine=0.32, r_chest=0.30, r_neck=0.26, r_head=0.28,
                 r_base=0.28, r_leg=0.08, badge_size=[0.180, 0.100])

    bones = [
        mat_bone("flame_base", "head", (0.0, 0.510 - 0.55, 0.0), (0, 1, 0), 0.18, 0.16),
        mat_bone("flame_tip", "flame_base", (0.0, 0.260, 0.0), (0, 1, 0), 0.20, 0.14),
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
                ["#C86A4A", "#FF4400", "#FF8C00", "#FFF4D6"], 1.02).finish(parts)

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
    KUMBHA — Golden Kalasha pot with mango leaves & coconut (Audited by AI MAX & AI B).
    Architecture & Fixes:
    - High-polish sacred temple brass body with engraved neck relief ring and hand-hammered bulges.
    - 5 Pip Lathed Teardrop Mango Leaves arranged in a radiating collar with midrib folds.
    - Coconut with Mochi fibrous coir tufts and organic surface texture.
    - Wise, serene Boba eyes with emerald iris, pupil depth, dual catchlights, and blush.
    """
    M = dict(shared_mats())
    M.update({
        "brass": dict(color=srgb("#D4AF37"), roughness=0.25, metallic=0.95),
        "brass_dark": dict(color=srgb("#A68020"), roughness=0.35, metallic=0.92),
        "mango_leaf": dict(color=srgb("#2E8B57"), roughness=0.55, metallic=0.0),
        "coconut": dict(color=srgb("#5C4033"), roughness=0.88, metallic=0.0, texture="stone"),
        "tuft_light": dict(color=srgb("#8B6834"), roughness=0.90, metallic=0.0),
        "mouth_dark": dict(color=srgb("#553810"), roughness=0.45, metallic=0.15),
        "lid": dict(color=srgb("#C49E30"), roughness=0.30, metallic=0.85),
        "eye_iris": dict(color=srgb("#2A4A20"), roughness=0.25, metallic=0.0),
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

    # Lathed ornate Kalasha pot belly with authentic urn profile
    pot_profile = [
        (0.140, 0.045),
        (0.240, 0.110),
        (0.330, 0.230),
        (0.355, 0.360),
        (0.320, 0.500),
        (0.245, 0.580),
        (0.195, 0.620),
        (0.245, 0.660)
    ]
    pot = lathe(pot_profile, seg=42, name="kalasha_pot", mat="brass")
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

    # Textured fibrous coconut nestled in center
    coconut = superellipsoid(0.130, 0.185, 0.130, e1=0.48, e2=0.48, seg=26, rings=18,
                             name="coconut", mat="coconut")
    coconut.move(0.0, 0.810, 0.0)
    coconut.tag("head", "coconut_top")
    add(coconut, False)

    # 3-tier curved fibrous coir tufts (Kumbha's hair)
    for ti, tang in enumerate((-0.20, 0.0, 0.20)):
        tuft = teardrop_blade(length=0.100, width=0.032, thickness=0.016, seg=12, rings=6,
                              name=f"tuft_{ti}", mat="tuft_light")
        tuft.rotate(rz=-tang)
        tuft.move(math.sin(tang) * 0.025, 0.970, 0.0)
        tuft.tag("head", "coconut_top")
        parts.append(tuft)

    # 5 Pip Lathed Teardrop Mango Leaves cupping the coconut collar
    N_LEAVES = 5
    for li in range(N_LEAVES):
        l_ang = li * (TAU / N_LEAVES)
        leaf = teardrop_blade(length=0.240, width=0.078, thickness=0.022, seg=16, rings=8,
                              name=f"mango_leaf_{li}", mat="mango_leaf")
        leaf.rotate(rx=0.62)
        leaf.rotate(ry=l_ang)
        lx = math.sin(l_ang) * 0.190
        lz = math.cos(l_ang) * 0.190
        leaf.move(lx, 0.720, lz)
        leaf.tag("head", "leaf_crown")
        parts.append(leaf)

    # Sweet open smile on brass belly
    mouth = superellipsoid(0.046, 0.028, 0.024, e1=0.45, e2=0.45, seg=16, rings=8,
                           name="mouth", mat="mouth_dark")
    mouth.move(0.0, 0.315, 0.355)
    mouth.tag("head")
    parts.append(mouth)

    # Big open serene Boba eyes with emerald iris & blush
    ex, ey = 0.115, 0.395
    parts.extend(eye_pair(shell, ex, ey, 0.065, 0.072, 0.040, M,
                          lid=(1.10, 0.35, 0.80), lid_lift=1.35, proud=0.80, lid_mat="lid",
                          iris_mat="eye_iris", has_blush=True))

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
        mat_bone("leaf_crown", "head", (0.0, 0.720 - 0.64, 0.0), (0, 1, 0), 0.14, 0.25),
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
                ["#D4AF37", "#A68020", "#2E8B57", "#5C4033"], 1.05).finish(parts)

# ============================================================== 6 · GRANTHA ===
def build_grantha():
    """
    GRANTHA — Ancient Vedic Palm-Leaf Manuscript creature (Audited by AI MAX & AI B).
    Architecture & Fixes:
    - Carved dark teak wood covers with rounded beveled edges that act like clapping hands.
    - Fanned palm-leaf / birch-bark folio pages with layered fibrous edges.
    - Braided crimson silk cord with dangling brass jingle bells.
    - Springy peacock feather quill pen tucked into the spine binding.
    - Boba eyes on front cover with indigo/ink iris, pupil depth, dual catchlights, and blush.
    """
    M = dict(shared_mats())
    M.update({
        "teak_wood": dict(color=srgb("#4A3018"), roughness=0.65, metallic=0.0, texture="ceramic"),
        "palm_leaf": dict(color=srgb("#F5E6D3"), roughness=0.80, metallic=0.0),
        "cord_red": dict(color=srgb("#B71C1C"), roughness=0.45, metallic=0.0),
        "bell_brass": dict(color=srgb("#D4AF37"), roughness=0.20, metallic=0.95),
        "quill_teal": dict(color=srgb("#004B49"), roughness=0.30, metallic=0.10),
        "quill_gold": dict(color=srgb("#D4A548"), roughness=0.25, metallic=0.70),
        "quill_shaft": dict(color=srgb("#FFF8E7"), roughness=0.25, metallic=0.0),
        "mouth_dark": dict(color=srgb("#3A1A08"), roughness=0.50, metallic=0.0),
        "lid": dict(color=srgb("#4A3018"), roughness=0.65, metallic=0.0),
        "eye_iris": dict(color=srgb("#3A2A80"), roughness=0.20, metallic=0.0),
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

    # Top carved wooden manuscript cover (acting like clapping hands)
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
        bell = teardrop_blade(length=0.045, width=0.022, thickness=0.022, seg=10, rings=5,
                              name="brass_bell", mat="bell_brass")
        bell.move(-0.080 + sgn * 0.025, 0.690, 0.135)
        bell.tag("head", "cord_tassel")
        return [stem, bell]

    parts.extend(mirrored(tassel_bell))

    # Ornate peacock feather quill pen tucked into the top binding (Pip Teardrop methodology)
    quill_shaft = capsule(0.009, 0.380, seg=10, rings=4, name="quill_shaft", mat="quill_shaft")
    quill_shaft.rotate(rz=-0.35, rx=0.15)
    quill_shaft.move(0.120, 0.950, -0.040)
    quill_shaft.tag("head", "quill_pen")
    parts.append(quill_shaft)

    # Peacock feather vane
    quill_vane = teardrop_blade(length=0.180, width=0.055, thickness=0.014, seg=14, rings=6,
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

    # Big open expressive Boba eyes with deep indigo iris & blush
    ex, ey = 0.095, 0.585
    parts.extend(eye_pair(shell, ex, ey, 0.055, 0.065, 0.035, M,
                          lid=(1.10, 0.35, 0.80), lid_lift=1.35, proud=0.80, lid_mat="lid",
                          iris_mat="eye_iris", has_blush=True))

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
                ["#4A3018", "#F5E6D3", "#B71C1C", "#004B49"], 1.15).finish(parts)


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
    SALYA — Indian Scaled Pangolin mascot (Audited by AI MAX & AI B).
    Architecture & Fixes:
    - 5 Rows of Overlapping Low-Poly Curved Shield Scales (Mochi's lobe methodology).
    - Smooth cream underbelly contrasting against golden keratin armor.
    - Upturned curious snout with pink sniffing nose button.
    - Tapered curled muscular armored tail designed for spring-bounce kinematics.
    - Boba eyes with dark iris, recessed pupil depth, dual catchlights, and blush.
    """
    M = dict(shared_mats())
    M.update({
        "scale_amber": dict(color=srgb("#FF8C00"), roughness=0.20, metallic=0.0,
                            emissive=tuple(c * 0.15 for c in srgb("#FF8F00"))),
        "scale_edge": dict(color=srgb("#FFD54F"), roughness=0.25, metallic=0.10),
        "skin_belly": dict(color=srgb("#FFF3E0"), roughness=0.75, metallic=0.0),
        "claw_dark": dict(color=srgb("#3A3020"), roughness=0.40, metallic=0.0),
        "nose_pink": dict(color=srgb("#F48FB1"), roughness=0.50, metallic=0.0),
        "mouth_dark": dict(color=srgb("#553518"), roughness=0.45, metallic=0.0),
        "lid": dict(color=srgb("#D48010"), roughness=0.35, metallic=0.0),
        "eye_iris": dict(color=srgb("#1A1A15"), roughness=0.15, metallic=0.0),
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

    # Chubby pear-shaped torso (soft cream underbelly)
    body = lathe([(0.140, 0.140), (0.240, 0.240), (0.310, 0.380), (0.315, 0.540),
                  (0.260, 0.680), (0.190, 0.780)], seg=32, name="pangolin_body", mat="skin_belly")
    body.tag("hips", "spine", "chest", "base")
    add(body)

    # 5 Tiers of Overlapping Shingled Pinecone Scales (Pip & Mochi Teardrop Lobe Method)
    scale_configs = [
        (0.780, 0.240, 0.35, 5, 0.120),
        (0.680, 0.290, 0.25, 6, 0.135),
        (0.540, 0.320, 0.10, 7, 0.145),
        (0.380, 0.310, -0.05, 6, 0.140),
        (0.240, 0.270, -0.20, 5, 0.125),
    ]
    for row_i, (sy, sz, srx, n_scales, s_rad) in enumerate(scale_configs):
        for si in range(n_scales):
            s_frac = (si / max(1, n_scales - 1)) - 0.5
            sx = s_frac * (s_rad * 2.2)
            blade = teardrop_blade(length=0.140, width=0.065, thickness=0.022, seg=12, rings=6,
                                   name=f"scale_{row_i}_{si}", mat="scale_amber")
            blade.rotate(rx=srx, ry=-s_frac * 0.45)
            blade.move(sx, sy, -0.060 - row_i * 0.035)
            blade.tag("spine" if row_i < 3 else "hips")
            parts.append(blade)

    # Scaled helmet hood over head
    hood = superellipsoid(0.220, 0.140, 0.190, e1=0.40, e2=0.40, seg=22, rings=10,
                          name="scale_hood", mat="scale_amber")
    hood.rotate(rx=0.20)
    hood.move(0.0, 0.900, -0.030)
    hood.tag("head", "scale_hood")
    add(hood)

    # Curious upturned snout
    snout_pts = [
        (0.0, 0.860, 0.120),
        (0.0, 0.840, 0.250),
        (0.0, 0.810, 0.380),
        (0.0, 0.790, 0.460),
    ]
    snout = tube(snout_pts, 0.090, radial=16, name="snout", mat="skin_belly",
                 taper=[1.0, 0.85, 0.60, 0.35])
    snout.tag("head")
    add(snout, False)

    # Pink sniffing button nose
    nose = sphere(0.032, 0.026, 0.026, seg=12, rings=8, name="nose", mat="nose_pink")
    nose.move(0.0, 0.790, 0.475)
    nose.tag("head")
    parts.append(nose)

    # Muscular curled armored tail at back (key ball-spring anatomy)
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

    # Shy, endearing Boba eyes with recessed pupil & blush
    ex, ey = 0.105, 0.850
    parts.extend(eye_pair(shell, ex, ey, 0.055, 0.062, 0.035, M,
                          lid=(1.10, 0.35, 0.80), lid_lift=1.35, proud=0.80, lid_mat="lid",
                          iris_mat="eye_iris", has_blush=True))

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
                ["#FF8C00", "#FFD54F", "#FFF3E0", "#F48FB1"], 0.92).finish(parts)


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
