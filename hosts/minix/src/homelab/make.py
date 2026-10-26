#!/usr/bin/env python3
"""Homelab: pixel-art plymouth theme for minix.

A desk in a small room, drawn like a 2D game: the Minix box with a cat asleep on top,
the wifi router, a monitor scrolling the server's status, a desk lamp, and a window
on the city. Boot goes night -> day with the boot progress, shutdown/reboot day -> night.
The scene is split into layers (three skies, room, desk, night shade, night lights) plus
small sprite animations, moved and faded by homelab.script.

Everything is drawn at 342x192 logical pixels and written x4 (nearest neighbour) as PNG.
Needs only python (ImageMagick `magick` for the preview GIFs).

Usage: make.py OUTDIR [--preview DIR]
  OUTDIR    theme directory (marlinos: hosts/minix/system/usr/share/plymouth/themes/homelab)
  --preview also write preview stills and GIFs of boot and shutdown, composited like the script
"""
import math
import os
import random
import struct
import subprocess
import sys
import zlib

W, H = 342, 192
SCALE = 4
HERE = os.path.dirname(os.path.abspath(__file__))

DESK_Y = 128          # top of the desk surface
FLOOR_Y = 172         # top of the floor
GLASS = (198, 18, 306, 96)   # window glass x0, y0, x1, y1 (sky shows through)

# ---------------------------------------------------------------- palette (daylight)
OUTLINE = (40, 30, 40)
WALL, WALL_L, WALL_D = (176, 150, 128), (188, 162, 138), (156, 132, 112)
TRIM, TRIM_D = (122, 88, 62), (96, 68, 48)
FRAME, FRAME_D = (236, 232, 222), (196, 190, 178)
CURTAIN, CURTAIN_D = (176, 70, 62), (138, 50, 48)
FLOOR, FLOOR_L, FLOOR_D = (128, 86, 56), (148, 102, 68), (104, 68, 44)
DESK, DESK_L, DESK_D = (166, 114, 72), (192, 140, 92), (122, 80, 48)
METAL, METAL_L, METAL_D = (62, 64, 72), (92, 96, 106), (40, 42, 48)
CASE, CASE_L = (52, 54, 60), (80, 82, 90)
ROUTER, ROUTER_D = (228, 228, 222), (186, 186, 180)
LEAF, LEAF_L, LEAF_D = (70, 140, 74), (104, 172, 86), (44, 104, 62)
POT = (190, 104, 70)
LAMP_SHADE, LAMP_SHADE_D = (230, 186, 64), (186, 140, 40)
SCREEN = (16, 24, 28)
TERM = (110, 240, 150)
BLUE_LED, GREEN_LED, AMBER_LED, RED_LED = (90, 180, 255), (90, 240, 120), (255, 190, 70), (255, 80, 70)
WARM = (255, 200, 110)
WHALE, WHALE_D = (64, 140, 220), (40, 100, 176)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(len(a)))


def clamp01(v):
    return max(0.0, min(1.0, v))


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

    def line(self, x0, y0, x1, y1, c):
        n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
        for i in range(n + 1):
            t = i / n
            self.set(round(x0 + (x1 - x0) * t), round(y0 + (y1 - y0) * t), c)

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

# 3x5 pixel font, rows left to right, top to bottom (a 20-character glyph is 4 wide)
FONT3x5 = {
    "A": ".#.#.#####.##.#", "B": "##.#.###.#.###.", "C": ".###..#..#...##", "D": "##.#.##.##.###.",
    "E": "####..##.#..###", "F": "####..##.#..#..", "G": ".###..#.##.#.##", "H": "#.##.#####.##.#",
    "I": "###.#..#..#.###", "J": "..#..#..##.#.#.", "K": "#.##.###.#.##.#", "L": "#..#..#..#..###",
    "M": "#.########.##.#", "N": "#..###.##.###..##..#", "O": ".#.#.##.##.#.#.", "P": "##.#.###.#..#..",
    "R": "##.#.###.#.##.#", "S": ".###...#...###.", "T": "###.#..#..#..#.", "U": "#.##.##.##.####",
    "V": "#.##.##.##.#.#.", "W": "#.##.########.#", "X": "#.##.#.#.#.##.#", "Y": "#.##.#.#..#..#.",
    "Z": "###..#.#.#..###",
    "0": "####.##.##.####", "1": ".#.##..#..#.###", "2": "##...#.#.#..###", "3": "###..#.##..####",
    "4": "#.##.####..#..#", "5": "####..###..####", "6": "####..####.####", "7": "###..#..#..#..#",
    "8": "####.#####.####", "9": "####.####..####",
    " ": "...............", "/": "..#..#.#.#..#..", "-": "......###......", ">": "#...#...#.#.#..",
    "_": "............###", ".": ".............#.", ":": "....#.....#....", "=": "...###...###...",
    "+": "....#.###.#....", "!": ".#..#..#.....#.",
}


