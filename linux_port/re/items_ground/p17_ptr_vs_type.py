"""p17: is F+0x54 an item-type key? For each held pointer value, list the
type ids (+0x420 of record ptr-4) it carried across snapshots (p04 pickles).
Also: every held pointer must resolve to a grid record (ptr-4-LO) % 0x430 == 0."""
import collections, pickle, sys
from p06_analyze import U
LO = 0x0C4FBD30
m = collections.defaultdict(collections.Counter); bad = 0; tot = 0
for p in sys.argv[1:]:
    R = pickle.load(open(p, "rb"))
    for f, d, pb, pxyz in R["snaps"]:
        cur = {}
        for (fh, pl, o, n, go, gn, xyz) in R["held"]:
            if fh <= f: cur[pl] = n
        for pl, ptr in cur.items():
            if not ptr: continue
            tot += 1
            if (ptr - 4 - LO) % 0x430: bad += 1; continue
            idx = (ptr - 4 - LO) // 0x430
            b = d.get(idx)
            if b is None: continue
            m[ptr][(hex(U(b, 8)), hex(b[0x420]))] += 1
print(f"held samples={tot} not-on-grid={bad}")
for ptr, c in sorted(m.items()):
    print(f"F+0x54={ptr:#x}: " + ", ".join(f"{vt}/id{t}x{n}" for (vt, t), n in c.most_common()))
