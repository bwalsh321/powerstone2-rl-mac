import numpy as np
from collections import Counter, defaultdict
from common import *
res = defaultdict(Counter); paths = defaultdict(Counter)
for L in LINEUPS:
    d = load(L); led = d["ledger"]; names = LINEUPS[L]
    hdr = u32(led, 4) & 0xFF; vt = u32(led, 8)
    F, NL, _ = led.shape
    for i in range(NL):
        on = hdr[:, i] == 1
        st = np.flatnonzero(on & ~np.r_[False, on[:-1]] | (on & np.r_[False, vt[1:, i] != vt[:-1, i]]))
        for f in st:
            s, p = owner_chain(led[f], i)
            c = int(vt[f, i])
            res[c][names[s] if s is not None else "-"] += 1
            paths[c][" > ".join(p)] += 1
for c in sorted(res, key=lambda c: -sum(res[c].values())):
    print(f"{c:#010x} {dict(res[c])}  via {paths[c].most_common(2)}")
