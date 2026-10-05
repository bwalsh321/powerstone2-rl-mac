"""E16c: dump bytes in 0x8C472A00-0x8C472E00 and 0x8C46E000-0x8C46E400 that differ across the 6 stage states (same 2 Falcons, same menu path)."""
from harness import *
br = boot()
order = [("iceberg", "c0"), ("space", "r"), ("desert", "d"), ("ship", "dd"), ("pharaoh", "rd"), ("garden", "rdd"), ("iceberg2", "rr"), ("ship2", "u")]
S = []
for g, n in order:
    load(br, os.path.join(HERE, f"stage_{n}.state")); S.append(snap(br))
S = np.stack(S)
print("cols:", [g for g, _ in order])
for lo, hi in ((0x472A00, 0x472E40), (0x46E000, 0x46E400), (0x475000, 0x475300)):
    for a in range(lo, hi):
        col = S[:, a]
        if len(set(col.tolist())) > 1 and col[0] == col[6] and col[3] == col[7]:
            print(f"  {0x8C000000+a:08X}", col.tolist())
print("DONE"); sys.stdout.flush(); os._exit(0)
