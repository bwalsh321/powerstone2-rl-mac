"""S17: camera search (desert slot1). P1 AND P2 random-walk; 120 RAM snapshots (every 15 f). Find float triples whose x/z
track the P1-P2 midpoint (corr>0.97) outside player structs, then report offset (cam - mid) stats -> camera pos / target.
Saves only candidate series (disk budget)."""
from common import *
br = boot()
load(br, STATES["slot1"]); br.run_frames(10)
rng = np.random.default_rng(1)
DIRS = ["up", "down", "left", "right", "up+left", "up+right", "down+left", "down+right"]
LO, HI = 0x000000, 0x600000
F = []; mids = []; spread = []
for k in range(100):
    if k % 4 == 0: setpad(br, DIRS[rng.integers(8)], 1); setpad(br, DIRS[rng.integers(8)], 0)
    br.run_frames(15)
    r = br.ram
    F.append(np.frombuffer(r[LO:HI].tobytes(), "<f4").copy())   # window LO..HI only (memory)
    a, b = np.array(logpos(r, 0)), np.array(logpos(r, 1))
    mids.append((a + b) / 2); spread.append(np.hypot(*(a - b)[[0, 2]]))
F = np.stack(F); mids = np.array(mids); spread = np.array(spread)
F = np.where(np.isfinite(F) & (np.abs(F) < 1e5), F, 0).astype(np.float32)
def corr(X, y, ch=200000):
    yc = (y - y.mean()).astype(np.float32); out = np.zeros(X.shape[1], np.float32)
    for j in range(0, X.shape[1], ch):
        Xc = X[:, j:j + ch] - X[:, j:j + ch].mean(0)
        out[j:j + ch] = (Xc * yc[:, None]).sum(0) / (np.sqrt((Xc ** 2).sum(0) * (yc ** 2).sum()) + 1e-9)
    return out
cx = corr(F, mids[:, 0]); cz = corr(F, mids[:, 2]); cs = corr(F, spread)
pl_lo, pl_hi = ((P0 & 0xFFFFFF) - LO) // 4, (((P0 + 4 * PSTRIDE) & 0xFFFFFF) - LO) // 4
outp = np.ones(len(cx), bool); outp[pl_lo:pl_hi] = False
for nm, c in (("midx", cx), ("midz", cz), ("spread", cs)):
    top = np.argsort(-np.where(outp, np.abs(c), 0))[:12]
    print(f"top |corr| with {nm}:", " ".join(f"{0x8C000000+LO+4*i:08X}:{c[i]:+.2f}(m{F[:, i].mean():.0f})" for i in top))
idx = np.nonzero((cx > 0.97))[0]
idx = [i for i in idx if not (pl_lo <= i < pl_hi) and i + 2 < F.shape[1] and cz[i + 2] > 0.97]
msd = np.hypot(mids[:, 0].std(), mids[:, 2].std())
osd = {i: np.hypot((F[:, i] - mids[:, 0]).std(), (F[:, i + 2] - mids[:, 2]).std()) for i in idx}
print("midpoint xz std", round(float(msd), 1))
idx = sorted([i for i in idx if osd[i] < 0.5 * msd], key=lambda i: osd[i])
print("x/z-tracking triples (a, a+8):", len(idx))
for i in idx[:40]:
    ox = F[:, i] - mids[:, 0]; oy = F[:, i + 1] - mids[:, 1]; oz = F[:, i + 2] - mids[:, 2]
    print(f"  {0x8C000000+LO+4*i:08X} off x {ox.mean():8.1f}±{ox.std():6.1f}  y {F[:, i+1].mean():8.1f}±{F[:, i+1].std():6.1f}"
          f"  z {oz.mean():8.1f}±{oz.std():6.1f}  corr(y,spread)={cs[i+1]:.2f}")
np.savez_compressed("data/s17_camera_cands.npz", mids=mids, spread=spread, addrs=np.array([0x8C000000 + LO + 4 * i for i in idx]),
                    series=np.stack([F[:, i:i + 3] for i in idx]) if idx else np.zeros(0))
print("DONE")
