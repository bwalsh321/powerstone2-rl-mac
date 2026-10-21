"""hunter_bot.py -- a scripted, maximally aggressive opponent that ONLY hunts our bot (Oct 10 2026, Blake's idea).

Why: in grading the three lv8 COMs target our bot only ~2-5% of the time (obs v4 com_targets_me; an even split would be
~33%), so part of the ~56% lv8mix comes from being ignored. The hunter measures that and can be trained against.

Source: Blake's Windows-era aimbot, cheater_bot.py v4 "BLAKE-FIT" ladder (github.com/bwalsh321/powerstone2-rl), retargeted:
  * the target is ONE seat (our bot, in-game P2 = player index 1); no other fighter is ever chased or attacked on
    purpose (stones and chests are fair game);
  * it plays the bot's own 63-action joint interface (action_space.py: 9 dpad directions x 7 buttons), no analog stick,
    so its edge is aggression and wallhack vision, not better controls. Buttons become taps when the env says so
    (ffa_selfplay_env.py releases the hunter's button part for the last PS2_TAP_RELEASE frames, like the learner).
  * movement uses the measured dpad -> world frame (stage_geom.dpad_dirs_from_camera: the camera yaw is fixed per
    stage in play, dpad 'up' = -camera back vector), so no per-episode stick calibration is needed. It is re-read every
    decision: during the round intro the camera pans, and a frame cached there pointed the hunter ~135 deg off.

Ladder (per decision, top wins):
  TRANSFORMED (form == 1):
    meter >= 60%            -> Power Drive (X) at the target when in range, else run at it   (aimbot meter budget)
    target within FUSION_R  -> Power Fusions at the target, alternating R and L (both specials) while facing it
    otherwise               -> run at the target (jumping when it is above)
  NOT TRANSFORMED:
    1. carrying 2 stones    -> finish the set: nearest reachable stone, else nearest chest (smash it)
    2. target carries >= 1  -> mug it: chase and attack (only loose stones within PASS_R interrupt)
    3. pickups: a stone within PASS_R (any direction; while mugging these are the stones the mug knocks loose), or
       (not mugging) a stone within STONE_R nearer than the target, or a chest within PASS_R on the way to the target.
       A pickup that gets no closer for PICK_STALL decisions is ignored for BAN_N (stones beyond a wall)
    4. hunt: run at the target; in range -> attack (X, every GRAB_EVERY-th close decision B = grab/throw), jump
       attack an airborne target, throw a held item (Y) from THROW_R
  Watchdog (from the aimbot, combat-aware): ten movement decisions without 40 u of progress and no damage taken ->
  jump + sidestep for a few decisions. Never spent while transformed.

decide(state, my_seat, target_seat, ram=None) -> joint action index 0..62. `state` is the env's parsed state dict
(PowerStoneEnvV6._parse_state_once: h, players[k] = pos/face/gems/form/meter/item, stones, stones_y, chests, pstate).
"""
import numpy as np

from action_space import BTNS, DIRS
from stage_geom import DPAD_WORLD_DESERT, dpad_dirs_from_camera

N_BTN = len(BTNS)                           # 7
B_NONE, B_A, B_B, B_X, B_Y, B_L, B_R = range(7)   # none, A jump, B action/grab, X attack, Y throw item, L, R triggers

# ---- tunables (world units; the desert box is about +-1140) -------------------------------------------------------
ATTACK_R = 170.0        # melee swing range (aimbot ATTACK_R 180)
GRAB_R = 110.0          # B (grab / throw) range
GRAB_EVERY = 4          # every 4th in-range decision is a grab attempt instead of a punch
THROW_R = 330.0         # holding an item and target within this -> throw it at the target
DRIVE_R = 600.0         # transformed, meter >= 60%: Power Drive (X) from this range (the drive shots travel)
FUSION_R = 900.0        # transformed, meter < 60%: Power Fusion when the target is within this
CLOSE_R = 300.0         # fusion choice: close -> L first, far -> R first (then alternate)
PASS_R = 260.0          # stones this close are always taken; chests this close AND on the way to the target
STONE_R = 450.0         # not mugging: a stone this close and nearer than the target is taken too
STONE_DY_MAX = 260.0    # stone more than this above/below = another floor, unreachable
CHEST_R = 170.0         # close enough to swing at a chest
AIR_DY = 90.0           # target this much higher than me -> it is airborne / on a ledge: jump
FORM_DECISIONS = 25     # meter-fallback step clock (aimbot)
STUCK_N, STUCK_D = 10, 40.0
PICK_STALL, BAN_N = 15, 300   # a pickup that gets no closer for 15 decisions is ignored for 300


def joint(d, b):
    return int(d) * N_BTN + int(b)


