# Hand-off prompt: make **Meera** and **Cherry** more beautiful

Paste everything below into a fresh conversation with another AI. It contains the
project context, the hard technical constraints, and the complete current source
for the two characters.

---

## PROMPT (copy from here)

You are working on a single-file Three.js (**r128**) luxury "Haute Bridal & Makeup
Studio 3D Concierge Selector". Seven animated concierges stand on a dark studio
stage (`#060606` background, `#C8A96A` gold accents). Two of them are rigged GLTF
models of birds and the client loves them - the task is to make **Meera** (a
flamingo) and **Cherry** (a parrot) more beautiful without breaking anything.

### Hard constraints - read before changing anything

1. **Three.js r128**, loaded as a global `THREE` (aliased `T`). Not ES modules.
   Plain ES5-style JavaScript, no `import`, `const` or arrow functions in this
   file (function-scoped `var` throughout). Match that style.
2. **Colour management**: every authored sRGB hex MUST pass through
   `LC(hex)` (= `new THREE.Color(hex).convertSRGBToLinear()`). Never pass a raw
   hex to a material `color`. Skipping `LC()` is what makes colours wash out.
3. **r128 gotcha**: `MeshPhysicalMaterial.sheen` is a **`THREE.Color`**, not a
   float. Setting `sheen: 1.0` corrupts a `vec3` uniform and throws
   `uniform3fv: Overload resolution failed`, rendering the material black. This
   already bit the project once.
4. **Models load asynchronously.** `buildOne()` creates the character shell
   synchronously; the GLB arrives later. Never assume geometry exists at build time.
5. **`measure(c)` caches** `_h`, `_w`, `_cy` on the character object. If you change
   a model's size, set those three to `undefined` so the camera re-frames. It also
   deliberately ignores empty bounding boxes.
6. **Auto-scale**: each model is scaled to its roster `h` (target height in
   metres), planted on the floor (`-b.min.y`) and centred on x/z. Anything you
   parent into the model must be counter-scaled by `1/k` where
   `k = cfg.h / bindBoxHeight`, or it will be invisible.
7. Some clips carry **root motion** (Michelle's samba walks the character off
   camera). `updateModel()` pins `_root.position.x/z` each frame - don't remove that.
8. Helpers in scope: `LC`, `lathe(profile2D, seg, smooth)`,
   `capsule(r, len, seg, capSeg)`, `roundedBox`, `tubeFrom(points, r, seg, radial,
   closed)`, `fluff(geo, amp, freq)`, `folds(geo, count, amp, yFalloff)`,
   `parametric`, `V3`, `TAU`, `goldMat(tone)`, `silkMat(col, rough)`, `velvetMat`,
   `hairMat`, `crystalMat`, `pearlMat`, `matteMat`, `glossMat`, `makeEye`,
   `makeMouth`, `hairCap`, `jewel`, `Rig`, `CANON`.

### What "more beautiful" should mean here

The stage is a dark luxury studio. Priorities, in order:

- **Silhouette and form first** - the birds currently read as small and slightly
  flat. Richer surface treatment (sheen, subtle iridescence, feather-like normal
  variation) beats adding more geometry.
- **They must stay recognisably themselves** - a flamingo and a parrot, not generic
  birds. Keep the species silhouette.
- **Studio-appropriate styling** - this is a *bridal couture* studio. Think jewelled
  collar, gem brooch, subtle gold leafing, a couture sash or head piece. They
  already have a gold collar + gem (see `addJewels`); improve it rather than
  replacing it wholesale.
- **Contrast against `#060606`** - dark-on-dark characters disappear. Anything you
  add should be mid-to-light in tone.

### Specific known issues to fix if you can

1. **They render too small at narrow viewports.** At 648x527 Meera occupies only
   about 19 percent of frame width and Cherry about 28 percent, while at 1280x800
   both are about 99 percent. Their morph (flap) animation changes the bounding
   box, so the auto-fit and the camera fight each other. Options: stabilise the
   framing by measuring the *posed* box after a delay, or give them a wider
   `frame.fill` / a larger roster `h`.
