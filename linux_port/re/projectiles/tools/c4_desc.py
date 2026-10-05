"""Dump melee attack descriptors (PLAYER_MAT-0x490+0x414 targets, 0x14-byte entries) from a live state."""
import gzip, os, sys, struct, numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, ROOT)
from flycast_bridge import FlycastBridge
core = os.path.expanduser("~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib")
br = FlycastBridge(core, os.path.join(ROOT, "../Power Stone 2 (USA).chd"), os.path.join(ROOT, "states"), instance_id=4)
br.run_frames(8)
br.emu.set_state(gzip.open(sys.argv[1]).read()); br.run_frames(4)
r = br.ram
for a in [int(x, 16) for x in sys.argv[2:]]:
    o = a & 0x00FFFFFF
    print(f"{a:#x}:")
    for e in range(6):
        b = bytes(r[o + e * 0x14: o + e * 0x14 + 0x14])
        print("   ", b.hex(" "), " f:", [round(x, 2) for x in struct.unpack("<5f", b)], " h:", struct.unpack("<10h", b))
br.emu.close()
