"""E18: melee hitbox validation. For each character state cstates/char_<id>.state (P1 = char, P2 = Falcon
dummy, both human), P2 is teleported at distance D in front of P1 (or along the 'right' run direction for
dash moves) and P1 performs a move. Per frame we log compact fields for both players.
Output: data_e18.npz (small) with arrays keyed by run index + run table."""
import itertools
from harness import *
from flycast_bridge import DC_TO_RETRO
CHARS = [0, 6, 4, 1, 2, 5, 7, 3, 8, 10, 9, 11, 14, 15]
MOVES = {
    "x":    [("x", 2), ("none", 70)],
    "xxx":  [("x", 2), ("none", 8), ("x", 2), ("none", 8), ("x", 2), ("none", 80)],
    "b":    [("b", 2), ("none", 70)],
    "jx":   [("a", 2), ("none", 6), ("x", 2), ("none", 70)],
    "jb":   [("a", 2), ("none", 6), ("b", 2), ("none", 80)],
    "dashx": [("right", 18), ("right+x", 2), ("none", 70)],
    "dashb": [("right", 18), ("right+b", 2), ("none", 70)],
}
DISTS = [50, 90, 130, 170, 230]
br = boot()
def setm(port, mask):
    m = np.zeros(16, np.uint8)
    for bit, rid in DC_TO_RETRO.items():
        if mask & bit: m[rid] = 1
    br.emu.set_button_mask(m, port)
def expand(steps):
    seq = []
    for b, n in steps:
        m = 0
        for k in b.split("+"): m |= BTN[k]
        seq += [m] * n
    return seq
FIELDS = []  # per frame: [P1 0x100..0x1C0 raw u32 (48), P2 0x100..0x1C0 (48), P1/P2 pos(3+3), state, act, hp]
runs, data = [], []
for cid in CHARS:
    st_path = os.path.join(HERE, f"cstates/char_{cid}.state")
    for mv, steps in MOVES.items():
        for D in DISTS:
            load(br, st_path)
            r = snap(br); x, y, z = ppos(r, 0)
            if mv.startswith("dash"):
                ux, uz = 0.7071, -0.7071; D2 = D + 140
            else:
                a = u16(r, P[0] + 0x38) * 2 * np.pi / 65536; ux, uz = np.sin(a), np.cos(a); D2 = D
            place(br, 1, x + ux * D2, 0.0, z + uz * D2); br.run_frames(1)
            seq = expand(steps); rec = []
            for t, m in enumerate(seq):
                setm(0, m); setm(1, 0); br.emu.run()
                row = []
                for k in (0, 1):
                    b = br.ram[off(P[k]):off(P[k]) + 0x3830]
                    row.append(np.concatenate([b[0x0:0x200].view("<u4"), b[0x3710:0x3830].view("<u4")]))
                rec.append(np.stack(row))
            runs.append((cid, mv, D)); data.append(np.stack(rec))
    print("char", cid, "done", flush=True)
L = max(len(d) for d in data)
arr = np.zeros((len(data), L, 2, data[0].shape[2]), np.uint32)
for i, d in enumerate(data): arr[i, :len(d)] = d
np.savez_compressed(os.path.join(HERE, "data_e18.npz"), arr=arr, runs=np.array([f"{c}|{m}|{d}" for c, m, d in runs]),
                    lens=np.array([len(d) for d in data]))
print("DONE"); sys.stdout.flush(); os._exit(0)
