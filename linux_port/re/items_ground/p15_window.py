"""p15: ledger window coverage. Distribution of grid idx (relative to
OBJ_GRID_LO) of category-9 objects per vt; fraction outside [0,110) =
objects the production _obj_scan cannot see."""
import pickle, sys, collections
from p06_analyze import U
c = collections.defaultdict(collections.Counter)
for p in sys.argv[1:]:
    R = pickle.load(open(p, "rb"))
    for f, d, pb, pxyz in R["snaps"]:
        for idx, b in d.items():
            c[U(b, 8)][idx] += 1
for vt, cnt in sorted(c.items()):
    tot = sum(cnt.values()); out = sum(n for i, n in cnt.items() if not (0 <= i < 110))
    print(f"vt={vt:#010x} n={tot:5d} idx range [{min(cnt)},{max(cnt)}]  outside[0,110): {out} ({100*out/tot:.1f}%)")
