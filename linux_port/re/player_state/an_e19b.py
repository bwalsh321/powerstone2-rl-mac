"""Hitbox validation v2: multi-sphere list. Collision records at P+0x184 + 0x20*j (j=0 hurt cylinder,
j>=1 hit spheres), count = byte3 of P+0x184. Record layout: +0 hdr, +8 x, +0xC y, +0x10 z, +0x14 r, +0x18 h."""
import collections, sys
import numpy as np
P0 = 0x0C532498; S = 0x3938
for tag in sys.argv[1:]:
    Z = np.load(f"data_e19_{tag}.npz"); out = Z["out"]; cols = list(Z["cols"]); raw = Z["raw"]
    c = {o: i for i, o in enumerate(cols)}
    U = lambda o: out[:, :, c[o]]
    R = lambda o: raw[:, :, (o - 0x160) // 4]
    RF = lambda o: raw[:, :, (o - 0x160) // 4].view("<f4")
    N = out.shape[0]
    st = (U(0x3714) >> 8) & 0xFF; act = U(0x3818) & 0xFFFF
    flag = ((U(0x124) >> 8) & 0xFF) != 0
    cnt = (R(0x184) >> 24).astype(int); nhit = np.clip(cnt - 1, 0, 8)
    live = nhit > 0
    hp = out[:, :, c[0x160]].view("<f4"); item = U(0x376C) != 0; form = (U(0x3718) & 0x10000) != 0
    hittable = (U(0x12C) & 0xFFFF) != 0
    print(f"== {tag}: agreement 0x124-flag vs (count>1): {(flag == live).mean():.4f}; flag&!count {(flag & ~live).sum()} count&!flag {(live & ~flag).sum()}")
    hx, hy, hz, rr, hh = RF(0x18C), RF(0x190), RF(0x194), RF(0x198), RF(0x19C)
    def spheres(k, t):
        return [(RF(0x1AC + 0x20*j)[t, k], RF(0x1B0 + 0x20*j)[t, k], RF(0x1B4 + 0x20*j)[t, k], RF(0x1B8 + 0x20*j)[t, k]) for j in range(nhit[t, k])]
    def overlap(k, v, t, scale=1.0):
        for (x, y, z, r) in spheres(k, t):
            if np.hypot(x - hx[t, v], z - hz[t, v]) <= scale * (r + rr[t, v]) and abs(y - hy[t, v]) <= r + hh[t, v]: return True
        return False
    ev = collections.Counter(); unexpl = collections.Counter(); by = collections.Counter()
    for t in range(1, N):
        for v in range(4):
            d = hp[t - 1, v] - hp[t, v]
            if not (0.01 < d < 900): continue
            ev["events"] += 1
            who = [k for k in range(4) if k != v and (overlap(k, v, t) or overlap(k, v, t - 1))]
            if who:
                ev["melee_explained"] += 1; k = who[0]; by[(int(st[t, k]), "item" if item[t, k] else "-", "form" if form[t, k] else "-")] += 1
            else:
                anyl = [k for k in range(4) if k != v and (live[t, k] or live[t-1, k])]
                unexpl["someone live (no overlap)" if anyl else "no live hitbox anywhere (projectile/object/stage)"] += 1
    print("  damage events:", dict(ev)); print("  explained by (state,item,form):", dict(by.most_common(12))); print("  unexplained:", dict(unexpl))
    conf = collections.Counter(); cat = collections.defaultdict(collections.Counter)
    for k in range(4):
        t = 0
        while t < N:
            if live[t, k]:
                s = t
                while t < N and live[t, k]: t += 1
                cc = ("item" if item[s, k] else "-") + "/" + ("form" if form[s, k] else "-") + f"/s{st[s, k]}"
                for v in range(4):
                    if v == k: continue
                    pred = any(overlap(k, v, q) and hittable[q, v] for q in range(s, t))
                    seg = hp[max(s - 1, 0):min(t + 2, N), v]
                    actual = bool((np.diff(seg) < -0.01).any())
                    conf[(pred, actual)] += 1; cat[cc][(pred, actual)] += 1
            else: t += 1
    tp, fp, fn, tn = conf[(True, True)], conf[(True, False)], conf[(False, True)], conf[(False, False)]
    print(f"  window-level: TP {tp} FP {fp} FN {fn} TN {tn} precision {tp/max(1,tp+fp):.3f} recall {tp/max(1,tp+fn):.3f}")
    for cc, m in sorted(cat.items(), key=lambda kv: -sum(kv[1].values()))[:12]:
        print(f"    {cc:16s} TP {m[(True,True)]:4d} FP {m[(True,False)]:4d} FN {m[(False,True)]:4d} TN {m[(False,False)]:5d}")
    print("  hit-sphere count distribution on live frames:", dict(collections.Counter(nhit[live].tolist())))

# ---- FN inspection (run with FN=1)
import os
if os.environ.get("FN"):
    for tag in sys.argv[1:]:
        Z = np.load(f"data_e19_{tag}.npz"); out = Z["out"]; cols = list(Z["cols"]); raw = Z["raw"]
        c = {o: i for i, o in enumerate(cols)}
        U = lambda o: out[:, :, c[o]]; RF = lambda o: raw[:, :, (o - 0x160) // 4].view("<f4")
        R = lambda o: raw[:, :, (o - 0x160) // 4]
        N = out.shape[0]; st = (U(0x3714) >> 8) & 0xFF; act = U(0x3818) & 0xFFFF
        nhit = np.clip((R(0x184) >> 24).astype(int) - 1, 0, 8); live = nhit > 0
        hp = out[:, :, c[0x160]].view("<f4")
        hx, hy, hz, rr, hh = RF(0x18C), RF(0x190), RF(0x194), RF(0x198), RF(0x19C)
        n = 0
        for k in range(4):
            t = 0
            while t < N:
                if live[t, k]:
                    s = t
                    while t < N and live[t, k]: t += 1
                    for v in range(4):
                        if v == k: continue
                        seg = hp[max(s - 1, 0):min(t + 2, N), v]
                        dt = np.nonzero(np.diff(seg) < -0.01)[0]
                        if not len(dt): continue
                        best = 9e9
                        for q in range(s, t):
                            for j in range(nhit[q, k]):
                                x, y, z, r = (RF(0x1AC + 0x20*j)[q, k], RF(0x1B0 + 0x20*j)[q, k], RF(0x1B4 + 0x20*j)[q, k], RF(0x1B8 + 0x20*j)[q, k])
                                m = np.hypot(x - hx[q, v], z - hz[q, v]) / (r + rr[q, v]); my = abs(y - hy[q, v]) / (r + hh[q, v])
                                best = min(best, max(m, my))
                        if best > 1.0 and n < 25:
                            n += 1
                            td = max(s - 1, 0) + dt[0] + 1
                            others = [kk for kk in range(4) if kk not in (k, v) and live[max(td-1,0):td+1, kk].any()]
                            print(f"{tag} FN att P{k+1} s{st[s,k]} act {act[s,k]:x} win {s}-{t} victim P{v+1} dmg@{td} victim st {st[td,v]} best margin {best:.2f} others-live {others} dmg {seg[0]-seg[-1]:.1f}")
                else: t += 1
