import io, sys

P = '/home/user/index-expressions.html'
s = io.open(P, encoding='utf-8').read()
orig = len(s)
log = []

def rep(old, new, label):
    global s
    n = s.count(old)
    if n != 1:
        print('FAIL[' + label + '] count=' + str(n))
        sys.exit(1)
    s = s.replace(old, new)
    log.append('ok ' + label)

# ===========================================================================
# 1. THE PINK STRIP "CHANGING" WHEN MOCHI BREATHES.
#    The sash, its gold trim and the emerald brooch were parented to
#    this.root, while the body lives in this.bodyGroup -- and update() scales
#    bodyGroup every frame for breathing. So the body inflated and deflated
#    underneath a sash that never moved, and because the ribbon is a flat
#    zero-thickness strip lying ON the body surface, that mismatch shows up as
#    the sash sliding / shimmering / popping through the fur. Parenting them to
#    bodyGroup makes them breathe with the body.
# ===========================================================================
rep(u"""        // Small velvet sash wraps the plump body and meets at an emerald brooch.
        ribbon(this.root,[[-.43,.92,.12],[-.25,.81,.35],[0,.74,.45],[.24,.81,.35],[.43,.92,.12]],.135,sash,30);
        tube(this.root,[[-.43,.92,.13],[-.25,.81,.36],[0,.74,.46],[.24,.81,.36],[.43,.92,.13]],.007,gold);
        addMesh(this.root,new THREE.TorusGeometry(.068,.012,10,24),gold).position.set(0,.76,.46);
        const jewel=addMesh(this.root,new THREE.OctahedronGeometry(.05),emerald); jewel.position.set(0,.76,.48); jewel.scale.y=1.3;""",
    u"""        // Small velvet sash wraps the plump body and meets at an emerald brooch.
        // Parented to bodyGroup, NOT root: breathing scales bodyGroup every
        // frame, and a flat ribbon left on root slides against the fur.
        ribbon(this.bodyGroup,[[-.43,.92,.12],[-.25,.81,.35],[0,.74,.45],[.24,.81,.35],[.43,.92,.12]],.135,sash,30);
        tube(this.bodyGroup,[[-.43,.92,.13],[-.25,.81,.36],[0,.74,.46],[.24,.81,.36],[.43,.92,.13]],.007,gold);
        addMesh(this.bodyGroup,new THREE.TorusGeometry(.068,.012,10,24),gold).position.set(0,.76,.46);
        const jewel=addMesh(this.bodyGroup,new THREE.OctahedronGeometry(.05),emerald); jewel.position.set(0,.76,.48); jewel.scale.y=1.3;""",
    'mochi-sash-parented')

# ===========================================================================
# 2. MOCHI: fluffy pom-pom tail instead of one hard ball.
# ===========================================================================
rep(u"        sphere(this.bodyGroup,fur,[0,.44,-.43],[.125,.13,.13],16);\n",
    u"""        // Pom-pom tail: a core plus a shell of overlapping lobes so the
        // silhouette scallops like fur instead of reading as one hard ball.
        // Lobes on the front half sit inside the body, so only the back ones show.
        const tail=new THREE.Group(); tail.position.set(0,.47,-.375); this.bodyGroup.add(tail);
        sphere(tail,fur,[0,0,-.02],[.125,.13,.115],20);
        for(let i=0;i<14;i++){
          const y=1-(i/13)*2, rr=Math.sqrt(Math.max(0,1-y*y)), a=i*2.39996, d=.072;
          const rad=.052+(i%3)*.009;
          sphere(tail,i%4===0?chestFur:fur,[Math.cos(a)*rr*d, y*.085, -.035+Math.sin(a)*rr*d],[rad,rad,rad],12);
        }
        this.tickers.push(t=>{ tail.rotation.y=Math.sin(t*1.35)*.11; tail.rotation.x=Math.sin(t*.95)*.05; });
""",
    'mochi-pom-tail')

# ===========================================================================
# 3. MOCHI: proper ears. Old version = one hard ellipsoid + a FLAT pink plate
#    stuck on the front + a gold hoop floating round the middle. New = three
#    tapered lobes (narrow base, full middle, softly rounded tip) with a pink
#    inner cup that is proud in the middle and tucks under the fur at the edges.
# ===========================================================================
rep(u"""        [-1,1].forEach(side=>{
          const ear=new THREE.Group(); ear.position.set(side*.16,.32,-.01); ear.rotation.z=-side*.15; this.headRig.add(ear);
          sphere(ear,fur,[0,.31,0],[.105,.36,.08],20);
          sphere(ear,pink,[0,.31,.073],[.062,.27,.022],18);
          const thread=addMesh(ear,new THREE.TorusGeometry(.083,.009,8,20),gold); thread.position.set(0,.56,.01); thread.rotation.x=Math.PI/2;
          sphere(ear,gold,[0,.66,0],[.025,.035,.025],10);
          this.earParts.push({group:ear,side:side});
        });""",
    u"""        [-1,1].forEach(side=>{
          const ear=new THREE.Group(); ear.position.set(side*.155,.30,-.005); ear.rotation.z=-side*.13; this.headRig.add(ear);
          // Outer shell: narrow at the base, fullest through the middle, softly
          // domed at the tip. A single ellipsoid reads as a flat leaf.
          sphere(ear,fur,[0,.16,0],[.072,.13,.062],18);
          sphere(ear,fur,[0,.34,0],[.098,.19,.075],20);
          sphere(ear,fur,[0,.52,0],[.082,.13,.062],18);
          // Inner cup follows the same taper. It stands ~.006 proud at the
          // centre line but sinks under the fur at its own edges, so it reads
          // as a hollow rather than a pink plate glued to the front.
          sphere(ear,pink,[0,.17,.042],[.040,.095,.026],14);
          sphere(ear,pink,[0,.35,.051],[.056,.150,.030],16);
          sphere(ear,pink,[0,.51,.044],[.040,.095,.024],14);
          this.earParts.push({group:ear,side:side});
        });""",
    'mochi-ears')

