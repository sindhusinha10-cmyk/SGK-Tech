/* =====================================================================
   04 · THE FIVE CONCIERGES
   Each builder is standalone: it returns { meta, rig } and touches no
   global scene. Detach any one of them with HBStudio.buildCharacter(id).
   ===================================================================== */
(function () {
'use strict';
var U = window.__HBS, T = U.T;
var V3 = U.V3, C = U.C, LC = U.C, clamp = U.clamp, lerp = U.lerp;
var capsule = U.capsule, lathe = U.lathe, roundedBox = U.roundedBox, parametric = U.parametric,
    ribbon = U.ribbon, tubeFrom = U.tubeFrom, fluff = U.fluff, folds = U.folds, mesh = U.mesh, group = U.group;
var skinMat = U.skinMat, goldMat = U.goldMat, velvetMat = U.velvetMat, silkMat = U.silkMat,
    hairMat = U.hairMat, glossMat = U.glossMat, crystalMat = U.crystalMat, pearlMat = U.pearlMat,
    matteMat = U.matteMat, glowMat = U.glowMat;
var Rig = U.Rig, makeEye = U.makeEye, makeMouth = U.makeMouth, buildHumanoid = U.buildHumanoid,
    hairCap = U.hairCap, jewel = U.jewel, CANON = U.CANON, TAU = Math.PI * 2;

/* shared: ellipsoid radius helper for hair + drapes */
function ellR(dx, dy, dz, rx, ry, rz) {
  return 1 / Math.sqrt((dx / rx) * (dx / rx) + (dy / ry) * (dy / ry) + (dz / rz) * (dz / rz));
}

/* =====================================================================
   01 · ASHA — The Royal Bridal Stylist
   Honey-wheat skin · crimson velvet · antique gold zardozi
   ===================================================================== */
function buildAsha() {
  var rig = new Rig({ id: 'asha' });
  var SKIN = 0xBA7742;
  var skin = skinMat(SKIN, { glow: 0.13, rough: 0.56, cc: 0.32 });
  var velvet = velvetMat(0x741226, { glow: 0.10 });
  var velvetDark = velvetMat(0x4E0C1A, { glow: 0.06 });
  var brocade = silkMat(0xDCC7A4, 0.34);   /* champagne lehenga: breaks the red monolith */
  var gold = goldMat(0), goldLt = goldMat(1), goldDeep = goldMat(2);

  buildHumanoid(rig, {
    skin: skin, blush: true,
    blushInner: 'rgba(255,142,118,0.95)', blushOuter: 'rgba(238,86,104,0.20)', blushOpacity: 0.66,
    browColor: 0x1A0D07, nostrilColor: 0x7A3A1E, armR: 0.049,
    legMat: matteMat(0x5A2A16, 0.9), footMat: goldDeep,
    earring: function (s, p) {
      var j = jewel.jhumka(1.0, 0);
      j.position.set(p.x + s * 0.012, p.y - 0.062, p.z + 0.012);
      rig['jhumka' + (s > 0 ? 'R' : 'L')] = j;
      return j;
    }
  });

  var rx = CANON.headRX, ry = CANON.headRY, rz = CANON.headRZ;

  /* ---------------- eyes ---------------- */
  var eyeTex = U.eyeTex('#3A1B0B', '#7E4318', '#190903', '#1D0C04', '#DFA860');
  [1, -1].forEach(function (s) {
    var e = makeEye({
      r: 0.065, sx: 1.16, sy: 1.06, sz: 0.92, tex: eyeTex, lidMat: skin,
      lashColor: 0x150A05,
      glints: [{ x: -0.30, y: 0.34, r: 0.30, o: 1 }, { x: 0.36, y: -0.24, r: 0.125, o: 0.72 }]
    });
    e.group.position.set(s * rx * 0.45, ry * -0.05, rz * 0.82);
    e.group.rotation.y = s * 0.05;
    rig.head.add(e.group);
    rig[s > 0 ? 'eyeR' : 'eyeL'] = e;
  });

  /* ---------------- mouth ---------------- */
  var mouth = makeMouth({ lipMat: silkMat(0xC46E6C, 0.24), w: 0.050, thick: 0.0124 });
  mouth.group.position.set(0, -ry * 0.52, rz * 0.82);
  mouth.base = mouth.group.position.clone();
  rig.head.add(mouth.group);
  rig.mouth = mouth;

  /* ---------------- hair ---------------- */
  var hairCol = 0x1B1109;
  var hair = hairMat(hairCol, { rough: 0.36 });
  var cap = new T.Mesh(hairCap({
    rx: rx, ry: ry, rz: rz, gap: 0.013, bulge: 0.060, wave: 0.006, crown: 0.010,
    startFront: 0.02 * Math.PI, startBack: 0.02 * Math.PI,
    endFront: 0.250 * Math.PI, endBack: 0.92 * Math.PI
  }), hair);
  cap.castShadow = true;
  rig.head.add(cap);

  /* middle parting: two swept strands from the crown to the temples */
  [1, -1].forEach(function (s) {
    var st = new T.Mesh(tubeFrom([
      V3(s * 0.014, ry * 0.92, rz * 0.02), V3(s * 0.075, ry * 0.86, rz * 0.42),
      V3(s * 0.145, ry * 0.62, rz * 0.66), V3(s * 0.175, ry * 0.24, rz * 0.70)
    ], 0.016, 34, 10), hair);
    rig.head.add(st);
  });
  /* face-framing tendrils */
  [1, -1].forEach(function (s) {
    var t2 = new T.Mesh(tubeFrom([
      V3(s * rx * 0.80, ry * 0.62, rz * 0.52), V3(s * rx * 0.92, ry * 0.18, rz * 0.60),
      V3(s * rx * 0.86, -ry * 0.28, rz * 0.56), V3(s * rx * 0.72, -ry * 0.66, rz * 0.40)
    ], 0.0115, 34, 8), hair);
    rig.head.add(t2);
  });
  /* flyaways */
  for (var i = 0; i < 5; i++) {
    var a = -0.6 + Math.random() * 1.2;
    var fy = new T.Mesh(tubeFrom([
      V3(Math.sin(a) * 0.05, ry * 0.98, Math.cos(a) * 0.05),
      V3(Math.sin(a) * 0.13, ry * 1.16, Math.cos(a) * 0.10),
      V3(Math.sin(a) * 0.20, ry * 1.10, Math.cos(a) * 0.02)
    ], 0.0042, 20, 6), hair);
    rig.head.add(fy);
  }
  /* low bun + antique gold bun cover */
  var bun = new T.Mesh(new T.SphereGeometry(0.098, 26, 20), hair);
  bun.scale.set(1.05, 0.92, 0.92);
  bun.position.set(0, -ry * 0.10, -rz * 1.16);
  rig.head.add(bun);
  var bunRing = new T.Mesh(new T.TorusGeometry(0.082, 0.011, 10, 36), gold);
  bunRing.position.set(0, -ry * 0.10, -rz * 1.24);
  bunRing.rotation.x = 0.22;
  rig.head.add(bunRing);
  var bunPin = new T.Mesh(new T.CylinderGeometry(0.006, 0.004, 0.18, 10), gold);
  bunPin.position.set(0, -ry * 0.02, -rz * 1.06);
  bunPin.rotation.set(1.15, 0, 0.22);
  rig.head.add(bunPin);

  /* ---------------- maang tikka ---------------- */
  var tikka = jewel.maangTikka({});
  tikka.position.set(0, ry * 0.06, rz * 0.02);
  rig.head.add(tikka);
  var bindi = new T.Mesh(new T.SphereGeometry(0.011, 14, 12), new T.MeshPhysicalMaterial({
    color: LC(0xB0142E), roughness: 0.15, clearcoat: 1, clearcoatRoughness: 0.05, envMapIntensity: 1.6, emissive: LC(0x2A0008)
  }));
  bindi.scale.set(1, 1, 0.35);
  var bp = rig.onSurface(0, ry * 0.30, -0.002);
  bindi.position.copy(bp);
  rig.head.add(bindi);

  /* ---------------- lehenga (crimson velvet skirt) ---------------- */
  var skirtGeo = lathe([
    [0.03, 0.012], [0.24, 0.020], [0.40, 0.075], [0.485, 0.185], [0.525, 0.335],
    [0.522, 0.470], [0.470, 0.610], [0.375, 0.740], [0.272, 0.845], [0.222, 0.900], [0.205, 0.925]
  ], 56, true);
  folds(skirtGeo, 15, 0.020, [0.02, 0.90]);
  var skirtMat = brocade.clone(); skirtMat.side = T.DoubleSide;
  var skirt = new T.Mesh(skirtGeo, skirtMat);
  skirt.castShadow = true; skirt.receiveShadow = true;
  rig.body.add(skirt);

  /* hem zardozi borders */
  var hem1 = new T.Mesh(new T.TorusGeometry(0.522, 0.0135, 10, 72), gold);
  hem1.rotation.x = Math.PI / 2; hem1.position.y = 0.030;
  rig.body.add(hem1);
  var hem2 = new T.Mesh(new T.TorusGeometry(0.508, 0.0065, 8, 72), goldLt);
  hem2.rotation.x = Math.PI / 2; hem2.position.y = 0.072;
  rig.body.add(hem2);
  /* scattered zardozi butti on the skirt */
  var dots = jewel.scatterDots(46, function (t, r) {
    var y = 0.10 + t * 0.62;
    var rad = lerp(0.50, 0.26, t) + (r - 0.5) * 0.05;
    return { x: rad, y: y, z: rad };
  }, goldLt, 0.0072);
  rig.body.add(dots);
  for (var d = 0; d < dots.children.length; d++) {
    var ang = Math.atan2(dots.children[d].position.z, dots.children[d].position.x);
    var rr = 0.5 + 0.02 * Math.sin(ang * 15);
    dots.children[d].position.x = Math.cos(ang) * rr * 1.02;
    dots.children[d].position.z = Math.sin(ang) * rr * 1.02;
  }

  /* ---------------- choli (velvet blouse) ---------------- */
  var choliGeo = lathe([
    [0.02, 0.845], [0.192, 0.855], [0.196, 0.900], [0.176, 0.965], [0.166, 1.020],
    [0.178, 1.080], [0.212, 1.180], [0.238, 1.262], [0.196, 1.308], [0.02, 1.318]
  ], 48, true);
  var choliMat = velvetMat(0x7E1429, { glow: 0.11 });
  choliMat.side = T.DoubleSide;
  var choli = new T.Mesh(choliGeo, choliMat);
  choli.castShadow = true;
  rig.body.add(choli);

  var waistBand = new T.Mesh(new T.TorusGeometry(0.196, 0.014, 10, 48), gold);
  waistBand.rotation.x = Math.PI / 2 - 0.05; waistBand.position.y = 0.880; waistBand.scale.z = 0.9;
  rig.body.add(waistBand);
  var neckTrim = new T.Mesh(new T.TorusGeometry(0.126, 0.008, 8, 44), gold);
  neckTrim.rotation.x = Math.PI / 2 - 0.22; neckTrim.position.y = 1.296; neckTrim.scale.z = 0.78;
  rig.body.add(neckTrim);
  /* choli zardozi */
  var cDots = jewel.scatterDots(30, function (t, r) {
    return { x: 0.20, y: 0.92 + r * 0.34, z: 0.20 };
  }, goldLt, 0.0055);
  rig.body.add(cDots);
  cDots.children.forEach(function (c, i) {
    var a2 = (i / cDots.children.length) * TAU;
    var rad = 0.175 + 0.03 * Math.sin(a2 * 6);
    c.position.x = Math.cos(a2) * rad;
    c.position.z = Math.sin(a2) * rad * 0.78;
    c.position.y = 0.94 + (i % 5) * 0.070;
  });

  /* ---------------- dupatta: head veil ---------------- */
  var veilMat = silkMat(0xC9A86A, 0.30);   /* gold tissue, not crimson: no hooded silhouette */
  veilMat.side = T.DoubleSide;
  /* drape path: θ sweeps from the front hairline, up over the crown and down
     the back — so the face is never covered.                                */
  function veilPoint(u, v, target) {
    var yaw = (u - 0.5) * 2.10;
    var th = (0.455 + v * 0.765) * Math.PI;         /* 82° → 220° (front hair stays visible) */
    var st = Math.sin(th), ct = Math.cos(th);
    var dx = Math.sin(yaw) * ct, dy = st, dz = Math.cos(yaw) * ct;
    var re = ellR(dx, dy, dz, rx, ry, rz);
    var flare = 1 + 0.34 * Math.pow(v, 2.4);
    var rr = (re + 0.020 + 0.032 * Math.pow(v, 1.7)) * flare;
    var droop = 0.24 * Math.pow(v, 2.3);
    var hem = 0.024 * Math.sin(u * Math.PI * 7) * Math.pow(v, 1.7);
    target.set(dx * rr, dy * rr - droop + hem, dz * rr);
    return target;
  }
  var veil = new T.Mesh(parametric(veilPoint, 80, 50), veilMat);
  veil.castShadow = true;
  rig.head.add(veil);

  /* gold border along the veil hem */
  var borderPts = [], tmp = V3();
  for (var b = 0; b <= 72; b++) { veilPoint(b / 72, 1.0, tmp); borderPts.push(tmp.clone()); }
  var veilBorder = new T.Mesh(tubeFrom(borderPts, 0.0062, 120, 8, false), goldLt);
  rig.head.add(veilBorder);

  /* ---------------- dupatta: stole over the shoulders ---------------- */
  var stoleCurve = new T.CatmullRomCurve3([
    V3(0.215, 0.900, 0.255), V3(0.248, 1.075, 0.215), V3(0.262, 1.250, 0.075),
    V3(0.185, 1.335, -0.075), V3(0.0, 1.352, -0.150), V3(-0.185, 1.335, -0.075),
    V3(-0.262, 1.250, 0.075), V3(-0.248, 1.075, 0.215), V3(-0.215, 0.900, 0.255)
  ]);
  var stole = new T.Mesh(ribbon(stoleCurve, function (u) { return 0.30 + 0.09 * Math.sin(u * Math.PI); }, 110, 8), veilMat);
  stole.castShadow = true;
  rig.body.add(stole);
  var stoleTrim = new T.Mesh(ribbon(stoleCurve, function (u) { return 0.315 + 0.09 * Math.sin(u * Math.PI); }, 110, 3),
    (function () { var m = goldLt.clone(); m.side = T.DoubleSide; return m; })());
  stoleTrim.scale.set(1.004, 1.004, 1.004);
  rig.body.add(stoleTrim);

  /* ---------------- jewellery ---------------- */
  var neck = jewel.choker(0.108, { w: 0.026, tiers: 3, tone: 0, beads: 13, tube: 0.013 });
  neck.position.y = 1.318;
  rig.body.add(neck);
  var longHar = new T.Mesh(tubeFrom([
    V3(-0.10, 1.310, 0.085), V3(-0.075, 1.180, 0.150), V3(0.0, 1.130, 0.185),
    V3(0.075, 1.180, 0.150), V3(0.10, 1.310, 0.085)
  ], 0.0048, 40, 8), gold);
  rig.body.add(longHar);
  var pendant = new T.Mesh(new T.OctahedronGeometry(0.022, 1), new T.MeshPhysicalMaterial({
    color: LC(0xC2183A), roughness: 0.05, clearcoat: 1, envMapIntensity: 2.4, emissive: LC(0x38020E)
  }));
  pendant.scale.set(1, 1.35, 0.6); pendant.position.set(0, 1.118, 0.192);
  rig.body.add(pendant);

  [rig.armR, rig.armL].forEach(function (a) {
    var b = jewel.bangles(5, 0.045, { tube: 0.0085 });
    b.position.y = -0.268;
    a.elbow.add(b);
  });
  var ringR = new T.Mesh(new T.TorusGeometry(0.0135, 0.0035, 8, 20), gold);
  ringR.position.set(-0.024, -0.098, 0.004); ringR.rotation.x = 1.2;
  rig.armR.hand.add(ringR);

  /* ---------------- living detail ---------------- */
  rig.extra = function (t, dt) {
    var s = Math.sin(t * 1.5), s2 = Math.sin(t * 1.9 + 1);
    if (rig.jhumkaL) { rig.jhumkaL.rotation.z = 0.07 * s; rig.jhumkaL.rotation.x = 0.05 * s2; }
    if (rig.jhumkaR) { rig.jhumkaR.rotation.z = -0.07 * s; rig.jhumkaR.rotation.x = 0.05 * s2; }
  };

  return {
    id: 'asha',
    name: 'Asha',
    title: 'The Royal Bridal Stylist',
    desc: 'Signature lehengas, zardozi ateliers and the ceremonial drape — Asha walks you through the entire bridal trousseau, from first fabric to final phera.',
    tags: ['Zardozi', 'Crimson Velvet', 'Ceremony', 'Trousseau'],
    specs: [['Palette', 'Crimson · Antique Gold'], ['Signature', 'Maang Tikka & Jhumka'], ['Consultation', '45 min · By appointment']],
    swatch: ['#7A1226', '#D8BC7E'],
    frame: { fill: 0.72, el: 0.100, fov: 34 },
    rig: rig
  };
}

/* =====================================================================
   02 · MOCHI — The Luxury Haute Velvet Mascot Bunny
   Cashmere ivory plush · burgundy satin sash · emerald brooch · boba eyes
   ===================================================================== */
function buildMochi() {
  var rig = new Rig({ id: 'mochi', headY: 1.03 });
  var FUR = 0xD5D7D9;
  var furMat = velvetMat(FUR, { glow: 0.08 });
  furMat.roughness = 1.0; furMat.clearcoat = 0.20; furMat.clearcoatRoughness = 1.0;
  var furMat2 = furMat.clone();
  var pinkMat = new T.MeshPhysicalMaterial({ color: LC(0xE8929E), roughness: 0.45, clearcoat: 0.8, clearcoatRoughness: 0.3, envMapIntensity: 1.2, emissive: LC(0x3A0C12) });
  var satin = silkMat(0x5C1226, 0.24);
  var gold = goldMat(1), goldLt = goldMat(3);
  var dark = new T.MeshPhysicalMaterial({ color: LC(0x0B0B0E), roughness: 0.12, clearcoat: 1, clearcoatRoughness: 0.02, envMapIntensity: 2.6 });

  /* ---------------- body ---------------- */
  var bodyG = new T.Group();
  bodyG.position.y = 0.0;
  rig.root.add(bodyG);
  rig.bodyWrap = bodyG;

  var belly = new T.Mesh(fluff(new T.SphereGeometry(0.365, 48, 36), 0.012, 9), furMat);
  belly.scale.set(1.0, 0.98, 0.90);
  belly.position.y = 0.455;
  belly.castShadow = true; belly.receiveShadow = true;
  bodyG.add(belly);

  var chestFluff = new T.Mesh(fluff(new T.SphereGeometry(0.20, 32, 24), 0.016, 12), furMat2);
  chestFluff.position.set(0, 0.66, 0.20);
  chestFluff.scale.set(1.15, 0.95, 0.75);
  bodyG.add(chestFluff);

  /* feet */
  [1, -1].forEach(function (s) {
    var foot = new T.Mesh(fluff(new T.SphereGeometry(0.115, 26, 20), 0.008, 14), furMat);
    foot.scale.set(0.82, 0.52, 1.30);
    foot.position.set(s * 0.165, 0.062, 0.135);
    foot.castShadow = true;
    bodyG.add(foot);
    var pad = new T.Mesh(new T.SphereGeometry(0.045, 16, 14), pinkMat);
    pad.scale.set(1, 0.55, 1.25);
    pad.position.set(s * 0.165, 0.055, 0.185);
    bodyG.add(pad);
  });
  /* tail */
  var tail = new T.Mesh(fluff(new T.SphereGeometry(0.098, 28, 22), 0.026, 16), furMat2);
  tail.position.set(0, 0.44, -0.375);
  tail.castShadow = true;
  bodyG.add(tail);

  /* ---------------- head ---------------- */
  var head = rig.head;
  var hR = 0.302;
  var skull = new T.Mesh(fluff(new T.SphereGeometry(hR, 52, 40), 0.008, 11), furMat);
  skull.scale.set(1.0, 0.97, 0.95);
  skull.castShadow = true;
  head.add(skull);

  var muzzle = new T.Mesh(fluff(new T.SphereGeometry(0.125, 32, 24), 0.006, 16), furMat2);
  muzzle.scale.set(1.32, 0.86, 0.95);
  muzzle.position.set(0, -0.062, 0.222);
  head.add(muzzle);

  /* nose */
  var nose = new T.Mesh(new T.SphereGeometry(0.030, 20, 16), pinkMat);
  nose.scale.set(1.35, 0.92, 0.85);
  nose.position.set(0, -0.024, 0.322);
  head.add(nose);
  var noseHighlight = new T.Mesh(new T.SphereGeometry(0.009, 10, 8), new T.MeshBasicMaterial({ color: LC(0xffffff), transparent: true, opacity: 0.65 }));
  noseHighlight.scale.set(1, 0.7, 0.5);
  noseHighlight.position.set(-0.012, -0.012, 0.344);
  head.add(noseHighlight);

  /* mouth — bunny "w" */
  var mouthG = new T.Group();
  mouthG.position.set(0, -0.072, 0.298);
  head.add(mouthG);
  var lipCurveMat = new T.MeshStandardMaterial({ color: LC(0x4A2A22), roughness: 0.6 });
  [1, -1].forEach(function (s) {
    var w = new T.Mesh(tubeFrom([
      V3(0, 0.0, 0.004), V3(s * 0.020, -0.026, 0.006), V3(s * 0.042, -0.026, 0.004), V3(s * 0.052, -0.004, 0.0)
    ], 0.0062, 26, 8), lipCurveMat);
    mouthG.add(w);
  });
  var innerM = new T.Mesh(new T.SphereGeometry(0.030, 18, 14), new T.MeshStandardMaterial({ color: LC(0x2A0C10), roughness: 0.5 }));
  innerM.scale.set(1, 0.35, 0.4);
  innerM.position.set(0, -0.030, 0.0);
  mouthG.add(innerM);
  var teeth = new T.Mesh(roundedBox(0.034, 0.026, 0.012, 0.006, 3),
    new T.MeshPhysicalMaterial({ color: LC(0xFFFBF2), roughness: 0.22, clearcoat: 1, envMapIntensity: 1.2 }));
  teeth.position.set(0, -0.024, 0.012);
  mouthG.add(teeth);

  /* eyes — big glossy boba */
  var boba = U.eyeTex('#0A0A0D', '#1B1B22', '#000000', '#050506', '#33333E');
  [1, -1].forEach(function (s) {
    var e = makeEye({
      r: 0.088, sx: 1.02, sy: 1.08, sz: 0.98, tex: boba, lidMat: furMat, lashes: false,
      lidTheta: 0.40 * Math.PI, lowTheta: 0.26 * Math.PI,
      glints: [{ x: -0.28, y: 0.32, r: 0.24, o: 1 }, { x: 0.30, y: -0.24, r: 0.105, o: 0.8 }]
    });
    e.group.position.set(s * 0.126, -0.022, 0.246);
    rig.head.add(e.group);
    rig[s > 0 ? 'eyeR' : 'eyeL'] = e;
  });
  /* brows: tiny fur tufts */
  [1, -1].forEach(function (s) {
    var br = new T.Mesh(tubeFrom([
      V3(-0.030, -0.004, 0), V3(0, 0.012, 0.004), V3(0.030, -0.002, 0)
    ], 0.0072, 20, 8), furMat2);
    br.position.set(s * 0.120, 0.128, 0.238);
    br.rotation.z = -s * 0.18;
    br.base = { y: br.position.y, z: br.rotation.z };
    rig.head.add(br);
    rig[s > 0 ? 'browR' : 'browL'] = br;
  });

  /* blush */
  var bt = U.radialTex('rgba(255,150,160,0.95)', 'rgba(240,90,120,0.20)', 256, 0.34);
  var bmat = new T.MeshBasicMaterial({ map: bt, transparent: true, blending: T.AdditiveBlending, depthWrite: false, opacity: 0.72 });
  [1, -1].forEach(function (s) {
    var b2 = new T.Mesh(new T.PlaneGeometry(0.135, 0.115), bmat);
    b2.position.set(s * 0.176, -0.048, 0.218);
    b2.rotation.y = s * 0.55; b2.rotation.z = -s * 0.15;
    b2.renderOrder = 2;
    rig.head.add(b2);
  });

  /* ---------------- ears ---------------- */
  var earProfile = [
    [0.004, 0.0], [0.048, 0.020], [0.066, 0.085], [0.068, 0.180], [0.062, 0.275],
    [0.052, 0.360], [0.038, 0.430], [0.020, 0.478], [0.004, 0.492]
  ];
  var innerProfile = [
    [0.002, 0.030], [0.034, 0.060], [0.046, 0.130], [0.047, 0.220], [0.042, 0.300],
    [0.032, 0.370], [0.018, 0.420], [0.003, 0.436]
  ];
  var innerEarMat = new T.MeshPhysicalMaterial({
    color: LC(0xE8909C), roughness: 0.55, clearcoat: 0.5, clearcoatRoughness: 0.5,
    envMapIntensity: 1.0, emissive: LC(0x5A0E16), emissiveIntensity: 1
  });
  [1, -1].forEach(function (s) {
    var earPivot = new T.Group();
    earPivot.position.set(s * 0.106, 0.208, -0.020);
    earPivot.scale.set(1.22, 0.80, 1.0);   /* shorter + thicker: plush, not hare */
    earPivot.rotation.z = -s * 0.15;
    earPivot.rotation.x = -0.10;
    rig.head.add(earPivot);

    var ear = new T.Mesh(lathe(earProfile, 34, true), furMat);
    ear.scale.set(1, 1, 0.62);
    ear.castShadow = true;
    earPivot.add(ear);

    var inner = new T.Mesh(lathe(innerProfile, 30, true), innerEarMat);
    inner.scale.set(0.92, 0.94, 0.55);
    inner.position.z = 0.020;
    earPivot.add(inner);

    /* gold-threaded tip */
    var tip = new T.Mesh(new T.SphereGeometry(0.042, 20, 16), goldLt);
    tip.scale.set(1, 1.05, 0.66);
    tip.position.y = 0.452;
    earPivot.add(tip);
    var band = new T.Mesh(new T.TorusGeometry(0.048, 0.0065, 8, 28), goldLt);
    band.rotation.x = Math.PI / 2;
    band.position.y = 0.330;
    band.scale.z = 0.66;
    earPivot.add(band);
    var band2 = new T.Mesh(new T.TorusGeometry(0.056, 0.0050, 8, 28), gold);
    band2.rotation.x = Math.PI / 2;
    band2.position.y = 0.232;
    band2.scale.z = 0.66;
    earPivot.add(band2);

    rig[s > 0 ? 'earR' : 'earL'] = earPivot;
  });

  /* ---------------- arms (stubby plush) ---------------- */
  function arm(side) {
    var shoulder = new T.Group();
    shoulder.position.set(side * 0.315, 0.640, 0.020);
    bodyG.add(shoulder);
    var upper = new T.Mesh(capsule(0.072, 0.20, 16, 8), furMat);
    upper.position.y = -0.10;
    upper.castShadow = true;
    shoulder.add(upper);
    var elbow = new T.Group();
    elbow.position.y = -0.205;
    shoulder.add(elbow);
    var fore = new T.Mesh(capsule(0.062, 0.16, 16, 8), furMat);
    fore.position.y = -0.082;
    fore.castShadow = true;
    elbow.add(fore);
    var hand = new T.Group();
    hand.position.y = -0.170;
    elbow.add(hand);
    var paw = new T.Mesh(fluff(new T.SphereGeometry(0.072, 22, 18), 0.006, 14), furMat2);
    paw.scale.set(1, 0.86, 0.9);
    paw.position.y = -0.030;
    hand.add(paw);
    var pad = new T.Mesh(new T.SphereGeometry(0.030, 14, 12), pinkMat);
    pad.scale.set(1, 0.6, 0.9);
    pad.position.set(0, -0.040, 0.040);
    hand.add(pad);
    return { shoulder: shoulder, elbow: elbow, hand: hand };
  }
  rig.armR = arm(1);
  rig.armL = arm(-1);

  /* ---------------- sash + emerald brooch ---------------- */
  var sash = new T.Mesh(new T.TorusGeometry(0.335, 0.058, 16, 72), satin);
  sash.rotation.x = Math.PI / 2 - 0.05;
  sash.position.y = 0.505;
  sash.scale.set(1, 1, 0.88);
  sash.castShadow = true;
  bodyG.add(sash);
  var sashTrim = new T.Mesh(new T.TorusGeometry(0.335, 0.012, 8, 72), goldLt);
  sashTrim.rotation.x = Math.PI / 2 - 0.05;
  sashTrim.position.y = 0.556;
  sashTrim.scale.set(1, 1, 0.88);
  bodyG.add(sashTrim);
  var sashTrim2 = sashTrim.clone();
  sashTrim2.position.y = 0.454;
  bodyG.add(sashTrim2);

  var broochBase = new T.Mesh(new T.CylinderGeometry(0.062, 0.062, 0.018, 24), goldLt);
  broochBase.rotation.x = Math.PI / 2;
  broochBase.position.set(0, 0.505, 0.336);
  bodyG.add(broochBase);
  var emerald = new T.Mesh(new T.OctahedronGeometry(0.052, 1), new T.MeshPhysicalMaterial({
    color: LC(0x0E8C5A), roughness: 0.03, metalness: 0.05, clearcoat: 1, clearcoatRoughness: 0.02,
    envMapIntensity: 3.0, emissive: LC(0x01301C), transparent: true, opacity: 0.94
  }));
  emerald.scale.set(1, 1.25, 0.85);
  emerald.position.set(0, 0.505, 0.352);
  bodyG.add(emerald);
  for (var i = 0; i < 8; i++) {
    var a = (i / 8) * TAU;
    var prong = new T.Mesh(new T.SphereGeometry(0.009, 10, 8), goldLt);
    prong.position.set(Math.cos(a) * 0.046, 0.505 + Math.sin(a) * 0.058, 0.348);
    bodyG.add(prong);
  }

  /* ---------------- breathing on the belly ---------------- */
  rig.chest.position.y = 0.455;
  rig.chestBaseY = 0.455;
  var bellyScale = belly;
  rig.body.position.y = 0;

  /* Mochi's body doesn't use the humanoid torso: drive the belly directly */
  rig.extra = function (t, dt, p) {
    var br = Math.sin(t * 1.45) * p.breath;
    bellyScale.scale.set(1 + 0.030 * br, 1 + 0.022 * br, 1 + 0.030 * br);
    chestFluff.scale.set(1.15 + 0.03 * br, 0.95 + 0.02 * br, 0.75 + 0.02 * br);
    var sw = Math.sin(t * 1.15), sw2 = Math.sin(t * 1.5 + 0.8);
    if (rig.earL) { rig.earL.rotation.x = -0.12 + 0.16 * sw - p.bounce * 0.24 * Math.abs(Math.sin(t * 4.1)); rig.earL.rotation.z = 0.15 + 0.09 * sw2; }
    if (rig.earR) { rig.earR.rotation.x = -0.12 + 0.16 * sw2 - p.bounce * 0.24 * Math.abs(Math.sin(t * 4.1)); rig.earR.rotation.z = -0.15 - 0.09 * sw; }
    tail.position.x = Math.sin(t * 1.9) * 0.012;
    tail.rotation.z = Math.sin(t * 1.9) * 0.06;
    emerald.rotation.y = t * 0.6;
  };

  /* pose overrides — Mochi is small, so mute the arm sweeps */
  ['welcome', 'happy', 'thinking', 'hesitant', 'poise'].forEach(function (k) {
    var e = rig.emotions[k];
    for (var key in e) {
      if (key.indexOf('arm') === 0 || key.indexOf('elbow') === 0) e[key] *= 0.72;
    }
  });

  return {
    id: 'mochi',
    name: 'Mochi',
    title: 'The Haute Velvet Mascot',
    desc: 'The atelier’s plush concierge. Mochi greets first-time visitors, hands out swatch books and softens every consultation with a wag of an ear.',
    tags: ['Cashmere Plush', 'Burgundy Satin', 'Welcome Ritual'],
    specs: [['Palette', 'Ivory · Burgundy · Emerald'], ['Signature', 'Gold-threaded ears'], ['Consultation', 'Always on duty']],
    swatch: ['#E8D8C4', '#C86E86'],
    frame: { fill: 0.64, el: 0.055, fov: 34 },
    rig: rig
  };
}

/* =====================================================================
   03 · NOOR — The Modern Parisian / Indo-Western Glamour Artist
   Porcelain skin · obsidian blazer · satin lapels · glowing blending brush
   ===================================================================== */
function buildNoor() {
  var rig = new Rig({ id: 'noor' });
  var SKIN = 0xE4C0A6;
  var skin = skinMat(SKIN, { glow: 0.14, rough: 0.48, cc: 0.42 });
  var obsidian = new T.MeshPhysicalMaterial({ color: LC(0x0C0C10), roughness: 0.58, metalness: 0.08, clearcoat: 0.55, clearcoatRoughness: 0.42, envMapIntensity: 1.0 });
  var satinLapel = silkMat(0x17171E, 0.16);
  var shirtMat = silkMat(0x08080A, 0.30);
  var gold = goldMat(0), goldLt = goldMat(3);

  buildHumanoid(rig, {
    skin: skin, blush: true, blushOpacity: 0.34,
    blushInner: 'rgba(226,140,130,0.85)', blushOuter: 'rgba(214,90,100,0.10)',
    browColor: 0x141118, nostrilColor: 0x8A6A58, armR: 0.047,
    rx: 0.196, ry: 0.214, rz: 0.192,
    legMat: obsidian, footMat: new T.MeshPhysicalMaterial({ color: LC(0x101014), roughness: 0.25, clearcoat: 1, envMapIntensity: 1.6 }),
    earring: function (s, p) {
      var g = new T.Group();
      var hoop = new T.Mesh(new T.TorusGeometry(0.026, 0.0042, 8, 28), goldLt);
      hoop.rotation.y = Math.PI / 2;
      g.add(hoop);
      var drop = new T.Mesh(new T.SphereGeometry(0.008, 12, 10), goldLt);
      drop.position.y = -0.030;
      g.add(drop);
      g.position.set(p.x + s * 0.006, p.y - 0.030, p.z + 0.004);
      return g;
    }
  });
  var rx = 0.196, ry = 0.214, rz = 0.192;

  /* ---------------- eyes ---------------- */
  var eyeTex = U.eyeTex('#2A1A12', '#4E2C18', '#0A0503', '#160C06', '#B98550');
  [1, -1].forEach(function (s) {
    var e = makeEye({
      r: 0.061, sx: 1.22, sy: 1.05, sz: 0.90, tex: eyeTex, lidMat: skin,
      lashColor: 0x0E0B0A, lidTheta: 0.40 * Math.PI,
      glints: [{ x: -0.32, y: 0.32, r: 0.26, o: 1 }, { x: 0.34, y: -0.22, r: 0.11, o: 0.7 }]
    });
    e.group.position.set(s * rx * 0.46, ry * -0.04, rz * 0.82);
    e.group.rotation.y = s * 0.05;
    rig.head.add(e.group);
    rig[s > 0 ? 'eyeR' : 'eyeL'] = e;
  });

  /* ---------------- winged liner ---------------- */
  [1, -1].forEach(function (s) {
    var sh = new T.Shape();
    sh.moveTo(-0.030, 0.004);
    sh.quadraticCurveTo(0.004, 0.026, 0.042, 0.046);
    sh.quadraticCurveTo(0.014, 0.018, -0.022, -0.008);
    sh.quadraticCurveTo(-0.030, -0.004, -0.030, 0.004);
    var g = new T.ShapeGeometry(sh, 24);
    var pos = g.attributes.position;
    for (var i = 0; i < pos.count; i++) {
      var x = pos.getX(i), y = pos.getY(i);
      pos.setZ(i, -0.014 * (x * x) * 8);
    }
    g.computeVertexNormals();
    var liner = new T.Mesh(g, new T.MeshPhysicalMaterial({ color: LC(0x08080A), roughness: 0.12, clearcoat: 1, clearcoatRoughness: 0.05, envMapIntensity: 1.8, side: T.DoubleSide }));
    var p = rig.onSurface(s * rx * 0.52, ry * 0.16, 0.004);
    liner.position.copy(p);
    liner.rotation.y = s * 0.30;
    liner.scale.x = s;
    rig.head.add(liner);

    /* lower lash flick */
    var sh2 = new T.Shape();
    sh2.moveTo(-0.024, -0.004);
    sh2.quadraticCurveTo(0.010, -0.016, 0.034, -0.004);
    sh2.quadraticCurveTo(0.006, -0.010, -0.024, -0.004);
    var l2 = new T.Mesh(new T.ShapeGeometry(sh2, 16), liner.material);
    l2.position.copy(p);
    l2.position.y -= 0.062;
    l2.rotation.y = s * 0.30;
    l2.scale.x = s;
    rig.head.add(l2);
  });

  /* ---------------- contour streak ---------------- */
  var contTex = U.radialTex('rgba(150,84,66,0.85)', 'rgba(140,70,60,0.06)', 256, 0.32);
  var contMat = new T.MeshBasicMaterial({ map: contTex, transparent: true, blending: T.AdditiveBlending, depthWrite: false, opacity: 0.42 });
  [1, -1].forEach(function (s) {
    var c = rig.facePatch(s * rx * 0.72, -ry * 0.20, rx * 0.92, contMat, -0.003, s * -0.85);
    c.scale.set(0.52, 1.5, 1);
  });

  /* ---------------- lips (crimson) ---------------- */
  var mouth = makeMouth({ lipMat: silkMat(0xB01B2E, 0.18), w: 0.050, thick: 0.0132 });
  mouth.group.position.set(0, -ry * 0.52, rz * 0.82);
  mouth.base = mouth.group.position.clone();
  rig.head.add(mouth.group);
  rig.mouth = mouth;

  /* ---------------- sleek bob ---------------- */
  var hairCol = 0x0D0A0C;
  var hair = hairMat(hairCol, { rough: 0.24 });
  var cap = new T.Mesh(hairCap({
    rx: rx, ry: ry, rz: rz, gap: 0.011, bulge: 0.090, wave: 0.0035, crown: 0.008,
    startFront: 0.02 * Math.PI, startBack: 0.02 * Math.PI,
    endFront: 0.252 * Math.PI, endBack: 0.70 * Math.PI, useg: 72, vseg: 44
  }), hair);
  cap.castShadow = true;
  rig.head.add(cap);

  /* blunt fringe with a slightly uneven edge */
  var fringe = new T.Mesh(parametric(function (u, v, target) {
    var a = (u - 0.5) * 1.95;
    var edge = 0.235 * Math.PI + 0.022 * Math.PI * Math.sin(u * Math.PI * 3.2) + 0.014 * Math.PI * Math.sin(u * Math.PI * 7);
    var polar = 0.04 * Math.PI + v * (edge - 0.04 * Math.PI);
    var sp = Math.sin(polar), cp = Math.cos(polar);
    var dx = Math.sin(a) * sp, dy = cp, dz = Math.cos(a) * sp;
    var re = ellR(dx, dy, dz, rx, ry, rz);
    var rr = re + 0.014 + 0.010 * v;
    target.set(dx * rr, dy * rr, dz * rr);
    return target;
  }, 64, 26), hair);
  fringe.castShadow = true;
  rig.head.add(fringe);

  /* side-swept sleek strands hugging the cheeks */
  [1, -1].forEach(function (s) {
    var st = new T.Mesh(tubeFrom([
      V3(s * rx * 0.86, ry * 0.72, rz * 0.42), V3(s * rx * 0.98, ry * 0.30, rz * 0.56),
      V3(s * rx * 0.92, -ry * 0.22, rz * 0.58), V3(s * rx * 0.80, -ry * 0.58, rz * 0.44)
    ], 0.0135, 36, 10), hair);
    rig.head.add(st);
  });

  /* ---------------- obsidian blazer ---------------- */
  var blazer = new T.Mesh(roundedBox(0.46, 0.56, 0.29, 0.10, 6), obsidian);
  blazer.position.set(0, 1.10, 0.006);
  blazer.castShadow = true; blazer.receiveShadow = true;
  rig.body.add(blazer);

  var collar = new T.Mesh(lathe([
    [0.005, 0.0], [0.150, 0.005], [0.160, 0.045], [0.128, 0.090], [0.140, 0.130], [0.020, 0.140]
  ], 40, true), obsidian);
  collar.position.y = 1.285;
  collar.scale.z = 0.86;
  rig.body.add(collar);

  /* satin lapels — ruled surfaces following the chest */
  [1, -1].forEach(function (s) {
    var lapel = new T.Mesh(parametric(function (u, v, target) {
      var p0 = V3(s * 0.050, 1.320, 0.128);
      var p1 = V3(s * 0.108, 1.045, 0.150);
      var p2 = V3(s * 0.190, 1.262, 0.070);
      var p3 = V3(s * 0.118, 1.010, 0.118);
      var a = V3().lerpVectors(p0, p1, u), b = V3().lerpVectors(p2, p3, u);
      target.lerpVectors(a, b, v);
      target.z += 0.014 * Math.sin(v * Math.PI) + 0.006;
      target.x += s * 0.006 * Math.sin(v * Math.PI);
      return target;
    }, 22, 14), satinLapel);
    lapel.castShadow = true;
    rig.body.add(lapel);
  });
  /* shirt insert (deep V) */
  var vShape = new T.Shape();
  vShape.moveTo(-0.055, 1.330); vShape.lineTo(0.055, 1.330);
  vShape.lineTo(0.010, 1.030); vShape.lineTo(-0.010, 1.030); vShape.lineTo(-0.055, 1.330);
  var shirt = new T.Mesh(new T.ShapeGeometry(vShape), shirtMat);
  shirt.position.z = 0.128;
  rig.body.add(shirt);

  /* shoulders + sleeves */
  [1, -1].forEach(function (s) {
    var sh = new T.Mesh(new T.SphereGeometry(0.088, 24, 18), obsidian);
    sh.scale.set(1, 0.92, 0.98);
    sh.position.set(s * 0.212, 1.268, 0.006);
    sh.castShadow = true;
    rig.body.add(sh);
    var sl = new T.Mesh(capsule(0.070, 0.30, 18, 8), obsidian);
    sl.position.y = -0.16;
    sl.rotation.z = s * 0.05;
    sl.castShadow = true;
    rig[s > 0 ? 'armR' : 'armL'].shoulder.add(sl);
  });

  /* gold chain + pendant */
  var chain = new T.Mesh(tubeFrom([
    V3(-0.085, 1.318, 0.090), V3(-0.055, 1.268, 0.128), V3(0, 1.250, 0.140),
    V3(0.055, 1.268, 0.128), V3(0.085, 1.318, 0.090)
  ], 0.0040, 40, 8), goldLt);
  rig.body.add(chain);
  var charm = new T.Mesh(new T.TorusGeometry(0.013, 0.004, 8, 22), goldLt);
  charm.position.set(0, 1.238, 0.142);
  rig.body.add(charm);

  /* ---------------- glowing blending brush ---------------- */
  var brush = new T.Group();
  var handle = new T.Mesh(new T.CylinderGeometry(0.0135, 0.0115, 0.155, 18), goldLt);
  handle.position.y = -0.030;
  brush.add(handle);
  var ferrule = new T.Mesh(new T.CylinderGeometry(0.0155, 0.0155, 0.038, 18), goldMat(0));
  ferrule.position.y = 0.064;
  brush.add(ferrule);
  var bristleGeo = lathe([
    [0.001, 0.0], [0.014, 0.010], [0.017, 0.040], [0.0145, 0.075], [0.008, 0.100], [0.001, 0.108]
  ], 22, true);
  var bristleMat = new T.MeshPhysicalMaterial({
    color: LC(0xF3E6D2), roughness: 0.72, metalness: 0.0, clearcoat: 0.35,
    emissive: LC(0xC8A96A), emissiveIntensity: 0.0, envMapIntensity: 1.1
  });
  var bristles = new T.Mesh(bristleGeo, bristleMat);
  bristles.position.y = 0.082;
  brush.add(bristles);
  var brushGlow = new T.PointLight(LC(0xFFD9A0), 0.0, 1.4, 2);
  brushGlow.position.set(0, 0.14, 0);
  brush.add(brushGlow);
  var halo = new T.Mesh(new T.SphereGeometry(0.035, 16, 14), new T.MeshBasicMaterial({
    color: LC(0xFFDCA8), transparent: true, opacity: 0.0, blending: T.AdditiveBlending, depthWrite: false
  }));
  halo.position.y = 0.135;
  brush.add(halo);
  brush.position.set(0, -0.090, 0.030);
  brush.rotation.set(-0.35, 0, 0.22);
  rig.armR.hand.add(brush);
  rig.brush = brush; rig.brushGlow = brushGlow; rig.bristles = bristles; rig.halo = halo;

  /* trouser crease highlight */
  [1, -1].forEach(function (s) {
    var crease = new T.Mesh(new T.BoxGeometry(0.006, 0.62, 0.004), new T.MeshBasicMaterial({ color: LC(0x2A2A34) }));
    crease.position.set(s * 0.098, 0.52, 0.078);
    rig.body.add(crease);
  });

  rig.extra = function (t, dt, p) {
    var g = p.glow * (0.75 + 0.25 * Math.sin(t * 2.2));
    bristleMat.emissiveIntensity = g * 1.5;
    brushGlow.intensity = g * 1.5;
    halo.material.opacity = g * 0.32;
    halo.scale.setScalar(1 + 0.12 * Math.sin(t * 2.2));
  };

  return {
    id: 'noor',
    name: 'Noor',
    title: 'The Indo-Western Glamour Artist',
    desc: 'Parisian contour, razor winged liner, red-carpet finish. Noor builds the modern reception look — and blends it until the light obeys her.',
    tags: ['Contour', 'Satin Lapel', 'Editorial', 'Reception Glam'],
    specs: [['Palette', 'Obsidian · Champagne'], ['Signature', 'Gilded blending brush'], ['Consultation', '60 min · Trial + Look']],
    swatch: ['#101014', '#E2CFA0'],
    frame: { fill: 0.72, el: 0.095, fov: 34 },
    rig: rig
  };
}

/* =====================================================================
   04 · TARA — The Sacred Heritage Saree Drape & Henna Guru
   Emerald + marigold silk · temple choker · nath · jasmine gajra bun
   ===================================================================== */
function buildTara() {
  var rig = new Rig({ id: 'tara' });
  var SKIN = 0xB87F4C;
  var skin = skinMat(SKIN, { glow: 0.13, rough: 0.58, cc: 0.30 });
  var emerald = silkMat(0x11604A, 0.30);
  var emeraldDeep = silkMat(0x0A3C30, 0.34);
  var marigold = silkMat(0xE8A03C, 0.26);
  var gold = goldMat(0), goldLt = goldMat(1), goldAntique = goldMat(2);
  var gemMat = new T.MeshPhysicalMaterial({ color: LC(0x0E8C5A), roughness: 0.04, clearcoat: 1, envMapIntensity: 2.6, emissive: LC(0x02281A) });

  buildHumanoid(rig, {
    skin: skin, blush: true, blushOpacity: 0.48,
    blushInner: 'rgba(255,150,120,0.85)', blushOuter: 'rgba(232,110,90,0.14)',
    browColor: 0x1A0F08, nostrilColor: 0x6E3A1E, armR: 0.050,
    legMat: skinMat(SKIN, { glow: 0.10 }), footMat: goldAntique,
    earring: function (s, p) {
      var j = jewel.jhumka(0.92, 2);
      j.position.set(p.x + s * 0.010, p.y - 0.058, p.z + 0.010);
      rig['jhumka' + (s > 0 ? 'R' : 'L')] = j;
      return j;
    }
  });
  var rx = CANON.headRX, ry = CANON.headRY, rz = CANON.headRZ;

  /* ---------------- eyes ---------------- */
  var eyeTex = U.eyeTex('#2E1608', '#6B3A16', '#150702', '#1A0B03', '#D09A55');
  [1, -1].forEach(function (s) {
    var e = makeEye({
      r: 0.064, sx: 1.18, sy: 1.06, sz: 0.92, tex: eyeTex, lidMat: skin,
      lashColor: 0x160B05,
      glints: [{ x: -0.30, y: 0.34, r: 0.29, o: 1 }, { x: 0.35, y: -0.23, r: 0.12, o: 0.72 }]
    });
    e.group.position.set(s * rx * 0.45, ry * -0.05, rz * 0.82);
    e.group.rotation.y = s * 0.05;
    rig.head.add(e.group);
    rig[s > 0 ? 'eyeR' : 'eyeL'] = e;
  });

  /* kohl waterline (a soft dark rim under the eye) */
  [1, -1].forEach(function (s) {
    var kohl = new T.Mesh(new T.TorusGeometry(0.030, 0.0042, 8, 30, Math.PI * 0.9), new T.MeshStandardMaterial({ color: LC(0x1A0E08), roughness: 0.7 }));
    kohl.rotation.set(Math.PI / 2 - 0.25, 0, Math.PI * 0.05);
    var p = rig.onSurface(s * rx * 0.42, ry * 0.02, 0.004);
    kohl.position.copy(p);
    kohl.position.y -= 0.050;
    rig.head.add(kohl);
  });

  /* ---------------- mouth ---------------- */
  var mouth = makeMouth({ lipMat: silkMat(0xB54A4E, 0.24), w: 0.050, thick: 0.0126 });
  mouth.group.position.set(0, -ry * 0.52, rz * 0.82);
  mouth.base = mouth.group.position.clone();
  rig.head.add(mouth.group);
  rig.mouth = mouth;

  /* ---------------- hair: pulled back + braided bun ---------------- */
  var hairCol = 0x140C08;
  var hair = hairMat(hairCol, { rough: 0.34 });
  var cap = new T.Mesh(hairCap({
    rx: rx, ry: ry, rz: rz, gap: 0.009, bulge: 0.020, wave: 0.002, crown: 0.004,
    startFront: 0.02 * Math.PI, startBack: 0.02 * Math.PI,
    endFront: 0.248 * Math.PI, endBack: 0.72 * Math.PI
  }), hair);
  cap.castShadow = true;
  rig.head.add(cap);
  /* centre parting strand */
  var part = new T.Mesh(tubeFrom([
    V3(0, ry * 0.95, rz * 0.10), V3(0, ry * 0.90, rz * 0.30), V3(0, ry * 0.80, rz * 0.52)
  ], 0.008, 20, 8), hair);
  rig.head.add(part);

  /* bun */
  var bun = new T.Mesh(new T.SphereGeometry(0.108, 28, 22), hair);
  bun.scale.set(1.06, 0.94, 0.94);
  bun.position.set(0, ry * 0.02, -rz * 1.10);
  bun.castShadow = true;
  rig.head.add(bun);
  /* braided plait wrapping down the back */
  var braidPts = [];
  for (var i = 0; i <= 28; i++) {
    var u = i / 28;
    braidPts.push(V3(
      Math.sin(u * 9.5) * 0.036 * (1 - u * 0.4),
      ry * 0.02 - u * 0.62,
      -rz * 1.06 - u * 0.06 + Math.sin(u * 9.5) * 0.008
    ));
  }
  var braid = new T.Mesh(tubeFrom(braidPts, 0.026, 90, 10), hair);
  braid.castShadow = true;
  rig.head.add(braid);
  for (var j = 0; j < 7; j++) {
    var u2 = 0.10 + j * 0.12;
    var ring = new T.Mesh(new T.TorusGeometry(0.028, 0.005, 8, 22), goldLt);
    var pt = braidPts[Math.round(u2 * 28)];
    ring.position.copy(pt);
    ring.rotation.x = Math.PI / 2 + 0.2;
    rig.head.add(ring);
  }
  /* gajra around the bun */
  var gajra = jewel.gajra(0.118, 16, { strands: 2 });
  gajra.position.copy(bun.position);
  rig.head.add(gajra);
  /* jasmine strands hanging beside the face */
  [1, -1].forEach(function (s) {
    var st = new T.Mesh(tubeFrom([
      V3(s * rx * 0.70, ry * 0.55, -rz * 0.10), V3(s * rx * 0.86, ry * 0.20, -rz * 0.30),
      V3(s * rx * 0.80, -ry * 0.16, -rz * 0.55)
    ], 0.0075, 26, 6), hair);
    rig.head.add(st);
    for (var k = 0; k < 4; k++) {
      var u3 = 0.25 + k * 0.22;
      var bud = new T.Mesh(new T.SphereGeometry(0.011, 10, 8), new T.MeshPhysicalMaterial({
        color: LC(0xFFFBF0), roughness: 0.4, clearcoat: 0.7, envMapIntensity: 1.2, emissive: LC(0x2A2418)
      }));
      bud.scale.set(0.85, 1.2, 0.85);
      bud.position.set(s * rx * (0.78 + 0.06 * Math.sin(k)), ry * 0.30 - k * 0.10, -rz * (0.20 + k * 0.10));
      rig.head.add(bud);
    }
  });

  /* ---------------- bindi + tilak ---------------- */
  var bindi = new T.Mesh(new T.SphereGeometry(0.013, 16, 14), new T.MeshPhysicalMaterial({
    color: LC(0xB0142E), roughness: 0.1, clearcoat: 1, clearcoatRoughness: 0.03, envMapIntensity: 2.0, emissive: LC(0x36000E)
  }));
  bindi.scale.set(1, 1, 0.30);
  var bp = rig.onSurface(0, ry * 0.30, -0.002);
  bindi.position.copy(bp);
  rig.head.add(bindi);
  var tilak = new T.Mesh(new T.BoxGeometry(0.006, 0.055, 0.002), new T.MeshBasicMaterial({ color: LC(0xC2183A), transparent: true, opacity: 0.85 }));
  tilak.position.copy(bp);
  tilak.position.y += 0.052;
  tilak.rotation.z = 0.0;
  rig.head.add(tilak);

  /* ---------------- saree (emerald silk skirt) ---------------- */
  var sareeTex = (function () {
    var c = document.createElement('canvas'); c.width = 512; c.height = 128;
    var g = c.getContext('2d');
    g.fillStyle = '#11604A'; g.fillRect(0, 0, 512, 128);
    var grd = g.createLinearGradient(0, 0, 0, 128);
    grd.addColorStop(0, 'rgba(232,160,60,0.95)');
    grd.addColorStop(0.13, 'rgba(232,160,60,0.85)');
    grd.addColorStop(0.20, 'rgba(232,160,60,0)');
    grd.addColorStop(0.80, 'rgba(232,160,60,0)');
    grd.addColorStop(0.90, 'rgba(232,160,60,0.85)');
    grd.addColorStop(1, 'rgba(232,160,60,0.95)');
    g.fillStyle = grd; g.fillRect(0, 0, 512, 128);
    g.fillStyle = 'rgba(240,200,110,0.9)';
    for (var i = 0; i < 40; i++) {
      var x = (i * 97) % 512, y = 20 + ((i * 53) % 88);
      g.beginPath(); g.arc(x, y, 2.6, 0, TAU); g.fill();
      g.beginPath(); g.arc(x + 3, y + 3, 1.4, 0, TAU); g.fill();
    }
    var t = new T.CanvasTexture(c);
    t.encoding = T.sRGBEncoding; t.wrapS = t.wrapT = T.RepeatWrapping;
    t.repeat.set(3, 1);
    return t;
  })();
  var sareeMat = silkMat(0xffffff, 0.30);
  sareeMat.map = sareeTex;
  sareeMat.side = T.DoubleSide;

  var sareeGeo = lathe([
    [0.03, 0.012], [0.22, 0.020], [0.36, 0.080], [0.44, 0.190], [0.478, 0.330],
    [0.470, 0.470], [0.415, 0.620], [0.320, 0.760], [0.250, 0.855], [0.215, 0.905]
  ], 56, true);
  folds(sareeGeo, 18, 0.026, [0.02, 0.90]);
  var saree = new T.Mesh(sareeGeo, sareeMat);
  saree.castShadow = true; saree.receiveShadow = true;
  rig.body.add(saree);

  /* pleat fan at the waist front */
  var pleat = new T.Mesh(parametric(function (u, v, target) {
    var x = (u - 0.5) * 0.30;
    var y = 0.90 - v * 0.34;
    var z = 0.20 - v * 0.13 + 0.022 * Math.sin(u * Math.PI * 9);
    target.set(x, y, z);
    return target;
  }, 40, 20), sareeMat);
  rig.body.add(pleat);
  for (var pf = 0; pf < 9; pf++) {
    var px = -0.135 + pf * 0.0337;
    var fold = new T.Mesh(new T.BoxGeometry(0.004, 0.30, 0.006), marigold);
    fold.position.set(px, 0.745, 0.148 - 0.10);
    fold.rotation.x = -0.28;
    rig.body.add(fold);
  }

  /* hem + waist borders */
  var hem = new T.Mesh(new T.TorusGeometry(0.474, 0.0125, 10, 72), marigold);
  hem.rotation.x = Math.PI / 2; hem.position.y = 0.028;
  rig.body.add(hem);
  var kamar = new T.Mesh(new T.TorusGeometry(0.212, 0.016, 12, 52), gold);
  kamar.rotation.x = Math.PI / 2 - 0.04; kamar.position.y = 0.898; kamar.scale.z = 0.88;
  rig.body.add(kamar);
  var kamarPendant = new T.Mesh(new T.OctahedronGeometry(0.020, 1), gemMat);
  kamarPendant.scale.set(1, 1.2, 0.6);
  kamarPendant.position.set(0, 0.878, 0.196);
  rig.body.add(kamarPendant);

  /* ---------------- blouse ---------------- */
  var blouseGeo = lathe([
    [0.02, 0.845], [0.190, 0.855], [0.194, 0.900], [0.174, 0.965], [0.164, 1.020],
    [0.176, 1.080], [0.210, 1.175], [0.232, 1.250], [0.180, 1.292], [0.02, 1.302]
  ], 46, true);
  var blouseMat = silkMat(0x0E5E48, 0.28);
  blouseMat.side = T.DoubleSide;
  var blouse = new T.Mesh(blouseGeo, blouseMat);
  blouse.castShadow = true;
  rig.body.add(blouse);
  var bTrim = new T.Mesh(new T.TorusGeometry(0.128, 0.0075, 8, 44), marigold);
  bTrim.rotation.x = Math.PI / 2 - 0.20; bTrim.position.y = 1.282; bTrim.scale.z = 0.76;
  rig.body.add(bTrim);
  var bTrim2 = new T.Mesh(new T.TorusGeometry(0.192, 0.0075, 8, 48), marigold);
  bTrim2.rotation.x = Math.PI / 2 - 0.04; bTrim2.position.y = 0.872; bTrim2.scale.z = 0.9;
  rig.body.add(bTrim2);
  /* elbow-length sleeves */
  [1, -1].forEach(function (s) {
    var sl = new T.Mesh(capsule(0.062, 0.20, 16, 8), blouseMat);
    sl.position.y = -0.105;
    sl.castShadow = true;
    rig[s > 0 ? 'armR' : 'armL'].shoulder.add(sl);
    var cuff = new T.Mesh(new T.TorusGeometry(0.060, 0.007, 8, 26), marigold);
    cuff.rotation.x = Math.PI / 2; cuff.position.y = -0.205;
    rig[s > 0 ? 'armR' : 'armL'].shoulder.add(cuff);
  });

  /* ---------------- pallu (draped over the left shoulder) ---------------- */
  var palluCurve = new T.CatmullRomCurve3([
    V3(0.150, 0.870, 0.260), V3(0.205, 1.010, 0.225), V3(0.250, 1.180, 0.120),
    V3(0.235, 1.320, -0.020), V3(0.110, 1.372, -0.130), V3(-0.050, 1.372, -0.168),
    V3(-0.190, 1.300, -0.190), V3(-0.245, 1.120, -0.185), V3(-0.250, 0.930, -0.150),
    V3(-0.235, 0.760, -0.105)
  ]);
  var palluMat = silkMat(0xffffff, 0.28);
  palluMat.map = sareeTex.clone();
  palluMat.map.repeat.set(1.6, 1);
  palluMat.map.needsUpdate = true;
  palluMat.side = T.DoubleSide;
  var pallu = new T.Mesh(ribbon(palluCurve, function (u) { return 0.32 + 0.10 * Math.sin(u * Math.PI * 0.9); }, 120, 8), palluMat);
  pallu.castShadow = true;
  rig.body.add(pallu);
  /* gold edge beads along the pallu */
  for (var pb = 0; pb <= 34; pb++) {
    var pu = pb / 34;
    var pp = palluCurve.getPointAt(pu);
    var bead = new T.Mesh(new T.SphereGeometry(0.0068, 10, 8), goldLt);
    bead.position.copy(pp);
    bead.position.x += (pu - 0.5) * 0.20;
    bead.position.z += 0.02;
    rig.body.add(bead);
  }

  /* ---------------- temple jewellery ---------------- */
  var chokerN = jewel.choker(0.112, { w: 0.032, tiers: 3, tone: 0, beads: 15, tube: 0.014, gem: gemMat });
  chokerN.position.y = 1.300;
  rig.body.add(chokerN);
  var haar = new T.Mesh(tubeFrom([
    V3(-0.098, 1.292, 0.090), V3(-0.070, 1.170, 0.150), V3(0, 1.128, 0.176),
    V3(0.070, 1.170, 0.150), V3(0.098, 1.292, 0.090)
  ], 0.0050, 44, 8), gold);
  rig.body.add(haar);
  var locket = new T.Mesh(lathe([
    [0.001, 0.0], [0.020, 0.004], [0.026, 0.014], [0.020, 0.024], [0.008, 0.030], [0.001, 0.032]
  ], 24, true), gold);
  locket.rotation.x = Math.PI;
  locket.position.set(0, 1.140, 0.178);
  rig.body.add(locket);
  var locketGem = new T.Mesh(new T.OctahedronGeometry(0.013, 0), gemMat);
  locketGem.scale.set(1, 1.2, 0.6);
  locketGem.position.set(0, 1.126, 0.186);
  rig.body.add(locketGem);

  /* nath (nose ring + chain) */
  var nath = jewel.nath({ r: 0.034 });
  nath.position.set(0.026, -0.052, 0.182);
  nath.rotation.y = -0.35;
  rig.head.add(nath);

  /* bangles */
  [rig.armR, rig.armL].forEach(function (a) {
    var g1 = jewel.bangles(3, 0.048, { tube: 0.008 });
    g1.position.y = -0.268;
    a.elbow.add(g1);
    var glass = new T.Mesh(new T.TorusGeometry(0.048, 0.009, 10, 34), new T.MeshPhysicalMaterial({
      color: LC(0x0E7A52), roughness: 0.08, clearcoat: 1, envMapIntensity: 2.2, transparent: true, opacity: 0.9
    }));
    glass.rotation.x = Math.PI / 2; glass.position.y = -0.226; glass.scale.z = 0.88;
    a.elbow.add(glass);
  });

  /* mehndi on the hands */
  var hennaMat = new T.MeshStandardMaterial({ color: LC(0x7A3A1E), roughness: 0.75, transparent: true, opacity: 0.85 });
  [rig.armR, rig.armL].forEach(function (a) {
    var h1 = new T.Mesh(new T.SphereGeometry(0.038, 20, 16), hennaMat);
    h1.scale.set(1, 1.25, 0.32);
    h1.position.set(0, -0.048, -0.020);
    a.hand.add(h1);
    for (var d = 0; d < 7; d++) {
      var dot = new T.Mesh(new T.SphereGeometry(0.0055, 8, 8), hennaMat);
      var ang = (d / 7) * TAU;
      dot.position.set(Math.cos(ang) * 0.026, -0.070 + Math.sin(ang) * 0.018, 0.018);
      a.hand.add(dot);
    }
  });

  rig.extra = function (t, dt) {
    var s = Math.sin(t * 1.5), s2 = Math.sin(t * 1.9 + 1);
    if (rig.jhumkaL) { rig.jhumkaL.rotation.z = 0.07 * s; }
    if (rig.jhumkaR) { rig.jhumkaR.rotation.z = -0.07 * s; }
    gajra.rotation.y = Math.sin(t * 0.6) * 0.03;
    braid.rotation.z = Math.sin(t * 0.7) * 0.012;
  };

  return {
    id: 'tara',
    name: 'Tara',
    title: 'The Heritage Saree & Henna Guru',
    desc: 'Kanjeevaram drapes, temple jewellery and ritual mehndi. Tara holds the sacred thread of the ceremony — and knows every regional drape by heart.',
    tags: ['Emerald Silk', 'Temple Jewels', 'Mehndi', 'Gajra'],
    specs: [['Palette', 'Emerald · Marigold'], ['Signature', 'Nath & gajra bun'], ['Consultation', '90 min · Drape + Mehndi']],
    swatch: ['#0E5E48', '#E8A03C'],
    frame: { fill: 0.72, el: 0.095, fov: 34 },
    rig: rig
  };
}

/* =====================================================================
   05 · GIA — The Avant-Garde Editorial Nail & Crystal Beauty Icon
   Iridescent pastel-rose hair · holographic skin · crystal nail couture
   ===================================================================== */
function buildGia() {
  var rig = new Rig({ id: 'gia' });
  var SKIN = 0xEDCDBC;
  var skin = skinMat(SKIN, { glow: 0.15, rough: 0.44, cc: 0.48 });
  var gold = goldMat(1), goldLt = goldMat(3);
  var irid = U.iridTex(512);
  var holoMat = new T.MeshPhysicalMaterial({
    map: irid, color: LC(0xF6C8D6), roughness: 0.24, metalness: 0.55,
    clearcoat: 1.0, clearcoatRoughness: 0.12, envMapIntensity: 2.0
  });
  var bustierMat = new T.MeshPhysicalMaterial({
    map: irid.clone(), color: LC(0xE6D6EC), roughness: 0.22, metalness: 0.42,
    clearcoat: 1.0, clearcoatRoughness: 0.10, envMapIntensity: 2.2
  });
  bustierMat.map.wrapS = bustierMat.map.wrapT = T.RepeatWrapping;
  bustierMat.map.repeat.set(2, 2);
  var tulleMat = new T.MeshPhysicalMaterial({
    color: LC(0xF0DCE6), roughness: 0.85, metalness: 0.0, clearcoat: 0.4,
    transparent: true, opacity: 0.22, side: T.DoubleSide, depthWrite: false, envMapIntensity: 1.2
  });

  buildHumanoid(rig, {
    skin: skin, blush: true, blushOpacity: 0.30,
    blushInner: 'rgba(255,168,196,0.9)', blushOuter: 'rgba(198,150,255,0.12)',
    browColor: 0xC79AB0, nostrilColor: 0xC08A8A, armR: 0.046,
    rx: 0.198, ry: 0.216, rz: 0.194,
    legMat: skin, footMat: new T.MeshPhysicalMaterial({ color: LC(0xE8DCE8), roughness: 0.2, clearcoat: 1, envMapIntensity: 2 }),
    earring: function (s, p) {
      var g = new T.Group();
      var stud = new T.Mesh(new T.SphereGeometry(0.010, 12, 10), goldLt);
      g.add(stud);
      var drop = new T.Mesh(new T.OctahedronGeometry(0.016, 0), crystalMat(0xE4F0FF));
      drop.scale.set(0.8, 1.35, 0.8);
      drop.position.y = -0.036;
      g.add(drop);
      g.position.set(p.x + s * 0.004, p.y - 0.026, p.z + 0.004);
      return g;
    }
  });
  var rx = 0.198, ry = 0.216, rz = 0.194;

  /* ---------------- eyes (soft lilac-gray) ---------------- */
  var eyeTex = U.eyeTex('#4A4048', '#8E7FA6', '#161018', '#2A202C', '#C8B8DC');
  [1, -1].forEach(function (s) {
    var e = makeEye({
      r: 0.062, sx: 1.20, sy: 1.04, sz: 0.90, tex: eyeTex, lidMat: skin,
      lashColor: 0x2A1E28, lidTheta: 0.44 * Math.PI,
      glints: [{ x: -0.30, y: 0.34, r: 0.28, o: 1 }, { x: 0.34, y: -0.22, r: 0.12, o: 0.75 }]
    });
    e.group.position.set(s * rx * 0.46, ry * -0.04, rz * 0.82);
    e.group.rotation.y = s * 0.05;
    rig.head.add(e.group);
    rig[s > 0 ? 'eyeR' : 'eyeL'] = e;
  });

  /* ---------------- holographic lid + cheek highlights ---------------- */
  var holoPatchMat = new T.MeshBasicMaterial({
    map: irid.clone(), transparent: true, opacity: 0.42, blending: T.AdditiveBlending,
    depthWrite: false, side: T.DoubleSide
  });
  rig.holoTex = holoPatchMat.map;
  [1, -1].forEach(function (s) {
    var lid = rig.facePatch(s * rx * 0.46, ry * 0.20, rx * 0.70, holoPatchMat, 0.004, s * 0.35);
    lid.scale.set(1.25, 0.62, 1);
    var cheek = rig.facePatch(s * rx * 0.74, -ry * 0.10, rx * 0.80, holoPatchMat, 0.004, s * -0.6);
    cheek.scale.set(0.55, 1.35, 1);
    var temple = rig.facePatch(s * rx * 0.86, ry * 0.46, rx * 0.44, holoPatchMat, 0.004, s * 0.9);
    temple.scale.set(0.5, 1.1, 1);
  });

  /* ---------------- pearl face stickers ---------------- */
  [1, -1].forEach(function (s) {
    [[0.40, -0.20], [0.52, -0.28], [0.30, -0.30], [0.62, -0.14], [0.86, 0.38], [0.94, 0.28]].forEach(function (pp, i) {
      var pearl = new T.Mesh(new T.SphereGeometry(0.0072 - (i % 3) * 0.0012, 12, 10), pearlMat());
      var p = rig.onSurface(s * rx * pp[0], ry * pp[1], 0.008);
      pearl.position.copy(p);
      pearl.scale.set(1, 1, 0.62);
      rig.head.add(pearl);
      if (i < 2) {
        var tiny = new T.Mesh(new T.OctahedronGeometry(0.0045, 0), crystalMat(0xEAF6FF));
        tiny.position.copy(p);
        tiny.position.x += s * 0.016;
        tiny.position.y += 0.010;
        rig.head.add(tiny);
      }
    });
  });
  /* forehead crystal cluster */
  var fc = rig.onSurface(0, ry * 0.44, 0.008);
  [[0, 0], [-0.022, -0.016], [0.022, -0.016], [0, 0.024]].forEach(function (o, i) {
    var cr = new T.Mesh(new T.OctahedronGeometry(0.0075, 0), crystalMat(0xE8F4FF));
    cr.position.set(fc.x + o[0], fc.y + o[1], fc.z);
    cr.scale.set(1, 1.1, 0.6);
    rig.head.add(cr);
  });

  /* ---------------- lips (glossy rose) ---------------- */
  var mouth = makeMouth({ lipMat: silkMat(0xDC9098, 0.10), w: 0.047, thick: 0.0120 });
  mouth.group.position.set(0, -ry * 0.52, rz * 0.82);
  mouth.base = mouth.group.position.clone();
  rig.head.add(mouth.group);
  rig.mouth = mouth;

  /* ---------------- iridescent hair + dual high buns ---------------- */
  var hair2 = new T.MeshPhysicalMaterial({
    map: irid.clone(), color: LC(0xF6C2D2), roughness: 0.26, metalness: 0.5,
    clearcoat: 1.0, clearcoatRoughness: 0.12, envMapIntensity: 2.1
  });
  rig.hairTex = hair2.map;
  var cap = new T.Mesh(hairCap({
    rx: rx, ry: ry, rz: rz, gap: 0.010, bulge: 0.032, wave: 0.004, crown: 0.006,
    startFront: 0.02 * Math.PI, startBack: 0.02 * Math.PI,
    endFront: 0.252 * Math.PI, endBack: 0.74 * Math.PI
  }), hair2);
  cap.castShadow = true;
  rig.head.add(cap);

  [1, -1].forEach(function (s) {
    var pivot = new T.Group();
    pivot.position.set(s * rx * 0.86, ry * 0.92, -rz * 0.16);
    pivot.rotation.z = -s * 0.22;
    rig.head.add(pivot);
    rig[s > 0 ? 'bunR' : 'bunL'] = pivot;

    var bun = new T.Mesh(new T.SphereGeometry(0.098, 30, 24), hair2);
    bun.scale.set(1, 0.94, 0.94);
    bun.castShadow = true;
    pivot.add(bun);
    /* swirl wrap */
    var pts = [];
    for (var i = 0; i <= 40; i++) {
      var u = i / 40;
      var a = u * TAU * 2.4;
      var rr = 0.086 * (1 - u * 0.42);
      pts.push(V3(Math.cos(a) * rr, Math.sin(u * Math.PI) * 0.075 - 0.010, Math.sin(a) * rr));
    }
    var swirl = new T.Mesh(tubeFrom(pts, 0.014, 90, 8), hair2);
    pivot.add(swirl);
    /* scrunchie */
    var tie = new T.Mesh(new T.TorusGeometry(0.062, 0.013, 10, 30), new T.MeshPhysicalMaterial({
      color: LC(0xF2E2EC), roughness: 0.32, metalness: 0.25, clearcoat: 1, envMapIntensity: 2.0
    }));
    tie.rotation.x = Math.PI / 2;
    tie.position.y = -0.052;
    pivot.add(tie);
    /* crystal pins */
    for (var k = 0; k < 3; k++) {
      var pin = new T.Mesh(new T.OctahedronGeometry(0.010, 0), crystalMat(0xEAF6FF));
      var ang = k * 2.1;
      pin.position.set(Math.cos(ang) * 0.055, 0.030 + k * 0.008, Math.sin(ang) * 0.055);
      pin.scale.set(0.8, 1.4, 0.8);
      pivot.add(pin);
    }
    /* flyaway strands */
    for (var f = 0; f < 3; f++) {
      var st = new T.Mesh(tubeFrom([
        V3(0, 0.06, 0), V3(s * (0.04 + f * 0.02), 0.16, 0.02), V3(s * (0.06 + f * 0.03), 0.20, -0.02)
      ], 0.0055, 18, 6), hair2);
      pivot.add(st);
    }
  });
  /* face-framing wavy strands */
  [1, -1].forEach(function (s) {
    var st2 = new T.Mesh(tubeFrom([
      V3(s * rx * 0.80, ry * 0.66, rz * 0.42), V3(s * rx * 0.96, ry * 0.24, rz * 0.52),
      V3(s * rx * 0.88, -ry * 0.24, rz * 0.52), V3(s * rx * 0.74, -ry * 0.62, rz * 0.38)
    ], 0.0125, 34, 8), hair2);
    rig.head.add(st2);
  });

  /* ---------------- iridescent bustier + tulle ---------------- */
  var bustier = new T.Mesh(lathe([
    [0.02, 0.860], [0.188, 0.872], [0.192, 0.920], [0.172, 0.985], [0.162, 1.040],
    [0.174, 1.100], [0.206, 1.190], [0.226, 1.258], [0.170, 1.300], [0.02, 1.312]
  ], 48, true), bustierMat);
  bustier.castShadow = true;
  rig.body.add(bustier);
  var sweetheart = new T.Mesh(new T.TorusGeometry(0.128, 0.008, 8, 44), goldLt);
  sweetheart.rotation.x = Math.PI / 2 - 0.24; sweetheart.position.y = 1.288; sweetheart.scale.z = 0.74;
  rig.body.add(sweetheart);
  /* corset seams */
  for (var cs = 0; cs < 8; cs++) {
    var a2 = -1.9 + cs * 0.54;
    var seam = new T.Mesh(new T.BoxGeometry(0.003, 0.36, 0.003), goldLt);
    var rr2 = 0.198;
    seam.position.set(Math.sin(a2) * rr2, 1.06, Math.cos(a2) * rr2 * 0.72);
    seam.rotation.x = 0.06;
    rig.body.add(seam);
  }

  /* tulle shrug + skirt */
  var shrug = new T.Mesh(new T.SphereGeometry(0.30, 40, 30), tulleMat);
  shrug.scale.set(1.25, 0.86, 1.0);
  shrug.position.set(0, 1.22, 0);
  rig.body.add(shrug);
  var tulleSkirt = new T.Mesh(fluff(new T.SphereGeometry(0.52, 48, 30), 0.014, 7), tulleMat);
  tulleSkirt.scale.set(1, 0.78, 1);
  tulleSkirt.position.y = 0.52;
  rig.body.add(tulleSkirt);
  var tulleSkirt2 = new T.Mesh(fluff(new T.SphereGeometry(0.40, 40, 26), 0.010, 9), tulleMat);
  tulleSkirt2.scale.set(1, 0.72, 1);
  tulleSkirt2.position.y = 0.60;
  rig.body.add(tulleSkirt2);
  /* pearl waist chain */
  var waist = new T.Mesh(new T.TorusGeometry(0.204, 0.008, 8, 50), goldLt);
  waist.rotation.x = Math.PI / 2 - 0.05; waist.position.y = 0.905; waist.scale.z = 0.88;
  rig.body.add(waist);
  for (var pw = 0; pw < 16; pw++) {
    var pa = (pw / 16) * TAU;
    var pearl = new T.Mesh(new T.SphereGeometry(0.011, 12, 10), pearlMat());
    pearl.position.set(Math.cos(pa) * 0.204, 0.905 - 0.014, Math.sin(pa) * 0.204 * 0.88);
    rig.body.add(pearl);
  }

  /* ---------------- sculpted hands with crystal nails ---------------- */
  [rig.armR, rig.armL].forEach(function (a) {
    while (a.hand.children.length) a.hand.remove(a.hand.children[0]);
    var h = U.sculptedHand(skin, { nails: true, nailMat: crystalMat(0xE6EEF8), crystalMat: crystalMat(0xDCEFFF) });
    h.position.y = -0.052;
    h.rotation.x = -0.12;
    a.hand.add(h);
  });

  /* pearl choker */
  for (var pc = 0; pc < 18; pc++) {
    var pca = -2.2 + (pc / 17) * 4.4;
    var pp2 = new T.Mesh(new T.SphereGeometry(0.0105, 12, 10), pearlMat());
    pp2.position.set(Math.sin(pca) * 0.112, 1.316 - Math.cos(pca) * 0.006, Math.cos(pca) * 0.098);
    rig.body.add(pp2);
  }
  var pendant2 = new T.Mesh(new T.OctahedronGeometry(0.016, 0), crystalMat(0xEAF4FF));
  pendant2.position.set(0, 1.300, 0.112);
  pendant2.scale.set(0.85, 1.3, 0.85);
  rig.body.add(pendant2);

  /* ---------------- pose overrides: hands showcase the nails ---------------- */
  rig.emotions.poise.armRx = -0.92; rig.emotions.poise.armRz = -0.34;
  rig.emotions.poise.elbowRx = -1.74; rig.emotions.poise.elbowRz = -0.52;
  rig.emotions.poise.armLx = -0.30; rig.emotions.poise.armLz = -0.30;
  rig.emotions.poise.elbowLx = -0.62; rig.emotions.poise.elbowLz = 0.10;
  rig.emotions.thinking.armRx = -1.05; rig.emotions.thinking.armRz = -0.46;
  rig.emotions.thinking.elbowRx = -1.95; rig.emotions.thinking.elbowRz = -0.62;
  rig.emotions.happy.armRx = -0.86; rig.emotions.happy.armRz = -0.30;
  rig.emotions.happy.elbowRx = -1.62; rig.emotions.happy.elbowRz = -0.40;
  rig.emotions.hesitant.armRx = -0.72; rig.emotions.hesitant.armRz = -0.24;
  rig.emotions.hesitant.elbowRx = -1.34; rig.emotions.hesitant.elbowRz = -0.30;

  rig.extra = function (t, dt, p) {
    if (rig.holoTex) { rig.holoTex.offset.x = (t * 0.035) % 1; rig.holoTex.offset.y = Math.sin(t * 0.2) * 0.05; }
    if (rig.hairTex) { rig.hairTex.offset.x = (t * 0.018) % 1; }
    holoPatchMat.opacity = 0.30 + 0.14 * Math.sin(t * 1.6) + p.glow * 0.10;
    var b = Math.sin(t * 0.9);
    if (rig.bunL) rig.bunL.rotation.x = 0.05 * b;
    if (rig.bunR) rig.bunR.rotation.x = 0.05 * Math.sin(t * 0.9 + 1.2);
    tulleSkirt.rotation.y = t * 0.05;
    tulleSkirt2.rotation.y = -t * 0.04;
  };

  return {
    id: 'gia',
    name: 'Gia',
    title: 'The Avant-Garde Nail & Crystal Icon',
    desc: 'Sculpted crystal nail couture, holographic skin and pearl detailing. Gia builds the editorial look that breaks the feed — and the rulebook.',
    tags: ['Crystal Nails', 'Holographic', 'Gen-Z Couture', 'Editorial'],
    specs: [['Palette', 'Pastel Rose · Chrome'], ['Signature', 'Dual buns & pearl stickers'], ['Consultation', '75 min · Nail + Face']],
    swatch: ['#F2B8CC', '#BFD8FF'],
    frame: { fill: 0.72, el: 0.090, fov: 34 },
    rig: rig
  };
}

/* ------------------------------------------------------------------ export */

/* =====================================================================
   06 · MEERA — The Couture Hair & Makeup Artist
   Pixar-style cute: widest eyes of the five, tiny nose, small mouth,
   glossy black bob with a blunt fringe.
   ===================================================================== */
function buildMeera() {
  var rig = new Rig({ id: 'meera' });
  var SKIN = 0xE0A97E;
  var skin = skinMat(SKIN, { glow: 0.13, rough: 0.56, cc: 0.32 });
  var black = hairMat(0x0B0806, { rough: 0.30 });
  var ink = silkMat(0x16161C, 0.30);
  var ivory = silkMat(0xDFD4C0, 0.36);   /* keeps her off the black backdrop */
  var gold = goldMat(0), goldLt = goldMat(1);

  buildHumanoid(rig, {
    skin: skin, blush: true,
    blushInner: 'rgba(255,148,128,0.92)', blushOuter: 'rgba(240,108,128,0.18)', blushOpacity: 0.60,
    browColor: 0x140B06, nostrilColor: 0x8A4A28, armR: 0.048,
    legMat: matteMat(0x2A2A32, 0.9), footMat: goldLt
  });

  var rx = CANON.headRX, ry = CANON.headRY, rz = CANON.headRZ;

  /* ---------------- eyes: biggest of the five ---------------- */
  var eyeTex = U.eyeTex('#3A1B0B', '#8A4A1E', '#190903', '#1D0C04', '#E8B870');
  [1, -1].forEach(function (s) {
    var e = makeEye({
      r: 0.072, sx: 1.18, sy: 1.10, sz: 0.94, tex: eyeTex, lidMat: skin,
      lashColor: 0x120A05,
      glints: [{ x: -0.30, y: 0.34, r: 0.32, o: 1 }, { x: 0.36, y: -0.24, r: 0.130, o: 0.75 }]
    });
    e.group.position.set(s * rx * 0.44, ry * -0.05, rz * 0.84);
    e.group.rotation.y = s * 0.05;
    rig.head.add(e.group);
    rig[s > 0 ? 'eyeR' : 'eyeL'] = e;
  });

  /* ---------------- tiny nose + small mouth (cute canon) ---------------- */
  var mouth = makeMouth({ lipMat: silkMat(0xC4706E, 0.24), w: 0.044, thick: 0.0112 });
  mouth.group.position.set(0, -ry * 0.52, rz * 0.84);
  mouth.base = mouth.group.position.clone();
  rig.head.add(mouth.group);
  rig.mouth = mouth;

  /* ---------------- glossy black bob ---------------- */
  var cap = new T.Mesh(hairCap({
    rx: rx, ry: ry, rz: rz, gap: 0.012, bulge: 0.055, wave: 0.005, crown: 0.010,
    startFront: 0.02 * Math.PI, startBack: 0.02 * Math.PI,
    endFront: 0.30 * Math.PI, endBack: 0.90 * Math.PI
  }), black);
  cap.castShadow = true;
  rig.head.add(cap);

  /* back mass — pushed behind the face plane so it never covers the features */
  var backHair = new T.Mesh(lathe([
    [0.03, 0.40], [0.17, 0.38], [0.25, 0.26], [0.28, 0.06], [0.275, -0.14],
    [0.235, -0.30], [0.155, -0.40], [0.04, -0.43]
  ], 44, true), black);
  backHair.position.set(0, ry * 0.06, -rz * 0.55);
  backHair.scale.set(1.0, 1.0, 0.70);
  backHair.castShadow = true;
  rig.head.add(backHair);

  /* blunt fringe + face-framing side panels */
  [1, -1].forEach(function (s) {
    var fr = new T.Mesh(tubeFrom([
      V3(s * 0.010, ry * 0.80, rz * 0.62), V3(s * 0.070, ry * 0.74, rz * 0.80),
      V3(s * 0.135, ry * 0.60, rz * 0.86), V3(s * 0.170, ry * 0.40, rz * 0.80)
    ], 0.014, 30, 8), black);
    rig.head.add(fr);
    var side = new T.Mesh(tubeFrom([
      V3(s * rx * 0.86, ry * 0.42, rz * 0.30), V3(s * rx * 0.98, ry * 0.00, rz * 0.28),
      V3(s * rx * 0.94, -ry * 0.34, rz * 0.22), V3(s * rx * 0.80, -ry * 0.62, rz * 0.14)
    ], 0.019, 34, 8), black);
    side.castShadow = true;
    rig.head.add(side);
  });

  /* ---------------- charcoal couture gown ---------------- */
  var gown2 = ivory.clone(); gown2.side = T.DoubleSide;
  var skirtGeo = lathe([
    [0.03, 0.012], [0.22, 0.020], [0.34, 0.090], [0.40, 0.230], [0.415, 0.400],
    [0.385, 0.560], [0.310, 0.720], [0.240, 0.850], [0.205, 0.925], [0.195, 0.960]
  ], 52, true);
  folds(skirtGeo, 14, 0.016, [0.02, 0.90]);
  var skirt = new T.Mesh(skirtGeo, gown2);
  skirt.castShadow = true; skirt.receiveShadow = true;
  rig.body.add(skirt);

  var bodice = new T.Mesh(lathe([
    [0.200, 0.845], [0.188, 0.930], [0.165, 1.010], [0.176, 1.070],
    [0.212, 1.180], [0.238, 1.278], [0.215, 1.300]
  ], 44, true), ink);
  bodice.castShadow = true;
  rig.body.add(bodice);

  var belt = new T.Mesh(new T.TorusGeometry(0.215, 0.011, 10, 64), goldLt);
  belt.rotation.x = Math.PI / 2; belt.position.y = 0.90;
  rig.body.add(belt);

  /* crystal hair pin */
  var pin = new T.Mesh(new T.SphereGeometry(0.016, 16, 12), gold);
  pin.position.set(rx * 0.62, ry * 0.72, rz * 0.42);
  rig.head.add(pin);

  rig.extra = function (t) {
    var s = Math.sin(t * 1.5);
    if (this.earL) this.earL.rotation.z = 0;
    if (pin) pin.rotation.y = s * 0.5;
  };

  return {
    id: 'meera',
    name: 'Meera',
    title: 'The Couture Hair & Makeup Artist',
    desc: 'Blowouts, bridal partings and the 14-hour hold — Meera designs the hair and beauty look that survives the phera, the photos and the after-party.',
    tags: ['Hair Couture', 'Bridal Beauty', 'Long-Wear', 'Editorial'],
    specs: [['Palette', 'Ivory · Ink Black · Gold'], ['Signature', 'Glossy Bob & Blunt Fringe'], ['Consultation', '60 min · Trial included']],
    swatch: ['#DFD4C0', '#16161C'],
    frame: { fill: 0.72, el: 0.100, fov: 34 },
    rig: rig
  };
}

/* =====================================================================
   07 · CHERRY — The Glow-Berry Skincare Concierge
   A whole-body fruit mascot: the berry itself carries the face,
   yellow seeds, green calyx, stubby arms and feet.
   ===================================================================== */
function buildCherry() {
  var rig = new Rig({ id: 'cherry', headY: 0.54 });
  var BERRY = 0xD42A3C;
  var berryMat = silkMat(BERRY, 0.34);
  var berryDeep = silkMat(0x9E1526, 0.38);
  var seedMat = new T.MeshPhysicalMaterial({
    color: LC(0xF5D777), roughness: 0.30, clearcoat: 1, clearcoatRoughness: 0.08, envMapIntensity: 1.2
  });
  var leafMat = silkMat(0x4E9B3F, 0.42);
  var stemMat = matteMat(0x6B4A2A, 0.85);
  var goldLt = goldMat(1);

  /* ---------------- the berry (head-local) ----------------
     modelled as an ellipsoid centred at y=-0.015, a=0.355, b=0.425 */
  var berry = new T.Mesh(lathe([
    [0.02, -0.44], [0.10, -0.43], [0.19, -0.39], [0.28, -0.32], [0.335, -0.21],
    [0.355, -0.06], [0.350, 0.08], [0.325, 0.20], [0.275, 0.30], [0.195, 0.37],
    [0.10, 0.40], [0.03, 0.41]
  ], 56, true), berryMat);
  berry.castShadow = true; berry.receiveShadow = true;
  rig.head.add(berry);

  function surfR(y) {
    return 0.355 * Math.sqrt(Math.max(0, 1 - Math.pow((y + 0.015) / 0.425, 2)));
  }

  /* ---------------- seeds, skipping the face panel ---------------- */
  var seedGeo = new T.SphereGeometry(0.0135, 10, 8);
  for (var ri = 0; ri < 10; ri++) {
    var tt = ri / 9;
    var y = -0.36 + tt * 0.70;
    var rm = surfR(y);
    if (rm < 0.06) continue;
    for (var k = 0; k < 7; k++) {
      var ang = (k / 7) * TAU + ri * 0.42;
      var px = Math.sin(ang) * (rm - 0.012), pz = Math.cos(ang) * (rm - 0.012);
      if (pz > 0.10 && Math.abs(px) < 0.21 && y > -0.18 && y < 0.17) continue;  /* face */
      var sd = new T.Mesh(seedGeo, seedMat);
      sd.position.set(px, y, pz);
      sd.scale.set(1, 0.62, 0.62);
      sd.lookAt(0, y, 0);
      rig.head.add(sd);
    }
  }

  /* ---------------- calyx + stem ---------------- */
  var leafGeo = new T.SphereGeometry(0.10, 14, 10);
  for (var li = 0; li < 6; li++) {
    var la = (li / 6) * TAU + 0.30;
    var leaf = new T.Mesh(leafGeo, leafMat);
    leaf.scale.set(0.72, 0.22, 1.25);
    leaf.position.set(Math.sin(la) * 0.150, 0.395, Math.cos(la) * 0.150);
    leaf.rotation.y = la;
    leaf.rotation.z = -0.42;
    leaf.castShadow = true;
    rig.head.add(leaf);
  }
  var stem = new T.Mesh(capsule(0.020, 0.10, 12, 8), stemMat);
  stem.position.set(0, 0.465, 0);
  stem.rotation.z = 0.14;
  rig.head.add(stem);

  /* ---------------- big glossy eyes ---------------- */
  var boba2 = U.eyeTex('#12121A', '#26262F', '#050507', '#08080B', '#3A3A48');
  [1, -1].forEach(function (s) {
    var e = makeEye({
      r: 0.082, sx: 1.04, sy: 1.10, sz: 0.98, tex: boba2, lidMat: berryMat, lashes: false,
      lidTheta: 0.42 * Math.PI, lowTheta: 0.26 * Math.PI,
      glints: [{ x: -0.28, y: 0.32, r: 0.26, o: 1 }, { x: 0.30, y: -0.24, r: 0.110, o: 0.8 }]
    });
    e.group.position.set(s * 0.115, 0.010, 0.300);
    rig.head.add(e.group);
    rig[s > 0 ? 'eyeR' : 'eyeL'] = e;
  });

  /* ---------------- small smile ---------------- */
  var mouth = makeMouth({ lipMat: silkMat(0xB03344, 0.24), w: 0.046, thick: 0.0115 });
  mouth.group.position.set(0, -0.115, 0.335);
  mouth.base = mouth.group.position.clone();
  rig.head.add(mouth.group);
  rig.mouth = mouth;

  /* ---------------- blush ---------------- */
  var blushMat = new T.MeshBasicMaterial({ color: LC(0xE86A7C), transparent: true, opacity: 0.32 });
  [1, -1].forEach(function (s) {
    var bl = new T.Mesh(new T.CircleGeometry(0.050, 20), blushMat);
    bl.position.set(s * 0.175, -0.055, 0.315);
    bl.rotation.y = s * 0.45;
    rig.head.add(bl);
  });

  /* ---------------- stubby arms + feet (world space, under the berry) ---- */
  [1, -1].forEach(function (s) {
    var arm = new T.Mesh(capsule(0.036, 0.13, 14, 8), berryMat);
    arm.position.set(s * 0.340, 0.40, 0.030);
    arm.rotation.z = s * 0.90;
    arm.castShadow = true;
    rig.body.add(arm);
    var foot = new T.Mesh(new T.SphereGeometry(0.062, 16, 12), berryDeep);
    foot.scale.set(1, 0.55, 1.35);
    foot.position.set(s * 0.135, 0.055, 0.050);
    foot.castShadow = true;
    rig.body.add(foot);
  });

  /* a gold-leaf brooch, so she still reads as studio staff */
  var brooch = new T.Mesh(new T.TorusGeometry(0.030, 0.0075, 8, 24), goldLt);
  brooch.position.set(0.155, 0.30, 0.300);
  brooch.rotation.y = 0.5;
  rig.head.add(brooch);

  rig.extra = function (t) {
    var b = Math.sin(t * 1.7);
    if (this.earL) this.earL.rotation.z = 0;
    stem.rotation.z = 0.14 + b * 0.05;
    for (var i = 0; i < 6; i++) { /* leaves are children 1..6 after the berry */ }
  };

  return {
    id: 'cherry',
    name: 'Cherry',
    title: 'The Glow-Berry Skincare Concierge',
    desc: 'Berry enzymes, vitamin-C facials and pre-bridal skin prep — Cherry builds the 90-day glow plan that makes the makeup sit like glass.',
    tags: ['Skincare', 'Vitamin C', 'Pre-Bridal', 'Glow Plan'],
    specs: [['Palette', 'Berry Red · Leaf Green'], ['Signature', 'Seed-Dot Detailing'], ['Consultation', '30 min · Skin analysis']],
    swatch: ['#D42A3C', '#4E9B3F'],
    frame: { fill: 0.70, el: 0.060, fov: 34 },
    rig: rig
  };
}


/* =====================================================================
   FULL-GLTF MODE — proper rigged models replace the procedural bodies.
   Each entry is an auto-scaled, auto-planted skinned mesh with its own
   skeleton and animation clips.
   ===================================================================== */
var GLTF_ROSTER = [
  { id:'asha',   url:'models/Michelle.glb',        h:1.76, rate:0.12, reskin:{ skin:0xC98F63, cloth:0x7A1226, metal:0xD8BC7E }, name:'Asha',   title:'The Royal Bridal Stylist',
    desc:'Signature lehengas, zardozi ateliers and the ceremonial drape — Asha walks you through the entire bridal trousseau, from first fabric to final phera.',
    tags:['Zardozi','Crimson Velvet','Ceremony','Trousseau'],
    specs:[['Palette','Crimson · Antique Gold'],['Signature','Maang Tikka & Jhumka'],['Consultation','45 min · By appointment']],
    swatch:['#7A1226','#D8BC7E'], frame:{fill:0.72,el:0.100,fov:34} },

  { id:'mochi',  url:'models/Fox.glb',             h:1.05, name:'Mochi',  title:'The Haute Velvet Mascot',
    desc:'The studio mascot — Mochi guides first-time brides through the atelier, and knows exactly which velvet reads best under mandap lighting.',
    tags:['Mascot','Plush','Atelier Guide','Velvet'],
    specs:[['Palette','Ivory · Burgundy'],['Signature','Boba Eyes & Sash'],['Consultation','Drop-in']],
    swatch:['#D5D7D9','#5C1226'], frame:{fill:0.64,el:0.055,fov:34} },

  { id:'noor',   url:'models/Soldier.glb',         h:1.76, couture:{ kind:'lehenga', cloth:0x11604A }, name:'Noor',   title:'The Indo-Western Glamour Artist',
    desc:'Gowns with a banarasi spine, corsetry with dupatta drama — Noor builds the fusion look that photographs like a film still.',
    tags:['Indo-Western','Gowns','Fusion','Corsetry'],
    specs:[['Palette','Emerald · Marigold'],['Signature','Dupatta Draping'],['Consultation','50 min']],
    swatch:['#11604A','#E8A03C'], frame:{fill:0.72,el:0.095,fov:34} },

  { id:'tara',   url:'models/RobotExpressive.glb', h:1.70, couture:{ kind:'saree', cloth:0x0E5E48 }, name:'Tara',   title:'The Heritage Saree & Henna Guru',
    desc:'Nine yards, twelve drapes and mehndi that stains deep — Tara carries the classical vocabulary, from Kanjeevaram to the Bengaal atpourey.',
    tags:['Saree','Henna','Heritage','Classical'],
    specs:[['Palette','Emerald · Vermilion'],['Signature','Nine-Yard Drape'],['Consultation','60 min']],
    swatch:['#0E5E48','#C2452D'], frame:{fill:0.72,el:0.095,fov:34} },

  { id:'gia',    url:'models/Xbot.glb',            h:1.78, reskin:{ skin:0xE0A97E, cloth:0xE7B7C4, metal:0x8E7CC3 }, name:'Gia',    title:'The Avant-Garde Nail & Crystal Icon',
    desc:'Sculpted gel, chrome powders and crystal nail couture — Gia treats the hands as the final accessory of the bridal look.',
    tags:['Nail Couture','Chrome','Crystal','Avant-Garde'],
    specs:[['Palette','Pastel Rose · Iridescent'],['Signature','Crystal Nail Couture'],['Consultation','40 min']],
    swatch:['#E7B7C4','#8E7CC3'], frame:{fill:0.72,el:0.090,fov:34} },

  { id:'meera',  url:'models/Flamingo.glb',        h:1.30, jewels:{ metal:1, gem:0xE8C26A }, name:'Meera',  title:'The Couture Hair & Makeup Artist',
    desc:'Blowouts, bridal partings and the 14-hour hold — Meera designs the hair and beauty look that survives the phera, the photos and the after-party.',
    tags:['Hair Couture','Bridal Beauty','Long-Wear','Editorial'],
    specs:[['Palette','Ivory · Ink Black · Gold'],['Signature','Glossy Bob & Blunt Fringe'],['Consultation','60 min · Trial included']],
    swatch:['#DFD4C0','#16161C'], frame:{fill:0.70,el:0.070,fov:34} },

  { id:'cherry', url:'models/Parrot.glb',          h:1.00, jewels:{ metal:0, gem:0xE24A5E }, name:'Cherry', title:'The Glow-Berry Skincare Concierge',
    desc:'Berry enzymes, vitamin-C facials and pre-bridal skin prep — Cherry builds the 90-day glow plan that makes the makeup sit like glass.',
    tags:['Skincare','Vitamin C','Pre-Bridal','Glow Plan'],
    specs:[['Palette','Berry Red · Leaf Green'],['Signature','Seed-Dot Detailing'],['Consultation','30 min · Skin analysis']],
    swatch:['#D42A3C','#4E9B3F'], frame:{fill:0.70,el:0.060,fov:34} }
];

/* emotion -> animation-clip preference, used when a model ships named clips */
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

function buildAsha() { return makeGLTFCharacter(GLTF_ROSTER[0]); }
function buildMochi() { return makeGLTFCharacter(GLTF_ROSTER[1]); }
function buildNoor() { return makeGLTFCharacter(GLTF_ROSTER[2]); }
function buildTara() { return makeGLTFCharacter(GLTF_ROSTER[3]); }
function buildGia() { return makeGLTFCharacter(GLTF_ROSTER[4]); }
function buildMeera() { return makeGLTFCharacter(GLTF_ROSTER[5]); }
function buildCherry() { return makeGLTFCharacter(GLTF_ROSTER[6]); }

window.__HBS.builders = { asha: buildAsha, mochi: buildMochi, noor: buildNoor, tara: buildTara, gia: buildGia, meera: buildMeera, cherry: buildCherry };
window.__HBS.GLTF_ROSTER = GLTF_ROSTER;
})();
