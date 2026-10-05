import numpy as np
S = np.load("data_e4_full.npy", mmap_mode="r")
T = S.shape[0]
my = (0x532928 + 0x34)//4
print("mat y:", np.asarray(S[:, my]).round(1).tolist())
# windows: airborne roughly frames 4..45 relative (jump pressed 2 frames before capture)
W = slice(8, 30)
X = np.asarray(S[W], dtype=np.float64)
with np.errstate(all="ignore"):
    d = np.diff(X, axis=0)
    dd = np.diff(d, axis=0)
    ok = np.all(np.isfinite(X), axis=0) & (np.abs(X).max(0) < 1e5)
    # linear ramp: constant nonzero first difference
    ramp = ok & (np.abs(d).min(0) > 1e-3) & (d.std(0) < 0.02*np.abs(d.mean(0))) & (np.sign(d).min(0) == np.sign(d).max(0))
    # parabola: constant nonzero second difference
    para = ok & (np.abs(dd.mean(0)) > 1e-3) & (dd.std(0) < 0.05*np.abs(dd.mean(0)))
for name, m in (("ramp", ramp), ("parabola", para)):
    idx = np.nonzero(m)[0]
    print(name, len(idx))
    for i in idx[:60]:
        print(f"  {0x8C000000+4*i:08X} first={X[0,i]:.3f} d={d[:,i].mean():.4f} dd={dd[:,i].mean():.4f}")
