"""E17: build human-vs-human match states: P1 = each of the 14 selectable characters, P2 = Falcon,
desert stage (stage-select cursor: down, down from the top-left icon). Runs until the fight-live
counter advances (+20 frames) and saves cstates/char_<id>.state. Char cycle order from t_charcycle."""
from harness import *
ORDER = [0, 6, 4, 1, 2, 5, 7, 3, 8, 10, 9, 11, 14, 15]
br = boot()
os.makedirs(os.path.join(HERE, "shots/e17"), exist_ok=True)
for n, cid in enumerate(ORDER):
    load(br, os.path.join(LP, "menu_cycle.state")); br.run_frames(10)
    for i in range(n + 1): br.press(BTN["a"], 2, player=0); br.press(0, 25, player=0)
    got = u32(snap(br), 0x8C472DA8 + 8)
    br.press(BTN["start"], 2, player=0); br.press(0, 60, player=0)
    for m in ("down", "down"): br.press(BTN[m], 2, player=0); br.press(0, 10, player=0)
    br.press(BTN["a"], 2, player=0); br.press(0, 2, player=0)
    prev = u32(snap(br), 0x8C475200); t0 = None
    for t in range(3000):
        br.run_frames(1); v = u32(snap(br), 0x8C475200)
        if v != prev: t0 = t; break
    br.run_frames(20)
    r = snap(br)
    shot(br, os.path.join(HERE, f"shots/e17/char_{cid:02d}.png"))
    with gzip.open(os.path.join(HERE, f"cstates/char_{cid}.state"), "wb") as fh: fh.write(br.emu.get_state())
    print(f"char {cid}: menu id {got}, live after {t0}, P+2 = {r[off(P[0]+2)]}, P2 char {r[off(P[1]+2)]}, stage area {u32(r, 0x8C472CF8)}, P1 pos {ppos(r,0)} P2 pos {ppos(r,1)}")
print("DONE"); sys.stdout.flush(); os._exit(0)
