"""Gild the stock Lottie (.tgs) illustrations onto the Syyn palette, and build the Syyn bolt animations.

    python tools/syyn_assets/make_animations.py recolor <animations-dir> [--list recolor.txt] [--dry]
    python tools/syyn_assets/make_animations.py bolt <animations-dir>

`recolor` maps every fill, stroke and gradient stop to a gold duotone by perceptual lightness, so the
shading and the timing of each animation are untouched and only the hue family changes. Emoji-like
art whose colours carry meaning (the dice, the star reactions, flags) is not in the list.
`bolt` writes the new Syyn animations (see below).
"""
from __future__ import annotations

import argparse
import copy
import gzip
import json
import math
import os
import sys

# L* (0..100) -> colour; monotonic, so highlights stay light and shadows stay deep.
GILD_RAMP = [
    (0.0, (0x3A, 0x2C, 0x12)),
    (14.0, (0x5E, 0x47, 0x1B)),
    (30.0, (0x8A, 0x6C, 0x26)),
    (46.0, (0xB5, 0x8F, 0x38)),
    (60.0, (0xD0, 0xA8, 0x4A)),
    (74.0, (0xE6, 0xC4, 0x6C)),
    (87.0, (0xF4, 0xDF, 0x9E)),
    (100.0, (0xFF, 0xF6, 0xDD)),
]


def lstar(r: float, g: float, b: float) -> float:
    def lin(c: float) -> float:
        return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

    y = 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)
    f = y ** (1 / 3) if y > 216 / 24389 else (24389 / 27 * y + 16) / 116
    return max(0.0, min(100.0, 116 * f - 16))


def gild(r: float, g: float, b: float) -> tuple[float, float, float]:
    l = lstar(r, g, b)
    for (l0, c0), (l1, c1) in zip(GILD_RAMP, GILD_RAMP[1:]):
        if l0 <= l <= l1:
            t = (l - l0) / (l1 - l0)
            return tuple(round((c0[i] + (c1[i] - c0[i]) * t) / 255, 4) for i in range(3))  # type: ignore[return-value]
    return tuple(round(c / 255, 4) for c in GILD_RAMP[-1][1])  # type: ignore[return-value]


def _is_number_list(value) -> bool:
    return isinstance(value, list) and value and all(isinstance(x, (int, float)) for x in value)


def recolor_color_prop(prop: dict) -> None:
    """A Lottie colour property: static `k=[r,g,b,(a)]` or keyframed `k=[{s:[...],e:[...]}]`."""
    k = prop.get("k")
    if _is_number_list(k) and len(k) >= 3:
        k[0], k[1], k[2] = gild(k[0], k[1], k[2])
    elif isinstance(k, list):
        for frame in k:
            if not isinstance(frame, dict):
                continue
            for field in ("s", "e"):
                v = frame.get(field)
                if _is_number_list(v) and len(v) >= 3:
                    v[0], v[1], v[2] = gild(v[0], v[1], v[2])


def recolor_gradient(grad: dict) -> None:
    """Gradient stops are one flat list: p stops of [offset, r, g, b], then optional alpha stops."""
    count = grad.get("p", 0)
    stops = grad.get("k", {})
    k = stops.get("k")
    lists = []
    if _is_number_list(k):
        lists.append(k)
    elif isinstance(k, list):
        for frame in k:
            if isinstance(frame, dict):
                for field in ("s", "e"):
                    if _is_number_list(frame.get(field)):
                        lists.append(frame[field])
    for flat in lists:
        for i in range(count):
            base = i * 4
            if base + 3 < len(flat):
                flat[base + 1], flat[base + 2], flat[base + 3] = gild(flat[base + 1], flat[base + 2], flat[base + 3])


def walk(node) -> int:
    changed = 0
    if isinstance(node, dict):
        ty = node.get("ty")
        if ty in ("fl", "st") and isinstance(node.get("c"), dict):
            recolor_color_prop(node["c"])
            changed += 1
        elif ty in ("gf", "gs") and isinstance(node.get("g"), dict):
            recolor_gradient(node["g"])
            changed += 1
        elif ty == 1 and isinstance(node.get("sc"), str) and node["sc"].startswith("#") and len(node["sc"]) == 7:
            r, g, b = (int(node["sc"][i:i + 2], 16) / 255 for i in (1, 3, 5))
            node["sc"] = "#%02x%02x%02x" % tuple(round(c * 255) for c in gild(r, g, b))
            changed += 1
        for value in node.values():
            changed += walk(value)
    elif isinstance(node, list):
        for value in node:
            changed += walk(value)
    return changed


