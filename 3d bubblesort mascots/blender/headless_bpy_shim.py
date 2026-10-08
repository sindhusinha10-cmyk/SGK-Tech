#!/usr/bin/env python3
"""
headless_bpy_shim.py — build the tiny stub libraries needed to `import bpy` in a
container that has no X server and no Mesa.

WHY THIS EXISTS
    Blender 4.2.23 LTS is installable straight from PyPI (`pip install bpy==4.2.23`,
    the official upstream wheel). Its `__init__.so` links against a handful of X11 /
    input / GL sonames that a slim Debian container does not ship:

        libXrender.so.1  libXxf86vm.so.1  libXfixes.so.3  libXi.so.6
        libxkbcommon.so.0  libSM.so.6  libICE.so.6  libGL.so.1  libXt.so.6

    With no root access and no Debian mirror reachable, they cannot be installed. So
    this script generates minimal stand-in shared objects that ((a)) exist under the
    right soname and ((b)) define the symbols the loader demands, as no-op functions
    returning NULL.

    It is only ever a *loader* requirement. Every one of those symbols lives inside
    an X11 / GL call path that Blender never enters in `--background` mode: no window,
    no GL context, no display. Rendering in this project is done with **Cycles on
    CPU**, which goes nowhere near them. Nothing in the shipped models, textures,
    renders or .blend files depends on this shim.

    It does not touch, patch or re-link Blender itself, and it is not needed at all on
    a normal desktop with an X server.

USAGE
    python3 blender/headless_bpy_shim.py            # writes /tmp/bpy-shim/lib/*.so
    export LD_LIBRARY_PATH=/tmp/bpy-shim/lib:$LD_LIBRARY_PATH
    export LD_PRELOAD=/tmp/bpy-shim/lib/libbpy_shim.so
    python3 blender/make_blend.py

    (On a machine where Blender is installed normally, just use
     `blender --background --python blender/make_blend.py` and ignore this file.)
"""

import os
import re
import subprocess
import sys

SHIM_DIR = "/tmp/bpy-shim/lib"
WORK = "/tmp/bpy-shim/work"
SHIM = os.path.join(SHIM_DIR, "libbpy_shim.so")
SHIM_SRC = os.path.join(WORK, "shim.c")

# sonames that must exist even if they contribute no symbol we can see coming
STUB_SONAMES = [
    "libXrender.so.1", "libXxf86vm.so.1", "libXfixes.so.3", "libXi.so.6",
    "libxkbcommon.so.0", "libSM.so.6", "libICE.so.6", "libGL.so.1", "libXt.so.6",
]

# symbols are routed to a soname by prefix; anything unmatched lands in the preload shim
PREFIX_RULES = [
    ("xkb_", "libxkbcommon.so.0", "V_0.5.0"),
    ("XF86VidMode", "libXxf86vm.so.1", None),
    ("XFixes", "libXfixes.so.3", None),
    ("XOpenDevice", "libXi.so.6", None),
    ("XCloseDevice", "libXi.so.6", None),
    ("XListInputDevices", "libXi.so.6", None),
    ("XFreeDeviceList", "libXi.so.6", None),
    ("XQueryDeviceState", "libXi.so.6", None),
    ("XFreeDeviceState", "libXi.so.6", None),
    ("_XiGetDevicePresenceNotifyEvent", "libXi.so.6", None),
    ("XGetExtensionVersion", "libXi.so.6", None),
    ("XGetSelectedExtensionEvents", "libXi.so.6", None),
    ("XSelectExtensionEvent", "libXi.so.6", None),
    ("XInput", "libXi.so.6", None),
    ("XRender", "libXrender.so.1", None),
    ("Smc", "libSM.so.6", None),
    ("Sms", "libSM.so.6", None),
    ("Sm", "libSM.so.6", None),
    ("Ice", "libICE.so.6", None),
    ("Xt", "libXt.so.6", None),
    ("glX", "libGL.so.1", None),
    ("egl", "libGL.so.1", None),
    ("gl", "libGL.so.1", None),
]


def bpy_dir():
    import importlib.util
    spec = importlib.util.find_spec("bpy")
    if spec is None or not spec.origin:
        raise SystemExit("bpy is not installed: pip install bpy==4.2.23")
    return os.path.dirname(spec.origin)


def elf_objects(root):
    objs = [os.path.join(root, "__init__.so"), sys.executable]
    for path, _dirs, files in os.walk(root):
        for f in files:
            if ".so" in f:
                objs.append(os.path.join(path, f))
    return [o for o in objs if os.path.isfile(o)]


