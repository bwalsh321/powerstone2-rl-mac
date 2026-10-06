"""Screenshot every menu_*.state (after 20 frames) to see what screen each one is on."""
from harness import *
import glob
br = boot(); os.makedirs(os.path.join(HERE, "shots/menus"), exist_ok=True)
for p in sorted(glob.glob(os.path.join(LP, "menu_*.state"))):
    load(br, p); br.run_frames(20)
    n = os.path.basename(p)[:-6]; shot(br, os.path.join(HERE, f"shots/menus/{n}.png"))
    r = snap(br); print(n, "fightctr", u32(r, 0x8C475200), "seat table", [[u32(r, 0x8C472DA8 + 0x14*i + 4*k) for k in (0, 2, 4)] for i in range(4)])
print("DONE"); sys.stdout.flush(); os._exit(0)
