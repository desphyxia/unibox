"""How much each creature animation adds to the game's download, to keep track as more animals arrive.
Reads the imported ASTC textures (what the web build and iPhone/iPad use) and gzips them the way GitHub Pages does.
Run from the repo root after Godot has imported the frames:  python art/tools/size_report.py [game/art/creatures]"""
import glob, gzip, os, re, sys

root = sys.argv[1] if len(sys.argv) > 1 else os.path.join("game", "art", "creatures")
game = os.path.join("game")
rows, total = [], {}
for anim_dir in sorted(glob.glob(os.path.join(root, "*", "*"))):
    if not os.path.isdir(anim_dir):
        continue
    kind, anim = anim_dir.replace("\\", "/").split("/")[-2:]
    raw = gz = n = 0
    w = h = 0
    for imp in sorted(glob.glob(os.path.join(anim_dir, "frame_*.png.import"))):
        m = re.search(r'path\.astc="res://([^"]+)"', open(imp, encoding="utf-8").read())
        if not m:
            continue
        data = open(os.path.join(game, m.group(1)), "rb").read()
        raw += len(data)
        gz += len(gzip.compress(data, 6))
        n += 1
    if n == 0:
        continue
    try:
        from PIL import Image
        w, h = Image.open(os.path.join(anim_dir, "frame_00.png")).size
    except Exception:
        pass
    rows.append((kind, anim, n, f"{w}x{h}", raw, gz))
    t = total.setdefault(kind, [0, 0, 0])
    t[0] += n
    t[1] += raw
    t[2] += gz

print(f"{'creature':10} {'animation':18} {'frames':>6} {'size':>9} {'raw MB':>7} {'download MB':>11}")
for kind, anim, n, size, raw, gz in rows:
    print(f"{kind:10} {anim:18} {n:6d} {size:>9} {raw / 1e6:7.2f} {gz / 1e6:11.2f}")
for kind, (n, raw, gz) in total.items():
    print(f"{kind:10} {'TOTAL':18} {n:6d} {'':>9} {raw / 1e6:7.2f} {gz / 1e6:11.2f}")
