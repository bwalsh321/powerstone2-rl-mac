"""surgery_lstm.py <in_zip> <out_zip> [--hidden 128] — turn a (stacked) PPO MLP policy into a
RecurrentPPO SkipLSTMPolicy WITHOUT changing its behaviour (Oct 2 2026; recurrent_policy.py).

The MLP heads of the new policy read [features, lstm_out]: the parent's first-layer weights go into the
feature columns, the lstm columns start at ZERO, every other MLP / head tensor is copied verbatim, and
the LSTMs keep their fresh initialisation (their output is multiplied by zero until training moves those
columns). Hyperparameters, num_timesteps and n_updates are carried over. Check with equivalence_lstm.py.
"""
import argparse

import gymnasium
import numpy as np
import torch as th
from sb3_contrib import RecurrentPPO
from stable_baselines3 import PPO

from obs_stack import kd_for
from recurrent_policy import CUSTOM_OBJECTS, SkipLSTMPolicy

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("dst")
ap.add_argument("--hidden", type=int, default=128)
ap.add_argument("--seed", type=int, default=0)
a = ap.parse_args()
th.manual_seed(a.seed)

src = PPO.load(a.src.removesuffix(".zip"), device="cpu", custom_objects=CUSTOM_OBJECTS)
K, d = kd_for(src)
D = int(src.observation_space.shape[0])


class SpaceEnv(gymnasium.Env):
    def __init__(self):
        self.observation_space = src.observation_space
        self.action_space = src.action_space
    def reset(self, *, seed=None, options=None): return np.zeros(D, np.float32), {}
    def step(self, action): return np.zeros(D, np.float32), 0.0, False, False, {}


pk = dict(src.policy_kwargs or {})
pk.update(lstm_hidden_size=a.hidden, lstm_input_dim=d, n_lstm_layers=1,
          shared_lstm=False, enable_critic_lstm=True)
kw = dict(learning_rate=src.learning_rate, n_steps=src.n_steps, batch_size=src.batch_size,
          n_epochs=src.n_epochs, gamma=src.gamma, gae_lambda=src.gae_lambda,
          clip_range=src.clip_range(1.0), ent_coef=src.ent_coef, vf_coef=src.vf_coef,
          max_grad_norm=src.max_grad_norm, target_kl=src.target_kl,
          policy_kwargs=pk, device="cpu", verbose=0, seed=a.seed)
dst = RecurrentPPO(SkipLSTMPolicy, SpaceEnv(), **kw)

sd_src, sd_dst = src.policy.state_dict(), dst.policy.state_dict()
new, copied, widened, fresh = {}, [], [], []
for name, t in sd_dst.items():
    if name in sd_src:
        s = sd_src[name]
        if t.shape == s.shape:
            new[name] = s.clone(); copied.append(name)
        elif name.endswith(".0.weight") and t.shape[0] == s.shape[0] and t.shape[1] == s.shape[1] + a.hidden:
            w = th.zeros_like(t); w[:, :s.shape[1]] = s          # [features | lstm=0]
            new[name] = w; widened.append(name)
        else:
            raise SystemExit(f"shape mismatch {name}: dst {tuple(t.shape)} src {tuple(s.shape)}")
    else:
        assert "lstm" in name, f"unexpected new tensor {name}"
        new[name] = t.clone(); fresh.append(name)
missing = [n for n in sd_src if n not in sd_dst]
assert not missing, f"parent tensors with no home: {missing}"
dst.policy.load_state_dict(new)
dst.num_timesteps = src.num_timesteps
dst._n_updates = src._n_updates
dst.save(a.dst.removesuffix(".zip"))
print(f"surgery: {a.src} (K={K} x {d} = {D} inputs, MLP) -> {a.dst} (SkipLSTM hidden {a.hidden} on the newest "
      f"{d} inputs); copied {len(copied)} tensors, widened {widened}, fresh LSTM tensors {len(fresh)}; "
      f"num_timesteps={dst.num_timesteps} n_updates={dst._n_updates}")
