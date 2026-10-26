"""Preview the hutong theme without plymouth: composite the layers the way hutong.script does
and write boot.gif (night -> day) and shutdown.gif (day -> night). Used by make.py --preview."""
import math
import os
import subprocess

from make import W, H, Canvas, sun, moon


def clamp01(v):
    return max(0.0, min(1.0, v))


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


def compose(layers, idle, walk, tod, tick, label, fill):
    cv = Canvas(W, H, (0, 0, 0, 255))
    over(cv, layers["sky-day"])
    over(cv, layers["sky-dawn"], opacity=1 if tod < 0.4 else clamp01(1 - (tod - 0.4) / 0.4))
    over(cv, layers["sky-night"], opacity=clamp01(1 - tod / 0.4))
    m = clamp01(tod / 0.45)
    over(cv, moon(), int(70 + m * 200), int(22 + m * 90))
    s = clamp01((tod - 0.3) / 0.7)
    over(cv, sun(), int(16 + s * 210), int(104 - math.sin(s * 1.9) * 84))

    items = [(10, "bg", None), (30, "mid", None)]
    for name, frames, x, y, z, period in idle:
        items.append((z, frames[(tick // period) % len(frames)], (x, y - frames[0].h, 1)))
    for name, frames, x, y, z, speed, period, day in walk:
        span = W + 2 + frames[0].w
        px = (x + frames[0].w + speed * tick) % span - frames[0].w
        op = clamp01((tod - 0.4) / 0.4) if day else 1
        items.append((z, frames[(tick // period) % len(frames)], (int(px), y - frames[0].h, op)))
    for z, it, pos in sorted(items, key=lambda i: i[0]):
        if pos is None:
            over(cv, layers[it])
        else:
            over(cv, it, pos[0], pos[1], pos[2])

    over(cv, layers["night"], opacity=clamp01(1 - tod / 0.55))
    over(cv, layers["lights"], opacity=clamp01(1 - tod / 0.45))
    over(cv, label["hud"], (W - 150) // 2, 166)
    over(cv, label["text"], (W - label["text"].w) // 2, 168)
    over(cv, label["bar"], (W - 122) // 2, 181)
    bar = Canvas(max(1, int(120 * fill)), 3, (255, 190, 90, 255))
    over(cv, bar, (W - 122) // 2 + 1, 182)
    return cv


def render_previews(theme_dir, out, layers, idle, walk):
    from make import label as make_label, hud_panel
    os.makedirs(out, exist_ok=True)
    bar = Canvas(122, 5)
    for x in range(122):
        bar.set(x, 0, (250, 240, 220))
        bar.set(x, 4, (250, 240, 220))
    for y in range(5):
        bar.set(0, y, (250, 240, 220))
        bar.set(121, y, (250, 240, 220))
    for name, zh, en, col, forward in (("boot", "启动中", "BOOTING", (255, 214, 110), True),
                                       ("shutdown", "关机", "SHUTTING DOWN", (255, 140, 170), False)):
        lab = {"hud": hud_panel(150, 22), "text": make_label(zh, en, col), "bar": bar}
        paths = []
        n = 72
        for i in range(n):
            tod = i / (n - 1) if forward else 1 - i / (n - 1)
            tick = i * 6
            fill = tod if forward else 1 - tod
            p = os.path.join(out, f"{name}-{i:03d}.png")
            compose(layers, idle, walk, tod, tick, lab, fill).save(p, scale=2)
            paths.append(p)
            print(f"{name} {i + 1}/{n}", end="\r", flush=True)
        print()
        subprocess.run(["magick", "-delay", "12", "-loop", "0", *paths, os.path.join(out, f"{name}.gif")],
                       check=True)
