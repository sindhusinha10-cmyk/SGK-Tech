"""
creatures — the five Bubble-Sort Squadders.

Design rules followed by every character (see ../README.md for the full rationale):

  * Y-up, front = +Z, origin on the ground, one shared 14-bone core skeleton
  * one blank un-deformed badge plate on the chest for the website's number label
  * the same eye construction (dark lens + cream catchlight + chunky lid) so the
    family reads as one set without being recolours of one model
  * a single saturated pop colour (celadon/mint) shared across the roster
  * silhouette first: every design differs in height, width, mass distribution,
    face arrangement, appendages and surface material

Nothing here is derived from an existing character, franchise or asset pack — the
forms come from non-character objects so no familiar creature template is reused.
"""

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


# Shared family materials — identical in every file so the set looks lit the same.
def shared_mats():
    return {
        "eye_dark": dict(color=srgb("#17171C"), roughness=0.10, metallic=0.0),
        "eye_glint": dict(color=srgb("#FFF7E9"), roughness=0.28, metallic=0.0,
                          emissive=tuple(c * 0.55 for c in srgb("#FFF1D8"))),
        "badge": dict(color=srgb("#F7F2E8"), roughness=0.52, metallic=0.0, texture="matte"),
        "badge_rim": dict(color=srgb("#B08A4A"), roughness=0.34, metallic=0.85, texture=None),
        "pop": dict(color=srgb("#6FD9BE"), roughness=0.30, metallic=0.15,
                    emissive=tuple(c * 0.30 for c in srgb("#6FD9BE"))),
    }


def mat_bone(name, parent, offset, dirv=(0, 1, 0), length=0.10, radius=0.16, group="extra"):
    return Bone(name, parent, offset, w_dir=dirv, w_len=length, w_radius=radius, group=group)


# ------------------------------------------------------------------- helpers
def probe_z(parts, x, y, z_start=3.0):
    """Frontmost surface z at (x, y) by raycasting along -Z.

    Faces and badge plates must sit ON the body surface, not inside it — bodies
    here are revolves, so a constant z would bury the eyes inside the silhouette.
    """
    import numpy as _np
    o = _np.array([x, y, z_start], dtype=_np.float64)
    d = _np.array([0.0, 0.0, -1.0])
    best = None
    for p in parts:
        if len(p.f) == 0:
            continue
        v0 = p.v[p.f[:, 0]]; v1 = p.v[p.f[:, 1]]; v2 = p.v[p.f[:, 2]]
        e1 = v1 - v0; e2 = v2 - v0
        pv = _np.cross(d, e2)
        det = _np.einsum("ij,ij->i", e1, pv)
        ok = _np.abs(det) > 1e-12
        if not ok.any():
            continue
        inv = _np.zeros_like(det)
        inv[ok] = 1.0 / det[ok]
        tv = o[None, :] - v0
        u = _np.einsum("ij,ij->i", tv, pv) * inv
        qv = _np.cross(tv, e1)
        vv = _np.einsum("ij,j->i", qv, d) * inv
        t = _np.einsum("ij,ij->i", e2, qv) * inv
        m = ok & (u >= 0) & (u <= 1) & (vv >= 0) & (u + vv <= 1) & (t > 1e-6)
        if m.any():
            z = z_start - float(t[m].min())
            if best is None or z > best:
                best = z
    return best


def on_surface(parts, x, y, out, fallback=0.25):
    z = probe_z(parts, x, y)
    if z is None:
        z = fallback
    return z - out




def eye_pair(shell, cx, cy, rx, ry, rz, M, lid=(1.15, 0.62, 0.80), lid_lift=1.15,
             proud=0.70, yaw=0.0, glint=0.32, brow_lift=0.0):
    """The family eye, mounted on whatever surface `shell` presents at (+-cx, cy).

    Dark lens + cream catchlight + a chunky lid that rests *above* the lens (a
    flap, not a cap) and sweeps down over it when the lid bone rotates. `proud`
    is the fraction of the lens standing out of the body so no eye is ever buried.
    """
    parts = []
    for side, sgn, bone in (("L", -1.0, "eyeL"), ("R", 1.0, "eyeR")):
        zf = probe_z(shell, sgn * cx, cy)
        if zf is None:
            zf = 0.25
        cz = zf - rz * (1.0 - proud)
        e = sphere(rx, ry, rz, seg=26, rings=14, name="eye" + side, mat="eye_dark")
        e.move(sgn * cx, cy, cz)
        if yaw:
            e.rotate(ry=sgn * yaw)
        e.tag(bone)
        parts.append(e)
        g = sphere(rx * glint, ry * glint, rz * glint, seg=16, rings=9,
                   name="glint" + side, mat="eye_glint")
        g.move(sgn * (cx - 0.30 * rx), cy + 0.36 * ry, cz + rz * 0.80)
        g.tag(bone)
        parts.append(g)

        lr, ly, lz = rx * lid[0], ry * lid[1], rz * lid[2]
        lidp = superellipsoid(lr, ly, lz, e1=0.58, e2=0.58, seg=22, rings=13,
                              name="lid" + side, mat="lid")
        # rest position: the lid's lower edge overlaps only the top ~30% of the lens
        lidp.move(sgn * cx, cy + lid_lift * ly + brow_lift, cz + lz * 0.35)
        lidp.tag("lid" + side)
        parts.append(lidp)
    return parts


def eye_ring(shell, cx, cy, rx, ry, mat="eye_dark", thickness=0.016, proud=0.004, lift=0.0,
             name="ring"):
    """A flat dark ring behind each eye — extra read for eyes on soft or
    translucent bodies, where a bare dark lens can wash out."""
    out = []
    for side, sgn, bone in (("L", -1.0, "eyeL"), ("R", 1.0, "eyeR")):
        zf = probe_z(shell, sgn * cx, cy) or 0.25
        r = superellipsoid(rx, ry, thickness, e1=0.5, e2=0.5, seg=26, rings=14,
                           name=name + side, mat=mat)
        r.move(sgn * cx, cy + lift, zf - thickness + proud)
        r.tag(bone)
        out.append(r)
    return out


