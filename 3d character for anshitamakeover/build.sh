#!/usr/bin/env bash
# Rebuild index.html from parts/ and regenerate the fully-inlined index.offline.html
set -e
cd /home/user
cat parts/01_head.html parts/02_core.js parts/03_rig.js parts/04_chars.js parts/05_app.js > index.html
python3 - <<'PYEOF'
import re
src = open('/home/user/index.html', encoding='utf-8').read()
vendor = {
 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js':'vendor/three.min.js',
 'https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/controls/OrbitControls.js':'vendor/OrbitControls.js',
 'https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/shaders/CopyShader.js':'vendor/CopyShader.js',
 'https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/shaders/LuminosityHighPassShader.js':'vendor/LuminosityHighPassShader.js',
 'https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/postprocessing/EffectComposer.js':'vendor/EffectComposer.js',
 'https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/postprocessing/RenderPass.js':'vendor/RenderPass.js',
 'https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/postprocessing/ShaderPass.js':'vendor/ShaderPass.js',
 'https://cdn.jsdelivr.net/npm/three@0.128.0/examples/js/postprocessing/UnrealBloomPass.js':'vendor/UnrealBloomPass.js',
 'https://cdnjs.cloudflare.com/ajax/libs/gsap/3.12.5/gsap.min.js':'vendor/gsap.min.js',
}
out = src
for url, path in vendor.items():
    code = open('/home/user/'+path, encoding='utf-8').read()
    tag = '<script src="%s"></script>' % url
    out = out.replace(tag, '<script>/* inlined: %s */\n%s\n</script>' % (url.split('/')[-1], code))
out = re.sub(r"<script>window\.(THREE|gsap)\|\|document\.write[^<]*</script>\n?", "", out)
open('/home/user/index.offline.html','w',encoding='utf-8').write(out)
print('index.html', len(src), '| index.offline.html', len(out))
PYEOF
python3 -c "
import re
src=open('/home/user/index.html',encoding='utf-8').read()
b=re.findall(r'<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>',src,re.S)
open('/tmp/chk.js','w',encoding='utf-8').write(b[-1])"
node --check /tmp/chk.js && echo "JS syntax OK"
