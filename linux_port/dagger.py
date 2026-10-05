"""dagger.py — the imitation term for DAgger drills (Oct 3 2026; reworked Oct 5 2026 after legs 125-127).

drill_play.py records Blake playing the bot's failure moments: per decision the exact observation the bot would
have seen and his action in the 63-action joint set. Here those recordings become a behaviour-cloning term that the
async trainer applies after every PPO update (before the new weights are broadcast).

Each drill is replayed as ONE sequence from a zero LSTM state with episode_start at its first step (a recurrent
policy's state at the drill moment is not recorded; the frame stack carries the short-term history, the skip
connection keeps the feature path exact).

Oct 5 2026 rework (Blake; legs 125-127 lost 11-15 points of lv8mix while agreement on the training drills rose
7% -> 55% and on unseen drills only 7% -> 25%):
  * only drills Blake got out of are imitated (result win or cut = still alive when the drill ended); his deaths
    taught the bot his losing play as much as his escapes.
  * a fixed 20% of drills (by name hash, stable across legs) is held out; agreement / nll on it is logged, and the
    BC term stops for the rest of the leg once held-out nll has not improved for PS2_BC_PATIENCE checks.
  * the weight fades linearly to zero over the first PS2_BC_ANNEAL fraction of the leg.
  * the weight is a real knob: the BC step runs at lr x weight. (Before, BC was its own Adam step, and Adam
    normalises the step size, so coef 0.2 still moved the policy a full step per update.)
Knobs:
  PS2_DEMOS        comma list of drill folders (rec_*.npz written by drill_play.py)
  PS2_BC_COEF      starting weight = fraction of the PPO learning rate used by a BC step (default 0.5)
  PS2_BC_STEPS     BC gradient steps per PPO update (default 1)
  PS2_BC_SEQS      drills per BC step (default 16)
  PS2_BC_ANNEAL    fraction of the leg over which the weight fades to 0 (default 1.0; 0 = constant)
  PS2_BC_HOLDOUT   held-out fraction (default 0.2)
  PS2_BC_EVAL      held-out check every N updates (default 5)
  PS2_BC_PATIENCE  checks without held-out nll improvement before BC stops (default 4)
  PS2_BC_RESULTS   recorded results to imitate (default win,cut)
"""
import glob
import os
import zlib

import numpy as np
import torch as th


def _held_out(name, frac):
    return (zlib.crc32(name.encode()) % 1000) < int(frac * 1000)


class DemoSet:
    def __init__(self, dirs, obs_dim, n_actions, button_tap=False, results=None, holdout=None, part="all"):
        # Oct 4 2026: recordings carry the button semantics they were made under (drill_play.py: taps by default;
        # recordings without the field predate taps = held). Only recordings matching the trainer's semantics load.
        self.seqs, self.names, self.skipped, self.other_semantics, self.filtered = [], [], 0, 0, 0
        for d in [x for x in dirs.split(",") if x.strip()]:
            for f in sorted(glob.glob(os.path.join(d.strip(), "rec_*.npz"))):
                name = os.path.join(os.path.basename(d.strip().rstrip("/")), os.path.basename(f))
                if holdout is not None and part != "all" and _held_out(name, holdout) != (part == "held"):
                    continue
                z = np.load(f)
                tap = bool(z["button_tap"]) if "button_tap" in z.files else False
                if tap != bool(button_tap):
                    self.other_semantics += 1
                    continue
                if results is not None and str(z["result"]) not in results:
                    self.filtered += 1
                    continue
                o, a = z["obs"].astype(np.float32), z["actions"].astype(np.int64)
                if o.ndim != 2 or o.shape[1] != obs_dim or len(a) != len(o) or len(a) < 2 or a.max() >= n_actions:
                    self.skipped += 1
                    continue
                self.seqs.append((o, a))
                self.names.append(name)
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


def bc_step(model, demos, weight, n_seqs, rng):
    """One BC gradient step at learning rate lr x weight. Returns (nll, agreement) on the sampled drills."""
    policy = model.policy
    policy.set_training_mode(True)
    idx = rng.choice(len(demos), size=min(n_seqs, len(demos)), replace=False)
    losses, hits, n = [], 0, 0
    for i in idx:
        obs, act = demos.seqs[i]
        logp, am = _seq_logp(policy, obs, act)
        losses.append(-logp.mean())
        hits += int((am.detach().numpy() == act).sum()); n += len(act)
    loss = th.stack(losses).mean()
    opt = policy.optimizer
    lrs = [g["lr"] for g in opt.param_groups]
    for g in opt.param_groups:
        g["lr"] = g["lr"] * weight
    try:
        opt.zero_grad()
        loss.backward()
        th.nn.utils.clip_grad_norm_(policy.parameters(), model.max_grad_norm)
        opt.step()
    finally:
        for g, lr in zip(opt.param_groups, lrs):
            g["lr"] = lr
    policy.set_training_mode(False)
    return float(loss.detach()), hits / max(n, 1)