def conform_plate(shell, poly, y, thickness=0.014, proud=0.009, mat="badge",
                  rim_mat="badge_rim", rim=1.12, rim_proud=0.006,
                  name="badge", cx=0.0, bone="badge"):
    """A flat plate that conforms to the body surface at height `y`.

    Samples the body's front z across the plate outline (with a margin, so the
    plate always clears the body's curvature) and builds a slightly domed plate.
    `cx` shifts the whole plate sideways, which is how the pair of visor eyes and
    the shutters are made to conform to ZAG's angular face.
    """
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


def mount_mouth(shell, x, y, part, proud=0.010):
    zf = probe_z(shell, x, y)
    part.move(x, y, (zf if zf is not None else 0.25) + proud)
    return part


def badge_plate(poly, thickness, pos, tilt=0.0, rim=1.12, rim_gap=0.010,
                rim_thickness=None, mats=None, tilt_y=0.0):
    """Legacy flat plate (kept for flat-fronted bodies)."""
    out = []
    rp = plate([(px * rim, py * rim) for px, py in poly], rim_thickness or thickness * 0.7,
               bevel=0.008, name="badge_rim", mat="badge_rim")
    rp.move(0, 0, -rim_gap)
    bp = plate(poly, thickness, bevel=min(thickness * 0.45, 0.012), name="badge_face", mat="badge")
    for p in (rp, bp):
        p.rotate(ry=tilt_y)
        p.rotate(rx=tilt)
        p.move(*pos)
        p.tag("badge")
        out.append(p)
    return out


def facet(p):
    return flat_normals(p)


def mirrored(part_fn):
    """Build a right-side part, then produce its mirrored twin."""
    a = part_fn(1.0)
    b = part_fn(-1.0)
    return [a, b]


# ============================================================== 1 · KILN =====
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
        if abs(lo[1]) > 1e-9:                     # plant every character on y = 0
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
            "badge_size": self.props.get("badge_size", [0.16, 0.10]),
            "clip_order": [c for c, _ in clips.CLIP_SPECS],
            "part_count": len(mesh.parts),
            "joint_count": len(self.skel.bones),
        })
        return self


