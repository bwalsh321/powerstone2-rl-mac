"""Better eyes, step 2 (Sep 23 2026): per-frame RAM scanner for the four player objects.

capture: boot a hidden libretro instance, load a savestate, snapshot every player object
         (0x3938 bytes each, window starting PLAYER_MAT[k] - 0x400) EVERY FRAME while a
         scripted P2 (the bot's seat) presses attack / jump / throw / grab on a fixed
         cadence and the three COMs fight. Health is refilled every --refill frames by the
         known-good HEALTH_OBJ write so nobody dies and the fight keeps producing hits.
         Records: snaps [F,4,0x3938] u8, health [F,4] f32, pos [F,4,3] f32, the P2 input
         mask per frame, the event list (press / hit) and PNGs at the first events.

analyze: rank byte offsets by how well their changes line up with events:
         HIT   candidates: change within [f-1, f+3] of a health drop in the SAME object,
                           low change rate otherwise, consistent across the four objects.
         PRESS candidates: change within [f, f+3] of a P2 button press, in P2's object.
         ID    candidates: small-integer fields (u8) with 3..64 distinct values, piecewise
                           constant, that change at both press and hit events.
         Prints top tables with value transitions; writes <out>/analysis.txt.

    PYTHONPATH=../sdlarch-rl/p4:. python ram_scan.py capture --core ... --game ... \
        --states states --slot 2 --instance 11 --frames 3600 --out scan/run1
    python ram_scan.py analyze --out scan/run1

No emulator is touched by analyze. Never run capture on an instance id the league uses
(0-9 = actors, 11 = scout/battery video; use 12+ while a battery may run).
"""
import argparse
import json
import os
import struct
import sys
import time

import numpy as np

STATE_NAMES = {0: "idle", 1: "walk", 2: "t2", 4: "jump0", 5: "air", 6: "t6", 7: "attack", 8: "s8", 9: "s9",
               10: "s10", 11: "s11", 12: "s12", 14: "s14", 15: "s15", 16: "s16", 25: "XFORM", 26: "SPECIAL",
               30: "s30", 32: "HIT", 33: "s33", 34: "HITair", 35: "s35"}
PCOL = ["1P-red", "2P-yel", "3P-blu", "4P-grn"]

OBJ_LEN = 0x3938
OBJ_PRE = 0x400                 # window starts this far BEFORE PLAYER_MAT[k]
DC_B, DC_A = 0x2, 0x4
DC_UP, DC_DOWN, DC_LEFT, DC_RIGHT = 0x10, 0x20, 0x40, 0x80
DC_Y, DC_X = 0x200, 0x400
PRESS_NAMES = {DC_X: "attack", DC_A: "jump", DC_Y: "throw", DC_B: "grab"}


