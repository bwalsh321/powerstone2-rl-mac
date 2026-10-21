"""test_netwidth_flagoff.py -- the bigger-network option (PS2_NET_WIDTH / PS2_LSTM_HIDDEN, recurrent_policy.check_net_flags,
surgery_widen_net.py, league_surgery.txt widen<W>/lstm<H>) must be INERT for the live recipe (Oct 14 2026; same harness
shape as test_framestack_flagoff.py).

Runs the same work with the pre-change code (an export of the parent commit's linux_port, e.g.
`git archive <parent> linux_port | tar -x -C DIR`) and with this tree, and compares BIT FOR BIT:
  learner  the tree's OWN train_selfplay_async.main() on the warm zip, in-process, with the actor processes replaced by
           a fixed queue of chunks built from recorded real observations (the learner code path is untouched: load,
           [config], seam check, ppo_train.train with PS2_PPO_KL_REF=prox, save); every RNG re-seeded after each
           load_model so minibatch order is reproducible. Compared: every policy tensor and Adam moment of the saved
           zip, num_timesteps / n_updates, and the [config]/[check]/[ppo]/[stats] log lines (timings stripped);
  eval     the tree's OWN eval_parity.py (in-process with runpy, top moves, slots 90,91, paired pre-roll) on the warm
           zip: every observation the policy is handed and every action it returns, plus the summary.
Runs: old (flags unset) vs new with flags unset, vs new with PS2_NET_WIDTH=256 PS2_LSTM_HIDDEN=128 (= the zip: the
trainer checks and prints one extra [config] line, weights must still be identical) and, for eval only, new with
PS2_NET_WIDTH=512 PS2_LSTM_HIDDEN=256 (loaders must ignore the flags and build the zip's 256/128 net).
Also: new learner with PS2_NET_WIDTH=512 on the 256 zip must REFUSE (exit != 0, message names the surgery).
At most 3 emulators at a time (eval runs; instances --instance .. +2). Exit 1 on any mismatch.

    python test_netwidth_flagoff.py --old-tree /abs/export/linux_port --pool DIR --mixed-states DIR \\
        --model /abs/powerstone_v6_leg176_league.zip --real-obs /abs/real_obs.npz [--instance 70]
Each run is a subprocess with cwd = its tree (PYTHONPATH must contain "." and the harness).
"""
import argparse
import io
import os
import random
import re
import runpy
import subprocess
import sys
import time
from contextlib import redirect_stdout

import numpy as np

ARENA = dict(PS2_OBS_V2="1", PS2_OBS_V3="1", PS2_OBS_V4="1", PS2_OBS_V4_ITEMEMB="keep", PS2_OBJ_GRID_N="208",
             PS2_ZERO_SUM="1", PS2_START_HEALTH="0.5,1.0", PS2_OBS_CTX_FIX="1", PS2_OBS_STACK="2",
             PS2_ZS_TIME="1", PS2_SPECIAL_DMG_W="1.0", PS2_SPECIAL_R="700", PS2_LOST_EXTRA_W="1.0",
             PS2_SPECIAL_WINDOW="2.0", PS2_LOSS_SCALE_LV8="0.5", PS2_SPECIAL_WINDOW_CLOCK="frames",
             PS2_SPECIAL_ATTRIB="1", PS2_BUTTON_TAP="1", PS2_FFA_SEATS="0,2", PS2_POOL_SAMPLING="uniform",
             PS2_PPO_KL_REF="prox", PS2_LR="5e-5", PS2_TARGET_KL="0.03", PS2_BATCH_SIZE="256", PS2_ENV="ffa")
FLAGS = {"unset": {}, "match": dict(PS2_NET_WIDTH="256", PS2_LSTM_HIDDEN="128"),
         "wide": dict(PS2_NET_WIDTH="512", PS2_LSTM_HIDDEN="256")}
N_CHUNKS, N_ENVS, T = 4, 2, 2048          # 2 learner updates of 2 columns x 2048 steps


def seed_all(s):
    import torch as th
    random.seed(s)
    np.random.seed(s)
    th.manual_seed(s)


