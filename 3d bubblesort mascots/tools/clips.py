"""
clips — the shared animation vocabulary for all five mascots.

Eight clips, identical names + durations on every character so the website can run
one state machine and swap characters without retiming anything:

    Idle     4.00s  loop    breathing, micro-sway, two blinks
    GlanceL  0.90s  hold    turn + look at the neighbour on the −X side (compare)
    GlanceR  0.90s  hold    mirror of GlanceL
    Crouch   0.50s  hold    anticipation squash before a hop
    Hop      0.72s  once    in-place vertical hop: crouch, launch, apex, fall, contact
    Land     0.50s  once    impact squash, rebound, settle
    NoSwap   0.95s  once    small "no swap needed" lean-away + head shake
    Success  1.25s  once    double bounce, happy squint, badge pop

Everything is authored around a normalised `phases()` dict so a character's own
appendages can react to the *same* core motion (secondary animation, offset by a
small lag) instead of being hand-keyed separately.
"""

import math

TAU = math.pi * 2.0


# ------------------------------------------------------------------- easing
def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3.0 - 2.0 * x)


def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1.0 - (1.0 - x) ** 3


def ease_in(x):
    x = min(max(x, 0.0), 1.0)
    return x ** 3


def keyed(t, keys, ease=smooth):
    """Piecewise interpolation over (time, value) keys."""
    if t <= keys[0][0]:
        return keys[0][1]
    for i in range(len(keys) - 1):
        t0, v0 = keys[i]
        t1, v1 = keys[i + 1]
        if t0 <= t <= t1:
            a = 0.0 if t1 <= t0 else (t - t0) / (t1 - t0)
            return v0 + (v1 - v0) * ease(a)
    return keys[-1][1]


def pulse(t, t0, dur, shape=smooth):
    """0 -> 1 -> 0 bump starting at t0."""
    if t <= t0 or t >= t0 + dur:
        return 0.0
    a = (t - t0) / dur
    return shape(a * 2.0) if a < 0.5 else shape((1.0 - a) * 2.0)


def blink(t, t0, dur=0.16):
    return pulse(t, t0, dur, shape=lambda x: ease_out(x) if x > 0.5 else x * x)


# ------------------------------------------------------------------- params
CLIP_SPECS = [("Idle", 4.00), ("GlanceL", 0.90), ("GlanceR", 0.90), ("Crouch", 0.50),
              ("Hop", 0.72), ("Land", 0.50), ("NoSwap", 0.95), ("Success", 1.25)]

# Base per-character animation tuning; each design overrides what it needs.
DEFAULT_PARAMS = {
    "hop_h": 0.30,          # hip rise at the apex (m)
    "crouch_d": 0.100,      # hip drop in the crouch (m)
    "land_d": 0.130,        # hip drop on landing impact (m)
    "squash": 1.00,         # multiplier on squash/stretch
    "gaze_yaw": -0.50,      # head yaw for GlanceL (radians; negative = look toward −X)
    "chest_yaw": 0.30,      # chest follows the head by this fraction
    "lid_close": 1.65,      # lid rotation that fully covers the eye (radians)
    "blink_ids": (1.05, 2.72),
    "legs": True,           # False -> the `base` bone takes the ground-contact work
    "breath": 1.00,
    "sway": 1.00,
    "eyelead": 0.011,       # how far the eyeballs shift toward a glance (m)
    "leg_squash": 0.78,     # airborne leg tuck
    "leg_len": 0.20,        # hip-to-ground distance: how far the legs can compress
    "up_scale": 1.00,       # 1.0 = hips travel the authored amount; legless
                            # silhouettes use <1 and squash more instead
}


