"""Synthetic check: laying actor chunks into SB3's RolloutBuffer as columns
must reproduce EXACTLY what collect_rollouts' row-by-row add() produces,
including GAE returns/advantages. No emulator. Run:
    PYTHONPATH=../sdlarch-rl:. python test_async_buffer.py
"""
import numpy as np
import torch as th
from gymnasium import spaces
from stable_baselines3.common.buffers import RolloutBuffer

from train_selfplay_async import fill_buffer_from_chunks

rng = np.random.default_rng(0)
T, N, D = 64, 5, 122
obs_space = spaces.Box(-5, 5, (D,), np.float32)
act_space = spaces.Discrete(10)

# random trajectories with episode boundaries
obs = rng.normal(size=(T, N, D)).astype(np.float32)
act = rng.integers(0, 10, size=(T, N))
rew = rng.normal(size=(T, N)).astype(np.float32)
starts = (rng.random((T, N)) < 0.05).astype(np.float32)
starts[0] = 1.0
vals = rng.normal(size=(T, N)).astype(np.float32)
logp = -rng.random((T, N)).astype(np.float32)
last_vals = rng.normal(size=N).astype(np.float32)
last_dones = rng.random(N) < 0.3

# reference: SB3's own path
ref = RolloutBuffer(T, obs_space, act_space, device="cpu", gae_lambda=0.95, gamma=0.999, n_envs=N)
for t in range(T):
    ref.add(obs[t], act[t].reshape(N, 1), rew[t], starts[t],
            th.as_tensor(vals[t]), th.as_tensor(logp[t]))
ref.compute_returns_and_advantage(th.as_tensor(last_vals), last_dones)

# ours: per-actor chunks -> columns
chunks = [dict(actor=i, version=0, obs=obs[:, i], actions=act[:, i], rewards=rew[:, i],
               episode_starts=starts[:, i], values=vals[:, i], log_probs=logp[:, i],
               last_value=float(last_vals[i]), last_done=bool(last_dones[i])) for i in range(N)]
mine = RolloutBuffer(T, obs_space, act_space, device="cpu", gae_lambda=0.95, gamma=0.999, n_envs=N)
lv, dn = fill_buffer_from_chunks(mine, chunks)
mine.compute_returns_and_advantage(lv, dn)

for name in ("observations", "actions", "rewards", "episode_starts", "values", "log_probs",
             "advantages", "returns"):
    a, b = getattr(ref, name), getattr(mine, name)
    assert a.shape == b.shape, (name, a.shape, b.shape)
    assert np.array_equal(a, b), f"{name} differs (max abs diff {np.abs(a - b).max()})"
assert mine.full and mine.pos == T

ref_returns = ref.returns.copy()   # get() swaps/flattens in place below
# the minibatch generator must also see identical data (it swaps/flattens)
sa = np.concatenate([s.returns.numpy() for s in ref.get(64)])
sb = np.concatenate([s.returns.numpy() for s in mine.get(64)])
assert sa.shape == sb.shape == (T * N,)
assert np.isclose(np.sort(sa), np.sort(sb)).all()
# and a second fill after get() (which swap_and_flattens) must work
lv, dn = fill_buffer_from_chunks(mine, chunks)
mine.compute_returns_and_advantage(lv, dn)
assert np.array_equal(mine.returns, ref_returns)
print("test_async_buffer: PASS — column fill == SB3 row-by-row add (obs/act/rew/starts/values/logp/adv/returns)")
