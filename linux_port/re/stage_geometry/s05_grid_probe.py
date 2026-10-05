"""S05: teleport-probe grid. For each (x,z) place P2 at (x, Y0, z), run F frames, record final logical pos + state.
Displacement in xz => static collider resolves penetration (wall/obstacle). Usage: s05_grid_probe.py state step Y0 F tag"""
import sys
from common import *
state, step, Y0, F, tag = sys.argv[1], int(sys.argv[2]), float(sys.argv[3]), int(sys.argv[4]), sys.argv[5]
br = boot()
xs = np.arange(-1200, 1201, step)
res = np.zeros((len(xs), len(xs), 5), np.float32)  # fx, fy, fz, state, p1far
n = 0
def reset():
    load(br, STATES.get(state, state)); br.run_frames(20)
for corner in ((-1100.0, -1100.0), (1100.0, 1100.0)):
    reset()
    for iz, z in enumerate(xs):
        for ix, x in enumerate(xs):
            d = np.hypot(x - corner[0], z - corner[1])
            if res[iz, ix, 4] > d:   # already probed with P1 farther away
                continue
            if n % 300 == 0:
                reset()
            n += 1
            place(br, 0, corner[0], 0.0, corner[1])
            place(br, 1, float(x), Y0, float(z))
            br.run_frames(F)
            p = logpos(br.ram, 1)
            res[iz, ix] = (p[0], p[1], p[2], pstate(br.ram, 1), d)
np.savez(f"data/s05_{tag}.npz", xs=xs, res=res)
dx = res[..., 0] - xs[None, :]; dz = res[..., 2] - xs[:, None]
inside = (np.abs(xs[None, :]) <= 1140) & (np.abs(xs[:, None]) <= 1140)
disp = np.hypot(dx, dz)
print("probes", n, "inside-box points", inside.sum(), "displaced>1 inside box", (disp[inside] > 1).sum())
print("final y unique (rounded):", np.unique(np.round(res[..., 1][inside])) [:40])
idx = np.argwhere(inside & (disp > 1))
for iz, ix in idx[:60]:
    print("  ", (xs[ix], xs[iz]), "->", np.round(res[iz, ix, :3], 1), "st", res[iz, ix, 3])
print("DONE")