# ----------------------------------------------------------------------------- capture
def capture(a):
    import ps2_addr as A
    from flycast_bridge import FlycastBridge, DC_TO_RETRO, N_BUTTONS
    from PIL import Image

    os.makedirs(a.out, exist_ok=True)
    br = FlycastBridge(a.core, a.game, a.states, a.instance)
    emu, ram = br.emu, br.ram
    base = A.RAM_BASE + A.RAM_DELTA
    obj_off = [A.PLAYER_MAT[k] - OBJ_PRE - base for k in range(4)]
    h_off = [A.HEALTH_OBJ[k] - base for k in range(4)]
    mir_off = [[A.HEALTH[k] - base, A.HEALTH[k] + 0x30 - base, A.HEALTH[k] + 0x50 - base] for k in range(4)]
    pos_off = [A.PLAYER_MAT[k] + A.MAT_POS[0] - base for k in range(4)]
    H, W = emu.get_shape()
    fbuf = np.zeros((H, W, 3), np.uint8)
    dict_off = int(a.dict_off, 16) if a.dict_off else None
    dict_seen = {}                   # value -> shots taken
    pool_o = A.POOL_BASE - base
    pool_idx = pool_o + np.arange(A.POOL_SLOTS) * A.POOL_STRIDE
    pool_cls_seen = {}

    def shot(name):
        emu.get_frame(fbuf, W, H)
        Image.fromarray(fbuf[::-1]).save(os.path.join(a.out, name))

    from PIL import ImageDraw
    ov_dir = os.path.join(a.out, "overlay")
    if a.overlay_every:
        os.makedirs(ov_dir, exist_ok=True)
    csv = open(os.path.join(a.out, "frames.csv"), "w")
    csv.write("frame,mask," + ",".join(f"p{k+1}_hp,p{k+1}_state,p{k+1}_stun,p{k+1}_form,p{k+1}_x,p{k+1}_z" for k in range(4))
              + ",nfast,fast1_cls,fast1_spd,fast1_dist,fast2_cls,fast2_spd,fast2_dist,fast3_cls,fast3_spd,fast3_dist\n")
    prev_pool = None                 # (act, cls, pos) of the previous frame for speeds

    def overlay(f, hh, rows, fast):
        emu.get_frame(fbuf, W, H)
        im = Image.fromarray(fbuf[::-1]); dr = ImageDraw.Draw(im)
        dr.rectangle((0, 0, W, 78), fill=(0, 0, 0))
        dr.text((4, 2), f"f{f:05d}  t={f/60:6.2f}s  P2mask={int(mask[f]):#05x}", fill=(255, 255, 255))
        for k in range(4):
            st_, stun_, form_ = rows[k]
            dr.text((4, 14 + 12 * k), f"{PCOL[k]} hp={hh[k]:4.0f} state={st_:2d}:{STATE_NAMES.get(st_, '?'):7s} "
                    f"stun={stun_:2d} form={form_}", fill=(255, 255, 0) if k == 1 else (220, 220, 220))
        dr.text((4, 64), "fast objs: " + ("  ".join(f"{c:#x}@{d:.0f}u {sp:.0f}u/s" for c, sp, d in fast) if fast else "none"),
                fill=(120, 255, 255))
        im.save(os.path.join(ov_dir, f"f{f:05d}.png"))

    def pool_read():
        act = ram[pool_idx + A.POOL_ACTIVE]
        cls = (ram[pool_idx + A.POOL_CLASS].astype(np.uint32)
               | ram[pool_idx + A.POOL_CLASS + 1].astype(np.uint32) << 8
               | ram[pool_idx + A.POOL_CLASS + 2].astype(np.uint32) << 16
               | ram[pool_idx + A.POOL_CLASS + 3].astype(np.uint32) << 24)
        return act, cls

    def set_mask(dc_mask, player):
        m = np.zeros(N_BUTTONS, np.uint8)
        for bit, rid in DC_TO_RETRO.items():
            if dc_mask & bit:
                m[rid] = 1
        emu.set_button_mask(m, player)

    def health():
        return np.array([struct.unpack_from("<f", ram, o)[0] for o in h_off], np.float32)

    def refill():
        packed = np.frombuffer(struct.pack("<f", 1000.0), dtype=np.uint8)
        for k in range(4):
            ram[h_off[k]:h_off[k] + 4] = packed
            for o in mir_off[k]:
                ram[o:o + 4] = packed

    print(f"[scan] instance {a.instance} loading states/slot{a.slot}.state", flush=True)
    br.loadstate(a.slot)
    br.clear_inputs()
    # pre-roll until the match is live (every seat above 100 health and the P2 object moving)
    for _ in range(a.preroll):
        emu.run()
    hp = health()
    print(f"[scan] after pre-roll health={hp.tolist()}", flush=True)

    F = a.frames
    snaps = np.zeros((F, 4, OBJ_LEN), np.uint8)
    hlth = np.zeros((F, 4), np.float32)
    pos = np.zeros((F, 4, 3), np.float32)
    mask = np.zeros(F, np.uint16)
    pact = np.zeros((F, A.POOL_SLOTS), np.uint8)
    pcls = np.zeros((F, A.POOL_SLOTS), np.uint32)
    ppos = np.zeros((F, A.POOL_SLOTS, 3), np.float32)
    events = []                      # (frame, kind, who, detail)
    shots = 0
    # scripted P2 cadence: idle 50, press 6, idle 50, ... cycling the four buttons,
    # plus a 20-frame walk toward the nearest opponent every 4th press so hits land.
    cycle = [DC_X, DC_A, DC_Y, DC_B]
    script = []
    ci = 0
    while len(script) < F:
        script += [0] * a.idle
        btn = cycle[ci % 4]
        script += [btn] * a.hold
        if ci % 4 == 3:
            script += [0] * 10 + [DC_RIGHT if ci % 8 == 3 else DC_LEFT] * 20
        ci += 1
    script = script[:F]
    prev_mask = 0
    prev_h = hp.copy()
    t0 = time.time()
    for f in range(F):
        m = script[f]
        if m != prev_mask:
            set_mask(m, 1)
            if m:
                events.append((f, "press", 1, PRESS_NAMES.get(m, "walk")))
            prev_mask = m
        if a.refill and f and f % a.refill == 0:
            refill()
            events.append((f, "refill", -1, ""))
        emu.run()
        for k in range(4):
            o = obj_off[k]
            snaps[f, k] = ram[o:o + OBJ_LEN]
            pos[f, k] = struct.unpack_from("<fff", ram, pos_off[k])
        hh = health()
        hlth[f] = hh
        mask[f] = m
        if dict_off is not None:
            for k in range(4):
                v = int(snaps[f, k, dict_off])
                if f == 0 or v != int(snaps[f - 1, k, dict_off]):
                    n = dict_seen.get(v, 0)
                    if n < a.dict_shots:
                        dict_seen[v] = n + 1
                        shot(f"state_{v:03d}_p{k+1}_f{f:05d}.png")
                        events.append((f, "state", k, str(v)))
        if a.pool:
            act, cls = pool_read()
            pact[f], pcls[f] = act, cls
            live_i = np.flatnonzero(act == 1)
            if len(live_i):
                for j in live_i:
                    o = int(pool_idx[j])
                    ppos[f, j] = struct.unpack_from("<f", ram, o + A.POOL_POS[0])[0], \
                                 struct.unpack_from("<f", ram, o + A.POOL_POS[1])[0], \
                                 struct.unpack_from("<f", ram, o + A.POOL_POS[2])[0]
                    c = int(cls[j])
                    n = pool_cls_seen.get(c, 0)
                    if n < a.pool_shots and (f == 0 or pact[f - 1, j] != 1 or pcls[f - 1, j] != c):
                        pool_cls_seen[c] = n + 1
                        shot(f"pool_{c:08x}_s{j:03d}_f{f:05d}.png")
                        events.append((f, "pool", int(j), f"{c:#010x}"))
        rows = [(int(snaps[f, k, 0x3685]), int(snaps[f, k, 0x3792]), int(snaps[f, k, 0x368a] & 1)) for k in range(4)]
        fast = []
        if a.pool:
            act, cls = pact[f], pcls[f]
            if prev_pool is not None:
                pa_, pc_, pp_ = prev_pool
                same = (act == 1) & (pa_ == 1) & (cls == pc_)
                dp = ppos[f] - pp_
                spd = np.sqrt((dp ** 2).sum(-1)) * 60.0
                spd[~same] = 0.0
                cand = [j for j in np.flatnonzero(spd >= 700.0)
                        if int(cls[j]) not in A.PROJ_EXCLUDE
                        and not any(lo <= int(cls[j]) < hi for lo, hi in A.PROJ_EXCLUDE_BANDS)]
                bx, bz = pos[f, 1, 0], pos[f, 1, 2]
                fast = sorted(((int(cls[j]), float(spd[j]),
                                float(np.hypot(ppos[f, j, 0] - bx, ppos[f, j, 2] - bz))) for j in cand),
                              key=lambda t: t[2])[:3]
            prev_pool = (act.copy(), cls.copy(), ppos[f].copy())
        csv.write(f"{f},{int(m):#05x}," + ",".join(f"{hh[k]:.0f},{rows[k][0]},{rows[k][1]},{rows[k][2]},{pos[f,k,0]:.0f},{pos[f,k,2]:.0f}" for k in range(4))
                  + f",{len(fast)}," + ",".join(f"{c:#x},{sp:.0f},{d:.0f}" for c, sp, d in fast)
                  + ",,," * (3 - len(fast)) + "\n")
        if a.overlay_every and f % a.overlay_every == 0:
            overlay(f, hh, rows, fast)
        for k in range(4):
            if hh[k] < prev_h[k] - 0.5:
                events.append((f, "hit", k, f"{prev_h[k]:.0f}->{hh[k]:.0f}"))
                if shots < a.shots:
                    emu.get_frame(fbuf, W, H)
                    Image.fromarray(fbuf[::-1]).save(os.path.join(a.out, f"hit_f{f:05d}_p{k+1}.png"))
                    shots += 1
        prev_h = hh
        if f % 600 == 0:
            print(f"[scan] frame {f}/{F} health={hh.astype(int).tolist()} events={len(events)} "
                  f"{time.time()-t0:.0f}s", flush=True)
    set_mask(0, 1)
    csv.close()
    np.savez_compressed(os.path.join(a.out, "snaps.npz"), snaps=snaps, health=hlth, pos=pos, mask=mask,
                        pool_act=pact, pool_cls=pcls, pool_pos=ppos)
    with open(os.path.join(a.out, "events.json"), "w") as fh:
        json.dump({"events": events, "slot": a.slot, "frames": F, "obj_pre": OBJ_PRE,
                   "obj_len": OBJ_LEN, "player_mat": [hex(x) for x in A.PLAYER_MAT]}, fh)
    kinds = {}
    for e in events:
        kinds[e[1]] = kinds.get(e[1], 0) + 1
    print(f"[scan] done {F} frames in {time.time()-t0:.0f}s; events {kinds}; out {a.out}", flush=True)
    try:
        emu.close()
    except Exception:
        pass


