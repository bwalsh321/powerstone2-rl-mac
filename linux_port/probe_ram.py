"""Step-1 go/no-go: prove we can read Power Stone 2 state from libretro RAM.

Run on the Linux box (Xvfb or SDL dummy video, same as the boot test that
already works):

    DISPLAY=:99 SDL_AUDIODRIVER=dummy python3 probe_ram.py \
        --core ../cores/flycast_libretro.so --game "../Power Stone 2 (USA).chd"

What it does:
 1. Boots the core, runs N frames (default 3600 = ~60 s of attract mode).
 2. Checks RAM size and reads the four health floats at the RAM_MAP addrs.
 3. If they don't read as plausible health, SCANS all of RAM for the
    signature (four contiguous float32 == 1000.0, 4-byte stride) and
    reports the delta so ps2_addr.RAM_DELTA can be set.
 4. Dumps the first synthesized v7 state line as a bonus.

Success looks like:  "HEALTH OK at +0x0: [1000.0, 1000.0, 1000.0, 1000.0]"
(attract-mode demo fights also show sub-1000 values — anything in (0, 1000]
on 2+ slots counts).
"""
import argparse
import sys

import numpy as np

import _retro
import ps2_addr as A


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--core", required=True)
    ap.add_argument("--game", required=True)
    ap.add_argument("--frames", type=int, default=3600)
    ap.add_argument("--state", default=None,
                    help="gzip'd slot .state to load before probing (skips the "
                         "attract-mode wait; probe mid-match where health is live)")
    args = ap.parse_args()

    emu = _retro.RetroEmulator()
    # README_MIGRATION correction: the project has never had real BIOS files —
    # run flycast on its built-in HLE BIOS, same as the Windows rig always did.
    # (modern core uses the flycast_ prefix; reicast_ kept for older builds)
    emu.set_variable("flycast_hle_bios", "enabled")
    emu.set_variable("reicast_hle_bios", "enabled")
    # VMUs in port A/B slot 1 — flycast only attaches expansion devices on a
    # variables update after startup; setting these raises the update flag.
    emu.set_variable("flycast_device_port1_slot1", "VMU")
    emu.set_variable("flycast_device_port2_slot1", "VMU")
    # Threaded rendering races our frontend at init/teardown; single-thread
    # is also the deterministic mode an RL harness wants.
    emu.set_variable("flycast_threaded_rendering", "disabled")
    emu.set_variable("reicast_threaded_rendering", "disabled")
    emu.init(args.core.encode(), args.game.encode(), 0)
    if args.state:
        import gzip
        print("core booted; warming up before loadstate…")
        for i in range(120):
            emu.run()
        with gzip.open(args.state, "rb") as fh:
            emu.set_state(fh.read())
        print(f"loaded {args.state}; settling…")
        for i in range(4):
            emu.run()
    else:
        print("core booted; running frames…")
        for i in range(args.frames):
            emu.run()

    try:
        ram = emu.get_ram()
    except RuntimeError as e:
        print(f"FAIL: core does not expose SYSTEM_RAM ({e}).")
        print("Fallback: emu.get_memory_pointer() + a ctypes view, or patch")
        print("flycast's retro_get_memory_data. This is the only hard blocker.")
        sys.exit(2)

    print(f"SYSTEM_RAM exposed: {ram.size / 1024 / 1024:.0f} MiB")

    def read_health(delta):
        base = A.RAM_BASE + delta
        out = []
        for a in A.HEALTH:
            o = a - base
            if 0 <= o <= ram.size - 4:
                out.append(float(np.frombuffer(ram[o:o+4], "<f4")[0]))
            else:
                out.append(float("nan"))
        return out

    h = read_health(0)
    plausible = sum(1 for v in h if 0.0 < v <= 1000.0)
    if plausible >= 2:
        print(f"HEALTH OK at delta +0x0: {h}")
    else:
        print(f"direct read implausible ({h}); scanning for the signature…")
        f = np.frombuffer(ram.tobytes(), "<f4")
        full = np.isclose(f, 1000.0)
        hits = np.nonzero(full[:-3] & full[1:-2] & full[2:-1] & full[3:])[0]
        if len(hits) == 0:
            print("no 4x1000.0 signature — start an actual match (or run more")
            print("frames into attract mode) and retry. If it still fails,")
            print("the core may expose RAM via memory maps only.")
            sys.exit(1)
        for hidx in hits[:5]:
            byte_off = int(hidx) * 4
            delta = byte_off - (A.HEALTH[0] - A.RAM_BASE)
            print(f"  candidate at byte +{byte_off:#x} -> RAM_DELTA = {delta:#x}")
        print("Set ps2_addr.RAM_DELTA to the (single) reported delta.")

    # bonus: full line synth
    try:
        from ps2_ram import StateLineSynth
        s = StateLineSynth(ram, bot_player=2)
        s.tick(0); emu.run(); s.tick(0)
        line = s.line          # Aug 28: line is a lazy property now
        print("sample v7 line:")
        print(" ", line.strip()[:200], "…")
        print(f"  fields: {len(line.strip().split(','))} (want 80)")
    except Exception as e:
        print(f"(line synth not ready yet: {e})")

    emu.close()   # join core threads before interpreter teardown


if __name__ == "__main__":
    main()
