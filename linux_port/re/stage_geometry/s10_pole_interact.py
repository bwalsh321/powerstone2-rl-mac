"""S10: pole interaction. P2 placed 120 u from the (100,1000) pole on the +x+z diagonal (dpad 'up' runs toward -x-z = into it).
Scenarios: run into pole; run + B; run + A (jump into pole); stand adjacent + B; stand + A.
Log state byte / pos per frame and screenshot mid-way."""
from common import *
br = boot()
load(br, STATES["slot1"]); br.run_frames(20)
place(br, 0, -1100, 0, -400); br.run_frames(2)
snap = br.emu.get_state()
CX, CZ = 100.0, 1000.0
scen = {
  "run_into": [("up", 60)],
  "run_B": [("up", 12), ("up+b", 6), ("up", 60)],
  "run_A": [("up", 8), ("up+a", 6), ("up", 60)],
  "adj_B": [("none", 2), ("b", 6), ("none", 60)],
  "adj_A": [("none", 2), ("a", 6), ("up", 60)],
  "adj_upA_hold": [("up", 4), ("up+a", 30), ("up", 40)],
}
for name, steps in scen.items():
    br.emu.set_state(snap); br.clear_inputs()
    d0 = 85 if name.startswith("adj") else 140
    place(br, 1, CX + d0 / 1.4142, 0, CZ + d0 / 1.4142); br.run_frames(2)
    log = []; t = 0
    for b, n in steps:
        setpad(br, b, 1)
        for _ in range(n):
            br.run_frames(1); t += 1
            p = logpos(br.ram, 1)
            log.append((t, b, pstate(br.ram, 1), round(np.hypot(p[0] - CX, p[2] - CZ), 1), round(p[1], 1)))
            if t == 30: shot(br, f"shots/s10_{name}.png")
    setpad(br, "none", 1)
    # RLE of state
    print("==", name)
    prev = None
    for t, b, st, d, y in log:
        if st != prev or t % 10 == 0:
            print(f"   t={t:3} btn={b:8} st={st:3} dist={d:6.1f} y={y:6.1f}")
        prev = st
print("DONE")
