"""Flight runs of NON-category-1 ledger objects: consecutive frames with 400 <= speed <= 6000 u/s (no teleports)."""
import numpy as np, sys
from collections import Counter, defaultdict
from common import *
runs = defaultdict(list)
for L in LINEUPS:
    d = load(L); led = d["ledger"]; pos = d["pos"]
    hdr = u32(led, 4) & 0xFF; vt = u32(led, 8)
    P = np.stack([f32(led, 0x2C), f32(led, 0x30), f32(led, 0x34)], -1).astype(np.float64)
    sp = np.linalg.norm(np.diff(P, axis=0), axis=-1) * 60
    same = (vt[1:] == vt[:-1]) & (hdr[1:] == hdr[:-1])
    ok = same & (sp >= 400) & (sp <= 6000) & np.isfinite(sp)
    F, NL = ok.shape
    for i in range(NL):
        o = ok[:, i]; f = 0
        while f < F:
            if o[f]:
                g = f
                while g < F and o[g]: g += 1
                if g - f >= 5:
                    c = int(vt[f, i]); h = int(hdr[f, i])
                    if h != 1:
                        # nearest player at start (holder/thrower?)
                        dd = np.hypot(pos[f, :, 0] - P[f, i, 0], pos[f, :, 2] - P[f, i, 2])
                        runs[(h, c)].append((L, i, f, g - f, float(np.median(sp[f:g, i])), float(P[f:g, i, 1].max()), float(dd.min())))
                f = g
            else:
                f += 1
for (h, c), r in sorted(runs.items(), key=lambda kv: -len(kv[1])):
    print(f"hdr{h} {c:#010x} runs={len(r):4d} len med={np.median([x[3] for x in r]):4.0f} spd med={np.median([x[4] for x in r]):5.0f} "
          f"ymax med={np.median([x[5] for x in r]):5.0f} nearest-player-at-start med={np.median([x[6] for x in r]):5.0f} ex={r[0][:4]}")
