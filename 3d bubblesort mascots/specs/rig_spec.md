# Rig specification

## The shared 14-bone core

All five characters are built on the *same* 14-bone core, with identical bone names and
identical parenting, so one animation state machine drives the whole roster. Only the
bone **positions** change, because the characters are different sizes and shapes.

```
root                         world anchor — never animated (hops are in place)
└── hips                     crouch / hop / land + squash & stretch
    ├── spine                lower body bend
    │   └── chest            breathing, compare-twist
    │       ├── neck         head base
    │       │   └── head     glances, nods, tilts
    │       │       ├── lidL     eyelid (rotating it sweeps the lid over the eye)
    │       │       ├── lidR     eyelid
    │       │       ├── eyeL     eyeball: gaze offset + squint
    │       │       └── eyeR     eyeball
    │       └── badge        the blank number plate — intentionally NOT deformed
    ├── legL                 foot plant / compression / air tuck
    ├── legR                 foot plant / compression / air tuck
    └── base                 ground-contact pad (used by the legless silhouettes)
```

**Why these bones and no more:** the animation needs exactly five things — a body that
breathes and squashes (`hips`, `spine`, `chest`), a head that glances (`neck`, `head`),
eyes that look and blink (`eyeL/R`, `lidL/R`), feet that stay planted (`legL/R`, `base`),
and a label that never warps (`badge`). Knees, elbows, fingers or a spine chain would add
keyframes and weight-painting risk without changing the read at small video sizes.

