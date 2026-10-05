"""S00: load each savestate, screenshot, print player positions (mat vs logical) and state bytes."""
from common import *
br = boot()
for name, p in list(STATES.items()) + [("menu_stage", "menu_stage.state"), ("menu_match", "menu_match.state")]:
    load(br, p)
    br.run_frames(30)
    r = br.ram
    shot(br, f"shots/s00_{name}.png")
    print(name)
    for i in range(4):
        print(f"  P{i+1} mat={[round(v,1) for v in matpos(r,i)]} log={[round(v,1) for v in logpos(r,i)]} st={pstate(r,i)}")
print("DONE")
