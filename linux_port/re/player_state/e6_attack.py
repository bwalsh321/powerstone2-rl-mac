"""E6: place P2 100 units in front of P1, then P1 presses x / b / y / a+x (separate runs).
Records P1/P2 structs + screenshots; reports health at P+0x160 and HEALTH table."""
from harness import *
br = boot()
OUT = {}
os.makedirs(os.path.join(HERE, "shots/e6"), exist_ok=True)
for btn in ["x", "b", "y", "x+b", "a+x"]:
    load(br, os.path.join(HERE, "base_s1.state"))
    r = snap(br); x, y, z = ppos(r, 0)
    # P1 facing angle 0x8000; try both +z/-z: use P1 matrix r0 to find forward
    place(br, 1, x, 0.0, z - 90.0)
    br.run_frames(2)
    tag = btn.replace("+", "")
    d, lab = record(br, [(btn, 2), ("none", 118)], {"p1": preg(0), "p2": preg(1)},
                    shots_at={4, 12, 24, 40, 70}, shot_prefix=os.path.join(HERE, f"shots/e6/{tag}"))
    OUT[tag + "_p1"] = d["p1"]; OUT[tag + "_p2"] = d["p2"]
    r = snap(br)
    print(btn, "P1", ppos(r, 0), "P2", ppos(r, 1), "hp P+160:", f32(r, P[0]+0x160), f32(r, P[1]+0x160),
          "HEALTH:", f32(r, A.HEALTH[0]), f32(r, A.HEALTH[1]))
np.savez_compressed(os.path.join(HERE, "data_e6.npz"), **OUT)
print("DONE"); sys.stdout.flush(); os._exit(0)
