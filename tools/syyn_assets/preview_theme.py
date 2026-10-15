"""Render a mock of the client from a theme's colours, for a quick look without launching the app.

    python tools/syyn_assets/preview_theme.py <colors.tdesktop-theme> <tile.png> <out.png>

The mock follows the SyynGram client kit layout (folder rail, chat list, conversation, composer).
It reads the real palette values, so what it shows is what the theme sets, not a separate design.
"""
from __future__ import annotations

import os
import re
import sys

from PIL import Image, ImageDraw, ImageFont

LINE = re.compile(r"^\s*([A-Za-z0-9_]+):\s*([^;]+);")


def load(path: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in open(path, encoding="utf-8").read().splitlines():
        m = LINE.match(raw)
        if m:
            values[m.group(1)] = m.group(2).strip()
    return values


def color(values: dict[str, str], key: str, depth: int = 0) -> tuple[int, int, int, int]:
    v = values.get(key, "#ff00ff")
    if v in values and depth < 12:
        return color(values, v, depth + 1)
    v = v.lstrip("#")
    return int(v[0:2], 16), int(v[2:4], 16), int(v[4:6], 16), int(v[6:8], 16) if len(v) == 8 else 255


def font(size: int, bold: bool = False) -> ImageFont.FreeTypeFont:
    for name in ("segoeuib.ttf" if bold else "segoeui.ttf", "arialbd.ttf" if bold else "arial.ttf"):
        for base in ("C:/Windows/Fonts", "/usr/share/fonts/truetype/dejavu"):
            path = os.path.join(base, name)
            if os.path.exists(path):
                return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def render(colors_path: str, tile_path: str, out_path: str) -> None:
    c = load(colors_path)

    def col(key: str) -> tuple[int, int, int, int]:
        return color(c, key)

    W, H = 1000, 620
    img = Image.new("RGBA", (W, H), col("windowBg"))
    d = ImageDraw.Draw(img, "RGBA")

    rail_w, list_w = 76, 300
    d.rectangle((0, 0, rail_w, H), fill=col("sideBarBg"))
    for i, label in enumerate(["All", "Personal", "Groups", "Bots"]):
        y = 30 + i * 62
        active = i == 0
        if active:
            d.rounded_rectangle((8, y - 6, rail_w - 8, y + 48), 8, fill=col("sideBarBgActive"))
        fg = col("sideBarTextFgActive") if active else col("sideBarTextFg")
        d.ellipse((rail_w / 2 - 9, y, rail_w / 2 + 9, y + 18), outline=fg, width=2)
        t = font(10)
        d.text((rail_w / 2 - d.textlength(label, font=t) / 2, y + 26), label, font=t, fill=fg)
        if i == 0:
            d.rounded_rectangle((rail_w - 30, y - 4, rail_w - 12, y + 10), 7, fill=col("sideBarBadgeBg"))
            d.text((rail_w - 24, y - 3), "5", font=font(10, True), fill=col("sideBarBadgeFg"))

    lx = rail_w
    d.rectangle((lx, 0, lx + list_w, H), fill=col("dialogsBg"))
    d.text((lx + 16, 18), "SYYNGRAM", font=font(15, True), fill=col("dialogsNameFg"))
    d.rounded_rectangle((lx + 12, 52, lx + list_w - 12, 84), 8, fill=col("filterInputInactiveBg"))
    d.text((lx + 24, 60), "Search", font=font(13), fill=col("placeholderFg"))
    rows = [
        ("Maren Voss", "Sent you the diff, check the lock screen", "10:42", 2, "normal"),
        ("Field Ops", "Ghost mode is on for everyone", "09:18", 0, "active"),
        ("Tomas K.", "Voice message (0:23)", "Mon", 4, "muted"),
        ("Syyn Updates", "v0.2: duress timer, quick lock", "Sun", 0, "normal"),
    ]
    for i, (name, text, time, unread, state) in enumerate(rows):
        y = 100 + i * 66
        active = state == "active"
        if active:
            d.rectangle((lx, y, lx + list_w, y + 62), fill=col("dialogsBgActive"))
        d.ellipse((lx + 14, y + 11, lx + 54, y + 51), fill=col("historyPeer%dUserpicBg" % (i + 1)))
        d.text((lx + 24, y + 20), name[0], font=font(16, True), fill=col("historyPeerUserpicFg"))
        d.text((lx + 66, y + 10), name, font=font(14, True),
               fill=col("dialogsNameFgActive") if active else col("dialogsNameFg"))
        tf = font(11)
        d.text((lx + list_w - 14 - d.textlength(time, font=tf), y + 12), time, font=tf,
               fill=col("dialogsDateFgActive") if active else col("dialogsDateFg"))
        d.text((lx + 66, y + 34), text[:30], font=font(12),
               fill=col("dialogsTextFgActive") if active else col("dialogsTextFg"))
        if unread:
            bg = col("dialogsUnreadBgMuted") if state == "muted" else col("dialogsUnreadBg")
            d.rounded_rectangle((lx + list_w - 38, y + 34, lx + list_w - 14, y + 52), 9, fill=bg)
            d.text((lx + list_w - 29, y + 35), str(unread), font=font(11, True), fill=col("dialogsUnreadFg"))

    cx = lx + list_w
    tile = Image.open(tile_path).convert("RGBA")
    for yy in range(0, H, tile.height):
        for xx in range(cx, W, tile.width):
            img.alpha_composite(tile, (xx, yy))
    d = ImageDraw.Draw(img, "RGBA")
    d.rectangle((cx, 0, W, 54), fill=col("windowBg"))
    d.line((cx, 54, W, 54), fill=col("filterInputBorderFg"))
    d.text((cx + 18, 8), "Field Ops", font=font(15, True), fill=col("windowBoldFg"))
    d.text((cx + 18, 30), "online", font=font(11), fill=col("windowActiveTextFg"))

    def bubble(x: int, y: int, w: int, lines: list[str], out: bool, extra=None) -> int:
        h = 18 * len(lines) + 30
        bg = col("msgOutBg") if out else col("msgInBg")
        bx = x if not out else x - w
        d.rounded_rectangle((bx, y, bx + w, y + h), 14, fill=bg)
        ty = y + 8
        if extra:
            d.text((bx + 12, ty), extra, font=font(12, True),
                   fill=col("msgOutServiceFg") if out else col("msgInServiceFg"))
            ty += 18
            h += 18
            d.rounded_rectangle((bx, y, bx + w, y + h), 14, fill=bg)
            d.text((bx + 12, y + 8), extra, font=font(12, True),
                   fill=col("msgOutServiceFg") if out else col("msgInServiceFg"))
        for ln in lines:
            d.text((bx + 12, ty), ln, font=font(14),
                   fill=col("historyTextOutFg") if out else col("historyTextInFg"))
            ty += 18
        meta = "10:42" + (" ✓✓" if out else "")
        mf = font(11)
        d.text((bx + w - 12 - d.textlength(meta, font=mf), y + h - 19), meta, font=mf,
               fill=col("msgOutDateFg") if out else col("msgInDateFg"))
        return h

    pill = "Today"
    pf = font(12)
    pw = int(d.textlength(pill, font=pf)) + 24
    d.rounded_rectangle((cx + (W - cx - pw) / 2, 74, cx + (W - cx + pw) / 2, 98), 12, fill=col("msgServiceBg"))
    d.text((cx + (W - cx - pw) / 2 + 12, 78), pill, font=pf, fill=col("msgServiceFg"))
    y = 116
    y += bubble(cx + 22, y, 360, ["Sent you the diff. Can you check", "the lock screen before I merge?"], False, "Maren") + 10
    y += bubble(W - 24, y, 330, ["On it. The veil looks clean,", "ember rings and all."], True) + 10
    y += bubble(cx + 22, y, 280, ["https://syyn.ca/notes"], False) + 10
    d.text((cx + 34, y - 36), "https://syyn.ca/notes", font=font(14), fill=col("historyLinkInFg"))
    y += bubble(W - 24, y, 250, ["Shipping tonight."], True) + 10
    d.rectangle((cx, H - 58, W, H), fill=col("historyComposeAreaBg"))
    d.text((cx + 20, H - 40), "Write a message", font=font(14), fill=col("placeholderFg"))
    d.ellipse((W - 52, H - 46, W - 20, H - 14), fill=col("windowBgActive"))
    d.text((W - 42, H - 42), "➤", font=font(16), fill=col("windowFgActive"))
    img.convert("RGB").save(out_path)


if __name__ == "__main__":
    render(sys.argv[1], sys.argv[2], sys.argv[3])
