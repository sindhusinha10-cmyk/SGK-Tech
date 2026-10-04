"""
glb — a minimal, strict glTF 2.0 / GLB writer.

Only what this project needs: one skinned mesh per file, a joint hierarchy, PBR
metallic-roughness materials, embedded PNG textures and LINEAR-sampled animation
clips. No glTF extensions are emitted, so the files load in Three.js r128,
<model-viewer>, Babylon, Unity and Blender's glTF importer without surprises.
"""

import json
import struct

COMP_FLOAT = 5126
COMP_USHORT = 5123
COMP_UINT = 5125
COMP_UBYTE = 5121

T_SCALAR = "SCALAR"
T_VEC2 = "VEC2"
T_VEC3 = "VEC3"
T_VEC4 = "VEC4"
T_MAT4 = "MAT4"

COMP_SIZE = {COMP_FLOAT: 4, COMP_USHORT: 2, COMP_UINT: 4, COMP_UBYTE: 1}
N_COMP = {T_SCALAR: 1, T_VEC2: 2, T_VEC3: 3, T_VEC4: 4, T_MAT4: 16}
TARGET_ARRAY = 34962
TARGET_INDEX = 34963


class GLB(object):
    def __init__(self):
        self.bin = bytearray()
        self.buffer_views = []
        self.accessors = []
        self.meshes = []
        self.materials = []
        self.images = []
        self.textures = []
        self.nodes = []
        self.skins = []
        self.animations = []
        self.scene_nodes = []
        self.asset_generator = "SGK-Tech Bubble-Sort Mascots pipeline"

    # ------------------------------------------------------------------ buffer
    def _align(self, n=4):
        while len(self.bin) % n:
            self.bin.append(0)

    def add_view(self, data, target=None, name=None):
        self._align(4)
        off = len(self.bin)
        self.bin.extend(data)
        bv = {"buffer": 0, "byteOffset": off, "byteLength": len(data)}
        if target is not None:
            bv["target"] = target
        if name:
            bv["name"] = name
        self.buffer_views.append(bv)
        return len(self.buffer_views) - 1

    def add_accessor(self, view, comp_type, count, type_, minmax=True, arr=None, name=None):
        acc = {"bufferView": view, "componentType": comp_type, "count": int(count), "type": type_}
        if minmax and arr is not None:
            a = arr
            if type_ == T_SCALAR:
                acc["min"] = [float(a.min())]
                acc["max"] = [float(a.max())]
            elif type_ in (T_VEC2, T_VEC3, T_VEC4, T_MAT4):
                acc["min"] = [float(x) for x in a.min(axis=0)]
                acc["max"] = [float(x) for x in a.max(axis=0)]
        if name:
            acc["name"] = name
        self.accessors.append(acc)
        return len(self.accessors) - 1

    # --------------------------------------------------------------- resources
    def add_image_png(self, png_bytes, name):
        view = self.add_view(png_bytes, name=name + " image")
        self.images.append({"bufferView": view, "mimeType": "image/png", "name": name})
        return len(self.images) - 1

    def add_texture(self, image, sampler=None):
        t = {"source": image}
        if sampler is not None:
            t["sampler"] = sampler
        self.textures.append(t)
        return len(self.textures) - 1

    def add_material(self, name, base_color=(1, 1, 1, 1), metallic=0.0, roughness=0.5,
                     emissive=(0, 0, 0), base_color_texture=None, alpha_mode="OPAQUE",
                     double_sided=False, extras=None):
        pbr = {
            "baseColorFactor": [float(c) for c in base_color],
            "metallicFactor": float(metallic),
            "roughnessFactor": float(roughness),
        }
        if base_color_texture is not None:
            pbr["baseColorTexture"] = {"index": int(base_color_texture), "texCoord": 0}
        mat = {"name": name, "pbrMetallicRoughness": pbr, "doubleSided": bool(double_sided)}
        if any(emissive):
            mat["emissiveFactor"] = [float(c) for c in emissive]
        if alpha_mode != "OPAQUE":
            mat["alphaMode"] = alpha_mode
        if extras:
            mat["extras"] = extras
        self.materials.append(mat)
        return len(self.materials) - 1

    # ------------------------------------------------------------------- nodes
    def add_node(self, name, translation=(0, 0, 0), rotation=(0, 0, 0, 1), scale=(1, 1, 1),
                 children=None, mesh=None, skin=None, extras=None):
        node = {"name": name}
        node["translation"] = [float(x) for x in translation]
        if tuple(rotation) != (0.0, 0.0, 0.0, 1.0):
            node["rotation"] = [float(x) for x in rotation]
        if tuple(scale) != (1.0, 1.0, 1.0):
            node["scale"] = [float(x) for x in scale]
        if children:
            node["children"] = [int(c) for c in children]
        if mesh is not None:
            node["mesh"] = int(mesh)
        if skin is not None:
            node["skin"] = int(skin)
        if extras:
            node["extras"] = extras
        self.nodes.append(node)
        return len(self.nodes) - 1

    # -------------------------------------------------------------------- mesh
    def add_skinned_mesh(self, name, positions, normals, uvs, joints, weights,
                         primitives, extras=None):
        """primitives: list of (material_index, face_index_array)."""
        pos_view = self.add_view(positions.tobytes(), target=TARGET_ARRAY, name=name + " POSITION")
        a_pos = self.add_accessor(pos_view, COMP_FLOAT, len(positions), T_VEC3, arr=positions)
        nrm_view = self.add_view(normals.tobytes(), target=TARGET_ARRAY, name=name + " NORMAL")
        a_nrm = self.add_accessor(nrm_view, COMP_FLOAT, len(normals), T_VEC3, arr=normals)
        uv_view = self.add_view(uvs.tobytes(), target=TARGET_ARRAY, name=name + " TEXCOORD_0")
        a_uv = self.add_accessor(uv_view, COMP_FLOAT, len(uvs), T_VEC2, arr=uvs)
        j_view = self.add_view(joints.tobytes(), target=TARGET_ARRAY, name=name + " JOINTS_0")
        a_j = self.add_accessor(j_view, COMP_UBYTE, len(joints), T_VEC4, minmax=False)
        w_view = self.add_view(weights.tobytes(), target=TARGET_ARRAY, name=name + " WEIGHTS_0")
        a_w = self.add_accessor(w_view, COMP_FLOAT, len(weights), T_VEC4, minmax=False)

        attrs = {"POSITION": a_pos, "NORMAL": a_nrm, "TEXCOORD_0": a_uv, "JOINTS_0": a_j, "WEIGHTS_0": a_w}
        prims = []
        for mi, faces in primitives:
            idx = faces.astype("uint32").ravel()
            iv = self.add_view(idx.tobytes(), target=TARGET_INDEX, name=name + " indices")
            a_i = self.add_accessor(iv, COMP_UINT, len(idx), T_SCALAR, arr=idx)
            prims.append({"attributes": attrs, "indices": a_i, "material": int(mi), "mode": 4})
        mesh = {"name": name, "primitives": prims}
        if extras:
            mesh["extras"] = extras
        self.meshes.append(mesh)
        return len(self.meshes) - 1

    def add_skin(self, joint_nodes, ibm_matrices, name="Skeleton"):
        import numpy as np
        arr = np.asarray(ibm_matrices, dtype="float32")          # (J,4,4) row-major
        # glTF wants column-major
        col = np.transpose(arr, (0, 2, 1)).reshape(len(arr), 16)
        view = self.add_view(col.tobytes(), name=name + " IBM")
        acc = self.add_accessor(view, COMP_FLOAT, len(arr), T_MAT4, minmax=False)
        self.skins.append({"name": name, "joints": [int(j) for j in joint_nodes],
                           "inverseBindMatrices": acc})
        return len(self.skins) - 1

    # -------------------------------------------------------------- animations
    def add_animation(self, name, tracks, extras=None):
        """tracks: dict node_index -> {'translation': (times, values), 'rotation': ..., 'scale': ...}"""
        import numpy as np
        samplers, channels = [], []
        for node_idx in sorted(tracks.keys()):
            for path, (times, values) in sorted(tracks[node_idx].items()):
                tv = np.asarray(times, dtype="float32")
                vv = np.asarray(values, dtype="float32")
                t_view = self.add_view(tv.tobytes(), name="%s %s time" % (name, path))
                a_t = self.add_accessor(t_view, COMP_FLOAT, len(tv), T_SCALAR, arr=tv)
                v_type = {1: T_SCALAR, 3: T_VEC3, 4: T_VEC4}[vv.shape[1]]
                v_view = self.add_view(vv.tobytes(), name="%s %s value" % (name, path))
                a_v = self.add_accessor(v_view, COMP_FLOAT, len(vv), v_type, minmax=False)
                samplers.append({"input": a_t, "output": a_v, "interpolation": "LINEAR"})
                channels.append({"sampler": len(samplers) - 1,
                                 "target": {"node": int(node_idx), "path": path}})
        anim = {"name": name, "samplers": samplers, "channels": channels}
        if extras:
            anim["extras"] = extras
        self.animations.append(anim)
        return len(self.animations) - 1

    # -------------------------------------------------------------------- write
    def write(self, path, scene_extras=None):
        gltf = {
            "asset": {"version": "2.0", "generator": self.asset_generator},
            "scene": 0,
            "scenes": [{"name": "Scene", "nodes": [int(n) for n in self.scene_nodes]}],
            "nodes": self.nodes,
            "meshes": self.meshes,
            "materials": self.materials,
            "accessors": self.accessors,
            "bufferViews": self.buffer_views,
            "buffers": [{"byteLength": len(self.bin)}],
        }
        if self.skins:
            gltf["skins"] = self.skins
        if self.animations:
            gltf["animations"] = self.animations
        if self.images:
            gltf["images"] = self.images
        if self.textures:
            gltf["textures"] = self.textures
            gltf["samplers"] = [{"magFilter": 9729, "minFilter": 9987, "wrapS": 10497, "wrapT": 10497}]
            for t in self.textures:
                t["sampler"] = 0
        if scene_extras:
            gltf["scenes"][0]["extras"] = scene_extras

        js = json.dumps(gltf, separators=(",", ":"), allow_nan=False).encode("utf-8")
        while len(js) % 4:
            js += b" "
        bin_data = bytes(self.bin)
        while len(bin_data) % 4:
            bin_data += b"\x00"

        total = 12 + 8 + len(js) + 8 + len(bin_data)
        with open(path, "wb") as fh:
            fh.write(b"glTF")
            fh.write(struct.pack("<II", 2, total))
            fh.write(struct.pack("<I", len(js)))
            fh.write(b"JSON")
            fh.write(js)
            fh.write(struct.pack("<I", len(bin_data)))
            fh.write(b"BIN\x00")
            fh.write(bin_data)
        return total