def build_kiln():
    """KILN — a tall glazed ceramic kiln-pot. Narrow silhouette, chimney crown."""
    M = dict(shared_mats())
    M.update({
        "clay": dict(color=srgb("#BC6238"), roughness=0.62, metallic=0.0, texture="ceramic"),
        "glaze": dict(color=srgb("#F3E5CE"), roughness=0.16, metallic=0.02, texture="ceramic"),
        "indigo": dict(color=srgb("#2C3A5E"), roughness=0.22, metallic=0.04, texture="ceramic"),
        "lid": dict(color=srgb("#EFDFC4"), roughness=0.20, metallic=0.02),
    })
    parts = []
    shell = []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    # foot ring + pot body
    foot = lathe([(0.20, 0.0), (0.255, 0.012), (0.262, 0.055), (0.245, 0.075)],
                 seg=34, name="foot", mat="glaze")
    foot.tag("base")
    add(foot)
    belly = lathe([(0.245, 0.062), (0.288, 0.16), (0.318, 0.30), (0.325, 0.42),
                   (0.300, 0.55), (0.250, 0.66), (0.205, 0.735)],
                  seg=38, name="belly", mat="clay")
    belly.tag("hips", "spine", "chest", "base")
    add(belly)

    band = lathe([(0.202, 0.732), (0.222, 0.762), (0.216, 0.800), (0.190, 0.818)],
                 seg=38, name="band", mat="indigo")
    band.tag("chest")
    add(band)
    drip = lathe([(0.196, 0.800), (0.206, 0.812), (0.196, 0.824)], seg=38, name="drip", mat="pop")
    drip.tag("chest")
    add(drip)
    neck = lathe([(0.190, 0.812), (0.150, 0.845), (0.143, 0.905)], seg=34, name="neck", mat="glaze")
    neck.tag("chest", "neck")
    add(neck)

    dome = lathe([(0.143, 0.900), (0.170, 0.935), (0.186, 0.985), (0.181, 1.045),
                  (0.152, 1.098), (0.098, 1.140), (0.0, 1.168)],
                 seg=38, name="dome", mat="glaze")
    dome.tag("neck", "head")
    add(dome)
    collar = lathe([(0.062, 1.150), (0.070, 1.162), (0.062, 1.174)], seg=26, name="collar", mat="indigo")
    collar.tag("head")
    add(collar, False)
    chimney = lathe([(0.050, 1.150), (0.052, 1.280), (0.046, 1.300)], seg=26, name="chimney", mat="indigo")
    chimney.tag("crown")
    add(chimney, False)
    cap = lathe([(0.046, 1.298), (0.070, 1.318), (0.062, 1.340), (0.030, 1.352), (0.0, 1.356)],
                seg=26, name="cap", mat="pop")
    cap.tag("crown")
    add(cap, False)

    def handle(sgn):
        h = arc_tube((0, 0.470, 0.0), 0.118, -1.90, 1.90, 0.026, steps=16, plane="XY",
                     radial=10, name="handle", mat="clay")
        h.scale(1.0, 1.0, 0.85)
        h.move(sgn * 0.290, 0.0, 0.0)
        h.tag("handle" + ("L" if sgn < 0 else "R"))
        return h

    parts.extend(mirrored(handle))

    # ---- face, placed on the actual dome surface --------------------------
    ex, ey = 0.090, 0.998
    parts.extend(eye_pair(shell, ex, ey, 0.062, 0.078, 0.040, M,
                          lid=(1.02, 0.40, 0.92), lid_lift=1.32, proud=0.78))
    my = 0.888
    mouth = superellipsoid(0.070, 0.032, 0.024, e1=0.45, e2=0.45, seg=22, rings=12,
                           name="mouth", mat="indigo")
    parts.append(mount_mouth(shell, 0.0, my, mouth, proud=0.004))
    mouth_z = probe_z(shell, 0.0, my) or 0.25
    for i, dy in enumerate((-0.016, 0.0, 0.016)):
        bar = capsule(0.0075, 0.062, seg=12, rings=5, name="grate%d" % i, mat="glaze")
        bar.rotate(rz=np.pi * 0.5)
        bar.move(0, my + dy, mouth_z + 0.012)
        bar.tag("head")
        parts.append(bar)

    # ---- blank number badge, conforming to the belly ----------------------
    poly = hex_poly(0.118)
    parts.extend(conform_plate(shell, poly, 0.520, thickness=0.020, proud=0.014,
                               rim=1.15, rim_proud=0.008, name="badge"))
    bz = (probe_z(shell, 0.0, 0.520) or 0.30) + 0.014
    ez = (probe_z(shell, ex, ey) or 0.25)

    props = dict(hipY=0.30, spineY=0.48, chestY=0.72, neckY=0.86, headY=1.01,
                 legX=0.17, legY=0.05, baseY=0.03, badgeY=0.520, badgeZ=bz,
                 eyeX=ex, eyeY=ey, eyeZ=ez,
                 r_hips=0.30, r_spine=0.26, r_chest=0.24, r_neck=0.14, r_head=0.20,
                 r_base=0.26, r_leg=0.10, badge_size=[0.22, 0.19])

    bones = [
        mat_bone("crown", "head", (0.0, 1.150 - 1.01, 0.0), (0, 1, 0), 0.20, 0.09),
        mat_bone("handleL", "spine", (-0.290, 0.470 - 0.48, 0.0), (0, 1, 0), 0.10, 0.12),
        mat_bone("handleR", "spine", (0.290, 0.470 - 0.48, 0.0), (0, 1, 0), 0.10, 0.12),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.30, "crouch_d": 0.060, "land_d": 0.075, "squash": 1.15,
              "gaze_yaw": -0.42, "chest_yaw": 0.35, "legs": False, "leg_squash": 1.0,
              "up_scale": 0.62, "breath": 0.85, "sway": 0.8, "lid_close": 1.62})

    def extras(clip, t, dur, ph):
        b = ph["breath"]
        lag = ph["lag_up"]
        imp = ph["impact"]
        happy = ph["happy"]
        wob = 0.05 * b + 0.30 * np.sin(TAU * t * 1.6) * imp * 0.4
        crown = {"r": (wob - 8.0 * lag, 0.02 * b, 0.05 * ph["lean"])}
        if clip == "Success":
            crown["r"] = (crown["r"][0] - 0.16 * happy, 0.0,
                          0.10 * np.sin(TAU * t * 3.0) * happy)
            crown["s"] = (1.0 + 0.05 * happy,) * 3
        splay = 0.10 * imp + 0.16 * happy + 0.10 * abs(ph["shake"]) - 0.34 * lag
        if clip == "NoSwap":
            splay = 0.55 * ph["lean"] * 3.0
        hl = {"r": (0.0, 0.02 * b, +splay)}
        hr = {"r": (0.0, -0.02 * b, -splay)}
        return {"crown": crown, "handleL": hl, "handleR": hr}

    return Char("kiln", "Kiln", "The Terracotta Array Item",
                "glazed pottery with a whistle-chimney crown and loop handles",
                M, P, props, extras, bones,
                ["#BC6238", "#F3E5CE", "#2C3A5E", "#6FD9BE"], 1.36).finish(parts)


