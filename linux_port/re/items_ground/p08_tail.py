"""p08: per (vt, model) group, show the record tail +0x410..+0x430 and
+0x120..+0x12C (value sets) to locate id/category bytes for all cat-9 vts."""
import collections, pickle, struct, sys
from p06_analyze import nodes, U
runs = [pickle.load(open(p, "rb")) for p in sys.argv[1:]]
g = collections.defaultdict(list)
for R in runs:
    for f, d, pb, pxyz in R["snaps"]:
        for idx, b in d.items():
            g[(U(b, 8), nodes(b, pb)[:1])].append(b)
for (vt, m), L in sorted(g.items()):
    def vs(o, fmt="<I"):
        s = collections.Counter(struct.unpack_from(fmt, b, o)[0] for b in L)
        return "/".join(f"{v:x}" for v, _ in s.most_common(3))
    print(f"vt={vt:08x} m0={(m[0] if m else 0):08x} n={len(L):4d} +120={vs(0x120)} +124={vs(0x124)} +128={vs(0x128)} +12c={vs(0x12c)} | +418={vs(0x418)} +41c={vs(0x41c)} +420={vs(0x420)} +424={vs(0x424)} +428={vs(0x428)} +42c={vs(0x42c)}")
