"""Press A repeatedly on P1's character box (menu_cycle.state) and log the seat-table char id."""
from harness import *
br = boot(); load(br, os.path.join(LP, "menu_cycle.state")); br.run_frames(10)
os.makedirs(os.path.join(HERE, "shots/cc"), exist_ok=True)
for i in range(18):
    br.press(BTN["a"], 2, player=0); br.press(0, 25, player=0)
    r = snap(br); c = u32(r, 0x8C472DA8 + 8)
    shot(br, os.path.join(HERE, f"shots/cc/{i:02d}_char{c}.png")); print(i, "P1 char id", c)
print("DONE"); sys.stdout.flush(); os._exit(0)
