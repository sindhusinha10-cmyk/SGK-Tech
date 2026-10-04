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

# The band was 3-4% SMALLER than the skull, so ~60% of the tube was buried and
# only a thin gold ridge showed. Push every radius out to sit exactly ON the
# skin at that height, so ~half the band stands proud.
rep(u"const crown=new THREE.Group(); crown.position.set(0,.20,0); crown.scale.set(1,1,.88);",
    u"const crown=new THREE.Group(); crown.position.set(0,.20,0); crown.scale.set(1,1,.87);",
    'crown-zscale')

rep(u"        // Sized off the skull: at y=.20 the head is .416 wide in x and .339 in\n"
    u"        // z, so a .398 band with a .040 tube STRADDLES the surface -- the ring\n"
    u"        // is half sunk into the head, which is what kills the floating gap.\n",
    u"        // Sized off the skull: at y=.20 the head is .416 wide in x and .362 in\n"
    u"        // z. A .416 band sits exactly ON that silhouette, so half of the .040\n"
    u"        // tube stands proud -- a band resting on the head, not sunk into it.\n",
    'crown-comment')

rep(u"const band=addMesh(crown,new THREE.TorusGeometry(.398,.040,12,44),gold);",
    u"const band=addMesh(crown,new THREE.TorusGeometry(.416,.040,12,44),gold);",
    'crown-band')

rep(u"const bandTop=addMesh(crown,new THREE.TorusGeometry(.378,.013,10,40),gold);",
    u"const bandTop=addMesh(crown,new THREE.TorusGeometry(.373,.013,10,40),gold);",
    'crown-bandtop')

rep(u"const a=(i+.5)/POINTS*Math.PI*2, sx=Math.sin(a)*.392, sz=Math.cos(a)*.392;",
    u"const a=(i+.5)/POINTS*Math.PI*2, sx=Math.sin(a)*.410, sz=Math.cos(a)*.410;",
    'crown-spikes')

rep(u"crownGem.position.set(0,.025,.455);",
    u"crownGem.position.set(0,.025,.465);",
    'crown-gem')

io.open(P, 'w', encoding='utf-8').write(s)
print('\n'.join(log))
print('WROTE ' + str(len(s)) + ' bytes (was ' + str(orig) + ', delta ' + str(len(s) - orig) + ')')
