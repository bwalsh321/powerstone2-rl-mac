"""RLE of low-cardinality u32/u16/u8 fields of a struct array in an npz key.
usage: an_rle2.py npz key [width] [maxdistinct] [maxruns] [lo_off] [hi_off]"""
import sys, numpy as np
f, key = sys.argv[1], sys.argv[2]
width = sys.argv[3] if len(sys.argv) > 3 else "u32"
maxd = int(sys.argv[4]) if len(sys.argv) > 4 else 16
maxr = int(sys.argv[5]) if len(sys.argv) > 5 else 30
lo = int(sys.argv[6], 16) if len(sys.argv) > 6 else 0
hi = int(sys.argv[7], 16) if len(sys.argv) > 7 else 1 << 30
D = np.load(f); a = D[key]
dt = {"u32": "<u4", "u16": "<u2", "u8": "u1", "f32": "<f4"}[width]
v = a.view(dt); T, N = v.shape; sz = np.dtype(dt).itemsize
for j in range(N):
    o = j*sz
    if o < lo or o >= hi: continue
    col = v[:, j]
    u = np.unique(col)
    if 1 < len(u) <= maxd:
        runs = []; s = 0
        for i in range(1, T + 1):
            if i == T or col[i] != col[s]:
                runs.append(f"{col[s]:x}@{s}" if width != "f32" else f"{col[s]:.3g}@{s}"); s = i
        if len(runs) > maxr: continue
        print(f"P+{o:04X} n={len(u)}: " + " ".join(runs))