def read_tgs(path: str) -> dict:
    with gzip.open(path, "rb") as handle:
        return json.loads(handle.read())


def write_tgs(path: str, data: dict) -> None:
    raw = json.dumps(data, separators=(",", ":")).encode("utf-8")
    with open(path, "wb") as handle:
        handle.write(gzip.compress(raw, compresslevel=9, mtime=0))


def recolor(directory: str, names: list[str], dry: bool) -> None:
    for name in names:
        path = os.path.join(directory, name)
        data = read_tgs(path)
        changed = walk(data)
        if not dry:
            write_tgs(path, data)
        print(f"{'would gild' if dry else 'gilded'} {name}: {changed} colour objects")


# ---------------------------------------------------------------------------------------------
# New animations. Telegram's sticker format: 512 x 512, 60 fps, at most 3 s, vector shapes only
# (no expressions, effects, images or text), and a file under 64 KB.

BOLT = [(15.5, 1.0), (4.0, 31.0), (11.6, 29.4), (7.0, 55.0), (20.5, 21.0), (12.9, 22.8), (18.6, 1.0)]


def _static(v):
    return {"a": 0, "k": v}


def _anim(keys, dims=1):
    """keys: [(frame, value, ease_out, ease_in)] -> Lottie keyframes with bezier easing.

    `dims=2` repeats a scalar for a two-dimensional property such as scale."""
    frames = []
    for i, (t, v, *rest) in enumerate(keys):
        entry = {"t": t, "s": v if isinstance(v, list) else [v] * dims}
        if i < len(keys) - 1:
            o, n = (rest + [(0.33, 0.0), (0.67, 1.0)])[:2] if len(rest) < 2 else rest
            entry["o"] = {"x": [o[0]], "y": [o[1]]}
            entry["i"] = {"x": [n[0]], "y": [n[1]]}
        frames.append(entry)
    return {"a": 1, "k": frames}


EASE_OUT = [(0.2, 0.0), (0.0, 1.0)]
EASE_IN_OUT = [(0.42, 0.0), (0.58, 1.0)]


def transform(anchor=(0, 0), position=(256, 256), scale=100, rotation=0, opacity=100):
    def prop(v):
        return v if isinstance(v, dict) else _static(v)

    return {
        "o": prop(opacity),
        "r": prop(rotation),
        "p": prop(list(position) if not isinstance(position, dict) else position),
        "a": _static(list(anchor)),
        "s": prop([scale, scale] if not isinstance(scale, dict) else scale),
    }


def group(items, name="Group"):
    return {"ty": "gr", "it": items + [{"ty": "tr", **transform((0, 0), (0, 0))}], "nm": name}


def bolt_path(scale: float, cx: float, cy: float) -> dict:
    mx, my = (4.0 + 20.5) / 2, (1.0 + 55.0) / 2
    pts = [((x - mx) * scale + cx, (y - my) * scale + cy) for x, y in BOLT]
    n = len(pts)
    return {
        "ty": "sh",
        "ks": _static({"c": True, "v": [list(p) for p in pts], "i": [[0, 0]] * n, "o": [[0, 0]] * n}),
        "nm": "Bolt",
    }


def ellipse(size: float, cx: float = 0, cy: float = 0) -> dict:
    return {"ty": "el", "p": _static([cx, cy]), "s": _static([size, size]), "nm": "Ellipse"}


def fill(rgb: tuple[float, float, float], opacity=100) -> dict:
    return {"ty": "fl", "c": _static([*rgb, 1]), "o": _static(opacity) if not isinstance(opacity, dict) else opacity, "r": 1, "nm": "Fill"}


