"""For each fast pool class (>=700 u/s, live low byte 1), which ledger object sits at the same position (<3u)?"""
import numpy as np
from collections import Counter, defaultdict
from common import *
m = defaultdict(Counter); npos = Counter()
for L in LINEUPS:
    d = load(L); led = d["ledger"]; pact, pcls, ppos = d["pact"], d["pcls"], d["ppos"]
    hdr = u32(led, 4) & 0xFF; vt = u32(led, 8)
    LP = np.stack([f32(led, 0x2C), f32(led, 0x30), f32(led, 0x34)], -1)
    for f in range(3, len(pact), 3):
        live = ((pact[f] & 0xFF) == 1) & ((pact[f-3] & 0xFF) == 1) & (pcls[f] == pcls[f-3])
        sp = np.linalg.norm(ppos[f] - ppos[f-3], axis=-1) * 20
        for j in np.flatnonzero(live & (sp >= 700) & (sp < 8000)):
            c = int(pcls[f, j]); npos[c] += 1
            dd = np.linalg.norm(LP[f] - ppos[f, j], axis=-1)
            dd = np.where(np.isfinite(dd), dd, 1e9); k = int(np.argmin(dd))
            m[c][(int(hdr[f, k]), int(vt[f, k])) if dd[k] < 3 else ("none", 0)] += 1
for c in sorted(npos, key=lambda c: -npos[c])[:45]:
    print(f"pool {c:#010x} fast={npos[c]:4d} -> " + ", ".join(f"{k[0]}:{k[1]:#x}={v}" for k, v in m[c].most_common(3)))
