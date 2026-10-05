"""Per ledger class (word at slot+8): instances, lifetime, speed, owner, header values."""
import sys, numpy as np
from collections import Counter, defaultdict
from common import *
want = set(int(x, 16) for x in sys.argv[1:]) or None
rows = defaultdict(list)    # vt -> list of (L, slot, f0, f1, owner, maxspd, medspd, hdrs)
for L in LINEUPS:
    d = load(L); led = d["ledger"]; names = LINEUPS[L]
    F, NL, _ = led.shape
    vt = u32(led, 8); hdr = u32(led, 4); own = u32(led, 0x14)
    px, py, pz = f32(led, 0x2C), f32(led, 0x30), f32(led, 0x34)
    for i in range(NL):
        v = vt[:, i]; h = hdr[:, i]
        # instance boundary: vt change or header change in low byte, or slot header zero
        key = v.astype(np.uint64) << 8 | (h & 0xFF)
        cut = np.flatnonzero(key[1:] != key[:-1]) + 1
        segs = np.split(np.arange(F), cut)
        for s in segs:
            c = int(v[s[0]])
            if not (0x0C000000 <= c < 0x0C200000): continue
            if want and c not in want: continue
            if (h[s[0]] & 0xFF) == 0: continue
            dx = np.diff(px[s, i]); dy = np.diff(py[s, i]); dz = np.diff(pz[s, i])
            sp = np.sqrt(dx*dx + dy*dy + dz*dz) * 60 if len(s) > 1 else np.zeros(1)
            sp = sp[np.isfinite(sp) & (sp < 50000)]
            o = seat_of(int(own[s[0], i]))
            rows[c].append((L, i, int(s[0]), int(s[-1]), names[o] if o is not None else "-",
                            float(sp.max()) if len(sp) else 0, float(np.median(sp)) if len(sp) else 0,
                            int(h[s[0]] & 0xFF), bool(s[0] == 0), bool(s[-1] == F - 1)))
out = []
for c, r in rows.items():
    n = len(r); life = [x[3] - x[2] + 1 for x in r if not x[8] and not x[9]]
    out.append((c, n, r, life))
out.sort(key=lambda t: -t[1])
for c, n, r, life in out:
    own = Counter(x[4] for x in r)
    print(f"{c:#010x} n={n:4d} hdr={dict(Counter(x[7] for x in r))} life med={np.median(life) if life else -1:6.0f} "
          f"max={max(life) if life else -1:5d} | spd med={np.median([x[6] for x in r]):6.0f} p90max={np.percentile([x[5] for x in r],90):6.0f} "
          f"| owners={dict(own.most_common(4))} lineups={dict(Counter(x[0] for x in r))}")
