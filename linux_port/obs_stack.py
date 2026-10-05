"""Frame stacking for the Power Stone 2 policies (Sep 22-23 2026).

A stacked policy sees several past frames of the 122-number observation concatenated, OLDEST
FIRST, NEWEST LAST. Which past frames is given by a list of LAGS in decision steps (0.1 s each):
    contiguous K=4 :  [3, 2, 1, 0]                 (0.3 s window; legs 68-69)
    strided   K=6 :  [16, 8, 4, 2, 1, 0]           (1.6 s window with 6 frames)
    strided   K=7 :  [16, 8, 4, 3, 2, 1, 0]        (1.6 s window AND every K=4 lag kept -> exact surgery; leg 70+)
The lag list is implied by the frame count (OFFSETS_BY_K) so evaluators and pool seats can
reconstruct it from a model's observation space alone; PS2_STACK_OFFSETS="16,8,4,2,1,0" overrides
for the trainer. At a reset the ring is filled with copies of the first frame.

  FrameStack(k_or_offsets, dim)   reset(obs) / push(obs) -> stacked vector
  StackedEnv(env, k_or_offsets)   old-gym env wrapper for the learner
  k_for(model, dim)               frame count implied by a model's observation space
  offsets_for(k)                  lag list for a frame count (or the PS2_STACK_OFFSETS override)
"""
import os
import numpy as np

OFFSETS_BY_K = {1: [0], 2: [1, 0], 3: [2, 1, 0], 4: [3, 2, 1, 0],
                6: [16, 8, 4, 2, 1, 0], 7: [16, 8, 4, 3, 2, 1, 0], 8: [7, 6, 5, 4, 3, 2, 1, 0]}


def offsets_for(k):
    ov = os.environ.get("PS2_STACK_OFFSETS", "").strip()
    if ov:
        offs = sorted({int(x) for x in ov.split(",")}, reverse=True)
        if len(offs) == int(k):
            return offs
    if int(k) not in OFFSETS_BY_K:
        raise ValueError(f"no lag list for K={k}; set PS2_STACK_OFFSETS")
    return list(OFFSETS_BY_K[int(k)])


def _norm(k_or_offsets):
    if isinstance(k_or_offsets, (list, tuple)):
        offs = sorted({int(x) for x in k_or_offsets}, reverse=True)
    else:
        offs = offsets_for(int(k_or_offsets))
    assert offs[-1] == 0, "lag 0 (the current frame) must be included"
    return offs


class FrameStack:
    def __init__(self, k_or_offsets, dim):
        self.offsets = _norm(k_or_offsets)
        self.k, self.dim = len(self.offsets), int(dim)
        self.depth = self.offsets[0] + 1
        self.ring = None

    def reset(self, obs):
        obs = np.asarray(obs, dtype=np.float32)
        self.ring = [obs] * self.depth              # ring[-1] = newest, ring[-1-lag] = lag steps ago
        return self.get()

    def push(self, obs):
        obs = np.asarray(obs, dtype=np.float32)
        if self.ring is None:
            return self.reset(obs)
        self.ring = self.ring[1:] + [obs]
        return self.get()

    def get(self):
        return np.concatenate([self.ring[-1 - lag] for lag in self.offsets]).astype(np.float32)


class StackedEnv:
    """Wraps an old-gym env (reset()->obs, step()->(obs, r, done, info)); everything else
    is delegated, so env.steps / env.prev / env._lr_bridge keep working."""

    def __init__(self, env, k_or_offsets):
        import gym
        self._env = env
        d = env.observation_space.shape[0]
        self._fs = FrameStack(k_or_offsets, d)
        self.k, self.offsets = self._fs.k, self._fs.offsets
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


# obs v4, obs v3, obs v2/v1 (checked in this order). Oct 5 2026: 430*K never equals 160*K' or 122*K' for K, K' in
# OFFSETS_BY_K (430..3440 vs 160..1280 / 122..976), so the width alone still identifies the contract.
BASE_DIMS = (430, 160, 122)


def kd_for(model):
    """(K, per-frame dim) of a policy from its input width: 122 (v2), 160 (v3) or 430 (v4) per frame."""
    n = int(model.observation_space.shape[0])
    for d in BASE_DIMS:
        if n % d == 0 and (n // d) in OFFSETS_BY_K:
            return n // d, d
    raise ValueError(f"model obs dim {n} is not K x 122, K x 160 or K x 430 for a known K")


def k_for(model, base_dim=None):
    if base_dim is None:
        return kd_for(model)[0]
    n = int(model.observation_space.shape[0])
    if n % base_dim:
        raise ValueError(f"model obs dim {n} is not a multiple of {base_dim}")
    return n // base_dim
