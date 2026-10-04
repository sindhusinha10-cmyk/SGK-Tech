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
# 1. PIP: the two cheek arcs read as a MOUSTACHE. Birds have no lips, so the
#    smile becomes the beak itself -- the lower mandible drops as the mood
#    opens up.
# ===========================================================================
rep(u"""        // Birds have no lips: the expression lives at the commissure, so two
        // small up-curved arcs sit just outside the beak and ride the same
        // setMood channel as the humanoid mouths.
        const beakLine=colorMat(0xc9764a,{roughness:.5,clearcoat:.3});
        const beakFace={c:[0,-.13,.318],r:[.30,.235,.13]};
        const cleft=[-1,1].map(side=>smile(this.headRig,[side*.150,-.105,.425],.095,beakLine,beakFace));
        this.mouth={setMood:function(c,o,d){cleft.forEach(m=>m.setMood(c,o,d));}};
""",
    u"""        // Birds have no lips, so Pip's "smile" IS the beak: the lower mandible
        // (the cone) drops as the mood opens up. Two little arcs on the cheeks
        // were tried first and read as a moustache, so they are gone.
        this.mouth={setMood:function(c,o,d){
          const open=Math.PI/2+Math.max(0,o||0)*.26;
          if(G) G.to(beakTip.rotation,{x:open,duration:d||.45,ease:'power2.out',overwrite:true});
          else beakTip.rotation.x=open;
        }};
""",
    'pip-moustache-removed')

# ===========================================================================
# 2. PIP: crown was hovering. Re-seat it lower and tighter against the skull.
#    At y=.20 the head is .416 wide, so a .398 band with a .040 tube straddles
#    the surface instead of ringing it with a gap.
# ===========================================================================
old_crown_start = s.index(u"        const crown=new THREE.Group(); crown.position.set(0,.25,0);")
old_crown_end = s.index(u"        this.crown=crown;\n", old_crown_start) + len(u"        this.crown=crown;\n")
new_crown = u"""        const crown=new THREE.Group(); crown.position.set(0,.20,0); crown.scale.set(1,1,.88); this.headRig.add(crown);
        const pearlMat=colorMat(0xfff7e8,{roughness:.14,clearcoat:1,clearcoatRoughness:.08});
        const mint=gemMat(0x8dd4c0);
        // Sized off the skull: at y=.20 the head is .416 wide in x and .339 in
        // z, so a .398 band with a .040 tube STRADDLES the surface -- the ring
        // is half sunk into the head, which is what kills the floating gap.
        const band=addMesh(crown,new THREE.TorusGeometry(.398,.040,12,44),gold); band.rotation.x=Math.PI/2;
        const bandTop=addMesh(crown,new THREE.TorusGeometry(.378,.013,10,40),gold); bandTop.rotation.x=Math.PI/2; bandTop.position.y=.075;
        const POINTS=7;
        for(let i=0;i<POINTS;i++){
          const a=(i+.5)/POINTS*Math.PI*2, sx=Math.sin(a)*.392, sz=Math.cos(a)*.392;
          const pivot=new THREE.Group(); pivot.position.set(sx,.02,sz); pivot.rotation.y=a; crown.add(pivot);
          const lean=new THREE.Group(); lean.rotation.x=-.10; pivot.add(lean);
          const spike=addMesh(lean,new THREE.ConeGeometry(.062,.15,4),gold); spike.position.y=.075; spike.rotation.y=Math.PI/4;
          sphere(lean,pearlMat,[0,.163,0],[.027,.031,.027],14);
          sphere(crown,i%2?coral:mint,[sx,.048,sz],[.019,.019,.019],12);
        }
        const crownGem=addMesh(crown,new THREE.OctahedronGeometry(.048),mint); crownGem.position.set(0,.025,.455); crownGem.scale.set(.95,1.3,.6);
        this.crown=crown;
"""
s = s[:old_crown_start] + new_crown + s[old_crown_end:]
log.append('ok pip-crown-reseated (' + str(old_crown_end - old_crown_start) + ' -> ' + str(len(new_crown)) + ')')

# ===========================================================================
# 3. MOCHI: the "white shield" on the chest. It was a near-white ellipsoid
#    (.33 x .38) pushed .03 proud of the body, so it read as a plate bolted on.
#    Now it is a soft, warm, low-profile chest tuft: .01 proud at the centre
#    and fully buried at the rim, so it blends instead of shielding.
# ===========================================================================
rep(u"        const cream = colorMat(0xfff9ee,{roughness:.82,sheen:new THREE.Color(0xffe7d8)});\n",
    u"        const cream = colorMat(0xfff9ee,{roughness:.82,sheen:new THREE.Color(0xffe7d8)});\n"
    u"        const chestFur = colorMat(0xf8f1e6,{roughness:.87,sheen:new THREE.Color(0xfff3e4)});\n",
    'mochi-chest-mat')

rep(u"        sphere(this.bodyGroup,cream,[0,.66,.29],[.33,.38,.17],24);\n",
    u"        sphere(this.bodyGroup,chestFur,[0,.62,.345],[.24,.28,.10],24);\n",
    'mochi-chest-shield')

io.open(P, 'w', encoding='utf-8').write(s)
print('\n'.join(log))
print('WROTE ' + str(len(s)) + ' bytes (was ' + str(orig) + ', delta ' + str(len(s) - orig) + ')')