2. **Feathers are flat.** Consider procedural normal/roughness variation or a
   subtle iridescent clearcoat so the plumage catches the rim light.
3. **Meera is flamingo pink, Cherry is parrot green/red.** Tie them into the
   studio's gold (`#C8A96A`) so they read as staff, not wildlife.

### Deliverable

Return the **complete replacement code** for:
- the `meera` and `cherry` entries in `GLTF_ROSTER`
- `addJewels()` (and any new helper you add)

...as plain JavaScript in the existing ES5 style, with `LC()` around every colour,
plus a one-line note on what each change does. Do not return the whole file - just
the pieces to swap in.

---

## CURRENT SOURCE (include this in the prompt)

### 1. Roster entries

```js
{ id:'meera',  url:'models/Flamingo.glb',        h:1.30, jewels:{ metal:1, gem:0xE8C26A }, name:'Meera',  title:'The Couture Hair & Makeup Artist',
    desc:'Blowouts, bridal partings and the 14-hour hold — Meera designs the hair and beauty look that survives the phera, the photos and the after-party.',
    tags:['Hair Couture','Bridal Beauty','Long-Wear','Editorial'],
    specs:[['Palette','Ivory · Ink Black · Gold'],['Signature','Glossy Bob & Blunt Fringe'],['Consultation','60 min · Trial included']],
    swatch:['#DFD4C0','#16161C'], frame:{fill:0.70,el:0.070,fov:34} },
```

```js
{ id:'cherry', url:'models/Parrot.glb',          h:1.00, jewels:{ metal:0, gem:0xE24A5E }, name:'Cherry', title:'The Glow-Berry Skincare Concierge',
    desc:'Berry enzymes, vitamin-C facials and pre-bridal skin prep — Cherry builds the 90-day glow plan that makes the makeup sit like glass.',
    tags:['Skincare','Vitamin C','Pre-Bridal','Glow Plan'],
    specs:[['Palette','Berry Red · Leaf Green'],['Signature','Seed-Dot Detailing'],['Consultation','30 min · Skin analysis']],
    swatch:['#D42A3C','#4E9B3F'], frame:{fill:0.70,el:0.060,fov:34} }
];
```

### 2. Clip selection (change which animation plays)

