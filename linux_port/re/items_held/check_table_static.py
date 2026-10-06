"""Is the item table / name table identical across savestates (static game data)?
Loads slot1/slot2/slot3, hashes 0x0C273900..+121*0x34 and the name-pointer table."""
import hashlib
from common import *
br = boot()
for s in ("states/slot1.state", "states/slot2.state", "states/slot3.state"):
    load(br, s); br.run_frames(60); ram = br.emu.get_ram()
    t = bytes(ram[off(0x0C273900):off(0x0C273900) + 121 * 0x34])
    n = bytes(ram[off(0x0C29DDD0):off(0x0C29DDD0) + 183 * 4])
    print(s, "item_table md5", hashlib.md5(t).hexdigest(), "name_ptrs md5", hashlib.md5(n).hexdigest(),
          "gun counter", u16(ram, 0x0C273906), "MG counter", u16(ram, 0x0C273900 + 11 * 0x34 + 6))
