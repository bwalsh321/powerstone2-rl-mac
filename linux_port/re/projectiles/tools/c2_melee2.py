import numpy as np
from collections import Counter
from common import *
d = dict(np.load(f"{HERE}/../cap/Afull/cap.npz")); P = np.load(f"{HERE}/../cap/Afull/pobj.npz")["pobj"]
st = d["st"]; hp = d["hp"]; hs = d["hsrc"]
b134 = P[:, :, 0x134]; w414 = u32(P, 0x414)
for s in range(4):
    on = w414[:, s] != 0
    print(f"seat{s} {LINEUPS['A'][s]}: 0x414 on {on.mean():.2%} of frames; values {Counter(hex(int(v)) for v in w414[on, s]).most_common(4)}")
    print(f"    b134 values {Counter(b134[:, s].tolist()).most_common(5)}; agree(on414, b134!=0)={(on == (b134[:, s] != 0)).mean():.2%}")
    print(f"    states while on: {Counter(st[on, s].tolist()).most_common(8)}")
    # run lengths
    r = np.diff(np.r_[0, on.astype(int), 0]); starts = np.flatnonzero(r == 1); ends = np.flatnonzero(r == -1)
    print(f"    windows={len(starts)} len med={np.median(ends-starts) if len(starts) else 0}")
# do all melee hits from seat s fall in its on-window?
tot = ok = 0
for f in range(1, len(hp)):
    for k in range(4):
        if 0.5 < hp[f-1, k] - hp[f, k] < 900:
            s = seat_of(int(hs[f, k]))
            if s is not None and s != k:
                tot += 1; ok += bool(w414[f-2:f+1, s].any())
print(f"melee hits inside the attacker's 0x414 window (f-2..f): {ok}/{tot}")
