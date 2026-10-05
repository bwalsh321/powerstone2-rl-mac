"""Tiles at hit frames for given source classes (vt), with victim + slot motion around the hit."""
import sys, os, numpy as np
from PIL import Image, ImageDraw
from common import *
want = [int(x, 16) for x in sys.argv[2:]]; out = sys.argv[1]
tiles = []
for L in "ABCD":
    d = load(L); hp, hs, led = d["hp"], d["hsrc"], d["ledger"]; names = LINEUPS[L]
    for f in range(1, len(hp)):
        for k in range(4):
            if not (0.5 < hp[f-1, k] - hp[f, k] < 900): continue
            i, r = lslot(int(hs[f, k]))
            if i is None or i >= led.shape[1] or seat_of(int(hs[f,k])) is not None: continue
            c = int(u32(led[f, i], 8))
            if c not in want: continue
            P = [(float(f32(led[g, i], 0x2C)), float(f32(led[g, i], 0x30)), float(f32(led[g, i], 0x34))) for g in (f-6, f)]
            sp = np.linalg.norm(np.subtract(P[1], P[0])) * 10
            for g in (f - 6, f):
                gg = g // 3 * 3
                im = Image.open(f"{HERE}/../cap/{L}/jpg/f{gg:05d}.jpg").convert("RGB"); dr = ImageDraw.Draw(im)
                dr.rectangle((0, 0, 320, 12), fill=(0, 0, 0))
                dr.text((2, 1), f"{c:#x} {L} hit {names[k]} f{f} shot{gg} hdr{int(u32(led[f,i],4))&0xff:x} sp{sp:.0f} y{P[1][1]:.0f}", fill=(255, 255, 0))
                tiles.append(im)
tiles = tiles[:32]
M = Image.new("RGB", (320 * 4, 240 * ((len(tiles) + 3) // 4)))
for j, im in enumerate(tiles): M.paste(im, ((j % 4) * 320, (j // 4) * 240))
M.save(out, quality=85); print(len(tiles))
