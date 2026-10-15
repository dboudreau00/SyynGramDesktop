"""Draw the Syyngram app icon family and write it into Telegram/Resources.

Usage (from the repository root):
    python tools/syyn_assets/make_icons.py            # write the assets
    python tools/syyn_assets/make_icons.py --sheet out.png   # preview sheet only

Every icon is drawn per size, not scaled from one master: thin details drop out
and the bolt thickens below 64 px so it stays readable in the taskbar and tray.
"""
from __future__ import annotations

import argparse
import math
import os
import sys

from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from syyn_common import (  # noqa: E402
    BOLT,
    GOLD,
    NIGHT,
    SAND,
    bolt_polygon,
    disk_mask,
    downscale,
    glow,
    layer,
    linear_gradient,
    paste_masked,
    polygon_mask,
    radial_gradient,
    rgb,
    solid,
    stroke_mask,
    write_ico,
)

# id (stored in settings and used for the qrc paths), title, short description
ICONS = [
    ("default", "Ember", "Cream bolt on night, gold ring"),
    ("vellum", "Vellum", "Dark bolt on parchment"),
    ("gilt", "Gilt", "Solid gold, dark bolt"),
    ("obsidian", "Obsidian", "Outline bolt on black"),
    ("signal", "Signal", "Bolt with broadcast rings"),
    ("ward", "Ward", "Bolt inside a shield"),
    ("circuit", "Circuit", "Bolt over a faint lattice"),
    ("eclipse", "Eclipse", "Dark bolt over a gold sun"),
]

SIZES_ICO = [16, 24, 32, 48, 64, 128, 256]


def work_size(px: int) -> int:
    if px <= 64:
        return px * 8
    if px <= 256:
        return px * 4
    return px * 2


def bolt_layer(
    S: int,
    cx: float,
    cy: float,
    height: float,
    fill: str,
    stroke: str | None = None,
    stroke_w: float = 0.0,
    halo: str | None = None,
    halo_r: float = 0.0,
    halo_strength: float = 1.0,
    halo_alpha: int = 200,
) -> Image.Image:
    pts = bolt_polygon(cx, cy, height)
    body = polygon_mask(S, pts)
    out = layer(S)
    union = body
    if stroke and stroke_w:
        outline = stroke_mask(S, pts, stroke_w)
        union = Image.composite(outline, body, outline)
    if halo and halo_r:
        out.alpha_composite(glow(union, rgb(halo, halo_alpha), halo_r, halo_strength))
    if stroke and stroke_w:
        paste_masked(out, solid(S, rgb(stroke)), outline)
    paste_masked(out, solid(S, rgb(fill)), body)
    return out


def bolt_outline_only(
    S: int,
    cx: float,
    cy: float,
    height: float,
    color: str,
    width: float,
    halo: str | None,
    halo_r: float,
) -> Image.Image:
    pts = bolt_polygon(cx, cy, height)
    ring = stroke_mask(S, pts, width)
    out = layer(S)
    if halo:
        out.alpha_composite(glow(ring, rgb(halo, 170), halo_r, 1.0))
    paste_masked(out, solid(S, rgb(color)), ring)
    return out


def ring_layer(S: int, radius: float, width: float, color: tuple[int, int, int, int]) -> Image.Image:
    out = layer(S)
    ImageDraw.Draw(out).ellipse(
        (S / 2 - radius, S / 2 - radius, S / 2 + radius, S / 2 + radius),
        outline=color,
        width=max(1, round(width)),
    )
    return out


def finish(base: Image.Image, S: int) -> Image.Image:
    """Clip to the full-bleed disk."""
    mask = disk_mask(S, S / 2)
    out = layer(S)
    paste_masked(out, base, mask)
    return out


def draw_default(S: int, px: int) -> Image.Image:
    u = S / 1024
    small = px < 64
    bg = radial_gradient(
        S,
        [(0.0, rgb("#1A140C")), (0.65, rgb(NIGHT[900])), (1.0, rgb(NIGHT[950]))],
        S * 0.62,
        (S * 0.5, S * 0.46),
    )
    base = bg.copy()
    rw = (52 if small else 22) * u
    base.alpha_composite(ring_layer(S, S / 2 - rw / 2 - 2 * u, rw, rgb(GOLD[400])))
    if not small:
        base.alpha_composite(ring_layer(S, S / 2 - 66 * u, 3 * u, rgb(NIGHT[500])))
    h = (0.74 if small else 0.60) * S
    base.alpha_composite(
        bolt_layer(
            S, S * 0.5, S * 0.5, h,
            fill=BOLT,
            stroke=GOLD[400],
            stroke_w=(30 if small else 16) * u,
            halo=GOLD[400],
            halo_r=(14 if small else 34) * u,
            halo_alpha=(150 if small else 220),
        )
    )
    return finish(base, S)


