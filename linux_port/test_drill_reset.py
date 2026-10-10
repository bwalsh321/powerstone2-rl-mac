"""test_drill_reset.py -- practice start points end to end in the training env (Oct 10 2026).

Loads --n random drills (drill_capture.py output) through FFASelfPlayEnv's drill reset (PS2_DRILL_P=1, the live arena
flags, mixed seats 0,2) and plays each out with the --model policy (sampled actions, frame stack, as the trainer's
actors do). Per drill: the load succeeds, the tracked opponent set, how many are alive, health right after the load vs
the capture's record (the episode must start AT the saved moment: no pre-roll, no start-health draw), no pool policy
attached, every observation finite, and the episode ends in a win / loss (or the FFA step cap). Exit 1 on a failure.

    PS2_DRILL_DIR=../drills/leg155_rl python test_drill_reset.py --model ./powerstone_v6_leg155_league.zip \\
        --mixed-states ./states_mixed --pool ./pool_x --n 20 --instance 93
"""
import argparse
import json
import os
import random
import sys

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--model", required=True)
ap.add_argument("--mixed-states", default="./states_mixed")
ap.add_argument("--pool", required=True)
ap.add_argument("--game", default="../Power Stone 2 (USA).chd")
ap.add_argument("--n", type=int, default=20)
ap.add_argument("--seed", type=int, default=7)
ap.add_argument("--instance", type=int, default=93)
a = ap.parse_args()
assert os.environ.get("PS2_DRILL_DIR"), "set PS2_DRILL_DIR"
os.environ["PS2_DRILL_P"] = "1"

import torch as th
th.set_num_threads(1)
random.seed(a.seed); np.random.seed(a.seed); th.manual_seed(a.seed)
from ffa_selfplay_env import FFASelfPlayEnv
from obs_stack import FrameStack, kd_for
from recurrent_policy import PolicyRunner, load_model

env = FFASelfPlayEnv(core_path=os.environ["PS2_CORE"], game_path=a.game, states_dir=a.mixed_states,
                     instance_id=a.instance, state_slots=[55], bridge_dir=os.path.abspath(f"bridge_i{a.instance}"),
                     pool_dir=a.pool)
model = load_model(a.model)
env.set_action_mode(int(model.action_space.n))
K, d = kd_for(model)
runner = PolicyRunner(model)
all_drills = list(env._drills)
picks = random.sample(all_drills, min(a.n, len(all_drills)))
rows, fails = [], []
for meta in picks:
    env._drills = [meta]                       # reset() draws from this list (p = 1)
    try:
        o = np.asarray(env.reset(), np.float32)
    except Exception as e:                      # noqa: BLE001
        fails.append(f"{meta['drill']}: reset raised {type(e).__name__}: {e}")
        continue
    s = env.prev
    h0 = [float(x) for x in s["h"]]
    ref = (meta.get("at") or {}).get("h")
    hdiff = max(abs(x - y) for x, y in zip(h0, ref)) if ref else float("nan")
    pool_attached = any(v.model is not None for v in env._views.values())
    alive0 = [j for j in env._active_opp if env._alive(env.prev_health[j])]
    finite = bool(np.isfinite(o).all())
    fs = FrameStack(K, d); obs = fs.reset(o[:d]); runner.reset()
    ret, steps, done, info = 0.0, 0, False, {}
    while not done:
        act = runner.act(obs, deterministic=False)
        o, r, done, info = env.step(int(act))
        o = np.asarray(o, np.float32)
        finite &= bool(np.isfinite(o).all()) and bool(np.isfinite(r))
        obs = fs.push(o[:d]); ret += float(r); steps += 1
    res = info.get("result", "timeout")
    row = dict(drill=meta["drill"], slot=meta["slot"], kind=meta.get("kind"), ko_was=meta.get("seconds_before_ko"),
               active=list(env._active_opp), alive_at_start=len(alive0), h_start=[round(x) for x in h0],
               h_diff_vs_capture=round(hdiff, 1), pool_attached=pool_attached, finite=finite, result=res, steps=steps,
               ret=round(ret, 2), ep_slot=env._episode_slot)
    rows.append(row)
    print("[drilltest] " + json.dumps(row), flush=True)
    if pool_attached:
        fails.append(f"{meta['drill']}: pool policy attached")
    if not finite:
        fails.append(f"{meta['drill']}: non-finite obs/reward")
    if len(env._active_opp) < 1 or not alive0:
        fails.append(f"{meta['drill']}: no live opponent tracked")
    if res not in ("win", "loss", "timeout"):
        fails.append(f"{meta['drill']}: result {res}")
    if env._episode_slot != meta["slot"]:
        fails.append(f"{meta['drill']}: episode slot {env._episode_slot} != drill slot {meta['slot']}")
n = len(rows)
w = sum(r["result"] == "win" for r in rows); l = sum(r["result"] == "loss" for r in rows)
print(f"[drilltest] loaded {n}/{len(picks)}  win {w}  loss {l}  timeout {n - w - l}  "
      f"alive-at-start hist {dict(sorted(__import__('collections').Counter(r['alive_at_start'] for r in rows).items()))}  "
      f"max h_diff {max((r['h_diff_vs_capture'] for r in rows), default=float('nan'))}  "
      f"mean len {np.mean([r['steps'] for r in rows]) if rows else 0:.0f}", flush=True)
for f in fails:
    print("[drilltest] FAIL " + f, flush=True)
print("drill reset test:", "PASS" if not fails else "FAIL", flush=True)
sys.stdout.flush()
os._exit(0 if not fails else 1)
