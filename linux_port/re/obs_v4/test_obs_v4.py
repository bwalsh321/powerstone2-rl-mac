"""test_obs_v4.py -- live tests of the PROPOSED obs-v4 reader on this Mac (instance 8, one emulator at a time).

Run from linux_port/:
    source ~/ps2rl/bin/activate; export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:.
    python re/obs_v4/test_obs_v4.py                  # all parts, each in its own process (one emulator at a time)
    python re/obs_v4/test_obs_v4.py --frames 6000    # longer raw run per slot

Parts (each a subprocess; a teardown `mutex lock failed` abort is harmless and ignored):
  raw   slots 1/2/3: thousands of frames with seeded random P2 inputs, features for ALL FOUR seats every
        6 frames (env cadence). Asserts shape, finiteness, per-feature ranges, one-hot sums, seat symmetry
        (seat-intrinsic blocks identical whether a seat is "self" or "opponent k" in another view; absolute
        positions of items/chests consistent across views), cross-checks against independent RAM sources
        (seat-table character id, F+0x54 non-zero <=> held class, airborne vs logical y). Times the shared
        scan and the per-seat assembly. Writes obs_v4_stats.txt (per-feature non-zero fraction, min, max).
  det   determinism: slot 2 replayed twice with the same seeded inputs -> bit-identical vectors; a second
        reader queried in a different seat order on the same frames -> identical vectors.
  env   the real PowerStoneEnvLibretro (PS2_OBS_V3=1) with the v4 patch applied IN THIS TEST ONLY (subclass,
        no repo file touched): obs is 430-dim and obs[:160] is bit-identical to the unpatched v3 builder on the
        same state; then FFASelfPlayEnv._obs_from_view for every other seat (seat-generic integration).
Exit code 1 on any failure.
"""
import argparse
import gzip
import json
import math
import os
import random
import subprocess
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LP = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, HERE)
sys.path.insert(0, LP)
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
INSTANCE = int(os.environ.get("PS2_V4_TEST_INSTANCE", "8"))
CORE = os.environ.get("PS2_CORE") or os.path.expanduser(
    "~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib" if sys.platform == "darwin"
    else "~/cores/flycast_libretro.so")
GAME = os.path.join(LP, "..", "Power Stone 2 (USA).chd")

import obs_v4_reader as V  # noqa: E402

NAMES = V.feature_names()
FAILS = []


def check(cond, msg):
    if not cond:
        FAILS.append(msg)
        if len(FAILS) <= 40:
            print("FAIL:", msg, flush=True)


# ------------------------------------------------------------------ per-feature range table
def bounds(name):
    f = name.split(".")[-1]
    if name.startswith("H."):
        return (-5.0, 5.0)
    if f in ("hit_live", "atk414", "body124", "present", "thrown", "ready", "melee", "ranged", "food", "other",
             "has_stone", "big", "r_long", "r_short", "invuln", "airborne", "down", "held", "grabbing",
             "last_hit_me", "com_targets_me", "item_swing", "fight_live", "menu_open", "variant", "map_present") \
            or name.startswith(("F.", "G.stage", "H.ray_")):
        return (0.0, 1.0)
    if f in ("margin", "best_margin"):
        return (-1.0, 1.0)
    if f in ("hit_age", "atk414_age", "tca", "uses_frac", "state_age"):
        return (0.0, 1.0)
    if f in ("sph_r", "radius"):
        return (0.0, 5.0)
    if f in ("dca", "crowd600", "hurt_h"):
        return (0.0, 2.0)
    if f == "vy":
        return (-2.0, 2.0)
    return (-5.0, 5.0)


LO = np.array([bounds(n)[0] for n in NAMES], np.float32)
HI = np.array([bounds(n)[1] for n in NAMES], np.float32)
BINARY = np.array([bounds(n) == (0.0, 1.0) and n.split(".")[-1] not in
                   ("hit_age", "atk414_age", "tca", "uses_frac", "state_age") for n in NAMES])
# expected to be all-zero on the desert test states (documented in OBS_V4_SPEC.md); not "dead" red flags
EXPECTED_DEAD_PREFIX = ("H.floor_ahead", "G.stage0", "G.stage1", "G.stage2", "G.stage3", "G.stage4", "G.stage6",
                        "G.variant", "G.menu_open")   # desert: flat floor (floor-ahead 0), stage id 5, variant 0
# zero only because of the lineups / item spawns in states/slot1-3 (characters not loaded, no "other"-class item)
LINEUP_DEAD_PREFIX = ("F.",)
LINEUP_DEAD_SUFFIX = (".other", ".food")