def draw_vellum(S: int, px: int) -> Image.Image:
    u = S / 1024
    small = px < 64
    bg = radial_gradient(
        S,
        [(0.0, rgb("#FBF6EA")), (0.7, rgb(SAND[50])), (1.0, rgb(SAND[100]))],
        S * 0.62,
        (S * 0.5, S * 0.44),
    )
    base = bg.copy()
    rw = (52 if small else 22) * u
    base.alpha_composite(ring_layer(S, S / 2 - rw / 2 - 2 * u, rw, rgb(GOLD[600])))
    if not small:
        base.alpha_composite(ring_layer(S, S / 2 - 66 * u, 3 * u, rgb(GOLD[300])))
    h = (0.74 if small else 0.60) * S
    base.alpha_composite(
        bolt_layer(
            S, S * 0.5, S * 0.5, h,
            fill=NIGHT[900],
            stroke=GOLD[500],
            stroke_w=(22 if small else 12) * u,
            halo=GOLD[500],
            halo_r=(10 if small else 26) * u,
            halo_strength=0.7,
            halo_alpha=120,
        )
    )
    return finish(base, S)


def draw_gilt(S: int, px: int) -> Image.Image:
    u = S / 1024
    small = px < 64
    bg = linear_gradient(
        S,
        [(0.0, rgb(GOLD[200])), (0.38, rgb(GOLD[400])), (0.75, rgb(GOLD[500])), (1.0, rgb(GOLD[700]))],
        62,
    )
    base = bg.copy()
    base.alpha_composite(ring_layer(S, S / 2 - 10 * u, (36 if small else 16) * u, rgb(GOLD[700], 200)))
    h = (0.74 if small else 0.60) * S
    shadow = bolt_layer(S, S * 0.5 + 10 * u, S * 0.5 + 14 * u, h, fill="#7D6122")
    shadow.putalpha(shadow.getchannel("A").point(lambda v: int(v * 0.45)))
    if not small:
        base.alpha_composite(shadow)
    base.alpha_composite(
        bolt_layer(
            S, S * 0.5, S * 0.5, h,
            fill=NIGHT[900],
            stroke=GOLD[200],
            stroke_w=(14 if small else 8) * u,
        )
    )
    return finish(base, S)


def draw_obsidian(S: int, px: int) -> Image.Image:
    u = S / 1024
    small = px < 64
    base = solid(S, rgb(NIGHT[950]))
    base.alpha_composite(ring_layer(S, S / 2 - 12 * u, (40 if small else 12) * u, rgb(NIGHT[500])))
    h = (0.74 if small else 0.62) * S
    base.alpha_composite(
        bolt_outline_only(
            S, S * 0.5, S * 0.5, h,
            color=GOLD[400],
            width=(46 if small else 20) * u,
            halo=GOLD[400],
            halo_r=(12 if small else 30) * u,
        )
    )
    return finish(base, S)


def draw_signal(S: int, px: int) -> Image.Image:
    u = S / 1024
    small = px < 64
    base = radial_gradient(
        S,
        [(0.0, rgb("#16110A")), (1.0, rgb(NIGHT[900]))],
        S * 0.7,
    )
    rings = [(300, 0.60), (400, 0.38), (490, 0.20)] if not small else [(360, 0.55), (470, 0.30)]
    for radius, alpha in rings:
        base.alpha_composite(
            ring_layer(S, radius * u, (16 if not small else 40) * u, rgb(GOLD[400], int(255 * alpha)))
        )
    h = (0.50 if not small else 0.68) * S
    base.alpha_composite(
        bolt_layer(
            S, S * 0.5, S * 0.5, h,
            fill=BOLT,
            stroke=GOLD[400],
            stroke_w=(26 if small else 14) * u,
            halo=GOLD[400],
            halo_r=(12 if small else 28) * u,
            halo_alpha=(150 if small else 210),
        )
    )
    return finish(base, S)


def _bezier(p0, p1, p2, p3, steps=48):
    out = []
    for i in range(steps + 1):
        t = i / steps
        a = (1 - t) ** 3
        b = 3 * (1 - t) ** 2 * t
        c = 3 * (1 - t) * t ** 2
        d = t ** 3
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0], a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def shield_points(S: int, cx: float, top: float, width: float, height: float) -> list[tuple[float, float]]:
    """A heater shield: a gently peaked top, straight shoulders, a curved base meeting at a point."""
    half = width / 2
    shoulder = top + height * 0.12
    waist = top + height * 0.50
    tip = top + height
    left_top = (cx - half, shoulder)
    right_top = (cx + half, shoulder)
    peak = (cx, top)
    loop = []
    loop += _bezier(left_top, (cx - half * 0.55, shoulder - height * 0.01), (cx - half * 0.25, top + height * 0.02), peak, 24)
    loop += _bezier(peak, (cx + half * 0.25, top + height * 0.02), (cx + half * 0.55, shoulder - height * 0.01), right_top, 24)[1:]
    loop += [(cx + half, waist)]
    loop += _bezier((cx + half, waist), (cx + half, top + height * 0.76), (cx + half * 0.38, top + height * 0.92), (cx, tip), 48)[1:]
    loop += _bezier((cx, tip), (cx - half * 0.38, top + height * 0.92), (cx - half, top + height * 0.76), (cx - half, waist), 48)[1:]
    return loop


