"""Class table for PROJECTILES.md: category-1 + thrown classes, from all captures."""
import numpy as np
from collections import Counter, defaultdict
from common import *
from proposed_labels import LABELS, RADIUS
inst = defaultdict(list); hits = Counter(); dmg = Counter()
for L in LINEUPS:
    d = load(L); led = d["ledger"]; names = LINEUPS[L]; hp, hs = d["hp"], d["hsrc"]
    hdr = u32(led, 4) & 0xFF; vt = u32(led, 8)
    V = np.stack([f32(led, 0x50), f32(led, 0x54), f32(led, 0x58)], -1).astype(float) * 60
    sp = np.linalg.norm(V, axis=-1)
    for i in range(led.shape[1]):
        on = hdr[:, i] == 1
        st = np.flatnonzero(on & ~np.r_[False, on[:-1]] | (on & np.r_[False, vt[1:, i] != vt[:-1, i]]))
        for f in st:
            c = int(vt[f, i]); e = f
            while e < len(on) and on[e] and vt[e, i] == c: e += 1
            s, _ = owner_chain(led[f], i)
            s2 = sp[f:e, i]; s2 = s2[np.isfinite(s2)]
            inst[c].append((L, names[s] if s is not None else "-", e - f, float(np.median(s2)) if len(s2) else 0.0, float(s2.max()) if len(s2) else 0.0))
    for f in range(1, len(hp)):
        for k in range(4):
            if 0.5 < hp[f-1, k] - hp[f, k] < 900:
                p = int(hs[f, k]); i, r = lslot(p)
                if seat_of(p) is None and i is not None and i < led.shape[1] and hdr[f, i] == 1:
                    hits[int(vt[f, i])] += 1; dmg[int(vt[f, i])] += hp[f-1, k] - hp[f, k]
print("| vtable | label | owner (resolved via +0x14) | lineups | n | life med/max (f) | speed med/max (u/s) | radius +0x19C | hits / dmg | conf |")
print("|---|---|---|---|---|---|---|---|---|---|")
for c in sorted(inst, key=lambda c: -len(inst[c])):
    r = inst[c]; own = Counter(x[1] for x in r); lu = "".join(sorted(set(x[0] for x in r)))
    life = [x[2] for x in r]
    conf = "high" if (len(r) >= 10 and hits[c] > 0) else ("med" if len(r) >= 4 else "low")
    print(f"| `{c:#010x}` | {LABELS.get(c, '?')} | {', '.join(f'{k} {v}' for k, v in own.most_common(2))} | {lu} | {len(r)} | {np.median(life):.0f}/{max(life)} | "
          f"{np.median([x[3] for x in r]):.0f}/{max(x[4] for x in r):.0f} | {RADIUS.get(c, '')} | {hits[c]} / {dmg[c]:.0f} | {conf} |")
