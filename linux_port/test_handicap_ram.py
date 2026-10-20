"""test_handicap_ram.py -- the adaptive handicap in the real env (Oct 19 2026; handicap.py, ffa_selfplay_env.py).

One emulator. FFASelfPlayEnv with PS2_HANDICAP=1 (live arena flags, a v4 pool policy on seats P1/P3). For each case,
the same seeded reset is done twice, once at h = 1.0 and once at h = 0.7, and every seat's health is read straight
from SYSTEM_RAM (the float32 object field ps2_addr.HEALTH_OBJ[k] the reset wrote) after the reset:
  A  PS2_START_HEALTH=0.5,1.0 (live), slot 55 (handicapped): learner (P2) health ratio 0.7, every other seat 1.0
  B  PS2_START_HEALTH=0.5,1.0, slot 30 (not handicapped):     every ratio 1.0
  C  PS2_START_HEALTH unset, slot 55:                         learner ratio 0.7 of the savestate value, others 1.0
Then one full episode on slot 55 at h = 0.7: the [ep] line carries hcap=0.700, h moves by -0.0045 (win) or +0.0055
(loss / timeout), and the env's state file is written. Exit 1 on any failure.

    python test_handicap_ram.py --pool DIR --mixed-states /abs/states_mixed --state-dir /abs/tmpdir [--instance 73]
"""
import argparse
import json
import os
import random
import struct
import sys

import numpy as np

ARENA = dict(PS2_OBS_V2="1", PS2_OBS_V3="1", PS2_OBS_V4="1", PS2_OBS_V4_ITEMEMB="keep", PS2_OBJ_GRID_N="208",
             PS2_ZERO_SUM="1", PS2_START_HEALTH="0.5,1.0", PS2_OBS_CTX_FIX="1", PS2_OBS_STACK="2",
             PS2_ZS_TIME="1", PS2_SPECIAL_DMG_W="1.0", PS2_SPECIAL_R="700", PS2_LOST_EXTRA_W="1.0",
             PS2_SPECIAL_WINDOW="2.0", PS2_LOSS_SCALE_LV8="0.5", PS2_SPECIAL_WINDOW_CLOCK="frames",
             PS2_SPECIAL_ATTRIB="1", PS2_BUTTON_TAP="1", PS2_FFA_SEATS="0,2", PS2_POOL_SAMPLING="uniform",
             PS2_PPO_KL_REF="prox", PS2_NET_WIDTH="512", PS2_HANDICAP="1")
FAILS = []


def check(cond, msg):
    print(("  ok   " if cond else "  FAIL ") + msg, flush=True)
    if not cond:
        FAILS.append(msg)


def seed_all(s):
    import torch as th
    random.seed(s)
    np.random.seed(s)
    th.manual_seed(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pool", required=True)
    ap.add_argument("--mixed-states", required=True)
    ap.add_argument("--state-dir", required=True)
    ap.add_argument("--game", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                                                    "Power Stone 2 (USA).chd")))
    ap.add_argument("--instance", type=int, default=73)
    ap.add_argument("--max-steps", type=int, default=3000)
    a = ap.parse_args()
    os.environ.update(ARENA)
    os.environ["PS2_HANDICAP_STATE"] = a.state_dir
    for k in ("PS2_HUNTER_P", "PS2_HUNTER_SEATS", "PS2_DRILL_DIR", "PS2_DRILL_P"):
        os.environ.pop(k, None)
    import torch as th
    th.set_num_threads(1)
    import ffa_selfplay_env as F
    import ps2_addr as A
    env = F.FFASelfPlayEnv(core_path=os.environ["PS2_CORE"], game_path=a.game, states_dir=a.mixed_states,
                           instance_id=a.instance, state_slots=[55],
                           bridge_dir=os.path.abspath(f"bridge_i{a.instance}"), pool_dir=a.pool)
    env.set_action_mode(63)
    check(env._hcap is not None, "PS2_HANDICAP=1 -> env has a handicap controller")
    ram = env._lr_bridge.ram
    base = A.RAM_BASE + A.RAM_DELTA
    L = env._learner_idx

    def ram_health():
        out = []
        for k in range(4):
            o = A.HEALTH_OBJ[k] - base
            out.append(struct.unpack("<f", bytes(ram[o:o + 4]))[0])
        return out

    def reset_at(slot, h, seed):
        seed_all(seed)
        env.STATE_SLOTS = [slot]
        env._hcap.h = h
        env.reset()
        return ram_health(), list(env._present_seats())

    sh = F.START_HEALTH
    for tag, slot, start_health, want_l in (("A start_health + slot 55", 55, sh, 0.7),
                                            ("B start_health + slot 30", 30, sh, 1.0),
                                            ("C no start_health + slot 55", 55, None, 0.7)):
        F.START_HEALTH = start_health
        h1, seats = reset_at(slot, 1.0, 11)
        h7, seats7 = reset_at(slot, 0.7, 11)
        F.START_HEALTH = sh
        ratios = {k: (h7[k] / h1[k] if h1[k] else float("nan")) for k in seats}
        print(f"  [{tag}] seats={seats} health@h=1.0 " + " ".join(f"P{k + 1}={h1[k]:.1f}" for k in seats)
              + "  health@h=0.7 " + " ".join(f"P{k + 1}={h7[k]:.1f}" for k in seats)
              + "  ratio " + " ".join(f"P{k + 1}={ratios[k]:.4f}" for k in seats), flush=True)
        check(seats == seats7 and L in seats and len(seats) >= 3, f"{tag}: same seats both resets")
        check(abs(ratios[L] - want_l) < 1e-3, f"{tag}: learner P{L + 1} ratio {ratios[L]:.4f} (want {want_l})")
        check(all(abs(ratios[k] - 1.0) < 1e-6 for k in seats if k != L), f"{tag}: other seats unchanged")
        check(env._hcap_ep == (0.7 if slot == 55 else None), f"{tag}: episode marked handicapped = {slot == 55}")

    # one full episode at h = 0.7 on slot 55
    _, _ = reset_at(55, 0.7, 12)
    h_before = env._hcap.h
    n_before = env._hcap.n
    rng = random.Random(5)
    info, done, t = {}, False, 0
    while not done and t < a.max_steps:
        _, _, done, info = env.step(rng.randrange(63))
        t += 1
    won = info.get("result") == "win"
    want = min(1.0, max(0.5, h_before - 0.01 * ((1.0 if won else 0.0) - 0.55)))
    print(f"  [episode] steps={t} done={done} result={info.get('result', '-')} h {h_before:.4f} -> {env._hcap.h:.4f} "
          f"ema={env._hcap.ema:.4f}", flush=True)
    check(done, "episode ended")
    check(abs(env._hcap.h - want) < 1e-9 and env._hcap.n == n_before + 1,
          f"h updated by the rule ({'win' if won else 'loss/timeout'}: {want - h_before:+.4f})")
    p = os.path.join(a.state_dir, f"hcap_i{a.instance}.json")
    st = json.load(open(p)) if os.path.exists(p) else {}
    check(abs(st.get("h", -1) - env._hcap.h) < 1e-6, f"state file {p} written: {st}")
    print("handicap RAM / env check:", "PASS" if not FAILS else f"FAIL ({len(FAILS)})", flush=True)
    sys.stdout.flush()
    os._exit(1 if FAILS else 0)          # skip the core's teardown abort


if __name__ == "__main__":
    main()
