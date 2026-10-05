"""Reconcile melee signals: P+0x414 (attack-data ptr, mine) vs P+0x124 byte1 (player_state hitbox flag),
plus P+0x1AC hit sphere. P = PLAYER_MAT - 0x490 (same base in both reports)."""
import numpy as np
from collections import Counter
from common import *
def run_start(on, f):
    g = f
    while g > 0 and on[g - 1]: g -= 1
    return g
tot = Counter(); lead = {"414": [], "124": []}; sph = []; base = []; desc = Counter(); both_on = []
for cap in ("Afull", "Dpobj"):
    d = dict(np.load(f"{HERE}/../cap/{cap}/cap.npz")); P = np.load(f"{HERE}/../cap/{cap}/pobj.npz")["pobj"]
    hp, hs, st, pos = d["hp"], d["hsrc"], d["st"], d["pos"].astype(float)
    s414 = u32(P, 0x414) != 0; s124 = ((u32(P, 0x124) >> 8) & 0xFF) != 0
    C = np.stack([f32(P, 0x1AC), f32(P, 0x1B0), f32(P, 0x1B4)], -1).astype(float); R = f32(P, 0x1B8).astype(float)
    both_on.append((s414.mean(), s124.mean(), (s124 & ~s414).mean(), (s414 & ~s124).mean()))
    desc.update((int(b1) & 0xFF, int(b0)) for b1, b0 in zip(((u32(P, 0x124) >> 8)[s124]).ravel(), P[:, :, 0x134][s124].ravel()))
    for f in range(2, len(hp)):
        for k in range(4):
            if not (0.5 < hp[f-1, k] - hp[f, k] < 900): continue
            s = seat_of(int(hs[f, k]))
            if s is None or s == k: continue
            tot["hits"] += 1
            for nm, sig in (("414", s414), ("124", s124)):
                on = sig[:, s]
                w = [g for g in (f, f - 1, f - 2) if on[g]]
                if w:
                    tot[nm] += 1; lead[nm].append(f - run_start(on, w[0]))
            if s124[f-2:f+1, s].any():
                g = max(g for g in (f-2, f-1, f) if s124[g, s])
                dist = np.linalg.norm(C[g, s] - pos[f-1, k]); sph.append((dist, R[g, s], np.hypot(*(C[g, s] - pos[g, s])[[0, 2]])))
                base.append(np.linalg.norm(pos[f-1, s] - pos[f-1, k]))
print("melee hits:", tot["hits"])
for nm in ("414", "124"):
    L = np.array(lead[nm])
    print(f"P+0x{nm}: on within f-2..f for {tot[nm]}/{tot['hits']}; frames from window open to hit: median {np.median(L):.0f}, p10 {np.percentile(L,10):.0f}, p90 {np.percentile(L,90):.0f}")
for i, cap in enumerate(("Afull", "Dpobj")):
    a, b, c, e = both_on[i]
    print(f"{cap}: duty 414 {a:.1%}, 124 {b:.1%}; 124-without-414 {c:.1%}, 414-without-124 {e:.1%} of seat-frames")
S = np.array(sph); B = np.array(base)
print(f"sphere: n={len(S)} radius med {np.median(S[:,1]):.0f} (range {S[:,1].min():.0f}-{S[:,1].max():.0f}); centre->victim pos med {np.median(S[:,0]):.0f} "
      f"(p90 {np.percentile(S[:,0],90):.0f}); centre - attacker xz med {np.median(S[:,2]):.0f}; attacker->victim med {np.median(B):.0f}; "
      f"centre->victim <= radius+60: {(S[:,0] <= S[:,1] + 60).mean():.0%}")
print("0x124 byte1 values while on (with 0x134 byte0):", desc.most_common(8))
