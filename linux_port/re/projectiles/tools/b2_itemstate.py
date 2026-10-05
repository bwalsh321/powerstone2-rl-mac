"""Item ledger objects (hdr 9, vt in ITEM family): which byte fields separate moving vs resting vs 'held'.
held proxy = within 150u (xz) of a player and y > 30; rest = speed 0 and y < 60; fly = 400..6000 u/s and no player within 150u."""
import numpy as np
from collections import Counter, defaultdict
from common import *
FAM = [0x0c0c9810, 0x0c0ca928, 0x0c0c9f50, 0x0c0ca5d8, 0x0c0cacac]
B = {"rest": [], "fly": [], "held": []}
for L in "ABCD":
    d = load(L); led = d["ledger"]; pos = d["pos"]
    hdr = u32(led, 4) & 0xFF; vt = u32(led, 8)
    P = np.stack([f32(led, 0x2C), f32(led, 0x30), f32(led, 0x34)], -1).astype(float)
    for f in range(1, len(led) - 1, 2):
        for i in np.flatnonzero((hdr[f] == 9) & np.isin(vt[f], FAM)):
            if vt[f-1, i] != vt[f, i]: continue
            sp = np.linalg.norm(P[f, i] - P[f-1, i]) * 60
            dmin = np.min(np.hypot(pos[f, :, 0] - P[f, i, 0], pos[f, :, 2] - P[f, i, 2]))
            if sp == 0 and P[f, i, 1] < 60 and dmin > 150: B["rest"].append(led[f, i])
            elif 400 <= sp <= 6000 and dmin > 150: B["fly"].append(led[f, i])
            elif dmin < 60 and sp < 1: B["held"].append(led[f, i])
for k in B: B[k] = np.array(B[k]); print(k, B[k].shape)
LB = B["rest"].shape[1]
for o in range(0, LB):
    vals = {k: Counter(B[k][:, o].tolist()) for k in B if len(B[k])}
    top = {k: v.most_common(1)[0] for k, v in vals.items()}
    shares = {k: top[k][1] / len(B[k]) for k in top}
    if len(set(t[0] for t in top.values())) > 1 and min(shares.values()) > 0.7 and o not in range(0x2C, 0x38):
        print(f"+{o:#04x}: " + "  ".join(f"{k}={top[k][0]:#04x}({shares[k]:.0%})" for k in top))
