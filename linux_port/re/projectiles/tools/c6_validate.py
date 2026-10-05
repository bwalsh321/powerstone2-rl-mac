"""Offline validation on the captures: proposed ledger rule (v4) vs a replica of the v3 pool rule.
Coverage = share of NON-MELEE damage events (hit-source = ledger object) where the rule reported
(a) the exact source slot, or (b) anything within 200u (xz) of the victim, in frames f-6..f-1."""
import sys, os, numpy as np
from collections import Counter, defaultdict
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../.."))
import ps2_addr as A
from common import *
STAGE_EX = {0x0C0CBCB0, 0x0C0CC7A8, 0x0C0CACAC}
def v4_reports(led, pos):
    hdr = u32(led, 4) & 0xFF; vt = u32(led, 8)
    P = np.stack([f32(led, 0x2C), f32(led, 0x30), f32(led, 0x34)], -1).astype(float)
    V = np.stack([f32(led, 0x50), f32(led, 0x54), f32(led, 0x58)], -1).astype(float) * 60
    okvt = (vt >= 0x0C000000) & (vt < 0x0C200000)
    fin = np.isfinite(P).all(-1) & np.isfinite(V).all(-1)
    hit = (hdr == 1) & okvt & fin
    sp = np.linalg.norm(V, axis=-1); hsp = np.hypot(V[..., 0], V[..., 2])
    dxz = np.hypot(pos[:, None, :, 0] - P[:, :, None, 0], pos[:, None, :, 2] - P[:, :, None, 2])   # [F,NL,4]
    pv = np.vstack([np.zeros((1, 4, 3)), np.diff(pos, axis=0) * 60])                                 # [F,4,3]
    rel = np.linalg.norm(V[:, :, None, :] - pv[:, None, :, :], axis=-1)                               # [F,NL,4]
    held = ((dxz < 120) & (rel < 300)).any(-1)
    dpp = np.zeros_like(P); dpp[1:] = (P[1:] - P[:-1]) * 60                  # observed motion (needs 1-frame history)
    dpp[1:][(vt[1:] != vt[:-1])] = 0
    cons = np.hypot(dpp[..., 0] - V[..., 0], dpp[..., 2] - V[..., 2]) <= 0.25 * hsp + 60
    thr = cons & (np.hypot(dpp[..., 0], dpp[..., 2]) >= 300) & (((hdr == 9) & ~np.isin(vt, list(STAGE_EX))) | ((hdr == 2) & (vt == 0x0C16DBD4))) & okvt & fin & (sp >= 600 * (hdr == 9) + 300 * (hdr == 2)) & (hsp >= 300) & (sp <= 8000) & ~held
    return hit, thr, P
def v3_reports(d):
    pact, pcls, ppos = d["pact"], d["pcls"], d["ppos"]
    F = len(pact); rep = [np.zeros((0, 3))] * F
    exb = list(A.PROJ_EXCLUDE_BANDS) + list(A.PROJ_EXCLUDE_BANDS_V3)
    for f in range(3, F):
        live = ((pact[f] & 0xFF) == 1) & ((pact[f-3] & 0xFF) == 1) & (pcls[f] == pcls[f-3])
        sp = np.linalg.norm(ppos[f] - ppos[f-3], axis=-1) * 20
        c = pcls[f]
        known = np.isin(c, list(A.PROJ_CLASSES))
        bad = np.isin(c, list(A.PROJ_EXCLUDE) + list(A.PROJ_EXCLUDE_V3))
        for lo, hi in exb: bad |= (c >= lo) & (c < hi)
        m = live & ~bad & (known | ((sp >= A.PROJ_SPEED_MIN) & np.isfinite(sp)))
        rep[f] = ppos[f][m]
    return rep
tot = Counter(); miss = Counter(); per_frame = defaultdict(list)
for L in LINEUPS:
    d = load(L); led = d["ledger"]; pos = d["pos"].astype(float); hp, hs = d["hp"], d["hsrc"]
    hit, thr, P = v4_reports(led, pos); r3 = v3_reports(d)
    rep4 = hit | thr
    per_frame["v4"].append(rep4.sum(1)); per_frame["v3"].append(np.array([len(x) for x in r3]))
    for f in range(7, len(hp)):
        for k in range(4):
            if not (0.5 < hp[f-1, k] - hp[f, k] < 900): continue
            p = int(hs[f, k])
            if seat_of(p) is not None or p == 0: continue
            i, r = lslot(p)
            if i is None or i >= led.shape[1]: continue
            vt = int(u32(led[f, i], 8)); cat = int(u32(led[f, i], 4)) & 0xFF
            grp = "cat1" if cat == 1 else f"cat{cat}"
            # ignore held-weapon swings (cat9 source not moving): those are melee with an item
            moving = np.linalg.norm(P[f-6, i] - P[f-1, i]) * 12 >= 300 if np.isfinite(P[f-6:f, i]).all() else False
            if cat == 9 and not moving: grp = "cat9-static(held swing/hazard)"
            tot[grp] += 1
            vx, vz = pos[f, k, 0], pos[f, k, 2]
            exact = rep4[f-6:f, i].any()
            near4 = any((np.hypot(P[g, rep4[g], 0] - vx, P[g, rep4[g], 2] - vz) < 200).any() for g in range(f-6, f))
            near3 = any(len(r3[g]) and (np.hypot(r3[g][:, 0] - vx, r3[g][:, 2] - vz) < 200).any() for g in range(f-6, f))
            tot[grp + "|v4exact"] += exact; tot[grp + "|v4near"] += near4; tot[grp + "|v3near"] += near3
            if not exact: miss[(grp, hex(vt))] += 1
for g in sorted({k.split("|")[0] for k in tot}):
    n = tot[g]
    print(f"{g:34s} n={n:4d}  v4 exact-source {tot[g+'|v4exact']/n:6.1%}  v4 near-victim {tot[g+'|v4near']/n:6.1%}  v3(pool) near-victim {tot[g+'|v3near']/n:6.1%}")
print("v4 misses (exact) by class:", miss.most_common(12))
for k in ("v3", "v4"):
    a = np.concatenate(per_frame[k]); print(f"{k}: reports/frame mean {a.mean():.2f}, frames with >=1 report {np.mean(a > 0):.1%}")
