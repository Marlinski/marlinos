#!/usr/bin/env python3
"""Office: pixel-art plymouth theme for marlinos.

A cozy study seen three-quarters: a big window with plants on the sill and a hanging pot,
fairy lights, a shelf, the X230 open on the desk, a cup of tea, a desk lamp, and a half-turned
chair with a plaid where the cat sleeps. Boot goes night -> day: the sun rises in the window,
rays and dust drift across the room while the lamp dims; shutdown/reboot go day -> night (sun
sets, moon rises, the lamp and the fairy lights come on). Everything the system says (boot log,
progress, the disk passphrase) appears on the X230's own screen in the scene.

Same canvas as the hutong theme (342x192 logical pixels, written x4) and the same toolkit,
loaded from ../hutong/make.py.

Usage: make.py OUTDIR [--preview DIR]
  OUTDIR    theme directory (marlinos: hosts/x230/system/usr/share/plymouth/themes/office)
  --preview also write stills and boot/shutdown GIFs composited like the script does
"""
import importlib.util
import math
import os
import random
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
_spec = importlib.util.spec_from_file_location("hutong", os.path.join(HERE, "..", "hutong", "make.py"))
T = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(T)
Canvas, lerp, cjk = T.Canvas, T.lerp, T.cjk
W, H, OUTLINE = T.W, T.H, T.OUTLINE

# ---------------------------------------------------------------- layout (logical pixels)
GLASS = (28, 10, 132, 80)             # window glass x0, y0, x1, y1 (exclusive)
SILL_Y = 80
SIDE_X = 16                           # corner between the left wall and the back wall
FLOOR_Y = 132                         # back wall meets the floor (mostly behind the desk)
DESK_BACK, DESK_FRONT = 96, 150       # desk top, back and front edges
LID = (145, 22, 263, 104)             # X230 lid outer box
SX, SY, SW, SH = 151, 28, 106, 66     # X230 screen (everything the system says goes here)
DECK_TOP, DECK_BOT = 106, 144         # keyboard deck, in perspective
LAMP_POOL = (280, 130)                # centre of the lamp's light on the desk
RIM = ((284, 80), (304, 90))          # lamp shade rim
RAY_DX, RAY_Y = 0.55, 45              # sun rays: x shift per pixel down, reference row
SUN_PATH = (30, 44, 80, 64)           # x0, dx, y0, dy (sun climbs from the lower left of the glass)
MOON_PATH = (62, 48, 12, 64)          # x0, dx, y0, dy (moon sinks to the lower right)

# ---------------------------------------------------------------- palette
WALL_L, WALL, WALL_F = (250, 232, 200), (238, 214, 180), (206, 174, 142)
SIDE, SIDE_D = (208, 172, 138), (176, 140, 110)
FRAME, FRAME_D = (248, 242, 228), (204, 192, 172)
WOOD, WOOD_L, WOOD_D = (150, 100, 62), (180, 128, 82), (106, 68, 42)
DESK, DESK_L, DESK_D, DESK_E = (178, 120, 74), (200, 144, 94), (148, 96, 58), (112, 72, 44)
FLOOR, FLOOR_D = (140, 92, 60), (112, 72, 46)
CURTAIN, CURTAIN_L, CURTAIN_D = (206, 126, 98), (228, 154, 122), (166, 94, 74)
LEAF, LEAF_L, LEAF_D = (84, 150, 86), (122, 186, 104), (52, 108, 70)
POT, POT_L = (196, 108, 72), (222, 136, 96)
PAD, PAD_D, KEY, KEY_L = (44, 44, 50), (28, 28, 32), (20, 20, 24), (70, 70, 80)
BEZEL, SCREEN_BG = (32, 32, 36), (12, 16, 24)
TP_RED = (226, 40, 40)
CAT, CAT_L, CAT_D, CAT_W, CAT_P = (236, 152, 74), (250, 184, 110), (196, 110, 48), (252, 246, 236), (246, 156, 170)
LAMP, LAMP_L, LAMP_D = (66, 124, 120), (104, 164, 152), (40, 86, 86)
PLAID_R, PLAID_G, PLAID_C = (182, 58, 54), (54, 86, 66), (238, 216, 172)
PORCELAIN, BLUE = (244, 242, 236), (52, 84, 168)
GREEN_OK, LOG_TXT, AMBER = (110, 220, 120), (176, 186, 200), (255, 196, 96)
NIGHT_TINT = (16, 16, 44)
SUNLIGHT = (255, 236, 186)
BULB_COLORS = [(255, 196, 96), (255, 146, 146), (252, 238, 204), (150, 222, 186)]

# 3x5 font: the hutong set plus what the boot log needs
FONT = dict(T.FONT3x5)
FONT.update({
    "[": "##.#..#..#..##.", "]": "##..#..#..#.##.", "V": "#.##.##.##.#.#.", "X": "#.##.#.#.#.##.#",
    "J": "..#..#..##.#.#.", "Q": ".#.#.##.##.#..#", "Z": "###..#.#.#..###", "3": "##...#.#...###.",
    "5": "####..##...###.", "6": ".###..##.#.#.#.", "7": "###..#..#.#..#.", "8": ".#.#.#.#.#.#.#.",
    "9": ".#.#.#.##..###.",
})


def text(cv, x, y, s, c, k=1):
    for ch in s:
        g = FONT.get(ch, FONT[" "])
        for i, v in enumerate(g):
            if v == "#":
                cv.rect(x + i % 3 * k, y + i // 3 * k, k, k, c)
        x += 4 * k
    return x


def clamp01(v):
    return max(0.0, min(1.0, v))


def mul(c, k):
    return tuple(max(0, min(255, int(v * k))) for v in c[:3])


def in_glass(x, y):
    return GLASS[0] <= x < GLASS[2] and GLASS[1] <= y < GLASS[3]


def in_screen(x, y):
    return SX <= x < SX + SW and SY <= y < SY + SH


def poly(cv, pts, c, a=None):
    """Fill a polygon (even-odd scanlines); a: blend instead of paint."""
    ys = [p[1] for p in pts]
    for y in range(int(min(ys)), int(max(ys)) + 1):
        yc = y + 0.5
        xs = sorted(x0 + (yc - y0) * (x1 - x0) / (y1 - y0)
                    for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])
                    if (y0 <= yc < y1) or (y1 <= yc < y0))
        for xa, xb in zip(xs[::2], xs[1::2]):
            for x in range(int(round(xa)), int(round(xb))):
                if callable(c):
                    cv.set(x, y, c(x, y))
                elif a is None:
                    cv.set(x, y, c)
                else:
                    cv.blend(x, y, c, a)


def line(cv, x0, y0, x1, y1, c, w=1):
    n = int(max(abs(x1 - x0), abs(y1 - y0))) + 1
    for i in range(n + 1):
        t = i / n
        x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        cv.rect(round(x - w / 2 + 0.5), round(y - w / 2 + 0.5), w, w, c)


def outline(cv, c=OUTLINE):
    """1px dark outline around the opaque pixels (like hutong's sprite())."""
    solid = [[cv.get(x, y)[3] == 255 for x in range(cv.w)] for y in range(cv.h)]
    for y in range(cv.h):
        for x in range(cv.w):
            if not solid[y][x] and any(0 <= x + dx < cv.w and 0 <= y + dy < cv.h and solid[y + dy][x + dx]
                                       for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))):
                cv.set(x, y, c)
    return cv


def shadow(cv, cx, cy, rx, ry, a=0.28):
    """Soft contact shadow on the desk, offset away from the window."""
    for y in range(int(cy - ry) - 1, int(cy + ry) + 2):
        for x in range(int(cx - rx) - 1, int(cx + rx) + 2):
            d = ((x - cx) / rx) ** 2 + ((y - cy) / ry) ** 2
            if d <= 1:
                cv.blend(x, y, (40, 20, 14), a * (1 - d * 0.5))


def leaf(cv, x, y, c=LEAF, hi=LEAF_L, flip=False):
    """3x2 heart-ish leaf."""
    s = -1 if flip else 1
    cv.set(x, y, c)
    cv.set(x + s, y, hi)
    cv.set(x, y + 1, c)
    cv.set(x + s, y + 1, c)
    cv.set(x + 2 * s, y + 1, LEAF_D)


