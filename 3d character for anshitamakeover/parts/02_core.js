<script>
/* =====================================================================
   MAISON LUMIÈRE — Haute Bridal & Makeup Studio · 3D Concierge Selector
   ---------------------------------------------------------------------
   Single-file, zero-asset, procedural character system.

   ARCHITECTURE (everything is detachable — see window.HBStudio at the end)
     02_core.js   → utils · material library · procedural textures ·
                    geometry helpers · HDR studio environment · renderer
     03_rig.js    → Rig class (gaze, blink, breath, emotion poses) +
                    shared humanoid / eye / mouth / hair builders
     04_chars.js  → Asha · Mochi · Noor · Tara · Gia
     05_app.js    → camera, transitions, UI, widget, loop, export API

   EMBEDDING A CHARACTER ANYWHERE (any Three.js r128 project):
     const char = HBStudio.buildCharacter('asha');   // or 'mochi' …
     scene.add(char.root);                           // char.root is a Group
     char.setEmotion('welcome');                     // | 'happy' | 'thinking'
     char.update(time, delta, {x:0, y:0});           // | 'hesitant' | 'poise'
     char.lookTarget(mouseNDC.x, mouseNDC.y);        // −1 … 1
   Nothing else is required: no textures, no models, no network.
   ===================================================================== */
