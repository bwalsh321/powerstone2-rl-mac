import numpy as np
from common import *
from v4rule import v4_reports
d = load("A"); led = d["ledger"]; pos = d["pos"].astype(float)
hit, thr, P = v4_reports(led, pos); vt = u32(led, 8)
V = np.stack([f32(led, 0x50), f32(led, 0x54), f32(led, 0x58)], -1) * 60
for i in range(thr.shape[1]):
    t = thr[:, i]
    if not t.any() or int(vt[np.argmax(t), i]) != 0x0c0f1688: continue
    f = int(np.argmax(t)); e = f
    while e < len(t) and t[e]: e += 1
    for g in list(range(f, min(e, f + 12), 2)) + [e - 3, e - 1]:
        dp = (P[g + 1, i] - P[g, i]) * 60
        print(i, g, "pos", np.round(P[g, i]), "vel50", np.round(V[g, i]), "dpos", np.round(dp), "hdr", int(u32(led[g, i], 4)) & 0xff)
    break
