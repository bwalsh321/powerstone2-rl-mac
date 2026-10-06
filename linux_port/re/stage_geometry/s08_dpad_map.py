"""S08: dpad -> world direction for P2 at several stage positions (desert slot1). Hold each dir 40 f, measure displacement
over frames 20-40 (steady run). Also measure run speed. Camera yaw dependency = does the mapping change with position?"""
from common import *
br = boot()
load(br, STATES["slot1"]); br.run_frames(20)
place(br, 0, -1100, 0, 1100); br.run_frames(2)
snap = br.emu.get_state()
for (x0, z0) in [(0, 0), (800, 800), (-800, -800), (800, -800), (-500, 500)]:
    for d in ("up", "down", "left", "right", "up+right"):
        br.emu.set_state(snap); br.clear_inputs()
        place(br, 1, x0, 0, z0); br.run_frames(3)
        setpad(br, d, 1)
        ps = []
        for t in range(40):
            br.run_frames(1); ps.append(logpos(br.ram, 1))
        setpad(br, "none", 1)
        ps = np.array(ps)
        v = (ps[39] - ps[19]) / 20
        ang = np.degrees(np.arctan2(v[2], v[0]))
        print(f"at ({x0:5},{z0:5}) {d:9s} v/frame=({v[0]:6.2f},{v[2]:6.2f}) speed={np.hypot(v[0],v[2]):5.2f} angle(atan2 z,x)={ang:7.1f}")
print("DONE")
