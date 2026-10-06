"""p02: long random-input census of the object ledger + pool classes.
usage: python p02_census.py <slot> <frames> <seed> [step]
Logs every ledger slot spawn/despawn (slot addr, vt, pos), keeps a per-vt
summary (count of sightings, max simultaneous, y range, first frame), and
dumps the first 0x200 bytes of each newly-seen vt record to out/vtdump_*.
Also tallies pool classes (act==1 and cls!=0)."""
import collections
import sys
from common import *

slot, N, seed = int(sys.argv[1]), int(sys.argv[2]), int(sys.argv[3])
step = int(sys.argv[4]) if len(sys.argv) > 4 else 4
br = boot(); load(br, slot)
ram = br.ram
pad = RandomPad(seed)
lo = LED_LO - 40 * 0x430
prev = {}
summary = {}
poolc = collections.Counter()
pool_first = {}
dump = open(f"{HERE}/out/vtdump_s{slot}_{seed}.txt", "w")
ev = open(f"{HERE}/out/events_s{slot}_{seed}.txt", "w")
items_seen = collections.Counter()
f = 0
while f < N:
    if f % 16 == 0:
        pad.step(br, 0)
    br.run_frames(step); f += step
    L = ledger(ram, lo, 220)
    cur = {}
    perv = collections.Counter()
    for k, a, h, vt, x, y, z in L:
        cur[a] = vt
        perv[vt] += 1
        s = summary.setdefault(vt, dict(n=0, maxsim=0, ymin=1e9, ymax=-1e9, first=f, slots=set()))
        s["n"] += 1; s["ymin"] = min(s["ymin"], y); s["ymax"] = max(s["ymax"], y)
        s["slots"].add(k - 40)
        if prev.get(a) != vt:
            ev.write(f"f={f:6d} SPAWN idx={k-40:3d} {a:#x} vt={vt:#010x} hdr={h:#010x} pos=({x:.1f},{y:.1f},{z:.1f})\n")
            if s["n"] == 1:
                o = off(a)
                dump.write(f"### vt={vt:#010x} first f={f} slot {a:#x}\n")
                for r in range(0, 0x200, 16):
                    w = [u32(ram, a + r + 4*i) for i in range(4)]
                    dump.write(f"  +{r:03x}: " + " ".join(f"{v:08x}" for v in w) + "\n")
    for a, vt in prev.items():
        if cur.get(a) != vt:
            ev.write(f"f={f:6d} GONE  {a:#x} vt={vt:#010x}\n")
    for vt, n in perv.items():
        summary[vt]["maxsim"] = max(summary[vt]["maxsim"], n)
    prev = cur
    if f % 32 == 0:
        P = pool(ram)
        for _, a, cl in P:
            if cl:
                poolc[cl] += 1
                pool_first.setdefault(cl, f)
        for p in range(4):
            it = held_item(ram, p)
            if it:
                items_seen[it] += 1
    if f % 1200 == 0:
        shot(br, f"{HERE}/shots/p02_s{slot}_{seed}_{f}.png")
        print(f"f={f} live ledger: " + ", ".join(f"{vt:#x}x{n}" for vt, n in sorted(perv.items())), flush=True)
print("\n=== ledger vtables (sightings, maxsim, y range, first frame, grid idxs)")
for vt, s in sorted(summary.items()):
    sl = sorted(s["slots"])
    print(f"  {vt:#010x} n={s['n']:6d} maxsim={s['maxsim']:3d} y=[{s['ymin']:.1f},{s['ymax']:.1f}] first={s['first']} idx={sl[0]}..{sl[-1]} ({len(sl)})")
print("=== pool classes (sightings per 32f, first frame)")
for cl, n in sorted(poolc.items()):
    print(f"  {cl:#010x} n={n} first={pool_first[cl]}")
print("=== held items seen", {f'{k:#x}': v for k, v in items_seen.items()})
br.emu.close()
