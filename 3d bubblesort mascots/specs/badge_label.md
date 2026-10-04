# Number display — where to put the value

No number, word, caption, logo or symbol is baked into any model. Each character carries
a **blank plate** (matte cream face, brushed rim) on the front, plus a dedicated `badge`
bone that is never deformed, so a label mounted on it cannot warp, wobble or shear when
the body breathes, squashes or hops.

---

## Option A (recommended) — a live texture on the badge bone

Mount a small quad (or a decal mesh) on the `badge` bone and draw the number into a
canvas texture. It inherits the character's squash, follows it in depth, and reads as
printed on the badge.

```js
// once, when the character is created
const bone = gltf.scene.getObjectByName('badge');
const W = char.meta.badgeSize[0], H = char.meta.badgeSize[1];
const canvas = document.createElement('canvas');
canvas.width = 256; canvas.height = Math.round(256 * H / W);
const ctx = canvas.getContext('2d');
const tex = new THREE.CanvasTexture(canvas);
tex.anisotropy = 4;

const label = new THREE.Mesh(
  new THREE.PlaneGeometry(W * 0.92, H * 0.86),
  new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthWrite: false,
                                toneMapped: false })
);
label.position.z = 0.012;        // sit just proud of the plate
label.renderOrder = 2;
bone.add(label);                 // parent to the bone, not the scene

// whenever the value changes
function setValue(v) {
  ctx.clearRect(0, 0, canvas.width, canvas.height);
  ctx.fillStyle = '#2A2018';
  ctx.font = `600 ${canvas.height * 0.66}px "Outfit", system-ui, sans-serif`;
  ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
  ctx.fillText(String(v), canvas.width / 2, canvas.height * 0.54);
  tex.needsUpdate = true;
}
setValue(7);
```

**Plate anchors** — the badge bone's world position in model space, and the size of the
plate you have to print on:

| model | height | `badge` bone (x, y, z) | plate (w × h) | front surface z |
|---|---|---|---|---|
| `kiln` | 1.356 m | `[0.000, 0.520, 0.320]` | 0.220 × 0.190 m | 0.320 m |
| `ribb` | 0.854 m | `[0.000, 0.152, 0.259]` | 0.172 × 0.114 m | 0.259 m |
| `zag` | 1.074 m | `[0.000, 0.520, 0.237]` | 0.200 × 0.170 m | 0.237 m |
| `glim` | 0.796 m | `[0.000, 0.234, 0.300]` | 0.146 × 0.146 m | 0.300 m |
| `rumble` | 0.655 m | `[0.000, 0.220, 0.309]` | 0.186 × 0.106 m | 0.309 m |

(The plate is a rounded plate; treat the size as the safe area and stay ~8 % inside it.)

**Do not** attach the label to `chest` or `head` directly — those bones are scaled by the
squash/stretch channels, so text would stretch with the body. The `badge` bone is immune:
it is a joint with its own inverse bind matrix, but no geometry is weighted to it, and the
clips only ever apply a small uniform scale pop (≤1.10) to it during `Success`.

---

## Option B — a screen-space DOM label

If you would rather draw numbers as crisp HTML (best for tiny characters), project the
badge anchor every frame and place an absolutely-positioned element:

```js
function badgeScreenPos(char, renderer, camera) {
  const p = new THREE.Vector3(...char.meta.badgeAnchor);   // model space
  char.root.updateWorldMatrix(true, false);
  p.applyMatrix4(char.root.matrixWorld).project(camera);
  return {
    x: (p.x * 0.5 + 0.5) * renderer.domElement.clientWidth,
    y: (-p.y * 0.5 + 0.5) * renderer.domElement.clientHeight,
    z: p.z,                                                // cull if > 1
  };
}
```

The `badgeAnchor` value for every character is in `specs/roster.json` under
`badge_anchor`, and also inside each GLB as node extras
(`nodes[mesh].extras.badgeAnchor` / `badgeSize`), so the runtime can read it from the
file without a lookup table.

**Why there is also a physical plate.** Even with screen-space labels, the plate does real
work: it gives the number a consistent, high-contrast background on all five characters
(cream against terracotta, weave, slate, cyan and aluminium), and it gives the eye a
stable anchor so the value does not appear to swim when a character hops.

---

## Slot spacing

The rehearsal scene places the five characters at `x = (index − 2) × 1.10 m`. The widest
character (Ribb, 1.03 m across including handles) leaves a small gap to its neighbours at
that spacing; 1.10 m is therefore the recommended minimum slot pitch for a five-slot row.
