"""
mlib — mesh primitives for the Bubble-Sort Mascots pipeline.

Conventions used across this whole project (see ../README.md):
    * Y is up, the character FRONT faces +Z, character origin sits on the ground (y = 0).
    * Units are metres. 1.0 m ~ one array slot's worth of character.
    * Every primitive returns a `Part`, which carries its own vertex array, normals,
      UVs, triangle list, material key, the list of bones allowed to deform it and a
      flat/smooth shading flag. Parts are merged at the end of a build.

No third-party dependencies except numpy.
"""

import numpy as np

TAU = np.pi * 2.0


# --------------------------------------------------------------------------- Part
class Part(object):
    """A single primitive: geometry + material key + skinning hints."""

    def __init__(self, name, mat, v, n, uv, f, bones=(), flat=False):
        self.name = name
        self.mat = mat
        self.v = np.asarray(v, dtype=np.float64).reshape(-1, 3)
        self.n = np.asarray(n, dtype=np.float64).reshape(-1, 3)
        self.uv = np.asarray(uv, dtype=np.float64).reshape(-1, 2)
        self.f = np.asarray(f, dtype=np.int32).reshape(-1, 3)
        # bones that may influence this part (by name); empty -> nearest-bone search
        self.bones = tuple(bones)
        self.flat = bool(flat)
        assert len(self.v) == len(self.n) == len(self.uv)
        self.fix_winding()

    # -- winding ------------------------------------------------------------
    def fix_winding(self):
        """Orient faces so the geometric normal agrees with the analytic normal.

        Front faces are CCW in a right-handed Y-up space (the glTF/three.js
        convention). Doing this automatically means back-face culling behaves
        identically in Blender, three.js and the offline renderer.
        """
        if len(self.f) == 0:
            return self
        v0, v1, v2 = self.v[self.f[:, 0]], self.v[self.f[:, 1]], self.v[self.f[:, 2]]
        geo = np.cross(v1 - v0, v2 - v0)
        ref = self.n[self.f[:, 0]] + self.n[self.f[:, 1]] + self.n[self.f[:, 2]]
        w = np.einsum("ij,ij->i", geo, ref)
        if np.sum(w) < 0:
            self.f = self.f[:, ::-1].copy()
        return self

    def signed_volume(self):
        """Positive for a closed surface wound with outward normals."""
        v0, v1, v2 = self.v[self.f[:, 0]], self.v[self.f[:, 1]], self.v[self.f[:, 2]]
        return float(np.einsum("ij,ij->i", v0, np.cross(v1, v2)).sum() / 6.0)

    # -- transforms ---------------------------------------------------------
    def transform(self, M):
        vh = np.concatenate([self.v, np.ones((len(self.v), 1))], axis=1)
        self.v = (vh @ M.T)[:, :3]
        # normals: inverse-transpose of the 3x3
        A = np.linalg.inv(M[:3, :3]).T
        self.n = self.n @ A.T
        self._renormalise()
        return self

    def _renormalise(self):
        L = np.linalg.norm(self.n, axis=1, keepdims=True)
        L[L < 1e-12] = 1.0
        self.n = self.n / L

    def move(self, x=0.0, y=0.0, z=0.0):
        self.v = self.v + np.array([x, y, z], dtype=np.float64)
        return self

    def rotate(self, rx=0.0, ry=0.0, rz=0.0):
        return self.transform(TRS((0, 0, 0), (rx, ry, rz)))

    def scale(self, sx=1.0, sy=None, sz=None):
        if sy is None:
            sy = sx
        if sz is None:
            sz = sx
        self.v = self.v * np.array([sx, sy, sz], dtype=np.float64)
        self.n = self.n / np.array([sx, sy, sz], dtype=np.float64)
        self._renormalise()
        return self

    def mirror_x(self):
        """Mirror across the YZ plane and flip winding so faces stay outward."""
        self.v = self.v * np.array([-1.0, 1.0, 1.0])
        self.n = self.n * np.array([-1.0, 1.0, 1.0])
        self.f = self.f[:, ::-1].copy()
        return self

    def tint(self, mat):
        self.mat = mat
        return self

    def tag(self, *bones):
        self.bones = tuple(bones)
        return self

    def bbox(self):
        return self.v.min(axis=0), self.v.max(axis=0)

    def tri_count(self):
        return len(self.f)


