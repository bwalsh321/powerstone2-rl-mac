"""test_widen_paired_eval.py -- SAMPLED-move eval of a widened zip vs its parent with the SAME random numbers (Oct 14 2026,
bigger-network option). eval_parity.py --stochastic is run in-process (runpy) with load_model patched to re-seed
python/numpy/torch to --seed right after loading (load_model normally re-seeds from entropy), so parent and widened
model draw the same uniform numbers for their samples. If the widened net computes the same action distribution
(surgery_widen_net.py's gate: |prob diff| ~1e-7), every sampled move and every game is the same, step for step; a
sample can only flip where a draw lands within ~1e-7 of a cumulative-probability boundary.

    python test_widen_paired_eval.py --dump OUT.npz --model M.zip --instance I [--episodes 10] [--seed 5]   (one run)
    python test_widen_paired_eval.py --compare A.npz B.npz
Run the two dumps with the same --seed, --episodes and PS2_EVAL_INSTANCE_BASE = --instance (shard 0 start points).
"""
import argparse
import io
import os
import random
import runpy
import sys
from contextlib import redirect_stdout

import numpy as np


def dump(a):
    import torch as th
    th.set_num_threads(1)
    sys.path[0] = os.getcwd()
    import recurrent_policy
    orig_load = recurrent_policy.load_model

    def load_model(*args, **kw):
        m = orig_load(*args, **kw)
        random.seed(a.seed); np.random.seed(a.seed); th.manual_seed(a.seed)
        return m
    recurrent_policy.load_model = load_model
    acts, eps = [], []
    orig_act = recurrent_policy.PolicyRunner.act
    orig_reset = recurrent_policy.PolicyRunner.reset

    def act(self, obs, deterministic=False):
        r = orig_act(self, obs, deterministic)
        acts.append(int(np.asarray(r).ravel()[0]))
        eps.append(len(starts) - 2)        # PolicyRunner() resets once at construction, then once per round
        return r
    starts = []

    def reset(self):
        starts.append(len(acts))
        return orig_reset(self)
    recurrent_policy.PolicyRunner.act = act
    recurrent_policy.PolicyRunner.reset = reset
    sys.argv = ["eval_parity.py", "--core", os.environ["PS2_CORE"], "--game", a.game, "--states", a.states,
                "--slots", "90,91,92,93,94", "--episodes", str(a.episodes), "--model", a.model,
                "--instance", str(a.instance), "--stochastic"]
    buf = io.StringIO()
    with redirect_stdout(buf):
        try:
            runpy.run_path(os.path.join(os.getcwd(), "eval_parity.py"), run_name="__main__")
        except SystemExit:
            pass
    text = buf.getvalue()
    results = [next((w for w in ln.split() if w in ("win", "loss", "tie", "timeout")), "?")
               for ln in text.splitlines() if ln.startswith("[ep]")]
    summ = text[text.find("================ EVAL SUMMARY"):]
    np.savez(a.dump, act=np.array(acts), ep=np.array(eps), results=np.array(results),
             summary=np.frombuffer(summ.encode(), np.uint8))
    print(f"[dump] {a.model}: {len(acts)} sampled moves, {len(results)} rounds\n{summ}", flush=True)


def compare(pa, pb):
    A, B = np.load(pa), np.load(pb)
    n_ep = max(int(A["ep"].max()), int(B["ep"].max())) + 1
    same_games = 0
    for e in range(n_ep):
        x, y = A["act"][A["ep"] == e], B["act"][B["ep"] == e]
        k = next((i for i in range(min(len(x), len(y))) if x[i] != y[i]), None)
        ra = A["results"][e] if e < len(A["results"]) else "?"
        rb = B["results"][e] if e < len(B["results"]) else "?"
        same = k is None and len(x) == len(y)
        same_games += same
        print(f"[paired] round {e:2d}: {len(x)} vs {len(y)} sampled moves, "
              f"{'IDENTICAL' if same else 'first different move at step %s' % k}; result {ra} vs {rb}")
    wa, wb = int((A["results"] == "win").sum()), int((B["results"] == "win").sum())
    print(f"[paired] {same_games}/{n_ep} rounds identical move for move; wins {wa}/{len(A['results'])} "
          f"vs {wb}/{len(B['results'])}")
    return same_games == n_ep


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--dump", default="")
    ap.add_argument("--compare", nargs=2, default=None)
    ap.add_argument("--model", default="")
    ap.add_argument("--instance", type=int, default=84)
    ap.add_argument("--episodes", type=int, default=10)
    ap.add_argument("--seed", type=int, default=5)
    ap.add_argument("--states", default="./states")
    ap.add_argument("--game", default=os.path.abspath(os.path.join(os.path.dirname(__file__), "..",
                                                                    "Power Stone 2 (USA).chd")))
    a = ap.parse_args()
    if a.compare:
        sys.exit(0 if compare(*a.compare) else 1)
    dump(a)
    sys.stdout.flush()
    os._exit(0)
