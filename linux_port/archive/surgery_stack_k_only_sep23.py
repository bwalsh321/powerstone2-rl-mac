"""surgery_stack.py <in_zip> <out_zip> --k K — widen a single-frame PPO policy to a K-frame
stacked input WITHOUT changing its behaviour (OpenAI Five style "surgery", Sep 22 2026).

The new first layers of both MLPs (policy_net.0, value_net.0) are (256, 122*K): the old
(256, 122) weights are copied into the LAST 122 columns (the newest frame), all other columns
are zero, biases and every other tensor are copied verbatim. Hyperparameters (lr, batch, n_steps,
target_kl, ent_coef, gamma, ...) are carried over. Verified equal by equivalence_stack.py.
"""
import argparse, os
import numpy as np, torch as th, gymnasium
from stable_baselines3 import PPO

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("dst"); ap.add_argument("--k", type=int, default=4)
a = ap.parse_args()
src = PPO.load(a.src.removesuffix(".zip"), device="cpu")
d = src.observation_space.shape[0]
assert d == 122, f"expected a single-frame (122) policy, got {d}"
D = d * a.k

class SpaceEnv(gymnasium.Env):
    def __init__(self):
        self.observation_space = gymnasium.spaces.Box(-5.0, 5.0, (D,), np.float32)
        self.action_space = gymnasium.spaces.Discrete(int(src.action_space.n))
    def reset(self, *, seed=None, options=None): return np.zeros(D, np.float32), {}
    def step(self, action): return np.zeros(D, np.float32), 0.0, False, False, {}

kw = dict(learning_rate=src.learning_rate, n_steps=src.n_steps, batch_size=src.batch_size,
          n_epochs=src.n_epochs, gamma=src.gamma, gae_lambda=src.gae_lambda,
          clip_range=src.clip_range(1.0), ent_coef=src.ent_coef, vf_coef=src.vf_coef,
          max_grad_norm=src.max_grad_norm, target_kl=src.target_kl,
          policy_kwargs=dict(src.policy_kwargs or {}), device="cpu", verbose=0)
dst = PPO("MlpPolicy", SpaceEnv(), **kw)
sd_src, sd_dst = src.policy.state_dict(), dst.policy.state_dict()
new = {}
for name, t in sd_dst.items():
    s = sd_src[name]
    if name.endswith(".0.weight") and t.shape[1] == D and s.shape[1] == d:
        w = th.zeros_like(t); w[:, -d:] = s; new[name] = w      # newest frame = last 122 columns
    else:
        assert t.shape == s.shape, (name, t.shape, s.shape); new[name] = s.clone()
dst.policy.load_state_dict(new)
dst.num_timesteps = src.num_timesteps
dst._n_updates = src._n_updates
dst.save(a.dst.removesuffix(".zip"))
print(f"surgery: {a.src} ({d}) -> {a.dst} ({D}, K={a.k}); num_timesteps={dst.num_timesteps} n_updates={dst._n_updates}")
print("hparams:", {k: (v if not callable(v) else "fn") for k, v in kw.items() if k != 'policy_kwargs'}, dst.policy_kwargs)
