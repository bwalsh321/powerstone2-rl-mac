"""p04: raw-bytes event recorder for the object ledger (category 9 = pickups).
usage: python p04_events.py <slot> <frames> <seed>
Writes out/ev_s<slot>_<seed>.pkl : dict(events=[...], snaps=[...])
  event = (frame, kind, idx, vt_old, vt_new, bytes_old, bytes_new)
    kind 'chg' on any change of (hdr&0xff, vt) where either side is cat 9
  snaps every 60f: (frame, {idx: bytes}) for all cat-9 records
  held  = (frame, player, old_ptr, new_ptr, gems_old, gems_new, pxyz)
Also the pool (0x8C3E7400, 160*0x90) is snapshotted with each snap."""
import pickle
import sys
from common import *

slot, N, seed = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
br = boot(); load(br, slot)
ram = br.ram
pad = RandomPad(seed)
LO = LED_LO - 40 * 0x430
NS = 220
o0 = off(LO)


def rec(k):
    return bytes(ram[o0 + k * 0x430: o0 + (k + 1) * 0x430])


events, snaps, held = [], [], []
prevkey, prevbytes = {}, {}
ph = [0] * 4; pg = [None] * 4
f = 0
while f < N:
    if f % 16 == 0:
        pad.step(br, 0)
    br.run_frames(2); f += 2
    hdr = words(ram, LO, 0x430, NS, 4); vt = words(ram, LO, 0x430, NS, 8)
    for k in range(NS):
        v = int(vt[k]); h = int(hdr[k]) & 0xFF
        key = (h, v) if 0x0C000000 <= v < 0x0C200000 else None
        old = prevkey.get(k)
        cat9 = (key is not None and key[0] == 9) or (old is not None and old[0] == 9)
        if key != old and cat9:
            events.append((f, 'chg', k - 40, old, key, prevbytes.get(k), rec(k)))
        prevkey[k] = key
        if (key is not None and key[0] == 9) or cat9:
            prevbytes[k] = rec(k)
        else:
            prevbytes.pop(k, None)
    for p in range(4):
        it = held_item(ram, p); g = u8(ram, A.GEMS[p][0])
        if it != ph[p] or g != pg[p]:
            held.append((f, p, ph[p], it, pg[p], g, player_xyz(ram, p)))
            ph[p] = it; pg[p] = g
    if f % 60 == 0:
        d = {}
        for k in range(NS):
            if prevkey.get(k) and prevkey[k][0] == 9:
                d[k - 40] = rec(k)
        pb = bytes(ram[off(A.POOL_BASE): off(A.POOL_BASE) + 160 * 0x90])
        snaps.append((f, d, pb, [player_xyz(ram, p) for p in range(4)]))
pickle.dump(dict(events=events, snaps=snaps, held=held, slot=slot, seed=seed, N=N),
            open(f"{HERE}/out/ev_s{slot}_{seed}.pkl", "wb"))
print(f"events={len(events)} snaps={len(snaps)} held={len(held)}")
br.emu.close()
