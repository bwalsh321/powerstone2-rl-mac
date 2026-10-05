import numpy as np, sys
D = np.load("data_e3.npz"); base = 0x8C530000
for name in ("jump", "runjump"):
    a = D[name]; fl = a.view("<f4").astype(np.float64)
    mo = (0x8C532928 - base)//4
    pos = fl[:, mo+12:mo+15]
    d = np.vstack([np.zeros(3), np.diff(pos, axis=0)])
    print("==", name, "dy:", d[:60, 1].round(2).tolist())
    print("   dx:", d[:60, 0].round(2).tolist())
    for ax in (0, 1, 2):
        dd = d[:, ax]
        if dd.std() < 0.1: continue
        res = []
        for lag in range(-2, 3):
            x = np.roll(dd, lag)[3:-3]
            for j in range(fl.shape[1]):
                c = fl[3:-3, j]
                if not np.all(np.isfinite(c)) or c.std() < 1e-4 or np.abs(c).max() > 1e5: continue
                r = np.corrcoef(c, x)[0, 1]
                if abs(r) > 0.97:
                    k = np.polyfit(c, x, 1)
                    res.append((abs(r), base + 4*j, lag, k[0], k[1]))
        res.sort(reverse=True)
        print("  ax", ax, [(f"{r[1]:08X}", round(r[0], 4), r[2], round(r[3], 4), round(r[4], 3)) for r in res[:12]])
