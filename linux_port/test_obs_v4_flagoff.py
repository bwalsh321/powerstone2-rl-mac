"""test_obs_v4_flagoff.py -- the obs-v4 integration must be INERT with the flag off (Oct 5 2026).

Runs the same seeded episodes twice, once with the pre-v4 code (an export of the parent commit's linux_port, e.g.
`git archive <parent> linux_port`) and once with this tree, and compares every observation BIT FOR BIT:
  ffa   the training env (FFASelfPlayEnv, mixed seats 0,2, joint63, the league_env.txt arena flags) on a few
        states_mixed slots, with a 160-dim pool policy driving the two policy seats: the learner's observation,
        reward and done of every step, plus every pool seat's view (_obs_from_view output);
  base  the eval env (PowerStoneEnvLibretro, the eval_parity.py contract for a 160-dim model) on held-out slots.
Then (--flag-on) this tree again with PS2_OBS_V4=1 PS2_OBS_V4_ITEMEMB=keep: the obs is 430-dim and obs[:160] must be
bit-identical to the pre-v4 obs on the same frames (pool seats' views too, they are 160-dim consumers).

    python test_obs_v4_flagoff.py --old-tree /path/to/export/linux_port --pool DIR_WITH_A_160_DIM_ZIP \\
        --mixed-states /abs/states_mixed --states /abs/states [--instance 60] [--steps 150]
Each run is a subprocess with cwd = its tree (PYTHONPATH must contain "." and the harness). Exit 1 on any mismatch.
"""
import argparse
import json
import os
import random
import subprocess
import sys
import time

import numpy as np

ARENA = dict(PS2_OBS_V2="1", PS2_OBS_V3="1", PS2_ZERO_SUM="1", PS2_START_HEALTH="0.5,1.0", PS2_OBS_CTX_FIX="1",
             PS2_ZS_TIME="1", PS2_SPECIAL_DMG_W="1.0", PS2_SPECIAL_R="700", PS2_LOST_EXTRA_W="1.0",
             PS2_SPECIAL_WINDOW="2.0", PS2_LOSS_SCALE_LV8="0.5", PS2_SPECIAL_WINDOW_CLOCK="frames",
             PS2_SPECIAL_ATTRIB="1", PS2_BUTTON_TAP="1", PS2_FFA_SEATS="0,2", PS2_POOL_SAMPLING="uniform")
FFA_SLOTS = (0, 12, 33, 55)
BASE_SLOTS = (90, 93)


def seed_all(s):
    import torch as th
    random.seed(s)
    np.random.seed(s)
    th.manual_seed(s)


def dump(a):
    import torch as th
    th.set_num_threads(1)
    core = os.environ["PS2_CORE"]
    out = {}
    if a.part == "ffa":
        from ffa_selfplay_env import FFASelfPlayEnv
        seed_all(1)
        env = FFASelfPlayEnv(core_path=core, game_path=a.game, states_dir=a.mixed_states, instance_id=a.instance,
                             state_slots=[FFA_SLOTS[0]], bridge_dir=os.path.abspath(f"bridge_i{a.instance}"),
                             pool_dir=a.pool)
        slots = FFA_SLOTS
    else:
        from powerstone_env_libretro import PowerStoneEnvLibretro
        seed_all(1)
        env = PowerStoneEnvLibretro(core_path=core, game_path=a.game, states_dir=a.states, instance_id=a.instance,
                                    state_slots=[BASE_SLOTS[0]], bridge_dir=os.path.abspath(f"bridge_i{a.instance}"))
        env._legacy_proj_main = env._legacy_proj = False          # eval_parity.py for a 160-dim (v3) model
        env._legacy_item_main = env._legacy_item = True
        slots = BASE_SLOTS
    env.set_action_mode(63)
    views = []
    if hasattr(env, "_obs_from_view"):
        orig = env._obs_from_view

        def rec(v, _o=orig):
            o = _o(v)
            views.append(np.asarray(o, np.float32).copy())
            return o
        env._obs_from_view = rec
    for slot in slots:
        seed_all(100 + slot)
        env.STATE_SLOTS = [slot]
        obs = [np.asarray(env.reset(), np.float32).copy()]
        rew, done_ = [], []
        rng = random.Random(slot)
        for _ in range(a.steps):
            o, r, d, info = env.step(rng.randrange(63))
            obs.append(np.asarray(o, np.float32).copy()); rew.append(float(r)); done_.append(bool(d))
            if d:
                obs.append(np.asarray(env.reset(), np.float32).copy())
        out[f"obs_{slot}"] = np.stack(obs)
        out[f"rew_{slot}"] = np.array(rew, np.float64)
        out[f"done_{slot}"] = np.array(done_)
    out["views"] = np.stack(views) if views else np.zeros((0, 160), np.float32)
    np.savez(a.out, **out)
    print(f"[dump] {a.part} obs_dim={env.OBS_DIM} slots={slots} steps={a.steps} views={len(views)} -> {a.out}", flush=True)