# ============================================================== 2 · RIBB =====
def build_ribb():
    """RIBB — a squat woven basket with two big loop handles and a tipping lid."""
    M = dict(shared_mats())
    M.update({
        "weave": dict(color=srgb("#C9A468"), roughness=0.72, metallic=0.0, texture="weave"),
        "weave_dk": dict(color=srgb("#9C7845"), roughness=0.78, metallic=0.0, texture="weave"),
        "cream": dict(color=srgb("#EFE2C6"), roughness=0.62, metallic=0.0, texture="weave"),
        "cord": dict(color=srgb("#AC5230"), roughness=0.60, metallic=0.0, texture="cord"),
        "lid": dict(color=srgb("#E8D9B6"), roughness=0.55, metallic=0.0, texture="weave"),
    })
    parts = []
    shell = []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    for sgn in (-1.0, 1.0):
        for zs in (1.0, -1.0):
            f = capsule(0.045, 0.010, seg=16, rings=6, name="foot", mat="weave_dk")
            f.move(sgn * 0.200, 0.046, zs * 0.148)
            f.tag("base")
            add(f, False)
    plinth = superellipsoid(0.300, 0.088, 0.245, e1=0.36, e2=0.42, seg=34, rings=18,
                            name="plinth", mat="weave_dk")
    plinth.move(0, 0.148, 0)
    plinth.tag("base")
    add(plinth)
    band = lathe([(0.292, 0.150), (0.310, 0.180), (0.296, 0.210)], seg=34, name="band", mat="cord")
    band.scale(1.0, 1.0, 0.84)
    band.tag("base")
    add(band)
    for i, zz in enumerate((-0.21, -0.07, 0.07, 0.21)):
        rib = torus(0.296, 0.011, seg_major=44, seg_minor=8, name="rib%d" % i, mat="cord")
        rib.scale(1.0, 1.0, 0.775)
        rib.move(0, 0.150, 0)
        rib.tag("base")
        add(rib, False)

    body = lathe([(0.268, 0.196), (0.306, 0.250), (0.325, 0.330), (0.328, 0.410),
                  (0.312, 0.472), (0.286, 0.520)],
                 seg=40, name="body", mat="weave")
    body.tag("hips", "spine", "chest", "head", "base")
    add(body)
    rib2 = lathe([(0.319, 0.300), (0.333, 0.330), (0.325, 0.362)], seg=40, name="body_rib", mat="cord")
    rib2.tag("spine")
    add(rib2, False)
    rim = lathe([(0.286, 0.512), (0.302, 0.536), (0.292, 0.566), (0.262, 0.586)],
                seg=40, name="rim", mat="cream")
    rim.tag("chest")
    add(rim)

    lid = lathe([(0.262, 0.580), (0.252, 0.640), (0.212, 0.700), (0.140, 0.742), (0.0, 0.762)],
                seg=40, name="lid_dome", mat="lid")
    lid.tag("head")
    add(lid)
    knot = sphere(0.052, 0.048, 0.052, seg=22, rings=14, name="knot", mat="cord")
    knot.move(0, 0.802, 0)
    knot.tag("lidKnot")
    add(knot, False)
    for i, (sgn, zz) in enumerate(((-1.0, 0.03), (1.0, -0.02))):
        tail = tube([(sgn * 0.02, 0.783, zz), (sgn * 0.056, 0.752, zz + 0.02),
                     (sgn * 0.080, 0.716, zz + 0.01), (sgn * 0.072, 0.688, zz - 0.02)],
                    0.012, radial=8, name="tail%d" % i, mat="cord")
        tail.tag("lidKnot")
        add(tail, False)

    def handle(sgn):
        h = arc_tube((0, 0.330, 0.0), 0.196, -1.34, 1.34, 0.031, steps=20, plane="XY",
                     radial=10, name="handle", mat="cord")
        h.scale(1.0, 1.0, 0.78)
        h.move(sgn * 0.296, 0.0, 0.0)
        h.tag("handle" + ("L" if sgn < 0 else "R"))
        return h

    parts.extend(mirrored(handle))

    # ---- face ------------------------------------------------------------
    by = 0.404
    ex = 0.086
    patches = eye_ring(shell, ex, by, 0.092, 0.094, mat="cream", thickness=0.052, proud=0.024,
                       name="patch")
    for pt in patches:
        pt.bones = ("head",)
    parts.extend(patches)
    parts.extend(eye_pair(patches, ex, by, 0.066, 0.070, 0.036, M,
                          lid=(1.50, 0.36, 1.04), lid_lift=1.30, proud=0.80))
    for i, dx in enumerate((-0.050, -0.017, 0.017, 0.050)):
        st = capsule(0.0080, 0.022, seg=10, rings=5, name="stitch%d" % i, mat="cord")
        st.move(dx, 0.288 + (0.007 if i % 2 else 0.0),
                (probe_z(shell, dx, 0.288) or 0.30) + 0.006)
        st.tag("chest")
        parts.append(st)

    poly = rounded_rect_poly(0.164, 0.104, 0.030, seg=6)
    parts.extend(conform_plate(shell, poly, 0.152, thickness=0.018, proud=0.013,
                               rim=1.11, rim_proud=0.008, name="badge"))
    pz = (probe_z(shell, 0.0, 0.152) or 0.30) + 0.013
    ez = (probe_z(patches, ex, by) or 0.25)

    props = dict(hipY=0.16, spineY=0.26, chestY=0.36, neckY=0.44, headY=0.50,
                 legX=0.205, legY=0.075, baseY=0.10, badgeY=0.152, badgeZ=pz,
                 eyeX=ex, eyeY=by, eyeZ=ez,
                 r_hips=0.34, r_spine=0.32, r_chest=0.30, r_neck=0.26, r_head=0.34,
                 r_base=0.30, r_leg=0.10, badge_size=[0.172, 0.114])

    bones = [
        mat_bone("lidKnot", "head", (0.0, 0.802 - 0.50, 0.0), (0, 1, 0), 0.10, 0.12),
        mat_bone("handleL", "chest", (-0.296, 0.330 - 0.36, 0.0), (0, 1, 0), 0.12, 0.14),
        mat_bone("handleR", "chest", (0.296, 0.330 - 0.36, 0.0), (0, 1, 0), 0.12, 0.14),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.24, "crouch_d": 0.055, "land_d": 0.070, "squash": 1.35,
              "gaze_yaw": -0.34, "chest_yaw": 0.45, "legs": False, "leg_squash": 1.0,
              "up_scale": 0.55, "breath": 1.05, "sway": 1.1, "lid_close": 1.90})

    def extras(clip, t, dur, ph):
        b = ph["breath"]
        lag = ph["lag_up"]
        imp = ph["impact"]
        happy = ph["happy"]
        knot = {"r": (0.05 * b - 4.2 * lag, 0.06 * b, 0.05 * ph["lean"] + 0.04 * ph["shake"])}
        if clip == "Success":
            knot["s"] = (1.0 + 0.16 * happy,) * 3
            knot["r"] = (knot["r"][0] - 0.24 * happy, 0.0,
                         0.10 * np.sin(TAU * t * 3.4) * happy)
        if clip == "NoSwap":
            knot["r"] = (0.08 + 0.30 * ph["lean"], 0.10 * ph["shake"], 0.0)
        fl = 0.16 * imp + 0.28 * happy + 0.20 * abs(ph["shake"]) - 3.4 * lag
        if clip == "NoSwap":
            fl = 0.72 * ph["lean"]
        hl = {"r": (0.06 * b, 0.0, fl)}
        hr = {"r": (0.06 * b, 0.0, -fl)}
        return {"lidKnot": knot, "handleL": hl, "handleR": hr}

    return Char("ribb", "Ribb", "The Woven Index",
                "hand-woven basket, loop handles, a lid that tips when it is sure",
                M, P, props, extras, bones,
                ["#C9A468", "#EFE2C6", "#AC5230", "#6FD9BE"], 0.86).finish(parts)