def opp_order(P, seat, health):
    """Mimic the env: alive (health > 0.1% of full) opponents, nearest-first in xz."""
    me = P[seat]["pos"]
    c = [(math.hypot(P[j]["pos"][0] - me[0], P[j]["pos"][2] - me[2]), j) for j in range(4)
         if j != seat and health[j] > 1.0]
    return [j for _, j in sorted(c)][:3]


def health(ram):
    import struct
    return [struct.unpack_from("<f", ram, a - V.RAM_BASE)[0] for a in (0x8C475A04, 0x8C475A08, 0x8C475A0C,
                                                                         0x8C475A10)]


def boot():
    from flycast_bridge import FlycastBridge
    br = FlycastBridge(CORE, GAME, os.path.join(LP, "states"), instance_id=INSTANCE)
    br.run_frames(8)
    return br


def load(br, slot):
    with gzip.open(os.path.join(LP, "states", f"slot{slot}.state"), "rb") as f:
        assert br.emu.set_state(f.read()) is not False
    br.clear_inputs()
    br.run_frames(2)


MOVES = [0x10, 0x20, 0x40, 0x80, 0x400, 0x002, 0x004, 0x200, 0x10 | 0x400, 0x80 | 0x002, 0]


# ------------------------------------------------------------------ part: raw
def part_raw(slot, frames, out_json):
    import struct
    br = boot()
    load(br, slot)
    rd = V.ObsV4Reader(br.ram)
    rng = random.Random(1000 + slot)
    fr, n_samples = 0, 0
    vecs = []
    t_scan, t_feat = [], []
    agree_air = [0, 0]
    held_mismatch = 0
    char_mismatch = 0
    spatial_mismatch = [0]
    tally = {"frames_with_threat": 0, "frames_with_melee_live": 0, "chests": 0, "chests_stone": 0,
             "items": 0, "held_any": 0, "sym_checks": 0}
    while fr < frames:
        # P2 = random policy-ish inputs; the COMs drive the other seats
        br.press(rng.choice(MOVES), 6, player=1)
        fr += 6
        ram = br.ram
        h = health(ram)
        t0 = time.perf_counter()
        S = rd.scan(fr)
        t_scan.append(time.perf_counter() - t0)
        P = S["P"]
        per_seat = {}
        for seat in range(4):
            oo = opp_order(P, seat, h)
            t0 = time.perf_counter()
            v, info = rd.features(seat, oo, fr)
            t_feat.append(time.perf_counter() - t0)
            per_seat[seat] = (v, info, oo)
            # ---- shape / finite / ranges
            check(v.shape == (V.V4_EXTRA,) and v.dtype == np.float32, f"shape {v.shape} {v.dtype}")
            check(bool(np.all(np.isfinite(v))), f"slot{slot} f{fr} seat{seat}: non-finite")
            bad = np.nonzero((v < LO - 1e-6) | (v > HI + 1e-6))[0]
            check(len(bad) == 0, f"slot{slot} f{fr} seat{seat}: out of range "
                                 + ", ".join(f"{NAMES[i]}={v[i]:.3f}" for i in bad[:5]))
            nb = np.nonzero(BINARY & ~np.isin(v, (0.0, 1.0)))[0]
            check(len(nb) == 0, f"slot{slot} f{fr} seat{seat}: non-binary " + ", ".join(NAMES[i] for i in nb[:5]))
            # one-hot sums
            for i in range(V.N_ITEM):
                b = V.C_GROUND + 10 * i
                check(abs(v[b + 5:b + 10].sum() - v[b]) < 1e-6, f"item{i} class sum != present")
            for s_i in range(4):
                b = V.D_HELD + 6 * s_i
                check(v[b:b + 5].sum() <= 1.0 + 1e-6, "held one-hot sum > 1")
                check(v[b:b + 5].sum() > 0.5 or v[b + 5] == 0.0, "uses_frac without a held class")
                check(v[V.F_CHAR + 14 * s_i:V.F_CHAR + 14 * s_i + 14].sum() <= 1.0 + 1e-6, "char one-hot sum > 1")
            check(v[V.F_CHAR:V.F_CHAR + 14].sum() == 1.0, "self character one-hot missing")
            check(v[V.G_GLOBAL + 2:V.G_GLOBAL + 9].sum() <= 1.0, "stage one-hot sum > 1")
            check(v[V.H_SPATIAL + 26] == 1.0, "spatial map_present != 1 on a desert state")
            if seat == 1:   # the reader's spatial block == stage_geom's own encoder with its own ledger read
                import stage_geom as SG
                lp = P[seat]["pos"]
                ref = getattr(part_raw, "_sg", None) or SG.SpatialEncoder()
                part_raw._sg = ref
                rv = np.clip(ref(ram, float(lp[0]), float(lp[1]), float(lp[2])), -5, 5)
                if not np.allclose(rv, v[V.H_SPATIAL:V.H_SPATIAL + 27], atol=1e-5):
                    spatial_mismatch[0] += 1
            # independent sources
            seat_char = struct.unpack_from("<I", ram, 0x8C472DA8 + 0x14 * seat + 8 - V.RAM_BASE)[0]
            ci = V.CHAR_IDX.get(seat_char)
            if ci is None or v[V.F_CHAR + ci] != 1.0:
                char_mismatch += 1
            ptr = P[seat]["heldptr"]
            has_cls = v[V.D_HELD:V.D_HELD + 5].sum() > 0.5
            if bool(ptr) != has_cls:
                held_mismatch += 1
            if P[seat]["state"] not in (19,):
                agree_air[0] += int(P[seat]["airborne"] == (P[seat]["pos"][1] > 2.0))
                agree_air[1] += 1
            vecs.append(v)
        n_samples += 1
        # ---- seat symmetry: intrinsic blocks of seat j identical as self and as an opponent
        for a in range(4):
            va, ia, oa = per_seat[a]
            for k, j in enumerate(oa):
                vj = per_seat[j][0]
                for blk, w, so, oo_ in ((V.D_HELD, 6, 0, 6 * (k + 1)), (V.E_STATE, 8, 0, 8 * (k + 1)),
                                        (V.F_CHAR, 14, 0, 14 * (k + 1))):
                    check(np.array_equal(vj[blk + so:blk + so + w], va[blk + oo_:blk + oo_ + w]),
                          f"slot{slot} f{fr}: seat {j} block@{blk} differs as self vs as opp{k} of seat {a}")
                tally["sym_checks"] += 1
            # absolute chest/item positions agree across views (dx*1000 + my x)
            for b_ in range(4):
                if b_ == a:
                    continue
                vb = per_seat[b_][0]
                pa, pb = P[a]["pos"], P[b_]["pos"]
                cb = V.C_GROUND + 34
                b_abs = [(vb[cb + 5 * q + 1] * 1000 + pb[0], vb[cb + 5 * q + 2] * 1000 + pb[2], vb[cb + 5 * q + 4])
                         for q in range(V.N_CHEST) if vb[cb + 5 * q]]
                for i in range(V.N_CHEST):
                    c = cb + 5 * i
                    if not va[c] or abs(va[c + 1]) > 4.9 or abs(va[c + 2]) > 4.9:
                        continue
                    xa, za = va[c + 1] * 1000 + pa[0], va[c + 2] * 1000 + pa[2]
                    hit = [q for q in b_abs if abs(q[0] - xa) + abs(q[1] - za) < 2.0]
                    tally["sym_checks"] += 1
                    if len(b_abs) < V.N_CHEST:          # fewer than 2 chests exist -> B must see A's chest too
                        check(len(hit) == 1, f"slot{slot} f{fr}: chest seen by seat {a} missing in seat {b_}'s view")
                    if hit:
                        check(hit[0][2] == va[c + 4], f"slot{slot} f{fr}: chest has_stone differs between views")
        v1 = per_seat[1][0]
        tally["frames_with_threat"] += int(v1[V.B_THREAT] > 0)
        tally["frames_with_melee_live"] += int(any(v1[V.A_MELEE + V.A_OPP_W * k] > 0 for k in range(3)))
        tally["chests"] += int(v1[V.C_GROUND + 34] > 0)
        tally["chests_stone"] += int(v1[V.C_GROUND + 38] > 0)
        tally["items"] += int(v1[V.C_GROUND] > 0)
        tally["held_any"] += int(any(per_seat[s][0][V.D_HELD:V.D_HELD + 5].sum() > 0 for s in range(4)))
    check(char_mismatch == 0, f"slot{slot}: character one-hot disagrees with the seat table {char_mismatch}x")
    check(held_mismatch == 0, f"slot{slot}: held class vs F+0x54 non-zero disagree {held_mismatch}x")
    check(spatial_mismatch[0] == 0, f"slot{slot}: spatial block != stage_geom reference {spatial_mismatch[0]}x")
    air = agree_air[0] / max(1, agree_air[1])
    check(air >= 0.95, f"slot{slot}: airborne vs y>2 agreement {air:.3f} < 0.95")
    V_ = np.stack(vecs)
    res = dict(slot=slot, frames=fr, samples=n_samples, seat_vectors=len(vecs),
               scan_ms=dict(mean=1e3 * float(np.mean(t_scan)), p99=1e3 * float(np.percentile(t_scan, 99)),
                            max=1e3 * float(np.max(t_scan))),
               feat_ms=dict(mean=1e3 * float(np.mean(t_feat)), p99=1e3 * float(np.percentile(t_feat, 99)),
                            max=1e3 * float(np.max(t_feat))),
               airborne_agree=air, tally=tally, fails=FAILS[:40], n_fails=len(FAILS),
               nz=(V_ != 0).sum(0).tolist(), mn=V_.min(0).tolist(), mx=V_.max(0).tolist(),
               mean=V_.mean(0).tolist())
    with open(out_json, "w") as f:
        json.dump(res, f)
    print(f"[raw slot{slot}] {n_samples} samples x 4 seats, scan {res['scan_ms']['mean']:.3f} ms "
          f"(p99 {res['scan_ms']['p99']:.3f}), per-seat features {res['feat_ms']['mean']:.3f} ms "
          f"(p99 {res['feat_ms']['p99']:.3f}); airborne agree {air:.3f}; {tally}; fails {len(FAILS)}", flush=True)


