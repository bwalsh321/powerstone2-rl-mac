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
docs/README_PORT.md step 5.
"""
import os
import random

import numpy as np

from powerstone_env_libretro import PowerStoneEnvLibretro
from ps2_ram import StateLineSynth


class OpponentPool:
    """Frozen SB3 policies sampled per episode.

    Sampling: 50% uniform over the newest `recent_k`, 50% uniform over the
    full history — 50/50 recency-history sampling (NOT true PFSP: no
    performance-based priorities). The path list is loaded ONCE at
    construction; the pool is frozen for the whole leg and grows only
    between legs."""

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
        # Sep 2 review fix: sort by MTIME, not filename step-number — the
        # old key parsed "<n>_steps" (0 for finals/seeds), which made the
        # "recent" half of sampling permanently = leg1's 28-31.9M snapshots
        # and buried every prog_* final at the bottom. mtime makes "recent"
        # mean what it says across fresh-clock legs and untagged finals.
        import os as _os
        self.paths = sorted(zips, key=lambda p: _os.path.getmtime(p))

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
        self.last_path = pick   # Aug 28: exposed so the env can log WHO
                                # each episode was against — without it a
                                # high learner win% is unreadable (crushing
                                # 0.2M-15M relics vs beating 27.9M peers)
        if pick not in self._cache:
            if len(self._cache) > 20:      # LRU-ish: don't hold 250 models
                self._cache.pop(next(iter(self._cache)))
            from recurrent_policy import load_model
            self._cache[pick] = load_model(pick)   # Oct 2: PPO or RecurrentPPO
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
        self._view_ctr = {}    # agent_player -> [form_timer, g_int] (Sep 25: per-seat, no learner leak)
                               # (velocity deltas in _observe; cleared per ep)
        self._view_last = {}   # agent_player -> that view's own last action
        # a P1-perspective obs builder: reuse this env's own machinery by
        # keeping a light second parser state. AGENT_PLAYER handling: the v6
        # obs builder is written around index (AGENT_PLAYER-1); we flip it
        # per-call below.

    # -------------------------------------------------------- lifecycle
    def reset(self):
        self._opp_model = self._pool.sample()
        if self._opp_model is not None:
            print(f"[opp] {os.path.basename(self._pool.last_path)}")
        self._view_prev.clear()
        self._view_last.clear()
        self._view_ctr.clear()
        self._opp_stack = None
        self._opp_runner = None        # Oct 2: per-episode stateful runner (recurrent opponents)
        self._view_last_n = 10         # Oct 3: the view's reset-time last action (0) is a legacy index
        return super().reset()

    def step(self, action):
        # 1) opponent acts first (its held input persists through the
        #    learner's frames — mirrors two humans pressing simultaneously)
        if self._opp_model is not None:
            from obs_stack import kd_for
            kv, dv = kd_for(self._opp_model)
            self._legacy_proj = (dv == 122)               # Sep 25: v2 opponent -> v2-rule projectiles
            self._legacy_item = (dv <= 160)               # Oct 5 (obs v4): a v2/v3 opponent keeps [12..17], no v4 block
            try:
                opp_obs = self._obs_from_view(self._opp_synth, agent_player=1)
            finally:
                self._legacy_proj = getattr(self, "_legacy_proj_main", False)   # Sep 28: keep the main model's contract
                self._legacy_item = getattr(self, "_legacy_item_main", False)
            if dv < opp_obs.shape[0]:
                opp_obs = opp_obs[:dv]                    # Sep 23: v2 opponent under an obs v3 env
            if kv > 1:                                   # Sep 22: stacked opponent model
                st = getattr(self, "_opp_stack", None)
                if st is None or st.k != kv or getattr(self, "_opp_stack_model", None) is not self._opp_model:
                    from obs_stack import FrameStack
                    st = FrameStack(kv, opp_obs.shape[0]); self._opp_stack = st; self._opp_stack_model = self._opp_model
                    opp_obs = st.reset(opp_obs)
                else:
                    opp_obs = st.push(opp_obs)
            if self._opp_runner is None or self._opp_runner.model is not self._opp_model:
                from recurrent_policy import PolicyRunner
                self._opp_runner = PolicyRunner(self._opp_model)
            opp_action = self._opp_runner.act(opp_obs, deterministic=self._opp_det)
            self._view_last[1] = int(opp_action)
            self._view_last_n = int(self._opp_model.action_space.n)    # Oct 3: 10 legacy / 63 joint
            self._apply_action_for(int(opp_action), player_port=0,
                                   run=False, n_act=self._view_last_n)   # set mask only, no frames
        # 2) learner acts; frames run inside (both masks held during them)
        return super().step(action)

    # ------------------------------------------------------------ helpers
    def _apply_action_for(self, action, player_port, run, n_act=10):
        # Oct 3 2026: n_act = the acting model's action-set size (10 legacy / 63 joint, action_space.py).
        from action_space import JOINT_TO_LEGACY
        a = int(action)
        legacy = a if n_act == len(self.ACTIONS) else JOINT_TO_LEGACY.get(a)
        if legacy is None:
            from action_space import execution
            dmask, axis, _frames = execution(a, n_act, self.ACTION_FRAMES)
            self._lr_bridge.combo(dmask, axis, 0 if not run else self.ACTION_FRAMES, player=player_port)
            return
        name, kind, val = self.ACTIONS[legacy]
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
        [0] would make the P1 view list ITSELF as its opponent.

        Aug 28 fix #7: parse the view's line via _parse_line DIRECTLY.
        The first wiring pinned it onto _lr_synth.line and called
        _parse_state_once — but the pump-on-stale check fires on EVERY
        opponent read (last parse is always the same frame), runs a
        frame, and the tick invalidates the pin: the opponent was
        parsing the LEARNER-sorted line all along (own pos/health fine —
        player blocks are port-ordered — but stones/chests/projectiles
        sorted around its enemy). Signature: learner 62W/4L in bring-up.
        _parse_line is the pure path: no pin, no pump, no
        _last_parsed_frame touch — learner cadence is unaffected.

        KNOWN ISSUE (Sep 10 external audit, confirmed, NOT fixed here):
        this swap covers AGENT_PLAYER, _active_opp and last_action only.
        _observe() also reads self._form_timer (obs[9] fallback when the
        view's own form flag is off) and self._my_g_int (gem fallback),
        which are the LEARNER's counters. An untransformed P1 can thus
        read a full own-form feature while P2's timer is running. This
        touches the frozen opponent's view in training and the reference
        seat in ab_selfplay_probe.py; it does not touch the slot-2/slot-3
        COM evaluations (no PPO opponent there). Fixing it changes the
        observation contract mid-lineage, so it is deferred to the end of
        the pre-registered campaign and will ship as a versioned
        observation change with old/new AB results kept separate. Also
        note the learner's last-action one-hot is one step older than the
        opponent view's (see powerstone_env_v6.step)."""
        line = synth.line
        if not line:
            return np.zeros(self.OBS_DIM, dtype=np.float32)
        saved_agent = self.AGENT_PLAYER
        saved_active = self._active_opp
        saved_last = self.last_action
        saved_last_n = self._last_n
        saved_ctr = (self._form_timer, self._my_g_int)
        try:
            type(self).AGENT_PLAYER = agent_player
            # 1v1 mirror: the other port is the whole opponent set
            self._active_opp = [1] if agent_player == 1 else [0]
            # last-action one-hot must be the VIEW's own last action, not
            # the learner's (obs[_ACT0+..] reads self.last_action — combo/
            # timing state; feeding the enemy's action corrupts it)
            self.last_action = self._view_last.get(agent_player, 0)
            self._last_n = getattr(self, "_view_last_n", 10) if agent_player == 1 else self.N_ACT
            s = self._parse_line(line)
            if s is None:
                return np.zeros(self.OBS_DIM, dtype=np.float32)
            prev = self._view_prev.get(agent_player, s)
            # Sep 25 2026 (Astra, the "KNOWN ISSUE" above, now fixed): the view's own form timer and
            # gem fallback, mirrored from ITS transitions exactly like FFASelfPlayEnv._update_view_counters,
            # so an untransformed P1 never reads the learner's running timer as its own form.
            ctr = self._view_ctr.setdefault(agent_player, [0, 0])
            me_n = s["players"][agent_player - 1]; me_p = prev["players"][agent_player - 1]
            if me_n.get("form", 0) == 1 and me_p.get("form", 0) == 0:
                ctr[0] = self.FORM_STEPS
            if me_n.get("form", 0) == 1:
                ctr[0] = max(ctr[0], 2)
            ctr[1] = max(0, min(3, int(me_n.get("gems", 0) if me_n.get("gems", -1) >= 0 else ctr[1])))
            if ctr[0] > 0:
                ctr[0] -= 1
            self._form_timer, self._my_g_int = ctr[0], ctr[1]
            obs = self._observe(s, prev)
            self._view_prev[agent_player] = s
            return obs
        finally:
            type(self).AGENT_PLAYER = saved_agent
            self._active_opp = saved_active
            self.last_action = saved_last
            self._last_n = saved_last_n
            self._form_timer, self._my_g_int = saved_ctr


# NOTE resolved Aug 28: the obs constructor is _observe(s, prev) — wired
# above with per-view prev tracking and the _active_opp flip. Still worth
# eyeballing the first episodes: the P1 view is the one thing the Windows
# rig never exercised.