# ============================================================== 3 · ZAG ======
def build_zag():
    """ZAG — an angular, faceted mineral shard on peg legs. Strictly flat-shaded."""
    M = dict(shared_mats())
    M.update({
        "stone": dict(color=srgb("#5E6C79"), roughness=0.48, metallic=0.06, texture="stone"),
        "strata": dict(color=srgb("#93A2AC"), roughness=0.58, metallic=0.04, texture="stone"),
        "dark": dict(color=srgb("#2A323A"), roughness=0.34, metallic=0.10),
        "glow": dict(color=srgb("#2FD8B4"), roughness=0.24, metallic=0.0,
                     emissive=tuple(c * 0.55 for c in srgb("#39E6C2"))),
        "lid": dict(color=srgb("#5D6B77"), roughness=0.42, metallic=0.08),
    })
    parts = []
    shell = []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    def leg(sgn):
        l = facet(ngon_prism(0.058, 6, 0.185, taper=0.88, rot=np.pi / 6.0,
                             name="leg", mat="strata"))
        l.move(sgn * 0.108, 0.108, 0.0)
        l.tag("legL" if sgn < 0 else "legR")
        return l

    parts.extend(mirrored(leg))

    def pad(sgn):
        p = facet(ngon_prism(0.080, 6, 0.030, taper=0.92, rot=np.pi / 6.0, name="pad", mat="dark"))
        p.move(sgn * 0.108, 0.017, 0.0)
        p.tag("legL" if sgn < 0 else "legR")
        return p

    parts.extend(mirrored(pad))

    body = facet(lathe([(0.118, 0.196), (0.170, 0.250), (0.222, 0.330), (0.246, 0.420),
                        (0.250, 0.520), (0.232, 0.620), (0.198, 0.700), (0.166, 0.760)],
                       seg=6, name="body", mat="stone", flat=True))
    body.rotate(ry=TAU / 24.0)
    body.tag("legL", "legR", "hips", "spine", "chest", "base")
    add(body)

    for y, r, key in ((0.420, 0.254, "glow"), (0.588, 0.240, "dark")):
        band = facet(lathe([(r - 0.022, y - 0.032), (r, y - 0.010), (r, y + 0.010), (r - 0.022, y + 0.032)],
                           seg=6, name="band_%s" % key, mat=key, flat=True))
        band.rotate(ry=TAU / 24.0)
        band.tag("chest" if y > 0.5 else "spine")
        add(band, False)

    head = facet(lathe([(0.166, 0.752), (0.206, 0.812), (0.216, 0.884), (0.196, 0.952),
                        (0.146, 1.014), (0.072, 1.058), (0.0, 1.076)],
                       seg=6, name="head", mat="stone", flat=True))
    head.rotate(ry=TAU / 24.0 + 0.20)
    head.tag("chest", "head", "neck")
    add(head)

    # ---- face: a flat chiselled visor plate carrying the eyes ------------
    vy = 0.930
    visor_poly = [(x * 0.172, y * 0.084) for x, y in hex_poly(1.0)]
    visor_parts = conform_plate(shell, visor_poly, vy, thickness=0.024, proud=0.012,
                                mat="dark", rim_mat=None, name="visor")
    for vp in visor_parts:
        vp.bones = ("head",)
    parts.extend(visor_parts)

    ex = 0.078
    eye_poly = [(x * 0.050, y * 0.040) for x, y in hex_poly(1.0)]
    for sgn, bone in ((-1.0, "eyeL"), (1.0, "eyeR")):
        panel = [(x, y + 0.004) for x, y in eye_poly]
        lit = conform_plate(visor_parts, panel, vy, thickness=0.018, proud=0.008,
                            mat="glow", rim_mat=None, name="gloweye", cx=sgn * ex, bone=bone)
        parts.extend(lit)
        zf = probe_z(lit, sgn * ex, vy + 0.004) or 0.25
        g = sphere(0.017, 0.012, 0.009, seg=12, rings=8, name="glint", mat="eye_glint")
        g.move(sgn * (ex - 0.024), vy + 0.020, zf + 0.006)
        g.tag(bone)
        parts.append(g)
        shutter = [(x * 0.98, y * 0.92 + 0.046) for x, y in eye_poly]
        parts.extend(conform_plate(visor_parts, shutter, vy, thickness=0.022, proud=0.011,
                                   mat="lid", rim_mat=None, name="shutter", cx=sgn * ex,
                                   bone="lid" + bone[-1]))
    ez = (probe_z(visor_parts, 0.0, vy) or 0.25) + 0.004

    def fin(sgn):
        f = facet(ngon_prism(0.062, 4, 0.230, taper=0.18, rot=np.pi / 4.0, name="fin", mat="strata"))
        f.rotate(ry=np.pi * 0.25)
        f.rotate(rx=0.62)
        f.move(sgn * 0.092, 0.836, -0.096)
        f.tag("finL" if sgn < 0 else "finR")
        return f

    parts.extend(mirrored(fin))

    poly = hex_poly(0.108)
    parts.extend(conform_plate(shell, poly, 0.520, thickness=0.019, proud=0.013,
                               rim=1.14, rim_proud=0.008, name="badge"))
    pz = (probe_z(shell, 0.0, 0.520) or 0.24) + 0.013

    props = dict(hipY=0.30, spineY=0.46, chestY=0.64, neckY=0.78, headY=0.92,
                 legX=0.108, legY=0.196, baseY=0.03, badgeY=0.520, badgeZ=pz,
                 eyeX=ex, eyeY=vy, eyeZ=ez,
                 r_hips=0.22, r_spine=0.20, r_chest=0.20, r_neck=0.14, r_head=0.20,
                 r_base=0.24, r_leg=0.09, badge_size=[0.20, 0.17])

    bones = [
        mat_bone("finL", "chest", (-0.092, 0.836 - 0.64, -0.096), (0, 1, 0), 0.18, 0.13),
        mat_bone("finR", "chest", (0.092, 0.836 - 0.64, -0.096), (0, 1, 0), 0.18, 0.13),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.30, "crouch_d": 0.105, "land_d": 0.130, "squash": 0.85,
              "gaze_yaw": -0.40, "chest_yaw": 0.40, "leg_squash": 0.68, "leg_len": 0.196,
              "up_scale": 1.0, "breath": 0.55, "sway": 0.6, "lid_close": 1.55,
              "eyelead": 0.008})

    def extras(clip, t, dur, ph):
        b = ph["breath"]
        lag = ph["lag_up"]
        imp = ph["impact"]
        happy = ph["happy"]
        fl = 0.20 * imp + 0.34 * happy - 2.6 * lag
        finL = {"r": (0.05 * b, 0.0, -fl - 0.10 * abs(ph["shake"]))}
        finR = {"r": (0.05 * b, 0.0, fl + 0.10 * abs(ph["shake"]))}
        if clip == "Success":
            sc = (1.0 + 0.10 * happy, 1.0 + 0.14 * happy, 1.0 + 0.10 * happy)
            finL["s"] = sc
            finR["s"] = sc
        if clip == "NoSwap":
            finL["r"] = (0.0, 0.0, 0.66 * ph["lean"])
            finR["r"] = (0.0, 0.0, 0.66 * ph["lean"])
        return {"finL": finL, "finR": finR}

    return Char("zag", "Zag", "The Mineral Constant",
                "faceted slate crystal on peg legs, glow-lit visor eyes",
                M, P, props, extras, bones,
                ["#5E6C79", "#93A2AC", "#2A323A", "#8FF0D6"], 1.10).finish(parts)


