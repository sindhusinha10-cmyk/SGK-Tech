"""
textures — small procedural PNG detail maps (multiplicative, near-white).

These are *detail* maps, not colour maps: they multiply the per-material
baseColorFactor, so every character keeps its palette while picking up a surface
identity (glazed ceramic, woven fibre, mineral grain, twisted cord, soft matte).
All maps are tileable and 256² so the five GLBs stay tiny.
"""

import io
import math

import numpy as np
from PIL import Image

SIZE = 256


def _vnoise(rng, cells, size=SIZE):
    """Tileable value noise in [0,1]."""
    g = rng.rand(cells, cells)
    xs = np.linspace(0.0, cells, size, endpoint=False)
    x0 = np.floor(xs).astype(int) % cells
    x1 = (x0 + 1) % cells
    f = xs - np.floor(xs)
    f = f * f * (3.0 - 2.0 * f)
    A = g[np.ix_(x0, x0)]
    B = g[np.ix_(x1, x0)]
    C = g[np.ix_(x0, x1)]
    D = g[np.ix_(x1, x1)]
    fx = f[None, :]
    fy = f[:, None]
    top = A * (1 - fx) + B * fx
    bot = C * (1 - fx) + D * fx
    return top * (1 - fy) + bot * fy


def _fbm(rng, cells, octaves=4, size=SIZE):
    out = np.zeros((size, size))
    amp, tot = 1.0, 0.0
    for o in range(octaves):
        out += amp * _vnoise(rng, cells * (2 ** o), size)
        tot += amp
        amp *= 0.5
    return out / tot


def _norm(a, lo, hi):
    a = a - a.min()
    m = a.max() if a.max() > 1e-9 else 1.0
    return lo + (a / m) * (hi - lo)


def ceramic(seed=11):
    rng = np.random.RandomState(seed)
    speck = _fbm(rng, 3, octaves=5)
    mottle = _fbm(rng, 6, octaves=3)
    t = 0.90 + 0.05 * (speck - 0.5) * 2.0
    t += 0.045 * np.sin(2 * math.pi * np.linspace(0, 1, SIZE))[None, :]   # glaze runnel
    t *= 1.0 - 0.06 * np.clip(mottle - 0.62, 0, 1) * 2.0
    return t


def weave(seed=23):
    """Over-under basket weave, tileable at 16 px per strand pair."""
    rng = np.random.RandomState(seed)
    y, x = np.mgrid[0:SIZE, 0:SIZE].astype(float)
    per = 32.0
    tex = np.zeros((SIZE, SIZE))
    # two crossed families of rounded strands; where they cross, one wins -> weave
    strip_a = 0.5 + 0.5 * np.cos(2 * np.pi * x / per)
    strip_b = 0.5 + 0.5 * np.cos(2 * np.pi * y / per)
    cell = (np.floor(x / (per / 2)) + np.floor(y / (per / 2))) % 2
    over_a = cell == 0
    tex = np.where(over_a, strip_a, strip_b)
    tex = 0.86 + 0.16 * tex
    fibre = _fbm(rng, 8, octaves=4)
    tex *= 0.97 + 0.06 * (fibre - 0.5)
    tex = np.clip(tex, 0.55, 1.0)
    return tex


def stone(seed=37):
    rng = np.random.RandomState(seed)
    mottle = _fbm(rng, 4, octaves=5)
    grain = _fbm(rng, 24, octaves=3)
    seams = np.abs(_fbm(rng, 3, octaves=3) - 0.5)
    t = 0.92 + 0.06 * (mottle - 0.5) * 2.0
    t += 0.05 * (grain - 0.5)
    t -= 0.10 * np.clip(0.06 - seams, 0, 1) * 4.0
    return t


def cord(seed=51):
    rng = np.random.RandomState(seed)
    y, x = np.mgrid[0:SIZE, 0:SIZE].astype(float)
    twist = 0.5 + 0.5 * np.sin((x * 0.75 + y * 0.42) * 2 * np.pi / 26.0)
    tex = 0.88 + 0.12 * twist
    fibre = _fbm(rng, 16, octaves=3)
    tex *= 0.98 + 0.05 * (fibre - 0.5)
    return tex


def matte(seed=71):
    rng = np.random.RandomState(seed)
    grain = _fbm(rng, 20, octaves=4)
    soft = _fbm(rng, 5, octaves=3)
    return 0.95 + 0.035 * (grain - 0.5) + 0.02 * (soft - 0.5)


def metal_brush(seed=91):
    rng = np.random.RandomState(seed)
    y, x = np.mgrid[0:SIZE, 0:SIZE].astype(float)
    streaks = _fbm(rng, 4, octaves=4)
    streaks = streaks.mean(axis=0)[None, :] * np.ones((SIZE, 1))
    fine = _fbm(rng, 30, octaves=3)
    return 0.94 + 0.05 * (streaks - 0.5) + 0.03 * (fine - 0.5)


KINDS = {
    "ceramic": ceramic,
    "weave": weave,
    "stone": stone,
    "cord": cord,
    "matte": matte,
    "metal": metal_brush,
}


def png_bytes(kind, size=SIZE):
    fn = KINDS[kind]
    t = np.clip(fn(), 0.0, 1.0)
    if t.shape != (size, size):
        t = np.clip(t, 0, 1)
    arr = (t * 255.0).astype(np.uint8)
    rgb = np.dstack([arr, arr, arr])
    buf = io.BytesIO()
    Image.fromarray(rgb, "RGB").save(buf, format="PNG", optimize=True)
    return buf.getvalue()


if __name__ == "__main__":
    for k in KINDS:
        print(k, len(png_bytes(k)), "bytes")
