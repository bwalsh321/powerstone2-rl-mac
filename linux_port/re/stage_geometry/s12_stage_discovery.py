"""S12: per-stage discovery: set_state timing, clamp test (place far out in 8 dirs, y=+600, 90 f), ledger census."""
import time, collections
from common import *
br = boot()
for name, path in STAGE_STATES.items():
    load(br, path); br.run_frames(10)
    snap = br.emu.get_state()
    t0 = time.time()
    for _ in range(5): br.emu.set_state(snap)
    dt = (time.time() - t0) / 5
    r = br.ram
    p1, p2 = logpos(r, 0), logpos(r, 1)
    print(f"== {name}  set_state {dt*1000:.1f} ms   P1 {[round(v) for v in p1]} P2 {[round(v) for v in p2]}  hp2={health(r,1):.0f}")
    c = collections.Counter(vt for _, _, vt, _ in ledger(r))
    print("   ledger vtables:", {hex(k): v for k, v in c.items()})
    cx, cz = (p1[0] + p2[0]) / 2, (p1[2] + p2[2]) / 2
    for ang in range(0, 360, 45):
        br.emu.set_state(snap); br.clear_inputs()
        x = cx + 6000 * np.cos(np.radians(ang)); z = cz + 6000 * np.sin(np.radians(ang))
        place(br, 1, x, 600, z); br.run_frames(2)
        q0 = logpos(br.ram, 1)
        br.run_frames(90)
        q = logpos(br.ram, 1)
        print(f"   far {ang:3}deg -> after2f ({q0[0]:7.0f},{q0[1]:5.0f},{q0[2]:7.0f})  after92f ({q[0]:7.0f},{q[1]:6.0f},{q[2]:7.0f}) st={pstate(br.ram,1)}")
print("DONE")
