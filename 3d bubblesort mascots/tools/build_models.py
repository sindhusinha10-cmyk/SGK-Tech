#!/usr/bin/env python3
"""
build_models.py — build the five rigged GLB mascots + their spec files.

    python3 build_models.py                 # writes ../models/*.glb and ../specs/*
    python3 build_models.py kiln            # only one character (fast iteration)

Output per character: skinned mesh, 14 core joints + extras, 8 baked clips,
embedded detail textures. Nothing else is required by the runtime.
"""

import json
import os
import sys
import time

import numpy as np

import clips
import creatures
import rig
import textures
from glb import GLB

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MODELS = os.path.join(ROOT, "models")
SPECS = os.path.join(ROOT, "specs")

FPS = 30


def build_one(cid):
    t0 = time.time()
    ch = creatures.BUILDERS[cid]()
    mesh, skel = ch.mesh, ch.skel

    joints, weights = rig.compute_weights(mesh, skel)

    glb = GLB()

    # ---- textures (shared per kind, embedded once per file) ----------------
    tex_index = {}
    for key in sorted({m.get("texture") for m in ch.mats.values() if m.get("texture")}):
        img = glb.add_image_png(textures.png_bytes(key), key)
        tex_index[key] = glb.add_texture(img)

    # ---- materials ---------------------------------------------------------
    mat_index = {}
    for key in sorted(ch.mats.keys()):
        m = ch.mats[key]
        alpha = float(m.get("alpha", 1.0))
        mi = glb.add_material(
            "%s_%s" % (cid, key),
            base_color=tuple(m["color"]) + (alpha,),
            metallic=m.get("metallic", 0.0),
            roughness=m.get("roughness", 0.5),
            emissive=m.get("emissive", (0, 0, 0)),
            base_color_texture=tex_index.get(m.get("texture")),
            alpha_mode="BLEND" if alpha < 1.0 else "OPAQUE",
            extras={"sgk_surface": key},
        )
        mat_index[key] = mi

    # ---- joint nodes -------------------------------------------------------
    joint_nodes = []
    for b in skel.bones:
        joint_nodes.append(glb.add_node(b.name, translation=tuple(b.offset)))
    for i, b in enumerate(skel.bones):
        if skel.parent_idx[i] >= 0:
            glb.nodes[joint_nodes[skel.parent_idx[i]]].setdefault("children", []).append(joint_nodes[i])

    # ---- mesh primitives grouped by material -------------------------------
    by_mat = {}
    for fi, key in enumerate(mesh.face_mat):
        by_mat.setdefault(key, []).append(mesh.f[fi])
    prims = [(mat_index[k], np.asarray(v, dtype=np.int32)) for k, v in sorted(by_mat.items())]

    badge = ch.skel.rest_pos("badge")
    mesh_node = glb.add_node(
        cid + "_mesh",
        mesh=glb.add_skinned_mesh(cid, mesh.v.astype("float32"), mesh.n.astype("float32"),
                                  mesh.uv.astype("float32"), joints, weights, prims,
                                  extras={"sgk_character": cid}),
        skin=None,
        extras={
            "id": cid, "name": ch.name, "role": ch.role,
            "badgeAnchor": [round(float(x), 4) for x in badge],
            "badgeSize": ch.props.get("badge_size", [0.16, 0.10]),
            "height": ch.meta["height"],
            "clipOrder": [c for c, _ in clips.CLIP_SPECS],
            "fps": FPS,
            "up": "+Y", "front": "+Z",
        },
    )
    skin = glb.add_skin(joint_nodes, skel.ibms(), name=cid + "_armature")
    glb.nodes[mesh_node]["skin"] = skin
    glb.scene_nodes = [joint_nodes[0], mesh_node]

    # ---- clips -------------------------------------------------------------
    fns = clips.build_clip_fns(ch)
    clip_meta = []
    for name, dur in clips.CLIP_SPECS:
        tracks, meta = rig.bake_clip(skel, name, fns[name][1], dur, fps=FPS)
        node_tracks = {joint_nodes[skel.index[b]]: t for b, t in tracks.items()}
        glb.add_animation(name, node_tracks,
                          extras={"loop": name == "Idle", "duration": dur})
        clip_meta.append(meta)

    # ---- write -------------------------------------------------------------
    os.makedirs(MODELS, exist_ok=True)
    path = os.path.join(MODELS, "%s.glb" % cid)
    size = glb.write(path, scene_extras={"sgk": "bubble-sort-mascot", "id": cid,
                                         "clips": [c for c, _ in clips.CLIP_SPECS]})

    meta = dict(ch.meta)
    meta.update({
        "file": "models/%s.glb" % cid,
        "bytes": size,
        "clips": clip_meta,
        "materials": {k: {"surface": k, "color": [round(c, 4) for c in v["color"]],
                          "metallic": v.get("metallic", 0.0),
                          "roughness": v.get("roughness", 0.5),
                          "alpha": v.get("alpha", 1.0),
                          "texture": v.get("texture")} for k, v in sorted(ch.mats.items())},
        "bones": skel.describe(),
        "palette_srgb": ch.palette,
        "blurb": ch.blurb,
        "build_seconds": round(time.time() - t0, 2),
    })
    return meta


def main():
    only = sys.argv[1:] or list(creatures.BUILDERS.keys())
    os.makedirs(SPECS, exist_ok=True)
    roster = {"characters": [], "clips": [{"name": n, "duration": d,
                                           "loop": n == "Idle"} for n, d in clips.CLIP_SPECS],
              "fps": FPS, "up": "+Y", "front": "+Z", "units": "metres",
              "convention": {
                  "origin": "on the ground, centred on the array slot",
                  "hop": "in place - the website translates the slot for swaps",
                  "badge": "blank cream plate + `badge` bone = number label anchor"}}

    print("%-8s %7s %7s %7s %8s %7s %7s %6s" %
          ("char", "tris", "verts", "joints", "clips", "bytes", "height", "sec"))
    for cid in only:
        meta = build_one(cid)
        roster["characters"].append(meta)
        print("%-8s %7d %7d %7d %8d %7d %7.3f %6.1f" %
              (cid, meta["triangles"], meta["vertices"], meta["joint_count"],
               len(meta["clips"]), meta["bytes"], meta["height"], meta["build_seconds"]))

    if len(only) == len(creatures.BUILDERS):
        with open(os.path.join(SPECS, "roster.json"), "w") as fh:
            json.dump(roster, fh, indent=1)
        total = sum(c["triangles"] for c in roster["characters"])
        print("\nroster.json written | %d characters | %d triangles total" %
              (len(roster["characters"]), total))


if __name__ == "__main__":
    main()
