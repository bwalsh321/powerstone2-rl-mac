"""hdr-9 objects: byte fields separating TRUE flight (pos delta == +0x50 velocity, nonzero) from STALE velocity
(pos frozen while +0x50 nonzero) and from held/rest."""
import numpy as np
from collections import Counter
from common import *
for c in (0x0c0f1688, 0x0c0c9810):
    fly, stale, rest = [], [], []
    for L in LINEUPS:
        d = load(L); led = d["ledger"]; vt = u32(led, 8); hdr = u32(led, 4) & 0xFF
        P = np.stack([f32(led, 0x2C), f32(led, 0x30), f32(led, 0x34)], -1).astype(float)
        V = np.stack([f32(led, 0x50), f32(led, 0x54), f32(led, 0x58)], -1).astype(float)
        dp = np.zeros_like(P); dp[:-1] = P[1:] - P[:-1]
        m = (vt == c) & (hdr == 9)
        vn = np.linalg.norm(V, axis=-1); dn = np.linalg.norm(dp, axis=-1); err = np.linalg.norm(dp - V, axis=-1)
        fly.append(led[m & (vn * 60 > 600) & (err < 0.5)])
        stale.append(led[m & (vn * 60 > 600) & (dn == 0)])
        rest.append(led[m & (vn == 0) & (dn == 0)])
    fly, stale, rest = (np.concatenate(x) for x in (fly, stale, rest))
    print(f"{c:#x}: fly={len(fly)} stale={len(stale)} rest={len(rest)}")
    for o in range(0x100):
        if o in range(0x2C, 0x38) or o in range(0x50, 0x5C): continue
        a, b, r = (Counter(x[:, o].tolist()).most_common(1)[0] if len(x) else (None, 0) for x in (fly, stale, rest))
        sa, sb = a[1] / max(1, len(fly)), b[1] / max(1, len(stale))
        if a[0] != b[0] and sa > 0.75 and sb > 0.75:
            print(f"   +{o:#04x}: fly={a[0]:#04x}({sa:.0%}) stale={b[0]:#04x}({sb:.0%}) rest={r[0]}({r[1]/max(1,len(rest)):.0%})")
