"""Four-seat self-play free-for-all env (Sep 13 2026) — the OpenAI Five shape
applied to Power Stone 2: every fighter in the arena is a policy.

One emulator, four seats. The LEARNER keeps in-game P2 (DC port B) exactly
as the whole lineage did. The other seats (in-game P1, P3, P4 = ports A, C,
D) are driven by FROZEN policies sampled per episode from the pool, each
with its own StateLineSynth view (bot_player=k) and its own per-view state.
All three opponent actions are applied as held masks before the learner's
frames run (the same mechanism the 2-seat SelfPlayEnv used for one seat).

obs v2 contract (PS2_OBS_V2=1 is REQUIRED for this env):
  * last-action one-hot = a_t for every seat (the base env's OBS_V2 switch);
  * every non-learner view owns its gem count, form timer, last action and
    previous state — the v1 P1 view leaked the learner's _form_timer and
    _my_g_int into the opponent's obs (Sep 10 audit item 6). Here the view
    counters are updated from that seat's own form/gem transitions with the
    same rules the learner's counters follow (_counter_gems).

Savestate: Original-mode true FFA, desert, ALL FOUR SEATS HUMAN, all Falcon
(every pool policy is a Falcon policy), four distinct colours. Slot number
FFA_SLOT (default 0 on the Mac; documented re-stamp — Law 8). SLOT_META for
that slot mirrors slot1's context dims (1, 2): the model reads "self-play
regime" and sees the FFA-ness through the three opponent blocks.

Mechanical smoke without the four-human state: point STATE_SLOTS at slot 3
(lv8 COM FFA). The three views then build obs for COM-driven seats and their
actions land on COM ports (ignored by the game), which exercises every code
path except the opponents actually moving under policy control.

Pool sampling: PS2_POOL_SAMPLING=uniform (the league's 50/50 recent-10 /
uniform-history rule, unchanged) or pfsp (the "uniform-history" half becomes
p ∝ (1 - w)^2 + 0.05 where w is a per-opponent EMA of the learner's win
share; the episode outcome is credited to all sampled opponents).
"""
import os
import random

import numpy as np

from powerstone_env_libretro import PowerStoneEnvLibretro
from ps2_ram import StateLineSynth
from selfplay_env import OpponentPool

FFA_SLOT = int(os.environ.get("PS2_FFA_SLOT", "0"))


class PFSPPool(OpponentPool):
    """OpponentPool with an optional prioritized-fictitious-self-play mode."""

    def __init__(self, pool_dir, recent_k=10, sampling="uniform", ema=0.05):
        super().__init__(pool_dir, recent_k=recent_k)
        self.sampling = sampling
        self.ema = ema
        self.winrate = {}          # path -> EMA of learner win share (init 0.5)

    def sample(self):
        if not self.paths:
            return None
        if random.random() < 0.5:
            pick = random.choice(self.paths[-self.recent_k:])
        elif self.sampling == "pfsp":
            w = np.array([(1.0 - self.winrate.get(p, 0.5)) ** 2 + 0.05 for p in self.paths])
            pick = self.paths[int(np.random.choice(len(self.paths), p=w / w.sum()))]
        else:
            pick = random.choice(self.paths)
        self.last_path = pick
        if pick not in self._cache:
            if len(self._cache) > 20:
                self._cache.pop(next(iter(self._cache)))
            self._cache[pick] = self._PPO.load(pick, device="cpu")
        return self._cache[pick]

    def credit(self, path, won):
        w = self.winrate.get(path, 0.5)
        self.winrate[path] = (1 - self.ema) * w + self.ema * (1.0 if won else 0.0)


class SeatView:
    """Per-seat state for a policy-driven non-learner seat (obs v2 item b)."""

    def __init__(self, player_idx, synth):
        self.player = player_idx          # 0-based in-game index (0 = P1, 2 = P3, 3 = P4)
        self.synth = synth
        self.model = None
        self.path = None
        self.reset()

    def reset(self):
        self.prev = None
        self.last_action = 0
        self.g_int = 0
        self.form_timer = 0


