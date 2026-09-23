"""Frame stacking for the Power Stone 2 policies (Sep 22 2026, Blake: "let's add this").

The base observation is one 122-number frame. A stacked policy sees the last K frames
concatenated, OLDEST FIRST, NEWEST LAST (so the newest frame occupies the final 122
columns; surgery_stack.py copies the single-frame weights there and zeroes the rest).
At a reset the stack is filled with K copies of the first frame.

  FrameStack(k, dim)     manual stacker for eval loops: reset(obs) / push(obs) -> stacked
  StackedEnv(env, k)     old-gym env wrapper for the learner (reset/step return stacked obs)
  k_for(model, dim)      K implied by a loaded model's observation space (1 = single frame)
"""
import numpy as np


class FrameStack:
    def __init__(self, k, dim):
        self.k, self.dim, self.buf = int(k), int(dim), None

    def reset(self, obs):
        obs = np.asarray(obs, dtype=np.float32)
        self.buf = [obs] * self.k
        return self.get()

    def push(self, obs):
        obs = np.asarray(obs, dtype=np.float32)
        if self.buf is None:
            return self.reset(obs)
        self.buf = self.buf[1:] + [obs]
        return self.get()

    def get(self):
        return np.concatenate(self.buf).astype(np.float32)


class StackedEnv:
    """Wraps an old-gym env (reset()->obs, step()->(obs, r, done, info)); everything else
    is delegated, so env.steps / env.prev / env._lr_bridge keep working."""

    def __init__(self, env, k):
        import gym
        self._env, self.k = env, int(k)
        d = env.observation_space.shape[0]
        self._fs = FrameStack(self.k, d)
        lo, hi = float(env.observation_space.low.min()), float(env.observation_space.high.max())
        self.observation_space = gym.spaces.Box(lo, hi, (d * self.k,), np.float32)
        self.action_space = env.action_space

    def reset(self, *a, **kw):
        return self._fs.reset(self._env.reset(*a, **kw))

    def step(self, action):
        obs, r, done, info = self._env.step(action)
        return self._fs.push(obs), r, done, info

    def __getattr__(self, name):
        return getattr(self._env, name)


def k_for(model, base_dim=122):
    n = int(model.observation_space.shape[0])
    if n % base_dim:
        raise ValueError(f"model obs dim {n} is not a multiple of {base_dim}")
    return n // base_dim