# ----------------------------------------------------------------------------- analyze
def _runs(series):
    """Frames where the series changes."""
    return np.flatnonzero(series[1:] != series[:-1]) + 1


def _align(changes, ev_frames, lo, hi):
    """Fraction of events with a change in [f+lo, f+hi]; and the change frames used."""
    if len(ev_frames) == 0:
        return 0.0, 0
    hit = 0
    used = set()
    for f in ev_frames:
        w = changes[(changes >= f + lo) & (changes <= f + hi)]
        if len(w):
            hit += 1
            used.update(w.tolist())
    return hit / len(ev_frames), len(used)


def analyze(a):
    d = np.load(os.path.join(a.out, "snaps.npz"))
    snaps, hlth, mask = d["snaps"], d["health"], d["mask"]
    ev = json.load(open(os.path.join(a.out, "events.json")))["events"]
    F = snaps.shape[0]
    hits = {k: np.array([e[0] for e in ev if e[1] == "hit" and e[2] == k]) for k in range(4)}
    presses = np.array([e[0] for e in ev if e[1] == "press" and e[3] != "walk"])
    refills = np.array([e[0] for e in ev if e[1] == "refill"])
    health_off = 0x400 - 0x330      # HEALTH_OBJ inside the window; excluded (known)
    out = []
    P = print

    def emit(s=""):
        out.append(s); P(s)

    emit(f"frames={F} hits per object={[len(hits[k]) for k in range(4)]} presses={len(presses)} refills={len(refills)}")
    # byte-level change frames per (object, offset)
    ch = snaps[1:] != snaps[:-1]                       # [F-1,4,L] bool
    nchg = ch.sum(axis=0)                              # [4,L]
    # exclude offsets that never change, or change nearly every frame (timers/matrices)
    live = (nchg > 0) & (nchg < F * a.max_rate)
    live[:, health_off:health_off + 4] = False
    emit(f"live offsets per object (0 < change rate < {a.max_rate:.0%}): {live.sum(axis=1).tolist()}")

    # --- HIT candidates: per object, alignment with that object's own health drops
    rows = []
    for o in range(OBJ_LEN):
        if not live[:, o].any():
            continue
        al, cnt, nc = [], [], []
        for k in range(4):
            if len(hits[k]) < a.min_events or not live[k, o]:
                al.append(None); continue
            c = np.flatnonzero(ch[:, k, o]) + 1
            c = c[~np.isin(c, refills) & ~np.isin(c, refills + 1)]
            fr, used = _align(c, hits[k], -1, 3)
            al.append(fr); cnt.append(len(c)); nc.append(len(hits[k]))
        vals = [x for x in al if x is not None]
        if not vals:
            continue
        score = float(np.mean(vals)) * len(vals) / 4.0
        rate = sum(cnt) / max(sum(nc), 1)             # changes per hit event (1.0-3.0 ideal)
        rows.append((score, rate, o, al, cnt))
    rows.sort(key=lambda r: (-r[0], r[1]))
    emit("\n== HIT candidates (offset in window; align = share of the object's own health drops with a "
         "change within [-1,+3] frames, per object P1..P4; chg/hit = change frames per hit)")
    for score, rate, o, al, cnt in rows[:a.top]:
        if score < 0.5:
            break
        emit(f"  +0x{o:04x} score {score:.2f} chg/hit {rate:5.1f}  align " +
             " ".join("  -- " if x is None else f"{x:4.2f}" for x in al) +
             "  " + _describe(snaps, o, hits, refills))

    # --- PRESS candidates: P2 object (k=1) vs scripted presses
    rows = []
    for o in range(OBJ_LEN):
        if not live[1, o]:
            continue
        c = np.flatnonzero(ch[:, 1, o]) + 1
        fr, used = _align(c, presses, 0, 3)
        if fr < 0.5:
            continue
        rows.append((fr, len(c) / max(len(presses), 1), o))
    rows.sort(key=lambda r: (-r[0], r[1]))
    emit("\n== PRESS candidates (P2 object; align = share of scripted presses with a change within [0,+3])")
    for fr, rate, o in rows[:a.top]:
        emit(f"  +0x{o:04x} align {fr:4.2f} chg/press {rate:5.1f}  " + _describe(snaps, o, {1: presses}, refills, k_only=1))

    # --- ID candidates: u8 fields, 3..64 distinct values, piecewise constant, react to both
    rows = []
    for o in range(OBJ_LEN):
        if not live[:, o].any():
            continue
        sc = []
        for k in range(4):
            s = snaps[:, k, o]
            nd = len(np.unique(s))
            if nd < 3 or nd > 64:
                continue
            c = np.flatnonzero(ch[:, k, o]) + 1
            if len(c) == 0 or np.median(np.diff(c)) < 4 if len(c) > 1 else False:
                continue
            fh, _ = _align(c, hits[k], -1, 3) if len(hits[k]) >= a.min_events else (0.0, 0)
            fp, _ = _align(c, presses, 0, 3) if k == 1 else (0.0, 0)
            sc.append((nd, fh, fp))
        if not sc:
            continue
        mh = np.mean([x[1] for x in sc]); mp = max(x[2] for x in sc)
        if mh < 0.4 and mp < 0.4:
            continue
        rows.append((mh + mp, o, sc))
    rows.sort(key=lambda r: -r[0])
    emit("\n== ID candidates (u8, 3-64 distinct values, piecewise constant; per object: distinct/hit-align/press-align)")
    for s, o, sc in rows[:a.top]:
        emit(f"  +0x{o:04x} " + "  ".join(f"[{nd:2d} {fh:.2f} {fp:.2f}]" for nd, fh, fp in sc))
    with open(os.path.join(a.out, "analysis.txt"), "w") as fh:
        fh.write("\n".join(out) + "\n")
    P(f"\nwritten {a.out}/analysis.txt")


