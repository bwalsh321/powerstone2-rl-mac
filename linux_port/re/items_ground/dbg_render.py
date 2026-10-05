"""dbg: does set_state + run + get_frame reflect state changes?"""
import numpy as np, struct
from common import *
br = boot(); load(br, 2); br.run_frames(900)
st = br.emu.get_state()
def frame():
    h, w = br.emu.get_shape(); arr = np.zeros((h, w, 3), np.uint8); br.emu.get_frame(arr, w, h); return arr
br.run_frames(3); a = frame()
br.emu.set_state(st); br.run_frames(3); b = frame()
br.emu.set_state(st); br.run_frames(30); c = frame()
print("a-b", np.abs(a.astype(int)-b).sum(), "a-c", np.abs(a.astype(int)-c).sum())
L = ledger(br.ram, LED_LO - 40*0x430, 220)
br.emu.set_state(st)
for k, ad, h, vt, x, y, z in L:
    if vt == 0x0C0CC7A8:
        for _ in range(3):
            struct.pack_into("<f", br.ram, off(ad + 0x30), 2000.0); struct.pack_into("<f", br.ram, off(ad + 0x9C), 2000.0)
            br.run_frames(1)
d = frame()
print("a-d", np.abs(a.astype(int)-d).sum())
br.emu.close()
