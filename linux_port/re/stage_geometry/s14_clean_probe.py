"""S14: CLEAN teleport probe (state restored before EVERY probe). Usage:
   s14_clean_probe.py <stage> <tag> <x0> <x1> <z0> <z1> <step> <Y0> <F>
Per probe: restore snapshot, park P1 at the far corner, place P2 at (x, Y0, z), run F frames.
Records final pos, state byte, health delta, min y seen, frames-to-land. -> data/s14_<tag>.npz"""
from common import *
stage, tag = sys.argv[1], sys.argv[2]
x0, x1, z0, z1, step, Y0, F = map(float, sys.argv[3:10]); F = int(F)
br = boot()
load(br, STAGE_STATES[stage]); br.run_frames(10)
snap = br.emu.get_state()
xs = np.arange(x0, x1 + 1e-6, step); zs = np.arange(z0, z1 + 1e-6, step)
corners = [(x0 - 0.0, z0), (x1, z1)]
res = np.full((len(zs), len(xs), 8), np.nan, np.float32)  # fx fy fz state dhp miny land_t p1dist
hp0 = None
for corner in corners:
    for iz, z in enumerate(zs):
        for ix, x in enumerate(xs):
            d = np.hypot(x - corner[0], z - corner[1])
            if np.isfinite(res[iz, ix, 7]) and res[iz, ix, 7] >= d: continue
            br.emu.set_state(snap); br.clear_inputs()
            place(br, 0, corner[0], 0.0, corner[1])
            place(br, 1, float(x), Y0, float(z))
            hp0 = health(br.ram, 1)
            miny = 1e9; land = -1
            for t in range(F):
                br.emu.run()
                y = f32(br.ram, P[1] + 0x2C)
                miny = min(miny, y)
                if land < 0 and t > 1 and pstate(br.ram, 1) in (0, 1, 2): land = t
            p = logpos(br.ram, 1)
            res[iz, ix] = (p[0], p[1], p[2], pstate(br.ram, 1), health(br.ram, 1) - hp0, miny, land, d)
np.savez(f"data/s14_{tag}.npz", xs=xs, zs=zs, res=res, stage=stage, Y0=Y0, F=F)
dx = res[..., 0] - xs[None, :]; dz = res[..., 2] - zs[:, None]
disp = np.hypot(dx, dz)
print(f"{tag}: probes {res.shape[0]*res.shape[1]}  displaced>2: {(disp>2).sum()}  y range {np.nanmin(res[...,1]):.1f}..{np.nanmax(res[...,1]):.1f}"
      f"  states {np.unique(res[...,3]).astype(int).tolist()}  dhp<0: {(res[...,4]<0).sum()}")
print("DONE")
