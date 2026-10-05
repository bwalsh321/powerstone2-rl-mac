"""E19: compact 4-player census for hitbox validation in the wild (COM fights + random P1/P2 inputs).
Per frame, per seat: selected u32 words (see COLS). Health refilled every 300 frames (no KOs).
usage: e19_census_hit.py SLOTPATH FRAMES TAG SEED"""
import random
from harness import *
from flycast_bridge import DC_TO_RETRO
sp, N, tag, seed = sys.argv[1], int(sys.argv[2]), sys.argv[3], int(sys.argv[4]); random.seed(seed)
COLS = [0x28, 0x2C, 0x30, 0x124, 0x12C, 0x134, 0x160, 0x18C, 0x190, 0x194, 0x198, 0x19C, 0x1A4, 0x1AC, 0x1B0,
        0x1B4, 0x1B8, 0x3714, 0x3718, 0x376C, 0x3770, 0x3774, 0x3818, 0x3820, 0x0000]
br = boot(); load(br, sp)
out = np.zeros((N, 4, len(COLS)), np.uint32)
raw = np.zeros((N, 4, 0x80), np.uint32)   # P+0x160..0x360
def setm(port, mask):
    m = np.zeros(16, np.uint8)
    for bit, rid in DC_TO_RETRO.items():
        if mask & bit: m[rid] = 1
    br.emu.set_button_mask(m, port)
BTNS = [0, BTN["x"], BTN["a"], BTN["b"], BTN["y"], BTN["x"] | BTN["a"], BTN["a"] | BTN["b"], BTN["x"] | BTN["b"] | BTN["a"]]
DIRS = [0, BTN["up"], BTN["down"], BTN["left"], BTN["right"], BTN["up"] | BTN["left"], BTN["down"] | BTN["right"]]
cur = [0, 0]; left = [0, 0]
idx = np.array(COLS)
for t in range(N):
    for port in (0, 1):
        if left[port] <= 0:
            cur[port] = random.choice(DIRS) | (random.choice(BTNS) if random.random() < 0.5 else 0); left[port] = random.randint(2, 25)
        left[port] -= 1; setm(port, cur[port])
    br.emu.run()
    for k in range(4):
        o = off(P[k]) + idx
        out[t, k] = br.ram[o].astype(np.uint32) | br.ram[o+1].astype(np.uint32) << 8 | br.ram[o+2].astype(np.uint32) << 16 | br.ram[o+3].astype(np.uint32) << 24
    for k in range(4):
        raw[t, k] = br.ram[off(P[k]) + 0x160: off(P[k]) + 0x360].view('<u4')
    if t % 300 == 0:
        for k in range(4):
            for ad in (A.HEALTH_OBJ[k], A.HEALTH[k], A.HEALTH[k] + 0x30, A.HEALTH[k] + 0x50): wf32(br, ad, 1000.0)
np.savez_compressed(os.path.join(HERE, f"data_e19_{tag}.npz"), out=out, cols=np.array(COLS), raw=raw)
print("DONE"); sys.stdout.flush(); os._exit(0)
