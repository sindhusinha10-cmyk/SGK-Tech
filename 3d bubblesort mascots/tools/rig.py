"""
rig — skeleton definition, automatic smooth skinning, pose evaluation and clip baking.

Every mascot shares the same 14-bone core so the website can drive all five with one
animation state machine, plus an optional block of extra bones for silhouette-specific
appendages (crown, handles, fins, fronds, armour rings, extra legs).

Core bones (parent -> child) and what they are for:

    root                 world anchor, never animated  (hops stay in place)
    hips                 crouch / hop / land vertical motion + squash
    spine  -> chest      breathing, lean, compare-twist
    neck   -> head       glances, nods, tilts
    head   -> lidL, lidR blinks            (one bone per eyelid)
    head   -> eyeL, eyeR gaze offset / squint / sparkle
    chest  -> badge      the blank number plate: stays undeformed so labels never warp
    hips   -> legL, legR foot plants, crouch compression
    hips   -> base       ground-contact pad for legless silhouettes (pot, gel drop)

Poses are plain python dicts::

    { 'head': {'r': (rx, ry, rz),        # local euler rotation (radians, ZYX order)
               't': (dx, dy, dz),        # offset added to the rest translation
               's': (sx, sy, sz)} }      # local scale

Any bone may be omitted; omitted bones stay at rest.
"""

import numpy as np

from mlib import TAU, euler_matrix, quat_from_euler, qnorm

CORE_BONE_ORDER = ["root", "hips", "spine", "chest", "neck", "head",
                   "lidL", "lidR", "eyeL", "eyeR", "badge",
                   "legL", "legR", "base"]


class Bone(object):
    def __init__(self, name, parent, offset, deform=True, w_dir=(0, 0, 0), w_len=0.0001,
                 w_radius=0.10, group="core"):
        self.name = name
        self.parent = parent
        self.offset = np.asarray(offset, dtype=np.float64)
        self.deform = deform
        self.w_dir = np.asarray(w_dir, dtype=np.float64)
        self.w_len = float(w_len)
        self.w_radius = float(w_radius)
        self.group = group


def core_bones(p):
    """Build the 14 shared bones from a proportions dict `p`."""
    hipY, spineY, chestY = p["hipY"], p["spineY"], p["chestY"]
    neckY, headY = p["neckY"], p["headY"]
    legX, legY = p.get("legX", 0.16), p.get("legY", 0.06)
    baseY = p.get("baseY", 0.02)
    badgeY, badgeZ = p["badgeY"], p["badgeZ"]
    eyeX, eyeY, eyeZ = p["eyeX"], p["eyeY"], p["eyeZ"]

    B = []
    add = B.append
    add(Bone("root", None, (0, 0, 0), deform=False))
    add(Bone("hips", "root", (0, hipY, 0), w_dir=(0, 1, 0), w_len=0.10, w_radius=p.get("r_hips", 0.30)))
    add(Bone("spine", "hips", (0, spineY - hipY, 0), w_dir=(0, 1, 0), w_len=0.12, w_radius=p.get("r_spine", 0.26)))
    add(Bone("chest", "spine", (0, chestY - spineY, 0), w_dir=(0, 1, 0), w_len=0.12, w_radius=p.get("r_chest", 0.26)))
    add(Bone("neck", "chest", (0, neckY - chestY, 0), w_dir=(0, 1, 0), w_len=0.06, w_radius=p.get("r_neck", 0.14)))
    add(Bone("head", "neck", (0, headY - neckY, 0), w_dir=(0, 1, 0), w_len=0.10, w_radius=p.get("r_head", 0.20)))
    add(Bone("lidL", "head", (-eyeX, eyeY - headY, eyeZ), group="face"))
    add(Bone("lidR", "head", (eyeX, eyeY - headY, eyeZ), group="face"))
    add(Bone("eyeL", "head", (-eyeX, eyeY - headY, eyeZ), group="face"))
    add(Bone("eyeR", "head", (eyeX, eyeY - headY, eyeZ), group="face"))
    add(Bone("badge", "chest", (0, badgeY - chestY, badgeZ), group="badge"))
    add(Bone("legL", "hips", (-legX, legY - hipY, 0), w_dir=(0, 1, 0), w_len=max(legY, 0.05),
             w_radius=p.get("r_leg", 0.11)))
    add(Bone("legR", "hips", (legX, legY - hipY, 0), w_dir=(0, 1, 0), w_len=max(legY, 0.05),
             w_radius=p.get("r_leg", 0.11)))
    add(Bone("base", "hips", (0, baseY - hipY, 0), w_dir=(0, -1, 0), w_len=0.08,
             w_radius=p.get("r_base", 0.30)))
    return B


