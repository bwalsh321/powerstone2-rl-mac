"""overlay_v4.py -- VIDEO sanity check of the PROPOSED obs-v4 decode (obs_overlay.py style, drawn on the real game frames).

Plays a savestate headless (instance 8) with a simple scripted P2 (chase the nearest opponent, pick up nearby items,
attack/fire when close; the COMs drive the other seats), and pipes every 2nd emulator frame (30 fps = real time)
straight into ffmpeg (H.264, CRF 28, 640x480; no intermediate PNGs). Drawn on top, from the v4 reader's decode:
  * every player: hurtbox CYLINDER (wire), state name, INV / AIR flags; live HIT SPHERES (red) with frames-active,
    and the attack-startup indicator (P+0x414) with its age;
  * held items: item name on the holder; ground items: item name (the 3 the bot's obs carries are boxed);
  * resting chests: "STONE inside" (gold) or the item name from +0x42C, BEFORE they open;
  * ledger threats (v4): orange = enemy projectile, magenta = thrown object, grey = the bot's own; velocity arrows
    (0.25 s); "v4#k" marks the 3 in the obs. v3 POOL projectile slots (the live contract) in CYAN, for comparison;
  * the bot's 8 free-run rays (spatial block, action frame) in green on the floor;
  * corner HUD: bot's held item + uses fraction, threat / melee / chest summary, frame and time.
World -> screen: RAM camera (eye 0x8C5411A4, back 0x8C541194) + intrinsics fitted by ablation in
calibrate_projection.py (projection.json; held-out median error ~12 px).
Also writes <video>.events.json (timestamps of first chest opening, held items, projectiles, hits) for WATCHLIST.md.
    python re/obs_v4/overlay_v4.py --slot 2 --seconds 75 --out re/obs_v4/videos/slot2_lv3_ffa.mp4
"""
import argparse
import json
import math
import os
import random
import struct
import subprocess
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, "..", "items_held"))
os.environ["PS2_OBS_V3"] = "1"                   # the synth reports the v3 projectile slots (live contract)
import obs_v4_reader as V  # noqa: E402
import test_obs_v4 as T  # noqa: E402
from calibrate_projection import project  # noqa: E402
from items_dict import ITEMS  # noqa: E402

FFMPEG = "/opt/homebrew/bin/ffmpeg" if os.path.exists("/opt/homebrew/bin/ffmpeg") else "ffmpeg"
K = json.load(open(os.path.join(HERE, "projection.json")))["K"]
STATE_NAMES = {0: "idle", 1: "run", 2: "brake", 4: "jumpsq", 5: "air", 6: "land", 7: "ATTACK", 8: "use-item",
               9: "grab?", 10: "pickup", 11: "GRAB", 12: "THROW", 14: "down", 15: "getup", 16: "launched",
               19: "entry", 25: "POWER-CHG", 26: "SPECIAL", 30: "air-catch", 32: "HIT", 33: "follow", 34: "HELD",
               35: "pole", 36: "guard"}
SEATC = {0: (255, 70, 70), 1: (255, 230, 40), 2: (80, 140, 255), 3: (70, 220, 100)}
DPAD = [0x10, 0x20, 0x40, 0x80, 0x10 | 0x40, 0x10 | 0x80, 0x20 | 0x40, 0x20 | 0x80]
RAYN = ["U", "D", "L", "R", "UL", "UR", "DL", "DR"]
try:
    FONT = ImageFont.load_default(size=11)
except TypeError:                                  # Pillow < 10.1: bitmap font, no outline
    FONT = None


class _Draw:
    """ImageDraw with outlined text (readable on any background)."""

    def __init__(self, img):
        self.d = ImageDraw.Draw(img)

    def text(self, xy, s, fill):
        if FONT is not None:
            self.d.text(xy, s, fill=fill, font=FONT, stroke_width=1, stroke_fill=(0, 0, 0))
        else:
            self.d.text(xy, s, fill=fill)

    def __getattr__(self, k):
        return getattr(self.d, k)


def iname(code):
    if code in ITEMS:
        return ITEMS[code][0]
    return {0xC1: "stone", 0xC2: "chest", 0xC3: "cactus", 0xC8: "saguaro"}.get(code, f"#{code:02x}")


def proj(ram, pts):
    uv, ok = project(ram, np.asarray(pts, np.float64), K)
    return uv, ok


