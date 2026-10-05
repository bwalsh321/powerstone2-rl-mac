"""Smoke-test the round-2 reader: run slot3 (lv8 4P) and print threat features whenever a hit sphere is live."""
from harness import *
from ps2_ram import PS2Ram
import player_state_reader as R
br = boot(); load(br, "states/slot3.state"); br.run_frames(300)
ram = PS2Ram(br.ram); clk = R.HitboxClock(); shown = 0
for t in range(3000):
    br.run_frames(1); age = clk.update(ram)
    for k in range(4):
        if age[k] == 1 and shown < 12:
            for me in range(4):
                if me == k: continue
                f = R.threat_features(ram, me, k)
                if f and f[4] < 150:
                    d = R.read_player(ram, k)
                    print(f"t{t} P{k+1} {R.CHAR_NAMES[d['char']]} s{d['state']} act {d['act']:x} spheres {len(d['hit_spheres'])} -> vs P{me+1}: dx {f[0]:.0f} dy {f[1]:.0f} dz {f[2]:.0f} r {f[3]:.0f} margin {f[4]:.0f}")
                    shown += 1
print("stage area", ram.u32(R.G_STAGE_AREA))
print("DONE"); sys.stdout.flush(); os._exit(0)
