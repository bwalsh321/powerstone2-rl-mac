import numpy as np
from collections import Counter
from common import *
cats = Counter(); spawn_gap = Counter()
for L in LINEUPS:
    d = load(L); led = d["ledger"]; hp, hs = d["hp"], d["hsrc"]
    hdr = u32(led, 4) & 0xFF; vt = u32(led, 8)
    for c in (2, 3, 4, 6):
        for v in np.unique(vt[hdr == c]): cats[(c, hex(int(v)))] += int(((hdr == c) & (vt == v)).sum())
    for f in range(7, len(hp)):
        for k in range(4):
            if not (0.5 < hp[f-1, k] - hp[f, k] < 900): continue
            p = int(hs[f, k]); i, r = lslot(p)
            if seat_of(p) is not None or i is None or i >= led.shape[1] or hdr[f, i] != 1: continue
            if (hdr[f-6:f, i] == 1).any() and (vt[f-6:f, i] == vt[f, i]).any(): continue
            g = f
            while g > 0 and hdr[g-1, i] == 1 and vt[g-1, i] == vt[f, i]: g -= 1
            spawn_gap[f - g] += 1
print("other categories (frames):", cats.most_common(12))
print("cat1 misses: frames from source spawn to hit:", sorted(spawn_gap.items()))
