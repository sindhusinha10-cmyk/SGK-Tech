# Tech Critters — concept pass v2

Five **new creature concepts** for the bubble-sort animation, drawn as 3D renders so
you can judge the shapes rather than imagine them.

This folder is a **concept review**, separate from the shipped v1 roster in the parent
directory. Nothing here overwrites v1 — `../models/*.glb` are untouched. If you pick
these, they get rigged, baked and exported by the same pipeline v1 already uses.

```
concepts/
├── critters.py            the five designs (build + proportions + bones + clip tuning)
├── sheets.py              renders the sheets below
└── shots/
    ├── concept_roster.png        all five, on array slots, with live number labels
    ├── concept_views_<id>.png    front / side / back, orthographic, per creature
    ├── concept_silhouettes.png   solid-black silhouette test
    └── concept_rigproof.png      the real 8-clip vocabulary, posed through the rig
```

---

## 1 · What changed, and why

The brief asked for "Pokémon-inspired". Two things follow from that, and they are
different:

* **The genre's design language** — bold readable silhouettes, one clear idea per
  creature, big expressive eyes, a set that feels collectible. That is a style, it is
  not anybody's property, and it is a good call for this project.
* **Specific franchise characters** — a yellow mouse with red cheeks, a fire lizard,
  a ball with a leaf. That is Nintendo / The Pokémon Company IP and is off the table.

So: **same design language, fully original characters.** Nothing below is traced,
recoloured or derived from any existing creature, and there are no logos or
franchise symbols anywhere.

### The real change: these are creatures, not objects

v1 is five **objects** — a terracotta pot, a woven basket, a mineral shard, a gel
droplet, a metal loaf. Charming, but read together they feel like household mascots.

v2 is five **creatures**, each a genuinely different *kind* of animal-machine, each
carrying one computing idea:

| id | name | body plan | computing idea | height |
|---|---|---|---|---|
| `volt` | **Volt** — The Charge Buddy | **biped** — squat amber can, cream rubber feet, filament tuft | stored charge | 0.97 m |
| `chip` | **Chip** — The Wafer Index | **quadruped** — low indigo wafer on four gold pins, lit die on top | the data item itself | 0.53 m |
| `bug` | **Bug** — The Debug Beetle | **hexapod** — sage carapace, circuit traces, antennae, six copper legs | the bug you debug | 0.68 m |
| `wisp` | **Wisp** — The Packet Spirit | **floating** — faceted lilac lantern around a bright core, swept-back tail | a packet in flight | 0.83 m |
| `spool` | **Spool** — The Iteration Coil | **segmented** — cream core wrapped in steel rings, one live celadon ring | the loop | 0.96 m |

Five body plans, not five hats on one shape. Check `concept_silhouettes.png`: a biped,
a low slab on legs, a beetle, a floating teardrop, and a stacked coil — no two are
mistakable for each other in solid black, which is the point of the test.

---

## 2 · What keeps them a family

Deliberately shared, so the set still reads as one roster:

* the **same eye construction** — dark lens + cream catchlight + a chunky lid, built
  by the same `eye_pair()` helper v1 uses;
* the **same blank cream badge plate** with a brushed rim, in the same relative place;
* **one celadon pop accent** per character, used sparingly;
* the same **rest pose, ground contact and lighting intent**;
* the same **14-bone core skeleton** and the same **eight clip names**.

Everything else — topology, proportions, face arrangement, appendages, material story —
is different per creature.

---

## 3 · They are already riggable (this is verified, not claimed)

`concept_rigproof.png` is **not** a posed still and **not** a mock-up. For each creature
it builds the real skinning weights, bakes the real clip functions, and poses the mesh
through `rig.deform()` — exactly the path the exporter uses. All five run the full
eight-clip vocabulary:

> `Idle` · `GlanceL` · `GlanceR` · `Crouch` · `Hop` · `Land` · `NoSwap` · `Success`

The sheet shows five of them: idle, glance, hop apex, land, success. Things worth
noticing in it:

* **Volt** throws its arms up on `Success` and its filaments splay on `Land`;
* **Chip** tucks all four pins on the hop and splays them on impact;
* **Bug** lifts six legs on the hop and wags both antennae;
* **Wisp** has no legs at all — it uses the legless clip path, squashing rather than
  compressing, and its tail trails the body with a lag;
* **Spool** compresses its coil on impact and releases on the hop, like a spring.

Per-creature extra bones, which is where each silhouette gets its life:

| character | extra bones |
|---|---|
| `volt` | `armL armR filamentL filamentR` |
| `chip` | `pinFL pinFR pinBL pinBR` |
| `bug` | `antennaL antennaR` |
| `wisp` | `core whiskerL whiskerR tailA tailB` |
| `spool` | `coil coilA coilB armL armR` |

All of it is in budget: worst case 9,944 triangles against a 15,000 target.

---

## 4 · Number display

Unchanged from v1 and working already — see `concept_roster.png`, where the values
`7 3 9 1 5` are drawn as **live screen-space text projected onto each `badge` bone**,
exactly the way the runtime label does it. Nothing numeric is baked into any model or
texture. `../specs/badge_label.md` still applies.

---

## 5 · Caveats, stated plainly

* **These are concept renders, not exported models.** The poses are real and the rig is
  real, but no `.glb` has been written for v2 yet, and the `specs/` files still describe
  v1. Export is a short step once the designs are signed off.
* **No `.blend` for v2 yet.** The Blender sources in `../blender/source/` are v1's. The
  route to v2 `.blend` files is the same `make_blend.py` — it only needs the exported
  GLBs first.
* **v1 is untouched.** Every file in `../models/`, `../specs/` and `../shots/` is
  exactly as it was, and `../tools/validate.py` still passes 5/5.

---

## 6 · Rebuilding these sheets

```bash
cd "3d bubblesort mascots/concepts"
python3 critters.py            # build-only sanity table: tris, joints, heights, badge anchors
python3 sheets.py              # roster + 5 view sheets + silhouette test
python3 sheets.py poses        # the rig proof (about 30 s)
python3 sheets.py views volt   # one creature's views while iterating
```

Needs `numpy` and `Pillow`. Everything else is v1's own pipeline, imported from
`../tools/`.

---

## 7 · Feedback wanted

Open questions before anything gets exported:

1. **Names and concepts** — do the five ideas land, or swap any? `Spool` and `volt` are
   both fairly tall; `chip` and `bug` are both fairly small.
2. **Sizes** — the heights above are the current spread. Tighten it, or keep the big
   size variation?
3. **Colours** — each has a distinct value structure on purpose (amber / indigo / sage /
   lilac / cream-steel). Happy with that, or want a different family palette?
4. **Which to keep** — if you only want three or four of these, say which and I will
   blend the chosen ones with whichever v1 characters you want to keep.
