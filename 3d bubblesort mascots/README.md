# Bubble-Sort Squad — five original creature mascots

Five independently designed, rigged, web-ready creature mascots for a computer-science
animation about **bubble sort**. Each character is one array item: they stand on array
slots, look at the neighbour they are compared with, hop past each other to swap, and
celebrate when the array comes out sorted.

Everything in this folder was generated from scratch by the scripts in `tools/`
(no third-party models, textures or character art). The characters are original
designs: their forms are adapted from *non-character* objects (a kiln pot, a woven
basket, a mineral shard, a gel droplet, a soft mechanical loaf) and they share no
names, silhouettes, markings, accessories or colour arrangements with any existing
franchise or asset pack.

---

## 1 · The roster

| id | name | construction | silhouette | surface | height |
|---|---|---|---|---|---|
| `kiln` | **Kiln** · The Terracotta Array Item | glazed kiln-pot, chimney crown, two loop handles | tall + narrow, stacked | ceramic glaze | 1.36 m |
| `ribb` | **Ribb** · The Woven Index | woven basket, two big loop handles, tipping lid | squat + wide | woven fibre | 0.85 m |
| `zag` | **Zag** · The Mineral Constant | faceted crystal body, peg legs, crystal fins, chisel visor | angular, faceted | mineral, flat-shaded | 1.07 m |
| `glim` | **Glim** · The Translucent Buffer | gel droplet, floating glowing core, six fronds | teardrop | translucent | 0.80 m |
| `rumble` | **Rumble** · The Sorted Segments | soft loaf under three copper armour rings, rubber-shod legs | very low + wide | aluminium, copper | 0.66 m |

**A roster sheet** (`shots/roster_sheet.png`) shows all five together with the numbers
drawn the way the website will draw them: as live text on the blank badge, never baked
into the model.

**How they read as one family without being recolours** — every character shares:

* the same eye construction (dark lens + cream catchlight + a chunky lid),
* the same cream blank badge plate with a brushed rim, in the same relative position,
* one saturated pop colour (celadon/mint) used as a single accent,
* the same rest pose, ground contact and lighting intent,
* the same 14-bone core skeleton and the same eight clip names.

Everything else — topology, proportions, face arrangement, appendages, material and
shading model — is deliberately different per character, and each pop colour is paired
with a completely different value structure (a mid-brown pot vs. a pale basket vs. a
dark blue-grey crystal vs. a transparent cyan gel vs. a warm metal loaf). The
**silhouette test** (`shots/silhouettes.png`) is the proof: five unmistakably different
outlines in solid black.

---

## 2 · Deliverables

```
3d bubblesort mascots/
├── models/                     FIVE SEPARATE WEB-READY GLB FILES
│   ├── kiln.glb  ribb.glb  zag.glb  glim.glb  rumble.glb
├── specs/
│   ├── roster.json             machine-readable roster: exact sizes, materials,
│   │                           per-clip durations/keyframe counts, bone tables
│   ├── animation_clips.md      every clip, what it does and how to drive it
│   ├── rig_spec.md             the 14-bone core + per-character extras, in detail
│   ├── badge_label.md          where to put the number, in model space and screen space
│   └── validation_report.json  the pass/fail report produced by tools/validate.py
├── index.html                  LIVE VIEWER — drives the GLBs in a browser
├── vendor/                     three.js r128 + GLTFLoader (MIT, vendored so the
│                               viewer works with no internet connection)
├── shots/
│   ├── roster_sheet.png        all five together, on array slots
│   ├── views_kiln.png …        front / side / back, orthographic, one per character
│   ├── silhouettes.png         solid-black silhouette test (front + three-quarter)
│   ├── animation_strip.png     idle → glance → hop apex → landing → success, per character
│   ├── bubblesort_rehearsal.webp / .gif   a real bubble-sort pass, performed live
│   └── rehearsal_keysheet.png  the same pass as a contact sheet
├── tools/                      the source pipeline (rebuilds everything, byte-for-byte)
│   ├── mlib.py                 geometry primitives (lathe, tube, superellipsoid, plates…)
│   ├── rig.py                  skeleton, automatic skinning, clip baking
│   ├── clips.py                the shared eight-clip animation vocabulary
│   ├── creatures.py            THE FIVE CHARACTER DESIGNS
│   ├── textures.py             procedural detail maps
│   ├── glb.py                  dependency-free glTF 2.0 / GLB writer
│   ├── build_models.py         builds models/*.glb + specs/roster.json
│   ├── validate.py             independent verification of the exported GLBs
│   ├── render.py               offline software renderer used for every PNG
│   ├── make_sheets.py          roster / views / silhouettes / animation strip
│   └── make_gif.py             the animated bubble-sort rehearsal
└── blender/                    Blender source — see "Blender source files" below
```