# ============================================================== 4 · GLIM =====
def build_glim():
    """GLIM — a translucent gel droplet with a floating core and a frond skirt."""
    import math
    M = dict(shared_mats())
    M.update({
        "gel": dict(color=srgb("#4FCFC8"), roughness=0.09, metallic=0.0, alpha=0.70),
        "gel_dp": dict(color=srgb("#2E9E9E"), roughness=0.12, metallic=0.0, alpha=0.72),
        "core": dict(color=srgb("#FFC98A"), roughness=0.34, metallic=0.0,
                     emissive=tuple(c * 1.1 for c in srgb("#FFB067"))),
        "frond": dict(color=srgb("#8FE6D9"), roughness=0.16, metallic=0.0, alpha=0.88),
        "lid": dict(color=srgb("#BFF2EA"), roughness=0.14, metallic=0.0, alpha=0.90),
    })
    parts = []
    shell = []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    pad = lathe([(0.235, 0.0), (0.252, 0.020), (0.244, 0.062), (0.214, 0.086), (0.180, 0.098)],
                seg=36, name="pad", mat="gel_dp")
    pad.tag("base")
    add(pad)
    body = lathe([(0.180, 0.070), (0.240, 0.128), (0.284, 0.222), (0.300, 0.320),
                  (0.292, 0.415), (0.258, 0.512), (0.202, 0.606), (0.128, 0.690),
                  (0.058, 0.756), (0.0, 0.790)],
                 seg=40, name="drop", mat="gel")
    body.tag("hips", "spine", "chest", "head", "base")
    add(body)
    ripple = lathe([(0.270, 0.186), (0.286, 0.204), (0.272, 0.224)], seg=36, name="ripple", mat="gel_dp")
    ripple.tag("hips")
    add(ripple, False)

    core = sphere(0.090, 0.088, 0.090, seg=24, rings=14, name="core", mat="core")
    core.move(0, 0.392, 0.0)
    core.tag("core")
    add(core, False)

    ex, ey = 0.100, 0.455
    ring_poly = hex_poly(1.0)
    parts.extend(eye_pair(shell, ex, ey, 0.058, 0.062, 0.042, M,
                          lid=(0.98, 0.28, 0.56), lid_lift=1.40, proud=1.0))
    my = 0.336
    mouth = sphere(0.032, 0.025, 0.018, seg=18, rings=10, name="mouth", mat="eye_dark")
    parts.append(mount_mouth(shell, 0.0, my, mouth, proud=0.014))
    ez = (probe_z(shell, ex, ey) or 0.25)

    def frond(ang, bone, r0=0.248, y0=0.232):
        s, c = math.sin(ang), math.cos(ang)
        pts = [(s * r0, y0, c * r0),
               (s * (r0 + 0.038), y0 - 0.078, c * (r0 + 0.038)),
               (s * (r0 + 0.032), y0 - 0.152, c * (r0 + 0.032)),
               (s * (r0 - 0.018), y0 - 0.216, c * (r0 - 0.018))]
        f = tube(pts, 0.031, radial=10, name="frond", mat="frond", taper=[0.9, 0.8, 0.68, 0.5])
        f.tag(bone)
        return f

    parts.append(frond(0.42, "frondF"))
    parts.append(frond(-0.42, "frondF"))
    parts.append(frond(math.pi - 0.38, "frondB"))
    parts.append(frond(math.pi + 0.38, "frondB"))
    parts.append(frond(math.pi * 0.5, "frondL"))
    parts.append(frond(-math.pi * 0.5, "frondR"))

    poly = rounded_rect_poly(0.152, 0.146, 0.040, seg=6)
    parts.extend(conform_plate(shell, poly, 0.234, thickness=0.019, proud=0.014,
                               rim=1.10, rim_proud=0.008, name="badge"))
    pz = (probe_z(shell, 0.0, 0.234) or 0.28) + 0.014

    props = dict(hipY=0.20, spineY=0.32, chestY=0.44, neckY=0.56, headY=0.66,
                 legX=0.12, legY=0.06, baseY=0.05, badgeY=0.234, badgeZ=pz,
                 eyeX=ex, eyeY=ey, eyeZ=ez,
                 r_hips=0.30, r_spine=0.28, r_chest=0.26, r_neck=0.24, r_head=0.26,
                 r_base=0.26, r_leg=0.10, badge_size=[0.146, 0.146])

    bones = [
        mat_bone("core", "chest", (0.0, 0.392 - 0.44, 0.0), (0, 1, 0), 0.10, 0.12),
        mat_bone("frondF", "hips", (0.0, 0.232 - 0.20, 0.248), (0, -1, 0), 0.14, 0.16),
        mat_bone("frondB", "hips", (0.0, 0.232 - 0.20, -0.248), (0, -1, 0), 0.14, 0.16),
        mat_bone("frondL", "hips", (-0.248, 0.232 - 0.20, 0.0), (0, -1, 0), 0.14, 0.16),
        mat_bone("frondR", "hips", (0.248, 0.232 - 0.20, 0.0), (0, -1, 0), 0.14, 0.16),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.30, "crouch_d": 0.060, "land_d": 0.080, "squash": 1.55,
              "gaze_yaw": -0.30, "chest_yaw": 0.42, "legs": False, "leg_squash": 1.0,
              "up_scale": 0.55, "breath": 1.35, "sway": 1.25, "lid_close": 1.55,
              "eyelead": 0.013})

    def extras(clip, t, dur, ph):
        b = ph["breath"]
        lag = ph["lag_up"]
        imp = ph["impact"]
        happy = ph["happy"]
        pulse = 0.06 * b + 0.05 * ph["pop"]
        core = {"s": (1.0 + pulse, 1.0 + pulse, 1.0 + pulse), "t": (0.0, 1.6 * lag, 0.0)}
        if clip == "Success":
            core["s"] = (1.0 + 0.18 * happy + pulse,) * 3
        fl = 0.20 * imp + 0.30 * happy
        out = {"core": core}
        for name, sign in (("frondF", 1.0), ("frondB", -1.0), ("frondL", -1.0), ("frondR", 1.0)):
            r0 = 0.10 * b * (1.0 if name in ("frondF", "frondB") else 0.6)
            r1 = -5.0 * lag
            r2 = sign * fl * 0.5
            s1 = 1.0 + 0.06 * happy
            if clip == "NoSwap":
                out[name] = {"r": (0.0, -5.0 * lag, sign * 0.72 * ph["lean"]), "s": (1.0, 1.0, 1.0)}
            else:
                out[name] = {"r": (r0, r1, r2), "s": (1.0, s1, 1.0)}
        return out

    return Char("glim", "Glim", "The Translucent Buffer",
                "soft gel droplet, glowing core, swaying frond skirt",
                M, P, props, extras, bones,
                ["#5FD3CC", "#FFC98A", "#8FE6D9", "#6FD9BE"], 0.80).finish(parts)


