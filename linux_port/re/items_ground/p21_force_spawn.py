"""p21: forced chest contents -> what spawns (vt class per item id), no
screenshots. Each newly born chest gets +0x42C = next id from CHEST_FORCE;
when its content clears, the NEW category-9 object born within 4 f and 60
units of the chest is reported (vt, type id).
usage: CHEST_FORCE=59,5a,... python p21_force_spawn.py <slot> <frames> <seed>"""
import math
import os
import sys

from common import *

slot, N, seed = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
FORCE = [int(x, 16) for x in os.environ.get("CHEST_FORCE", "").split(",") if x]
br = boot(); load(br, slot)
ram = br.ram
pad = RandomPad(seed)
LO = LED_LO - 40 * 0x430
seen, fi = set(), 0
prev = {}
opening = {}     # addr -> (content, x, z, f)
f = 0
while f < N:
    if f % 16 == 0:
        pad.step(br, 0)
    br.run_frames(2); f += 2
    L = ledger(ram, LO, 220)
    cur = {}
    for k, a, h, vt, x, y, z in L:
        cur[a] = vt
        if vt == 0x0C0CC7A8:
            c = u8(ram, a + 0x42C)
            if a not in seen and u8(ram, a + 0x421) == 2:
                seen.add(a); ram[off(a + 0x42C)] = FORCE[fi % len(FORCE)]; fi += 1
            if c:
                opening[a] = (c, x, z, f)
            elif a in opening and opening[a][3] == f - 2:
                print(f"f={f} chest {a:#x} content {opening[a][0]:#04x} cleared (state {u8(ram, a + 0x421)})", flush=True)
    for k, a, h, vt, x, y, z in L:
        if prev.get(a) != vt and vt != 0x0C0CC7A8:
            print(f"f={f}   new vt={vt:#010x} id={u8(ram, a + 0x420):#04x} at ({x:.0f},{y:.0f},{z:.0f})", flush=True)
            for ca, (c, cx, cz, cf) in list(opening.items()):
                if math.hypot(x - cx, z - cz) < 60 and f - cf <= 4 and u8(ram, ca + 0x42C) == 0:
                    print(f"f={f} chest content {c:#04x} -> spawned vt={vt:#010x} id={u8(ram, a + 0x420):#04x} st={u8(ram, a + 0x421)}", flush=True)
                    opening.pop(ca)
    for a in list(seen):
        if cur.get(a) != 0x0C0CC7A8:
            seen.discard(a); opening.pop(a, None)
    prev = cur
br.emu.close()
