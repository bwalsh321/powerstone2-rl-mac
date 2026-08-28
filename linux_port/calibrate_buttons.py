"""Empirically verify the RetroPad -> DC button mapping.

The DC_TO_RETRO table in flycast_bridge.py follows flycast-libretro's
standard layout, but 30 seconds of verification beats a week of training on
a swapped jump button. From a loaded match savestate this holds each
RetroPad id for a second and reports what moved:

  * dpad ids 4-7: bot x/z should change sign-consistently
  * jump (DC A): bot y (matrix +0x34) should spike
  * attack/grab/throw: opponent health / gem drops — eyeball the printout

Usage:
    DISPLAY=:99 SDL_AUDIODRIVER=dummy python3 calibrate_buttons.py \
        --core ... --game ... --state states/slot1.state --player 1
"""
import argparse
import gzip

import numpy as np

import _retro
import ps2_addr as A
from ps2_ram import PS2Ram


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--core", required=True)
    ap.add_argument("--game", required=True)
    ap.add_argument("--state", required=True)
    ap.add_argument("--player", type=int, default=1,
                    help="libretro port index (DC port B / in-game P2 = 1)")
    ap.add_argument("--ingame-player", type=int, default=2)
    args = ap.parse_args()

    emu = _retro.RetroEmulator()
    # Standard harness options: HLE BIOS, VMUs, and threaded rendering OFF
    # (threaded rendering races our frontend at init/teardown; single-thread
    # is also the deterministic mode an RL harness wants).
    emu.set_variable("flycast_hle_bios", "enabled")
    emu.set_variable("reicast_hle_bios", "enabled")
    emu.set_variable("flycast_device_port1_slot1", "VMU")
    emu.set_variable("flycast_device_port2_slot1", "VMU")
    emu.set_variable("flycast_threaded_rendering", "disabled")
    emu.set_variable("reicast_threaded_rendering", "disabled")
    emu.init(args.core.encode(), args.game.encode(), 0)
    for _ in range(120):
        emu.run()
    with gzip.open(args.state, "rb") as fh:
        emu.set_state(fh.read())
    for _ in range(30):
        emu.run()

    ram = PS2Ram(emu.get_ram())
    mat = A.PLAYER_MAT[args.ingame_player - 1]

    def pose():
        return np.array([ram.f32(mat + o) for o in A.MAT_POS])

    names = {0: "B(=DC A?)", 1: "Y(=DC X?)", 3: "START", 4: "UP", 5: "DOWN",
             6: "LEFT", 7: "RIGHT", 8: "A(=DC B?)", 9: "X(=DC Y?)",
             10: "L1", 11: "R1", 12: "L2(=DC Ltrig?)", 13: "R2(=DC Rtrig?)"}
    with gzip.open(args.state, "rb") as fh:
        snap = fh.read()

    for rid, label in names.items():
        emu.set_state(snap)
        for _ in range(20):
            emu.run()
        p0 = pose()
        h0 = [ram.f32(a) for a in A.HEALTH]
        m = np.zeros(16, np.uint8); m[rid] = 1
        emu.set_button_mask(m, args.player)
        for _ in range(60):
            emu.run()
        emu.set_button_mask(np.zeros(16, np.uint8), args.player)
        for _ in range(30):
            emu.run()
        d = pose() - p0
        dh = [round(ram.f32(a) - h, 1) for a, h in zip(A.HEALTH, h0)]
        print(f"id {rid:2d} {label:16s} dpos=({d[0]:8.1f},{d[1]:7.1f},{d[2]:8.1f})"
              f"  dHealth={dh}")

    print("\nInterpretation: dpad -> big |dx| or |dz|; jump (DC A) -> dy > 0;")
    print("attack ids -> opponent dHealth < 0 if in range. Update DC_TO_RETRO")
    print("in flycast_bridge.py if anything is swapped.")
    emu.close()   # join core threads before interpreter teardown


if __name__ == "__main__":
    main()
