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

# === 0. eyeBrows: optional width/height/radius so Pip can have BIGGER brows.
#       Defaults are unchanged, so the four humanoids are untouched.
rep(u"      const y = options.y || .14, z = options.z || .215, x = options.x || .1;",
    u"      const y = options.y || .14, z = options.z || .215, x = options.x || .1;\n"
    u"      const bw = options.w || .045, bh = options.h || .022, br = options.r || .009;",
    'eyebrows-opts')
rep(u"        tube(pivot, [[-.045, 0, 0], [0, .022, .004], [.045, 0, 0]], .009, hairMat, 7);",
    u"        tube(pivot, [[-bw, 0, 0], [0, bh, .004], [bw, 0, 0]], br, hairMat, 7);",
    'eyebrows-geometry')

# === 1. PIP BROWS. He had NO brow channel at all -- `this.brows` was never set,
#        so setEmotion's strongest cue (brow raise/tilt) silently did nothing.
rep(u"        this.eyes=eyePair(this.headRig,{x:.165,y:.06,z:.352,radius:.115,dark:true});",
    u"        this.eyes=eyePair(this.headRig,{x:.165,y:.06,z:.352,radius:.115,dark:true});\n"
    u"        // Feather brow tufts. Pip had no brow channel at all, and brows carry\n"
    u"        // most of an expression -- that is why his face looked frozen.\n"
    u"        const browMat=colorMat(0x2e7f80,{roughness:.42,metalness:.06,clearcoat:.55});\n"
    u"        this.brows=eyeBrows(this.headRig,browMat,browMat,{y:.235,z:.335,x:.165,w:.062,h:.030,r:.011});",
    'pip-brows')

# === 2. Beak into a group so it can be SCALED, not just opened.
rep(u"        sphere(this.headRig,beakMat,[0,-.12,.441],[.105,.075,.105],20);\n"
    u"        const beakTip=addMesh(this.headRig,new THREE.ConeGeometry(.092,.17,7),beakMat);beakTip.rotation.x=Math.PI/2;beakTip.position.set(0,-.17,.49);",
    u"        const beak=new THREE.Group(); beak.position.set(0,-.12,.441); this.headRig.add(beak);\n"
    u"        sphere(beak,beakMat,[0,0,0],[.105,.075,.105],20);\n"
    u"        const beakTip=addMesh(beak,new THREE.ConeGeometry(.092,.17,7),beakMat);beakTip.rotation.x=Math.PI/2;beakTip.position.set(0,-.05,.049);",
    'pip-beak-group')

# === 3. Beak now answers the CURVE too. mouthOpen is 0 for five of the nine
#        moods, so the beak previously did nothing at all for most of them.
rep(u"""        this.mouth={setMood:function(c,o,d){
          const open=Math.PI/2+Math.max(0,o||0)*.26;
          if(G) G.to(beakTip.rotation,{x:open,duration:d||.45,ease:'power2.out',overwrite:true});
          else beakTip.rotation.x=open;
        }};""",
    u"""        this.mouth={setMood:function(c,o,d){
          const open=Math.PI/2+Math.max(0,o||0)*.26;
          const cc=Math.max(-1.2,Math.min(1.8,c||0));
          if(G){
            G.to(beakTip.rotation,{x:open,duration:d||.45,ease:'power2.out',overwrite:true});
            G.to(beak.scale,{x:1+cc*.07,y:1-cc*.045,duration:d||.45,ease:'power2.out'});
          } else { beakTip.rotation.x=open; beak.scale.set(1+cc*.07,1-cc*.045,1); }
        }};""",
    'pip-beak-curve')

# === 4. Crest plumes captured so they can act as a mood channel.
rep(u"""        for(let i=0;i<3;i++){
          const plume=addMesh(this.headRig,new THREE.ConeGeometry(.07,.23,12),i===1?coral:plumeM);
          plume.position.set((i-1)*.085,.43+Math.abs(i-1)*.015,-.005);plume.rotation.z=(i-1)*-.25;
        }""",
    u"""        const plumes=[];
        for(let i=0;i<3;i++){
          const plume=addMesh(this.headRig,new THREE.ConeGeometry(.07,.23,12),i===1?coral:plumeM);
          plume.position.set((i-1)*.085,.43+Math.abs(i-1)*.015,-.005);plume.rotation.z=(i-1)*-.25;
          plumes.push({mesh:plume,baseZ:(i-1)*-.25});
        }
        this.plumes=plumes; this.plumeLift=0; this.plumeTarget=.5;""",
    'pip-plumes')

# === 5. animateExtra: wings take the pose swing, crest reacts.
rep(u"""        this.animateExtra=(t)=>{
          wings.forEach(w=>{
            w.group.rotation.x=Math.sin(t*(this.emotion==='happy' ? 11 : 2.1)+w.side)*(.035+this.flap*(this.emotion==='happy' ? .18 : .025));
          });
          tail.rotation.y=Math.sin(t*1.5)*.07;
        };""",
    u"""        this.animateExtra=(t)=>{
          // Wings also fold in the pose swing, so the "offering" stance reads on
          // a bird. update() deliberately skips wings, because animateExtra owns
          // their rotation.x -- so it has to be added here instead.
          wings.forEach(w=>{
            w.group.rotation.x=Math.sin(t*(this.emotion==='happy' ? 11 : 2.1)+w.side)*(.035+this.flap*(this.emotion==='happy' ? .18 : .025)) + this.armSwingX*.55;
          });
          // Crest: lifts and splays when bright, sweeps back and flattens when sad.
          this.plumeLift += (this.plumeTarget-this.plumeLift)*.09;
          this.plumes.forEach(p=>{
            p.mesh.rotation.z=p.baseZ*(1+this.plumeLift*.5);
            p.mesh.rotation.x=this.plumeLift<.3 ? (this.plumeLift-.3)*.55 : 0;
            const s=1+this.plumeLift*.13; p.mesh.scale.set(s,s,s);
          });
          tail.rotation.y=Math.sin(t*1.5)*.07;
        };""",
    'pip-animateextra')

# === 6. onMood drives the crest, and the coupon pose sparkles.
rep(u"        this.onMood=(mood)=>{this.flap=mood==='happy' ? 1.5 : (mood==='thinking' ? .25 : .65);if(mood==='happy'&&this.onSpark)this.onSpark(vec(.15,1.2,.4),12);};",
    u"        const PLUME_MOOD={happy:1.0,surprised:1.25,coupon:.85,welcome:.55,wink:.7,thinking:.3,waiting:.35,hesitant:.05,sad:-1.0};\n"
    u"        this.onMood=(mood)=>{\n"
    u"          this.flap=mood==='happy' ? 1.5 : (mood==='thinking' ? .25 : .65);\n"
    u"          this.plumeTarget=PLUME_MOOD[mood]!==undefined?PLUME_MOOD[mood]:.5;\n"
    u"          if((mood==='happy'||mood==='coupon')&&this.onSpark)this.onSpark(vec(.15,1.2,.4),mood==='coupon'?16:12);\n"
    u"        };",
    'pip-onmood')

io.open(P, 'w', encoding='utf-8').write(s)
print('\n'.join(log))
print('WROTE ' + str(len(s)) + ' bytes (was ' + str(orig) + ', delta ' + str(len(s) - orig) + ')')
