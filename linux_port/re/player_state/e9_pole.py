"""E9: pole test. Teleport P1 (slot1 desert) next to the tall cactus at ~(66,*,970) and jump into it."""
from harness import *
from flycast_bridge import DC_TO_RETRO
br = boot()
def setm(port, mask):
    m = np.zeros(16, np.uint8)
    for bit, rid in DC_TO_RETRO.items():
        if mask & bit: m[rid] = 1
    br.emu.set_button_mask(m, port)
sd = os.path.join(HERE, "shots/e9"); os.makedirs(sd, exist_ok=True)
for name, (dx, dz, dirmask) in {"fromE": (120, 0, BTN["left"] | BTN["up"]), "fromS": (0, 120, BTN["up"]),
                                "fromE2": (120, 0, BTN["left"]), "fromN": (0, -120, BTN["down"])}.items():
    load(br, os.path.join(HERE, "base_s1.state"))
    place(br, 0, 66 + dx, 0, 970 + dz); br.run_frames(3)
    seq = [dirmask] * 6 + [dirmask | BTN["a"]] * 2 + [dirmask] * 30 + [0] * 30 + [BTN["x"]] * 2 + [0] * 60
    out = []
    for t, m in enumerate(seq):
        setm(0, m); br.emu.run(); r = snap(br)
        b = r[off(P[0]):off(P[0]) + PSTRIDE]
        out.append((b[0x3715], struct.unpack_from("<H", b, 0x3818)[0], [round(v) for v in struct.unpack_from("<3f", b, 0x28)]))
        if t % 6 == 0: shot(br, os.path.join(sd, f"{name}_{t:03d}.png"))
    s = []; prev = None
    for t, (st, act, pos) in enumerate(out):
        if (st, act) != prev: s.append(f"{t}:s{st}/a{act:x}{pos}"); prev = (st, act)
    print(name, " ".join(s))
print("DONE"); sys.stdout.flush(); os._exit(0)