# ============================================================= 5 · RUMBLE ====
def build_rumble():
    """RUMBLE — a low, wide, softly-mechanical loaf under three copper armour rings."""
    M = dict(shared_mats())
    M.update({
        "shell": dict(color=srgb("#D9B98C"), roughness=0.56, metallic=0.0, texture="matte"),
        "copper": dict(color=srgb("#A25C2C"), roughness=0.44, metallic=0.55),
        "rubber": dict(color=srgb("#33343B"), roughness=0.88, metallic=0.0),
        "vent": dict(color=srgb("#4A3B31"), roughness=0.62, metallic=0.20),
        "lid": dict(color=srgb("#E2C79E"), roughness=0.42, metallic=0.10, texture="matte"),
    })
    parts = []
    shell = []

    def add(p, to_shell=True):
        parts.append(p)
        if to_shell:
            shell.append(p)
        return p

    def leg(sgn, back, bone):
        l = capsule(0.056, 0.062, seg=18, rings=7, name="leg", mat="copper")
        l.move(sgn * 0.245, 0.088, back * 0.185)
        l.tag(bone)
        p = sphere(0.062, 0.040, 0.062, seg=18, rings=12, name="pad", mat="rubber")
        p.move(sgn * 0.245, 0.040, back * 0.185)
        p.tag(bone)
        return [l, p]

    for sgn in (-1.0, 1.0):
        for lp in leg(sgn, 1.0, "legL" if sgn < 0 else "legR"):
            add(lp, False)
        for lp in leg(sgn, -1.0, "legBL" if sgn < 0 else "legBR"):
            add(lp, False)

    loaf = superellipsoid(0.400, 0.255, 0.300, e1=0.44, e2=0.46, seg=44, rings=24,
                          name="loaf", mat="shell")
    loaf.move(0, 0.352, 0.0)
    loaf.tag("hips", "spine", "chest", "base", "head")
    add(loaf)

    for i, (zz, R) in enumerate(((-0.170, 0.352), (0.010, 0.404), (0.180, 0.345))):
        ring = arc_tube((0, 0.352, zz), R, 0.22, np.pi - 0.22, 0.034, steps=26, plane="XY",
                        radial=10, name="ring%d" % i, mat="copper")
        ring.scale(1.0, 0.66, 1.0)
        ring.tag("ringA" if i == 0 else ("ringB" if i == 1 else "ringC"))
        add(ring, False)

    # ---- face plate -------------------------------------------------------
    fy = 0.404
    face_poly = [(x * 0.132, y * 0.084) for x, y in rounded_rect_poly(2.0, 2.0, 0.55, seg=6)]
    face_parts = conform_plate(shell, face_poly, fy, thickness=0.030, proud=0.016,
                               mat="copper", rim_mat="copper", rim=1.04, rim_proud=0.010,
                               name="face_plate")
    for fp in face_parts:
        fp.bones = ("head",)
    parts.extend(face_parts)

    for i, dy in enumerate((-0.082, -0.062)):
        slat = superellipsoid(0.070, 0.009, 0.014, e1=0.35, e2=0.35, seg=20, rings=8,
                              name="slat%d" % i, mat="vent")
        slat.move(0, fy + dy, (probe_z(face_parts, 0.0, fy + dy) or 0.30) - 0.002)
        slat.tag("head")
        parts.append(slat)
    lamp = sphere(0.030, 0.030, 0.024, seg=16, rings=10, name="lamp", mat="pop")
    lamp.move(0.196, fy - 0.030, (probe_z(face_parts, 0.196, fy - 0.030) or 0.30) - 0.010)
    lamp.tag("head")
    parts.append(lamp)

    ex = 0.104
    parts.extend(eye_pair(face_parts, ex, fy + 0.020, 0.062, 0.062, 0.036, M,
                          lid=(1.16, 0.38, 0.90), lid_lift=1.46, proud=0.76))

    flap = superellipsoid(0.150, 0.105, 0.048, e1=0.42, e2=0.5, seg=22, rings=14,
                          name="flap", mat="rubber")
    flap.rotate(rx=-0.30)
    flap.move(0, 0.212, -0.300)
    flap.tag("tailFlap")
    parts.append(flap)

    poly = rounded_rect_poly(0.182, 0.102, 0.026, seg=6)
    parts.extend(conform_plate(shell, poly, 0.220, thickness=0.019, proud=0.013,
                               rim=1.08, rim_proud=0.008, name="badge"))
    pz = (probe_z(shell, 0.0, 0.220) or 0.30) + 0.013

    props = dict(hipY=0.16, spineY=0.28, chestY=0.42, neckY=0.54, headY=0.60,
                 legX=0.245, legY=0.135, baseY=0.06, badgeY=0.220, badgeZ=pz,
                 eyeX=ex, eyeY=fy + 0.036, eyeZ=(probe_z(face_parts, ex, fy + 0.036) or 0.30),
                 r_hips=0.34, r_spine=0.32, r_chest=0.30, r_neck=0.26, r_head=0.30,
                 r_base=0.30, r_leg=0.11, badge_size=[0.186, 0.106])

    bones = [
        mat_bone("ringA", "chest", (0.0, 0.352 - 0.42, -0.170), (0, 1, 0), 0.14, 0.13),
        mat_bone("ringB", "chest", (0.0, 0.352 - 0.42, 0.010), (0, 1, 0), 0.14, 0.13),
        mat_bone("ringC", "chest", (0.0, 0.352 - 0.42, 0.180), (0, 1, 0), 0.14, 0.13),
        mat_bone("tailFlap", "hips", (0.0, 0.212 - 0.16, -0.300), (0, -1, 0), 0.10, 0.12),
        mat_bone("legBL", "hips", (-0.245, 0.088 - 0.16, -0.185), (0, -1, 0), 0.09, 0.10),
        mat_bone("legBR", "hips", (0.245, 0.088 - 0.16, -0.185), (0, -1, 0), 0.09, 0.10),
    ]

    P = dict(clips.DEFAULT_PARAMS)
    P.update({"hop_h": 0.22, "crouch_d": 0.055, "land_d": 0.070, "squash": 0.80,
              "gaze_yaw": -0.26, "chest_yaw": 0.50, "leg_squash": 0.80, "leg_len": 0.135,
              "up_scale": 1.0, "breath": 0.9, "sway": 0.7, "lid_close": 1.70,
              "eyelead": 0.009})

    def extras(clip, t, dur, ph):
        b = ph["breath"]
        lag = ph["lag_up"]
        imp = ph["impact"]
        happy = ph["happy"]
        out = {}
        for i, name in enumerate(("ringB", "ringA", "ringC")):
            kick = (0.9, 1.0, 0.8)[i]
            sc = 1.0 + kick * (0.030 * imp + 0.020 * happy)
            out[name] = {"s": (sc, sc, sc), "r": (0.04 * b, 0.0, 0.0)}
        flap_r = (0.10 * b - 1.2 * lag, 0.0, 0.06 * ph["shake"] + 0.10 * ph["lean"])
        if clip == "Success":
            flap_r = (-0.42 * happy, 0.0, 0.20 * np.sin(TAU * t * 4.0) * happy)
        if clip == "NoSwap":
            flap_r = (0.30 * ph["lean"], 0.0, 0.0)
        out["tailFlap"] = {"r": flap_r}
        bl = min(max(ph.get("legsq", 1.0), 0.5), 1.4)
        for name in ("legBL", "legBR"):
            out[name] = {"s": (1.0, bl, 1.0), "r": (ph.get("legx", 0.0), 0.0, 0.0)}
        return out

    return Char("rumble", "Rumble", "The Sorted Segments",
                "low softly-mechanical loaf under three copper rings, rubber shod",
                M, P, props, extras, bones,
                ["#D9B98C", "#B4713C", "#33343B", "#6FD9BE"], 0.66).finish(parts)


BUILDERS = {
    "kiln": build_kiln,
    "ribb": build_ribb,
    "zag": build_zag,
    "glim": build_glim,
    "rumble": build_rumble,
}