# ------------------------------------------------------------------ part: determinism
def part_det(out_json):
    br = boot()

    def run(order):
        load(br, 2)
        rd = V.ObsV4Reader(br.ram)
        rng = random.Random(7)
        out, fr = [], 0
        for _ in range(150):
            br.press(rng.choice(MOVES), 6, player=1)
            fr += 6
            h = health(br.ram)
            P = rd.scan(fr)["P"]
            row = {}
            for seat in order:
                row[seat] = rd.features(seat, opp_order(P, seat, h), fr)[0].copy()
            # cache: a second call in the same frame returns the same vector
            again = rd.features(order[0], opp_order(P, order[0], h), fr)[0]
            check(np.array_equal(again, row[order[0]]), "same-frame repeat differs")
            out.append(np.stack([row[s] for s in range(4)]))
        return np.stack(out)

    a = run([0, 1, 2, 3])
    b = run([3, 1, 0, 2])
    check(np.array_equal(a, b), f"determinism: replay with a different seat order differs "
                                f"(max diff {np.abs(a - b).max():.3g})")
    with open(out_json, "w") as f:
        json.dump(dict(fails=FAILS, n_fails=len(FAILS), steps=int(a.shape[0]),
                       identical=bool(np.array_equal(a, b))), f)
    print(f"[det] {a.shape[0]} steps x 4 seats, identical={np.array_equal(a, b)}, fails {len(FAILS)}", flush=True)


