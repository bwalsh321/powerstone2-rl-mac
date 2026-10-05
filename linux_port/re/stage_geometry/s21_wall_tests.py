"""S21: what happens at the desert boundary wall? (random walk showed long airborne spells + state 44 at the wall)
Scenarios from (0,0,-900): hold 'right' (world (+1,-1)/r2 -> hits z=-1140 wall at 45 deg) / hold 'down+left' (world (0,+1)...)
we pick dirs that hit the wall head-on or obliquely, with and without A. Logs state RLE + y."""
from common import *
br = boot()
load(br, STATES["slot1"]); br.run_frames(10)
place(br, 0, 1000, 0, 1000); br.run_frames(2)
snap = br.emu.get_state()
# world dirs: up+right=(0,-1) head-on into z=-1140 wall; right=(1,-1)/r2 oblique
scen = {"headon_hold": [("up+right", 150)], "oblique_hold": [("right", 150)],
        "headon_jump_at_wall": [("up+right", 40), ("up+right+a", 6), ("up+right", 80)],
        "headon_jump_then_neutral": [("up+right", 40), ("up+right+a", 6), ("none", 80)],
        "headon_jump_then_away": [("up+right", 40), ("up+right+a", 6), ("up+right", 14), ("down+left", 60)],
        "pole_slide": [("up", 150)]}
for name, steps in scen.items():
    br.emu.set_state(snap); br.clear_inputs()
    if name == "pole_slide": place(br, 1, -1000 + 160, 0, -1000 + 175)   # slightly off-axis -> slides around the pole
    else: place(br, 1, 0, 0, -900)
    br.run_frames(2)
    log = []
    for b, n in steps:
        setpad(br, b, 1)
        for _ in range(n):
            br.run_frames(1); p = logpos(br.ram, 1); log.append((pstate(br.ram, 1), p))
    seq = []
    for i, (s, p) in enumerate(log):
        if i == 0 or s != log[i - 1][0]: seq.append(f"t{i}:st{s}@({p[0]:.0f},{p[1]:.0f},{p[2]:.0f})")
    print(f"{name:26s} maxy={max(p[1] for s, p in log):6.1f}  " + " ".join(seq[:14]))
print("DONE")
