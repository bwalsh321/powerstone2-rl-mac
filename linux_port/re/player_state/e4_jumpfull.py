"""E4: full-RAM search during a standing jump for vertical velocity (linear ramp) and
logical height (parabola). Stores snaps of frames 12..62 for later analysis."""
from harness import *
br = boot(); load(br, os.path.join(HERE, "base_s1.state"))
br.press(0, 10, player=0); br.press(BTN["a"], 2, player=0); br.press(0, 0, player=0)
snaps = []
for t in range(50):
    br.run_frames(1); snaps.append(snap(br).view("<f4").copy())
S = np.stack(snaps).astype(np.float64)
np.save(os.path.join(HERE, "data_e4_full.npy"), np.stack(snaps)[:, :])  # f32
print("DONE"); sys.stdout.flush(); os._exit(0)
