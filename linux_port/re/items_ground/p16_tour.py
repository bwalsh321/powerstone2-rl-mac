"""p16: stage tour = p13 replay (same seed / CHEST_FORCE => same trajectory)
but with CAP=0 (no ablations) and, at frames in env SNAP_AT, a labelled
overview: every category-9 object ablated and boxed with its type id, plus a
full census line. Original p13 doc follows.
p13: item gallery. Plays <slot> with RandomPad(<seed>); every 60 frames it
checkpoints, and for each category-9 object whose type id (+0x420) has not
been captured yet (or captured < 2 times) and is NOT held (+0x421 != 5/7),
ablates it (lift +3000 for 3 frames) to find its on-screen bbox, saves a crop
named by id, then restores the checkpoint so play continues untouched.
usage: python p13_gallery.py <slot> <frames> <seed> [cap_per_id]
Optional env CHEST_FORCE=<hexid,...>: every newly born chest gets its content
byte (+0x42C) overwritten with the next id from the list (to make the game
spawn specific items for labelling)."""
import collections
import os
import struct
import sys

import numpy as np
from common import *

slot, N, seed = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
CAP = int(sys.argv[4]) if len(sys.argv) > 4 else 2
FORCE = [int(x, 16) for x in os.environ.get("CHEST_FORCE", "").split(",") if x]
br = boot(); load(br, slot)
ram = br.ram
pad = RandomPad(seed)
LO = LED_LO - 40 * 0x430
import pygame
pygame.init()
got = collections.Counter()
os.makedirs(f"{HERE}/gallery", exist_ok=True)
log = open(f"{HERE}/gallery/index_s{slot}_{seed}.txt", "a")
seen_chests = set()


def frame():
    h, w = br.emu.get_shape()
    arr = np.zeros((h, w, 3), np.uint8)
    br.emu.get_frame(arr, w, h)
    return arr[::-1].copy()


def wf(addr, v):
    struct.pack_into("<f", ram, off(addr), v)


def save(arr, path):
    s = pygame.surfarray.make_surface(np.ascontiguousarray(arr.swapaxes(0, 1)))
    pygame.image.save(s, path)


SNAP_AT = set(int(x) for x in os.environ.get("SNAP_AT", "").split(",") if x)
from PIL import Image, ImageDraw


def overview(f):
    st0 = br.emu.get_state()
    br.run_frames(3); base = frame()
    objs = ledger(ram, LO, 220)
    im = Image.fromarray(base); dr = ImageDraw.Draw(im)
    for k, a, h, vt, x, y, z in objs:
        tid = u8(ram, a + 0x420); st = u8(ram, a + 0x421)
        br.emu.set_state(st0)
        yy = {o: f32(ram, a + o) for o in (0x30, 0x9C)}
        for _ in range(3):
            for o in (0x30, 0x9C):
                wf(a + o, yy[o] + 3000.0)
            br.run_frames(1)
        d = np.abs(frame().astype(int) - base.astype(int)).sum(2) > 40
        vis = ""
        if 30 <= d.sum():
            ys, xs = np.nonzero(d)
            bb = (int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max()))
            if bb[2]-bb[0] < 400:
                dr.rectangle(bb, outline=(255, 0, 255)); dr.text((bb[0]+2, bb[1]+2), f"{tid:02x}", fill=(255, 255, 0))
                vis = f"bbox={bb}"
        print(f"TOUR f={f} idx={k-40} vt={vt:#010x} hdr={h:#010x} id={tid:#04x} st={st:#x} pos=({x:.0f},{y:.0f},{z:.0f}) {vis}", flush=True)
    br.emu.set_state(st0)
    im.save(f"{HERE}/shots/tour_f{f}.png")


f = 0
fi = 0
while f < N:
    if f % 16 == 0:
        pad.step(br, 0)
    br.run_frames(2); f += 2
    if FORCE:
        for k, a, h, vt, x, y, z in ledger(ram, LO, 220):
            if vt == 0x0C0CC7A8 and a not in seen_chests and u8(ram, a + 0x421) == 2:
                seen_chests.add(a)
                ram[off(a + 0x42C)] = FORCE[fi % len(FORCE)]
                print(f"f={f} forced chest {a:#x} content -> {FORCE[fi % len(FORCE)]:#x}")
                fi += 1
            if vt != 0x0C0CC7A8:
                seen_chests.discard(a)
    if f in SNAP_AT:
        overview(f)
    if f % 60:
        continue
    todo = []
    for k, a, h, vt, x, y, z in ledger(ram, LO, 220):
        tid = u8(ram, a + 0x420); st = u8(ram, a + 0x421)
        if st in (5, 7) or got[(vt, tid)] >= CAP:
            continue
        todo.append((k, a, vt, tid, st, x, y, z))
    if not todo:
        continue
    held_inputs = {p: m.copy() for p, m in br._held.items()} if hasattr(br, "_held") else {}
    st0 = br.emu.get_state()
    br.run_frames(3); base = frame()
    for k, a, vt, tid, st, x, y, z in todo:
        br.emu.set_state(st0)
        y0 = {o: f32(ram, a + o) for o in (0x30, 0x9C)}
        for _ in range(3):
            for o in (0x30, 0x9C):
                wf(a + o, y0[o] + 3000.0)
            br.run_frames(1)
        d = np.abs(frame().astype(int) - base.astype(int)).sum(2) > 40
        if d.sum() < 30:
            continue
        ys, xs = np.nonzero(d)
        x0, y0b, x1, y1 = int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())
        if (x1 - x0) > 300 or (y1 - y0b) > 300:
            continue   # camera/HUD side effect, not a clean object diff
        got[(vt, tid)] += 1
        crop = base[max(0, y0b-10):y1+10, max(0, x0-10):x1+10]
        # upscale x3 for readability
        crop = crop.repeat(3, 0).repeat(3, 1)
        p = f"{HERE}/gallery/id{tid:02x}_vt{vt:08x}_s{slot}_{seed}_f{f}.png"
        try:
            save(crop, p)
        except Exception as e:
            print('save failed', e, crop.shape); continue
        log.write(f"id={tid:#04x} vt={vt:#010x} st={st:#x} f={f} pos=({x:.0f},{y:.0f},{z:.0f}) bbox=({x0},{y0b},{x1},{y1}) -> {os.path.basename(p)}\n")
        log.flush()
        print(f"f={f} captured id={tid:#04x} vt={vt:#x}", flush=True)
    br.emu.set_state(st0)
print("captured:", {f"{v:#x}/{t:#x}": n for (v, t), n in sorted(got.items())})
br.emu.close()
