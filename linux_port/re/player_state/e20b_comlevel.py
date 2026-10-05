"""E20b: poke each global candidate byte (2 in slot2 / 7 in slot3) in slot2 to 7 every frame and measure
COM activity vs idle P2 (3600 frames). A real live difficulty byte should change the numbers."""
from harness import *
br = boot()
C = [0x8c443837, 0x8c445a43, 0x8c44678f, 0x8c446d77, 0x8c446da3, 0x8c448989, 0x8c44898b, 0x8c46335e, 0x8c466e04, 0x8c472ad4, 0x8c5429ad, 0x8c5429c8]
def run(pokes, val, slot=2, n=3600):
    load(br, f"states/slot{slot}.state")
    windows = 0; dmg2 = 0.0; prev = [False]*4
    for t in range(n):
        for a in pokes: br.ram[off(a)] = val
        br.emu.run(); r = br.ram
        for k in (0, 2, 3):
            live = r[off(P[k] + 0x187)] > 1
            if live and not prev[k]: windows += 1
            prev[k] = live
        hp = struct.unpack_from("<f", r, off(P[1] + 0x160))[0]
        if hp < 1000.0:
            dmg2 += 1000.0 - hp
            for ad in (A.HEALTH_OBJ[1], A.HEALTH[1], A.HEALTH[1] + 0x30, A.HEALTH[1] + 0x50): wf32(br, ad, 1000.0)
    return windows, dmg2
print("baseline slot2:", run([], 0))
for a in C:
    print(f"poke {a:#x}=7 every frame:", run([a], 7))
print("poke 0x8c5429ad+0x8c5429c8 = 0:", run([0x8c5429ad, 0x8c5429c8], 0))
print("DONE"); sys.stdout.flush(); os._exit(0)
