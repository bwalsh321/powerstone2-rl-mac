"""Headless menu driver — navigate the game via scripted button steps,
screenshot via get_frame, save/load work-in-progress savestates.

Built Aug 28 to re-stamp slot1 as Falcon-vs-Falcon without the visible
make_savestates window (slot1 shipped with P1=Ayame; every pool policy
is a Falcon policy, so the P1 self-play seat was structurally crippled —
the face_norm fingerprint 0.895 vs 0.991 was the tell).

Steps (comma-separated, run in order):
  p1:<btn>:<frames>   hold button on DC port A, then release
  p2:<btn>:<frames>   same on DC port B
  wait:<frames>       run frames with no input change
  shot:<name>         write <name>.png to --outdir + print RAM fingerprint
  save:<path>         gzip current emu state to <path>
Buttons: a b x y start up down left right

Example:
  python menu_drive.py --load states/slot1.state \
      --steps "p1:start:10,wait:60,shot:pause" --save work.state
"""
import argparse
import gzip
import math
import os

import numpy as np

from flycast_bridge import FlycastBridge
from ps2_ram import StateLineSynth

BTN = {"a": 0x004, "b": 0x002, "x": 0x400, "y": 0x200, "start": 0x008,
       "up": 0x010, "down": 0x020, "left": 0x040, "right": 0x080}


def fingerprint(synth):
    try:
        v = [float(x) for x in synth.line.split(",")]
    except (ValueError, AttributeError):
        return "line unavailable"
    h = v[1:5]
    out = [f"h={[round(x) for x in h]}"]
    for k in range(2):
        o = 5 + 5 * k
        n = math.hypot(v[o + 3], v[o + 4])
        out.append(f"P{k+1} pos=({v[o]:.0f},{v[o+2]:.0f}) face_norm={n:.3f}")
    return "  ".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--load", required=True)
    ap.add_argument("--steps", default="shot:probe")
    ap.add_argument("--save", default=None)
    ap.add_argument("--outdir", default="./menu_shots")
    ap.add_argument("--instance", type=int, default=5)
    args = ap.parse_args()

    core = os.path.expanduser(
        "~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib")
    game = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "../Power Stone 2 (USA).chd")
    os.makedirs(args.outdir, exist_ok=True)

    br = FlycastBridge(core, game, "./states", instance_id=args.instance)
    synth = StateLineSynth(br.ram, bot_player=2)
    br.attach_synth(synth)
    br.run_frames(8)
    with gzip.open(args.load, "rb") as f:
        br.emu.set_state(f.read())
    br.run_frames(8)
    print(f"[md] loaded {args.load}: {fingerprint(synth)}")

    for step in args.steps.split(","):
        parts = step.strip().split(":")
        if parts[0] in ("p1", "p2"):
            player = 0 if parts[0] == "p1" else 1
            mask, frames = BTN[parts[1]], int(parts[2])
            br.press(mask, frames, player=player)
            br.press(0x000, 4, player=player)     # release + settle
        elif parts[0] == "wait":
            br.run_frames(int(parts[1]))
        elif parts[0] == "shot":
            import pygame
            h, w = br.emu.get_shape()
            arr = np.zeros((h, w, 3), np.uint8)
            br.emu.get_frame(arr, w, h)
            surf = pygame.surfarray.make_surface(arr.swapaxes(0, 1))
            p = os.path.join(args.outdir, parts[1] + ".png")
            pygame.image.save(surf, p)
            print(f"[md] shot -> {p}   {fingerprint(synth)}")
        elif parts[0] == "save":
            with gzip.open(parts[1], "wb") as f:
                f.write(br.emu.get_state())
            print(f"[md] saved -> {parts[1]}   {fingerprint(synth)}")
        else:
            raise SystemExit(f"unknown step: {step}")
    br.emu.close()


if __name__ == "__main__":
    main()
