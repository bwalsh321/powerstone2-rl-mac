"""Run-length print of low-cardinality changing fields in a recorded region."""
import sys, numpy as np
f, reg = sys.argv[1], sys.argv[2]
base = int(sys.argv[3], 16); width = sys.argv[4] if len(sys.argv) > 4 else "u32"
maxd = int(sys.argv[5]) if len(sys.argv) > 5 else 24
D = np.load(f); a = D[reg]; lab = D["lab"]
dt = {"u32": "<u4", "u16": "<u2", "u8": "u1"}[width]
v = a.view(dt)
T, N = v.shape
sz = np.dtype(dt).itemsize
# phase boundaries
bounds = [0] + [i for i in range(1, T) if lab[i] != lab[i-1]]
print("phases:", [(b, lab[b]) for b in bounds])
for j in range(N):
    col = v[:, j]
    u = np.unique(col)
    if 1 < len(u) <= maxd:
        runs = []; s = 0
        for i in range(1, T + 1):
            if i == T or col[i] != col[s]:
                runs.append(f"{col[s]:x}@{s}"); s = i
        if len(runs) > 40: continue
        print(f"{base + j*sz:08X} (+{j*sz:04X}) n={len(u)}: " + " ".join(runs))
