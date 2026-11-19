#!/usr/bin/env python3
"""News front page for Thursday 19 November 2026.

Draws a 1024x1024 newspaper-style infographic (six stories) with only the
Python standard library. Text is rendered from a fixed-grid bitmap font
atlas (atlas.png, shipped beside this file) that is decoded with zlib;
all shapes are drawn with small raster helpers written here, and the
final image is encoded as PNG by hand. No network, no randomness, no
time or environment dependence: every run writes identical bytes.

Run:  MAKEFUN_OUTPUT_DIR=out python3 main.py   (default output: /output)
"""

import binascii
import os
import struct
import zlib

W = 1024
H = 1024

# ---------------------------------------------------------------- palette
PAPER = (245, 239, 227)
CARD = (255, 255, 255)
INK = (25, 25, 25)
BODY = (56, 56, 56)
RED = (180, 35, 24)
NAVY = (27, 58, 92)
STEEL = (70, 110, 150)
GOLD = (217, 164, 65)
GREEN = (46, 125, 50)
BLUE = (37, 99, 235)
SKY = (147, 197, 253)
GRAY = (110, 110, 110)
LIGHTGRAY = (200, 200, 200)

BAND_TINTS = [
    (234, 240, 247),   # 1 summit: pale steel blue
    (253, 238, 232),   # 2 middle east: pale red
    (238, 238, 240),   # 3 bridge: pale slate
    (247, 240, 224),   # 4 gaza: pale sand
    (232, 244, 233),   # 5 markets: pale green
    (16, 32, 56),      # 6 space: dark navy
]

# ---------------------------------------------------------------- canvas
canvas = bytearray(W * H * 3)


def _set(x, y, c):
    if 0 <= x < W and 0 <= y < H:
        i = (y * W + x) * 3
        canvas[i] = c[0]
        canvas[i + 1] = c[1]
        canvas[i + 2] = c[2]


def fill_rect(x, y, w, h, c):
    x0 = max(0, x)
    y0 = max(0, y)
    x1 = min(W, x + w)
    y1 = min(H, y + h)
    for yy in range(y0, y1):
        base = (yy * W + x0) * 3
        for xx in range(x0, x1):
            i = base + (xx - x0) * 3
            canvas[i] = c[0]
            canvas[i + 1] = c[1]
            canvas[i + 2] = c[2]


def hline(x0, x1, y, c):
    if x0 > x1:
        x0, x1 = x1, x0
    for x in range(max(0, x0), min(W, x1 + 1)):
        _set(x, y, c)


def vline(x, y0, y1, c):
    if y0 > y1:
        y0, y1 = y1, y0
    for y in range(max(0, y0), min(H, y1 + 1)):
        _set(x, y, c)


def line(x0, y0, x1, y1, c):
    dx = abs(x1 - x0)
    dy = -abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx + dy
    while True:
        _set(x0, y0, c)
        if x0 == x1 and y0 == y1:
            break
        e2 = 2 * err
        if e2 >= dy:
            err += dy
            x0 += sx
        if e2 <= dx:
            err += dx
            y0 += sy


def dashed_line(x0, y0, x1, y1, c, dash=7, gap=5):
    import math
    dist = math.hypot(x1 - x0, y1 - y0)
    if dist == 0:
        return
    ux = (x1 - x0) / dist
    uy = (y1 - y0) / dist
    d = 0.0
    while d < dist:
        e = min(d + dash, dist)
        line(int(x0 + ux * d), int(y0 + uy * d),
             int(x0 + ux * e), int(y0 + uy * e), c)
        d = e + gap


def circle(cx, cy, r, c):
    for dy in range(-r, r + 1):
        dx = int((r * r - dy * dy) ** 0.5)
        hline(cx - dx, cx + dx, cy + dy, c)


def ring(cx, cy, r, t, c, bg):
    circle(cx, cy, r, c)
    if r - t > 0:
        circle(cx, cy, r - t, bg)


def ellipse(cx, cy, rx, ry, c):
    for dy in range(-ry, ry + 1):
        f = 1.0 - (dy * dy) / float(ry * ry)
        dx = int(rx * (f ** 0.5)) if f > 0 else 0
        hline(cx - dx, cx + dx, cy + dy, c)


