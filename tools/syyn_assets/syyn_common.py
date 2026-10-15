"""Shared palette and drawing helpers for the Syyngram asset generators.

The palette and the bolt come from the SyynGram client kit (tailwind.config.js
and src/components/brand/Bolt.tsx), so the app, the icons and the website agree.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

NIGHT = {
    950: "#050403",
    900: "#0B0907",
    850: "#100D09",
    800: "#15110C",
    700: "#1D1811",
    600: "#2A2318",
    500: "#3A3022",
}
SAND = {
    50: "#F3ECDD",
    100: "#E6DCC6",
    300: "#B8A988",
    400: "#9A8B70",
    500: "#6C604C",
}
GOLD = {
    200: "#F7E6B5",
    300: "#F1D589",
    400: "#E2B85A",
    500: "#C9A24A",
    600: "#A9842F",
    700: "#7D6122",
}
BOLT = "#FFF6DD"

# The brand bolt, in the kit's 24 x 56 box.
BOLT_POINTS = [
    (15.5, 1.0),
    (4.0, 31.0),
    (11.6, 29.4),
    (7.0, 55.0),
    (20.5, 21.0),
    (12.9, 22.8),
    (18.6, 1.0),
]
BOLT_BOX = (4.0, 1.0, 20.5, 55.0)


def rgb(value: str, alpha: int = 255) -> tuple[int, int, int, int]:
    value = value.lstrip("#")
    return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16), alpha


def bolt_polygon(cx: float, cy: float, height: float) -> list[tuple[float, float]]:
    """Bolt points scaled to `height` pixels tall and centred on (cx, cy)."""
    x0, y0, x1, y1 = BOLT_BOX
    scale = height / (y1 - y0)
    mx = (x0 + x1) / 2
    my = (y0 + y1) / 2
    return [(cx + (x - mx) * scale, cy + (y - my) * scale) for x, y in BOLT_POINTS]


def layer(size: int) -> Image.Image:
    return Image.new("RGBA", (size, size), (0, 0, 0, 0))


def disk_mask(size: int, radius: float, center: tuple[float, float] | None = None) -> Image.Image:
    cx, cy = center or (size / 2, size / 2)
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).ellipse((cx - radius, cy - radius, cx + radius, cy + radius), fill=255)
    return mask


def _stops_to_lookup(stops: list[tuple[float, tuple[int, int, int, int]]], steps: int = 1024) -> np.ndarray:
    positions = np.array([p for p, _ in stops], dtype=np.float64)
    colors = np.array([c for _, c in stops], dtype=np.float64)
    table = np.zeros((steps, 4), dtype=np.float64)
    ts = np.linspace(0.0, 1.0, steps)
    for channel in range(4):
        table[:, channel] = np.interp(ts, positions, colors[:, channel])
    return table


def radial_gradient(
    size: int,
    stops: list[tuple[float, tuple[int, int, int, int]]],
    radius: float,
    center: tuple[float, float] | None = None,
) -> Image.Image:
    cx, cy = center or (size / 2, size / 2)
    ys, xs = np.mgrid[0:size, 0:size]
    t = np.clip(np.hypot(xs + 0.5 - cx, ys + 0.5 - cy) / radius, 0.0, 1.0)
    table = _stops_to_lookup(stops)
    idx = np.minimum((t * (len(table) - 1)).astype(np.int64), len(table) - 1)
    out = table[idx].astype(np.uint8)
    return Image.fromarray(out, "RGBA")


def linear_gradient(
    size: int,
    stops: list[tuple[float, tuple[int, int, int, int]]],
    angle_deg: float,
) -> Image.Image:
    ys, xs = np.mgrid[0:size, 0:size]
    a = math.radians(angle_deg)
    dx, dy = math.cos(a), math.sin(a)
    proj = (xs + 0.5 - size / 2) * dx + (ys + 0.5 - size / 2) * dy
    half = (abs(dx) + abs(dy)) * size / 2
    t = np.clip((proj / half + 1) / 2, 0.0, 1.0)
    table = _stops_to_lookup(stops)
    idx = np.minimum((t * (len(table) - 1)).astype(np.int64), len(table) - 1)
    return Image.fromarray(table[idx].astype(np.uint8), "RGBA")


def paste_masked(base: Image.Image, top: Image.Image, mask: Image.Image | None = None) -> None:
    if mask is not None:
        alpha = ImageChops.multiply(top.getchannel("A"), mask)
        top = top.copy()
        top.putalpha(alpha)
    base.alpha_composite(top)


def solid(size: int, color: tuple[int, int, int, int]) -> Image.Image:
    return Image.new("RGBA", (size, size), color)


def polygon_mask(size: int, points: list[tuple[float, float]]) -> Image.Image:
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).polygon(points, fill=255)
    return mask


def stroke_mask(size: int, points: list[tuple[float, float]], width: float, closed: bool = True) -> Image.Image:
    """A stroke centred on the path, with round joins."""
    mask = Image.new("L", (size, size), 0)
    draw = ImageDraw.Draw(mask)
    path = list(points) + ([points[0]] if closed else [])
    for a, b in zip(path, path[1:]):
        draw.line([a, b], fill=255, width=max(1, round(width)))
    r = width / 2
    for x, y in points:
        draw.ellipse((x - r, y - r, x + r, y + r), fill=255)
    return mask


def glow(mask: Image.Image, color: tuple[int, int, int, int], radius: float, strength: float = 1.0) -> Image.Image:
    blurred = mask.filter(ImageFilter.GaussianBlur(radius))
    if strength != 1.0:
        blurred = blurred.point(lambda v: min(255, int(v * strength)))
    out = Image.new("RGBA", mask.size, color)
    out.putalpha(ImageChops.multiply(blurred, Image.new("L", mask.size, color[3])))
    return out


def downscale(image: Image.Image, size: int) -> Image.Image:
    if image.width == size:
        return image
    return image.resize((size, size), Image.LANCZOS)


def write_ico(path: str, frames: dict[int, Image.Image]) -> None:
    """Write a PNG-compressed .ico with one separately drawn frame per size."""
    import io
    import struct

    sizes = sorted(frames)
    blobs = []
    for size in sizes:
        buffer = io.BytesIO()
        frames[size].convert("RGBA").save(buffer, format="PNG", optimize=True)
        blobs.append(buffer.getvalue())
    header = struct.pack("<HHH", 0, 1, len(sizes))
    offset = 6 + 16 * len(sizes)
    entries = b""
    for size, blob in zip(sizes, blobs):
        dim = 0 if size >= 256 else size
        entries += struct.pack("<BBBBHHII", dim, dim, 0, 0, 1, 32, len(blob), offset)
        offset += len(blob)
    with open(path, "wb") as handle:
        handle.write(header + entries + b"".join(blobs))


@dataclass(frozen=True)
class Paths:
    resources: str
    github: str
