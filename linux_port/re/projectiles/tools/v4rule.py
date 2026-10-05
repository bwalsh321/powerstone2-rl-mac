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
