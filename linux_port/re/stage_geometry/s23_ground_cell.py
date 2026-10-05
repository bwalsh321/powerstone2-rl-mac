"""S23: is 0x8C471A78 the floor height UNDER P2 (shadow), or P2's y? P2 jumps (A) on desert and on the bluesky deck;
P2 then teleported above a cactus cluster (desert) mid-air. Prints P2 y, 0x8C471A6C..0x8C471A8C per few frames."""
from common import *
br = boot()
for stage in ("desert", "bluesky"):
    load(br, STAGE_STATES[stage]); br.run_frames(10)
    print("==", stage)
    setpad(br, "a", 1)
    for t in range(48):
        br.run_frames(1)
        if t == 6: setpad(br, "none", 1)
        if t % 6 == 0:
            r = br.ram
            print(f"  t{t:2} P2 y={logpos(r,1)[1]:7.1f} st={pstate(r,1):2}  P1 y={logpos(r,0)[1]:6.1f}  cells " +
                  " ".join(f"{f32(r, a):8.1f}" for a in range(0x8C471A60, 0x8C471A90, 4)))
print("DONE")
