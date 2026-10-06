"""p10: chest lifecycle tracer. Every 2 frames, for every category-9 record,
logs changes of the id block (+0x420..+0x42F as 4 u32), vt, hdr and y.
Chests (vt 0x0C0CC7A8) are followed from birth; when a chest leaves, the
next new category-9 object within 200 f and 150 xz units is reported as its
yield, and compared with the chest's content byte (+0x42C) history.
usage: python p10_chest_life.py <slot> <frames> <seed> [verbose]"""
import math
import sys
from common import *

slot, N, seed = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
V = len(sys.argv) > 4
br = boot(); load(br, slot)
ram = br.ram
pad = RandomPad(seed)
LO = LED_LO - 40 * 0x430
NS = 220
state = {}          # k -> tuple
chest_hist = {}     # k -> list of (f, content, sub)
pending = []        # (f_end, k, x, z, hist)
results = []


def snap(k):
    a = LO + k * 0x430
    return (u32(ram, a + 8), u32(ram, a + 4) & 0xFFFF, u8(ram, a + 0x420), u8(ram, a + 0x421),
            u8(ram, a + 0x428), u8(ram, a + 0x42C), round(f32(ram, a + 0x2C)), round(f32(ram, a + 0x30)), round(f32(ram, a + 0x34)))


f = 0
while f < N:
    if f % 16 == 0:
        pad.step(br, 0)
    br.run_frames(2); f += 2
    hdr = words(ram, LO, 0x430, NS, 4); vt = words(ram, LO, 0x430, NS, 8)
    for k in range(NS):
        v = int(vt[k]); h = int(hdr[k]) & 0xFF
        live9 = h == 9 and 0x0C000000 <= v < 0x0C200000
        old = state.get(k)
        if not live9:
            if old is not None:
                if V: print(f"f={f:6d} idx={k-40:3d} END   {old[0]:#x}")
                if old[0] == 0x0C0CC7A8:
                    pending.append((f, k, old[6], old[8], chest_hist.pop(k, [])))
                state.pop(k)
            continue
        s = snap(k)
        if old is None or old[0] != s[0]:
            if old is not None and old[0] == 0x0C0CC7A8:
                pending.append((f, k, old[6], old[8], chest_hist.pop(k, [])))
            # newborn: does it satisfy a pending chest?
            for pnd in list(pending):
                if f - pnd[0] <= 200 and math.hypot(s[6] - pnd[2], s[8] - pnd[3]) < 150 and s[0] != 0x0C0CC7A8:
                    hist = pnd[4]
                    contents = sorted(set(c for _, c, _ in hist if c))
                    good = s[2] in contents
                    results.append(good)
                    print(f"YIELD f={f} chest(idx={pnd[1]-40},{pnd[2]},{pnd[3]}) contents_seen={[hex(c) for c in contents]} -> vt={s[0]:#x} id={s[2]:#04x} after {f-pnd[0]}f  {'MATCH' if good else 'MISMATCH'}")
                    pending.remove(pnd)
                    break
            if s[0] == 0x0C0CC7A8:
                chest_hist[k] = []
            if V: print(f"f={f:6d} idx={k-40:3d} NEW   {s}")
        elif V and old[1:6] != s[1:6]:
            print(f"f={f:6d} idx={k-40:3d} chg   {old[1:6]} -> {s[1:6]}  pos={s[6:]}")
        if s[0] == 0x0C0CC7A8:
            hst = chest_hist.setdefault(k, [])
            if not hst or hst[-1][1:] != (s[5], s[3]):
                hst.append((f, s[5], s[3]))
        state[k] = s
    for pnd in list(pending):
        if f - pnd[0] > 200:
            hist = pnd[4]
            print(f"NOYIELD f_end={pnd[0]} chest(idx={pnd[1]-40},{pnd[2]},{pnd[3]}) hist(f,content,+421)={[(a, hex(b), hex(c)) for a, b, c in hist]}")
            pending.remove(pnd)
print(f"MATCH={sum(results)} MISMATCH={len(results)-sum(results)}")
br.emu.close()