```js
var CLIP_WANT = { poise:['idle','Idle','IDLE','standing','Standing','survey','Survey'],
                  joy:['wave','Wave','jump','Jump','dance','Dance','run','Run'],
                  serenity:['walk','Walk','idle','Idle','survey','Survey'],
                  smoulder:['no','No','punch','Punch','thumbsUp','ThumbsUp','idle','Idle'] };

function pickClip(clips, want) {
  if (!clips || !clips.length) return null;
  for (var i = 0; i < want.length; i++) {
    for (var j = 0; j < clips.length; j++) if (clips[j].name === want[i]) return clips[j].name;
  }
  return clips[0].name;
}


/* ------------------------------------------------- couture & re-skin ------ */
function reskinModel(root, cfg) {
  var mSkin  = new T.MeshPhysicalMaterial({ color: LC(cfg.skin),  roughness: 0.52, clearcoat: 0.30, clearcoatRoughness: 0.45, envMapIntensity: 1.10 });
  var mCloth = new T.MeshPhysicalMaterial({ color: LC(cfg.cloth), roughness: 0.62, envMapIntensity: 1.35 });
  var mMetal = new T.MeshPhysicalMaterial({ color: LC(cfg.metal), roughness: 0.24, metalness: 0.92, envMapIntensity: 1.45 });
  root.traverse(function (o) {
    if (!o.isMesh) return;
    var ms = Array.isArray(o.material) ? o.material : [o.material];
    for (var i = 0; i < ms.length; i++) if (ms[i] && ms[i].map) return;   /* keep textured parts */
    var n = (o.name || '').toLowerCase();
    if (/head|face|skin|body|neck|hand/.test(n)) o.material = mSkin;
    else if (/hair|helmet|boot|shoe|glove|belt|strap|buckle/.test(n)) o.material = mMetal;
    else o.material = mCloth;
  });
}

/* Skirt hung at the waist, sized in metres, then divided by the model's
   auto-scale so it survives being parented into a scaled rig. */
/* A jewelled collar + gem brooch, for characters too small or feathered
   for a full couture skirt. Sized in metres, counter-scaled by the rig. */
function addJewels(model, cfg, k) {
  var box = new T.Box3().setFromObject(model);
  var h = box.max.y - box.min.y;
  var rad = Math.max(0.045, h * 0.085);
  var g = new T.Group();

  var collar = new T.Mesh(new T.TorusGeometry(rad, rad * 0.15, 12, 40), goldMat(cfg.metal === undefined ? 1 : cfg.metal));
  collar.rotation.x = Math.PI / 2 - 0.20;
  collar.castShadow = true;
  g.add(collar);

  var ring2 = new T.Mesh(new T.TorusGeometry(rad * 1.22, rad * 0.055, 10, 44), goldMat(0));
  ring2.rotation.x = Math.PI / 2 - 0.20;
  ring2.position.y = -rad * 0.42;
  g.add(ring2);

  var gem = new T.Mesh(new T.SphereGeometry(rad * 0.40, 20, 16), crystalMat(cfg.gem || 0xE8C26A));
  gem.position.set(0, -rad * 0.98, rad * 0.62);
  g.add(gem);

  var holder = new T.Group();
  holder.add(g);
  holder.scale.setScalar(1 / k);
  holder.position.y = box.min.y + h * 0.70;
  model.add(holder);
  return holder;
}

function addCouture(model, cfg, k) {
  var box = new T.Box3().setFromObject(model);
  var waistY = box.min.y + (box.max.y - box.min.y) * 0.52;
  var profile = cfg.kind === 'saree'
    ? [[0.03, 0.012], [0.20, 0.020], [0.30, 0.070], [0.36, 0.200], [0.385, 0.400],
       [0.345, 0.600], [0.280, 0.760], [0.225, 0.880], [0.200, 0.950]]
    : [[0.03, 0.012], [0.22, 0.020], [0.34, 0.090], [0.40, 0.230], [0.415, 0.400],
       [0.385, 0.560], [0.310, 0.720], [0.240, 0.850], [0.205, 0.925], [0.195, 0.960]];
  var skirtGeo = lathe(profile, 48, true);
  folds(skirtGeo, 14, 0.018, [0.02, 0.90]);
  var sm = silkMat(cfg.cloth, 0.32); sm.side = T.DoubleSide;
  var skirt = new T.Mesh(skirtGeo, sm);
  skirt.castShadow = true; skirt.receiveShadow = true;

  var holder = new T.Group();
  holder.add(skirt);
  holder.scale.setScalar(1 / k);
  holder.position.y = waistY;
  model.add(holder);

  var beltGeo = new T.TorusGeometry(0.215, 0.011, 10, 60);
  var belt = new T.Mesh(beltGeo, goldMat(1));
  belt.rotation.x = Math.PI / 2;
  var bh = new T.Group();
  bh.add(belt);
  bh.scale.setScalar(1 / k);
  bh.position.y = waistY + 0.86 / 1;
  model.add(bh);
  return holder;
}
```

### 3. `addJewels()` - the current collar + gem

```js
function addJewels(model, cfg, k) {
  var box = new T.Box3().setFromObject(model);
  var h = box.max.y - box.min.y;
  var rad = Math.max(0.045, h * 0.085);
  var g = new T.Group();

  var collar = new T.Mesh(new T.TorusGeometry(rad, rad * 0.15, 12, 40), goldMat(cfg.metal === undefined ? 1 : cfg.metal));
  collar.rotation.x = Math.PI / 2 - 0.20;
  collar.castShadow = true;
  g.add(collar);

  var ring2 = new T.Mesh(new T.TorusGeometry(rad * 1.22, rad * 0.055, 10, 44), goldMat(0));
  ring2.rotation.x = Math.PI / 2 - 0.20;
  ring2.position.y = -rad * 0.42;
  g.add(ring2);

  var gem = new T.Mesh(new T.SphereGeometry(rad * 0.40, 20, 16), crystalMat(cfg.gem || 0xE8C26A));
  gem.position.set(0, -rad * 0.98, rad * 0.62);
  g.add(gem);

  var holder = new T.Group();
  holder.add(g);
  holder.scale.setScalar(1 / k);
  holder.position.y = box.min.y + h * 0.70;
  model.add(holder);
  return holder;
}
```

