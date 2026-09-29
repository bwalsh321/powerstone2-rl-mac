"""analyze_hitsrc.py (Sep 29 2026): find the OWNER field inside non-player hit-source objects.
Input: scan/<run>/hitsrc.npz (from ram_scan.py capture --hitsrc) + snaps.npz (states, positions).
For every non-player source snapshot (0x400 bytes at the pointer), list aligned u32 offsets whose
value, read as a physical address, lands inside one of the four player objects. The true owner
field is the offset that (a) appears in most snapshots, (b) names a seat other than the victim,
and (c) names a seat that was in an attack / special state (7-12, 25, 26) within the last 3 s.
Usage: python analyze_hitsrc.py scan/hitsrc1
"""
import sys, numpy as np
from collections import Counter, defaultdict
run = sys.argv[1]
h = np.load(f"{run}/hitsrc.npz"); d = np.load(f"{run}/snaps.npz")
S, H = d["snaps"], d["health"]; st = S[:, :, 0x3685]
PM = [int(x) for x in h["player_mat"]]; OBJ_LEN = 0x3938
bases = [(b - 0x490) & 0x0FFFFFFF for b in PM]
def owner(phys):
    for k in range(4):
        if bases[k] <= phys < bases[k] + OBJ_LEN: return k
    return None
fr, vic, ptr, own, blob, has = h["frame"], h["victim"], h["ptr"], h["owner"], h["blob"], h["has_blob"]
n = len(fr); print(f"[hitsrc] {n} pointer changes; player-object sources {int((own >= 0).sum())}, non-player {int(has.sum())}")
# does a pointer change coincide with a health drop of the victim (within -3..+3 frames)?
def dropped(f, k):
    lo, hi = max(1, f - 3), min(len(H) - 1, f + 3)
    return any(H[g, k] < H[g - 1, k] - 0.5 for g in range(lo, hi + 1))
co = Counter()
for i in range(n):
    co["with_drop" if dropped(int(fr[i]), int(vic[i])) else "no_drop"] += 1
print("[hitsrc] pointer changes coinciding with a victim health drop:", dict(co))
# owner-offset search inside non-player sources
off_hits = Counter(); off_valid = Counter(); off_other = Counter(); per_off_seats = defaultdict(Counter)
idx = [i for i in range(n) if has[i]]
for i in idx:
    f, k = int(fr[i]), int(vic[i]); b = blob[i]
    u32 = b[: (len(b) // 4) * 4].view("<u4")
    for j, v in enumerate(u32):
        o = owner(int(v) & 0x0FFFFFFF)
        if o is None: continue
        off = j * 4; off_hits[off] += 1
        if o != k:
            off_other[off] += 1
            if any(7 <= int(st[g, o]) <= 12 or int(st[g, o]) in (25, 26) for g in range(max(0, f - 180), f + 1)):
                off_valid[off] += 1
        per_off_seats[off][o] += 1
print(f"[hitsrc] candidate owner offsets inside the source object ({len(idx)} snapshots):")
for off, c in sorted(off_hits.items(), key=lambda x: -x[1])[:12]:
    print(f"  +0x{off:03x}: player pointer in {c:3d} snapshots ({100*c/max(1,len(idx)):3.0f}%); names another seat {off_other[off]:3d}; that seat attacked/special within 3 s {off_valid[off]:3d}; seats {dict(per_off_seats[off])}")
# source pointer families (which 0x8C5xxxxx objects hit us)
fam = Counter(hex(int(p) & 0x0FFFFFFF) for p, o in zip(ptr, own) if o < 0)
print("[hitsrc] most common non-player source objects:", fam.most_common(10))
