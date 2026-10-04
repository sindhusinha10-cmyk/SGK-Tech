import io, sys, re

P = '/home/user/index-expressions.html'
s = io.open(P, encoding='utf-8').read()
orig_len = len(s)
log = []

def rep(old, new, label, count=1):
    global s
    n = s.count(old)
    if n != count:
        print('FAIL[' + label + '] expected ' + str(count) + ' got ' + str(n))
        sys.exit(1)
    s = s.replace(old, new)
    log.append('ok ' + label)

# ---------------------------------------------------------------------------
# 1. taperedTube helper + a much bigger, cuter, face-hugging smile()
# ---------------------------------------------------------------------------
smile_start = s.index('    function smile(parent, position, width, material) {')
smile_end_marker = '      return group;\n    }\n'
smile_end = s.index(smile_end_marker, smile_start) + len(smile_end_marker)
old_smile = s[smile_start:smile_end]

new_smile = u'''    /* TubeGeometry can only sweep a CONSTANT radius, which makes a mouth read
       as a bent wire rather than as lips. This sweeps a variable radius so the
       smile is fat through the middle and drawn to a fine point at each
       corner -- that taper is most of what makes a smile look "cute". */
    function taperedTube(curve, tubularSegments, radiusFn, radialSegments) {
      const frames = curve.computeFrenetFrames(tubularSegments, false);
      const pos = [], nor = [], uvs = [], idx = [];
      const P = new THREE.Vector3(), N = new THREE.Vector3();
      for (let i = 0; i <= tubularSegments; i++) {
        const t = i / tubularSegments;
        curve.getPointAt(t, P);
        const r = Math.max(.0008, radiusFn(t));
        const Bi = frames.binormals[i], Ni = frames.normals[i];
        for (let j = 0; j <= radialSegments; j++) {
          const v = j / radialSegments * Math.PI * 2;
          const sn = Math.sin(v), cs = -Math.cos(v);
          N.set(cs * Ni.x + sn * Bi.x, cs * Ni.y + sn * Bi.y, cs * Ni.z + sn * Bi.z).normalize();
          pos.push(P.x + r * N.x, P.y + r * N.y, P.z + r * N.z);
          nor.push(N.x, N.y, N.z);
          uvs.push(t, j / radialSegments);
        }
      }
      for (let i = 1; i <= tubularSegments; i++) {
        for (let j = 1; j <= radialSegments; j++) {
          const a = (radialSegments + 1) * (i - 1) + (j - 1);
          const b = (radialSegments + 1) * i + (j - 1);
          const c = (radialSegments + 1) * i + j;
          const d = (radialSegments + 1) * (i - 1) + j;
          idx.push(a, b, d, b, c, d);
        }
      }
      const geo = new THREE.BufferGeometry();
      geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
      geo.setAttribute('normal', new THREE.Float32BufferAttribute(nor, 3));
      geo.setAttribute('uv', new THREE.Float32BufferAttribute(uvs, 2));
      geo.setIndex(idx);
      return geo;
    }
    function smile(parent, position, width, material, face) {
      const group = new THREE.Group();
      group.position.set(position[0], position[1], position[2]);
      parent.add(group);
      const mesh = addMesh(group, new THREE.BufferGeometry(), material);
      const state = { c: 1, o: 0 };
      const SEGS = 12;
      /* Follow the curvature of the face (or the muzzle, for Mochi) so a wide
         grin wraps around the cheeks instead of floating out in front of the
         chin. `face` is { c:[cx,cy,cz], r:[rx,ry,rz] } in headRig space. */
      function surfaceZ(x, y) {
        if (!face) return null;
        const a = (x - face.c[0]) / face.r[0];
        const b = (y - face.c[1]) / face.r[1];
        const k = 1 - a * a - b * b;
        const z = face.c[2] + face.r[2] * Math.sqrt(k > 0 ? k : 0) - position[2] + .006;
        return Math.max(-.075, Math.min(.075, z));
      }
      function build(cAmt, oAmt) {
        const c = cAmt, o = Math.max(0, oAmt);
        /* A cute smile is a wide, shallow bowl whose corners flick UP past the
           mouth line. Both depth and flick scale with the mouth width so the
           same code reads on a .10 bunny mouth and a .12 human one. */
        const w = width * (1 + Math.max(0, c - 1) * .14);
        const depth = c * width * .26;
        const flick = c * width * .18;
        const pts = [];
        for (let i = 0; i <= SEGS; i++) {
          const u = -1 + (2 * i) / SEGS;
          const bell = 1 - u * u;
          const x = u * w * .5;
          const y = depth * (u * u - 1) + flick * Math.pow(Math.abs(u), 3) - o * width * .34 * bell;
          const z = surfaceZ(x, position[1] + y);
          pts.push(vec(x, y, z === null ? .008 * bell : z));
        }
        const curve = new THREE.CatmullRomCurve3(pts);
        const thick = Math.max(.010, width * .125) * (1 + o * .5);
        const geo = taperedTube(curve, 32, function (t) {
          return thick * (.18 + .82 * Math.sqrt(Math.max(0, Math.sin(Math.PI * t))));
        }, 10);
        if (mesh.geometry) mesh.geometry.dispose();
        mesh.geometry = geo;
      }
      build(state.c, state.o);
      group.setMood = function (cAmt, oAmt, dur) {
        const toC = (cAmt === undefined) ? 1 : cAmt, toO = oAmt || 0;
        if (G && dur !== 0) G.to(state, { c: toC, o: toO, duration: dur || .45,
          ease: 'power2.out', onUpdate: function () { build(state.c, state.o); } });
        else { state.c = toC; state.o = toO; build(state.c, state.o); }
      };
      return group;
    }
'''
s = s[:smile_start] + new_smile + s[smile_end:]
log.append('ok smile-rewrite (' + str(len(old_smile)) + ' -> ' + str(len(new_smile)) + ' bytes)')