def make_chunks(real_obs, H):
    z = np.load(real_obs)
    obs, starts = z["obs"].astype(np.float32), z["start"].astype(np.float32)
    g = np.random.default_rng(7)
    out = []
    for i in range(N_CHUNKS):
        idx = (np.arange(T) + int(g.integers(len(obs)))) % len(obs)
        st = starts[idx].copy()
        st[0] = 1.0                                   # chunk begins at an episode start (zero LSTM state is exact)
        c = dict(actor=i % N_ENVS, version=0, versions=np.zeros(T, np.int64), obs=obs[idx],
                 actions=g.integers(0, 63, T).astype(np.int64), rewards=g.normal(0, 0.3, T).astype(np.float32),
                 episode_starts=st, values=g.normal(0, 1, T).astype(np.float32),
                 log_probs=np.log(np.full(T, 1 / 63, np.float32)) + g.normal(0, 0.1, T).astype(np.float32),
                 last_value=float(g.normal()), last_done=False)
        for k in ("h_pi", "c_pi", "h_vf", "c_vf"):
            c[k] = np.zeros((T, 1, H), np.float32)
        out.append(c)
    return out


def run_learner(a):
    """train_selfplay_async.main() with a fake multiprocessing context: no actors, a fixed chunk queue."""
    import multiprocessing
    import torch as th
    th.set_num_threads(1)
    import recurrent_policy
    orig_load = recurrent_policy.load_model

    def load_model(*args, **kw):                      # load_model re-seeds from entropy: pin it for the comparison
        m = orig_load(*args, **kw)
        seed_all(123)
        return m
    recurrent_policy.load_model = load_model
    chunks = make_chunks(a.real_obs, a.lstm_h)

    class Q:
        def __init__(self, *args, **kw):
            self.items = list(chunks)

        def get(self, timeout=None):
            return self.items.pop(0)

        def put(self, x):
            self.items.append(x)

    class Conn:
        def send(self, x):
            pass

        def poll(self, *args):
            return False

    class Proc:
        def __init__(self, *args, **kw):
            pass

        def start(self):
            pass

        def kill(self):
            pass

        def is_alive(self):
            return True

    class Ctx:
        Queue = Q
        Process = Proc

        @staticmethod
        def Pipe():
            return Conn(), Conn()
    multiprocessing.get_context = lambda *args, **kw: Ctx()
    import train_selfplay_async
    train_selfplay_async.main()                       # saves PS2_OUT, prints "leg complete", os._exit(0)


def dump_eval(a):
    import torch as th
    th.set_num_threads(1)
    seed_all(1)
    import recurrent_policy
    rec_obs, rec_act = [], []
    orig_act = recurrent_policy.PolicyRunner.act
    widths = []

    def act(self, obs, deterministic=False):
        if not widths:
            widths.append(str(recurrent_policy.net_widths(self.model.policy)) if hasattr(recurrent_policy, "net_widths")
                          else "n/a")
        rec_obs.append(np.asarray(obs, np.float32).copy())
        r = orig_act(self, obs, deterministic)
        rec_act.append(int(np.asarray(r).ravel()[0]))
        return r
    recurrent_policy.PolicyRunner.act = act
    sys.argv = ["eval_parity.py", "--core", os.environ["PS2_CORE"], "--game", a.game, "--slots", "90,91",
                "--episodes", str(a.eval_episodes), "--model", a.model, "--instance", str(a.instance), "--states", a.states]
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
    print(f"[dump-eval] steps={len(rec_obs)} obs_width={rec_obs[0].shape[0]} built_net={widths[0]} exit={code}\n{summ}",
          flush=True)


def cmp_npz(ref, new):
    r, n = np.load(ref), np.load(new)
    rows, ok = [], True
    for k in r.files:
        x, y = r[k], n[k]
        same = x.shape == y.shape and x.dtype == y.dtype and x.tobytes() == y.tobytes()
        rows.append((k, tuple(x.shape), tuple(y.shape), same))
        ok &= same
    return ok, rows


def cmp_zip(ref, new):
    """Bitwise comparison of two trainer outputs: policy tensors, Adam state, clocks."""
    from recurrent_policy import load_model
    A, B = load_model(ref), load_model(new)
    sa, sb = A.policy.state_dict(), B.policy.state_dict()
    bad_t = [k for k in sa if k not in sb or sa[k].shape != sb[k].shape or not bool((sa[k] == sb[k]).all())]
    oa, ob = A.policy.optimizer.state_dict()["state"], B.policy.optimizer.state_dict()["state"]
    bad_o = [i for i in oa for key in ("step", "exp_avg", "exp_avg_sq")
             if not bool((oa[i][key] == ob[i][key]).all())]
    clocks = (A.num_timesteps, A._n_updates) == (B.num_timesteps, B._n_updates)
    return not bad_t and not bad_o and clocks, len(sa), bad_t, len(oa), bad_o, (A.num_timesteps, A._n_updates)


