"""test_drill_flagoff.py -- practice start points (PS2_DRILL_DIR / PS2_DRILL_P) must be INERT when off (Oct 10 2026).

Runs the same seeded FFA steps (FFASelfPlayEnv, mixed seats 0,2, joint63, obs v4, the live league_env.txt arena
flags, a v4 pool policy on the policy seats) with the pre-drill code (an export of the parent commit's linux_port,
e.g. `git archive <parent> linux_port | tar -x -C DIR`) and with this tree, and compares the learner's observation,
reward and done of every step plus every pool seat's view BIT FOR BIT. Runs on this tree:
  new      no drill flags;
  dir_p0   PS2_DRILL_DIR set, PS2_DRILL_P=0 (the folder is never read).

    python test_drill_flagoff.py --old-tree /path/to/export/linux_port --pool DIR_WITH_A_430_DIM_ZIP \\
        --mixed-states /abs/states_mixed --drills /abs/drills/leg155_rl [--instance 93] [--steps 300]
Each run is a subprocess with cwd = its tree (PYTHONPATH must contain "." and the harness). Exit 1 on any mismatch.
"""
import argparse
import os
import random
import subprocess
import sys
import time

import numpy as np

ARENA = dict(PS2_OBS_V2="1", PS2_OBS_V3="1", PS2_OBS_V4="1", PS2_OBS_V4_ITEMEMB="keep", PS2_OBJ_GRID_N="208",
             PS2_ZERO_SUM="1", PS2_START_HEALTH="0.5,1.0", PS2_OBS_CTX_FIX="1", PS2_OBS_STACK="7",
             PS2_ZS_TIME="1", PS2_SPECIAL_DMG_W="1.0", PS2_SPECIAL_R="700", PS2_LOST_EXTRA_W="1.0",
             PS2_SPECIAL_WINDOW="2.0", PS2_LOSS_SCALE_LV8="0.5", PS2_SPECIAL_WINDOW_CLOCK="frames",
             PS2_SPECIAL_ATTRIB="1", PS2_BUTTON_TAP="1", PS2_FFA_SEATS="0,2", PS2_POOL_SAMPLING="uniform",
             PS2_PPO_KL_REF="prox")
SLOTS = (30, 55, 62)


def seed_all(s):
    import torch as th
    random.seed(s)
    np.random.seed(s)
    th.manual_seed(s)


def dump(a):
    import torch as th
    th.set_num_threads(1)
    from ffa_selfplay_env import FFASelfPlayEnv
    seed_all(1)
    env = FFASelfPlayEnv(core_path=os.environ["PS2_CORE"], game_path=a.game, states_dir=a.mixed_states,
                         instance_id=a.instance, state_slots=[SLOTS[0]],
                         bridge_dir=os.path.abspath(f"bridge_i{a.instance}"), pool_dir=a.pool)
    env.set_action_mode(63)
    views = []
    orig = env._obs_from_view

    def rec(v, _o=orig):
        o = _o(v)
        views.append(np.asarray(o, np.float32).copy())
        return o
    env._obs_from_view = rec
    out = {}
    for slot in SLOTS:
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
    out["views"] = np.stack(views) if views else np.zeros((0, 430), np.float32)
    np.savez(a.out, **out)
    print(f"[dump] obs_dim={env.OBS_DIM} slots={SLOTS} steps={a.steps} views={len(views)} "
          f"dones={sum(int(out[f'done_{s}'].sum()) for s in SLOTS)} -> {a.out}", flush=True)


def compare(ref, new):
    r, n = np.load(ref), np.load(new)
    rows, ok = [], True
    for k in r.files:
        x, y = r[k], n[k]
        same = x.shape == y.shape and x.dtype == y.dtype and x.tobytes() == y.tobytes()
        diff = float(np.abs(x.astype(np.float64) - y.astype(np.float64)).max()) if x.shape == y.shape and x.size else -1.0
        rows.append((k, tuple(x.shape), tuple(y.shape), same, diff))
        ok &= same
    return ok, rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--old-tree", default="")
    ap.add_argument("--pool", required=True)
    ap.add_argument("--mixed-states", required=True)
    ap.add_argument("--drills", default="")
    ap.add_argument("--game", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                                                    "Power Stone 2 (USA).chd")))
    ap.add_argument("--instance", type=int, default=93)
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--tmp", default=os.environ.get("TMPDIR", "/tmp"))
    ap.add_argument("--par", type=int, default=3, help="emulator processes at once")
    a = ap.parse_args()
    if a.part:
        sys.path[0] = os.getcwd()         # import the env code of the tree we run in (cwd), not this file's tree
        dump(a)
        sys.stdout.flush()
        os._exit(0)                       # skip the core's teardown abort
    here = os.path.dirname(os.path.abspath(__file__))
    common = ["--pool", a.pool, "--mixed-states", a.mixed_states, "--game", a.game, "--steps", str(a.steps)]
    runs = [("old", a.old_tree, {}), ("new", here, {})]
    if a.drills:
        runs.append(("dir_p0", here, {"PS2_DRILL_DIR": a.drills, "PS2_DRILL_P": "0"}))
    procs = []
    for i, (tag, tree, extra) in enumerate(runs):
        env = dict(os.environ, **ARENA, **extra)
        for k in ("PS2_DRILL_DIR", "PS2_DRILL_P"):
            if k not in extra:
                env.pop(k, None)
        env["PS2_STAGGER_FRAMES"] = env.get("PS2_STAGGER_FRAMES", "240")
        out = os.path.join(a.tmp, f"drillflag_{tag}.npz")
        cmd = [sys.executable, os.path.abspath(__file__), "--part", "ffa", "--out", out,
               "--instance", str(a.instance + i)] + common
        while len([p for p in procs if p[2].poll() is None]) >= a.par:
            time.sleep(1.0)
        procs.append((tag, out, subprocess.Popen(cmd, cwd=tree, env=env)))
    for _, _, p in procs:
        p.wait()
    ok_all = True
    ref = os.path.join(a.tmp, "drillflag_old.npz")
    for tag, out, _ in procs[1:]:
        ok, rows = compare(ref, out)
        ok_all &= ok
        for k, s0, s1, same, diff in rows:
            print(f"[cmp] {tag:6s} {k:8s} old {s0} vs {s1}: {'BIT-IDENTICAL' if same else 'DIFFERENT max|d|=%.3g' % diff}",
                  flush=True)
    print("drill flag-off bit-identity:", "PASS" if ok_all else "FAIL")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