# ---------------------------------------------------------------------------
# 2. Mochi: muzzle fix. The mouth sat at z=.395 but the cream muzzle it is
#    supposed to sit on reaches z=.420, so the whole smile was buried inside
#    the muzzle mesh and invisible. Nudged the nose up to make room.
# ---------------------------------------------------------------------------
rep(u"        sphere(this.headRig,pink,[0,-.09,.402],[.045,.033,.027],16);\n",
    u"        sphere(this.headRig,pink,[0,-.072,.402],[.045,.033,.027],16);\n",
    'mochi-nose')

# ---------------------------------------------------------------------------
# 3. Bigger call-site widths + face ellipsoids
# ---------------------------------------------------------------------------
rep(u"this.mouth = smile(this.headRig, [0,-.19,.229], .105, colorMat(0x762332,{roughness:.38,clearcoat:.45}));",
    u"this.mouth = smile(this.headRig, [0,-.198,.229], .122, colorMat(0x762332,{roughness:.38,clearcoat:.45}), {c:[0,0,0],r:[.29,.34,.255]});",
    'asha-mouth')

rep(u"this.mouth=smile(this.headRig,[0,-.151,.395],.082,colorMat(0x9c5662,{roughness:.4}));",
    u"this.mouth=smile(this.headRig,[0,-.158,.418],.100,colorMat(0x9c5662,{roughness:.4}),{c:[0,-.14,.291],r:[.245,.17,.13]});",
    'mochi-mouth')

rep(u"this.mouth=smile(this.headRig,[0,-.18,.22],.085,colorMat(0x963c50,{roughness:.35,clearcoat:.4}));",
    u"this.mouth=smile(this.headRig,[0,-.188,.22],.104,colorMat(0x963c50,{roughness:.35,clearcoat:.4}),{c:[0,0,0],r:[.275,.335,.245]});",
    'noor-mouth')

rep(u"this.mouth=smile(this.headRig,[0,-.18,.22],.105,colorMat(0x813041,{roughness:.36}));",
    u"this.mouth=smile(this.headRig,[0,-.188,.22],.122,colorMat(0x813041,{roughness:.36}),{c:[0,0,0],r:[.285,.335,.25]});",
    'tara-mouth')

