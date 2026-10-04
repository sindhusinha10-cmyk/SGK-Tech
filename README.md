# SGK-Tech

Working repository. Two projects live here.

## `3d bubblesort mascots/` — rigged mascot roster (new)

Five original, rigged, web-ready creature mascots for a computer-science animation about
**bubble sort**. Each mascot is one array item: they stand on array slots, glance at the
neighbour they are compared with, hop past each other to swap, and celebrate when the
array is sorted.

* **`models/*.glb`** — five separate GLB files, 8 animation clips each, embedded textures
* **`index.html`** — a live viewer that runs a real bubble sort with the models
  (`python3 -m http.server 8137` inside that folder, then open `/`)
* **`shots/`** — roster sheet, per-character front/side/back views, solid-black silhouette
  test, animation strip, and an animated rehearsal of a sort pass
* **`specs/`** — roster data, clip documentation, rig documentation, badge-label
  placement, and a validation report
* **`tools/`** — the whole procedural pipeline (geometry, rigging, skinning, glTF export,
  offline renderer, verification) — no third-party assets
* **`blender/`** — a one-command script that turns the GLBs into native Blender sources

Start with [`3d bubblesort mascots/README.md`](3d%20bubblesort%20mascots/README.md).

Verified state: 5/5 models pass `tools/validate.py` (19 checks each — skin weights, joint
ranges, ground origin, +Z facing, all eight clips present, in-place hop, seamless idle
loop, and a real skinning deformation test), totalling 41,154 triangles with a worst-case
model at 14,032 / 15,000.

## `3d character for anshitamakeover/` — Maison Lumière concierge selector

An earlier, unrelated project in this repository: a single-file Three.js (r128) 3D
concierge selector for a bridal & makeup studio, with five procedurally generated
characters and two rigged glTF birds. See its own `README.md` and
`MEERA_CHERRY_HANDOFF.md`. It is untouched by the mascot work; the only thing shared
between them is the vendored three.js r128 build, which the mascot viewer also uses.