def text3x5(cv, x, y, s, c, k=1):
    """Draw text in the 3x5 font, each font pixel k x k."""
    for ch in s:
        g = FONT3x5.get(ch, FONT3x5[" "])
        gw = len(g) // 5
        for i, v in enumerate(g):
            if v == "#":
                cv.rect(x + i % gw * k, y + i // gw * k, k, k, c)
        x += (gw + 1) * k
    return x


def text_width(s, k=1):
    return (sum(len(FONT3x5.get(ch, FONT3x5[" "])) // 5 + 1 for ch in s) - 1) * k


# ---------------------------------------------------------------- sprites

def sprite(rows, legend, outline=True):
    """Canvas from a character map; '.' is transparent. Adds a 1px dark outline."""
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


def cat_sleep(f):
    """An orange cat curled up asleep, breathing (2 frames)."""
    rows = [
        "..................",
        "..ooooooooooo..o.o",
        ".oooooooooooooooooo",
        "oooowwoooooooooo-oo",
        "oooooooooooooooooow",
        "tttttooooooooooowww",
    ]
    if f:
        rows[0] = "....ooooooo......."
        rows[1] = "..ooooooooooo..o.o"
    return sprite(rows, {"o": (236, 150, 60), "w": (246, 232, 212), "t": (214, 126, 46),
                         "-": (120, 60, 30)})


def led(color, on):
    cv = Canvas(3, 3)
    c = color if on else lerp(color, (30, 30, 34), 0.75)
    cv.set(1, 1, c)
    if on:   # a faint halo
        for x, y in ((1, 0), (0, 1), (2, 1), (1, 2)):
            cv.set(x, y, tuple(c) + (110,))
    return cv


def leds(colors, pattern):
    """A row of LEDs 6px apart; pattern is one on/off flag per LED."""
    cv = Canvas(len(colors) * 6, 3)
    for i, (c, on) in enumerate(zip(colors, pattern)):
        cv.paste(led(c, on), i * 6, 0)
    return cv


TERM_LINES = ["MINIX LOGIN:", "K3S    READY", "DOCKER    UP", "SSHD   :4242", "WIFI      OK",
              "PODS   10/10", "TRAEFIK   UP", "REGISTRY  UP", "LOAD    0.21", "TEMP     41C"]


def terminal(f):
    """Monitor content: status lines scrolling up one per frame, blinking cursor at the bottom."""
    cv = Canvas(56, 28)
    for i in range(4):
        text3x5(cv, 2, 2 + i * 6, TERM_LINES[(f // 2 + i) % len(TERM_LINES)], TERM)
    if f % 2 == 0:
        cv.rect(2, 2 + 4 * 6 - 1, 3, 2, TERM)
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


def vacuum(f):
    """Robot vacuum, side view, with a blinking status light."""
    rows = [
        "...gggggggggg...",
        ".gggggggggggggg.",
        "kkkkkkkkkkkkkkkk",
        "kkkkkkkkkkkkkkkk",
        ".ww..........ww.",
    ]
    rows[0] = rows[0][:7] + ("L" if f else "l") + rows[0][8:]
    return sprite(rows, {"g": (200, 204, 212), "k": (50, 52, 60), "w": (30, 30, 34),
                         "L": GREEN_LED, "l": (40, 90, 60)})


def birds(f):
    a = [".w...w.", "..w.w..", "...w..."] if f else ["...w...", ".wwwww.", "w.....w"]
    cv = Canvas(30, 12)
    for dx, dy in ((0, 0), (9, 4), (18, 1)):
        for j, r in enumerate(a):
            for i, ch in enumerate(r):
                if ch == "w":
                    cv.set(dx + i, dy + j, (60, 60, 80))
    return cv


def cloud(seed):
    rng = random.Random(seed)
    cv = Canvas(44, 14)
    for _ in range(7):
        cx, cy, r = rng.uniform(8, 36), rng.uniform(6, 9), rng.uniform(3, 6)
        cv.disc(cx, cy, r, (255, 255, 255, 235))
    for x in range(44):
        for y in range(14):
            if cv.get(x, y)[3] and cv.get(x, y + 2)[3] == 0:
                cv.set(x, y, (225, 232, 245, 235))
    return cv


# ---------------------------------------------------------------- scene drawing

def glow(cv, cx, cy, r, c, strength, ry=None):
    """Soft light on a lights layer: color + alpha, keeping the strongest."""
    ry = ry or r
    for yy in range(int(cy - ry), int(cy + ry) + 1):
        for xx in range(int(cx - r), int(cx + r) + 1):
            d = math.hypot((xx - cx) / r, (yy - cy) / ry)
            if d < 1:
                a = strength * (1 - d) ** 2
                o = cv.get(xx, yy)
                if o[3] < 255:
                    na = min(255, int(o[3] + a * 255))
                    base = c if o[3] == 0 else lerp(o[:3], c, 0.5)
                    if 0 <= xx < cv.w and 0 <= yy < cv.h:
                        cv.p[yy * cv.w + xx] = tuple(base) + (na,)


def wire(cv, x0, y0, x1, y1, sag, c):
    n = int(abs(x1 - x0)) + 1
    for i in range(n + 1):
        t = i / n
        cv.set(x0 + (x1 - x0) * t, y0 + (y1 - y0) * t + sag * 4 * t * (1 - t), c)


def in_glass(x, y):
    x0, y0, x1, y1 = GLASS
    return x0 <= x <= x1 and y0 <= y <= y1


def skyline(cv, lights, rng):
    """City seen through the window: two rows of buildings, some windows lit at night."""
    x0, y0, x1, y1 = GLASS
    for far, color, win in ((True, (136, 152, 182), (166, 182, 206)), (False, (104, 118, 150), (140, 156, 184))):
        x = x0 - rng.randrange(6)
        while x < x1:
            w = rng.randrange(10, 20) if far else rng.randrange(12, 24)
            top = rng.randrange(44, 66) if far else rng.randrange(58, 80)
            for yy in range(top, y1 + 1):
                for xx in range(x, x + w):
                    if in_glass(xx, yy):
                        cv.set(xx, yy, color)
            if not far and rng.random() < 0.4:   # antenna
                for yy in range(top - 6, top):
                    if in_glass(x + w // 2, yy):
                        cv.set(x + w // 2, yy, color)
                if in_glass(x + w // 2, top - 7):
                    lights.set(x + w // 2, top - 7, (255, 70, 60, 255))
            for wy in range(top + 3, y1 - 1, 4):
                for wx in range(x + 2, x + w - 2, 3):
                    if in_glass(wx, wy):
                        cv.set(wx, wy, win)
                        if rng.random() < (0.25 if far else 0.4):
                            lights.set(wx, wy, (255, 214, 120, 255))
            x += w + (rng.randrange(1, 4) if far else 0)


def whale():
    """Docker-whale figurine with a stack of containers on its back."""
    rows = [
        ".....rgbr......",
        "....rgbrgb.....",
        "..wwwwwwwwwww.w",
        ".wwwwwwwwwwwwww",
        "wwewwwwwwwwwww.",
        "wwwwwwwwwwwww..",
        ".dddddddddd....",
    ]
    return sprite(rows, {"w": WHALE, "d": WHALE_D, "e": (240, 240, 250), "r": (210, 70, 60),
                         "g": (90, 170, 90), "b": (240, 190, 60)})


def background(rng):
    """The room: wall, window with the city, curtains, shelf, poster, desk, floor."""
    cv = Canvas(W, H)
    lights = Canvas(W, H)
    # wall with a faint stripe
    for y in range(FLOOR_Y):
        for x in range(W):
            cv.set(x, y, WALL_L if x % 14 in (0, 1) else WALL)
    # floor: planks
    for y in range(FLOOR_Y, H):
        for x in range(W):
            seam = (y - FLOOR_Y) % 6 == 5 or (x + ((y - FLOOR_Y) // 6) * 37) % 64 == 0
            cv.set(x, y, FLOOR_D if seam else (FLOOR_L if (y - FLOOR_Y) % 6 == 0 else FLOOR))
    cv.rect(0, FLOOR_Y - 5, W, 5, TRIM)
    cv.hline(0, W - 1, FLOOR_Y - 5, TRIM_D)

    # window: frame, transparent glass, city, cross bars, sill
    x0, y0, x1, y1 = GLASS
    cv.rect(x0 - 4, y0 - 4, x1 - x0 + 9, y1 - y0 + 9, FRAME)
    for y in range(y0, y1 + 1):
        for x in range(x0, x1 + 1):
            cv.p[y * W + x] = (0, 0, 0, 0)
    skyline(cv, lights, rng)
    cx, cy = (x0 + x1) // 2, (y0 + y1) // 2
    cv.rect(cx - 1, y0, 3, y1 - y0 + 1, FRAME)
    cv.rect(x0, cy - 1, x1 - x0 + 1, 3, FRAME)
    cv.vline(cx + 2, y0, y1, FRAME_D)
    cv.hline(x0, x1, cy + 2, FRAME_D)
    cv.rect(x0 - 8, y1 + 4, x1 - x0 + 17, 4, FRAME)
    cv.hline(x0 - 8, x1 + 8, y1 + 8, FRAME_D)
    # curtains, gathered at the sides
    for side, xs in ((0, range(x0 - 14, x0 - 2)), (1, range(x1 + 3, x1 + 15))):
        for x in xs:
            fold = (x - xs.start) % 4 in (0, 1)
            for y in range(y0 - 8, y1 + 22):
                bulge = abs(y - (y1 - 6)) < 6
                if bulge and (x - xs.start) in ((0, 1) if side else (10, 11)):
                    continue
                cv.set(x, y, CURTAIN_D if fold else CURTAIN)
    cv.rect(x0 - 18, y0 - 10, x1 - x0 + 37, 2, METAL)   # curtain rod

    # shelf with books, a plant and the whale
    cv.rect(26, 54, 100, 3, DESK_D)
    cv.hline(26, 125, 54, DESK_L)
    for bx in (32, 116):
        cv.rect(bx, 57, 2, 5, METAL)
    x = 30
    for c, h in (((70, 90, 150), 18), ((180, 80, 70), 15), ((90, 140, 90), 20), ((210, 180, 90), 16),
                 ((120, 80, 140), 19), ((60, 60, 70), 14)):
        cv.rect(x, 54 - h, 5, h, c)
        cv.hline(x, x + 4, 54 - h + 3, lerp(c, (255, 255, 255), 0.3))
        x += 6
    cv.line(x, 54, x + 9, 54 - 14, (200, 120, 60))   # a leaning book
    cv.line(x + 1, 54, x + 10, 54 - 14, (200, 120, 60))
    cv.line(x + 2, 54, x + 11, 54 - 14, (170, 96, 46))
    cv.rect(84, 44, 10, 10, POT)
    cv.hline(83, 94, 44, lerp(POT, (255, 255, 255), 0.2))
    for i, (dx, dy) in enumerate(((-3, -6), (0, -9), (4, -7), (7, -4), (-4, 2), (9, 4), (-2, 8), (11, 10))):
        cv.disc(89 + dx, 44 + dy, 2.2, LEAF if i % 2 else LEAF_L)
    cv.paste(whale(), 100, 54 - 9)

    # poster: a ship's wheel over "K3S"
    px, py = 146, 22
    cv.rect(px, py, 36, 42, (230, 226, 214))
    cv.rect(px + 2, py + 2, 32, 38, (36, 60, 110))
    wx, wy = px + 18, py + 17
    for a in range(7):
        ang = a * 2 * math.pi / 7 - math.pi / 2
        cv.line(wx, wy, wx + math.cos(ang) * 11, wy + math.sin(ang) * 11, (240, 240, 250))
    for t in range(64):
        ang = t * 2 * math.pi / 64
        cv.set(wx + math.cos(ang) * 8, wy + math.sin(ang) * 8, (240, 240, 250))
    cv.disc(wx, wy, 2, (240, 240, 250))
    text3x5(cv, px + 12, py + 32, "K3S", (240, 240, 250))
    cv.set(px + 18, py - 1, METAL_D)   # pin

    # desk
    cv.rect(14, DESK_Y, 316, 5, DESK)
    cv.hline(14, 329, DESK_Y, DESK_L)
    cv.rect(16, DESK_Y + 5, 312, 4, DESK_D)
    for lx in (20, 314):
        cv.rect(lx, DESK_Y + 9, 7, FLOOR_Y - DESK_Y - 7, DESK_D)
        cv.vline(lx, DESK_Y + 9, FLOOR_Y + 1, DESK)
    # drawer block on the right
    cv.rect(250, DESK_Y + 9, 64, 26, DESK)
    cv.rect(250, DESK_Y + 21, 64, 1, DESK_D)
    for hy in (DESK_Y + 15, DESK_Y + 28):
        cv.rect(278, hy, 8, 2, METAL_L)
    # power strip on the floor, cables up to the desk
    cv.rect(58, FLOOR_Y - 1, 36, 4, (226, 226, 222))
    cv.hline(58, 93, FLOOR_Y + 3, (186, 186, 180))
    for sx in (64, 72, 80):
        cv.rect(sx, FLOOR_Y, 3, 1, METAL_D)
    cv.set(89, FLOOR_Y, RED_LED)
    glow(lights, 89, FLOOR_Y, 6, RED_LED, 0.6)
    wire(cv, 66, FLOOR_Y - 1, 128, DESK_Y + 9, 14, METAL_D)
    wire(cv, 74, FLOOR_Y - 1, 214, DESK_Y + 9, 18, METAL_D)
    wire(cv, 82, FLOOR_Y - 1, 286, DESK_Y + 9, 22, METAL_D)
    return cv, lights


def lamp_light(lights):
    """Warm cone from the desk lamp onto the desk."""
    glow(lights, 78, 112, 46, WARM, 0.75, ry=30)
    for y in range(110, DESK_Y + 3):
        half = 4 + (y - 110) * 1.2
        for x in range(int(78 - half), int(78 + half) + 1):
            lights.blend(x, y, WARM, 0.25)


def desk_items(lights):
    """Things on the desk: lamp, Minix box, router, mug, monitor, keyboard."""
    cv = Canvas(W, H)
    # desk lamp
    cv.rect(36, DESK_Y - 4, 18, 4, METAL)
    cv.hline(36, 53, DESK_Y - 4, METAL_L)
    cv.line(45, DESK_Y - 4, 56, 96, METAL)
    cv.line(46, DESK_Y - 4, 57, 96, METAL)
    cv.disc(56, 96, 2, METAL_L)
    cv.line(56, 96, 72, 102, METAL)
    cv.line(56, 97, 72, 103, METAL)
    for y in range(98, 110):
        half = 3 + (y - 98) * 0.75
        for x in range(int(76 - half), int(76 + half) + 1):
            cv.set(x, y, LAMP_SHADE_D if x < 76 - half + 2 else LAMP_SHADE)
    cv.hline(68, 85, 110, (255, 236, 170))
    lamp_light(lights)

    # Minix box: dark case, lighter top, MINIX on the front, two USB ports, power button
    bx, by, bw, bh = 104, 113, 54, 15
    cv.rect(bx + 1, by, bw - 2, bh, CASE)
    cv.rect(bx, by + 1, bw, bh - 2, CASE)
    cv.rect(bx + 1, by, bw - 2, 3, CASE_L)
    cv.hline(bx + 1, bx + bw - 2, by + bh - 3, METAL_D)
    text3x5(cv, bx + 5, by + 6, "MINIX", (156, 158, 168))
    for ux in (bx + 28, bx + 35):
        cv.rect(ux, by + 7, 5, 3, (20, 20, 24))
        cv.hline(ux + 1, ux + 3, by + 8, (120, 124, 140))
    cv.disc(bx + 47, by + 8, 2, METAL_D)
    for fx in (bx + 3, bx + bw - 6):
        cv.rect(fx, by + bh, 3, 1, (20, 20, 24))
    glow(lights, bx + 47, by + 8, 10, BLUE_LED, 0.45)

    # ethernet cable to the router
    wire(cv, bx + bw, by + 10, 200, DESK_Y - 4, 4, (60, 110, 200))

    # wifi router with two antennas
    rx, ry = 198, 112
    cv.rect(rx, ry, 38, 16, ROUTER)
    cv.hline(rx, rx + 37, ry, (246, 246, 240))
    cv.rect(rx + 2, ry + 9, 34, 5, ROUTER_D)
    for ax, tilt in ((rx + 4, -5), (rx + 33, 5)):
        cv.line(ax, ry, ax + tilt, ry - 18, METAL)
        cv.line(ax + 1, ry, ax + tilt + 1, ry - 18, METAL_L)
    glow(lights, rx + 18, ry + 11, 14, GREEN_LED, 0.35)

    # mug
    mx, my = 170, 117
    cv.rect(mx, my, 9, 11, (200, 60, 56))
    cv.hline(mx, mx + 8, my, (230, 90, 80))
    cv.rect(mx + 1, my + 1, 7, 1, (70, 40, 30))
    cv.disc(mx + 10, my + 5, 2.5, (200, 60, 56))
    cv.disc(mx + 10, my + 5, 1, (0, 0, 0, 0))

    # monitor on a stand
    sx, sy = 256, 84
    cv.rect(sx, sy, 64, 36, METAL_D)
    cv.hline(sx, sx + 63, sy, METAL)
    cv.rect(sx + 4, sy + 4, 56, 28, SCREEN)
    cv.rect(sx + 26, sy + 36, 12, 5, METAL)
    cv.rect(sx + 20, DESK_Y - 3, 24, 3, METAL)
    cv.hline(sx + 20, sx + 43, DESK_Y - 3, METAL_L)
    cv.rect(sx + 50, sy - 3, 9, 8, (250, 230, 110))   # sticky note
    cv.hline(sx + 51, sx + 57, sy + 1, (180, 160, 70))
    cv.hline(sx + 51, sx + 55, sy + 3, (180, 160, 70))
    glow(lights, sx + 32, sy + 18, 44, (130, 220, 255), 0.5, ry=30)

    # keyboard
    kx = 252
    cv.rect(kx, DESK_Y - 2, 58, 3, (70, 72, 80))
    for i in range(0, 56, 3):
        cv.set(kx + 1 + i, DESK_Y - 2, (130, 134, 146))
    return cv


def sky(kind):
    cv = Canvas(W, H)
    top, bot = {"night": ((10, 12, 40), (52, 40, 96)),
                "dawn": ((70, 70, 150), (255, 168, 120)),
                "day": ((96, 170, 236), (196, 228, 250))}[kind]
    for y in range(H):
        c = lerp(top, bot, clamp01((y - GLASS[1]) / (GLASS[3] - GLASS[1])))
        for x in range(W):
            cv.set(x, y, c)
    if kind == "night":
        srng = random.Random(11)
        for _ in range(40):
            x, y = srng.randrange(GLASS[0], GLASS[2]), srng.randrange(GLASS[1], GLASS[1] + 40)
            cv.set(x, y, (255, 255, 255) if srng.random() < 0.3 else (180, 180, 230))
    if kind == "dawn":
        for y in range(50, GLASS[3] + 1):
            for x in range(W):
                cv.blend(x, y, (255, 200, 140), (y - 50) / 60)
    return cv


def night_shade(*light_layers):
    """Dark blue veil over the whole scene, thinner where lights shine."""
    cv = Canvas(W, H)
    for y in range(H):
        for x in range(W):
            l = max(layer.get(x, y)[3] for layer in light_layers) / 255
            a = int(255 * 0.66 * (1 - 0.85 * l))
            cv.p[y * W + x] = (12, 14, 46, a)
    return cv


def sun():
    cv = Canvas(13, 13)
    cv.disc(6, 6, 5.5, (255, 220, 120))
    cv.disc(6, 6, 4, (255, 244, 180))
    return cv


def moon():
    cv = Canvas(11, 11)
    cv.disc(5, 5, 4.5, (240, 236, 210))
    cv.set(3, 4, (210, 206, 186))
    cv.set(5, 7, (210, 206, 186))
    cv.disc(8, 3, 3, (0, 0, 0, 0))
    return cv


# moon and sun paths through the window (same formulas in homelab.script.in)
def moon_pos(t):
    m = clamp01(t / 0.45)
    return 222 + m * 72, 24 + m * 62


def sun_pos(t):
    s = clamp01((t - 0.3) / 0.7)
    return 204 + s * 64, 86 - math.sin(s * 1.9) * 60


def hud_panel(w, h):
    cv = Canvas(w, h)
    for y in range(h):
        for x in range(w):
            if (x in (0, w - 1)) and (y in (0, h - 1)):
                continue
            edge = x in (0, w - 1) or y in (0, h - 1)
            cv.set(x, y, (250, 240, 220, 255) if edge else (24, 22, 36, 215))
    return cv


def label(text, color):
    cv = Canvas(text_width(text, 2) + 2, 12)
    text3x5(cv, 1, 1, text, color, k=2)
    return cv


# ---------------------------------------------------------------- objects for the script
#
# idle:   (name, frames, x, y, z, ticks per frame)       cycling in place
# walker: (name, frames, x, y, z, speed px/tick, ticks per frame, day_only)
#         walks across and wraps around; speed < 0 walks left.
# (x, y) is the sprite's bottom-left in logical pixels. z > 101 is above the night shade (it glows).

def objects():
    idle, walk = [], []
    idle.append(("cat", [cat_sleep(f) for f in (0, 1)], 113, 114, 32, 40))
    idle.append(("power", [led(BLUE_LED, True), led(BLUE_LED, True), led(BLUE_LED, False)],
                 150, 123, 110, 60))
    idle.append(("activity", [led(AMBER_LED, f) for f in (1, 0, 1, 1, 0, 0, 1, 0)], 141, 117, 110, 5))
    patterns = [(1, 1, 0, 1), (1, 0, 1, 1), (1, 1, 1, 0), (1, 0, 1, 1), (1, 1, 0, 0), (1, 1, 1, 1)]
    idle.append(("router", [leds([GREEN_LED] * 3 + [BLUE_LED], p) for p in patterns], 203, 125, 110, 7))
    idle.append(("term", [terminal(f) for f in range(len(TERM_LINES) * 2)], 260, 116, 110, 30))
    idle.append(("steam", [steam(f) for f in range(5)], 168, 117, 33, 6))
    walk.append(("vacuum", [vacuum(f) for f in (0, 1)], 120, H - 4, 40, 0.18, 30, 0))
    walk.append(("cloud1", [cloud(1)], 200, 40, 4, 0.03, 1000, 1))
    walk.append(("cloud2", [cloud(2)], 300, 54, 4, 0.02, 1000, 1))
    walk.append(("birds", [birds(f) for f in (0, 1)], 150, 46, 5, 0.25, 8, 1))
    return idle, walk


# ---------------------------------------------------------------- output

def write_script(out, idle, walk):
    lines = []
    for i, (name, frames, x, y, z, period) in enumerate(idle):
        for k in range(len(frames)):
            lines.append(f'idle[{i}].frames[{k}] = load("{name}-{k}.png");')
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
    template = open(os.path.join(HERE, "homelab.script.in")).read()
    with open(os.path.join(out, "homelab.script"), "w") as f:
        f.write(template.replace("@OBJECTS@", "\n".join(lines)).replace("@W@", str(W)))


LABELS = {"boot": ("BOOTING", (255, 214, 110)), "shutdown": ("SHUTTING DOWN", (255, 140, 170)),
          "reboot": ("REBOOTING", (140, 220, 255))}


def progress_bar():
    bar = Canvas(122, 5)
    for x in range(122):
        bar.set(x, 0, (250, 240, 220))
        bar.set(x, 4, (250, 240, 220))
    for y in range(5):
        bar.set(0, y, (250, 240, 220))
        bar.set(121, y, (250, 240, 220))
    return bar


def main():
    args = sys.argv[1:]
    preview = None
    if "--preview" in args:
        preview = args[args.index("--preview") + 1]
        del args[args.index("--preview"):args.index("--preview") + 2]
    out = args[0] if args else "."
    os.makedirs(out, exist_ok=True)
    rng = random.Random(2026)

    layers = {f"sky-{kind}": sky(kind) for kind in ("night", "dawn", "day")}
    bg, bg_lights = background(rng)
    desk_lights = Canvas(W, H)
    mid = desk_items(desk_lights)
    lights = Canvas(W, H)
    lights.paste(bg_lights, 0, 0)
    lights.paste(desk_lights, 0, 0)
    layers.update(bg=bg, mid=mid, night=night_shade(bg_lights, desk_lights), lights=lights)
    for name, cv in layers.items():
        cv.save(f"{out}/{name}.png")
    sun().save(f"{out}/sun.png")
    moon().save(f"{out}/moon.png")

    idle, walk = objects()
    for name, frames, *_ in idle + walk:
        for k, fr in enumerate(frames):
            fr.save(f"{out}/{name}-{k}.png")

    for mode, (text, color) in LABELS.items():
        label(text, color).save(f"{out}/label-{mode}.png")
    hud_panel(150, 22).save(f"{out}/hud.png")
    progress_bar().save(f"{out}/bar.png")
    Canvas(1, 3, (255, 190, 90, 255)).save(f"{out}/bar-fill.png")
    write_script(out, idle, walk)

    if preview:
        render_previews(preview, layers, idle, walk)


# ---------------------------------------------------------------- preview (no plymouth needed)

def over(dst, src, x0=0, y0=0, opacity=1.0):
    for j in range(src.h):
        y = y0 + j
        if not 0 <= y < H:
            continue
        for i in range(src.w):
            x = x0 + i
            if not 0 <= x < W:
                continue
            c = src.p[j * src.w + i]
            a = c[3] / 255 * opacity
            if a <= 0:
                continue
            o = dst.p[y * W + x]
            dst.p[y * W + x] = tuple(int(o[k] + (c[k] - o[k]) * a) for k in range(3)) + (255,)


def compose(layers, idle, walk, tod, tick, mode):
    """One frame, composited in the same z order and with the same fades as homelab.script."""
    cv = Canvas(W, H, (0, 0, 0, 255))
    over(cv, layers["sky-day"])
    over(cv, layers["sky-dawn"], opacity=1 if tod < 0.4 else clamp01(1 - (tod - 0.4) / 0.4))
    over(cv, layers["sky-night"], opacity=clamp01(1 - tod / 0.4))
    mx, my = moon_pos(tod)
    over(cv, moon(), int(mx), int(my))
    sx, sy = sun_pos(tod)
    over(cv, sun(), int(sx), int(sy))

    items = [(10, layers["bg"], 0, 0, 1), (30, layers["mid"], 0, 0, 1),
             (100, layers["night"], 0, 0, clamp01(1 - tod / 0.55)),
             (101, layers["lights"], 0, 0, clamp01(1 - tod / 0.45))]
    for name, frames, x, y, z, period in idle:
        items.append((z, frames[(tick // period) % len(frames)], x, y - frames[0].h, 1))
    for name, frames, x, y, z, speed, period, day in walk:
        span = W + 2 + frames[0].w
        px = (x + frames[0].w + speed * tick) % span - frames[0].w
        op = clamp01((tod - 0.4) / 0.4) if day else 1
        items.append((z, frames[(tick // period) % len(frames)], int(px), y - frames[0].h, op))
    for z, img, x, y, op in sorted(items, key=lambda i: i[0]):
        over(cv, img, x, y, op)

    text, color = LABELS[mode]
    lab = label(text, color)
    over(cv, hud_panel(150, 22), (W - 150) // 2, 166)
    over(cv, lab, (W - lab.w) // 2, 168)
    over(cv, progress_bar(), (W - 122) // 2, 181)
    fill = tod if mode == "boot" else 1 - tod
    over(cv, Canvas(max(1, int(120 * fill)), 3, (255, 190, 90, 255)), (W - 122) // 2 + 1, 182)
    return cv


def render_previews(out, layers, idle, walk):
    os.makedirs(out, exist_ok=True)
    for tod, name in ((0, "night"), (0.45, "dawn"), (1, "day")):
        compose(layers, idle, walk, tod, 0, "boot").save(os.path.join(out, f"still-{name}.png"), scale=3)
    for mode, forward in (("boot", True), ("shutdown", False)):
        paths = []
        n = 72
        for i in range(n):
            tod = i / (n - 1) if forward else 1 - i / (n - 1)
            p = os.path.join(out, f"{mode}-{i:03d}.png")
            compose(layers, idle, walk, tod, i * 6, mode).save(p, scale=2)
            paths.append(p)
            print(f"{mode} {i + 1}/{n}", end="\r", flush=True)
        print()
        subprocess.run(["magick", "-delay", "12", "-loop", "0", *paths, os.path.join(out, f"{mode}.gif")],
                       check=True)
        for p in paths:
            os.remove(p)


if __name__ == "__main__":
    main()
