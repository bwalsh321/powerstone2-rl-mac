"""BC rehearsal as an importable module — DQfD-style demo anchor for any leg.

Extracted from train_v6_par.py (Aug 20) so the self-play/FFA trainers can
rehearse Blake's demos without carrying the whole legacy trainer around.
Two changes from the original, both pre-agreed in the demo-pipeline plan:

  1. PARAMETERIZED: demo dirs, batch counts and fractions are constructor
     args, so game-night corpora (demos_gamenight/) can join without
     editing this file.
  2. ANNEALED aux weight: the Sec-22 lesson is that a fixed-strength
     rehearsal anchor eventually FIGHTS PPO (erosion elsewhere). The
     weight now decays linearly from aux_start to aux_end over
     anneal_steps of model timesteps — strong early (restore the human
     prior), weak late (let PPO own the endgame). Set aux_end == aux_start
     for the old fixed behavior.

The landmines the original defused stay defused:
  * fires in _on_rollout_start, NEVER _on_rollout_end (phantom KL -> PPO
    aborts at step 0; HANDOFF Sec 25.5)
  * class weights computed only over corpora actually SAMPLED (Aug 17 fix)
  * uses the model's own optimizer so Adam state stays coherent

Usage (in a trainer, before model.learn):
    from bc_rehearsal import BCRehearsalCallback
    rehearsal = BCRehearsalCallback(
        dirs=[("demos", 1.0)],              # (dir, sampling fraction)
        batches=16, bs=256,
        aux_start=1.0, aux_end=0.25, anneal_steps=1_000_000)
    model.learn(..., callback=[checkpoint, rehearsal, ...])
"""
import glob
import os

import numpy as np
import torch

from stable_baselines3.common.callbacks import BaseCallback


class BCRehearsalCallback(BaseCallback):
    def __init__(self, dirs, batches=16, bs=256, aux_start=1.0,
                 aux_end=0.25, anneal_steps=1_000_000, log_every=20,
                 verbose=0):
        super().__init__(verbose)
        self.batches, self.bs, self.log_every = batches, bs, log_every
        self.aux_start, self.aux_end = float(aux_start), float(aux_end)
        self.anneal_steps = max(int(anneal_steps), 1)
        self._t0 = None                      # first-rollout timestep anchor
        self.rollouts = 0
        # normalize fractions over dirs that actually have data
        self.corpora = []                    # (obs, act, frac)
        loaded = []
        for d, frac in dirs:
            x, y = self._load(d)
            if x is not None and frac > 0.0:
                loaded.append((x, y, float(frac), d))
        tot = sum(f for _x, _y, f, _d in loaded)
        if not loaded or tot <= 0:
            print("[rehearse] NO demos found — rehearsal disabled")
            self.cw = None
            return
        counts = np.zeros(10, dtype=np.int64)
        for x, y, f, d in loaded:
            self.corpora.append((x, y, f / tot))
            counts += np.bincount(y, minlength=10)
            print(f"[rehearse] {d}: {len(y)} pairs at frac {f / tot:.0%}")
        w = 1.0 / np.sqrt(np.maximum(counts, 1))
        w = w / w.sum() * 10.0
        self.cw = torch.as_tensor(w, dtype=torch.float32)
        print(f"[rehearse] {batches}x{bs}/rollout, aux "
              f"{self.aux_start} -> {self.aux_end} over "
              f"{self.anneal_steps:,} steps")

    @staticmethod
    def _load(d):
        files = sorted(glob.glob(os.path.join(d, "*.npz")))
        xs, ys = [], []
        for f in files:
            try:
                z = np.load(f)
                xs.append(z["obs"])
                ys.append(z["action"])
            except Exception as e:
                print(f"[rehearse] SKIP {os.path.basename(f)}: {e}")
        if not xs:
            return None, None
        return np.concatenate(xs), np.concatenate(ys).astype(np.int64)

    def _aux(self):
        if self._t0 is None:
            self._t0 = self.model.num_timesteps
        t = min(1.0, (self.model.num_timesteps - self._t0)
                / self.anneal_steps)
        return self.aux_start + t * (self.aux_end - self.aux_start)

    def _batch(self):
        parts_x, parts_y = [], []
        left = self.bs
        for idx, (x, y, frac) in enumerate(self.corpora):
            n = left if idx == len(self.corpora) - 1 \
                else int(round(self.bs * frac))
            n = max(0, min(n, left))
            left -= n
            if n:
                i = np.random.randint(0, len(y), n)
                parts_x.append(x[i])
                parts_y.append(y[i])
        return (torch.as_tensor(np.concatenate(parts_x)),
                torch.as_tensor(np.concatenate(parts_y)))

    def _on_rollout_start(self):
        if self.cw is None:
            return
        aux = self._aux()
        if aux <= 0.0:
            return
        policy = self.model.policy
        policy.set_training_mode(True)
        losses = []
        for _ in range(self.batches):
            xb, yb = self._batch()
            dist = policy.get_distribution(xb)
            ce = -(dist.log_prob(yb) * self.cw[yb]).mean()
            loss = aux * ce
            policy.optimizer.zero_grad()
            loss.backward()
            torch.nn.utils.clip_grad_norm_(policy.parameters(), 0.5)
            policy.optimizer.step()
            losses.append(float(ce))
        self.rollouts += 1
        if self.rollouts % self.log_every == 0:
            print(f"[rehearse] rollout {self.rollouts}: demo CE "
                  f"{np.mean(losses):.3f} (aux {aux:.2f})")

    def _on_step(self):
        return True
