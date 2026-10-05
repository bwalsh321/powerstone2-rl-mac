"""Offline unit test of stage_geom (no emulator): desert box + the 4 poles/8 clusters at their slot1 positions."""
import time, numpy as np
from stage_geom import *
t0 = time.time(); enc = SpatialEncoder(); print(f"precompute {time.time()-t0:.2f}s")
props = [(POLE_VT, -1000, -1000), (POLE_VT, 950, -850), (POLE_VT, 100, 1000), (POLE_VT, -1050, 800)] + \
        [(CLUSTER_VT, x, z) for x, z in [(-500, 1000), (100, -900), (300, -1100), (-850, 1000), (-650, 1050), (-1000, -100), (-900, 100), (-1100, 300)]]
class FakeRam(bytearray): pass
ram = bytearray(16 * 1024 * 1024)
struct.pack_into("<I", ram, STAGE_ID_ADDR & 0xFFFFFF, 5)
for (x, z) in [(0, 0), (1100, 0), (100, 900), (-400, -900)]:
    t0 = time.perf_counter(); v = enc(ram, x, 0.0, z, props=props); dt = time.perf_counter() - t0
    print((x, z), f"{dt*1e6:.0f}us", "rays", np.round(v[0:8] * RAY_MAX).astype(int).tolist(), "pole", np.round(v[8:11], 3).tolist(),
          "edge", np.round(v[14:17], 3).tolist())
print("DONE")
