"""S02: does teleporting P2 (logical pos P+0x28 & P+0x94) work, and what happens when dropped from height / into walls?"""
from common import *
br = boot()
load(br, STATES["slot1"]); br.run_frames(60)
I = 1
tests = [(0, 400, 0), (-150, 400, 900), (0, 400, 2000), (3000, 400, 0), (-150, 0, 900), (500, 0, 0), (0, 1500, 0)]
for (x, y, z) in tests:
    load(br, STATES["slot1"]); br.run_frames(30)
    place(br, I, x, y, z)
    tr = []
    for t in range(120):
        br.run_frames(1)
        lp = logpos(br.ram, I)
        tr.append((t, [round(v, 1) for v in lp], pstate(br.ram, I)))
    print(f"place {x,y,z}:")
    for t, lp, st in tr[:5] + tr[5::15] + tr[-1:]:
        print("   ", t, lp, st)
    shot(br, f"shots/s02_{x}_{y}_{z}.png")
print("DONE")
