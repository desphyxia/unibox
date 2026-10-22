"""A watercolour paper backdrop for the new unicorn's renders (unicorn2.py), made from code: warm white paper, soft
pastel washes with pigment pooled at their edges, a few drips and speckles, and a soft shadow under the hooves. Each
render (transparent PNG) is set on its own backdrop.
Usage: python unicorn2_backdrop.py RENDER_DIR OUT_DIR"""
import os, sys
import numpy as np
from PIL import Image, ImageFilter

SRC, DST = sys.argv[1], sys.argv[2]
os.makedirs(DST, exist_ok=True)
PASTELS = [(247, 178, 205), (255, 205, 170), (190, 214, 245), (214, 196, 244), (255, 224, 170), (200, 232, 238)]


def blob_mask(w, h, cx, cy, r, rng, n=9):
    """an irregular soft shape: overlapping circles, blurred, with a darker rim where the pigment pools"""
    m = Image.new("L", (w, h), 0)
    from PIL import ImageDraw
    d = ImageDraw.Draw(m)
    for _ in range(n):
        ox, oy = rng.normal(0, r * 0.45, 2)
        rr = r * rng.uniform(0.35, 0.75)
        d.ellipse([cx + ox - rr, cy + oy - rr * rng.uniform(0.7, 1.0), cx + ox + rr, cy + oy + rr], fill=255)
    m = m.filter(ImageFilter.GaussianBlur(r * 0.12))
    a = np.asarray(m, np.float32) / 255
    edge = np.clip(a * (1 - a) * 4, 0, 1)                  # strongest where the wash fades out
    return a, edge


def backdrop(w, h, seed):
    rng = np.random.default_rng(seed)
    paper = np.ones((h, w, 3), np.float32) * np.array([253, 251, 249], np.float32)
    grain = rng.normal(0, 2.2, (h // 4, w // 4)).astype(np.float32)
    grain = np.asarray(Image.fromarray(grain).resize((w, h), Image.BICUBIC))
    paper += grain[..., None]
    img = paper.copy()
    for k in range(9):
        col = np.array(PASTELS[k % len(PASTELS)], np.float32)
        side = rng.choice([-1, 1])
        cx = w * (0.5 + side * rng.uniform(0.18, 0.42))
        cy = h * rng.uniform(0.15, 0.85)
        r = min(w, h) * rng.uniform(0.07, 0.15)
        a, edge = blob_mask(w, h, cx, cy, r, rng)
        alpha = (a * 0.32 + edge * 0.22)[..., None] * rng.uniform(0.6, 1.0)
        img = img * (1 - alpha) + col * alpha
        if rng.random() < 0.5:                             # a drip running down from it
            x = int(cx + rng.uniform(-r * 0.5, r * 0.5))
            y0, y1 = int(cy + r * 0.4), int(cy + r * rng.uniform(1.2, 2.4))
            for y in range(max(y0, 0), min(y1, h)):
                t = (y - y0) / max(y1 - y0, 1)
                ww = max(1, int(3 * (1 - t) + 1))
                img[y, max(x - ww, 0):x + ww] = img[y, max(x - ww, 0):x + ww] * 0.75 + col * 0.25
    for _ in range(60):                                     # speckles
        col = np.array(PASTELS[rng.integers(len(PASTELS))], np.float32)
        x, y = rng.integers(0, w), rng.integers(0, h)
        rr = rng.integers(2, 7)
        yy, xx = np.ogrid[max(y - rr, 0):min(y + rr, h), max(x - rr, 0):min(x + rr, w)]
        mask = ((yy - y) ** 2 + (xx - x) ** 2) <= rr * rr
        sub = img[max(y - rr, 0):min(y + rr, h), max(x - rr, 0):min(x + rr, w)]
        sub[mask] = sub[mask] * 0.45 + col * 0.55
    return np.clip(img, 0, 255).astype(np.uint8)


for i, name in enumerate(sorted(f for f in os.listdir(SRC) if f.endswith(".png"))):
    fg = Image.open(os.path.join(SRC, name)).convert("RGBA")
    w, h = fg.size
    bg = Image.fromarray(backdrop(w, h, 31 + i)).convert("RGBA")
    a = np.asarray(fg)[..., 3]
    ys, xs = np.nonzero(a > 128)
    if len(ys) and name != "head.png":
        # a soft lilac shadow under the hooves
        sh = Image.new("L", (w, h), 0)
        from PIL import ImageDraw
        cx = (xs.min() + xs.max()) / 2
        bw = (xs.max() - xs.min()) * 0.42
        y = ys.max() - h * 0.008
        ImageDraw.Draw(sh).ellipse([cx - bw, y - h * 0.018, cx + bw, y + h * 0.018], fill=110)
        sh = sh.filter(ImageFilter.GaussianBlur(h * 0.012))
        shadow = Image.new("RGBA", (w, h), (150, 130, 190, 0))
        shadow.putalpha(sh)
        bg.alpha_composite(shadow)
    bg.alpha_composite(fg)
    bg.convert("RGB").save(os.path.join(DST, name.replace(".png", ".jpg")), quality=92)
    print("composed", name)