### 4. `reskinModel()` - recolours untextured rig parts (textured ones skipped)

```js
function reskinModel(root, cfg) {
  var mSkin  = new T.MeshPhysicalMaterial({ color: LC(cfg.skin),  roughness: 0.52, clearcoat: 0.30, clearcoatRoughness: 0.45, envMapIntensity: 1.10 });
  var mCloth = new T.MeshPhysicalMaterial({ color: LC(cfg.cloth), roughness: 0.62, envMapIntensity: 1.35 });
  var mMetal = new T.MeshPhysicalMaterial({ color: LC(cfg.metal), roughness: 0.24, metalness: 0.92, envMapIntensity: 1.45 });
  root.traverse(function (o) {
    if (!o.isMesh) return;
    var ms = Array.isArray(o.material) ? o.material : [o.material];
    for (var i = 0; i < ms.length; i++) if (ms[i] && ms[i].map) return;   /* keep textured parts */
    var n = (o.name || '').toLowerCase();
    if (/head|face|skin|body|neck|hand/.test(n)) o.material = mSkin;
    else if (/hair|helmet|boot|shoe|glove|belt|strap|buckle/.test(n)) o.material = mMetal;
    else o.material = mCloth;
  });
}

/* Skirt hung at the waist, sized in metres, then divided by the model's
   auto-scale so it survives being parented into a scaled rig. */
/* A jewelled collar + gem brooch, for characters too small or feathered
   for a full couture skirt. Sized in metres, counter-scaled by the rig. */
function addJewels(model, cfg, k) {
  var box = new T.Box3().setFromObject(model);
  var h = box.max.y - box.min.y;
  var rad = Math.max(0.045, h * 0.085);
  var g = new T.Group();

  var collar = new T.Mesh(new T.TorusGeometry(rad, rad * 0.15, 12, 40), goldMat(cfg.metal === undefined ? 1 : cfg.metal));
  collar.rotation.x = Math.PI / 2 - 0.20;
  collar.castShadow = true;
  g.add(collar);

  var ring2 = new T.Mesh(new T.TorusGeometry(rad * 1.22, rad * 0.055, 10, 44), goldMat(0));
  ring2.rotation.x = Math.PI / 2 - 0.20;
  ring2.position.y = -rad * 0.42;
  g.add(ring2);

  var gem = new T.Mesh(new T.SphereGeometry(rad * 0.40, 20, 16), crystalMat(cfg.gem || 0xE8C26A));
  gem.position.set(0, -rad * 0.98, rad * 0.62);
  g.add(gem);

  var holder = new T.Group();
  holder.add(g);
  holder.scale.setScalar(1 / k);
  holder.position.y = box.min.y + h * 0.70;
  model.add(holder);
  return holder;
}

function addCouture(model, cfg, k) {
  var box = new T.Box3().setFromObject(model);
  var waistY = box.min.y + (box.max.y - box.min.y) * 0.52;
  var profile = cfg.kind === 'saree'
    ? [[0.03, 0.012], [0.20, 0.020], [0.30, 0.070], [0.36, 0.200], [0.385, 0.400],
       [0.345, 0.600], [0.280, 0.760], [0.225, 0.880], [0.200, 0.950]]
    : [[0.03, 0.012], [0.22, 0.020], [0.34, 0.090], [0.40, 0.230], [0.415, 0.400],
       [0.385, 0.560], [0.310, 0.720], [0.240, 0.850], [0.205, 0.925], [0.195, 0.960]];
  var skirtGeo = lathe(profile, 48, true);
  folds(skirtGeo, 14, 0.018, [0.02, 0.90]);
  var sm = silkMat(cfg.cloth, 0.32); sm.side = T.DoubleSide;
  var skirt = new T.Mesh(skirtGeo, sm);
  skirt.castShadow = true; skirt.receiveShadow = true;

  var holder = new T.Group();
  holder.add(skirt);
  holder.scale.setScalar(1 / k);
  holder.position.y = waistY;
  model.add(holder);

  var beltGeo = new T.TorusGeometry(0.215, 0.011, 10, 60);
  var belt = new T.Mesh(beltGeo, goldMat(1));
  belt.rotation.x = Math.PI / 2;
  var bh = new T.Group();
  bh.add(belt);
  bh.scale.setScalar(1 / k);
  bh.position.y = waistY + 0.86 / 1;
  model.add(bh);
  return holder;
}

function makeGLTFCharacter(cfg) {
  var rig = new Rig({ id: cfg.id });
  var c = {
    id: cfg.id, name: cfg.name, title: cfg.title, desc: cfg.desc,
    tags: cfg.tags, specs: cfg.specs, swatch: cfg.swatch, frame: cfg.frame,
    rig: rig, ready: false, error: null, _rate: cfg.rate || 1, _targetH: cfg.h,
    _mixer: null, _actions: {}, _active: null, _clips: null
  };

  c.playClip = function (name) {
    if (!this._mixer || !name || !this._actions[name]) return;
    if (this._active && this._active !== name) this._actions[this._active].stop();
    var a = this._actions[name];
    a.reset().fadeIn(0.45).play();
    a.setEffectiveTimeScale(this._rate || 1);
    this._active = name;
  };
  c.setEmotionClip = function (emo) {
    this.playClip(pi
```