class Skeleton(object):
    def __init__(self, bones):
        self.bones = bones
        self.index = {b.name: i for i, b in enumerate(bones)}
        self.parent_idx = [(-1 if b.parent is None else self.index[b.parent]) for b in bones]
        self.rest_local = [b.offset.copy() for b in bones]
        self.rest_world = self._world_matrices({})

    # ------------------------------------------------------------------ helpers
    def _world_matrices(self, pose):
        mats = []
        for i, b in enumerate(self.bones):
            local = np.eye(4)
            local[:3, :3] = euler_matrix(*pose.get(b.name, {}).get("r", (0, 0, 0)))[:3, :3]
            s = pose.get(b.name, {}).get("s")
            if s:
                local[:3, :3] = local[:3, :3] @ np.diag(np.asarray(s, dtype=np.float64))
            t = self.rest_local[i] + np.asarray(pose.get(b.name, {}).get("t", (0, 0, 0)), dtype=np.float64)
            local[:3, 3] = t
            p = self.parent_idx[i]
            mats.append(local if p < 0 else mats[p] @ local)
        return mats

    def world(self, pose=None):
        return self._world_matrices(pose or {})

    def rest_pos(self, name):
        return self.rest_world[self.index[name]][:3, 3].copy()

    def ibms(self):
        out = []
        for i in range(len(self.bones)):
            out.append(np.linalg.inv(self.rest_world[i]))
        return np.array(out)

    def deform_bones(self):
        return [i for i, b in enumerate(self.bones) if b.deform]

    def describe(self):
        rows = []
        for i, b in enumerate(self.bones):
            pos = self.rest_world[i][:3, 3]
            rows.append({"name": b.name, "parent": b.parent, "group": b.group,
                         "rest": [round(float(x), 4) for x in pos]})
        return rows


# ------------------------------------------------------------------- skinning
def _seg_distance(P, a, b):
    ab = b - a
    denom = float(np.dot(ab, ab))
    if denom < 1e-12:
        return np.linalg.norm(P - a, axis=1)
    t = np.clip(((P - a) @ ab) / denom, 0.0, 1.0)
    proj = a + t[:, None] * ab
    return np.linalg.norm(P - proj, axis=1)


def compute_weights(mesh, skel, rigid_map=None, power=0.35, max_infl=4, blend_floor=0.0):
    """Distance-weighted skinning over the *allowed* bones of each part.

    mesh.vert_part indexes mesh.parts (name, material, allowed bone names).  A part
    that names exactly one bone binds rigidly, which is what we want for badges,
    eyes, lids, armour rings and fins (no rubbery distortion of hard parts).
    """
    N = len(mesh.v)
    J = np.zeros((N, max_infl), dtype=np.uint8)
    W = np.zeros((N, max_infl), dtype=np.float32)
    rigid_map = rigid_map or {}

    allow_cache = {}
    for i, (pname, _mat, bones) in enumerate(mesh.parts):
        if not bones:
            allow_cache[i] = None
        elif len(bones) == 1:
            allow_cache[i] = ("rigid", skel.index[bones[0]])
        else:
            allow_cache[i] = ("multi", [skel.index[b] for b in bones])

    for pid in range(len(mesh.parts)):
        sel = np.where(mesh.vert_part == pid)[0]
        if len(sel) == 0:
            continue
        entry = allow_cache[pid]
        pname = mesh.parts[pid][0]
        if entry is None:                                # nearest-bone fallback
            cand = [i for i, b in enumerate(skel.bones) if b.deform]
        elif entry[0] == "rigid":
            J[sel, 0] = entry[1]
            W[sel, 0] = 1.0
            continue
        else:
            cand = entry[1]

        P = mesh.v[sel]
        D = np.zeros((len(sel), len(cand)))
        for k, bi in enumerate(cand):
            b = skel.bones[bi]
            head = skel.rest_world[bi][:3, 3]
            tail = head + b.w_dir * b.w_len
            D[:, k] = _seg_distance(P, head, tail)
        rad = np.array([skel.bones[bi].w_radius for bi in cand])
        # smooth radial falloff, then sharpen
        Wn = np.exp(-np.power(D / rad[None, :], 2.0) * 1.6) + blend_floor
        Wn = Wn / np.maximum(D, 1e-4) ** (power * 0.5)
        # keep top max_infl
        order = np.argsort(-Wn, axis=1)[:, :max_infl]
        for r in range(len(sel)):
            idxs = order[r]
            vals = Wn[r, idxs]
            s = vals.sum()
            if s <= 1e-12:
                vals = np.ones(len(idxs)); s = float(len(idxs))
            vals = vals / s
            J[sel[r], :len(idxs)] = [cand[k] for k in idxs]
            W[sel[r], :len(idxs)] = vals.astype(np.float32)
    return J, W


