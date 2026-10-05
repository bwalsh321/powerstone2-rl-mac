"""Probe 1: sample F+0x54 for all 4 players while COMs play; for each held
pointer record the object-slot vtable (ptr+4 == slot+8) and screenshot first
sighting. Hypothesis: F+0x54 is (object-arena slot + 4), not a def table."""
import sys, random, json
from common import *
slot = sys.argv[1] if len(sys.argv) > 1 else "states/slot2.state"
N = int(sys.argv[2]) if len(sys.argv) > 2 else 12000
tag = os.path.basename(slot).split(".")[0]
br = boot(); load(br, slot); ram = br.emu.get_ram()
seen_ptr = {}; seen_vt = {}
rng = random.Random(1)
for fr in range(N):
    if fr % 30 == 0:  # random-ish inputs for P1,P2 so the humans also act
        for p in (0, 1):
            m = rng.choice([0, BTN["left"], BTN["right"], BTN["up"], BTN["down"],
                            BTN["a"], BTN["b"], BTN["y"], BTN["x"],
                            BTN["up"] | BTN["right"], BTN["down"] | BTN["left"]])
            br.press(m, 0, player=p)
    br.run_frames(1)
    for p in range(4):
        ptr = u32(ram, F[p] + 0x54)
        if not ptr:
            continue
        vt = u32(ram, ptr + 4)
        key = (ptr, vt)
        if vt not in seen_vt:
            seen_vt[vt] = fr
            fn = f"shots/{tag}_vt{vt:08x}_P{p+1}_f{fr}.png"
            shot(br, os.path.join(HERE, fn))
            hdr = words(ram, ptr - 4, 24)
            print(f"NEWVT f={fr} P{p+1} ptr={ptr:08x} slotres={(ptr-0x0C500030)%0x430:#x} "
                  f"vt={vt:08x} bucket={(ptr//0x430)%256} shot={fn}")
            print("   slot words:", " ".join(f"{w:08x}" for w in hdr))
        seen_ptr.setdefault(key, 0); seen_ptr[key] += 1
print("SUMMARY ptr,vt,frames_held")
for (p, v), c in sorted(seen_ptr.items()):
    print(f"  {p:08x} vt={v:08x} bucket={(p//0x430)%256} n={c}")
