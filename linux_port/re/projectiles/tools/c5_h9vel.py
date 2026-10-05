import numpy as np
from common import *
for c in (0x0c0f1688, 0x0c0c9810, 0x0c0f18d4, 0x0c0cbcb0):
    errs = {}; n = 0
    for L in LINEUPS:
        d = load(L); led = d["ledger"]; vt = u32(led, 8); hdr = u32(led, 4) & 0xFF
        P = np.stack([f32(led, 0x2C), f32(led, 0x30), f32(led, 0x34)], -1).astype(float)
        dp = P[1:] - P[:-1]
        m = (vt[1:] == c) & (vt[:-1] == c) & (hdr[:-1] == 9) & (np.linalg.norm(dp, axis=-1) * 60 > 600) & (np.linalg.norm(dp, axis=-1) * 60 < 6000)
        fi = np.argwhere(m)
        n += len(fi)
        for off in range(0x38, 0x100, 4):
            if off + 12 > led.shape[2]: break
            V = np.stack([f32(led[:-1], off), f32(led[:-1], off+4), f32(led[:-1], off+8)], -1).astype(float)
            e = np.abs(V[m] - dp[m]).max(-1)
            errs.setdefault(off, []).append(e)
    best = sorted(((np.median(np.concatenate(v)), o) for o, v in errs.items() if sum(len(x) for x in v)), key=lambda t: t[0])[:3]
    print(f"{c:#x} moving samples={n} best velocity-triple offsets (median abs err u/frame): {[(hex(o), round(e, 3)) for e, o in best]}")
