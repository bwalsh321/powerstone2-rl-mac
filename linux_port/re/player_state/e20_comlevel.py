"""E20: COM level. (a) search COM player structs for a per-seat copy of the level (2 in slot2, 7 in slot3);
(b) causal test: in slot2 (COMs lv3) poke 0x8C472AD4 := 7 (or keep 2) right after load, run 3600 frames with
P2 (human) idle and health refill, and measure COM activity: attack-window count, damage dealt to P2."""
from harness import *
br = boot()
snaps = {}
for s in (2, 3):
    load(br, f"states/slot{s}.state"); br.run_frames(400); snaps[s] = snap(br)
for k in range(4):
    pass
cands = []
for o in range(PSTRIDE):
    v2 = [snaps[2][off(P[k] + o)] for k in range(4)]; v3 = [snaps[3][off(P[k] + o)] for k in range(4)]
    if all(v2[k] == 2 for k in (0, 2, 3)) and all(v3[k] == 7 for k in (0, 2, 3)):
        cands.append((o, v2, v3))
print("per-seat level copies in P struct (COM seats == 2 in slot2, == 7 in slot3):", [(hex(o), a, b) for o, a, b in cands])
cands_g = [a for a in range(0x400000, 0x560000) if snaps[2][a] == 2 and snaps[3][a] == 7]
print("global bytes (0x8C400000-0x8C560000) with 2 in slot2 and 7 in slot3:", [hex(0x8C000000 + a) for a in cands_g][:40])
def run(poke, slot=2, n=3600):
    load(br, f"states/slot{slot}.state")
    if poke is not None:
        br.ram[off(0x8C472AD4)] = poke
    windows = 0; dmg2 = 0.0; prev_live = [False]*4; t_first = None
    for t in range(n):
        br.emu.run()
        r = br.ram
        for k in (0, 2, 3):
            cnt = r[off(P[k] + 0x187)]
            live = cnt > 1
            if live and not prev_live[k]: windows += 1
            prev_live[k] = live
        hp = struct.unpack_from("<f", r, off(P[1] + 0x160))[0]
        if hp < 1000.0:
            dmg2 += 1000.0 - hp
            for ad in (A.HEALTH_OBJ[1], A.HEALTH[1], A.HEALTH[1] + 0x30, A.HEALTH[1] + 0x50): wf32(br, ad, 1000.0)
    return windows, dmg2
for slot in (2, 3):
    for poke in (None, 0, 2, 7):
        w, d = run(poke, slot)
        print(f"slot{slot} poke {poke}: COM attack windows {w}, damage dealt to idle P2 {d:.0f}  (level byte now {br.ram[off(0x8C472AD4)]})")
print("DONE"); sys.stdout.flush(); os._exit(0)
