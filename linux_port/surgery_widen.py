"""surgery_widen.py <in_zip> <out_zip> [--dim-in 122] [--dim-out 160] — widen every per-frame slot of a
(stacked) PPO policy from dim-in to dim-out inputs WITHOUT changing behaviour: the existing columns
are copied into the first dim-in positions of each lag slot, the new columns start at ZERO, biases
and every other tensor are copied verbatim, hyperparameters and step counters carried over.
Sep 23 2026, obs v3 (122 -> 160). Check with equivalence_widen.py."""
import argparse, numpy as np, torch as th, gymnasium
from stable_baselines3 import PPO
from obs_stack import kd_for

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("dst")
ap.add_argument("--dim-in", type=int, default=122); ap.add_argument("--dim-out", type=int, default=160)
a = ap.parse_args()
src = PPO.load(a.src.removesuffix(".zip"), device="cpu")
K, d = kd_for(src)
assert d == a.dim_in, f"source is {d}/frame, expected {a.dim_in}"
D = a.dim_out * K

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
new, widened = {}, []
for name, t in sd_dst.items():
    s = sd_src[name]
    if name.endswith(".0.weight") and t.shape[1] == D:
        w = th.zeros_like(t)
        for j in range(K):
            w[:, j * a.dim_out: j * a.dim_out + a.dim_in] = s[:, j * a.dim_in:(j + 1) * a.dim_in]
        new[name] = w; widened.append(name)
    else:
        assert t.shape == s.shape, (name, t.shape, s.shape); new[name] = s.clone()
dst.policy.load_state_dict(new)
dst.num_timesteps = src.num_timesteps
dst._n_updates = src._n_updates
dst.save(a.dst.removesuffix(".zip"))
print(f"widen: {a.src} (K={K}, {d}/frame) -> {a.dst} ({a.dim_out}/frame, {D} inputs); widened {widened}; "
      f"num_timesteps={dst.num_timesteps} n_updates={dst._n_updates}")