def halo_fill(rgb, radius: float, strength) -> dict:
    """A radial glow: the colour at `strength` percent in the middle, fading to nothing at `radius`."""
    stops = [0, *rgb, 0.45, *rgb, 1, *rgb, 0, 0.5, 0.45, 0.18, 1, 0]
    return {
        "ty": "gf", "o": strength if isinstance(strength, dict) else _static(strength), "r": 1, "t": 2,
        "s": _static([0, 0]), "e": _static([radius, 0]), "h": _static(0), "a": _static(0),
        "g": {"p": 3, "k": _static(stops)}, "nm": "Glow",
    }


def stroke(rgb, width, opacity=100) -> dict:
    return {
        "ty": "st", "c": _static([*rgb, 1]), "o": _static(opacity) if not isinstance(opacity, dict) else opacity,
        "w": _static(width) if not isinstance(width, dict) else width, "lc": 2, "lj": 2, "nm": "Stroke",
    }


def trim(end) -> dict:
    return {"ty": "tm", "s": _static(0), "e": end if isinstance(end, dict) else _static(end), "o": _static(0), "m": 1, "nm": "Trim"}


def shape_layer(name: str, shapes: list, tr: dict, ind: int, frames: int, parent=None) -> dict:
    layer = {
        "ddd": 0, "ind": ind, "ty": 4, "nm": name, "sr": 1, "ks": tr, "ao": 0, "shapes": shapes,
        "ip": 0, "op": frames, "st": 0, "bm": 0,
    }
    if parent:
        layer["parent"] = parent
    return layer


def hexf(value: str) -> tuple[float, float, float]:
    return tuple(int(value[i:i + 2], 16) / 255 for i in (1, 3, 5))  # type: ignore[return-value]


# Mid golds with a dark gold edge, so the mark reads on the night themes and on parchment alike.
GOLD400, GOLD500, GOLD600, GOLD700 = hexf("#E2B85A"), hexf("#C9A24A"), hexf("#A9842F"), hexf("#7D6122")


def lottie(name: str, frames: int, layers: list) -> dict:
    return {"v": "5.5.2", "fr": 60, "ip": 0, "op": frames, "w": 512, "h": 512, "nm": name, "ddd": 0, "assets": [], "layers": layers}


def bolt_strike() -> dict:
    """The mark arriving: a ring draws round, the bolt strikes in, a halo breathes. 120 frames (2 s)."""
    frames = 120
    ring = shape_layer(
        "Ring",
        [group([ellipse(380), trim(_anim([(0, 0, *EASE_OUT), (50, 100)])), stroke(GOLD400, 10)], "Ring")],
        transform(position=(256, 256), rotation=_anim([(0, -90, *EASE_OUT), (50, -90)])),
        3, frames,
    )
    halo = shape_layer(
        "Halo",
        [group([ellipse(340), halo_fill(GOLD400, 170, _anim([(0, 0, *EASE_IN_OUT), (45, 0, *EASE_IN_OUT), (75, 100, *EASE_IN_OUT), (100, 60, *EASE_IN_OUT), (120, 80)]))], "Halo")],
        transform(position=(256, 256), scale=_anim([(40, 70, *EASE_OUT), (80, 118, *EASE_IN_OUT), (120, 104)], 2)),
        2, frames,
    )
    bolt = shape_layer(
        "Bolt",
        [group([bolt_path(5.6, 0, 0), fill(GOLD400), stroke(GOLD700, 5)], "Bolt")],
        transform(
            position=_anim([(26, [256, 232], *EASE_OUT), (46, [256, 256])]),
            scale=_anim([(26, 78, *EASE_OUT), (46, 100)], 2),
            opacity=_anim([(26, 0), (34, 100)]),
        ),
        1, frames,
    )
    return lottie("syyn_bolt_strike", frames, [bolt, halo, ring])