# ---------------------------------------------------------------- outside the window

def outside():
    """Hills, rooftops and a tree seen through the window (clipped to the glass)."""
    cv = Canvas(W, H)
    lit = []
    rng = random.Random(7)
    for x in range(GLASS[0], GLASS[2]):                       # far hills
        top = int(56 + 4 * math.sin(x * 0.07) + 3 * math.sin(x * 0.17 + 1))
        for y in range(top, GLASS[3]):
            cv.set(x, y, lerp((128, 152, 176), (104, 132, 150), (y - top) / 20))
    for x0, x1, top in ((22, 66, 64), (58, 104, 60), (98, 136, 67)):   # roofs with upturned eaves
        for y in range(top, GLASS[3]):
            inset = max(0, 4 - (y - top))
            for x in range(x0 + inset, x1 - inset):
                if in_glass(x, y):
                    c = (84, 88, 108) if y < top + 5 else (196, 184, 166)
                    if y == top + 5:
                        c = (120, 112, 104)
                    if y >= top + 8 and (x - x0) % 9 in (3, 4, 5) and y < top + 11:
                        c = (70, 66, 70)
                        lit.append((x, y))
                    cv.set(x, y, c)
    for y in range(52, GLASS[3]):                              # tree on the right
        cv.rect(120, y, 2, 1, (90, 62, 44))
    for cx, cy, r in ((121, 46, 11), (112, 52, 7), (129, 52, 7), (121, 37, 7)):
        for y in range(cy - r, cy + r + 1):
            for x in range(cx - r, cx + r + 1):
                d = math.hypot(x - cx, (y - cy) * 1.1)
                if d <= r - (1 if (x * 3 + y * 5) % 7 == 0 else 0) and in_glass(x, y):
                    up = (y - cy) < -r * 0.3 or (x - cx) < -r * 0.4
                    cv.set(x, y, (96, 158, 88) if up and rng.random() < 0.7 else (60, 118, 70))
    return cv, lit


def cloud(seed):
    rng = random.Random(seed)
    cv = Canvas(30, 11)
    for _ in range(6):
        cv.disc(rng.uniform(7, 23), rng.uniform(5, 7), rng.uniform(3, 5), (255, 255, 255))
    for x in range(30):
        for y in range(11):
            if cv.get(x, y)[3] and cv.get(x, y + 2)[3] == 0:
                cv.set(x, y, (226, 232, 246))
    return cv


# ---------------------------------------------------------------- the room