def compare(ref, new, prefix_only):
    """Bitwise comparison; prefix_only: compare new[..., :ref_width] (flag-on run vs pre-v4)."""
    r, n = np.load(ref), np.load(new)
    rows, ok = [], True
    for k in r.files:
        x, y = r[k], n[k]
        if prefix_only and x.ndim == 2 and y.ndim == 2 and y.shape[1] > x.shape[1]:
            y = y[:, :x.shape[1]]
        same = x.shape == y.shape and x.dtype == y.dtype and x.tobytes() == y.tobytes()
        diff = float(np.abs(x.astype(np.float64) - y.astype(np.float64)).max()) if x.shape == y.shape and x.size else -1.0
        rows.append((k, tuple(x.shape), tuple(n[k].shape), same, diff))
        ok &= same
    return ok, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--old-tree", default="")
    ap.add_argument("--pool", required=True)
    ap.add_argument("--mixed-states", required=True)
    ap.add_argument("--states", required=True)
    ap.add_argument("--game", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                                                    "Power Stone 2 (USA).chd")))
    ap.add_argument("--instance", type=int, default=60)
    ap.add_argument("--steps", type=int, default=150)
    ap.add_argument("--tmp", default=os.environ.get("TMPDIR", "/tmp"))
    ap.add_argument("--flag-on", action="store_true")
    ap.add_argument("--par", type=int, default=2, help="emulator processes at once (~1.5 GB each)")
    a = ap.parse_args()
    if a.part:
        sys.path[0] = os.getcwd()         # import the env code of the tree we run in (cwd), not this file's tree
        dump(a)
        sys.stdout.flush()
        os._exit(0)                       # skip the core's teardown abort
    here = os.path.dirname(os.path.abspath(__file__))
    common = ["--pool", a.pool, "--mixed-states", a.mixed_states, "--states", a.states, "--game", a.game,
              "--steps", str(a.steps)]
    runs = [("old", a.old_tree, {}), ("new", here, {})]
    if a.flag_on:
        runs.append(("v4on", here, {"PS2_OBS_V4": "1", "PS2_OBS_V4_ITEMEMB": "keep"}))
    procs = []
    for i, (tag, tree, extra) in enumerate(runs):
        for part in ("ffa", "base"):
            env = dict(os.environ, **ARENA, **extra)
            for k in ("PS2_OBS_V4", "PS2_OBS_V4_ITEMEMB"):
                if k not in extra:
                    env.pop(k, None)
            env["PS2_STAGGER_FRAMES"] = env.get("PS2_STAGGER_FRAMES", "240")
            out = os.path.join(a.tmp, f"flagoff_{tag}_{part}.npz")
            inst = a.instance + 2 * i + (part == "base")
            cmd = [sys.executable, os.path.abspath(__file__), "--part", part, "--out", out,
                   "--instance", str(inst)] + common
            while len([p for p in procs if p[3].poll() is None]) >= a.par:  # at most --par emulators at once
                time.sleep(1.0)
            procs.append((tag, part, out, subprocess.Popen(cmd, cwd=tree, env=env)))
    for _, _, _, p in procs:
        p.wait()
    ok_all = True
    res = {}
    for part in ("ffa", "base"):
        ref = os.path.join(a.tmp, f"flagoff_old_{part}.npz")
        for tag, prefix in (("new", False), ("v4on", True)):
            if tag == "v4on" and not a.flag_on:
                continue
            ok, rows = compare(ref, os.path.join(a.tmp, f"flagoff_{tag}_{part}.npz"), prefix)
            ok_all &= ok
            res[f"{part}/{tag}"] = rows
            for k, s0, s1, same, diff in rows:
                print(f"[cmp] {part:4s} {tag:4s} {k:10s} pre-v4 {s0} vs {s1}: "
                      f"{'BIT-IDENTICAL' if same else 'DIFFERENT max|d|=%.3g' % diff}"
                      f"{' (prefix [:%d])' % s0[1] if prefix and len(s0) == 2 else ''}", flush=True)
    print(json.dumps({k: sum(int(r[3]) for r in v) for k, v in res.items()}))
    print("flag-off bit-identity:", "PASS" if ok_all else "FAIL")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