# --------------------------------------------------------------------- matrices
def TRS(t=(0, 0, 0), r=(0, 0, 0), s=(1, 1, 1)):
    """4x4 from translation / ZYX-euler rotation (radians) / scale."""
    M = np.eye(4)
    R = euler_matrix(*r)
    S = np.diag(np.array([s[0], s[1], s[2], 1.0], dtype=np.float64))
    M = R @ S
    M[:3, 3] = np.array(t, dtype=np.float64)
    return M


def euler_matrix(rx, ry, rz):
    cx, sx = np.cos(rx), np.sin(rx)
    cy, sy = np.cos(ry), np.sin(ry)
    cz, sz = np.cos(rz), np.sin(rz)
    X = np.array([[1, 0, 0, 0], [0, cx, -sx, 0], [0, sx, cx, 0], [0, 0, 0, 1]], dtype=np.float64)
    Y = np.array([[cy, 0, sy, 0], [0, 1, 0, 0], [-sy, 0, cy, 0], [0, 0, 0, 1]], dtype=np.float64)
    Z = np.array([[cz, -sz, 0, 0], [sz, cz, 0, 0], [0, 0, 1, 0], [0, 0, 0, 1]], dtype=np.float64)
    return Z @ Y @ X


def quat_from_euler(rx, ry, rz):
    """ZYX euler -> quaternion (x, y, z, w). Matches euler_matrix() ordering."""
    qx = _axis_q((1, 0, 0), rx)
    qy = _axis_q((0, 1, 0), ry)
    qz = _axis_q((0, 0, 1), rz)
    return qmul(qmul(qz, qy), qx)


def _axis_q(axis, ang):
    h = ang * 0.5
    s = np.sin(h)
    return np.array([axis[0] * s, axis[1] * s, axis[2] * s, np.cos(h)], dtype=np.float64)


