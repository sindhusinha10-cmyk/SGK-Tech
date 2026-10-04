#!/usr/bin/env python3
"""
validate.py — independent verification of the five exported GLBs.

Nothing here trusts the build script: it re-reads each .glb from disk, checks the
glTF structure against the spec's limits, re-implements linear-blend skinning from
the file's own data and confirms the clips really do move the skeleton, then
writes specs/validation_report.json.

    python3 validate.py
"""

import json
import os
import struct
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MODELS = os.path.join(ROOT, "models")
SPECS = os.path.join(ROOT, "specs")

TRI_BUDGET = 15000
EXPECT_CLIPS = ["Idle", "GlanceL", "GlanceR", "Crouch", "Hop", "Land", "NoSwap", "Success"]

COMP = {5120: ("b", 1), 5121: ("B", 1), 5122: ("h", 2), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
NCOMP = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4, "MAT4": 16}


def read_glb(path):
    with open(path, "rb") as fh:
        data = fh.read()
    magic, version, length = struct.unpack("<4sII", data[:12])
    assert magic == b"glTF", "not a GLB"
    assert version == 2, "glTF %d" % version
    assert length == len(data), "declared length %d != file length %d" % (length, len(data))
    off = 12
    js, bin_chunk = None, None
    while off < length:
        clen, ctype = struct.unpack("<I4s", data[off:off + 8])
        chunk = data[off + 8: off + 8 + clen]
        if ctype == b"JSON":
            js = json.loads(chunk.decode("utf-8"))
        elif ctype.startswith(b"BIN"):
            bin_chunk = chunk
        off += 8 + clen
    return js, bin_chunk


def accessor(gl, blob, idx):
    a = gl["accessors"][idx]
    bv = gl["bufferViews"][a["bufferView"]]
    fmt, size = COMP[a["componentType"]]
    n = NCOMP[a["type"]]
    start = bv.get("byteOffset", 0) + a.get("byteOffset", 0)
    count = a["count"]
    stride = bv.get("byteStride") or size * n
    if stride == size * n:
        arr = np.frombuffer(blob, dtype=np.dtype(fmt), count=count * n, offset=start)
        return arr.reshape(count, n) if n > 1 else arr
    out = np.empty((count, n), dtype=np.dtype(fmt))
    for i in range(count):
        out[i] = np.frombuffer(blob, dtype=np.dtype(fmt), count=n, offset=start + i * stride)
    return out


