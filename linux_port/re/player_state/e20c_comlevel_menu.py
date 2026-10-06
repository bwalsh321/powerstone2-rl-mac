"""E20c: causal COM-level test via the menu. menu_cycle -> P1 Falcon, P3 = COM Pete, stage select;
poke 0x8C472AD4 := L BEFORE choosing the desert stage; play 3600 frames with both humans idle (health
refilled) and count Pete's attack windows (hit-sphere count byte P+0x187 > 1) and damage dealt."""
from harness import *
br = boot()
def to_stage_select():
    load(br, os.path.join(LP, "menu_cycle.state")); br.run_frames(10)
    for b in ["a", "right", "right", "up", "a", "a", "down", "down", "a"]:
        br.press(BTN[b], 2, player=0); br.press(0, 22, player=0)
    br.press(BTN["start"], 2, player=0); br.press(0, 60, player=0)
def go(level):
    to_stage_select()
    before = br.ram[off(0x8C472AD4)]
    if level is not None: br.ram[off(0x8C472AD4)] = level
    for m in ("down", "down"): br.press(BTN[m], 2, player=0); br.press(0, 10, player=0)
    br.press(BTN["a"], 2, player=0); br.press(0, 2, player=0)
    prev = u32(snap(br), 0x8C475200)
    for t in range(3000):
        br.run_frames(1)
        if u32(snap(br), 0x8C475200) != prev: break
    after = br.ram[off(0x8C472AD4)]
    win = 0; dmg = 0.0; pl = False; acts = set()
    for t in range(3600):
        br.emu.run(); r = br.ram
        live = r[off(P[2] + 0x187)] > 1
        if live and not pl: win += 1
        pl = live; acts.add(struct.unpack_from("<H", r, off(P[2] + 0x3818))[0])
        for k in (0, 1):
            hp = struct.unpack_from("<f", r, off(P[k] + 0x160))[0]
            if hp < 1000.0:
                dmg += 1000.0 - hp
                for ad in (A.HEALTH_OBJ[k], A.HEALTH[k], A.HEALTH[k] + 0x30, A.HEALTH[k] + 0x50): wf32(br, ad, 1000.0)
    print(f"level poke {level}: byte at stage select {before} -> at fight start {after}; P3 char {br.ram[off(P[2]+2)]} COM {br.ram[off(P[2]+0x3720)]}; "
          f"COM attack windows {win}, damage to idle humans {dmg:.0f}, distinct acts {len(acts)}")
for L in (None, 0, 7, 0, 7):
    go(L)
print("DONE"); sys.stdout.flush(); os._exit(0)
