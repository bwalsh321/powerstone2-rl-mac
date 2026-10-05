"""p19: end-to-end validation of ground_scan.py on live play.
 (a) scan_ground() through the production PS2Ram class;
 (b) grid scan vs the arena's own category-9 linked list (head at
     ARENA_HEADS + 4*9, next at record+0x10) must give the same set;
 (c) production StateLineSynth._obj_scan 'fall' count vs what it really
     counts (vt 0x0C0C9810 items incl. HELD ones) and chests/stones it misses
     beyond OBJ_GRID_N;
 (d) per-call cost of scan_ground.
usage: python p19_validate.py <slot> <frames> <seed>"""
import collections
import sys
import time

from common import *
from ps2_ram import PS2Ram, StateLineSynth
import ground_scan as G

slot, N, seed = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
br = boot(); load(br, slot)
ram = br.ram
r = PS2Ram(ram)
synth = StateLineSynth(ram, bot_player=2)
pad = RandomPad(seed)


def list_walk(cat):
    out = set(); p = u32(ram, G.ARENA_HEADS + 4 * cat); n = 0
    while p and n < 400:
        a = (p - 4) | 0x80000000
        out.add(a); p = u32(ram, a + 0x10); n += 1
    return out


mism = 0; checks = 0; t_tot = 0.0; ncall = 0
fall_breakdown = collections.Counter(); missed = collections.Counter()
f = 0
while f < N:
    if f % 16 == 0:
        pad.step(br, 0)
    br.run_frames(2); f += 2
    if f % 30:
        continue
    t0 = time.perf_counter()
    objs = G.scan_ground(r, include_held=True, include_fixed=True)
    t_tot += time.perf_counter() - t0; ncall += 1
    grid = set(o.addr for o in objs)
    # list may hold category-9 records of vts outside the pickup whitelist
    lst = set(a for a in list_walk(9) if 0x0C000000 <= u32(ram, a + 8) < 0x0C200000 and u32(ram, a + 8) not in (G.VT_HELPER, G.VT_WEARABLE)
              and not (f32(ram, a + 0x2C) == 0.0 and f32(ram, a + 0x30) == 0.0 and f32(ram, a + 0x34) == 0.0))
    checks += 1
    if grid != lst:
        mism += 1
        if mism <= 5:
            print(f"f={f} MISMATCH grid-only={[hex(a) for a in grid-lst]} list-only={[hex(a) for a in lst-grid]}")
    stones, chests, fall = synth._obj_scan()
    for o in objs:
        if o.vt == G.VT_ITEM:
            fall_breakdown["held" if o.state in (5, 7) else f"state{o.state}"] += 1
        if o.vt in (G.VT_CHEST, G.VT_STONE) and not (0 <= o.idx < 110):
            missed[hex(o.vt)] += 1
    n_items = sum(1 for o in objs if o.vt == G.VT_ITEM and 0 <= o.idx < 110)
    assert fall == n_items, (fall, n_items)
    if f % 1800 == 0:
        free = [o for o in objs if o.state not in (5, 7)]
        print(f"f={f} objs={len(objs)} free={len(free)} legacy(stones={len(stones)},chests={len(chests)},fall={fall}) "
              + " ".join(f"{o.tid:02x}/{o.state}@({o.x:.0f},{o.z:.0f})" for o in free if o.vt not in (G.VT_CACTUS, G.VT_SAGUARO)), flush=True)
print(f"grid-vs-list checks={checks} mismatches={mism}")
print(f"legacy 'fall' (CHEST_FALL_VT) actually counted vt 0x0C0C9810 items by state: {dict(fall_breakdown)}")
print(f"chest/stone sightings the legacy OBJ_GRID_N=110 window misses: {dict(missed)}")
print(f"scan_ground mean cost {1e6*t_tot/max(ncall,1):.0f} us/call over {ncall} calls")
br.emu.close()
