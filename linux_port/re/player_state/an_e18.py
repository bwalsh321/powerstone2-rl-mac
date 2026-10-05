"""Hit/no-hit prediction from P1's live hitbox sphere vs P2's hurt cylinder (E18 data)."""
import collections
from an_e18_lib import *
def windows(live):
    out = []; t = 0; n = len(live)
    while t < n:
        if live[t]:
            s = t
            while t < n and live[t]: t += 1
            out.append((s, t))
        else: t += 1
    return out
models = {
  "cyl":  lambda dh, dy, rh, rr, hh: (dh <= rh + rr) & (np.abs(dy) <= rh + hh),
  "cyl_x0.8": lambda dh, dy, rh, rr, hh: (dh <= 0.8*(rh + rr)) & (np.abs(dy) <= rh + hh),
  "sph": lambda dh, dy, rh, rr, hh: np.hypot(dh, dy) <= rh + rr,
  "cyl_x1.2": lambda dh, dy, rh, rr, hh: (dh <= 1.2*(rh + rr)) & (np.abs(dy) <= rh + hh),
}
res = {m: collections.Counter() for m in models}
dmg_events = 0; dmg_with_live = 0; dmg_no_live = []
first_live_lag = collections.Counter()
per_move = collections.defaultdict(collections.Counter)
for i, (cid, mv, D) in enumerate(RUNS):
    live = ((W(i, 0, 0x124) >> 8) & 0xFF) != 0
    hp = F(i, 1, 0x160); dmg = np.r_[False, np.diff(hp) < -0.01]
    cx, cy, cz, rh = F(i, 0, 0x1AC), F(i, 0, 0x1B0), F(i, 0, 0x1B4), F(i, 0, 0x1B8)
    hx, hy, hz, rr, hh = F(i, 1, 0x18C), F(i, 1, 0x190), F(i, 1, 0x194), F(i, 1, 0x198), F(i, 1, 0x19C)
    hittable = (W(i, 1, 0x12C) & 0xFFFF) != 0
    dh = np.hypot(cx - hx, cz - hz); dy = cy - hy
    for t in np.nonzero(dmg)[0]:
        dmg_events += 1
        if live[max(0, t-1):t+1].any(): dmg_with_live += 1
        else: dmg_no_live.append((cid, mv, D, int(t), int(B(i, 0, 0x3715)[t]), int(W(i, 0, 0x3818)[t] & 0xFFFF)))
    for (s, e) in windows(live):
        actual = dmg[s:min(e + 2, len(dmg))].any()
        for m, f in models.items():
            ov = f(dh[s:e], dy[s:e], rh[s:e], rr[s:e], hh[s:e]) & hittable[s:e]
            pred = ov.any()
            res[m][(bool(pred), bool(actual))] += 1
        ov = models["cyl"](dh[s:e], dy[s:e], rh[s:e], rr[s:e], hh[s:e]) & hittable[s:e]
        per_move[f"{mv}"][(bool(ov.any()), bool(actual))] += 1
        if actual:
            first = np.argmax(dmg[s:min(e+2, len(dmg))]); first_live_lag[int(first)] += 1
print(f"damage events {dmg_events}; with P1 hitbox live at t or t-1: {dmg_with_live}")
print("damage without live flag (cid,move,D,t,P1 state,act):", dmg_no_live[:30])
print("live windows: frames from window start to damage:", dict(sorted(first_live_lag.items())))
for m, c in res.items():
    tp, fp, fn, tn = c[(True, True)], c[(True, False)], c[(False, True)], c[(False, False)]
    print(f"model {m:9s}: TP {tp} FP {fp} FN {fn} TN {tn}  precision {tp/max(1,tp+fp):.3f} recall {tp/max(1,tp+fn):.3f}")
for mv, c in per_move.items():
    print(f"  move {mv:6s} (cyl): TP {c[(True,True)]} FP {c[(True,False)]} FN {c[(False,True)]} TN {c[(False,False)]}")
