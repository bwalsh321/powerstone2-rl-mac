"""Tiles for flight runs of given (hdr9) vts: frames start, mid, end of each run."""
import sys, numpy as np
from PIL import Image, ImageDraw
from common import *
out = sys.argv[1]; want = [int(x, 16) for x in sys.argv[2:]]
tiles = []; per_vt = {}
for L in LINEUPS:
    d = load(L); led = d["ledger"]; pos = d["pos"]; names = LINEUPS[L]
    hdr = u32(led, 4) & 0xFF; vt = u32(led, 8)
    P = np.stack([f32(led, 0x2C), f32(led, 0x30), f32(led, 0x34)], -1).astype(np.float64)
    sp = np.linalg.norm(np.diff(P, axis=0), axis=-1) * 60
    ok = (vt[1:] == vt[:-1]) & (sp >= 400) & (sp <= 6000)
    for i in range(ok.shape[1]):
        f = 0
        while f < ok.shape[0]:
            if ok[f, i] and int(vt[f, i]) in want:
                g = f
                while g < ok.shape[0] and ok[g, i]: g += 1
                c = int(vt[f, i])
                if g - f >= 5 and per_vt.get(c, 0) < 6:
                    per_vt[c] = per_vt.get(c, 0) + 1
                    for h in (f, (f + g) // 2, g):
                        hh = h // 3 * 3
                        im = Image.open(f"{HERE}/../cap/{L}/jpg/f{hh:05d}.jpg").convert("RGB"); dr = ImageDraw.Draw(im)
                        dr.rectangle((0, 0, 320, 12), fill=(0, 0, 0))
                        dr.text((2, 1), f"{c:#x} {L}s{i} f{h} run{f}-{g} y{P[h,i,1]:.0f} sp{np.median(sp[f:g,i]):.0f}", fill=(255, 255, 0))
                        tiles.append(im)
                f = g
            else:
                f += 1
tiles = tiles[:int(__import__("os").environ.get("NT", 999))]; M = Image.new("RGB", (320 * 3, 240 * ((len(tiles) + 2) // 3)))
for j, im in enumerate(tiles): M.paste(im, ((j % 3) * 320, (j // 3) * 240))
M.save(out, quality=80); print(len(tiles), per_vt)
