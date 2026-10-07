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

import struct

import numpy as np

import ps2_addr as A
from powerstone_env_libretro import PowerStoneEnvLibretro
from ps2_ram import StateLineSynth
from selfplay_env import OpponentPool

FFA_SLOT = int(os.environ.get("PS2_FFA_SLOT", "0"))

# Sep 20 2026 (Blake: "Test what you can without me ... Go for it"), after reading
# https://openai.com/index/openai-five/ together (Sep 17): two TRAINING-ONLY arena levers,
# both inert unless set (evals use the base env and never set them):
#   PS2_ZERO_SUM=1      every present seat is scored with ONE consistent shaped-reward
#                       function (the learner's constants; damage attributed to the
#                       NEAREST alive other seat), and the learner's reward becomes
#                       r_learner - mean(r_other seats). OpenAI Five: "subtracting the
#                       other team's average reward to prevent the agents from finding
#                       positive-sum situations" (stone farming is ours).
#   PS2_START_HEALTH=lo,hi   at reset, every present seat's health is multiplied by an
#                       independent U(lo, hi) draw written straight into SYSTEM_RAM
#                       (ps2_addr.HEALTH, float32; verified Sep 20: the value sticks and
#                       damage applies on top of it). OpenAI Five randomized unit
#                       properties "to force exploration in strategy space".
ZERO_SUM = os.environ.get("PS2_ZERO_SUM", "0") == "1"
ZS_TIME = os.environ.get("PS2_ZS_TIME", "1") == "1"   # Sep 23: learner time cost after zero-sum
# Sep 26 2026 (Blake: "cancel this run and adjust the rewards"; NEXT MOVES #2, pre-registered):
#   PS2_SPECIAL_DMG_W  extra cost per unit of health lost while ANY other present seat within
#                      PS2_SPECIAL_R (xz units) is in obs-v3 state 25/26 (transforming / special in
#                      progress). Needs the v9 line (pstate); 0 = off.
#   PS2_LOST_EXTRA_W   extra cost per stone knocked off the seat, OUTSIDE the per-episode gem cap
#                      (the active diet's LOST_W is 0 since the Leg F ablation). 0 = off.
# Both are applied to every seat inside the zero-sum sum (same constants for all), like the rest.
SPECIAL_DMG_W = float(os.environ.get("PS2_SPECIAL_DMG_W", "0"))
SPECIAL_R = float(os.environ.get("PS2_SPECIAL_R", "700"))
LOST_EXTRA_W = float(os.environ.get("PS2_LOST_EXTRA_W", "0"))
# Sep 27 2026 (Blake: "do both"): PS2_SPECIAL_WINDOW = seconds a seat stays "in a special" for the
# special-damage term AFTER its state leaves 25/26. Legs 86-87 showed spec_pen ~ -0.09/round because
# rockets / missiles / beams land after the caster's state clears (~1.6 s). 0 = state-only (legs 86-88).
SPECIAL_WINDOW = float(os.environ.get("PS2_SPECIAL_WINDOW", "0"))
# Sep 28 2026 (Astra review 3, finding 1): the window clock. "steps" = the legs 89-93 behavior (20 DECISIONS;
# movement decisions run 10 frames, others 6, so the real span is 2.0-3.3 s). "frames" = emulator frames
# from the state line (120 frames = a true 2.0 s). Changing the clock is a reward-contract change: Blake's call.
SPECIAL_WINDOW_CLOCK = os.environ.get("PS2_SPECIAL_WINDOW_CLOCK", "steps")
# Sep 28 (Astra review 3, finding 2): optional per-hit event log for the learner (frame, damage, caster
# state / frames since special / distance, whether the term fired). Diagnostics only; 0/unset = off.
SPECIAL_EVENTS = os.environ.get("PS2_SPECIAL_EVENTS", "")
# Sep 29 2026 (Blake: "learner-only attribution fix next as a two-leg read"): PS2_SPECIAL_ATTRIB=1 replaces the
# radius heuristic with the game's own attribution and applies the special-damage cost to the LEARNER ONLY.
# RAM: each player object carries a 32-bit physical pointer to the object that last hit it at PLAYER_MAT+0x32E4
# (scan Sep 29: written on the hit frame; 36% of hits point straight at another player's object, that seat was in
# an attack/special state in 98% of those, never the victim; 64% point at a projectile / item object whose OWNER
# pointer sits at +0x10, naming a seat that was in an attack/special state in 100% of the resolvable cases).
# Under attrib, opponent seats get NO special term (the two-sided bonus side is removed).
SPECIAL_ATTRIB = os.environ.get("PS2_SPECIAL_ATTRIB", "0") == "1"
HITSRC_OFF = 0x32E4            # PLAYER_MAT[k] + HITSRC_OFF: u32 physical pointer to the last hit source
HITSRC_OWNER_OFF = 0x10        # inside a non-player source object: u32 physical pointer to the owning player object
PLAYER_OBJ_LEAD, PLAYER_OBJ_LEN = 0x490, 0x3938
_SH = os.environ.get("PS2_START_HEALTH", "").strip()
START_HEALTH = tuple(float(x) for x in _SH.split(",")) if _SH else None


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
            from recurrent_policy import load_model
            self._cache[pick] = load_model(pick)   # Oct 2: PPO or RecurrentPPO
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
        self.n_act = 10            # Oct 3: action-set size of this seat's model (10 legacy / 63 joint)
        self.g_int = 0
        self.form_timer = 0
        self.stack = None          # Sep 22: FrameStack for a K-frame opponent model (None = single-frame)
        self.runner = None         # Oct 2: per-episode stateful runner (recurrent pool policies keep LSTM state)