def quat_to_mat(q):
    x, y, z, w = q
    return np.array([
        [1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
        [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
        [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)],
    ])


def node_local(node, anim_state=None):
    t = np.array(node.get("translation", [0, 0, 0]), dtype=np.float64)
    q = np.array(node.get("rotation", [0, 0, 0, 1]), dtype=np.float64)
    s = np.array(node.get("scale", [1, 1, 1]), dtype=np.float64)
    if anim_state and "node" in anim_state:
        pass
    M = np.eye(4)
    M[:3, :3] = quat_to_mat(q) @ np.diag(s)
    M[:3, 3] = t
    return M


def world_matrices(gl, anim=None, time=None):
    """Compose the node hierarchy; `anim` = {node_index: {path: (times, values)}}."""
    nodes = gl["nodes"]
    order = []
    seen = set()

    def walk(i):
        if i in seen:
            return
        seen.add(i)
        order.append(i)
        for c in nodes[i].get("children", []):
            walk(c)

    for i in range(len(nodes)):
        walk(i)

    mats = {}
    for i in order:
        n = nodes[i]
        t = np.array(n.get("translation", [0, 0, 0]), dtype=np.float64)
        q = np.array(n.get("rotation", [0, 0, 0, 1]), dtype=np.float64)
        s = np.array(n.get("scale", [1, 1, 1]), dtype=np.float64)
        if anim and i in anim and time is not None:
            if "translation" in anim[i]:
                ts, vs = anim[i]["translation"]
                t = np.array([np.interp(time, ts, vs[:, k]) for k in range(3)])
            if "rotation" in anim[i]:
                ts, vs = anim[i]["rotation"]
                q = np.array([np.interp(time, ts, vs[:, k]) for k in range(4)])
                q /= max(np.linalg.norm(q), 1e-12)
            if "scale" in anim[i]:
                ts, vs = anim[i]["scale"]
                s = np.array([np.interp(time, ts, vs[:, k]) for k in range(3)])
        M = np.eye(4)
        M[:3, :3] = quat_to_mat(q) @ np.diag(s)
        M[:3, 3] = t
        parent = None
        for j, nd in enumerate(nodes):
            if i in nd.get("children", []):
                parent = j
                break
        mats[i] = (mats[parent] @ M) if parent is not None else M
    return mats


def skin_mesh(gl, blob, mats, skin):
    """Linear blend skinning straight from the file."""
    mesh_i = None
    for i, n in enumerate(gl["nodes"]):
        if "mesh" in n and "skin" in n:
            mesh_i = i
            break
    if mesh_i is None:
        return None, None
    prim = gl["meshes"][gl["nodes"][mesh_i]["mesh"]]["primitives"][0]
    pos = accessor(gl, blob, prim["attributes"]["POSITION"]).astype(np.float64)
    jnt = accessor(gl, blob, prim["attributes"]["JOINTS_0"]).astype(int)
    wgt = accessor(gl, blob, prim["attributes"]["WEIGHTS_0"]).astype(np.float64)
    ibm = accessor(gl, blob, skin["inverseBindMatrices"]).astype(np.float64).reshape(-1, 4, 4)
    ibm = np.transpose(ibm, (0, 2, 1))          # file is column-major
    joints = skin["joints"]
    out = np.zeros_like(pos)
    for k in range(jnt.shape[1]):
        w = wgt[:, k]
        nz = np.where(w > 1e-6)[0]
        for j in np.unique(jnt[nz, k]):
            sel = nz[jnt[nz, k] == j]
            M = mats[joints[j]] @ ibm[j]
            ph = np.concatenate([pos[sel], np.ones((len(sel), 1))], axis=1)
            out[sel] += w[sel, None] * (ph @ M.T)[:, :3]
    return out, pos


def check(cid):
    path = os.path.join(MODELS, "%s.glb" % cid)
    gl, blob = read_glb(path)
    res = {"id": cid, "file": os.path.basename(path), "bytes": os.path.getsize(path),
           "checks": [], "warnings": []}

    def ck(name, ok, detail=""):
        res["checks"].append({"name": name, "pass": bool(ok), "detail": detail})
        return ok

    # ---- structure -------------------------------------------------------
    ck("glTF 2.0 asset", gl["asset"]["version"] == "2.0", gl["asset"].get("generator", ""))
    n_skin = len(gl.get("skins", []))
    ck("has a skin", n_skin == 1, "%d skin(s)" % n_skin)
    skin = gl["skins"][0]
    ck("skin has joints", len(skin["joints"]) > 0, "%d joints" % len(skin["joints"]))
    ck("inverse bind matrices", "inverseBindMatrices" in skin)

    # bufferView bounds
    bad = 0
    for bv in gl["bufferViews"]:
        if bv.get("byteOffset", 0) + bv["byteLength"] > len(blob):
            bad += 1
    ck("bufferViews inside BIN chunk", bad == 0, "%d out of range" % bad)

    # ---- mesh ------------------------------------------------------------
    tris = 0
    verts = 0
    prims = 0
    for m in gl["meshes"]:
        for p in m["primitives"]:
            idx = accessor(gl, blob, p["indices"])
            tris += len(idx) // 3
            prims += 1
            verts = max(verts, gl["accessors"][p["attributes"]["POSITION"]]["count"])
    res["triangles"] = int(tris)
    res["vertices"] = int(verts)
    res["primitives"] = prims
    res["materials"] = len(gl["materials"])
    res["images"] = len(gl.get("images", []))
    ck("triangles under budget", tris <= TRI_BUDGET, "%d / %d" % (tris, TRI_BUDGET))
    ck("single mesh, multiple materials", len(gl["meshes"]) == 1, "%d mesh(es), %d prims" % (len(gl["meshes"]), prims))

    # ---- skin weights ----------------------------------------------------
    prim = gl["meshes"][gl["nodes"][[i for i, n in enumerate(gl["nodes"]) if "skin" in n][0]]["mesh"]]["primitives"][0]
    jnt = accessor(gl, blob, prim["attributes"]["JOINTS_0"]).astype(int)
    wgt = accessor(gl, blob, prim["attributes"]["WEIGHTS_0"]).astype(np.float64)
    s = wgt.sum(axis=1)
    ck("weights normalised", bool(np.allclose(s, 1.0, atol=2e-2)), "min %.4f max %.4f" % (s.min(), s.max()))
    ck("joint indices in range", int(jnt.max()) < len(skin["joints"]),
       "max joint %d of %d" % (jnt.max(), len(skin["joints"])))
    res["max_influences_used"] = int((wgt > 1e-6).sum(axis=1).max())

    # ---- rest pose -------------------------------------------------------
    rest = world_matrices(gl)
    mesh_node = [i for i, n in enumerate(gl["nodes"]) if "skin" in n][0]
    pos = accessor(gl, blob, prim["attributes"]["POSITION"]).astype(np.float64)
    lo, hi = pos.min(axis=0), pos.max(axis=0)
    res["bbox_min"] = [round(float(x), 4) for x in lo]
    res["bbox_max"] = [round(float(x), 4) for x in hi]
    res["height"] = round(float(hi[1] - lo[1]), 4)
    ck("origin on the ground", abs(lo[1]) < 0.01, "min y = %.4f" % lo[1])
    ck("Y up (taller than deep)", (hi[1] - lo[1]) > (hi[2] - lo[2]) * 0.5,
       "h=%.3f d=%.3f" % (hi[1] - lo[1], hi[2] - lo[2]))

    # ---- front direction: eye materials must sit on +Z -------------------
    eye_centroids = []
    for p in gl["meshes"][0]["primitives"]:
        mat = gl["materials"][p["material"]]
        if mat.get("extras", {}).get("sgk_surface") in ("eye_dark", "glow"):
            idx = accessor(gl, blob, p["indices"]).ravel()
            eye_centroids.append(pos[idx].mean(axis=0))
    if eye_centroids:
        fz = min(c[2] for c in eye_centroids)
        ck("front faces +Z (eyes on +Z)", fz > 0.02,
           "front-most eye centroid z = %.3f" % fz)
    else:
        res["warnings"].append("no eye material found for the front-direction test")

    # ---- animations ------------------------------------------------------
    names = [a["name"] for a in gl.get("animations", [])]
    ck("all eight clips present", names == EXPECT_CLIPS, ", ".join(names))
    anim_probe = {}
    for a in gl.get("animations", []):
        dur = 0.0
        for s_ in a["samplers"]:
            t = accessor(gl, blob, s_["input"])
            dur = max(dur, float(t.max()))
            if not np.all(np.diff(t) > 0):
                res["warnings"].append("%s: non-monotonic keyframe times" % a["name"])
    res["clips"] = []
    for a in gl.get("animations", []):
        keys = 0
        dur = 0.0
        tracks = {}
        for ch in a["channels"]:
            s_ = a["samplers"][ch["sampler"]]
            t = accessor(gl, blob, s_["input"]).astype(np.float64)
            v = accessor(gl, blob, s_["output"]).astype(np.float64)
            dur = max(dur, float(t.max()))
            keys += len(t)
            tracks.setdefault(ch["target"]["node"], {})[ch["target"]["path"]] = (t, v)
        res["clips"].append({"name": a["name"], "duration": round(dur, 3),
                             "channels": len(a["channels"]), "keys": keys})
        anim_probe[a["name"]] = (dur, tracks)
    ck("keyframe budget", all(c["keys"] <= 1200 for c in res["clips"]),
       "max %d keys/clip" % max(c["keys"] for c in res["clips"]))

    # ---- skinning actually moves the mesh --------------------------------
    root_moved = False
    for clip in ("Hop", "Success", "GlanceL", "Land"):
        if clip not in anim_probe:
            continue
        dur, tracks = anim_probe[clip]
        for t in (0.0, dur * 0.33, dur * 0.66, dur):
            mats = world_matrices(gl, tracks, t)
            out, _ = skin_mesh(gl, blob, mats, skin)
            if out is None:
                continue
            if not np.all(np.isfinite(out)):
                ck("%s deforms without NaN" % clip, False, "t=%.2f" % t)
                break
            r_lo, r_hi = out.min(axis=0), out.max(axis=0)
            if np.abs(out - pos).max() > 1e-4:
                root_moved = True
            # hop must lift the body and the feet must not sink through the floor
            if clip == "Hop" and t > dur * 0.25 and t < dur * 0.6:
                ck("Hop lifts the body", r_hi[1] > hi[1] + 0.05,
                   "t=%.2f apex y=%.3f vs rest %.3f" % (t, r_hi[1], hi[1]))
                ck("Hop keeps the feet near the ground", r_lo[1] > -0.06,
                   "t=%.2f min y=%.4f" % (t, r_lo[1]))
    ck("skinning deforms the mesh", root_moved, "mesh follows the joint hierarchy")

    # ---- badge anchor ----------------------------------------------------
    badge_anchor = None
    for i, n in enumerate(gl["nodes"]):
        if n.get("name") == "badge":
            badge_anchor = world_matrices(gl)[i][:3, 3]
    ck("badge bone exists at the chest", badge_anchor is not None and badge_anchor[2] > 0.05,
       "anchor = %s" % (np.round(badge_anchor, 3).tolist() if badge_anchor is not None else None))
    res["badge_anchor"] = [round(float(x), 4) for x in badge_anchor] if badge_anchor is not None else None

    # ---- idle must be seamless -------------------------------------------
    if "Idle" in anim_probe:
        dur, tracks = anim_probe["Idle"]
        m0 = world_matrices(gl, tracks, 0.0)
        m1 = world_matrices(gl, tracks, dur)
        worst = 0.0
        for i in m0:
            worst = max(worst, float(np.abs(m0[i] - m1[i]).max()))
        ck("Idle loops seamlessly", worst < 2e-3, "max joint delta over the loop = %.5f" % worst)

    res["pass"] = all(c["pass"] for c in res["checks"])
    return res


def main():
    ids = sys.argv[1:] or ["gaja", "mayur", "diya", "patra", "kumbha"]
    report = {"models": [], "summary": {}}
    width = 44
    print("%-8s %-6s %s" % ("char", "result", "detail"))
    for cid in ids:
        r = check(cid)
        report["models"].append(r)
        nj = len(read_glb(os.path.join(MODELS, "%s.glb" % cid))[0]["skins"][0]["joints"])
        print("%-8s %-6s %2d checks | %5d tris | %2d joints | %d clips | %6.0f KB" %
              (cid, "PASS" if r["pass"] else "FAIL", len(r["checks"]), r["triangles"],
               nj, len(r["clips"]), r["bytes"] / 1024.0))
        for c in r["checks"]:
            if not c["pass"]:
                print("    FAIL %-38s %s" % (c["name"], c["detail"]))
        for w in r["warnings"]:
            print("    warn %s" % w)
    report["summary"] = {
        "models": len(report["models"]),
        "passed": sum(1 for m in report["models"] if m["pass"]),
        "total_triangles": sum(m["triangles"] for m in report["models"]),
        "max_triangles": max(m["triangles"] for m in report["models"]),
        "total_bytes": sum(m["bytes"] for m in report["models"]),
        "clips_per_model": [len(m["clips"]) for m in report["models"]],
    }
    os.makedirs(SPECS, exist_ok=True)
    with open(os.path.join(SPECS, "validation_report.json"), "w") as fh:
        json.dump(report, fh, indent=1)
    s = report["summary"]
    print("\n%d/%d models pass | %d triangles total | max %d/15000 | %.0f KB" %
          (s["passed"], s["models"], s["total_triangles"], s["max_triangles"], s["total_bytes"] / 1024.0))
    return 0 if s["passed"] == s["models"] else 1


if __name__ == "__main__":
    sys.exit(main())
