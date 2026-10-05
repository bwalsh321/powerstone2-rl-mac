"""E18 v2: multi-sphere model per character and move (P1 attacker, P2 Falcon dummy)."""
import collections
from an_e18_lib import *
NAMES = {0: "Falcon", 1: "Ryoma", 2: "WangTang", 3: "Jack", 4: "Gunrock", 5: "Galuda", 6: "Ayame", 7: "Rouge", 8: "Pete", 9: "Gourmand", 10: "Julia", 11: "Accel", 14: "Mel", 15: "Pride"}
per_char = collections.defaultdict(collections.Counter); per_move = collections.defaultdict(collections.Counter)
dmg_src = collections.Counter(); timing = collections.Counter(); active_len = collections.defaultdict(list)
for i, (cid, mv, D) in enumerate(RUNS):
    n = LENS[i]
    cnt = (W(i, 0, 0x184) >> 24).astype(int); nhit = np.clip(cnt - 1, 0, 3)  # only 3 spheres captured (to 0x200)
    live = cnt > 1
    hp = F(i, 1, 0x160); dmg = np.r_[False, np.diff(hp) < -0.01]
    hx, hy, hz, rr, hh = F(i, 1, 0x18C), F(i, 1, 0x190), F(i, 1, 0x194), F(i, 1, 0x198), F(i, 1, 0x19C)
    hittable = (W(i, 1, 0x12C) & 0xFFFF) != 0
    def ov(t):
        for j in range(min(nhit[t], 3)):
            x, y, z, r = F(i, 0, 0x1AC+0x20*j)[t], F(i, 0, 0x1B0+0x20*j)[t], F(i, 0, 0x1B4+0x20*j)[t], F(i, 0, 0x1B8+0x20*j)[t]
            if np.hypot(x-hx[t], z-hz[t]) <= r + rr[t] and abs(y-hy[t]) <= r + hh[t]: return True
        return False
    for t in np.nonzero(dmg)[0]:
        st = int(B(i, 0, 0x3715)[t]); a = int(W(i, 0, 0x3818)[t] & 0xFFFF)
        if live[max(0, t-1):t+1].any(): dmg_src["P1 hit-sphere live"] += 1
        else: dmg_src[f"no sphere: P1 s{st} act {a:x} ({NAMES[int(cid)]} {mv})"] += 1
    t = 0
    while t < n:
        if live[t]:
            s = t
            while t < n and live[t]: t += 1
            pred = any(ov(q) and hittable[q] for q in range(s, t))
            actual = dmg[s:min(t+2, n)].any()
            per_char[NAMES[int(cid)]][(pred, actual)] += 1; per_move[mv][(pred, actual)] += 1
            if actual: timing[int(np.argmax(dmg[s:min(t+2, n)]))] += 1
            active_len[mv].append(t - s)
        else: t += 1
def fmt(c): return f"TP {c[(True,True)]:3d} FP {c[(True,False)]:2d} FN {c[(False,True)]:2d} TN {c[(False,False)]:3d}"
print("damage events by source:", dict(dmg_src.most_common()))
print("frames from hit-sphere appearance to damage:", dict(sorted(timing.items())))
tot = collections.Counter()
for k, c in per_char.items(): print(f"  {k:9s} {fmt(c)}"); tot.update(c)
for k, c in per_move.items(): print(f"  move {k:6s} {fmt(c)}  median active frames {np.median(active_len[k]):.0f}")
print("TOTAL", fmt(tot), f"precision {tot[(True,True)]/max(1,tot[(True,True)]+tot[(True,False)]):.3f} recall {tot[(True,True)]/max(1,tot[(True,True)]+tot[(False,True)]):.3f}")