def deform(mesh, skel, pose, joints, weights):
    """Linear blend skinning — used by the PNG renderer and by pose previews."""
    mats = skel._world_matrices(pose)
    ibm = skel.ibms()
    V = np.concatenate([mesh.v, np.ones((len(mesh.v), 1))], axis=1)
    out = np.zeros((len(mesh.v), 3))
    nrm = np.zeros((len(mesh.v), 3))
    for k in range(weights.shape[1]):
        w = weights[:, k]
        nz = np.where(w > 0)[0]
        if len(nz) == 0:
            continue
        for ji in np.unique(joints[nz, k]):
            sel = nz[joints[nz, k] == ji]
            M = mats[ji] @ ibm[ji]
            out[sel] += w[sel, None] * (V[sel] @ M.T)[:, :3]
            A = np.linalg.inv(M[:3, :3]).T
            nrm[sel] += w[sel, None] * (mesh.n[sel] @ A.T)
    L = np.linalg.norm(nrm, axis=1, keepdims=True)
    L[L < 1e-9] = 1.0
    return out, nrm / L


# ------------------------------------------------------------------ clip baking
def _decimate(times, values, tol):
    """Drop keyframes that a straight line already reproduces within `tol`."""
    n = len(times)
    if n <= 2:
        return times, values
    keep = np.zeros(n, dtype=bool)
    keep[0] = keep[-1] = True
    stack = [(0, n - 1)]
    while stack:
        i0, i1 = stack.pop()
        if i1 - i0 < 2:
            continue
        t0, t1 = times[i0], times[i1]
        span = max(t1 - t0, 1e-9)
        worst, wi = -1.0, -1
        for i in range(i0 + 1, i1):
            a = (times[i] - t0) / span
            lin = values[i0] * (1 - a) + values[i1] * a
            d = float(np.max(np.abs(lin - values[i])))
            if d > worst:
                worst, wi = d, i
        if worst > tol:
            keep[wi] = True
            stack.append((i0, wi)); stack.append((wi, i1))
    return times[keep], values[keep]


def bake_clip(skel, name, pose_fn, duration, fps=30, tol_rot=1.5e-3, tol_pos=8e-4, tol_scale=1e-3):
    """Sample a pose function into glTF-ready per-node tracks.

    Returns (tracks, meta) where tracks maps bone name ->
    {'translation'|'rotation'|'scale': (times, values)} — only channels that
    actually move are emitted, so files stay small.
    """
    frames = int(round(duration * fps)) + 1
    times = np.arange(frames, dtype=np.float64) / fps
    times[-1] = duration

    acc = {}
    for i, b in enumerate(skel.bones):
        rot = np.zeros((frames, 4))
        tra = np.zeros((frames, 3))
        scl = np.zeros((frames, 3))
        rest_q = np.array([0.0, 0.0, 0.0, 1.0])
        for fi, t in enumerate(times):
            p = pose_fn(float(t)).get(b.name, {})
            rot[fi] = qnorm(quat_from_euler(*p.get("r", (0, 0, 0))))
            tra[fi] = skel.rest_local[i] + np.asarray(p.get("t", (0, 0, 0)), dtype=np.float64)
            scl[fi] = np.asarray(p.get("s", (1, 1, 1)), dtype=np.float64)
        if np.max(np.abs(rot - rot[0])) > 1e-7:
            # keep the quaternion hemisphere consistent for interpolation
            for fi in range(1, frames):
                if np.dot(rot[fi], rot[fi - 1]) < 0:
                    rot[fi] *= -1.0
            tt, vv = _decimate(times.copy(), rot, tol_rot)
            acc.setdefault(b.name, {})["rotation"] = (tt, vv)
        rest_t = skel.rest_local[i]
        if np.max(np.abs(tra - rest_t[None, :])) > 1e-6:
            tt, vv = _decimate(times.copy(), tra, tol_pos)
            acc.setdefault(b.name, {})["translation"] = (tt, vv)
        if np.max(np.abs(scl - 1.0)) > 1e-6:
            tt, vv = _decimate(times.copy(), scl, tol_scale)
            acc.setdefault(b.name, {})["scale"] = (tt, vv)

    meta = {"name": name, "duration": round(float(duration), 4), "fps": fps,
            "tracks": sum(len(v) for v in acc.values()),
            "keys": int(sum(len(a[0]) for v in acc.values() for a in v.values()))}
    return acc, meta


def lcg(seed):
    """Tiny deterministic RNG so builds are byte-reproducible."""
    state = [seed & 0x7FFFFFFF]

    def nxt():
        state[0] = (1103515245 * state[0] + 12345) & 0x7FFFFFFF
        return state[0] / float(0x7FFFFFFF)

    return nxt
