"""ppo_train.py — the learner's PPO update, instrumented (Oct 6 2026, audit finding: target_kl stops early).

A copy of sb3_contrib RecurrentPPO.train (2.9.0) with:
  * counters: gradient steps taken out of the possible n_epochs x minibatches, and the KL between the acting
    (behaviour) policy and the learner's weights at the START of the update (`kl0`, the staleness the async actors
    bring in before any learning happens). Printed as one `[ppo]` line per update.
  * PS2_PPO_KL_REF=prox (default "behav" = stock behaviour): the early-stopping KL is measured against the learner's
    own weights at the start of the update (the proximal policy) instead of the stale acting policy, so data
    staleness no longer uses up the KL budget. The surrogate loss and its clipping are unchanged.
With the default, the arithmetic is the stock train() step for step (same minibatches, same loss, same stop rule).
"""
import copy
import os

import numpy as np
import torch as th
from gymnasium import spaces
from stable_baselines3.common.utils import explained_variance

KL_REF = os.environ.get("PS2_PPO_KL_REF", "behav")


def train(self, n_update=None):
    self.policy.set_training_mode(True)
    self._update_learning_rate(self.policy.optimizer)
    clip_range = self.clip_range(self._current_progress_remaining)
    if self.clip_range_vf is not None:
        clip_range_vf = self.clip_range_vf(self._current_progress_remaining)

    prox = None
    if KL_REF == "prox":
        # Oct 7 2026: one copy made once, then refreshed by state_dict each update. A deepcopy per update failed
        # ("Only Tensors created explicitly by the user support the deepcopy protocol") once training had left a
        # non-leaf tensor attribute on the policy; the first copy is taken before the first gradient step.
        prox = getattr(self, "_ps2_prox", None)
        if prox is None:
            prox = self._ps2_prox = copy.deepcopy(self.policy)
        prox.load_state_dict(self.policy.state_dict())
        prox.set_training_mode(False)

    entropy_losses, pg_losses, value_losses, clip_fractions = [], [], [], []
    continue_training = True
    n_steps = n_possible = 0
    kl0 = None
    approx_kl_divs = []
    for epoch in range(self.n_epochs):
        approx_kl_divs = []
        for rollout_data in self.rollout_buffer.get(self.batch_size):
            n_possible += 1 if epoch == 0 else 0
            actions = rollout_data.actions
            if isinstance(self.action_space, spaces.Discrete):
                actions = rollout_data.actions.long().flatten()
            mask = rollout_data.mask > 1e-8
            values, log_prob, entropy = self.policy.evaluate_actions(
                rollout_data.observations, actions, rollout_data.lstm_states, rollout_data.episode_starts)
            values = values.flatten()
            advantages = rollout_data.advantages
            if self.normalize_advantage:
                advantages = (advantages - advantages[mask].mean()) / (advantages[mask].std() + 1e-8)
            ratio = th.exp(log_prob - rollout_data.old_log_prob)
            policy_loss_1 = advantages * ratio
            policy_loss_2 = advantages * th.clamp(ratio, 1 - clip_range, 1 + clip_range)
            policy_loss = -th.mean(th.min(policy_loss_1, policy_loss_2)[mask])
            pg_losses.append(policy_loss.item())
            clip_fractions.append(th.mean((th.abs(ratio - 1) > clip_range).float()[mask]).item())
            if self.clip_range_vf is None:
                values_pred = values
            else:
                values_pred = rollout_data.old_values + th.clamp(
                    values - rollout_data.old_values, -clip_range_vf, clip_range_vf)
            value_loss = th.mean(((rollout_data.returns - values_pred) ** 2)[mask])
            value_losses.append(value_loss.item())
            if entropy is None:
                entropy_loss = -th.mean(-log_prob[mask])
            else:
                entropy_loss = -th.mean(entropy[mask])
            entropy_losses.append(entropy_loss.item())
            loss = policy_loss + self.ent_coef * entropy_loss + self.vf_coef * value_loss

            with th.no_grad():
                log_ratio = log_prob - rollout_data.old_log_prob
                kl_behav = th.mean(((th.exp(log_ratio) - 1) - log_ratio)[mask]).cpu().numpy()
                if kl0 is None and epoch == 0:
                    kl0 = float(kl_behav)        # first minibatch, before any step: pure staleness
                if prox is not None:
                    _, lp_prox, _ = prox.evaluate_actions(
                        rollout_data.observations, actions, rollout_data.lstm_states, rollout_data.episode_starts)
                    lr_p = log_prob - lp_prox
                    approx_kl_div = th.mean(((th.exp(lr_p) - 1) - lr_p)[mask]).cpu().numpy()
                else:
                    approx_kl_div = kl_behav
                approx_kl_divs.append(approx_kl_div)

            if self.target_kl is not None and approx_kl_div > 1.5 * self.target_kl:
                continue_training = False
                if self.verbose >= 1:
                    print(f"Early stopping at step {epoch} due to reaching max kl: {approx_kl_div:.2f}")
                break

            self.policy.optimizer.zero_grad()
            loss.backward()
            th.nn.utils.clip_grad_norm_(self.policy.parameters(), self.max_grad_norm)
            self.policy.optimizer.step()
            n_steps += 1

        self._n_updates += 1
        if not continue_training:
            break

    explained_var = explained_variance(self.rollout_buffer.values.flatten(), self.rollout_buffer.returns.flatten())
    self.logger.record("train/entropy_loss", np.mean(entropy_losses))
    self.logger.record("train/policy_gradient_loss", np.mean(pg_losses))
    self.logger.record("train/value_loss", np.mean(value_losses))
    self.logger.record("train/approx_kl", np.mean(approx_kl_divs))
    self.logger.record("train/clip_fraction", np.mean(clip_fractions))
    self.logger.record("train/loss", loss.item())
    self.logger.record("train/explained_variance", explained_var)
    if hasattr(self.policy, "log_std"):
        self.logger.record("train/std", th.exp(self.policy.log_std).mean().item())
    self.logger.record("train/n_updates", self._n_updates, exclude="tensorboard")
    self.logger.record("train/clip_range", clip_range)
    if self.clip_range_vf is not None:
        self.logger.record("train/clip_range_vf", clip_range_vf)
    total = n_possible * self.n_epochs
    print(f"[ppo] update {n_update if n_update is not None else '?'} kl_ref={KL_REF} grad_steps={n_steps}/{total} "
          f"({100 * n_steps / max(total, 1):.1f}%) epochs_started={epoch + 1} kl0_staleness={kl0 if kl0 is not None else float('nan'):.4f}",
          flush=True)
