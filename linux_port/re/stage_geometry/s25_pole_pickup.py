"""S25: can P2 pick up / swing on the desert pole (tall cactus) once in CONTACT? run into the (100,1000) pole 30 f, then
B (action), or A held toward it, or B+up. Report P2 state RLE, pole ledger pos/y afterwards (moved = picked up/thrown)."""
from common import *
br = boot()
load(br, STATES["slot1"]); br.run_frames(10)
place(br, 0, -1100, 0, -400); br.run_frames(2)
snap = br.emu.get_state()
CX, CZ = 100.0, 1000.0
def pole():
    for _, a, vt, p in ledger(br.ram):
        if vt == 0x0C0F18D4 and np.hypot(p[0] - CX, p[2] - CZ) < 1500 and a == 0x8C504B90: return p
for name, steps in {"contact_B": [("up", 30), ("b", 8), ("none", 60)], "contact_upB": [("up", 30), ("up+b", 8), ("none", 60)],
                    "contact_B_hold": [("up", 30), ("b", 40), ("none", 30)], "contact_X": [("up", 30), ("x", 8), ("none", 40)],
                    "contact_A_into": [("up", 30), ("up+a", 8), ("up", 60)]}.items():
    br.emu.set_state(snap); br.clear_inputs()
    place(br, 1, CX + 140 / 1.4142, 0, CZ + 140 / 1.4142); br.run_frames(2)
    sts = []
    for b, n in steps:
        setpad(br, b, 1)
        for _ in range(n):
            br.run_frames(1); sts.append(pstate(br.ram, 1))
    rle = [sts[0]] + [s for i, s in enumerate(sts[1:], 1) if s != sts[i - 1]]
    pp = pole()
    print(f"{name:15s} P2 states {rle}  pole now {None if pp is None else [round(v) for v in pp]}  P2 {[round(v) for v in logpos(br.ram, 1)]}")
    shot(br, f"shots/s25_{name}.png")
print("DONE")
