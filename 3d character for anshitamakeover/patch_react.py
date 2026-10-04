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
# A. CharacterBase: squash channel + the poke-reaction system
# ===========================================================================
rep(u"        this.breath = 1;\n        this.phase = Math.random() * Math.PI * 2;\n",
    u"        this.breath = 1;\n"
    u"        this.squash = 1;\n"
    u"        this.reactions = ['tickle', 'shy', 'bounce'];\n"
    u"        this.phase = Math.random() * Math.PI * 2;\n",
    'base-fields')

# Every frame update() overwrites bodyGroup.scale.y, so reactions tween a
# `squash` property that update() folds in instead of fighting it.
rep(u"        const breath = Math.sin(time * 1.85 + this.phase) * .009 * this.breath;\n"
    u"        this.bodyGroup.scale.y = 1 + breath;\n",
    u"        const breath = Math.sin(time * 1.85 + this.phase) * .009 * this.breath;\n"
    u"        const sq = this.squash || 1;\n"
    u"        this.bodyGroup.scale.set(sq, (1 + breath) / Math.sqrt(sq), sq);\n",
    'base-squash-applied')

REACTIONS = u"""      flutter(tl, amount, reps) {
        [this.armL, this.armR].forEach((arm, i) => {
          if (!arm) return;
          const z0 = arm.shoulder.rotation.z;
          const to = arm.isWing ? z0 + amount * .3 : z0 + (arm === this.armL ? -1 : 1) * Math.abs(amount);
          tl.to(arm.shoulder.rotation, { z: to, duration: .085, repeat: reps, yoyo: true, ease: 'sine.inOut' }, 0);
        });
      }
      /* Poking the character: each tap runs a DIFFERENT reaction from the pool
         and never the same one twice in a row, so it never reads as a loop. */
      react() {
        if (this._reactBusy) return null;
        const pool = (this.reactions || ['tickle', 'shy', 'bounce']).filter(n => n !== this._lastReact);
        const name = pool[Math.floor(Math.random() * pool.length)] || 'tickle';
        this._lastReact = name;
        this._reactBusy = true;
        let dur = 1.2;
        try {
          const fn = this['react_' + name];
          dur = (fn ? fn.call(this) : this.react_tickle.call(this)) || 1.2;
        } catch (e) { dur = 1.2; }
        window.setTimeout(() => { this._reactBusy = false; }, dur * 1000);
        return name;
      }
      /* "gudi gudi" -- a shivery tickle: whole body wiggles, head lolls, eyes
         squeeze shut and it giggle-hops. */
      react_tickle() {
        const prev = this.emotion;
        const restore = () => this.setEmotion(prev, false);
        if (this.eyes) this.eyes.mood(.28);
        if (this.mouth) this.mouth.setMood(1.8, .45, .18);
        if (this.brows) this.brows.set(1, 0);
        if (!G) { window.setTimeout(restore, 900); return 1; }
        const tl = G.timeline({ onComplete: restore });
        tl.to(this.root.rotation, { z: .085, duration: .085, repeat: 7, yoyo: true, ease: 'sine.inOut' }, 0)
          .to(this.headTarget, { z: .10, duration: .085, repeat: 7, yoyo: true, ease: 'sine.inOut' }, 0)
          .to(this, { squash: 1.06, jump: .05, duration: .085, repeat: 7, yoyo: true, ease: 'sine.inOut' }, 0)
          .to(this.root.rotation, { z: 0, duration: .3, ease: 'power2.out' }, .74)
          .to(this.headTarget, { z: 0, duration: .3, ease: 'power2.out' }, .74)
          .to(this, { squash: 1, jump: 0, duration: .3, ease: 'power2.out' }, .74);
        this.flutter(tl, .55, 7);
        return 1.1;
      }
      react_shy() {
        const prev = this.emotion, gx = this.gazeTarget.x, gy = this.gazeTarget.y;
        if (this.eyes) this.eyes.mood(.82);
        if (this.mouth) this.mouth.setMood(1.05, .05, .3);
        if (this.brows) this.brows.set(.72, -.22);
        if (!G) { window.setTimeout(() => this.setEmotion(prev, false), 1100); return 1.2; }
        const tl = G.timeline({ onComplete: () => { G.to(this.gazeTarget, { x: gx, y: gy, duration: .5 }); this.setEmotion(prev, false); } });
        tl.to(this.headTarget, { x: .13, z: .14, duration: .45, ease: 'power2.out' }, 0)
          .to(this.gazeTarget, { x: -.6, y: -.45, duration: .45, ease: 'power2.out' }, 0)
          .to(this, { squash: 1.035, duration: .17, repeat: 5, yoyo: true, ease: 'sine.inOut' }, 0)
          .to(this.headTarget, { x: 0, z: 0, duration: .5, ease: 'power2.inOut' }, 1.1)
          .to(this.gazeTarget, { x: gx, y: gy, duration: .55, ease: 'power2.inOut' }, 1.1)
          .to(this, { squash: 1, duration: .35, ease: 'power2.out' }, 1.1);
        this.flutter(tl, .3, 5);
        return 1.7;
      }
      react_bounce() {
        const prev = this.emotion;
        if (this.eyes) this.eyes.mood(.45);
        if (this.mouth) this.mouth.setMood(1.6, .5, .15);
        if (!G) { window.setTimeout(() => this.setEmotion(prev, false), 700); return .8; }
        const tl = G.timeline({ onComplete: () => this.setEmotion(prev, false) });
        tl.to(this, { jump: .26, duration: .22, ease: 'power2.out' }, 0)
          .to(this, { jump: 0, duration: .3, ease: 'bounce.out' }, .22)
          .to(this, { squash: .93, duration: .12, ease: 'power2.out' }, 0)
          .to(this, { squash: 1.06, duration: .16, ease: 'power2.out' }, .26)
          .to(this, { squash: 1, duration: .45, ease: 'elastic.out' }, .42);
        this.flutter(tl, -.6, 3);
        return 1.05;
      }
      setEmotion(name, announce = true) {"""

