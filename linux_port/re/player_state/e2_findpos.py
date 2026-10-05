"""E2: find all RAM copies of P1's world position (x,z) while running, and save full-RAM snaps."""
from harness import *
br = boot(); load(br, "states/slot1.state")
br.run_frames(200)      # get past READY/ACTION intro
with gzip.open(os.path.join(HERE, "base_s1.state"), "wb") as fh: fh.write(br.emu.get_state())
snaps = []
br.press(BTN["right"] | BTN["down"], 20, player=0)
for k in range(4):
    br.press(BTN["right"] | BTN["down"], 1, player=0)
    snaps.append(snap(br))
np.save(os.path.join(HERE, "data_e2_snaps.npy"), np.stack(snaps))
fl = [s[: (len(s)//4)*4].view("<f4") for s in snaps]
for ax, o in zip("xyz", A.MAT_POS):
    vals = [f32(s, MAT[0] + o) for s in snaps]
    m = np.ones(len(fl[0]), bool)
    for v, F_ in zip(vals, fl):
        m &= np.abs(F_ - v) < 1.0
    print(ax, [round(v, 2) for v in vals], [hex(0x8C000000 + 4*i) for i in np.nonzero(m)[0]][:30])
print("DONE"); sys.stdout.flush(); os._exit(0)