def phases(clip, t, dur, P):
    """Normalised motion values shared by the core rig and the appendage hooks."""
    p = {
        "clip": clip, "t": t, "u": t / max(dur, 1e-6), "dur": dur,
        "up": 0.0, "sy": 1.0, "sxz": 1.0, "lid": 0.0, "air": 0.0,
        "gaze": 0.0, "chestgaze": 0.0, "nod": 0.0, "tilt": 0.0,
        "breath": math.sin(TAU * t / 4.0),      # exactly one cycle per Idle loop
        "lean": 0.0, "shake": 0.0, "happy": 0.0, "pop": 0.0,
        "legx": 0.0, "legsq": 1.0, "lag_up": 0.0, "impact": 0.0, "huff": 0.0,
    }
    gz = P["gaze_yaw"]

    if clip == "Idle":
        b = p["breath"]
        p["up"] = 0.009 * b * P["breath"]
        p["sy"] = 1.0 + 0.016 * b * P["breath"]
        p["sxz"] = 1.0 - 0.008 * b * P["breath"]
        p["nod"] = -0.012 + 0.020 * math.sin(TAU * t / 4.0 + 0.9) * P["breath"]
        p["gaze"] = 0.055 * math.sin(TAU * t / 2.0 + 0.4) * P["sway"]
        p["tilt"] = 0.014 * math.sin(TAU * t / 4.0 + 2.1) * P["sway"]
        p["chestgaze"] = p["gaze"] * 0.25
        p["lid"] = blink(t, P["blink_ids"][0], 0.15) + blink(t, P["blink_ids"][1], 0.13)
        p["happy"] = 0.0
        p["pop"] = 0.10 + 0.05 * math.sin(TAU * t / 4.0 + 1.4)

    elif clip in ("GlanceL", "GlanceR"):
        s = -1.0 if clip == "GlanceL" else 1.0
        p["gaze"] = s * keyed(t, [(0.0, 0.0), (0.26, gz * 1.14), (0.44, gz), (dur, gz)])
        p["chestgaze"] = p["gaze"] * P["chest_yaw"]
        p["nod"] = 0.055 * pulse(t, 0.30, 0.34) - 0.02 * pulse(t, 0.72, 0.20)
        p["tilt"] = -s * 0.05 * pulse(t, 0.22, 0.50)
        p["lid"] = blink(t, 0.50, 0.14) + 0.10 * pulse(t, 0.30, 0.30)
        p["up"] = 0.004 * pulse(t, 0.26, 0.40)

    elif clip == "Crouch":
        d = P["crouch_d"]
        p["up"] = keyed(t, [(0.0, 0.0), (0.22, -d * 1.10), (0.34, -d * 0.94), (dur, -d)])
        sq = keyed(t, [(0.0, 1.0), (0.22, 0.90), (0.34, 0.93), (dur, 0.915)])
        p["sy"] = 1.0 - (1.0 - sq) * P["squash"]
        p["sxz"] = 1.0 + (1.0 - sq) * 0.75 * P["squash"]
        p["nod"] = keyed(t, [(0.0, 0.0), (0.24, 0.14), (dur, 0.10)])
        p["lid"] = keyed(t, [(0.0, 0.0), (0.28, 0.26), (dur, 0.22)])
        p["legsq"] = 1.0 - (1.0 - P["leg_squash"]) * min(1.0, keyed(t, [(0.0, 0.0), (0.26, 1.0), (dur, 1.0)]))

    elif clip == "Hop":
        h = P["hop_h"]
        p["up"] = keyed(t, [(0.0, 0.0), (0.10, -h * 0.26), (0.16, -h * 0.10), (0.32, h),
                            (0.40, h * 0.96), (0.55, h * 0.34), (0.62, 0.0),
                            (0.66, -h * 0.20), (0.72, -h * 0.06)],
                        ease=lambda x: smooth(x))
        # ballistic feel: fast rise, slower top, accelerating fall
        stretch = keyed(t, [(0.0, 1.0), (0.10, 0.94), (0.20, 1.10), (0.34, 1.02),
                            (0.44, 1.06), (0.58, 1.10), (0.66, 0.90), (0.72, 0.97)])
        p["sy"] = 1.0 + (stretch - 1.0) * P["squash"]
        p["sxz"] = 1.0 + (1.0 - stretch) * 0.7 * P["squash"]
        air = keyed(t, [(0.0, 0.0), (0.20, 1.0), (0.55, 1.0), (0.66, 0.0), (0.72, 0.0)])
        p["air"] = air
        p["legx"] = air * 0.20
        p["legsq"] = 1.0 - 0.30 * air
        p["nod"] = keyed(t, [(0.0, 0.0), (0.16, 0.10), (0.34, -0.10), (0.55, -0.06), (0.66, 0.14), (0.72, 0.06)])
        p["lid"] = keyed(t, [(0.0, 0.10), (0.20, -0.06), (0.55, 0.0), (0.64, 0.45), (0.72, 0.18)])
        p["impact"] = pulse(t, 0.62, 0.10)
        p["lag_up"] = keyed(t, [(0.0, 0.0), (0.16, -h * 0.26), (0.38, h), (0.61, h * 0.34),
                                (0.70, 0.0), (0.72, 0.0)]) * 0.42

    elif clip == "Land":
        d = P["land_d"]
        p["up"] = keyed(t, [(0.0, 0.0), (0.06, -d), (0.18, 0.018), (0.30, -0.012),
                            (0.40, 0.004), (dur, 0.0)])
        sy = keyed(t, [(0.0, 1.06), (0.06, 0.84), (0.20, 1.03), (0.34, 0.99), (dur, 1.0)])
        p["sy"] = 1.0 + (sy - 1.0) * P["squash"]
        p["sxz"] = 1.0 + (1.0 - sy) * 0.75 * P["squash"]
        p["nod"] = keyed(t, [(0.0, 0.10), (0.08, 0.20), (0.22, -0.06), (0.36, 0.02), (dur, 0.0)])
        p["lid"] = keyed(t, [(0.0, 0.30), (0.08, 0.55), (0.26, 0.10), (dur, 0.0)])
        p["impact"] = pulse(t, 0.0, 0.16)
        p["legsq"] = 1.0 - (1.0 - P["leg_squash"]) * min(1.0, keyed(t, [(0.0, 0.6), (0.06, 1.0), (0.22, 0.0), (dur, 0.0)]))
        p["lag_up"] = keyed(t, [(0.0, 0.10), (0.10, -d * 0.5), (0.30, 0.05), (0.50, 0.0)]) * 0.4

    elif clip == "NoSwap":
        lean = keyed(t, [(0.0, 0.0), (0.14, 0.115), (0.30, 0.10), (0.58, 0.105), (0.78, 0.02), (dur, 0.0)])
        p["lean"] = lean
        p["shake"] = keyed(t, [(0.0, 0.0), (0.24, -0.20), (0.34, 0.18), (0.44, -0.13),
                               (0.54, 0.08), (0.64, -0.03), (0.72, 0.0), (dur, 0.0)])
        p["huff"] = pulse(t, 0.62, 0.26) + pulse(t, 0.14, 0.20) * 0.6
        p["lid"] = keyed(t, [(0.0, 0.0), (0.18, 0.10), (0.34, 0.34), (0.70, 0.30), (0.86, 0.05), (dur, 0.0)])
        p["nod"] = keyed(t, [(0.0, 0.0), (0.16, -0.06), (0.40, -0.02), (0.66, 0.08), (dur, 0.0)])
        p["up"] = keyed(t, [(0.0, 0.0), (0.16, -0.012), (0.34, 0.0), (dur, 0.0)])
        p["tilt"] = -p["lean"] * 0.35

    elif clip == "Success":
        p["up"] = keyed(t, [(0.0, 0.0), (0.12, 0.085), (0.22, 0.0), (0.36, 0.050),
                            (0.46, 0.0), (0.58, 0.018), (0.68, 0.0), (dur, 0.0)])
        sy = keyed(t, [(0.0, 1.0), (0.10, 1.06), (0.12, 1.05), (0.22, 0.94), (0.28, 1.0),
                       (0.44, 0.96), (0.50, 1.0), (0.66, 0.985), (dur, 1.0)])
        p["sy"] = 1.0 + (sy - 1.0) * P["squash"]
        p["sxz"] = 1.0 + (1.0 - sy) * 0.8 * P["squash"]
        p["happy"] = keyed(t, [(0.0, 0.0), (0.16, 0.85), (0.70, 0.8), (0.95, 0.25), (dur, 0.0)])
        p["lid"] = p["happy"] * 0.42
        p["nod"] = keyed(t, [(0.0, 0.0), (0.14, -0.16), (0.28, 0.06), (0.40, -0.12), (0.56, 0.03), (dur, 0.0)])
        p["gaze"] = keyed(t, [(0.0, 0.0), (0.18, -0.13), (0.36, 0.13), (0.60, 0.0), (dur, 0.0)])
        p["tilt"] = keyed(t, [(0.0, 0.0), (0.20, 0.13), (0.46, -0.10), (0.72, 0.04), (dur, 0.0)])
        p["pop"] = keyed(t, [(0.0, 0.0), (0.10, 1.0), (0.30, 0.15), (0.40, 0.35), (0.60, 0.0), (dur, 0.0)])
        p["impact"] = pulse(t, 0.20, 0.14) + pulse(t, 0.44, 0.14)
        p["air"] = keyed(t, [(0.0, 0.0), (0.05, 1.0), (0.17, 0.0), (0.31, 0.0), (0.34, 1.0),
                             (0.43, 0.0), (0.55, 0.0), (0.60, 1.0), (0.66, 0.0), (dur, 0.0)])
        p["lag_up"] = keyed(t, [(0.0, 0.0), (0.16, 0.085), (0.26, 0.0), (0.40, 0.050),
                                (0.50, 0.0), (0.62, 0.018), (dur, 0.0)]) * 0.45
    return p


