"""p11: correlate held status (some player's F+0x54 == record+4) with record
fields: +0x421 state byte, hdr byte1 (+0x05), +0x423, y. Uses p04 pickles."""
import collections, pickle, struct, sys
from p06_analyze import U, F
LO = 0x8C4FBD30 - 40 * 0x430
tab = collections.Counter()
for p in sys.argv[1:]:
    R = pickle.load(open(p, "rb"))
    held = R["held"]
    for f, d, pb, pxyz in R["snaps"]:
        cur = {}
        for (fh, pl, o, n, go, gn, xyz) in held:
            if fh <= f:
                cur[pl] = n
        hp = {v: k for k, v in cur.items() if v}
        for idx, b in d.items():
            a = (LO + (idx + 40) * 0x430) - 0x80000000 + 4
            vt = U(b, 8)
            h = hp.get(a, -1)
            tab[(vt, b[0x420] if vt != 0x0C0C9810 else 'item', h >= 0, b[0x421], b[5], b[0x423])] += 1
for k, n in sorted(tab.items(), key=str):
    vt, tid, isheld, st, h1, b423 = k
    print(f"vt={vt:#010x} id={tid} held={isheld!s:5} +421={st:#04x} hdr.b1={h1:#04x} +423={b423:#04x}  n={n}")