class HunterBot:
    def __init__(self, seat=None, target=1, ram=None):
        self.seat = seat
        self.target = target
        self.ram = ram
        self.reset()

    def reset(self):
        self.form_steps = 0
        self.was_formed = False
        self.pos_hist = []
        self.move_streak = 0
        self.unstick = 0
        self.unstick_dir = 1
        self.last_hp = None
        self.close_n = 0
        self.fusion_flip = False
        self.jump_next_x = False
        self.counts = {}              # ladder-branch counts this episode (telemetry)
        self.t = 0                    # decisions this episode
        self.pick = None              # [key, best distance, decisions without progress] of the current pickup
        self.ban = {}                 # pickup key -> decision index until which it is ignored (unreachable)

    # ------------------------------------------------------------------ geometry
    def _dirs(self, ram):
        ram = ram if ram is not None else self.ram
        return dpad_dirs_from_camera(ram) if ram is not None else DPAD_WORLD_DESERT

    def _dir_to(self, me, tx, tz, ram):
        """dpad direction index (1..8) whose world vector best matches me -> (tx, tz); 0 if already there."""
        v = np.array([tx - me[0], tz - me[2]], np.float64)
        n = float(np.hypot(v[0], v[1]))
        if n < 1.0:
            return 0
        dots = self._dirs(ram) @ (v / n)
        return int(np.argmax(dots)) + 1

    @staticmethod
    def _xz(a, b):
        return float(np.hypot(a[0] - b[0], a[2] - b[2]))

    def _stones(self, s, me):
        ys = s.get("stones_y") or []
        cur = []
        for q, (x, z) in enumerate(s.get("stones") or []):
            if any(abs(x - cx) <= 70.0 and abs(z - cz) <= 70.0 for cx, cz, _ in cur):
                continue                                  # per-colour entity pairs -> one visual stone (env dedupe)
            y = ys[q] if q < len(ys) else me[1]
            cur.append((x, z, y))
        ok = [(x, z) for x, z, y in cur if abs(y - me[1]) <= STONE_DY_MAX]
        return sorted(ok, key=lambda p: (p[0] - me[0]) ** 2 + (p[1] - me[2]) ** 2)

    @staticmethod
    def _chests(s, me):
        ch = [(c[0], c[1]) for c in (s.get("chests") or [])]
        return sorted(ch, key=lambda p: (p[0] - me[0]) ** 2 + (p[1] - me[2]) ** 2)

    def _meter(self, p):
        m = p.get("meter", -1.0)
        if m is not None and m > 5.0:
            return min(1.0, m / 100.0)
        return max(0.0, 1.0 - self.form_steps / FORM_DECISIONS)

    def _go(self, me, tx, tz, ram, btn=B_NONE):
        d = self._dir_to(me, tx, tz, ram)
        if d == 0:
            return joint(0, B_X)                          # on top of it: a swing covers pickup lag / chest
        return joint(d, btn)

    @staticmethod
    def _key(x, z):
        return (int(round(x / 60.0)), int(round(z / 60.0)))

    def _free(self, pts):
        return [p for p in pts if self.ban.get(self._key(p[0], p[1]), -1) < self.t]

    def _pickup(self, me, x, z, ram, swing=False):
        """Go to (or swing at) a stone / chest, banning it for BAN_N decisions after PICK_STALL decisions without
        getting 30 u closer (stones beyond a wall or under scenery would otherwise pin the hunter to a wall)."""
        k, d = self._key(x, z), float(np.hypot(x - me[0], z - me[2]))
        if self.pick is None or self.pick[0] != k:
            self.pick = [k, d, 0]
        elif d < self.pick[1] - 30.0:
            self.pick[1], self.pick[2] = d, 0
        else:
            self.pick[2] += 1
            if self.pick[2] >= (PICK_STALL * 2 if swing else PICK_STALL):
                self.ban[k] = self.t + BAN_N
                self.pick = None
        if swing:
            return joint(self._dir_to(me, x, z, ram), B_X)
        return self._go(me, x, z, ram)

    def _tick(self, key):
        self.counts[key] = self.counts.get(key, 0) + 1

    # ------------------------------------------------------------------ the ladder
    def decide(self, s, my_seat=None, target_seat=None, ram=None):
        a = self._decide(s, self.seat if my_seat is None else my_seat,
                         self.target if target_seat is None else target_seat, ram)
        d, b = divmod(a, N_BTN)
        self.move_streak = self.move_streak + 1 if (d and b in (B_NONE,)) else 0
        return a

    def _decide(self, s, i, t, ram):
        self.t += 1
        P = s["players"]
        me, tg = P[i], P[t]
        mp, tp = me["pos"], tg["pos"]
        h = s["h"]
        formed = me.get("form", 0) == 1
        if formed and not self.was_formed:
            self.form_steps = 0
        self.form_steps = self.form_steps + 1 if formed else 0
        self.was_formed = formed
        self.pos_hist.append((mp[0], mp[2]))
        if len(self.pos_hist) > 12:
            self.pos_hist.pop(0)
        hp = float(h[i])
        if self.last_hp is not None and hp < self.last_hp - 1e-3:   # being hit is not being stuck
            self.move_streak, self.unstick = 0, 0
            self.pos_hist.clear()
        self.last_hp = hp
        pst = s.get("pstate")
        if pst is not None and i < len(pst) and pst[i] != 1:   # only RUNNING without progress is "stuck" (state 1 =
            self.move_streak = 0                                # run; intro, hit-stun, knock-down, grabs are not)
            self.pos_hist.clear()
        dist = self._xz(mp, tp)
        dy = float(tp[1] - mp[1])
        if h[t] <= 1.0:                                   # target down: nothing to hunt (the round is ending)
            self._tick("idle")
            return joint(0, B_NONE)

        # ---- watchdog (never while transformed) -----------------------------------------------------------------
        if not formed:
            if self.unstick > 0:
                self.unstick -= 1
                self._tick("unstick")
                d0 = self._dir_to(mp, tp[0], tp[2], ram) or 1
                side = {1: (3, 4), 2: (4, 3), 3: (2, 1), 4: (1, 2), 5: (6, 7), 6: (8, 5), 7: (5, 8), 8: (7, 6)}[d0]
                return joint(side[0] if self.unstick_dir > 0 else side[1], B_A if self.unstick % 2 == 0 else B_NONE)
            if self.move_streak >= STUCK_N and len(self.pos_hist) == 12:
                x0, z0 = self.pos_hist[0]
                if np.hypot(mp[0] - x0, mp[2] - z0) < STUCK_D:
                    self.unstick, self.move_streak = 5, 0
                    self.unstick_dir = -self.unstick_dir
                    self.pos_hist.clear()
                    self._tick("unstick")
                    return joint(0, B_A)

        # ---- transformed ------------------------------------------------------------------------------------------
        if formed:
            m = self._meter(me)
            d = self._dir_to(mp, tp[0], tp[2], ram)
            if m >= 0.60:                                 # first 40% of the form: Power Drive at the target
                if dist <= DRIVE_R:
                    self._tick("drive")
                    return joint(d, B_X)
                self._tick("form_chase")
                return joint(d, B_A if dy > AIR_DY else B_NONE)
            if dist <= FUSION_R:                          # both Power Fusions, alternating, facing the target
                self.fusion_flip = not self.fusion_flip
                first = B_L if dist <= CLOSE_R else B_R
                other = B_R if first == B_L else B_L
                b = first if self.fusion_flip else other
                self._tick("fusion_L" if b == B_L else "fusion_R")
                return joint(d, b)
            self._tick("form_chase")
            return joint(d, B_A if dy > AIR_DY else B_NONE)

        stones = self._free(self._stones(s, mp))
        chests = self._free(self._chests(s, mp))
        my_g = int(me.get("gems", -1))

        # 1. FINISH THE SET
        if my_g >= 2:
            if stones:
                self._tick("finish_set")
                return self._pickup(mp, stones[0][0], stones[0][1], ram)
            if chests:
                cx, cz = chests[0]
                self._tick("finish_set")
                return self._pickup(mp, cx, cz, ram, swing=np.hypot(cx - mp[0], cz - mp[2]) <= CHEST_R)

        # 2. MUG THE CARRIER (only the target); 3. pickups on the way; 4. hunt
        #    Stones within PASS_R are always taken (while mugging those are the ones the mug knocks loose); when not
        #    mugging also stones within STONE_R that are nearer than the target, and chests within PASS_R that lie
        #    toward the target (stones are the hunter's transform, i.e. its biggest damage source).
        mug = int(tg.get("gems", -1)) >= 1
        tv = np.array([tp[0] - mp[0], tp[2] - mp[2]])
        tn = float(np.hypot(tv[0], tv[1])) or 1.0
        for kind, pts in (("stone", stones), ("chest", [] if mug else chests)):
            for (x, z) in pts[:2]:
                dv = np.array([x - mp[0], z - mp[2]])
                dn = float(np.hypot(dv[0], dv[1]))
                toward = dn < 80.0 or float(dv @ tv) / (dn * tn) > 0.0
                if kind == "stone":
                    ok = dn <= PASS_R or (not mug and dn <= STONE_R and dn < dist)
                else:
                    ok = dn <= PASS_R and dn < dist and toward
                if ok:
                    self._tick(f"pass_{kind}")
                    return self._pickup(mp, x, z, ram, swing=(kind == "chest" and dn <= CHEST_R))
        self._tick("mug" if mug else "hunt")
        d = self._dir_to(mp, tp[0], tp[2], ram)
        if me.get("item", 0) and dist <= THROW_R:
            return joint(d, B_Y)
        if self.jump_next_x:                              # second half of a jump attack
            self.jump_next_x = False
            return joint(d, B_X)
        if dist <= ATTACK_R:
            if dy > AIR_DY:                               # airborne / ledge target: jump, then swing
                self.jump_next_x = True
                return joint(d, B_A)
            self.close_n += 1
            if dist <= GRAB_R and self.close_n % GRAB_EVERY == 0:
                return joint(d, B_B)
            return joint(d, B_X)
        if dy > 2 * AIR_DY and dist <= 2 * ATTACK_R:      # it is above me: jump toward it
            return joint(d, B_A)
        return joint(d, B_NONE)