class Bot:
    """Scripted P2: chase the nearest opponent; grab a nearby item when empty-handed; attack / use when close."""

    def __init__(self, seed, dirs, chest_until=0.0):
        self.rng = random.Random(seed)
        self.dirs = dirs
        self.chest_until = chest_until            # seconds: open chests first (slot1: the opponent is idle)

    def act(self, S, h, t=0.0):
        me = S["P"][1]
        mx, mz = me["pos"][0], me["pos"][2]
        rest = [c for c in S["chests"] if c[5] == 2]
        if t < self.chest_until and rest and not me["held_code"]:
            c = min(rest, key=lambda q: (q[0] - mx) ** 2 + (q[2] - mz) ** 2)
            vx, vz = c[0] - mx, c[2] - mz
            k = int(np.argmax(self.dirs @ np.array([vx, vz])))
            return 0x400 if math.hypot(vx, vz) < 140 and self.rng.random() < 0.7 else DPAD[k]
        opps = [(math.hypot(S["P"][j]["pos"][0] - mx, S["P"][j]["pos"][2] - mz), j) for j in (0, 2, 3) if h[j] > 1]
        tgt, d = None, 1e9
        if opps:
            d, j = min(opps)
            tgt = S["P"][j]["pos"]
        if not me["held_code"] and S["items"]:
            it = min(S["items"], key=lambda q: (q[0] - mx) ** 2 + (q[2] - mz) ** 2)
            di = math.hypot(it[0] - mx, it[2] - mz)
            if di < 500 and it[3]:
                if di < 90:
                    return 0x002                                  # B: pick up
                tgt, d = (it[0], 0, it[2]), 1e9
        if tgt is None:
            return 0
        vx, vz = tgt[0] - mx, tgt[2] - mz
        k = int(np.argmax(self.dirs @ np.array([vx, vz])))
        r = self.rng.random()
        if me["held_code"] and d < 700 and r < 0.35:
            return 0x400                                          # use / fire the item
        if d < 200:
            return 0x400 if r < 0.7 else (0x002 if r < 0.85 else DPAD[k] | 0x004)
        if r < 0.06:
            return DPAD[k] | 0x004                                # jump towards
        return DPAD[k]


def cyl_lines(ram, cyl):
    cx, cy, cz, R, H = cyl
    a = np.linspace(0, 2 * np.pi, 13)
    out = []
    for yy in (cy - H, cy + H):
        pts = np.stack([cx + R * np.cos(a), np.full_like(a, yy), cz + R * np.sin(a)], 1)
        uv, ok = proj(ram, pts)
        if ok.all():
            out.append([tuple(p) for p in uv])
    return out


