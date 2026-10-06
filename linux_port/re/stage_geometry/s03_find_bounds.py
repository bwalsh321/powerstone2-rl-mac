"""S03: search RAM (desert slot1, live match) for the 1140 clamp constant and neighbours; corner test."""
from common import *
import time
br = boot()
load(br, STATES["slot1"]); br.run_frames(30)
t0 = time.time(); br.run_frames(600); print("fps", 600 / (time.time() - t0))
r = br.ram.copy()
I = 1
for (x, z) in [(3000, 3000), (-3000, -3000), (3000, -3000), (1300, 1300), (1100, 1100), (1000, 1000), (-1139, 500)]:
    load(br, STATES["slot1"]); br.run_frames(30)
    place(br, I, x, 0, z); br.run_frames(2)
    print("place", (x, z), "->", [round(v, 1) for v in logpos(br.ram, I)])
f = np.frombuffer(r.tobytes(), dtype="<f4")
for val in (1140.0, -1140.0, 1200.0, -1200.0, 1080.0, 1100.0, 1160.0):
    idx = np.nonzero(f == np.float32(val))[0]
    print(val, len(idx), [hex(0x8C000000 + 4 * i) for i in idx[:40]])
print("DONE")
