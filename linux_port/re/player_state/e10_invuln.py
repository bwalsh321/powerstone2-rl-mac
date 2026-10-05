"""E10: does P+0x12C (lo u16 == 0) make a player unhittable?  Throw P2 (grab b + x), wait until
P2 is in getting-up state 15 (12C lo == 0), teleport P2 in front of P1 and punch.
Run A: untouched.  Run B: force P2's P+0x12C = 0xFFFFFFFF every frame.  Run C: control - P2 idle,
force P+0x12C = 0xFFFF0000 every frame and punch."""
from harness import *
from flycast_bridge import DC_TO_RETRO
br = boot()
def setm(port, mask):
    m = np.zeros(16, np.uint8)
    for bit, rid in DC_TO_RETRO.items():
        if mask & bit: m[rid] = 1
    br.emu.set_button_mask(m, port)
def u(a): return struct.unpack_from("<I", br.ram, off(a))[0]
for run in "ABC":
    load(br, os.path.join(HERE, "base_s1.state"))
    r = snap(br); x, y, z = ppos(r, 0)
    place(br, 1, x, 0, z - 90); br.run_frames(2)
    if run in "AB":
        seq = [BTN["b"]]*2 + [0]*38 + [BTN["x"]]*2
        for m in seq: setm(0, m); br.emu.run()
        setm(0, 0)
        for t in range(400):
            br.emu.run()
            if br.ram[off(P[1] + 0x3715)] == 15: break
        print(run, "P2 reached state", br.ram[off(P[1] + 0x3715)], "after", t, "12C=%08x" % u(P[1] + 0x12C))
    r = snap(br); x, y, z = ppos(r, 0)
    place(br, 1, x, 0, z - 90)
    hp0 = f32(snap(br), P[1] + 0x160)
    for t in range(30):
        if run in "B": struct.pack_into("<I", br.ram, off(P[1] + 0x12C), 0xFFFFFFFF)
        if run in "C": struct.pack_into("<I", br.ram, off(P[1] + 0x12C), 0xFFFF0000)
        setm(0, BTN["x"] if t < 2 else 0); br.emu.run()
    r = snap(br)
    print(run, "P2 hp before punch %.1f after %.1f  state=%d" % (hp0, f32(r, P[1] + 0x160), r[off(P[1] + 0x3715)]))
print("DONE"); sys.stdout.flush(); os._exit(0)
