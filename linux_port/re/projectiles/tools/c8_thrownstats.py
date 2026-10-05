import numpy as np
from collections import Counter
from common import *
from v4rule import v4_reports
runs = Counter(); frames = Counter(); hitruns = Counter()
for L in LINEUPS:
    d = load(L); led = d["ledger"]; pos = d["pos"].astype(float); hp, hs = d["hp"], d["hsrc"]
    hit, thr, P = v4_reports(led, pos); vt = u32(led, 8)
    hitslots = set()
    for f in range(1, len(hp)):
        for k in range(4):
            if 0.5 < hp[f-1, k] - hp[f, k] < 900:
                i, r = lslot(int(hs[f, k]))
                if i is not None and i < led.shape[1]: hitslots.add((i, f))
    for i in range(thr.shape[1]):
        t = thr[:, i]; st = np.flatnonzero(t & ~np.r_[False, t[:-1]])
        for f in st:
            e = f
            while e < len(t) and t[e]: e += 1
            c = hex(int(vt[f, i])); runs[c] += 1; frames[c] += e - f
            if any((i, g) in hitslots for g in range(f, min(e + 6, len(t)))): hitruns[c] += 1
for c in runs: print(f"{c}: thrown-flight runs={runs[c]:4d} mean len={frames[c]/runs[c]:5.1f} f, runs ending in a hit within 6 f: {hitruns[c]}")
