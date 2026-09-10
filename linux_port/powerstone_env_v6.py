"""
Power Stone 2 RL environment, v4 — RUN-3 OBS (multi-opponent edition).

Everything the Aug 3 2026 RE mega-take pinned, wired into one observation:

- SELF: health, ABSOLUTE x,z + real height y, velocity, FACING unit vector
  (render-matrix rotation row 0), internal gem count, form-timer heuristic.
- OPPONENTS x3, sorted NEAREST-FIRST (permutation invariance: slot 0 is
  always the most immediate threat), each with an alive flag, egocentric
  dx,dz,dy, distance, velocity, health, and a threat-dot (their facing
  aimed at me = 1). Absent/dead opponents zero out.
- STONES: all 4 pool pairs as (present, dx, dz) — upgrade from nearest-only.
- STAGE: savestate-slot one-hot (abs position only means something once the
  net knows which arena it's in). No memory address needed — the env knows
  which slot it loaded.
- Last-action one-hot + 8 reserved spares (the reserved-slot trick saved
  run 2 from orphaning; always leave room for the next idea).

Bridge: requires the v4 state line (36 fields) for full data — the lua
emits it when the current savestate slot has calibrated player-matrix
bases (`playerbase` / ps2_players.txt, found via `matscan`). Falls back
to parsing the v3 line (22 fields): 2 players, no facing (zeros).

Rewards are v3's (already multi-opponent for damage and win-when-all-dead)
plus: approach shaping targets the NEAREST ALIVE opponent, and gem-v2
pickup attribution tests the bot against the nearest opponent instead of a
fixed one. Only opponents ACTIVE AT RESET (pinned matrix + healthy
baseline) count for rewards/win — stale h3/h4 bytes on 1v1 slots can't
create phantom unkillable opponents.
"""

import os
import random
import time

import gym
import numpy as np
from gym import spaces

try:
    import pydirectinput
    pydirectinput.PAUSE = 0
except ImportError:
    pydirectinput = None

BRIDGE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bridge")
STATE_FILE = os.path.join(BRIDGE_DIR, "ps2_state.txt")
CMD_FILE = os.path.join(BRIDGE_DIR, "ps2_cmd.txt")

DC_B, DC_A = 0x2, 0x4
DC_UP, DC_DOWN, DC_LEFT, DC_RIGHT = 0x10, 0x20, 0x40, 0x80
DC_Y, DC_X = 0x200, 0x400

POS_SCALE = 1000.0
VEL_SCALE = 50.0
HEIGHT_SCALE = 500.0      # real height observed -175..+495 in the RE take


