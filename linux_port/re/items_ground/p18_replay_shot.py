"""p18: replay a p04/p10-style run (RandomPad(seed), step every 16 f, 2-frame
ticks) and save labelled screenshots at given frames: every live category-9
object is ablated (lifted) to find its bbox and boxed with its type id/state.
usage: python p18_replay_shot.py <slot> <seed> <f1,f2,...>"""
import struct
import sys

import numpy as np
from PIL import Image, ImageDraw
from common import *

slot, seed = int(sys.argv[1]), int(sys.argv[2])
AT = sorted(int(x) for x in sys.argv[3].split(","))
br = boot(); load(br, slot)
ram = br.ram
pad = RandomPad(seed)
LO = LED_LO - 40 * 0x430


def frame():
    h, w = br.emu.get_shape()
    arr = np.zeros((h, w, 3), np.uint8)
    br.emu.get_frame(arr, w, h)
    return arr[::-1].copy()


def wf(addr, v):
    struct.pack_into("<f", ram, off(addr), v)


f = 0
while f < AT[-1]:
    if f % 16 == 0:
        pad.step(br, 0)
    br.run_frames(2); f += 2
    if f in AT:
        st0 = br.emu.get_state()
        br.run_frames(1); base = frame()
        im = Image.fromarray(base.copy()); dr = ImageDraw.Draw(im)
        for k, a, h, vt, x, y, z in ledger(ram, LO, 220):
            tid = u8(ram, a + 0x420); s = u8(ram, a + 0x421)
            br.emu.set_state(st0)
            yy = {o: f32(ram, a + o) for o in (0x30, 0x9C)}
            for o in (0x30, 0x9C):
                wf(a + o, yy[o] + 3000.0)
            br.run_frames(1)
            d = np.abs(frame().astype(int) - base.astype(int)).sum(2) > 40
            bb = None
            if d.sum() >= 30:
                ys, xs = np.nonzero(d)
                bb = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
                dr.rectangle(bb, outline=(255, 0, 255))
                dr.text((bb[0] + 2, bb[1] + 2), f"{tid:02x}/{s}", fill=(255, 255, 0))
            print(f"SHOT f={f} idx={k-40} vt={vt:#010x} hdr={h:#010x} id={tid:#04x} st={s} pos=({x:.0f},{y:.0f},{z:.0f}) bbox={bb}")
        for p in range(4):
            print(f"SHOT f={f} P{p+1} xyz={tuple(round(v) for v in player_xyz(ram, p))} held={held_item(ram, p):#x}")
        br.emu.set_state(st0)
        im.save(f"{HERE}/shots/replay_s{slot}_{seed}_f{f}.png")
br.emu.close()
