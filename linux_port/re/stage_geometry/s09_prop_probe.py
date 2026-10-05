"""S09: clean per-probe snapshot (set_state each probe) around one pole and one cactus cluster.
(a) ground probe: place at y=0, run 20 f -> pushout radius.  (b) drop probe: place at y=400, run 70 f -> landing y (standable top?).
(c) edit pole collision radius (+0x19C) 15 -> 100 and re-measure pushout along +x."""
from common import *
br = boot()
load(br, STATES["slot1"]); br.run_frames(20)
place(br, 0, -1100, 0, -400); br.run_frames(2)
snap = br.emu.get_state()
def probe(x, y, z, F):
    br.emu.set_state(snap); br.clear_inputs()
    place(br, 1, x, y, z); br.run_frames(F)
    return logpos(br.ram, 1), pstate(br.ram, 1)
for name, (cx, cz) in {"pole_100_1000": (100, 1000), "cluster_m500_1000": (-500, 1000)}.items():
    print("==", name)
    for r in range(0, 160, 10):
        p, st = probe(cx + r + 0.5, 0, cz + 0.3, 20)
        q, st2 = probe(cx + r + 0.5, 400, cz + 0.3, 70)
        print(f"  ground start dx={r:4} -> dist {np.hypot(p[0]-cx, p[2]-cz):7.1f} y={p[1]:6.1f} st={st:3}   | drop -> y={q[1]:6.1f} dist {np.hypot(q[0]-cx, q[2]-cz):7.1f} st={st2}")
# (c) radius edit
POLE = 0x8C504B90   # ledger slot of the (100,0,1000) pole in slot1 (#34)
print("pole rec +0x190:", [round(f32(br.ram, POLE + 0x190 + 4*k), 1) for k in range(5)])
for newr in (15.0, 100.0):
    br.emu.set_state(snap); br.clear_inputs()
    wf32(br, POLE + 0x19C, newr)
    place(br, 1, 100 + 20.5, 0, 1000.3); br.run_frames(20)
    p = logpos(br.ram, 1)
    print(f"  radius field={newr}: start dx=20 -> dist {np.hypot(p[0]-100, p[2]-1000):.1f}")
print("DONE")