def bolt_pulse() -> dict:
    """A calm idle loop for the veil and the security card: the bolt breathes inside a slow ring. 180 frames."""
    frames = 180
    ring = shape_layer(
        "Ring",
        [group([ellipse(360), stroke(GOLD600, 6, _anim([(0, 55, *EASE_IN_OUT), (90, 100, *EASE_IN_OUT), (180, 55)]))], "Ring")],
        transform(position=(256, 256)), 3, frames,
    )
    halo = shape_layer(
        "Halo",
        [group([ellipse(340), halo_fill(GOLD400, 170, _anim([(0, 35, *EASE_IN_OUT), (90, 100, *EASE_IN_OUT), (180, 35)]))], "Halo")],
        transform(position=(256, 256), scale=_anim([(0, 96, *EASE_IN_OUT), (90, 112, *EASE_IN_OUT), (180, 96)], 2)),
        2, frames,
    )
    bolt = shape_layer(
        "Bolt",
        [group([bolt_path(5.6, 0, 0), fill(GOLD400), stroke(GOLD700, 5)], "Bolt")],
        transform(position=(256, 256), scale=_anim([(0, 98, *EASE_IN_OUT), (90, 104, *EASE_IN_OUT), (180, 98)], 2)),
        1, frames,
    )
    return lottie("syyn_bolt_pulse", frames, [bolt, halo, ring])


def bolt_lock() -> dict:
    """The veil dropping: a shield closes round the bolt, then settles. 90 frames (1.5 s)."""
    frames = 90
    shield = shield_outline(256, 92, 300, 350)
    n = len(shield)
    shield_shape = {
        "ty": "sh",
        "ks": _static({"c": True, "v": [list(p) for p in shield], "i": [[0, 0]] * n, "o": [[0, 0]] * n}),
        "nm": "Shield",
    }
    shield_layer = shape_layer(
        "Shield",
        [group([shield_shape, trim(_anim([(0, 0, *EASE_OUT), (40, 100)])), stroke(GOLD500, 12), fill(GOLD400, _anim([(30, 0, *EASE_OUT), (60, 14)]))], "Shield")],
        transform(position=(0, 0), anchor=(0, 0)), 2, frames,
    )
    bolt = shape_layer(
        "Bolt",
        [group([bolt_path(4.0, 0, 0), fill(GOLD400), stroke(GOLD700, 5)], "Bolt")],
        transform(
            position=(256, 262),
            scale=_anim([(24, 40, *EASE_OUT), (52, 108, *EASE_IN_OUT), (66, 100)], 2),
            opacity=_anim([(24, 0), (36, 100)]),
        ),
        1, frames,
    )
    return lottie("syyn_bolt_lock", frames, [bolt, shield_layer])


def _bezier(p0, p1, p2, p3, steps):
    out = []
    for i in range(steps + 1):
        t = i / steps
        a, b, c, d = (1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t ** 2, t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def shield_outline(cx: float, top: float, width: float, height: float) -> list[tuple[float, float]]:
    half = width / 2
    shoulder, waist, tip = top + height * 0.12, top + height * 0.50, top + height
    pts = _bezier((cx - half, shoulder), (cx - half * 0.55, shoulder - height * 0.01), (cx - half * 0.25, top + height * 0.02), (cx, top), 14)
    pts += _bezier((cx, top), (cx + half * 0.25, top + height * 0.02), (cx + half * 0.55, shoulder - height * 0.01), (cx + half, shoulder), 14)[1:]
    pts += [(cx + half, waist)]
    pts += _bezier((cx + half, waist), (cx + half, top + height * 0.76), (cx + half * 0.38, top + height * 0.92), (cx, tip), 20)[1:]
    pts += _bezier((cx, tip), (cx - half * 0.38, top + height * 0.92), (cx - half, top + height * 0.76), (cx - half, waist), 20)[1:]
    return pts


def write_bolt(directory: str) -> None:
    for name, fn in (("syyn_bolt_strike", bolt_strike), ("syyn_bolt_pulse", bolt_pulse), ("syyn_bolt_lock", bolt_lock)):
        path = os.path.join(directory, name + ".tgs")
        write_tgs(path, fn())
        print(f"wrote {name}.tgs ({os.path.getsize(path)} bytes)")


def main() -> None:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("recolor")
    r.add_argument("directory")
    r.add_argument("--list", required=True, help="text file: one .tgs path (relative to directory) per line")
    r.add_argument("--dry", action="store_true")
    b = sub.add_parser("bolt")
    b.add_argument("directory")
    args = ap.parse_args()
    if args.cmd == "recolor":
        names = [ln.strip() for ln in open(args.list, encoding="utf-8") if ln.strip()]
        recolor(args.directory, names, args.dry)
    else:
        write_bolt(args.directory)


if __name__ == "__main__":
    main()
