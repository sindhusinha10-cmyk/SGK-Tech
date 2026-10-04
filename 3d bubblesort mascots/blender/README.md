# Blender source files — shipped, and built here

This folder contains **real, working Blender source**. The five `.blend` files in
`source/` were written by Blender 4.2.23 LTS itself, from the shipped GLBs, on this
machine — they are not a recipe, and nothing here is a placeholder.

```
blender/
├── source/
│   ├── kiln.blend  ribb.blend  zag.blend  glim.blend  rumble.blend
│   └── bubblesort_squad_roster.blend      all five on 1.10 m array slots
├── make_blend.py                 builds source/*.blend from models/*.glb
├── render_blender_shots.py       Cycles renders of the .blend files -> ../shots/
└── headless_bpy_shim.py          only needed to run Blender as a pip module in a
                                  container with no X server (see "Running this here")
```

## What is inside each `.blend`

| | |
|---|---|
| Skinned mesh | one mesh object, parented to the armature, an `ARMATURE` modifier, vertex groups named after the bones, materials and the embedded 256² detail textures resolved into Blender image datablocks |
| Armature | `<id>_armature`, the full 14-bone core plus that character's extras |
| Animation | all eight clips as **actions** (fake user set, so they survive the save) **and** one NLA track per clip; every track is muted except `Idle`, so the file opens on a clean idle pose |
| Scene | metric units, scale 1.0, **30 fps**, frame range 1–121 (the 4 s Idle loop) |
| Lighting | `KEY` / `FILL` / `RIM` area lights aimed at the character, plus a matte `GROUND` plane — the same three-point intent as the reference sheets |
| Camera | a framed `CAM` object, ready to render |
| Custom properties | on the armature: `sgk_id`, `sgk_up`, `sgk_front`, `sgk_origin`, `sgk_units`, `sgk_clip_order`, `sgk_badge_bone`, `sgk_slot_pitch`, `sgk_root_motion` |
| Text datablock | a `README` block inside the file carrying the conventions below |

### Axis note (important when editing)

glTF is Y-up and the characters face **+Z**. Blender is Z-up, and its glTF importer maps
glTF `(x, y, z)` → Blender `(x, −z, y)`. So inside these `.blend` files each character
stands on **Z = 0** and **faces −Y**, which is exactly Blender's front view. Re-export
with **`+Y Up` on** (the default) and the round trip is lossless — do not rotate the
objects by hand.

## Per-character contents

| character | bones | extras | triangles | clips | `source/<id>.blend` |
|---|---|---|---|---|---|
| `kiln` | 17 | `crown`, `handleL`, `handleR` | 7,136 | 8 | 387 KB |
| `ribb` | 17 | `lidKnot`, `handleL`, `handleR` | 14,032 | 8 | 555 KB |
| `zag` | 16 | `finL`, `finR` | 1,286 | 8 | 247 KB |
| `glim` | 19 | `core`, `frondF`, `frondB`, `frondL`, `frondR` | 6,024 | 8 | 353 KB |
| `rumble` | 20 | `ringA`, `ringB`, `ringC`, `tailFlap`, `legBL`, `legBR` | 12,676 | 8 | 510 KB |

`bubblesort_squad_roster.blend` (1.5 MB) holds all five on their slots: the same
`1.10 m` pitch `index.html` and the sheets use, each with a thin `slot_N` pad, one
wide camera, and one shared light rig.

## The eight clips

The clip list below is read back **out of the `.blend` files** and is identical for all
five characters — the same names, the same durations, the same timing:

| clip | seconds | frames @ 30 fps | plays |
|---|---|---|---|
| `Idle` | 4.00 | 0–120 | breathing, blinks, subtle sway — loops seamlessly |
| `GlanceL` | 0.90 | 0–27 | left neighbour comparison, look left |
| `GlanceR` | 0.90 | 0–27 | right neighbour comparison, look right |
| `Crouch` | 0.50 | 0–15 | anticipation squash before a hop |
| `Hop` | 0.72 | 0–21 | the hop itself, **in place** |
| `Land` | 0.50 | 0–15 | impact squash and rebound |
| `NoSwap` | 0.95 | 0–28 | "not bigger than me" shake-off |
| `Success` | 1.25 | 0–37 | a short double pop when the array is sorted |

Every clip is **in place**: the `root` bone never translates horizontally, because the
website owns all left/right travel and tweens the slot position during a swap. Feet
never pass through Z = 0.

## Verification

