"""Replay slot3 seed 3 (probe3 scheme, no START) and print items_dict.held_item() for all
seats at a few frames; screenshot f=9000 (P3 holding a Hammer, counter ~350/600) to compare
with the pink HUD gauge."""
import random
from common import *
import items_dict as D
br = boot(); load(br, "states/slot3.state"); ram = br.emu.get_ram()
rng = random.Random(3)
for fr in range(9001):
    if fr % 15 == 0:
        for p in (0, 1):
            m = rng.choice([0, BTN["left"], BTN["right"], BTN["up"], BTN["down"], BTN["a"], BTN["b"], BTN["y"], BTN["x"],
                            BTN["a"], BTN["b"], BTN["x"], BTN["up"] | BTN["right"], BTN["down"] | BTN["left"], 0])
            br.press(m, 0, player=p)
    br.run_frames(1)
    if fr % 200 == 0:
        refill(ram)
    if fr in (1000, 2100, 4800, 9000):
        print(fr, [D.held_item(ram, f) for f in F])
shot(br, os.path.join(HERE, "shots", "reader_f9000.png"))