def poly(points, c):
    """Scanline fill of a simple polygon (even-odd)."""
    if not points:
        return
    ys = [p[1] for p in points]
    y0, y1 = min(ys), max(ys)
    n = len(points)
    for y in range(y0, y1 + 1):
        xs = []
        for i in range(n):
            x0, ya = points[i]
            x1, yb = points[(i + 1) % n]
            if ya == yb:
                continue
            if (ya <= y < yb) or (yb <= y < ya):
                xs.append(x0 + (y - ya) * (x1 - x0) / (yb - ya))
        xs.sort()
        for k in range(0, len(xs) - 1, 2):
            hline(int(xs[k]), int(xs[k + 1]), y, c)


def thick_line(x0, y0, x1, y1, t, c):
    import math
    dx, dy = x1 - x0, y1 - y0
    d = math.hypot(dx, dy)
    if d == 0:
        circle(x0, y0, t // 2, c)
        return
    px, py = -dy / d * t / 2.0, dx / d * t / 2.0
    poly([(int(x0 + px), int(y0 + py)), (int(x1 + px), int(y1 + py)),
          (int(x1 - px), int(y1 - py)), (int(x0 - px), int(y0 - py))], c)


def star(cx, cy, r_out, r_in, n, c):
    import math
    pts = []
    for i in range(2 * n):
        r = r_out if i % 2 == 0 else r_in
        a = math.pi * i / n - math.pi / 2
        pts.append((int(cx + r * math.cos(a)), int(cy + r * math.sin(a))))
    poly(pts, c)


# ---------------------------------------------------------------- PNG codec
def read_png_rgba(path):
    """Minimal PNG reader: 8-bit, non-interlaced, color type 2 or 6."""
    with open(path, "rb") as f:
        data = f.read()
    assert data[:8] == b"\x89PNG\r\n\x1a\n", "not a PNG"
    pos = 8
    w = h = None
    ctype = None
    idat = bytearray()
    while pos < len(data):
        ln = struct.unpack(">I", data[pos:pos + 4])[0]
        typ = data[pos + 4:pos + 8]
        chunk = data[pos + 8:pos + 8 + ln]
        if typ == b"IHDR":
            w, h, depth, ctype, _, _, inter = struct.unpack(">IIBBBBB", chunk)
            assert depth == 8 and inter == 0
            assert ctype in (2, 6)
        elif typ == b"IDAT":
            idat += chunk
        elif typ == b"IEND":
            break
        pos += 12 + ln
    ch = 4 if ctype == 6 else 3
    stride = w * ch
    raw = zlib.decompress(bytes(idat))
    out = bytearray(w * h * 4)
    prev = bytearray(stride)
    p = 0
    for y in range(h):
        ft = raw[p]
        p += 1
        row = bytearray(raw[p:p + stride])
        p += stride
        if ft == 1:
            for i in range(ch, stride):
                row[i] = (row[i] + row[i - ch]) & 255
        elif ft == 2:
            for i in range(stride):
                row[i] = (row[i] + prev[i]) & 255
        elif ft == 3:
            for i in range(stride):
                a = row[i - ch] if i >= ch else 0
                row[i] = (row[i] + ((a + prev[i]) >> 1)) & 255
        elif ft == 4:
            for i in range(stride):
                a = row[i - ch] if i >= ch else 0
                b = prev[i]
                cc = prev[i - ch] if i >= ch else 0
                pp = a + b - cc
                pa, pb, pc = abs(pp - a), abs(pp - b), abs(pp - cc)
                pr = a if (pa <= pb and pa <= pc) else (b if pb <= pc else cc)
                row[i] = (row[i] + pr) & 255
        elif ft != 0:
            raise ValueError("bad filter %d" % ft)
        if ch == 4:
            out[y * w * 4:(y + 1) * w * 4] = row
        else:
            for x in range(w):
                o = (y * w + x) * 4
                s = x * 3
                out[o] = row[s]
                out[o + 1] = row[s + 1]
                out[o + 2] = row[s + 2]
                out[o + 3] = 255
        prev = row
    return w, h, out


def encode_png(rgb, w, h):
    raw = bytearray()
    stride = w * 3
    for y in range(h):
        raw.append(0)
        raw += rgb[y * stride:(y + 1) * stride]
    comp = zlib.compress(bytes(raw), 9)

    def chunk(typ, payload):
        return (struct.pack(">I", len(payload)) + typ + payload +
                struct.pack(">I", binascii.crc32(typ + payload) & 0xFFFFFFFF))

    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) +
            chunk(b"IDAT", comp) + chunk(b"IEND", b""))


