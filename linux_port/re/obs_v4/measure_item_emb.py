"""measure_item_emb.py <model_zip> [--steps N] [--slot S] [--instance 8] -- how much does a trained policy lean on
obs[12..17], the slot-hash "item embedding"? (PROPOSAL tool for the OBS_V4_SPEC.md [12..17] decision.)

Runs the real env (PowerStoneEnvLibretro; obs version follows the model: 122 -> v2, 160 -> v3) with the model
acting on the REAL observation, and at every step also evaluates it with obs[12..17] zeroed in every stacked
frame. Reports: steps where the embedding is non-zero, greedy-action agreement, mean total-variation distance
between the two action distributions, and value change. Feed-forward (stacked) models: exact logits. Recurrent
models: greedy agreement of two runners (real stream acts; zeroed stream shadows with its own LSTM state).
    PS2_OBS_V2=1 [PS2_OBS_V3=1] PYTHONPATH=../sdlarch-rl:. python re/obs_v4/measure_item_emb.py X.zip --steps 1500
"""
import argparse
import os
import sys

import numpy as np
import torch as th

HERE = os.path.dirname(os.path.abspath(__file__))
LP = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, LP)

ap = argparse.ArgumentParser()
ap.add_argument("model")
ap.add_argument("--steps", type=int, default=1500)
ap.add_argument("--slot", type=int, default=3)
ap.add_argument("--instance", type=int, default=8)
a = ap.parse_args()

from surgery_widen_v4 import load_any  # noqa: E402

M, rec = load_any(a.model)
n_in = int(M.observation_space.shape[0])
d = 160 if n_in % 160 == 0 and os.environ.get("PS2_OBS_V3") == "1" else 122
assert n_in % d == 0, f"model obs {n_in} vs env per-frame {d}: set PS2_OBS_V3=1 for a 160-dim model"
K = n_in // d
from obs_stack import FrameStack  # noqa: E402
from powerstone_env_libretro import PowerStoneEnvLibretro  # noqa: E402

core = os.path.expanduser("~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib"
                          if os.uname().sysname == "Darwin" else "~/cores/flycast_libretro.so")
env = PowerStoneEnvLibretro(core_path=core, game_path=os.path.join(LP, "..", "Power Stone 2 (USA).chd"),
                            states_dir=os.path.join(LP, "states"), state_slots=[a.slot], instance_id=a.instance,
                            bridge_dir=os.path.join(os.environ.get("TMPDIR", "/tmp"), f"bridge_itememb_{a.instance}"))
assert env.OBS_DIM == d


def zero(o):
    o = o.copy()
    o[12:18] = 0.0
    return o


fr, fz = FrameStack(K, d), FrameStack(K, d)
obs = env.reset()
xr, xz = fr.reset(obs), fz.reset(zero(obs))
nz = agree = agree_f = n = 0
tv, dv, flag = [], [], []
if rec:
    from recurrent_policy import PolicyRunner
    rr, rz = PolicyRunner(M), PolicyRunner(M)
with th.no_grad():
    while n < a.steps:
        f_ = np.abs(xr - xz).sum() > 0          # any stacked frame carries a non-zero embedding
        nz += int(f_)
        flag.append(bool(f_))
        if rec:
            act = int(rr.act(xr, deterministic=True))
            same = int(act == int(rz.act(xz, deterministic=True)))
            agree += same
            agree_f += same * int(f_)
        else:
            pr = M.policy.get_distribution(th.as_tensor(xr[None])).distribution.probs[0]
            pz = M.policy.get_distribution(th.as_tensor(xz[None])).distribution.probs[0]
            tv.append(0.5 * float((pr - pz).abs().sum()))
            dv.append(float((M.policy.predict_values(th.as_tensor(xr[None])) -
                             M.policy.predict_values(th.as_tensor(xz[None]))).abs()))
            same = int(pr.argmax() == pz.argmax())
            agree += same
            agree_f += same * int(f_)
            act = int(th.distributions.Categorical(probs=pr).sample())
        obs, r, done, info = env.step(act)
        n += 1
        if done:
            obs = env.reset()
            xr, xz = fr.reset(obs), fz.reset(zero(obs))
            if rec:
                rr.reset(); rz.reset()
        else:
            xr, xz = fr.push(obs), fz.push(zero(obs))
msg = (f"item-emb reliance of {os.path.basename(a.model)} ({'SkipLSTM' if rec else 'MLP'}, K={K}, {d}/frame) over "
       f"{n} steps on slot {a.slot}: embedding non-zero (any stacked frame) on {nz}/{n} steps; greedy agreement real vs zeroed {agree}/{n} ({agree_f}/{nz} on steps with an embedding)")
if tv:
    tv, dv, flag = np.array(tv), np.array(dv), np.array(flag[:len(tv)])
    sub = tv[flag] if flag.any() else np.zeros(1)
    msg += (f"; on steps WITH an embedding: action-distribution TV distance mean {sub.mean():.4f} "
            f"(p90 {np.percentile(sub, 90):.4f}, max {sub.max():.4f}), |value change| mean "
            f"{(dv[flag] if flag.any() else np.zeros(1)).mean():.4f}")
print(msg, flush=True)
os._exit(0)
