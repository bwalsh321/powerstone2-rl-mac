"""Hits whose source is a hdr-9 (item family) ledger object: speed of the source over the 6 frames before the hit,
and distance to the nearest NON-victim player (held swing ~<100u vs thrown >150u)."""
import numpy as np
from collections import Counter
from common import *
rows = []
for L in LINEUPS:
    d = load(L); hp, hs, led, pos = d["hp"], d["hsrc"], d["ledger"], d["pos"]
    for f in range(7, len(hp)):
        for k in range(4):
            if not (0.5 < hp[f-1, k] - hp[f, k] < 900): continue
            p = int(hs[f, k])
            if seat_of(p) is not None: continue
            i, r = lslot(p)
            if i is None or i >= led.shape[1]: continue
            if int(u32(led[f, i], 4)) & 0xFF != 9: continue
            P = np.array([[float(f32(led[g, i], o)) for o in (0x2C, 0x30, 0x34)] for g in range(f - 6, f + 1)])
            sp = np.linalg.norm(np.diff(P, axis=0), axis=1) * 60
            others = [j for j in range(4) if j != k]
            dn = min(np.hypot(pos[f, j, 0] - P[-1, 0], pos[f, j, 2] - P[-1, 2]) for j in others)
            rows.append((L, f, k, hex(int(u32(led[f, i], 8))), float(np.median(sp)), float(P[-1, 1]), float(dn), hp[f-1,k]-hp[f,k]))
print(len(rows))
for r in rows: print(r[0], r[1], LINEUPS[r[0]][r[2]], r[3], f"spd={r[4]:.0f} y={r[5]:.0f} nearest_other={r[6]:.0f} dmg={r[7]:.0f}")
