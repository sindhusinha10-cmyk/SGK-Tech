/* =====================================================================
   05 · APPLICATION — camera, transitions, UI, widget, loop
   ===================================================================== */
(function () {
'use strict';
var U = window.__HBS, T = U.T;
var V3 = U.V3, C = U.C, LC = U.C, clamp = U.clamp, lerp = U.lerp, damp = U.damp;
var scene = U.scene, renderer = U.renderer, camera = U.camera, widgetCam = U.widgetCam, studio = U.studio;
var HBS = window.HBStudio;

var ORDER = ['asha', 'mochi', 'noor', 'tara', 'gia', 'meera', 'cherry'];
var WIDGET_DIST = { asha: 1.34, mochi: 1.86, noor: 1.30, tara: 1.36, gia: 1.52, meera: 1.34, cherry: 1.05 };
var WIDGET_LIFT = { asha: 0.02, mochi: 0.13, noor: 0.02, tara: 0.04, gia: 0.06, meera: 0.02, cherry: 0.05 };
var chars = {};
var current = null;
var sweeping = false;
var dualView = true;
var autoOrbit = false;

/* ------------------------------------------------------------------ DOM */
var $ = function (s) { return document.querySelector(s); };
var dockInner = $('#dockInner'), elName = $('#cName'), elTitle = $('#cTitle'), elDesc = $('#cDesc'),
    elTags = $('#cTags'), elSpecs = $('#cSpecs'), elIdx = $('#idxNum'), elWidget = $('#widget'),
    elWName = $('#wName'), elHint = $('#hint'), elFlash = $('#flash'), elGlow = $('#cursorGlow'),
    btnDual = $('#btnDual'), btnOrbit = $('#btnOrbit'), loader = $('#loader');

/* ------------------------------------------------------------- controls */
var controls = null;
var camState = { az: 0.20, el: 0.10, dist: 3.6, ty: 1.14 };
var smoothCam = { az: 0.20, el: 0.10, dist: 3.6, ty: 1.14 };

if (T.OrbitControls) {
  controls = new T.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.075;
  controls.enablePan = false;
  controls.rotateSpeed = 0.62;
  controls.zoomSpeed = 0.72;
  controls.minDistance = 1.35;
  controls.maxDistance = 6.2;
  controls.minPolarAngle = 0.55;
  controls.maxPolarAngle = 1.60;
  controls.autoRotateSpeed = 0.55;
  controls.target.set(0, 1.14, 0);
} else {
  /* ultra-light fallback drag-orbit so the page still works without the CDN extra */
  (function () {
    var down = false, lx = 0, ly = 0;
    var el = renderer.domElement;
    el.addEventListener('pointerdown', function (e) { down = true; lx = e.clientX; ly = e.clientY; el.setPointerCapture(e.pointerId); });
    el.addEventListener('pointerup', function (e) { down = false; });
    el.addEventListener('pointermove', function (e) {
      if (!down) return;
      camState.az -= (e.clientX - lx) * 0.006;
      camState.el = clamp(camState.el + (e.clientY - ly) * 0.004, -0.12, 0.85);
      lx = e.clientX; ly = e.clientY;
    });
    el.addEventListener('wheel', function (e) { camState.dist = clamp(camState.dist + e.deltaY * 0.0016, 1.4, 6); e.preventDefault(); }, { passive: false });
  })();
}

/* Measure each character once, then frame it from its real bounding box so
   nobody is ever cropped — works for the 1.78 m humans and 1.58 m bunny.     */
function measure(c) {
  if (c._h !== undefined) return c;
  c.rig.root.updateMatrixWorld(true);
  var box = new T.Box3().setFromObject(c.rig.root);
  /* models stream in async — a measurement of an empty box must not be cached,
     or the camera keeps framing a 0.6 m object at floor level for ever */
  if (box.isEmpty()) return c;
  var s2 = box.getSize(new T.Vector3()), ctr = box.getCenter(new T.Vector3());
  /* Box3.setFromObject uses the BIND pose, which morph-animated models
     (flamingo, parrot) inflate badly — the camera then framed a phantom size
     and they rendered as specks. We auto-scale each model to a known height,
     so trust that over the raw box when they disagree. */
  var th = c._targetH;
  c._h = th || Math.max(s2.y, 0.6);
  c._w = Math.min(Math.max(s2.x, 0.4), c._h * 1.25);
  c._cy = (th && Math.abs(s2.y - th) > th * 0.45) ? th * 0.52 : ctr.y;
  return c;
}
function cyOf(c) {
  return (c._cy !== undefined) ? c._cy : (c._targetH ? c._targetH * 0.52 : 0.90);
}
function fitDist(c) {
  measure(c);
  var f = c.frame;
  if (f.fov && camera.fov !== f.fov) { camera.fov = f.fov; camera.updateProjectionMatrix(); }
  var h = (c._h !== undefined) ? c._h : (c._targetH || 1.75);
  var w = (c._w !== undefined) ? c._w : 0.55;
  var tan = Math.tan((camera.fov * Math.PI / 180) / 2);
  var dH = (h / f.fill / 2) / tan;
  /* cap the width term: spread-wing models (flamingo, parrot) are far wider
     than tall and were pushing the camera so far back they read as specks */
  var vw = Math.max(Math.min(w, h * 0.95) / 0.74, h * 0.40);
  var dW = (vw / 2) / (tan * camera.aspect);
  var d = Math.max(dH, dW);
  if (window.innerWidth < 860) d *= 0.94;
  return clamp(d, 1.6, 9);
}
function readCam() {
  if (!controls) return;
  var o = V3().copy(camera.position).sub(controls.target);
  camState.dist = o.length();
  camState.el = Math.asin(clamp(o.y / camState.dist, -1, 1));
  camState.az = Math.atan2(o.x, o.z);
  camState.ty = controls.target.y;
}
function applyCam() {
  var d = camState.dist, e = camState.el, a = camState.az;
  var h = d * Math.cos(e);
  camera.position.set(Math.sin(a) * h, camState.ty + d * Math.sin(e), Math.cos(a) * h);
  if (controls) { controls.target.y = camState.ty; controls.target.x = 0; controls.target.z = 0; }
  camera.lookAt(0, camState.ty, 0);
}

/* --------------------------------------------------------------- composer */
var composer = null, bloom = null;
if (T.EffectComposer && T.RenderPass && T.UnrealBloomPass) {
  try {
    composer = new T.EffectComposer(renderer);
    composer.addPass(new T.RenderPass(scene, camera));
    bloom = new T.UnrealBloomPass(new T.Vector2(window.innerWidth, window.innerHeight), 0.40, 0.42, 0.92);
    composer.addPass(bloom);
  } catch (e) { composer = null; }
}

/* ------------------------------------------------------- studio backdrop */
var backdropDome = new T.Mesh(
  new T.SphereGeometry(34, 32, 24),
  new T.ShaderMaterial({
    side: T.BackSide, depthWrite: false,
    uniforms: { uTop: { value: U.C(0x191722) }, uBot: { value: U.C(0x050507) }, uWarm: { value: U.C(0x402E1A) } },
    vertexShader: 'varying vec3 vD; void main(){ vD = normalize(position); gl_Position = projectionMatrix * modelViewMatrix * vec4(position,1.0); }',
    fragmentShader: [
      'varying vec3 vD; uniform vec3 uTop; uniform vec3 uBot; uniform vec3 uWarm;',
      'void main(){',
      '  vec3 d = normalize(vD);',
      '  float h = clamp(d.y*0.5+0.5, 0.0, 1.0);',
      '  vec3 c = mix(uBot, uTop, pow(h, 0.85));',
      '  float g = pow(max(dot(d, normalize(vec3(0.30,0.12,0.94))), 0.0), 4.5);',
      '  c += uWarm * g * 0.85;',
      '  float g2 = pow(max(dot(d, normalize(vec3(-0.85,0.10,0.40))), 0.0), 6.0);',
      '  c += vec3(0.05,0.07,0.14) * g2;',
      '  gl_FragColor = vec4(c, 1.0);',
      '}'
    ].join('\n')
  })
);
backdropDome.renderOrder = -10;
studio.add(backdropDome);

/* ------------------------------------------------------------- characters */
function buildOne(id) {
  if (chars[id]) return chars[id];
  var c = U.builders[id]();
  c.rig.root.visible = false;
  c.rig.collectMaterials();
  scene.add(c.rig.root);
  chars[id] = c;
  /* models stream in asynchronously — re-measure once one lands */
  if (typeof c.ready === 'boolean') {
    c.onReady = function () {
      try { c.rig.collectMaterials(); } catch (e) {}
      /* the camera was framed against an empty rig — re-aim it now the
         geometry exists, whether this is the boot character or a later switch */
      try {
        c._h = undefined; c._w = undefined; c._cy = undefined;
        if (!current || current === c) reframeCurrent(current ? 1.2 : 0);
      } catch (e) {}
    };
  }
  return c;
}

/* ------------------------------------------------------------- switching */
function reframeCurrent(dur) {
  if (!current) return;
  current._h = undefined; current._w = undefined; current._cy = undefined;
  measure(current);
  var d = fitDist(current), f = current.frame;
  if (dur) {
    sweeping = true;
    window.gsap.to(camState, {
      dist: d, el: f.el, ty: cyOf(current), duration: dur, ease: 'power3.inOut',
      onComplete: function () { sweeping = false; readCam(); }
    });
  } else {
    camState.dist = d; camState.el = f.el; camState.ty = cyOf(current);
    applyCam(); readCam();
  }
}
HBS.reframe = function (d) { if (current) reframeCurrent(d === undefined ? 1.0 : d); };
window.__HBS_ACTIVE = function () { return current; };

function switchTo(id, instant) {
  if (!chars[id]) buildOne(id);
  if (current && current.id === id) return;
  var next = chars[id];
  var first = !current;
  var prev = current;

  measure(next);
  var f = next.frame;
  var toDist = fitDist(next), toEl = f.el, toTy = cyOf(next);
  var dir = (Math.random() < 0.5 ? 1 : -1);

  if (prev) {
    sweeping = true;
    if (controls) controls.enabled = false;
    var tl = window.gsap.timeline({
      onComplete: function () {
        sweeping = false;
        if (controls) { controls.enabled = true; }
        readCam();
      }
    });
    tl.to(elFlash, { opacity: 0.85, duration: 0.26, ease: 'power2.out' }, 0);
    tl.add(function () {
      prev.rig.root.visible = false;
      next.rig.root.visible = true;
      next.rig.root.scale.setScalar(0.88);
      next.rig.root.position.y = -0.07;
      window.gsap.to(next.rig.root.scale, { x: 1, y: 1, z: 1, duration: 1.35, ease: 'elastic.out(1, 0.62)' });
      window.gsap.to(next.rig.root.position, { y: 0, duration: 1.1, ease: 'power3.out' });
      paintInfo(next);
    }, 0.16);
    tl.to(elFlash, { opacity: 0, duration: 0.85, ease: 'power2.inOut' }, 0.30);
    /* cinematic camera sweep */
    window.gsap.to(camState, {
      az: camState.az + dir * 1.15, el: toEl, dist: toDist, ty: toTy,
      duration: 1.75, ease: 'power3.inOut'
    });
    /* ground pulse */
    pulseRing();
  } else {
    next.rig.root.visible = true;
    paintInfo(next);
  }
  current = next;
  next.rig.setEmotion(next.rig.emotion === 'poise' ? 'poise' : next.rig.emotion, instant ? 0 : 0.9);

  /* pills */
  Array.prototype.forEach.call(dockInner.children, function (p) {
    p.classList.toggle('active', p.dataset.id === id);
  });
  if (elWName) elWName.textContent = next.name;
  hideHint();
}

var pulse = new T.Mesh(new T.RingGeometry(0.55, 0.60, 96), new T.MeshBasicMaterial({
  color: LC(0xC8A96A), transparent: true, opacity: 0, blending: T.AdditiveBlending, depthWrite: false, side: T.DoubleSide
}));
pulse.rotation.x = -Math.PI / 2;
pulse.position.y = 0.02;
studio.add(pulse);
function pulseRing() {
  window.gsap.killTweensOf(pulse.scale);
  window.gsap.killTweensOf(pulse.material);
  pulse.scale.setScalar(0.5);
  pulse.material.opacity = 0.75;
  window.gsap.to(pulse.scale, { x: 3.0, y: 3.0, z: 3.0, duration: 1.4, ease: 'power2.out' });
  window.gsap.to(pulse.material, { opacity: 0, duration: 1.4, ease: 'power2.out' });
}

function paintInfo(c) {
  var i = ORDER.indexOf(c.id);
  elName.textContent = c.name;
  elTitle.textContent = c.title;
  elDesc.textContent = c.desc;
  elIdx.textContent = ('0' + (i + 1)).slice(-2);
  elTags.innerHTML = c.tags.map(function (t) { return '<span class="tag">' + t + '</span>'; }).join('');
  elSpecs.innerHTML = c.specs.map(function (s) {
    return '<div class="spec"><i>' + s[0] + '</i><b>' + s[1] + '</b></div>';
  }).join('');
  window.gsap.fromTo([elIdx.parentNode, elName, elTitle, elDesc, elTags, elSpecs],
    { y: 16, opacity: 0 },
    { y: 0, opacity: 1, duration: 0.85, stagger: 0.055, ease: 'power3.out', overwrite: true });
}

/* ------------------------------------------------------------- emotions */
var emoBtns = Array.prototype.slice.call(document.querySelectorAll('.emo'));
function setEmotion(name) {
  if (!current) return;
  if (current.rig.emotion === name) name = 'poise';
  current.rig.setEmotion(name, 1.1);
  emoBtns.forEach(function (b) { b.classList.toggle('active', b.dataset.emo === name); });
  hideHint();
}
emoBtns.forEach(function (b) {
  b.addEventListener('click', function () { setEmotion(b.dataset.emo); });
});
var EMO_CYCLE = ['welcome', 'happy', 'thinking', 'hesitant'];

/* ------------------------------------------------------------- toggles */
function setDual(on) {
  dualView = on;
  elWidget.classList.toggle('on', on);
  btnDual.classList.toggle('active', on);
}
function setOrbit(on) {
  autoOrbit = on;
  if (controls) controls.autoRotate = on;
  btnOrbit.classList.toggle('active', on);
}
btnDual.addEventListener('click', function () { setDual(!dualView); });
btnOrbit.addEventListener('click', function () { setOrbit(!autoOrbit); });

/* ------------------------------------------------------------- pointer */
var mouse = { x: 0, y: 0 };
var glowOn = false;
function pointerMove(cx, cy) {
  mouse.x = (cx / window.innerWidth) * 2 - 1;
  mouse.y = -((cy / window.innerHeight) * 2 - 1);
  if (elGlow) {
    if (!glowOn) { glowOn = true; elGlow.style.opacity = '1'; }
    elGlow.style.transform = 'translate3d(' + cx + 'px,' + cy + 'px,0)';
  }
}
window.addEventListener('pointermove', function (e) { pointerMove(e.clientX, e.clientY); }, { passive: true });
window.addEventListener('pointerdown', function () { hideHint(); });
window.addEventListener('keydown', function (e) {
  var k = e.key;
  if (k >= '1' && k <= '7') { switchTo(ORDER[parseInt(k, 10) - 1]); }
  if (k === 'h') {
    document.body.classList.toggle('clean-ui');
    var cb = document.getElementById('cleanBtn');
    if (cb) cb.textContent = document.body.classList.contains('clean-ui') ? 'Show UI' : 'Clean view';
  }
  else if (k === 'e' || k === 'E') {
    var i = EMO_CYCLE.indexOf(current ? current.rig.emotion : 'poise');
    setEmotion(EMO_CYCLE[(i + 1) % EMO_CYCLE.length]);
  } else if (k === 'd' || k === 'D') { setDual(!dualView); }
  else if (k === 'o' || k === 'O') { setOrbit(!autoOrbit); }
});

var hintTimer = setTimeout(hideHint, 9000);
function hideHint() { if (hintTimer) clearTimeout(hintTimer); elHint.classList.add('hide'); }

/* ------------------------------------------------------------- resize */
function resize() {
  var w = window.innerWidth, h = window.innerHeight;
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.setSize(w, h, false);
  camera.aspect = w / h;
  camera.updateProjectionMatrix();
  if (composer) composer.setSize(w, h);
  if (bloom) bloom.setSize(w, h);
  if (current && !sweeping) {
    camState.dist = fitDist(current);
  }
}
window.addEventListener('resize', resize);
window.addEventListener('orientationchange', function () { setTimeout(resize, 260); });

function widgetRect() {
  var wv = elWidget.querySelector('.wv');
  var r = wv.getBoundingClientRect();
  return { x: r.left, y: window.innerHeight - r.bottom, w: r.width, h: r.height };
}

/* ------------------------------------------------------------- loop */
var clock = new T.Clock();
var started = false;
var sparkles = new U.Sparkles(150, 0.85, 2.0, 0xFFDCA0, 0.030);
sparkles.points.position.y = 0.1;
scene.add(sparkles.points);

function tick() {
  requestAnimationFrame(tick);
  var dt = Math.min(clock.getDelta(), 0.05);
  var t = clock.elapsedTime;

  /* camera */
  if (sweeping || !controls) applyCam();
  else { if (controls) { controls.update(); readCam(); } }

  /* character */
  if (current) {
    current.rig.lookTarget(mouse.x, mouse.y);
    current.rig.update(t, dt);
    if (current.updateModel) current.updateModel(dt);
    sparkles.intensity = current.rig.pose.sparkle;
    sparkles.points.visible = sparkles.points.material.opacity > 0.01 || sparkles.intensity > 0.02;
  }
  sparkles.update(t, dt);

  /* widget camera — slow drifting head-and-shoulders framing */
  if (dualView) {
    var d = WIDGET_DIST[current ? current.id : 'asha'] || 1.34;
    var hy = (current ? current.rig.head.position.y : 1.53) + (WIDGET_LIFT[current ? current.id : 'asha'] || 0);
    var az = Math.sin(t * 0.33) * 0.55 + 0.14;
    var el = 0.05 + Math.sin(t * 0.47) * 0.035;
    var hh = d * Math.cos(el);
    widgetCam.position.set(Math.sin(az) * hh, hy + Math.sin(el) * d - 0.03, Math.cos(az) * hh);
    widgetCam.lookAt(0, hy - 0.05, 0);
  }

  /* subtle light breathing */
  var kb = U.keyLight.userData.base;
  U.keyLight.intensity = kb * (1 + Math.sin(t * 0.9) * 0.024);

  /* ---- draw ---- */
  var w = window.innerWidth, h = window.innerHeight;
  renderer.setScissorTest(false);
  renderer.setViewport(0, 0, w, h);
  if (composer) { renderer.clear(true, true, true); composer.render(); }
  else { renderer.clear(true, true, true); renderer.render(scene, camera); }

  if (dualView) {
    var r = widgetRect();
    if (r.w > 12 && r.h > 12) {
      studio.visible = false;
      renderer.setViewport(r.x, r.y, r.w, r.h);
      renderer.setScissor(r.x, r.y, r.w, r.h);
      renderer.setScissorTest(true);
      renderer.clear(true, true, false);
      renderer.render(scene, widgetCam);
      renderer.setScissorTest(false);
      studio.visible = true;
    }
  }
}

/* ------------------------------------------------- info card / clean view */
(function () {
  var infoEl = document.getElementById('info');
  var infoTog = document.getElementById('infoToggle');
  var cleanBtn = document.getElementById('cleanBtn');
  function setCollapsed(on) {
    if (!infoEl) return;
    infoEl.classList.toggle('collapsed', on);
    if (infoTog) infoTog.textContent = on ? '+' : '\u2013';
  }
  if (infoTog) infoTog.addEventListener('click', function () {
    setCollapsed(!(infoEl && infoEl.classList.contains('collapsed')));
  });
  if (cleanBtn) cleanBtn.addEventListener('click', function () {
    document.body.classList.toggle('clean-ui');
    cleanBtn.textContent = document.body.classList.contains('clean-ui') ? 'Show UI' : 'Clean view';
  });
  /* on short or narrow viewports the card covers the character — open closed */
  if (window.innerWidth < 1000 || window.innerHeight < 720) setCollapsed(true);
})();

/* --------------------------------------------------------- selector dock */
function buildDock() {
  dockInner.innerHTML = '';
  ORDER.forEach(function (id, i) {
    var c = buildOne(id);
    var b = document.createElement('button');
    b.type = 'button';
    b.className = 'pill' + (i === 0 ? ' active' : '');
    b.dataset.id = id;
    b.innerHTML =
      '<span class="swatch" style="--c1:' + c.swatch[0] + ';--c2:' + c.swatch[1] + '"></span>' +
      '<span class="txt"><b>' + c.name + '</b><i>' + c.title.replace(/^The\s+/, '') + '</i></span>' +
      '<span class="num">' + ('0' + (i + 1)).slice(-2) + '</span>';
    b.addEventListener('click', function () { switchTo(id); });
    dockInner.appendChild(b);
  });
}

/* ------------------------------------------------------------- boot */
function boot() {
  U.progress(0.20);
  buildOne('asha');
  U.progress(0.35);
  buildDock();
  U.progress(0.55);
  resize();
  switchTo('asha', true);
  /* wide establishing shot, then settle */
  measure(current);
  camState.dist = fitDist(current) * 1.5;
  camState.el = 0.26;
  camState.az = -0.85;
  camState.ty = cyOf(current);
  applyCam();
  current.rig.root.scale.setScalar(0.92);
  current.rig.root.position.y = -0.05;

  tick();

  sweeping = true;
  window.gsap.to(camState, {
    dist: fitDist(current), el: current.frame.el, az: 0.20, ty: cyOf(current),
    duration: 2.6, ease: 'power3.inOut',
    onComplete: function () { sweeping = false; readCam(); }
  });
  window.gsap.to(current.rig.root.scale, { x: 1, y: 1, z: 1, duration: 1.8, ease: 'power3.out' });
  window.gsap.to(current.rig.root.position, { y: 0, duration: 1.4, ease: 'power3.out' });

  setDual(true);
  U.progress(1);

  setTimeout(function () {
    loader.classList.add('done');
    pulseRing();
  }, 260);

  /* build the remaining concierges in the background */
  var rest = ORDER.slice(1), i = 0;
  (function nextBuild() {
    if (i >= rest.length) { U.progress(1); return; }
    var id = rest[i++];
    buildOne(id);
    U.progress(0.55 + 0.45 * (i / rest.length));
    setTimeout(nextBuild, 130);
  })();
}

/* ------------------------------------------------------------- export API */
HBS.controls = controls;
HBS.fitDist = fitDist;
HBS.measure = measure;
HBS.readCam = readCam;
HBS.applyCam = applyCam;
HBS.camState = camState;
HBS.frameCharacter = function (id, instant) { switchTo(id, instant); };
HBS.reframe = function (id, extra) {
  var c = id ? chars[id] : current; if (!c) return null;
  var f = c.frame;
  camState.az = 0; camState.el = f.el; camState.ty = c._cy;
  camState.dist = fitDist(c) * (extra || 1);
  applyCam(); readCam(); return camState;
};
HBS.setBloom = function (strength, radius, threshold) {
  if (!bloom) return null;
  if (strength !== undefined) bloom.strength = strength;
  if (radius !== undefined) bloom.radius = radius;
  if (threshold !== undefined) bloom.threshold = threshold;
  return { strength: bloom.strength, radius: bloom.radius, threshold: bloom.threshold };
};
HBS.composer = function () { return composer; };
HBS.bloomPass = function () { return bloom; };

HBS.CHARACTERS = ORDER;
HBS.list = function () { return ORDER.slice(); };
HBS.get = function (id) { return chars[id] || null; };
HBS.active = function () { return current; };
HBS.buildCharacter = function (id) {
  var f = U.builders[id];
  if (!f) { console.warn('[HBStudio] unknown character "' + id + '" — falling back to asha'); f = U.builders.asha; }
  var c = f();
  c.rig.collectMaterials();
  /* handy standalone helpers on every character object */
  c.setEmotion = function (n) { c.rig.setEmotion(n); return c; };
  c.lookAt = function (x, y) { c.rig.lookTarget(x, y); return c; };
  c.update = function (time, delta) { c.rig.update(time, delta === undefined ? 0.016 : delta); return c; };
  c.show = function () { c.rig.root.visible = true; return c; };
  c.hide = function () { c.rig.root.visible = false; return c; };
  return c;
};
HBS.createLights = function (target) {
  target = target || new T.Scene();
  target.environment = U.envMap;
  var hemi = new T.HemisphereLight(LC(0x3A4763), LC(0x120C08), 0.38);
  var key = new T.DirectionalLight(LC(0xFFD7A2), 2.20); key.position.set(2.7, 3.7, 3.3); key.castShadow = true;
  var fill = new T.DirectionalLight(LC(0x9FB4FF), 0.50); fill.position.set(-3.4, 1.5, 2.6);
  var rim = new T.SpotLight(LC(0xFFE2AF), 4.0, 14, 0.72, 0.62, 1.2); rim.position.set(-0.7, 3.1, -3.6);
  rim.target.position.set(0, 1.25, 0);
  var rimC = new T.DirectionalLight(LC(0xB79CFF), 0.62); rimC.position.set(-2.6, 1.9, -3.2);
  var bounce = new T.PointLight(LC(0xFFC489), 0.70, 4.5, 2); bounce.position.set(0.2, 0.55, 1.35);
  [hemi, key, fill, rim, rim.target, rimC, bounce].forEach(function (l) { target.add(l); });
  return { hemi: hemi, key: key, fill: fill, rim: rim, rimCool: rimC, bounce: bounce };
};

/* go */
if (document.readyState === 'complete' || document.readyState === 'interactive') setTimeout(boot, 60);
else window.addEventListener('DOMContentLoaded', function () { setTimeout(boot, 60); });
})();
</script>
</body>
</html>