### Triangles and file sizes (measured, not estimated)

| model | triangles | vertices | joints | clips | GLB |
|---|---|---|---|---|---|
| kiln | 7,136 | 4,192 | 17 | 8 | 413 KB |
| ribb | 14,032 | 7,967 | 17 | 8 | 715 KB |
| zag | 1,286 | 2,534 | 16 | 8 | 269 KB |
| glim | 6,024 | 3,436 | 19 | 8 | 366 KB |
| rumble | 12,676 | 7,018 | 20 | 8 | 624 KB |

Every model is comfortably under the 15,000-triangle budget (worst case 14,032).
`tools/validate.py` re-reads each GLB from disk and checks 19 properties per model —
budget, skin weights, joint ranges, ground origin, +Z facing, clip presence, keyframe
monotonicity, in-place hop (the feet never sink through the floor), a seamless `Idle`
loop and a real skinning deformation test. **All five pass**; see
`specs/validation_report.json`.

---

## 3 · Conventions every model follows

| convention | value |
|---|---|
| Up axis | **+Y** |
| Front | **+Z** (the eyes and the badge face +Z) |
| Origin | on the ground, centred on the array slot (`min y = 0.000`) |
| Units | metres; 1 slot spacing ≈ 1.10 m of floor |
| Scale | one shared scale — Kiln is 1.36 m, Rumble is 0.66 m, so the family varies in size *by design* while sharing a common ground plane |
| Skinning | 4 influences max, weights normalised to 1.0 |
| Rig | 14-bone core + 0–6 extras, identical core bone names in every file |
| Clips | the same eight names and durations in every file |
| Textures | 256² tileable PNG detail maps, embedded in the GLB (1–3 per model) |
| Materials | PBR metallic-roughness, no glTF extensions, no external images |

---

## 4 · Number display

Each character has a **blank plate** on the front (cream face + brushed rim) and a
dedicated **`badge` bone** that is *not* deformed by body motion, so a label placed on
it never warps or wobbles. A second option is a screen-space DOM label — both are
documented in `specs/badge_label.md`, including the exact model-space anchor of the
badge on each character and a ready-to-paste Three.js snippet.

No numbers, words, captions, logos or symbols are baked into any model.

---

## 5 · Using the models

### See them first

```bash
cd "3d bubblesort mascots"
python3 -m http.server 8137
# open http://localhost:8137/
```

`index.html` is a self-contained viewer: it loads all five GLBs, plays the clips through a
real bubble sort (compare → glance, swap → hop + slot tween + land, no-swap, success),
draws the array values as **live text projected onto each `badge` bone** exactly as
described in `specs/badge_label.md`, and lets you orbit, zoom, single-step the algorithm,
resize the array, and change speed. It uses the vendored three.js r128 in `vendor/`, so it
works offline.

### In your own project

Any glTF 2.0 runtime works. Nothing outside the `.glb` is required.

```js
// Three.js r128 (matches the rest of this repository's stack)
const gltf = await new THREE.GLTFLoader().loadAsync('models/kiln.glb');
scene.add(gltf.scene);
const mixer = new THREE.AnimationMixer(gltf.scene);
const actions = {};
for (const clip of gltf.animations) {
  actions[clip.name] = mixer.clipAction(clip);
  actions[clip.name].clampWhenFinished = (clip.name !== 'Idle');
}

// one array slot, five characters, one state machine
actions.Idle.play();
function compare(a, b) {                       // neighbours look at each other
  const winner = (a.value > b.value) ? a : b;
  a.actions.GlanceR.reset().play();            // a is left of b
  b.actions.GlanceL.reset().play();
  return a.value > b.value;
}
function swap(a, b) {                          // hop in place, translated by YOU
  a.actions.Hop.reset().play(); b.actions.Hop.reset().play();
  tween(a.slotX, b.slotX, 0.62);               // the model never walks off-slot
}
function celebrate(c) { c.actions.Success.reset().play(); }
```

