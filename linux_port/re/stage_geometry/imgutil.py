"""Tiny PIL heatmap helpers (no matplotlib in ~/ps2rl). Arrays are [z, x]; image drawn with +z UP, +x RIGHT."""
import numpy as np
from PIL import Image, ImageDraw

def colormap(v, lo, hi):
    t = np.clip((np.asarray(v, float) - lo) / max(hi - lo, 1e-9), 0, 1)
    # viridis-ish 5-stop
    stops = np.array([[68, 1, 84], [59, 82, 139], [33, 145, 140], [94, 201, 98], [253, 231, 37]], float)
    s = t * (len(stops) - 1); i = np.minimum(s.astype(int), len(stops) - 2); f = (s - i)[..., None]
    return (stops[i] * (1 - f) + stops[i + 1] * f).astype(np.uint8)

def heat(arr, lo, hi, scale=4, mask=None, title=None, nan_color=(40, 40, 40)):
    rgb = colormap(np.nan_to_num(arr, nan=lo), lo, hi)
    bad = ~np.isfinite(arr)
    if mask is not None: bad |= mask
    rgb[bad] = nan_color
    img = Image.fromarray(rgb[::-1]).resize((arr.shape[1] * scale, arr.shape[0] * scale), Image.NEAREST)
    if title:
        canvas = Image.new("RGB", (img.width, img.height + 16), (0, 0, 0)); canvas.paste(img, (0, 16))
        ImageDraw.Draw(canvas).text((2, 2), f"{title}  [{lo:g}..{hi:g}]", fill=(255, 255, 255)); img = canvas
    return img

def hstack(imgs, pad=6):
    W = sum(i.width for i in imgs) + pad * (len(imgs) - 1); H = max(i.height for i in imgs)
    out = Image.new("RGB", (W, H), (0, 0, 0)); x = 0
    for i in imgs: out.paste(i, (x, 0)); x += i.width + pad
    return out
