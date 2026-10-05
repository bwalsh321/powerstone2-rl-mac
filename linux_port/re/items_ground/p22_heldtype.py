"""p22: live check of ground_scan.held_type against the record behind F+0x54
(state must be 5/7 and the type a pickable id). usage: p22_heldtype.py slot frames seed"""
import collections, sys
from common import *
from ps2_ram import PS2Ram
import ground_scan as G
slot, N, seed = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
br = boot(); load(br, slot); r = PS2Ram(br.ram); pad = RandomPad(seed)
c = collections.Counter(); bad = 0; f = 0
while f < N:
    if f % 16 == 0: pad.step(br, 0)
    br.run_frames(2); f += 2
    for p in range(4):
        t = G.held_type(r, p)
        if t:
            ptr = held_item(br.ram, p); st = u8(br.ram, (ptr | 0x80000000) - 4 + 0x421)
            c[(t, st)] += 1
            if st not in (5, 7): bad += 1
print("held (type, state) counts:", {f"{t:#x}/{s}": n for (t, s), n in sorted(c.items())})
print("samples with state not 5/7:", bad)
br.emu.close()
