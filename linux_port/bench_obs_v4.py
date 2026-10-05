"""bench_obs_v4.py -- single-env throughput with obs v4 off vs on (Oct 5 2026).

One FFASelfPlayEnv (the training env: mixed seats 0,2, joint63, taps) on --slots of --states, random learner actions,
the two policy seats driven by the zips in --pool. Prints env steps/s over --steps steps (resets included) and, with
PS2_OBS_V4=1, the time spent in the v4 reader: the shared per-frame RAM scan (ObsV4Reader._scan) and the whole
_observe_v4 call (scan + per-seat assembly), per learner step. Run once per setting (the flag is read at import):
    PS2_OBS_V4=0 python bench_obs_v4.py --pool pool160 ...      # today's contract
    PS2_OBS_V4=1 python bench_obs_v4.py --pool pool430 ...      # v4, every policy seat builds v4 (worst case)
"""
import argparse
import os
import random
import sys
import time

import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument("--pool", required=True)
ap.add_argument("--states", required=True)
ap.add_argument("--slots", default="0,12,33,55")
ap.add_argument("--steps", type=int, default=2000)
ap.add_argument("--instance", type=int, default=60)
ap.add_argument("--game", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "Power Stone 2 (USA).chd"))
ap.add_argument("--tag", default="")
a = ap.parse_args()
for k, v in dict(PS2_OBS_V2="1", PS2_OBS_V3="1", PS2_FFA_SEATS="0,2", PS2_BUTTON_TAP="1", PS2_ZERO_SUM="1",
                 PS2_START_HEALTH="0.5,1.0").items():
    os.environ.setdefault(k, v)

import torch as th  # noqa: E402
th.set_num_threads(1)
from ffa_selfplay_env import FFASelfPlayEnv  # noqa: E402

slots = [int(s) for s in a.slots.split(",")]
random.seed(0)
th.manual_seed(0)
env = FFASelfPlayEnv(core_path=os.environ["PS2_CORE"], game_path=a.game, states_dir=a.states, state_slots=slots,
                     instance_id=a.instance, bridge_dir=os.path.abspath(f"bridge_i{a.instance}"), pool_dir=a.pool)
env.set_action_mode(63)
T = {"v4": 0.0, "scan": 0.0, "n_v4": 0}
if env.OBS_V4:
    orig_v4 = env._observe_v4

    def timed_v4(obs, s, i, _o=orig_v4):
        t0 = time.perf_counter()
        _o(obs, s, i)
        T["v4"] += time.perf_counter() - t0
        T["n_v4"] += 1
        if "wrapped" not in T:
            r = env._v4
            orig_scan = r._scan

            def timed_scan(frame, _s=orig_scan):
                t1 = time.perf_counter()
                out = _s(frame)
                T["scan"] += time.perf_counter() - t1
                return out
            r._scan = timed_scan
            T["wrapped"] = r
    env._observe_v4 = timed_v4
rng = random.Random(1)
env.reset()
warm = 50
for _ in range(warm):                                  # boot / first-episode noise out of the timing
    _, _, d, _ = env.step(rng.randrange(63))
    if d:
        env.reset()
T.update(v4=0.0, scan=0.0, n_v4=0)
if "wrapped" in T:
    T["n_scans0"] = T["wrapped"].n_scans
t0, resets = time.perf_counter(), 0
for _ in range(a.steps):
    _, _, d, _ = env.step(rng.randrange(63))
    if d:
        env.reset()
        resets += 1
dt = time.perf_counter() - t0
n_scans = (T["wrapped"].n_scans - T["n_scans0"]) if "wrapped" in T else 0
print(f"[bench{(' ' + a.tag) if a.tag else ''}] obs_v4={int(env.OBS_V4)} obs_dim={env.OBS_DIM} pool={os.path.basename(a.pool.rstrip('/'))} "
      f"steps={a.steps} resets={resets} wall={dt:.1f}s -> {a.steps / dt:.1f} env steps/s; "
      f"v4 reader: {1e3 * T['v4'] / a.steps:.3f} ms/step in _observe_v4 ({T['n_v4']} calls, "
      f"{1e3 * T['v4'] / max(1, T['n_v4']):.3f} ms/call), RAM scan {1e3 * T['scan'] / a.steps:.3f} ms/step "
      f"({n_scans} scans, {1e3 * T['scan'] / max(1, n_scans):.3f} ms/scan)", flush=True)
sys.stdout.flush()
os._exit(0)
