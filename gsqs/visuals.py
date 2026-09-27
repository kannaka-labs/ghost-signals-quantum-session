"""Images of the Heesch leader: a 15-cell polyhex wearing four complete rings of copies of itself and a
partial fifth, with three required cells of the fifth ring left bare (score 4 + 251/254 = 4.9882).

Tiles are drawn as whole shapes (each tile's cells filled edge to edge, a dark seam between tiles),
coloured by ring. The same renderer makes the cover and every keyframe of the video.
"""
from __future__ import annotations

import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

BG = (8, 13, 19)
RINGS = [(236, 226, 206), (156, 195, 207), (111, 159, 174), (75, 120, 135), (51, 88, 106), (216, 160, 72)]
BARE = (255, 84, 60)
FONTS = Path("C:/Windows/Fonts")


def load(path):
    return json.loads(Path(path).read_text())


def _hex_center(q, r, s):
    return (math.sqrt(3) * (q + r / 2) * s, 1.5 * r * s)


def _hex_poly(cx, cy, s):
    return [(cx + s * math.cos(math.radians(60 * k - 30)), cy + s * math.sin(math.radians(60 * k - 30))) for k in range(6)]


def render(data, size=(1400, 1400), max_level=5, reveal=1.0, scale=None, center=None, glow=True):
    """Draw tiles with level <= max_level (the top level only up to `reveal` of its tiles, in order)."""
    W, H = size
    cells = [c for t in data["tiles"] for c in t["cells"]] + [tuple(c) for c in data["uncovered"]]
    xs = [_hex_center(q, r, 1)[0] for q, r in cells]
    ys = [_hex_center(q, r, 1)[1] for q, r in cells]
    s = scale or 0.92 * min(W / (max(xs) - min(xs) + 2), H / (max(ys) - min(ys) + 2))
    cx0 = center[0] if center else (max(xs) + min(xs)) / 2
    cy0 = center[1] if center else (max(ys) + min(ys)) / 2
    ox, oy = W / 2 - cx0 * s, H / 2 - cy0 * s
    img = Image.new("RGB", size, BG)
    d = ImageDraw.Draw(img)
    tiles = sorted(data["tiles"], key=lambda t: t["level"])
    top = [t for t in tiles if t["level"] == max_level]
    shown = [t for t in tiles if t["level"] < max_level] + top[: int(round(len(top) * reveal))]
    for t in shown:
        col = RINGS[min(t["level"], 5)]
        for q, r in t["cells"]:
            x, y = _hex_center(q, r, s)
            d.polygon(_hex_poly(x + ox, y + oy, s * 1.02), fill=col)
        # seams: redraw each cell's outline only where its neighbour belongs to another tile
        own = {tuple(c) for c in t["cells"]}
        for q, r in t["cells"]:
            x, y = _hex_center(q, r, s)
            pts = _hex_poly(x + ox, y + oy, s)
            # edge k joins vertex k (at 60k-30 degrees) and k+1; on a pointy-top axial grid with y down,
            # those edges face E, SE, SW, W, NW, NE in turn
            for k, (dq, dr) in enumerate(((1, 0), (0, 1), (-1, 1), (-1, 0), (0, -1), (1, -1))):
                if (q + dq, r + dr) not in own:
                    d.line([pts[k], pts[(k + 1) % 6]], fill=BG, width=max(1, int(s * 0.16)))
    if max_level >= 5 and reveal >= 1.0:
        layer = Image.new("RGB", size, (0, 0, 0))
        g = ImageDraw.Draw(layer)
        for q, r in data["uncovered"]:
            x, y = _hex_center(q, r, s)
            d.polygon(_hex_poly(x + ox, y + oy, s * 0.9), fill=BARE)
            g.ellipse([x + ox - 4 * s, y + oy - 4 * s, x + ox + 4 * s, y + oy + 4 * s], fill=(160, 40, 25))
        if glow:   # additive halo around the bare cells only
            halo = layer.filter(ImageFilter.GaussianBlur(s * 2.5))
            img = Image.eval(Image.merge("RGB", [Image.eval(a, lambda v: v) for a in img.split()]), lambda v: v)
            from PIL import ImageChops
            img = ImageChops.add(img, halo)
            d = ImageDraw.Draw(img)
            for q, r in data["uncovered"]:
                x, y = _hex_center(q, r, s)
                d.polygon(_hex_poly(x + ox, y + oy, s * 0.9), fill=BARE)
    return img


def frame(data, size):
    """(scale, centre) that fit the whole corona, so partial renders line up with the full one."""
    W, H = size
    cells = [c for t in data["tiles"] for c in t["cells"]] + [tuple(c) for c in data["uncovered"]]
    xs = [_hex_center(q, r, 1)[0] for q, r in cells]
    ys = [_hex_center(q, r, 1)[1] for q, r in cells]
    s = 0.92 * min(W / (max(xs) - min(xs) + 2), H / (max(ys) - min(ys) + 2))
    return s, ((max(xs) + min(xs)) / 2, (max(ys) + min(ys)) / 2)


def mask_outer(data, size, min_level=3):
    """White where the rings at or beyond `min_level` are: the unsettled frontier the quantum blur touches."""
    s, c = frame(data, size)
    sub = dict(data, tiles=[t for t in data["tiles"] if t["level"] >= min_level])
    ring = render(sub, size, scale=s, center=c, glow=False).convert("L")
    return ring.point(lambda v: 255 if v > 30 else 0).filter(ImageFilter.GaussianBlur(3))

def font(name="segoeuib.ttf", px=64):
    return ImageFont.truetype(str(FONTS / name), px)
