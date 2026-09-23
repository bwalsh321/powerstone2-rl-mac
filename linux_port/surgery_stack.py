"""surgery_stack.py <in_zip> <out_zip> --k K [--offsets 16,8,4,2,1,0] — widen (or re-lay-out) a
stacked PPO policy WITHOUT changing its behaviour (OpenAI Five style "surgery").

Source may be single-frame (K=1) or already stacked (its lag list from obs_stack.OFFSETS_BY_K).
For every destination lag: copy the source columns for the SAME lag if present; otherwise, for a
source lag with no exact match, its columns go to the nearest destination lag that is at most 2x
away (e.g. K=4's lag 3 -> strided lag 4); everything else starts at zero. Biases and all other
tensors are copied verbatim; hyperparameters carried over. Check with equivalence_stack.py.
"""
import argparse, os
import numpy as np, torch as th, gymnasium
from stable_baselines3 import PPO
from obs_stack import OFFSETS_BY_K, k_for

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("dst"); ap.add_argument("--k", type=int, default=4)
ap.add_argument("--offsets", default="")
a = ap.parse_args()
src = PPO.load(a.src.removesuffix(".zip"), device="cpu")
d = 122
ks = k_for(src); src_offs = OFFSETS_BY_K[ks]
dst_offs = sorted({int(x) for x in a.offsets.split(",")}, reverse=True) if a.offsets else OFFSETS_BY_K[a.k]
assert len(dst_offs) == a.k and dst_offs[-1] == 0
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

# column mapping: source slot i (lag src_offs[i]) -> destination slot j
mapping = {}
for i, lag in enumerate(src_offs):
    if lag in dst_offs:
        mapping[i] = dst_offs.index(lag)
    else:
        cands = [(abs(dl - lag), j) for j, dl in enumerate(dst_offs) if dl >= lag and dl <= 2 * max(lag, 1)]
        if cands:
            mapping[i] = min(cands)[1]
print("slot mapping (src lag -> dst lag):", {src_offs[i]: dst_offs[j] for i, j in mapping.items()},
      "| dropped src lags:", [src_offs[i] for i in range(ks) if i not in mapping])
sd_src, sd_dst = src.policy.state_dict(), dst.policy.state_dict()
new = {}
for name, t in sd_dst.items():
    s = sd_src[name]
    if name.endswith(".0.weight") and t.shape[1] == D:
        w = th.zeros_like(t)
        for i, j in mapping.items():
            w[:, j * d:(j + 1) * d] += s[:, i * d:(i + 1) * d]
        new[name] = w
    else:
        assert t.shape == s.shape, (name, t.shape, s.shape); new[name] = s.clone()
dst.policy.load_state_dict(new)
dst.num_timesteps = src.num_timesteps
dst._n_updates = src._n_updates
dst.save(a.dst.removesuffix(".zip"))
print(f"surgery: {a.src} (K={ks} {src_offs}) -> {a.dst} (K={a.k} {dst_offs}, {D} inputs); num_timesteps={dst.num_timesteps} n_updates={dst._n_updates}")
