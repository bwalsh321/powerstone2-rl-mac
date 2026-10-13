"""test_framestack_flagoff.py -- the frame-stack option (PS2_OBS_STACK=2, obs_stack.stack_for, surgery_frame_stack.py)
must be INERT for the live recipe: PS2_OBS_STACK unset or 7 (Oct 13 2026; same harness as test_hunter_flagoff.py).

Runs the same seeded steps with the pre-change code (an export of the parent commit's linux_port, e.g.
`git archive -o old.tar <parent> linux_port`) and with this tree, and compares BIT FOR BIT:
  train  the actor's learner stream: FFASelfPlayEnv (mixed seats 0,2, joint63, obs v4, the live league_env.txt arena
         flags, v4 pool policies on the policy seats) wrapped in the tree's obs_stack.StackedEnv with K taken from
         PS2_OBS_STACK exactly as train_selfplay_async.py does (default 1); seeded random actions; every stacked obs,
         reward and done, on slot 30 (P1/P3 human) and 55 (all COM);
  eval   the tree's OWN eval_parity.py (run in-process with runpy, top moves, slots 90,91, paired pre-roll) on the
         leg 169 zip: every stacked observation the policy is handed and every action it returns (PolicyRunner.act
         is wrapped to record them), plus the summary it prints.
Runs: old/new x {PS2_OBS_STACK unset (train: K=1, the trainer's default), PS2_OBS_STACK=7}; 4 emulators at a time
(instances --instance .. +3). Exit 1 on any mismatch.

    python test_framestack_flagoff.py --old-tree /path/to/export/linux_port --pool DIR_WITH_V4_ZIPS \\
        --mixed-states /abs/states_mixed --model /abs/powerstone_v6_leg169_league.zip [--instance 70]
Each run is a subprocess with cwd = its tree (PYTHONPATH must contain "." and the harness).
"""
import argparse
import io
import os
import random
import runpy
import subprocess
import sys
import time
from contextlib import redirect_stdout

import numpy as np

ARENA = dict(PS2_OBS_V2="1", PS2_OBS_V3="1", PS2_OBS_V4="1", PS2_OBS_V4_ITEMEMB="keep", PS2_OBJ_GRID_N="208",
             PS2_ZERO_SUM="1", PS2_START_HEALTH="0.5,1.0", PS2_OBS_CTX_FIX="1",
             PS2_ZS_TIME="1", PS2_SPECIAL_DMG_W="1.0", PS2_SPECIAL_R="700", PS2_LOST_EXTRA_W="1.0",
             PS2_SPECIAL_WINDOW="2.0", PS2_LOSS_SCALE_LV8="0.5", PS2_SPECIAL_WINDOW_CLOCK="frames",
             PS2_SPECIAL_ATTRIB="1", PS2_BUTTON_TAP="1", PS2_FFA_SEATS="0,2", PS2_POOL_SAMPLING="uniform",
             PS2_PPO_KL_REF="prox")
SLOTS = (30, 55)


def seed_all(s):
    import torch as th
    random.seed(s)
    np.random.seed(s)
    th.manual_seed(s)


def dump_train(a):
    import torch as th
    th.set_num_threads(1)
    from ffa_selfplay_env import FFASelfPlayEnv
    from obs_stack import StackedEnv
    seed_all(1)
    env = FFASelfPlayEnv(core_path=os.environ["PS2_CORE"], game_path=a.game, states_dir=a.mixed_states,
                         instance_id=a.instance, state_slots=[SLOTS[0]],
                         bridge_dir=os.path.abspath(f"bridge_i{a.instance}"), pool_dir=a.pool)
    env.set_action_mode(63)
    K = int(os.environ.get("PS2_OBS_STACK", "1"))            # train_selfplay_async.py's reading of the flag
    senv = StackedEnv(env, K) if K > 1 else env               # actor_main: wrap only when K > 1
    out = {}
    for slot in SLOTS:
        seed_all(100 + slot)
        env.STATE_SLOTS = [slot]
        obs = [np.asarray(senv.reset(), np.float32).copy()]
        rew, done_ = [], []
        rng = random.Random(slot)
        for _ in range(a.steps):
            o, r, d, info = senv.step(rng.randrange(63))
            obs.append(np.asarray(o, np.float32).copy()); rew.append(float(r)); done_.append(bool(d))
            if d:
                obs.append(np.asarray(senv.reset(), np.float32).copy())
        out[f"obs_{slot}"] = np.stack(obs)
        out[f"rew_{slot}"] = np.array(rew, np.float64)
        out[f"done_{slot}"] = np.array(done_)
    np.savez(a.out, **out)
    print(f"[dump-train] K={K} obs_width={out[f'obs_{SLOTS[0]}'].shape[1]} steps={a.steps} -> {a.out}", flush=True)


