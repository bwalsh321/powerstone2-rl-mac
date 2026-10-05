"""Category-1 ledger objects (hdr low byte == 1): per class, which offsets hold player-object pointers,
and which seat they name (-> owner char). Also first-frame spawn distance to each seat."""
import numpy as np
from collections import Counter, defaultdict
from common import *
res = defaultdict(lambda: defaultdict(Counter)); spawn = defaultdict(Counter); n = Counter()
for L in LINEUPS:
    d = load(L); led = d["ledger"]; names = LINEUPS[L]; pos = d["pos"]
    F, NL, LB = led.shape
    hdr = u32(led, 4) & 0xFF; vt = u32(led, 8)
    for i in range(NL):
        on = (hdr[:, i] == 1)
        starts = np.flatnonzero(on & ~np.r_[False, on[:-1]] | (on & np.r_[False, vt[1:, i] != vt[:-1, i]]))
        for f in starts:
            c = int(vt[f, i]); n[c] += 1
            b = led[f, i]
            w = b[:LB - LB % 4].view("<u4")
            for j, v in enumerate(w):
                s = seat_of(int(v)) if (int(v) & 0x0F000000) == 0x0C000000 else None
                if s is not None:
                    res[c][j*4][names[s]] += 1
            p = np.array([f32(b, 0x2C), f32(b, 0x30), f32(b, 0x34)], float)
            dd = np.hypot(pos[f, :, 0] - p[0], pos[f, :, 2] - p[2])
            spawn[c][names[int(np.argmin(dd))]] += 1
for c in sorted(n, key=lambda c: -n[c]):
    offs = sorted(res[c].items(), key=lambda kv: -sum(kv[1].values()))[:3]
    print(f"{c:#010x} n={n[c]:4d} nearest-at-spawn={dict(spawn[c].most_common(3))}  ptr-offsets: " +
          "  ".join(f"+{o:#x}:{dict(cn.most_common(2))}" for o, cn in offs))