rep(u"this.mouth=smile(this.headRig,[0,-.18,.208],.084,colorMat(0xd8517e,{roughness:.32,clearcoat:.55}));",
    u"this.mouth=smile(this.headRig,[0,-.186,.208],.104,colorMat(0xd8517e,{roughness:.32,clearcoat:.55}),{c:[0,0,0],r:[.27,.34,.235]});",
    'gia-mouth')

# ---------------------------------------------------------------------------
# 4. Pip: a beak "smile". Birds have no lips, so the expression lives at the
#    commissure -- two small up-curved arcs just outside the beak, riding the
#    same setMood channel as the humanoid mouths.
# ---------------------------------------------------------------------------
rep(u"        // Three soft crest plumes and a tiny golden circlet.\n",
    u"""        // Birds have no lips: the expression lives at the commissure, so two
        // small up-curved arcs sit just outside the beak and ride the same
        // setMood channel as the humanoid mouths.
        const beakLine=colorMat(0xc9764a,{roughness:.5,clearcoat:.3});
        const beakFace={c:[0,-.13,.318],r:[.30,.235,.13]};
        const cleft=[-1,1].map(side=>smile(this.headRig,[side*.13,-.105,.425],.095,beakLine,beakFace));
        this.mouth={setMood:function(c,o,d){cleft.forEach(m=>m.setMood(c,o,d));}};
        // Three soft crest plumes and a real 3D crown.
""",
    'pip-beak-smile')

# ---------------------------------------------------------------------------
# 5. Pip: the real crown. The old "circlet" was a near-vertical ring of radius
#    .22 parked at a height where the head is .40 wide -- it was buried inside
#    the skull and never showed. This is an elliptical band that straddles the
#    head surface, with seven tapered points, pearls and gems.
# ---------------------------------------------------------------------------
rep(u"""        const circlet=addMesh(this.headRig,new THREE.TorusGeometry(.22,.009,8,32),gold);circlet.position.set(0,.28,.05);circlet.rotation.x=.1;
        sphere(this.headRig,gemMat(0x8dd4c0),[0,.28,.263],[.038,.05,.018],14);
""",
    u"""        const crown=new THREE.Group(); crown.position.set(0,.25,0); crown.scale.set(1,1,.88); this.headRig.add(crown);
        const pearlMat=colorMat(0xfff7e8,{roughness:.14,clearcoat:1,clearcoatRoughness:.08});
        const mint=gemMat(0x8dd4c0);
        const band=addMesh(crown,new THREE.TorusGeometry(.392,.032,12,44),gold); band.rotation.x=Math.PI/2;
        const bandTop=addMesh(crown,new THREE.TorusGeometry(.380,.013,10,40),gold); bandTop.rotation.x=Math.PI/2; bandTop.position.y=.082;
        const POINTS=7;
        for(let i=0;i<POINTS;i++){
          const a=(i+.5)/POINTS*Math.PI*2, sx=Math.sin(a)*.388, sz=Math.cos(a)*.388;
          const pivot=new THREE.Group(); pivot.position.set(sx,.02,sz); pivot.rotation.y=a; crown.add(pivot);
          const lean=new THREE.Group(); lean.rotation.x=-.13; pivot.add(lean);
          const spike=addMesh(lean,new THREE.ConeGeometry(.062,.18,4),gold); spike.position.y=.09; spike.rotation.y=Math.PI/4;
          sphere(lean,pearlMat,[0,.208,0],[.027,.031,.027],14);
          sphere(crown,i%2?coral:mint,[sx,.014,sz],[.019,.019,.019],12);
        }
        const crownGem=addMesh(crown,new THREE.OctahedronGeometry(.052),mint); crownGem.position.set(0,.052,.40); crownGem.scale.set(.95,1.3,.6);
        [-1,1].forEach(side=>sphere(crown,coral,[Math.sin(side*.42)*.392,.028,Math.cos(.42)*.392],[.02,.02,.02],12));
        this.crown=crown;
""",
    'pip-crown')

io.open(P, 'w', encoding='utf-8').write(s)
print('\n'.join(log))
print('WROTE ' + str(len(s)) + ' bytes (was ' + str(orig_len) + ', delta ' + str(len(s) - orig_len) + ')')
