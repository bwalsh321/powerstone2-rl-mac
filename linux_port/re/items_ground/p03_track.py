"""p03: per-slot state-change tracker (ignores the hdr==9 filter) correlated
with held-item pointers (F+0x54) and gem counts (F+0x35).
usage: python p03_track.py <slot> <frames> <seed> [shots:0/1]
Every change of (hdr low byte, vt) on any grid slot is logged together with
the record's +0x28, +0x120, node count +0xC4 and the pool classes of its
render nodes (+0xC8.. -> pool record +0x34, class at node-0x34+0x3C).
Held/gem changes are logged with player pos and the nearest slot."""
import sys
from common import *

slot, N, seed = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
SH = int(sys.argv[4]) if len(sys.argv) > 4 else 0
br = boot(); load(br, slot)
ram = br.ram
pad = RandomPad(seed)
LO = LED_LO - 40 * 0x430
NS = 220


def nodes(a):
    n = u32(ram, a + 0xC4)
    out = []
    for i in range(min(n, 8)):
        p = u32(ram, a + 0xC8 + 4 * i)
        if 0x0C000000 <= p < 0x0D000000:
            out.append(u32(ram, p - 0x34 + 0x3C))
    return n, out


def desc(k):
    a = LO + k * 0x430
    vt = u32(ram, a + 8); h = u32(ram, a + 4)
    n, cl = nodes(a)
    return (f"idx={k-40:3d} {a:#x} hdr={h:#010x} vt={vt:#010x} pos=({f32(ram,a+0x2C):.1f},{f32(ram,a+0x30):.1f},{f32(ram,a+0x34):.1f}) "
            f"+28={u32(ram,a+0x28):#x} +120={u32(ram,a+0x120):#x} +18={u32(ram,a+0x18):#010x} +1c={u32(ram,a+0x1C):#010x} nodes={n}:" + ",".join(f"{c:#x}" for c in cl))


prev = {}
ph = [0] * 4; pg = [0] * 4
f = 0
while f < N:
    if f % 16 == 0:
        pad.step(br, 0)
    br.run_frames(2); f += 2
    hdr = words(ram, LO, 0x430, NS, 4); vt = words(ram, LO, 0x430, NS, 8)
    for k in range(NS):
        v = int(vt[k]); h = int(hdr[k]) & 0xFF
        key = (h, v) if 0x0C000000 <= v < 0x0C200000 else None
        if prev.get(k) != key:
            if key is None:
                print(f"f={f:6d} CLR   idx={k-40:3d} was={prev.get(k)}")
            else:
                print(f"f={f:6d} SLOT  {desc(k)}")
            prev[k] = key
    for p in range(4):
        it = held_item(ram, p); g = u8(ram, A.GEMS[p][0])
        if it != ph[p] or g != pg[p]:
            x, y, z = player_xyz(ram, p)
            extra = ""
            if it and it != ph[p]:
                k = (it - 4 - (LO & 0x0FFFFFFF | 0x0C000000)) // 0x430 if False else ((it - 4) - (LO - 0x80000000)) // 0x430
                extra = " -> " + desc(k)
            print(f"f={f:6d} P{p+1} item {ph[p]:#x}->{it:#x} gems {pg[p]}->{g} at ({x:.0f},{y:.0f},{z:.0f}){extra}")
            if SH:
                shot(br, f"{HERE}/shots/p03_s{slot}_{seed}_f{f}_P{p+1}.png")
            ph[p] = it; pg[p] = g
br.emu.close()