# ------------------------------------------------------------------ core pose
def core_pose(clip, ph, P):
    """Build the shared 14-bone pose from the phase dict."""
    lid = ph["lid"] * P["lid_close"]
    pose = {}
    up_eff = ph["up"] * P["up_scale"]
    air = min(max(ph.get("air", 0.0), 0.0), 1.0)

    # root stays put: every hop is in place, the website moves the slot x/z
    pose["root"] = {"r": (0.0, 0.0, 0.0), "t": (0.0, 0.0, 0.0)}

    hips = {"t": (0.0, up_eff, 0.0), "s": (ph["sxz"], ph["sy"], ph["sxz"])}
    pose["hips"] = hips

    breath = ph.get("breath", 0.0)
    chest_sy = 1.0 + 0.014 * breath * P["breath"]
    chest = {"s": (1.0 / chest_sy ** 0.5, chest_sy, 1.0 / chest_sy ** 0.5)}
    chest["r"] = (ph["nod"] * 0.45, ph["chestgaze"], ph["lean"] * 0.55)
    if ph.get("happy"):
        chest["s"] = (chest["s"][0] * (1.0 + 0.05 * ph["happy"]),
                      chest["s"][1] * (1.0 + 0.02 * ph["happy"]),
                      chest["s"][2] * (1.0 + 0.05 * ph["happy"]))
    pose["chest"] = chest

    pose["spine"] = {"r": (ph["nod"] * 0.25, ph["chestgaze"] * 0.4, ph["lean"] * 0.75),
                     "s": (1.0, 1.0 + 0.008 * breath, 1.0)}

    pose["neck"] = {"r": (ph["nod"] * 0.25, ph["gaze"] * 0.30, ph["tilt"] * 0.35)}
    pose["head"] = {"r": (ph["nod"] * 0.5, ph["gaze"] * 0.70 + ph["shake"],
                          ph["tilt"] + ph["happy"] * 0.03)}

    # eyelids: +rx sweeps the lid down over the eye
    pose["lidL"] = {"r": (lid, 0.0, 0.0)}
    pose["lidR"] = {"r": (lid, 0.0, 0.0)}

    lead = P["eyelead"] * (-ph["gaze"] / max(abs(P["gaze_yaw"]), 1e-6))
    eye_s = 1.0 - 0.06 * ph["happy"]
    pose["eyeL"] = {"t": (-lead, 0.0, 0.0), "s": (eye_s, eye_s, eye_s)}
    pose["eyeR"] = {"t": (-lead, 0.0, 0.0), "s": (eye_s, eye_s, eye_s)}

    pop = ph.get("pop", 0.0)
    pose["badge"] = {"s": (1.0 + 0.10 * pop, 1.0 + 0.10 * pop, 1.0)}

    # ---- legs / ground contact -------------------------------------------
    # Legged silhouettes: the legs compress by exactly the hip travel so the feet
    # stay planted while the body squashes. Legless silhouettes get the same
    # treatment from the `base` pad bone, which counter-translates in the air.
    if P["legs"]:
        L = max(P["leg_len"], 1e-3)
        s_plant = min(max(1.0 + up_eff / L, 0.35), 1.6)
        tuck = min(max(ph.get("legsq", 1.0), 0.4), 1.6)
        ls = (1.0 - air) * s_plant + air * tuck
        leg_t = (0.0, 0.0, 0.0)
    else:
        ls = min(max(ph.get("legsq", 1.0), 0.5), 1.3)
        leg_t = (0.0, 0.0, 0.0)
    legx = ph.get("legx", 0.0)
    for name in ("legL", "legR"):
        pose[name] = {"r": (legx, 0.0, 0.0), "s": (1.0 / ls ** 0.4, ls, 1.0 / ls ** 0.4),
                      "t": leg_t}

    if not P["legs"]:
        # pad stays on the floor while grounded, rides up with the body in the air
        pose["base"] = {"t": (0.0, -up_eff * (1.0 - air), 0.0),
                        "s": (ph["sxz"] ** 0.5, min(max(ph["sy"], 0.62), 1.25), ph["sxz"] ** 0.5)}
    else:
        pose["base"] = {"s": (1.0, 1.0, 1.0)}
    return pose


def build_clip_fns(char):
    """Return {clip_name: (duration, pose_fn)} for a character object."""
    out = {}
    for name, dur in CLIP_SPECS:
        def fn(t, _name=name, _dur=dur):
            ph = phases(_name, float(t), _dur, char.P)
            pose = core_pose(_name, ph, char.P)
            extra = char.extras(_name, float(t), _dur, ph)
            for k, v in (extra or {}).items():
                if k in pose:
                    merged = dict(pose[k])
                    merged.update({kk: vv for kk, vv in v.items() if vv is not None})
                    pose[k] = merged
                else:
                    pose[k] = v
            return pose
        out[name] = (dur, fn)
    return out