### 5. `addCouture()` - skirt used by the humanoid concierges (for reference)

```js
function addCouture(model, cfg, k) {
  var box = new T.Box3().setFromObject(model);
  var waistY = box.min.y + (box.max.y - box.min.y) * 0.52;
  var profile = cfg.kind === 'saree'
    ? [[0.03, 0.012], [0.20, 0.020], [0.30, 0.070], [0.36, 0.200], [0.385, 0.400],
       [0.345, 0.600], [0.280, 0.760], [0.225, 0.880], [0.200, 0.950]]
    : [[0.03, 0.012], [0.22, 0.020], [0.34, 0.090], [0.40, 0.230], [0.415, 0.400],
       [0.385, 0.560], [0.310, 0.720], [0.240, 0.850], [0.205, 0.925], [0.195, 0.960]];
  var skirtGeo = lathe(profile, 48, true);
  folds(skirtGeo, 14, 0.018, [0.02, 0.90]);
  var sm = silkMat(cfg.cloth, 0.32); sm.side = T.DoubleSide;
  var skirt = new T.Mesh(skirtGeo, sm);
  skirt.castShadow = true; skirt.receiveShadow = true;

  var holder = new T.Group();
  holder.add(skirt);
  holder.scale.setScalar(1 / k);
  holder.position.y = waistY;
  model.add(holder);

  var beltGeo = new T.TorusGeometry(0.215, 0.011, 10, 60);
  var belt = new T.Mesh(beltGeo, goldMat(1));
  belt.rotation.x = Math.PI / 2;
  var bh = new T.Group();
  bh.add(belt);
  bh.scale.setScalar(1 / k);
  bh.position.y = waistY + 0.86 / 1;
  model.add(bh);
  return holder;
}
```

### 6. `makeGLTFCharacter()` - the loader both characters run through

