"""Can a COM seat be driven by a pad after writing P+0x3720 = 0 (and/or seat table type = 0)?"""
from harness import *
from flycast_bridge import DC_TO_RETRO
br = boot()
for mode in ("none", "flag", "flag+table"):
    load(br, "states/slot2.state"); br.run_frames(400)
    k = 2  # P3 Pete
    for t in range(120):
        if mode != "none": br.ram[off(P[k] + 0x3720)] = 0
        if mode == "flag+table": struct.pack_into("<I", br.ram, off(0x8C472DA8 + 0x14*k), 0)
        m = np.zeros(16, np.uint8); m[DC_TO_RETRO[BTN["a"]]] = 1 if t % 40 < 2 else 0
        br.emu.set_button_mask(m, k)
        br.emu.run()
        if t % 40 == 3: print(mode, t, "P3 state", br.ram[off(P[k] + 0x3715)], "act %x" % u16(snap(br), P[k] + 0x3818))
print("DONE"); sys.stdout.flush(); os._exit(0)