def qmul(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return np.array([
        aw * bx + ax * bw + ay * bz - az * by,
        aw * by - ax * bz + ay * bw + az * bx,
        aw * bz + ax * by - ay * bx + az * bw,
        aw * bw - ax * bx - ay * by - az * bz,
    ], dtype=np.float64)


def qnorm(q):
    return q / np.linalg.norm(q)


# ----------------------------------------------------------------- primitives
def _grid_uv(nu, nv):
    """UV grid for a (nu+1) x (nv+1) vertex patch."""
    u = np.linspace(0.0, 1.0, nu + 1)
    v = np.linspace(0.0, 1.0, nv + 1)
    U, V = np.meshgrid(u, v, indexing="ij")
    return np.stack([U.ravel(), V.ravel()], axis=1)


def _grid_faces(nu, nv, flip=False):
    idx = lambda i, j: i * (nv + 1) + j
    f = []
    for i in range(nu):
        for j in range(nv):
            a, b, c, d = idx(i, j), idx(i + 1, j), idx(i + 1, j + 1), idx(i, j + 1)
            f.append([a, b, c])
            f.append([a, c, d])
    f = np.array(f, dtype=np.int32)
    if flip:
        f = f[:, ::-1]
    return f


def sphere(rx, ry, rz, seg=32, rings=16, name="sphere", mat="shell", flat=False):
    """Ellipsoid, poles on Y, seamless UV, analytic normals."""
    v, n, uv = [], [], []
    for j in range(rings + 1):
        phi = np.pi * j / rings                      # 0 = +Y pole
        sp, cp = np.sin(phi), np.cos(phi)
        for i in range(seg + 1):
            th = TAU * i / seg                       # 0 at +Z, growing toward +X
            st, ct = np.sin(th), np.cos(th)
            x, y, z = sp * st, cp, sp * ct
            v.append((x * rx, y * ry, z * rz))
            nn = np.array([x / rx, y / ry, z / rz], dtype=np.float64)
            n.append(nn / max(np.linalg.norm(nn), 1e-12))
            uv.append((i / seg, 1.0 - j / rings))
    return Part(name, mat, v, n, uv, _grid_faces(rings, seg), flat=flat)


def lathe(profile, seg=32, name="lathe", mat="shell", flat=False, uv_scale=(1.0, 1.0),
          uv_off=(0.0, 0.0), cap_bottom=False):
    """Revolve a (radius, y) profile around Y.

    A profile point with radius <= 0 collapses to a single shared vertex (pole),
    so domes/teardrops stay clean. `seg` also doubles as a facet count: use 6 with
    flat=True for a hexagonal mineral body.
    """
    prof = [(float(r), float(y)) for r, y in profile]
    v, n, uv = [], [], []
    vmap = {}                                # (ring, i) -> vertex index (pole sharing)
    ymin = min(y for _, y in prof)
    ymax = max(y for _, y in prof)
    span = max(ymax - ymin, 1e-6)

    def dr_dy(k):
        r0, y0 = prof[max(k - 1, 0)]
        r1, y1 = prof[min(k + 1, len(prof) - 1)]
        return (r1 - r0) / max(y1 - y0, 1e-6)

    for k, (r, y) in enumerate(prof):
        if r <= 1e-6:
            v.append((0.0, y, 0.0))
            n.append((0.0, 0.0, 0.0))         # fixed up below
            uv.append((0.5, (y - ymin) / span * uv_scale[1] + uv_off[1]))
            vmap[(k, -1)] = len(v) - 1
            continue
        m = dr_dy(k)
        for i in range(seg + 1):
            th = TAU * i / seg
            st, ct = np.sin(th), np.cos(th)
            x, z = r * st, r * ct
            v.append((x, y, z))
            nn = np.array([st, -m, ct], dtype=np.float64)
            n.append(nn / max(np.linalg.norm(nn), 1e-12))
            uv.append((i / seg * uv_scale[0] + uv_off[0], (y - ymin) / span * uv_scale[1] + uv_off[1]))
            vmap[(k, i)] = len(v) - 1

    f = []
    for k in range(len(prof) - 1):
        r0, r1 = prof[k][0], prof[k + 1][0]
        if r0 <= 1e-6:                                    # bottom pole fan
            c = vmap[(k, -1)]
            for i in range(seg):
                f.append([c, vmap[(k + 1, i + 1)], vmap[(k + 1, i)]])
        elif r1 <= 1e-6:                                  # top pole fan
            c = vmap[(k + 1, -1)]
            for i in range(seg):
                f.append([c, vmap[(k, i)], vmap[(k, i + 1)]])
        else:
            for i in range(seg):
                a, b = vmap[(k, i)], vmap[(k, i + 1)]
                c, d = vmap[(k + 1, i + 1)], vmap[(k + 1, i)]
                f.append([a, b, c])
                f.append([a, c, d])

    if cap_bottom:
        r0, y0 = prof[0]
        if r0 > 1e-6:
            cv = len(v)
            v.append((0.0, y0, 0.0)); n.append((0.0, -1.0, 0.0)); uv.append((0.5, 0.0))
            loop = [vmap[(0, i)] for i in range(seg)]
            for i in range(seg):
                f.append([cv, loop[(i + 1) % seg], loop[i]])

    p = Part(name, mat, v, n, uv, f, flat=flat)
    # pole normals: average of their fan
    for key, vi in vmap.items():
        if key[1] == -1:
            acc = np.zeros(3)
            ring = key[0]
            nb = ring + 1 if prof[ring][0] <= 1e-6 else ring - 1
            for i in range(seg):
                for cand in (vmap.get((nb, i)), vmap.get((nb, i + 1))):
                    if cand is not None:
                        acc += p.n[cand]
            L = np.linalg.norm(acc)
            if L > 1e-9:
                p.n[vi] = acc / L
            else:
                p.n[vi] = (0, 1, 0) if ring == len(prof) - 1 else (0, -1, 0)
    return p


def capsule(r, length, seg=24, rings=8, name="capsule", mat="shell"):
    """Capsule along Y : cylinder of `length` between two hemispherical caps."""
    prof = []
    for j in range(rings + 1):
        a = np.pi * 0.5 * j / rings                # 0..pi/2
        prof.append((r * np.sin(a), length * 0.5 + r * np.cos(a)))
    prof.append((r, -length * 0.5))
    for j in range(1, rings + 1):
        a = np.pi * 0.5 * j / rings
        prof.append((r * np.cos(a), -length * 0.5 - r * np.sin(a)))
    # profiles run bottom-pole -> top-pole so the lathe normals face outward
    return lathe(prof[::-1], seg=seg, name=name, mat=mat)


def superellipsoid(sx, sy, sz, e1=0.40, e2=0.40, seg=28, rings=18, name="blob", mat="shell"):
    """Rounded box / squircle solid with clean UVs (e ~0.3 is a soft rounded box)."""
    v, n, uv = [], [], []
    for j in range(rings + 1):
        phi = np.pi * (j / rings - 0.5)              # -pi/2 .. pi/2
        cp, sp = np.cos(phi), np.sin(phi)
        for i in range(seg + 1):
            th = TAU * i / seg - np.pi * 0.5         # 0 at +Z-ish
            ct, st = np.cos(th), np.sin(th)
            x = np.sign(cp) * abs(cp) ** e1 * np.sign(st) * abs(st) ** e2
            y = np.sign(sp) * abs(sp) ** e1
            z = np.sign(cp) * abs(cp) ** e1 * np.sign(ct) * abs(ct) ** e2
            v.append((x * sx, y * sy, z * sz))
            nn = np.array([x / sx, y / sy, z / sz], dtype=np.float64)
            n.append(nn / max(np.linalg.norm(nn), 1e-12))
            uv.append((i / seg, 1.0 - j / rings))
    return Part(name, mat, v, n, uv, _grid_faces(rings, seg))


def tube(path, r, radial=12, caps=True, name="tube", mat="shell", taper=None, up=(0, 1, 0),
         uv_scale=(1.0, 1.0)):
    """Sweep a circular tube along a polyline of 3D points (handles, fronds, tails)."""
    P = np.asarray(path, dtype=np.float64)
    n_pts = len(P)
    tang = np.zeros_like(P)
    tang[0] = P[1] - P[0]
    tang[-1] = P[-1] - P[-2]
    for i in range(1, n_pts - 1):
        tang[i] = P[i + 1] - P[i - 1]
    tang /= np.maximum(np.linalg.norm(tang, axis=1, keepdims=True), 1e-9)

    upv = np.array(up, dtype=np.float64)
    if abs(np.dot(tang[0], upv)) > 0.95:
        upv = np.array([0.0, 0.0, 1.0])
    # parallel transport a reference frame so the tube does not twist
    norms = []
    ref = np.cross(upv, tang[0]); ref /= max(np.linalg.norm(ref), 1e-9)
    norms.append(ref)
    for i in range(1, n_pts):
        r0 = norms[-1]
        t0, t1 = tang[i - 1], tang[i]
        axis = np.cross(t0, t1)
        L = np.linalg.norm(axis)
        if L < 1e-9:
            norms.append(r0.copy())
        else:
            axis = axis / L
            ang = np.arccos(np.clip(np.dot(t0, t1), -1, 1))
            c, s = np.cos(ang), np.sin(ang)
            r0 = r0 * c + np.cross(axis, r0) * s + axis * np.dot(axis, r0) * (1 - c)
            norms.append(r0 / max(np.linalg.norm(r0), 1e-9))

    v, n, uv = [], [], []
    if taper is None:
        taper = np.ones(n_pts)
    taper = np.asarray(taper, dtype=np.float64)
    for i in range(n_pts):
        t = tang[i]; N = norms[i]; B = np.cross(t, N)
        rr = r * taper[i]
        for k in range(radial + 1):
            a = TAU * k / radial
            dirv = N * np.cos(a) + B * np.sin(a)
            v.append(P[i] + dirv * rr)
            n.append(dirv)
            uv.append((k / radial * uv_scale[0], i / (n_pts - 1) * uv_scale[1]))
    f = _grid_faces(n_pts - 1, radial, flip=True)
    p = Part(name, mat, v, n, uv, f)
    if caps:
        for end, tip in ((0, P[0] - tang[0] * r * 0.9), (n_pts - 1, P[-1] + tang[-1] * r * 0.9)):
            ci = len(p.v)
            p.v = np.vstack([p.v, tip])
            p.n = np.vstack([p.n, tang[end]])
            p.uv = np.vstack([p.uv, (0.5, 0.5)])
            ring = [end * (radial + 1) + k for k in range(radial)]
            for k in range(radial):
                a, b = ring[k], ring[(k + 1) % radial]
                p.f = np.vstack([p.f, [ci, b, a] if end == 0 else [ci, a, b]])
    return p


def arc_tube(center, radius, a0, a1, tube_r, steps=16, plane="XY", radial=10,
             name="arc", mat="shell", squash=(1.0, 1.0), uv_scale=(1.0, 1.0)):
    """Circular arc in a cardinal plane, swept as a tube (basket handles, rings)."""
    cx, cy, cz = center
    pts = []
    for i in range(steps + 1):
        a = a0 + (a1 - a0) * i / steps
        s, c = np.sin(a), np.cos(a)
        if plane == "XY":
            pts.append((cx + radius * s * squash[0], cy + radius * c * squash[1], cz))
        elif plane == "XZ":
            pts.append((cx + radius * s * squash[0], cy, cz + radius * c * squash[1]))
        else:                                     # YZ
            pts.append((cx, cy + radius * c * squash[1], cz + radius * s * squash[0]))
    return tube(pts, tube_r, radial=radial, name=name, mat=mat, uv_scale=uv_scale)


def ngon_prism(radius, sides, height, taper=1.0, rot=0.0, name="prism", mat="shell"):
    """Flat-shaded extruded n-gon with a tapered top (badges, crystal shards)."""
    prof = []
    steps = 3
    for k in range(steps + 1):                   # slight rounded-in bottom edge
        t = k / steps
        prof.append((radius * (1.0 - 0.04 * (1 - t)), -height * 0.5 + height * 0.04 * t))
    prof.append((radius, 0.0))
    prof.append((radius * taper, height * 0.5))
    for k in range(1, steps + 1):
        t = k / steps
        prof.append((radius * taper * (1.0 - 0.10 * t), height * 0.5 + height * 0.06 * t))
    p = lathe(prof, seg=sides, name=name, mat=mat, flat=True)
    if rot:
        p.rotate(ry=rot)
    return p


def torus(R, r, seg_major=32, seg_minor=12, name="torus", mat="shell"):
    v, n, uv = [], [], []
    for i in range(seg_major + 1):
        a = TAU * i / seg_major
        ca, sa = np.cos(a), np.sin(a)
        for j in range(seg_minor + 1):
            b = TAU * j / seg_minor
            cb, sb = np.cos(b), np.sin(b)
            x = (R + r * cb) * sa
            z = (R + r * cb) * ca
            y = r * sb
            v.append((x, y, z))
            nn = np.array([cb * sa, sb, cb * ca])
            n.append(nn / max(np.linalg.norm(nn), 1e-12))
            uv.append((i / seg_major, j / seg_minor))
    return Part(name, mat, v, n, uv, _grid_faces(seg_major, seg_minor))


def plate(poly2d, thickness, bevel=0.012, name="plate", mat="badge", flat=False):
    """Extruded flat polygon in the XZ plane (faces +Z), for blank number badges.

    poly2d is a list of (x, y) points; extrusion is along Z (thickness) with a
    small bevel so the rim catches light.
    """
    P = np.asarray(poly2d, dtype=np.float64)
    npts = len(P)
    c = P.mean(axis=0)
    v, n, uv, f = [], [], [], []
    ext = np.linspace(-thickness * 0.5, thickness * 0.5, 2)
    rings = []
    for z, shrink in ((ext[0], 1.0 - bevel / max(np.abs(P - c).max(), 1e-6)),
                      (ext[0] - 0.0, 1.0 - bevel / max(np.abs(P - c).max(), 1e-6)),
                      (ext[1], 1.0 - bevel / max(np.abs(P - c).max(), 1e-6))):
        pass
    # front face (shrunken, so the rim bevels), rim ring, back face
    b = bevel / max(np.abs(P - c).max(), 1e-6)
    small = c + (P - c) * (1.0 - b)
    big = c + (P - c) * 1.0
    layers = [(ext[1], small), (ext[0], big)]
    for z, ring in layers:
        for i, (x, y) in enumerate(ring):
            v.append((x, y, z)); n.append((0.0, 0.0, 1.0 if z > 0 else -1.0))
            uv.append(((x - c[0]) * 0.5 + 0.5, (y - c[1]) * 0.5 + 0.5))
    # rim quads
    for i in range(npts):
        j = (i + 1) % npts
        a0 = layers[0][1][i]; a1 = layers[0][1][j]
        b0 = layers[1][1][i]; b1 = layers[1][1][j]
        idx = len(v)
        for p3, nn in ((a0, 1), (a1, 1), (b1, -1), (b0, -1)):
            v.append((p3[0], p3[1], ext[1] if nn > 0 else ext[0]))
            e = (np.array(a1) - np.array(a0))
            rim = np.array([e[1], -e[0], 0.0])
            rim /= max(np.linalg.norm(rim), 1e-9)
            n.append(rim)
            uv.append((i / npts, 0.5))
        f.append([idx, idx + 2, idx + 1]); f.append([idx, idx + 3, idx + 2])
    # front + back fans
    for sign, layer in ((1, layers[0]), (-1, layers[1])):
        base = len(v)
        cz = ext[1] if sign > 0 else ext[0]
        v.append((c[0], c[1], cz)); n.append((0, 0, sign)); uv.append((0.5, 0.5))
        for i in range(npts):
            p3 = layer[1][i]
            v.append((p3[0], p3[1], cz)); n.append((0, 0, sign))
            uv.append(((p3[0] - c[0]) * 0.5 + 0.5, (p3[1] - c[1]) * 0.5 + 0.5))
        for i in range(npts):
            a = base + 1 + i
            bb = base + 1 + (i + 1) % npts
            if sign > 0:
                f.append([base, a, bb])
            else:
                f.append([base, bb, a])
    return Part(name, mat, v, n, uv, f)


def circle_poly(r, n=24, squash=(1.0, 1.0), rot=0.0):
    a = np.linspace(0, TAU, n, endpoint=False) + rot
    return [(np.cos(t) * r * squash[0], np.sin(t) * r * squash[1]) for t in a]


def rounded_rect_poly(w, h, r, seg=5):
    """Rounded rectangle outline in 2D (x right, y up), CCW."""
    pts = []
    corners = [(w * 0.5 - r, h * 0.5 - r, 0.0), (-w * 0.5 + r, h * 0.5 - r, np.pi * 0.5),
               (-w * 0.5 + r, -h * 0.5 + r, np.pi), (w * 0.5 - r, -h * 0.5 + r, np.pi * 1.5)]
    for cx, cy, a0 in corners:
        for k in range(seg + 1):
            a = a0 + np.pi * 0.5 * k / seg
            pts.append((cx + r * np.cos(a), cy + r * np.sin(a)))
    return pts


def hex_poly(r):
    return [(np.cos(TAU * k / 6 + np.pi / 6) * r, np.sin(TAU * k / 6 + np.pi / 6) * r) for k in range(6)]


def trapezoid_poly(w_bot, w_top, h):
    return [(-w_bot * 0.5, -h * 0.5), (w_bot * 0.5, -h * 0.5), (w_top * 0.5, h * 0.5), (-w_top * 0.5, h * 0.5)]


# ---------------------------------------------------------------------- merging
class Mesh(object):
    """Merged geometry ready for skinning + export."""

    def __init__(self):
        self.v = np.zeros((0, 3))
        self.n = np.zeros((0, 3))
        self.uv = np.zeros((0, 2))
        self.f = np.zeros((0, 3), dtype=np.int32)
        self.face_mat = []          # material key per face
        self.vert_part = np.zeros(0, dtype=np.int32)
        self.parts = []             # list of (name, mat, bones)

    def add(self, part):
        off = len(self.v)
        pid = len(self.parts)
        self.parts.append((part.name, part.mat, part.bones))
        self.v = np.vstack([self.v, part.v])
        self.n = np.vstack([self.n, part.n])
        self.uv = np.vstack([self.uv, part.uv])
        self.f = np.vstack([self.f, part.f + off]).astype(np.int32)
        self.face_mat.extend([part.mat] * len(part.f))
        self.vert_part = np.concatenate([self.vert_part, np.full(len(part.v), pid, dtype=np.int32)])
        return self

    def add_all(self, parts):
        for p in parts:
            self.add(p)
        return self

    def tri_count(self):
        return len(self.f)

    def bbox(self):
        return self.v.min(axis=0), self.v.max(axis=0)

    def apply_flat_shading(self):
        """Recompute normals per-face for parts flagged flat (mineral facets)."""
        flat_parts = {i for i, (_, _, _) in enumerate(self.parts) if False}
        return self


def flat_normals(part):
    """Split vertices so each face has its own normal (crisp facets)."""
    v, n, uv, f = [], [], [], []
    for tri in part.f:
        p0, p1, p2 = part.v[tri[0]], part.v[tri[1]], part.v[tri[2]]
        fn = np.cross(p1 - p0, p2 - p0)
        L = np.linalg.norm(fn)
        fn = fn / L if L > 1e-12 else np.array([0.0, 1.0, 0.0])
        base = len(v)
        for k, vi in enumerate(tri):
            v.append(part.v[vi]); n.append(fn); uv.append(part.uv[vi])
        f.append([base, base + 1, base + 2])
    p = Part(part.name, part.mat, v, n, uv, f, bones=part.bones, flat=True)
    return p
