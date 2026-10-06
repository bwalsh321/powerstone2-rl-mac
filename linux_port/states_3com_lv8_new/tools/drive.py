"""drive.py -- menu_drive.py (linux_port/) extended for the discriminator stamps.

Adds over menu_drive.py:
  p3:/p4:<btn>:<frames>   DC ports C/D (libretro ports 2/3)
  dump:<name>             write SYSTEM_RAM bytes to <outdir>/<name>.ram
  shot:<name>             PNG is written already flipped upright
  rep:<n>:<step;step>     repeat a ';'-separated sub-sequence n times
Default instance = 4 (other agents use 1-3).
"""
import argparse, gzip, math, os, sys
import numpy as np
ROOT="/home/superserver/powerstone2-rl-mac/linux_port"
sys.path.insert(0, ROOT)
from flycast_bridge import FlycastBridge
from ps2_ram import StateLineSynth

BTN = {"a": 0x004, "b": 0x002, "x": 0x400, "y": 0x200, "start": 0x008,
       "up": 0x010, "down": 0x020, "left": 0x040, "right": 0x080}
PORT = {"p1": 0, "p2": 1, "p3": 2, "p4": 3}


def fingerprint(synth):
    try:
        v = [float(x) for x in synth.line.split(",")]
    except (ValueError, AttributeError):
        return "line unavailable"
    out = [f"h={[round(x) for x in v[1:5]]}"]
    for k in range(2):
        o = 5 + 5 * k
        out.append(f"P{k+1} face_norm={math.hypot(v[o+3], v[o+4]):.3f}")
    return "  ".join(out)


NAMES = {0:"Falcon",1:"Ryoma",2:"Wang-Tang",3:"Jack",4:"Gunrock",5:"Galuda",6:"Ayame",7:"Rouge",8:"Pete",9:"Gourmand",10:"Julia",11:"Accel",14:"Mel",15:"Pride"}
def ram_info(ram):
    r = np.asarray(ram, dtype=np.uint8)
    u32 = lambda o: int.from_bytes(bytes(r[o:o+4]), "little")
    diff = [int(r[o]) for o in (0x472AD4, 0x4683A6, 0x46C3D4, 0x5429AD, 0x5429C8)]
    seats = []
    for k in range(4):
        b = 0x472DA8 + 0x14 * k
        t, cid, pres = u32(b), u32(b + 8), u32(b + 0x10)
        seats.append(f"P{k+1}:{['HUM','COM','EMPTY'][t] if t<3 else t}/{NAMES.get(cid, cid)}/{pres}")
    return f"diff={diff} live={u32(0x475200)} stage={u32(0x472CF8)} seats=[{', '.join(seats)}]"


def expand(steps):
    out = []
    for s in steps.split(","):
        s = s.strip()
        if not s:
            continue
        if s.startswith("rep:"):
            _, n, sub = s.split(":", 2)
            out += [x for x in sub.split(";")] * int(n)
        else:
            out.append(s)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--load", default=None)
    ap.add_argument("--steps", default="shot:probe")
    ap.add_argument("--outdir", default="./shots")
    ap.add_argument("--instance", type=int, default=70)
    args = ap.parse_args()
    root = ROOT
    core = os.path.expanduser("~/cores/flycast_libretro.so")
    game = os.path.join(root, "../Power Stone 2 (USA).chd")
    os.makedirs(args.outdir, exist_ok=True)
    br = FlycastBridge(core, game, "/tmp/claude-1000/stamp60/statesdir", instance_id=args.instance)
    synth = StateLineSynth(br.ram, bot_player=2)
    br.attach_synth(synth)
    br.run_frames(8)
    if args.load:
        with gzip.open(args.load, "rb") as f:
            br.emu.set_state(f.read())
        br.run_frames(8)
    print(f"[dr] loaded {args.load}: {fingerprint(synth)}", flush=True)
    for step in expand(args.steps):
        parts = step.split(":")
        if parts[0] in PORT and parts[1] in ("l", "r"):
            pl = PORT[parts[0]]
            br.axis(5 if parts[1] == "l" else 6, 1.0, int(parts[2]), player=pl)
            br.press(0x000, 4, player=pl)
        elif parts[0] in PORT:
            pl = PORT[parts[0]]
            br.press(BTN[parts[1]], int(parts[2]), player=pl)
            br.press(0x000, 4, player=pl)
        elif parts[0] == "wait":
            br.run_frames(int(parts[1]))
        elif parts[0] == "shot":
            from PIL import Image, ImageOps
            h, w = br.emu.get_shape()
            arr = np.zeros((h, w, 3), np.uint8)
            br.emu.get_frame(arr, w, h)
            p = os.path.join(args.outdir, parts[1] + ".png")
            ImageOps.flip(Image.fromarray(arr)).save(p)
            print(f"[dr] shot -> {p}   {fingerprint(synth)}", flush=True)
        elif parts[0] == "info":
            print(f"[dr] info {parts[1] if len(parts)>1 else ''}: {ram_info(br.ram)}", flush=True)
        elif parts[0] == "dump":
            p = os.path.join(args.outdir, parts[1] + ".ram")
            np.asarray(br.ram, dtype=np.uint8).tofile(p)
            print(f"[dr] ram -> {p}", flush=True)
        elif parts[0] == "save":
            with gzip.open(parts[1], "wb") as f:
                f.write(br.emu.get_state())
            print(f"[dr] saved -> {parts[1]}   {fingerprint(synth)}", flush=True)
        else:
            raise SystemExit(f"unknown step: {step}")
    br.emu.close()


if __name__ == "__main__":
    main()
