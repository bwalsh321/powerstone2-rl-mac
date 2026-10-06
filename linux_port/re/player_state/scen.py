"""Scenario runner: from base_s1.state (or --state), apply per-port input scripts,
record P1..P4 structs every frame, screenshot every --every frames, and print a
per-frame table of the candidate state fields for both players.
usage: scen.py NAME 'p1script' 'p2script' [--place dz] [--state path] [--every n] [--gems n]
script: comma list of btn:frames (btn = none|a|b|x|y|up|down|left|right, '+' to combine)"""
import argparse
from harness import *
ap = argparse.ArgumentParser()
ap.add_argument("name"); ap.add_argument("s1"); ap.add_argument("s2", nargs="?", default="none:1")
ap.add_argument("--place", type=float, default=None, help="put P2 at P1 + (0,0,-dz)")
ap.add_argument("--placex", type=float, default=0.0)
ap.add_argument("--state", default=os.path.join(HERE, "base_s1.state"))
ap.add_argument("--every", type=int, default=6)
ap.add_argument("--nplayers", type=int, default=2)
ap.add_argument("--poke", action="append", default=[], help="addr:type:val written once at start")
ap.add_argument("--save", default=None, help="save state at end")
ap.add_argument("--table", action="store_true")
args = ap.parse_args()

def parse(s):
    out = []
    for tok in s.split(","):
        b, n = tok.split(":"); out.append((b, int(n)))
    return out
def expand(steps):
    seq = []
    for b, n in steps:
        m = 0
        for k in b.split("+"): m |= BTN[k]
        seq += [m]*n
    return seq
s1, s2 = expand(parse(args.s1)), expand(parse(args.s2))
T = max(len(s1), len(s2))
br = boot(); load(br, args.state)
if args.place is not None:
    r = snap(br); x, y, z = ppos(r, 0); place(br, 1, x + args.placex, y, z - args.place); br.run_frames(2)
for p in args.poke:
    a, t, v = p.split(":"); a = int(a, 16)
    if t == "f": wf32(br, a, float(v))
    elif t == "u8": br.ram[off(a)] = int(v, 0)
    elif t == "u32": struct.pack_into("<I", br.ram, off(a), int(v, 0))
sd = os.path.join(HERE, "shots", args.name); os.makedirs(sd, exist_ok=True)
from flycast_bridge import DC_TO_RETRO
def setm(port, mask):
    m = np.zeros(16, np.uint8)
    for bit, rid in DC_TO_RETRO.items():
        if mask & bit: m[rid] = 1
    br.emu.set_button_mask(m, port)
rec = []
for t in range(T):
    setm(0, s1[t] if t < len(s1) else 0); setm(1, s2[t] if t < len(s2) else 0)
    br.emu.run()
    rec.append(np.stack([br.ram[off(P[i]):off(P[i]) + PSTRIDE].copy() for i in range(args.nplayers)]))
    if t % args.every == 0: shot(br, os.path.join(sd, f"{t:04d}.png"))
R = np.stack(rec)
np.save(os.path.join(HERE, f"data_scen_{args.name}.npy"), R)
if args.save:
    with gzip.open(args.save, "wb") as fh: fh.write(br.emu.get_state())
def row(t, i):
    b = R[t, i]
    U = lambda o: struct.unpack_from("<I", b, o)[0]
    H = lambda o: struct.unpack_from("<H", b, o)[0]
    Fl = lambda o: struct.unpack_from("<f", b, o)[0]
    return (f"act={H(0x3818):04x} md={b[0x3715]:02x}/{b[0x3716]:02x} s14={U(0x14):06x} t1c={U(0x1C):08x} "
            f"f134={U(0x134):05x} y={Fl(0x2C):6.1f} v=({Fl(0x4C):5.1f},{Fl(0x50):5.1f},{Fl(0x54):5.1f}) "
            f"hp={Fl(0x160):6.1f} ang={H(0x38):04x} gnd={U(0x404):08x} 38cc={U(0x38CC):08x}/{U(0x38D0)}")
def rle(i):
    out = []; prev = None
    for t in range(T):
        b = R[t, i]; key = (b[0x3715], struct.unpack_from("<H", b, 0x3818)[0])
        if key != prev:
            y = struct.unpack_from("<f", b, 0x2C)[0]; hp = struct.unpack_from("<f", b, 0x160)[0]
            out.append(f"{t}:s{key[0]}/a{key[1]:x}(y{y:.0f},hp{hp:.0f})"); prev = key
    return " ".join(out)
for i in range(args.nplayers):
    print(f"P{i+1} RLE:", rle(i))
if not args.table:
    print("DONE"); sys.stdout.flush(); os._exit(0)
print("frame  in1 in2 | P1 ... || P2 ...")
for t in range(T):
    print(f"{t:4d} {s1[t] if t < len(s1) else 0:4x} {s2[t] if t < len(s2) else 0:4x} | {row(t,0)} || {row(t,1)}")
print("DONE"); sys.stdout.flush(); os._exit(0)
