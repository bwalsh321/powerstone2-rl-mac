"""p05: visual labelling by ablation. Runs <slot> with RandomPad(<seed>) to
frame <F>, then for every category-9 ledger object (and optionally given
extra vts) re-runs the SAME frame with that object's position (+0x2C/+0x30/
+0x34 and matrix translation +0x98/+0x9C/+0xA0) shoved 20000 units down,
and diffs the rendered frame against the untouched one. The diff bbox is
where the object is drawn; crops + a boxed overview are saved.
usage: python p05_ablate.py <slot> <seed> <F> [tag]"""
import struct
import sys
import numpy as np
from common import *

slot, seed, F = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
tag = sys.argv[4] if len(sys.argv) > 4 else f"s{slot}_{seed}_{F}"
br = boot(); load(br, slot)
ram = br.ram
pad = RandomPad(seed)
f = 0
while f < F:
    if f % 16 == 0:
        pad.step(br, 0)
    br.run_frames(2); f += 2
br.clear_inputs()
st = br.emu.get_state()


def frame():
    h, w = br.emu.get_shape()
    arr = np.zeros((h, w, 3), np.uint8)
    br.emu.get_frame(arr, w, h)
    return arr[::-1].copy()


def wf(addr, v):
    struct.pack_into("<f", ram, off(addr), v)


br.emu.set_state(st); br.run_frames(3)
base = frame()
LO = LED_LO - 40 * 0x430
objs = [o for o in ledger(ram, LO, 220)]
import pygame
boxes = []
for k, a, h, vt, x, y, z in objs:
    br.emu.set_state(st)
    y0 = {o: f32(ram, a + o) for o in (0x30, 0x9C)}
    for _ in range(3):
        for o in (0x30, 0x9C):
            wf(a + o, y0[o] + 3000.0)
        br.run_frames(1)
    img = frame()
    d = np.abs(img.astype(int) - base.astype(int)).sum(2) > 40
    if d.sum() < 4:
        print(f"idx={k-40:3d} vt={vt:#010x} hdr={h:#010x} pos=({x:.0f},{y:.0f},{z:.0f})  not visible")
        continue
    ys, xs = np.nonzero(d)
    bb = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
    print(f"idx={k-40:3d} vt={vt:#010x} hdr={h:#010x} pos=({x:.0f},{y:.0f},{z:.0f})  bbox={bb} px={int(d.sum())}")
    boxes.append((k - 40, vt, bb))
    x0, y0, x1, y1 = bb
    crop = base[max(0, y0-8):y1+8, max(0, x0-8):x1+8]
    if crop.size:
        s = pygame.surfarray.make_surface(np.ascontiguousarray(crop.swapaxes(0, 1)))
        pygame.image.save(s, f"{HERE}/shots/abl_{tag}_idx{k-40}_{vt:08x}.png")
ov = base.copy()
for idx, vt, (x0, y0, x1, y1) in boxes:
    ov[y0, x0:x1+1] = (255, 0, 255); ov[y1, x0:x1+1] = (255, 0, 255)
    ov[y0:y1+1, x0] = (255, 0, 255); ov[y0:y1+1, x1] = (255, 0, 255)
s = pygame.surfarray.make_surface(np.ascontiguousarray(ov.swapaxes(0, 1)))
pygame.image.save(s, f"{HERE}/shots/abl_{tag}_overview.png")
for p in range(4):
    print(f"P{p+1} xyz={tuple(round(v) for v in player_xyz(ram,p))} held={held_item(ram,p):#x}")
br.emu.close()
