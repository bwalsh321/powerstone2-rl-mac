"""Pool render class co-located with a given ledger vt, per lineup (is the pool class lineup-dependent?)."""
import numpy as np, sys
from collections import Counter
from common import *
for c in [int(x, 16) for x in sys.argv[1:]]:
    for L in "ABCD":
        d = load(L); led = d["ledger"]; pact, pcls, ppos = d["pact"], d["pcls"], d["ppos"]
        vt = u32(led, 8); hdr = u32(led, 4) & 0xFF
        LP = np.stack([f32(led, 0x2C), f32(led, 0x30), f32(led, 0x34)], -1)
        cc = Counter()
        for f in range(0, len(led), 2):
            for i in np.flatnonzero((vt[f] == c) & (hdr[f] == 1)):
                live = (pact[f] & 0xFF) == 1
                dd = np.linalg.norm(ppos[f] - LP[f, i], axis=-1); dd[~live] = 1e9
                for j in np.flatnonzero(dd < 3): cc[int(pcls[f, j])] += 1
        if cc: print(f"{c:#x} lineup {L}: " + ", ".join(f"{k:#x}={v}" for k, v in cc.most_common(4)))