# ---------------------------------------------------------------- font atlas
ATLAS_CELL_W = 40
ATLAS_CELL_H = 72
ATLAS_COLS = 10
ATLAS_W = 0
ATLAS_H = 0
ATLAS = b""
_glyph_cache = {}


def load_atlas():
    global ATLAS_W, ATLAS_H, ATLAS
    here = os.path.dirname(os.path.abspath(__file__))
    ATLAS_W, ATLAS_H, ATLAS = read_png_rgba(os.path.join(here, "atlas.png"))


def _glyph(ch, bold, scale):
    key = (ch, bold, scale)
    g = _glyph_cache.get(key)
    if g is not None:
        return g
    idx = ord(ch) - 32
    if idx < 0 or idx > 94:
        idx = 0
    col = idx % ATLAS_COLS
    row = idx // ATLAS_COLS + (0 if bold else 10)
    sx0 = col * ATLAS_CELL_W
    sy0 = row * ATLAS_CELL_H
    dw = max(1, int(round(ATLAS_CELL_W * scale)))
    dh = max(1, int(round(ATLAS_CELL_H * scale)))
    out = bytearray(dw * dh)
    inv = 1.0 / scale
    for dy in range(dh):
        y0 = dy * inv
        y1 = (dy + 1) * inv
        iy0 = int(y0)
        iy1 = int(y1)
        if iy1 > ATLAS_CELL_H - 1:
            iy1 = ATLAS_CELL_H - 1
        for dx in range(dw):
            x0 = dx * inv
            x1 = (dx + 1) * inv
            ix0 = int(x0)
            ix1 = int(x1)
            if ix1 > ATLAS_CELL_W - 1:
                ix1 = ATLAS_CELL_W - 1
            s = 0.0
            wsum = 0.0
            for iy in range(iy0, iy1 + 1):
                wy = min(y1, iy + 1) - max(y0, iy)
                if wy <= 0:
                    continue
                base = ((sy0 + iy) * ATLAS_W + sx0) * 4 + 3
                for ix in range(ix0, ix1 + 1):
                    wx = min(x1, ix + 1) - max(x0, ix)
                    if wx <= 0:
                        continue
                    s += ATLAS[base + ix * 4] * wx * wy
                    wsum += wx * wy
            out[dy * dw + dx] = int(s / wsum + 0.5) if wsum else 0
    g = (dw, dh, out)
    _glyph_cache[key] = g
    return g


def text_width(s, scale):
    return int(round(len(s) * ATLAS_CELL_W * scale))


def draw_text(s, x, y, color, scale, bold=True):
    cx = x
    for ch in s:
        dw, dh, alpha = _glyph(ch, bold, scale)
        for dy in range(dh):
            yy = y + dy
            if yy < 0 or yy >= H:
                continue
            rowbase = (yy * W + cx) * 3
            abase = dy * dw
            for dx in range(dw):
                a = alpha[abase + dx]
                if a == 0:
                    continue
                xx = cx + dx
                if xx < 0 or xx >= W:
                    continue
                i = rowbase + dx * 3
                if a == 255:
                    canvas[i] = color[0]
                    canvas[i + 1] = color[1]
                    canvas[i + 2] = color[2]
                else:
                    canvas[i] = (canvas[i] * (255 - a) + color[0] * a) // 255
                    canvas[i + 1] = (canvas[i + 1] * (255 - a) + color[1] * a) // 255
                    canvas[i + 2] = (canvas[i + 2] * (255 - a) + color[2] * a) // 255
        cx += dw
    return cx


