"""surgery_actions.py <in_zip> <out_zip> [--penalty 4.0] — widen a 10-action policy (PPO or SkipLSTM RecurrentPPO)
to the 63-action joint set (action_space.py) with a behaviour-preserving start (Oct 3 2026).

Action head rows: each legacy action's row is copied to its exact joint equivalent. A combo (dir d, button b)
starts as the MEAN of its two parts' rows minus `penalty` (bias), so combos whose parts the policy already
favours start as the likeliest combos; "none+none" (stand still) starts as the mean of all legacy rows minus
`penalty`. Everything else (features, LSTMs, MLP, value head) is copied verbatim. With penalty P, a combo's
logit sits P below its parts' average: the legacy argmax is preserved wherever its lead over the combos'
part-averages exceeds 0 (always, for P > 0 on legacy-optimal states) and the combo mass starts small;
measure it with agreement_actions.py and pick P.
"""
import argparse

import gymnasium
import numpy as np
import torch as th

from action_space import BTNS, DIRS, JOINT_N, LEGACY_N, LEGACY_TO_JOINT
from recurrent_policy import CUSTOM_OBJECTS, load_model

ap = argparse.ArgumentParser()
ap.add_argument("src"); ap.add_argument("dst")
ap.add_argument("--penalty", type=float, default=4.0)
a = ap.parse_args()

src = load_model(a.src)
assert int(src.action_space.n) == LEGACY_N, f"source has {src.action_space.n} actions, expected {LEGACY_N}"
D = int(src.observation_space.shape[0])


class SpaceEnv(gymnasium.Env):
    def __init__(self):
        self.observation_space = src.observation_space
        self.action_space = gymnasium.spaces.Discrete(JOINT_N)
    def reset(self, *, seed=None, options=None): return np.zeros(D, np.float32), {}
    def step(self, action): return np.zeros(D, np.float32), 0.0, False, False, {}


kw = dict(learning_rate=src.learning_rate, n_steps=src.n_steps, batch_size=src.batch_size,
          n_epochs=src.n_epochs, gamma=src.gamma, gae_lambda=src.gae_lambda,
          clip_range=src.clip_range(1.0), ent_coef=src.ent_coef, vf_coef=src.vf_coef,
          max_grad_norm=src.max_grad_norm, target_kl=src.target_kl,
          policy_kwargs=dict(src.policy_kwargs or {}), device="cpu", verbose=0)
dst = type(src)(type(src.policy), SpaceEnv(), **kw)

sd_src, sd_dst = src.policy.state_dict(), dst.policy.state_dict()
new = {}
for n, t in sd_dst.items():
    s = sd_src[n]
    if n.startswith("action_net."):
        assert t.shape[0] == JOINT_N and s.shape[0] == LEGACY_N, (n, t.shape, s.shape)
        out = th.zeros_like(t)
        part_dir = {0: None, 1: 0, 2: 1, 3: 2, 4: 3}       # dir index -> legacy row (cardinals)
        diag = {5: (0, 2), 6: (0, 3), 7: (1, 2), 8: (1, 3)}
        part_btn = {0: None, 1: 4, 2: 5, 3: 6, 4: 7, 5: 8, 6: 9}
        for d in range(len(DIRS)):
            for b in range(len(BTNS)):
                j = d * len(BTNS) + b
                if j in LEGACY_TO_JOINT.values():
                    continue
                rows = []
                if d in diag:
                    rows += [s[diag[d][0]], s[diag[d][1]]]
                elif part_dir.get(d) is not None:
                    rows.append(s[part_dir[d]])
                if part_btn[b] is not None:
                    rows.append(s[part_btn[b]])
                if not rows:                                  # none+none: stand still
                    rows = [s[k] for k in range(LEGACY_N)]
                out[j] = th.stack(rows).mean(0)
                if n.endswith("bias"):
                    out[j] -= a.penalty
        for k, j in LEGACY_TO_JOINT.items():
            out[j] = s[k]
        new[n] = out
    else:
        assert t.shape == s.shape, (n, t.shape, s.shape)
        new[n] = s.clone()
dst.policy.load_state_dict(new)
dst.num_timesteps = src.num_timesteps
dst._n_updates = src._n_updates
dst.save(a.dst.removesuffix(".zip"))
print(f"surgery_actions: {a.src} ({type(src).__name__}, {LEGACY_N} actions) -> {a.dst} ({JOINT_N} joint actions, "
      f"combo penalty {a.penalty}); num_timesteps={dst.num_timesteps}")
