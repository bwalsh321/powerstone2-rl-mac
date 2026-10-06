"""Smoke-test player_state_reader against PS2Ram on slot2 (4P)."""
from harness import *
from ps2_ram import PS2Ram
import player_state_reader as R
br = boot(); load(br, "states/slot2.state"); br.run_frames(240)
ram = PS2Ram(br.ram); clk = R.FightClock(); clk.live(ram); br.run_frames(1)
print("fight live:", clk.live(ram), "menu:", ram.u8(R.G_MENU_OPEN), "COM level:", ram.u8(R.G_COM_LEVEL))
for k in range(4):
    d = R.read_player(ram, k)
    print(k, {kk: (tuple(round(x, 2) for x in v) if isinstance(v, tuple) else (round(v, 2) if isinstance(v, float) else v)) for kk, v in d.items()})
print("DONE"); sys.stdout.flush(); os._exit(0)
