"""p14: what is vt 0x0C0CACAC? Relate each birth to gem-count drops (F+0x35)
and to the next stone (0x0C0CBCB0) birth, from p04 pickles."""
import pickle, sys, struct, math
from p06_analyze import U, F
for p in sys.argv[1:]:
    R = pickle.load(open(p, "rb"))
    drops = [(f, pl, go, gn, xyz) for f, pl, o, n, go, gn, xyz in R["held"] if go is not None and gn < go]
    for f, kind, idx, old, new, bo, bn in R["events"]:
        if new and new[1] == 0x0C0CACAC and old != new:
            x, y, z = F(bn, 0x2C), F(bn, 0x30), F(bn, 0x34)
            near = [d for d in drops if abs(d[0] - f) <= 20]
            st = [(f2, F(b2, 0x2C), F(b2, 0x30), F(b2, 0x34)) for f2, k2, i2, o2, n2, _, b2 in R["events"] if n2 and n2[1] == 0x0C0CBCB0 and o2 != n2 and 0 <= f2 - f <= 30]
            print(f"{p[-12:]} f={f} cacac idx={idx} owner={bn[5]} id={bn[0x420]:#x} pos=({x:.0f},{y:.0f},{z:.0f}) gemdrops={[(d[0], 'P%d' % (d[1]+1), d[2], d[3]) for d in near]} stone_births={[(a, round(b), round(c), round(d)) for a, b, c, d in st]}")
