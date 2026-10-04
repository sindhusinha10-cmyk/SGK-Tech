/* =====================================================================
   03 · RIG — living character system
   Gaze tracking · organic blinks · breathing · sway · emotion posing
   ===================================================================== */
(function () {
'use strict';
var H = window.__HBS, T = H.T;
var V3 = H.V3, C = H.C, LC = H.C, clamp = H.clamp, lerp = H.lerp, damp = H.damp;
var capsule = H.capsule, lathe = H.lathe, roundedBox = H.roundedBox, parametric = H.parametric,
    ribbon = H.ribbon, tubeFrom = H.tubeFrom, fluff = H.fluff, folds = H.folds, mesh = H.mesh, group = H.group;
var skinMat = H.skinMat, goldMat = H.goldMat, velvetMat = H.velvetMat, silkMat = H.silkMat,
    hairMat = H.hairMat, glossMat = H.glossMat, crystalMat = H.crystalMat, pearlMat = H.pearlMat,
    matteMat = H.matteMat, glowMat = H.glowMat;
var TAU = Math.PI * 2;

/* ------------------------------------------------------------------ constants */
var LID_OPEN = -0.16;     // upper-lid sweep, fully open
var LID_SHUT = 1.78;      // upper-lid sweep, fully closed
var CANON = {             // shared humanoid proportions (metres-ish)
  hipY: 0.86, chestY: 1.16, shoulderY: 1.29, neckY: 1.38, headY: 1.53,
  headRX: 0.201, headRY: 0.217, headRZ: 0.199
};

/* ================================================================== Rig ===== */
function Rig(cfg) {
  cfg = cfg || {};
  this.id = cfg.id || 'rig';
  this.root = new T.Group();
  this.body = new T.Group();
  this.root.add(this.body);
  this.head = new T.Group();
  this.head.position.set(0, cfg.headY !== undefined ? cfg.headY : CANON.headY, 0);
  this.body.add(this.head);
  this.chest = new T.Group();
  this.body.add(this.chest);

  this.parts = [];
  this.gx = 0; this.gy = 0; this.tgx = 0; this.tgy = 0;
  this.blinkTimer = 1.4 + Math.random() * 2.6;
  this.blinkActive = false; this.blinkT = 0;
  this.emotion = 'poise';
  this.time = 0;

  /* every animated scalar lives here — GSAP tweens this object directly */
  this.pose = {
    headRx: 0, headRy: 0, headRz: 0, headY: 0, headZ: 0,
    bodyRx: 0, bodyRy: 0, bodyRz: 0, bodyY: 0, bodyLean: 0,
    browL: 0, browR: 0, lidL: 1, lidR: 1,
    mouthOpen: 0.04, smile: 0.55, eyeX: 0, eyeY: 0,
    armRx: -0.06, armRy: 0, armRz: 0.14, elbowRx: -0.16, elbowRz: -0.05,
    armLx: -0.06, armLy: 0, armLz: -0.14, elbowLx: -0.16, elbowLz: 0.05,
    bounce: 0, glow: 0.3, sparkle: 0, breath: 1
  };

  /* emotion targets (per-character builders may extend / override these) */
  this.emotions = {
    poise: {
      headRx: 0, headRy: 0, headRz: 0, headY: 0,
      bodyRx: 0, bodyRy: 0, bodyRz: 0, bodyY: 0,
      browL: 0, browR: 0, lidL: 1, lidR: 1,
      mouthOpen: 0.04, smile: 0.55, eyeX: 0, eyeY: 0,
      armRx: -0.06, armRy: 0, armRz: 0.14, elbowRx: -0.16, elbowRz: -0.05,
      armLx: -0.06, armLy: 0, armLz: -0.14, elbowLx: -0.16, elbowLz: 0.05,
      bounce: 0, glow: 0.3, sparkle: 0.06
    },
    welcome: {
      headRx: 0.11, headRy: 0, headRz: 0, headY: -0.018,
      bodyRx: 0.03, bodyRy: 0, bodyRz: 0, bodyY: -0.008,
      browL: 0.25, browR: 0.25, lidL: 0.82, lidR: 0.82,
      mouthOpen: 0.05, smile: 0.95, eyeX: 0, eyeY: 0,
      armRx: -1.02, armRy: 0, armRz: -0.06, elbowRx: -1.44, elbowRz: -0.32,
      armLx: -1.02, armLy: 0, armLz: 0.06, elbowLx: -1.44, elbowLz: 0.32,
      bounce: 0.16, glow: 0.55, sparkle: 0.25
    },
    happy: {
      headRx: -0.05, headRy: 0, headRz: 0.07, headY: 0.012,
      bodyRx: -0.03, bodyRy: 0, bodyRz: 0, bodyY: 0,
      browL: 0.55, browR: 0.45, lidL: 0.74, lidR: 0.74,
      mouthOpen: 0.42, smile: 1.30, eyeX: 0, eyeY: 0.03,
      armRx: -0.58, armRy: 0, armRz: 0.44, elbowRx: -1.02, elbowRz: -0.18,
      armLx: -0.58, armLy: 0, armLz: -0.44, elbowLx: -1.02, elbowLz: 0.18,
      bounce: 1.0, glow: 0.9, sparkle: 1
    },
    thinking: {
      headRx: 0.07, headRy: -0.20, headRz: -0.10, headY: 0,
      bodyRx: 0.02, bodyRy: 0.10, bodyRz: 0, bodyY: -0.004,
      browL: 0.62, browR: -0.12, lidL: 0.66, lidR: 0.60,
      mouthOpen: 0.02, smile: 0.22, eyeX: -0.05, eyeY: -0.11,
      armRx: -0.86, armRy: 0, armRz: -0.40, elbowRx: -1.86, elbowRz: -0.52,
      armLx: -0.24, armLy: 0, armLz: -0.22, elbowLx: -0.62, elbowLz: 0.14,
      bounce: 0, glow: 0.45, sparkle: 0.12
    },
    hesitant: {
      headRx: 0.04, headRy: 0.17, headRz: 0.14, headY: -0.006,
      bodyRx: 0.06, bodyRy: -0.10, bodyRz: 0, bodyY: -0.014,
      browL: -0.34, browR: -0.20, lidL: 0.88, lidR: 0.88,
      mouthOpen: 0.015, smile: -0.18, eyeX: 0.03, eyeY: 0.02,
      armRx: -0.40, armRy: 0, armRz: -0.26, elbowRx: -0.80, elbowRz: -0.40,
      armLx: -0.40, armLy: 0, armLz: 0.26, elbowLx: -0.80, elbowLz: 0.40,
      bounce: 0, glow: 0.20, sparkle: 0
    }
  };
}

Rig.prototype.setEmotion = function (name, dur) {
  var t = this.emotions[name] ? this.emotions[name] : this.emotions.poise;
  this.emotion = this.emotions[name] ? name : 'poise';
  var o = { duration: dur === undefined ? 1.15 : dur, ease: 'power3.out', overwrite: 'auto' };
  for (var k in t) o[k] = t[k];
  window.gsap.to(this.pose, o);
  if (this.onEmotion) this.onEmotion(this.emotion);
};

Rig.prototype.lookTarget = function (x, y) {
  this.tgx = clamp(x, -1, 1);
  this.tgy = clamp(y, -1, 1);
};

Rig.prototype.collectMaterials = function () {
  var out = [];
  this.root.traverse(function (o) {
    if (o.isMesh || o.isPoints) {
      var m = o.material;
      if (!m) return;
      if (m.__orig === undefined) {
        m.__orig = { transparent: m.transparent, opacity: m.opacity, depthWrite: m.depthWrite };
      }
      out.push(m);
    }
  });
  this.mats = out;
  return out;
};
Rig.prototype.setOpacity = function (v) {
  if (!this.mats) this.collectMaterials();
  for (var i = 0; i < this.mats.length; i++) {
    var m = this.mats[i], o = m.__orig;
    if (v >= 0.999) { m.transparent = o.transparent; m.opacity = o.opacity; m.depthWrite = o.depthWrite; }
    else {
      m.transparent = true;
      m.opacity = o.opacity * v;
      m.depthWrite = o.transparent ? false : (v > 0.7);
    }
  }
};

Rig.prototype.update = function (t, dt) {
  var p = this.pose;
  this.time = t;
  this.gx = damp(this.gx, this.tgx, 4.4, dt);
  this.gy = damp(this.gy, this.tgy, 4.4, dt);

  /* ---- organic blink ---- */
  this.blinkTimer -= dt;
  if (this.blinkTimer <= 0 && !this.blinkActive) {
    this.blinkActive = true; this.blinkT = 0;
    this.blinkTimer = (Math.random() < 0.2 ? 0.17 : 2.3 + Math.random() * 4.2);
  }
  var blinkAmt = 0;
  if (this.blinkActive) {
    this.blinkT += dt / 0.17;
    if (this.blinkT >= 1) { this.blinkActive = false; blinkAmt = 0; }
    else blinkAmt = Math.sin(this.blinkT * Math.PI);
  }

  /* ---- breathing + idle sway ---- */
  var br = Math.sin(t * 1.32) * p.breath;
  var br2 = Math.sin(t * 1.32 + 0.55) * p.breath;
  var hop = p.bounce > 0.01 ? Math.abs(Math.sin(t * 4.1)) * 0.05 * p.bounce : 0;
  var lean = p.bodyLean;

  this.body.rotation.y = p.bodyRy + 0.040 * Math.sin(t * 0.55);
  this.body.rotation.z = p.bodyRz + 0.019 * Math.sin(t * 0.42 + 1.3);
  this.body.rotation.x = p.bodyRx + lean + 0.013 * Math.sin(t * 0.71 + 0.4);
  this.body.position.y = p.bodyY + 0.010 * br + hop;
  if (this.chest) {
    this.chest.scale.set(1 + 0.013 * br, 1 + 0.017 * br, 1 + 0.016 * br);
    this.chest.position.y = (this.chestBaseY || 0) + 0.004 * br2;
  }

  /* ---- head: emotion + idle + gaze ---- */
  if (this.head) {
    this.head.rotation.x = p.headRx + 0.021 * Math.sin(t * 0.93 + 0.4) - this.gy * 0.17;
    this.head.rotation.y = p.headRy + 0.048 * Math.sin(t * 0.61 + 2.1) + this.gx * 0.34;
    this.head.rotation.z = p.headRz + 0.023 * Math.sin(t * 0.47) + this.gx * 0.05;
    this.head.position.y = (this.headY0 || this.head.position.y) + p.headY + 0.006 * Math.sin(t * 1.32 + 1.1) + hop * 0.4;
  }

  /* ---- eyes ---- */
  var ex = this.gx * 0.17 + p.eyeX, ey = -this.gy * 0.11 + p.eyeY;
  if (this.eyeL) this.applyEye(this.eyeL, ex, ey, p.lidL * (1 - blinkAmt), blinkAmt);
  if (this.eyeR) this.applyEye(this.eyeR, ex, ey, p.lidR * (1 - blinkAmt), blinkAmt);

  /* ---- brows ---- */
  if (this.browL) this.applyBrow(this.browL, p.browL);
  if (this.browR) this.applyBrow(this.browR, p.browR);

  /* ---- mouth ---- */
  if (this.mouth) {
    var m = this.mouth;
    m.group.scale.set(1, 1 + p.smile * 0.32, 1);
    m.group.position.y = m.base.y + p.smile * 0.006;
    if (m.inner) {
      m.inner.scale.set(1, 0.16 + p.mouthOpen * 1.15, 1);
      m.inner.position.y = -0.004 - p.mouthOpen * 0.012;
      m.inner.visible = p.mouthOpen > 0.05;
    }
    if (m.teeth) { m.teeth.visible = p.mouthOpen > 0.18; m.teeth.position.y = m.teethBaseY - p.mouthOpen * 0.006; }
    if (m.lower) m.lower.position.y = -p.mouthOpen * 0.030;
  }

  /* ---- arms ---- */
  if (this.armR) {
    this.armR.shoulder.rotation.set(p.armRx, p.armRy, p.armRz);
    this.armR.elbow.rotation.set(p.elbowRx, 0, p.elbowRz);
  }
  if (this.armL) {
    this.armL.shoulder.rotation.set(p.armLx, p.armLy, p.armLz);
    this.armL.elbow.rotation.set(p.elbowLx, 0, p.elbowLz);
  }

  if (this.extra) this.extra(t, dt, p);
};

Rig.prototype.applyEye = function (e, ex, ey, openness, blinkAmt) {
  e.group.rotation.y = ex;
  e.group.rotation.x = ey;
  var o = clamp(openness, 0, 1);
  e.lid.rotation.x = lerp(LID_SHUT, LID_OPEN, o);
  if (e.glints) {
    var vis = blinkAmt < 0.42;
    for (var i = 0; i < e.glints.length; i++) e.glints[i].visible = vis;
  }
};
Rig.prototype.applyBrow = function (b, v) {
  b.position.y = b.base.y + v * 0.014;
  b.rotation.z = b.base.z + v * 0.11;
};

/* ================================================================ EYE ======= */
/* A glossy cartoon eye: dark chocolate almond ball + sweeping skin lid
   + a lash line riding the lid rim + two specular catchlights.           */
function makeEye(o) {
  o = o || {};
  var r = o.r || 0.050;
  var sx = o.sx || 1.16, sy = o.sy || 1.00, sz = o.sz || 0.90;
  var g = new T.Group();
  var lidMat = o.lidMat;

  var ball = new T.Mesh(
    new T.SphereGeometry(r, 44, 32),
    new T.MeshPhysicalMaterial({
      map: o.tex || null, color: LC(o.tex ? 0xffffff : (o.color || 0x2B1409)),
      roughness: 0.06, metalness: 0.0, clearcoat: 1.0, clearcoatRoughness: 0.025,
      envMapIntensity: 2.4
    })
  );
  ball.scale.set(sx, sy, sz);
  g.add(ball);

  /* triple high-contrast anime catchlights */
  var glints = [];
  var gs = o.glints || [
    { x: -0.30, y: 0.36, r: 0.30, o: 1.00 },
    { x: 0.34, y: -0.24, r: 0.15, o: 0.85 },
    { x: 0.22, y: 0.38, r: 0.09, o: 0.90 }
  ];
  gs.forEach(function (c) {
    var m = new T.Mesh(
      new T.SphereGeometry(r * c.r, 14, 12),
      new T.MeshBasicMaterial({ color: LC(0xffffff), transparent: true, opacity: c.o, depthWrite: false })
    );
    m.scale.set(1, 1, 0.45);
    m.position.set(r * sx * c.x, r * sy * c.y, r * sz * 1.03);
    m.renderOrder = 3;
    g.add(m); glints.push(m);
  });

  /* upper lid — spherical cap that sweeps down over the ball */
  var lidR = r * 1.06;
  var theta = o.lidTheta !== undefined ? o.lidTheta : 0.42 * Math.PI;
  var lid = new T.Mesh(new T.SphereGeometry(lidR, 36, 22, 0, TAU, 0, theta), lidMat);
  lid.scale.set(sx, sy, sz);
  lid.rotation.x = LID_OPEN;
  g.add(lid);

  /* lash line riding the lid rim (inherits lid scale + sweep) */
  if (o.lashes !== false) {
    var lashMat = o.lashMat || new T.MeshStandardMaterial({ color: LC(o.lashColor || 0x140C08), roughness: 0.55, metalness: 0.05 });
    var lash = new T.Mesh(new T.TorusGeometry(lidR * Math.sin(theta), lidR * 0.052, 6, 56), lashMat);
    lash.rotation.x = Math.PI / 2;
    lash.position.y = lidR * Math.cos(theta);
    lid.add(lash);
  }

  /* lower lid — static, carves the almond aperture */
  var lowTheta = o.lowTheta !== undefined ? o.lowTheta : 0.30 * Math.PI;
  var low = new T.Mesh(new T.SphereGeometry(lidR, 36, 22, 0, TAU, 0, lowTheta), lidMat);
  low.scale.set(sx, sy, sz);
  low.rotation.x = Math.PI - 0.36;
  g.add(low);

  return { group: g, ball: ball, lid: lid, low: low, glints: glints, r: r };
}

/* ============================================================== MOUTH ======= */
function makeMouth(o) {
  o = o || {};
  var lipMat = o.lipMat || silkMat(0xC06A6E, 0.28);
  var g = new T.Group();
  var W = o.w || 0.052, thick = o.thick || 0.0122;

  function curve(pts) { return pts.map(function (p) { return V3(p[0], p[1], p[2]); }); }

  var upper = new T.Mesh(tubeFrom(curve([
    [-W, 0.001, 0.001], [-W * 0.52, 0.019, 0.004], [-0.012, 0.009, 0.005],
    [0, 0.014, 0.005], [0.012, 0.009, 0.005], [W * 0.52, 0.019, 0.004], [W, 0.001, 0.001]
  ]), thick, 44, 10, false), lipMat);
  var lower = new T.Mesh(tubeFrom(curve([
    [-W, 0.001, 0.001], [-W * 0.5, -0.017, 0.004], [0, -0.026, 0.005], [W * 0.5, -0.017, 0.004], [W, 0.001, 0.001]
  ]), thick * 1.06, 40, 10, false), lipMat);
  g.add(upper); g.add(lower);

  var inner = new T.Mesh(new T.SphereGeometry(0.042, 24, 18),
    new T.MeshStandardMaterial({ color: LC(o.innerColor || 0x3D1015), roughness: 0.42, metalness: 0.0 }));
  inner.scale.set(1.0, 0.16, 0.5);
  inner.position.set(0, -0.004, -0.006);
  g.add(inner);

  var teeth = new T.Mesh(roundedBox(0.046, 0.014, 0.020, 0.005, 3),
    new T.MeshPhysicalMaterial({ color: LC(0xF6F1E6), roughness: 0.22, clearcoat: 1, clearcoatRoughness: 0.1, envMapIntensity: 1.2 }));
  teeth.position.set(0, 0.006, -0.002);
  g.add(teeth);

  return { group: g, upper: upper, lower: lower, inner: inner, teeth: teeth, base: V3(0, 0, 0), teethBaseY: 0.006 };
}

/* ========================================================== HEAD BASE ======= */
/* Shared stylised head: skull, jaw, muzzle, ears, nose, blush, brows, hair bed */
function buildHead(rig, o) {
  o = o || {};
  var skin = o.skin;
  var head = rig.head;
  var rx = o.rx || CANON.headRX, ry = o.ry || CANON.headRY, rz = o.rz || CANON.headRZ;
  var R = { x: rx, y: ry, z: rz };

  var skull = new T.Mesh(new T.SphereGeometry(1, 56, 44), skin);
  skull.scale.set(rx, ry, rz);
  skull.castShadow = true;
  head.add(skull);
  rig.skull = skull;

  var jaw = new T.Mesh(new T.SphereGeometry(1, 40, 32), skin);
  jaw.scale.set(rx * 0.80, ry * 0.60, rz * 0.78);
  jaw.position.set(0, -ry * 0.52, rz * 0.10);
  head.add(jaw);

  if (o.muzzle !== false) {
    var muz = new T.Mesh(new T.SphereGeometry(1, 36, 28), skin);
    muz.scale.set(rx * 0.56, ry * 0.40, rz * 0.52);
    muz.position.set(0, -ry * 0.17, rz * 0.56);
    head.add(muz);
  }
  if (o.chin !== false) {
    var chin = new T.Mesh(new T.SphereGeometry(1, 28, 22), skin);
    chin.scale.set(rx * 0.30, ry * 0.20, rz * 0.28);
    chin.position.set(0, -ry * 0.74, rz * 0.36);
    head.add(chin);
  }
  /* ears */
  [1, -1].forEach(function (s) {
    var ear = new T.Mesh(new T.SphereGeometry(1, 24, 20), skin);
    ear.scale.set(rx * 0.16, ry * 0.42, rz * 0.30);
    ear.position.set(s * rx * 0.97, -ry * 0.06, -rz * 0.06);
    ear.rotation.z = -s * 0.16;
    head.add(ear);
    if (o.earring) head.add(o.earring(s, ear.position));
  });

  /* ---- helpers that stick a patch onto the head ellipsoid ---- */
  function onSurface(x, y, inset) {
    var k = 1 - (x / rx) * (x / rx) - (y / ry) * (y / ry);
    var z = rz * Math.sqrt(Math.max(0.0, k));
    return V3(x, y, z + (inset || 0));
  }
  function facePatch(x, y, size, mat, inset, rot) {
    var p = onSurface(x, y, inset);
    var n = V3(x / (rx * rx), y / (ry * ry), p.z / (rz * rz)).normalize();
    var m = new T.Mesh(new T.PlaneGeometry(size, size * (rot ? 1 : 1)), mat);
    m.position.copy(p);
    m.quaternion.setFromUnitVectors(V3(0, 0, 1), n);
    m.rotateZ(rot || 0);
    m.renderOrder = 2;
    head.add(m);
    return m;
  }
  rig.onSurface = onSurface;
  rig.facePatch = facePatch;

  /* ---- nose ---- */
  var noseP = onSurface(0, -ry * 0.21, -0.004);
  /* the nose catches the hottest highlight — soften that one lobe only */
  if (!rig.noseSkin) {
    rig.noseSkin = skin.clone();
    rig.noseSkin.roughness = Math.min(0.95, (skin.roughness || 0.58) + 0.16);
    if (rig.noseSkin.clearcoat !== undefined) rig.noseSkin.clearcoat = 0.12;
  }
  var nose = new T.Mesh(new T.SphereGeometry(1, 24, 20), rig.noseSkin);
  nose.scale.set(rx * 0.155, ry * 0.115, rz * 0.19);
  nose.position.copy(noseP);
  head.add(nose);
  rig.nose = nose;
  if (o.nostrils !== false) {
    [1, -1].forEach(function (s) {
      var n = new T.Mesh(new T.SphereGeometry(rx * 0.030, 12, 10),
        new T.MeshStandardMaterial({ color: LC(o.nostrilColor || 0x6B3B22), roughness: 0.6 }));
      n.scale.set(1, 0.7, 0.8);
      n.position.set(s * rx * 0.062, noseP.y - ry * 0.028, noseP.z + rz * 0.11);
      head.add(n);
    });
  }

  /* ---- blush ---- */
  if (o.blush) {
    var bt = H.radialTex(o.blushInner || 'rgba(255,138,130,0.72)', o.blushOuter || 'rgba(255,110,120,0.10)', 256, 0.30);
    var bm = new T.MeshBasicMaterial({ map: bt, transparent: true, blending: T.AdditiveBlending, depthWrite: false, opacity: o.blushOpacity === undefined ? 0.42 : o.blushOpacity });
    rig.blushL = facePatch(-rx * 0.56, -ry * 0.20, rx * 0.44, bm, 0.010);
    rig.blushR = facePatch(rx * 0.56, -ry * 0.20, rx * 0.44, bm, 0.010);
  }

  /* ---- brows ---- */
  var browMat = o.browMat || hairMat(o.browColor || 0x1A0F0A, { rough: 0.55 });
  [1, -1].forEach(function (s) {
    var p = onSurface(s * rx * 0.42, ry * 0.35, -0.002);
    var b = new T.Mesh(tubeFrom([
      V3(-0.038, -0.004, 0), V3(-0.012, 0.014, 0.004), V3(0.016, 0.016, 0.004), V3(0.040, 0.002, 0)
    ], o.browThick || 0.0088, 26, 8, false), browMat);
    b.position.copy(p);
    b.rotation.z = -s * 0.13;
    b.scale.x = s;
    b.base = { y: p.y, z: b.rotation.z };
    head.add(b);
    if (s > 0) rig.browR = b; else rig.browL = b;
  });

  return head;
}

/* ============================================================== HAIR ======== */
/* Hair shell that hugs the skull ellipsoid exactly, with an artist-controlled
   hairline (high at the front, low at the back) and volumetric tips.        */
function hairCap(o) {
  o = o || {};
  var rx = o.rx, ry = o.ry, rz = o.rz;
  var sf = o.startFront, sb = o.startBack, ef = o.endFront, eb = o.endBack;
  var gap = o.gap !== undefined ? o.gap : 0.012;
  var bulge = o.bulge !== undefined ? o.bulge : 0.05;
  var wave = o.wave !== undefined ? o.wave : 0.008;
  var crown = o.crown || 0;
  var uSeg = o.useg || 64, vSeg = o.vseg || 40;
  var dir = V3();
  return parametric(function (u, v, target) {
    var a = u * TAU;
    var f = Math.pow(Math.max(0, Math.cos(a)), 1.25);
    var s = lerp(sb, sf, f);
    var e = lerp(eb, ef, f);
    var polar = s + (e - s) * v;
    dir.set(Math.sin(a) * Math.sin(polar), Math.cos(polar), Math.cos(a) * Math.sin(polar));
    var re = 1 / Math.sqrt((dir.x / rx) * (dir.x / rx) + (dir.y / ry) * (dir.y / ry) + (dir.z / rz) * (dir.z / rz));
    /* At the front the shell hugs the skull and lands ON the hairline (no
       visor effect); volume only builds where hair hangs free at the back. */
    var hug = gap * (1 - 0.85 * v * f);
    var grow = bulge * Math.pow(v, 2.1) * (1 - 0.88 * f);
    var rr = re + hug + grow
      + wave * Math.sin(a * 5 + v * 4.2)
      + crown * Math.pow(Math.max(0, Math.cos(polar)), 3);
    target.set(dir.x * rr, dir.y * rr, dir.z * rr);
    return target;
  }, uSeg, vSeg);
}

/* a swept strand of hair (used for flyaways, braids, fringes) */
function strand(pts, r, mat) { return new T.Mesh(tubeFrom(pts, r, 40, 8, false), mat); }

/* ========================================================== HUMANOID ======== */
/* Skin skeleton + arms + neck that every humanoid character shares.
   Outfits are added afterwards by each character builder.                  */
function buildHumanoid(rig, o) {
  o = o || {};
  var skin = o.skin;
  var hipY = CANON.hipY, shY = CANON.shoulderY;

  /* ---- torso (skin base, hidden under the outfit) ---- */
  var torsoGeo = lathe([
    [0.02, hipY - 0.10], [0.155, hipY - 0.04], [0.185, hipY], [0.172, 0.94],
    [0.150, 1.02], [0.158, 1.08], [0.198, 1.19], [0.222, shY - 0.01],
    [0.150, 1.335], [0.02, 1.36]
  ], 44, true);
  torsoGeo.translate(0, -hipY, 0);
  var torso = new T.Mesh(torsoGeo, skin);
  torso.position.y = 0;
  torso.castShadow = true;
  rig.chest.position.y = hipY;   /* breathing pivots at the waist */
  rig.chestBaseY = hipY;
  rig.chest.add(torso);
  rig.torso = torso;

  /* ---- legs + feet ---- */
  if (o.legs !== false) {
    [1, -1].forEach(function (s) {
      var leg = new T.Mesh(capsule(o.legR || 0.072, 0.80, 18, 8), o.legMat || skin);
      leg.position.set(s * 0.098, 0.50, 0.005);
      leg.castShadow = true;
      rig.body.add(leg);
      var foot = new T.Mesh(roundedBox(0.105, 0.062, 0.215, 0.028, 4), o.footMat || skin);
      foot.position.set(s * 0.098, 0.040, 0.052);
      rig.body.add(foot);
    });
  }

  /* ---- neck (long enough to stay visible below the jaw) ---- */
  var neck = new T.Mesh(capsule(0.058, 0.19, 18, 8), skin);
  neck.position.set(0, 1.395, 0.006);
  rig.body.add(neck);

  /* ---- arms ---- */
  function arm(side) {
    var shoulder = new T.Group();
    shoulder.position.set(side * 0.218, shY, 0.004);
    rig.body.add(shoulder);

    var cap = new T.Mesh(new T.SphereGeometry(0.072, 24, 18), skin);
    cap.scale.set(1, 0.92, 0.95);
    shoulder.add(cap);

    var upper = new T.Mesh(capsule(o.armR || 0.050, 0.28, 18, 8), skin);
    upper.position.y = -0.15;
    upper.castShadow = true;
    shoulder.add(upper);

    var elbow = new T.Group();
    elbow.position.y = -0.285;
    shoulder.add(elbow);
    var joint = new T.Mesh(new T.SphereGeometry(0.048, 20, 16), skin);
    elbow.add(joint);

    var fore = new T.Mesh(capsule((o.armR || 0.050) * 0.86, 0.26, 18, 8), skin);
    fore.position.y = -0.14;
    fore.castShadow = true;
    elbow.add(fore);

    var hand = new T.Group();
    hand.position.y = -0.278;
    elbow.add(hand);

    var palm = new T.Mesh(roundedBox(0.068, 0.098, 0.040, 0.020, 4), skin);
    palm.position.y = -0.045;
    palm.castShadow = true;
    hand.add(palm);
    /* simple fingers */
    for (var i = 0; i < 4; i++) {
      var f = new T.Mesh(capsule(0.0105, 0.058, 10, 6), skin);
      f.position.set(-0.023 + i * 0.0155, -0.104, 0.004);
      f.rotation.x = 0.22;
      hand.add(f);
    }
    var thumb = new T.Mesh(capsule(0.0115, 0.048, 10, 6), skin);
    thumb.position.set(-side * 0.030, -0.070, 0.014);
    thumb.rotation.z = side * 0.55;
    hand.add(thumb);

    return { shoulder: shoulder, elbow: elbow, hand: hand, upper: upper, fore: fore };
  }
  rig.armR = arm(1);
  rig.armL = arm(-1);

  /* ---- head ----
     the raw skull is 0.40 x 0.43 m — on a 1.78 m figure that is a 1:4.1
     chibi ball that swallows the neck whole.  Scaling the whole head group
     (skull + face + hair cap + jewellery, all of which are its children)
     to fashion-illustration proportion (~1:5.6) and lifting it clear of the
     shoulders restores a visible neck and a reading silhouette. */
  buildHead(rig, o);
  rig.head.scale.set(1.10, 0.86, 0.90);
  rig.head.position.set(0, 1.618, 0.004);
  rig.headY0 = rig.head.position.y;
  return rig;
}

/* sculpted hand for Gia / Noor (fingers with crystal nails) */
function sculptedHand(mat, o) {
  o = o || {};
  var g = new T.Group();
  var nails = o.nails !== false;
  var palm = new T.Mesh(roundedBox(0.070, 0.092, 0.036, 0.019, 4), mat);
  palm.castShadow = true;
  g.add(palm);
  var nailMat = o.nailMat || crystalMat(0xE9F3FF);
  var fingers = [
    { x: -0.0245, len: 0.055, r: 0.0102, rot: 0.16 },
    { x: -0.0085, len: 0.062, r: 0.0108, rot: 0.10 },
    { x: 0.0085, len: 0.058, r: 0.0106, rot: 0.08 },
    { x: 0.0245, len: 0.048, r: 0.0096, rot: 0.14 }
  ];
  fingers.forEach(function (f, i) {
    var knuckle = new T.Group();
    knuckle.position.set(f.x, -0.046, 0.002);
    knuckle.rotation.x = f.rot;
    g.add(knuckle);
    var p1 = new T.Mesh(capsule(f.r, f.len * 0.55, 10, 6), mat);
    p1.position.y = -f.len * 0.275;
    knuckle.add(p1);
    var j = new T.Group(); j.position.y = -f.len * 0.55; knuckle.add(j);
    var p2 = new T.Mesh(capsule(f.r * 0.9, f.len * 0.42, 10, 6), mat);
    p2.position.y = -f.len * 0.21;
    j.add(p2);
    if (nails) {
      var nail = new T.Mesh(new T.SphereGeometry(f.r * 1.02, 14, 12), nailMat);
      nail.scale.set(0.85, 1.5, 0.42);
      nail.position.set(0, -f.len * 0.46, f.r * 0.62);
      j.add(nail);
      var cr = new T.Mesh(new T.OctahedronGeometry(f.r * 0.72, 0), o.crystalMat || crystalMat(0xDCEFFF));
      cr.scale.set(1, 0.55, 1.25);
      cr.position.set(0, -f.len * 0.47, f.r * 0.78);
      j.add(cr);
    }
  });
  var thumb = new T.Mesh(capsule(0.0118, 0.050, 10, 6), mat);
  thumb.position.set(-0.032, -0.040, 0.014);
  thumb.rotation.z = 0.62; thumb.rotation.x = -0.25;
  g.add(thumb);
  if (nails) {
    var tn = new T.Mesh(new T.OctahedronGeometry(0.0088, 0), o.crystalMat || crystalMat(0xDCEFFF));
    tn.scale.set(1.1, 0.5, 1.3);
    tn.position.set(-0.044, -0.066, 0.020);
    g.add(tn);
  }
  return g;
}

/* ========================================================= JEWELLERY ======== */
function jhumka(scale, goldTone) {
  var g = new T.Group();
  var gold = goldMat(goldTone === undefined ? 0 : goldTone);
  var s = scale || 1;
  var bell = new T.Mesh(lathe([
    [0.002, 0.030], [0.010, 0.022], [0.020, 0.008], [0.030, -0.012],
    [0.036, -0.030], [0.030, -0.040], [0.016, -0.046], [0.004, -0.047]
  ], 28, true), gold);
  bell.scale.setScalar(s);
  g.add(bell);
  var stud = new T.Mesh(new T.SphereGeometry(0.014 * s, 16, 12), gold);
  stud.position.y = 0.036 * s;
  g.add(stud);
  var ring = new T.Mesh(new T.TorusGeometry(0.014 * s, 0.0032 * s, 8, 20), gold);
  ring.position.y = 0.050 * s;
  g.add(ring);
  /* dangling pearls */
  for (var i = 0; i < 5; i++) {
    var a = (i / 5) * TAU;
    var p = new T.Mesh(new T.SphereGeometry(0.006 * s, 10, 8), pearlMat());
    p.position.set(Math.cos(a) * 0.032 * s, -0.058 * s, Math.sin(a) * 0.032 * s);
    g.add(p);
  }
  return g;
}

function choker(radius, o) {
  o = o || {};
  var g = new T.Group();
  var gold = goldMat(o.tone === undefined ? 0 : o.tone);
  var band = new T.Mesh(new T.TorusGeometry(radius, o.tube || 0.017, 14, 64), gold);
  band.rotation.x = Math.PI / 2 - 0.12;
  band.scale.z = 0.82;
  g.add(band);
  /* tiered pendant plates */
  var tiers = o.tiers || 3;
  for (var i = 0; i < tiers; i++) {
    var w = (o.w || 0.030) * (1 - i * 0.16);
    var plate = new T.Mesh(roundedBox(w * 2, 0.016, 0.008, 0.004, 3), gold);
    plate.position.set(0, -0.020 - i * 0.026, radius * 0.80 + i * 0.006);
    g.add(plate);
    if (o.gem) {
      var gem = new T.Mesh(new T.OctahedronGeometry(0.011, 0), o.gem);
      gem.scale.set(1, 1.25, 0.7);
      gem.position.set(0, -0.020 - i * 0.026, radius * 0.84 + i * 0.006);
      g.add(gem);
    }
  }
  /* beaded fringe */
  var n = o.beads || 11;
  for (var j = 0; j < n; j++) {
    var a = -0.9 + (j / (n - 1)) * 1.8;
    var b = new T.Mesh(new T.SphereGeometry(0.0068, 10, 8), gold);
    b.position.set(Math.sin(a) * radius * 0.94, -0.014 - Math.cos(a) * 0.006, Math.cos(a) * radius * 0.78);
    g.add(b);
  }
  return g;
}

/* maang tikka: forehead pendant + hair-part chain */
function maangTikka(o) {
  o = o || {};
  var g = new T.Group();
  var gold = goldMat(0);
  var chain = new T.Mesh(tubeFrom([
    V3(0, 0.150, 0.050), V3(0, 0.128, 0.068), V3(0, 0.098, 0.078), V3(0, 0.070, 0.082)
  ], 0.0042, 30, 8, false), gold);
  g.add(chain);
  var ring = new T.Mesh(new T.TorusGeometry(0.019, 0.0042, 10, 28), gold);
  ring.position.set(0, 0.062, 0.080);
  ring.rotation.x = 0.30;
  g.add(ring);
  var ruby = new T.Mesh(new T.OctahedronGeometry(0.016, 1), o.gem || crystalMat(0xC2183A));
  ruby.material = new T.MeshPhysicalMaterial({
    color: LC(0xC2183A), roughness: 0.05, metalness: 0.1, clearcoat: 1, clearcoatRoughness: 0.02,
    envMapIntensity: 2.6, emissive: LC(0x3A0210)
  });
  ruby.scale.set(0.85, 1.45, 0.85);
  ruby.position.set(0, 0.040, 0.082);
  g.add(ruby);
  var drop = new T.Mesh(new T.SphereGeometry(0.006, 10, 8), pearlMat());
  drop.position.set(0, 0.014, 0.084);
  g.add(drop);
  /* side strands */
  [1, -1].forEach(function (s) {
    var st = new T.Mesh(tubeFrom([
      V3(s * 0.012, 0.146, 0.052), V3(s * 0.055, 0.140, 0.020), V3(s * 0.086, 0.120, -0.030)
    ], 0.0030, 24, 6, false), gold);
    g.add(st);
  });
  return g;
}

/* nath: nose ring + the little chain that hooks to the hair */
function nath(o) {
  o = o || {};
  var g = new T.Group();
  var gold = goldMat(1);
  var ring = new T.Mesh(new T.TorusGeometry(o.r || 0.038, 0.0055, 10, 32), gold);
  ring.rotation.y = Math.PI / 2 - 0.35;
  g.add(ring);
  for (var i = 0; i < 5; i++) {
    var a = -0.7 + (i / 4) * 1.4;
    var p = new T.Mesh(new T.SphereGeometry(0.0042, 8, 8), pearlMat());
    p.position.set(-0.030, Math.sin(a) * 0.030, -0.006);
    g.add(p);
  }
  var chain = new T.Mesh(tubeFrom([
    V3(0.006, 0.030, -0.006), V3(0.05, 0.075, -0.010), V3(0.10, 0.115, -0.030), V3(0.135, 0.145, -0.070)
  ], 0.0028, 30, 6, false), gold);
  g.add(chain);
  return g;
}

/* gajra: ring of jasmine buds around a bun */
function gajra(radius, count, o) {
  o = o || {};
  var g = new T.Group();
  var budMat = o.budMat || new T.MeshPhysicalMaterial({
    color: LC(0xFFFBF2), roughness: 0.42, metalness: 0.0, clearcoat: 0.7,
    clearcoatRoughness: 0.4, envMapIntensity: 1.2, emissive: LC(0x2A241A)
  });
  var core = new T.MeshStandardMaterial({ color: LC(0xF2D98A), roughness: 0.6, emissive: LC(0x1A1408) });
  var strands = o.strands || 2;
  for (var s = 0; s < strands; s++) {
    for (var i = 0; i < count; i++) {
      var a = (i / count) * TAU + s * 0.16;
      var y = -s * 0.020;
      var rr = radius + s * 0.004;
      var bud = new T.Mesh(new T.SphereGeometry(0.0125, 12, 10), budMat);
      bud.scale.set(0.85, 1.25, 0.85);
      bud.position.set(Math.cos(a) * rr, y + Math.sin(a * 3) * 0.004, Math.sin(a) * rr);
      bud.rotation.z = Math.cos(a) * 0.3;
      g.add(bud);
      var c = new T.Mesh(new T.SphereGeometry(0.0055, 8, 8), core);
      c.position.copy(bud.position);
      c.position.y += 0.013;
      g.add(c);
    }
  }
  return g;
}

/* bangles */
function bangles(count, radius, o) {
  o = o || {};
  var g = new T.Group();
  for (var i = 0; i < count; i++) {
    var t = new T.Mesh(new T.TorusGeometry(radius, o.tube || 0.0075, 10, 34),
      i % 2 ? goldMat(0) : goldMat(1));
    t.rotation.x = Math.PI / 2;
    t.position.y = -i * 0.017;
    t.scale.z = 0.86;
    g.add(t);
  }
  return g;
}

/* zardozi / crystal scatter on a surface patch */
function scatterDots(count, radiusFn, dotMat, size) {
  var g = new T.Group();
  for (var i = 0; i < count; i++) {
    var a = Math.random() * TAU, r = radiusFn(i / count, Math.random());
    var d = new T.Mesh(new T.SphereGeometry(size || 0.0055, 8, 8), dotMat || goldMat(1));
    d.position.set(Math.cos(a) * r.x, r.y, Math.sin(a) * r.z);
    d.scale.set(1, 0.55, 1);
    g.add(d);
  }
  return g;
}

/* ------------------------------------------------------------------ exports */
window.__HBS.Rig = Rig;
window.__HBS.makeEye = makeEye;
window.__HBS.makeMouth = makeMouth;
window.__HBS.buildHead = buildHead;
window.__HBS.buildHumanoid = buildHumanoid;
window.__HBS.hairCap = hairCap;
window.__HBS.strand = strand;
window.__HBS.sculptedHand = sculptedHand;
window.__HBS.CANON = CANON;
window.__HBS.LID = { open: LID_OPEN, shut: LID_SHUT };
window.__HBS.jewel = {
  jhumka: jhumka, choker: choker, maangTikka: maangTikka, nath: nath,
  gajra: gajra, bangles: bangles, scatterDots: scatterDots
};
})();
