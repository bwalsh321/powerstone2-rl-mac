"""E3: P1 standing jump (A) and running jump from base_s1.state; record P1 block + wide window."""
from harness import *
br = boot()
REG = {"p1": (0x8C530000, 0x8C536260)}
out = {}
for name, steps in {"jump": [("none", 10), ("a", 2), ("none", 70)],
                    "runjump": [("right", 30), ("right+a", 2), ("right", 70)]}.items():
    load(br, os.path.join(HERE, "base_s1.state"))
    d, lab = record(br, steps, REG)
    out[name] = d["p1"]; out[name + "_lab"] = np.array(lab)
np.savez_compressed(os.path.join(HERE, "data_e3.npz"), **out)
print("ok")
print("DONE"); sys.stdout.flush(); os._exit(0)
