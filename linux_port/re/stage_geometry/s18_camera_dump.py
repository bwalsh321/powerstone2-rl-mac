"""S18: dump the camera candidate block 0x8C541180.. and 0x8C00ECD0.. at 3 moments (players spread apart differently)
alongside the P1/P2 midpoint, to label camera eye / target / distance fields."""
from common import *
br = boot()
load(br, STATES["slot1"]); br.run_frames(10)
def dump(a0, n):
    r = br.ram
    for a in range(a0, a0 + n, 16):
        print(f"   {a:08X}: " + " ".join(f"{f32(r, a + 4*k):10.2f}" for k in range(4)))
for (p1, p2) in [((-400, -400), (400, 400)), ((0, 0), (100, 0)), ((-1000, 500), (900, 600))]:
    place(br, 0, p1[0], 0, p1[1]); place(br, 1, p2[0], 0, p2[1])
    br.run_frames(240)
    r = br.ram
    m = (np.array(logpos(r, 0)) + np.array(logpos(r, 1))) / 2
    print(f"== P1 {[round(v) for v in logpos(r,0)]} P2 {[round(v) for v in logpos(r,1)]} mid {np.round(m,1).tolist()}")
    dump(0x8C541180, 0x80); print("   ..."); dump(0x8C00ECD0, 0x30)
print("DONE")