(function () {
'use strict';

/* ---------------------------------------------------------------- 0 · boot */
var T = window.THREE;
var loaderEl = document.getElementById('loader');
var ldNote = document.getElementById('ldNote');
var ldBar = document.getElementById('ldBar');

function offline(msg) {
  if (!loaderEl) return;
  loaderEl.classList.remove('done');
  document.querySelector('#loader .bar').style.display = 'none';
  ldNote.className = 'offline';
  ldNote.innerHTML = msg;
}
if (!T) {
  offline('<b>Three.js could not be loaded.</b><br/>This build streams r128 from a CDN, so it needs an internet connection the first time. Open it in a browser with network access — or use the fully inlined <code>index.offline.html</code> build.');
  return;
}
if (!window.gsap) {
  offline('<b>GSAP could not be loaded.</b><br/>Animation library unreachable — open this file with network access, or use <code>index.offline.html</code>.');
  return;
}
function progress(p) { if (ldBar) ldBar.style.right = (100 - Math.round(p * 100)) + '%'; }

/* ---------------------------------------------------------------- 1 · utils */
var TAU = Math.PI * 2;
var clamp = T.MathUtils.clamp;
var lerp = T.MathUtils.lerp;
function V3(x, y, z) { return new T.Vector3(x, y, z); }
/* three r128 has no colour management: a hex literal is sRGB, but the renderer
   treats material / light colours as LINEAR radiance. Every authored colour in
   this file (and in 03/04/05) therefore goes through LC() once.             */
function LC(h) { return new T.Color(h).convertSRGBToLinear(); }
function C(h) { return LC(h); }
function damp(current, target, lambda, dt) { return lerp(current, target, 1 - Math.exp(-lambda * dt)); }

/* deterministic hash noise (no deps) */
function hash(n) { var s = Math.sin(n * 127.1 + 311.7) * 43758.5453123; return s - Math.floor(s); }
function noise3(x, y, z) {
  var i = Math.floor(x), j = Math.floor(y), k = Math.floor(z);
  var f = function (t) { return t * t * (3 - 2 * t); };
  var u = f(x - i), v = f(y - j), w = f(z - k);
  var n = hash(i + j * 57 + k * 131);
  var a = hash(i + 1 + j * 57 + k * 131), b = hash(i + (j + 1) * 57 + k * 131), c = hash(i + 1 + (j + 1) * 57 + k * 131);
  var d = hash(i + j * 57 + k * 131 + 57), e = hash(i + 1 + j * 57 + k * 131 + 57), g = hash(i + (j + 1) * 57 + k * 131 + 57), h = hash(i + 1 + (j + 1) * 57 + k * 131 + 57);
  return lerp(lerp(lerp(n, a, u), lerp(b, c, u), v), lerp(lerp(d, e, u), lerp(g, h, u), v), w);
}

/* ---------------------------------------------------------------- 2 · material library */
/* Skin: faked subsurface via a warm emissive bleed + clearcoat specular. */
function skinMat(col, o) {
  o = o || {};
  return new T.MeshPhysicalMaterial({
    color: LC(col),
    roughness: o.rough !== undefined ? o.rough : 0.58,
    metalness: 0,
    clearcoat: o.cc !== undefined ? o.cc : 0.26,
    clearcoatRoughness: 0.56,
    envMapIntensity: o.env !== undefined ? o.env : 0.9,
    emissive: C(col).multiplyScalar(o.glow !== undefined ? o.glow : 0.11)
  });
}
function goldMat(tone) {
  var t = tone || 0;
  var cols = [0xC8A96A, 0xE9D29B, 0xA8843F, 0xF2DFB4];
  var rough = [0.24, 0.14, 0.36, 0.10];
  return new T.MeshPhysicalMaterial({
    color: LC(cols[t]), metalness: 1.0, roughness: rough[t],
    envMapIntensity: 1.75, clearcoat: 0.7, clearcoatRoughness: 0.18
  });
}
function velvetMat(col, o) {
  o = o || {};
  return new T.MeshPhysicalMaterial({
    color: LC(col), roughness: 0.97, metalness: 0.0,
    clearcoat: 0.32, clearcoatRoughness: 0.92,
    envMapIntensity: 0.55,
    emissive: C(col).multiplyScalar(o.glow !== undefined ? o.glow : 0.07)
  });
}
function silkMat(col, rough) {
  return new T.MeshPhysicalMaterial({
    color: LC(col), roughness: rough === undefined ? 0.30 : rough, metalness: 0.08,
    clearcoat: 1.0, clearcoatRoughness: 0.20, envMapIntensity: 1.35
  });
}
function hairMat(col, o) {
  o = o || {};
  return new T.MeshPhysicalMaterial({
    color: LC(col), roughness: o.rough !== undefined ? o.rough : 0.33, metalness: 0.18,
    clearcoat: 0.9, clearcoatRoughness: 0.16, envMapIntensity: 1.6
  });
}
function glossMat(col, rough) {
  return new T.MeshPhysicalMaterial({
    color: LC(col), roughness: rough === undefined ? 0.07 : rough, metalness: 0.0,
    clearcoat: 1.0, clearcoatRoughness: 0.03, envMapIntensity: 2.3
  });
}
function crystalMat(col) {
  return new T.MeshPhysicalMaterial({
    color: LC(col === undefined ? 0xEAF4FF : col), roughness: 0.02, metalness: 0.06,
    clearcoat: 1.0, clearcoatRoughness: 0.02, envMapIntensity: 3.0,
    transparent: true, opacity: 0.82, emissive: LC(0x0A1622)
  });
}
function pearlMat() {
  return new T.MeshPhysicalMaterial({
    color: LC(0xF6EDE4), roughness: 0.12, metalness: 0.35,
    clearcoat: 1.0, clearcoatRoughness: 0.06, envMapIntensity: 2.6,
    emissive: LC(0x2A1E1A)
  });
}
function matteMat(col, rough) {
  return new T.MeshStandardMaterial({ color: LC(col), roughness: rough === undefined ? 0.9 : rough, metalness: 0.0, envMapIntensity: 0.5 });
}
function glowMat(col, opacity) {
  return new T.MeshBasicMaterial({ color: LC(col), transparent: true, opacity: opacity === undefined ? 1 : opacity, blending: T.AdditiveBlending, depthWrite: false });
}

/* ---------------------------------------------------------------- 3 · procedural textures */
function cnv(w, h) { var c = document.createElement('canvas'); c.width = w; c.height = h; return c; }
function toTex(c, rep) {
  var t = new T.CanvasTexture(c);
  t.encoding = T.sRGBEncoding;
  t.anisotropy = 8;
  if (rep) { t.wrapS = t.wrapT = T.RepeatWrapping; }
  return t;
}
/* vertical / horizontal multi-stop gradient */
function gradTex(stops, vertical, w, h) {
  w = w || 8; h = h || 256;
  var c = cnv(w, h), g = c.getContext('2d');
  var gr = vertical ? g.createLinearGradient(0, 0, 0, h) : g.createLinearGradient(0, 0, w, 0);
  for (var i = 0; i < stops.length; i++) gr.addColorStop(stops[i][0], stops[i][1]);
  g.fillStyle = gr; g.fillRect(0, 0, w, h);
  return toTex(c);
}
/* soft radial blob (blush, light pools, sparkles) */
function radialTex(inner, outer, size, pow) {
  size = size || 256;
  var c = cnv(size, size), g = c.getContext('2d');
  var gr = g.createRadialGradient(size / 2, size / 2, 0, size / 2, size / 2, size / 2);
  gr.addColorStop(0, inner);
  gr.addColorStop(pow === undefined ? 0.45 : pow, outer);
  gr.addColorStop(1, 'rgba(0,0,0,0)');
  g.fillStyle = gr; g.fillRect(0, 0, size, size);
  return toTex(c);
}
/* eye map wrapped on a sphere: iris bullseye sits at u = 0.25 (= +Z front) */
function eyeTex(base, iris, pupil, ring, fibre) {
  var w = 1024, h = 512, c = cnv(w, h), g = c.getContext('2d');
  g.fillStyle = base; g.fillRect(0, 0, w, h);
  var cx = w * 0.25, cy = h * 0.5, R = w * 0.122;
  var gr = g.createRadialGradient(cx, cy, R * 0.05, cx, cy, R);
  gr.addColorStop(0.00, pupil);
  gr.addColorStop(0.38, pupil);
  gr.addColorStop(0.48, iris);
  gr.addColorStop(0.82, iris);
  gr.addColorStop(0.92, ring);
  gr.addColorStop(1.00, 'rgba(0,0,0,0)');
  g.fillStyle = gr; g.beginPath(); g.arc(cx, cy, R, 0, TAU); g.fill();
  /* iris fibres */
  g.save(); g.globalAlpha = 0.30; g.strokeStyle = fibre || '#C98B4A'; g.lineWidth = 2.2;
  for (var i = 0; i < 84; i++) {
    var a = (i / 84) * TAU + hash(i) * 0.3;
    var r0 = R * (0.40 + hash(i * 3) * 0.1), r1 = R * (0.86 + hash(i * 7) * 0.12);
    g.beginPath();
    g.moveTo(cx + Math.cos(a) * r0, cy + Math.sin(a) * r0);
    g.lineTo(cx + Math.cos(a) * r1, cy + Math.sin(a) * r1);
    g.stroke();
  }
  g.restore();
  /* lower catchlight bounce (subtle) */
  g.save(); g.globalAlpha = 0.18; g.fillStyle = '#FFD9A8';
  g.beginPath(); g.ellipse(cx, cy + R * 0.48, R * 0.42, R * 0.16, 0, 0, TAU); g.fill(); g.restore();
  return toTex(c);
}
/* iridescent / holographic gradient (Gia's makeup + hair) */
function iridTex(size) {
  size = size || 512;
  var c = cnv(size, size), g = c.getContext('2d');
  var gr = g.createLinearGradient(0, 0, size, size);
  gr.addColorStop(0.00, 'rgba(255,205,225,1)');
  gr.addColorStop(0.18, 'rgba(198,190,255,1)');
  gr.addColorStop(0.36, 'rgba(178,240,238,1)');
  gr.addColorStop(0.54, 'rgba(214,255,206,1)');
  gr.addColorStop(0.72, 'rgba(255,236,190,1)');
  gr.addColorStop(0.88, 'rgba(255,196,222,1)');
  gr.addColorStop(1.00, 'rgba(206,196,255,1)');
  g.fillStyle = gr; g.fillRect(0, 0, size, size);
  g.globalCompositeOperation = 'overlay';
  for (var i = 0; i < 26; i++) {
    var y = hash(i * 11) * size;
    g.fillStyle = 'rgba(255,255,255,' + (0.05 + hash(i) * 0.10) + ')';
    g.fillRect(0, y, size, 2 + hash(i * 5) * 9);
  }
  return toTex(c);
}
/* studio backdrop: warm pool of light falling off to black */
function backdropTex() {
  var s = 512, c = cnv(s, s), g = c.getContext('2d');
  g.fillStyle = '#050505'; g.fillRect(0, 0, s, s);
  var gr = g.createRadialGradient(s * 0.5, s * 0.62, 0, s * 0.5, s * 0.62, s * 0.58);
  gr.addColorStop(0.00, 'rgba(72,52,30,0.95)');
  gr.addColorStop(0.28, 'rgba(42,31,20,0.72)');
  gr.addColorStop(0.62, 'rgba(16,14,13,0.42)');
  gr.addColorStop(1.00, 'rgba(4,4,4,0)');
  g.fillStyle = gr; g.fillRect(0, 0, s, s);
  return toTex(c);
}
/* zardozi / brocade pattern for trims (gold on deep ground) */
function brocadeTex(ground, line) {
  var s = 256, c = cnv(s, s), g = c.getContext('2d');
  g.fillStyle = ground; g.fillRect(0, 0, s, s);
  g.strokeStyle = line; g.lineWidth = 2.2;
  for (var i = 0; i < 8; i++) {
    for (var j = 0; j < 8; j++) {
      var x = (i + 0.5) * s / 8, y = (j + 0.5) * s / 8;
      g.beginPath();
      for (var k = 0; k <= 16; k++) {
        var a = k / 16 * TAU, r = 9 + 5 * Math.sin(a * 4);
        var px = x + Math.cos(a) * r, py = y + Math.sin(a) * r * 0.7;
        if (k === 0) g.moveTo(px, py); else g.lineTo(px, py);
      }
      g.stroke();
      g.beginPath(); g.arc(x, y, 2.6, 0, TAU); g.fillStyle = line; g.fill();
    }
  }
  var t = toTex(c, true); t.repeat.set(6, 1); return t;
}

/* ---------------------------------------------------------------- 4 · geometry helpers */
function capsule(r, len, seg, capSeg) {
  seg = seg || 18; capSeg = capSeg || 8;
  var pts = [], i, a;
  for (i = 0; i <= capSeg; i++) { a = -Math.PI / 2 + (i / capSeg) * (Math.PI / 2); pts.push(new T.Vector2(Math.cos(a) * r, -len / 2 + Math.sin(a) * r)); }
  for (i = 0; i <= capSeg; i++) { a = (i / capSeg) * (Math.PI / 2); pts.push(new T.Vector2(Math.cos(a) * r, len / 2 + Math.sin(a) * r)); }
  return new T.LatheGeometry(pts, seg);
}
function lathe(profile2D, seg, smooth) {
  var pts = profile2D.map(function (p) { return p instanceof T.Vector2 ? p : new T.Vector2(p[0], p[1]); });
  if (smooth) {
    var sc = new T.SplineCurve(pts);
    pts = sc.getPoints(Math.max(18, pts.length * 3));
  }
  return new T.LatheGeometry(pts, seg || 40);
}
function roundedBox(w, h, d, r, seg) {
  seg = seg || 5;
  var g = new T.BoxGeometry(w, h, d, seg, seg, seg);
  var pos = g.attributes.position, v = new T.Vector3(), core = new T.Vector3(), dir = new T.Vector3();
  var hx = Math.max(0, w / 2 - r), hy = Math.max(0, h / 2 - r), hz = Math.max(0, d / 2 - r);
  for (var i = 0; i < pos.count; i++) {
    v.fromBufferAttribute(pos, i);
    core.set(clamp(v.x, -hx, hx), clamp(v.y, -hy, hy), clamp(v.z, -hz, hz));
    dir.copy(v).sub(core);
    if (dir.lengthSq() > 1e-9) { dir.normalize().multiplyScalar(r); v.copy(core).add(dir); }
    pos.setXYZ(i, v.x, v.y, v.z);
  }
  g.computeVertexNormals();
  return g;
}
/* generic parametric surface: fn(u,v,target) → Vector3 */
function parametric(fn, uSeg, vSeg) {
  uSeg = uSeg || 40; vSeg = vSeg || 30;
  var pos = [], uv = [], idx = [], p = new T.Vector3(), u, v, i, j;
  for (i = 0; i <= vSeg; i++) {
    v = i / vSeg;
    for (j = 0; j <= uSeg; j++) {
      u = j / uSeg;
      fn(u, v, p);
      pos.push(p.x, p.y, p.z); uv.push(u, 1 - v);
    }
  }
  for (i = 0; i < vSeg; i++) for (j = 0; j < uSeg; j++) {
    var a = i * (uSeg + 1) + j, b = a + 1, c = a + uSeg + 1, d = c + 1;
    idx.push(a, c, b, b, c, d);
  }
  var g = new T.BufferGeometry();
  g.setAttribute('position', new T.Float32BufferAttribute(pos, 3));
  g.setAttribute('uv', new T.Float32BufferAttribute(uv, 2));
  g.setIndex(idx);
  g.computeVertexNormals();
  return g;
}
/* ribbon swept along a 3D curve (sashes, pallus, gajra chains, braids) */
function ribbon(curve, widthFn, uSeg, vSeg, twistFn) {
  uSeg = uSeg || 60; vSeg = vSeg || 6;
  var up = V3(0, 1, 0), tan = V3(), side = V3(), nrm = V3(), p = V3(), out = V3();
  return parametric(function (u, v, target) {
    curve.getPointAt(u, p);
    curve.getTangentAt(u, tan);
    side.copy(tan).cross(up);
    if (side.lengthSq() < 1e-6) side.set(1, 0, 0);
    side.normalize();
    nrm.copy(side).cross(tan).normalize();
    if (twistFn) { var a = twistFn(u); side.applyAxisAngle(tan, a); nrm.applyAxisAngle(tan, a); }
    var w = widthFn(u, v);
    out.copy(p).addScaledVector(side, (v - 0.5) * w).addScaledVector(nrm, Math.sin(v * Math.PI) * w * 0.10);
    target.copy(out);
    return target;
  }, uSeg, vSeg);
}
function tubeFrom(points, r, seg, radial, closed) {
  var curve = new T.CatmullRomCurve3(points, !!closed, 'catmullrom', 0.5);
  return new T.TubeGeometry(curve, seg || 48, r, radial || 8, !!closed);
}
/* fur / plush displacement */
function fluff(geo, amp, freq) {
  var pos = geo.attributes.position, v = new T.Vector3();
  for (var i = 0; i < pos.count; i++) {
    v.fromBufferAttribute(pos, i);
    var n = noise3(v.x * freq, v.y * freq, v.z * freq) - 0.5;
    var m = noise3(v.x * freq * 2.7 + 9, v.y * freq * 2.7, v.z * freq * 2.7 + 4) - 0.5;
    var l = v.length() || 1;
    v.multiplyScalar(1 + (n * amp + m * amp * 0.45) / l);
    pos.setXYZ(i, v.x, v.y, v.z);
  }
  geo.computeVertexNormals();
  return geo;
}
/* radial fabric folds on a lathe skirt */
function folds(geo, count, amp, yFalloff) {
  var pos = geo.attributes.position, v = new T.Vector3();
  for (var i = 0; i < pos.count; i++) {
    v.fromBufferAttribute(pos, i);
    var a = Math.atan2(v.z, v.x);
    var f = 1 + Math.sin(a * count) * amp;
    var k = yFalloff ? Math.pow(clamp(1 - (v.y - yFalloff[0]) / (yFalloff[1] - yFalloff[0]), 0, 1), 1.4) : 1;
    v.x *= 1 + (f - 1) * k; v.z *= 1 + (f - 1) * k;
    pos.setXYZ(i, v.x, v.y, v.z);
  }
  geo.computeVertexNormals();
  return geo;
}
/* scatter N small meshes around a circle/helix (jasmine buds, zardozi dots) */
function scatterRing(count, fn) {
  var g = new T.Group();
  for (var i = 0; i < count; i++) { var m = fn(i / count, i); if (m) g.add(m); }
  return g;
}
function mesh(geo, mat, cast) {
  var m = new T.Mesh(geo, mat);
  m.castShadow = cast !== false;
  m.receiveShadow = false;
  return m;
}
function group(x, y, z) { var g = new T.Group(); g.position.set(x || 0, y || 0, z || 0); return g; }

/* ---------------------------------------------------------------- 5 · renderer + scene */
var canvas = document.getElementById('stage');
var renderer;
try {
  renderer = new T.WebGLRenderer({ canvas: canvas, antialias: true, alpha: true, powerPreference: 'high-performance' });
} catch (e) {
  offline('<b>WebGL is unavailable.</b><br/>Your browser or device blocked hardware acceleration. Try a desktop Chrome, Edge or Safari with WebGL enabled.');
  return;
}
renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
renderer.setSize(window.innerWidth, window.innerHeight, false);
renderer.setClearColor(0x000000, 0);
renderer.outputEncoding = T.sRGBEncoding;
renderer.toneMapping = T.ACESFilmicToneMapping;
renderer.toneMappingExposure = envFallback ? 1.05 : 1.0;
renderer.physicallyCorrectLights = false;
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = T.PCFSoftShadowMap;
renderer.autoClear = false;

var scene = new T.Scene();
scene.fog = new T.FogExp2(0x050506, 0.052);

var camera = new T.PerspectiveCamera(34, window.innerWidth / window.innerHeight, 0.08, 100);
camera.position.set(0, 1.42, 3.55);

var widgetCam = new T.PerspectiveCamera(30, 1, 0.05, 100);
widgetCam.position.set(0, 1.45, 1.05);

/* ---------- HDR studio environment (PMREM from a procedural softbox set) ---------- */
function buildEnvironment() {
  var pmrem = new T.PMREMGenerator(renderer);
  pmrem.compileEquirectangularShader();
  var es = new T.Scene();

  var dome = new T.Mesh(
    new T.SphereGeometry(14, 32, 24),
    new T.ShaderMaterial({
      side: T.BackSide,
      uniforms: {},
      vertexShader: [
        'varying vec3 vDir;',
        'void main(){ vDir = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }'
      ].join('\n'),
      fragmentShader: [
        'varying vec3 vDir;',
        'void main(){',
        '  vec3 d = normalize(vDir);',
        '  float h = clamp(d.y*0.5+0.5, 0.0, 1.0);',
        '  vec3 c = mix(vec3(0.008,0.008,0.010), vec3(0.050,0.048,0.058), h);',
        '  float key = pow(max(dot(d, normalize(vec3(0.60,0.50,0.62))), 0.0), 7.0);',
        '  c += vec3(0.62,0.40,0.17)*key*1.35;',
        '  float fill = pow(max(dot(d, normalize(vec3(-0.78,0.12,0.38))), 0.0), 8.0);',
        '  c += vec3(0.05,0.08,0.17)*fill*1.2;',
        '  float top = pow(max(dot(d, vec3(0.0,1.0,0.0)), 0.0), 5.0);',
        '  c += vec3(0.05,0.05,0.06)*top;',
        '  gl_FragColor = vec4(c,1.0);',
        '}'
      ].join('\n')
    })
  );
  es.add(dome);

  function softbox(w, h, pos, col) {
    var m = new T.Mesh(new T.PlaneGeometry(w, h), new T.MeshBasicMaterial({ color: LC(col), side: T.DoubleSide }));
    m.position.set(pos[0], pos[1], pos[2]);
    m.lookAt(0, 0.6, 0);
    es.add(m);
    return m;
  }
  softbox(7, 5, [4.6, 5.0, 5.2], new T.Color(7.2, 5.4, 3.1));   // warm key
  softbox(6, 6, [-6.4, 2.2, 3.4], new T.Color(0.55, 0.78, 1.35)); // cool fill
  softbox(1.4, 7, [0.4, 3.4, -7.0], new T.Color(9.5, 7.6, 4.6));  // hot rim strip
  softbox(1.0, 6, [-3.4, 2.6, -5.4], new T.Color(2.2, 1.5, 4.2)); // violet kicker
  softbox(8, 8, [0, 9.0, 0.5], new T.Color(1.05, 1.05, 1.15));    // overhead silk

  var rt = pmrem.fromScene(es, 0.035);
  dome.geometry.dispose(); dome.material.dispose();
  pmrem.dispose();
  return rt.texture;
}
/* Equirectangular canvas environment — used if PMREM is unavailable or
   produces a broken (NaN/black) probe on the host GPU.                     */
function equirectEnv() {
  /* painted small, then upscaled → soft blobs (no harsh mirror hotspots) */
  var sw = 256, sh = 128;
  var small = cnv(sw, sh), g = small.getContext('2d');
  var gr = g.createLinearGradient(0, 0, 0, sh);
  gr.addColorStop(0.00, '#1c1c26');
  gr.addColorStop(0.30, '#0d0d12');
  gr.addColorStop(0.58, '#08080b');
  gr.addColorStop(1.00, '#040405');
  g.fillStyle = gr; g.fillRect(0, 0, sw, sh);
  function blob(x, y, rx, ry, col, a) {
    var m = Math.max(rx, ry);
    var rg = g.createRadialGradient(x, y, 0, x, y, m);
    rg.addColorStop(0, col);
    rg.addColorStop(0.45, col.replace(/,[\d.]+\)$/, ',0.30)'));
    rg.addColorStop(1, 'rgba(0,0,0,0)');
    g.save();
    g.globalAlpha = a;
    g.translate(x, y); g.scale(rx / m, ry / m); g.translate(-x, -y);
    g.fillStyle = rg;
    g.beginPath(); g.arc(x, y, m, 0, TAU); g.fill();
    g.restore();
  }
  blob(74, 38, 78, 54, 'rgba(255,214,160,1)', 0.62);   /* warm key      */
  blob(192, 56, 58, 42, 'rgba(150,180,255,1)', 0.34);  /* cool fill     */
  blob(128, 26, 28, 80, 'rgba(255,236,195,1)', 0.40);  /* overhead silk */
  blob(34, 52, 34, 26, 'rgba(255,200,150,1)', 0.24);   /* kicker        */
  blob(150, 84, 80, 22, 'rgba(120,96,64,1)', 0.14);    /* floor bounce  */
  var c = cnv(1024, 512);
  c.getContext('2d').drawImage(small, 0, 0, 1024, 512);
  var t = new T.CanvasTexture(c);
  t.mapping = T.EquirectangularReflectionMapping;
  t.encoding = T.sRGBEncoding;
  return t;
}

/* Some software / limited GPUs produce a broken PMREM probe (NaNs that turn
   every PBR material black). Probe it once and fall back if it is dead.      */
function envIsUsable(tex) {
  try {
    var rt = new T.WebGLRenderTarget(4, 4);
    var s = new T.Scene();
    var m = new T.Mesh(new T.SphereGeometry(1, 10, 8),
      new T.MeshStandardMaterial({ color: LC(0x808080), roughness: 0.5, metalness: 0.0 }));
    s.add(m);
    s.environment = tex;
    var c2 = new T.PerspectiveCamera(45, 1, 0.1, 10);
    c2.position.set(0, 0, 3); c2.lookAt(0, 0, 0);
    var prevTarget = renderer.getRenderTarget();
    var prevColor = new T.Color(), prevAlpha = renderer.getClearAlpha();
    renderer.getClearColor(prevColor);
    renderer.setClearColor(0x000000, 1);
    renderer.setRenderTarget(rt);
    renderer.clear(true, true, true);
    renderer.render(s, c2);
    var px = new Uint8Array(4 * 4 * 4);
    renderer.readRenderTargetPixels(rt, 0, 0, 4, 4, px);
    renderer.setRenderTarget(prevTarget);
    renderer.setClearColor(prevColor, prevAlpha);
    var sum = 0;
    for (var i = 0; i < px.length; i += 4) sum += px[i] + px[i + 1] + px[i + 2];
    m.geometry.dispose(); m.material.dispose(); rt.dispose();
    return sum > 24;
  } catch (e) { return false; }
}

var envMap = null, envFallback = false;
try {
  var probe = buildEnvironment();
  if (envIsUsable(probe)) envMap = probe;
  else { envFallback = true; if (probe.dispose) probe.dispose(); }
} catch (e) { envFallback = true; }
if (!envMap) { envMap = equirectEnv(); envFallback = true; }
scene.environment = envMap;

/* ---------- lights: warm key · cool fill · hot rim ---------- */
var studio = new T.Group();     // hidden during the widget pass
scene.add(studio);

var hemi = new T.HemisphereLight(LC(0x3A4763), LC(0x120C08), envFallback ? 0.72 : 0.60);
scene.add(hemi);

var keyLight = new T.DirectionalLight(LC(0xFFD7A2), envFallback ? 3.20 : 2.70);
keyLight.position.set(2.7, 3.7, 3.3);
keyLight.castShadow = true;
keyLight.shadow.mapSize.width = 2048;
keyLight.shadow.mapSize.height = 2048;
keyLight.shadow.camera.near = 0.5;
keyLight.shadow.camera.far = 14;
keyLight.shadow.camera.left = -2.6; keyLight.shadow.camera.right = 2.6;
keyLight.shadow.camera.top = 3.2; keyLight.shadow.camera.bottom = -0.6;
keyLight.shadow.bias = -0.0009;
keyLight.shadow.radius = 3.2;
keyLight.userData.base = keyLight.intensity;   /* animated ±2 % in tick() */
scene.add(keyLight);

var fillLight = new T.DirectionalLight(LC(0x9FB4FF), envFallback ? 0.72 : 0.64);
fillLight.position.set(-3.4, 1.5, 2.6);
scene.add(fillLight);

var rimLight = new T.SpotLight(LC(0xFFE2AF), envFallback ? 4.80 : 4.30, 14, 0.72, 0.62, 1.2);
rimLight.position.set(-0.7, 3.1, -3.6);
rimLight.target.position.set(0, 1.25, 0);
scene.add(rimLight); scene.add(rimLight.target);

var rimCool = new T.DirectionalLight(LC(0xB79CFF), envFallback ? 0.82 : 0.74);
rimCool.position.set(-2.6, 1.9, -3.2);
scene.add(rimCool);

var bounce = new T.PointLight(LC(0xFFC489), envFallback ? 1.05 : 0.92, 4.5, 2);
bounce.position.set(0.2, 0.55, 1.35);
scene.add(bounce);

/* ---------- studio floor, backdrop, rings ---------- */
var floor = new T.Mesh(
  new T.CircleGeometry(7, 64),
  new T.MeshStandardMaterial({ color: LC(0x09090B), roughness: 0.46, metalness: 0.52, envMapIntensity: 0.70 })
);
floor.rotation.x = -Math.PI / 2;
floor.receiveShadow = true;
studio.add(floor);

var poolTex = radialTex('rgba(200,169,106,0.30)', 'rgba(200,169,106,0.05)', 512, 0.30);
var pool = new T.Mesh(new T.CircleGeometry(2.1, 48), new T.MeshBasicMaterial({
  map: poolTex, transparent: true, blending: T.AdditiveBlending, depthWrite: false, opacity: 0.85
}));
pool.rotation.x = -Math.PI / 2; pool.position.y = 0.004;
studio.add(pool);

var ringMat = new T.MeshBasicMaterial({ color: LC(0xC8A96A), transparent: true, opacity: 0.30, blending: T.AdditiveBlending, depthWrite: false });
var ring1 = new T.Mesh(new T.RingGeometry(1.52, 1.545, 128), ringMat);
ring1.rotation.x = -Math.PI / 2; ring1.position.y = 0.006;
studio.add(ring1);
var ring2 = new T.Mesh(new T.RingGeometry(1.92, 1.935, 128), ringMat.clone());
ring2.material.opacity = 0.14;
ring2.rotation.x = -Math.PI / 2; ring2.position.y = 0.006;
studio.add(ring2);

var backdrop = new T.Mesh(
  new T.PlaneGeometry(20, 12),
  new T.MeshBasicMaterial({ map: backdropTex(), side: T.DoubleSide, transparent: true, opacity: 0.9, depthWrite: false })
);
backdrop.position.set(0, 4.2, -5.0);
studio.add(backdrop);

/* ground shadow catcher (soft contact shadow under the character) */
var contactTex = radialTex('rgba(0,0,0,0.62)', 'rgba(0,0,0,0.18)', 256, 0.35);
var contact = new T.Mesh(new T.CircleGeometry(0.92, 40), new T.MeshBasicMaterial({
  map: contactTex, transparent: true, opacity: 0.75, depthWrite: false
}));
contact.rotation.x = -Math.PI / 2; contact.position.y = 0.008;
studio.add(contact);

/* ---------------------------------------------------------------- 6 · sparkles */
function Sparkles(count, radius, height, color, size) {
  var geo = new T.BufferGeometry();
  var arr = new Float32Array(count * 3), seeds = new Float32Array(count);
  for (var i = 0; i < count; i++) {
    var a = Math.random() * TAU, r = radius * (0.25 + Math.random() * 0.75);
    arr[i * 3] = Math.cos(a) * r; arr[i * 3 + 1] = Math.random() * height; arr[i * 3 + 2] = Math.sin(a) * r;
    seeds[i] = Math.random();
  }
  geo.setAttribute('position', new T.BufferAttribute(arr, 3));
  var mat = new T.PointsMaterial({
    size: size || 0.035, map: radialTex('rgba(255,240,205,1)', 'rgba(255,205,130,0.25)', 128, 0.22),
    color: LC(color || 0xFFE0A8), transparent: true, opacity: 0, blending: T.AdditiveBlending,
    depthWrite: false, sizeAttenuation: true
  });
  this.points = new T.Points(geo, mat);
  this.seeds = seeds; this.height = height; this.count = count;
  this.intensity = 0;
}
Sparkles.prototype.update = function (t, dt) {
  var pos = this.points.geometry.attributes.position, arr = pos.array;
  for (var i = 0; i < this.count; i++) {
    var s = this.seeds[i];
    arr[i * 3 + 1] += (0.045 + s * 0.10) * dt * (0.4 + this.intensity);
    if (arr[i * 3 + 1] > this.height) arr[i * 3 + 1] = 0;
  }
  pos.needsUpdate = true;
  this.points.material.opacity = damp(this.points.material.opacity, this.intensity * 0.85, 3, dt);
  this.points.rotation.y = t * 0.12;
};

/* ---------------------------------------------------------------- exports (filled later) */
window.HBStudio = {
  THREE: T, scene: scene, renderer: renderer, camera: camera, envMap: envMap,
  utils: {
    V3: V3, C: C, clamp: clamp, lerp: lerp, damp: damp, capsule: capsule, lathe: lathe,
    roundedBox: roundedBox, parametric: parametric, ribbon: ribbon, tubeFrom: tubeFrom,
    fluff: fluff, folds: folds, mesh: mesh, group: group, eyeTex: eyeTex, iridTex: iridTex,
    radialTex: radialTex, gradTex: gradTex, brocadeTex: brocadeTex, noise3: noise3, scatterRing: scatterRing
  },
  mats: {
    skin: skinMat, gold: goldMat, velvet: velvetMat, silk: silkMat, hair: hairMat,
    gloss: glossMat, crystal: crystalMat, pearl: pearlMat, matte: matteMat, glow: glowMat
  },
  characters: [],
  buildCharacter: null,
  progress: progress,
  studio: studio,
  lights: { hemi: hemi, key: keyLight, fill: fillLight, rim: rimLight, rimCool: rimCool, bounce: bounce },
  setBloom: null,          /* filled by 05_app.js when the composer exists */
  Sparkles: Sparkles
};

/* continue in 03_rig.js */
window.__HBS = {
  envFallback: envFallback,
  T: T, scene: scene, renderer: renderer, camera: camera, widgetCam: widgetCam, studio: studio,
  envMap: envMap, V3: V3, C: C, clamp: clamp, lerp: lerp, damp: damp,
  capsule: capsule, lathe: lathe, roundedBox: roundedBox, parametric: parametric, ribbon: ribbon,
  tubeFrom: tubeFrom, fluff: fluff, folds: folds, mesh: mesh, group: group, scatterRing: scatterRing,
  eyeTex: eyeTex, iridTex: iridTex, radialTex: radialTex, gradTex: gradTex, brocadeTex: brocadeTex, noise3: noise3,
  skinMat: skinMat, goldMat: goldMat, velvetMat: velvetMat, silkMat: silkMat, hairMat: hairMat,
  glossMat: glossMat, crystalMat: crystalMat, pearlMat: pearlMat, matteMat: matteMat, glowMat: glowMat,
  Sparkles: Sparkles, progress: progress, offline: offline,
  keyLight: keyLight, fillLight: fillLight, rimLight: rimLight, hemi: hemi, rimCool: rimCool,
  bounce: bounce, floor: floor, backdrop: backdrop, ring1: ring1, ring2: ring2, pool: pool
};
})();
