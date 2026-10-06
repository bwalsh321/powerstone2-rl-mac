"""Search a recorded region for float columns matching per-frame position deltas."""
import sys, numpy as np
f, reg, base = sys.argv[1], sys.argv[2], int(sys.argv[3], 16)
MAT = 0x8C532928
D = np.load(f); a = D[reg]; T = a.shape[0]
fl = a.view("<f4").astype(np.float64)
mo = (MAT - base) // 4
pos = fl[:, mo + 12: mo + 15]
print("pos samples:", pos[[0, 40, 100, 110, 120]].round(1).tolist())
dpos = np.vstack([np.zeros(3), np.diff(pos, axis=0)])
for ax, name in enumerate("xyz"):
    d = dpos[:, ax]
    if d.std() < 1e-6: continue
    res = []
    for lag in (-1, 0, 1):
        dd = np.roll(d, lag)
        for j in range(fl.shape[1]):
            c = fl[:, j]
            if not np.all(np.isfinite(c)) or c.std() < 1e-6 or np.abs(c).max() > 1e5: continue
            r = np.corrcoef(c[2:-2], dd[2:-2])[0, 1]
            if abs(r) > 0.9:
                k = np.dot(c, dd) / max(np.dot(c, c), 1e-9)
                res.append((abs(r), r, lag, base + 4*j, k))
    res.sort(reverse=True)
    print(f"--- d{name}  std={d.std():.3f}")
    for r in res[:15]:
        print(f"  {r[3]:08X} r={r[1]:+.3f} lag={r[2]} dpos/field={r[4]:.4f}")
