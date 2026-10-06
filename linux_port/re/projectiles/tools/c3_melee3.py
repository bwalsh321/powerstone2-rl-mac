import numpy as np
from collections import Counter
from common import *
d = dict(np.load(f"{HERE}/../cap/Afull/cap.npz")); P = np.load(f"{HERE}/../cap/Afull/pobj.npz")["pobj"]
st = d["st"]; hp = d["hp"]; hs = d["hsrc"]
w = u32(P, 0x414)
for s in range(4):
    a7 = np.isin(st[:, s], [7, 8, 9, 10, 11, 12, 26])
    print(f"seat{s}: attack-state frames {a7.sum()}, of which 0x414 on {(a7 & (w[:, s] != 0)).sum()}")
# offset of hit within window + bytes that change exactly within window (active sub-window?)
pos_in = []
for f in range(1, len(hp)):
    for k in range(4):
        if 0.5 < hp[f-1, k] - hp[f, k] < 900:
            s = seat_of(int(hs[f, k]))
            if s is None or s == k: continue
            g = f
            while g > 0 and w[g-1, s] != 0: g -= 1
            e = f
            while e < len(w) and w[e, s] != 0: e += 1
            pos_in.append((f - g, e - g, hex(int(w[f, s]))))
print("hit at frame-in-window / window length / descriptor:", pos_in[:40])