rep(u"        this.tickers.push((t)=>this.earParts.forEach(e=>{e.group.rotation.x=Math.sin(t*1.55+e.side)*.08; e.group.rotation.z=-e.side*(.15+Math.sin(t*.7+e.side)*.04);}));",
    u"        this.tickers.push((t)=>this.earParts.forEach(e=>{e.group.rotation.x=Math.sin(t*1.55+e.side)*.075; e.group.rotation.z=-e.side*(.13+Math.sin(t*.7+e.side)*.05);}));",
    'mochi-ear-ticker')

# ===========================================================================
# 4. PIP: crown scaled down ~20% (band .350 -> .285, points .11 -> .095).
# ===========================================================================
cs = s.index(u"        const CROWN_Y=.545;")
tl = u"        this.tickers.push(t=>{ crown.position.y=CROWN_Y+Math.sin(t*1.15)*.014; crown.rotation.y=Math.sin(t*.42)*.10; });\n"
ce = s.index(tl, cs) + len(tl)
new_crown = u"""        const CROWN_Y=.535;
        const crown=new THREE.Group(); crown.position.set(0,CROWN_Y,0); crown.scale.set(1,1,.87); this.headRig.add(crown);
        const pearlMat=colorMat(0xfff7e8,{roughness:.14,clearcoat:1,clearcoatRoughness:.08});
        const mint=gemMat(0x8dd4c0);
        const band=addMesh(crown,new THREE.TorusGeometry(.285,.026,12,40),gold); band.rotation.x=Math.PI/2;
        const bandTop=addMesh(crown,new THREE.TorusGeometry(.265,.010,10,36),gold); bandTop.rotation.x=Math.PI/2; bandTop.position.y=.042;
        const POINTS=7;
        for(let i=0;i<POINTS;i++){
          const a=(i+.5)/POINTS*Math.PI*2, sx=Math.sin(a)*.280, sz=Math.cos(a)*.280;
          const pivot=new THREE.Group(); pivot.position.set(sx,.02,sz); pivot.rotation.y=a; crown.add(pivot);
          const lean=new THREE.Group(); lean.rotation.x=-.08; pivot.add(lean);
          const spike=addMesh(lean,new THREE.ConeGeometry(.046,.095,4),gold); spike.position.y=.0475; spike.rotation.y=Math.PI/4;
          sphere(lean,pearlMat,[0,.105,0],[.022,.026,.022],14);
          sphere(crown,i%2?coral:mint,[sx,.033,sz],[.015,.015,.015],12);
        }
        const crownGem=addMesh(crown,new THREE.OctahedronGeometry(.036),mint); crownGem.position.set(0,.010,.320); crownGem.scale.set(.95,1.3,.6);
        this.crown=crown;
        this.tickers.push(t=>{ crown.position.y=CROWN_Y+Math.sin(t*1.15)*.014; crown.rotation.y=Math.sin(t*.42)*.10; });
"""
s = s[:cs] + new_crown + s[ce:]
log.append('ok pip-crown-smaller (' + str(ce - cs) + ' -> ' + str(len(new_crown)) + ')')

# ===========================================================================
# 5. PIP: tail feathers no longer POINTED. Cones come to a hard apex; these are
#    lathed teardrops -- rounded at the tip AND at the base -- flattened into
#    blades and fanned, which is how stylized bird tails are normally built.
# ===========================================================================
rep(u"""        // Tail: five fanned feathers, apex pointing BACK (the old ones were
        // flipped, so they showed their flat base and read as paddles), upswept
        // and layered so the silhouette is a fan rather than three spikes.
        const tail=new THREE.Group(); tail.position.set(0,.58,-.33); tail.rotation.x=.22; this.root.add(tail);
        for(let i=0;i<5;i++){
          const spread=(i-2)*.19, len=.36-Math.abs(i-2)*.035;
          const feather=addMesh(tail,new THREE.ConeGeometry(.05,len,10),i===2?coral:tealDeep);
          feather.rotation.set(-Math.PI/2,0,spread);
          feather.position.set(Math.sin(spread)*.085,0,-.10-Math.abs(i-2)*.012);
        }""",
    u"""        // Tail: five soft feathers. Each is a LATHED teardrop -- rounded at the
        // tip AND at the base -- flattened into a blade. Cones came to a hard
        // point, which is what made the tail look stabby.
        const tail=new THREE.Group(); tail.position.set(0,.58,-.30); tail.rotation.x=.20; this.root.add(tail);
        const FEATHER=[[.007,0],[.026,.045],[.034,.10],[.032,.16],[.024,.215],[.012,.255],[0,.27]];
        const featherGeo=new THREE.LatheGeometry(FEATHER.map(p=>new THREE.Vector2(p[0],p[1])),12);
        for(let i=0;i<5;i++){
          const spread=(i-2)*.20, len=1-Math.abs(i-2)*.07;
          const feather=addMesh(tail,featherGeo,i===2?coral:tealDeep);
          feather.rotation.set(-Math.PI/2,0,spread);
          feather.scale.set(.95,len,.40);
          feather.position.set(Math.sin(spread)*.055,0,-.055-Math.abs(i-2)*.008);
        }""",
    'pip-rounded-tail')

io.open(P, 'w', encoding='utf-8').write(s)
print('\n'.join(log))
print('WROTE ' + str(len(s)) + ' bytes (was ' + str(orig) + ', delta ' + str(len(s) - orig) + ')')
