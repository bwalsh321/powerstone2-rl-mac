"""test_surgery_v4.py -- offline check of surgery_widen_v4.py (no emulator, no real checkpoint needed).

Builds synthetic parents shaped like the live lineage (K=7 x 160 obs, 63 actions, net_arch 256x256):
  1. PPO MLP (stacked)                      -- always
  2. RecurrentPPO SkipLSTMPolicy, hidden 128 -- when sb3_contrib is importable (the 9950X venv has it)
randomises their weights (so zero columns would be noticed), widens each to 430/frame with and without
--zero-item-emb, saves/reloads the widened zip, and checks logits/values equal the parent's for random inputs
whose new v4 dims are random. Run from linux_port/:  python re/obs_v4/test_surgery_v4.py [--tmp DIR]
"""
import argparse
import os
import sys
import tempfile

import numpy as np
import torch as th

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..")))
import gymnasium  # noqa: E402
import surgery_widen_v4 as SW  # noqa: E402

K, D_IN, D_OUT, N_ACT = 7, 160, 430, 63


class SpaceEnv(gymnasium.Env):
    def __init__(self, d):
        self.observation_space = gymnasium.spaces.Box(-5.0, 5.0, (d,), np.float32)
        self.action_space = gymnasium.spaces.Discrete(N_ACT)

    def reset(self, *, seed=None, options=None):
        return np.zeros(self.observation_space.shape, np.float32), {}

    def step(self, a):
        return np.zeros(self.observation_space.shape, np.float32), 0.0, False, False, {}


def randomise(model, seed=5):
    g = th.Generator().manual_seed(seed)
    with th.no_grad():
        for p in model.policy.parameters():
            p.copy_(th.randn(p.shape, generator=g) * 0.1)


def main(tmp):
    fails = []
    parents = []
    from stable_baselines3 import PPO
    m = PPO("MlpPolicy", SpaceEnv(K * D_IN), policy_kwargs=dict(net_arch=[256, 256]), device="cpu", verbose=0)
    randomise(m)
    parents.append(("MLP", m, False))
    try:
        from sb3_contrib import RecurrentPPO
        from recurrent_policy import SkipLSTMPolicy
        r = RecurrentPPO(SkipLSTMPolicy, SpaceEnv(K * D_IN), device="cpu", verbose=0, seed=0,
                         policy_kwargs=dict(net_arch=[256, 256], lstm_hidden_size=128, lstm_input_dim=D_IN,
                                            n_lstm_layers=1, shared_lstm=False, enable_critic_lstm=True))
        randomise(r)
        parents.append(("SkipLSTM", r, True))
    except ImportError as e:
        print(f"[surgery] SkipLSTM path SKIPPED (sb3_contrib not importable: {e})")
    for label, src, rec in parents:
        for zi in (False, True):
            dst, k, widened = SW.widen(src, rec, D_IN, D_OUT, zero_item=zi)
            path = os.path.join(tmp, f"v4_{label}_{int(zi)}")
            dst.save(path)
            dst2, rec2 = SW.load_any(path + ".zip")
            assert rec2 == rec
            wl, wv = SW.check_equivalence(src, dst2, rec, k, D_IN, D_OUT, zero_item=zi)
            ok = wl < 1e-4 and wv < 1e-4 and int(dst2.observation_space.shape[0]) == K * D_OUT
            if rec:
                ok = ok and int(dst2.policy.lstm_actor.input_size) == D_OUT
            # the zero-item variant must actually differ from the parent on inputs with a non-zero [12..17]
            if zi:
                x = np.random.default_rng(0).uniform(-2, 2, (64, K * D_IN)).astype(np.float32)
                if not rec:
                    with th.no_grad():
                        lp = src.policy.get_distribution(th.as_tensor(x)).distribution.logits
                        xw = np.zeros((64, K * D_OUT), np.float32)
                        for j in range(K):
                            xw[:, j * D_OUT:j * D_OUT + D_IN] = x[:, j * D_IN:(j + 1) * D_IN]
                        lw = dst2.policy.get_distribution(th.as_tensor(xw)).distribution.logits
                    ok = ok and float((lp - lw).abs().max()) > 1e-3
            print(f"[surgery] {label:8s} zero_item_emb={zi!s:5s} widened {widened} -> max|dlogit| {wl:.1e} "
                  f"max|dvalue| {wv:.1e} -> {'PASS' if ok else 'FAIL'}")
            if not ok:
                fails.append((label, zi))
            for f in os.listdir(tmp):
                os.remove(os.path.join(tmp, f))
    print(f"surgery v4 tests: {len(parents) * 2 - len(fails)}/{len(parents) * 2} passed -> {'PASS' if not fails else 'FAIL'}")
    return 1 if fails else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tmp", default="")
    a = ap.parse_args()
    sys.exit(main(a.tmp or tempfile.mkdtemp(prefix="surg_v4_")))
