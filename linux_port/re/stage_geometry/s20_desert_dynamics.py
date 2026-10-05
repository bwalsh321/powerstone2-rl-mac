"""S20: desert prop dynamics.
(a) slot3 (3 lv8 COMs + idle P2) for 7200 f: sample the ledger every 30 f -> do clusters move / vanish / respawn? do poles?
(b) slot1: P2 interactions with a cluster at (-500,1000): push (walk into it 90 f), B (pick up?), X attack x3 -> cluster pos /
    ledger presence / P2 state (carry?)."""
from common import *
br = boot()
POLE, CL = 0x0C0F18D4, 0x0C0F1688
load(br, STATES["slot3"]); br.run_frames(10)
first = {a: (vt, p) for _, a, vt, p in ledger(br.ram) if vt in (POLE, CL)}
moved = {}; gone = set(); tline = []
for t in range(0, 7200, 30):
    br.run_frames(30)
    cur = {a: (vt, p) for _, a, vt, p in ledger(br.ram) if vt in (POLE, CL)}
    for a, (vt, p) in first.items():
        if a not in cur or cur[a][0] != vt: gone.add(a); continue
        d = np.hypot(cur[a][1][0] - p[0], cur[a][1][2] - p[2])
        moved[a] = max(moved.get(a, 0), d)
    tline.append((t, sum(1 for a in cur if cur[a][0] == CL), sum(1 for a in cur if cur[a][0] == POLE)))
print("(a) slot3 7200 f: clusters alive over time (every 600 f):", [c for (t, c, p) in tline[::20]], " poles:", [p for (t, c, p) in tline[::20]])
for a, (vt, p) in first.items():
    print(f"   {'POLE' if vt == POLE else 'CLUS'} @{a:08X} start ({p[0]:.0f},{p[2]:.0f}) max displacement {moved.get(a, 0):.0f}{'  GONE at some point' if a in gone else ''}")
# (b)
CX, CZ = -500.0, 1000.0
def cl_pos():
    for _, a, vt, p in ledger(br.ram):
        if vt == CL and np.hypot(p[0] - CX, p[2] - CZ) < 300: return p
    return None
for name, steps in {"push": [("up", 90)], "B": [("up", 12), ("b", 8), ("none", 40), ("down", 40)],
                    "X3": [("up", 12), ("x", 6), ("none", 10), ("x", 6), ("none", 10), ("x", 6), ("none", 60)]}.items():
    load(br, STATES["slot1"]); br.run_frames(10)
    place(br, 0, 1000, 0, -1000)
    place(br, 1, CX + 140 / 1.414, 0, CZ + 140 / 1.414); br.run_frames(2)    # 'up' walks into the cluster
    sts = []
    for b, n in steps:
        setpad(br, b, 1)
        for _ in range(n):
            br.run_frames(1); sts.append(pstate(br.ram, 1))
    setpad(br, "none", 1); br.run_frames(2)
    p = cl_pos(); q = logpos(br.ram, 1)
    shot(br, f"shots/s20_{name}.png")
    rle = [sts[0]] + [s for i, s in enumerate(sts[1:], 1) if s != sts[i - 1]]
    print(f"(b) {name}: cluster now {None if p is None else (round(p[0]), round(p[1]), round(p[2]))}  P2 {[round(v) for v in q]}  P2 state seq {rle}")
print("DONE")
