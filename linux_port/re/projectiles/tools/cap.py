"""cap.py -- per-frame capture of everything a projectile could live in (instance 4 by default).

Records per frame (npz + memmaps in --out):
  hp[4] f32 (HEALTH_OBJ), st[4] u8 (PLAYER_MAT+0x3285), pos[4,3], hsrc[4] u32 (PLAYER_MAT+0x32E4, physical ptr)
  pool: act u32 / cls u32 / pos f32  [160]
  ledger.npy (memmap)  [F, NL, LB] u8 : raw bytes of ledger slots from LEDGER_LO, stride 0x430
  pobj.npy  (optional) [F, 4, 0x3938] u8 : player objects (PLAYER_MAT-0x490 ..)
  jpg/fNNNNN.jpg every --shot-every frames (upright, 320x240)
Health refilled every --refill frames (HEALTH_OBJ + mirrors), so the fight never ends.
Optional --p2 script: "frame:mask:hold;..." DC masks for port B (e.g. "60:0x400:6") or --p2-cycle.
"""
import argparse, gzip, os, struct, sys, time
import numpy as np
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../.."))
sys.path.insert(0, ROOT)
import ps2_addr as A
from flycast_bridge import FlycastBridge, DC_TO_RETRO, N_BUTTONS

LEDGER_LO = 0x8C4FBD30
LSTRIDE = 0x430


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--load", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--frames", type=int, default=5400)
    ap.add_argument("--instance", type=int, default=4)
    ap.add_argument("--nl", type=int, default=150)
    ap.add_argument("--lb", type=int, default=0x100)
    ap.add_argument("--pobj", action="store_true")
    ap.add_argument("--shot-every", type=int, default=3)
    ap.add_argument("--refill", type=int, default=240)
    ap.add_argument("--p2", default="", help="'start:mask:hold:period' repeated events, ';' separated")
    a = ap.parse_args()
    os.makedirs(os.path.join(a.out, "jpg"), exist_ok=True)
    core = os.path.expanduser("~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib")
    game = os.path.join(ROOT, "../Power Stone 2 (USA).chd")
    br = FlycastBridge(core, game, os.path.join(ROOT, "states"), instance_id=a.instance)
    emu, ram = br.emu, br.ram
    br.run_frames(8)
    with gzip.open(a.load, "rb") as f:
        emu.set_state(f.read())
    br.run_frames(4)
    base = A.RAM_BASE + A.RAM_DELTA
    F = a.frames
    h_off = [x - base for x in A.HEALTH_OBJ]
    mir = [[A.HEALTH[k] - base, A.HEALTH[k] + 0x30 - base, A.HEALTH[k] + 0x50 - base] for k in range(4)]
    pm = [x - base for x in A.PLAYER_MAT]
    pidx = (A.POOL_BASE - base) + np.arange(A.POOL_SLOTS) * A.POOL_STRIDE
    lo = LEDGER_LO - base
    led = np.zeros((F, a.nl, a.lb), np.uint8)   # kept in RAM, saved compressed (disk is tight)
    pob = np.zeros((F, 4, 0x3938), np.uint8) if a.pobj else None
    hp = np.zeros((F, 4), np.float32); st = np.zeros((F, 4), np.uint8); pos = np.zeros((F, 4, 3), np.float32)
    hsrc = np.zeros((F, 4), np.uint32); mask = np.zeros(F, np.uint16)
    pact = np.zeros((F, A.POOL_SLOTS), np.uint32); pcls = np.zeros((F, A.POOL_SLOTS), np.uint32)
    ppos = np.zeros((F, A.POOL_SLOTS, 3), np.float32)
    lidx = lo + np.arange(a.nl)[:, None] * LSTRIDE + np.arange(a.lb)[None, :]
    H, W = emu.get_shape(); fbuf = np.zeros((H, W, 3), np.uint8)
    from PIL import Image
    packed = np.frombuffer(struct.pack("<f", 1000.0), np.uint8)
    ev = []
    for e in filter(None, a.p2.split(";")):
        s0, m, hold, per = e.split(":")
        ev.append((int(s0), int(m, 0), int(hold), int(per)))
    p2m = np.zeros(F, np.uint16)
    for s0, m, hold, per in ev:
        for t in range(s0, F, per if per > 0 else F + 1):
            p2m[t:t + hold] |= m
    prev = -1
    t0 = time.time()

    def u32v(offs):
        b = ram[offs[:, None] + np.arange(4)[None, :]].astype(np.uint32)
        return b[:, 0] | b[:, 1] << 8 | b[:, 2] << 16 | b[:, 3] << 24

    for f in range(F):
        m = int(p2m[f])
        if m != prev:
            mm = np.zeros(N_BUTTONS, np.uint8)
            for bit, rid in DC_TO_RETRO.items():
                if m & bit:
                    mm[rid] = 1
            emu.set_button_mask(mm, 1); prev = m
        if a.refill and f and f % a.refill == 0:
            for k in range(4):
                for o in [h_off[k]] + mir[k]:
                    ram[o:o + 4] = packed
        emu.run()
        mask[f] = m
        for k in range(4):
            hp[f, k] = struct.unpack_from("<f", ram, h_off[k])[0]
            st[f, k] = ram[pm[k] + 0x3285]
            pos[f, k] = struct.unpack_from("<fff", ram, pm[k] + 0x30)
            hsrc[f, k] = struct.unpack_from("<I", ram, pm[k] + 0x32E4)[0]
            if pob is not None:
                o = pm[k] - 0x490
                pob[f, k] = ram[o:o + 0x3938]
        pact[f] = u32v(pidx + A.POOL_ACTIVE); pcls[f] = u32v(pidx + A.POOL_CLASS)
        for i in range(3):
            ppos[f, :, i] = u32v(pidx + A.POOL_POS[i]).view(np.float32)
        led[f] = ram[lidx]
        if a.shot_every and f % a.shot_every == 0:
            emu.get_frame(fbuf, W, H)
            Image.fromarray(fbuf[::-1]).resize((320, 240)).save(os.path.join(a.out, "jpg", f"f{f:05d}.jpg"), quality=70)
        if f % 600 == 0:
            print(f"[cap] {f}/{F} hp={hp[f].astype(int).tolist()} st={st[f].tolist()} {time.time()-t0:.0f}s", flush=True)
    np.savez_compressed(os.path.join(a.out, "ledger.npz"), ledger=led)
    if pob is not None:
        np.savez_compressed(os.path.join(a.out, "pobj.npz"), pobj=pob)
    np.savez_compressed(os.path.join(a.out, "cap.npz"), hp=hp, st=st, pos=pos, hsrc=hsrc, mask=mask,
                        pact=pact, pcls=pcls, ppos=ppos, ledger_lo=LEDGER_LO, lstride=LSTRIDE)
    print(f"[cap] done {F} frames {time.time()-t0:.0f}s -> {a.out}", flush=True)
    emu.close()


if __name__ == "__main__":
    main()
