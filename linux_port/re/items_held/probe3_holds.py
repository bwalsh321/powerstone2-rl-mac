"""Probe 3: hold timelines. For every player every frame read F+0x54 -> held
object o (=ptr-4). Log per hold: item code u16 @ o+0x420, counter u16 @ o+0x424,
holder mask byte @ o+0x426, byte @ o+0x427, u32 @ o+0x428, the update fn @ o+8,
counter changes (frame, value, player state byte) and what happens to the object
after release (does it move fast = thrown?). Also census of every live grid
object's code each 300 frames (what is lying on the stage).
usage: probe3_holds.py <state> <frames> <seed> [tag]"""
import sys, random, json, collections
from common import *
slot = sys.argv[1]; N = int(sys.argv[2]); seed = int(sys.argv[3])
START_P = float(os.environ.get("START_P", "0"))
tag = (sys.argv[4] if len(sys.argv) > 4 else os.path.basename(slot).split(".")[0]) + f"_s{seed}"
br = boot(); load(br, slot); ram = br.emu.get_ram()
rng = random.Random(seed)
PM = A.PLAYER_MAT
GRID0 = 0x0C500030 - 16 * 0x430
holds = []; cur = [None]*4; census = collections.Counter(); released = []
def obj_info(o):
    return dict(code=u16(ram, o+0x420), ctr=u16(ram, o+0x424), mask=int(ram[off(o+0x426)]),
                b427=int(ram[off(o+0x427)]), w428=u32(ram, o+0x428), fn=u32(ram, o+8))
for fr in range(N):
    if fr % 15 == 0:
        for p in (0, 1):
            m = rng.choice([0, BTN["left"], BTN["right"], BTN["up"], BTN["down"],
                            BTN["a"], BTN["b"], BTN["y"], BTN["x"], BTN["a"], BTN["b"], BTN["x"],
                            BTN["up"] | BTN["right"], BTN["down"] | BTN["left"], BTN["start"] if (START_P and rng.random() < START_P) else 0])
            br.press(m, 0, player=p)
    br.run_frames(1)
    if fr % 200 == 0 and not START_P:
        refill(ram)
    for p in range(4):
        ptr = u32(ram, F[p] + 0x54)
        o = ptr - 4 if ptr else None
        h = cur[p]
        if h is not None and (o != h["o"]):
            h["end"] = fr; h["end_info"] = obj_info(h["o"])
            released.append((fr, h))
            cur[p] = None; h = None
        if o is not None and h is None:
            i = obj_info(o)
            h = dict(p=p, o=o, start=fr, end=None, info=i, ctr_log=[(fr, i["ctr"])], post=[])
            holds.append(h); cur[p] = h
        if h is not None:
            c = u16(ram, o + 0x424)
            if c != h["ctr_log"][-1][1]:
                st = int(ram[off(PM[p] + A.PSTATE_OFF)])
                h["ctr_log"].append((fr, c, st))
    # post-release trajectory of released objects for 40 frames
    for (rf, h) in list(released):
        o = h["o"]
        if fr - rf <= 40:
            if (fr - rf) % 4 == 0:
                h["post"].append((fr - rf, round(f32(ram, o+0x2c)), round(f32(ram, o+0x30)), round(f32(ram, o+0x34)),
                                  u16(ram, o+0x420), int(ram[off(o+4)]), u32(ram, o+8)))
        else:
            released.remove((rf, h))
    if fr % 300 == 0:
        for k in range(110):
            s = GRID0 + k * 0x430
            if ram[off(s+4)] == 9:
                census[(u16(ram, s+0x420), u32(ram, s+8))] += 1
out = dict(tag=tag, holds=[{k: v for k, v in h.items()} for h in holds],
           census=[[c, fn, n] for (c, fn), n in census.items()])
json.dump(out, open(os.path.join(HERE, "ev", f"holds_{tag}.json"), "w"))
print(f"{tag}: {len(holds)} holds")