def dump_eval(a):
    import torch as th
    th.set_num_threads(1)
    seed_all(1)
    import recurrent_policy
    rec_obs, rec_act = [], []
    orig_act = recurrent_policy.PolicyRunner.act

    def act(self, obs, deterministic=False):
        rec_obs.append(np.asarray(obs, np.float32).copy())
        r = orig_act(self, obs, deterministic)
        rec_act.append(int(np.asarray(r).ravel()[0]))
        return r
    recurrent_policy.PolicyRunner.act = act
    sys.argv = ["eval_parity.py", "--core", os.environ["PS2_CORE"], "--game", a.game, "--slots", "90,91",
                "--episodes", str(a.eval_episodes), "--model", a.model, "--instance", str(a.instance)]
    buf = io.StringIO()
    code = 0
    with redirect_stdout(buf):
        try:
            runpy.run_path(os.path.join(os.getcwd(), "eval_parity.py"), run_name="__main__")
        except SystemExit as e:
            code = e.code or 0
    text = buf.getvalue()
    summ = text[text.find("================ EVAL SUMMARY"):] if "EVAL SUMMARY" in text else text[-2000:]
    np.savez(a.out, obs=np.stack(rec_obs), act=np.array(rec_act), summary=np.frombuffer(summ.encode(), np.uint8),
             exit=np.array([code]))
    print(f"[dump-eval] steps={len(rec_obs)} obs_width={rec_obs[0].shape[0]} exit={code}\n{summ}", flush=True)


def compare(ref, new):
    r, n = np.load(ref), np.load(new)
    rows, ok = [], True
    for k in r.files:
        x, y = r[k], n[k]
        same = x.shape == y.shape and x.dtype == y.dtype and x.tobytes() == y.tobytes()
        diff = (float(np.abs(x.astype(np.float64) - y.astype(np.float64)).max())
                if x.shape == y.shape and x.size and x.dtype != np.uint8 else -1.0)
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
    ap.add_argument("--model", required=True)
    ap.add_argument("--game", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                                                    "Power Stone 2 (USA).chd")))
    ap.add_argument("--instance", type=int, default=70)
    ap.add_argument("--steps", type=int, default=300)
    ap.add_argument("--eval-episodes", type=int, default=2)
    ap.add_argument("--tmp", default=os.environ.get("TMPDIR", "/tmp"))
    a = ap.parse_args()
    if a.part:
        sys.path[0] = os.getcwd()         # import the code of the tree we run in (cwd), not this file's tree
        (dump_train if a.part == "train" else dump_eval)(a)
        sys.stdout.flush()
        os._exit(0)                       # skip the core's teardown abort
    here = os.path.dirname(os.path.abspath(__file__))
    common = ["--pool", a.pool, "--mixed-states", a.mixed_states, "--game", a.game, "--steps", str(a.steps),
              "--model", a.model, "--eval-episodes", str(a.eval_episodes)]
    # two batches of 4 emulators: all OLD runs, then all NEW runs; a config keeps the SAME instance id in both
    # batches (eval_parity's paired pre-roll depends on the shard = instance id)
    configs = [(part, flag) for part in ("train", "eval") for flag in ("unset", "7")]
    procs = []
    for tag, tree in (("old", a.old_tree), ("new", here)):
        batch = []
        for j, (part, flag) in enumerate(configs):
            env = dict(os.environ, **ARENA)
            env.pop("PS2_OBS_STACK", None)
            env.pop("PS2_STACK_OFFSETS", None)
            if flag != "unset":
                env["PS2_OBS_STACK"] = flag
            env["PS2_STAGGER_FRAMES"] = env.get("PS2_STAGGER_FRAMES", "240")
            out = os.path.join(a.tmp, f"fsflag_{part}_{flag}_{tag}.npz")
            cmd = [sys.executable, os.path.abspath(__file__), "--part", part, "--out", out,
                   "--instance", str(a.instance + j)] + common
            log = open(out.replace(".npz", ".log"), "w")
            batch.append(subprocess.Popen(cmd, cwd=tree, env=env, stdout=log, stderr=subprocess.STDOUT))
            time.sleep(3.0)
        for p in batch:
            p.wait()
        procs += batch
    ok_all = True
    for part in ("train", "eval"):
        for flag in ("unset", "7"):
            ref = os.path.join(a.tmp, f"fsflag_{part}_{flag}_old.npz")
            new = os.path.join(a.tmp, f"fsflag_{part}_{flag}_new.npz")
            if not (os.path.exists(ref) and os.path.exists(new)):
                print(f"[cmp] {part} PS2_OBS_STACK={flag}: missing dump (see {ref.replace('.npz', '.log')})")
                ok_all = False
                continue
            ok, rows = compare(ref, new)
            ok_all &= ok
            for k, s0, s1, same, diff in rows:
                print(f"[cmp] {part:5s} PS2_OBS_STACK={flag:5s} {k:8s} old {s0} vs new {s1}: "
                      f"{'BIT-IDENTICAL' if same else 'DIFFERENT max|d|=%.3g' % diff}", flush=True)
    print("frame-stack flag-off bit-identity:", "PASS" if ok_all else "FAIL")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