def draw(img, ram, S, vec, info, synth, sg_dirs, t_sec, frame_no, slot):
    d = _Draw(img)
    P = S["P"]
    me = P[1]
    # --- rays (spatial block, from the bot, on its floor plane)
    rays = vec[V.H_SPATIAL:V.H_SPATIAL + 8] * 1000.0
    o = np.array([me["pos"][0], me["pos"][1], me["pos"][2]])
    for k in range(8):
        e = o + np.array([sg_dirs[k, 0] * rays[k], 0.0, sg_dirs[k, 1] * rays[k]])
        uv, ok = proj(ram, [o, e])
        if ok.all():
            d.line([tuple(uv[0]), tuple(uv[1])], fill=(60, 230, 60), width=1)
            d.text((uv[1][0] + 2, uv[1][1] - 6), f"{RAYN[k]}{rays[k]:.0f}", fill=(60, 230, 60))
    # --- chests (content BEFORE opening) and ground items
    obs_items = set()
    for i in range(V.N_ITEM):
        b = V.C_GROUND + 10 * i
        if vec[b]:
            obs_items.add((round(vec[b + 1] * 1000 + o[0]), round(vec[b + 2] * 1000 + o[2])))
    for (x, y, z, stone, content, st) in S["chests"]:
        uv, ok = proj(ram, [(x, y + 60, z)])
        if ok[0]:
            lab = "STONE inside" if stone else (iname(content) if content else "(empty)")
            if st == 9:
                lab = "OPENING: " + lab
            d.text((uv[0][0] - 25, uv[0][1] - 18), lab, fill=(255, 210, 0) if stone else (230, 160, 90))
    v3st = []                                   # the live contract's 6 stone slots (STATE line, OBJ_GRID_N = 110)
    sc = getattr(synth, "_stone_cache", "")
    vals = [float(q) for q in sc.split(",")] if sc else []
    for k in range(len(vals) // 3):
        if vals[3 * k] or vals[3 * k + 1]:
            v3st.append((vals[3 * k], vals[3 * k + 1]))
    for (x, y, z, idx, st) in S["stones"]:
        uv, ok = proj(ram, [(x, y + 40, z)])
        if not ok[0]:
            continue
        slot3 = [k for k, (sx, sz) in enumerate(v3st) if abs(sx - x) < 70.0 and abs(sz - z) < 70.0]
        tag = f"v3#{slot3[0]}" if slot3 else ("208-only (idx %d)" % idx if idx >= 110 else "not in v3 (>6)")
        d.ellipse((uv[0][0] - 6, uv[0][1] - 6, uv[0][0] + 6, uv[0][1] + 6), outline=(255, 215, 0), width=2)
        d.text((uv[0][0] + 8, uv[0][1] - 8), f"STONE {tag}", fill=(255, 215, 0) if slot3 else (255, 120, 0))
    for (x, y, z, ready, gcls, t) in S["items"]:
        uv, ok = proj(ram, [(x, y + 45, z)])
        if ok[0]:
            boxed = (round(x), round(z)) in obs_items
            col = (120, 255, 255) if ready else (120, 180, 180)
            if boxed:
                d.rectangle((uv[0][0] - 5, uv[0][1] - 5, uv[0][0] + 5, uv[0][1] + 5), outline=col)
            d.text((uv[0][0] + 6, uv[0][1] - 6), iname(t) + ("" if ready else "~"), fill=col)
    # --- players: hurt cylinder, spheres, labels, held item
    for j in range(4):
        p = P[j]
        if struct.unpack_from("<I", ram, 0x472DA8 + 0x14 * j + 0x10)[0] == 0:
            continue                                   # empty seat (1v1 states keep a stale struct)
        for poly in cyl_lines(ram, p["cyl"]):
            d.line(poly, fill=SEATC[j], width=1)
        for x, y, z, r in p["spheres"]:
            uv, ok = proj(ram, [(x, y, z)])
            c = (x, y, z)
            if ok[0]:
                zc = max(1.0, float(np.dot(np.array(c) - np.array(struct.unpack_from("<3f", ram, 0x5411A4)),
                                           -np.array(struct.unpack_from("<3f", ram, 0x541194)))))
                rp = max(3.0, K["fx"] * r / zc)
                d.ellipse((uv[0][0] - rp, uv[0][1] - rp, uv[0][0] + rp, uv[0][1] + rp), outline=(255, 30, 30), width=2)
        head, ok = proj(ram, [(p["pos"][0], p["pos"][1] + 2 * p["cyl"][4] + 40, p["pos"][2])])
        if not ok[0]:
            continue
        hx, hy = head[0]
        flags = ("INV " if p["invuln"] else "") + ("AIR" if p["airborne"] else "")
        lines = [f"P{j + 1} {STATE_NAMES.get(p['state'], 's%d' % p['state'])} {flags}"]
        if len(p["spheres"]):
            lines.append(f"HIT x{len(p['spheres'])} {p['hit_age']}f")
        if p["atk414"]:
            lines.append(f"startup {p['atk_age']}f")
        if p["item_swing"]:
            lines.append("ITEM SWING (blade spheres)")
        if p["held_code"]:
            hc = p["held_code"]
            init = V.ITEM_CLS.get(hc, (0, 0, 0))[2]
            lines.append(f"[{iname(hc)}" + (f" {p['held_uses']}/{init}]" if init else "]"))
        for i, ln in enumerate(lines):
            col = (255, 60, 60) if ln.startswith(("HIT", "startup", "ITEM SWING")) else (120, 255, 255) if ln.startswith("[") \
                else SEATC[j]
            d.text((hx - 30, hy - 12 * (len(lines) - i)), ln, fill=col)
    # --- threats: v4 ledger (all; the obs's 3 marked) and v3 pool slots (cyan)
    obs_thr = []
    for t in range(V.N_THREAT):
        b = V.B_THREAT + 11 * t
        if vec[b]:
            obs_thr.append((vec[b + 1] * 1000 + o[0], vec[b + 3] * 1000 + o[2]))
    for (x, y, z, vx, vy, vz, rr, thrown, owner, vtj) in S["threats"]:
        uv, ok = proj(ram, [(x, y, z), (x + vx * 0.25, y + vy * 0.25, z + vz * 0.25)])
        if not ok.all():
            continue
        col = (150, 150, 150) if owner == 1 else ((255, 60, 255) if thrown else (255, 150, 30))
        d.line([tuple(uv[0]), tuple(uv[1])], fill=col, width=2)
        d.ellipse((uv[0][0] - 4, uv[0][1] - 4, uv[0][0] + 4, uv[0][1] + 4), fill=col)
        for k, (ox, oz) in enumerate(obs_thr):
            if abs(ox - x) < 6 and abs(oz - z) < 6:
                d.text((uv[0][0] + 5, uv[0][1] + 3), f"v4#{k}", fill=col)
    for k, (x, y, z, vx, vz) in enumerate(getattr(synth, "_proj_cache", [])[:3]):
        uv, ok = proj(ram, [(x, y, z), (x + vx * 0.25, y, z + vz * 0.25)])
        if ok.all():
            d.rectangle((uv[0][0] - 5, uv[0][1] - 5, uv[0][0] + 5, uv[0][1] + 5), outline=(0, 255, 255), width=2)
            d.line([tuple(uv[0]), tuple(uv[1])], fill=(0, 255, 255), width=1)
            d.text((uv[0][0] - 20, uv[0][1] + 6), f"v3#{k}", fill=(0, 255, 255))
    # --- corner HUD (bot)
    bd = V.D_HELD
    hc = me["held_code"]
    held = f"{iname(hc)}  uses {vec[bd + 5]:.2f}" if hc else "(empty hands)"
    nthr = sum(1 for t in range(3) if vec[V.B_THREAT + 11 * t])
    mel = " ".join(f"o{k}:{'HIT' if vec[V.A_MELEE + V.A_OPP_W * k] else '-'}{'/su' if vec[V.A_MELEE + V.A_OPP_W * k + 7] else ''}"
                   f"(m{vec[V.A_MELEE + V.A_OPP_W * k + 5] * 200:.0f})" for k in range(3))
    hud = [f"obs-v4 overlay  slot{slot}  t={t_sec:5.1f}s  f{frame_no}",
           f"BOT P2 held: {held}",
           f"v4 threats {nthr} (crowd {vec[V.B_THREAT + 33] * 5:.0f})  chests: " +
           " ".join(("STONE" if vec[V.C_GROUND + 38 + 5 * i] else "item") for i in range(2) if vec[V.C_GROUND + 34 + 5 * i]),
           f"melee {mel}",
           f"stones: {len(S['stones'])} loose ({sum(1 for q in S['stones'] if q[3] >= 110)} only visible at OBJ_GRID_N=208)",
           "orange=v4 proj  magenta=v4 thrown  grey=own (not in obs)  cyan=v3 pool slots  green=free-run rays"]
    d.rectangle((0, 0, 400, 13 * len(hud) + 4), fill=(0, 0, 0))
    for i, ln in enumerate(hud):
        d.text((3, 2 + 13 * i), ln, fill=(255, 255, 0) if i == 1 else (230, 230, 230))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--slot", type=int, default=2)
    ap.add_argument("--seconds", type=float, default=75.0)
    ap.add_argument("--warmup", type=int, default=0, help="emulator frames to skip before recording")
    ap.add_argument("--out", required=True)
    ap.add_argument("--crf", type=int, default=28)
    ap.add_argument("--chests-first", type=float, default=0.0, help="seconds the bot spends opening chests first")
    a = ap.parse_args()
    os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)
    from ps2_ram import StateLineSynth
    br = T.boot()
    synth = StateLineSynth(br.ram, bot_player=2)
    br.attach_synth(synth)
    T.load(br, a.slot)
    synth.on_loadstate()
    rd = V.ObsV4Reader(br.ram)
    sg_dirs = rd._sg.maps[5].dirs
    bot = Bot(100 + a.slot, sg_dirs, a.chests_first)
    Hh, Ww = br.emu.get_shape()
    buf = np.zeros((Hh, Ww, 3), np.uint8)
    ff = subprocess.Popen([FFMPEG, "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", "640x480",
                           "-r", "30", "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", str(a.crf),
                           "-pix_fmt", "yuv420p", "-movflags", "+faststart", a.out], stdin=subprocess.PIPE)
    events = {"stone": [], "stone_208_only": [], "own_bullet_excluded": [], "item_swing_contact": [], "chest_open": [], "held": [], "bot_held": [], "projectile": [], "thrown": [], "hit": [],
              "stone_chest_seen": []}
    seen_open, seen_held, prev_h, mask = set(), set(), None, 0
    total = a.warmup + int(a.seconds * 60)
    for fr in range(1, total + 1):
        if fr % 6 == 1:
            mask = bot.act(rd.scan(fr - 1), T.health(br.ram), max(0.0, (fr - a.warmup) / 60.0))   # pre-press state
        br.press(mask, 1, player=1)
        if fr <= a.warmup:
            continue
        t_sec = (fr - a.warmup) / 60.0
        h = T.health(br.ram)
        S = rd.scan(fr)
        vec, info = rd.features(1, T.opp_order(S["P"], 1, h), fr)
        # ---- events for the watchlist
        for (x, y, z, stone, content, st) in S["chests"]:
            key = (round(x / 50), round(z / 50))
            if st == 9 and key not in seen_open:
                seen_open.add(key)
                events["chest_open"].append((round(t_sec, 1), "STONE" if stone else iname(content)))
            if st == 2 and stone and len(events["stone_chest_seen"]) < 1:
                events["stone_chest_seen"].append((round(t_sec, 1), f"chest at ({x:.0f},{z:.0f})"))
        if S["stones"] and (not events["stone"] or t_sec - events["stone"][-1][0] > 10):
            events["stone"].append((round(t_sec, 1), f"{len(S['stones'])} loose stone(s)"))
        if any(q[3] >= 110 for q in S["stones"]) and (not events["stone_208_only"] or t_sec - events["stone_208_only"][-1][0] > 10):
            events["stone_208_only"].append((round(t_sec, 1), "stone at ledger idx >= 110 (missed by v3)"))
        for (x, y, z, vx, vy, vz, rr, thrown, owner, vtj) in S["threats"]:
            if owner == 1 and 0x0C162000 <= vtj < 0x0C16D000 and vtj not in V.SELF_HARM_VT and \
                    (not events["own_bullet_excluded"] or t_sec - events["own_bullet_excluded"][-1][0] > 3):
                events["own_bullet_excluded"].append((round(t_sec, 1), f"P2's own item bullet vt {vtj:#x} (grey, not in obs)"))
        for kk in range(3):
            b = V.A_MELEE + V.A_OPP_W * kk
            if vec[b + 10] and vec[b + 5] <= 0 and (not events["item_swing_contact"] or t_sec - events["item_swing_contact"][-1][0] > 3):
                events["item_swing_contact"].append((round(t_sec, 1), f"opp{kk} item swing in contact (margin {vec[b + 5] * 200:.0f})"))
        if vec[V.A_MELEE + V.A_OPP_W * 3 + 3] and (not events["item_swing_contact"] or t_sec - events["item_swing_contact"][-1][0] > 3):
            events["item_swing_contact"].append((round(t_sec, 1), "BOT swings its item"))
        for j in range(4):
            c = S["P"][j]["held_code"]
            if c and (j, c) not in seen_held:
                seen_held.add((j, c))
                events["bot_held" if j == 1 else "held"].append((round(t_sec, 1), f"P{j + 1} {iname(c)}"))
        if vec[V.B_THREAT] and (not events["projectile"] or t_sec - events["projectile"][-1][0] > 5):
            kind = "thrown" if vec[V.B_THREAT + 8] else "projectile"
            events[kind].append((round(t_sec, 1), f"{kind} at {vec[V.B_THREAT + 1] * 1000:.0f},{vec[V.B_THREAT + 3] * 1000:.0f} from P2"))
        if prev_h is not None:
            for j in range(4):
                if prev_h[j] - h[j] > 5 and prev_h[j] > 1:
                    src = rd._hit_source(j)
                    events["hit"].append((round(t_sec, 1), f"P{j + 1} -{prev_h[j] - h[j]:.0f}"
                                          + (f" by P{src + 1}" if src is not None else "")))
        prev_h = h
        if fr % 2:
            continue
        br.emu.get_frame(buf, Ww, Hh)
        img = Image.fromarray(buf[::-1].copy())          # frames come vertically flipped
        if img.size != (640, 480):
            img = img.resize((640, 480))
        draw(img, br.ram, S, vec, info, synth, sg_dirs, t_sec, fr, a.slot)
        ff.stdin.write(img.tobytes())
    ff.stdin.close()
    ff.wait()
    for k in events:
        events[k] = events[k][:12]
    with open(os.path.splitext(a.out)[0] + ".events.json", "w") as f:
        json.dump(events, f, indent=1)
    print(f"[overlay_v4] {a.out}: {total - a.warmup} frames, {os.path.getsize(a.out) / 1e6:.1f} MB; "
          f"events {[(k, len(v)) for k, v in events.items()]}", flush=True)
    os._exit(0)


if __name__ == "__main__":
    main()
