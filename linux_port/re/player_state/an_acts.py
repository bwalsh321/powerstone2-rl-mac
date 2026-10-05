"""Per action-word (P+0x3818) statistics from census runs: states, held item, partner ptr, airborne."""
import sys, numpy as np, collections
tags = sys.argv[1:]
rows = collections.defaultdict(lambda: collections.Counter())
for tag in tags:
    R = np.load(f"data_census_{tag}.npy", mmap_mode="r")
    st = np.asarray(R[:, :, 0x3715]).astype(int)
    act = np.asarray(R[:, :, 0x3818:0x381A]).copy().view("<u2")[..., 0].astype(int)
    u = lambda o: np.asarray(R[:, :, o:o+4]).copy().view("<u4")[..., 0]
    fl = lambda o: np.asarray(R[:, :, o:o+4]).copy().view("<f4")[..., 0]
    item = u(0x3718 + 0x54); part = u(0x3770); y = fl(0x2C)
    for a in np.unique(act):
        m = act == a; r = rows[a]
        r["n"] += int(m.sum()); r["item"] += int((item[m] != 0).sum()); r["part"] += int((part[m] != 0).sum())
        r["air"] += int((y[m] > 5).sum())
        for s, c in collections.Counter(st[m].tolist()).items(): r[("s", s)] += c
        for i in range(4): r[("seat", i+1)] += int(m[:, i].sum())
for a in sorted(rows):
    r = rows[a]; n = r["n"]
    ss = {k[1]: v for k, v in r.items() if isinstance(k, tuple) and k[0] == "s"}
    seats = {k[1]: v for k, v in r.items() if isinstance(k, tuple) and k[0] == "seat" and v}
    print(f"{a:04x} n={n:5d} item%={100*r['item']//n:3d} partner%={100*r['part']//n:3d} air%={100*r['air']//n:3d} states={ss} seats={seats}")
