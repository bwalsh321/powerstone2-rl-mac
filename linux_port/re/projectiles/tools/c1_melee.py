"""Melee hitbox hunt in player objects (cap/Afull pobj): for attacker seat s, bytes that are 'on' at frames where s
lands a melee hit (victim hsrc -> s's object) vs frames where s is idle/walking (state 0/1)."""
import numpy as np
from collections import Counter
from common import *
d = dict(np.load(f"{HERE}/../cap/Afull/cap.npz")); P = np.load(f"{HERE}/../cap/Afull/pobj.npz")["pobj"]
hp, hs, st = d["hp"], d["hsrc"], d["st"]
hitf = {s: [] for s in range(4)}
for f in range(1, len(hp)):
    for k in range(4):
        if 0.5 < hp[f-1, k] - hp[f, k] < 900:
            s = seat_of(int(hs[f, k]))
            if s is not None and s != k: hitf[s].append(f)
print({s: len(v) for s, v in hitf.items()})
res = []
LB = P.shape[2]
for s in range(4):
    H = sorted(set(hitf[s]) | set(f - 1 for f in hitf[s]))
    I = np.flatnonzero(np.isin(st[:, s], [0, 1]))
    if len(H) < 4: continue
    ph = P[H, s]; pi = P[I, s]
    for o in range(LB):
        mi = Counter(pi[:, o].tolist()).most_common(1)[0]
        if mi[1] / len(pi) < 0.97: continue          # stable when idle
        on = (ph[:, o] != mi[0]).mean()
        if on > 0.9: res.append((s, o, on, mi[0]))
cnt = Counter(o for s, o, _, _ in res)
print("offsets 'on' during hits for >=3 seats (stable when idle):")
for o, c in sorted(cnt.items()):
    if c >= 3:
        ex = [(s, round(on, 2), idle) for s, oo, on, idle in res if oo == o]
        print(f"  +{o:#06x} (PLAYER_MAT{o-0x490:+#x}) seats={c} {ex}")
