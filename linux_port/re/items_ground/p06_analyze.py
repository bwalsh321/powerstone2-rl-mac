"""p06: offline analysis of out/ev_*.pkl (from p04).
usage: python p06_analyze.py out/ev_s2_11.pkl [...]
 1. per-vt census of category-9 objects
 2. for vt 0x0C0C9810 records: model (pool node classes) vs candidate
    type fields (u8/u16/u32 constant within a model, varying across models)
 3. chest -> content linkage"""
import collections
import pickle
import struct
import sys

import numpy as np

POOL_BASE = 0x8C3E7400


def U(b, o):
    return struct.unpack_from("<I", b, o)[0]


def F(b, o):
    return struct.unpack_from("<f", b, o)[0]


def nodes(b, pool):
    n = U(b, 0xC4); out = []
    for i in range(min(n, 8)):
        p = U(b, 0xC8 + 4 * i)
        if 0x0C3E7400 <= p < 0x0C3E7400 + 160 * 0x90:
            po = (p - 0x34 + 0x3C) - 0x0C3E7400
            out.append(U(pool, po))
    return tuple(out)


def main():
    runs = [pickle.load(open(p, "rb")) for p in sys.argv[1:]]
    census = collections.Counter()
    models = collections.defaultdict(list)     # model -> list of record bytes
    for R in runs:
        for f, d, pb, pxyz in R["snaps"]:
            for idx, b in d.items():
                vt = U(b, 8)
                census[vt] += 1
                if vt in (0x0C0C9810, 0x0C0CBCB0, 0x0C0CC7A8, 0x0C0C9F50, 0x0C0CA928):
                    models[(vt, nodes(b, pb))].append((R["slot"], R["seed"], f, idx, b))
    print("== category-9 vt census (snap sightings)")
    for vt, n in census.most_common():
        print(f"  {vt:#010x}: {n}")
    print("== (vt, model) groups")
    for (vt, m), L in sorted(models.items(), key=lambda kv: (kv[0][0], -len(kv[1]))):
        print(f"  vt={vt:#010x} model={','.join(hex(c) for c in m)} n={len(L)} slots={sorted(set((s, i) for s, _, _, i, _ in L))[:6]}")
    
    # candidate type fields among vt 9810 groups
    g = {m: L for (vt, m), L in models.items() if vt == 0x0C0C9810 and m and len(L) >= 2}
    if len(g) >= 2:
        print("== offsets constant within each 9810 model & distinct across >=3 models")
        for o in range(0, 0x430, 2):
            per = {}
            ok = True
            for m, L in g.items():
                vals = set(struct.unpack_from("<H", b, o)[0] for *_, b in L)
                if len(vals) != 1:
                    ok = False; break
                per[m] = vals.pop()
            if ok and len(set(per.values())) >= 3:
                print(f"  +{o:#05x} u16: " + "  ".join(f"{m[0]:#x}->{v:#06x}" for m, v in per.items()))

if __name__ == "__main__":
    main()
