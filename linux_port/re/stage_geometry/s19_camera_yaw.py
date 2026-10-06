"""S19: on every stage, compare the dpad-'up' world angle (s16) with the camera back-vector at 0x8C541194 and the eye at
0x8C5411A4 -> is 'up' == -(camera back) projected on xz?  (if yes the env can derive the action frame live from RAM)."""
from common import *
UP = {"desert": -135.0, "bluesky": -90.0, "darkcastle": -135.0, "tomb": -123.3, "iceberg": -128.5,
      "spacestation": -144.1, "pharaoh": -135.0, "chaos": 180.0}
br = boot()
for name, path in STAGE_STATES.items():
    if name not in UP: continue
    load(br, path); br.run_frames(30)
    r = br.ram
    b = [f32(r, 0x8C541194 + 4 * k) for k in range(3)]
    e = [f32(r, 0x8C5411A4 + 4 * k) for k in range(3)]
    ang = np.degrees(np.arctan2(-b[2], -b[0]))
    m = (np.array(logpos(r, 0)) + np.array(logpos(r, 1))) / 2
    print(f"{name:13s} back=({b[0]:+.3f},{b[1]:+.3f},{b[2]:+.3f}) -> up angle {ang:7.1f}  (dpad-measured {UP[name]:7.1f})  eye=({e[0]:.0f},{e[1]:.0f},{e[2]:.0f}) mid=({m[0]:.0f},{m[2]:.0f})")
print("DONE")
