"""Independent check (main session): is F+0x54 a ledger-slot pointer (type varies per ptr)?
And do live pickup records exist past OBJ_GRID_N=110?"""
import gzip, os, sys, collections, struct
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
import numpy as np
from flycast_bridge import FlycastBridge
import ps2_addr as A
core = os.path.expanduser("~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib")
game = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../Power Stone 2 (USA).chd"))
br = FlycastBridge(core, game, "./states", instance_id=7)
ram = br.ram
u32 = lambda a: struct.unpack_from("<I", ram, (a & 0xFFFFFF))[0]
u8 = lambda a: int(ram[a & 0xFFFFFF])
seen = collections.defaultdict(collections.Counter)   # ptr -> Counter(type)
maxslot = 0; beyond = 0; samples = 0
for st in ["slot2", "slot3"]:
    br.run_frames(4)
    br.emu.set_state(gzip.open(f"states/{st}.state").read()); br.run_frames(4)
    rng = np.random.default_rng(1)
    for f in range(9000):
        if f % 20 == 0:   # P2 random-ish inputs so it also picks things up
            m = int(rng.choice([0x004, 0x002, 0x400, 0x010, 0x020, 0x040, 0x080, 0x012, 0x044, 0]))
            br.press(m, 1, player=1)
        else:
            br.run_frames(1)
        if f % 5: continue
        samples += 1
        for (_, F) in A.GEMS:
            p = u32(F + A.PF_ITEMP)
            if p:
                seen[p][u8(p + 0x41C)] += 1
        for k in range(0, 240):
            rec = A.OBJ_GRID_LO + k * 0x430
            if (u32(rec + 4) & 0xFF) == 0x09 and 0x0C000000 <= u32(rec + 8) < 0x0C200000:
                maxslot = max(maxslot, k)
                if k >= A.OBJ_GRID_N: beyond += 1
multi = {hex(p): dict(c) for p, c in seen.items() if len(c) > 1}
print(f"samples={samples} distinct_ptrs={len(seen)} ptrs_with_multiple_types={len(multi)}")
for p, c in list(multi.items())[:10]: print("  ", p, c)
print("on 0x430 grid residue 0x1E4:", sum(1 for p in seen if p % 0x430 == 0x1E4), "/", len(seen))
print(f"max live ledger slot={maxslot}  sightings at slot>={A.OBJ_GRID_N}: {beyond}")
br.emu.close()
