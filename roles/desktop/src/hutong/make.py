#!/usr/bin/env python3
"""Hutong (胡同): pixel-art plymouth theme for marlinos.

A side-view Beijing hutong lane, drawn like a 2D game. The scene is split into layers
(three skies, background, foreground, night shade, night lights) plus small sprite
animations; the plymouth script moves the walkers and fades night <-> day:
boot goes night -> day with the boot progress, shutdown/reboot go day -> night.

Everything is drawn at 342x192 logical pixels and written x4 (nearest neighbour) as PNG.
Needs only python and ImageMagick (`magick`, to rasterize the Chinese glyphs).

Usage: make.py OUTDIR [--preview DIR]
  OUTDIR    theme directory (marlinos: roles/desktop/system/usr/share/plymouth/themes/hutong)
  --preview also write preview PNGs/GIFs of boot and shutdown composited like the script does
"""
import functools
import math
import os
import random
import struct
import subprocess
import sys
import zlib

W, H = 342, 192
SCALE = 4
WALL_Y = 140          # bottom of the house walls / back edge of the lane
BACK_LANE = 155       # feet of walkers on the far side of the lane
FRONT_LANE = 170      # feet of walkers on the near side
HERE = os.path.dirname(os.path.abspath(__file__))
CJK_FONT = subprocess.run(["fc-match", "-f", "%{file}", "Source Han Sans CN:bold"],
                          capture_output=True, text=True, check=True).stdout

# ---------------------------------------------------------------- palette (daylight)
OUTLINE = (44, 32, 48)
BRICK, BRICK_D, BRICK_L, MORTAR = (146, 150, 160), (124, 128, 140), (166, 170, 178), (112, 116, 128)
TILE, TILE_L, TILE_D = (72, 76, 90), (98, 104, 118), (50, 52, 64)
RED, RED_D, GOLD = (196, 44, 44), (132, 26, 32), (236, 196, 82)
WOOD, WOOD_D, PAPER = (146, 94, 52), (92, 56, 32), (232, 218, 182)
STONE, STONE_D, STONE_L = (176, 170, 164), (150, 144, 140), (194, 188, 182)
LEAF, LEAF_L, LEAF_D, TRUNK = (70, 140, 74), (104, 172, 86), (44, 104, 62), (96, 64, 44)
SKIN, SKIN_D = (240, 196, 160), (210, 160, 126)
LAMP = (255, 200, 110)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


class Canvas:
    """RGBA pixel canvas."""

    def __init__(self, w, h, fill=(0, 0, 0, 0)):
        self.w, self.h = w, h
        self.p = [tuple(fill) for _ in range(w * h)]

    def get(self, x, y):
        if 0 <= x < self.w and 0 <= y < self.h:
            return self.p[y * self.w + x]
        return (0, 0, 0, 0)

    def set(self, x, y, c):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h:
            self.p[y * self.w + x] = tuple(c[:3]) + ((c[3],) if len(c) > 3 else (255,))

    def blend(self, x, y, c, a):
        x, y = int(x), int(y)
        if 0 <= x < self.w and 0 <= y < self.h and a > 0:
            o = self.p[y * self.w + x]
            a = min(a, 1)
            if o[3] == 0:
                self.p[y * self.w + x] = tuple(c[:3]) + (int(255 * a),)
            else:
                self.p[y * self.w + x] = tuple(int(o[i] + (c[i] - o[i]) * a) for i in range(3)) + (o[3],)

    def rect(self, x, y, w, h, c):
        for yy in range(int(y), int(y + h)):
            for xx in range(int(x), int(x + w)):
                self.set(xx, yy, c)

    def hline(self, x0, x1, y, c):
        for xx in range(int(x0), int(x1) + 1):
            self.set(xx, y, c)

    def vline(self, x, y0, y1, c):
        for yy in range(int(y0), int(y1) + 1):
            self.set(x, yy, c)

    def disc(self, cx, cy, r, c, ry=None):
        ry = ry or r
        for yy in range(int(cy - ry) - 1, int(cy + ry) + 2):
            for xx in range(int(cx - r) - 1, int(cx + r) + 2):
                if ((xx - cx) / r) ** 2 + ((yy - cy) / ry) ** 2 <= 1:
                    self.set(xx, yy, c)

    def paste(self, other, x, y):
        for j in range(other.h):
            for i in range(other.w):
                c = other.p[j * other.w + i]
                if c[3] == 255:
                    self.set(x + i, y + j, c)
                elif c[3]:
                    self.blend(x + i, y + j, c, c[3] / 255)

    def save(self, path, scale=SCALE):
        rows = []
        for y in range(self.h):
            line = b"".join(bytes(self.p[y * self.w + x]) * scale for x in range(self.w))
            rows.extend([b"\x00" + line] * scale)

        def chunk(tag, data):
            return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", zlib.crc32(tag + data))

        ihdr = struct.pack(">IIBBBBB", self.w * scale, self.h * scale, 8, 6, 0, 0, 0)
        with open(path, "wb") as f:
            f.write(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr)
                    + chunk(b"IDAT", zlib.compress(b"".join(rows), 9)) + chunk(b"IEND", b""))


# ---------------------------------------------------------------- text

