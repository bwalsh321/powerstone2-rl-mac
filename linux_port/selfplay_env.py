"""1v1 mirror self-play env — the Phillip lesson, applied.

One emulator, two agent views:
  * The LEARNER plays DC port B (in-game P2 — same anchors, same obs
    semantics as the entire Windows lineage, so Leg G's weights are a
    valid warm start).
  * The OPPONENT plays DC port A (in-game P1), driven by a FROZEN policy
    sampled per-episode from the checkpoint pool (checkpoints_v6/ has 250+
    snapshots of the whole training history — instant opponent diversity).

The learner sees a standard Gym interface; opponent inference happens
inside step(), so SubprocVecEnv still gets 1 stream per instance and
train_v6_par.py's harness shape carries over.

Opponent obs: built by a second StateLineSynth with bot_player=1 and a
parent-env obs builder configured for AGENT_PLAYER=1. All four players'
anchors are in ps2_addr.GEMS/PLAYER_MAT, so the P1 view needs no new RE —
but eyeball the first episodes: the P1 view is the one thing the Windows
rig never exercised.

Savestate requirement: slots must be VS-mode 2P matches (both DC ports
human) — the existing 1-human savestates put a COM on port A. See
README_PORT.md step 5.
"""
import os
import random

import numpy as np

from powerstone_env_libretro import PowerStoneEnvLibretro
from ps2_ram import StateLineSynth


class OpponentPool:
    """Frozen SB3 policies sampled per episode.

    Sampling: 50% uniform over the newest `recent_k`, 50% uniform over the
    full history (PFSP-lite — keeps the learner honest against old styles
    without letting the pool go stale)."""

    def __init__(self, pool_dir, recent_k=10):
        from stable_baselines3 import PPO
        self._PPO = PPO
        self.pool_dir = pool_dir
        self.recent_k = recent_k
        self._cache = {}
        self.refresh()

    def refresh(self):
        import glob
        zips = glob.glob(os.path.join(self.pool_dir, "*.zip"))
        self.paths = sorted(zips, key=lambda p: self._steps(p))

    @staticmethod
    def _steps(p):
        import re
        m = re.search(r"(\d+)_steps", p)
        return int(m.group(1)) if m else 0

    def sample(self):
        if not self.paths:
            return None
        pick = (random.choice(self.paths[-self.recent_k:])
                if random.random() < 0.5 else random.choice(self.paths))
        if pick not in self._cache:
            if len(self._cache) > 20:      # LRU-ish: don't hold 250 models
                self._cache.pop(next(iter(self._cache)))
            self._cache[pick] = self._PPO.load(pick, device="cpu")
        return self._cache[pick]


class SelfPlayEnv(PowerStoneEnvLibretro):
    def __init__(self, *args, pool_dir="checkpoints_v6", opp_deterministic=False,
                 **kwargs):
        super().__init__(*args, **kwargs)
        # second view of the SAME ram, sorted around P1
        self._opp_synth = StateLineSynth(self._lr_bridge.ram, bot_player=1)
        self._lr_bridge.attach_synth(self._opp_synth)
        self._pool = OpponentPool(pool_dir)
        self._opp_model = None
        self._opp_det = opp_deterministic
        self._view_prev = {}   # agent_player -> previous parsed state
                               # (velocity deltas in _observe; cleared per ep)
        # a P1-perspective obs builder: reuse this env's own machinery by
        # keeping a light second parser state. AGENT_PLAYER handling: the v6
        # obs builder is written around index (AGENT_PLAYER-1); we flip it
        # per-call below.

    # -------------------------------------------------------- lifecycle
    def reset(self):
        self._opp_model = self._pool.sample()
        self._view_prev.clear()
        return super().reset()

    def step(self, action):
        # 1) opponent acts first (its held input persists through the
        #    learner's frames — mirrors two humans pressing simultaneously)
        if self._opp_model is not None:
            opp_obs = self._obs_from_view(self._opp_synth, agent_player=1)
            opp_action, _ = self._opp_model.predict(
                opp_obs, deterministic=self._opp_det)
            self._apply_action_for(int(opp_action), player_port=0,
                                   run=False)   # set mask only, no frames
        # 2) learner acts; frames run inside (both masks held during them)
        return super().step(action)

    # ------------------------------------------------------------ helpers
    def _apply_action_for(self, action, player_port, run):
        name, kind, val = self.ACTIONS[action]
        if kind == "btn":
            self._lr_bridge.press(val, 0 if not run else self.ACTION_FRAMES,
                                  player=player_port)
        else:
            self._lr_bridge.axis(val, self.AXIS_VALUE, 0 if not run else
                                 self.ACTION_FRAMES, player=player_port)

    def _obs_from_view(self, synth, agent_player):
        """Build a 122-dim obs from the given synth's line, from
        agent_player's perspective. Uses the parent obs builder with
        AGENT_PLAYER temporarily flipped — the builder reads the class
        attr; keep this section in sync if that changes.

        Aug 28 wiring (the NOTE at the bottom of this file, resolved):
        the parent's obs constructor is `_observe(s, prev)`. prev feeds
        the velocity deltas — tracked per view in self._view_prev (the
        parent passes (s, s) on its own reset, so first-call = s is the
        same convention). _active_opp must ALSO flip: the learner's
        [0] would make the P1 view list ITSELF as its opponent."""
        line = synth.line
        saved_line = self._lr_synth.line
        saved_agent = self.AGENT_PLAYER
        saved_active = self._active_opp
        try:
            self._lr_synth.line = line
            type(self).AGENT_PLAYER = agent_player
            # 1v1 mirror: the other port is the whole opponent set
            self._active_opp = [1] if agent_player == 1 else [0]
            s = self._parse_state_once()
            prev = self._view_prev.get(agent_player, s)
            obs = self._observe(s, prev)
            self._view_prev[agent_player] = s
            return obs
        finally:
            self._lr_synth.line = saved_line
            type(self).AGENT_PLAYER = saved_agent
            self._active_opp = saved_active


# NOTE resolved Aug 28: the obs constructor is _observe(s, prev) — wired
# above with per-view prev tracking and the _active_opp flip. Still worth
# eyeballing the first episodes: the P1 view is the one thing the Windows
# rig never exercised.