class PowerStoneEnvV6(gym.Env):
    AGENT_PLAYER = 2          # bot is the port-2 human side (verify per slot!)
    LOAD_STATE_KEY = "f7"
    TURBO_KEY = "f9"

    # Only CALIBRATED slots belong here (playerbase pinned + stonescan'd).
    # Start with whatever RUN3_CALIBRATION.md has checked off.
    STATE_SLOTS = [0, 1, 2, 3, 4, 5, 6]   # Aug 12: CURRICULUM LADDER LIVE.
    # 0/1/2 = lv2 (slot 0 desert-A UNBENCHED: it was parked for projectile
    # blindness, cured since the v6 obs bus -- if kiting degeneracy
    # returns, drop 0 from this list), 3/4 = lv3, 5/6 = lv4. Uniform mix
    # ~43/29/29%% across difficulty; tilt harder as new-tier win%% climbs.
    # CURRICULUM LADDER (Aug 12, Blake's spec): slots 3/4 = the same two
    # stages at COM level 3; slots 5/6 = level 4. After Blake saves the new
    # states and calibration checks pass, set STATE_SLOTS = [1,2,3,4,5,6].
    # SLOT_META: slot -> (stage one-hot dim offset, COM level). Stage dims
    # are BY STAGE, not raw slot (slots 5/6 would have written INTO the
    # last-action block [97..106] -- obs corruption). Slots 1/2 keep the
    # exact dims every trained model already knows (94 elevator, 95
    # desert); new slots share them. Difficulty rides reserved dim 118
    # (always 0 for old models -> backward compatible).
    # Aug 15 AUDIT (Blake's sheet, checked against the actual saves):
    # the in-game COM levels NEVER matched the Aug-12 spec for several
    # slots -- true lineup: 1=lv2, 2=lv3, 3=lv3, 4=lv4, 5/6=lv5(!), and
    # slot 0 re-saved today: MEL'S SHOP stage @ lv4 (was desert lv2; briefly lv5, re-saved lv4 on rec).
    # Consequence: all historical "by level" groupings understated the
    # bot (old "lv4 8%" rows were LEVEL 5). Per-slot stats were always
    # correct. Mel's shop gets stage dim 3 (previously unused; dim 0 =
    # retired desert-A remains meaningful to old checkpoints only).
    # Aug 29 (Mac): slot 3 REDEFINED -- desert TRUE-FFA @ COM lv8 (the
    # BIL leg: hard battles only). Rig-era slot3 (elevator lv3) never
    # migrated; its old CSV rows keep their per-slot correctness. Slot
    # number kept < 4 ON PURPOSE: the obs gate below only writes stage
    # one-hot + DIFF_DIM for slots 0-3, and lv8 must be VISIBLE
    # (DIFF_DIM = 8/8 = 1.0).
    SLOT_META = {0: (3, 4), 1: (1, 2), 2: (2, 3),
                 3: (2, 8), 4: (2, 4), 5: (1, 5), 6: (1, 5),
                 # Leg I (Aug 19): 7/8 = Falcon-ditto SELF-PLAY states
                 # (opponent is a policy, not a COM -- level 4 declared on
                 # DIFF_DIM as a neutral mid value); 9 = 1v1 vs lv7 Pride,
                 # the external benchmark. Slot 9 stage dim PROVISIONAL
                 # (2 = desert) until Blake confirms which stage he saved.
                 7: (3, 4), 8: (2, 4), 9: (2, 7)}
    DIFF_DIM = 118
    # ^ slot 0 = the evasive/ranged comp on open desert. Kited from ep 0 of run-4:
    #   appr negative in EVERY 40-ep block across 560 eps, 8-22% wins, never fixed by
    #   the lv3->lv2 drop. Root cause = projectile blindness (not in obs yet) + a
    #   comp that can't be cornered -> the only representable policy is "keep distance",
    #   and that kiting bled into the shared MLP weights (same reason tomb/sub/sky were
    #   benched). RE-ADD when projectile vision lands in obs. Savestate slot 0 +
    #   playerbase/stone/gembase calibration stay banked (zero rework to restore).
    #   Old value: [0, 1, 2].

    N_OPP = 3                 # opponent slots in obs (4P max)

    ACTION_FRAMES = 6
    STEP_TIMEOUT = 5.0

    # Aug 17 opponent-detection race fix (Sec 34). Every savestate in the
    # current roster is 4P VS with three COMs, so three is the expected
    # complement. reset() polls up to OPP_SETTLE_S for all three to
    # initialise before freezing _active_opp for the episode.
    EXPECT_OPP = 3
    # Aug 19 (Leg I): per-slot expected complement. The 1v1 savestates
    # (7/8 self-play dittos, 9 Pride) have ONE opponent — without this,
    # every reset burned the FULL OPP_SETTLE_S budget waiting for two
    # opponents that don't exist, stalling the whole SubprocVecEnv
    # barrier ~2s per reset (the "9 games freeze while 1 resets" effect).
    EXPECT_OPP_BY_SLOT = {7: 1, 8: 1, 9: 1}
    OPP_SETTLE_S = 1.0    # Aug 19: was 2.0 — reset stalls pollute other envs' transitions; 1s still >> the Sec-34 race window

    # =====================================================================
    # LEG 1 REWARD PACKAGE — Aug 10 (Blake's call: "when stones hit the
    # ground, it should be one of the first things the bot grabs... its
    # literally how you win this game"). ONE reward domain changed — the gem
    # economy — everything else frozen, so the leg reads against the Leg 0
    # baseline: picks 2.0/ep, transforms in 9.0% of eps, chest participation
    # ~2 of ~47 opens/ep, win 19.9% (halves 14.9->24.8, z=+2.15).
    # Blake's eyewitness falsified the "chasing lost races" theory: the bot
    # KNOCKS gems loose and then ignores free pickups until they despawn
    # (4 on the ground while it tossed boxes). Diagnosis: dense rewards
    # (damage tick + KNOCK_W drip) outcompete the sparse pick (+2 once).
    # Leg 1 reprices so the collect half of the loop dominates the knock
    # half, movement toward gems outbids movement toward enemies, and
    # opening chests — the gem SOURCE, ~47/ep — pays for the first time.
    # =====================================================================
    # ---- LEG H: REWARD ORDERING  WIN >> DAMAGE > STONES (Aug 18) --------
    # Blake: "Stone grabbing does not translate into winning more matches for
    # the bot. It hasn't graduated a level in like 3-4 full legs."
    # MEASURED over Leg G (n=6,245), which is what these numbers are sized on:
    #     gems   mean 16.13  median 18.00   48.2% of episodes AT THE CAP
    #     damage mean  5.51  (raw 2.76 x old weight 2.0)
    #     win    20.00
    # Stones paid 2.9x what damage paid, and for HALF of all episodes the gem
    # channel was saturated — extra stones paid literally zero, so the term
    # had stopped shaping anything and become a large constant offset.
    # STRUCTURAL POINT: raw damage is BOUNDED near 3.0 (median 3.00, p90
    # 3.15) because three opponents x one health bar IS the whole field. So
    # the damage channel saturates exactly when you have won. Paying for
    # damage is paying for progress toward the win condition; paying for
    # stones is not — which is the whole "gets all the stones and still
    # loses" complaint, in numbers.
    # NEW ORDERING (per-episode, at typical play):
    #     WIN 20.00  >>  DAMAGE ~11.0  >  STONES 6.00 (capped)
    DAMAGE_DEALT_W = 2.0  # LEG I: reverted from Leg H's 4.0 (null result). was 2.0. Raw damage tops out ~3.15, so this makes
                          # a full sweep of the field worth ~12.6 — the
                          # largest dense signal, and it is aligned with
                          # winning by construction.
                          # "it's hiding, not fighting"): a full enemy
                          # lifebar now pays 2.0, a 3-opp room sweep 6.0.
                          # ASYMMETRIC on purpose — TAKEN stays 1.0 so we
                          # buy aggression without re-buying fear (we just
                          # spent a leg de-poisoning timidity).
    DAMAGE_TAKEN_W = 1.0
    WIN_BONUS = 20.0     # Leg 1: was 15. Raised ONLY to stay above the new
                         # gem ceiling (a full cycle is now 3x4+6=18; the
                         # cap is 19) — "a win is the single best thing"
                         # ordering is preserved, not weakened.
    LOSS_PENALTY = 10.0  # Aug 5 night: asymmetric — win stays king, but
                         # dying stops being worth elaborately delaying
                         # (symmetric 15/15 bred the corner coward)
    # Aug 14 (armed for the leg AFTER Leg A — Blake's call): scale the
    # terminal loss by COM level. Diagnosis in HANDOFF Sec 25.4: lv4 is
    # ~27% of the curriculum stream at ~96% losses; a flat -10 x gamma
    # .999 stamps every full-episode behavior there — including perfect
    # stone-hunting — as bad, and the pessimism bleeds through the
    # shared net into lv2/lv3 ("loss-poison"). Losing to an opponent
    # above your pay grade shouldn't erase good habits; losing to one
    # you SHOULD beat still hurts full price. WIN_BONUS untouched (a
    # win is the single best thing everywhere). Revisit the lv4 scale
    # upward once lv4 win rate approaches the teacher's ~20%.
    # Aug 29 (lv8 leg): 8 -> 0.2 (effective terminal loss -2). The
    # corner-coward math: gamma .999 discounts a certain end-of-episode
    # loss ~70% over 1200 steps, so at -10 stalling 'saves' ~7 vs the
    # -2.4 TIME_PENALTY bleed -- cowering PAYS. Below ~-3.4 it doesn't;
    # -2 keeps dying worse than any survivable mistake without making
    # near-certain lv8 deaths poison every good habit (Sec 25.4 logic).
    LOSS_SCALE_BY_LEVEL = {2: 1.0, 3: 0.7, 4: 0.4, 8: 0.2}
    TIME_PENALTY = 0.002  # anti-stall: corner-camping a 1200-step episode now bleeds -2.4
    APPROACH_W = 1.0
    STONE_APPROACH_W = 1.0   # Aug 15 Leg C: 1.25 -> 1.0, PARITY with
                             # opponent approach — walking at stones and
                             # walking at enemies now pay the same rate.
                             # (Leg 1 history: was 0.5 — HALF the opponent
                             # approach rate, i.e. the weights literally
                             # prioritized walking at enemies over walking at
                             # gems (set when stone reports were furniture and
                             # never revisited). Now a visible loose gem
                             # outbids an enemy as a movement target. Still
                             # potential-based (pays for progress only) so the
                             # kangaroo exploit stays impossible; loose gems
                             # DESPAWN on a timer (Blake, eyewitness), so
                             # urgency is a real game mechanic, not taste.
    URGENCY_MULT = 2.0  # Aug 6: 2-stone urgency (Blake's call) — stone-
                        # approach shaping doubles while we hold exactly 2
                        # (3rd = transform). Telemetry n=802: eps stalling
                        # at 2 picks win 31%, eps reaching 3+ win 48%.
                        # Potential-based: pays for closing distance only,
                        # so the 2-stone STATE isn't penalized and the 2nd
                        # pickup stays attractive. Watch appr/picks for
                        # kangaroo relapse after resume.
    FORM_STEPS = 150          # heuristic until per-slot logic-object anchors
    GEM_W = 3.0           # LEG I: reverted from Leg H's 1.5. was 3.0 (Leg H). Stones stay POSITIVE — Blake:
                          # "still give rewards for stones as they will allow
                          # easier wins" — just clearly subordinate to damage.
                          # 3x3+6=15 (< WIN 20). Stones stay the best
                          # per-event income; they just stop paying 4x a
                          # lifebar. Rehearsal guards the hunt habit now —
                          # this is the first stone-price cut made WITH a
                          # structural defense in place.
                          # (Leg 1 history: was 2. A grab paid ~7 knocks
                          # (KNOCK_W 0.6): knock-and-walk-away stops being a
                          # stable strategy; the full loop the bot already
                          # performs (knock +0.6, then COLLECT +4) is where
                          # the money is. KNOCK_W itself unchanged — knocking
                          # is good, it creates the supply.
    OPP_GEM_W = 0.15  # Aug 8 pm (0.75 -> 0.15, Blake-approved): when the
                      # anchors woke this term, 3 COMs x ~14 picks/ep made
                      # it -10/ep of weather the bot can't prevent — reward
                      # noise that collapsed opponent-approach and dragged
                      # wins 38%->30% in the first sighted leg. Enemy picks
                      # are now a whisper; OPP_TRANSFORM_PEN carries the
                      # real (visible) threat signal.
    KNOCK_W = 0.6
    LOST_W = 0.75
    TRANSFORM_BONUS = 3.0 # Aug 16 LEG D (was 6.0) — see FORM_DMG_MULT below.
                          # The bonus was paying to ENTER the form; the freed
                          # 3.0 moves to damage dealt INSIDE it.
    # Aug 16 LEG D — "pay for the kill, not the costume" (HANDOFF Sec 31).
    # Measured: wins with 1 transform end in 470 steps (dmg/form 4.39); wins
    # with 3+ transforms take 701 steps (dmg/form 1.96). The bot enters forms
    # it cannot convert, exactly matching Blake's eye-test ("blast rockets
    # from too far, miss, go get stones again"). Cause: TRANSFORM_BONUS paid
    # on the transform EVENT, while damage inside the form was worth the same
    # as any other damage.
    # CRITICAL DESIGN POINT: this premium lands in the DAMAGE channel, which
    # is UNCAPPED — NOT in `gem`, which is clamped by GEM_EP_CAP (19.0) and
    # already ~93% consumed on wins (mean gem 17.65/19). Routing it through
    # `gem` would have made it a no-op. Moving budget from a saturated capped
    # channel to an unsaturated uncapped one IS the intervention.
    FORM_DMG_MULT = 2.5   # damage dealt while transformed is worth 2.5x
                          # (DAMAGE_DEALT_W 2.0 -> effective 5.0 in form)
    OPP_TRANSFORM_PEN = 3.0
    DANGER_W = 0.005
    STONE_MATCH_TOL = 40.0
    STONE_MIN_AGE = 3
    PICKUP_R = 130.0
    KNOCK_R = 200.0
    # Aug 3 evening fix — slot-0 phantom gem storm (18 picks / 5 "forms"
    # per ep, gem_rew +25 avg while losing every game):
    GEM_EP_CAP = 19.0        # LEG I: reverted from Leg H's 6.0. was 19.0 (Leg H) — the single highest-leverage
                             # knob, because saturation is what killed the
                             # gradient. At GEM_W 1.5 this is 4 picks; one
                             # full transform cycle (3 picks = 4.5) still pays
                             # IN FULL, so collecting to transform is intact
                             # while hoarding beyond that earns nothing.
                             # Invariants still hold: WIN 20 > cap 6,
                             # LOSS 10 > floor 6, 3*GEM_W + TRANSFORM_BONUS
                             # = 4.5 <= 6.
                             # EXACTLY filled (3x2+6=12), so the bot's best
                             # gem episodes earned literally nothing further
                             # (Blake's clutch win printed gem_rew=+12.00, the
                             # clamp, on the wire). New cycle = 3x4+6 = 18;
                             # cap 19 gives it headroom + a knock or chest,
                             # and stays strictly < WIN_BONUS (20).
    GEM_EP_CAP_NEG = 6.0     # Aug 8 pm: negative floor SPLIT from the
                             # ceiling — at 12 a bad-gem episode outweighed
                             # the LOSS_PENALTY (10), so gem noise punished
                             # harder than dying. 6 < 10 keeps the ordering:
                             # nothing outweighs dying. UNCHANGED in Leg 1.
    CHEST_OPEN_W = 1.5       # Leg 1, NEW: attributed chest-open bonus. The
                             # gem SOURCE — ~47 opens/ep, bot at ~2 (Leg 0
                             # measured). Attribution mirrors pickup credit
                             # (strictly closest + inside radius), NOT the
                             # loose telemetry heuristic. Rides inside the
                             # gem component -> bounded by GEM_EP_CAP.
    CHEST_OPEN_R = 130.0     # radius for chest-open credit (= PICKUP_R)
    CHEST_NEAR_R = 150.0     # Aug 10: telemetry-only radius for "that chest
                             # open was probably ours" attribution
    PICKUP_MARGIN = 0.8      # credit requires STRICTLY closest by 20%
    PICKUP_R_ME = 90.0       # tighter radius for OUR pickup credit
    STONE_DEDUPE_TOL = 70.0  # per-color entity pairs -> one visual stone
                             # (45 -> 70 Aug 8: live scan showed one
                             # stone's cluster spread 59u per-axis, so 45
                             # split it into "two stones" in obs)

    # ---- STARVATION LEG (Aug 11, HANDOFF Sec 20) ---------------------------
    # The probe (probe_stone_sensitivity.py) proved the net SEES stones
    # (stone/opp response ratio 10.3) — the picks ceiling is prioritization:
    # the dense damage/knock faucet outbids fetching, and PPO never SAMPLES
    # the full disengage-and-fetch chain, so no gem price can reinforce it.
    # This leg shuts the faucet off instead of raising prices again:
    # gems, chests, transforms and WINNING become the only income; the sole
    # dense positive left is stone-approach shaping. Death still costs
    # LOSS_PENALTY (terminal), TIME_PENALTY stays as the anti-stall guard —
    # both dense DAMAGE terms go to zero together (taken-only would breed
    # another run3b coward).
    # PRE-REGISTERED (vs Leg 1b: picks 2.17, forms-eps 13%, win 28.8%):
    # resume of the Leg 1b model; if picks/forms are not CLEARLY up within
    # ~200k steps, the faucet was not the blocker and the imitation case is
    # airtight. Watch for the coward signature (ep_len inflation + timeouts).
    # Flip STARVE = False to restore Leg 1 prices exactly.
    STARVE = False   # starvation experiments CONCLUDED Aug 11 (both cells negative)
    if STARVE:
        DAMAGE_DEALT_W = 0.0     # was 1.0 — the faucet
        DAMAGE_TAKEN_W = 0.0     # was 1.0 — zeroed WITH dealt (coward guard)
        APPROACH_W = 0.0         # was 1.0 — no more pay for chasing enemies
        KNOCK_W = 0.0            # was 0.6 — knock-and-walk-away income, and
                                 # the +0.45/cycle knock/re-grab recycle loop
    # ---- LEG F: MINIMAL REWARD ABLATION (Aug 17, HANDOFF Sec 35) ----------
    # BLAKE'S HYPOTHESIS: we have too many rewards. 15 terms + 5 modifiers on
    # a game whose win condition is simply "be the last one standing", vs ~4
    # for the Pokemon Red agent on a far more complex game.
    #
    # THE PROJECT'S OWN TRACK RECORD IS THE EVIDENCE:
    #   Leg 1 gem reprice (5 weights)  -> "repricing did not move the economy"
    #   Leg 1b fresh, same rewards     -> plateaued
    #   Starve leg (see above)         -> negative, BOTH cells
    #   Leg D form premium             -> NULL RESULT
    #   BC on 9,943 human pairs        -> "THE CEILING IS BROKEN"
    #   hold-until-next interface fix  -> 2.2x win, 3.6x picks
    # Reward tuning ~0-for-5. Priors/interface 2-for-2, both transformative.
    #
    # THE MECHANISM (Sec 22, recorded at the time and then forgotten): the BC
    # leg PEAKED then ERODED, diagnosed as "the reward landscape still prefers
    # the old behavior, and once the value fn matured PPO began optimizing
    # back toward it, washing out the demo prior." **Our shaping actively
    # fought the human prior and won.** Dense shaping exists to solve
    # exploration; 252k demo pairs rehearsed 16x256/rollout solve it better
    # and more honestly. Keeping both is redundant at best, adversarial at
    # worst.
    #
    # BLAKE'S SHARPENING (Aug 17): "the win condition is be the last one
    # standing. stones just...make it easier. the fact that my bot can get
    # all the stones and still lose is a skill issue." Correct — and note
    # GEM_EP_CAP (19.0) is 95% of WIN_BONUS (20.0): we pay almost as much
    # for the PROXY as for the GOAL. Classic Goodhart.
    #
    # WHAT THIS MODE DOES: removes terms ONLY. It deliberately does NOT
    # retune any survivor — no new hand-picked numbers, because inventing
    # numbers is precisely the activity with the 0-for-5 record. The
    # proxy-vs-goal weighting (GEM_EP_CAP vs WIN_BONUS) is a SEPARATE
    # hypothesis and gets its OWN leg if this one survives.
    # Side effect worth noting: zeroing TRANSFORM_BONUS also lowers how fast
    # the gem channel saturates its cap, partially easing the Goodhart
    # pressure for free.
    #
    # SURVIVORS (5 + anti-stall): WIN_BONUS, LOSS_PENALTY, DAMAGE_DEALT_W,
    # DAMAGE_TAKEN_W, GEM_W, and TIME_PENALTY as the anti-stall guard.
    # BC rehearsal stays at FULL strength — it is the replacement shaping.
    #
    # PRE-REGISTERED (vs Leg E final quarter: lv4 ~49.9%, slot0 ~50.1%,
    # picks 6.98, forms 1.66, win 51.2%), resume of the Leg E model:
    #   HOLDS or IMPROVES -> the shaping was redundant/harmful. Simplify
    #     permanently, and the "reward tuning does not work here" doctrine
    #     is confirmed rather than suspected.
    #   DEGRADES MATERIALLY (picks < ~5 or lv4 < ~44%) -> shaping IS
    #     load-bearing. Revert, and we finally know instead of guessing.
    #   EITHER WAY it is one 7-hour leg for an answer we have been circling
    #     for two weeks.
    # Flip MINIMAL_REWARD = False to restore Leg E prices exactly.
    MINIMAL_REWARD = True
    if MINIMAL_REWARD:
        APPROACH_W = 0.0          # was 1.0  — pay for closing on enemies
        STONE_APPROACH_W = 0.0    # was 1.0  — pay for closing on stones
        URGENCY_MULT = 1.0        # was 2.0  — 2-gem stone-approach multiplier
        KNOCK_W = 0.0             # was 0.6  — knock a stone loose
        LOST_W = 0.0              # was 0.75 — lost a stone
        OPP_GEM_W = 0.0           # was 0.15 — opponent picked a stone
        OPP_TRANSFORM_PEN = 0.0   # was 3.0  — opponent transformed
        TRANSFORM_BONUS = 0.0     # was 3.0  — WE transformed (instrumental)
        FORM_DMG_MULT = 1.0       # was 2.5  — Leg D premium, null result
        DANGER_W = 0.0            # was 0.005
        CHEST_OPEN_W = 0.0        # was 1.5
        # KEPT: WIN_BONUS 20.0, LOSS_PENALTY 10.0, DAMAGE_DEALT_W 2.0,
        #       DAMAGE_TAKEN_W 1.0, GEM_W 3.0, TIME_PENALTY 0.002.
        # NOT RETUNED ON PURPOSE — see note above.

    MAX_STEPS = 6000

    # ACTION LABELS CORRECTED Aug 8 2026 (GameFAQs CChan movelist — Blake
    # spotted that "block" doesn't exist): real PS2 mapping is A=jump,
    # B=action/grab, X=attack (+push/use item), Y=drop/throw held item.
    # There is NO block/guard in this game. ORDER AND MASKS UNCHANGED —
    # indices are the policy head; only the cosmetic names changed.
    # NOTE (v5-ERA, SUPERSEDED by the v6 10-action table below — pf1_L/pf2_R
    # ARE in the action space now): transformed specials — Power Fusion 1/2 — are the
    # L/R TRIGGERS, which are ANALOG AXES on Dreamcast, not mask bits. They
    # are NOT in this action space -> the bot is physically unable to use
    # its transformed specials. Flycast lua CAN inject them
    # (flycast.input.setAxis(player, axis, value); axes 4/5 = L/R), so the
    # bridge side is easy — but adding actions resizes the policy output
    # layer = orphans the model. Do it at the next fresh model, or via
    # policy-head surgery (graft 2 new logits, init near-zero).
    # v6: 8 -> 10. Entries are (name, kind, value); kind is "btn" (digital
    # mask, the original 8, ORDER AND MASKS UNCHANGED so the labels still map
    # to the same physical inputs) or "axis" (analog trigger, new).
    # The first 8 indices are byte-identical in meaning to v4 -- that is
    # deliberate, so telemetry and any hand-analysis of old runs still reads
    # true. The 2 new logits go on the END.
    AXIS_L, AXIS_R = 5, 6   # Aug 12 FIX: flycast axes are 1/2=stick X/Y,
                        # 3/4=right stick (absent on DC), 5=LT, 6=RT.
                        # The old 4/5 aimed at right-stick-Y and LT —
                        # no bot ever actually fired a Power Fusion.
    AXIS_VALUE = 65535        # Aug 12 FIX: flycast axis scale is 0..65535
                          # (verified: Blake's recorded pulls read 65535).
                          # The old 1.0 was a 0.002% squeeze — a no-op.
    ACTIONS = [
        ("up", "btn", DC_UP), ("down", "btn", DC_DOWN),
        ("left", "btn", DC_LEFT), ("right", "btn", DC_RIGHT),
        ("jump", "btn", DC_A), ("grab", "btn", DC_B),
        ("attack", "btn", DC_X), ("throw", "btn", DC_Y),
        # Power Fusion 1/2 while transformed; L=attack / R=throw untransformed,
        # so these are never dead actions even outside a form.
        ("pf1_L", "axis", AXIS_L), ("pf2_R", "axis", AXIS_R),
    ]

    # --- obs layout v6 ----------------------------------------------------
    # FRESH BUS. No reserved-slot trick this time: the model is fresh by
    # decision (handoff Sec 10), so the layout is grouped for legibility rather
    # than budgeted around a graft. Everything is nearest-first where ordering
    # exists, and opponent sub-blocks stay contiguous so "opp k's gems" ride
    # with opp k's dx/dz/hp.
    #
    # self       [0]h [1]absx [2]absz [3]height [4]vdx [5]vdz [6]fx [7]fz
    #            [8]gems/3 [9]form_flag [10]form_meter/100 [11]has_item
    #            [12..17] item category one-hot                      (18)
    # opp k=0..2 base=18+13k:
    #            [+0]alive [+1]dx [+2]dz [+3]dy [+4]dist [+5]vdx [+6]vdz
    #            [+7]h [+8]threat_dot [+9]gems/3 [+10]form_flag
    #            [+11]form_meter/100 [+12]has_item                   (39)
    # stones k=0..5 base=57+4k: [+0]present [+1]dx [+2]dz [+3]dy     (24)
    #            6 slots, not 4: the new savestates carry 5-6 resting stones
    #            per stage, so 4 could not represent the board. dy is the
    #            elevator fix -- a stone one floor up is not reachable.
    # proj k=0..1 base=81+6k:
    #            [+0]present [+1]dx [+2]dz [+3]dy [+4]vx [+5]vz      (12)
    #            velocity IS the dodge signal; do not drop it.
    # stage one-hot: [93..96]                                        (4)
    # last action:   [97..106]  (10 actions now)                     (10)
    # chest [107..110]: [+0]present [+1]dx [+2]dz [+3]dy             (4)
    #            NEAREST unopened chest, from the v7 line's object-ledger
    #            report (Aug 10, HANDOFF Sec 15). Chests are the gem SOURCE
    #            on these stages, so this is perception the gem economy runs
    #            on. The dims were reserved for exactly this. NO reward term
    #            reads chests in Leg 0 — vision only.
    # reserved:      [111..121] always 0                             (11)
    #            2 stage phase, 5 sky hazard, 4 spare. Reserved on purpose:
    #            known-wanted and un-pinned; paying the dims now is far
    #            cheaper than a bus change (which orphans the model).
    OBS_DIM = 122
    _OPP0, _STN0, _PRJ0, _STG0, _ACT0 = 18, 57, 81, 93, 97
    _CHT0, _RSV0 = 107, 111
    N_STONE_OBS = 6
    N_PROJ_OBS = 2
    PROJ_VEL_SCALE = 1200.0   # ~rocket speed, so a rocket reads ~1.0

    # ---- item identity -------------------------------------------------
    # MEASURED Aug 9 (293k-step leg, 19 distinct pointers sampled live): every
    # item definition pointer at F+0x54 lands EXACTLY on a 0x430 grid, with a
    # constant residue of 0x1E4. F+0x54 indexes a fixed-stride definition
    # TABLE, so item identity is arithmetic and needs no hand-built dictionary:
    #
    #     bucket = (ptr // 0x430) % 256
    #
    # The whole observed table spans ~108 KB and a bucket collision would need
    # two items 256*0x430 = 274,432 bytes apart, so collisions are impossible
    # here. Measured buckets: molotov 236, gatling 24, sword 26.
    #
    # WHY THIS REPLACED THE CATEGORY ONE-HOT: with only 3 named items, all 19
    # items in play mapped to category 0 -- so five of the six category dims
    # were dead and the sixth was an exact duplicate of has_item. Six wasted
    # inputs.
    #
    # WHY A RANDOM EMBEDDING AND NOT AN INDEX SCALAR: item 24 is not "less
    # than" item 26 in any way an MLP should exploit -- a raw index invites the
    # net to learn a fake ordering. A fixed pseudo-random unit vector per
    # bucket (the hashing trick) gives every item a distinct, near-orthogonal
    # signature in 6 dims with no ordinal structure to misread. The seed is
    # fixed so codes are identical across runs and resumes -- changing the seed
    # would silently invalidate a trained model.
    ITEM_STRIDE = 0x430
    ITEM_RESIDUE = 0x1E4     # every valid pointer satisfies ptr % STRIDE == this
    ITEM_EMB_DIM = 6
    ITEM_EMB_SEED = 20260809
    # Kept for when the dictionary gets built by hand -- names are still more
    # useful than codes for READING telemetry, they are just not needed for
    # the net to tell items apart.
    ITEM_NAMES = {
        0x0C519664: "gatling",   # bucket 24
        0x0C519EC4: "sword",     # bucket 26
        0x0C50DE24: "molotov",   # bucket 236
    }

    # Per-channel kill switches. Blake is validating these against the screen
    # in parallel with this build; if one turns out to be misread, zero the
    # channel here instead of resizing the bus (which would orphan the model
    # all over again). All default ON.
    CH_METER = True
    CH_ITEM = True
    CH_PROJ = True
    CH_STONE_Y = True
    CH_CHEST = True   # Aug 10: nearest-chest obs off the v7 line (Sec 15).
                      # Eyeball-validated by Blake before it shipped; if the
                      # chest report ever misbehaves live, flip this off —
                      # obs [107..110] read zero and nothing else changes.

    @classmethod
    def _item_emb_table(cls):
        """Fixed pseudo-random unit vectors, one per item bucket. Built once."""
        t = getattr(cls, "_ITEM_EMB", None)
        if t is None:
            rng = np.random.RandomState(cls.ITEM_EMB_SEED)
            t = rng.normal(size=(256, cls.ITEM_EMB_DIM)).astype(np.float32)
            t /= np.linalg.norm(t, axis=1, keepdims=True)
            cls._ITEM_EMB = t
        return t

    @classmethod
    def item_bucket(cls, ptr):
        """Item identity from the F+0x54 definition pointer, or None.

        Returns None for 'holding nothing' AND for an off-grid pointer. The
        grid test is nearly free and it is a real read-validity check: a
        pointer that is not on the 0x430 grid is a bad read, not a new item,
        so it must not be handed to the net as if it were an identity.
        """
        if not ptr:
            return None
        if ptr % cls.ITEM_STRIDE != cls.ITEM_RESIDUE:
            return None
        return (ptr // cls.ITEM_STRIDE) % 256

    def __init__(self, bridge_dir=None, turbo=True, state_slots=None):
        """Aug 10 parallel-run support (behavior-identical by default):

        bridge_dir  — per-instance bridge folder. Each parallel Flycast is
                      launched with PS2_BRIDGE_DIR pointing at its own copy
                      (the lua reads the same env var); the env instance for
                      it gets the same path here. None = the classic shared
                      ./bridge, exactly as before.
        turbo       — hold F9 and allow the F7 keyboard fallback in reset().
                      MUST be False for parallel instances: pydirectinput is
                      GLOBAL keyboard input and lands on whichever window has
                      focus — with N windows that is at best one instance and
                      at worst the WRONG one loading a savestate. Parallel
                      speed comes from emu.cfg (vsync off etc.), not F9.
        state_slots — per-instance override of STATE_SLOTS, so different
                      instances can train different stages/rosters at once
                      (and, later, the BIL anti-forgetting mix rides here).
        """
        super(PowerStoneEnvV6, self).__init__()
        self._bridge_dir = bridge_dir or BRIDGE_DIR
        self._state_file = os.path.join(self._bridge_dir, "ps2_state.txt")
        self._cmd_file = os.path.join(self._bridge_dir, "ps2_cmd.txt")
        self._turbo = bool(turbo)
        if state_slots:
            self.STATE_SLOTS = list(state_slots)
        os.makedirs(self._bridge_dir, exist_ok=True)
        self.action_space = spaces.Discrete(len(self.ACTIONS))
        self.observation_space = spaces.Box(
            low=-5.0, high=5.0, shape=(self.OBS_DIM,), dtype=np.float32)

        self.steps = 0
        self.prev = None
        self.prev_health = None
        self.last_action = 0
        self._form_timer = 0
        self._ep = self._fresh_ep()
        self._stone_tracks = []
        self._my_g_int = 0
        self._opp_g_int = 0
        self._hurt_cd = 0
        self._dealt_cd = 0
        self._seq = 0
        self._active_opp = [0]        # player indices that count this episode
        self._warned_v3 = False
        self._send(f"player {self.AGENT_PLAYER}")
        # Aug 19: a flycast instance can be mid-stall (transient, self-
        # recovering — observed repeatedly) exactly when the trainer starts.
        # Retry instead of killing the whole SubprocVecEnv over one hiccup.
        for _attempt in range(4):
            try:
                self._wait_for_bridge()
                break
            except RuntimeError as e:
                if _attempt == 3:
                    raise
                print(f"[env] bridge not ready ({e}); retrying in 10s "
                      f"({_attempt + 1}/3)")
                time.sleep(10)
        if self._turbo and self.TURBO_KEY and pydirectinput is not None:
            pydirectinput.keyDown(self.TURBO_KEY)
            print(f"[env] holding {self.TURBO_KEY.upper()} (fast-forward) for this run")

    # ------------------------------------------------------------- bridge IPC

    def _send(self, cmd):
        self._seq += 1
        cf = getattr(self, "_cmd_file", None) or CMD_FILE
        tmp = cf + ".tmp"
        with open(tmp, "w") as f:
            f.write(f"{self._seq}|{cmd}\n")
        deadline0 = time.time() + self.STEP_TIMEOUT
        while True:
            try:
                os.replace(tmp, cf)
                break
            except PermissionError:
                if time.time() > deadline0:
                    raise
                time.sleep(0.003)
        deadline = time.time() + self.STEP_TIMEOUT
        while time.time() < deadline:
            s = self._parse_state_once()
            if s is not None and s["ack"] == self._seq:
                return
            time.sleep(0.002)
        print(f"[env] WARNING: no bridge ack for '{cmd}' (seq {self._seq})")

    def _parse_state_once(self):
        """Parse the v4 (36-field) or v3 (22-field) state line.

        Returns dict with: frame, h[4], players[4] = {pos(3), face(2)},
        stones [(x,z)...], v4 flag, ack.
        """
        try:
            with open(getattr(self, "_state_file", None) or STATE_FILE) as f:
                parts = f.read().strip().split(",")
            v = [float(p) for p in parts]
            players = [{"pos": np.zeros(3), "face": np.zeros(2)}
                       for _ in range(4)]
            if len(v) in (72, 80):                 # v6: v5 + stone y, meters,
                #                                    item ptrs, projectiles
                # v7 (80 fields, Aug 10): v6 + chest block at [71..78] =
                # chestN, fallN, [cx,cz,cy]x2 nearest-first, cmdseq LAST.
                # Chests are the GEM SOURCE (HANDOFF Sec 15: pads hold chests,
                # not stones), so the bot must see them or it is back to
                # memorizing pad locations per stage. OBS ONLY in Leg 0 —
                # no reward term reads any chest field.
                h = [max(0.0, x) for x in v[1:5]]
                for k in range(4):
                    o = 5 + 5 * k
                    players[k]["pos"] = np.array([v[o], v[o + 1], v[o + 2]])
                    face = np.array([v[o + 3], v[o + 4]])
                    n = float(np.hypot(face[0], face[1]))
                    players[k]["face"] = face / n if n > 1e-6 else face
                    players[k]["gems"] = int(v[45 + k])   # -1 = unanchored
                    players[k]["form"] = int(v[49 + k])
                    mtr = v[53 + k]
                    players[k]["meter"] = mtr if mtr >= 0.0 else -1.0
                    players[k]["item"] = int(v[57 + k])   # F+0x54 def pointer
                # stones: 6 TRIPLES (x, z, y) at [27..44]. `stones` stays a
                # list of (x, z) 2-tuples exactly as v4/v5 emitted, because the
                # whole reward path (_stone_gems, the approach shaping, the
                # pickup-credit tracker) unpacks 2-tuples. y rides alongside in
                # a parallel list instead of widening the tuple -- changing the
                # tuple shape would silently break `sx, sz = min(cur, ...)`.
                stones, stones_y = [], []
                for k in range(6):
                    o = 27 + 3 * k
                    x, z, y = v[o], v[o + 1], v[o + 2]
                    if x != 0.0 or z != 0.0:
                        stones.append((x, z))
                        stones_y.append(y)
                proj = []
                for k in range(2):
                    o = 61 + 5 * k
                    px, py, pz, pvx, pvz = v[o], v[o+1], v[o+2], v[o+3], v[o+4]
                    if px != 0.0 or pz != 0.0:
                        proj.append((px, py, pz, pvx, pvz))
                out = {"frame": int(v[0]), "h": h, "players": players,
                       "stones": stones, "stones_y": stones_y, "proj": proj,
                       "v4": True, "v5": True, "v6": True,
                       "ack": int(v[71])}
                if len(v) == 80:
                    chests = []
                    for k in range(2):
                        o = 73 + 3 * k
                        cx, cz, cy = v[o], v[o + 1], v[o + 2]
                        if cx != 0.0 or cz != 0.0:
                            chests.append((cx, cz, cy))
                    out["chestN"] = int(v[71])
                    out["chest_fall"] = int(v[72])
                    out["chests"] = chests
                    out["v7"] = True
                    out["ack"] = int(v[79])
                return out
            if len(v) == 44:                       # v5: v4 + real counters
                h = [max(0.0, x) for x in v[1:5]]
                for k in range(4):
                    o = 5 + 5 * k
                    players[k]["pos"] = np.array([v[o], v[o + 1], v[o + 2]])
                    face = np.array([v[o + 3], v[o + 4]])
                    n = float(np.hypot(face[0], face[1]))
                    players[k]["face"] = face / n if n > 1e-6 else face
                    players[k]["gems"] = int(v[35 + k])   # -1 = unanchored
                    players[k]["form"] = int(v[39 + k])
                stones = []
                for k in range(4):
                    x, z = v[27 + 2 * k], v[28 + 2 * k]
                    if x != 0.0 or z != 0.0:
                        stones.append((x, z))
                return {"frame": int(v[0]), "h": h, "players": players,
                        "stones": stones, "v4": True, "v5": True,
                        "ack": int(v[43])}
            if len(v) == 36:                       # v4
                h = [max(0.0, x) for x in v[1:5]]
                for k in range(4):
                    o = 5 + 5 * k
                    players[k]["pos"] = np.array([v[o], v[o + 1], v[o + 2]])
                    face = np.array([v[o + 3], v[o + 4]])
                    # normalize: render matrices carry per-character SCALE
                    # (Gunrock r0 norm = 1.2, verified Aug 3) — facing must
                    # be a unit vector or his fx/fz and threat-dot skew
                    n = float(np.hypot(face[0], face[1]))
                    players[k]["face"] = face / n if n > 1e-6 else face
                stones = []
                for k in range(4):
                    x, z = v[27 + 2 * k], v[28 + 2 * k]
                    if x != 0.0 or z != 0.0:
                        stones.append((x, z))
                return {"frame": int(v[0]), "h": h, "players": players,
                        "stones": stones, "v4": True, "ack": int(v[35])}
            if len(v) == 22:                       # v3 fallback (no facing)
                h = [max(0.0, x) for x in v[1:5]]
                players[0]["pos"] = np.array(v[5:8])
                players[1]["pos"] = np.array(v[8:11])
                stones = []
                for k in range(4):
                    x, z = v[13 + 2 * k], v[14 + 2 * k]
                    if x != 0.0 or z != 0.0:
                        stones.append((x, z))
                return {"frame": int(v[0]), "h": h, "players": players,
                        "stones": stones, "v4": False, "ack": int(v[21])}
        except (OSError, ValueError, IndexError):
            return None
        return None

    def _read_state(self):
        deadline = time.time() + self.STEP_TIMEOUT
        while time.time() < deadline:
            s = self._parse_state_once()
            if s is not None:
                return s
            time.sleep(0.002)
        raise RuntimeError("No data from the Lua bridge — is Flycast running "
                           "with powerstone.lua and a game loaded?")

    def _wait_for_bridge(self):
        s1 = self._read_state()
        time.sleep(0.3)
        s2 = self._read_state()
        if s1["frame"] == s2["frame"]:
            raise RuntimeError("Bridge frame counter not advancing — emulator paused?")
        print(f"[env] bridge alive (frame {s2['frame']}, "
              f"line={'v7' if s2.get('v7') else ('v6' if s2.get('v6') else ('v5' if s2.get('v5') else ('v4' if s2['v4'] else 'v3 FALLBACK')))}"
              f" obs_dim={self.OBS_DIM} actions={len(self.ACTIONS)})")
        if s2.get("v6") and not s2.get("v7"):
            print("[env] WARNING: v6 line but not v7 — chest obs [107..110] "
                  "will read zero. Update powerstone.lua (LINE_V7).")
        if not s2.get("v6"):
            # Loud, because this is the silent-degradation failure mode the
            # handoff calls gotcha 1: after a Flycast restart cur_slot is nil,
            # the line drops to v3, stones report NOTHING, and training looks
            # merely bad rather than broken. The env issues loadstate every
            # episode so it self-heals -- but say so, do not assume.
            print("[env] WARNING: not receiving the v6 line. Stone y, form "
                  "meters, items and projectiles will all read 0.0. "
                  "Check LINE_V6 in powerstone.lua and send `loadstate <n>`.")

    def _detect_opp(self, s, i):
        """Players that count as opponents in THIS state read.

        Extracted Aug 17 so reset() can poll it (see the race fix in reset).
        Rule is unchanged: healthy at reset AND (v3: player 0 only)
        (v4: any player with a pinned matrix = nonzero pos).
        """
        out = []
        for j in range(4):
            if j == i:
                continue
            pinned = s["v4"] and np.any(s["players"][j]["pos"] != 0)
            if (not s["v4"] and j == 0) or pinned:
                if s["h"][j] > 100.0:
                    out.append(j)
        return out

    def _wait_frames(self, start_frame, n):
        deadline = time.time() + self.STEP_TIMEOUT
        while time.time() < deadline:
            s = self._read_state()
            if s["frame"] >= start_frame + n or s["frame"] < start_frame:
                return s
            time.sleep(0.002)
        # Aug 16 (Sec 26): count 5s step ceilings. A nonzero count in the
        # [ep] line marks the env that is stalling the whole vector
        # (SubprocVecEnv steps in lockstep with its slowest env).
        self._ep_step_timeouts = getattr(self, "_ep_step_timeouts", 0) + 1
        return self._read_state()

    # ---------------------------------------------------------------- gym API

    def reset(self):
        self.steps = 0
        self._ep_step_timeouts = 0
        slot = random.choice(self.STATE_SLOTS)
        self._episode_slot = slot
        s = self._read_state()
        tries = 0
        # Aug 17 (Sec 34, second bug): FORCE a load on this env's FIRST reset.
        # _match_ready only checks "bot alive AND some opponent alive", which a
        # leftover MID-MATCH state from a previous run satisfies — so the while
        # loop below never fired, no loadstate was ever sent, and episode 1
        # silently continued someone else's match with players already dead.
        # Caught live: "SHORT OPPONENT SET slot0 ... h=[0.0, 563.3, 645.0, 0.0]
        # pinned=[True,True,True,True]" — everything pinned, two players simply
        # already KO'd. Costs ~10 junk episodes per launch if left alone.
        if not getattr(self, "_did_first_load", False):
            self._did_first_load = True
            self._send(f"loadstate {slot}")
            time.sleep(0.5)
            s = self._read_state()
        while not self._match_ready(s, provisional=True):
            mode = tries % 3
            # Aug 16 (Sec 26): the blind time.sleep(2.5) here was the 10-wide
            # throughput killer — every reset stalled the WHOLE SubprocVecEnv
            # barrier ~2.6s ("match ready after 1 tries" == one full nap).
            # Now: short settle so the loadstate actually applies (we must not
            # read the PRE-load state as ready), then fast-poll the remainder.
            if mode == 0:
                self._send(f"loadstate {slot}")
                settle, budget = 0.5, 2.5
            elif (mode == 1 and pydirectinput is not None
                  and getattr(self, "_turbo", True)):
                # keyboard fallback is GLOBAL input — parallel instances
                # (turbo=False) must never press it; it would land on
                # whichever window has focus.
                pydirectinput.press(self.LOAD_STATE_KEY)
                settle, budget = 0.5, 2.5
            else:
                self._send("press 4 6")
                settle, budget = 0.3, 1.5
            time.sleep(settle)
            t_end = time.time() + (budget - settle)
            while time.time() < t_end:
                s = self._read_state()
                if self._match_ready(s, provisional=True):
                    break
                time.sleep(0.15)
            s = self._read_state()
            tries += 1
            if tries % 15 == 0:
                print(f"[env] still trying to restart the match ({tries} tries)")
        if tries:
            print(f"[env] match ready after {tries} tries")
        if not s["v4"] and not self._warned_v3:
            print("[env] WARNING: v3 state line — slot has no playerbase "
                  "calibration; facing/3rd-4th opponents zeroed. See "
                  "RUN3_CALIBRATION.md")
            self._warned_v3 = True
        i = self.AGENT_PLAYER - 1
        # ================= Aug 17 OPPONENT-DETECTION RACE FIX =================
        # BUG (HANDOFF Sec 34): _active_opp was computed from ONE instantaneous
        # read right after loadstate. Opponents that had not finished
        # initialising yet (pos still 0, or health not yet written) were
        # silently excluded FOR THE WHOLE EPISODE — they never appear in obs,
        # damage dealt to them pays NOTHING, and the win fires when only the
        # TRACKED ones are dead. slot3 hit this on ~97% of episodes (saved a
        # few frames earlier in the spawn sequence than the other states);
        # every other slot hit it on 2-4%.
        # FIX: poll for the full complement instead of trusting one frame.
        # A savestate that genuinely has fewer opponents still works — we just
        # wait out the budget and take what is really there, and SAY SO.
        expect = self.EXPECT_OPP_BY_SLOT.get(slot, self.EXPECT_OPP)
        deadline = time.time() + self.OPP_SETTLE_S
        while True:
            cand = self._detect_opp(s, i)
            if len(cand) >= expect or time.time() >= deadline:
                break
            time.sleep(0.05)
            s = self._read_state()
        self._active_opp = cand
        if not self._active_opp:
            self._active_opp = [0 if i != 0 else 1]
        if len(self._active_opp) < expect:
            # PROOF, not inference: dump the raw health quad + pinned flags so
            # a short read can be diagnosed instead of guessed at.
            pin = [bool(s["v4"] and np.any(s["players"][j]["pos"] != 0))
                   for j in range(4)]
            print(f"[env] SHORT OPPONENT SET slot{slot}: "
                  f"{len(self._active_opp)}/{expect} after "
                  f"{self.OPP_SETTLE_S:.1f}s  h={[round(x,1) for x in s['h']]} "
                  f"pinned={pin} active={self._active_opp}")
        self.baseline = [max(h, 1000.0) for h in s["h"]]
        self.prev = s
        self.prev_health = self._frac(s["h"])
        self.last_action = 0
        self._form_timer = 0
        self._ep = self._fresh_ep()
        self._stone_tracks = []
        self._my_g_int = 0
        self._opp_g_int = 0
        self._hurt_cd = 0
        self._dealt_cd = 0
        return self._observe(s, s)

    def step(self, action):
        name, kind, val = self.ACTIONS[action]
        start = self._read_state()
        if kind == "axis":
            # Analog trigger. The lua releases any held button mask first, so
            # one action = one physical input and the two never compound.
            self._send(f"axis {val} {self.AXIS_VALUE:.2f} {self.ACTION_FRAMES}")
        elif action < 4:
            # MOVEMENT (Aug 13, "make the bot just walk"): direction presses
            # OVERLAP the next decision (frames > ACTION_FRAMES), so repeated
            # same-direction actions merge into a continuous hold instead of
            # the tap-release-tap Link-shuffle. A different next action still
            # replaces the mask immediately (lua applyPress releases first).
            self._send(f"press {val} {self.ACTION_FRAMES + 4}")
        else:
            self._send(f"press {val} {self.ACTION_FRAMES}")
        s = self._wait_frames(start["frame"], self.ACTION_FRAMES)
        self.steps += 1

        health = self._frac(s["h"])
        reward, done, info = self._reward(health, s)
        # NOTE (Sep 10 audit): the obs is built BEFORE last_action is
        # updated, so the one-hot the policy sees when choosing a_{t+1} is
        # a_{t-1}, not a_t. Every checkpoint in the lineage was trained and
        # evaluated under this convention; the self-play opponent view
        # (selfplay_env._obs_from_view) and the demo recorders use a
        # one-step-fresher one. Changing it is an observation-version
        # change, deferred to the end of the current campaign.
        obs = self._observe(s, self.prev)
        self.prev = s
        self.prev_health = health
        self.last_action = action

        if self.steps >= self.MAX_STEPS:
            done, info["timeout"] = True, True
        if done:
            e = self._ep
            res = info.get("result", "timeout")
            slot = getattr(self, "_episode_slot", 0)
            nopp = len(self._active_opp)
            print(f"[ep] slot{slot} opps={nopp} {res:>7} len={self.steps:4d}  "
                  f"dmg {e['dmg_out']:+.2f}/{e['dmg_in']:+.2f}  "
                  f"stones: picked={e['picks']} lost={e['lost']} "
                  f"opp={e['opicks']}(-{e['oploose']}) "
                  f"forms={e['forms']}/{e['oforms']}  "
                  f"gem_rew={e['gem']:+.2f} shape={e['stone']:+.2f} "
                  f"appr={e['approach']:+.2f}  "
                  f"chests={e['chesto']}({e['chestb']}) "
                  f"stonev={e['stonev']} dmgF={e['dmg_form']:.2f}"
                  + (f"  STEP_TIMEOUTS={self._ep_step_timeouts}"
                     if getattr(self, "_ep_step_timeouts", 0) else ""))
            try:
                # columns 17-19 (chesto, chestb, stonev) APPENDED Aug 10 —
                # appended, not inserted, so positional readers of the first
                # 16 columns keep working on mixed-era files.
                with open(os.path.join(
                        getattr(self, "_bridge_dir", None) or BRIDGE_DIR,
                        "ep_stats_v6.csv"), "a") as f:
                    f.write(f"{s['frame']},{res},{self.steps},"
                            f"{e['dmg_out']:.3f},{e['dmg_in']:.3f},"
                            f"{e['approach']:.3f},{e['gem']:.3f},"
                            f"{e['stone']:.3f},{e['picks']},{e['lost']},"
                            f"{e['opicks']},{e['oploose']},"
                            f"{e['forms']},{e['oforms']},{slot},{nopp},"
                            f"{e['chesto']},{e['chestb']},{e['stonev']},"
                            f"{e['dmg_form']:.3f}\n")   # col 19, Leg D
            except OSError as _e:
                # Aug 20: bridge_i7 lost ~95 rows to silent append failures
                # (cause unconfirmed — file was NOT open in Excel). Never
                # eat these silently again.
                print(f"[env] WARNING: ep_stats append FAILED "
                      f"({type(_e).__name__}: {_e}) — row lost")
        return obs, reward, done, info

    def render(self, mode="human"):
        pass

    def close(self):
        if (getattr(self, "_turbo", True) and self.TURBO_KEY
                and pydirectinput is not None):
            pydirectinput.keyUp(self.TURBO_KEY)

    # -------------------------------------------------------------- internals

    @staticmethod
    def _fresh_ep():
        return {"dmg_out": 0.0, "dmg_in": 0.0, "approach": 0.0, "gem": 0.0,
                "stone": 0.0, "picks": 0, "lost": 0, "opicks": 0,
                "oploose": 0, "forms": 0, "oforms": 0,
                # Aug 10 chest telemetry (STATS ONLY — no reward reads these).
                # chesto = chests opened by anyone this episode; chestb =
                # opens where the bot was within CHEST_NEAR_R of the vanished
                # chest (approximate bot attribution); stonev = steps with at
                # least one loose gem visible (availability of the shaping
                # signal). These are the numbers Leg 1's chest-reward sizing
                # comes from.
                "chesto": 0, "chestb": 0, "stonev": 0,
                # Aug 16 Leg D: reward-weighted damage dealt while
                # transformed. The conversion metric — this is what the
                # FORM_DMG_MULT change is supposed to move.
                "dmg_form": 0.0}

    def _frac(self, raw):
        return [min(1.5, r / b) for r, b in zip(raw, self.baseline)]

    def _alive(self, h):
        return h > 0.001

    def _match_ready(self, s, provisional=False):
        i = self.AGENT_PLAYER - 1
        me = s["h"][i]
        if provisional:
            opps = [h for j, h in enumerate(s["h"]) if j != i]
            return me > 100.0 and any(h > 100.0 for h in opps)
        return me > 100.0 and any(s["h"][j] > 100.0 for j in self._active_opp)

    def _me(self, s):
        return s["players"][self.AGENT_PLAYER - 1]

    def _opps(self, s, alive_only=True):
        """Active opponents as (player_idx, player_dict), nearest first."""
        me = self._me(s)["pos"]
        health = self._frac(s["h"])
        out = []
        for j in self._active_opp:
            if alive_only and not self._alive(health[j]):
                continue
            p = s["players"][j]
            d = float(np.hypot(p["pos"][0] - me[0], p["pos"][2] - me[2]))
            out.append((d, j, p))
        out.sort(key=lambda t: t[0])
        return out

    def _dist_nearest(self, s):
        opps = self._opps(s)
        if not opps:
            opps = self._opps(s, alive_only=False)
        return opps[0][0] if opps else 0.0

    def _nearest_opp_xz(self, s):
        opps = self._opps(s)
        if not opps:
            opps = self._opps(s, alive_only=False)
        if not opps:
            return None
        p = opps[0][2]["pos"]
        return p[0], p[2]

    def _counter_gems(self, s):
        """Gem system v3 (Aug 3 night): LEDGER-based — real per-player
        logic-object counters from the v5 line. No proximity inference,
        no phantoms possible. Falls back to _stone_gems when unanchored."""
        i = self.AGENT_PLAYER - 1
        me_n, me_p = s["players"][i], self.prev["players"][i]
        gem, e = 0.0, self._ep
        d = me_n["gems"] - me_p["gems"]
        formed = me_n["form"] == 1 and me_p["form"] == 0
        if formed:
            gem += self.TRANSFORM_BONUS
            e["forms"] += 1
            self._form_timer = self.FORM_STEPS
        if me_n["form"] == 1:
            self._form_timer = max(self._form_timer, 2)
        if d > 0:
            gem += self.GEM_W * d
            e["picks"] += d
        elif d < 0 and not formed and me_p["form"] != 1:
            # real knock-loss only: the HUD byte holds 3 THROUGH a form and
            # drops 3->0 when it ENDS (me_p form==1 guards that), and the
            # transform-start consumption is guarded by `formed`
            gem -= self.LOST_W * (-d)
            e["lost"] += -d
        self._my_g_int = max(0, min(3, me_n["gems"]))
        opp_max = 0
        for _dst, j, pn in self._opps(s):
            pp = self.prev["players"][j]
            if pn.get("gems", -1) < 0 or pp.get("gems", -1) < 0:
                continue
            od = pn["gems"] - pp["gems"]
            oformed = pn["form"] == 1 and pp["form"] == 0
            if oformed:
                gem -= self.OPP_TRANSFORM_PEN
                e["oforms"] += 1
            if od > 0:
                gem -= self.OPP_GEM_W * od
                e["opicks"] += od
            elif od < 0 and not oformed and self._dealt_cd > 0:
                gem += self.KNOCK_W * (-od)
                e["oploose"] += -od
            opp_max = max(opp_max, min(3, pn["gems"]))
        self._opp_g_int = opp_max
        if self._opp_g_int >= 2:
            gem -= self.DANGER_W
        return gem

    def _counters_ok(self, s):
        i = self.AGENT_PLAYER - 1
        return (s.get("v5") and self.prev.get("v5")
                and s["players"][i].get("gems", -1) >= 0
                and self.prev["players"][i].get("gems", -1) >= 0)

    def _stone_gems(self, s):
        """Gem system v2, multi-opponent: attribution vs NEAREST opponent."""
        pme = self._me(self.prev)["pos"]
        # attribution = who is closest to the STONE, over ALL active
        # opponents — the old nearest-to-bot single opponent over-credited
        # the bot for COM pickups in 4P scrums
        opps_xz = [(p["pos"][0], p["pos"][2])
                   for _d, _j, p in self._opps(self.prev)]
        raw = list(s.get("stones") or [])
        cur = []   # dedupe: cluster entities -> one stone
        for x, z in raw:
            if not any(abs(x - cx) <= self.STONE_DEDUPE_TOL
                       and abs(z - cz) <= self.STONE_DEDUPE_TOL
                       for cx, cz in cur):
                cur.append((x, z))
        gem, e = 0.0, self._ep

        used = [False] * len(cur)
        new_tracks = []
        for tr in self._stone_tracks:
            hit = None
            for k, (x, z) in enumerate(cur):
                if (not used[k] and abs(x - tr["x"]) <= self.STONE_MATCH_TOL
                        and abs(z - tr["z"]) <= self.STONE_MATCH_TOL):
                    hit = k
                    break
            if hit is not None:
                used[hit] = True
                new_tracks.append({"x": tr["x"], "z": tr["z"],
                                   "age": tr["age"] + 1})
                continue
            if tr["age"] < self.STONE_MIN_AGE:
                continue
            dme = ((tr["x"] - pme[0]) ** 2 + (tr["z"] - pme[2]) ** 2) ** 0.5
            dopp = float("inf")
            for ox, oz in opps_xz:
                d = ((tr["x"] - ox) ** 2 + (tr["z"] - oz) ** 2) ** 0.5
                if d < dopp:
                    dopp = d
            if min(dme, dopp) > self.PICKUP_R:
                continue
            if dme < self.PICKUP_MARGIN * dopp and dme <= self.PICKUP_R_ME:
                gem += self.GEM_W
                e["picks"] += 1
                self._my_g_int += 1
                if self._my_g_int >= 3:
                    gem += self.TRANSFORM_BONUS
                    e["forms"] += 1
                    self._my_g_int = 0
                    self._form_timer = self.FORM_STEPS
            elif dopp < self.PICKUP_MARGIN * dme:
                gem -= self.OPP_GEM_W
                e["opicks"] += 1
                self._opp_g_int += 1
                if self._opp_g_int >= 3:
                    gem -= self.OPP_TRANSFORM_PEN
                    e["oforms"] += 1
                    self._opp_g_int = 0

        for k, (x, z) in enumerate(cur):
            if used[k]:
                continue
            dme = ((x - pme[0]) ** 2 + (z - pme[2]) ** 2) ** 0.5
            dopp = float("inf")
            for ox, oz in opps_xz:
                d = ((x - ox) ** 2 + (z - oz) ** 2) ** 0.5
                if d < dopp:
                    dopp = d
            if (dme <= dopp and dme <= self.KNOCK_R and self._my_g_int > 0
                    and self._hurt_cd > 0):
                self._my_g_int -= 1
                gem -= self.LOST_W
                e["lost"] += 1
            elif (dopp < dme and dopp <= self.KNOCK_R and self._opp_g_int > 0
                    and self._dealt_cd > 0):
                self._opp_g_int -= 1
                gem += self.KNOCK_W
                e["oploose"] += 1
            new_tracks.append({"x": x, "z": z, "age": 1})

        self._stone_tracks = new_tracks
        if self._opp_g_int >= 2:
            gem -= self.DANGER_W
        return gem

    def _observe(self, s, prev):
        i = self.AGENT_PLAYER - 1
        health = self._frac(s["h"])
        me, pme = self._me(s), self._me(prev)
        mp, pp = me["pos"], pme["pos"]

        obs = np.zeros(self.OBS_DIM, dtype=np.float32)
        # ---- self [0..17]
        obs[0] = health[i]
        obs[1] = mp[0] / POS_SCALE
        obs[2] = mp[2] / POS_SCALE
        obs[3] = mp[1] / HEIGHT_SCALE
        obs[4] = (mp[0] - pp[0]) / VEL_SCALE
        obs[5] = (mp[2] - pp[2]) / VEL_SCALE
        obs[6], obs[7] = me["face"][0], me["face"][1]
        g_real = me.get("gems", -1)
        obs[8] = (min(3, g_real) / 3.0) if g_real >= 0 else self._my_g_int / 3.0
        formed = me.get("form", 0) == 1
        obs[9] = (1.0 if formed
                  else self._form_timer / float(self.FORM_STEPS))
        # form meter: measured 0 when not formed, ~100 at transform, draining
        # monotonically to exactly 0.00, with the form flag clearing 0.2-1.2s
        # later (3/3 captures). So this is a real "my form is about to drop"
        # signal, not just a gauge. -1 = unanchored -> read 0.0, never noise.
        obs[10] = self._meter(me)
        # items: has_item + coarse category one-hot. Keyed on the F+0x54
        # definition POINTER; F+0x100 is an animation state and must not key
        # anything. An unrecognised pointer still sets has_item and category 0,
        # so "I am holding something" is learnable before the dictionary is
        # complete.
        iptr = me.get("item", 0) if self.CH_ITEM else 0
        bucket = self.item_bucket(iptr)
        if bucket is not None:
            obs[11] = 1.0
            obs[12:12 + self.ITEM_EMB_DIM] = self._item_emb_table()[bucket]
        elif iptr:
            # on the wire but off-grid: say "holding something" and leave the
            # identity code at zero rather than inventing one from a bad read.
            obs[11] = 1.0
        # ---- opponents, nearest first [18..56]
        prev_pos = {j: prev["players"][j]["pos"] for j in self._active_opp}
        for k, (d, j, p) in enumerate(self._opps(s)[:self.N_OPP]):
            b = self._OPP0 + 13 * k
            op, of = p["pos"], p["face"]
            obs[b + 0] = 1.0
            obs[b + 1] = (op[0] - mp[0]) / POS_SCALE
            obs[b + 2] = (op[2] - mp[2]) / POS_SCALE
            obs[b + 3] = (op[1] - mp[1]) / HEIGHT_SCALE
            obs[b + 4] = d / POS_SCALE
            pv = prev_pos.get(j, op)
            obs[b + 5] = (op[0] - pv[0]) / VEL_SCALE
            obs[b + 6] = (op[2] - pv[2]) / VEL_SCALE
            obs[b + 7] = health[j]
            # threat-dot: their facing vs the unit vector from them to me
            to_me = np.array([mp[0] - op[0], mp[2] - op[2]])
            n = np.linalg.norm(to_me)
            if n > 1.0 and (of[0] != 0 or of[1] != 0):
                obs[b + 8] = float(np.dot(of, to_me / n))
            # ledger + meter + item ride the SAME nearest-first k as the block
            # above, so every field for opponent k stays contiguous.
            g = p.get("gems", -1)
            obs[b + 9] = (min(3, g) / 3.0) if g >= 0 else 0.0
            obs[b + 10] = 1.0 if p.get("form", 0) == 1 else 0.0
            obs[b + 11] = self._meter(p)
            obs[b + 12] = 1.0 if (self.CH_ITEM and p.get("item", 0)) else 0.0
            # opponents get a has_item flag only. Which item an opponent holds
            # would cost 6 dims x3 and the bot cannot see their hands anyway;
            # "armed or not" is the decision-relevant bit.
        # ---- stones, nearest-first [57..80]
        # 6 slots (was 4). y is carried per stone: on the elevator a stone one
        # floor up rides y~3550 while the bot is near 0, so without dy the bot
        # cannot tell a reachable stone from an unreachable one. y is an
        # OBSERVATION and never a filter -- slot 1 has a real resting stone at
        # y~189 next to the y~50 ones, so height cannot classify.
        raw = list(s.get("stones") or [])
        ys = list(s.get("stones_y") or [])
        if len(ys) < len(raw):
            ys = ys + [mp[1]] * (len(raw) - len(ys))   # v3/v4/v5 line: no y
        order = sorted(range(len(raw)),
                       key=lambda q: (raw[q][0] - mp[0]) ** 2
                                     + (raw[q][1] - mp[2]) ** 2)
        for k, q in enumerate(order[:self.N_STONE_OBS]):
            x, z = raw[q]
            b = self._STN0 + 4 * k
            obs[b] = 1.0
            obs[b + 1] = (x - mp[0]) / POS_SCALE
            obs[b + 2] = (z - mp[2]) / POS_SCALE
            if self.CH_STONE_Y:
                obs[b + 3] = (ys[q] - mp[1]) / HEIGHT_SCALE
        # ---- projectiles, nearest-first [81..92]
        # The lua already sorts nearest-first and applies the class exclusion
        # list; sort again here so a v5/v4 fallback line (which carries none)
        # and any future reordering both stay correct.
        if self.CH_PROJ:
            pr = sorted((s.get("proj") or []),
                        key=lambda q: (q[0] - mp[0]) ** 2 + (q[2] - mp[2]) ** 2)
            for k, (px, py, pz, pvx, pvz) in enumerate(pr[:self.N_PROJ_OBS]):
                b = self._PRJ0 + 6 * k
                obs[b] = 1.0
                obs[b + 1] = (px - mp[0]) / POS_SCALE
                obs[b + 2] = (pz - mp[2]) / POS_SCALE
                obs[b + 3] = (py - mp[1]) / HEIGHT_SCALE
                obs[b + 4] = pvx / self.PROJ_VEL_SCALE
                obs[b + 5] = pvz / self.PROJ_VEL_SCALE
        # ---- nearest chest [107..110] (v7 line only; zeros on any fallback)
        # The gem SOURCE. The lua reports the 2 nearest resting chests; take
        # the nearest again here (same defensive re-sort as projectiles). dy
        # matters for the same reason stone dy does: an elevator chest one
        # floor up is not openable from here.
        if self.CH_CHEST:
            ch = sorted((s.get("chests") or []),
                        key=lambda q: (q[0] - mp[0]) ** 2 + (q[1] - mp[2]) ** 2)
            if ch:
                cx, cz, cy = ch[0]
                b = self._CHT0
                obs[b] = 1.0
                obs[b + 1] = (cx - mp[0]) / POS_SCALE
                obs[b + 2] = (cz - mp[2]) / POS_SCALE
                obs[b + 3] = (cy - mp[1]) / HEIGHT_SCALE
        # ---- stage one-hot + last action ([111..121] stay zero)
        slot = getattr(self, "_episode_slot", 0)
        if 0 <= slot < 4:
            stage_dim, level = self.SLOT_META.get(
                slot, (min(slot, 3), 2))
            obs[self._STG0 + stage_dim] = 1.0
            obs[self.DIFF_DIM] = level / 8.0   # COM difficulty (curriculum)
        obs[self._ACT0 + self.last_action] = 1.0
        return np.clip(obs, -5.0, 5.0)

    def _meter(self, p):
        """Form meter -> [0,1]. -1 (unanchored) and missing keys read 0.0.

        Zero is the right fallback: it is what an untransformed player reads,
        so a bad anchor degrades to 'nobody is transformed' rather than to
        noise the net would have to learn to ignore.
        """
        if not self.CH_METER:
            return 0.0
        m = p.get("meter", -1.0)
        if m is None or m < 0.0:
            return 0.0
        return float(min(1.0, m / 100.0))

    def _reward(self, health, s):
        i = self.AGENT_PLAYER - 1
        me_now, me_prev = health[i], self.prev_health[i]
        pairs = [(self.prev_health[j], health[j]) for j in self._active_opp
                 if self._alive(self.prev_health[j]) or self._alive(health[j])]

        damage_dealt = sum(max(0.0, p - n) for p, n in pairs)
        # Aug 16 LEG D: damage dealt WHILE TRANSFORMED earns a premium.
        # Read the live form flag off the state line (same source the gem
        # path uses), not _form_timer — the timer is a 150-step heuristic
        # and would keep paying after the form actually ended.
        _in_form = bool(s["players"][i].get("form") == 1)
        dmg_w = self.DAMAGE_DEALT_W * (self.FORM_DMG_MULT if _in_form else 1.0)
        own_delta = me_now - me_prev
        approach = (self._dist_nearest(self.prev)
                    - self._dist_nearest(s)) / POS_SCALE

        if own_delta < 0:
            self._hurt_cd = 5
        elif self._hurt_cd:
            self._hurt_cd -= 1
        if damage_dealt > 0:
            self._dealt_cd = 5
        elif self._dealt_cd:
            self._dealt_cd -= 1
        # ---- chest opens (Aug 10; REWARDED from Leg 1). Chest count
        # dropping = someone opened one. Credit rule mirrors pickup credit:
        # the bot earns CHEST_OPEN_W only if it was INSIDE CHEST_OPEN_R of
        # the vanished chest AND strictly closest by the pickup margin over
        # every opponent — being merely nearby while a COM opens pays
        # nothing. Only the 2 nearest chests ride the wire, so credit for a
        # chest the bot wasn't close to is structurally unlikely to begin
        # with. The bonus rides the gem component -> GEM_EP_CAP bounds it.
        # e['chestb'] now counts ATTRIBUTED (paid) opens; e['chesto'] still
        # counts everyone's.
        chest_bonus = 0.0
        if s.get("v7") and self.prev.get("v7"):
            dc = self.prev["chestN"] - s["chestN"]
            if dc > 0:
                self._ep["chesto"] += dc
                pme_ = self._me(self.prev)["pos"]
                opp_prev = [self.prev["players"][j]["pos"]
                            for j in self._active_opp]
                gone = [c for c in (self.prev.get("chests") or [])
                        if not any(abs(c[0] - n[0]) < 40 and abs(c[1] - n[1]) < 40
                                   for n in (s.get("chests") or []))]
                for c in gone:
                    dme = ((c[0] - pme_[0]) ** 2 + (c[1] - pme_[2]) ** 2) ** 0.5
                    dopp = min((((c[0] - op[0]) ** 2 + (c[1] - op[2]) ** 2) ** 0.5
                                for op in opp_prev), default=float("inf"))
                    if dme <= self.CHEST_OPEN_R and dme < self.PICKUP_MARGIN * dopp:
                        chest_bonus += self.CHEST_OPEN_W
                        self._ep["chestb"] += 1
            if s.get("stones"):
                self._ep["stonev"] += 1
        gem = (self._counter_gems(s) if self._counters_ok(s)
               else self._stone_gems(s))
        gem += chest_bonus
        # hard clamp: cumulative episode gem reward stays inside
        # [-GEM_EP_CAP, +GEM_EP_CAP] — Aug 2's "nothing outbids a win"
        # rule, now structural (slot-0 phantom storms hit +67/ep without it)
        _g0 = self._ep["gem"]
        # Aug 29: at lv8 the terminal loss is 2.0 (scale 0.2) -- shrink the
        # negative gem floor below it so 'nothing outweighs dying' holds.
        _neg_cap = self.GEM_EP_CAP_NEG
        if self.SLOT_META.get(getattr(self, "_episode_slot", 0), (0, 2))[1] >= 8:
            _neg_cap = 1.5
        gem = max(-_neg_cap - _g0, min(gem, self.GEM_EP_CAP - _g0))

        stone_shape = 0.0
        if self._form_timer > 0:
            self._form_timer -= 1
        else:
            cur, prv = s.get("stones") or [], self.prev.get("stones") or []
            if cur and prv:
                pos_now = self._me(s)["pos"]
                pos_prev = self._me(self.prev)["pos"]
                mx, mz = pos_now[0], pos_now[2]
                sx, sz = min(cur, key=lambda p: (p[0] - mx) ** 2
                                                + (p[1] - mz) ** 2)
                if any(abs(px - sx) < 2.0 and abs(pz - sz) < 2.0
                       for px, pz in prv):
                    d_now = ((sx - mx) ** 2 + (sz - mz) ** 2) ** 0.5
                    d_prev = ((sx - pos_prev[0]) ** 2
                              + (sz - pos_prev[2]) ** 2) ** 0.5
                    _w = self.STONE_APPROACH_W * (
                        self.URGENCY_MULT if self._my_g_int == 2 else 1.0)
                    stone_shape = (d_prev - d_now) / POS_SCALE * _w

        e = self._ep
        e["dmg_out"] += dmg_w * damage_dealt
        if _in_form:
            e["dmg_form"] += dmg_w * damage_dealt   # Leg D telemetry
        e["dmg_in"] += self.DAMAGE_TAKEN_W * min(0.0, own_delta)
        e["approach"] += self.APPROACH_W * approach
        e["gem"] += gem
        e["stone"] += stone_shape

        reward = (dmg_w * damage_dealt
                  + self.DAMAGE_TAKEN_W * min(0.0, own_delta)
                  + self.APPROACH_W * approach
                  + gem
                  + stone_shape
                  - self.TIME_PENALTY)

        done, info = False, {"health": health, "dist": self._dist_nearest(s)}
        if not self._alive(me_now) and self._alive(me_prev):
            _lv = self.SLOT_META.get(
                getattr(self, "_episode_slot", 0), (0, 2))[1]
            reward -= self.LOSS_PENALTY * self.LOSS_SCALE_BY_LEVEL.get(_lv, 1.0)
            done, info["result"] = True, "loss"
        elif pairs and all(not self._alive(n) for _, n in pairs):
            reward += self.WIN_BONUS
            done, info["result"] = True, "win"
        return reward, done, info
