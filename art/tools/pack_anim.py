"""Pack a rendered animation loop for the game: clear the faint render haze, crop every frame to one shared box, copy the
frames into the game with VRAM-compressed imports, and write anim.json with what the game needs to place it:
  anchor   where the creature's ground origin is, in cropped-frame pixels (the same world point for every animation
           from one camera, so swapping idle and walk does not make the creature jump)
  shadow   centre x and width of the ground contact, relative to the anchor, for the game-drawn shadow
  stride   ground travelled per walk cycle, in frame pixels (0 for loops that stay in place); stance is the share of the
           cycle a paw is on the ground, so paws don't slide: speed = stride / (stance * cycle seconds)
Usage: python pack_anim.py RENDER_DIR GAME_DIR [--anchor-from OTHER_RENDER_DIR] [--fps 12] [--stance 0.6]"""
import glob, json, os, shutil, sys
import numpy as np
from PIL import Image

args = sys.argv[1:]
src, dst = args[0], args[1]
opt = {args[i]: args[i + 1] for i in range(2, len(args) - 1, 2)}
meta_path = os.path.join(src, "anchor.json")
borrowed = not os.path.exists(meta_path)
if borrowed:                                    # an older render without its own anchor: same camera, so borrow one
    meta_path = os.path.join(opt["--anchor-from"], "anchor.json")
meta = json.load(open(meta_path))
if borrowed:
    meta["stride_px"] = 0.0
files = sorted(glob.glob(os.path.join(src, "frame_*.png")))
ims = []
for f in files:
    im = Image.open(f).convert("RGBA")
    r, g, b, a = im.split()
    ims.append(Image.merge("RGBA", (r, g, b, a.point(lambda v: 0 if v < 8 else v))))
box = None
for im in ims:
    bb = im.getchannel("A").point(lambda v: 255 if v > 3 else 0).getbbox()
    box = bb if box is None else (min(box[0], bb[0]), min(box[1], bb[1]), max(box[2], bb[2]), max(box[3], bb[3]))
pad = 4
box = (max(box[0] - pad, 0), max(box[1] - pad, 0), min(box[2] + pad, ims[0].width), min(box[3] + pad, ims[0].height))
# ground contact: the lowest solid rows, averaged over the loop
xs = []
for im in ims:
    A = np.asarray(im.getchannel("A")) > 128
    rows = np.nonzero(A.any(axis=1))[0]
    foot = rows.max()
    cols = np.nonzero(A[foot - 40:foot + 1].any(axis=0))[0]
    xs.append((cols.min(), cols.max()))
x0, x1 = np.mean([c[0] for c in xs]), np.mean([c[1] for c in xs])
ax, ay = meta["anchor"]
if os.path.isdir(dst):
    shutil.rmtree(dst)
os.makedirs(dst)
for i, im in enumerate(ims):
    p = os.path.join(dst, f"frame_{i:02d}.png")
    im.crop(box).save(p, optimize=True)
    open(p + ".import", "w").write('[remap]\n\nimporter="texture"\ntype="CompressedTexture2D"\n\n[params]\n\ncompress/mode=2\ncompress/high_quality=true\nmipmaps/generate=false\n')
info = dict(frames=len(ims), fps=float(opt.get("--fps", 12)), anchor=[ax - box[0], ay - box[1]],
            shadow=[(x0 + x1) / 2 - ax, (x1 - x0) * 1.05], stride=meta.get("stride_px", 0.0), stance=float(opt.get("--stance", 0.6)),
            crop=[box[0], box[1]], render_anchor=[ax, ay])
json.dump(info, open(os.path.join(dst, "anim.json"), "w"), indent=1)
print(json.dumps(info))
