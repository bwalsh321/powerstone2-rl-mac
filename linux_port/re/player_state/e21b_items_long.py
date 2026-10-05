"""E21b (longer, 4 x 40000 frames, seed argv[1]) -- E21: held-item melee. Run a 4P slot3/slot2 census (random P1/P2 inputs) until some seat is holding an item
(P+0x376C != 0) and is in state 7, logging each such attack window: sphere count, radii, hits.
Health refilled. Stops after 60000 frames. Also logs pole states (35, and acts 0x208-0x20f/0x21f)."""
import random, collections
from harness import *
from flycast_bridge import DC_TO_RETRO
random.seed(int(sys.argv[1]) if len(sys.argv) > 1 else 5)
br = boot()
def setm(port, mask):
    m = np.zeros(16, np.uint8)
    for bit, rid in DC_TO_RETRO.items():
        if mask & bit: m[rid] = 1
    br.emu.set_button_mask(m, port)
BTNS = [0, BTN["x"], BTN["a"], BTN["b"], BTN["y"], BTN["x"], BTN["x"]]
DIRS = [0, BTN["up"], BTN["down"], BTN["left"], BTN["right"]]
def F_(k, o): return struct.unpack_from("<f", br.ram, off(P[k] + o))[0]
def U_(k, o): return struct.unpack_from("<I", br.ram, off(P[k] + o))[0]
def hurt(k): return (F_(k, 0x18C), F_(k, 0x190), F_(k, 0x194), F_(k, 0x198), F_(k, 0x19C))
def spheres(k):
    n = max(0, br.ram[off(P[k] + 0x187)] - 1)
    return [tuple(F_(k, 0x1AC + 0x20*j + 4*q) for q in range(4)) for j in range(n)]
def ov(k, v):
    hx, hy, hz, rr, hh = hurt(v)
    return any(np.hypot(x-hx, z-hz) <= r+rr and abs(y-hy) <= r+hh for x, y, z, r in spheres(k))
res = collections.defaultdict(collections.Counter); radii = collections.defaultdict(collections.Counter)
for slot in (3, 2, 3, 2):
    load(br, f"states/slot{slot}.state")
    cur = [0, 0]; left = [0, 0]; win = {}
    for t in range(40000):
        for p in (0, 1):
            if left[p] <= 0: cur[p] = random.choice(DIRS) | random.choice(BTNS); left[p] = random.randint(2, 20)
            left[p] -= 1; setm(p, cur[p])
        hp0 = [F_(k, 0x160) for k in range(4)]
        br.emu.run()
        hp1 = [F_(k, 0x160) for k in range(4)]
        for k in range(4):
            st = br.ram[off(P[k] + 0x3715)]; act = U_(k, 0x3818) & 0xFFFF
            holding = U_(k, 0x376C) != 0
            cat = "item" if holding and st in (7, 8) else ("pole" if st == 35 or 0x208 <= act <= 0x20f or act == 0x21f else ("special" if st == 26 else None))
            live = br.ram[off(P[k] + 0x187)] > 1
            if cat and live:
                w = win.setdefault(k, {"cat": cat, "pred": set(), "act": set(), "n": 0})
                w["n"] += 1
                for v in range(4):
                    if v != k and ov(k, v) and (U_(v, 0x12C) & 0xFFFF): w["pred"].add(v)
                for s in spheres(k): radii[cat][round(s[3])] += 1
            if k in win and (not live):
                w = win.pop(k)
                res[w["cat"]][("pred" if w["pred"] else "nopred", "dmg" if w["act"] else "nodmg")] += 1
            if k in win:
                for v in range(4):
                    if v != k and hp1[v] < hp0[v] - 0.01: win[k]["act"].add(v)
        if t % 300 == 0:
            for k in range(4):
                for ad in (A.HEALTH_OBJ[k], A.HEALTH[k], A.HEALTH[k] + 0x30, A.HEALTH[k] + 0x50): wf32(br, ad, 1000.0)
for cat, c in res.items(): print(cat, dict(c), "sphere radii:", radii[cat].most_common(8))
print("DONE"); sys.stdout.flush(); os._exit(0)