rep(u"      setEmotion(name, announce = true) {", REACTIONS, 'base-reactions')

# ===========================================================================
# B. PIP: tail. The old cones had rotation.x=+PI/2, which points the apex
#    FORWARD into the body -- so every feather showed its flat base and stuck
#    out backwards like a paddle. Flipped to -PI/2, fanned to five, upswept.
# ===========================================================================
rep(u"""        const tail=new THREE.Group();tail.position.set(0,.58,-.37);this.root.add(tail);
        for(let i=0;i<3;i++){
          const feather=addMesh(tail,new THREE.ConeGeometry(.055,.34,12),i===1?coral:tealDeep);
          feather.rotation.x=Math.PI/2;feather.rotation.z=(i-1)*.18;feather.position.set((i-1)*.085,0,-.12);
        }
""",
    u"""        // Tail: five fanned feathers, apex pointing BACK (the old ones were
        // flipped, so they showed their flat base and read as paddles), upswept
        // and layered so the silhouette is a fan rather than three spikes.
        const tail=new THREE.Group(); tail.position.set(0,.58,-.33); tail.rotation.x=.22; this.root.add(tail);
        for(let i=0;i<5;i++){
          const spread=(i-2)*.19, len=.36-Math.abs(i-2)*.035;
          const feather=addMesh(tail,new THREE.ConeGeometry(.05,len,10),i===2?coral:tealDeep);
          feather.rotation.set(-Math.PI/2,0,spread);
          feather.position.set(Math.sin(spread)*.085,0,-.10-Math.abs(i-2)*.012);
        }
""",
    'pip-tail')

rep(u"""        this.animateExtra=(t)=>wings.forEach(w=>{
          w.group.rotation.x=Math.sin(t*(this.emotion==='happy' ? 11 : 2.1)+w.side)*(.035+this.flap*(this.emotion==='happy' ? .18 : .025));
        });
""",
    u"""        this.animateExtra=(t)=>{
          wings.forEach(w=>{
            w.group.rotation.x=Math.sin(t*(this.emotion==='happy' ? 11 : 2.1)+w.side)*(.035+this.flap*(this.emotion==='happy' ? .18 : .025));
          });
          tail.rotation.y=Math.sin(t*1.5)*.07;
        };
""",
    'pip-tail-flick')

# ===========================================================================
# C. PIP: "try to fly, but shy" -- his own reaction plus his pool
# ===========================================================================
rep(u"        this.onMood=(mood)=>{this.flap=",
    u"""        /* Pip's own poke reaction: a burst of wing-beating and little hopped
           take-off attempts, head ducked and eyes sliding away = shy. */
        this.reactions=['shyFly','tickle'];
        this.react_shyFly=()=>{
          const prev=this.emotion, flap0=this.flap;
          this.flap=2.2; this.emotion='happy';
          if(this.eyes) this.eyes.mood(.5);
          if(this.onSpark) this.onSpark(vec(0,1.05,.25),10);
          const restore=()=>{ this.flap=flap0; this.setEmotion(prev,false); };
          if(!G){ window.setTimeout(restore,1300); return 1.4; }
          const tl=G.timeline({onComplete:restore});
          tl.to(this,{jump:.17,duration:.17,repeat:3,yoyo:true,ease:'power2.out'},0)
            .to(this.root.rotation,{z:-.05,duration:.12,repeat:5,yoyo:true,ease:'sine.inOut'},0)
            .to(this.headTarget,{x:.15,z:.11,duration:.32,ease:'power2.out'},0)
            .to(this.gazeTarget,{x:-.45,y:-.5,duration:.32,ease:'power2.out'},0)
            .to(this.headTarget,{x:0,z:0,duration:.45,ease:'power2.inOut'},1.05)
            .to(this.gazeTarget,{x:0,y:0,duration:.45,ease:'power2.inOut'},1.05)
            .to(this,{jump:0,duration:.3,ease:'power2.out'},1.05)
            .to(this.root.rotation,{z:0,duration:.3,ease:'power2.out'},1.05);
          return 1.55;
        };
        this.onMood=(mood)=>{this.flap=""",
    'pip-shyfly')

