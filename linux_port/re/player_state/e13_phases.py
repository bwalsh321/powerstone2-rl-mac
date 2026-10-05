"""E13: match-phase globals. (a) slot1 from load through READY/ACTION intro; (b) from base_s1, drop
P2 health to 10 and punch -> KO -> whatever follows (1500 frames). Records 0x8C470000-0x8C480000 per
frame (+ P structs every frame) and screenshots every 30 frames."""
from harness import *
from flycast_bridge import DC_TO_RETRO
br = boot()
def setm(port, mask):
    m = np.zeros(16, np.uint8)
    for bit, rid in DC_TO_RETRO.items():
        if mask & bit: m[rid] = 1
    br.emu.set_button_mask(m, port)
G = (0x8C470000, 0x8C480000)
sd = os.path.join(HERE, "shots/e13"); os.makedirs(sd, exist_ok=True)
out = {}
for name in ("intro", "ko"):
    if name == "intro":
        load(br, "states/slot1.state"); n = 300; seq = [0] * n
    else:
        load(br, os.path.join(HERE, "base_s1.state"))
        r = snap(br); x, y, z = ppos(r, 0); place(br, 1, x, 0, z - 90)
        for a_ in (A.HEALTH_OBJ[1], A.HEALTH[1], A.HEALTH[1] + 0x30, A.HEALTH[1] + 0x50): wf32(br, a_, 10.0)
        br.run_frames(2); n = 1800; seq = [BTN["x"]] * 2 + [0] * (n - 2)
    g = []; p = []
    for t in range(n):
        setm(0, seq[t]); br.emu.run()
        g.append(br.ram[off(G[0]):off(G[1])].copy())
        p.append(np.stack([br.ram[off(P[i]):off(P[i]) + 0x400].copy() for i in range(2)]))
        if t % 30 == 0: shot(br, os.path.join(sd, f"{name}_{t:04d}.png"))
    out[name] = np.stack(g); out[name + "_p"] = np.stack(p)
np.savez_compressed(os.path.join(HERE, "data_e13.npz"), **out)
print("DONE"); sys.stdout.flush(); os._exit(0)
