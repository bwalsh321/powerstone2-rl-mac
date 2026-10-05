"""Category-1 classes: instance counts per lineup (to split ownerless classes by character)."""
import numpy as np
from collections import Counter, defaultdict
from common import *
cnt = defaultdict(Counter); own = defaultdict(Counter)
for L in LINEUPS:
    d = load(L); led = d["ledger"]; names = LINEUPS[L]
    hdr = u32(led, 4) & 0xFF; vt = u32(led, 8)
    for i in range(led.shape[1]):
        on = hdr[:, i] == 1
        st = np.flatnonzero(on & ~np.r_[False, on[:-1]] | (on & np.r_[False, vt[1:, i] != vt[:-1, i]]))
        for f in st:
            c = int(vt[f, i]); cnt[c][L] += 1
            s, _ = owner_chain(led[f], i); own[c][names[s] if s is not None else "-"] += 1
for c in sorted(cnt):
    print(f"{c:#010x} " + " ".join(f"{L}:{cnt[c][L]:3d}" for L in LINEUPS) + f"  owners={dict(own[c])}")
