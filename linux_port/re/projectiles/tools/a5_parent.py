"""For ownerless category-1 classes: follow pointers into the ledger (one hop) and look for a player owner."""
import numpy as np, sys
from collections import Counter, defaultdict
from common import *
want = [int(x, 16) for x in sys.argv[1:]]
res = defaultdict(lambda: defaultdict(Counter)); n = Counter()
for L in "ABCD":
    d = load(L); led = d["ledger"]; names = LINEUPS[L]
    F, NL, LB = led.shape
    hdr = u32(led, 4) & 0xFF; vt = u32(led, 8)
    for i in range(NL):
        for f in np.flatnonzero((hdr[:, i] == 1) & np.isin(vt[:, i], want))[::5]:
            c = int(vt[f, i]); n[c] += 1
            w = led[f, i][:LB].view("<u4")
            for j, v in enumerate(w):
                v = int(v) & 0x0FFFFFFF
                k, r = lslot(v)
                if k is None or k >= NL or k == i: continue
                pb = led[f, k]
                ow = seat_of(int(u32(pb, 0x14)))
                tag = f"slot+{r:#x} vt={int(u32(pb,8)):#x} hdr={int(u32(pb,4))&0xff} own={names[ow] if ow is not None else '-'}"
                res[c][j * 4][tag] += 1
for c in want:
    print(f"{c:#x} samples={n[c]}")
    for o, cn in sorted(res[c].items(), key=lambda kv: -sum(kv[1].values()))[:5]:
        print(f"   +{o:#x}: {cn.most_common(3)}")
