"""E12: full-RAM snapshots of slot1/2/3 (after 30 frames) for character/COM/level/stage diffing."""
from harness import *
br = boot(); S = []
for s in (1, 2, 3):
    load(br, f"states/slot{s}.state"); br.run_frames(30); S.append(snap(br))
load(br, os.path.join(HERE, "base_s1.state")); br.run_frames(30); S.append(snap(br))
np.save(os.path.join(HERE, "data_e12_slots.npy"), np.stack(S))
print("DONE"); sys.stdout.flush(); os._exit(0)
