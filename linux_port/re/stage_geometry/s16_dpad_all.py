"""S16: dpad -> world direction on every stage (P2 at its spawn, 'up' and 'right' held 30 f, steady-state velocity).
Also re-checks over time (t=+0 and t=+1500 f) whether the mapping (camera yaw) changes during a match."""
from common import *
br = boot()
ALL = dict(STAGE_STATES); ALL['slot2'] = os.path.join(LP, 'states/slot2.state'); ALL['slot3'] = os.path.join(LP, 'states/slot3.state')
for name, path in ALL.items():
    for wait in (0, 1500):
        load(br, path); br.run_frames(10 + wait)
        snap = br.emu.get_state()
        out = []
        for d in ("up", "right"):
            br.emu.set_state(snap); br.clear_inputs(); setpad(br, d, 1)
            ps = []
            for t in range(30):
                br.run_frames(1); ps.append(logpos(br.ram, 1))
            v = np.array(ps[29]) - np.array(ps[14])
            out.append(f"{d}: angle {np.degrees(np.arctan2(v[2], v[0])):7.1f} speed {np.hypot(v[0], v[2])/15:4.2f}")
        print(f"{name:13s} sid={u32(br.ram,0x8C46E198)} var={u8(br.ram,0x8C54235E)} t+{wait:5}: " + " | ".join(out))
print("DONE")
