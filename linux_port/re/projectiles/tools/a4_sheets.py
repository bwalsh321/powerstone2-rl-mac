"""Contact sheets: for each category-1 ledger class, up to K instances, frames spawn+3 and +12 (jpg cadence 3)."""
import sys, numpy as np, os
from collections import defaultdict
from PIL import Image, ImageDraw
from common import *
K = 2
inst = defaultdict(list)
for L in "ABCD":
    d = load(L); led = d["ledger"]; names = LINEUPS[L]
    hdr = u32(led, 4) & 0xFF; vt = u32(led, 8); own = u32(led, 0x14)
    F, NL, _ = led.shape
    for i in range(NL):
        on = hdr[:, i] == 1
        st = np.flatnonzero(on & ~np.r_[False, on[:-1]] | (on & np.r_[False, vt[1:, i] != vt[:-1, i]]))
        for f in st:
            c = int(vt[f, i])
            if len([x for x in inst[c] if x[0] == L]) >= K: continue
            e = f + 1
            while e < F and hdr[e, i] == 1 and vt[e, i] == c: e += 1
            s = seat_of(int(own[f, i]))
            inst[c].append((L, int(f), int(e - f), names[s] if s is not None else "-"))
tiles = []
for c in sorted(inst):
    for L, f, life, o in inst[c][:3]:
        for df in (3, 12):
            g = (f + df) // 3 * 3
            p = f"{HERE}/../cap/{L}/jpg/f{g:05d}.jpg"
            if not os.path.exists(p): continue
            im = Image.open(p).convert("RGB"); dr = ImageDraw.Draw(im)
            dr.rectangle((0, 0, 320, 12), fill=(0, 0, 0))
            dr.text((2, 1), f"{c:#x} {L}{tuple(LINEUPS[L])[0][:3]}.. own={o} f{f}+{df} life{life}", fill=(255, 255, 0))
            tiles.append(im)
out = sys.argv[1] if len(sys.argv) > 1 else f"{HERE}/../shots/cat1"
os.makedirs(out, exist_ok=True)
per = 16
for s in range(0, len(tiles), per):
    M = Image.new("RGB", (320 * 4, 240 * 4))
    for j, im in enumerate(tiles[s:s + per]):
        M.paste(im, ((j % 4) * 320, (j // 4) * 240))
    M.save(f"{out}/sheet{s // per:02d}.jpg", quality=85)
print(len(tiles), "tiles")