**Root motion:** all clips are *in place* — the hips rise and squash but the root bone
never translates horizontally. The website owns all left/right travel, so swapping two
characters is a tween of their slot x positions while both play `Hop` → `Land`.

---

## 6 · What was built, and what is a spec

To be explicit, because a claim like "rigged and animation-ready" has to be true:

* **Verified in the files:** each GLB contains a skinned mesh with `JOINTS_0`/`WEIGHTS_0`
  (≤4 influences), an `inverseBindMatrices` accessor, a joint hierarchy, eight animation
  clips with named channels, and embedded textures. The skeleton is exercised by
  re-implementing skinning straight from the file bytes and confirming that `Hop` lifts
  the body, that the feet stay on the floor, and that `Idle` returns exactly to its
  starting pose (`tools/validate.py`). The exported files also parse cleanly with the
  independent `@gltf-transform/core` library.
* **Rendered evidence:** every PNG in `shots/` is rendered from the *skinned* geometry
  through the same pose functions that were baked into the clips — not from a separate
  mock-up.
* **Blender source:** see `blender/README.md`. This environment has no Blender installed
  and no access to the Blender download servers, so no `.blend` is shipped. Instead the
  folder contains the exact recipe to produce native Blender files (a complete
  `import_and_bake_blender.py` script for Blender 3.6+/4.x, written against the glTF
  importer, plus the `use_inverse_kinematics`/action-naming steps) — it is a spec, and
  is labelled as one.

---

## 7 · Research notes — what the asset pages changed in the plan

The brief listed five public asset pages as **context only**. They were checked, and
they shaped the technical decisions below. No asset from any of them was downloaded,
traced, recoloured or used as an image-to-3D source, and no character design was derived
from them.

| Source | Verified finding | Effect on this build |
|---|---|---|
| Quaternius *Cute Animated Monsters* | CC0, ~21 animated monsters, Blender/FBX/OBJ/glTF | Confirmed CC0 packs ship **many clips per model**; so this build bakes 8 clips into each GLB rather than shipping a rig and expecting the user to key clips. |
| Quaternius *Ultimate Monsters* | CC0, 50 models, attack/death/run/walk sets | Packs are built from **one base body recoloured**; this brief forbids that, so all five silhouettes, topologies and material models here are distinct. |
| Quaternius *Ultimate Animated Animals* | CC0, 12+ clips each including jumps | Jump/hop clips are conventionally **in place with no root translation** — adopted directly: that is exactly what a swap needs. |
| Kenney *Blocky Characters* | CC0, 18 characters / **27 animations**, separate glTF models, editable UV maps | Two takeaways: (a) ship **separate GLB per character** (not one atlas of five), and (b) keep UVs intentionally editable — hence every material here is a base colour × one tileable detail map, so recolouring is a one-line change. |
| Sketchfab *Cute Monster* | one model, **CC BY 4.0 (attribution required)** | Avoided entirely. Everything in this folder is generated by the scripts here, so the deliverable carries **no attribution obligations**. |

Licence summary for *this* folder: all five characters, all textures and all code were
created for this task and are original work; nothing third-party is redistributed.

---

## 8 · Rebuilding

```bash
cd "3d bubblesort mascots/tools"
python3 build_models.py        # -> ../models/*.glb + ../specs/roster.json   (~5 s)
python3 validate.py            # -> ../specs/validation_report.json           (~1 s)

python3 make_sheets.py         # roster + 5 view sheets + silhouettes + animation strip
python3 make_sheets.py views   # a single sheet
python3 make_sheets.py q kiln front   # one fast preview panel while iterating

python3 make_gif.py            # the animated bubble-sort rehearsal (about 15 min)
python3 make_gif.py sheet      # just the contact sheet (about 20 s)
```

Dependencies: `numpy` and `Pillow` only (`pip install numpy pillow`). Everything else —
glTF writing, skinning, rendering — is implemented in this folder.
