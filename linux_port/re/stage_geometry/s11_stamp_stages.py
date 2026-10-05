"""S11: stamp a 2-human (Falcon vs Falcon) savestate for every stage from menu_stage.state (cursor starts r1c0 = Iceberg).
Saves re/stage_geometry/states/<stage>.state once P2 responds to input (match live)."""
import gzip
from common import *
CELLS = {"bluesky": ["up"], "darkcastle": ["up", "right"], "tomb": ["up", "right", "right"],
         "iceberg": [], "spacestation": ["right"], "desert": ["down"], "pharaoh": ["down", "right"],
         "chaos": ["down", "right", "right"]}
only = sys.argv[1:] or list(CELLS)
br = boot()
def tap(b, player=0):
    setpad(br, b, player); br.run_frames(4); setpad(br, "none", player); br.run_frames(16)
for name in only:
    load(br, "menu_stage.state"); br.run_frames(20)
    for m in CELLS[name]: tap(m)
    shot(br, f"shots/s11_{name}_cursor.png")
    tap("a")
    live = None
    for t in range(0, 3000, 60):
        br.run_frames(60)
        p0 = logpos(br.ram, 1)
        setpad(br, "down", 1); br.run_frames(10); setpad(br, "none", 1); br.run_frames(2)
        p1 = logpos(br.ram, 1)
        if np.hypot(p1[0] - p0[0], p1[2] - p0[2]) > 20 and t > 300:
            live = t; break
        if t in (600, 1200): shot(br, f"shots/s11_{name}_t{t}.png")
    br.run_frames(30)
    shot(br, f"shots/s11_{name}_live.png")
    with gzip.open(f"states/{name}.state", "wb") as f:
        f.write(br.emu.get_state())
    r = br.ram
    print(name, "live at", live, "P1", [round(v) for v in logpos(r, 0)], "P2", [round(v) for v in logpos(r, 1)])
print("DONE")
