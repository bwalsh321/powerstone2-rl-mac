"""Hitbox validation in 4P COM fights (E19)."""
import collections, sys
import numpy as np
P0 = 0x0C532498; S = 0x3938
def seat(p):
    d = int(p) - P0
    return d // S if p and d >= 0 and d % S == 0 and d // S < 4 else -1
for tag in sys.argv[1:]:
    Z = np.load(f"data_e19_{tag}.npz"); out = Z["out"]; cols = list(Z["cols"])
    c = {o: i for i, o in enumerate(cols)}
    U = lambda o: out[:, :, c[o]]
    Fl = lambda o: out[:, :, c[o]].view("<f4")
    N = out.shape[0]
    st = (U(0x3714) >> 8) & 0xFF; act = U(0x3818) & 0xFFFF
    live = ((U(0x124) >> 8) & 0xFF) != 0
    hp = Fl(0x160); item = U(0x376C) != 0; form = (U(0x3718) & 0x10000) != 0
    hittable = (U(0x12C) & 0xFFFF) != 0
    cx, cy, cz, rh = Fl(0x1AC), Fl(0x1B0), Fl(0x1B4), Fl(0x1B8)
    hx, hy, hz, rr, hh = Fl(0x18C), Fl(0x190), Fl(0x194), Fl(0x198), Fl(0x19C)
    def overlap(k, v, t, scale=1.0):
        dh = np.hypot(cx[t, k] - hx[t, v], cz[t, k] - hz[t, v]); dy = cy[t, k] - hy[t, v]
        return dh <= scale * (rh[t, k] + rr[t, v]) and abs(dy) <= rh[t, k] + hh[t, v]
    ev = collections.Counter(); unexpl = collections.Counter(); expl_by = collections.Counter()
    for t in range(1, N):
        for v in range(4):
            d = hp[t - 1, v] - hp[t, v]
            if not (0.01 < d < 900): continue
            who = [k for k in range(4) if k != v and (live[t, k] or live[t - 1, k]) and (overlap(k, v, t) or overlap(k, v, t - 1))]
            who12 = [k for k in range(4) if k != v and (live[t, k] or live[t - 1, k]) and (overlap(k, v, t, 1.2) or overlap(k, v, t - 1, 1.2))]
            la = seat(U(0x3774)[t, v])
            ev["events"] += 1
            if who: ev["melee_cyl"] += 1; k = who[0]; expl_by[(int(st[t, k]), "item" if item[t, k] else "-", "form" if form[t, k] else "-")] += 1
            elif who12: ev["melee_cyl1.2"] += 1
            else:
                anylive = [k for k in range(4) if k != v and (live[t, k] or live[t-1, k])]
                if la >= 0: unexpl[("lastatt", int(st[t, la]), hex(int(act[t, la])), "item" if item[t, la] else "-", "live" if live[t, la] or live[t-1, la] else "dead")] += 1
                else: unexpl[("no-lastatt", "someone live" if anylive else "none live")] += 1
    print(f"== {tag}: frames {N}")
    print("  damage events:", dict(ev))
    print("  melee-explained hits by attacker (state, item, form):", dict(expl_by.most_common(20)))
    print("  unexplained:", dict(unexpl.most_common(25)))
    # window-level precision: each live window of attacker k vs each hittable victim
    conf = collections.Counter(); conf_cat = collections.defaultdict(collections.Counter)
    for k in range(4):
        t = 0
        while t < N:
            if live[t, k]:
                s = t
                while t < N and live[t, k]: t += 1
                cat = ("item" if item[s, k] else "-") + "/" + ("form" if form[s, k] else "-") + f"/s{st[s, k]}"
                for v in range(4):
                    if v == k: continue
                    pred = any(overlap(k, v, q) and hittable[q, v] for q in range(s, t))
                    seg = hp[max(s-1, 0):min(t + 2, N), v]
                    actual = bool((np.diff(seg) < -0.01).any())
                    conf[(pred, actual)] += 1; conf_cat[cat][(pred, actual)] += 1
            else: t += 1
    tp, fp, fn, tn = conf[(True, True)], conf[(True, False)], conf[(False, True)], conf[(False, False)]
    print(f"  window-level (attacker live window x victim): TP {tp} FP {fp} FN {fn} TN {tn} precision {tp/max(1,tp+fp):.3f} recall {tp/max(1,tp+fn):.3f}")
    for cat, cc in sorted(conf_cat.items(), key=lambda kv: -sum(kv[1].values()))[:15]:
        print(f"    {cat:16s} TP {cc[(True,True)]:4d} FP {cc[(True,False)]:4d} FN {cc[(False,True)]:4d} TN {cc[(False,False)]:5d}")
    print("  hurt cylinder params seen (r, half-h) per seat:", [sorted(set(zip(np.round(rr[:, k]).tolist(), np.round(hh[:, k]).tolist())))[:6] for k in range(4)])
    print("  hit radius values:", collections.Counter(np.round(rh[live]).tolist()).most_common(10))
    print("  0x1A4 hi16 (bone?) on live frames:", collections.Counter((U(0x1A4)[live] >> 16).tolist()).most_common(10))
