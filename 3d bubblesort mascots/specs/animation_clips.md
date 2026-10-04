# Animation clips — the shared vocabulary

Every one of the five models contains **the same eight clips, with the same names and
the same durations**, so the website can run a single state machine and swap characters
without retiming anything. Frames are baked at **30 fps**; keyframes are thinned with a
per-channel tolerance, so a clip only carries the keys it actually needs.

| # | clip | duration | loop | what it is for |
|---|---|---|---|---|
| 1 | `Idle` | 4.00 s | **loop** | subtle breathing, micro-sway, two blinks |
| 2 | `GlanceL` | 0.90 s | hold | turn and look at the neighbour on the −X side |
| 3 | `GlanceR` | 0.90 s | hold | mirror of `GlanceL` |
| 4 | `Crouch` | 0.50 s | hold | anticipation squash before a hop |
| 5 | `Hop` | 0.72 s | once | in-place vertical hop: crouch, launch, apex, fall, contact |
| 6 | `Land` | 0.50 s | once | impact squash, rebound, settle |
| 7 | `NoSwap` | 0.95 s | once | small lean-away + head shake: "already in order" |
| 8 | `Success` | 1.25 s | once | double bounce, happy squint, badge pop |

Measured clip payloads (keyframes across all channels, from `specs/roster.json`):

| model | Idle | GlanceL/R | Crouch | Hop | Land | NoSwap | Success |
|---|---|---|---|---|---|---|---|
| kiln | 161 | 113 | 98 | 254 | 146 | 142 | 360 |
| ribb | 183 | 114 | 98 | 270 | 152 | 144 | 384 |
| zag | 158 | 119 | 107 | 216 | 150 | 146 | 368 |
| glim | 233 | 123 | 101 | 326 | 181 | 153 | 487 |
| rumble | 189 | 129 | 126 | 266 | 178 | 147 | 378 |

`Idle` is the only looping clip; its first and last poses are identical (verified: the
maximum joint-matrix delta over the loop is below 2·10⁻³ in every model) so it can be
cross-faded or repeated without a pop.

---

## What each clip actually does

**`Idle`** — a breathing cycle (`hips` rises ~9 mm and stretches 1.6 % on the inhale),
a slow gaze wander, a small head tilt, and two blinks at ~1.05 s and ~2.72 s. The badge
brightness pulses very slightly. Legless characters (Kiln, Ribb, Glim) substitute a
squash-and-release in the body shell for the leg work.

**`GlanceL` / `GlanceR`** — the head turns ~24–29° toward the neighbour with the chest
following by 30–50 %, the eyes lead the turn by a few millimetres, the lids lift
slightly ("attention"), and there is a small nod at the end as if confirming what it
saw. This is the **compare** pose for the animation.

**`Crouch`** — a 50 ms anticipation: the body drops, squashes, and the legs compress;
the head dips. Ends held in the crouch so a hop can be triggered from it.

**`Hop`** — starts with a deeper crouch, launches, stretches ~6–10 % on the way up,
tucks the legs in the air, and lands with a clear contact squash at 0.62 s. **The root
bone never translates**: the hop is entirely in-place (see `Root motion` below), and the
feet never pass below `y = 0` (verified in `validate.py`).

**`Land`** — impact squash down to ~84 % height for the soft characters (Glim squashes
hardest at 1.55× multiplier; Zag barely deforms at 0.85×), then a small rebound and a
settle back to neutral in 0.5 s.

**`NoSwap`** — the character leans *away* from the neighbour by ~6–7°, gives a quick
two-beat head shake, huffs (a small body pop), and settles. This is the "these two are
already in order" beat.

**`Success`** — two quick bounces with squash on each landing, a happy squint (lids
close to ~42 %), the gaze flicks left-right (a little celebratory look around), and the
badge scales to 1.10 for the pop. Appendages celebrate in character: Kiln's chimney
wobbles, Ribb's lid knot bounces, Zag's fins flare, Glim's core pulses, Rumble's copper
rings kick outward and its rear flap flaps.

---

## Root motion

**There is none.** All horizontal travel is owned by the website:

```
slot positions:    x = (index - 2) * 1.10          // 5 slots, 1.10 m apart
swap:              both characters play Hop (0.72 s)
                   tween their slot x to each other's slot over 0.55 s of it
                   then play Land (0.50 s) on touchdown
```

Because the hop is vertical-only and the root bone is pinned, a character can be
teleported to any slot mid-clip without breaking the animation.

---

## Suggested driving logic

```js
const CLIP = {
  idle:    'Idle',
  compare: (meIsLeft) => meIsLeft ? 'GlanceR' : 'GlanceL',
  swap:    'Hop',
  land:    'Land',
  noSwap:  'NoSwap',
  success: 'Success',
};

function playOnce(action) {
  action.reset();
  action.setLoop(THREE.LoopOnce, 1);
  action.clampWhenFinished = true;
  action.play();
}

// bubble sort, one comparison
function compare(a, b) {
  playOnce(a.actions[CLIP.compare(true)]);       // a sits left of b
  playOnce(b.actions[CLIP.compare(false)]);
  const mustSwap = a.value > b.value;
  setTimeout(() => mustSwap ? doSwap(a, b) : noSwap(a, b), 600);
}

function doSwap(a, b) {
  playOnce(a.actions.Hop); playOnce(b.actions.Hop);
  tweenSlotX(a, b.slotX, 620);                   // 0.62 s, matches Hop's airtime
  tweenSlotX(b, a.slotX, 620);
  setTimeout(() => { playOnce(a.actions.Land); playOnce(b.actions.Land); }, 620);
}
```

**Blending notes**

* Cross-fade `Idle` ↔ anything over 0.12–0.18 s; the clips start from neutral so short
  fades look clean.
* `Hop` and `Land` are designed to run back-to-back (`Hop` ends at −6 % height, which is
  exactly where `Land` starts) — triggering `Land` as `Hop` finishes produces no pop.
* `Success` starts from neutral and ends at neutral, so it can be fired any time after a
  `Land` completes.
* If you need a "thinking" beat while the pair is being compared, hold the last frame of
  `GlanceL`/`GlanceR` (`clampWhenFinished = true`) and it reads as a held look.