def _describe(snaps, o, ev_by_k, refills, k_only=None, n=3):
    """Value transitions around the first n events: idle value -> value after -> frames to revert."""
    parts = []
    for k, evs in ev_by_k.items():
        if k_only is not None and k != k_only:
            continue
        if evs is None or len(evs) == 0:
            continue
        s = snaps[:, k, o].astype(int)
        u16 = (snaps[:, k, o].astype(int) | (snaps[:, k, o + 1].astype(int) << 8)) if o + 1 < OBJ_LEN else s
        desc = []
        for f in evs[:n]:
            f = int(f)
            lo, hi = max(f - 2, 0), min(f + 40, len(s) - 1)
            before = s[lo]
            seg = s[lo:hi]
            idx = np.flatnonzero(seg != before)
            if len(idx) == 0:
                desc.append(f"f{f}:{before}=")
                continue
            after = seg[idx[0]]
            back = np.flatnonzero(seg[idx[0]:] == before)
            rev = int(back[0]) if len(back) else -1
            desc.append(f"f{f}:{before}->{after}" + (f"({rev}f)" if rev >= 0 else "(stays)"))
        parts.append(f"P{k+1} " + " ".join(desc))
    return "; ".join(parts)


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("capture")
    c.add_argument("--core", required=True); c.add_argument("--game", required=True)
    c.add_argument("--states", default="states"); c.add_argument("--slot", type=int, default=2)
    c.add_argument("--instance", type=int, default=12); c.add_argument("--frames", type=int, default=3600)
    c.add_argument("--preroll", type=int, default=300); c.add_argument("--refill", type=int, default=300)
    c.add_argument("--idle", type=int, default=50); c.add_argument("--hold", type=int, default=6)
    c.add_argument("--shots", type=int, default=24); c.add_argument("--out", required=True)
    c.add_argument("--dict-off", default=None, help="hex offset in the object window; PNG on each new value (e.g. 3685)")
    c.add_argument("--dict-shots", type=int, default=2)
    c.add_argument("--pool", action="store_true", help="track the 160-slot entity pool; PNG per new class pointer")
    c.add_argument("--pool-shots", type=int, default=2)
    c.add_argument("--overlay-every", type=int, default=0, help="save an annotated frame every N frames (15 = 4 fps)")
    s_ = sub.add_parser("sheets", help="tile overlay frames into 6x8 contact sheets")
    s_.add_argument("--out", required=True); s_.add_argument("--cols", type=int, default=6); s_.add_argument("--rows", type=int, default=8)
    z = sub.add_parser("analyze")
    z.add_argument("--out", required=True); z.add_argument("--top", type=int, default=30)
    z.add_argument("--max-rate", type=float, default=0.25, help="drop offsets changing more often than this share of frames")
    z.add_argument("--min-events", type=int, default=3)
    a = ap.parse_args()
    if a.cmd == "capture":
        capture(a)
    elif a.cmd == "sheets":
        sheets(a)
    else:
        analyze(a)


def sheets(a):
    import glob
    from PIL import Image
    files = sorted(glob.glob(os.path.join(a.out, "overlay", "f*.png")))
    per = a.cols * a.rows
    tw, th = 480, 360
    n = 0
    for i in range(0, len(files), per):
        chunk = files[i:i + per]
        im = Image.new("RGB", (a.cols * tw, a.rows * th), (0, 0, 0))
        for j, f in enumerate(chunk):
            im.paste(Image.open(f).resize((tw, th)), ((j % a.cols) * tw, (j // a.cols) * th))
        n += 1
        im.save(os.path.join(a.out, f"sheet{n:03d}.png"))
    print(f"{len(files)} overlay frames -> {n} sheets ({a.cols}x{a.rows}, {tw}x{th} tiles) in {a.out}")


if __name__ == "__main__":
    main()
