"""S07: screenshot P2 placed next to each 0C0F18D4 / 0C0F1688 ledger object; dump their records (float view)."""
from common import *
br = boot()
load(br, STATES["slot1"]); br.run_frames(60)
r = br.ram.copy()
def dumprec(a, n=0x200):
    for o in range(0, n, 16):
        ws = [u32(r, a + o + 4 * k) for k in range(4)]
        fs = [f32(r, a + o + 4 * k) for k in range(4)]
        print(f"   +{o:03X}: " + " ".join(f"{w:08X}" for w in ws) + "  " + " ".join(f"{v:11.4g}" for v in fs))
print("pad #32 record"); dumprec(0x8C504330)
print("prop #24 record"); dumprec(0x8C5021B0)
for name, (x, z) in {"pad_m1000_m1000": (-1000, -1000), "pad_950_m850": (950, -850), "prop_m500_1000": (-500, 1000), "prop_m1000_m100": (-1000, -100)}.items():
    load(br, STATES["slot1"]); br.run_frames(20)
    place(br, 0, 1100, 0, 1100)
    place(br, 1, x + 150, 0, z)
    br.run_frames(60)
    shot(br, f"shots/s07_{name}.png")
    print(name, [round(v) for v in logpos(br.ram, 1)])
print("DONE")