def draw_text_centered(s, cx, y, color, scale, bold=True):
    draw_text(s, cx - text_width(s, scale) // 2, y, color, scale, bold)


def wrap_text(s, max_w, scale):
    char_w = ATLAS_CELL_W * scale
    max_chars = max(1, int(max_w // char_w))
    words = s.split(" ")
    lines = []
    cur = ""
    for word in words:
        trial = word if not cur else cur + " " + word
        if len(trial) <= max_chars:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


# ---------------------------------------------------------------- icons
def icon_summit(bx, by):
    # Three leaders: heads, shoulders, small flag bars on their chests.
    skins = [(232, 185, 138), (217, 160, 102), (201, 142, 95)]
    suits = [NAVY, (122, 31, 31), (51, 51, 51)]
    for k in range(3):
        cx = bx + 63 + k * 95
        # neck
        fill_rect(cx - 6, by + 44, 12, 16, skins[k])
        circle(cx, by + 32, 16, skins[k])
        # shoulders: flat suit block with a rounded top
        fill_rect(cx - 30, by + 58, 60, 38, suits[k])
        ellipse(cx, by + 58, 30, 12, suits[k])
        # shirt V + tie
        poly([(cx - 8, by + 58), (cx + 8, by + 58), (cx, by + 74)], CARD)
        poly([(cx - 3, by + 62), (cx + 3, by + 62), (cx, by + 76)], RED)
        # flag bar on chest
        fx = cx - 19
        fy = by + 80
        if k == 0:  # USA: stripes + blue canton
            for s in range(5):
                fill_rect(fx, fy + s * 2, 38, 2, RED if s % 2 == 0 else CARD)
            fill_rect(fx, fy, 16, 6, NAVY)
        elif k == 1:  # China: red field, yellow star dots
            fill_rect(fx, fy, 38, 10, RED)
            circle(fx + 8, fy + 5, 3, GOLD)
            circle(fx + 20, fy + 3, 1, GOLD)
            circle(fx + 26, fy + 6, 1, GOLD)
        else:  # Russia: white / blue / red
            fill_rect(fx, fy, 38, 4, CARD)
            fill_rect(fx, fy + 3, 38, 4, BLUE)
            fill_rect(fx, fy + 7, 38, 3, RED)


def icon_strikes(bx, by):
    # Rocket on a diagonal, flame at the tail, burst at the nose.
    dashed_line(bx + 40, by + 88, bx + 138, by + 66, (150, 150, 150), 6, 5)
    # flame, attached at the tail
    poly([(bx + 146, by + 72), (bx + 112, by + 90), (bx + 132, by + 92)], (255, 140, 40))
    poly([(bx + 146, by + 74), (bx + 124, by + 88), (bx + 134, by + 90)], (255, 210, 80))
    # body: nose (238,18), tail (150,66); perpendicular (0.6,0.8)*9
    poly([(bx + 238, by + 18), (bx + 221, by + 33), (bx + 157, by + 75),
          (bx + 143, by + 61)], (220, 225, 230))
    poly([(bx + 238, by + 18), (bx + 221, by + 33), (bx + 208, by + 25)], RED)
    circle(bx + 196, by + 42, 6, SKY)
    ring(bx + 196, by + 42, 6, 2, INK, SKY)
    # fins at the tail
    poly([(bx + 157, by + 75), (bx + 143, by + 61), (bx + 128, by + 76)], RED)
    poly([(bx + 157, by + 75), (bx + 143, by + 61), (bx + 162, by + 88)], RED)
    # burst star at the nose
    star(bx + 262, by + 16, 16, 6, 8, GOLD)
    star(bx + 288, by + 40, 9, 4, 8, (255, 140, 40))
    circle(bx + 60, by + 30, 3, GRAY)
    circle(bx + 90, by + 16, 2, GRAY)


def icon_bridge(bx, by):
    # Suspension bridge with a broken span and smoke.
    deck_y = by + 58
    # towers
    fill_rect(bx + 84, by + 14, 10, deck_y - by - 14, INK)
    fill_rect(bx + 222, by + 14, 10, deck_y - by - 14, INK)
    # cables
    line(bx + 89, by + 14, bx + 30, deck_y, INK)
    line(bx + 89, by + 14, bx + 148, deck_y, INK)
    line(bx + 227, by + 14, bx + 168, deck_y, INK)
    line(bx + 227, by + 14, bx + 286, deck_y, INK)
    # deck, broken in the middle
    fill_rect(bx + 24, deck_y, 118, 6, INK)
    fill_rect(bx + 174, deck_y, 118, 6, INK)
    # jagged broken ends
    poly([(bx + 142, deck_y), (bx + 152, deck_y + 10), (bx + 142, deck_y + 6)], INK)
    poly([(bx + 174, deck_y), (bx + 164, deck_y + 10), (bx + 174, deck_y + 6)], INK)
    # smoke above the gap
    circle(bx + 148, by + 34, 9, (150, 150, 150))
    circle(bx + 162, by + 26, 12, (170, 170, 170))
    circle(bx + 176, by + 36, 8, (150, 150, 150))
    # water below
    for yy, x0 in ((by + 74, bx + 40), (by + 82, bx + 90), (by + 90, bx + 60)):
        hline(x0, x0 + 120, yy, STEEL)
        hline(x0 + 130, x0 + 190, yy, STEEL)


def icon_tank(bx, by):
    # Tank crossing a dashed yellow ceasefire line.
    ground = by + 80
    hline(bx + 20, bx + 296, ground, INK)
    # dashed yellow line, vertical, right of the tank
    for yy in range(by + 8, ground, 14):
        vline(bx + 252, yy, min(yy + 8, ground), GOLD)
    # hull + turret + barrel
    fill_rect(bx + 96, by + 46, 108, 26, (85, 107, 47))
    fill_rect(bx + 128, by + 28, 52, 20, (70, 90, 40))
    thick_line(bx + 180, by + 36, bx + 240, by + 30, 6, (70, 90, 40))
    circle(bx + 154, by + 38, 5, (60, 78, 34))
    # wheels
    for k in range(4):
        circle(bx + 112 + k * 26, by + 74, 8, INK)
        circle(bx + 112 + k * 26, by + 74, 3, GRAY)
    # small flag on the turret
    line(bx + 132, by + 28, bx + 132, by + 12, INK)
    poly([(bx + 132, by + 12), (bx + 152, by + 16), (bx + 132, by + 20)], RED)


def icon_ipo(bx, by):
    # Rising bars, arrow, gold coin with a dollar sign.
    hline(bx + 56, bx + 250, by + 84, INK)
    vline(bx + 56, by + 12, by + 84, INK)
    heights = [22, 36, 50, 66]
    for k, hh in enumerate(heights):
        x = bx + 76 + k * 38
        fill_rect(x, by + 84 - hh, 26, hh, BLUE if k < 3 else GREEN)
    thick_line(bx + 84, by + 58, bx + 232, by + 16, 4, INK)
    poly([(bx + 238, by + 12), (bx + 214, by + 12), (bx + 240, by + 24)], INK)
    # coin
    circle(bx + 272, by + 30, 16, GOLD)
    ring(bx + 272, by + 30, 16, 3, (150, 105, 20), GOLD)
    draw_text("$", bx + 266, by + 18, (90, 60, 0), 0.38, bold=True)


def icon_voyager(bx, by):
    # Dark sky, stars, spacecraft, Earth, dotted path.
    import math
    for (sx, sy, r) in [(40, 18, 2), (90, 10, 1), (150, 14, 2), (210, 22, 1),
                        (60, 52, 1), (120, 78, 2), (200, 70, 1), (250, 12, 2),
                        (30, 70, 1), (180, 52, 1)]:
        circle(bx + sx, by + sy, r, CARD)
    star(bx + 100, by + 26, 5, 2, 4, CARD)
    star(bx + 230, by + 48, 5, 2, 4, CARD)
    # dotted path from Earth to the craft
    dashed_line(bx + 246, by + 62, bx + 170, by + 44, LIGHTGRAY, 4, 4)
    # spacecraft body
    poly([(bx + 96, by + 46), (bx + 118, by + 28), (bx + 152, by + 36),
          (bx + 152, by + 54), (bx + 118, by + 62)], GOLD)
    circle(bx + 100, by + 46, 11, CARD)
    ring(bx + 100, by + 46, 11, 2, GRAY, CARD)
    line(bx + 152, by + 38, bx + 176, by + 20, CARD)
    circle(bx + 178, by + 18, 3, RED)
    poly([(bx + 118, by + 62), (bx + 168, by + 70), (bx + 168, by + 80),
          (bx + 118, by + 72)], STEEL)
    # Earth
    circle(bx + 264, by + 72, 20, BLUE)
    ellipse(bx + 258, by + 66, 7, 4, GREEN)
    ellipse(bx + 270, by + 78, 6, 4, GREEN)
    ring(bx + 264, by + 72, 20, 2, SKY, BLUE)


ICONS = [icon_summit, icon_strikes, icon_bridge, icon_tank, icon_ipo, icon_voyager]

STORIES = [
    ("SUMMIT IN SHENZHEN", ["TRUMP, XI AND", "PUTIN MEET"],
     "First three-way talks at APEC. Xi hugged Trump on arrival."),
    ("MIDDLE EAST", ["US-IRAN WAR", "WIDENS"],
     "US hit Qeshm. Iran hits a US base in Kuwait and Bahrain."),
    ("UKRAINE WAR", ["CRIMEA BRIDGE", "HIT AGAIN"],
     "Traffic halted after a new attack on the strategic bridge."),
    ("GAZA", ["ISRAEL PUSHES", "INTO GAZA"],
     "Rare ground push beyond the ceasefire line, the Yellow Line."),
    ("MARKETS", ["ANTHROPIC IPO", "SETS RECORD"],
     "$81.3bn raised, the biggest IPO ever. Shares priced at $83."),
    ("SPACE", ["VOYAGER 1 IS", "ONE LIGHT-DAY"],
     "Nearly 50 years on, Voyager 1 is one light-day out. NASA marks it."),
]


# ---------------------------------------------------------------- build
def build():
    load_atlas()
    fill_rect(0, 0, W, H, PAPER)
    # double outer rule
    fill_rect(12, 12, W - 24, 3, INK)
    fill_rect(12, H - 15, W - 24, 3, INK)
    fill_rect(12, 12, 3, H - 24, INK)
    fill_rect(W - 15, 12, 3, H - 24, INK)

    # masthead
    draw_text_centered("THE WORLD TODAY", W // 2, 30, INK, 1.05, bold=True)
    fill_rect(W // 2 - 350, 114, 700, 4, RED)
    draw_text_centered("THURSDAY 19 NOVEMBER 2026", W // 2, 126, RED, 0.72, bold=True)
    fill_rect(24, 186, W - 48, 3, INK)

    # grid: 3 columns x 2 rows
    gx, gy = 24, 198
    cw, ch = 316, 391
    gut = 14
    for i, (kicker, headline, body) in enumerate(STORIES):
        col, row = i % 3, i // 3
        x = gx + col * (cw + gut)
        y = gy + row * (ch + gut)
        fill_rect(x, y, cw, ch, CARD)
        # border
        fill_rect(x, y, cw, 2, INK)
        fill_rect(x, y + ch - 2, cw, 2, INK)
        fill_rect(x, y, 2, ch, INK)
        fill_rect(x + cw - 2, y, 2, ch, INK)
        # icon band
        fill_rect(x + 2, y + 2, cw - 4, 96, BAND_TINTS[i])
        ICONS[i](x + 2, y + 2)
        # kicker
        draw_text(kicker, x + 14, y + 108, RED, 0.40, bold=True)
        # headline
        hy = y + 142
        for ln in headline:
            draw_text(ln, x + 14, hy, INK, 0.55, bold=True)
            hy += 48
        # body
        by = y + 242
        for ln in wrap_text(body, cw - 28, 0.40):
            draw_text(ln, x + 14, by, BODY, 0.40, bold=False)
            by += 33
    return bytes(canvas)


def main():
    outdir = os.environ.get("MAKEFUN_OUTPUT_DIR", "/output")
    os.makedirs(outdir, exist_ok=True)
    data = encode_png(build(), W, H)
    with open(os.path.join(outdir, "entry.png"), "wb") as f:
        f.write(data)


if __name__ == "__main__":
    main()