```js
function makeGLTFCharacter(cfg) {
  var rig = new Rig({ id: cfg.id });
  var c = {
    id: cfg.id, name: cfg.name, title: cfg.title, desc: cfg.desc,
    tags: cfg.tags, specs: cfg.specs, swatch: cfg.swatch, frame: cfg.frame,
    rig: rig, ready: false, error: null, _rate: cfg.rate || 1, _targetH: cfg.h,
    _mixer: null, _actions: {}, _active: null, _clips: null
  };

  c.playClip = function (name) {
    if (!this._mixer || !name || !this._actions[name]) return;
    if (this._active && this._active !== name) this._actions[this._active].stop();
    var a = this._actions[name];
    a.reset().fadeIn(0.45).play();
    a.setEffectiveTimeScale(this._rate || 1);
    this._active = name;
  };
  c.setEmotionClip = function (emo) {
    this.playClip(pickClip(this._clips, CLIP_WANT[emo] || CLIP_WANT.poise));
  };
  c.updateModel = function (dt) {
    if (this._mixer) this._mixer.update(dt);
    /* some clips (Michelle's samba) carry root translation — pin the model's
       horizontal position so it cannot dance out of the framed area */
    if (this._root) {
      this._root.position.x = this._baseX;
      this._root.position.z = this._baseZ;
    }
  };

  if (typeof T.GLTFLoader === 'undefined') { c.error = 'GLTFLoader unavailable'; return c; }
  new T.GLTFLoader().load(cfg.url, function (gltf) {
    var m = gltf.scene;
    m.traverse(function (o) { if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; } });
    /* auto-scale to a target height, then plant on the floor and centre —
       the source models come in wildly different unit scales */
    var b = new T.Box3().setFromObject(m);
    var hh = b.max.y - b.min.y;
    if (hh > 1e-4) m.scale.multiplyScalar(cfg.h / hh);
    b.setFromObject(m);
    m.position.set(-(b.max.x + b.min.x) / 2, -b.min.y, -(b.max.z + b.min.z) / 2);
    var k = cfg.h / (hh > 1e-4 ? hh : 1);
    if (cfg.reskin)  { try { reskinModel(m, cfg.reskin); } catch (e) {} }
    if (cfg.couture) { try { addCouture(m, cfg.couture, k); } catch (e) {} }
    if (cfg.jewels)  { try { addJewels(m, cfg.jewels, k); }  catch (e) {} }
    /* imported PBR materials are authored for brighter rigs — lift their
       environment response so they do not read as black silhouettes */
    m.traverse(function (o) {
      if (!o.isMesh) return;
      var ms = Array.isArray(o.material) ? o.material : [o.material];
      for (var i = 0; i < ms.length; i++) {
        var mm = ms[i]; if (!mm) continue;
        if ('envMapIntensity' in mm) mm.envMapIntensity = Math.max(mm.envMapIntensity || 0, 1.55);
        if (mm.isMeshStandardMaterial && !mm.map) { /* flat-shaded rigs: lift base response */
          mm.roughness = Math.min(mm.roughness, 0.72);
        }
      }
    });
    rig.body.add(m);
    c._mixer = new T.AnimationMixer(m);
    if (gltf.animations && gltf.animations.length) {
      c._clips = gltf.animations;
      for (var i = 0; i < gltf.animations.length; i++) {
        c._actions[gltf.animations[i].name] = c._mixer.clipAction(gltf.animations[i]);
      }
      c.playClip(pickClip(c._clips, CLIP_WANT.poise));
    }
    c._root = m; c._baseX = m.position.x; c._baseZ = m.position.z;
    c.ready = true;
    /* the box used for the initial fit is the BIND pose; morph/rig animation
       can change the real silhouette a lot (the birds were scaled to specks).
       Re-fit once the clip has posed the model so the authored height is real. */
    setTimeout(function () {
      try {
        var b2 = new T.Box3().setFromObject(m);
        var h2 = b2.max.y - b2.min.y;
        if (h2 > 1e-4 && Math.abs(h2 - cfg.h) / cfg.h > 0.10) {
          m.scale.multiplyScalar(cfg.h / h2);
          b2.setFromObject(m);
          m.position.set(-(b2.max.x + b2.min.x) / 2, -b2.min.y, -(b2.max.z + b2.min.z) / 2);
          c._baseX = m.position.x; c._baseZ = m.position.z;
          c._h = undefined; c._w = undefined; c._cy = undefined;
          if (typeof HBS !== 'undefined' && HBS.reframe && window.__HBS_ACTIVE) {
            if (window.__HBS_ACTIVE() === c) HBS.reframe(0.6);
          }
        }
      } catch (e) {}
    }, 500);
    if (typeof c.onReady === 'function') { try { c.onReady(); } catch (e) {} }
  }, undefined, function () { c.error = 'failed: ' + cfg.url; });

  return c;
}
```