# ===========================================================================
# D. PIP: crown now FLOATS clear of the skull with a visible gap, halo-style,
#    gently bobbing -- the crest plumes reach up through the open ring.
# ===========================================================================
cs = s.index(u"        const crown=new THREE.Group(); crown.position.set(0,.20,0);")
ce = s.index(u"        this.crown=crown;\n", cs) + len(u"        this.crown=crown;\n")
new_crown = u"""        // Floating crown, halo-style: it hovers clear of the skull with a real
        // gap and drifts, while the crest plumes reach up through the open
        // middle of the ring. Band underside sits .045 above the head top (.47).
        const CROWN_Y=.545;
        const crown=new THREE.Group(); crown.position.set(0,CROWN_Y,0); crown.scale.set(1,1,.87); this.headRig.add(crown);
        const pearlMat=colorMat(0xfff7e8,{roughness:.14,clearcoat:1,clearcoatRoughness:.08});
        const mint=gemMat(0x8dd4c0);
        const band=addMesh(crown,new THREE.TorusGeometry(.350,.030,12,44),gold); band.rotation.x=Math.PI/2;
        const bandTop=addMesh(crown,new THREE.TorusGeometry(.325,.011,10,40),gold); bandTop.rotation.x=Math.PI/2; bandTop.position.y=.048;
        const POINTS=7;
        for(let i=0;i<POINTS;i++){
          const a=(i+.5)/POINTS*Math.PI*2, sx=Math.sin(a)*.345, sz=Math.cos(a)*.345;
          const pivot=new THREE.Group(); pivot.position.set(sx,.02,sz); pivot.rotation.y=a; crown.add(pivot);
          const lean=new THREE.Group(); lean.rotation.x=-.08; pivot.add(lean);
          const spike=addMesh(lean,new THREE.ConeGeometry(.055,.11,4),gold); spike.position.y=.055; spike.rotation.y=Math.PI/4;
          sphere(lean,pearlMat,[0,.140,0],[.026,.030,.026],14);
          sphere(crown,i%2?coral:mint,[sx,.038,sz],[.017,.017,.017],12);
        }
        const crownGem=addMesh(crown,new THREE.OctahedronGeometry(.042),mint); crownGem.position.set(0,.012,.395); crownGem.scale.set(.95,1.3,.6);
        this.crown=crown;
        this.tickers.push(t=>{ crown.position.y=CROWN_Y+Math.sin(t*1.15)*.014; crown.rotation.y=Math.sin(t*.42)*.10; });
"""
s = s[:cs] + new_crown + s[ce:]
log.append('ok pip-floating-crown (' + str(ce - cs) + ' -> ' + str(len(new_crown)) + ')')

# ===========================================================================
# E. App: tapping the character itself pokes it
# ===========================================================================
rep(u"""        raycaster.setFromCamera(ndc,camera);const point=new THREE.Vector3();
        if(raycaster.ray.intersectPlane(floorPlane,point))emitSparkles(point,9);""",
    u"""        raycaster.setFromCamera(ndc,camera);
        /* Tap the character itself and it reacts -- a different one each time. */
        if(activeCharacter){
          const hits=raycaster.intersectObject(activeCharacter.root,true);
          if(hits.length){
            activeCharacter.react();
            if(activeCharacter.onSpark)activeCharacter.onSpark(hits[0].point,8);
            return;
          }
        }
        const point=new THREE.Vector3();
        if(raycaster.ray.intersectPlane(floorPlane,point))emitSparkles(point,9);""",
    'app-poke')

io.open(P, 'w', encoding='utf-8').write(s)
print('\n'.join(log))
print('WROTE ' + str(len(s)) + ' bytes (was ' + str(orig) + ', delta ' + str(len(s) - orig) + ')')