class FFASelfPlayEnv(PowerStoneEnvLibretro):
    SLOT_META = dict(PowerStoneEnvLibretro.SLOT_META)
    SLOT_META[FFA_SLOT] = (1, 2)      # mirror slot1's context dims (pre-registered choice)
    # ANTI-STALL (Sep 14 2026, Blake's "fix" after leg 28's degenerate equilibrium:
    # entropy collapse, 10.6% of episodes at the 6,000-step cap, four copies of one
    # policy settling into mutual passivity). Two levers, both env-level:
    #   * a shorter episode cap on the FFA state (default 2,000 steps; leg 27's
    #     p90 was 690, so real fights are not cut);
    #   * a timeout is scored as a LOSS (the same terminal penalty as being
    #     knocked out) so running the clock can never beat fighting.
    # Pool sampling goes back to uniform for the same reason (league_leg_async.sh).
    MAX_STEPS = int(os.environ.get("PS2_FFA_MAX_STEPS", "2000"))
    TIMEOUT_IS_LOSS = os.environ.get("PS2_FFA_TIMEOUT_LOSS", "1") == "1"

    def __init__(self, *args, pool_dir="pool_league", seats=None,
                 sampling=None, opp_deterministic=False, **kwargs):
        # Sep 15 (Blake): MIXED variant — PS2_FFA_SEATS="0,2" makes seats P1 and P3
        # policy-driven and leaves P4 to the game's COM (a permanent aggression
        # source against the four-copies-of-one-policy stall). Default "0,2,3" =
        # pure four-policy FFA. The learner's opponent set still covers every
        # other seat (COM included); a COM seat simply has no view and no mask.
        if seats is None:
            seats = tuple(int(x) for x in os.environ.get("PS2_FFA_SEATS", "0,2,3").split(","))
        if not self.OBS_V2:
            raise RuntimeError("FFASelfPlayEnv requires PS2_OBS_V2=1 (obs v2 contract)")
        super().__init__(*args, **kwargs)
        self._views = {}
        for k in seats:
            synth = StateLineSynth(self._lr_bridge.ram, bot_player=k + 1)
            self._lr_bridge.attach_synth(synth)
            self._views[k] = SeatView(k, synth)
        sampling = sampling or os.environ.get("PS2_POOL_SAMPLING", "uniform")
        self._pool = PFSPPool(pool_dir, sampling=sampling)
        self._opp_det = opp_deterministic
        self._learner_idx = self.AGENT_PLAYER - 1

    # ---------------------------------------------------------------- lifecycle
    def reset(self):
        for v in self._views.values():
            v.reset()
            v.model = self._pool.sample()
            v.path = self._pool.last_path if v.model is not None else None
        if any(v.model is not None for v in self._views.values()):
            print("[opp] " + " ".join(f"P{v.player + 1}={os.path.basename(v.path)}"
                                      for v in self._views.values() if v.path))
        return super().reset()

    def step(self, action):
        # 1) every policy-driven seat acts first; masks persist through the
        #    learner's frames (four humans pressing simultaneously)
        for v in self._views.values():
            if v.model is None:
                continue
            obs_v = self._obs_from_view(v)
            a, _ = v.model.predict(obs_v, deterministic=self._opp_det)
            v.last_action = int(a)
            self._apply_action_for(int(a), player_port=v.player, run=False)
        # 2) learner acts; frames run inside
        obs, r, done, info = super().step(action)
        if done and info.get("timeout") and self.TIMEOUT_IS_LOSS and "result" not in info:
            level = self.SLOT_META.get(getattr(self, "_episode_slot", 0), (0, 2))[1]
            r -= self.LOSS_PENALTY * self.LOSS_SCALE_BY_LEVEL.get(level, 1.0)
            info["result"] = "timeout"          # keeps the [ep] label; scored as a loss
        if done and self._pool.sampling == "pfsp":
            won = info.get("result") == "win"
            for v in self._views.values():
                if v.path:
                    self._pool.credit(v.path, won)
        return obs, r, done, info

    # ------------------------------------------------------------------ helpers
    def _apply_action_for(self, action, player_port, run):
        name, kind, val = self.ACTIONS[action]
        if kind == "btn":
            self._lr_bridge.press(val, 0 if not run else self.ACTION_FRAMES,
                                  player=player_port)
        else:
            self._lr_bridge.axis(val, self.AXIS_VALUE, 0 if not run else
                                 self.ACTION_FRAMES, player=player_port)

    def _view_opponents(self, k):
        """The seats a view fights: the learner plus every tracked opponent
        other than itself (the learner's _active_opp is the tracked set)."""
        others = [self._learner_idx] + [j for j in self._active_opp if j != k]
        return sorted(set(j for j in others if j != k))

    def _update_view_counters(self, v, s):
        """Mirror the learner's gem/form bookkeeping for this seat, from its
        OWN transitions (obs v2 item b): FORM_STEPS on transform, >=2 while
        formed, one-step drain, gem count clamped 0..3."""
        me_n = s["players"][v.player]
        me_p = (v.prev or s)["players"][v.player]
        if me_n["form"] == 1 and me_p["form"] == 0:
            v.form_timer = self.FORM_STEPS
        if me_n["form"] == 1:
            v.form_timer = max(v.form_timer, 2)
        v.g_int = max(0, min(3, int(me_n.get("gems", 0))))
        if v.form_timer > 0:
            v.form_timer -= 1

    def _obs_from_view(self, v):
        line = v.synth.line
        if not line:
            return np.zeros(self.OBS_DIM, dtype=np.float32)
        s = self._parse_line(line)
        if s is None:
            return np.zeros(self.OBS_DIM, dtype=np.float32)
        self._update_view_counters(v, s)
        saved = (self.AGENT_PLAYER, self._active_opp, self.last_action,
                 self._my_g_int, self._form_timer)
        try:
            type(self).AGENT_PLAYER = v.player + 1
            self._active_opp = self._view_opponents(v.player)
            self.last_action = v.last_action
            self._my_g_int = v.g_int
            self._form_timer = v.form_timer
            prev = v.prev if v.prev is not None else s
            obs = self._observe(s, prev)
        finally:
            (type(self).AGENT_PLAYER, self._active_opp, self.last_action,
             self._my_g_int, self._form_timer) = saved
        v.prev = s
        return obs
