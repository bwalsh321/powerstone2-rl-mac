"""p20: thrown objects as projectiles. Tracks every category-9 record each
2 frames; for each continuous run of a state (per record), reports duration,
mean/max speed (u/s, world pos) and the holder byte. Answers: is state 6
(items) / 8,10 (stage props) 'in flight after a throw', and how fast?
usage: python p20_thrown.py <slot> <frames> <seed>"""
import collections
import math
import sys

from common import *

slot, N, seed = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
br = boot(); load(br, slot)
ram = br.ram
pad = RandomPad(seed, grab_bias=0.35)
LO = LED_LO - 40 * 0x430
runs = {}      # addr -> [state, tid, f0, last_pos, speeds, holder]
agg = collections.defaultdict(list)   # (vtclass, state) -> list of (dur, mean, max)
f = 0
while f < N:
    if f % 16 == 0:
        pad.step(br, 0)
    br.run_frames(2); f += 2
    cur = set()
    for k, a, h, vt, x, y, z in ledger(ram, LO, 220):
        tid = u8(ram, a + 0x420); st = u8(ram, a + 0x421)
        cur.add(a)
        R = runs.get(a)
        if R is None or R[0] != st or R[1] != tid:
            if R is not None:
                sp = R[4]
                agg[(R[1] if R[1] >= 0xC0 else 'item', R[0])].append((f - R[2], sum(sp) / len(sp) if sp else 0, max(sp) if sp else 0))
            runs[a] = [st, tid, f, (x, y, z), [], (h >> 8) & 0xFF]
        else:
            px, py, pz = R[3]
            if st not in (5, 7):
                R[4].append(math.dist((x, y, z), (px, py, pz)) * 30.0)
            R[3] = (x, y, z)
    for a in list(runs):
        if a not in cur:
            runs.pop(a)
print("(type, state): n_runs, median duration f, median mean-speed u/s, median max-speed u/s")
for key, L in sorted(agg.items(), key=str):
    L.sort(key=lambda t: t[0]); d = L[len(L) // 2][0]
    ms = sorted(t[1] for t in L)[len(L) // 2]; mx = sorted(t[2] for t in L)[len(L) // 2]
    print(f"  {str(key):>10}: n={len(L):4d} dur~{d:5d}f  mean~{ms:7.0f}  max~{mx:7.0f}")
br.emu.close()
