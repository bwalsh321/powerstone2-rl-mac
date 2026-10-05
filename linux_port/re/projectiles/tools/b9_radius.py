import numpy as np
from collections import defaultdict
from common import *
d = dict(np.load(f"{HERE}/../cap/Afull/cap.npz")); led = np.load(f"{HERE}/../cap/Afull/ledger.npz")["ledger"]
hdr = u32(led, 4) & 0xFF; vt = u32(led, 8)
S = defaultdict(list)
for f in range(0, len(led), 2):
    for i in np.flatnonzero(hdr[f] == 1):
        S[int(vt[f, i])].append(led[f, i])
print({hex(c): len(v) for c, v in S.items()})
cls = [c for c in S if len(S[c]) >= 10]
med = {}
for c in cls:
    A = np.array(S[c])[:, :1072 - 1072 % 4].copy().view("<f4")
    m = np.nanmedian(A, axis=0); sd = np.nanstd(A, axis=0); fin = np.isfinite(A).mean(0)
    med[c] = (m, sd, fin)
n = len(med[cls[0]][0])
for j in range(n):
    vals = []
    ok = True
    for c in cls:
        m, sd, fin = med[c]
        if fin[j] < 0.99 or sd[j] > 1e-3 * max(1, abs(m[j])) or not (2 <= abs(m[j]) <= 2000): ok = False; break
        vals.append(m[j])
    if ok and len(set(np.round(vals, 2))) > 1:
        print(f"+{j*4:#05x}: " + "  ".join(f"{c:#x}={v:.1f}" for c, v in zip(cls, vals)))
print("---- per-class constant floats (2..2000)")
for c in cls:
    m, sd, fin = med[c]
    idx = [j for j in range(n) if fin[j] > .99 and sd[j] <= 1e-3 * max(1, abs(m[j])) and 2 <= abs(m[j]) <= 2000]
    print(f"{c:#x}: " + " ".join(f"+{j*4:#x}={m[j]:.1f}" for j in idx[:40]))
