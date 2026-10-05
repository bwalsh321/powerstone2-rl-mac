"""E8: record the per-player external blocks pointed by P+0x118/P+0x11C (0x8C40D600..0x8C40E000)
during a whiffed punch (x) and kick (b) by P1."""
from harness import *
br = boot(); out = {}
for btn in ("x", "b"):
    load(br, os.path.join(HERE, "base_s1.state"))
    d, lab = record(br, [(btn, 2), ("none", 50)], {"r": (0x8C40D600, 0x8C40E000), "p1": preg(0)})
    out[btn] = d["r"]; out[btn + "_p1"] = d["p1"]
np.savez_compressed(os.path.join(HERE, "data_e8.npz"), **out)
print("DONE"); sys.stdout.flush(); os._exit(0)