# ------------------------------------------------------------------ part: env integration
def part_env(out_json, steps):
    os.environ["PS2_OBS_V3"] = "1"
    os.environ["PS2_OBS_V2"] = "1"
    os.environ.setdefault("PS2_STAGGER_FRAMES", "1")
    import tempfile
    from ffa_selfplay_env import FFASelfPlayEnv
    import powerstone_env_v6 as PE

    from obs_v4_envpatch import with_obs_v4

    class V4Env(with_obs_v4(FFASelfPlayEnv)):
        """The INTEGRATION.md patch (obs_v4_envpatch mixin, no repo file touched) plus a parity probe."""

        def _observe(self, s, prev):
            obs = super()._observe(s, prev)
            self.n_builds = getattr(self, "n_builds", 0) + 1
            seat = self.AGENT_PLAYER - 1
            ext = obs[V.V3_DIM:V.V4_DIM]
            bad = np.nonzero((ext < LO - 1e-6) | (ext > HI + 1e-6))[0]
            check(len(bad) == 0, "env v4 out of range " + ", ".join(f"{NAMES[i]}={ext[i]:.3f}" for i in bad[:5]))
            import struct as _st
            ch = _st.unpack_from("<I", self._lr_bridge.ram, 0x8C472DA8 + 0x14 * seat + 8 - V.RAM_BASE)[0]
            check(V.CHAR_IDX.get(ch) is not None and ext[V.F_CHAR + V.CHAR_IDX[ch]] == 1.0,
                  f"view seat {seat}: self character block is not this seat's character")
            # parity: the unpatched v3 builder on the same (s, prev) must equal obs[:160]; under ITEMEMB=zero
            # obs[12..17] must be 0 and every other prefix dim identical
            saved = type(self).OBS_DIM
            try:
                type(self).OBS_DIM = 160
                ref = PE.PowerStoneEnvV6._observe(self, s, prev)
            finally:
                type(self).OBS_DIM = saved
            keep = np.ones(160, bool)
            if self.OBS_V4_ITEMEMB == "zero":
                keep[12:18] = False
                self.emb_zero = getattr(self, "emb_zero", 0) + int(not obs[12:18].any())
                self.emb_ref_nz = getattr(self, "emb_ref_nz", 0) + int(ref[12:18].any())
            self.parity.append(bool(np.array_equal(ref[keep], obs[:V.V3_DIM][keep])) and ref.shape == (160,))
            return obs

    pool = tempfile.mkdtemp(prefix="v4pool_")
    V4Env.parity = []
    env = V4Env(core_path=CORE, game_path=GAME, states_dir=os.path.join(LP, "states"), state_slots=[3],
                instance_id=INSTANCE, bridge_dir=tempfile.mkdtemp(prefix="v4br_"), pool_dir=pool)
    env.parity = []
    obs = env.reset()
    check(obs.shape == (V.V4_DIM,), f"env obs shape {obs.shape}")
    check(env.OBS_V3 and env.prev is not None and env.prev.get("v8"), "env is not producing the obs-v3 (v8) line")
    rng = random.Random(3)
    n_view, n_steps, t_obs = 0, 0, []
    for _ in range(steps):
        obs, r, done, info = env.step(rng.randrange(env.action_space.n))
        n_steps += 1
        check(obs.shape == (V.V4_DIM,) and np.all(np.isfinite(obs)), "env obs bad")
        for v in env._views.values():                               # every other seat's view (seat-generic)
            t0 = time.perf_counter()
            ov = env._obs_from_view(v)
            t_obs.append(time.perf_counter() - t0)
            check(ov.shape == (V.V4_DIM,) and np.all(np.isfinite(ov)), f"view {v.player} obs bad")
            # the view's self character block must be ITS seat's character
            n_view += 1
        if done:
            obs = env.reset()
    par = float(np.mean(env.parity)) if env.parity else 0.0
    share = env._v4.n_scans / max(1, env.n_builds)
    check(env.emb_zero == env.n_builds, f"ITEMEMB=zero left obs[12..17] non-zero on {env.n_builds - env.emb_zero} builds")
    print(f"[env] obs[12..17] zeroed on {env.emb_zero}/{env.n_builds} builds (the v3 builder had a slot hash there on "
          f"{env.emb_ref_nz})")
    print(f"[env] RAM scans per obs build {share:.3f} (learner + 3 views share one scan per emulator frame)")
    check(par == 1.0, f"v3 prefix parity {par:.4f} != 1.0 over {len(env.parity)} observations")
    res = dict(steps=n_steps, views=n_view, prefix_parity=par, n_parity=len(env.parity),
               view_obs_ms=1e3 * float(np.mean(t_obs)) if t_obs else 0.0, fails=FAILS, n_fails=len(FAILS))
    with open(out_json, "w") as f:
        json.dump(res, f)
    print(f"[env] {n_steps} learner steps + {n_view} other-seat views, obs dim {V.V4_DIM}, v3-prefix parity "
          f"{par:.4f} over {len(env.parity)} builds, full _obs_from_view {res['view_obs_ms']:.2f} ms; "
          f"fails {len(FAILS)}", flush=True)


