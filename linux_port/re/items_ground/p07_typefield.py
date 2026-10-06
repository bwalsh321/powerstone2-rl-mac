"""p07: relaxed type-field search for vt 0x0C0C9810 items: per offset, count
models where the u8/u16/u32 value is constant and how many distinct values
across models; prints offsets constant in >=90% of models with >=4 values."""
import collections, pickle, struct, sys
from p06_analyze import nodes, U
runs = [pickle.load(open(p, "rb")) for p in sys.argv[1:]]
g = collections.defaultdict(list)
for R in runs:
    for f, d, pb, pxyz in R["snaps"]:
        for idx, b in d.items():
            if U(b, 8) == 0x0C0C9810:
                g[nodes(b, pb)].append(b)
g = {m: L for m, L in g.items() if m and len(L) >= 3}
print("models", len(g))
for fmt, w in (("<B", 1), ("<H", 2), ("<I", 4)):
    for o in range(0, 0x430 - w + 1, w):
        const, vals = 0, {}
        for m, L in g.items():
            s = set(struct.unpack_from(fmt, b, o)[0] for b in L)
            if len(s) == 1:
                const += 1; vals[m] = s.pop()
        nd = len(set(vals.values()))
        if const >= 0.9 * len(g) and nd >= 4:
            print(f"+{o:#05x} {fmt} const_in={const}/{len(g)} distinct={nd} " +
                  " ".join(f"{m[0]&0xfffff:05x}:{v:#x}" for m, v in sorted(vals.items())))