def evaluate(model, demos):
    """(nll, agreement) over every decision of a DemoSet, no gradient."""
    policy = model.policy
    policy.set_training_mode(False)
    nll, hits, n = 0.0, 0, 0
    with th.no_grad():
        for obs, act in demos.seqs:
            logp, am = _seq_logp(policy, obs, act)
            nll += float(-logp.sum()); hits += int((am.numpy() == act).sum()); n += len(act)
    return nll / max(n, 1), hits / max(n, 1)


class Dagger:
    """The trainer's handle: call after_update(model, n_update, progress) once per PPO update."""

    def __init__(self, model, dirs, cfg):
        obs_dim, n_act = int(model.observation_space.shape[0]), int(model.action_space.n)
        self.cfg = cfg
        res = set(cfg["results"])
        self.train = DemoSet(dirs, obs_dim, n_act, cfg["tap"], res, cfg["holdout"], "train")
        self.held = DemoSet(dirs, obs_dim, n_act, cfg["tap"], res, cfg["holdout"], "held")
        self.rng = np.random.default_rng()
        self.best, self.bad, self.stopped = float("inf"), 0, False
        allrec = DemoSet(dirs, obs_dim, n_act, cfg["tap"])
        print(f"[config] dagger demos={dirs} imitate={','.join(cfg['results'])} train={len(self.train)} drills/"
              f"{self.train.n_steps} decisions held_out={len(self.held)}/{self.held.n_steps} "
              f"(filtered out by result: {self.train.filtered + self.held.filtered}, other button semantics: "
              f"{allrec.other_semantics}, bad shape: {allrec.skipped}) weight={cfg['coef']} x lr, fading to 0 over "
              f"{cfg['anneal']:.0%} of the leg, bc_steps={cfg['steps']} bc_seqs={cfg['seqs']} "
              f"eval every {cfg['eval']} updates, patience {cfg['patience']} button_tap={int(cfg['tap'])}", flush=True)
        if len(self.held):
            nll, acc = evaluate(model, self.held)
            self.best = nll
            print(f"[bc] start held-out nll={nll:.4f} agree={100 * acc:.1f}%", flush=True)

    def weight(self, progress):
        a = self.cfg["anneal"]
        return self.cfg["coef"] * (max(0.0, 1.0 - progress / a) if a > 0 else 1.0)

    def after_update(self, model, n_update, progress):
        if self.stopped:
            return
        w = self.weight(progress)
        if w <= 0:
            self.stopped = True
            print(f"[bc] update {n_update} weight faded to 0: BC off for the rest of the leg", flush=True)
            return
        for _ in range(self.cfg["steps"]):
            nll, acc = bc_step(model, self.train, w, self.cfg["seqs"], self.rng)
        line = f"[bc] update {n_update} weight={w:.3f} train nll={nll:.4f} agree={100 * acc:.1f}%"
        if len(self.held) and n_update % self.cfg["eval"] == 0:
            hn, ha = evaluate(model, self.held)
            line += f" | held-out nll={hn:.4f} agree={100 * ha:.1f}%"
            if hn < self.best - 1e-3:
                self.best, self.bad = hn, 0
            else:
                self.bad += 1
                if self.bad >= self.cfg["patience"]:
                    self.stopped = True
                    line += f" | held-out stopped improving (best {self.best:.4f}): BC off for the rest of the leg"
        print(line, flush=True)


def from_env(model):
    dirs = os.environ.get("PS2_DEMOS", "").strip()
    if not dirs:
        return None
    cfg = dict(coef=float(os.environ.get("PS2_BC_COEF", "0.5")), steps=int(os.environ.get("PS2_BC_STEPS", "1")),
               seqs=int(os.environ.get("PS2_BC_SEQS", "16")), anneal=float(os.environ.get("PS2_BC_ANNEAL", "1.0")),
               holdout=float(os.environ.get("PS2_BC_HOLDOUT", "0.2")), eval=int(os.environ.get("PS2_BC_EVAL", "5")),
               patience=int(os.environ.get("PS2_BC_PATIENCE", "4")),
               results=[r.strip() for r in os.environ.get("PS2_BC_RESULTS", "win,cut").split(",") if r.strip()],
               tap=os.environ.get("PS2_BUTTON_TAP", "0") == "1")
    d = Dagger(model, dirs, cfg)
    return d if len(d.train) else None