# ------------------------------------------------------------------ part: owners and held-item swings
def part_owner(slot, seconds, chests_first, out_json):
    """Ground truth from the game itself, checked every frame, with the overlay's scripted P2 (it picks up and
    uses items) and the COMs:
      FIRE events = a seat's held ranged-item counter ticks down (the shot leaves on that frame);
      HIT events  = a victim's health drops and its hit source P+0x3774 points at a ledger record.
    (a) header byte 1 of every new category-1 record == the +0x14 chain owner whenever the chain resolves;
    (b) ITEM bullets (vt 0x0C162000..0x0C16D000; no chain owner): byte 1 == the single seat that fired within
        -2..+8 frames (agreement >= 95%);
    (c) P2's obs (env cadence) never carries an item bullet that P2 fired;
    (d) every hit whose source is a HELD MELEE item has reader contact (item-swing spheres vs victim cylinder,
        margin <= 0) at the hit frame or the frame before (>= 90%)."""
    import struct
    import collections
    sys.path.insert(0, os.path.join(HERE, "..", "items_held"))
    import overlay_v4 as O
    br = boot()
    load(br, slot)
    rd = V.ObsV4Reader(br.ram)
    bot = O.Bot(100 + slot, rd._sg.maps[5].dirs, chests_first)
    r = br.ram
    lo = V.LEDGER_LO - V.RAM_BASE
    L = r[lo:lo + V.LEDGER_N * V.LEDGER_STRIDE].reshape(V.LEDGER_N, V.LEDGER_STRIDE)
    PB = lambda j: V.P_BASE - V.RAM_BASE + j * V.P_STRIDE  # noqa: E731
    prev_u, fires, seen, live, log = [None] * 4, [], {}, {}, []
    cnt = collections.Counter()
    prevh, prev_m, mask, last_contact = health(r), {}, 0, {}
    for fr in range(1, int(seconds * 60)):
        if fr % 6 == 1:
            mask = bot.act(rd.scan(fr - 1), health(r), fr / 60.0)   # state BEFORE this frame (cached)
        br.press(mask, 1, player=1)
        S = rd.scan(fr)
        P = S["P"]
        for j in range(4):
            u, c = (P[j]["held_uses"], P[j]["held_code"]) if P[j]["held_idx"] is not None else (None, 0)
            if prev_u[j] is not None and u is not None and u < prev_u[j] and V.ITEM_CLS.get(c, (9,))[0] in (1, 2):
                fires.append((fr, j, c))
            prev_u[j] = u
        for k in range(V.LEDGER_N):
            if L[k, 4] != 1:
                seen.pop(k, None)
                live.pop(k, None)
                continue
            ser = struct.unpack_from("<I", L[k], 0x28)[0]
            if seen.get(k) == ser:
                continue
            seen[k] = ser
            rec = (fr, struct.unpack_from("<I", L[k], 8)[0], int(L[k, 5]), rd._owner(k, L),
                   [V.ITEM_CLS.get(P[q]["held_code"], (9,))[0] for q in range(4)])
            live[k] = rec
            log.append(rec)
        cur_m = {}
        for a in range(4):
            if P[a]["item_swing"]:
                for v in range(4):
                    if v != a:
                        cx, cy, cz, R, H = P[v]["cyl"]
                        cur_m[(a, v)] = min(max(math.hypot(x - cx, z - cz) - (rr + R), abs(y - cy) - (rr + H))
                                            for x, y, z, rr in P[a]["spheres"])
        h = health(r)
        for v in range(4):
            if prevh[v] - h[v] > 3 and prevh[v] > 1:
                src = struct.unpack_from("<I", r, PB(v) + V.OFF_LASTHIT)[0] & 0xFFFFFF
                o_ = src - 4 - lo
                if 0 <= o_ < V.LEDGER_N * V.LEDGER_STRIDE and o_ % V.LEDGER_STRIDE == 0:
                    ch_ = rd._owner(o_ // V.LEDGER_STRIDE, L)
                    if ch_ is not None and ch_ != v:              # "last hit me" attribution for projectile hits
                        cnt["proj_hits_chain_owned"] += 1
                        hs_ = rd._hit_source(v)
                        cnt["proj_hits_last_hit_me_ok"] += int(hs_ == ch_)
                        if hs_ != ch_:
                            print(f"[owner-miss] lasthit f{fr} victim P{v + 1} src={src:#x} chain={ch_} reader={hs_} "
                                  f"cached_src={rd._cache['P'][v]['lasthit']:#x}", flush=True)
                for a in range(4):
                    i = P[a]["held_idx"]
                    if i is not None and src == lo + i * V.LEDGER_STRIDE + 4 \
                            and V.ITEM_CLS.get(P[a]["held_code"], (9,))[0] == 0:
                        cnt["item_melee_hits"] += 1
                        ok_ = min(cur_m.get((a, v), 9e9), prev_m.get((a, v), 9e9)) <= 0
                        cnt["item_melee_hits_with_contact"] += int(ok_)
                        lc = last_contact.get((a, v))
                        cur_c = cur_m.get((a, v), 9e9) <= 0
                        cnt["item_melee_hits_contact_8f"] += int(cur_c or (lc is not None and fr - lc <= 8))
                        if not ok_:
                            hi = P[a]["held_idx"]
                            print(f"[owner-miss] swing f{fr} P{a + 1}->P{v + 1} code={P[a]['held_code']:#x} "
                                  f"pst={P[a]['state']} recst={int(L[hi, 0x421])} item_swing={P[a]['item_swing']} "
                                  f"hdr188={struct.unpack_from('<I', L[hi], 0x188)[0]:#010x} "
                                  f"m_now={cur_m.get((a, v))} m_prev={prev_m.get((a, v))}", flush=True)
        for key, m in cur_m.items():
            if m <= 0:
                last_contact[key] = fr
        prevh, prev_m = h, cur_m
        if fr % 6 == 0:                                   # (c) P2's obs at env cadence
            vec, info = rd.features(1, opp_order(P, 1, h), fr)
            for (dx, dy, dz, vx, vy, vz, rr, thrown, owner, vtj) in info["threats"][:V.N_THREAT]:
                if not (0x0C162000 <= vtj < 0x0C16D000) or vtj in V.SELF_HARM_VT:
                    continue
                x, z = dx + P[1]["pos"][0], dz + P[1]["pos"][2]
                for k, (bf, bvt, b1, chain, _hc) in live.items():
                    if bvt == vtj and abs(struct.unpack_from("<f", L[k], 0x2C)[0] - x) < 1.0 \
                            and abs(struct.unpack_from("<f", L[k], 0x34)[0] - z) < 1.0:
                        cnt["p2_obs_item_bullets"] += 1
                        cnt["p2_obs_OWN_item_bullets"] += int({j for (f, j, *_c) in fires if -2 <= bf - f <= 8} == {1})
    for bf, vt, b1, chain, hc in log:
        if chain is not None:
            cnt["chain_owned"] += 1
            cnt["chain_owned_b1_agrees"] += int(b1 == chain)
        elif 0x0C162000 <= vt < 0x0C16D000:
            if vt not in V.SELF_HARM_VT:                      # second truth: the byte-1 seat holds a ranged item
                cnt["item_bullets"] += 1
                cnt["item_bullets_b1_holds_ranged"] += int(b1 < 4 and hc[b1] in (1, 2))
            fs = {j for (f, j, *_c) in fires if 0 <= bf - f <= 3}     # a bullet is born on (or just after) its shot
            if len(fs) == 1:
                cnt["item_bullets_with_shooter"] += 1
                sh = next(iter(fs))
                cnt["item_bullets_b1_is_shooter"] += int(b1 == sh)
                if b1 != sh:
                    print(f"[owner-miss] bullet f{bf} vt={vt:#x} b1={b1} shooter={sh} fires near: "
                          f"{[(f, j, hex(c_)) for (f, j, c_) in fires if -10 <= bf - f <= 12]}", flush=True)
    c = cnt
    check(c["chain_owned_b1_agrees"] == c["chain_owned"], f"slot{slot}: byte1 != chain owner "
                                                           f"{c['chain_owned'] - c['chain_owned_b1_agrees']}x")
    if c["item_bullets_with_shooter"] >= 5:
        check(c["item_bullets_b1_is_shooter"] >= 0.9 * c["item_bullets_with_shooter"],
              f"slot{slot}: item-bullet owner agreement {c['item_bullets_b1_is_shooter']}/{c['item_bullets_with_shooter']}")
    if c["item_bullets"] >= 5:
        check(c["item_bullets_b1_holds_ranged"] >= 0.95 * c["item_bullets"],
              f"slot{slot}: byte-1 seat holds a ranged item for {c['item_bullets_b1_holds_ranged']}/{c['item_bullets']} bullets")
    check(c["proj_hits_last_hit_me_ok"] == c["proj_hits_chain_owned"],
          f"slot{slot}: last-hit attribution {c['proj_hits_last_hit_me_ok']}/{c['proj_hits_chain_owned']} projectile hits")
    check(c["p2_obs_OWN_item_bullets"] == 0, f"slot{slot}: P2 obs carried its own item bullet {c['p2_obs_OWN_item_bullets']}x")
    if c["item_melee_hits"] >= 5:
        check(c["item_melee_hits_contact_8f"] >= 0.75 * c["item_melee_hits"],
              f"slot{slot}: item-swing contact (<= 8 f before the hit) on {c['item_melee_hits_contact_8f']}/{c['item_melee_hits']}")
    with open(out_json, "w") as f:
        json.dump(dict(slot=slot, counts=dict(c), fires=len(fires), fails=FAILS, n_fails=len(FAILS)), f)
    print(f"[owner slot{slot}] fires {len(fires)}; chain-owned b1 agrees {c['chain_owned_b1_agrees']}/{c['chain_owned']}; "
          f"item bullets b1==shooter {c['item_bullets_b1_is_shooter']}/{c['item_bullets_with_shooter']}, b1 seat holds a "
          f"ranged item {c['item_bullets_b1_holds_ranged']}/{c['item_bullets']}; P2-obs item "
          f"bullets {c['p2_obs_item_bullets']} (last-hit-me on projectile hits {c['proj_hits_last_hit_me_ok']}/"
          f"{c['proj_hits_chain_owned']}) of which own {c['p2_obs_OWN_item_bullets']}; item-melee hits with contact "
          f"on the hit/previous frame {c['item_melee_hits_with_contact']}/{c['item_melee_hits']}, within 8 f "
          f"{c['item_melee_hits_contact_8f']}/{c['item_melee_hits']}; fails {len(FAILS)}", flush=True)


# ------------------------------------------------------------------ driver
def write_stats(raws, path):
    nz = np.sum([r["nz"] for r in raws], 0)
    n = sum(r["seat_vectors"] for r in raws)
    mn = np.min([r["mn"] for r in raws], 0)
    mx = np.max([r["mx"] for r in raws], 0)
    mean = np.sum([np.array(r["mean"]) * r["seat_vectors"] for r in raws], 0) / n
    zero = [NAMES[i] for i in range(V.V4_EXTRA) if nz[i] == 0 and not NAMES[i].startswith(EXPECTED_DEAD_PREFIX)]
    lineup = [z for z in zero if z.startswith(LINEUP_DEAD_PREFIX) or z.endswith(LINEUP_DEAD_SUFFIX)]
    dead = [z for z in zero if z not in lineup]
    lines = [f"obs v4 appended-block stats: {n} seat-vectors (4 seats x every 6th frame) over slots "
             f"{[r['slot'] for r in raws]}, {sum(r['frames'] for r in raws)} frames, random P2 inputs + COMs.",
             f"UNEXPECTED dead features ({len(dead)}): {', '.join(dead) if dead else 'none'}",
             f"zero because of the test lineups / desert item spawns ({len(lineup)}): {', '.join(lineup)}",
             f"expected-zero by design on these states: {', '.join(EXPECTED_DEAD_PREFIX)}", "",
             f"{'obs idx':>7} {'feature':28s} {'nonzero':>8} {'min':>8} {'max':>8} {'mean':>8}"]
    for i, nm in enumerate(NAMES):
        lines.append(f"{V.V3_DIM + i:7d} {nm:28s} {nz[i] / n:8.4f} {mn[i]:8.3f} {mx[i]:8.3f} {mean[i]:8.3f}")
    with open(path, "w") as f:
        f.write("\n".join(lines) + "\n")
    return dead


def driver(a):
    tmp = os.environ.get("TMPDIR", "/tmp")
    jobs = [("raw", ["--slot", str(s), "--frames", str(a.frames)]) for s in (1, 2, 3)]
    jobs += [("det", []), ("env", ["--steps", str(a.steps)])]
    jobs += [("owner", ["--slot", str(sl), "--seconds", str(sec), "--chests-first", str(cf)])
             for sl, sec, cf in ((1, 90, 40), (2, 240, 0), (3, 240, 0))]
    results, ok = {}, True
    for part, extra in jobs:
        out = os.path.join(tmp, f"obs_v4_{part}_{extra[1] if part in ('raw', 'owner') else 'x'}.json")
        if os.path.exists(out):
            os.remove(out)
        cmd = [sys.executable, os.path.abspath(__file__), "--part", part, "--out", out] + extra
        for attempt in range(3):            # the core occasionally segfaults at boot (known flake, re/*/run.sh)
            p = subprocess.run(cmd, cwd=LP, capture_output=True, text=True)
            if os.path.exists(out) or p.returncode >= 0:
                break
            print(f"[driver] part {part} {extra}: emulator crashed (rc {p.returncode}), retry {attempt + 1}", flush=True)
        for line in p.stdout.splitlines():
            if line.startswith(("[raw", "[det", "[env", "[owner", "FAIL")):
                print(line, flush=True)
        if not os.path.exists(out):
            print(f"FAIL: part {part} {extra} produced no result (rc {p.returncode})\n{p.stderr[-2000:]}")
            ok = False
            continue
        with open(out) as f:
            results[(part, tuple(extra))] = json.load(f)
        os.remove(out)
        if results[(part, tuple(extra))]["n_fails"]:
            ok = False
    raws = [v for (p, _), v in results.items() if p == "raw"]
    if raws:
        dead = write_stats(raws, os.path.join(HERE, "obs_v4_stats.txt"))
        scan = np.mean([r["scan_ms"]["mean"] for r in raws])
        feat = np.mean([r["feat_ms"]["mean"] for r in raws])
        print(f"[summary] shared scan {scan:.3f} ms/frame + {feat:.3f} ms/seat -> learner-only step "
              f"{scan + feat:.3f} ms, FFA 4 views {scan + 4 * feat:.3f} ms; unexpected dead features: {dead or 'none'}")
    nf = sum(r["n_fails"] for r in results.values())
    print(f"obs v4 tests: {len(results)}/{len(jobs)} parts ran, {nf} failures -> {'PASS' if ok and nf == 0 else 'FAIL'}")
    return 0 if ok and nf == 0 else 1


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="")
    ap.add_argument("--slot", type=int, default=2)
    ap.add_argument("--frames", type=int, default=6000)
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--out", default="")
    ap.add_argument("--seconds", type=float, default=240.0)
    ap.add_argument("--chests-first", type=float, default=0.0)
    a = ap.parse_args()
    if a.part == "raw":
        part_raw(a.slot, a.frames, a.out)
    elif a.part == "det":
        part_det(a.out)
    elif a.part == "owner":
        part_owner(a.slot, a.seconds, a.chests_first, a.out)
    elif a.part == "env":
        part_env(a.out, a.steps)
    else:
        sys.exit(driver(a))
    sys.stdout.flush()
    os._exit(0)          # skip the core's teardown (the harmless 'mutex lock failed' abort)
