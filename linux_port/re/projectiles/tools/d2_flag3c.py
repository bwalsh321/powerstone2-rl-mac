import numpy as np
from common import *
for c in (0x0c0f1688, 0x0c0c9810, 0x0c0ca928, 0x0c0c9f50):
    R = {"fly": [], "stale": [], "rest": [], "slowmove": []}
    for L in LINEUPS:
        d = load(L); led = d["ledger"]; vt = u32(led, 8); hdr = u32(led, 4) & 0xFF
        P = np.stack([f32(led, 0x2C), f32(led, 0x30), f32(led, 0x34)], -1).astype(float)
        V = np.stack([f32(led, 0x50), f32(led, 0x54), f32(led, 0x58)], -1).astype(float)
        dp = np.zeros_like(P); dp[:-1] = P[1:] - P[:-1]
        m = (vt == c) & (hdr == 9); vn = np.linalg.norm(V, axis=-1) * 60; dn = np.linalg.norm(dp, axis=-1) * 60
        err = np.linalg.norm(dp - V, axis=-1)
        w = u32(led, 0x3C)
        R["fly"].append(w[m & (vn > 600) & (err < 0.5)]); R["stale"].append(w[m & (vn > 600) & (dn == 0)])
        R["rest"].append(w[m & (vn == 0) & (dn == 0)]); R["slowmove"].append(w[m & (dn > 0) & (dn < 600)])
    print(hex(c), {k: (len(np.concatenate(v)), f"{np.mean(np.concatenate(v) != 0) if len(np.concatenate(v)) else 0:.0%}") for k, v in R.items()})
