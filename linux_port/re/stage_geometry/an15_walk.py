"""AN15: random-walk logs -> empirical walkability map per stage.
Per 25-u cell: visits, grounded-floor y (median of y while state in {0,1,2}), max y, stall count (dpad held, state 1,
speed < 1 u/f = pressing into a wall/obstacle). Events: respawns (state 22), health drops.
Writes data/map_walk_<stage>.npz (kept) and shots/walk_<stage>.png. Usage: an15_walk.py stage [stage...]"""
import sys, numpy as np
from imgutil import heat, hstack
RES = 25.0
for st in sys.argv[1:]:
    L = np.load(f"data/s15_walk_{st}.npz")["log"]
    x, y, z, s, m, hp = L.T
    v = np.r_[0, np.hypot(np.diff(x), np.diff(z))]
    jump = v > 60                                   # teleports (respawn / reload)
    grounded = np.isin(s, (0, 1, 2))
    stall = (s == 1) & (m > 0) & (v < 1.0)
    x0, x1, z0, z1 = np.floor(x.min() / RES) * RES - RES, np.ceil(x.max() / RES) * RES + RES, np.floor(z.min() / RES) * RES - RES, np.ceil(z.max() / RES) * RES + RES
    nx, nz = int((x1 - x0) / RES) + 1, int((z1 - z0) / RES) + 1
    ix = ((x - x0) / RES).astype(int); iz = ((z - z0) / RES).astype(int)
    visits = np.zeros((nz, nx), np.int32); np.add.at(visits, (iz, ix), 1)
    stalls = np.zeros((nz, nx), np.int32); np.add.at(stalls, (iz[stall], ix[stall]), 1)
    floor = np.full((nz, nx), np.nan, np.float32); ymax = np.full((nz, nx), np.nan, np.float32)
    order = np.lexsort((y, iz * nx + ix))
    for cell in np.unique(iz * nx + ix):
        sel = (iz * nx + ix == cell)
        g = sel & grounded
        if g.any(): floor.flat[cell] = np.median(y[g])
        ymax.flat[cell] = y[sel].max()
    resp = np.nonzero((s == 22) & np.r_[True, s[:-1] != 22])[0]
    dmg = np.nonzero(np.diff(hp) < -0.5)[0] + 1
    dmg_nonresp = [i for i in dmg if s[i] != 22]
    np.savez_compressed(f"data/map_walk_{st}.npz", x0=x0, z0=z0, res=RES, visits=visits, stalls=stalls, floor=floor, ymax=ymax,
                        respawn_xyz=np.stack([x[resp - 1], y[resp - 1], z[resp - 1]], 1) if len(resp) else np.zeros((0, 3)),
                        dmg_xyz=np.stack([x[dmg_nonresp], y[dmg_nonresp], z[dmg_nonresp]], 1) if dmg_nonresp else np.zeros((0, 3)))
    fl = floor[np.isfinite(floor)]
    lv = np.unique(np.round(fl / 10) * 10, return_counts=True)
    print(f"== {st}: frames {len(L)}  x {x.min():.0f}..{x.max():.0f}  z {z.min():.0f}..{z.max():.0f}  cells visited {int((visits>0).sum())}"
          f"  floor y {fl.min():.0f}..{fl.max():.0f}  respawns {len(resp)}  health drops {len(dmg)} (non-respawn {len(dmg_nonresp)})")
    top = np.argsort(-lv[1])[:8]
    print("   floor levels (y rounded 10: cells):", ", ".join(f"{lv[0][k]:.0f}:{lv[1][k]}" for k in sorted(top)))
    if len(resp): print("   respawn triggered at (last pos):", np.round(np.stack([x[resp-1], y[resp-1], z[resp-1]], 1)[:6]).tolist())
    states = np.unique(s.astype(int), return_counts=True)
    print("   state histogram:", dict(zip(states[0].tolist(), states[1].tolist())))
    # phases: multi-level stages (elevator/descending rooms) -> split grounded samples into y bands separated by >1000 u gaps
    gy = np.sort(y[grounded]); cuts = gy[1:][np.diff(gy) > 1000]
    edges = np.r_[-np.inf, (cuts - 1.0), np.inf]
    bands = []
    for b in range(len(edges) - 1):
        selb = grounded & (y >= edges[b]) & (y < edges[b + 1])
        vb = np.zeros((nz, nx), np.int32); np.add.at(vb, (iz[selb], ix[selb]), 1)
        bands.append((float(np.median(y[selb])), vb))
    if len(bands) > 1:
        print("   phase bands (median grounded y: cells):", ", ".join(f"{m:.0f}: {int((vb>0).sum())}" for m, vb in bands))
        np.savez_compressed(f"data/map_walk_{st}_bands.npz", band_y=np.array([m for m, _ in bands]), visits=np.stack([vb for _, vb in bands]), x0=x0, z0=z0, res=RES)
    sc = max(1, 360 // max(nx, nz))
    fmin = np.nanmin(floor) if np.isfinite(floor).any() else 0; fmax = np.nanmax(floor) if np.isfinite(floor).any() else 1
    hstack([heat(np.log1p(visits).astype(float), 0, float(np.log1p(visits).max()), sc, mask=visits == 0, title=f"{st} log visits"),
            heat(floor, float(fmin), float(fmax) + 1e-3, sc, title="ground y"),
            heat(np.minimum(stalls, 20).astype(float), 0, 20, sc, mask=visits == 0, title="wall stalls")]
           + ([heat(np.log1p(vb).astype(float), 0, float(np.log1p(vb).max()) + 1e-3, sc, mask=vb == 0, title=f"phase y~{m:.0f}") for m, vb in bands] if len(bands) > 1 else [])
           ).save(f"shots/walk_{st}.png")
