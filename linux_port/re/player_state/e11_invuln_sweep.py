"""E11: hittability sweep across the getting-up window. After a throw, wait D frames past P2's
entry into state 15, teleport P2 90u in front of P1, press punch; log P2 state and P+0x12C during
the punch's active frames (P1 P+0x124 hi byte != 0) and whether P2 lost health."""
from harness import *
from flycast_bridge import DC_TO_RETRO
br = boot()
def setm(port, mask):
    m = np.zeros(16, np.uint8)
    for bit, rid in DC_TO_RETRO.items():
        if mask & bit: m[rid] = 1
    br.emu.set_button_mask(m, port)
def u(a): return struct.unpack_from("<I", br.ram, off(a))[0]
for D in [0, 10, 18, 22, 24, 26, 28, 30, 34, 40, 60, 90]:
    load(br, os.path.join(HERE, "base_s1.state"))
    r = snap(br); x, y, z = ppos(r, 0); place(br, 1, x, 0, z - 90); br.run_frames(2)
    for m in [BTN["b"]]*2 + [0]*38 + [BTN["x"]]*2: setm(0, m); br.emu.run()
    setm(0, 0)
    for t in range(400):
        br.emu.run()
        if br.ram[off(P[1] + 0x3715)] == 15: break
    br.run_frames(D - 8 if D >= 8 else 0)
    r = snap(br); x, y, z = ppos(r, 0); place(br, 1, x, 0, z - 90)
    hp0 = f32(snap(br), P[1] + 0x160); log = []
    for t in range(20):
        setm(0, BTN["x"] if t < 2 else 0); br.emu.run()
        if (u(P[0] + 0x124) & 0xFF00):
            log.append("s%d/%04x" % (br.ram[off(P[1] + 0x3715)], u(P[1] + 0x12C) & 0xFFFF))
    hp1 = f32(snap(br), P[1] + 0x160)
    print(f"D={D:3d} (punch active ~D) P2 during active frames: {' '.join(log)}  dmg={hp0-hp1:.1f}")
print("DONE"); sys.stdout.flush(); os._exit(0)