def log_lines(path):
    keep = []
    for ln in open(path, errors="replace"):
        if ln.startswith(("[config]", "[check]", "[ppo]", "[stats]", "[learner]", "leg complete")):
            ln = re.sub(r"train=[0-9.]+s", "train=*s", ln)
            ln = re.sub(r"[0-9.]+ steps/s|nan steps/s", "* steps/s", ln)
            ln = re.sub(r"warm=\S+|pool=\S+", "", ln)
            ln = re.sub(r"leg complete -> .*", "leg complete -> <PS2_OUT>.zip", ln)
            keep.append(ln.rstrip())
    return keep


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", default="")
    ap.add_argument("--out", default="")
    ap.add_argument("--old-tree", default="")
    ap.add_argument("--pool", required=True)
    ap.add_argument("--mixed-states", required=True)
    ap.add_argument("--states", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "states")))
    ap.add_argument("--model", required=True)
    ap.add_argument("--real-obs", required=True)
    ap.add_argument("--lstm-h", type=int, default=128)
    ap.add_argument("--game", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                                                    "Power Stone 2 (USA).chd")))
    ap.add_argument("--instance", type=int, default=70)
    ap.add_argument("--eval-episodes", type=int, default=2)
    ap.add_argument("--tmp", default=os.environ.get("TMPDIR", "/tmp"))
    a = ap.parse_args()
    if a.part:
        sys.path[0] = os.getcwd()         # import the code of the tree we run in (cwd), not this file's tree
        if a.part == "learner":
            run_learner(a)
        else:
            dump_eval(a)
        sys.stdout.flush()
        os._exit(0)                       # skip the core's teardown abort
    here = os.path.dirname(os.path.abspath(__file__))
    common = ["--pool", a.pool, "--mixed-states", a.mixed_states, "--game", a.game, "--model", a.model,
              "--real-obs", a.real_obs, "--states", a.states, "--eval-episodes", str(a.eval_episodes), "--lstm-h", str(a.lstm_h)]

    def env_for(flag, out_zip=None):
        env = dict(os.environ, **ARENA)
        for k in ("PS2_NET_WIDTH", "PS2_LSTM_HIDDEN", "PS2_DEMOS", "PS2_ENT_COEF"):
            env.pop(k, None)
        env.update(FLAGS[flag])
        env.update(PS2_STAGGER_FRAMES=env.get("PS2_STAGGER_FRAMES", "240"), PS2_WARM=a.model, PS2_FRESH="1",
                   PS2_NACTORS=str(N_ENVS), PS2_NENVS=str(N_ENVS), PS2_TOTAL_STEPS=str(N_CHUNKS * T),
                   PS2_POOL=os.path.join(a.tmp, "nwflag_pool"), PS2_CKPT_DIR=os.path.join(a.tmp, "nwflag_ckpt"),
                   PS2_STATES_DIR=a.mixed_states, OMP_NUM_THREADS="1", MKL_NUM_THREADS="1")
        if out_zip:
            env["PS2_OUT"] = out_zip.removesuffix(".zip")
        return env

    # 1) eval runs (3 emulators at once): old/unset, new/unset, new/wide
    evals = [("old", a.old_tree, "unset"), ("new", here, "unset"), ("new", here, "wide")]
    procs = []
    for j, (tag, tree, flag) in enumerate(evals):
        out = os.path.join(a.tmp, f"nwflag_eval_{flag}_{tag}.npz")
        log = open(out.replace(".npz", ".log"), "w")
        cmd = [sys.executable, os.path.abspath(__file__), "--part", "eval", "--out", out,
               "--instance", str(a.instance + j)] + common
        e = env_for(flag)
        e["PS2_EVAL_INSTANCE_BASE"] = str(a.instance + j)   # every run is shard 0 -> identical paired pre-roll
        procs.append(subprocess.Popen(cmd, cwd=tree, env=e, stdout=log, stderr=subprocess.STDOUT))
        time.sleep(3.0)
    # 2) learner runs, sequential, no emulators
    learners = [("old", a.old_tree, "unset"), ("new", here, "unset"), ("new", here, "match")]
    for tag, tree, flag in learners:
        out = os.path.join(a.tmp, f"nwflag_learner_{flag}_{tag}.zip")
        cmd = [sys.executable, os.path.abspath(__file__), "--part", "learner", "--out", out] + common
        with open(out.replace(".zip", ".log"), "w") as log:
            subprocess.call(cmd, cwd=tree, env=env_for(flag, out), stdout=log, stderr=subprocess.STDOUT)
    refuse_log = os.path.join(a.tmp, "nwflag_learner_wide_refuse.log")
    e = env_for("wide", os.path.join(a.tmp, "nwflag_learner_wide_refuse.zip"))
    with open(refuse_log, "w") as log:
        rc_refuse = subprocess.call([sys.executable, os.path.abspath(__file__), "--part", "learner", "--out", "x"]
                                    + common, cwd=here, env=e, stdout=log, stderr=subprocess.STDOUT)
    for p in procs:
        p.wait()

    ok_all = True
    ref = os.path.join(a.tmp, "nwflag_learner_unset_old.zip")
    ref_lines = log_lines(ref.replace(".zip", ".log"))
    for flag in ("unset", "match"):
        new = os.path.join(a.tmp, f"nwflag_learner_{flag}_new.zip")
        if not (os.path.exists(ref) and os.path.exists(new)):
            print(f"[cmp] learner {flag}: missing output (see {new.replace('.zip', '.log')})")
            ok_all = False
            continue
        ok, nt, bad_t, no, bad_o, clk = cmp_zip(ref, new)
        new_lines = log_lines(new.replace(".zip", ".log"))
        extra = [ln for ln in new_lines if ln not in ref_lines]
        missing = [ln for ln in ref_lines if ln not in new_lines]
        lines_ok = not missing and all("zip matches" in ln for ln in extra) and (flag != "unset" or not extra)
        ok_all &= ok and lines_ok
        print(f"[cmp] learner flags={flag:6s} old vs new after {N_CHUNKS * T // (N_ENVS * T)} updates: "
              f"{nt} policy tensors {'BIT-IDENTICAL' if not bad_t else 'DIFFERENT ' + str(bad_t)}; {no} Adam entries "
              f"{'BIT-IDENTICAL' if not bad_o else 'DIFFERENT ' + str(bad_o)}; clocks {clk}; log lines "
              f"{len(ref_lines)} old / {len(new_lines)} new, missing {len(missing)}, extra {extra or 0} -> "
              f"{'PASS' if ok and lines_ok else 'FAIL'}", flush=True)
    rtxt = open(refuse_log, errors="replace").read()
    rmsg = [ln for ln in rtxt.splitlines() if "PS2_NET_WIDTH=512" in ln]
    refuse_ok = rc_refuse != 0 and bool(rmsg) and "leg complete" not in rtxt
    ok_all &= refuse_ok
    print(f"[cmp] learner PS2_NET_WIDTH=512 on the 256 zip: exit {rc_refuse}, "
          f"{rmsg[-1].strip() if rmsg else 'no message'} -> {'REFUSED (PASS)' if refuse_ok else 'FAIL'}", flush=True)
    for flag in ("unset", "wide"):
        r = os.path.join(a.tmp, "nwflag_eval_unset_old.npz")
        n = os.path.join(a.tmp, f"nwflag_eval_{flag}_new.npz")
        if not (os.path.exists(r) and os.path.exists(n)):
            print(f"[cmp] eval {flag}: missing dump (see {n.replace('.npz', '.log')})")
            ok_all = False
            continue
        ok, rows = cmp_npz(r, n)
        ok_all &= ok
        for k, s0, s1, same in rows:
            print(f"[cmp] eval    flags={flag:6s} {k:8s} old {s0} vs new {s1}: "
                  f"{'BIT-IDENTICAL' if same else 'DIFFERENT'}", flush=True)
    print("net-width flag-off bit-identity:", "PASS" if ok_all else "FAIL")
    return 0 if ok_all else 1


if __name__ == "__main__":
    sys.exit(main())