`make_blend.py` also writes `../specs/blender_verification.json`. That file is a
*second, independent* check of the GLBs: the numbers in it are read back by Blender's
own glTF importer, not by the pipeline that authored the files. It confirms, per
character, the triangle count, bone list, every core bone, all eight clip names and
durations, the material and image set, the skinning influences, the ground contact, and
the badge bone anchor. Spot-checked result:

* triangle counts and the badge anchor `[0.0, 0.52, 0.3198]` match
  `../specs/validation_report.json` exactly;
* `max_influences = 4` for every mesh;
* every mesh carries exactly one `ARMATURE` modifier;
* `ground_z = 0.0` for every character.

## Rendered from the `.blend` files

`render_blender_shots.py` renders the native Blender scenes with **Cycles on CPU** and
writes:

| file | what it shows |
|---|---|
| `../shots/blender_roster.png` | all five on their slots, with the array value drawn as live screen-space text projected onto each `badge` bone |
| `../shots/blender_views_<id>.png` | orthographic front / side / back from `source/<id>.blend` |
| `../shots/blender_poses_<id>.png` | idle · glance · hop apex · land · success, posed by the actual actions |

These are a genuinely independent second opinion on the deliverable: the pictures in
`../shots/` without the `blender_` prefix come from the pipeline's own software
renderer, and these come from Cycles, reading the same skeleton and the same clips.
Nothing numeric is baked into a model — the roster numbers are composited onto the
render in screen space, exactly the way the runtime label works.

## Rebuilding

```bash
cd "3d bubblesort mascots"

# with Blender installed normally:
blender --background --python blender/make_blend.py            -- models blender/source
blender --background --python blender/render_blender_shots.py  -- models blender/source shots all

# or as the pip module (see below)
python3 blender/make_blend.py
python3 blender/render_blender_shots.py -- models blender/source shots all
```

Roughly 2 s to write all six `.blend` files and about 5 minutes for the ten Cycles
sheets on CPU.

## Running this here (`headless_bpy_shim.py`)

This container has no X server and no Mesa, and the Debian mirrors are unreachable, but
Blender's **official upstream wheel is on PyPI**:

```bash
pip install bpy==4.2.23          # exact match for this container's Python 3.11
```

`bpy`'s `__init__.so` links against nine X11 / input / GL sonames that a slim container
does not ship (`libXrender.so.1`, `libXxf86vm.so.1`, `libXfixes.so.3`, `libXi.so.6`,
`libxkbcommon.so.0`, `libSM.so.6`, `libICE.so.6`, `libGL.so.1`, `libXt.so.6`).
`headless_bpy_shim.py` generates minimal stand-in shared objects for them and a small
`LD_PRELOAD` shim for the ~60 X11 symbols the loader still demands:

```bash
python3 blender/headless_bpy_shim.py
export LD_LIBRARY_PATH=/tmp/bpy-shim/lib:$LD_LIBRARY_PATH
export LD_PRELOAD=/tmp/bpy-shim/lib/libbpy_shim.so
python3 blender/make_blend.py
```

Be clear about what that is: a **loader-only workaround**. Every stubbed symbol sits
inside an X11/GL code path that Blender never enters in `--background` mode — no
window, no GL context, no display. Cycles runs on **CPU**. Blender itself is never
patched or re-linked, and none of the shipped models, textures, renders or `.blend`
files depend on the shim. On a normal desktop with Blender installed, delete this
paragraph's advice and use `blender --background` directly — the scripts are the same.

## If you edit a `.blend` and re-export

* **Format** `glTF Binary (.glb)`, **`+Y Up` on**, `Skinning` on, `Apply Modifiers` off.
* Keep the material names in the `<id>_<surface>` form so runtime lookups keep working.
* **Keep the `badge` bone unweighted.** It is a mount point for the runtime number
  label (`../specs/badge_label.md`), deliberately excluded from skinning so a value
  change can never deform geometry.
* **Keep blinks on `lidL`/`lidR`** and gaze on `eyeL`/`eyeR` — they are bones, not shape
  keys, and `../specs/animation_clips.md` depends on that.
* Extras are optional. Deleting `crown`/`handleL`/`handleR` (kiln), `lidKnot` (ribb),
  `finL`/`finR` (zag), `core`/`frond*` (glim) or `ring*`/`tailFlap`/`legBL`/`legBR`
  (rumble) removes only that flourish; the core 14 bones and all eight clips keep working.
* Keep the clip names exactly as listed above — the website's state machine indexes
  them by name.