@functools.lru_cache(maxsize=None)
def cjk(text, size):
    """Rasterize Chinese text to a 1-bit glyph grid (list of strings, '#' = ink)."""
    pbm = subprocess.run(["magick", "-background", "white", "-fill", "black", "-font", CJK_FONT,
                          "-pointsize", str(size), "label:" + text, "-threshold", "55%", "pbm:-"],
                         capture_output=True, check=True).stdout
    parts = pbm.split(b"\n", 2)
    w, h = map(int, parts[1].split())
    data, stride = parts[2], (w + 7) // 8
    rows = ["".join("#" if data[y * stride + x // 8] >> (7 - x % 8) & 1 else "." for x in range(w))
            for y in range(h)]
    rows = [r for r in rows if "#" in r]
    left = min(r.index("#") for r in rows)
    right = max(r.rindex("#") for r in rows)
    return [r[left:right + 1] for r in rows]


# hand-drawn glyphs for characters the font can't render cleanly this small
PIXEL_GLYPHS = {
    "茶": ["...#...#...", "###########", "...#...#...", ".....#.....", "...##.##...", ".##.....##.",
          "#.#######.#", ".....#.....", "..#..#..#..", ".#...#...#.", "....##....."],
    "煎": ["..#.....#..", "...#...#...", "###########", ".####.#..#.", ".#..#.#..#.", ".####.#..#.",
          ".#..#.#..#.", ".#..#....#.", ".#.##...##.", "...........", "#..#..#..#."],
    "饼": [".#...#...#.", "#.#...#.#..", "#...#######", "#.....#.#..", "#.....#.#..", "#...#######",
          "#.#...#.#..", "##....#..#.", "#....#...#."],
}


def glyph(cv, x, y, text, size, c):
    """Draw Chinese text left to right; returns the width used."""
    for ch in text:
        g = PIXEL_GLYPHS.get(ch) or cjk(ch, size)
        for j, row in enumerate(g):
            for i, v in enumerate(row):
                if v == "#":
                    cv.set(x + i, y + j, c)
        x += len(g[0]) + 1
    return x


# 3x5 pixel font, rows left to right, top to bottom
FONT3x5 = {
    "A": ".#.#.#####.##.#", "B": "##.#.###.#.###.", "C": ".###..#..#...##", "D": "##.#.##.##.###.",
    "E": "####..##.#..###", "F": "####..##.#..#..", "G": ".###..#.##.#.##", "H": "#.##.#####.##.#",
    "I": "###.#..#..#.###", "K": "#.##.###.#.##.#", "L": "#..#..#..#..###", "M": "#.########.##.#",
    "N": "##.#.##.##.##.#", "O": ".#.#.##.##.#.#.", "P": "##.#.###.#..#..", "R": "##.#.###.#.##.#",
    "S": ".###...#...###.", "T": "###.#..#..#..#.", "U": "#.##.##.##.####", "W": "#.##.########.#",
    "Y": "#.##.#.#..#..#.", "0": "####.##.##.####", "1": ".#.##..#..#.###", "2": "##...#.#.#..###",
    "4": "#.##.####..#..#", " ": "...............", "/": "..#..#.#.#..#..", "-": "......###......",
    ">": "#...#...#.#.#..", "_": "............###", ".": ".............#.", ":": "....#.....#....",
}


def text3x5(cv, x, y, s, c, k=1):
    """Draw text in the 3x5 font, each font pixel k x k."""
    for ch in s:
        g = FONT3x5.get(ch, FONT3x5[" "])
        for i, v in enumerate(g):
            if v == "#":
                cv.rect(x + i % 3 * k, y + i // 3 * k, k, k, c)
        x += 4 * k
    return x


def text_width(s, k=1):
    return (len(s) * 4 - 1) * k


# ---------------------------------------------------------------- sprites

def sprite(rows, legend, outline=True, flip=False):
    """Canvas from a character map; '.' is transparent. Adds a 1px dark outline."""
    if flip:
        rows = [r[::-1] for r in rows]
    w, h = max(len(r) for r in rows) + 2, len(rows) + 2
    cv = Canvas(w, h)
    for j, row in enumerate(rows):
        for i, ch in enumerate(row):
            if ch in legend:
                cv.set(i + 1, j + 1, legend[ch])
    if outline:
        solid = [[cv.get(x, y)[3] == 255 for x in range(w)] for y in range(h)]
        for y in range(h):
            for x in range(w):
                if not solid[y][x] and any(0 <= x + dx < w and 0 <= y + dy < h and solid[y + dy][x + dx]
                                           for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                    cv.set(x, y, OUTLINE)
    return cv


HEAD = [
    "..hhhh..",
    ".hhhhhh.",
    ".hhhsss.",
    ".hhsses.",
    "..hssss.",
    "...ss...",
]
LEGS = [  # walk cycle, 4 frames
    ["..bbbb..", ".bb..bb.", "bb....bb", "kk....kk"],
    ["..bbbb..", "...bb...", "...bb...", "...kkk.."],
    ["..bbbb..", ".bb..bb.", "bb....bb", "kk....kk"],
    ["..bbbb..", "...bb...", "...bb...", "..kkk..."],
]
HANDS = [(6, 10), (5, 11), (1, 10), (5, 11)]


def person(f, hair, top, pants, shoes, skin=SKIN, extra=None, flip=False):
    """One walk-cycle frame of a generic person (facing right unless flip)."""
    body = ["..tttt..", ".tttttt.", ".tttttt.", ".tttttt.", "..tttt.."]
    rows = HEAD + body + LEGS[f]
    rows = [r.ljust(10, ".") for r in rows]
    leg = {"h": hair, "s": skin, "e": OUTLINE, "t": top, "b": pants, "k": shoes, "a": skin}
    if extra:
        rows, leg = extra(rows, leg, f)
    hx, hy = HANDS[f]
    rows[hy] = rows[hy][:hx] + "a" + rows[hy][hx + 1:]
    return sprite(rows, leg, flip=flip)


def put(rows, x, y, s):
    """Overwrite characters of a sprite map at (x, y), growing it if needed."""
    rows = list(rows)
    while y >= len(rows):
        rows.append("")
    for i, ch in enumerate(s):
        if ch == " ":
            continue
        r = rows[y + 0].ljust(x + i + 1, ".")
        rows[y] = r[:x + i] + ch + r[x + i + 1:]
    return rows


def with_bag(rows, leg, f):  # shopper with a green bag and a bun
    rows = put(rows, 2, 0, "hhh")
    rows = put(rows, 1, 0, "h")
    hx, hy = HANDS[f]
    for dy in range(1, 4):
        rows = put(rows, hx, hy + dy, "gg")
    leg["g"] = (70, 150, 90)
    return rows, leg


def with_cane(rows, leg, f):  # grandpa: cap, white shirt, cane
    rows = put(rows, 1, 0, "cccccc")
    rows = put(rows, 1, 1, "ccccccc")
    rows = put(rows, 7, 1, "c")
    for y in range(10, 15):
        rows = put(rows, 7, y, "w")
    leg["c"], leg["w"] = (60, 70, 100), WOOD_D
    return rows, leg


def with_balloon(rows, leg, f):  # kid with a balloon (drawn above the head)
    pad = ["..........", "....rr....", "...rrrr...", "...rrrr...", "....rr....", ".....l....",
           ".....l....", "......l..."]
    rows = pad + rows[:]
    rows = put(rows, 6, len(pad) - 1, "l")
    leg["r"], leg["l"] = (230, 50, 60), (200, 200, 200)
    return rows, leg


def walker_frames(kw, flip):
    return [person(f, flip=flip, **kw) for f in range(4)]


# -- sitting / idle characters (2-3 frames each)

def chef(f):
    rows = [
        "..www...",
        ".wwwww..",
        ".wwwww..",
        "..ssss..",
        "..sses..",
        "..ssss..",
        ".wwwwww.",
        "wwwwwwww",
        "wwwwwwww",
        ".wwwwww.",
    ]
    arms = [("a......a", "nnnnnnnn"), ("..a..a..", "..nnnn.."), ("a......a", "nnnnnnnn")][f]
    rows = put(rows, 0, 7, arms[0])
    rows = rows + [arms[1].replace(".", " ")]
    return sprite(rows, {"w": (245, 245, 240), "s": SKIN, "e": OUTLINE, "a": SKIN, "n": (250, 240, 200)})


def diner(f, top, hair, flip=False):
    rows = [
        "..hhhh..",
        ".hhhhhh.",
        ".hhsss..",
        ".hhses..",
        "..sss...",
        "..tttt..",
        ".ttttta.",
        ".tttttac",
        ".tttttt.",
        "..bbbbb.",
        "..b...b.",
    ]
    if f == 1:  # chopsticks up to the mouth
        rows[7] = ".tttttt."
        rows[6] = ".tttta.."
        rows[4] = "..sssc.."
    return sprite(rows, {"h": hair, "s": SKIN, "e": OUTLINE, "t": top, "b": (60, 60, 80), "a": SKIN,
                         "c": WOOD}, flip=flip)


def granny(f, top, flip=False):
    rows = [
        "..gggg..",
        ".gggggg.",
        ".gsssgg.",
        ".gsess..",
        "..ssss..",
        ".tttttt.",
        "ttttttt.",
        "ttttttt.",
        ".bbbbbb.",
        ".bb..bb.",
    ]
    fan = ["......FF", ".....FF."][f]
    rows = put(rows, 0, 4 + f, fan)
    return sprite(rows, {"g": (215, 215, 220), "s": SKIN, "e": OUTLINE, "t": top, "b": (60, 60, 90),
                         "F": (240, 120, 140)}, flip=flip)


def hacker(f):
    rows = [
        "h....h..",
        "hhhhhh..",
        "hhhhhhh.",
        "hhssshh.",
        "hhsGsG..",
        "hhssss..",
        ".hhhhh..",
        "hhhhhhLL",
        "hhhhhLLL",
        ".bbbbb..",
        ".b...b..",
    ]
    if f:
        rows[7] = "hhhhhaLL"
    else:
        rows[8] = "hhhhaLLL"
    return sprite(rows, {"h": (110, 70, 170), "s": SKIN, "G": (60, 230, 255), "L": (180, 182, 200),
                         "b": (50, 40, 70), "a": SKIN})


def fruit_seller(f):
    rows = [
        "...yy...",
        "..yyyy..",
        "yyyyyyyy",
        "..ssss..",
        "..sess..",
        "..ssss..",
        ".bbbbbb.",
        "bbbbbbbb",
        "bbbbbbbb",
    ]
    rows = put(rows, 7, 5 + f, "F")
    rows = put(rows, 6, 6 + f, "a")
    return sprite(rows, {"y": (220, 190, 110), "s": SKIN_D, "e": OUTLINE, "b": (70, 110, 170),
                         "F": (240, 240, 230), "a": SKIN_D})


def jianbing_cook(f):
    rows = [
        "..rrrr..",
        ".rrrrrr.",
        "..ssss..",
        "..sess..",
        "..ssss..",
        ".pppppp.",
        "pppppppp",
        "pppppppp",
    ]
    rows = put(rows, 6, 6 if f else 5, "aS")
    return sprite(rows, {"r": (200, 40, 40), "s": SKIN, "e": OUTLINE, "p": (240, 240, 240), "a": SKIN,
                         "S": (150, 150, 160)})


CAT_COLORS = {"o": (236, 150, 60), "k": (30, 26, 34), "w": (240, 238, 232), "g": (130, 130, 140)}


def cat_walk(f, fur, flip=False):
    legs = [".l..l..l.l", "..l.l..ll.", ".l..l..l.l", "..ll...l.l"][f]
    rows = [
        "t.......ff",
        ".t.....fff",
        ".tffffffEf",
        "..fffffff.",
        "..ffffff..",
        legs.replace("l", "f"),
    ]
    if f % 2:
        rows[0] = ".t......ff"
        rows[1] = "t......fff"
    return sprite(rows, {"f": fur, "t": fur, "E": (250, 220, 70)}, flip=flip)


def cat_sit(f, fur):
    rows = [
        "f...f...",
        "fffff...",
        "fEfEf...",
        "fffff...",
        ".fff....",
        "fffff...",
        "ffffft..",
        "ffffft..",
        "fffff...",
    ]
    tail = [["ffffft..", "fffff.t."], ["fffffft.", "fffff..t"], ["ffffft..", "fffff.t."]][f]
    rows[7], rows[8] = tail
    return sprite(rows, {"f": fur, "t": fur, "E": (120, 200, 90)})


def cat_sleep(f, fur):
    rows = [
        "..........",
        ".ffffff.ff",
        "fffffffffE",
        "ffffffffff",
        "tttffffff.",
    ]
    if f:
        rows[0] = "..ffff...."
        rows[1] = ".ffffff.ff"
    return sprite(rows, {"f": fur, "t": fur, "E": fur})


def bicycle(f, rider_top, flip=False):
    rows = [
        "......hhh.......",
        ".....hhhhs......",
        ".....hhsse......",
        "......tttt......",
        ".....ttttta.....",
        ".....tttt.aa....",
        "......bbb..H....",
        "......b.b..H....",
        "..WWW..FFFFH.WWW",
        ".W...W.F..F.W...",
        ".W.x.WFFFFF.W.x.",
        ".W...W......W...",
        "..WWW........WWW",
    ]
    if f:
        rows[10] = ".W.x.W.FFFF.W.x."
        rows[7] = "......bb.b..H..."
    return sprite(rows, {"h": (40, 40, 50), "s": SKIN, "e": OUTLINE, "t": rider_top, "a": SKIN,
                         "b": (50, 60, 90), "H": (60, 60, 70), "W": (40, 40, 48), "F": (40, 120, 200),
                         "x": (160, 160, 170)}, flip=flip)


def tricycle(f, flip=False):
    rows = [
        ".........hhh....",
        "........hhhhs...",
        "........hhsse...",
        "BBBBBBB..tttt...",
        "BbBBbBB..tttta..",
        "BBBBBBB.tttt.a..",
        "BBBBBBB..bbb.H..",
        "MMMMMMMMMMMMMH..",
        ".WWW.......WWW..",
        "W.x.W.....W.x.W.",
        ".WWW.......WWW..",
    ]
    if f:
        rows[9] = "W.+.W.....W.+.W."
    return sprite(rows, {"h": (60, 50, 40), "s": SKIN_D, "e": OUTLINE, "t": (60, 120, 200), "a": SKIN_D,
                         "b": (50, 50, 60), "B": (200, 160, 100), "M": (70, 90, 110),
                         "H": (60, 60, 70), "W": (40, 40, 48), "x": (160, 160, 170), "+": (160, 160, 170)},
                  flip=flip)


def pigeons(f):
    a = [".w...w.", "wwwwwww", "..w.w.."] if f else ["wwwwwww", ".wwwww.", "..w.w.."]
    rows = []
    for dy, dx in ((0, 0), (3, 9), (6, 2), (1, 17), (7, 14)):
        for j, r in enumerate(a):
            rows = put(rows, dx, dy + j, r)
    rows = [r.ljust(26, ".") for r in rows]
    return sprite(rows, {"w": (230, 230, 236)}, outline=False)


def cloud(seed):
    rng = random.Random(seed)
    cv = Canvas(60, 18)
    for _ in range(9):
        cx, cy, r = rng.uniform(10, 50), rng.uniform(7, 12), rng.uniform(4, 8)
        cv.disc(cx, cy, r, (255, 255, 255, 235))
    for x in range(60):
        for y in range(18):
            c = cv.get(x, y)
            if c[3] and cv.get(x, y + 2)[3] == 0:
                cv.set(x, y, (225, 232, 245, 235))
    return cv


def steam(f):
    cv = Canvas(12, 18)
    for i in range(3):
        p = (f * 2 + i * 3) % 9
        cx = 6 + math.sin(p * 0.9 + i) * 2
        cy = 16 - p * 1.8
        r = 1.5 + p / 5
        for yy in range(int(cy - r) - 1, int(cy + r) + 2):
            for xx in range(int(cx - r) - 1, int(cx + r) + 2):
                if math.hypot(xx - cx, yy - cy) <= r:
                    cv.blend(xx, yy, (250, 250, 255), 0.55 * (1 - p / 9))
    return cv


# ---------------------------------------------------------------- scene drawing

def roof(cv, x0, x1, y_eave, height, ornate=False):
    """Grey tiled roof with curled eave ends; y_eave is the bottom edge."""
    top = y_eave - height
    for y in range(top, y_eave + 1):
        u = (y - top) / max(height, 1)
        inset = int((1 - u) * 3)
        for x in range(x0 - 3 + inset, x1 + 4 - inset):
            c = TILE_L if (x - x0) % 3 == 0 else TILE
            if y == y_eave:
                c = TILE_D if (x - x0) % 3 else (130, 134, 146)
            cv.set(x, y, c)
    cv.hline(x0 - 1, x1 + 1, top - 1, TILE_D)
    cv.hline(x0 - 1, x1 + 1, top - 2, TILE_D)
    for ex, d in ((x0 - 1, -1), (x1 + 1, 1)):  # curled ridge ends
        cv.set(ex + d, top - 3, TILE_D)
        cv.set(ex + 2 * d, top - 4, TILE_D)
    for ex, d in ((x0 - 3, -1), (x1 + 3, 1)):  # upturned eave corners
        cv.set(ex + d, y_eave - 1, TILE_D)
        cv.set(ex + d, y_eave - 2, TILE_D)
    if ornate:
        for ex in (x0 + 2, x1 - 2):
            cv.rect(ex - 1, top - 5, 3, 3, TILE_D)


def brick_wall(cv, x0, x1, top, bottom=WALL_Y):
    for y in range(top, bottom):
        for x in range(x0, x1):
            r = (y - top) // 3
            c = BRICK
            if (y - top) % 3 == 2:
                c = MORTAR
            elif (x + (r % 2) * 3) % 6 == 0:
                c = MORTAR
            elif (x * 7 + y * 13) % 17 == 0:
                c = BRICK_L
            elif (x * 5 + y * 11) % 19 == 0:
                c = BRICK_D
            cv.set(x, y, c)
    cv.rect(x0, bottom - 4, x1 - x0, 4, STONE_D)
    cv.hline(x0, x1 - 1, bottom - 4, STONE)


def lattice_window(cv, lights, x, y, w, h):
    cv.rect(x - 1, y - 1, w + 2, h + 2, WOOD_D)
    for yy in range(y, y + h):
        for xx in range(x, x + w):
            grid = (xx - x) % 3 == 1 or (yy - y) % 3 == 1
            cv.set(xx, yy, WOOD if grid else PAPER)
            if not grid:
                lights.set(xx, yy, LAMP)


def red_door(cv, x, w, h, bottom=WALL_Y, lights=None, fu=True):
    cv.rect(x - 2, bottom - h - 2, w + 4, h + 2, WOOD_D)
    cv.rect(x, bottom - h, w, h, RED)
    cv.vline(x + w // 2, bottom - h, bottom - 1, RED_D)
    for yy in range(bottom - h + 2, bottom - 2, 3):
        for xx in (x + 2, x + w // 2 - 2, x + w // 2 + 2, x + w - 3):
            cv.set(xx, yy, GOLD)
    for side in (x - 5, x + w + 3):  # couplets
        cv.rect(side, bottom - h, 2, h - 2, RED)
        for yy in range(bottom - h + 1, bottom - 3, 2):
            cv.set(side + (yy % 4 == 1), yy, GOLD)
    if fu:  # 福 diamond
        cx, cy = x + w // 2, bottom - h - 6
        for d in range(4):
            cv.hline(cx - d, cx + d, cy - 3 + d, RED)
            cv.hline(cx - d, cx + d, cy + 3 - d, RED)
        cv.set(cx, cy, GOLD)


def lantern(cv, lights, x, y):
    cv.vline(x, y - 3, y - 1, OUTLINE)
    cv.rect(x - 2, y, 5, 1, GOLD)
    cv.rect(x - 3, y + 1, 7, 5, RED)
    cv.rect(x - 2, y + 6, 5, 1, GOLD)
    cv.vline(x, y + 7, y + 9, RED)
    cv.vline(x - 1, y + 2, y + 4, (230, 90, 70))
    for yy in range(y + 1, y + 6):
        for xx in range(x - 3, x + 4):
            lights.set(xx, yy, (255, 110, 70) if abs(xx - x) < 2 else (240, 60, 50))
    glow(lights, x, y + 3, 16, (255, 90, 60), 0.55)


def glow(cv, cx, cy, r, c, strength):
    for yy in range(int(cy - r), int(cy + r) + 1):
        for xx in range(int(cx - r), int(cx + r) + 1):
            d = math.hypot(xx - cx, yy - cy) / r
            if d < 1:
                a = strength * (1 - d) ** 2
                o = cv.get(xx, yy)
                if o[3] < 255:  # lights layer: keep the strongest glow, as alpha
                    na = min(255, int(o[3] + a * 255))
                    base = c if o[3] == 0 else lerp(o[:3], c, 0.5)
                    cv.p[yy * cv.w + xx] = tuple(base) + (na,)


def plaque(cv, x, y, text, size=9, fg=GOLD, bg=(40, 24, 20)):
    g = [cjk(ch, size) for ch in text]
    w = sum(len(a[0]) + 1 for a in g) + 5
    h = max(len(a) for a in g) + 5
    cv.rect(x, y, w, h, bg)
    cv.rect(x + 1, y + 1, w - 2, h - 2, (bg[0] + 20, bg[1] + 10, bg[2] + 10))
    for xx in range(x, x + w):
        cv.set(xx, y, fg)
        cv.set(xx, y + h - 1, fg)
    for yy in range(y, y + h):
        cv.set(x, yy, fg)
        cv.set(x + w - 1, yy, fg)
    glyph(cv, x + 3, y + 3, text, size, fg)
    return w, h


def tree(cv, x, base, size, rng, color_shift=0):
    cv.rect(x - 2, base - size, 4, size, TRUNK)
    cv.vline(x - 2, base - size, base - 1, (70, 46, 32))
    for _ in range(int(size * 1.6)):
        cx = x + rng.uniform(-size * 0.8, size * 0.8)
        cy = base - size - rng.uniform(-size * 0.2, size * 0.7)
        r = rng.uniform(size * 0.25, size * 0.45)
        cv.disc(cx, cy, r, lerp(LEAF_D, (40, 70, 60), color_shift))
    for _ in range(int(size * 1.2)):
        cx = x + rng.uniform(-size * 0.7, size * 0.7)
        cy = base - size - rng.uniform(0, size * 0.75)
        r = rng.uniform(size * 0.18, size * 0.32)
        cv.disc(cx, cy, r, lerp(LEAF, (60, 90, 80), color_shift))
        cv.disc(cx - r * 0.3, cy - r * 0.3, r * 0.5, lerp(LEAF_L, (80, 110, 100), color_shift))


def wire(cv, x0, y0, x1, y1, sag, c=OUTLINE):
    pts = []
    for x in range(x0, x1 + 1):
        u = (x - x0) / (x1 - x0)
        y = int(round(y0 + (y1 - y0) * u + sag * 4 * u * (1 - u)))
        cv.set(x, y, c)
        pts.append((x, y))
    return pts


def background(rng):
    """Everything behind the walkers: far tower and trees, houses, lane. Sky is transparent."""
    bg = Canvas(W, H)
    lights = Canvas(W, H)

    # far: drum tower and tree line (pale, hazy)
    far, far_d, far_l = (156, 172, 200), (136, 152, 184), (176, 190, 214)
    bg.rect(262, 88, 52, 20, far)  # brick platform with arches
    for ax in range(268, 310, 10):
        bg.rect(ax, 96, 5, 12, far_d)
        bg.hline(ax + 1, ax + 3, 95, far_d)
    bg.rect(270, 76, 36, 12, far_l)  # lower hall
    for cx in range(273, 305, 5):
        bg.vline(cx, 77, 87, far)
    for y, (x0, x1) in ((74, (262, 314)), (75, (264, 312)), (73, (266, 310))):
        bg.hline(x0, x1, y, far_d)
    bg.set(261, 72, far_d)
    bg.set(315, 72, far_d)
    bg.rect(276, 62, 24, 11, far_l)  # upper hall
    for cx in range(279, 299, 5):
        bg.vline(cx, 63, 72, far)
    for y, (x0, x1) in ((60, (268, 308)), (61, (270, 306)), (59, (272, 304)), (58, (276, 300))):
        bg.hline(x0, x1, y, far_d)
    bg.set(267, 58, far_d)
    bg.set(309, 58, far_d)
    trng = random.Random(4)
    for x in range(0, W, 9):
        bg.disc(x + trng.uniform(-3, 3), 100 + trng.uniform(-4, 4), trng.uniform(7, 12), (128, 160, 150))
    for x in range(4, W, 13):
        bg.disc(x + trng.uniform(-3, 3), 104 + trng.uniform(-3, 3), trng.uniform(6, 10), (110, 148, 128))

    # houses, left to right
    # A: plain courtyard wall with a red door
    brick_wall(bg, 0, 62, 112)
    roof(bg, 0, 61, 112, 10)
    lattice_window(bg, lights, 8, 118, 12, 8)
    red_door(bg, 34, 14, 20, lights=lights)
    lantern(bg, lights, 30, 113)
    lantern(bg, lights, 52, 113)

    # B: 面馆 noodle restaurant (wooden front)
    bg.rect(64, 108, 78, 32, WOOD)
    for x in range(64, 142, 13):
        bg.rect(x, 108, 2, 32, WOOD_D)
    bg.rect(68, 122, 34, 14, (70, 46, 32))  # open counter, warm inside
    lights.rect(69, 123, 32, 12, (255, 190, 110, 120))
    bg.rect(70, 124, 30, 3, (120, 80, 50))
    for xx in range(72, 99, 5):
        bg.rect(xx, 121, 3, 2, (230, 230, 220))  # bowls on the shelf
    bg.rect(108, 116, 26, 24, (40, 60, 120))  # door curtain
    for xx in range(108, 134, 6):
        bg.vline(xx, 116, 139, (30, 46, 96))
    glyph(bg, 115, 121, "面", 9, (240, 240, 250))
    roof(bg, 64, 141, 108, 11, ornate=True)
    plaque(bg, 80, 95, "面馆", 9)
    lantern(bg, lights, 68, 109)
    lantern(bg, lights, 138, 109)

    # C: siheyuan gate (taller roof, steps, door piers)
    brick_wall(bg, 144, 186, 106)
    roof(bg, 146, 184, 104, 13, ornate=True)
    red_door(bg, 156, 18, 26, lights=lights)
    bg.rect(150, 136, 42, 4, STONE_L)
    bg.rect(152, 132, 4, 4, STONE)
    bg.rect(176, 132, 4, 4, STONE)  # 门墩 drums
    lantern(bg, lights, 152, 105)
    lantern(bg, lights, 180, 105)

    # D: tea house with lattice windows and a hanging 茶 flag
    brick_wall(bg, 188, 252, 112)
    roof(bg, 188, 251, 112, 10)
    lattice_window(bg, lights, 194, 117, 18, 12)
    lattice_window(bg, lights, 224, 117, 18, 12)
    bg.rect(214, 120, 8, 20, WOOD_D)
    bg.vline(250, 96, 130, WOOD_D)
    bg.hline(234, 250, 96, WOOD_D)
    bg.rect(234, 98, 15, 16, (70, 140, 100))
    for x in range(234, 249, 2):
        bg.set(x, 114, (70, 140, 100))
    glyph(bg, 236, 101, "茶", 9, (250, 250, 240))

    # E: 小卖部 corner shop with crates of goods
    brick_wall(bg, 254, W, 112)
    roof(bg, 254, W, 112, 10)
    bg.rect(262, 116, 50, 20, (60, 50, 60))
    lights.rect(263, 117, 48, 18, (255, 230, 170, 110))
    goods = [(230, 70, 60), (250, 200, 60), (80, 170, 220), (120, 200, 90), (240, 240, 240)]
    for yy in range(118, 134, 4):
        for xx in range(264, 310, 3):
            bg.rect(xx, yy, 2, 3, goods[(xx * 3 + yy) % 5])
    plaque(bg, 262, 98, "小卖部", 9, fg=(255, 255, 255), bg=(170, 30, 30))

    # scholar tree on the right, overlapping the roofs
    tree(bg, 326, 140, 26, random.Random(9))

    # wires, laundry line with clothes
    wire(bg, 0, 86, 120, 90, 6)
    wire(bg, 120, 90, W - 1, 84, 7)
    pts = wire(bg, 150, 94, 250, 96, 5, (90, 90, 96))
    clothes = [(230, 80, 80), (80, 140, 220), (250, 250, 250), (240, 200, 70), (140, 90, 190)]
    for i, x in enumerate(range(160, 244, 12)):
        y = pts[x - 150][1]
        c = clothes[i % 5]
        if i % 2:
            bg.rect(x, y + 1, 6, 7, c)  # shirt
            bg.rect(x - 1, y + 1, 8, 2, c)
        else:
            bg.rect(x, y + 1, 5, 9, c)  # trousers
            bg.vline(x + 2, y + 5, y + 9, (0, 0, 0, 0))
    bg.vline(150, 94, 140, (100, 100, 108))

    # lane: stone paving with a curb
    for y in range(WALL_Y, H):
        for x in range(W):
            c = STONE
            if y == WALL_Y:
                c = STONE_D
            elif (y - WALL_Y) % 9 == 0 or (x + ((y - WALL_Y) // 9) * 7) % 16 == 0:
                c = STONE_D
            elif (x * 3 + y * 7) % 23 == 0:
                c = STONE_L
            bg.set(x, y, c)
    for x in range(0, W, 2):
        bg.set(x, WALL_Y + 1, (120, 116, 112))
    return bg, lights


def stalls(rng):
    """Props in the lane: noodle cart + tables, fruit stall, jianbing cart, stools.
    Drawn on two layers: 'mid' sits between back-lane and front-lane walkers."""
    mid = Canvas(W, H)
    lights = Canvas(W, H)

    # noodle cart in front of the 面馆 (chef stands behind it, idle sprite)
    mid.rect(70, 140, 34, 13, (160, 50, 40))
    mid.rect(70, 140, 34, 2, (210, 90, 70))
    mid.rect(72, 143, 30, 1, GOLD)
    glyph(mid, 82, 144, "面", 7, (255, 230, 120))
    mid.rect(74, 135, 11, 5, (120, 120, 132))  # pot
    mid.rect(74, 135, 11, 1, (170, 170, 180))
    mid.rect(90, 137, 9, 3, (230, 230, 220))  # bowls
    for wx in (75, 99):
        mid.disc(wx, 154, 2.5, (40, 40, 48))
    lights.rect(70, 140, 34, 2, (255, 180, 100))

    # a table with stools and bowls (diners are idle sprites)
    tx = 116
    mid.rect(tx, 146, 16, 2, (190, 120, 60))
    mid.vline(tx + 1, 148, 153, WOOD_D)
    mid.vline(tx + 14, 148, 153, WOOD_D)
    for bx in (tx + 2, tx + 10):
        mid.rect(bx, 144, 4, 2, (240, 240, 230))
        mid.rect(bx + 1, 143, 2, 1, (250, 220, 160))

    # fruit stall under a striped parasol
    mid.vline(222, 116, 160, (200, 200, 200))
    for y in range(114, 122):
        half = (y - 114) * 3 + 6
        for x in range(222 - half, 222 + half):
            mid.set(x, y, (230, 60, 60) if ((x - 222) // 5) % 2 else (250, 250, 250))
    mid.rect(204, 148, 36, 12, (150, 100, 60))
    mid.rect(204, 148, 36, 2, (190, 140, 90))
    fruit = [(250, 140, 40), (230, 50, 60), (120, 200, 70), (250, 220, 60), (150, 60, 160)]
    for i, x in enumerate(range(206, 238, 6)):
        for k in range(5):
            mid.set(x + k % 3, 145 + k // 3, fruit[i % 5])
            mid.set(x + 1 + k % 2, 144 + k // 3, fruit[i % 5])
    lights.rect(204, 148, 36, 2, (255, 210, 140))

    # jianbing tricycle cart
    mid.rect(266, 140, 32, 15, (230, 230, 225))
    mid.rect(266, 140, 32, 2, (200, 40, 40))
    glyph(mid, 270, 142, "煎饼", 8, (200, 40, 40))
    mid.rect(268, 138, 14, 3, (60, 60, 70))  # griddle
    mid.disc(272, 156, 3, (40, 40, 48))
    mid.disc(293, 156, 3, (40, 40, 48))
    mid.disc(282, 156, 3, (40, 40, 48))

    # stools by the gate for the grannies, the hacker's stool by the tea house
    for sx in (107, 133, 150, 168, 196):
        mid.rect(sx, 151, 8, 2, (60, 120, 200))
        mid.vline(sx + 1, 153, 156, (40, 80, 150))
        mid.vline(sx + 6, 153, 156, (40, 80, 150))
    glow(lights, 207, 146, 8, (60, 230, 255), 0.5)  # laptop screen
    return mid, lights


def sky(kind, rng):
    cv = Canvas(W, H)
    top, bot = {"night": ((10, 12, 40), (52, 40, 96)),
                "dawn": ((70, 70, 150), (255, 168, 120)),
                "day": ((96, 170, 236), (196, 228, 250))}[kind]
    for y in range(H):
        c = lerp(top, bot, min(y / 110, 1))
        for x in range(W):
            cv.set(x, y, c)
    if kind == "night":
        srng = random.Random(11)
        for _ in range(70):
            x, y = srng.randrange(W), srng.randrange(90)
            cv.set(x, y, (255, 255, 255) if srng.random() < 0.3 else (180, 180, 230))
    if kind == "dawn":
        for y in range(70, 110):
            for x in range(W):
                cv.blend(x, y, (255, 200, 140), (y - 70) / 80)
    return cv


def night_shade(bg_lights, mid_lights):
    """Dark blue veil over the whole scene, thinner where lights shine."""
    cv = Canvas(W, H)
    for y in range(H):
        for x in range(W):
            l = max(bg_lights.get(x, y)[3], mid_lights.get(x, y)[3]) / 255
            a = int(255 * 0.62 * (1 - 0.85 * l))
            cv.p[y * W + x] = (12, 14, 46, a)
    return cv


def sun():
    cv = Canvas(15, 15)
    cv.disc(7, 7, 6.5, (255, 220, 120))
    cv.disc(7, 7, 5, (255, 244, 180))
    return cv


def moon():
    cv = Canvas(13, 13)
    cv.disc(6, 6, 5.5, (240, 236, 210))
    for x, y in ((4, 5), (7, 8), (8, 4)):
        cv.set(x, y, (210, 206, 186))
    cv.disc(9, 4, 3.5, (0, 0, 0, 0))
    return cv


def hud_panel(w, h):
    cv = Canvas(w, h)
    for y in range(h):
        for x in range(w):
            corner = (x in (0, w - 1)) and (y in (0, h - 1))
            if corner:
                continue
            edge = x in (0, w - 1) or y in (0, h - 1)
            cv.set(x, y, (250, 240, 220, 255) if edge else (30, 22, 40, 215))
    return cv


def label(zh, en, color):
    g = [cjk(ch, 10) for ch in zh]
    w = sum(len(x[0]) + 1 for x in g) + 6 + text_width(en, 2) + 2
    cv = Canvas(w + 2, 12)
    x = 1
    for gl in g:
        for j, row in enumerate(gl):
            for i, v in enumerate(row):
                if v == "#":
                    cv.set(x + i, (12 - len(gl)) // 2 + j, color)
        x += len(gl[0]) + 1
    text3x5(cv, x + 5, 1, en, (250, 240, 220), k=2)
    return cv


# ---------------------------------------------------------------- objects for the script
#
# idle:   (name, frames, x, y, z, ticks per frame)       cycling in place
# walker: (name, frames, x, y, z, speed px/tick, ticks per frame, day_only)
#         walks across and wraps around; speed < 0 walks left.

def objects():
    idle, walk = [], []
    idle.append(("chef", [chef(f) for f in (0, 1, 2, 1)], 82, 123, 25, 9))
    idle.append(("steam", [steam(f) for f in range(5)], 73, 118, 26, 6))
    idle.append(("diner1", [diner(f, (200, 80, 80), (40, 30, 30)) for f in (0, 1)], 106, 153, 24, 17))
    idle.append(("diner2", [diner(f, (80, 150, 90), (90, 60, 40), flip=True) for f in (1, 0)], 132, 153, 24, 21))
    idle.append(("granny1", [granny(f, (120, 60, 140)) for f in (0, 1)], 149, 153, 24, 11))
    idle.append(("granny2", [granny(f, (200, 110, 60), flip=True) for f in (1, 0)], 167, 153, 24, 13))
    idle.append(("hacker", [hacker(f) for f in (0, 1)], 195, 153, 24, 7))
    idle.append(("fruit", [fruit_seller(f) for f in (0, 1)], 216, 150, 23, 15))
    idle.append(("jianbing", [jianbing_cook(f) for f in (0, 1)], 283, 146, 23, 12))
    idle.append(("catsit", [cat_sit(f, CAT_COLORS["o"]) for f in (0, 1, 2, 1)], 186, 140, 22, 10))
    idle.append(("catsleep", [cat_sleep(f, CAT_COLORS["g"]) for f in (0, 1)], 16, 96, 22, 30))

    shopper = dict(hair=(40, 30, 30), top=(230, 120, 150), pants=(70, 70, 110), shoes=(40, 40, 40),
                   extra=with_bag)
    grandpa = dict(hair=(200, 200, 200), top=(240, 240, 235), pants=(60, 60, 70), shoes=(30, 30, 30),
                   extra=with_cane)
    kid = dict(hair=(30, 30, 30), top=(250, 200, 60), pants=(60, 120, 200), shoes=(200, 60, 60),
               extra=with_balloon)
    student = dict(hair=(30, 30, 40), top=(70, 110, 200), pants=(40, 40, 60), shoes=(240, 240, 240))
    walk.append(("shopper", walker_frames(shopper, False), 20, BACK_LANE, 20, 0.22, 8, 0))
    walk.append(("grandpa", walker_frames(grandpa, True), 250, BACK_LANE, 20, -0.12, 12, 0))
    walk.append(("kid", walker_frames(kid, False), 120, FRONT_LANE, 40, 0.32, 6, 0))
    walk.append(("student", walker_frames(student, True), 300, FRONT_LANE, 40, -0.26, 7, 0))
    walk.append(("bike", [bicycle(f, (230, 90, 60)) for f in (0, 1)], -40, FRONT_LANE + 1, 41, 0.6, 5, 0))
    walk.append(("trike", [tricycle(f, flip=True) for f in (0, 1)], 200, BACK_LANE + 1, 21, -0.35, 7, 0))
    walk.append(("catwalk", [cat_walk(f, CAT_COLORS["k"]) for f in range(4)], 40, WALL_Y - 28, 15, 0.15, 7, 0))
    walk.append(("pigeons", [pigeons(f) for f in (0, 1)], 10, 40, 5, 0.5, 6, 1))
    walk.append(("cloud1", [cloud(1)], 30, 14, 4, 0.04, 1000, 1))
    walk.append(("cloud2", [cloud(2)], 210, 30, 4, 0.03, 1000, 1))
    return idle, walk


# ---------------------------------------------------------------- output

def write_script(out, idle, walk):
    lines = []
    for i, (name, frames, x, y, z, period) in enumerate(idle):
        for k in range(len(frames)):
            lines.append(f'idle[{i}].frames[{k}] = load("{name}-{k}.png");')
        # (x, y) is the sprite's feet/bottom-left in logical pixels
        lines.append(f"idle[{i}].n = {len(frames)}; idle[{i}].x = {x}; "
                     f"idle[{i}].y = {y - frames[0].h}; idle[{i}].z = {z}; idle[{i}].period = {period};")
    lines.append(f"idle_count = {len(idle)};")
    for i, (name, frames, x, y, z, speed, period, day) in enumerate(walk):
        for k in range(len(frames)):
            lines.append(f'walker[{i}].frames[{k}] = load("{name}-{k}.png");')
        lines.append(f"walker[{i}].n = {len(frames)}; walker[{i}].x = {x}; walker[{i}].y = {y - frames[0].h}; "
                     f"walker[{i}].z = {z}; walker[{i}].speed = {speed}; walker[{i}].period = {period}; "
                     f"walker[{i}].w = {frames[0].w}; walker[{i}].day_only = {day};")
    lines.append(f"walker_count = {len(walk)};")
    template = open(os.path.join(HERE, "hutong.script.in")).read()
    with open(os.path.join(out, "hutong.script"), "w") as f:
        f.write(template.replace("@OBJECTS@", "\n".join(lines)).replace("@W@", str(W)))


def main():
    args = sys.argv[1:]
    preview = None
    if "--preview" in args:
        preview = args[args.index("--preview") + 1]
        del args[args.index("--preview"):args.index("--preview") + 2]
    out = args[0] if args else "."
    os.makedirs(out, exist_ok=True)
    rng = random.Random(1987)

    layers = {}
    for kind in ("night", "dawn", "day"):
        layers[f"sky-{kind}"] = sky(kind, rng)
    bg, bg_lights = background(rng)
    mid, mid_lights = stalls(rng)
    lights = Canvas(W, H)
    lights.paste(bg_lights, 0, 0)
    lights.paste(mid_lights, 0, 0)
    layers.update(bg=bg, mid=mid, night=night_shade(bg_lights, mid_lights), lights=lights)
    for name, cv in layers.items():
        cv.save(f"{out}/{name}.png")
    sun().save(f"{out}/sun.png")
    moon().save(f"{out}/moon.png")

    idle, walk = objects()
    for name, frames, *_ in idle + walk:
        for k, fr in enumerate(frames):
            fr.save(f"{out}/{name}-{k}.png")

    label("启动中", "BOOTING", (255, 214, 110)).save(f"{out}/label-boot.png")
    label("关机", "SHUTTING DOWN", (255, 140, 170)).save(f"{out}/label-shutdown.png")
    label("重启", "REBOOTING", (140, 220, 255)).save(f"{out}/label-reboot.png")
    hud_panel(150, 22).save(f"{out}/hud.png")
    bar = Canvas(122, 5)
    for x in range(122):
        bar.set(x, 0, (250, 240, 220))
        bar.set(x, 4, (250, 240, 220))
    for y in range(5):
        bar.set(0, y, (250, 240, 220))
        bar.set(121, y, (250, 240, 220))
    bar.save(f"{out}/bar.png")
    fill = Canvas(1, 3, (255, 190, 90, 255))
    fill.save(f"{out}/bar-fill.png")
    write_script(out, idle, walk)

    if preview:
        from preview import render_previews
        render_previews(out, preview, layers, idle, walk)


if __name__ == "__main__":
    main()
