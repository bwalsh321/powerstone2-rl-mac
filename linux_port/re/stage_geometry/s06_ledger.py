"""S06: list every live object-ledger slot (0x8C4FBD30 stride 0x430) with vtable + pos, on each state."""
from common import *
import collections
br = boot()
for s in ("slot1", "slot3"):
    load(br, STATES[s]); br.run_frames(60)
    r = br.ram
    print("==", s)
    for k in range(A.OBJ_GRID_N + 40):
        a = A.OBJ_GRID_LO + k * A.OBJ_GRID_STRIDE
        hdr = u32(r, a + 4); vt = u32(r, a + 8)
        if (hdr & 0xFF) != 0x09: continue
        pos = [f32(r, a + o) for o in A.OBJ_POS]
        print(f"  #{k:3d} {a:08X} hdr={hdr:08X} vt={vt:08X} pos=({pos[0]:8.1f},{pos[1]:7.1f},{pos[2]:8.1f})")
print("DONE")