def draw_ward(S: int, px: int) -> Image.Image:
    u = S / 1024
    small = px < 64
    base = solid(S, rgb(NIGHT[900]))
    loop = shield_points(S, S * 0.5, S * 0.15, S * 0.56, S * 0.72)
    body = polygon_mask(S, loop)
    edge = stroke_mask(S, loop, (44 if small else 20) * u)
    face = radial_gradient(
        S,
        [(0.0, rgb(NIGHT[600])), (1.0, rgb(NIGHT[700]))],
        S * 0.45,
        (S * 0.5, S * 0.42),
    )
    glow_layer = glow(edge, rgb(GOLD[400], 150), 26 * u, 1.0)
    base.alpha_composite(glow_layer)
    paste_masked(base, solid(S, rgb(GOLD[400])), edge)
    paste_masked(base, face, body)
    h = (0.46 if small else 0.40) * S
    base.alpha_composite(
        bolt_layer(
            S, S * 0.5, S * 0.47, h,
            fill=BOLT,
            stroke=GOLD[400],
            stroke_w=(22 if small else 12) * u,
            halo=GOLD[400],
            halo_r=(10 if small else 22) * u,
            halo_alpha=(140 if small else 200),
        )
    )
    return finish(base, S)


def hex_lattice(S: int, cell: float, color: tuple[int, int, int, int], width: float) -> Image.Image:
    out = layer(S)
    draw = ImageDraw.Draw(out)
    dx = cell * math.sqrt(3)
    dy = cell * 1.5
    rows = int(S / dy) + 3
    cols = int(S / dx) + 3
    for r in range(-1, rows):
        for c in range(-1, cols):
            cx = c * dx + (dx / 2 if r % 2 else 0)
            cy = r * dy
            pts = [
                (cx + cell * math.cos(math.radians(60 * k - 30)), cy + cell * math.sin(math.radians(60 * k - 30)))
                for k in range(6)
            ]
            draw.line(pts + [pts[0]], fill=color, width=max(1, round(width)))
    return out


def draw_circuit(S: int, px: int) -> Image.Image:
    u = S / 1024
    small = px < 64
    base = solid(S, rgb(NIGHT[900]))
    if not small:
        lattice = hex_lattice(S, 74 * u, rgb(NIGHT[600]), 3 * u)
        fade = radial_gradient(
            S,
            [(0.0, rgb("#000000", 0)), (0.45, rgb("#000000", 0)), (0.62, rgb("#000000", 255)), (1.0, rgb("#000000", 255))],
            S * 0.5,
        )
        mask = fade.getchannel("A")
        paste_masked(base, lattice, mask)
        # a few node dots on the lattice edge
        draw = ImageDraw.Draw(base)
        for k in range(12):
            a = math.radians(30 * k + 15)
            rr = S * 0.40
            x = S / 2 + rr * math.cos(a)
            y = S / 2 + rr * math.sin(a)
            r = 9 * u
            draw.ellipse((x - r, y - r, x + r, y + r), fill=rgb(GOLD[600]))
    base.alpha_composite(ring_layer(S, S / 2 - 12 * u, (44 if small else 14) * u, rgb(GOLD[500])))
    h = (0.72 if small else 0.58) * S
    base.alpha_composite(
        bolt_layer(
            S, S * 0.5, S * 0.5, h,
            fill=BOLT,
            stroke=GOLD[400],
            stroke_w=(28 if small else 14) * u,
            halo=GOLD[400],
            halo_r=(12 if small else 30) * u,
            halo_alpha=(150 if small else 220),
        )
    )
    return finish(base, S)


def draw_eclipse(S: int, px: int) -> Image.Image:
    u = S / 1024
    small = px < 64
    base = solid(S, rgb(NIGHT[950]))
    sun_r = (0.34 if not small else 0.38) * S
    sun = radial_gradient(
        S,
        [(0.0, rgb(GOLD[200])), (0.55, rgb(GOLD[400])), (1.0, rgb(GOLD[600]))],
        sun_r,
    )
    base.alpha_composite(glow(disk_mask(S, sun_r), rgb(GOLD[400], 190), 60 * u, 1.0))
    paste_masked(base, sun, disk_mask(S, sun_r))
    h = (0.70 if small else 0.62) * S
    base.alpha_composite(
        bolt_layer(
            S, S * 0.5, S * 0.5, h,
            fill=NIGHT[950],
            stroke=BOLT,
            stroke_w=(22 if small else 10) * u,
        )
    )
    return finish(base, S)


