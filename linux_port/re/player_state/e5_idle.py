"""E5: 300 idle frames from base_s1 - does P2 move by itself (COM) ? record both structs."""
from harness import *
br = boot(); load(br, os.path.join(HERE, "base_s1.state"))
d, lab = record(br, [("none", 300)], {"p1": preg(0), "p2": preg(1), "g": (0x8C470000, 0x8C480000)})
np.savez_compressed(os.path.join(HERE, "data_e5.npz"), lab=np.array(lab), **d)
for t in range(0, 300, 30):
    print(t, "P1", [round(f32(d["p1"][t], 0x28 + 4*k + 0x8C000000 - 0x8C000000) if False else 0, 1) for k in range(1)], end=" ")
    a = d["p2"][t].view("<f4"); b = d["p1"][t].view("<f4")
    print("P1pos", b[10:13].round(1), "P2pos", a[10:13].round(1))
print("DONE"); sys.stdout.flush(); os._exit(0)
