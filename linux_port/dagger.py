"""dagger.py — the imitation term for DAgger drills (Oct 3 2026).

drill_play.py records Blake playing the bot's failure moments: per decision the exact observation the bot would
have seen and his action in the 63-action joint set. Here those recordings become a behaviour-cloning term that the
async trainer applies after every PPO update (before the new weights are broadcast):

    loss_bc = coef * mean over recorded decisions of  -log pi(a_human | s)

Each drill is replayed as ONE sequence from a zero LSTM state with episode_start at its first step (a recurrent
policy's state at the drill moment is not recorded; the frame stack carries the short-term history, the skip
connection keeps the feature path exact). Off unless PS2_DEMOS is set. Knobs:
  PS2_DEMOS      comma list of drill folders (rec_*.npz written by drill_play.py)
  PS2_BC_COEF    loss weight (default 0.5)
  PS2_BC_STEPS   BC gradient steps per PPO update (default 1)
  PS2_BC_SEQS    drills per BC step (default 16)
"""
import glob
import os

import numpy as np
import torch as th


class DemoSet:
    def __init__(self, dirs, obs_dim, n_actions):
        self.seqs, self.skipped = [], 0
        for d in [x for x in dirs.split(",") if x.strip()]:
            for f in sorted(glob.glob(os.path.join(d.strip(), "rec_*.npz"))):
                z = np.load(f)
                o, a = z["obs"].astype(np.float32), z["actions"].astype(np.int64)
                if o.ndim != 2 or o.shape[1] != obs_dim or len(a) != len(o) or len(a) < 2 or a.max() >= n_actions:
                    self.skipped += 1
                    continue
                self.seqs.append((o, a))
        self.n_steps = sum(len(a) for _, a in self.seqs)

    def __len__(self):
        return len(self.seqs)


def _seq_logp(policy, obs, act):
    """log pi(a|s) and argmax for one recorded sequence (recurrent policies replayed from a zero state)."""
    o, a = th.as_tensor(obs), th.as_tensor(act)
    if hasattr(policy, "lstm_actor"):
        from sb3_contrib.common.recurrent.type_aliases import RNNStates
        L, H = policy.lstm_actor.num_layers, policy.lstm_actor.hidden_size
        z = lambda: th.zeros((L, 1, H))
        st = RNNStates((z(), z()), (z(), z()))
        es = th.zeros(len(act)); es[0] = 1.0
        _, logp, _ = policy.evaluate_actions(o, a, st, es)
        dist, _ = policy.get_distribution(o, (z(), z()), es)
    else:
        _, logp, _ = policy.evaluate_actions(o, a)
        dist = policy.get_distribution(o)
    return logp, dist.distribution.logits.argmax(-1)


def bc_step(model, demos, coef, n_seqs, rng):
    policy = model.policy
    policy.set_training_mode(True)
    idx = rng.choice(len(demos), size=min(n_seqs, len(demos)), replace=False)
    losses, hits, n = [], 0, 0
    for i in idx:
        obs, act = demos.seqs[i]
        logp, am = _seq_logp(policy, obs, act)
        losses.append(-logp.mean())
        hits += int((am.detach().numpy() == act).sum()); n += len(act)
    loss = coef * th.stack(losses).mean()
    policy.optimizer.zero_grad()
    loss.backward()
    th.nn.utils.clip_grad_norm_(policy.parameters(), model.max_grad_norm)
    policy.optimizer.step()
    policy.set_training_mode(False)
    return float(loss.detach()) / coef, hits / max(n, 1)


def from_env(model):
    dirs = os.environ.get("PS2_DEMOS", "").strip()
    if not dirs:
        return None
    demos = DemoSet(dirs, int(model.observation_space.shape[0]), int(model.action_space.n))
    cfg = dict(coef=float(os.environ.get("PS2_BC_COEF", "0.5")), steps=int(os.environ.get("PS2_BC_STEPS", "1")),
               seqs=int(os.environ.get("PS2_BC_SEQS", "16")))
    print(f"[config] dagger demos={dirs} sequences={len(demos)} decisions={demos.n_steps} skipped={demos.skipped} "
          f"bc_coef={cfg['coef']} bc_steps={cfg['steps']} bc_seqs={cfg['seqs']}", flush=True)
    return (demos, cfg) if len(demos) else None
