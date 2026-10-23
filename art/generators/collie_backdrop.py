"""A meadow backdrop for the collie renders (collie_a.py, collie_b.py, collie_c.py), made from code in the storybook
watercolour feel of the reference: a soft sky, distant hills, a pale path, warm green grass with a few daisies and
clover, and a soft shadow under the dog. Each render (transparent PNG) is set on it.
Usage: python collie_backdrop.py RENDER_DIR OUT_DIR"""
import os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

SRC, DST = sys.argv[1], sys.argv[2]
os.makedirs(DST, exist_ok=True)


def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def meadow(w, h, seed, horizon=0.5):
    rng = np.random.default_rng(seed)
    img = Image.new("RGB", (w, h))
    d = ImageDraw.Draw(img)
    hy = int(h * horizon)
    for y in range(hy):                                     # sky: soft blue to warm cream
        d.line([(0, y), (w, y)], fill=lerp((196, 220, 236), (250, 240, 222), y / hy))
    for k in range(5):                                      # clouds
        cx, cy, r = rng.uniform(0, w), rng.uniform(0.05, 0.3) * h, rng.uniform(0.06, 0.12) * w
        for j in range(6):
            ox, oy = rng.normal(0, r * 0.5), rng.normal(0, r * 0.15)
            rr = r * rng.uniform(0.35, 0.6)
            d.ellipse([cx + ox - rr, cy + oy - rr * 0.6, cx + ox + rr, cy + oy + rr * 0.6], fill=(253, 251, 246))
    for k, (col, top) in enumerate((((176, 184, 206), 0.0), ((160, 186, 150), 0.035))):   # far hills, then near ones
        pts = [(0, h)]
        for x in range(0, w + 40, 40):
            pts.append((x, hy - h * (0.07 - top) * (0.6 + 0.4 * np.sin(x / w * 5 + k * 2 + seed))))
        pts.append((w, h))
        d.polygon(pts, fill=col)
    for y in range(hy, h):                                  # grass
        d.line([(0, y), (w, y)], fill=lerp((172, 196, 124), (126, 160, 92), (y - hy) / (h - hy)))
    path = [(w * 0.62, hy + 4), (w * 0.66, hy + 4)]          # a pale path winding off
    for t in np.linspace(0, 1, 30):
        path.append((w * (0.66 + 0.25 * t ** 1.4) + 30 * np.sin(t * 5), hy + 4 + (h - hy) * 0.55 * t))
    for t in np.linspace(1, 0, 30):
        path.append((w * (0.62 + 0.18 * t ** 1.4) + 30 * np.sin(t * 5), hy + 4 + (h - hy) * 0.55 * t))
    d.polygon(path, fill=(222, 206, 166))
    img = img.filter(ImageFilter.GaussianBlur(w * 0.004))
    d = ImageDraw.Draw(img)
    for _ in range(int(w * 1.4)):                           # grass blades
        x, y = rng.uniform(0, w), rng.uniform(hy, h)
        ln = (6 + 22 * (y - hy) / (h - hy)) * rng.uniform(0.6, 1.3) * w / 1200
        col = lerp((96, 132, 70), (160, 190, 110), rng.random())
        d.line([(x, y), (x + rng.normal(0, ln * 0.3), y - ln)], fill=col, width=max(1, int(w / 700)))
    for _ in range(40):                                     # daisies and clover
        x, y = rng.uniform(0, w), rng.uniform(hy + (h - hy) * 0.2, h)
        r = (3 + 7 * (y - hy) / (h - hy)) * w / 1200
        if rng.random() < 0.6:
            for k in range(8):
                a = k / 8 * 2 * np.pi
                d.ellipse([x + np.cos(a) * r - r * 0.45, y + np.sin(a) * r * 0.6 - r * 0.3, x + np.cos(a) * r + r * 0.45, y + np.sin(a) * r * 0.6 + r * 0.3], fill=(252, 250, 244))
            d.ellipse([x - r * 0.4, y - r * 0.3, x + r * 0.4, y + r * 0.3], fill=(240, 196, 70))
        else:
            d.ellipse([x - r, y - r, x + r, y + r], fill=(210, 150, 186))
    return img.filter(ImageFilter.GaussianBlur(w * 0.0015))


for i, name in enumerate(sorted(f for f in os.listdir(SRC) if f.endswith(".png"))):
    fg = Image.open(os.path.join(SRC, name)).convert("RGBA")
    w, h = fg.size
    bg = meadow(w, h, 5 + i, 0.42 if "head" not in name else 0.62).convert("RGBA")
    a = np.asarray(fg)[..., 3]
    ys, xs = np.nonzero(a > 128)
    if len(ys) and "head" not in name:
        sh = Image.new("L", (w, h), 0)
        cx, bw, y = (xs.min() + xs.max()) / 2, (xs.max() - xs.min()) * 0.48, ys.max() - h * 0.01
        ImageDraw.Draw(sh).ellipse([cx - bw, y - h * 0.025, cx + bw, y + h * 0.02], fill=120)
        sh = sh.filter(ImageFilter.GaussianBlur(h * 0.015))
        shadow = Image.new("RGBA", (w, h), (60, 70, 40, 0))
        shadow.putalpha(sh)
        bg.alpha_composite(shadow)
    bg.alpha_composite(fg)
    bg.convert("RGB").save(os.path.join(DST, name.replace(".png", ".jpg")), quality=92)
    print("composed", name)
