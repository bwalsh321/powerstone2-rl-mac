"""p09: chest -> content linkage. For every resting chest (vt 0x0C0CC7A8)
that stops being a chest, find the first NEW category-9 object that appears
within 120 frames of that, within 150 units (xz) of the chest. Compare the
newcomer's type byte (+0x420) with the chest's pre-open +0x42C byte."""
import collections, math, pickle, struct, sys
from p06_analyze import U, F
ok = bad = nolink = 0
conf = collections.Counter()
for p in sys.argv[1:]:
    R = pickle.load(open(p, "rb"))
    ev = R["events"]
    for i, (f, kind, idx, old, new, bo, bn) in enumerate(ev):
        if old and old[1] == 0x0C0CC7A8 and (new is None or new[1] != 0x0C0CC7A8) and bo:
            cx, cz = F(bo, 0x2C), F(bo, 0x34)
            pred = bo[0x42C]
            hit = None
            for f2, k2, idx2, o2, n2, bo2, bn2 in ev[i:]:
                if f2 - f > 120:
                    break
                if n2 and n2[0] == 9 and n2[1] != 0x0C0CC7A8 and (o2 is None or o2 != n2):
                    x, z = F(bn2, 0x2C), F(bn2, 0x34)
                    if math.hypot(x - cx, z - cz) < 150:
                        hit = (f2, idx2, n2[1], bn2[0x420], x, F(bn2, 0x30), z); break
            st = bo[0x421]
            if hit is None:
                nolink += 1
                print(f"{p[-12:]} f={f} chest idx={idx} ({cx:.0f},{cz:.0f}) +42C={pred:#04x} +421={st:#x} -> new={new} NO LINK")
                continue
            good = hit[3] == pred
            ok += good; bad += not good
            conf[(pred, hit[3])] += 1
            print(f"{p[-12:]} f={f} chest idx={idx} ({cx:.0f},{cz:.0f}) +42C={pred:#04x} -> f={hit[0]} idx={hit[1]} vt={hit[2]:#x} id={hit[3]:#04x} pos=({hit[4]:.0f},{hit[5]:.0f},{hit[6]:.0f}) {'MATCH' if good else 'MISMATCH'}")
print(f"MATCH={ok} MISMATCH={bad} NOLINK={nolink}")
