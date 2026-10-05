import numpy as np
from collections import Counter
from common import *
L414 = []; L124 = []; xz = []; dy = []; rr = []; stn = Counter(); fresh = []; first = []
for cap in ("Afull", "Dpobj"):
    d = dict(np.load(f"{HERE}/../cap/{cap}/cap.npz")); P = np.load(f"{HERE}/../cap/{cap}/pobj.npz")["pobj"]
    hp, hs, st, pos = d["hp"], d["hsrc"], d["st"], d["pos"].astype(float)
    w414 = u32(P, 0x414); s124 = ((u32(P, 0x124) >> 8) & 0xFF) != 0
    C = np.stack([f32(P, 0x1AC), f32(P, 0x1B0), f32(P, 0x1B4)], -1).astype(float); R = f32(P, 0x1B8).astype(float)
    stn.update(st[s124 & (w414 == 0)].tolist())
    for f in range(2, len(hp)):
        for k in range(4):
            if not (0.5 < hp[f-1, k] - hp[f, k] < 900): continue
            s = seat_of(int(hs[f, k]))
            if s is None or s == k: continue
            g = max(g for g in (f-2, f-1, f) if w414[g, s]); v = w414[g, s]; a = g
            while a > 0 and w414[a-1, s] == v: a -= 1
            b = g
            while b > 0 and s124[b-1, s] or (b == g and not s124[b, s] and b > f - 3): b -= 1
            # 124 run containing the latest on frame
            h = max(x for x in (f-2, f-1, f) if s124[x, s]); c = h
            while c > 0 and s124[c-1, s]: c -= 1
            L414.append(f - a); L124.append(f - c)
            first.append(a <= c)
            # sphere at the last live frame <= f
            cc, r = C[h, s], R[h, s]; vp = pos[min(f, h + 1), k]
            xz.append(np.hypot(cc[0] - vp[0], cc[2] - vp[2])); dy.append(cc[1] - vp[1]); rr.append(r)
            fresh.append(not np.allclose(C[h, s], C[max(c - 1, 0), s]))
L414, L124 = np.array(L414), np.array(L124); xz, dy, rr = map(np.array, (xz, dy, rr))
print(f"per-move lead (frames from this descriptor/flag turning on to the hit): 0x414 med {np.median(L414):.0f} p10 {np.percentile(L414,10):.0f} p90 {np.percentile(L414,90):.0f};"
      f" 0x124 med {np.median(L124):.0f} p10 {np.percentile(L124,10):.0f} p90 {np.percentile(L124,90):.0f}; 414 on no later than 124: {np.mean(first):.0%}")
print("lead pairs (414,124):", list(zip(L414.tolist(), L124.tolist())))
print(f"sphere xz centre->victim: med {np.median(xz):.0f} p90 {np.percentile(xz,90):.0f}; dy med {np.median(dy):.0f}; radius med {np.median(rr):.0f}; "
      f"xz<=r+50: {np.mean(xz <= rr + 50):.0%}, xz<=r+100: {np.mean(xz <= rr + 100):.0%}; centre updated when window opened: {np.mean(fresh):.0%}")
print("states where 124 on but 414 off:", stn.most_common(6))