def ffa_slot_meta(state_slots, base_meta=None):
    """The mixed-arena context table for a configured slot list (Sep 25 2026, one function so the
    constructor and test_obs_context.py cannot drift): COM-only lv8 arenas 1-9 / 50-68 (60-68 = Oct 6 balanced lineups) / 90-94 keep the
    base (stage 2, level 8) entry; slots 30-43 = P4 COM at level 8 -> (1, 8); every other slot (0, 10-22,
    unknown) = (1, 2), the pre-registered mixed-arena context."""
    meta = dict(base_meta if base_meta is not None else PowerStoneEnvLibretro.SLOT_META)
    for _slot in state_slots:
        if (1 <= _slot <= 9 or 50 <= _slot <= 68 or 90 <= _slot <= 94) and _slot in PowerStoneEnvLibretro.SLOT_META:
            continue
        meta[_slot] = (1, 8) if 30 <= _slot <= 43 else (1, 2)
    return meta


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
        # Sep 20 (character randomization): every configured state slot is an FFA/mixed
        # arena and carries the same (1, 2) context as slot 0, whatever character lineup
        # it was stamped with (the learner is always Falcon in P2; obs has no character id).
        self.SLOT_META = ffa_slot_meta(self.STATE_SLOTS, self.SLOT_META)
        self._views = {}
        for k in seats:
            synth = StateLineSynth(self._lr_bridge.ram, bot_player=k + 1)
            self._lr_bridge.attach_synth(synth)
            self._views[k] = SeatView(k, synth)
        sampling = sampling or os.environ.get("PS2_POOL_SAMPLING", "uniform")
        self._pool = PFSPPool(pool_dir, sampling=sampling)
        self._opp_det = opp_deterministic
        self._learner_idx = self.AGENT_PLAYER - 1
        self._zs_gem = {}          # per-seat cumulative gem reward this episode (cap mirror)
        self._zs = None            # per-episode zero-sum telemetry
        self._spec_win = int(round(SPECIAL_WINDOW * 60.0 / self.ACTION_FRAMES))   # window in env steps (clock=steps)
        self._spec_win_frames = int(round(SPECIAL_WINDOW * 60.0))                 # window in emulator frames (clock=frames)
        self._spec_clock = SPECIAL_WINDOW_CLOCK
        self._spec_last = {}       # seat -> env step index when last seen in state 25/26
        self._spec_last_frame = {} # seat -> emulator frame when last seen in state 25/26
        self._spec_t = 0           # env step counter (reset per episode)
        self._spec_now_frame = None
        self._pen_step = {}        # seat -> [spec_pen, lost_pen] for the current step (net telemetry)
        self._ev = open(SPECIAL_EVENTS, "a") if SPECIAL_EVENTS not in ("", "0") else None
        if ZERO_SUM:
            print("[config] zero_sum=1 (r = own - mean(others); nearest-attacker damage attribution)", flush=True)
            if SPECIAL_DMG_W > 0.0 or LOST_EXTRA_W > 0.0:
                print(f"[config] reward2: special_dmg_w={SPECIAL_DMG_W} special_r={SPECIAL_R:.0f} lost_extra_w={LOST_EXTRA_W}"
                      f" special_window={SPECIAL_WINDOW:g}s ({self._spec_win} steps | {self._spec_win_frames} frames, clock={self._spec_clock})"
                      f" loss_scale_lv8={self.LOSS_SCALE_BY_LEVEL.get(8)}"
                      + (" special_attrib=1 (learner-only; +0x32e4 hit source, owner +0x10)" if SPECIAL_ATTRIB else ""), flush=True)
        if START_HEALTH:
            print(f"[config] start_health=U{START_HEALTH} per seat (RAM write at reset)", flush=True)

    # ---------------------------------------------------------------- lifecycle
    def reset(self):
        for v in self._views.values():
            v.reset()
            v.model = self._pool.sample()
            v.path = self._pool.last_path if v.model is not None else None
        if any(v.model is not None for v in self._views.values()):
            print("[opp] " + " ".join(f"P{v.player + 1}={os.path.basename(v.path)}"
                                      for v in self._views.values() if v.path))
        obs = super().reset()
        self._zs_gem = {}
        self._spec_last = {}
        self._spec_last_frame = {}
        self._spec_t = 0
        self._zs = {"raw": 0.0, "opp_mean": 0.0, "adj": 0.0, "dealt_nn": 0.0, "n": 0}
        if START_HEALTH:
            obs = self._randomize_start_health()
        return obs

    # ------------------------------------------------ start randomization
    def _present_seats(self):
        return [self._learner_idx] + [j for j in self._active_opp if j != self._learner_idx]

    def _randomize_start_health(self):
        """Multiply every present seat's health by an independent U(lo, hi) draw,
        written into SYSTEM_RAM, then re-anchor prev/prev_health/views so the first
        step does not read the write as damage. baseline stays max(h, 1000)."""
        lo, hi = START_HEALTH
        ram = self._lr_bridge.ram
        base = A.RAM_BASE + A.RAM_DELTA
        s = self._read_state()
        drawn = []
        for k in self._present_seats():
            f = random.uniform(lo, hi)
            v = float(s["h"][k]) * f
            packed = np.frombuffer(struct.pack("<f", v), dtype=np.uint8)
            for addr in (A.HEALTH_OBJ[k], A.HEALTH[k], A.HEALTH[k] + 0x30, A.HEALTH[k] + 0x50):
                o = addr - base
                ram[o:o + 4] = packed          # primary object field + display mirrors
            drawn.append(f"P{k + 1}={v:.0f}")
        self._lr_bridge.run_frames(2)
        s = self._read_state()
        self.prev = s
        self.prev_health = self._frac(s["h"])
        for v in self._views.values():
            v.prev = None
        print("[start] health " + " ".join(drawn), flush=True)
        return self._observe(s, s)

    def step(self, action):
        # 1) every policy-driven seat acts first; masks persist through the
        #    learner's frames (four humans pressing simultaneously)
        for v in self._views.values():
            if v.model is None:
                continue
            from obs_stack import kd_for
            kv, dv = kd_for(v.model)
            self._legacy_proj = (dv == 122)     # Sep 25: v2 policy -> v2-rule projectile prefix
            # Oct 5 2026 (obs v4): a <=160-dim pool policy keeps the slot-hash [12..17] it was trained on, and the
            # v4 block is not computed for its view (sliced away below). Inert unless PS2_OBS_V4=1.
            self._legacy_item = (dv <= 160)
            try:
                obs_v = self._obs_from_view(v)
            finally:
                self._legacy_proj = getattr(self, "_legacy_proj_main", False)   # Sep 28: keep the main model's contract
                self._legacy_item = getattr(self, "_legacy_item_main", False)
            if dv < obs_v.shape[0]:
                obs_v = obs_v[:dv]              # Sep 23: v2 pool policy under an obs v3 env (Oct 5: v3 under v4)
            elif dv > obs_v.shape[0]:
                raise RuntimeError(f"pool model {v.path} reads {dv}/frame but this env builds {obs_v.shape[0]} "
                                   f"(a v4 pool zip under a PS2_OBS_V4=0 env?)")
            if kv > 1:                                   # stacked pool policy: keep its own history
                if v.stack is None:
                    from obs_stack import FrameStack
                    v.stack = FrameStack(kv, obs_v.shape[0]); obs_v = v.stack.reset(obs_v)
                else:
                    obs_v = v.stack.push(obs_v)
            if v.runner is None or v.runner.model is not v.model:
                from recurrent_policy import PolicyRunner
                v.runner = PolicyRunner(v.model)
            a = v.runner.act(obs_v, deterministic=self._opp_det)
            v.last_action = int(a)
            v.n_act = int(v.model.action_space.n)
            self._apply_action_for(int(a), player_port=v.player, run=False, n_act=v.n_act)
        # 2) learner acts; frames run inside
        prev_s, prev_h = self.prev, list(self.prev_health)
        obs, r, done, info = super().step(action)
        if ZERO_SUM:
            r = self._zero_sum_reward(prev_s, prev_h, self.prev, self.prev_health, info)
            if done:
                z = self._zs
                print(f"[zs] raw={z['raw']:+.2f} opp_mean={z['opp_mean']:+.2f} adj={z['adj']:+.2f} "
                      f"dealt_nn={z['dealt_nn']:.2f} steps={z['n']}"
                      + (f" spec_pen={z.get('spec_pen', 0.0):+.2f} lost_pen={z.get('lost_pen', 0.0):+.2f}"
                         f" spec_net={z.get('spec_net', 0.0):+.2f} lost_net={z.get('lost_net', 0.0):+.2f}"
                         if (SPECIAL_DMG_W > 0.0 or LOST_EXTRA_W > 0.0) else "")
                      + (f" attr={z.get('attr_p', 0)}/{z.get('attr_n', 0)} spec_dmg={z.get('spec_dmg', 0.0):.2f}" if SPECIAL_ATTRIB else ""), flush=True)
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

    # ------------------------------------------------------------ zero-sum
    def _seat_reward(self, k, prev_s, s, prev_h, h, dealt, present, level):
        """The learner's shaped reward function applied to seat k (same constants,
        same gem cap rule), with damage dealt = drops attributed to k by nearest
        alive attacker. Approach/stone-shape/chest terms are 0 in the active diet
        and are not mirrored."""
        pk, nk = prev_s["players"][k], s["players"][k]
        in_form = nk.get("form") == 1
        dmg_w = self.DAMAGE_DEALT_W * (self.FORM_DMG_MULT if in_form else 1.0)
        own_delta = h[k] - prev_h[k]
        gem = 0.0
        if pk.get("gems", -1) >= 0 and nk.get("gems", -1) >= 0:
            d = nk["gems"] - pk["gems"]
            formed = nk.get("form") == 1 and pk.get("form") == 0
            if formed:
                gem += self.TRANSFORM_BONUS
            if d > 0:
                gem += self.GEM_W * d
            elif d < 0 and not formed and pk.get("form") != 1:
                gem -= self.LOST_W * (-d)
        g0 = self._zs_gem.get(k, 0.0)
        neg_cap = 1.5 if level >= 8 else self.GEM_EP_CAP_NEG
        gem = max(-neg_cap - g0, min(gem, self.GEM_EP_CAP - g0))
        self._zs_gem[k] = g0 + gem
        rk = (dmg_w * dealt.get(k, 0.0)
              + self.DAMAGE_TAKEN_W * min(0.0, own_delta)
              + gem - self.TIME_PENALTY)
        # Sep 26 reward levers (see module flags): special-death cost and stone-retention cost
        if SPECIAL_DMG_W > 0.0 and own_delta < 0.0 and SPECIAL_ATTRIB:
            # Sep 29: learner-only, game-attributed. Opponent seats: no special term.
            if k == self._learner_idx:
                pst = s.get("pstate")
                att = self._hit_attacker(k)
                z = self._zs
                if z is not None:
                    z["attr_p" if att is not None else "attr_n"] = z.get("attr_p" if att is not None else "attr_n", 0) + 1
                if att is not None and pst is not None and att < len(pst) and self._in_special(att, pst):
                    pen = SPECIAL_DMG_W * own_delta
                    rk += pen
                    self._pen_step.setdefault(k, [0.0, 0.0])[0] += pen
                    if z is not None:
                        z["spec_pen"] = z.get("spec_pen", 0.0) + pen
                        z["spec_dmg"] = z.get("spec_dmg", 0.0) + (-own_delta)
        elif SPECIAL_DMG_W > 0.0 and own_delta < 0.0:
            pst = s.get("pstate")
            if pst is not None:
                px, pz = pk["pos"][0], pk["pos"][2]
                for m in present:
                    if m != k and self._in_special(m, pst) and self._alive(prev_h[m]):
                        pm = prev_s["players"][m]["pos"]
                        if (px - pm[0]) ** 2 + (pz - pm[2]) ** 2 <= SPECIAL_R * SPECIAL_R:
                            pen = SPECIAL_DMG_W * own_delta            # own_delta < 0
                            rk += pen
                            self._pen_step.setdefault(k, [0.0, 0.0])[0] += pen
                            if self._zs is not None and k == self._learner_idx:
                                self._zs["spec_pen"] = self._zs.get("spec_pen", 0.0) + pen
                            break
        if LOST_EXTRA_W > 0.0 and pk.get("gems", -1) >= 0 and nk.get("gems", -1) >= 0:
            d_ = nk["gems"] - pk["gems"]
            if d_ < 0 and not (nk.get("form") == 1 and pk.get("form") == 0) and pk.get("form") != 1:
                pen = -LOST_EXTRA_W * (-d_)
                rk += pen
                self._pen_step.setdefault(k, [0.0, 0.0])[1] += pen
                if self._zs is not None and k == self._learner_idx:
                    self._zs["lost_pen"] = self._zs.get("lost_pen", 0.0) + pen
        alive_p, alive_n = self._alive(prev_h[k]), self._alive(h[k])
        others_alive_now = any(self._alive(h[m]) for m in present if m != k)
        others_alive_prev = any(self._alive(prev_h[m]) for m in present if m != k)
        if alive_p and not alive_n:
            rk -= self.LOSS_PENALTY * self.LOSS_SCALE_BY_LEVEL.get(level, 1.0)
        elif alive_n and others_alive_prev and not others_alive_now:
            rk += self.WIN_BONUS
        return rk

    def _zero_sum_reward(self, prev_s, prev_h, s, h, info):
        i = self._learner_idx
        present = [k for k in self._present_seats() if k < len(h)]
        level = self.SLOT_META.get(getattr(self, "_episode_slot", 0), (0, 2))[1]
        # attribute every seat's health drop to its nearest alive other seat (xz plane)
        dealt = {}
        for k in present:
            drop = max(0.0, prev_h[k] - h[k])
            if drop <= 0.0:
                continue
            pk = prev_s["players"][k]["pos"]
            best, bd = None, float("inf")
            for m in present:
                if m == k or not self._alive(prev_h[m]):
                    continue
                pm = prev_s["players"][m]["pos"]
                d = (pk[0] - pm[0]) ** 2 + (pk[2] - pm[2]) ** 2
                if d < bd:
                    best, bd = m, d
            if best is not None:
                dealt[best] = dealt.get(best, 0.0) + drop
        # Sep 27: special-window bookkeeping (state 25/26 seen this step -> stamp the seat, in steps AND frames)
        pst = s.get("pstate")
        self._spec_now_frame = s.get("frame")
        if pst is not None:
            for m in present:
                if m < len(pst) and pst[m] in (25, 26):
                    self._spec_last[m] = self._spec_t
                    if self._spec_now_frame is not None:
                        self._spec_last_frame[m] = self._spec_now_frame
        self._pen_step = {}
        rs = {k: self._seat_reward(k, prev_s, s, prev_h, h, dealt, present, level) for k in present}
        self._spec_t += 1
        # Sep 28 (Astra review 3, finding 2): the learner's NET penalty contribution = own - mean(others)
        z0 = self._zs
        if z0 is not None and (SPECIAL_DMG_W > 0.0 or LOST_EXTRA_W > 0.0):
            oth = [m for m in present if m != i]
            for j, key in ((0, "spec_net"), (1, "lost_net")):
                own = self._pen_step.get(i, [0.0, 0.0])[j]
                om = (sum(self._pen_step.get(m, [0.0, 0.0])[j] for m in oth) / len(oth)) if oth else 0.0
                z0[key] = z0.get(key, 0.0) + (own - om)
        if self._ev is not None and h[i] < prev_h[i] and pst is not None:
            # one line per learner damage event: frame dmg fired | per other seat: state, frames-since-special, dist
            px, pz = prev_s["players"][i]["pos"][0], prev_s["players"][i]["pos"][2]
            cols = []
            for m in present:
                if m == i or m >= len(pst):
                    continue
                pm = prev_s["players"][m]["pos"]
                d_ = ((px - pm[0]) ** 2 + (pz - pm[2]) ** 2) ** 0.5
                lf = self._spec_last_frame.get(m)
                since = (self._spec_now_frame - lf) if (lf is not None and self._spec_now_frame is not None) else -1
                cols.append(f"m{m}:st={pst[m]},since={since},dist={d_:.0f},alive={int(self._alive(prev_h[m]))}")
            fired = self._pen_step.get(i, [0.0, 0.0])[0] != 0.0
            self._ev.write(f"frame={self._spec_now_frame} dmg={prev_h[i]-h[i]:.3f} fired={int(fired)} slot={getattr(self, '_episode_slot', -1)} "
                           + " ".join(cols) + "\n")
            self._ev.flush()
        others = [rs[k] for k in present if k != i]
        opp_mean = sum(others) / len(others) if others else 0.0
        adj = rs[i] - opp_mean
        # Sep 23 2026 (Astra review #9): the per-seat TIME_PENALTY cancels exactly under the
        # mean subtraction (same cost on every seat), so legs 55-71 trained with NO per-step
        # time cost. Re-apply it after the relative step; PS2_ZS_TIME=0 reverts.
        if ZS_TIME:
            adj -= self.TIME_PENALTY
        z = self._zs
        if z is not None:
            z["raw"] += rs[i]; z["opp_mean"] += opp_mean; z["adj"] += adj
            z["dealt_nn"] += dealt.get(i, 0.0); z["n"] += 1
        info["r_raw"], info["r_opp_mean"] = rs[i], opp_mean
        return adj

    def _hit_attacker(self, k):
        """Seat index that last hit seat k per the game's own bookkeeping, or None (null / unowned hazard).
        Reads RAM directly (no state-line change): PLAYER_MAT[k]+0x32E4 -> source object; if the source is
        another player object that seat is the attacker; otherwise the source's +0x10 owner pointer."""
        ram = self._lr_bridge.ram
        src = self._ram_u32(ram, A.PLAYER_MAT[k] + HITSRC_OFF)
        if src is None:
            return None
        src &= 0x0FFFFFFF
        att = self._owner_of(src)
        if att is not None:
            return None if att == k else att
        if src == 0:
            return None
        own = self._ram_u32(ram, (src | 0x80000000) + HITSRC_OWNER_OFF)
        if own is None:
            return None
        att = self._owner_of(own & 0x0FFFFFFF)
        return None if (att is None or att == k) else att

    @staticmethod
    def _ram_u32(ram, addr):
        """u32 at guest address addr, or None when the address is outside system RAM.
        Oct 1 2026 (Linux review, finding 4): the old code passed an unchecked offset to
        struct.unpack_from; a bad source pointer below RAM_BASE produced a NEGATIVE offset,
        which Python reads from the END of the buffer, so a garbage pointer could blame a
        real player. Bounds-checked here like ps2_ram's _off()."""
        import struct
        off = addr - (A.RAM_BASE + A.RAM_DELTA)
        if off < 0 or off + 4 > len(ram):
            return None
        return struct.unpack_from("<I", ram, off)[0]

    @staticmethod
    def _owner_of(phys):
        for j, pm in enumerate(A.PLAYER_MAT):
            b = (pm - PLAYER_OBJ_LEAD) & 0x0FFFFFFF
            if b <= phys < b + PLAYER_OBJ_LEN:
                return j
        return None

    def _in_special(self, m, pst):
        """Seat m counts as 'in a special' when its state is 25/26 now, or was within the
        last PS2_SPECIAL_WINDOW seconds (payload lands after the state clears)."""
        if m < len(pst) and pst[m] in (25, 26):
            return True
        if self._spec_win <= 0:
            return False
        if self._spec_clock == "frames":
            f0 = self._spec_last_frame.get(m)
            return (f0 is not None and self._spec_now_frame is not None
                    and 0 <= (self._spec_now_frame - f0) <= self._spec_win_frames)
        t0 = self._spec_last.get(m)
        return t0 is not None and (self._spec_t - t0) <= self._spec_win

    # ------------------------------------------------------------------ helpers
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
                 self._my_g_int, self._form_timer, self._last_n)
        try:
            type(self).AGENT_PLAYER = v.player + 1
            self._active_opp = self._view_opponents(v.player)
            self.last_action = v.last_action
            self._last_n = v.n_act
            self._my_g_int = v.g_int
            self._form_timer = v.form_timer
            prev = v.prev if v.prev is not None else s
            obs = self._observe(s, prev)
        finally:
            (type(self).AGENT_PLAYER, self._active_opp, self.last_action,
             self._my_g_int, self._form_timer, self._last_n) = saved
        v.prev = s
        return obs
