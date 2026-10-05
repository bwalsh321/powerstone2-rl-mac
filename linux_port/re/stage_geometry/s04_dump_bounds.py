"""S04: hexdump/float-dump around the 1140.0 hits (candidate stage-bounds records)."""
from common import *
br = boot()
load(br, STATES["slot1"]); br.run_frames(60)
r = br.ram.copy()
def dump(a0, n):
    for a in range(a0, a0 + n, 16):
        ws = [u32(r, a + 4 * k) for k in range(4)]
        fs = [f32(r, a + 4 * k) for k in range(4)]
        print(f"  {a:08X}: " + " ".join(f"{w:08X}" for w in ws) + "   " + " ".join(f"{v:12.4g}" for v in fs))
for a in (0x8C3F2100, 0x8C5433A0, 0x8C28A040, 0x8C28E120):
    print(hex(a)); dump(a, 0xA0)
print("DONE")