def dynsym(path, want):
    """Parse `readelf --dyn-syms`. want is 'UND' or 'DEF'."""
    try:
        out = subprocess.run(["readelf", "--dyn-syms", "-W", path],
                             capture_output=True, text=True, timeout=120).stdout
    except Exception:
        return {}
    found = {}
    for line in out.splitlines():
        p = line.split()
        if len(p) < 8:                       # Num: Value Size Type Bind Vis Ndx Name
            continue
        typ, ndx, name = p[3], p[6], p[7]
        if typ not in ("FUNC", "OBJECT", "IFUNC", "NOTYPE"):
            continue
        if want == "UND" and ndx != "UND":
            continue
        if want == "DEF" and ndx == "UND":
            continue
        ver = None
        if "@" in name:
            name, _, ver = name.partition("@")
            ver = ver.strip("()")
        if not name or name == "UND":
            continue
        found.setdefault(name, ver)
    return found


def compile_stub(soname, syms):
    c = os.path.join(WORK, soname.replace(".", "_") + ".c")
    with open(c, "w") as fh:
        fh.write("/* auto-generated loader stub - never called in --background mode */\n")
        for name, _v in syms:
            fh.write("void *%s(void) { return 0; }\n" % name)
        if not syms:
            fh.write("int __sgk_placeholder(void) { return 0; }\n")
    cmd = ["gcc", "-shared", "-fPIC", "-O0", "-w",
           "-o", os.path.join(SHIM_DIR, soname), c, "-Wl,-soname,%s" % soname]
    vers = sorted({v for _n, v in syms if v})
    if vers:
        vmap = os.path.join(WORK, soname + ".map")
        with open(vmap, "w") as fh:
            for v in vers:
                fh.write("%s {\n  global:\n" % v)
                for n, nv in syms:
                    if nv == v:
                        fh.write("    %s;\n" % n)
                fh.write("  local: *;\n};\n")
        cmd.append("-Wl,--version-script,%s" % vmap)
    r = subprocess.run(cmd, capture_output=True, text=True)
    return r.returncode == 0, r.stderr


def build_preload(extra):
    """Every X/GL symbol bpy references that the system does not already provide."""
    root = bpy_dir()
    und = {}
    for o in elf_objects(root):
        und.update(dynsym(o, "UND"))

    provided = set()
    for p in ("/usr/lib/x86_64-linux-gnu/libX11.so.6",
              "/usr/lib/x86_64-linux-gnu/libXext.so.6",
              "/usr/lib/x86_64-linux-gnu/libxcb.so.1"):
        if os.path.exists(p):
            provided |= set(dynsym(p, "DEF"))

    wanted = []
    for name in sorted(und):
        if name in provided or name.startswith("Py"):
            continue
        for prefix, _lib, _ver in PREFIX_RULES:
            if name.startswith(prefix):
                wanted.append(name)
                break
    syms = sorted(set(wanted) | set(extra))
    with open(SHIM_SRC, "w") as fh:
        fh.write("/* auto-generated preload shim for headless bpy */\n")
        for s in syms:
            fh.write("void *%s(void) { return 0; }\n" % s)
    r = subprocess.run(["gcc", "-shared", "-fPIC", "-O0", "-w", "-o", SHIM, SHIM_SRC],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(r.stderr[:2000])
    return syms


def verify():
    env = dict(os.environ)
    env["LD_LIBRARY_PATH"] = SHIM_DIR + ":" + env.get("LD_LIBRARY_PATH", "")
    env["LD_PRELOAD"] = SHIM
    r = subprocess.run([sys.executable, "-c",
                        "import bpy; print(bpy.app.version_string)"],
                       capture_output=True, text=True, env=env)
    return r.returncode, (r.stdout + r.stderr).strip()


def main():
    os.makedirs(SHIM_DIR, exist_ok=True)
    os.makedirs(WORK, exist_ok=True)
    root = bpy_dir()
    print("bpy found at %s" % root)

    und = {}
    for o in elf_objects(root):
        und.update(dynsym(o, "UND"))

    buckets = {s: [] for s in STUB_SONAMES}
    leftovers = []
    for name, ver in sorted(und.items()):
        hit = None
        for prefix, lib, _v in PREFIX_RULES:
            if name.startswith(prefix):
                hit = lib
                break
        if hit:
            buckets[hit].append((name, ver))
        elif name.startswith(("X", "gl", "egl")) and not name.startswith("Xlib"):
            leftovers.append(name)

    for soname in STUB_SONAMES:
        ok, err = compile_stub(soname, buckets[soname])
        print("  %-22s %3d symbols  %s" % (soname, len(buckets[soname]),
                                           "ok" if ok else "FAILED"))
        if not ok:
            print(err[:600])

    extra = set(leftovers)
    for _round in range(1, 41):
        build_preload(extra)
        code, out = verify()
        if code == 0:
            print("\n  import bpy -> %s" % out)
            print("  stubs in %s" % SHIM_DIR)
            print("\n  export LD_LIBRARY_PATH=%s:$LD_LIBRARY_PATH" % SHIM_DIR)
            print("  export LD_PRELOAD=%s" % SHIM)
            return 0
        m = re.search(r"undefined symbol: (\S+)", out)
        if not m or m.group(1) in extra:
            print(out[-2000:])
            return 1
        extra.add(m.group(1))
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
