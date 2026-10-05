"""Replay a probe3 run deterministically (same state, seed, input scheme) up to
given frames and screenshot, so a hold seen in the logs can be eyeballed.
usage: verify_shots.py <state> <seed> <start_p> <name:frame,name:frame,...>"""
import sys, random
from common import *
slot, seed, START_P = sys.argv[1], int(sys.argv[2]), float(sys.argv[3])
want = {}
for t in sys.argv[4].split(","):
    n, f = t.split(":"); want.setdefault(int(f), []).append(n)
br = boot(); load(br, slot); ram = br.emu.get_ram()
rng = random.Random(seed)
for fr in range(max(want) + 1):
    if fr % 15 == 0:
        for p in (0, 1):
            m = rng.choice([0, BTN["left"], BTN["right"], BTN["up"], BTN["down"],
                            BTN["a"], BTN["b"], BTN["y"], BTN["x"], BTN["a"], BTN["b"], BTN["x"],
                            BTN["up"] | BTN["right"], BTN["down"] | BTN["left"], BTN["start"] if (START_P and rng.random() < START_P) else 0])
            br.press(m, 0, player=p)
    br.run_frames(1)
    if fr % 200 == 0 and not START_P:
        refill(ram)
    for n in want.get(fr, []):
        held = [u32(ram, F[p] + 0x54) for p in range(4)]
        codes = [(u16(ram, h - 4 + 0x420) if h else 0) for h in held]
        shot(br, os.path.join(HERE, "shots", f"v_{n}.png"))
        print(f"shot {n} f={fr} codes={[hex(c) for c in codes]}")
