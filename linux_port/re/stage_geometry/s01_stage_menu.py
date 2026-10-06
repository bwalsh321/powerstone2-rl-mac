"""S01: walk the STAGE SELECT cursor (menu_stage.state) over all cells; screenshot each name label.
Also screenshot slots 1-3 after 900 frames (past intro)."""
from common import *
br = boot()
load(br, "menu_stage.state")
br.run_frames(20)
seq = [("none","r1c0"),("up","r0c0"),("right","r0c1"),("right","r0c2"),("down","r1c2"),("left","r1c1"),
       ("down","r2c1"),("left","r2c0"),("right","r2c1b"),("right","r2c2")]
for b, name in seq:
    if b != "none":
        setpad(br, b, 0); br.run_frames(4); setpad(br, "none", 0); br.run_frames(20)
    shot(br, f"shots/s01_{name}.png")
for s in ("slot1", "slot2", "slot3"):
    load(br, STATES[s]); br.run_frames(900)
    shot(br, f"shots/s01_{s}_f900.png")
    r = br.ram
    print(s, [[round(v) for v in logpos(r, i)] for i in range(4)])
print("DONE")
