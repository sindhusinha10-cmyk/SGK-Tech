"""
render — a small numpy software renderer used to produce every PNG deliverable
(roster sheet, per-character orthographic views, silhouette test, animation strip).

It renders the *actual* rigged, skinned geometry through the same pose functions
that get baked into the GLBs, so the sheets are honest previews of the models.
"""

import math

import numpy as np
from PIL import Image, ImageDraw, ImageFont

import textures

FONT_DIR = "/usr/share/fonts/truetype/dejavu/"
SKY = np.array([0.34, 0.40, 0.50])
GROUND = np.array([0.10, 0.09, 0.11])

DEFAULT_LIGHTS = [
    # (direction toward the light, colour, intensity)
    ((-0.55, 0.82, 0.70), np.array([1.00, 0.96, 0.90]), 1.35),
    ((0.85, 0.28, 0.42), np.array([0.62, 0.72, 0.92]), 0.55),
    ((0.15, 0.42, -0.95), np.array([0.86, 0.92, 1.00]), 0.85),
    ((0.10, -0.95, 0.25), np.array([0.30, 0.26, 0.24]), 0.30),
]


def font(size, bold=False):
    try:
        return ImageFont.truetype(FONT_DIR + ("DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), size)
    except Exception:
        return ImageFont.load_default()


# ------------------------------------------------------------------- camera
def look_at(eye, at, up=(0, 1, 0), fov=math.radians(30), aspect=1.0, near=0.05, far=60.0):
    eye = np.asarray(eye, dtype=np.float64)
    at = np.asarray(at, dtype=np.float64)
    fwd = at - eye
    fwd /= np.linalg.norm(fwd)
    up = np.asarray(up, dtype=np.float64)
    right = np.cross(fwd, up)
    right /= np.linalg.norm(right)
    upv = np.cross(right, fwd)
    R = np.stack([right, upv, -fwd])                      # world -> view rotation
    V = np.eye(4)
    V[:3, :3] = R
    V[:3, 3] = -R @ eye
    f = 1.0 / math.tan(fov * 0.5)
    P = np.zeros((4, 4))
    P[0, 0] = f / max(aspect, 1e-6)
    P[1, 1] = f
    P[2, 2] = (far + near) / (near - far)
    P[2, 3] = 2 * far * near / (near - far)
    P[3, 2] = -1.0
    return V, P, eye, at


def ortho(eye_dir, at, height, aspect=1.0, near=-10.0, far=10.0):
    """Orthographic camera along eye_dir (used for the clean view sheets)."""
    d = np.asarray(eye_dir, dtype=np.float64)
    d = d / np.linalg.norm(d)
    fwd = -d
    up = np.array([0.0, 1.0, 0.0])
    if abs(np.dot(fwd, up)) > 0.98:
        up = np.array([0.0, 0.0, 1.0])
    right = np.cross(fwd, up); right /= np.linalg.norm(right)
    upv = np.cross(right, fwd)
    R = np.stack([right, upv, -fwd])
    V = np.eye(4); V[:3, :3] = R; V[:3, 3] = -R @ np.asarray(at, dtype=np.float64)
    h = height * 0.5
    w = h * aspect
    P = np.eye(4)
    P[0, 0] = 1.0 / w
    P[1, 1] = 1.0 / h
    P[2, 2] = -2.0 / (far - near)
    P[2, 3] = -(far + near) / (far - near)
    eye = np.asarray(at, dtype=np.float64) - d * 8.0
    return V, P, eye, at


# ------------------------------------------------------------------- shading
def aces(x):
    a, b, c, d, e = 2.51, 0.03, 2.43, 0.59, 0.14
    return np.clip((x * (a * x + b)) / (x * (c * x + d) + e), 0.0, 1.0)


def srgb_encode(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def shade(n, pos, albedo, rough, metal, emissive, view_dir, lights, tex_val=None):
    """Per-pixel deferred shading (all arrays are (P,) or (P,3))."""
    if tex_val is not None:
        albedo = albedo * tex_val
    n = n / np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-9)
    v = -view_dir
    v = v / np.maximum(np.linalg.norm(v, axis=1, keepdims=True), 1e-9)
    col = np.zeros_like(albedo)
    # clamped so glossy surfaces get a tight highlight instead of a blob
    shin = min(max(2.0 / max(rough, 0.03) ** 4 - 2.0, 4.0), 220.0)
    spec_col = (0.05 * (1 - metal) + albedo * metal)
    for dirv, lcol, lint in lights:
        L = np.array(dirv, dtype=np.float64)
        L = L / np.linalg.norm(L)
        ndl = n @ L
        wrap = np.clip((ndl + 0.32) / 1.32, 0.0, 1.0)
        col += albedo * (lcol * lint) * wrap[:, None]
        H = L[None, :] + v
        H = H / np.maximum(np.linalg.norm(H, axis=1, keepdims=True), 1e-9)
        ndh = np.clip(np.sum(n * H, axis=1), 0.0, 1.0)
        spec = np.power(ndh, shin) * (shin + 8.0) / 90.0
        col += spec_col * (lcol * lint) * np.clip(spec, 0, 1.1)[:, None]
    # hemisphere ambient
    hemi = 0.5 + 0.5 * n[:, 1]
    amb = (GROUND[None, :] * (1 - hemi[:, None]) + SKY[None, :] * hemi[:, None])
    ndv = np.clip(np.sum(n * v, axis=1), 0.0, 1.0)
    fres = 0.05 + 0.95 * (1.0 - ndv) ** 4.5
    col += albedo * amb * 0.36
    col += amb * fres[:, None] * 0.22
    col += emissive[None, :]
    return col


def _sample_tex(tex, uv):
    if tex is None:
        return None
    h, w = tex.shape
    x = np.mod(uv[:, 0], 1.0) * (w - 1)
    y = np.mod(uv[:, 1], 1.0) * (h - 1)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    x1 = np.minimum(x0 + 1, w - 1); y1 = np.minimum(y0 + 1, h - 1)
    fx = (x - x0)[:, None]; fy = (y - y0)[:, None]
    a = tex[y0, x0][:, None]; b = tex[y0, x1][:, None]
    c = tex[y1, x0][:, None]; d = tex[y1, x1][:, None]
    return (a * (1 - fx) + b * fx) * (1 - fy) + (c * (1 - fx) + d * fx) * fy


class Scene(object):
    """A pile of skinned meshes + lights, rendered with an analytic studio floor."""

    def __init__(self, width, height, ss=2):
        self.W, self.H, self.ss = width, height, ss
        self.w, self.h = width * ss, height * ss
        self.color = np.zeros((self.h, self.w, 3), dtype=np.float32)
        self.depth = np.full((self.h, self.w), np.inf, dtype=np.float32)
        self.masks = []
        self.lights = DEFAULT_LIGHTS
        self.bg_top = np.array([0.055, 0.062, 0.078])
        self.bg_bot = np.array([0.020, 0.022, 0.030])

    # ---------------------------------------------------------------- drawing
    def camera(self, cam):
        self.V, self.P = cam[0], cam[1]
        self.cam_eye = cam[2] if len(cam) > 2 else None

    def _project(self, V, P, pts):
        ph = np.concatenate([pts, np.ones((len(pts), 1))], axis=1)
        clip = (P @ (V @ ph.T)).T
        w = clip[:, 3:4]
        w = np.where(np.abs(w) < 1e-9, 1e-9, w)
        ndc = clip[:, :3] / w
        sx = (ndc[:, 0] * 0.5 + 0.5) * self.w
        sy = (1.0 - (ndc[:, 1] * 0.5 + 0.5)) * self.h
        return np.stack([sx, sy], axis=1), ndc[:, 2], w[:, 0], ndc

    def add_mesh(self, verts, normals, uvs, faces, mats, alpha_split=True):
        """mats: list per face of dict(albedo, rough, metal, emissive, alpha, texture)."""
        self.masks.append((verts, faces))
        scr, ndc_z, w, _ = self._project(self.V, self.P, verts)
        view = verts @ self.V[:3, :3].T + self.V[:3, 3]
        opaque, blend = [], []
        for fi, tri in enumerate(faces):
            m = mats[fi]
            (blend if m.get("alpha", 1.0) < 0.999 else opaque).append(fi)
        order = opaque + sorted(blend, key=lambda fi: -view[faces[fi], 2].mean())
        for fi in order:
            self._tri(fi, faces, scr, ndc_z, verts, normals, uvs, mats, view)

    def _tri(self, fi, faces, scr, ndc_z, verts, normals, uvs, mats, view):
        tri = faces[fi]
        m = mats[fi]
        s = scr[tri]
        minx = max(int(np.floor(s[:, 0].min())), 0)
        maxx = min(int(np.ceil(s[:, 0].max())) + 1, self.w)
        miny = max(int(np.floor(s[:, 1].min())), 0)
        maxy = min(int(np.ceil(s[:, 1].max())) + 1, self.h)
        if minx >= maxx or miny >= maxy:
            return
        area = ((s[1, 0] - s[0, 0]) * (s[2, 1] - s[0, 1]) -
                (s[1, 1] - s[0, 1]) * (s[2, 0] - s[0, 0]))
        if abs(area) < 1e-9:
            return
        # screen space here has +y downward, which mirrors the 2D cross product,
        # so front-facing triangles have a NEGATIVE screen area
        double = m.get("double_sided", False) or m.get("alpha", 1.0) < 0.999
        if area > 0 and not double:
            return
        ys, xs = np.mgrid[miny:maxy, minx:maxx]
        px = xs.ravel() + 0.5
        py = ys.ravel() + 0.5
        inv = 1.0 / area
        l0 = ((s[1, 0] - px) * (s[2, 1] - py) - (s[1, 1] - py) * (s[2, 0] - px)) * inv
        l1 = ((s[2, 0] - px) * (s[0, 1] - py) - (s[2, 1] - py) * (s[0, 0] - px)) * inv
        l2 = 1.0 - l0 - l1
        inside = (l0 >= -1e-6) & (l1 >= -1e-6) & (l2 >= -1e-6)
        if not inside.any():
            return
        idx = np.where(inside)[0]
        # perspective-correct barycentrics; depth is interpolated in NDC space
        # (linear for the orthographic sheets, hyperbolic for the hero shots)
        zv = ndc_z[tri]
        lam = np.stack([l0[idx], l1[idx], l2[idx]])
        z = lam[0] * zv[0] + lam[1] * zv[1] + lam[2] * zv[2]
        yy = ys.ravel()[idx]
        xx = xs.ravel()[idx]
        zbuf = self.depth[yy, xx]
        keep = (z < zbuf)
        if not keep.any():
            return
        yy, xx, z, lam = yy[keep], xx[keep], z[keep], lam[:, keep]
        P = verts[tri]
        N = normals[tri]
        UV = uvs[tri]
        pos = lam[0][:, None] * P[0] + lam[1][:, None] * P[1] + lam[2][:, None] * P[2]
        nrm = lam[0][:, None] * N[0] + lam[1][:, None] * N[1] + lam[2][:, None] * N[2]
        uv = lam[0][:, None] * UV[0] + lam[1][:, None] * UV[1] + lam[2][:, None] * UV[2]
        view_dir = pos - self.cam_eye[None, :] if self.cam_eye is not None else np.tile(
            np.array([0.0, 0.0, 1.0]), (len(pos), 1))
        tex_val = _sample_tex(m.get("texture"), uv)
        col = shade(nrm, pos, np.tile(m["albedo"], (len(pos), 1)), m["rough"], m["metal"],
                    np.array(m["emissive"]), view_dir, self.lights, tex_val)
        a = m.get("alpha", 1.0)
        if a < 0.999:
            self.color[yy, xx] = self.color[yy, xx] * (1 - a) + col * a
        else:
            self.color[yy, xx] = col
            self.depth[yy, xx] = z

    # ------------------------------------------------------------------ floor
    def draw_background(self, floor_y=0.0, grid=0.0, shadow_softness=9):
        ys, xs = np.mgrid[0:self.h, 0:self.w]
        if self.cam_eye is None:
            ramp = (ys / self.h)[:, :, None]
            self.color = self.bg_top[None, None, :] * (1 - ramp) + self.bg_bot[None, None, :] * ramp
            return np.zeros((self.h, self.w))
        # reconstruct the ray for every pixel
        ndc_x = ((xs + 0.5) / self.w) * 2 - 1
        ndc_y = 1 - ((ys + 0.5) / self.h) * 2
        Pinv = np.linalg.inv(self.P)
        dirs = []
        for a, b in ((ndc_x, ndc_y),):
            v = np.stack([a, b, np.ones_like(a), np.ones_like(a)], axis=-1)
            e = v @ Pinv.T
            dirs.append(e[:, :, :3] / e[:, :, 3:4])
        eye = self.cam_eye
        # camera-space ray directions -> world
        d = dirs[0]
        Rw = self.V[:3, :3].T
        dw = d @ Rw.T
        t = np.where(np.abs(dw[:, :, 1]) < 1e-9, -1.0, (floor_y - eye[1]) / dw[:, :, 1])
        hit = t > 0
        ramp = (ys / self.h)[:, :, None]
        bg = self.bg_top[None, None, :] * (1 - ramp) + self.bg_bot[None, None, :] * ramp
        world = (eye[None, None, :] + dw * t[:, :, None]).astype(np.float32)
        dist = np.linalg.norm(world[:, :, [0, 2]] - eye[[0, 2]][None, None, :], axis=2)
        fade = np.exp(-(dist * 0.36) ** 1.5)[:, :, None]
        floor_col = np.array([0.085, 0.088, 0.105])[None, None, :] * (1.0 + 0.9 * fade)
        col = np.where(hit[:, :, None], floor_col, bg)
        if grid > 0:
            gx = np.abs(np.mod(world[:, :, 0] / grid + 0.5, 1.0) - 0.5)
            gz = np.abs(np.mod(world[:, :, 2] / grid + 0.5, 1.0) - 0.5)
            line = np.clip(1.0 - np.minimum(gx, gz) / 0.02, 0, 1) * hit * fade[:, :, 0]
            col = col + line[:, :, None] * np.array([0.10, 0.11, 0.14])[None, None, :]
        if shadow_softness > 0 and self.masks:
            sh = self._shadow_map(floor_y, world, hit, softness=shadow_softness)
            col = col * (1.0 - 0.55 * sh[:, :, None])
        self.color = col
        self.depth = np.where(hit, 1e5, np.inf).astype(np.float64)

    def _shadow_map(self, floor_y, world, hit, softness=9, span=None, res=320):
        L = np.array(self.lights[0][0], dtype=np.float64)
        L = L / np.linalg.norm(L)
        lo = np.array([np.inf, np.inf]); hi = np.array([-np.inf, -np.inf])
        for verts, faces in self.masks:
            p = verts[:, [0, 2]]
            lo = np.minimum(lo, p.min(axis=0)); hi = np.maximum(hi, p.max(axis=0))
        pad = 0.30
        lo -= pad; hi += pad
        size = res
        sx = size / max(hi[0] - lo[0], 1e-6)
        sz = size / max(hi[1] - lo[1], 1e-6)
        mask = np.zeros((size, size), dtype=np.float32)
        for verts, faces in self.masks:
            # project every vertex onto the floor plane along the light direction
            k = verts[:, 1] / max(L[1], 1e-6)
            proj = verts - k[:, None] * L[None, :]
            gx = (proj[:, 0] - lo[0]) * sx
            gz = (proj[:, 2] - lo[1]) * sz
            for tri in faces:
                x0, x1, x2 = gx[tri]; z0, z1, z2 = gz[tri]
                minx = max(int(x0.min()), 0); maxx = min(int(x0.max()) + 1, size)
                minz = max(int(z0.min()), 0); maxz = min(int(z0.max()) + 1, size)
                if minx >= maxx or minz >= maxz:
                    continue
                zz, xx = np.mgrid[minz:maxz, minx:maxx]
                area = (x1 - x0) * (z2 - z0) - (z1 - z0) * (x2 - x0)
                if abs(area) < 1e-9:
                    continue
                inv = 1.0 / area
                l0 = ((x1 - xx) * (z2 - zz) - (z1 - zz) * (x2 - xx)) * inv
                l1 = ((x2 - xx) * (z0 - zz) - (z2 - zz) * (x0 - xx)) * inv
                l2 = 1 - l0 - l1
                ins = (l0 >= -1e-4) & (l1 >= -1e-4) & (l2 >= -1e-4)
                mask[minz:maxz, minx:maxx][ins] = 1.0
        # blur
        k = int(softness)
        if k > 0:
            ker = np.ones(2 * k + 1) / (2 * k + 1)
            mask = np.apply_along_axis(lambda r: np.convolve(r, ker, mode="same"), 1, mask)
            mask = np.apply_along_axis(lambda r: np.convolve(r, ker, mode="same"), 0, mask)
        mx = np.clip(((world[:, :, 0] - lo[0]) * sx).astype(int), 0, size - 1)
        mz = np.clip(((world[:, :, 2] - lo[1]) * sz).astype(int), 0, size - 1)
        return mask[mz, mx] * hit

    # ---------------------------------------------------------------- compose
    def blit_mask(self, whole_scene=True):
        """Everything drawn into `self.masks` becomes the silhouette mask."""
        return [(v, f) for v, f in self.masks]

    def to_image(self, silhouette=False):
        img = self.color
        if silhouette:
            m = np.zeros((self.h, self.w), dtype=bool)
            for verts, faces in self.masks:
                self._silhouette_mask(m, verts, faces)
            out = np.where(m[:, :, None], 0.02, 1.0)
            out = np.repeat(out, 3, axis=2) if out.shape[2] == 1 else out
            img = out
        else:
            img = srgb_encode(aces(img))
        im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8), "RGB")
        if self.ss != 1:
            im = im.resize((self.W, self.H), Image.LANCZOS)
        return im

    def _silhouette_mask(self, mask, verts, faces):
        scr, _, _, _ = self._project(self.V, self.P, verts)
        for tri in faces:
            s = scr[tri]
            minx = max(int(np.floor(s[:, 0].min())), 0)
            maxx = min(int(np.ceil(s[:, 0].max())) + 1, self.w)
            miny = max(int(np.floor(s[:, 1].min())), 0)
            maxy = min(int(np.ceil(s[:, 1].max())) + 1, self.h)
            if minx >= maxx or miny >= maxy:
                continue
            ys, xs = np.mgrid[miny:maxy, minx:maxx]
            px = xs.ravel() + 0.5
            py = ys.ravel() + 0.5
            area = (s[1, 0] - s[0, 0]) * (s[2, 1] - s[0, 1]) - (s[1, 1] - s[0, 1]) * (s[2, 0] - s[0, 0])
            if abs(area) < 1e-9:
                continue
            inv = 1.0 / area
            l0 = ((s[1, 0] - px) * (s[2, 1] - py) - (s[1, 1] - py) * (s[2, 0] - px)) * inv
            l1 = ((s[2, 0] - px) * (s[0, 1] - py) - (s[2, 1] - py) * (s[0, 0] - px)) * inv
            l2 = 1 - l0 - l1
            ins = ((l0 >= 0) & (l1 >= 0) & (l2 >= 0)).reshape(maxy - miny, maxx - minx)
            mask[miny:maxy, minx:maxx] |= ins
