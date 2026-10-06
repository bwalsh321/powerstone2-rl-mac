"""BUILD: data/map_desert.npz (the shipped per-stage map for stage id 5 / variant 0) + shots/map_desert.png.
Static part = analytic +-1140 clamp box at 10-u resolution (CONFIRMED by s03/s14/s21); props = the slot1 spawn positions
(s06) -- informational only, the encoder reads props LIVE (they get pushed/thrown, s20).
Image panels: (1) s14 clean-probe displacement, (2) s15 walk visits, (3) static+spawn-prop min ray over 8 dirs,
(4) ray 'up' (dpad up = world (-x,-z))."""
import numpy as np
from imgutil import heat, hstack
import stage_geom as G
m = G.StageMap.box()
poles = [(-1000, -1000), (950, -850), (100, 1000), (-1050, 800)]
clus = [(-500, 1000), (100, -900), (300, -1100), (-850, 1000), (-650, 1050), (-1000, -100), (-900, 100), (-1100, 300)]
np.savez_compressed("data/map_desert.npz", x0=m.x0, z0=m.z0, res=m.res, walk=m.walk, floor=m.floor,
                    spawn_poles=np.array(poles, np.float32), spawn_clusters=np.array(clus, np.float32),
                    note="stage id 5 variant 0; box +-1140; props are dynamic -> read live from the ledger")
xs = m.x0 + m.res * np.arange(m.walk.shape[1]); zs = m.z0 + m.res * np.arange(m.walk.shape[0])
props = [(G.POLE_VT, a, b) for a, b in poles] + [(G.CLUSTER_VT, a, b) for a, b in clus]
sub = 4                                  # evaluate the full encoder on a 40-u lattice for the figure
R = np.zeros((len(zs[::sub]), len(xs[::sub]), 8), np.float32)
for i, z in enumerate(zs[::sub]):
    for j, x in enumerate(xs[::sub]):
        rays = m.ray[:, int(round((z - m.z0) / m.res)), int(round((x - m.x0) / m.res))].copy()
        for vt, cx, cz, *_ in props:
            rays = np.minimum(rays, G.ray_circle(x, z, m.dirs, cx, cz, G.PROP_RADIUS[vt]))
        R[i, j] = rays
d14 = np.load("data/s14_desert_ground.npz"); r14 = d14["res"]
disp = np.hypot(r14[..., 0] - d14["xs"][None, :], r14[..., 2] - d14["zs"][:, None])
w = np.load("data/map_walk_desert.npz")
hstack([heat(np.minimum(disp, 150), 0, 150, 3, title="probe pushout (s14)"),
        heat(np.log1p(w["visits"]).astype(float), 0, float(np.log1p(w["visits"]).max()), 3, mask=w["visits"] == 0, title="walk visits (s15)"),
        heat(R.min(-1), 0, 400, 6, title="min ray, 8 dirs"),
        heat(R[..., 0], 0, 1000, 6, title="ray dpad-UP")]).save("shots/map_desert.png")
print("saved data/map_desert.npz shots/map_desert.png")
