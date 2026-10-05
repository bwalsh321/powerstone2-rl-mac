"""Census of what hit whom: per health drop, the source pointer (PLAYER_MAT+0x32E4) decoded."""
import sys, numpy as np
from collections import Counter, defaultdict
from common import *
tot = Counter(); byvt = defaultdict(Counter); vt_dmg = Counter(); vt_own = defaultdict(Counter)
for L in LINEUPS:
    d = load(L); hp, hs, led = d["hp"], d["hsrc"], d["ledger"]; names = LINEUPS[L]
    F = len(hp)
    for f in range(1, F):
        for k in range(4):
            drop = hp[f-1, k] - hp[f, k]
            if drop <= 0.5 or drop > 900: continue
            p = int(hs[f, k]) & 0x0FFFFFFF
            s = seat_of(p)
            if s is not None:
                tot["player(melee/body)"] += 1; byvt["PLAYER"][names[s]] += 1; vt_dmg["PLAYER"] += drop; continue
            i, r = lslot(p)
            if p == 0 or i is None or i >= led.shape[1]:
                tot[f"other {p:#x}"] += 1; continue
            b = led[f, i]
            vt = int(u32(b, 8)); own = seat_of(int(u32(b, 0x14)))
            key = f"{vt:#010x}"
            tot["ledger"] += 1; vt_dmg[key] += drop
            byvt[key][(names[own] if own is not None else "none")] += 1
            vt_own[key][f"{L}{i}"] += 1
print(tot.most_common(12))
for key, c in sorted(byvt.items(), key=lambda kv: -sum(kv[1].values())):
    print(f"{key}: hits={sum(c.values()):4d} dmg={vt_dmg[key]:7.0f} owners={dict(c)}")
