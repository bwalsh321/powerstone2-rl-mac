"""Link pool render objects (0x0C6xxxxx band) to ledger objects by identical position; per pool class -> ledger vt/hdr.
Also per link: speed while linked, and whether the ledger object is within 120u of a player (held) or not (flying/ground)."""
import numpy as np
from collections import Counter, defaultdict
from common import *
link = defaultdict(Counter); motion = defaultdict(list)
for L in "ABCD":
    d = load(L); led = d["ledger"]; pact, pcls, ppos = d["pact"], d["pcls"], d["ppos"]; pos = d["pos"]
    hdr = u32(led, 4) & 0xFF; vt = u32(led, 8)
    LP = np.stack([f32(led, 0x2C), f32(led, 0x30), f32(led, 0x34)], -1)
    for f in range(0, len(pact), 3):
        live = np.flatnonzero(((pact[f] & 0xFF) == 1) & (pcls[f] >= 0x0C600000) & (pcls[f] < 0x0C700000))
        for j in live:
            dd = np.linalg.norm(LP[f] - ppos[f, j], axis=-1)
            k = int(np.nanargmin(np.where(np.isfinite(dd), dd, 1e9)))
            key = int(pcls[f, j])
            if dd[k] < 2.0:
                link[key][(int(hdr[f, k]), int(vt[f, k]))] += 1
            else:
                link[key][("none", round(float(dd[k])))] += 0
                link[key][("none",)] += 1
for c, cn in sorted(link.items(), key=lambda kv: -sum(kv[1].values())):
    tot = sum(cn.values())
    print(f"pool {c:#010x} n={tot:5d} -> " + ", ".join(f"{k[0]}:{k[1]:#x}={v}" if k[0] != 'none' else f"none={v}" for k, v in cn.most_common(4) if v))
