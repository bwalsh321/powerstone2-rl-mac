"""E1: drive P1 (port 0) through idle/run/a/x/b/y in slot1; record P1 block per frame."""
from harness import *
br = boot(); load(br, "states/slot1.state")
REG = {"p1": (0x8C530000, 0x8C536260), "hp": (0x8C475000, 0x8C476000)}
steps = [("none", 30), ("right", 40), ("none", 30),
         ("a", 2), ("none", 50), ("x", 2), ("none", 50),
         ("b", 2), ("none", 50), ("y", 2), ("none", 50)]
shots = {35, 60, 103, 112, 125, 155, 165, 185, 207, 217, 237, 259, 269, 289}
os.makedirs(os.path.join(HERE, "shots/e1"), exist_ok=True)
d, lab = record(br, steps, REG, shots_at=shots, shot_prefix=os.path.join(HERE, "shots/e1/f"))
np.savez_compressed(os.path.join(HERE, "data_e1.npz"), lab=np.array(lab), **d)
print("frames", len(lab))
print("DONE"); sys.stdout.flush(); os._exit(0)
