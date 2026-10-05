"""E14: full-RAM snapshots at labelled match phases (slot1 intro, then base_s1 KO sequence).
labels: 0=intro READY, 1=intro ACTION!, 2=fighting, 3=KO banner, 4=post-KO, 5=VICTORY, 6=continue menu"""
from harness import *
from flycast_bridge import DC_TO_RETRO
br = boot()
def setm(port, mask):
    m = np.zeros(16, np.uint8)
    for bit, rid in DC_TO_RETRO.items():
        if mask & bit: m[rid] = 1
    br.emu.set_button_mask(m, port)
snaps, labels, frames = [], [], []
load(br, "states/slot1.state")
plan = {5: 0, 40: 0, 110: 1, 130: 1, 220: 2, 280: 2}
for t in range(300):
    br.emu.run()
    if t in plan: snaps.append(snap(br)); labels.append(plan[t]); frames.append(("intro", t))
load(br, os.path.join(HERE, "base_s1.state"))
snaps.append(snap(br)); labels.append(2); frames.append(("ko", -1))
r = snap(br); x, y, z = ppos(r, 0); place(br, 1, x, 0, z - 90)
for a_ in (A.HEALTH_OBJ[1], A.HEALTH[1], A.HEALTH[1] + 0x30, A.HEALTH[1] + 0x50): wf32(br, a_, 10.0)
br.run_frames(2)
plan = {30: 2, 120: 3, 180: 3, 260: 4, 360: 4, 450: 5, 560: 5, 700: 6, 900: 6}
for t in range(901):
    setm(0, BTN["x"] if t < 2 else 0); br.emu.run()
    if t in plan: snaps.append(snap(br)); labels.append(plan[t]); frames.append(("ko", t))
np.save(os.path.join(HERE, "data_e14_snaps.npy"), np.stack(snaps)); np.save(os.path.join(HERE, "data_e14_labels.npy"), np.array(labels))
print(frames)
print("DONE"); sys.stdout.flush(); os._exit(0)