DRAW = {
    "default": draw_default,
    "vellum": draw_vellum,
    "gilt": draw_gilt,
    "obsidian": draw_obsidian,
    "signal": draw_signal,
    "ward": draw_ward,
    "circuit": draw_circuit,
    "eclipse": draw_eclipse,
}


def render(icon_id: str, px: int) -> Image.Image:
    S = work_size(px)
    return downscale(DRAW[icon_id](S, px), px)


def save_png(image: Image.Image, path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image.save(path, format="PNG", optimize=True)


def write_family(root: str) -> None:
    art = os.path.join(root, "Telegram", "Resources", "art")
    # The in-app icon packs: a 512 px PNG (used by the picker, the window and
    # the intro logo) and a multi-size .ico for the taskbar and the shortcut.
    for icon_id, _, _ in ICONS:
        folder = os.path.join(art, "ayu", icon_id)
        save_png(render(icon_id, 512), os.path.join(folder, "app.png"))
        write_ico(os.path.join(folder, "app_icon.ico"), {s: render(icon_id, s) for s in SIZES_ICO})

    # The default mark on every other place the app and installer use it.
    for size in (16, 32, 48, 64, 128, 256, 512):
        save_png(render("default", size), os.path.join(art, f"icon{size}.png"))
        save_png(render("default", size * 2), os.path.join(art, f"icon{size}@2x.png"))
    write_ico(os.path.join(art, "icon256.ico"), {s: render("default", s) for s in SIZES_ICO})
    save_png(render("default", 256), os.path.join(art, "icon_green.png"))
    save_png(render("default", 512), os.path.join(art, "iconbig_green.png"))
    save_png(render("default", 256), os.path.join(art, "logo_256.png"))
    save_png(render("default", 256), os.path.join(art, "logo_256_no_margin.png"))
    save_png(render("default", 1024), os.path.join(art, "icon_round512@2x.png"))
    save_png(render("default", 512), os.path.join(root, ".github", "AyuGram.png"))
    write_intro_mark(root)


def write_intro_mark(root: str) -> None:
    """The bolt in the middle of the login QR code, as a style mask the app recolours."""
    icons = os.path.join(root, "Telegram", "Resources", "icons")
    for scale, name in ((1, "intro_qr_plane"), (2, "intro_qr_plane@2x"), (3, "intro_qr_plane@3x")):
        px = 35 * scale
        S = px * 8
        pts = bolt_polygon(S / 2, S / 2, S * 0.84)
        mask = polygon_mask(S, pts)
        edge = stroke_mask(S, pts, S * 0.035)
        union = Image.composite(edge, mask, edge)
        # Style icons are opaque grayscale masks: white is the shape, black is nothing.
        small = union.resize((px, px), Image.LANCZOS)
        out = Image.merge("RGBA", (small, small, small, Image.new("L", (px, px), 255)))
        save_png(out, os.path.join(icons, name + ".png"))


def sheet(path: str) -> None:
    cell = 256
    pad = 24
    cols = 4
    rows = math.ceil(len(ICONS) / cols)
    small_sizes = (64, 32, 16)
    w = cols * (cell + pad) + pad
    h = rows * (cell + 130 + pad) + pad
    canvas = Image.new("RGBA", (w, h), rgb("#15110C"))
    draw = ImageDraw.Draw(canvas)
    for i, (icon_id, title, _) in enumerate(ICONS):
        r, c = divmod(i, cols)
        x = pad + c * (cell + pad)
        y = pad + r * (cell + 130 + pad)
        canvas.alpha_composite(render(icon_id, cell), (x, y))
        draw.text((x, y + cell + 6), f"{title} ({icon_id})", fill=rgb(SAND[50]))
        sx = x
        for s in small_sizes:
            # show each small size at 3x nearest so the pixels are visible
            im = render(icon_id, s)
            im3 = im.resize((s * 2, s * 2), Image.NEAREST) if s < 64 else im
            canvas.alpha_composite(im3, (sx, y + cell + 26))
            sx += im3.width + 10
    save_png(canvas, path)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", default=os.getcwd())
    parser.add_argument("--sheet", help="write only a preview sheet to this path")
    args = parser.parse_args()
    if args.sheet:
        sheet(args.sheet)
        return
    write_family(args.root)
    print("icon family written under", args.root)


if __name__ == "__main__":
    main()
