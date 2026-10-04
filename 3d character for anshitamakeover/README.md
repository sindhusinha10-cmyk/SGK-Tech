# Maison Lumière — Haute Bridal & Makeup Studio · 3D Concierge Selector

**`index.html`** is the deliverable: one self-contained HTML5 file (HTML + CSS + JS) that builds a
luxury dark-studio 3D concierge selector with **five procedurally generated characters**.

* Zero external 3D assets — no `.gltf` / `.obj` / textures. Every surface is generated from
  primitives, lathes, parametric surfaces, ribbon sweeps, tube sweeps and canvas-painted
  procedural textures at runtime.
* Three.js **r128** + GSAP 3 from CDN (with an offline `vendor/` fallback, see below).
* 162 KB single file, ~888 KB if you use the vendor-inlined build.

---

## Run it

Just open `index.html` in a browser (a local static server is not required, but if your browser
blocks `file://` canvas textures, serve the folder with `python3 -m http.server`).

Two builds are produced by `bash build.sh`:

| file | CDN | notes |
|---|---|---|
| `index.html` | yes | **the deliverable** – loads three r128 + GSAP from cdnjs/jsdelivr |
| `index.offline.html` | no | same page with all 9 vendor libs inlined; needs no network |

If the CDNs fail, `index.html` falls back to `vendor/*.js` next to it (kept in this workspace).

---

## The five concierges

| id | name | signature |
|---|---|---|
| `asha` | Asha · The Royal Bridal Stylist | honey-wheat skin, dark-chocolate almond eyes with double catchlights, crimson velvet gold-embroidered dupatta, 24K maang tikka with ruby teardrop, jhumkas |
| `mochi` | Mochi · The Plush Concierge | chubby velvet bunny, long flexible ears with gold-threaded tips, boba eyes, burgundy satin sash with emerald brooch |
| `noor` | Noor · The Parisian Glamour Artist | porcelain skin, midnight bob with fringe, winged liner, obsidian blazer with satin lapels, glowing blending brush |
| `tara` | Tara · The Heritage Drape & Henna Guru | emerald + marigold silk saree, temple choker, nath nose ring with chain, jasmine gajra bun |
| `gia` | Gia · The Avant-Garde Nail & Crystal Icon | iridescent pastel-rose twin buns, holographic highlights, pearl face stickers, crystal nail art |

Each is a fully rigged character: gaze tracking, idle breathing + sway, organic blink sweeps,
four emotion poses, and a `rig.extra(t, dt, params)` hook for per-character life (brush glow,
ear flicker, floating crystals, …).

---

## Interaction

| control | what it does |
|---|---|
| drag on the stage | orbit / inspect (OrbitControls, bounded: dist 1.35 – 6.2, polar 0.55 – 1.6) |
| mouse move | the concierge's head + eyes follow the cursor |
| bottom dock | 5 glassmorphic pills → GSAP camera sweep + gold flash transition |
| `E` key / emotion buttons | cycle **Welcoming · Happy · Thinking · Hesitant** |
| `Auto Orbit` | slow cinematic turntable |
| `Dual View` | floating miniature concierge widget (bottom-left) rendered with a scissor pass |

---

## Architecture (each layer is detachable)

```
parts/01_head.html   DOM + all CSS (dark #060606 · champagne #C8A96A · Cinzel + Outfit)
parts/02_core.js     utils · material library · procedural canvas textures · geometry
                     helpers (parametric / ribbon / tube / fluff / folds) · HDR-ish studio
                     environment · renderer · lights · floor · backdrop · Sparkles
parts/03_rig.js      Rig class (gaze, blink, breath, sway, emotion posing) + shared
                     humanoid / eye / mouth / hair-cap / hand builders + jewellery helpers
parts/04_chars.js    window.__HBS.builders = { asha, mochi, noor, tara, gia }
parts/05_app.js      OrbitControls + touch fallback, camera rig, dock, emotions, dual-view
                     widget, pulse ring, tick loop, boot sequence, public API
build.sh             concatenates 01→05 into index.html and inlines vendor/ for the offline build
```

### Public API — `window.HBStudio`

```js
HBStudio.THREE                        // the three.js build in use (r128)
HBStudio.buildCharacter('noor')       // → { id, name, title, desc, tags, specs, swatch, frame, rig }
                                      //   + .setEmotion(n) .lookAt(x,y) .update(t,dt) .show() .hide()
HBStudio.createLights(scene)          // → { hemi, key, fill, rim, rimCool, bounce }  (studio rig)
HBStudio.list() / .get(id) / .active()
HBStudio.CHARACTERS                   // ['asha','mochi','noor','tara','gia']

// helpers also exposed (handy for embedding / debugging)
HBStudio.mats      // { skin, gold, velvet, silk, hair, gloss, crystal, pearl, matte, glow }
HBStudio.utils     // { V3, parametric, ribbon, tubeFrom, fluff, folds, lathe, capsule,
                   //   roundedBox, eyeTex, iridTex, radialTex, gradTex, brocadeTex, … }
HBStudio.lights    // the live studio lights
HBStudio.camState / .controls / .reframe() / .frameCharacter() / .setBloom()
```

**Detaching one concierge into a standalone widget** — three lines:

```js
const c = HBStudio.buildCharacter('asha');           // fresh, independent instance
const scene = new HBStudio.THREE.Scene();
HBStudio.createLights(scene);                        // same 6-light studio rig
scene.add(c.rig.root);
// …your own renderer/camera, then each frame:  c.update(time, delta); c.lookAt(mx, my);
c.setEmotion('happy');
```

Nothing in `buildCharacter` touches the page DOM, the dock or the page camera, so a builder
returned this way is fully portable.

---

## Rendering notes

* `MeshPhysicalMaterial` skin (faked subsurface via a warm emissive bleed + clearcoat sheen),
  metallic gold zardozi, velvet with a sheen-friendly high roughness + clearcoat, glass
  catchlights, glossy layered eyes (sclera → iris map → catchlight → wet dome).
* warm amber directional key + cool fill + hot back-rim spot + floor bounce; ACES filmic tone
  mapping, sRGB output, PCF soft shadows, selective bloom.
* **Colour management:** three r128 has none, so every authored colour goes through `LC()`
  (`Color.convertSRGBToLinear()`) before it reaches a material or a light. Skipping this
  desaturates and blows out every surface.
* PMREM environments are probed once at boot (`envIsUsable()`); on GPUs that return a dead
  probe the scene silently falls back to an equirect canvas environment.