def floor_and_walls(cv):
    for y in range(FLOOR_Y, H):                                # floor planks
        for x in range(W):
            c = FLOOR_D if (y - FLOOR_Y) in (3, 8, 15, 24, 35, 48) else FLOOR
            cv.set(x, y, c)
    for y in range(FLOOR_Y):                                   # back wall, lit from the window
        for x in range(SIDE_X, W):
            d = clamp01(math.hypot((x - 80) / 1.5, y - 45) / 190)
            c = lerp(WALL_L, WALL, min(1, d * 2)) if d < 0.5 else lerp(WALL, WALL_F, (d - 0.5) * 2)
            if (x + (y // 10) % 2 * 5) % 10 == 0 and y % 10 == 5:
                c = mul(c, 0.93)                               # tiny flower dots of the wallpaper
            if y > 86:
                c = mul(c, 1 - (y - 86) / 200)
            cv.set(x, y, c)
    poly(cv, [(0, 0), (SIDE_X, 0), (SIDE_X, FLOOR_Y), (0, FLOOR_Y + 16)],
         lambda x, y: lerp(SIDE, SIDE_D, y / 150))
    cv.vline(SIDE_X, 0, FLOOR_Y, SIDE_D)
    for x in range(SIDE_X, W):                                 # little crown moulding
        cv.set(x, 0, FRAME)
        cv.set(x, 1, FRAME_D)


def window(cv):
    x0, y0, x1, y1 = GLASS
    for y in range(y0, y1):                                    # glass: transparent, the sky shows through
        for x in range(x0, x1):
            cv.set(x, y, (0, 0, 0, 0))
    for i in range(5):                                         # faint reflections
        for k in range(12):
            cv.set(x0 + 10 + i * 20 + k, y0 + 26 - k + (i % 2) * 18, (255, 255, 255, 30))
            cv.set(x0 + 12 + i * 20 + k, y0 + 26 - k + (i % 2) * 18, (255, 255, 255, 18))
    f = 4
    cv.rect(x0 - f, y0 - f, x1 - x0 + 2 * f, f, FRAME)
    cv.rect(x0 - f, y0, f, y1 - y0, FRAME)
    cv.rect(x1, y0, f, y1 - y0, FRAME)
    cv.rect((x0 + x1) // 2 - 1, y0, 3, y1 - y0, FRAME)        # mullion and transom
    cv.rect(x0, (y0 + y1) // 2 - 1, x1 - x0, 3, FRAME)
    cv.vline(x1 + f - 1, y0 - f, y1, FRAME_D)
    cv.hline(x0 - f, x1 + f - 1, y0 - f, (255, 252, 244))
    cv.vline((x0 + x1) // 2 + 1, y0, y1 - 1, FRAME_D)
    cv.hline(x0, x1 - 1, (y0 + y1) // 2 + 1, FRAME_D)
    cv.rect(x0 - 8, SILL_Y, x1 - x0 + 16, 4, FRAME)            # sill, front face, shadow under it
    cv.rect(x0 - 8, SILL_Y + 4, x1 - x0 + 16, 3, FRAME_D)
    for x in range(x0 - 8, x1 + 8):
        cv.blend(x, SILL_Y + 7, (60, 30, 20), 0.25)
        cv.blend(x, SILL_Y + 8, (60, 30, 20), 0.12)
    sill_plants(cv)
    line(cv, 8, 4, 150, 4, WOOD_D, 2)                          # curtain rod and finials
    cv.disc(8, 4, 2.5, WOOD)
    cv.disc(150, 4, 2.5, WOOD)
    curtain(cv, 12, 20, 1)
    curtain(cv, 146, 20, -1)


def curtain(cv, x_wall, width, side):
    """A curtain gathered by a tie-back; side 1: hangs right of x_wall, -1: left of it."""
    layer = Canvas(W, H)
    for y in range(6, 96):
        if y < 60:
            w = width - (width - 9) * (y - 6) / 54 * 0.9
        elif y < 66:
            w = 9
        else:
            w = 9 + (y - 66) * 0.28
        for i in range(int(w)):
            fold = int(i * 4 / max(w, 1) * 2) % 4
            c = (CURTAIN_L, CURTAIN, CURTAIN, CURTAIN_D)[fold]
            if 60 <= y < 66:
                c = mul(c, 0.85)
            layer.set(x_wall + side * i if side > 0 else x_wall - i - 1, y, c)
    for k in range(4):                                         # rings on the rod
        layer.set(x_wall + side * (2 + k * 5), 5, WOOD_D)
    tie = x_wall + side * 4 if side > 0 else x_wall - 10
    layer.rect(tie, 62, 7, 2, (240, 210, 150))
    cv.paste(outline(layer), 0, 0)


def sill_plants(cv):
    layer = Canvas(W, H)
    # snake plant on the right of the sill: pointed blades, banded, yellow edged
    for x, top, c in ((110, 58, LEAF_D), (114, 50, LEAF), (118, 54, LEAF_D), (121, 60, LEAF), (116, 62, LEAF_L)):
        for y in range(top, 74):
            half = 0 if y < top + 2 else (1 if y < top + 6 else 2)
            band = mul(c, 0.8) if (y + x) % 4 == 0 else c
            layer.hline(x - half, x + half, y, band)
            if half:
                layer.set(x + half, y, (206, 214, 110))
    poly(layer, [(107, 72), (125, 72), (123, 80), (109, 80)], POT)
    layer.hline(107, 124, 72, POT_L)
    # round succulent and a little cactus on the left
    poly(layer, [(42, 74), (54, 74), (53, 80), (43, 80)], (236, 230, 216))
    layer.hline(43, 53, 77, (120, 160, 190))
    for r, c in ((6, LEAF_D), (4.5, LEAF), (2.5, LEAF_L)):
        layer.disc(48, 72, r, c, ry=r * 0.55)
    layer.rect(62, 66, 4, 9, (96, 160, 96))
    layer.rect(60, 69, 2, 3, (96, 160, 96))
    layer.set(64, 65, (250, 150, 170))
    for y in (67, 70, 73):
        layer.set(63, y, (210, 236, 190))
    layer.rect(60, 75, 8, 5, POT)
    cv.paste(outline(layer), 0, 0)


GARLAND_PINS = [(150, 6), (202, 8), (254, 5), (302, 8), (342, 6)]


def garland_bulbs():
    bulbs = []
    for (ax, ay), (bx, by) in zip(GARLAND_PINS, GARLAND_PINS[1:]):
        for x in range(ax + 4, bx, 8):
            t = (x - ax) / (bx - ax)
            bulbs.append((x, int(ay + (by - ay) * t + 8 * 4 * t * (1 - t)) + 2))
    return bulbs


def garland(cv):
    for (ax, ay), (bx, by) in zip(GARLAND_PINS, GARLAND_PINS[1:]):
        for x in range(ax, bx + 1):
            t = (x - ax) / (bx - ax)
            cv.set(x, int(ay + (by - ay) * t + 8 * 4 * t * (1 - t)), (96, 76, 62))
        cv.rect(ax - 1, ay - 1, 2, 2, (120, 100, 90))
    for i, (x, y) in enumerate(garland_bulbs()):
        c = BULB_COLORS[i % 4]
        cv.set(x, y - 1, (90, 80, 70))
        cv.rect(x, y, 2, 2, mul(c, 0.86))
        cv.set(x, y, mul(c, 1.0))


def shelf(cv):
    layer = Canvas(W, H)
    layer.rect(268, 38, 72, 2, WOOD_L)
    layer.rect(268, 40, 72, 2, WOOD)
    for bx in (276, 328):
        poly(layer, [(bx, 42), (bx + 3, 42), (bx, 47)], WOOD_D)
    x = 272
    for w, h, c in ((4, 14, (126, 74, 96)), (3, 11, (74, 112, 136)), (5, 15, (210, 174, 104)),
                    (4, 12, (96, 136, 96)), (3, 13, (176, 94, 74))):
        layer.rect(x, 38 - h, w, h, c)
        layer.hline(x, x + w - 1, 38 - h + 2, mul(c, 1.25))
        layer.hline(x, x + w - 1, 38 - 4, mul(c, 1.25))
        x += w
    poly(layer, [(x, 38), (x + 3, 38), (x + 10, 26), (x + 7, 25)], (220, 200, 150))   # a leaning book
    layer.rect(296, 28, 11, 10, WOOD_D)                       # little framed photo
    layer.rect(297, 29, 9, 8, (250, 230, 200))
    layer.rect(297, 33, 9, 4, (150, 190, 210))
    layer.disc(301, 31, 1.2, (240, 140, 90))
    poly(layer, [(312, 30), (326, 30), (324, 38), (314, 38)], POT)   # pot for the trailing pothos
    layer.hline(312, 325, 30, POT_L)
    for lx, ly in ((313, 27), (317, 25), (321, 26), (324, 28), (315, 29), (320, 28)):
        leaf(layer, lx, ly, flip=lx > 319)
    cv.paste(outline(layer), 0, 0)


def desk(cv):
    for y in range(DESK_FRONT + 10, H):                        # under the desk: in shadow
        for x in range(8, W):
            cv.blend(x, y, (30, 18, 16), 0.62 - (y - DESK_FRONT) / 160)
    poly(cv, [(SIDE_X + 2, DESK_BACK), (SIDE_X + 2, DESK_BACK + 10), (2, DESK_FRONT + 10), (2, DESK_FRONT)],
         DESK_D)                                                # left end of the desk
    cv.rect(SIDE_X - 1, DESK_BACK + 10, 4, FLOOR_Y - DESK_BACK - 10, DESK_E)   # back leg
    cv.rect(2, DESK_FRONT + 10, 6, H, DESK_E)                   # front leg
    cv.vline(3, DESK_FRONT + 10, H, DESK_D)

    planks = [DESK_BACK + d for d in (7, 15, 24, 34, 45)]

    def top(x, y):
        c = DESK_D if y in planks else (DESK_L if y - 1 in planks else DESK)
        if (x * 7 + y * 13) % 41 == 0 or (x * 3 + y * 5) % 67 == 0:
            c = mul(c, 0.92)
        return mul(c, 1 - (DESK_FRONT - y) / 400 - max(0, x - 200) / 1400)
    poly(cv, [(SIDE_X + 2, DESK_BACK), (W, DESK_BACK), (W, DESK_FRONT), (2, DESK_FRONT)], top)
    cv.hline(SIDE_X + 2, W - 1, DESK_BACK, DESK_D)
    cv.hline(2, W - 1, DESK_FRONT, (214, 160, 108))             # rounded front edge catching light
    cv.rect(2, DESK_FRONT + 1, W, 9, DESK_E)                    # apron with a drawer
    cv.hline(2, W - 1, DESK_FRONT + 1, DESK_D)
    cv.hline(2, W - 1, DESK_FRONT + 10, (60, 36, 24))
    cv.rect(286, DESK_FRONT + 3, 52, 6, mul(DESK_E, 1.12))
    cv.hline(286, 337, DESK_FRONT + 8, mul(DESK_E, 0.8))
    cv.rect(310, DESK_FRONT + 5, 3, 2, (226, 190, 110))


def pencil_cup(cv):
    layer = Canvas(W, H)
    for (ax, ay), (bx, by), c in (((86, 100), (83, 88), (240, 200, 70)), ((90, 100), (92, 86), (90, 140, 210)),
                                  ((88, 100), (88, 90), (220, 80, 80))):
        line(layer, ax, ay, bx, by, c)
        layer.set(bx, by, (250, 170, 180) if c[0] == 240 else (60, 50, 50))
    layer.rect(83, 99, 10, 13, (236, 230, 216))
    layer.hline(83, 92, 103, LEAF)
    layer.hline(83, 92, 104, LEAF_D)
    layer.vline(83, 99, 111, (210, 202, 186))
    shadow(cv, 91, 112, 8, 2)
    cv.paste(outline(layer), 0, 0)


def notebook(cv):
    layer = Canvas(W, H)
    poly(layer, [(90, 133), (128, 131), (131, 146), (92, 148)], (250, 244, 228))
    line(layer, 109, 132, 111, 147, (210, 196, 170))
    for k in range(4):
        y0 = 136 + k * 3
        line(layer, 94, y0 + 0.3, 107, y0 - 0.3, (196, 206, 226))
        line(layer, 113, y0 - 0.4, 127, y0 - 1, (196, 206, 226))
    shadow(cv, 114, 148, 22, 2, 0.2)
    cv.paste(outline(layer), 0, 0)
    line(cv, 116, 143, 132, 134, (60, 70, 120), 2)              # pen
    cv.set(132, 134, (230, 200, 90))


def deck_edges(y):
    t = (y - DECK_TOP) / (DECK_BOT - DECK_TOP)
    return LID[0] - 12 * t, LID[2] + 12 * t


KEY_ROWS = [  # unit widths, 16 per row, ThinkPad-ish
    [1] * 16,
    [1] * 14 + [2],
    [1.5] + [1] * 13 + [1.5],
    [1.75] + [1] * 12 + [2.25],
    [2.25] + [1] * 11 + [2.75],
    [1, 1, 1, 1.25, 6.5, 1.25, 1, 1, 1, 1],
]


def laptop(cv):
    x0, y0, x1, y1 = LID
    poly(cv, [(LID[0] + 2, DECK_BOT + 2), (LID[2] + 14, DECK_BOT + 2), (LID[2] + 20, DECK_BOT + 6),
              (LID[0] + 6, DECK_BOT + 6)], (40, 20, 14), 0.3)   # shadow on the desk
    cv.rect(x0, y0, x1 - x0, y1 - y0, BEZEL)
    for x, y in ((x0, y0), (x1 - 1, y0)):
        cv.set(x, y, (0, 0, 0, 0))
    cv.hline(x0 + 1, x1 - 2, y0, (70, 70, 78))
    cv.vline(x0, y0 + 1, y1 - 1, (50, 50, 56))
    cv.rect(SX - 1, SY - 1, SW + 2, SH + 2, (16, 16, 20))
    cv.rect(SX, SY, SW, SH, SCREEN_BG)
    cv.set((x0 + x1) // 2, y0 + 3, (76, 76, 88))               # webcam
    text(cv, SX, SY + SH + 3, "LENOVO", (112, 112, 122))
    sx, sy = x1 - 14, SY + SH + 2                              # a tiny cat sticker on the bezel
    cv.rect(sx, sy + 1, 6, 4, CAT)
    cv.set(sx, sy, CAT)
    cv.set(sx + 5, sy, CAT)
    cv.set(sx + 1, sy + 2, OUTLINE)
    cv.set(sx + 4, sy + 2, OUTLINE)
    cv.set(sx + 2, sy + 3, CAT_P)
    cv.rect(x0 + 3, y1, x1 - x0 - 6, 2, (18, 18, 20))         # hinge
    # keyboard deck: as wide as the lid, opening up towards us
    for y in range(DECK_TOP, DECK_BOT):
        xa, xb = deck_edges(y)
        for x in range(int(xa), int(xb)):
            cv.set(x, y, PAD if y > DECK_TOP else (66, 66, 74))
        cv.set(int(xa), y, (60, 60, 68))
    xa, xb = deck_edges(DECK_BOT)
    cv.rect(int(xa), DECK_BOT, int(xb - xa), 3, PAD_D)
    cx = (x0 + x1) // 2
    for r, units in enumerate(KEY_ROWS):
        ky, kh = (DECK_TOP + 2, 2) if r == 0 else (DECK_TOP + 5 + (r - 1) * 4, 3)
        xa, xb = deck_edges(ky + 1)
        xa, xb = xa + 7, xb - 7
        pitch = (xb - xa) / 16
        u = 0
        for wu in units:
            ka, kb = int(xa + u * pitch), int(xa + (u + wu) * pitch) - 1
            cv.rect(ka, ky, kb - ka, kh, KEY)
            cv.hline(ka, kb - 1, ky, KEY_L)
            u += wu
    cv.rect(cx - 1, DECK_TOP + 15, 2, 2, TP_RED)               # TrackPoint between G, H and B
    by = DECK_TOP + 26                                          # the three buttons, then the touchpad
    for bx in (cx - 18, cx - 5, cx + 7):
        cv.rect(bx, by, 11, 2, (30, 30, 34))
        cv.hline(bx, bx + 10, by, (62, 62, 70))
    cv.vline(cx - 6, by, by + 1, TP_RED)
    cv.vline(cx + 6, by, by + 1, TP_RED)
    cv.rect(cx - 18, by + 4, 36, 8, (52, 52, 58))
    cv.hline(cx - 18, cx + 17, by + 4, (30, 30, 34))
    cv.vline(cx - 18, by + 4, by + 11, (30, 30, 34))
    lx = int(deck_edges(by + 6)[1]) - 40                       # palm rest logo
    text(cv, lx, by + 6, "THINKPAD", (150, 150, 160))
    cv.set(lx + 4 * 2 + 1, by + 5, TP_RED)                      # the dot on the i
    cv.rect(lx + 2, by + 1, 4, 3, (64, 64, 72))                 # fingerprint reader


def cup(cv):
    layer = Canvas(W, H)
    layer.disc(112, 127, 13, (226, 226, 220), ry=3.4)           # saucer
    layer.disc(112, 126, 10, (246, 246, 240), ry=2.2)
    for j in range(15):                                         # mug body, slightly rounded at the bottom
        half = 8 - max(0, j - 11)
        layer.hline(112 - half, 112 + half - 1, 111 + j, PORCELAIN if j > 1 else (226, 224, 216))
    for y in range(114, 122):                                   # handle
        layer.set(121 + (1 if 115 < y < 120 else 0), y, PORCELAIN)
        layer.set(122 + (1 if 115 < y < 120 else 0), y, PORCELAIN)
    layer.hline(104, 119, 115, BLUE)
    layer.hline(104, 119, 116, BLUE)
    for k in range(3):                                          # little blue flowers
        layer.set(107 + k * 4, 119, BLUE)
        layer.set(106 + k * 4, 120, (120, 150, 210))
        layer.set(108 + k * 4, 120, (120, 150, 210))
    layer.vline(105, 112, 123, (216, 216, 208))
    layer.hline(105, 118, 111, (176, 112, 48))                  # tea
    layer.hline(106, 117, 112, (204, 140, 62))
    shadow(cv, 117, 129, 15, 3)
    cv.paste(outline(layer), 0, 0)
    for y in range(116, 120):                                   # hole in the handle
        cv.set(122, y, DESK)


def lamp_and_books(cv):
    layer = Canvas(W, H)
    for (bx0, bx1, by0, by1, c) in ((290, 338, 126, 132, (74, 104, 152)), (293, 336, 121, 126, (214, 172, 92)),
                                    (296, 332, 117, 121, (194, 104, 104))):
        layer.rect(bx0, by0, bx1 - bx0, by1 - by0, c)
        layer.hline(bx0, bx1 - 1, by0, mul(c, 1.2))
        layer.rect(bx1 - 3, by0 + 1, 2, by1 - by0 - 1, (246, 236, 214))   # pages
        layer.vline(bx0 + 4, by0 + 1, by1 - 1, mul(c, 0.75))
    layer.disc(316, 116, 9, LAMP_D, ry=3)                        # base
    layer.disc(316, 115, 8, LAMP, ry=2.4)
    line(layer, 316, 113, 328, 92, LAMP_D, 3)                   # arms
    line(layer, 328, 92, 307, 70, LAMP_D, 3)
    line(layer, 315, 112, 327, 92, LAMP, 1)
    layer.disc(328, 92, 2.5, LAMP_L)
    apex, (ax, ay), (bx, by) = (308, 64), *RIM
    T_ = [(apex[0], apex[1]), (ax, ay), (bx, by)]
    poly(layer, T_, LAMP)
    poly(layer, [apex, ((ax + bx) // 2 + 2, (ay + by) // 2), (bx, by)], LAMP_D)
    line(layer, apex[0] - 2, apex[1] + 2, ax + 4, ay - 1, LAMP_L)
    layer.disc(apex[0], apex[1], 2, LAMP_D)
    shadow(cv, 324, 133, 26, 3)
    cv.paste(outline(layer), 0, 0)
    line(cv, ax, ay, bx, by, (252, 230, 176), 2)                 # rim, the bulb inside


def succulent(cv):
    layer = Canvas(W, H)
    poly(layer, [(318, 136), (334, 136), (332, 147), (320, 147)], (240, 236, 226))
    layer.hline(318, 333, 139, (226, 140, 120))
    for r, c, dy in ((8, LEAF_D, 0), (6, LEAF, -1), (4, LEAF_L, -2), (1.5, (190, 226, 150), -3)):
        layer.disc(326, 134 + dy, r, c, ry=r * 0.5)
    shadow(cv, 330, 147, 10, 2)
    cv.paste(outline(layer), 0, 0)


def plaid(x, y, k=1.0):
    """Red tartan with green and cream stripes."""
    vx, vy = x % 10, (y + x // 3) % 10
    c = PLAID_R
    if vx in (0, 1) or vy in (0, 1):
        c = lerp(PLAID_R, PLAID_G, 0.75 if (vx in (0, 1) and vy in (0, 1)) else 0.55)
    elif vx == 5 or vy == 5:
        c = lerp(PLAID_R, PLAID_C, 0.6)
    return mul(c, k)


def chair(cv):
    """Wooden chair half turned towards us, a plaid over its back and seat."""
    layer = Canvas(W, H)
    for (ax, ay), (bx, by), c in (((30, 162), (28, 192), WOOD_D), ((66, 160), (70, 192), WOOD_D),
                                  ((22, 166), (16, 192), WOOD), ((78, 165), (84, 192), WOOD)):
        line(layer, ax, ay, bx, by, c, 3)
    line(layer, 22, 180, 78, 180, WOOD_D, 2)                     # stretcher
    for y in range(158, 172):                                   # seat: thickness, then the top
        for x in range(14, 88):
            if ((x - 50) / 35) ** 2 + ((y - 162) / 10) ** 2 <= 1:
                layer.set(x, y, WOOD_D)
    layer.disc(50, 158, 35, WOOD_L, ry=10)
    layer.disc(50, 157, 33, (196, 144, 96), ry=8.5)
    line(layer, 20, 158, 13, 112, WOOD, 3)                      # back posts and spindles
    line(layer, 46, 150, 44, 104, WOOD, 3)
    for k in (1, 2, 3):
        t = k / 4
        line(layer, 20 + 26 * t, 158 - 8 * t, 14 + 30 * t, 116 - 8 * t, WOOD_D, 2)
    line(layer, 10, 116, 47, 104, WOOD_L, 4)                    # top rail
    line(layer, 10, 115, 47, 103, (204, 152, 104), 1)
    # the plaid: thrown over the top rail, falling in front, spread on the seat
    poly(layer, [(28, 154), (72, 150), (86, 158), (66, 167), (30, 166), (22, 160)],
         lambda x, y: plaid(x, y, 0.96))
    poly(layer, [(8, 116), (47, 103), (51, 108), (54, 138), (46, 150), (30, 157), (16, 155), (10, 136)],
         lambda x, y: plaid(x, y, 1.0 - max(0, 112 - y + (x - 8) * 0.3) * 0.02 - (0.12 if x < 14 else 0)))
    for x in range(10, 52):                                     # fold shadow along the rail
        for y in range(103, 125):
            if layer.get(x, y)[3] and y < 116 - (x - 8) * 0.31 + 4:
                layer.set(x, y, mul(layer.get(x, y), 0.82))
    for x in range(16, 46, 2):                                  # fringe at the bottom
        yb = int(155 + (x - 16) * -0.25 + (2 if x < 30 else 0))
        layer.vline(x, yb, yb + 2, PLAID_C)
    for x in range(66, 86, 2):
        layer.vline(x, int(167 - (x - 66) * 0.45), int(169 - (x - 66) * 0.45), PLAID_C)
    cv.paste(outline(layer), 0, 0)


def rug(cv):
    for y in range(170, H):
        for x in range(0, 150):
            if ((x - 60) / 92) ** 2 + ((y - 190) / 20) ** 2 <= 1:
                band = (y - 170) % 6
                cv.set(x, y, (232, 214, 182) if band < 4 else (196, 120, 96))


def room():
    cv = Canvas(W, H)
    floor_and_walls(cv)
    window(cv)
    garland(cv)
    shelf(cv)
    desk(cv)
    rug(cv)
    pencil_cup(cv)
    notebook(cv)
    laptop(cv)
    cup(cv)
    lamp_and_books(cv)
    succulent(cv)
    chair(cv)
    for y in range(H):                                          # gentle vignette
        for x in range(W):
            d = math.hypot((x - 190) / 210, (y - 100) / 130)
            if d > 0.7:
                c = cv.get(x, y)
                if c[3] == 255:
                    cv.set(x, y, mul(c, 1 - (d - 0.7) * 0.35))
    return cv


# ---------------------------------------------------------------- animated bits

def cat(f):
    """Orange tabby curled up asleep on the plaid. 16 frames: two slow breaths, a tail flick, an ear twitch."""
    K = 1.35                                                    # drawn on a 46x30 grid, scaled up
    rise = (math.sin(2 * math.pi * f / 8) + 1) / 2
    cv = Canvas(int(46 * K) + 2, int(30 * K) + 2)

    def P(*pts):
        return [(round(x * K), round(y * K)) for x, y in pts]
    bcx, bcy, rx, ry = 25 * K, (19 - rise * 0.7) * K, (17 + rise * 0.4) * K, (8.6 + rise * 0.8) * K
    for y in range(cv.h):
        for x in range(cv.w):
            d = ((x - bcx) / rx) ** 2 + ((y - bcy) / ry) ** 2
            if d <= 1:
                c = CAT
                if y > bcy + ry * 0.45:
                    c = CAT_D
                elif y < bcy - ry * 0.6 and x < bcx + 8:
                    c = CAT_L
                cv.set(x, y, c)
    for sx in (21, 26, 31, 36):                                 # tabby stripes across the back
        for k in range(4):
            cv.set(round(sx * K) + k // 2, int(bcy - ry + 1 + k), CAT_D)
    tip = (14, 24) if f not in (5, 6) else (13, 21.5)          # tail wrapped around the front
    pts = P((41, 21), (38, 26), (28, 27.3), (19, 26.3), tip)
    for (ax, ay), (bx, by) in zip(pts, pts[1:]):
        line(cv, ax, ay, bx, by, CAT, 4)
    line(cv, *pts[-2], *pts[-1], CAT_D, 4)
    for x in range(40, 50, 4):
        cv.set(x, round(27.6 * K), CAT_D)
    for px in (17, 21):                                         # white paws under the chin
        cv.disc(px * K, 24.2 * K, 2.6 * K, CAT_W, ry=1.6 * K)
        cv.set(round(px * K), round(25.2 * K), (220, 210, 200))
    hcy = (17 - rise * 0.3) * K
    hx = 12 * K
    for ear, inner in ((P((4, 14 - 3), (5, 14 - 11.5), (10.5, 14 - 6)), P((5.6, 14 - 4), (6, 14 - 9.5), (9, 14 - 6))),
                       (P((13.5, 14 - 6), (18, 14 - 11.5), (20, 14 - 3)) if f != 11 else
                        P((13.5, 14 - 6), (19.5, 14 - 10.5), (20.5, 14 - 2.5)),
                        P((15, 14 - 5.5), (17.6, 14 - 9.5), (18.4, 14 - 4)))):
        dy = round(hcy - 14 * K)
        poly(cv, [(a, b + dy) for a, b in ear], CAT)
        poly(cv, [(a, b + dy) for a, b in inner], CAT_P)
    cv.disc(hx, hcy, 8.6 * K, CAT, ry=6.9 * K)                  # head, resting on the paws
    cv.disc(hx - 2.5 * K, hcy - 3 * K, 4 * K, CAT_L, ry=2 * K)
    for x in (-2, 0, 2):                                        # forehead stripes
        cv.vline(round(hx + x * K), round(hcy - 6.2 * K), round(hcy - 4.4 * K), CAT_D)
    cv.disc(hx, hcy + 3.2 * K, 3.8 * K, CAT_W, ry=2.3 * K)      # muzzle
    hy = round(hcy)
    for ex in (-4.2, 4.2):                                      # closed eyes: little smiles
        x = round(hx + ex * K)
        cv.set(x - 2, hy, OUTLINE)
        cv.set(x - 1, hy + 1, OUTLINE)
        cv.set(x, hy + 1, OUTLINE)
        cv.set(x + 1, hy, OUTLINE)
        cv.rect(x - 2 + (-1 if ex < 0 else 1), hy + 3, 2, 1, CAT_P)   # blush
    nx = round(hx)
    cv.rect(nx - 1, hy + 2, 2, 1, CAT_P)                        # nose and a tiny mouth
    for x, y in ((nx - 2, hy + 4), (nx - 1, hy + 5), (nx, hy + 4), (nx + 1, hy + 5), (nx + 2, hy + 4)):
        cv.set(x - 0, y, (160, 96, 76))
    return outline(cv)


Z_SMALL = ["###", ".#.", "###"]
Z_BIG = ["####", "..#.", ".#..", "####"]


def zzz(f):
    cv = Canvas(18, 24)
    for p in ((f / 8), ((f + 4) % 8) / 8):
        g = Z_SMALL if p < 0.45 else Z_BIG
        x0, y0 = int(1 + p * 11), int(19 - p * 18)
        a = math.sin(p * math.pi)
        for j, row in enumerate(g):
            for i, v in enumerate(row):
                if v == "#":
                    cv.blend(x0 + i, y0 + j, (250, 248, 255), 0.9 * a)
    return cv


def steam(f, n=12):
    """Two soft curling wisps rising from the tea; loops over n frames."""
    cv = Canvas(18, 30)
    ph = 2 * math.pi * f / n
    for k in range(2):
        bx = 7 + k * 4
        for y in range(29, -1, -1):
            h = (29 - y) / 29
            x = bx + math.sin(h * 5 - ph + k * 2.2) * (0.8 + 3 * h)
            a = 0.8 * (1 - h) ** 1.1 * (0.45 + 0.55 * math.sin(h * 9 - 2 * ph + k * 1.7) ** 2)
            cv.blend(round(x), y, (255, 255, 255), a)
            cv.blend(round(x) + (1 if k else -1), y, (255, 255, 255), a * 0.45)
    return cv


def hanging_plant(f):
    """Macrame pot hanging from the ceiling in front of the window, its vines swaying."""
    cv = Canvas(28, 58)
    sway = math.sin(2 * math.pi * f / 6)
    line(cv, 14, 0, 14, 14, (226, 210, 176))
    line(cv, 14, 14, 8, 24, (226, 210, 176))
    line(cv, 14, 14, 20, 24, (226, 210, 176))
    for k, (dx, dy) in enumerate(((-5, -3), (-2, -5), (2, -5), (5, -3), (0, -6))):   # bushy top
        leaf(cv, 14 + dx, 23 + dy, LEAF if k % 2 else LEAF_L, flip=dx > 0)
    for vx, length, ph in ((8, 22, 0.0), (11, 30, 1.3), (16, 18, 2.1), (19, 26, 0.7)):
        for j in range(length):
            x = vx + math.sin(j * 0.22 + ph) * 1.2 + sway * 1.6 * (j / length) ** 1.5
            cv.set(round(x), 30 + j, LEAF_D)
            if j % 4 == 2:
                leaf(cv, round(x), 30 + j, LEAF if j % 8 == 2 else LEAF_L, flip=(j // 4 + vx) % 2 == 0)
    cv.disc(14, 26, 7, POT, ry=4)                               # pot
    cv.rect(7, 22, 15, 3, (0, 0, 0, 0))
    cv.rect(7, 23, 15, 2, POT_L)
    line(cv, 8, 25, 14, 30, (226, 210, 176))
    line(cv, 20, 25, 14, 30, (226, 210, 176))
    return outline(cv)


def pothos(f):
    """Vines trailing from the pot on the shelf."""
    cv = Canvas(30, 34)
    sway = math.sin(2 * math.pi * f / 6 + 1)
    for vx, length, ph in ((9, 26, 0.4), (14, 18, 1.8), (19, 30, 0.9), (24, 14, 2.5)):
        for j in range(length):
            x = vx + math.sin(j * 0.25 + ph) * 1.2 + sway * 1.4 * (j / length) ** 1.5
            cv.set(round(x), 2 + j, LEAF_D)
            if j % 4 == 1:
                leaf(cv, round(x), 2 + j, LEAF if j % 8 == 1 else LEAF_L, flip=(j // 4 + vx) % 2 == 1)
    return outline(cv)


def twinkle(f, bulbs):
    """Fairy lights at night: each bulb brightens in turn."""
    cv = Canvas(W, 26)
    for i, (x, y) in enumerate(bulbs):
        b = (math.sin(f * math.pi / 2 + i * 1.7) + 1) / 2
        if b > 0.5:
            c = BULB_COLORS[i % 4]
            for yy in range(y - 4, y + 6):
                for xx in range(x - 4, x + 6):
                    d = math.hypot(xx - x - 0.5, yy - y - 0.5) / 5
                    if d < 1:
                        cv.blend(xx, yy, c, 0.45 * (b - 0.5) * 2 * (1 - d))
            cv.rect(x, y, 2, 2, lerp(c, (255, 255, 255), 0.5))
    return cv


def mote(big):
    if not big:
        return Canvas(1, 1, (255, 248, 220, 255))
    cv = Canvas(3, 3)
    for x, y in ((1, 0), (0, 1), (2, 1), (1, 2)):
        cv.set(x, y, (255, 240, 200, 110))
    cv.set(1, 1, (255, 250, 230, 255))
    return cv


# ---------------------------------------------------------------- light

def sunbeam():
    """God rays from the window down to the desk, and the window's bright patch on the desk."""
    cv = Canvas(W, H)
    def band(xr):
        v = 0.5 + 0.3 * math.sin(xr * 0.19) + 0.25 * math.sin(xr * 0.47 + 1.3)
        if abs(xr - (GLASS[0] + GLASS[2]) / 2) < 2:
            v *= 0.3                                            # mullion shadow
        return clamp01(v)
    for y in range(GLASS[1] + 2, DESK_FRONT + 1):
        for x in range(W):
            if in_glass(x, y) or (LID[0] <= x < LID[2] and LID[1] <= y < LID[3]):
                continue
            xr = x - (y - RAY_Y) * RAY_DX
            if GLASS[0] + 2 <= xr < GLASS[2] - 2 and y > GLASS[1] + (xr - GLASS[0]) * 0.1:
                fade = 1 - (y - GLASS[1]) / 170
                cv.blend(x, y, SUNLIGHT, 0.34 * band(xr) ** 1.5 * fade)
    for y in range(DESK_BACK + 4, DESK_FRONT):                  # window patch on the desk
        for x in range(W):
            xp = x - (y - DESK_BACK - 4) * 0.9 - 30
            if GLASS[0] <= xp < GLASS[2] and not (77 <= xp <= 82) and y != 122 and y != 123:
                edge = min(xp - GLASS[0], GLASS[2] - xp, 6) / 6
                cv.blend(x, y, SUNLIGHT, 0.32 * edge)
    return cv


def dawn_glow():
    cv = Canvas(W, H)
    for y in range(H):
        for x in range(W):
            if in_screen(x, y):
                continue
            d = clamp01(math.hypot(x - 80, y - 45) / 300)
            cv.set(x, y, (255, 146, 96, int(30 + 70 * (1 - d))))
    return cv


def night_shade():
    cv = Canvas(W, H)
    for y in range(H):
        for x in range(W):
            if in_screen(x, y):
                continue                                        # the screen stays bright
            a = 80 if in_glass(x, y) else 176
            d = math.hypot((x - LAMP_POOL[0]) / 1.0, (y - LAMP_POOL[1]) / 0.55)
            a *= 0.3 + 0.7 * min(1, d / 100)
            if y < 22:
                a *= 0.85                                       # fairy lights along the top
            cv.set(x, y, NIGHT_TINT + (int(a),))
    return cv


def lights(lit_windows, bulbs):
    cv = Canvas(W, H)
    for y in range(50, H):                                      # warm pool from the lamp
        for x in range(160, W):
            d = math.hypot(x - LAMP_POOL[0], (y - LAMP_POOL[1]) / 0.55) / 82
            if d < 1:
                cv.set(x, y, (255, 196, 120, int(110 * (1 - d) ** 2)))
    (ax, ay), (bx, by) = RIM
    mx, my = (ax + bx) / 2, (ay + by) / 2
    for y in range(int(my), LAMP_POOL[1]):                      # beam: rim -> pool on the desk
        t = (y - my) / (LAMP_POOL[1] - my)
        cx = mx + (LAMP_POOL[0] - mx) * t
        half = 10 + 28 * t
        for x in range(int(cx - half), int(cx + half) + 1):
            edge = 1 - abs(x - cx) / half
            cv.blend(x, y, (255, 220, 160), 0.16 * edge * (1 - 0.5 * t))
    line(cv, ax, ay, bx, by, (255, 248, 220), 2)                # lit rim
    for y in range(SY - 10, DECK_BOT + 4):                       # screen glow on bezel and keys
        for x in range(SX - 16, SX + SW + 16):
            if in_screen(x, y):
                continue
            dx = max(SX - x, 0, x - (SX + SW - 1))
            dy = max(SY - y, 0, y - (SY + SH - 1))
            d = math.hypot(dx, dy * 0.6) / 16
            if d < 1:
                cv.blend(x, y, (120, 150, 230), 0.24 * (1 - d))
    for i, (x, y) in enumerate(bulbs):                          # fairy lights
        c = BULB_COLORS[i % 4]
        for yy in range(y - 5, y + 7):
            for xx in range(x - 5, x + 7):
                d = math.hypot(xx - x - 0.5, yy - y - 0.5) / 6
                if d < 1:
                    cv.blend(xx, yy, c, 0.3 * (1 - d))
        cv.rect(x, y, 2, 2, c)
    for x, y in lit_windows:
        cv.set(x, y, (255, 210, 120))
    cv.set(LID[2] - 6, DECK_TOP + 2, (120, 255, 140))           # power LED
    return cv


# ---------------------------------------------------------------- the X230 screen

def screen_label(zh, en, color):
    g = [cjk(ch, 10) for ch in zh]
    w = sum(len(x[0]) + 1 for x in g) + 4 + T.text_width(en)
    cv = Canvas(w + 2, 12)
    x = 1
    for gl in g:
        for j, row in enumerate(gl):
            for i, v in enumerate(row):
                if v == "#":
                    cv.set(x + i, (12 - len(gl)) // 2 + j, color)
        x += len(gl[0]) + 1
    text(cv, x + 3, 4, en, (230, 236, 244))
    return cv


BOOT_LOG = ["LOADED KERNEL 7.2", "STARTED UDEV", "MOUNTED / AND /BOOT", "UNLOCKED DISK DATA",
            "MOUNTED /HOME /DATA", "STARTED NETWORK", "REACHED DESKTOP"]
DOWN_LOG = ["STOPPED DESKTOP", "STOPPED NETWORK", "SAVED RANDOM SEED", "UNMOUNTED /DATA",
            "UNMOUNTED /HOME", "LOCKED DISK DATA", "GOOD NIGHT"]
UNLOCK_LINE = 3                       # boot log lines from here on wait for the passphrase
LOG_Y, LOG_STEP = 17, 6               # inside the screen
BAR_Y, BAR_W = 60, SW - 8
PANEL = (4, 16, SW - 8, 42)           # passphrase panel inside the screen
FIELD = (5, 19, SW - 18, 10)          # inside the panel
DOT_STEP = 4
DOT_MAX = (FIELD[2] - 6) // DOT_STEP


def log_line(s):
    cv = Canvas(SW - 8, 5)
    x = text(cv, 0, 0, "[", LOG_TXT)
    x = text(cv, x, 0, "OK", GREEN_OK)
    x = text(cv, x, 0, "] ", LOG_TXT)
    text(cv, x, 0, s, LOG_TXT)
    return cv


def bar_frame():
    cv = Canvas(BAR_W, 5)
    for x in range(BAR_W):
        cv.set(x, 0, LOG_TXT)
        cv.set(x, 4, LOG_TXT)
    for y in range(5):
        cv.set(0, y, LOG_TXT)
        cv.set(BAR_W - 1, y, LOG_TXT)
    return cv


def pass_panel():
    x0, y0, w, h = PANEL
    cv = Canvas(w, h, (8, 10, 18, 255))
    for x in range(w):
        cv.set(x, 0, AMBER)
        cv.set(x, h - 1, AMBER)
    for y in range(h):
        cv.set(0, y, AMBER)
        cv.set(w - 1, y, AMBER)
    lab = screen_label("密码", "PASSWORD", AMBER)
    cv.paste(lab, (w - lab.w) // 2, 4)
    fx, fy, fw, fh = FIELD
    cv.rect(fx, fy, fw, fh, (20, 24, 36))
    for x in range(fx, fx + fw):
        cv.set(x, fy, (90, 96, 120))
        cv.set(x, fy + fh - 1, (90, 96, 120))
    for y in range(fy, fy + fh):
        cv.set(fx, y, (90, 96, 120))
        cv.set(fx + fw - 1, y, (90, 96, 120))
    hint = "ENTER TO UNLOCK"
    text(cv, (w - T.text_width(hint)) // 2, fy + fh + 4, hint, (110, 118, 140))
    return cv


def dot():
    cv = Canvas(3, 4)
    cv.rect(0, 0, 3, 4, AMBER)
    for x, y in ((0, 0), (2, 0), (0, 3), (2, 3)):
        cv.set(x, y, (0, 0, 0, 0))
    return cv


# ---------------------------------------------------------------- objects for the script
# idle: (name, frames, x, y, z, ticks per frame, lit, drift, span)
#   lit: 0 always shown, 1 with the sun rays, 2 with the night lights, 3 with the day sky
#   drift: ticks per pixel moved right (0: still), wrapping every span pixels

def objects(bulbs):
    cat_frames = [cat(f) for f in range(16)]
    return [
        ("cat", cat_frames, 22, 126, 25, 18, 0, 0, 0),
        ("zzz", [zzz(f) for f in range(8)], 38, 104, 26, 14, 0, 0, 0),
        ("steam", [steam(f) for f in range(12)], 103, 82, 26, 5, 0, 0, 0),
        ("hang", [hanging_plant(f) for f in range(6)], 32, 0, 12, 22, 0, 0, 0),
        ("pothos", [pothos(f) for f in range(6)], 302, 30, 12, 26, 0, 0, 0),
        ("twinkle", [twinkle(f, bulbs) for f in range(4)], 0, 0, 102, 16, 2, 0, 0),
        ("cloud-a", [cloud(3)], -10, 16, 4, 12, 3, 12, 150),
        ("cloud-b", [cloud(8)], 40, 32, 4, 20, 3, 20, 150),
    ]


MOTE_N = 22
MOTE_Y0, MOTE_H = 48, 96


def motes():
    rng = random.Random(42)
    return [(rng.uniform(GLASS[0] + 6, GLASS[2] - 6), rng.uniform(0.9, 2.3), rng.randrange(1000),
             rng.uniform(0, 6.28)) for _ in range(MOTE_N)]


def write_script(out, idle, mote_list):
    lines = []
    for i, (name, frames, x, y, z, period, lit, drift, span) in enumerate(idle):
        for k in range(len(frames)):
            lines.append(f'idle[{i}].frames[{k}] = load("{name}-{k}.png");')
        lines.append(f"idle[{i}].n = {len(frames)}; idle[{i}].x = {x}; idle[{i}].y = {y}; idle[{i}].z = {z}; "
                     f"idle[{i}].period = {period}; idle[{i}].lit = {lit}; idle[{i}].drift = {drift}; "
                     f"idle[{i}].span = {span};")
    lines.append(f"idle_count = {len(idle)};")
    for i, (u, sp, off, ph) in enumerate(mote_list):
        lines.append(f"mote[{i}].u = {u:.1f}; mote[{i}].sp = {sp:.2f}; mote[{i}].off = {off}; "
                     f"mote[{i}].ph = {ph:.2f};")
    lines.append(f"mote_count = {len(mote_list)};")
    names = [f'log_boot[{i}] = "log-boot-{i}.png"; log_down[{i}] = "log-down-{i}.png";'
             for i in range(len(BOOT_LOG))]
    subst = {"@OBJECTS@": "\n".join(lines), "@LOG_NAMES@": "\n".join(names),
             "@W@": W, "@SX@": SX, "@SY@": SY, "@SW@": SW, "@SH@": SH, "@LOG_N@": len(BOOT_LOG),
             "@LOG_Y@": LOG_Y, "@LOG_STEP@": LOG_STEP, "@UNLOCK_LINE@": UNLOCK_LINE,
             "@BAR_Y@": BAR_Y, "@BAR_W@": BAR_W,
             "@PANEL_X@": PANEL[0], "@PANEL_Y@": PANEL[1], "@FIELD_X@": FIELD[0], "@FIELD_Y@": FIELD[1],
             "@DOT_STEP@": DOT_STEP, "@DOT_MAX@": DOT_MAX,
             "@SUN_X0@": SUN_PATH[0], "@SUN_DX@": SUN_PATH[1], "@SUN_Y0@": SUN_PATH[2], "@SUN_DY@": SUN_PATH[3],
             "@MOON_X0@": MOON_PATH[0], "@MOON_DX@": MOON_PATH[1], "@MOON_Y0@": MOON_PATH[2],
             "@MOON_DY@": MOON_PATH[3],
             "@MOTE_Y0@": MOTE_Y0, "@MOTE_H@": MOTE_H, "@RAY_DX@": RAY_DX, "@RAY_Y@": RAY_Y}
    s = open(os.path.join(HERE, "office.script.in")).read()
    for k, v in subst.items():
        s = s.replace(k, str(v))
    with open(os.path.join(out, "office.script"), "w") as f:
        f.write(s)


# ---------------------------------------------------------------- preview (mirrors office.script)

def over(dst, src, x0=0, y0=0, op=1.0):
    if op <= 0:
        return
    for j in range(src.h):
        for i in range(src.w):
            c = src.p[j * src.w + i]
            a = c[3] / 255 * op
            if a > 0:
                dst.blend(x0 + i, y0 + j, c, a) if a < 1 else dst.set(x0 + i, y0 + j, c)


def tod_levels(t):
    return {"day": clamp01((t - 0.55) / 0.35), "night": clamp01(1 - t / 0.75), "sky": clamp01((t - 0.25) / 0.4),
            "dawn": clamp01(1 - abs(t - 0.42) / 0.22)}


def compose(L, idle, mote_list, tod, tick, mode="boot", asking=0, frac=None):
    lv = tod_levels(tod)
    cv = Canvas(W, H, (0, 0, 0, 255))
    over(cv, L["sky-day"])
    over(cv, L["sky-dawn"], op=1 if tod < 0.45 else clamp01(1 - (tod - 0.45) / 0.35))
    over(cv, L["sky-night"], op=clamp01(1 - tod / 0.45))
    m = clamp01(tod / 0.5)
    over(cv, L["moon"], int(MOON_PATH[0] + m * MOON_PATH[1]), int(MOON_PATH[2] + m * MOON_PATH[3]))
    s = clamp01((tod - 0.3) / 0.7)
    over(cv, L["sun"], int(SUN_PATH[0] + s * SUN_PATH[1]), int(SUN_PATH[2] - math.sin(s * 1.6) * SUN_PATH[3]))
    ops = {0: 1, 1: lv["day"], 2: lv["night"], 3: lv["sky"]}
    by_z = sorted(idle, key=lambda o: o[4])

    def objs(zmin, zmax):
        for name, frames, x, y, z, period, lit, drift, span in by_z:
            if zmin <= z < zmax:
                dx = (tick // drift) % span if drift else 0
                over(cv, frames[(tick // period) % len(frames)], x + dx, y, ops[lit])
    objs(0, 5)
    over(cv, L["outside"])
    objs(5, 10)
    over(cv, L["room"])
    objs(10, 30)
    over(cv, L["sunbeam"], op=lv["day"])
    if lv["day"] > 0:
        for i, (u, sp, off, ph) in enumerate(mote_list):
            p = (int(tick * sp + off) % 1000) / 1000
            y = MOTE_Y0 + p * MOTE_H
            x = u + math.sin(tick * 0.03 + ph) * 3 + (y - RAY_Y) * RAY_DX
            a = lv["day"] * math.sin(p * math.pi) * (0.65 + 0.35 * math.sin(tick * 0.11 + ph))
            if not in_screen(x, y):
                over(cv, L[f"mote-{i % 2}"], int(x), int(y), a)
    over(cv, L["dawn"], op=lv["dawn"])
    over(cv, L["night"], op=clamp01(1 - tod / 0.6))
    over(cv, L["lights"], op=lv["night"])
    objs(100, 150)
    over(cv, L[f"label-{mode}"], SX + 4, SY + 3)
    frac = tod if frac is None else frac
    n = int(clamp01(frac) * (len(BOOT_LOG) + 1))
    for i in range(min(n, len(BOOT_LOG))):
        over(cv, L[f"log-{'boot' if mode == 'boot' else 'down'}-{i}"], SX + 4, SY + LOG_Y + i * LOG_STEP)
    over(cv, L["bar"], SX + 4, SY + BAR_Y)
    over(cv, Canvas(max(1, int((BAR_W - 2) * frac)), 3, AMBER + (255,)), SX + 5, SY + BAR_Y + 1)
    if asking:
        px, py = SX + PANEL[0], SY + PANEL[1]
        over(cv, L["pass"], px, py)
        for i in range(min(asking, DOT_MAX)):
            over(cv, L["dot"], px + FIELD[0] + 3 + i * DOT_STEP, py + FIELD[1] + 3)
        over(cv, Canvas(1, 6, (230, 236, 244, 255)), px + FIELD[0] + 3 + min(asking, DOT_MAX) * DOT_STEP,
             py + FIELD[1] + 2)
    return cv


def render_previews(L, idle, mote_list, out):
    os.makedirs(out, exist_ok=True)
    stills = {"night-ask": (0.06, "boot", 9, 0.35), "dawn": (0.42, "boot", 0, None), "day": (1.0, "boot", 0, None),
              "dusk": (0.4, "shutdown", 0, 0.6)}
    for name, (tod, mode, asking, frac) in stills.items():
        compose(L, idle, mote_list, tod, 40, mode, asking, frac).save(os.path.join(out, f"{name}.png"), scale=2)
    if "--stills" in sys.argv:
        return
    for mode in ("boot", "shutdown"):
        paths = []
        n = 64
        for i in range(n):
            t = min(1, i / (n - 12))                            # hold the end a moment
            tod = t if mode == "boot" else 1 - t
            p = os.path.join(out, f"{mode}-{i:03d}.png")
            compose(L, idle, mote_list, tod, i * 5, mode, 0, t).save(p, scale=2)
            paths.append(p)
            print(f"{mode} {i + 1}/{n}", end="\r", flush=True)
        print()
        subprocess.run(["magick", "-delay", "10", "-loop", "0", *paths, os.path.join(out, f"{mode}.gif")],
                       check=True)


# ---------------------------------------------------------------- output

def main():
    args = [a for a in sys.argv[1:] if a != "--stills"]
    preview = None
    if "--preview" in args:
        preview = args[args.index("--preview") + 1]
        del args[args.index("--preview"):args.index("--preview") + 2]
    out = args[0] if args else "."
    os.makedirs(out, exist_ok=True)
    rng = random.Random(1987)

    bulbs = garland_bulbs()
    L = {f"sky-{k}": T.sky(k, rng) for k in ("night", "dawn", "day")}
    L["outside"], lit = outside()
    L["room"] = room()
    L.update(sunbeam=sunbeam(), dawn=dawn_glow(), night=night_shade(), lights=lights(lit, bulbs),
             sun=T.sun(), moon=T.moon())
    L["label-boot"] = screen_label("启动中", "BOOTING", (255, 214, 110))
    L["label-shutdown"] = screen_label("关机", "SHUTTING DOWN", (255, 140, 170))
    L["label-reboot"] = screen_label("重启", "REBOOTING", (140, 220, 255))
    for i, s in enumerate(BOOT_LOG):
        L[f"log-boot-{i}"] = log_line(s)
    for i, s in enumerate(DOWN_LOG):
        L[f"log-down-{i}"] = log_line(s)
    L["bar"], L["pass"], L["dot"] = bar_frame(), pass_panel(), dot()
    L["mote-0"], L["mote-1"] = mote(False), mote(True)
    for f in os.listdir(out):                                   # drop images of the previous design
        if f.endswith(".png"):
            os.remove(os.path.join(out, f))
    for name, cv in L.items():
        cv.save(os.path.join(out, f"{name}.png"))
    Canvas(1, 3, AMBER + (255,)).save(os.path.join(out, "bar-fill.png"))
    Canvas(1, 6, (230, 236, 244, 255)).save(os.path.join(out, "caret.png"))
    Canvas(3, 5, (230, 236, 244, 255)).save(os.path.join(out, "cursor.png"))

    idle = objects(bulbs)
    for name, frames, *_ in idle:
        for k, fr in enumerate(frames):
            fr.save(os.path.join(out, f"{name}-{k}.png"))
    mote_list = motes()
    write_script(out, idle, mote_list)
    with open(os.path.join(out, "office.plymouth"), "w") as f:
        f.write("[Plymouth Theme]\nName=Office\n"
                "Description=A cozy study at the window: the sun rises on boot, sets on shutdown (marlinos)\n"
                "ModuleName=script\n\n[script]\nImageDir=/usr/share/plymouth/themes/office\n"
                "ScriptFile=/usr/share/plymouth/themes/office/office.script\n")

    if preview:
        render_previews(L, idle, mote_list, preview)


if __name__ == "__main__":
    main()
