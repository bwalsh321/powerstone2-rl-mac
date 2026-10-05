"""Probe 2: pickup events. When F+0x54 goes 0->X (or X->Y) record the full
0x430-byte object at (X-4), the hold duration, and a screenshot 12 frames
later. Saves npz for offline field analysis + a savestate per event (first
40 events) so items can be re-examined."""
import sys, random
from common import *
slot = sys.argv[1]; N = int(sys.argv[2]); seed = int(sys.argv[3]) if len(sys.argv) > 3 else 1
tag = os.path.basename(slot).split(".")[0] + f"_s{seed}"
os.makedirs(os.path.join(HERE, "ev"), exist_ok=True)
br = boot(); load(br, slot); ram = br.emu.get_ram()
rng = random.Random(seed)
cur = [0]*4; start = [0]*4; evs = []; pending = []
dumps = []
for fr in range(N):
    if fr % 20 == 0:
        for p in (0, 1):
            m = rng.choice([0, BTN["left"], BTN["right"], BTN["up"], BTN["down"],
                            BTN["a"], BTN["b"], BTN["y"], BTN["x"], BTN["a"], BTN["b"],
                            BTN["up"] | BTN["right"], BTN["down"] | BTN["left"]])
            br.press(m, 0, player=p)
    br.run_frames(1)
    for p in range(4):
        ptr = u32(ram, F[p] + 0x54)
        if ptr != cur[p]:
            if cur[p]:
                evs[start[p]]["dur"] = fr - evs[start[p]]["f"]
            if ptr:
                o = off(ptr - 4)
                d = bytes(ram[o:o+0x430])
                fd = bytes(ram[off(F[p]-0x200):off(F[p]-0x200)+0x800])
                e = dict(i=len(evs), f=fr, p=p, ptr=ptr, prev=cur[p], dur=-1)
                evs.append(e); dumps.append((d, fd)); start[p] = e["i"]
                pending.append((fr + 12, e["i"], p))
                # (per-event savestates removed: 7.7 MB each; disk budget)
            cur[p] = ptr
    for t in [x for x in pending if x[0] == fr]:
        pending.remove(t)
        shot(br, os.path.join(HERE, "shots", f"{tag}_ev{t[1]:03d}_P{t[2]+1}.png"))
np.savez_compressed(os.path.join(HERE, "ev", f"{tag}_dumps.npz"),
                    obj=np.array([np.frombuffer(d, np.uint8) for d, _ in dumps]),
                    fobj=np.array([np.frombuffer(f, np.uint8) for _, f in dumps]),
                    meta=np.array([[e["i"], e["f"], e["p"], e["ptr"], e["prev"], e["dur"]] for e in evs], dtype=np.int64))
for e, (d, _) in zip(evs, dumps):
    w = np.frombuffer(d, "<u4")
    print(f"ev{e['i']:03d} f={e['f']} P{e['p']+1} ptr={e['ptr']:08x} prev={e['prev']:08x} dur={e['dur']} vt={w[2]:08x} "
          f"w3..12={' '.join(f'{x:08x}' for x in w[3:13])}")
