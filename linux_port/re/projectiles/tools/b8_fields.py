"""Category-1 objects: per class, float fields that are constant across instances (radius/damage candidates) and
fields that equal the per-frame position delta (velocity candidates)."""
import numpy as np
from collections import defaultdict
from common import *
CL = [0x0c122fec, 0x0c143608, 0x0c12fb0a, 0x0c12cf48, 0x0c139010, 0x0c132d70, 0x0c162dac, 0x0c12da56, 0x0c143118, 0x0c127448, 0x0c16b9d2]
samp = defaultdict(list); vel = defaultdict(list)
for L in LINEUPS:
    d = load(L); led = d["ledger"]
    hdr = u32(led, 4) & 0xFF; vt = u32(led, 8)
    for f in range(1, len(led) - 1, 2):
        for i in np.flatnonzero((hdr[f] == 1) & np.isin(vt[f], CL)):
            c = int(vt[f, i])
            if vt[f+1, i] != c: continue
            b = led[f, i]; samp[c].append(b)
            dp = np.array([f32(led[f+1, i], o) - f32(b, o) for o in (0x2C, 0x30, 0x34)], float)
            vel[c].append((dp, b))
for c in CL:
    S = np.array(samp[c]);
    if not len(S): continue
    fl = S[:, :0x100].copy().view("<f4")  # [n, 64]
    line = []
    for j in range(64):
        x = fl[:, j]; ok = np.isfinite(x)
        if ok.mean() < .95: continue
        x = x[ok]
        if np.std(x) < 1e-3 and 1 <= abs(np.median(x)) <= 2000: line.append(f"+{j*4:#x}={np.median(x):.1f}")
    # velocity candidates: field triple (j,j+1,j+2) ~ dp per frame
    dv = np.array([v[0] for v in vel[c]]); B = np.array([v[1] for v in vel[c]])[:, :0x100].copy().view("<f4")
    vc = []
    for j in range(0, 62):
        if j*4 in (0x2C,): continue
        e = np.nanmedian(np.abs(B[:, j:j+3] - dv), axis=0)
        mag = np.nanmedian(np.abs(dv))
        if np.all(e < 0.05 * max(mag, 1)) and mag > 1: vc.append(f"+{j*4:#x}")
    print(f"{c:#x} n={len(S)} const: {' '.join(line[:14])}\n      vel-per-frame triple at: {vc}")
