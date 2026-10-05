"""E7 census: long 4-player run (slot2/slot3 COMs + random-but-aggressive inputs on ports 0/1),
record every player struct every frame, screenshot the first 3 occurrences of every new
(player state byte P+0x3715) and every new action word (P+0x3818) with an overlay.
usage: e7_census.py SLOT FRAMES TAG [--refill N] [--idle]"""
import argparse, random
from harness import *
from PIL import Image, ImageDraw
ap = argparse.ArgumentParser(); ap.add_argument("slot"); ap.add_argument("frames", type=int); ap.add_argument("tag")
ap.add_argument("--refill", type=int, default=0); ap.add_argument("--idle", action="store_true")
ap.add_argument("--seed", type=int, default=1)
a = ap.parse_args(); random.seed(a.seed)
br = boot(); load(br, f"states/slot{a.slot}.state")
sd = os.path.join(HERE, "shots", "census_" + a.tag); os.makedirs(sd, exist_ok=True)
N = a.frames
mm = np.lib.format.open_memmap(os.path.join(HERE, f"data_census_{a.tag}.npy"), "w+", np.uint8, (N, 4, PSTRIDE))
masks = np.zeros((N, 2), np.uint16)
from flycast_bridge import DC_TO_RETRO
def setm(port, mask):
    m = np.zeros(16, np.uint8)
    for bit, rid in DC_TO_RETRO.items():
        if mask & bit: m[rid] = 1
    br.emu.set_button_mask(m, port)
seen_s, seen_a = {}, {}
H, W = br.emu.get_shape(); fb = np.zeros((H, W, 3), np.uint8)
def overlay(t, i, what):
    br.emu.get_frame(fb, W, H); im = Image.fromarray(fb[::-1].copy()); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W, 14), fill=(0, 0, 0))
    d.text((3, 1), f"f{t} P{i+1} {what}", fill=(255, 255, 0)); return im
cur = [0, 0]; left = [0, 0]
BTNS = [0, BTN["x"], BTN["a"], BTN["b"], BTN["y"], BTN["x"] | BTN["a"], BTN["a"] | BTN["b"], BTN["x"] | BTN["b"] | BTN["a"]]
DIRS = [0, BTN["up"], BTN["down"], BTN["left"], BTN["right"], BTN["up"] | BTN["left"], BTN["down"] | BTN["right"]]
for t in range(N):
    for port in (0, 1):
        if a.idle: break
        if left[port] <= 0:
            cur[port] = random.choice(DIRS) | (random.choice(BTNS) if random.random() < 0.5 else 0)
            left[port] = random.randint(2, 25)
        left[port] -= 1; setm(port, cur[port]); masks[t, port] = cur[port]
    br.emu.run()
    for i in range(4):
        mm[t, i] = br.ram[off(P[i]):off(P[i]) + PSTRIDE]
    if a.refill and t % a.refill == 0:
        for i in range(4):
            for ad in (A.HEALTH_OBJ[i], A.HEALTH[i], A.HEALTH[i] + 0x30, A.HEALTH[i] + 0x50):
                wf32(br, ad, 1000.0)
    for i in range(4):
        s = int(mm[t, i, 0x3715]); act = struct.unpack_from("<H", mm[t, i], 0x3818)[0]
        for dct, key, lbl in ((seen_s, s, f"state={s}"), (seen_a, act, f"act={act:04x} state={s}")):
            n = dct.get(key, 0)
            if n < 3 and (n == 0 or t - dct.get(("t", key), -999) > 120):
                im = overlay(t, i, lbl)
                im.save(os.path.join(sd, f"{'s' if dct is seen_s else 'a'}_{key:04x}_{n}_f{t}_P{i+1}.png"))
                dct[key] = n + 1; dct[("t", key)] = t
mm.flush(); np.save(os.path.join(HERE, f"data_census_{a.tag}_masks.npy"), masks)
print("states seen:", sorted(k for k in seen_s if not isinstance(k, tuple)))
print("acts seen:", [hex(k) for k in sorted(k for k in seen_a if not isinstance(k, tuple))])
print("DONE"); sys.stdout.flush(); os._exit(0)
