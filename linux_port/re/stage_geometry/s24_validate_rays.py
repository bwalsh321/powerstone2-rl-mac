"""S24: closed-loop validation of the stage_geom ray features on the live desert (slot1).
Trial: restore snapshot, park P1 at (1100,1100), place P2 at a random point, compute the encoder (props read LIVE from RAM,
dpad frame from the live camera), pick a dpad dir k, hold it for 160 f; travelled distance = progress along dir k at the first frame (after f20) where the 6-frame mean
speed along k drops < 6.0 u/f (free run 7.2; a 45-deg wall slide gives 5.1; blocked 0) or after 160 f. Compare with ray_k (capped 1000).
Output: per-trial (pred, actual, blocker type) + summary. -> data/s24_validate.npz"""
from common import *
sys.path.insert(0, HERE)
import stage_geom as G
br = boot()
load(br, STATES["slot1"]); br.run_frames(10)
place(br, 0, 1100, 0, 1100); br.run_frames(2)
snap = br.emu.get_state()
enc = G.SpatialEncoder()
rng = np.random.default_rng(3)
DN = ["up", "down", "left", "right", "up+left", "up+right", "down+left", "down+right"]
rows = []; trajs = []
for trial in range(240):
    br.emu.set_state(snap); br.clear_inputs()
    x, z = rng.uniform(-1100, 1100, 2)
    place(br, 1, x, 0, z); br.run_frames(3)
    p = logpos(br.ram, 1)
    props = G.read_props(br.ram)
    enc.maps[5].dirs = G.dpad_dirs_from_camera(br.ram)
    v = enc(br.ram, p[0], p[1], p[2], props=props)
    k = int(rng.integers(8))
    # which blocker does the model predict? (static box vs pole vs cluster)
    dirs = enc.maps[5].dirs
    kinds = {"box": enc.maps[5].ray[k][enc.maps[5]._idx(p[0], p[2])]}
    for vt, cx, cz, *_ in props:
        d = G.ray_circle(p[0], p[2], dirs[k:k+1], cx, cz, G.PROP_RADIUS[vt])[0]
        nm = "pole" if vt == G.POLE_VT else "cluster"
        kinds[nm] = min(kinds.get(nm, G.RAY_MAX), d)
    blk = min(kinds, key=kinds.get)
    setpad(br, DN[k], 1)
    prog = []
    for t in range(160):
        br.run_frames(1)
        q = np.array(logpos(br.ram, 1))
        prog.append((q[0] - p[0]) * dirs[k, 0] + (q[2] - p[2]) * dirs[k, 1])     # progress ALONG the commanded dir
    prog = np.array(prog)
    sm = (prog[6:] - prog[:-6]) / 6.0                                           # 6-frame mean speed along dir
    bad = np.nonzero((np.arange(len(sm)) + 6 > 20) & (sm < 6.0))[0]           # deflected (wall slide 5.1) / blocked
    stopped = len(bad) > 0
    travel = prog[bad[0] + 6] if stopped else prog[-1]       # end of the first slow window
    rows.append((v[k] * G.RAY_MAX, travel, stopped, ["box", "pole", "cluster"].index(blk), k))
    trajs.append(prog)
R = np.array(rows, np.float32)
np.savez("data/s24_validate.npz", rows=R, trajs=np.array(trajs, np.float32))
pred, act, stp, bk = R[:, 0], R[:, 1], R[:, 2] > 0, R[:, 3]
for b, nm in enumerate(["box", "pole", "cluster"]):
    m = (bk == b) & (pred < 900)
    if m.any():
        e = act[m] - pred[m]
        print(f"{nm:8s} n={m.sum():3d}  stopped {stp[m].mean():.2f}  |err| median {np.median(np.abs(e)):6.1f}  p90 {np.percentile(np.abs(e), 90):6.1f}  mean err {e.mean():+6.1f}")
far = pred >= 999
print(f"no blocker within 1000: n={far.sum()}  stopped early {stp[far].mean():.2f}  min travel {act[far].min() if far.any() else 0:.0f}")
print("DONE")
