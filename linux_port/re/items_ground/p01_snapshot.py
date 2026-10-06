"""p01: one-shot snapshot of ledger (wide window) + pool classes per slot.
usage: python re/items_ground/p01_snapshot.py <slot> [frames]"""
import collections
import sys
from common import *

slot = int(sys.argv[1]); fr = int(sys.argv[2]) if len(sys.argv) > 2 else 0
br = boot(); load(br, slot); br.run_frames(fr)
ram = br.ram
# wide ledger window: 40 slots before LO .. 200 total
lo = LED_LO - 40 * 0x430
L = ledger(ram, lo, 220)
print(f"slot{slot} +{fr}f  wide-ledger live={len(L)} (grid idx relative to OBJ_GRID_LO)")
for k, a, h, vt, x, y, z in L:
    print(f"  idx={k-40:4d} {a:#010x} hdr={h:#010x} vt={vt:#010x}  pos=({x:9.2f},{y:8.2f},{z:9.2f})")
P = pool(ram)
c = collections.Counter(cl for _, _, cl in P)
print(f"pool live={len(P)}")
for cl, n in sorted(c.items()):
    print(f"  cls={cl:#010x} n={n}")
for p in range(4):
    print(f"P{p+1} xyz={tuple(round(v,1) for v in player_xyz(ram,p))} item={held_item(ram,p):#010x}")
shot(br, f"{HERE}/shots/p01_slot{slot}_{fr}.png")
br.emu.close()