**`legL` / `legR` on legless characters.** Kiln (a pot), Ribb (a basket) and Glim (a gel
drop) have no visible legs. They still carry the leg bones — the `Hop`/`Crouch` clips use
them as generic secondary motion (Kiln's handles react to them) — and all of their ground
contact is handled by the `base` pad bone, which counter-translates so the foot ring stays
on the floor while the body squashes.

## Per-character extra bones

Extras are appended after the core, so the core indices `0–13` are stable in every file.

| model | core + extras | extra bones |
|---|---|---|
| kiln | 14 + 3 = **17** | `crown` (chimney), `handleL`, `handleR` (loop handles) |
| ribb | 14 + 3 = **17** | `lidKnot` (lid + knot + tails), `handleL`, `handleR` |
| zag | 14 + 2 = **16** | `finL`, `finR` (crystal fins) |
| glim | 14 + 5 = **19** | `core` (floating inner core), `frondF`, `frondB`, `frondL`, `frondR` |
| rumble | 14 + 6 = **20** | `ringA`, `ringB`, `ringC` (copper armour rings), `tailFlap`, `legBL`, `legBR` |

Extras are pure secondary animation: they add their own keyframes to `Hop`, `Land`,
`NoSwap` and `Success` (e.g. Rumble's rings kick outward on impact, Zag's fins flare on
success, Glim's core floats and pulses) and idle with a small offset from the body motion.
Deleting an extra bone in a DCC tool would only remove that flourish — nothing else in the
rig depends on it.

## Skinning

Weights were computed in `tools/rig.py` by sampling each vertex against the *allowed* bones
of its own part, with a radial falloff over the bone's capsule plus a mild nearest-bone
bias, normalised to 4 influences. This produces smooth blends across joints without the
smearing you get from blanket distance weighting — rigid parts (badge, eyes, lids, crystal
shards, armour rings, fin plates) are bound to a single bone so they never deform at all.

Verified per file (`tools/validate.py`, and independently with `@gltf-transform/core`):

* every vertex sums to 1.0 within 2·10⁻²,
* joint indices are all inside the skin's joint list,
* at most **4** influences are used per vertex,
* the `badge` bone's plate geometry is 100 % single-bone weighted.

## Badge bone

`badge` is a child of `chest`, sits on the plate's surface, and is **excluded from all
deformation** — no part of the body geometry is weighted to it. Its world transform is
therefore a clean, always-correct mount point for a number label. See
`specs/badge_label.md` for the anchors.

## Bone tables (rest positions, model space, metres)

Rest positions are the bones' world positions at the neutral pose, i.e. directly in model
space — useful if you want to attach props or debug the skeleton.

### `kiln` — Kiln (The Terracotta Array Item)

Height 1.356 m · width 0.867 m · depth 0.661 m · 17 joints · 7136 triangles

| bone | parent | group | rest position (x, y, z) |
|---|---|---|---|
| `root` | — | core | 0.000, 0.000, 0.000 |
| `hips` | root | core | 0.000, 0.300, 0.000 |
| `spine` | hips | core | 0.000, 0.480, 0.000 |
| `chest` | spine | core | 0.000, 0.720, 0.000 |
| `neck` | chest | core | 0.000, 0.860, 0.000 |
| `head` | neck | core | 0.000, 1.010, 0.000 |
| `lidL` | head | face | -0.090, 0.998, 0.161 |
| `lidR` | head | face | 0.090, 0.998, 0.161 |
| `eyeL` | head | face | -0.090, 0.998, 0.161 |
| `eyeR` | head | face | 0.090, 0.998, 0.161 |
| `badge` | chest | badge | 0.000, 0.520, 0.320 |
| `legL` | hips | core | -0.170, 0.050, 0.000 |
| `legR` | hips | core | 0.170, 0.050, 0.000 |
| `base` | hips | core | 0.000, 0.030, 0.000 |
| `crown` | head | extra | 0.000, 1.150, 0.000 |
| `handleL` | spine | extra | -0.290, 0.470, 0.000 |
| `handleR` | spine | extra | 0.290, 0.470, 0.000 |

### `ribb` — Ribb (The Woven Index)

Height 0.854 m · width 1.033 m · depth 0.715 m · 17 joints · 14032 triangles

| bone | parent | group | rest position (x, y, z) |
|---|---|---|---|
| `root` | — | core | 0.000, 0.000, 0.000 |
| `hips` | root | core | 0.000, 0.160, 0.000 |
| `spine` | hips | core | 0.000, 0.260, 0.000 |
| `chest` | spine | core | 0.000, 0.360, 0.000 |
| `neck` | chest | core | 0.000, 0.440, 0.000 |
| `head` | neck | core | 0.000, 0.500, 0.000 |
| `lidL` | head | face | -0.086, 0.404, 0.339 |
| `lidR` | head | face | 0.086, 0.404, 0.339 |
| `eyeL` | head | face | -0.086, 0.404, 0.339 |
| `eyeR` | head | face | 0.086, 0.404, 0.339 |
| `badge` | chest | badge | 0.000, 0.152, 0.259 |
| `legL` | hips | core | -0.205, 0.075, 0.000 |
| `legR` | hips | core | 0.205, 0.075, 0.000 |
| `base` | hips | core | 0.000, 0.100, 0.000 |
| `lidKnot` | head | extra | 0.000, 0.802, 0.000 |
| `handleL` | chest | extra | -0.296, 0.330, 0.000 |
| `handleR` | chest | extra | 0.296, 0.330, 0.000 |

### `zag` — Zag (The Mineral Constant)

Height 1.074 m · width 0.491 m · depth 0.556 m · 16 joints · 1286 triangles

| bone | parent | group | rest position (x, y, z) |
|---|---|---|---|
| `root` | — | core | 0.000, 0.000, 0.000 |
| `hips` | root | core | 0.000, 0.300, 0.000 |
| `spine` | hips | core | 0.000, 0.460, 0.000 |
| `chest` | spine | core | 0.000, 0.640, 0.000 |
| `neck` | chest | core | 0.000, 0.780, 0.000 |
| `head` | neck | core | 0.000, 0.920, 0.000 |
| `lidL` | head | face | -0.078, 0.930, 0.198 |
| `lidR` | head | face | 0.078, 0.930, 0.198 |
| `eyeL` | head | face | -0.078, 0.930, 0.198 |
| `eyeR` | head | face | 0.078, 0.930, 0.198 |
| `badge` | chest | badge | 0.000, 0.520, 0.237 |
| `legL` | hips | core | -0.108, 0.196, 0.000 |
| `legR` | hips | core | 0.108, 0.196, 0.000 |
| `base` | hips | core | 0.000, 0.030, 0.000 |
| `finL` | chest | extra | -0.092, 0.836, -0.096 |
| `finR` | chest | extra | 0.092, 0.836, -0.096 |

### `glim` — Glim (The Translucent Buffer)

Height 0.796 m · width 0.618 m · depth 0.631 m · 19 joints · 6024 triangles

| bone | parent | group | rest position (x, y, z) |
|---|---|---|---|
| `root` | — | core | 0.000, 0.000, 0.000 |
| `hips` | root | core | 0.000, 0.200, 0.000 |
| `spine` | hips | core | 0.000, 0.320, 0.000 |
| `chest` | spine | core | 0.000, 0.440, 0.000 |
| `neck` | chest | core | 0.000, 0.560, 0.000 |
| `head` | neck | core | 0.000, 0.660, 0.000 |
| `lidL` | head | face | -0.100, 0.455, 0.259 |
| `lidR` | head | face | 0.100, 0.455, 0.259 |
| `eyeL` | head | face | -0.100, 0.455, 0.259 |
| `eyeR` | head | face | 0.100, 0.455, 0.259 |
| `badge` | chest | badge | 0.000, 0.234, 0.300 |
| `legL` | hips | core | -0.120, 0.060, 0.000 |
| `legR` | hips | core | 0.120, 0.060, 0.000 |
| `base` | hips | core | 0.000, 0.050, 0.000 |
| `core` | chest | extra | 0.000, 0.392, 0.000 |
| `frondF` | hips | extra | 0.000, 0.232, 0.248 |
| `frondB` | hips | extra | 0.000, 0.232, -0.248 |
| `frondL` | hips | extra | -0.248, 0.232, 0.000 |
| `frondR` | hips | extra | 0.248, 0.232, 0.000 |

### `rumble` — Rumble (The Sorted Segments)

Height 0.655 m · width 0.836 m · depth 0.716 m · 20 joints · 12676 triangles

| bone | parent | group | rest position (x, y, z) |
|---|---|---|---|
| `root` | — | core | 0.000, 0.000, 0.000 |
| `hips` | root | core | 0.000, 0.160, 0.000 |
| `spine` | hips | core | 0.000, 0.280, 0.000 |
| `chest` | spine | core | 0.000, 0.420, 0.000 |
| `neck` | chest | core | 0.000, 0.540, 0.000 |
| `head` | neck | core | 0.000, 0.600, 0.000 |
| `lidL` | head | face | -0.104, 0.440, 0.315 |
| `lidR` | head | face | 0.104, 0.440, 0.315 |
| `eyeL` | head | face | -0.104, 0.440, 0.315 |
| `eyeR` | head | face | 0.104, 0.440, 0.315 |
| `badge` | chest | badge | 0.000, 0.220, 0.309 |
| `legL` | hips | core | -0.245, 0.135, 0.000 |
| `legR` | hips | core | 0.245, 0.135, 0.000 |
| `base` | hips | core | 0.000, 0.060, 0.000 |
| `ringA` | chest | extra | 0.000, 0.352, -0.170 |
| `ringB` | chest | extra | 0.000, 0.352, 0.010 |
| `ringC` | chest | extra | 0.000, 0.352, 0.180 |
| `tailFlap` | hips | extra | 0.000, 0.212, -0.300 |
| `legBL` | hips | extra | -0.245, 0.088, -0.185 |
| `legBR` | hips | extra | 0.245, 0.088, -0.185 |
