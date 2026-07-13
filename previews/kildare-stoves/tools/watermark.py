"""Watermark Kildare Stoves product images.

Adds a tiled diagonal "KILDARE STOVES" wordmark (tunable opacity) plus a solid
corner mark, resizes to a web-friendly size and saves as .webp.

Usage:
    python watermark.py <in_dir> <out_dir> [--size 1200] [--opacity 46]
"""
import sys, os, glob, argparse
from PIL import Image, ImageDraw, ImageFont

def font(size):
    for p in (r"C:\Windows\Fonts\arialbd.ttf", r"C:\Windows\Fonts\Arial.ttf"):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default()

def watermark(img, size, opacity):
    img = img.convert("RGB")
    img = img.resize((size, size), Image.LANCZOS)
    # tiled diagonal wordmark on an oversized layer, then rotate + centre-crop
    big = int(size * 1.5)
    layer = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    f = font(int(size * 0.030))
    text = "KILDARE STOVES   •   "
    step_y = int(size * 0.16)
    for i, y in enumerate(range(0, big, step_y)):
        offset = (i % 2) * int(size * 0.22)  # brick-offset alternate rows
        d.text((-offset, y), text * 6, font=f, fill=(255, 255, 255, opacity))
    layer = layer.rotate(30, resample=Image.BICUBIC, center=(big // 2, big // 2))
    crop = (big - size) // 2
    layer = layer.crop((crop, crop, crop + size, crop + size))
    out = Image.alpha_composite(img.convert("RGBA"), layer)
    # solid corner mark (kept well inside the frame so display-crop can't clip it)
    d2 = ImageDraw.Draw(out)
    fc = font(int(size * 0.030))
    label = "KILDARE STOVES"
    tw = d2.textlength(label, font=fc)
    padx = int(size * 0.05)
    pady = int(size * 0.075)
    # subtle shadow for legibility on light images
    d2.text((size - tw - padx + 2, size - pady + 2), label, font=fc, fill=(0, 0, 0, 120))
    d2.text((size - tw - padx, size - pady), label, font=fc, fill=(255, 224, 186, 240))
    return out.convert("RGB")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("in_dir"); ap.add_argument("out_dir")
    ap.add_argument("--size", type=int, default=1200)
    ap.add_argument("--opacity", type=int, default=46)  # 0-255
    a = ap.parse_args()
    os.makedirs(a.out_dir, exist_ok=True)
    files = sorted(glob.glob(os.path.join(a.in_dir, "*.png")) + glob.glob(os.path.join(a.in_dir, "*.jpg")))
    for fp in files:
        name = os.path.splitext(os.path.basename(fp))[0]
        out = watermark(Image.open(fp), a.size, a.opacity)
        dest = os.path.join(a.out_dir, name + ".webp")
        out.save(dest, "WEBP", quality=86, method=6)
        print("watermarked", dest)

if __name__ == "__main__":
    main()
