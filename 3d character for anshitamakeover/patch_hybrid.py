import io, sys
p = '/home/user/parts/04_chars.js'
s = open(p).read()

def rep(old, new):
    global s
    c = s.count(old)
    assert c == 1, "MISS(%d): %s" % (c, old[:70])
    s = s.replace(old, new)

# --- 1. per-character art direction -------------------------------------
rep("  { id:'asha',   url:'models/Michelle.glb',        h:1.76, name:'Asha',",
    "  { id:'asha',   url:'models/Michelle.glb',        h:1.76, reskin:{ skin:0xC98F63, cloth:0x7A1226, metal:0xD8BC7E }, name:'Asha',")
rep("  { id:'noor',   url:'models/Soldier.glb',         h:1.76, name:'Noor',",
    "  { id:'noor',   url:'models/Soldier.glb',         h:1.76, couture:{ kind:'lehenga', cloth:0x11604A }, name:'Noor',")
rep("  { id:'tara',   url:'models/RobotExpressive.glb', h:1.70, name:'Tara',",
    "  { id:'tara',   url:'models/RobotExpressive.glb', h:1.70, couture:{ kind:'saree', cloth:0x0E5E48 }, name:'Tara',")
rep("  { id:'gia',    url:'models/Xbot.glb',            h:1.78, name:'Gia',",
    "  { id:'gia',    url:'models/Xbot.glb',            h:1.78, reskin:{ skin:0xE0A97E, cloth:0xE7B7C4, metal:0x8E7CC3 }, name:'Gia',")

# --- 2. couture + reskin helpers ----------------------------------------
COUTURE = r'''
/* ------------------------------------------------- couture & re-skin ------ */
function reskinModel(root, cfg) {
  var mSkin  = new T.MeshPhysicalMaterial({ color: LC(cfg.skin),  roughness: 0.52, clearcoat: 0.30, clearcoatRoughness: 0.45, envMapIntensity: 1.10 });
  var mCloth = new T.MeshPhysicalMaterial({ color: LC(cfg.cloth), roughness: 0.62, sheen: 1.0, envMapIntensity: 0.95 });
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

'''
rep("function makeGLTFCharacter(cfg) {", COUTURE + "function makeGLTFCharacter(cfg) {")

# --- 3. wire into the loader --------------------------------------------
rep("""    m.position.set(-(b.max.x + b.min.x) / 2, -b.min.y, -(b.max.z + b.min.z) / 2);
    rig.body.add(m);""",
"""    m.position.set(-(b.max.x + b.min.x) / 2, -b.min.y, -(b.max.z + b.min.z) / 2);
    var k = cfg.h / (hh > 1e-4 ? hh : 1);
    if (cfg.reskin)  { try { reskinModel(m, cfg.reskin); } catch (e) {} }
    if (cfg.couture) { try { addCouture(m, cfg.couture, k); } catch (e) {} }
    rig.body.add(m);""")

open(p, 'w').write(s)
print("04_chars.js: reskin + couture wired")
