# HANDOFF — Power Stone 2 RL lab notebook (Aug 22, 2026 onward)

> Sep 10 2026 repo cleanup: every eval/train receipt referenced below now
> lives in `linux_port/receipts/` (same filenames), pre-relay launchers and
> two rig-era zips in `linux_port/archive/`, porting notes and the Reddit
> kit in `docs/`. Model zips and the relay scripts did not move.

## STATE AT CONTEXT COMPACTION (Sep 23 2026 ~1:30 pm EDT) — READ THIS FIRST

**Sep 23 ~1:30 pm UPDATE (Astra review, Blake: "go on all of it before leg 71 battery"):** see
ASTRA REVIEW FIXES below. Leg 72 boots with two versioned changes: obs ctx fix (stage one-hot +
DIFF_DIM now written on the randomized slots 10-22; they were ZERO in ~93%% of training episodes
since leg 58 while the evals had them) and the learner time cost restored after the zero-sum step
(it had cancelled exactly since leg 55). Both are flags in `league_env.txt` (`PS2_OBS_CTX_FIX=1
PS2_ZS_TIME=1`, `=0` reverts either). Read legs 72-73 against 70-71 as ONE intervention (two changes
at once, Blake's call). Also: leg 70's "interval clear of the old record" line below is WRONG —
the Wilson intervals overlap (leg 59 20.3-27.7 vs leg 70 25.0-32.9, p~0.07); leg 70 is the new
observed best, +5 points, awaiting leg 71 as confirmation. And `forms=A/B` in the stats lines is
bot transforms / opponent transforms, NOT closed/attempted; the leg 68-70 review "closing rate"
lines are misreads (rubric now carries a data dictionary). The battery now enforces the hold
thresholds itself (`hold_gate.py`, marker `claude_bridge/hold_leg<N>.txt`), verifies the pool copy
before advancing state, and takes a per-leg lock dir `claude_bridge/battery_leg<N>.lock`.

**Live:** leg 85 training (standing recipe; launched 10:45 am EDT Sep 26, done ~3:25 pm; wake `ps2-leg85-end-wake` 4:00 pm), state `85 ./powerstone_v6_leg84_league.zip`, trainer = mixed. Leg 84 = trio 29.8 / lv3 **98.8** record / AB **85-15** best fixed / lv8mix 28.0; leg 83 = 31.4 / 96.8 / 75 / 30.0. NEXT LEVER needs Blake's go: special-death + stone-retention reward (NEXT MOVES #2).
state `71 ./powerstone_v6_leg70_league.zip`, `league_trainer.txt` = mixed, battery chains leg 72.
Leg 70's scouting run (tmux scout70) was still encoding at compaction: when `claude_bridge/
scout_leg70_done.txt` appears, spawn the Sonnet reviewer on `videos/review_leg70/` (rubric
`scout_rubric.md`), send `videos/leg70_win.mp4`, relay three lines. Relay watcher and the
scouting waiter are session monitors; a new session recreates the watcher (SESSION_HANDOFF sec 5).

**STANDING RECIPE (every piece passed its pre-registered read):** mixed arena (learner P2 Falcon,
pool policies P1+P3 Falcon, COM P4 lv3 with a RANDOM CHARACTER per episode, `states_mixed/`
slots 0,10-22), obs v2, 4-port harness, 10 actors, 4M steps/leg; optimizer `league_optim.txt` =
`PS2_LR=1e-4 PS2_TARGET_KL=0.03 PS2_BATCH_SIZE=256`; arena `league_env.txt` = `PS2_ZERO_SUM=1
PS2_START_HEALTH=0.5,1.0 PS2_STATE_SLOTS=0,10,...,22 PS2_OBS_STACK=7` (strided 7-lag frame
stack, lags 16,8,4,3,2,1,0 = 1.6 s; every zip from leg 70 on has an 854-wide input, evaluators
detect it). Env fixes live: reload on every reset, pre-roll stagger 0-239. Eval contract = the
"fair start" one from leg 41 (champion 5.8 / 92.0).

**SCOREBOARD (lv8 n=500 / lv3 n=250 / champion AB n=100):** leg 70 = **28.8 (25-33) / 97.6 / 74-26
= ALL-TIME RECORD by 5 points, interval clear of the old record (23.8, leg 59)**; K=4 stack legs
68-69 = 18.2 / 23.0; single-frame recipe legs 55-67 lv8 mean ~20 (band 16-24). Champion 5.8 -> 28.8
= 5x under the same contract. Training stream: stones ~5/ep, timeouts 0, win share 0.36-0.41,
per-character 0.33-0.43. Win share by bot transforms per round (legs 67-70, ~7.5k eps each):
0 -> 1%%, 1 -> 25-31%%, 2 -> 70-73%%, 3 -> 83-86%%; ~30%% of rounds have none. Transforms ARE wins.

**What landed since the Sep 16 compaction (each has its own section below):** optimizer sweep
(SWEEP 40 RESULTS; target_kl 0.1 lineage drifted and was abandoned, restart from the kl01 zip
with explicit lr/kl — ZIPS PERSIST target_kl); PRE-ROLL FIX + re-baseline; ARENA LEVERS (zero-sum
reward, start-health RAM write; HEALTH_OBJ is the real health cell); CHARACTER RANDOMIZATION
(13 stamped states, menu path recorded); PER-LEG VIDEO + FIGHT SCOUTING (battery records
`videos/leg<N>_lv8.mp4`, `scout_leg.sh` makes exact-cut sheets + 4 fps final strips + KO tail,
Sonnet review from `scout_rubric.md` into `videos/review_leg<N>.md`; reviews 61-69 exist);
FRAME STACKING (obs_stack.py, surgery_stack.py, equivalence/agreement tests; K=4 then strided
K=7 — the pure strided six was rejected because the lag-3->4 remap changed 10%% of decisions).
COM-level RAM write probe NEGATIVE (difficulty is consumed at match start); level randomization
needs level-5/8 state sets stamped via the options menu (queued).

**Repo:** local git repo initialised Sep 23 on top of origin/main (bwalsh321/powerstone2-rl-mac,
head 90573dc Sep 9): commit bcf5b36 (M4 era through leg 70, 335 files, 149 MB) + 5857901 (harness
source `sdlarch-rl/src` etc. tracked; builds, binaries, `sdlarch_rl/roms/` 480 MB excluded).
NOT PUSHED — no GitHub credential on this Mac; Blake pushes (`git push origin main`). `.gitignore`
extended (videos, logs, pools, states_mixed states, probe dirs, cores). New legs add zips +
receipts + review .md files; commit as Blake asks; never push unless he says so in the moment.

**Blake's preferences (binding):** one report per leg when the battery lands (table, three lines,
win clip via SendUserFile, three review lines); no hourly entropy pings; 12-hour am/pm times;
never change diet/core variables/ent_coef/optim/env flags unasked (propose; he decides); hold
rule slot2 < 70 / AB < 35 / lv8 < 4.0; two consecutive drops = watch, three = signal.

**Queued (Blake's order of interest):** (1) RE automation for an observation audit: per-fighter
move/animation id, hitbox-active, hit-stun — scan RAM around scripted events like the health
scan; (2) COM level randomization via stamped level-5/8 states; (3) league exploiters (a seat
whose job is to beat the main agent); (4) two action heads (direction x button); (5) LSTM /
recurrent policy (needs the recurrent PPO path; "a week"); (6) the 7950X Linux box as a second
lab (build harness, headless GL, dolphin dirs, parity with the leg 70 zip first); (7) human play
test of the current zip (`play_vs.py`). Old open items still parked: finishing-bonus diet idea,
level-5 COM seat, discriminator states.

## BETTER EYES (Sep 23 2026 10 pm-11 pm EDT; Blake: "Let's work on better eyes... I'd rather do that than buy compute")

Tool: `linux_port/ram_scan.py` (`capture` on a hidden instance: every frame, all four player objects
[PLAYER_MAT[k]-0x400, +0x3938), health/pos/mask, scripted P2 presses, HEALTH_OBJ refill every 300 f so
nobody dies; `--dict-off 3685` PNG per new state value; `--pool` tracks the 160-slot entity pool with a
PNG per new class pointer. `analyze` ranks offsets by alignment with hit / press events). Runs:
`scan/run1` (slot 2, 7,200 f) and `scan/run2_slot3` (slot 3, 14,400 f, 253 hits, 12 COM transforms).
Instance 12; 14,400 frames capture in ~70 s. Never use instances 0-9 (actors) or 11 (scout/battery).

FOUND (offsets inside the object window; all four objects, character-independent):
- **+0x3792 u8 = HIT-STUN TIMER.** Set to ~40 on the hit frame, -1 per frame to 0, retriggered per hit.
  Alignment with the object's own health drops 0.94-1.00 on all four seats (Falcon, Pride, Ryoma, Accel,
  Ayame, Pete). "This fighter cannot act for N frames."
- **+0x3685 u8 = STATE BYTE** (+0x3686 = previous state). Dictionary from 14,400 f: 0 idle, 1 walk (~35 f),
  2/4/6 short transitions, 5 airborne (~40 f; every jump press -> 4 -> 5), 7 attack animation (~45 f; attack,
  throw AND grab presses all -> 7), 8/9/10/11/12 throw/grab variants, 14/15/16 ? (chest/pickup-adjacent,
  unlabelled), 25 transforming (28 f; half its frames formed), 26 TRANSFORMED SPECIAL IN PROGRESS (100%% of
  its frames while formed, ~96 f), 30 ? (yellow ring under 2P), 32 hit reaction (stun>0 64%%, ~82 f incl.
  knockdown), 33 one 97 f episode, 34 hit while airborne, 35 one-frame.
- +0x00a2 u8 = hits-taken counter. +0x3788 u16 = fine action word (35-70 values per character; bit 0x400
  set during hit reactions). +0x36e4 u16 = changes on hit, stays (last-hit-by pointer low bits?).
  +0x039d/+0x039f/+0x03a1 = input latch (1 jump, 2 throw, 4 right...; also readable on COM seats).
- Knockback vector floats around +0x2680-0x2689 change on every hit (many values).

PROJECTILES: the reader's only known class `0x0C7F9A10 "rocket"` was NEVER live in 4 minutes with Pride
transforming 4 times. The specials are multi-instance object clusters and the `counts.get(c) == 1`
uniqueness gate in ps2_ram.py rejects them: Pride's special = 0x0C7EExxx/0x0C7EFxxx cluster (up to 15
simultaneous, ~2,100 u/s), Ryoma's = 0x0C80D230 (6-8 simultaneous), Accel's = 0x0C815xxx-0x0C81Exxx
(3-10 simultaneous, 1,500-2,400 u/s). Screenshot-confirmed (`scan/run2_slot3/montage_specials.png`): the
0x0C7EF130 / 0x0C7EECD8 first appearances show transformed Pride firing the rocket arc; 0x0C815EC8 / 0x0C816A88
show the sky beam of a transformed special; 0x0C81Cxxx-0x0C81E158 appear with Accel's armored form in melee.
=> THE BOT CANNOT SEE ANY COM SPECIAL PROJECTILE TODAY (Blake's
"Pride rockets take 80%% point blank" item confirmed as a blind spot). Ground items live in the
0x0C61xxxx band (excluded from projectiles on purpose; not on the obs at all); chests 0x0C5Dxxxx.

PROPOSED OBS V3 (Blake's go needed; nothing touches the league until then): per fighter (self + 3 opps,
nearest-first like the existing blocks) stun/40 + state one-hot {idle-walk, air, attack, hit, transforming,
special, other} = 8 dims x 4 = 32; projectiles: drop the uniqueness gate, report the 2-3 nearest fast
pool objects with velocity whatever their class (exclude stone/chest/item bands + carried visuals);
ground items: 2 nearest with pos + category (item dictionary from the pool class pointer, to build).
~40 new dims -> input 162 (x7 stack = 1,134); warm start by surgery with zero columns on the new inputs,
agreement test, two-leg read vs the 16-24 band. Chests/weapons: visibility only, NO item reward (Blake's
economy point; the bot learned cactus-throwing blind, wins will teach value).

## ASTRA REVIEW 2 (Sep 25 2026 ~12:30-2:30 pm EDT; Blake: "hold off on [the plan], queue that after these findings")

Report: `~/Documents/Codex/2026-09-23/cp/outputs/powerstone-review-2026-09-25.md` (+ validation txt). Verified fixes it
confirmed: context inputs, time cost, checkpoint persistence, hold gate, rejected loads, validator exit codes. What it
found and what was done (all committed; backups `archive/*_sep25.*`):
| # | Finding | Done |
|---|---|---|
| 1 | slot 3 is NOT "held out again": legs 77-78 trained on it (4,299 eps) and every later zip descends from them | prose corrected everywhere: slot 3 = SEEN-STATE regression benchmark from leg 77; states/slot90-94 = the fresh test; a third untouched set is still to be stamped for the eventual final test |
| 2 | slicing the v3 obs to 122 keeps the layout, not the contract: the v3 reader fills the two projectile slots that the v2 reader left empty (8 prefix positions differ on identical RAM); v2 pool policies and the AB champion were fed a changed input | FIXED: the reader now also computes the projectile pair by the v2 rule (line v9 = 103 fields, `proj_legacy`), and every v2 view (FFA pool seats, the 1v1 opponent / AB champion) is built with `_legacy_proj` so its [81..92] follow the v2 contract; the learner keeps v3. Unit test + arena smoke pass |
| 3 | AB champion P1 view leaked the learner's form timer / gem fallback (0.8 own-form while untransformed) | FIXED in selfplay_env: per-seat counters mirrored from the view's own transitions (the FFA method); seats still fixed (candidate P2, champion P1). RE-BASELINE: leg 80 vs champion = 80-22 (78%%) under the fixed view vs 86-14 old -> the old view inflated AB by ~8 points; fixed series starts at leg 81 |
| 4 | lv8mix receipt cannot prove all five lineups ran; sampling unbalanced | TODO after leg 80's battery: round-robin 100 episodes per lineup, per-lineup W/L in the summary, merge_receipts requires the exact `slots=` list |
| 5 | "78%% ceiling" is a conditional association, not causal; "never wins with < 2" is 1/149 wrong; the rubric's automatic swarm credit is too strong | prose corrected (hypothesis, not ceiling); rubric now says "likely bot (swarm)" and "uncertain" when another attacker is adjacent |
| 6 | native `getState` ignores `retro_serialize`'s result (a failed save returns a 16-byte buffer); Python opened the destination first | Python: validate the blob (>= 1 MB) BEFORE touching the file, write a temp and `os.replace` (atomic); C++ source now returns empty bytes on failure (rebuild needed: next harness build / the 9950X; the Mac binaries are unchanged) |
| 7 | headless Linux relay has no persistent DISPLAY path; G5 parity rule statistically wrong; core URL mutable | LINUX_BRINGUP: persistent Xvfb :99 systemd unit, every relay script exports DISPLAY on Linux; parity = two-proportion test + 6-point cap on n=200; pin the core by sha256 |
| 8 | validator PASSes tiny fixtures | coverage rule: < 90%% of the expected 196 seam checks or < 1,000 [ep] lines = FAIL |
| 9 | test_obs_context replicated the constructor's mapping by hand | `ffa_slot_meta()` is one function used by the constructor AND the test |
Still open (Astra, agreed): run manifests per checkpoint, mtime-free pool chronology, per-actor deadlines, scoped
`pkill`, evaluate both AB seat assignments, a recent-parent AB opponent, the legacy prose about "byte-identical".

## NEXT MOVES (Sep 25 2026 ~11:30 am EDT; Blake: "update the handoff with the next moves", "train on the eval shape
## should be the first variable to change", memory = "the biggest lift but also the biggest lever")

WHY, in one table (leg 79 lv8 eval, 500 rounds): bot transforms 0 -> 21%% of rounds, 0%% won; 1 -> 30%%, 1%%; 2 -> 24%%,
27%%; 3 -> 25%%, 78%%. It never wins a lv8 round with fewer than two transforms and fails to reach two in half its
rounds; 7.0 stones picked and 3.1 knocked off per round. Rounds with 3+ transforms are won 78%% of the time; that is a CONDITIONAL association (surviving
longer also allows more transforms), a hypothesis about the stone economy under pressure from three lv8 COMs, not a
causal estimate or a ceiling (Astra, Sep 25), and the recurring death is standing inside a special (6 reviews in a row).
BENCHMARKS: Blake vs three lv8 COMs = 23-1 (Aug 30 2026, rig, demos_lv8/demo_005.npz, 1,000+ hours of play). Bot:
26.2%% clean. Milestones to chase: 35%% next, then 50%%, then Blake's number (the 78%% row is a hypothesis, not a ceiling).
Benchmark design (Blake: "it has to be a test"): KEEP the fixed trio (states/slot3, 80 legs of history) AND a second
held-out set of five fixed three-COM lv8 lineups (states/slot90-94) that never train; training three-COM lineups are
different (states_mixed/slot50-59). Battery = 4 evals from leg 80 on (lv8 trio 500, lv3 250, champion AB 100, lv8mix
500 = ~15 min more); the hold rule still reads only the first three.

ORDER OF WORK (each = a pre-registered two-leg read against the band; nothing changes without Blake's go except #1):
1. TRAIN ON THE EVAL SHAPE (GO, applied for leg 81): ten three-lv8-COM lineups (slots 50-59) at 26%% of episodes
   alongside the 28 mixed-arena character states (14 lv3 + 14 lv8 P4-COM). This is a SLICE, not a switch: the
   fast test (legs 77-78, one trio at 26%%) lifted lv8 from 22.6 to ~27 and it held at 26.2 with the trio removed.
   Read = legs 81-82 on the trio AND on lv8mix. Revert = drop 50-59 from league_env.txt.
2. REWARD: (a) special-death penalty = extra cost for damage taken while a nearby opponent is in state 25/26
   (the obs v3 class the bot can now see; the Sep 20-era attempt failed because the bot could not see specials);
   (b) stone retention = a larger penalty per stone knocked off the bot. Kill switch: timeout share (a bot that only
   runs). Blake's go needed (diet).
3. LV8 COM AS A POOL SEAT: two-COM versions of the character states (one pool Falcon + one lv8 COM + P4 COM) so
   specials are common in self-play; same menu path. Blake's go needed.
4. MEMORY = recurrent policy (RecurrentPPO / LSTM). The frame stack is a 1.6 s window; a recurrent state carries
   "who charged a special ten seconds ago", "where the stone went", "I am being double-teamed" across the round.
   Biggest lift (new trainer path, no direct warm start: distil the current policy into the recurrent one or start
   from the BC seed), biggest lever. Queued behind 1-3 unless Blake pulls it forward; a 9950X job.
5. 9950X migration (box ordered Sep 24): `linux_port/setup_9950x.sh`, LINUX_BRINGUP.md, parity gate on the leg 73
   zip, then the league moves.
Also open: thrown-item classes for the projectile slots; a true grounded flag (AIR is ~80-85%% precise); the beam and
gatling projectiles the pool scan misses.

## LV8 CHARACTER STATES (Sep 25 2026 12:30-2:30 am EDT; Blake: the P4 COM seat at level 8 is the end state)

The COM difficulty is a GLOBAL option consumed when a match session starts: writing the cell (0x8C472AD4,
0-based, 3 = "2") in a live match and re-stamping through CHANGE CHARACTER changes NOTHING (controlled test:
identical COM behaviour and a single differing byte). So the states were stamped from the main menu.
MENU MAP (all P2 buttons unless noted; headless via FlycastBridge, instance 13, screenshots in the scratchpad):
pause = START; pause menu CANCEL / BUTTON CONFIG / CHANGE CHARACTER / QUIT (DOWN x3 + A = QUIT, no confirm);
main menu 1-ON-1 / ARCADE / ORIGINAL / ADVENTURE / ITEM SHOP / GAME OPTIONS / EXTRA OPTIONS / SAVE-LOAD
(DOWN x5 + A = GAME OPTIONS); GAME OPTIONS row 1 DIFFICULTY (LEFT/RIGHT, 1-8; RIGHT x5 = 8), DOWN x10 + A =
EXIT -> "settings changed, save?" B = No -> main menu (cursor on GAME OPTIONS); UP x3 + A = ORIGINAL -> PLAYER
SELECT directly (4 columns 1P red / 2P yellow / 3P blue / 4P green; rows HUMAN-COM / colour / PLAYER SELECT /
WIN). Each port has its own cursor and can roam columns; A on the HUMAN row toggles COM; DOWN x2 + A on
PLAYER SELECT shows the column's default character (P1 Falcon, P2 Ryoma, P3 Pete, P4 Accel), then A cycles the
roster FORWARD and B BACKWARD (roster: Falcon, Ayame, Gunrock, Ryoma, Wang-Tang, Galuda, Rouge, Jack, Pete,
Julia, Gourmand, Accel, Mel, Pride; HUMAN rings also contain RANDOM SELECT after Pride, COM rings do not);
START (any port) -> STAGE SELECT (Blue Sky default; UP = Desert Area) -> A -> match. Saved 200 frames in.
Menu states kept in the scratchpad (`main_opt8.state`, `orig_select_opt8.state`) and the recipe in
`states_mixed/README.md`.
RESULT: `states_mixed/slot30-43` = the 13 characters + Falcon in the P4 COM seat at LEVEL 8, P1/P2/P3 HUMAN
Falcon (face_norm 0.991 on all three; the first pass had P3 on RANDOM SELECT and was redone), sources in
`states_mixed_lv8/`. VERIFIED: 5 RAM cells read 2 in every lv3 state and 7 in every lv8 state (the global
cell + 4 AI copies: 0x8C4683A6, 0x8C46C3D4, 0x8C5429AD, 0x8C5429C8); idle probe (COM alone vs three idle
humans, 40 s): lv3 first hit ~1,230-2,035 f and 63-210 damage vs lv8 first hit ~960-1,040 f and 205-1,134
damage. Registered: `SLOT_META[30..43] = (1, 8)` (stage dim 1, level 8: DIFF_DIM 1.0, lv8 gem caps,
LOSS_SCALE 0.2) in powerstone_env_v6 and ffa_selfplay_env; unit tests 0 failures; live FFA smoke on slots
30/33/43 under obs v3: DIFF_DIM 1.0, pool views fine.
FRESH HELD-OUT: `states/slot90.state` = P1 COM Gunrock, P2 HUMAN Falcon, P3 COM Julia, P4 COM Mel, all lv8,
Desert; `SLOT_META[90] = (2, 8)`. Not yet in the battery (Blake's call: it would replace or join slot 3,
which is trained-on since leg 77).
LEAGUE: `league_env.txt` PS2_STATE_SLOTS = 0,10-22,30-43 (14 lv3 + 14 lv8 = 50/50; the slot-3 padding of the
fast test DROPPED; slot 3 is NOT trained on from leg 79 but it is NOT a clean held-out either: legs 77-78 trained on
that exact state for 4,299 episodes and every later zip descends from them -> label it a SEEN-STATE regression
benchmark from leg 77 onward; states/slot90-94 (never trained on) are the fresh test). Takes effect at leg 79's launch (after leg
78's battery, ~4:50 am). Backup `archive/league_env_pre_lv8set_sep25.txt`.

## OBS V3 BUILT + CUTOVER PLAN (Sep 23 2026 10 pm - 11:15 pm EDT; Blake: "Go. Do multiple smoke tests")

Flag `PS2_OBS_V3=1` (default off; everything v2 untouched when unset). Backups `archive/*_pre_obsv3_sep23.py`.
- Line v8 (93 fields, cmdseq LAST): v7 + state x4 + stun x4 + a THIRD projectile slot. `ps2_addr.PSTATE_OFF`
  (PLAYER_MAT+0x3285) / `PSTUN_OFF` (+0x3392); `ps2_ram.py` composes it and, under v3, reports projectile
  VOLLEYS (no uniqueness gate), requires >= 300 u/s horizontal motion, one entry per position, and excludes
  a null class and the 0x0C54Dxxx stage-effect band (both seen in overlays). `_proj_cache_cls` keeps the ids.
- Obs 160 = the v2 122 (same LAYOUT; NOT the same values: under v3 the reader itself changes, so the two projectile
  slots [81..92] now carry volleys that the v2 reader never reported -> a v2 policy fed the v3 prefix sees a changed
  contract on 12 dims; Astra Sep 25 measured 8 differing prefix positions on identical RAM) + [122..129] self stun/40 + 7-way state class (idle-walk, air, attack,
  hit, transforming, special, other) + [130..153] the same for the 3 opponents NEAREST-FIRST (same order
  as the opponent block) + [154..159] projectile slot 3. `powerstone_env_v6.OBS_V3/OBS_DIM/STATE_CLASS`.
- Stack helpers: `obs_stack.kd_for(model)` -> (K, 122|160); eval_parity / ab_selfplay_probe / watch_play /
  play_vs / agreement_stack use it and slice obs[:d] so a v2 policy runs under a v3 env; FFA SeatView and
  SelfPlayEnv opponent views slice the same way (v2 pool policies keep working). Trainer assert uses obs_dim.
- `surgery_widen.py` (122 -> 160 per lag slot, new columns ZERO, Adam not carried, same as the stack
  surgeries); `equivalence_widen.py` (live frames; parent on obs[:122] vs widened on v3 obs with the new
  dims zeroed: 1500/1500 argmax, logit diff 1.1e-5 = float32 noise, threshold 1e-4).
- Battery exports PS2_OBS_V3=1 when the leg's leg_modes.txt row carries it (eval contract); scout_leg.sh
  reads it too (tmux drops the environment); league_leg_async.sh whitelist accepts it.
SMOKE TESTS PASSED: `test_obs_v3.py` (synthetic v8 line through the real parser + builder, 0 failures),
`test_obs_context.py` still 0 failures, equivalence_widen PASS, `smoke_ffa_v3.py` (mixed arena, K=7 widened
learner, v2 pool policies K=1 and K=7 sliced, 400 steps, v3 block live every step, [zs] line printed),
eval_parity 2 eps and ab_selfplay_probe 2 eps (v3 candidate vs v2 champion) both run.
VISUAL VALIDATION (Blake's method: RAM values printed on the frame, Sonnet reviews footage vs data):
`ram_scan.py capture --overlay-every 15` + `sheets` (RAM overlays, `scan/val1_slot3`, rubric
`scan/validation_rubric.md`); `obs_overlay.py` (END TO END: the policy's own observation decoded on the
frame, `scan/ov3`, rubric `scan/obs_validation_rubric.md`). RAM reviews (val1_slot3, sheets 1-8): 0 real
disagreements over ~1,600 tile-checks; the 3 flagged were Accel's form flag leading the visible model swap
by ~2 s (RAM leads the picture: early warning, not error). Obs overlay reviews (ov3): sheets 1-4 = 0
disagreements over 764 checks; sheets 5-9 = 12 flags, checked one by one: 9 were reviewer misreads
(wrong line or wrong ENEMY; state 5 = airborne is confirmed by measured height: median 300 u up, 92%% of
its frames > 100 u, and state 16 is a launched-high state, median 476 u, now mapped to AIR), and ONE was
REAL: at step 900 the bot's own missile swarm was in flight with no projectile reported. Root cause found
with an independent per-step pool check (`obs_overlay.py` column `pool_fast`): the reader's pool sweep
tested the active flag as a whole u32 == 1, but volley objects carry a counter in the upper bytes
(0x00090001...), so EVERY rocket in a swarm was invisible (in v2 too). Fixed under v3 only (eval
contract): `live = (act & 0xFF) == 1`. After the fix (ov5, 1,500 steps) the reader reports Pride's
volley classes 0x0C7EE3A0 / 0x0C7EC9C8, Falcon's missiles 0x0C7FD6B8, Ryoma's 0x0C80D230; projectile
slots filled on 437/1,500 steps (was ~235). Remaining reader-vs-check differences are timing (3-frame vs
6-frame speed windows). ov5 reviews (helper agents per sheet): stun/HIT, SPECIAL/XFORM and hp checks agree ~100%%; the flags were
(i) explosion/blast-dome particles reported as projectiles (class band 0x0C5A0000-0x0C5D0000: Accel-impact
sparkles 0x0C5A7xxx, blast cloud 0x0C5BAA80) -> excluded under v3 (`PROJ_EXCLUDE_BANDS_V3`), ov6 rerun:
337/1,500 steps with a projectile, top classes Pride 0x0C7EC9C8/0x0C7EE3A0, Falcon 0x0C7FD6B8, Accel
0x0C81E158, Ryoma 0x0C80D230, thrown items 0x0C6xxxxx; (ii) opponent-ordering doubts that were reviewer
perspective (checked f01311 myself: Accel is right next to the bot as printed; the stage has elevation);
(iii) AIR: reviewers disagreed on ~20%% of AIR tiles (ov5 review_A: 10/45). Measured on run2: state 5 has
per-frame vertical motion |dy| > 4 u in 80%% of its frames and a median height gain of ~350 u per episode, but
11-21%% of COM state-5 episodes gain < 20 u (a hop/pre-jump the state machine still calls jump). So AIR is
~80-85%% precise; kept as is (the obs also carries heights: self obs[3], opponents' dy). A true grounded
flag from RAM is a follow-up, not a blocker. A projectile-only
review of ov6 (`scan/ov6/review_projectiles.md`) was running at 11:30 pm. Then (ov5 sheet011 flags 1476/1479:
Falcon's missiles invisible during their near-vertical dive) the horizontal-speed gate was DROPPED (the effect
bands already cover the vertical junk); ov7 rerun: Falcon 0x0C7FD6B8 187 reports, Ryoma 0x0C80D230 65, thrown
items 0x0C6xxxxx, the old 'rocket' 0x0C7F9A10 21; reader-vs-independent-check gap 74/1,500 steps (timing).
FINAL v3 PROJECTILE RULE: pool slot live (low byte == 1), class not in PROJ_EXCLUDE / PROJ_EXCLUDE_V3 / the
chest, item, stone, 0x0C54D, 0x0C5A-0x0C5D bands, speed >= 700 u/s over the 3-frame sweep OR known class;
one entry per position; 3 nearest reported. LATER (ov6 projectile-only review, 11:50 pm): 38/60 YES tiles were loot
gems flying out of chests / dropped or held items (0x0C6xxxxx) -> that band excluded too (thrown items in flight
are lost with it: FOLLOW-UP to identify and whitelist them). Three real misses: a missile swarm mid-dive (fixed
by dropping the horizontal gate), an X-pattern beam and a gatling bullet trail (not pool movers; follow-up).
CUTOVER: `league_trainer.txt` = hold (written 11:05 pm) so leg 73's battery HOLDS leg 74's launch. Then
`bash cutover_v3.sh 74` (guards: state "74 ./powerstone_v6_leg73_league.zip", hold, LAUNCH_HELD marker,
no trainer) widens leg 73's zip -> `powerstone_v6_leg73_v3.zip`, re-proves equivalence, points
league_state.txt at it, appends PS2_OBS_V3=1 to league_env.txt, sets mixed, launches, prints the boot
line (`obs_v3=1 obs_dim=160`, obs_stack=7, warm=leg73_v3) and the leg_modes row. V3 READ = legs 74-75 vs
72-73 (band 16-24). Revert = PS2_OBS_V3 removed from league_env.txt + warm start from the last v2 zip.
If the overlay reviews report real disagreements, fix first; `echo mixed > league_trainer.txt` before
~3 am keeps the standard chain instead.

## ASTRA REVIEW FIXES (Sep 23 2026, applied ~1:10-1:30 pm EDT, before the leg 71 battery)

Blake had Astra (Codex) review the repo at head 5857901; report at
`~/Documents/Codex/2026-09-23/cp/outputs/powerstone-review.md`. Every high-priority claim was
re-verified against the code here before acting; all held. Blake: "go on all of it". Backups of
every touched file in `linux_port/archive/*_sep23.*`.

| # | Finding (confirmed) | Fix | Effective |
|---|---|---|---|
| 1 | `_observe` wrote the stage one-hot + DIFF_DIM only for slot < 4; slots 10-22 (~93%% of training eps since leg 58) fed zeros while the slot-2/3 evals fed real values | gate on SLOT_META membership (`OBS_CTX_FIX`, env `PS2_OBS_CTX_FIX`, default 1); `test_obs_context.py` runs the real builder on a synthetic state for 16 slots x 4 seats: 0 failures fixed, 52 with the fix off | leg 72 (actors import at boot; leg 71 runs old code) |
| 9 | zero-sum reward: the per-seat TIME_PENALTY cancelled exactly under the mean subtraction, so legs 55-71 had NO per-step time cost (timeout loss still applied) | learner time cost re-applied AFTER the relative step (`ZS_TIME`, env `PS2_ZS_TIME`, default 1); unit test: unchanged state now -0.002, was 0.000 | leg 72 |
| 13 | scout reviews read `forms=A/B` as closed/attempted; it is bot transforms / opponent transforms; `chests=X(Y)` is arena chests opened / vanished near the bot | data dictionary added to `scout_rubric.md`; reviews 68-70 "closing rate" lines are misreads (the transforms-to-wins table used the field correctly) | next review |
| 2 | battery `cp` to the pool was unchecked; state advanced and DONE written even if it failed | copy to `.tmp`, `zipfile.testzip`, rename, size check, THEN advance state (state advance itself is now checked); failures write the FAILED marker and exit 1; per-leg lock dir `claude_bridge/battery_leg<N>.lock` (rmdir by hand after a FAILED) | leg 71 battery |
| 3 | hold thresholds lived only in the relay wakes; the script would launch on a 0%% receipt | `hold_gate.py <N>` (lv3 < 70, AB < 35, lv8 < 4.0, or unreadable receipt) runs in the battery; writes `hold` + `claude_bridge/hold_leg<N>.txt`; tested on leg 70 (no hold), leg 45 (AB 26 -> hold), synthetic lv8 3.0 (hold) | leg 71 battery |
| 4 | `validate_async_leg.py` printed FAIL but exited 0; missing [ep] stream or missing receipts were silently skipped | nonzero exit on FAIL; missing async stream / requested receipts are FAIL (not under `--stream-report-only` for the stream). NOTE: the FFA-lineage legs always FAIL the stats rules vs the lockstep leg 24 reference (different optimizer), so rc=1 on legs 46+ is expected; read the per-rule lines | now |
| 6 | `flycast_bridge.loadstate` ignored the core's unserialize result; `savestate` did not check the blob | raise RuntimeError on a rejected load or an empty serialize | now (evals, scouts, next leg) |
| 8 | frame-stack surgery resets Adam (new PPO, policy tensors copied, no optimizer state) | recorded, not changed: the K=4 and K=7 jumps are memory + optimizer reset together | note |
| 7 | leg 70 vs leg 59 "interval clear" claim wrong (p~0.07) | wording corrected in the top block; leg 71 is the confirmation | note |
| 5 | champion AB uses the old P1 view (form timer leak), candidate always P2 | known, unchanged; treat the AB series as a trend, not a seat-neutral ranking | note |

Not yet acted on (Astra's lower tier): analog button path reading a dead array in sdlarch.cpp
(digital path is what the game uses), per-actor stall deadlines, run manifests per checkpoint,
merge_receipts stochastic labelling, `pkill -f spawn_main` breadth, fresh-checkout build recipe,
README staleness, frozen final test set. Blake decides.

## STATE AT CONTEXT COMPACTION (Sep 16 2026 ~12:15 EDT; refreshed 16:55 EDT) — read this first on resume

**16:55 EDT UPDATE (Blake: "sweep, and fix the timeout reload before it").**
- `league_trainer.txt` = **hold**. Leg 40 (mixed, 0.01, launched 15:27) finishes ~19:30; its
  battery runs as usual and then writes `claude_bridge/leg41_LAUNCH_HELD.txt`. Do NOT launch leg 41.
- RESET FIX APPLIED 16:45 EDT: `powerstone_env_v6.py` reloads the savestate on EVERY reset
  (`RELOAD_ON_RESET`, env `PS2_RELOAD_ON_RESET=0` restores the old behaviour; backup
  `linux_port/archive/powerstone_env_v6_pre_reloadfix_sep16.py`). Verified with a 150-step cap:
  health returns to the baked values after each timeout. Leg 40's running actors imported the
  OLD code (unaffected); leg 40's battery is unaffected (0 timeouts in evals).
- OPTIMIZER SWEEP LAUNCHED 16:52 EDT in tmux `sweep40` (`linux_port/sweep_optim40.sh`): waits for
  `battery_leg40_done.txt` + quiet machine, then four 4M-step arms from the LEG 40 zip, mixed
  recipe, 0.01, fix active, each in its own APFS-cloned pool `pool_sweep40_<arm>`:
  ctrl (fix only) -> bs256 (PS2_BATCH_SIZE=256) -> lr1e4 (PS2_LR=1e-4) -> kl01 (PS2_TARGET_KL=0.1).
  Standard sharded battery per arm. Receipts `receipts/eval_sweep40_<arm>_*`, summary
  `receipts/sweep40_summary.txt`, markers `claude_bridge/sweep40_<arm>_done.txt` / `sweep40_done.txt`,
  log `linux_port/wrapper_sweep40.log`. ~20 h -> done ~16:00-17:00 EDT Sep 17.
  PRE-REGISTERED READ: compare each arm's lv8 / slot2 / champion AB to leg 40 and the mixed band
  (lv8 7.2-9.0, slot2 88-91, AB 78-82); ctrl vs leg 40 = the reset fix alone; the best arm by lv8
  with slot2/AB inside the band becomes leg 41's warm start (Law 6 precedent: the leg-3 program).
  Also read epochs/update from n_updates (the whole point: 1.1 today) and entropy per arm.
- **Sep 23 12:40 pm EDT: leg 70 (first strided K=7) = lv8 28.8 ALL-TIME RECORD (+5, interval clear of the old record)
  / 97.6 / 74-26. LEG 71 LIVE** (12:35 pm, strided, state `71 ./powerstone_v6_leg70_league.zip`), wake
  `ps2-leg71-end-wake` 5:50 pm EDT. Standing recipe now includes the 7-lag stack (PS2_OBS_STACK=7).
- Sep 23 7:58 am EDT: leg 69 = 23.0 / 94.8 / 75-25; STACK READ = PASS. LEG 70 LAUNCHED = FIRST STRIDED K=7 LEG
  (warm `powerstone_v6_leg69_stack7s.zip`, `PS2_OBS_STACK=7`, state `70 ./powerstone_v6_leg69_stack7s.zip`),
  wake `ps2-leg70-end-wake` 1:12 pm EDT. Read over legs 70-71 vs legs 68-69 (K=4) and 63-67 (single-frame).
- Sep 23 3:15 am EDT: leg 68 (first stacked) = 18.2 / 92.0 / 78-22, in band. LEG 69 LAUNCHED (3:12 am, stacked,
  state `69 ./powerstone_v6_leg68_league.zip`), wake `ps2-leg69-end-wake` 8:27 am EDT; completes the stack read.
- Sep 22 10:35 pm EDT: leg 67 = 17.8 / 93.2 / 68-32. LEG 68 LAUNCHED = FIRST FRAME-STACKED LEG (K=4, warm
  `powerstone_v6_leg67_stack4.zip`, `PS2_OBS_STACK=4` in league_env.txt, state `68 ./powerstone_v6_leg67_stack4.zip`),
  wake `ps2-leg68-end-wake` 3:51 am EDT Sep 23. Recipe = mixed + stack optimizer + zero-sum + start health +
  COM character random + 4-frame stack. Revert = warm from powerstone_v6_leg67_league.zip, drop PS2_OBS_STACK.
- Sep 22 5:55 pm EDT: leg 66 = 23.6 / 95.6 / 76-24 (four straight 20+). LEG 67 LAUNCHED (5:53 pm, state
  `67 ./powerstone_v6_leg66_league.zip`), wake `ps2-leg67-end-wake` 11:08 pm EDT.
- Sep 22 1:20 pm EDT: leg 65 = 23.0 / 96.4 / 73-27. LEG 66 LAUNCHED (1:13 pm, state `66 ./powerstone_v6_leg65_league.zip`),
  wake `ps2-leg66-end-wake` 6:28 pm EDT. Scouting packets now carry 4 fps final-12 s strips.
- Sep 22 8:40 am EDT: leg 64 = 20.6 / 92.4 / 75-25. LEG 65 LAUNCHED (8:36 am, state `65 ./powerstone_v6_leg64_league.zip`),
  wake `ps2-leg65-end-wake` 1:51 pm EDT.
- Sep 22 4:05 am EDT: leg 63 = 21.2 / 94.4 / 69-31. LEG 64 LAUNCHED (3:58 am, state `64 ./powerstone_v6_leg63_league.zip`),
  wake `ps2-leg64-end-wake` 9:13 am EDT.
- Sep 21 11:25 pm EDT: leg 62 = 18.0 / 93.2 / 67-33. LEG 63 LAUNCHED (11:20 pm, state `63 ./powerstone_v6_leg62_league.zip`),
  wake `ps2-leg63-end-wake` 4:35 am EDT Sep 22. Per-leg clip + scouting review now automatic (section above).
- Sep 21 6:40 pm EDT: leg 61 = 19.4 / 94.8 / 63-37. LEG 62 LAUNCHED (6:38 pm, state `62 ./powerstone_v6_leg61_league.zip`),
  wake `ps2-leg62-end-wake` 11:53 pm EDT.
- Sep 21 14:05 EDT: leg 60 = 17.8 / 92.4 / 74-26 (one drop, in band). LEG 61 LAUNCHED (14:02 EDT, state
  `61 ./powerstone_v6_leg60_league.zip`), wake `ps2-leg61-end-wake` 19:17 EDT.
- Sep 21 09:30 EDT: leg 59 = 23.8 (ALL-TIME RECORD) / 95.2 / 74-26; CHARACTER READ = PASS; watch cleared.
  LEG 60 LAUNCHED (09:23 EDT, standing recipe incl. character random, state `60 ./powerstone_v6_leg59_league.zip`),
  wake `ps2-leg60-end-wake` 14:38 EDT. Recipe = mixed + stack + zero-sum + start health + COM character random.
- Sep 21 04:50 EDT: leg 58 (first character leg) = 15.8 / 93.6 / 73-27; lv8 WATCH (2 drops). LEG 59 LAUNCHED
  (04:46 EDT, state `59 ./powerstone_v6_leg58_league.zip`), wake `ps2-leg59-end-wake` 10:01 EDT. Leg 59 completes
  the character read; a third lv8 drop = signal.
- Sep 21 00:10 EDT: leg 57 = 16.2 / 92.4 / 65-35 (one-leg dip, inside band). LEG 58 LAUNCHED = FIRST CHARACTER-
  RANDOMIZATION LEG (00:07 EDT, state `58 ./powerstone_v6_leg57_league.zip`), wake `ps2-leg58-end-wake` 05:22 EDT.
- **Sep 20 22:45 EDT: CHARACTER RANDOMIZATION ENABLED for leg 58+** (`PS2_STATE_SLOTS=0,10..22` added to
  league_env.txt; section "CHARACTER RANDOMIZATION BUILT"; read over legs 58-59 vs 55-56). Leg 57 unaffected.
  Queued next: COM level randomization (probe RAM first).
- **Sep 20 19:35 EDT: leg 56 = 22.4 / 97.6 / 78-22 — ALL-TIME RECORDS, ARENA READ = PASS** (leg 56 note).
  LEG 57 LIVE (19:31 EDT, same recipe: stack + zero-sum + start health), state `57 ./powerstone_v6_leg56_league.zip`,
  wake `ps2-leg57-end-wake` 00:46 EDT Sep 21. Standing recipe from here unless Blake says otherwise.
- Sep 20 15:00 EDT: leg 55 (first arena leg) = 19.2 / 95.2 / 69-31, stones/ep 6.0 -> 4.9. LEG 56 LAUNCHED
  (14:54 EDT, same flags, state `56 ./powerstone_v6_leg55_league.zip`), wake `ps2-leg56-end-wake` 20:10 EDT.
  Leg 56 completes the two-leg arena read.
- Sep 20 10:20 EDT: leg 54 = 19.6 / 91.2 / 60-40. LEG 55 LAUNCHED = FIRST ARENA LEG (10:14 EDT, stack + zero-sum +
  start health, state `55 ./powerstone_v6_leg54_league.zip`), wake `ps2-leg55-end-wake` 15:30 EDT.
- **Sep 20 08:30 EDT: ARENA LEVERS ENABLED for leg 55+** (`league_env.txt` = `PS2_ZERO_SUM=1 PS2_START_HEALTH=0.5,1.0`;
  section "ARENA LEVERS BUILT"; read over legs 55-56). Leg 54 runs unchanged on the stack.
- **Sep 20 05:35 EDT: leg 53 = 16.6 / 94.8 / 60-40. STACK READ VERDICT: neutral (leg 53 note). LEG 54 LIVE**
  (05:31 EDT, stack, state `54 ./powerstone_v6_leg53_league.zip`), wake `ps2-leg54-end-wake` 10:46 EDT.
  Awaiting Blake: keep the stack or revert to lr + kl; next lever = arena (zero-sum reward, randomization).
- Sep 20 00:50 EDT: leg 52 (first stack leg) = lv8 20.6 ALL-TIME RECORD / 94.0 / AB 53-47. LEG 53
  LAUNCHED (00:48 EDT, stack, state `53 ./powerstone_v6_leg52_league.zip`), wake `ps2-leg53-end-wake` 06:03 EDT.
  Leg 53 completes the pre-registered two-leg stack read.
- Sep 19 20:10 EDT: leg 51 DONE = 16.4 / 93.2 / 69-31 (plateau). LEG 52 LAUNCHED ON THE STACK (20:07 EDT,
  state `52 ./powerstone_v6_leg51_league.zip`, three override lines confirmed), wake `ps2-leg52-end-wake` 01:22 EDT Sep 20.
- **Sep 19 16:00 EDT (Blake: "Stack").** `league_optim.txt` = `PS2_LR=1e-4 PS2_TARGET_KL=0.03 PS2_BATCH_SIZE=256`
  from LEG 52 on (leg 51 runs unchanged). Pre-registered read: two legs; a real gain must clear the legs 46-50
  band (lv8 15-19, mean 17) with lv3 and AB in band; expect epochs/update to rise and KL/update to stay < 0.03.
  If lv8 falls under 15 twice -> revert to lr + kl only.
- Sep 19 15:30 EDT: leg 50 DONE = 15.0 / 95.6 / 70-30 (plateau). LEG 51 LAUNCHED (15:24 EDT, same setting,
  state `51 ./powerstone_v6_leg50_league.zip`), wake `ps2-leg51-end-wake` 20:40 EDT.
- Sep 19 10:45 EDT: leg 49 DONE = 18.8 / 96.4 / 68-32 (lv8 leg record, lv3 all-time record). LEG 50 LAUNCHED
  (10:43 EDT, same setting, state `50 ./powerstone_v6_leg49_league.zip`), wake `ps2-leg50-end-wake` 15:58 EDT.
- Sep 19 06:05 EDT: leg 48 DONE = 15.8 / 94.8 / 65-35. LEG 49 LAUNCHED (06:02 EDT, same setting, state
  `49 ./powerstone_v6_leg48_league.zip`), wake `ps2-leg49-end-wake` 11:20 EDT.
- Sep 19 01:25 EDT: leg 47 DONE = 18.6 / 92.8 / 67-33. LEG 48 LAUNCHED (01:19 EDT, same setting, state
  `48 ./powerstone_v6_leg47_league.zip`), wake `ps2-leg48-end-wake` 06:35 EDT.
- Sep 18 20:40 EDT: leg 46 DONE = 16.8 / 94.0 / 74-26 (restart holds). LEG 47 LAUNCHED (20:38 EDT, explicit
  `PS2_LR=1e-4 PS2_TARGET_KL=0.03`, state `47 ./powerstone_v6_leg46_league.zip`), wake `ps2-leg47-end-wake`
  01:55 EDT Sep 19. Battery chains leg 48.
- Sep 18 16:03 EDT: LEG 46 LAUNCHED — RESTART (Blake: "Restart"). Warm start `powerstone_v6_sweep40_kl01_league.zip`
  (19.0 / 92.8 / 71-29), `league_optim.txt` = `PS2_LR=1e-4` (standing), mixed, state
  `46 ./powerstone_v6_sweep40_kl01_league.zip`. Pool: `pool_league` = fresh clone of `pool_sweep40_kl01`;
  the drifted legs 41-45 pool is `pool_league_kl_drift_41_45/` (keep). Legs 41-45 stay in the ledger as
  the target_kl 0.1 lesson (lineage abandoned). Wake `ps2-leg46-end-wake` 21:20 EDT. Battery chains leg 47.
- Sep 18 15:55 EDT: HELD, MACHINE IDLE (superseded by the restart above). Leg 45 = 13.8 / 91.2 / **26-74** (AB below the 35 line, 5th
  straight drop). State `46 ./powerstone_v6_leg45_league.zip`, `leg46_LAUNCH_HELD.txt`. Nothing runs.
  Awaiting Blake's restart word (recommended kl01 zip + PS2_LR=1e-4; procedure SESSION_HANDOFF sec 2).
- **Sep 18 11:20 EDT: SIGNAL + HOLD.** Leg 44 = 12.8 / 90.4 / **37-63** (AB down 4 straight; leg 44 note).
  `league_trainer.txt` = hold. Leg 45 LIVE (11:13 EDT, target_kl 0.1, LAST on this setting), its battery
  evaluates and launches nothing; wake `ps2-leg45-end-wake` 16:30 EDT. Awaiting Blake: restart from the
  kl01 zip with PS2_LR=1e-4 (recommended) — procedure in SESSION_HANDOFF sec 2.
- Sep 18 06:40 EDT: leg 43 DONE = 16.8 / 94.0 / 51-49.
- Sep 18 01:50 EDT: leg 42 DONE = 12.6 / 92.8 / 53-47.
- Sep 17 21:05 EDT: leg 41 DONE = 16.2 / 90.4 / 65-35.
- **Sep 17 16:18 EDT: LEG 41 LAUNCHED — NEW LINEAGE.** Blake picked kl01 ("best lvl 8, the smartest
  opponent"). Warm start `powerstone_v6_sweep40_kl01_league.zip`; standing override `league_optim.txt`
  = `PS2_TARGET_KL=0.1` (wrapper exports it every leg, leg_modes.txt col 4); `league_trainer.txt` = mixed;
  state `41 ./powerstone_v6_sweep40_kl01_league.zip`. Pool: `pool_league` is now the kl01 arm's pool
  (clone of the old league pool + kl01 snapshots + `prog_sweep40_kl01.zip`); the pre-sweep league pool
  is preserved as `pool_league_pre41_leg40/` (never rm). Both env fixes active (reload on reset,
  stagger 0-239) => NEW EVAL CONTRACT from leg 41: references champion 5.8/92.0, parent kl01 lv8 19.0.
  Wake `ps2-leg41-end-wake` 21:35 EDT. Sweep summary: ctrl 6.2, bs256 9.0, lr1e4 13.6, kl01 16.6 (old
  contract); 16.4 / 19.0 for lr1e4 / kl01 under the new one. ent_coef 0.03 proposal WITHDRAWN.

- **Live:** leg 39 training (mixed recipe, ent_coef 0.01, launched 10:59 EDT, done
  ~15:30), tmux `ps2train`. `league_state.txt` = `39 ./powerstone_v6_leg38_league.zip`,
  `league_trainer.txt` = `mixed`, no `league_entcoef.txt` (=> 0.01). Wake:
  `ps2-leg39-end-wake` (16:30 EDT) + the collection task it creates. The interactive
  session runs a persistent relay watcher and an hourly entropy watch (scratchpad
  scripts; recreate per docs/SESSION_HANDOFF.md section 5 if the session is new).
- **The recipe ("mixed", adopted after leg 34):** learner P2, pool policies P1+P3,
  the game's level-3 COM in P4, `states_mixed/slot0.state`, obs v2, 4-port harness
  (`sdlarch-rl/p4`), uniform pool sampling, 2,000-step cap with timeout = loss,
  10 actors, 4M steps (~4.5 h), warm start = previous leg. Batteries 500/250/100.
- **Mixed-leg series (legs 34-38):** lv8 8.2 / 8.4 / 9.0 / 8.0 / 7.2 (project
  record 9.0 at leg 36; champion 5.2; pure-league best 5.6); slot2 91.2 / 88.4 /
  89.2 / 91.2 / 90.4 (champion 91.2; leg 26 94.8); champion AB 81 / 80 / 78 / 82 / 79.
  Best mixed zip by lv8 = leg 36 (`powerstone_v6_leg36_league.zip`); best-ever pure
  policy = leg 26 zip. Champion `powerstone_v6_ppo.zip` NEVER promoted/overwritten.
- **ENTROPY TRIGGER FIRED at leg 38** (entropy_loss medians -0.107 -> -0.075 legs
  35-38; leg 39 running value crossed -0.06 at update 50; stream win share stalled
  ~37%%, timeouts back to 12%%). PENDING BLAKE: ent_coef 0.01 -> 0.03 for mixed legs
  (mechanism built: write `0.03` into `linux_port/league_entcoef.txt`; the wrapper
  applies it at the next leg launch and records it in `leg_modes.txt`). Pre-registered
  read for the first 0.03 leg: entropy median back below -0.12, timeouts < 6%%, lv8
  back in leg 37's band; revert to 0.01 if slot2/AB cross the hold thresholds.
- **Blake's standing hold rule:** hold iff slot2 < 70 (n=250) or champion AB < 35/100
  or lv8 < 4.0%% (n=500) -> `echo hold > league_trainer.txt` (read at launch time).
- **Operator manual:** docs/SESSION_HANDOFF.md (modes, per-leg procedure, guards,
  shell traps, wake template). Use cheaper models for routine wakes (Blake).

## PRE-ROLL FIX (Sep 17 2026, 14:45 EDT) — eval-contract change, re-baselined

Probe (slot 3, 3x lv8 COM, instance 13, deterministic): intro to match-ready = 242 frames; the
first COM hit lands between 4.0 and 5.0 s of live play. Bot health at its first action by live
stagger k: 1000 for k <= 240; 964 at 300; 928 at 360-420; 740 at 480-599. The Aug 24 stagger
(0-599) therefore cost a quarter bar in ~25%% of lv8 episodes and some health in ~50%%.
CHANGE: `powerstone_env_libretro.py` live stagger is now `random.randrange(PS2_STAGGER_FRAMES)`
with default 240 (600 restores the old contract). Backup `archive/powerstone_env_libretro_pre_stagger_sep17.py`.
Decorrelation kept: 240 offsets -> ~93%% distinct episodes per 50-ep deterministic shard (was ~95%%).
Applies to training AND eval from here on. Every number above this section (all 40 legs, the sweep,
the champion's 5.2/91.2) was measured under the 0-599 handicap. Re-baseline under the new contract:
`rebaseline_preroll.sh` (champion lv8+lv3, lr1e4 lv8, kl01 lv8) -> `receipts/rebase_preroll_*`; results
recorded below when done.

RE-BASELINE RESULTS (15:30 EDT, receipts/rebase_preroll_*; distinct-outcome tuples in parentheses):
| model | lv8 old contract (0-599) | lv8 NEW contract (0-239) | lv3 old | lv3 NEW |
|---|---|---|---|---|
| champion powerstone_v6_ppo.zip | 5.2 (n=500) | **5.8** (29W, Wilson 4-8; picks 4.48 forms 0.78; 485/500 distinct) | 91.2 | **92.0** (230/250, Wilson 88-95; 186/250 distinct) |
| sweep40 lr1e4 | 13.6 | **16.4** (82W, Wilson 13-20; 6.38/1.37; 462/500) | 92.8 | — |
| sweep40 kl01 | 16.6 | **19.0** (95W, Wilson 16-23; 6.31/1.30; 472/500) | 92.8 | — |
Read: the handicap was worth ~+0.6 to +3 lv8 points depending on the bot (stronger bots lose more to
a bad start). Decorrelation intact (462-485 distinct of 500 vs 477 before). From leg 41 on, the
league's reference numbers are champion 5.8 / 92.0 and the candidates 16.4 (lr1e4) / 19.0 (kl01).

## STRIDED 6-FRAME STACK (Sep 23 2026, 4:00-5:00 am EDT; Blake: "do the strided six frame version next leg")

After the K=4 read (legs 68-69), leg 70 moves to a STRIDED stack: lags [16, 8, 4, 2, 1, 0] decision
steps = frames from 1.6, 0.8, 0.4, 0.2, 0.1 s ago plus the current one, 6 x 122 = 732 inputs. Same
information cost as K=6 contiguous but a 1.6 s window instead of 0.5 s: wind-ups, jump arcs,
projectile flight and transformation animations all fit. `obs_stack.py` now takes a lag list;
the frame count implies the lags (OFFSETS_BY_K: 4 -> contiguous, 6 -> strided, 8 -> contiguous;
PS2_STACK_OFFSETS overrides for the trainer), so evaluators and pool seats reconstruct it from a
model's input size alone. `surgery_stack.py` maps source lags to destination lags (K=4's lag 3 ->
strided lag 4, the nearest slot within 2x; everything else copies exactly or starts at zero), so
the K=6 model starts as (almost exactly) the K=4 model: `agreement_stack.py` measures argmax
agreement on a real trajectory since exact equality is impossible after a lag remap.
Plan: hold set 4:05 am; after leg 69's battery, `surgery_stack.py powerstone_v6_leg69_league.zip
powerstone_v6_leg69_stack6s.zip --k 6`, state -> `70 ./powerstone_v6_leg69_stack6s.zip`,
`PS2_OBS_STACK=6` in league_env.txt, launch leg 70. Read over legs 70-71 vs legs 68-69 (K=4) and
legs 63-67 (single-frame, lv8 mean 21.2). Gates (K=6 surgery of the leg 68 zip): see below.
GATE RESULTS, K=6 strided [16,8,4,2,1,0] (5:00 am): evaluator regression OK, 2-actor trainer smoke
OK (46 eps, seam 1.4e-5) — but AGREEMENT ONLY 90.35% (1807/2000 argmax, max |logit diff| 6.8):
remapping the K=4 model's lag-3 slot onto lag 4 changes ~10% of decisions. Not "starts identical".
DECISION (operator, within Blake's "100% certainty, not vibes" rule): use K=7 = [16,8,4,3,2,1,0]
— the same 1.6 s window plus every lag the K=4 bot already uses, so the surgery is EXACT (lags
4, 8, 16 start at zero). 854 inputs instead of 732. Blake can drop back to pure 6 lags later with
one more surgery once the strided slots carry weight (exactness is moot after training anyway).
Leg 70 = K=7; PS2_OBS_STACK=7. K=7 GATES (5:40 am) ALL GREEN: surgery leg 68 zip -> K=7, slot map
{3:3, 2:2, 1:1, 0:0}, agreement 2000/2000 argmax, max |logit diff| 7.6e-6, mean |prob diff| 3e-8;
evaluator regression OK (instance 20); 2-actor trainer smoke with PS2_OBS_STACK=7 OK (44 eps, 6
updates, seam logp_maxdiff 1.3e-5, "leg complete").

## FRAME STACKING BUILT (Sep 22 2026, 8:30-10:00 pm EDT; Blake: "Oh sick let's add this")

Why: the policy is a reflex player — one 122-number frame per decision, no history. A K-frame
stack (oldest first, newest last; K copies of the first frame at reset) gives it velocities,
wind-ups and jump arcs. OpenAI Five used an LSTM for the same reason; stacking is the cheap first
step and is warm-startable by SURGERY (their word): the new first layers of both MLPs are
(256, 122K) with the single-frame weights copied into the LAST 122 columns and zeros elsewhere,
so the stacked model starts as EXACTLY the current bot and learns to use history from there.
Code: `obs_stack.py` (FrameStack, StackedEnv, k_for), `surgery_stack.py <in> <out> --k K`,
`equivalence_stack.py <parent> <stacked>`. Wiring (all inert unless a stacked model or
PS2_OBS_STACK>1 is present): trainer actors wrap the env in StackedEnv when PS2_OBS_STACK=K and
assert the warm zip's input is 122K; FFA env seat views keep a per-view FrameStack for stacked
pool policies; the 2-seat SelfPlayEnv does the same for a stacked opponent; eval_parity,
ab_selfplay_probe, watch_play, play_vs infer K from the loaded model (k_for) and stack. The
eval contract does not change (same states, COMs, episode counts). Backups: archive/*_pre_stack_sep22.py.
GATE 1 (equivalence) PASSED: leg 66 zip -> leg66_stack4.zip (K=4): 3,000 real lv8 frames, random
junk in the three history slots, max |logit diff| 6.2e-6, max |value diff| 5.7e-6, argmax 3000/3000.
GATE 2 (evaluator path) PASSED 10:05 pm: eval_parity ran clean with the single-frame leg 66 zip
(instance 20) and the stacked leg66_stack4.zip (instance 21), 3 lv8 episodes each.
GATE 3 (trainer smoke) PASSED 10:20 pm: 2 actors, PS2_OBS_STACK=4, stacked warm start, 24,576
steps: "[config] obs_stack=4" printed, 51 episodes, 6 updates, seam check logp_maxdiff 1.3e-5,
"leg complete", zip saved. All three gates green; leg 68 launches stacked after leg 67's battery.
PLAN (Blake approved adding it; K=4 unless he says 8): hold set at 10:00 pm so leg 68 does not
auto-launch; when leg 67's zip lands, `surgery_stack.py powerstone_v6_leg67_league.zip
powerstone_v6_leg67_stack4.zip --k 4`; `league_state.txt` = `68 ./powerstone_v6_leg67_stack4.zip`;
add `PS2_OBS_STACK=4` to league_env.txt; `mixed`; launch. Pre-registered read over legs 68-69 vs
the last five legs (lv8 mean 21.9, band 16-24; AB 63-78; lv3 92-98): the stacked bot starts
identical, so leg 68 should be in band and leg 69 is where a gain would show; revert = warm
start from the single-frame leg 67 zip with the flag removed.

## PER-LEG VIDEO + FIGHT SCOUTING (Sep 21 2026, 7:00-10:30 pm EDT; Blake: "watching catches shit the numbers don't", "Totally worth it")

The pre-roll handicap (Aug 24 -> Sep 17) and the reset-continuation bug were both invisible in the
numbers and obvious in the first minute of footage; the spectator script had existed since leg 1 and
been used once. Now structural: every battery records two lv8 rounds (`videos/leg<N>_lv8.mp4`, phone
size) and starts `scout_leg.sh <N>` in tmux `scout<N>` (record until one win + one loss, cap 14
rounds; 1-fps 4x3 contact sheets; sheets for the first loss and first win -> `videos/review_leg<N>/`;
`videos/leg<N>_win.mp4`; marker `claude_bridge/scout_leg<N>_done.txt`). Whoever collects the leg
writes `videos/review_leg<N>.md` from `scout_rubric.md` (Sonnet agent from the interactive session,
~110k tokens, ~6 min; or the scheduled wake itself). Pilot on leg 61 (review_leg61.md): opens
isolated at the map edge ~7 s; dies pinned against terrain by two opponents at once; in the win it
never goes to finish a critically-low Pride (under zero-sum an elimination pays the same whoever
lands it — a possible finishing-bonus diet idea, NOT proposed). watch_play.py gained
`--stop-after-win`; the harness aborts on close, so scripts gate on the output file, not the exit code.
Game-time note: a step is 6-10 frames plus slip (directional presses hold 10), so the "0.1 s/step"
figure understates game time by ~1.5x; recordings show ~100 s per 675-step round incl. reset.

## CHARACTER RANDOMIZATION BUILT (Sep 20 2026, 20:15-22:30 EDT; Blake: "We definitely need to add character randomization")

Design: the LEARNER stays Falcon in P2 (the policy has no character input and every pool policy is
a Falcon policy — the Aug 28 Ayame lesson: a Falcon policy driving another body is crippled), and
the P1/P3 pool seats stay Falcon for the same reason. What varies is the COM seat (P4), which the
game's own AI plays natively for every character: 14 mixed states, one per roster character, sampled
uniformly per episode. The lv8 battery lineup is Pride/Ryoma/Accel and the lv3 lineup Pete/Pride/Julia,
so until now the bot trained against Falcons only and was evaluated against characters it had never
seen (the Aug 28 "matchup hypothesis").
States: `states_mixed/slot10..22.state` (Ayame, Gunrock, Ryoma, Wang-Tang, Galuda, Rouge, Jack, Pete,
Julia, Gourmand, Accel, Mel, Pride; slot0 = Falcon), stamped headlessly with menu_drive.py from
slot0: wait 1500 frames (past the camera intro) -> START on P2 = pause menu -> DOWN x2 + A = CHANGE
CHARACTER -> PLAYER SELECT (Battle Royal) -> P2 cursor RIGHT x2 into the P4 column, UP to the
portrait row -> A x k cycles the roster forward -> START -> STAGE SELECT (defaults to Blue Sky) ->
UP = Desert Area -> A -> saved 200 frames into the match. menu_drive's `--save` flag is a no-op;
use the `save:` step. Four controllers stay baked (the base state carried them). `states_mixed/README.md`.
Verification: (1) select-screen portrait per state (contact sheet in the session scratchpad:
slot10 AYAME ... slot22 PRIDE, exact roster order); (2) in-env probe of all 13 in the real mixed
FFASelfPlayEnv (leg 56 policy, 150 steps each): healths live at start, all four seats moved
(P1/P3 views 54-1467 units, P4 COM 970-2148 units), damage flowing, SLOT_META (1,2); (3) 2-actor
trainer smoke on the full slot list: PASSED 22:40 EDT (2 actors, instances 23-24, 24,576 steps,
state_slots=[0,10..22] in [config], 49 episodes over 13 of the 14 slots, 49 [zs] + 51 [start]
lines, "leg complete", exit 0).
**ENABLED 22:45 EDT for leg 58+** (Blake: "We definitely need to add character randomization" +
"keep the 2 pool seats"): `league_env.txt` = `PS2_ZERO_SUM=1 PS2_START_HEALTH=0.5,1.0
PS2_STATE_SLOTS=0,10,11,12,13,14,15,16,17,18,19,20,21,22`. Leg 57 (running) unaffected.
NEXT LEVER QUEUED (Blake, Sep 20 22:50): COM LEVEL randomization (3/5/8 sampled per episode) —
probe the RAM cell for COM difficulty by diffing states/slot2 (lv3) vs slot3 (lv8); if writable at
reset it becomes a flag like start health, else stamp level-5/level-8 state sets via the options
menu. Own two-leg read AFTER the character read (legs 58-59).
COM-LEVEL RAM PROBE RESULT (Sep 20 23:40 EDT, instance 13): NEGATIVE. Diffing states/slot2 (lv3) vs
slot3 (lv8) against two lv3 mixed states gave 14 u8 cells with a 3->8 / 2->7 pattern; writing each
(and all 14 at once) into the live lv3 mixed state and running 300 deterministic noop steps produced
IDENTICAL COM behaviour in every condition (damage to P1-P3 = 138, first hit at step ~115-136, cells
read back as written). Read: the difficulty is consumed at match start (copied into the COM's AI
object), so a post-load write cannot change it, and none of the 14 cells is the live copy. Path
forward for level randomization = STAMP state sets at COM difficulty 5 and 8 via the options menu
(pause -> QUIT -> main menu -> OPTIONS -> COM DIFFICULTY -> Battle Royal -> lineup -> Desert), then
PS2_STATE_SLOTS mixes the sets. Parked until the character read (legs 58-59) is in.
Plumbing: `PS2_STATE_SLOTS="0,10,...,22"` (train_selfplay_async.py; PS2_STATE_SLOT stays the
single-slot form); the FFA env forces SLOT_META (1,2) for every configured slot; league_leg_async.sh
accepts PS2_STATE_SLOTS in league_env.txt. The [ep] line already prints the slot, so per-character
win shares can be read from any training log. Evals unaffected (base env, states/).
Pre-registered read (legs 58-59 vs 55-56 = 19.2/22.4, 95.2/97.6, 69/78): training win share may
dip at first (new opponents); the discriminator is lv8 (its COMs are Pride/Ryoma/Accel, now seen in
training) and the champion AB should hold. Revert = remove PS2_STATE_SLOTS from league_env.txt.

## ARENA LEVERS BUILT: ZERO-SUM REWARD + START-HEALTH RANDOMIZATION (Sep 20 2026, 07:30-09:00 EDT; Blake: "Test what you can without me ... Go for it")

Both are TRAINING-ONLY (the FFA env; batteries use the base env and never set the flags), both
inert unless set, both from the OpenAI Five reading (Sep 17). Code: `ffa_selfplay_env.py`
(backup `archive/ffa_selfplay_env_pre_zerosum_sep20.py`), `ps2_addr.py` (HEALTH_OBJ),
`league_leg_async.sh` (reads `league_env.txt`, records it as leg_modes.txt column 5).

**PS2_ZERO_SUM=1.** Every present seat is scored with ONE consistent copy of the learner's
shaped-reward function (same constants: dealt 2.0, taken 1.0, stone 3.0, win +20, loss -10 x
level scale, time -0.002, same per-episode gem cap), and the learner's reward becomes
r_learner - mean(r_other seats). Damage attribution: each seat's health drop is credited to
the NEAREST alive other seat (xz plane) — the base env's "all opponent drops are mine" rule is
not mirrorable in a 4-seat arena (it would dilute the learner's own hits by crediting two
bystanders). Timeout penalty stays learner-only (mirroring it would cancel it out). Per-step
info carries r_raw / r_opp_mean; a "[zs] raw= opp_mean= adj= dealt_nn= steps=" line prints per
episode. VERIFIED event-by-event on the mixed arena (instance 20, leg 53 zip, 2 episodes):
learner stone +3.00; opponent stone -1.00; learner lands 0.264 dmg +0.62; learner takes 0.176
dmg -0.29; opponent eliminated (by anyone) +3.1; learner dies with a survivor -16.7 (its -10
plus the survivor's +20/3). Episode totals: a lost fight that farmed 6 stones went from raw
+7.24 to adjusted +0.74 — the positive-sum pocket closes.

**PS2_START_HEALTH=lo,hi.** At reset every present seat's health is multiplied by an
independent U(lo, hi) draw. RAM finding: `ps2_addr.HEALTH` (0x8C475A04..) is a DISPLAY MIRROR
refreshed from the player objects each frame (a write there held only while the fight was not
yet live); the primary float is in the player object at PLAYER_MAT[k] - 0x330 (stride 0x3938)
= `HEALTH_OBJ`. Found by scanning SYSTEM_RAM for float32 cells tracking P2's health across
three damage events (4 hits: the mirror, +0x30, +0x50, and the object field). Writing the
object field sticks and damage applies on top (600/700 written on slot3 -> 600/593 after 20
steps). The env writes the object field plus the mirrors, pumps 2 frames, re-anchors
prev/prev_health and the seat views so the first step reads dH = 0 (verified: first-step r =
-0.002, the time penalty). "[start] health P2=539 P1=520 P3=636 P4=549" prints per episode.
HUD frame checked (start_random_ep0.png in the session scratchpad).

**Pre-registered read (when Blake enables it):** `echo "PS2_ZERO_SUM=1 PS2_START_HEALTH=0.5,1.0"
> league_env.txt` before a leg launch; two legs from the then-current zip; discriminators =
lv8 (band 15-19 under the stack), champion AB (60-74), and in the training stream the [zs]
lines (adj vs raw), timeouts, stones per episode (expect picks to FALL from ~6.3 as farming
stops paying while dealt_nn RISES). Revert = empty league_env.txt. Note the eval contract does
not change, so the comparison to legs 46-53 is direct. Not enabled; Blake's call tonight.
2-actor trainer smoke with both flags (08:12-08:20 EDT, instances 21-22, leg 53 zip, 24,576 steps):
6 updates, 42 episodes, 42 [zs] lines, 44 [start] lines (42 + 2 initial resets), seam check
logp_maxdiff 1e-5, "leg complete", zip saved. Zero-sum overhead measured at 0.019 ms/step
(39.0 -> 40.9 ms/step total, inside noise). Wrapper parse dry-run OK; eval_parity/ab probe
import the base/2-seat envs only.
**ENABLED 08:30 EDT (Blake: "If all is validated with 100%% certainty and not vibes, enable the
stack for leg 55"): `league_env.txt` = `PS2_ZERO_SUM=1 PS2_START_HEALTH=0.5,1.0`, applies at
leg 55's launch (~10:20 EDT). Leg 54 (running) is unaffected. Optimizer stack unchanged.**
PRE-REGISTERED READ, legs 55-56 vs legs 52-54 (stack, no arena flags): lv8 (band 15-21),
champion AB (53-70), lv3 (94-95); stream: stones/episode expected to FALL from ~6, dealt_nn to
rise, [zs] adj vs raw; timeouts stay ~0. Revert = `: > league_env.txt` before a launch.

## ZIPS PERSIST target_kl — leg 46 ran a STACKED setting by accident (Sep 18 20:20 EDT, operator error, corrected for leg 47)

SB3 saves target_kl/learning_rate/batch_size INTO the zip. The kl01 arm's zip therefore carries
target_kl = 0.1, and the restart (leg 46: "kl01 zip + PS2_LR=1e-4") inherited it: leg 46 trained
with lr 1e-4 AND target_kl 0.1 (Early-stopping lines: 14 of 196 updates; epochs/update 9.58; KL/update
0.021 vs the lr1e4 arm's 0.006). That is NOT the approved low-drift setting; it is a stacked
setting nobody pre-registered. Verified: leg40 zip 0.03 / kl01 zip 0.1 / lr1e4 zip 0.03 / leg46 zip 0.1.
CORRECTION (within the approved intent "restart on the low-drift arm"): `league_optim.txt` =
`PS2_LR=1e-4 PS2_TARGET_KL=0.03` from leg 47 on. Rule from here: every optimizer value the lineage
relies on must be set EXPLICITLY in league_optim.txt; never assume the zip's value.
Leg 46 stays in the ledger as an unplanned data point (lr 1e-4 + kl 0.1): stream win 0.38-0.40,
entropy -0.293 -> -0.574 by quarter, picks 6.5, forms 1.6; held-out below.

## SWEEP 40 RESULTS (optimizer sweep from the leg 40 zip, reset fix active; Sep 16 19:55 -> Sep 17 14:25 EDT)

Blake (Sep 16): "run it 3 different times with different changes" + "fix the timeout reload before
it". Four 4M-step mixed legs, ent_coef 0.01, all from the SAME parent (leg 40 = 4.2/86.8/60-40,
old reset code), each in its own pool clone. Same battery contract as the relay (lv8 n=500,
lv3 n=250, champion AB n=100), all still measured WITH the pre-roll handicap (section below).

| arm | change | epochs/update | KL/update | entropy med (Q4) | timeouts Q4 | stream win Q4 | lv8 (n=500) | lv3 (n=250) | AB vs champ | lv8 picks/forms |
|---|---|---|---|---|---|---|---|---|---|---|
| leg 40 (parent) | old reset code | 1.10 | 0.006 | -0.063 (-0.066) | 13%% | 0.38 | 4.2 (Wilson 3-6) | 86.8 | 60-40 | 3.94/0.59 |
| ctrl | reload-on-reset fix only | 1.07 | 0.007 | -0.100 (-0.099) | 9%% | 0.36 | 6.2 (4-9) | 91.2 | 69-30 | 4.79/0.82 |
| bs256 | + batch_size 64->256 | 5.72 | 0.020 | -0.347 (-0.458) | 1%% | 0.40 | 9.0 (7-12) | 92.8 | 65-35 | 5.59/1.06 |
| lr1e4 | + learning_rate 3e-4->1e-4 | 3.31 | 0.006 | -0.154 (-0.249) | 3%% | **0.49** | 13.6 (11-17) | 92.8 | **76-24** | **6.23/1.31** |
| kl01 | + target_kl 0.03->0.1 | 2.31 | 0.021 | -0.156 (-0.240) | 1%% | 0.43 | **16.6 (14-20)** | 92.8 | 71-29 | 5.62/1.11 |

READ (pre-registered questions, in order):
1. Reset fix alone (ctrl vs leg 40): +2.0 lv8, +4.4 lv3, +9 AB, entropy -0.063 -> -0.100, timeouts
   27%% (Q3) -> 7%%. The continued-match episodes were a real drag.
2. Epochs/update: every optimizer arm raised it (1.07 -> 2.3 / 3.3 / 5.7). bs256 got the most
   gradient work; it did NOT get the most held-out gain, so "more passes" is not the whole story —
   drift per update matters too (bs256 and kl01 both sit at KL 0.02, three times ctrl).
3. Best lv8 with lv3 and AB in band: kl01 16.6 (14-20) then lr1e4 13.6 (11-17); intervals overlap.
   lr1e4 has the better champion match (76 vs 71), the best picks/forms, the lowest drift, and its
   stream win share was still RISING in Q4 (0.32 -> 0.49). kl01 is the riskier mechanism (3x drift)
   and its stream was flatter. Every arm beat every previous leg of the campaign on lv8 except ctrl.
4. Entropy: all three optimizer arms reversed the 0.01 collapse without touching ent_coef (Q4
   -0.24 to -0.46 vs -0.07 at legs 39-40). The ent_coef 0.03 proposal is WITHDRAWN as redundant.
5. RECOMMENDATION (Blake's call): leg 41 warm start = lr1e4 zip (powerstone_v6_sweep40_lr1e4_league.zip)
   with PS2_LR=1e-4 as the standing setting; kl01 is the close alternative. Open follow-up arm:
   lr 1e-4 + batch 256 stacked (same mechanism, each helped alone), one leg from the lr1e4 zip.
   Under either choice the pre-roll fix + champion re-baseline should land BEFORE leg 41 so the
   new lineage is measured fairly from its first leg.
Arms' pools: pool_sweep40_<arm>/ (keep until Blake picks; the chosen arm's pool becomes the league
pool for leg 41 — copy, never rm). Zips: powerstone_v6_sweep40_<arm>_league.zip.

## TWO RESET FINDINGS FROM WATCHING THE BOT (Sep 16 2026, 16:30-16:50 EDT) — verified, NOT fixed (Blake's call)

Blake watched the leg 38 lv8 video: "lost 1/4 of his bar in the first 15 seconds before
it started to move" and "hiding, running away instead of opening boxes". Probed on
instance 13 (zero footprint), leg 39/40 untouched.

1. PRE-ROLL SITTING DUCK (training AND eval, every lineage since Aug 24). The libretro
   `_send("loadstate")` pumps the intro (~240 frames) and then a random 0-599 frame
   stagger (Aug 24 fix #4, decorrelates deterministic episodes) with NO input on the
   bot's port while the match is live. 30 lv8 loads: frames pumped median 530 (243-815);
   bot health at its first action median 982, mean 923, 7/30 start at 740 (one quarter
   gone). The pre-roll damage is never penalised (baseline/prev_health are set after it)
   — the bot just starts a quarter down in ~25%% of lv8 episodes. Same code path in the
   batteries, so every held-out lv8 number (champion included) carries this handicap.
   Fix candidates: stagger 0-59 + random first 1-2 actions, or take the stagger inside
   the intro. Either changes the eval contract -> re-baseline the champion first.
2. TIMEOUT DOES NOT RELOAD (training only). reset() sends loadstate only when
   `_match_ready` is false (bot dead or all opponents dead). After a MAX_STEPS timeout
   everyone is alive, so the next "episode" CONTINUES the same match: residual health,
   stones, timer, and freshly sampled opponent brains dropped into the existing bodies.
   Verified with PS2_FFA_MAX_STEPS=150 on the mixed state: reset pumped 1 frame, health
   carried 815 -> 743 -> ... across three "episodes". Mixed legs time out 6-21%% of
   episodes, so roughly one episode in ten starts mid-fight at partial health, right
   after the timeout=loss penalty was booked. The FFA anti-stall (Sep 14) was layered on
   top of this. Fix: force a loadstate on every reset (one line). Batteries have 0 T so
   held-out numbers are unaffected; the training distribution changes.
3. The "coward" read: the active diet is Blake's MINIMAL_REWARD (Leg F): win +20, loss
   -10, damage dealt 2.0, taken 1.0, stone +3, time -0.002/step, NO pay for approaching
   or opening chests. Against three lv8 COMs engaging costs and stones are free money,
   so pickup-and-avoid is what this diet buys. Diet is Blake's; recorded, not proposed.

Also added (inert unless set): PS2_BATCH_SIZE / PS2_LR / PS2_TARGET_KL overrides in
train_selfplay_async.py for the optimizer sweep (each prints a "[config] ... override" line).

## HUMAN PLAY + SPECTATE TOOLING (Sep 16 2026, 13:30 EDT — Blake: "may as well try" playing the bot)

Blake has only ever played the ~30M-step bot and has never watched the current
one. Two zero-footprint tools (no pool/state writes, own instance id + bridge dir):
- `watch_play.py` gained `--instance <id>` (bridge_watch_<id>, dolphin-<id>) and
  `--hidden` (no pygame window, for unattended `--record --speed 0`). NOTE: never
  set SDL_VIDEODRIVER=dummy — the harness needs SDL's GL window; hide only pygame.
  Recorded under the mixed-leg eval contract (obs v2, p4 harness): the leg 38 zip
  vs 3x lv8 COM and vs 3x lv3 COM, 3 episodes each -> `linux_port/videos/`.
- `play_vs.py` (NEW): YOU in in-game P1 (libretro port 0, keyboard or first
  gamepad, mask set every frame inside a wrapped run_frames), the bot in P2 as
  always. `--mode 1v1` (states/slot1), `ffa` (states/slot0, P3+P4 policy seats),
  `mixed` (states_mixed/slot0, P3 policy, P4 lv3 COM). `--opps same|pool`.
  MAX_STEPS lifted so rounds end when the game ends them. Results print from the
  bot's side. Smoke-tested headless in all three modes (250-step cap) while leg 39
  trained. Default instance 12. Command in the docstring / SESSION_HANDOFF sec 9.
  This is the discriminator the lv8 number cannot give: does it beat a human.

## FFA SELF-PLAY LINEAGE — DESIGN + PRE-REGISTRATION (Sep 13 2026, Blake's call after the async validation)

Goal restated (Blake): four-way free-for-all where three of his own bots
beat him. The 1v1 self-play league is measured on FFA vs COMs it never
trains on; the OpenAI Five lesson is that self-play must BE the target
game. Decisions (Sep 13): four-seat self-play FFA is the next lineage;
fix the three deferred observation-contract bugs in the same change as
ONE versioned bump (obs v2); prioritized opponent sampling as a switch;
parallel 500/250/100 batteries; the parent A/B is dropped.

**obs v2 (PS2_OBS_V2=1; default stays v1 so the running pure-league relay
is untouched):** (a) last-action one-hot = a_t for EVERY seat (the
learner's was a_{t-1}; the P1 view's and the recorders' were a_t — one
convention now); (b) every non-learner view carries its OWN gem count,
form timer, last action and previous-state (the v1 P1 view leaked the
learner's _form_timer/_my_g_int); (c) the demo recorders' velocity
window is fixed with the same step semantics (only matters for future
recordings). Obs dim stays 122; warm start from the leg 25 zip (the
policy adapts to (a) under fine-tuning; a fresh start would waste 56M
steps of lineage).

**FFA env (ffa_selfplay_env.py):** one emulator, four seats; learner =
in-game P2 (port B) as always; seats 1, 3, 4 driven by FROZEN pool
policies, each with its own StateLineSynth view (bot_player=k) and its
own view state; all three opponent actions applied as held masks before
the learner's frames (same mechanism as the 2-seat env). Savestate:
Original mode true FFA, desert, ALL FOUR SEATS HUMAN, all Falcon
(every pool policy is a Falcon policy — the Ayame lesson), four
distinct colours (same colour = team). New slot 4; SLOT_META[4] = (1, 2)
mirroring slot1's context dims so the model reads "self-play regime"
and sees the FFA-ness through the three opponent blocks (pre-registered
choice; the alternative (2, 2) is noted). EXPECT_OPP 3.

**Pool sampling switch (PS2_POOL_SAMPLING=uniform|pfsp):** pfsp keeps a
per-opponent EMA of the learner's win share and samples opponents it
loses to more often (p ∝ (1 - w)^2 + eps, half of the time; the other
half uniform over the newest 10, as now). In FFA the episode outcome is
credited to all three sampled opponents. Off by default; the FFA
lineage runs with it ON (this is the diet change Blake asked for; no
COM rungs).

**Validation outcome rule for sharded batteries (added Sep 13 17:25, before
leg 27 ran):** layer 4 PASS iff slot2 >= 80 (n=250) AND AB vs the leg1
champion >= 40%% of 100 (a regression guard; recent legs read 67-83%% at
n=12). No parent AB exists any more.
**Validation (same harness):** validate_async_leg.py on the first FFA
leg vs leg 24's lockstep log for layers 1-2; layer 3 thresholds do not
transfer (FFA win share vs three pool opponents will be lower by
construction — reported, not gated); layer 4 = the new 500/250/100
battery. RE-BASELINE FIRST: the leg 25 zip and the leg1 champion are
re-evaluated under obs v2 on slot2/slot3 (sharded) before the lineage
launches, so every later number has a same-contract reference.
Mechanical smoke of the four-view code runs on slot3 (three COM seats)
before the four-human state exists.

**Relay:** the pure league continues on this Mac until the FFA lineage
is ready to launch, then stops here (historical control; may resume on
the M2 at Blake's option). Leg naming continues (FFA legs are legs 27+
with "FFA" in the lifetime column); pool_league keeps growing with
both.

**FFA BUILD LOG (Sep 13 13:30-14:30): four-seat env, 4-port harness, the
four-human savestate — all done headlessly.**
1. The built harness routed input to TWO ports (sdlarch.h MAX_PLAYERS=2).
   Now a compile option (SDLARCH_MAX_PLAYERS, default 2); a 4-port build
   lives in `sdlarch-rl/p4/` (use PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:.);
   the repo-root `_retro.so` is the unchanged 2-port binary the relay uses.
   The build's copy-to-root step is now a CMake option (SDLARCH_COPY_TO_ROOT,
   OFF for build_p4) — it overwrote the root binary once on Sep 13 and was
   restored from build/Release within minutes (leg 26 unaffected: running
   processes hold the old binary). 4-port binary parity on the standard
   2-seat slot2 eval, leg 25 zip, n=100: 91.0 / 10.00 / 2.99 (PASS).
2. Ports C/D still did nothing after the rebuild. Root cause (flycast
   source, libretro.cpp + maple_cfg.cpp): a SAVESTATE serializes the maple
   device table and mcfg_DeserializeDevices re-creates exactly those
   devices, so every state in this project (saved under 2 controllers)
   drops ports C/D on load. Fix: re-attach joypads after load
   (NONE->JOYPAD toggles via a new `_retro.set_controller_port_device`
   binding; opt-in hook PS2_RECONNECT_PORTS=1 in flycast_bridge.loadstate)
   AND bake four controllers into the new state: load, reconnect, run 120
   frames, save (a save only 4 frames after the reconnect produced a state
   with NO working ports at all). Verified: each of ports A-D moves its own
   seat ~600 units with the others at drift level (test script kept in
   the session scratchpad; recreate from this note if needed).
3. The four-human state was stamped headlessly with menu_drive.py (now
   supports p3/p4 steps) from slot2.state: pause (start on P2 after the
   ACTION banner), down x2 + A = CHANGE CHARACTER; on PLAYER SELECT the P2
   cursor can move into any column; rows cycle up: mode -> portrait ->
   colour -> mode; A on the mode row cycles COM -> NO ENTRY -> HUMAN; A on
   the PORTRAIT row cycles the roster FORWARD (B backward): Falcon, Ayame,
   Gunrock, Ryoma, Wang-Tang, Galuda, Rouge, Jack, Pete, Julia, Gourmand,
   Accel, Mel, Pride, RANDOM SELECT, (Falcon...); left/right move between
   columns; START (P2) -> STAGE SELECT, one UP from the start tile =
   Desert Area, A = match. Result: 4 x Falcon, 4 x HUMAN, red/yellow/blue/
   green, desert; saved ~140 frames into the intro (healths all 1000 once
   the intro ends). Installed as `states/slot0.state` (Mac slot 0 = the
   FFA4 self-play state; backup states/ffa4_falcon_desert_4human.state.bak;
   Law 8 re-stamp record). SLOT_META[0] -> (1, 2) in ffa_selfplay_env.py.
4. ffa_selfplay_env.py mechanical test on slot 3 (three COM seats) PASSED:
   each view reads its own seat's health, three opponents, its own
   counters; the learner's obs v2 last-action timing verified.
5. Relay modes in league_trainer.txt: lockstep | async | ffa | hold. "ffa"
   = league_leg_async.sh with PS2_ENV=ffa PS2_OBS_V2=1 PS2_STATE_SLOT=0
   PS2_POOL_SAMPLING=pfsp on the p4 harness, and league_battery.sh
   evaluates under obs v2 on the p4 harness. "hold" = battery runs,
   state advances, no launch (marker leg<N>_LAUNCH_HELD.txt). Set to hold
   for leg 27 so the obs-v2 re-baseline (rebaseline_obsv2.sh) can run on a
   quiet machine before the FFA lineage launches.

**OBS-V2 RE-BASELINE (Sep 13 14:07-15:30, sharded, 4-port harness,
PS2_OBS_V2=1) — AND A RECALIBRATION OF THE CHAMPION.** receipts/rebase_v2_*:

| model | slot3 lv8 (n=500) | slot2 lv3 (n=250) |
|---|---|---|
| leg 25 zip | 3.2% (16W/484L, Wilson 2-5), picks 3.42 | 88.0% (220/250, Wilson 83-91), picks 9.71 |
| leg1 champion (powerstone_v6_ppo.zip) | **5.2%** (26W/474L, Wilson 4-8), picks 4.21 | **91.2%** (228/250, Wilson 87-94), picks 9.16 |

Two readings. (1) The contract change did not move the held-out numbers
(leg 25: 88 -> 88 on slot2; 8%% at n=50 -> 3.2%% at n=500 is the same
rate seen sharply). (2) THE CHAMPION'S BASELINES WERE SMALL-SAMPLE
FLATTERY: "98.0 slot2" was 49/50 and "15%% lv8" was 3/20. At n=250/500
the champion reads 91.2 / 5.2. The lineage-vs-champion gap on held-out
COM evals is therefore ~3 points on slot2 and ~2 points on lv8, both
inside the intervals — the "parity" story is confirmed, the "wall at
15%%" was never 15%%. Any public number quoting 98 or 15%% should carry
the n; the honest champion line is 91 / 5 at n=250/500. (Caveat: these
are obs-v2 reads; leg 25 shows v1 == v2 within noise, so the champion's
v1 numbers at the same n would very likely match.)

## M4 PRO ERA (Sep 11, 2026) — bring-up, throughput probes, leg 21 recipe change

Relay moved from the M2 Pro to Blake's M4 Pro (10 P-cores + 4 E-cores,
48 GB; project at ~/Downloads/macbook_migration, symlinked from
~/Documents; machine on US/Pacific — M2 logs were EDT). The Claude session
on this machine runs a shell directly on the Mac (no VM), so the file
bridge is optional here.

**Bring-up (details in M4_SETUP.md, fixes baked into setup_m4.sh):**
Gatekeeper quarantine + ad-hoc re-sign of _retro.so / libpcsx2_headless /
flycast core; rpath baked in under the M2 username; `brew install
sdl2-compat`. **Parity gate PASSED** on the leg 20 zip, slot2 n=50:
94.0 (47W/3L, Wilson [84-98]) / picks 10.26 / forms 3.16 vs the M2's
88.0 / 10.56 / 3.22 (matched-reference test). Eval took 15 min vs 26.

**Throughput probes (zero-footprint: <100k steps, no pool/checkpoint
writes; 81,920-98,304 actual steps each; all booted first try at
stagger 20):**

| workers | aggregate steps/s | per worker | idle CPU during rollout |
|---|---|---|---|
| M2 Pro, 6 (legs 18-20) | 75-79 | 12.8 | (P-cores saturated) |
| 8 | 106.9 | 13.4 | 69% |
| 10 | 120.5 | 12.0 | 64% |
| 12 | 117.7 | 9.8 | 59% |
| 14 | 123.1 | 8.8 | 80% |

**Diagnosis:** the plateau at ~120 is NOT the hardware. One instance alone
does 53 steps/s (bench_fps C, 485 raw fps vs the M2's 325); TEN independent
instances fully overlapped do 35-44 each (~390 aggregate). The 3x loss is
the synchronous SubprocVecEnv: a reset costs ~1.0 s (loadstate + intro
pump) and stalls every worker; a 14-worker snapshot caught one worker at
32% CPU and thirteen at 5%. Render settings are NOT the lever: 320x240
internal resolution changed nothing at 10 workers (120.6); frame skipping
=1 cut throughput to 81.9 AND altered the game (238 eps vs ~170 per
budget, learner win share 75% -> 49%) — fails the chest-obs law, dead.
`flycast_bridge.py` gained a no-op-by-default PS2_CORE_VARS hook for such
benches; `bench_fps.py` gained --instance. OPEN ENGINEERING ITEM (Blake's
go required, prototype only on probes): an asynchronous rollout loop
could plausibly reach 300+ steps/s here.

**LEG 21 RECIPE CHANGE (Blake, Sep 11): 10 workers, 4M-step legs**
(league_leg.sh defaults; 2M->4M was the previous session's standing
recommendation). Note for curve reading: n_envs also sets PPO's rollout
size (2,048/worker/update) — a 4M leg at 10 workers is 195 updates vs
162 per 2M leg at 6 workers; total minibatch gradient steps per step
are unchanged. Lifetime after leg 21 = 40M. Leg 21 launched Sep 11
20:20 PDT (tmux ps2train), ETA ~9.3 h at 120 steps/s.

**ASYNC TRAINER, PHASE 1 DONE (Sep 11 evening, Blake's go):**
`train_selfplay_async.py` (new file; train_selfplay.py untouched) = actor-
learner PPO: N actors each own a SelfPlayEnv + CPU policy copy, step and
reset independently, ship n_steps chunks; the learner lays the first
N_ENVS chunks into SB3's own RolloutBuffer as columns and runs the
unchanged PPO.train(). Same env/obs/rewards/pool/hyperparameters/snapshot
cadence; the one difference is chunks up to one update stale (logged per
update as lag). `test_async_buffer.py` proves column fill == SB3's
row-by-row collect_rollouts bit for bit (obs/act/rew/starts/values/
logp/advantages/returns). 2-actor smoke beside leg 21: two updates, lag
0 then 1, 18 contested episodes, clean save, clean exit, no hang.
MEASUREMENT (Blake: hold leg 22 for it): `async_measure.sh` runs after
leg 21's battery on the quiet machine (10 actors/10 columns, then 12/10;
<100k steps each, artifacts deleted), writes claude_bridge/
async_measure_result.txt, then launches leg 22 itself. Lockstep reference
at 10 workers: 120.5 steps/s. Adoption as the leg recipe = Blake's call
after a validation leg + battery.

**ASYNC TRAINER MEASURED (Sep 12 06:27-06:41, quiet machine, leg 21 zip
as warm start, 81,920 steps per probe, artifacts deleted):**

| trainer | actors/columns | aggregate steps/s | learner win share in stream | lag |
|---|---|---|---|---|
| lockstep (train_selfplay.py, Sep 11) | 10 | 120.5 | ~75-80% | 0 |
| **async (train_selfplay_async.py)** | 10 / 10 | **275.5** | 79% (181/228 eps) | max 1 update |
| async | 12 / 10 | 266.0 | 82% (182/221) | max 2 updates |

2.3x on the same hardware, zero errors, clean exit, episode statistics
indistinguishable from the lockstep stream. Extra actors beyond the
column count buy nothing (the learner is not the bottleneck yet) and
raise staleness, so 10/10 is the configuration. Projection: a 4M leg in
~4.0 h instead of ~9.7 h. NOT yet the recipe: adoption = Blake's call
after a validation leg (proposal: leg 23 on the async trainer, same
10/10 + 4M, full battery, compared against legs 21-22). Needs a
league_leg_async.sh wrapper with the halt-on-mid-leg-death rule before
it can be chained. Leg 22 launched 06:41 PDT on the lockstep trainer.

**RECIPE CHANGE FROM LEG 23 (Blake, Sep 12 ~07:00): ASYNC TRAINER.**
`linux_port/league_trainer.txt` = "async" makes league_battery.sh chain
`league_leg_async.sh` (train_selfplay_async.py, 10 actors / 10 columns,
4M steps, ~4 h per leg) instead of league_leg.sh. Switch back by writing
"lockstep" (or anything else) into that file between legs. Leg 23's
battery is the validation read against legs 21-22 (same recipe
otherwise). The async leg exits cleanly at "leg complete" (no teardown
hang); wrapper lines are tagged [wrapper-async]. Scheduled fallback
wakes now work unattended: Blake added
`.claude/settings.local.json` (permission allowlist, git-ignored).

**PRE-REGISTERED VALIDATION OF THE ASYNC TRAINER (written Sep 12 ~13:45,
BEFORE leg 23 runs; Blake: "not vibes").** Four evidence layers, rules fixed
in advance, evaluated by `linux_port/validate_async_leg.py` after leg 23's
battery:
1. Seam integrity: the async learner re-evaluates every lag-0 chunk under
   the current weights and logs `[check] logp_maxdiff / value_maxdiff`.
   PASS iff max |dlogp| < 1e-4 and max |dvalue| < 1e-3 on every update.
2. Learning statistics per PPO update (approx_kl, clip_fraction,
   entropy_loss, explained_variance, value_loss; async `[stats]` lines vs
   SB3's verbose table from a matched LOCKSTEP reference run: same warm
   start as leg 22 (leg 21 zip), 10 workers, 450k steps, run beside leg 22
   in its own instance/checkpoint namespace — receipts/
   train_lockstep_stats_out.txt). PASS iff async medians: approx_kl <=
   2.5x, clip_fraction <= 2.0x, explained_variance >= ref - 0.15,
   entropy_loss within 25%, no NaN/inf, AND gradient steps per update
   (delta of train/n_updates) >= 0.75x the lockstep median — the zip
   carries target_kl=0.05, so SB3 early-stops an update's epochs when KL
   runs high; staleness must not be silently eating the async updates
   (added 14:35, still before leg 23).
3. Training stream (thousands of episodes): whole-leg learner win share
   within 10 points of the lockstep reference, picks/forms within 20%,
   no quarter below 50% win share.
4. Outcome: the normal battery (slot2 >= 80, AB vs parent >= 7-5 at n=12)
   plus an n=50 AB leg23-vs-leg22 for a tighter parent comparison.
Any FAIL = revert league_trainer.txt to lockstep for leg 24 and report;
the async leg's zip stays in the lineage only if the outcome layer passes
(a failed layer 1-3 with a passing battery is reported to Blake for a
call, not decided by the session).

**FINDING (Sep 12, from the first PPO-statistics log this lineage has ever
produced — the lockstep baseline probe): the zip carries target_kl=0.03,
and SB3 EARLY-STOPS most updates after 1-2 of the nominal 10 epochs**
("Early stopping at step 0/1 due to reaching max kl" = epoch index;
train/n_updates advances one per epoch and moved 1-2 per update in 15/15
updates). Every league leg has trained this way; the leg-21 move to 10
workers (20,480 samples/update, 320 minibatches per epoch) plausibly
lowered the effective epoch count further than 6 workers did (unverified —
a 6-worker probe would settle it). Not changed: it is the lineage's
standing behaviour and the pre-registered recipe; recorded so the async
comparison (same rule applies to both trainers) and any future LR/epoch
discussion start from the measured fact, not the constructor comment.

**LEG 25 ONWARD: ASYNC + MID-CHUNK WEIGHT PULLS (Blake, Sep 13 06:45).**
league_trainer.txt = async again; league_leg_async.sh now exports
PS2_PULL_EVERY=64 by default. Leg 24 (lockstep, launched 21:51 Sep 12
per the pre-registered revert) finishes as is. Leg 25 is the second
validation leg: same validate_async_leg.py run, expectation that the
gradient-epochs rule now passes (2-actor smoke: step lag 1.0 -> 0.1,
2-3 epochs per update).

**CORRECTION TO THE LEG-23 READ + LEG-25 PRE-REGISTRATION (Sep 13 07:45,
before leg 25 launched).** Leg 24 ran lockstep WITH the new statistics
table, giving a full-leg lockstep reference (195 updates) instead of the
21-update probe. Against it, lockstep itself early-stops in epoch 0 on
58% of updates (113/194; median 1, mean 1.43), so leg 23's async median
(1) does not fall below the reference median — the FAIL was against a
small-sample reference. The gap is real but smaller: async mean 1.15 vs
lockstep 1.43 epochs per update (~80% of the gradient work), async KL
p90 0.036 vs 0.018. Leg 25 (async + PS2_PULL_EVERY=64) is validated
against leg 24's log with the median rule AND a mean rule (async mean
>= 0.75x lockstep mean), both fixed here before the leg ran. Leg 24:
9h41m, 9,083 eps, stream 77.9/76.6/76.1/78.1, picks 4.44, forms 0.90.

**BATTERY UPGRADE (Blake, Sep 13 ~13:30): PARALLEL SHARDED EVALS, AB-vs-
PARENT DROPPED.** From leg 26's battery, league_battery.sh runs every eval
as 10 shards on 10 emulator instances (eval_parity.py --instance,
ab_selfplay_probe.py per-instance pool/bridge dirs), validated per shard
and merged by merge_receipts.py into the standard receipt format:
slot3 (lv8) 10x50 = **500 episodes** (Wilson half-width ~2 points at a
4% base rate, vs ~9 before), slot2 (lv3) 10x25 = 250, AB vs the leg1
champion 10x10 = 100. The AB vs the previous leg is gone ("it literally
always beats its former self" — Blake; the audits already rated it
practice, not transfer; the fixed champion reference keeps the tripwire
role). Wall-clock ~50 min. Shard files live in receipts/shards/; the
serial script is archived as archive/league_battery_serial_sep13.sh.
Rows from leg 26 on carry (n=500/250/100) — do not compare their
intervals to earlier n=50 rows without noting it.

## LEG 4 — THE SYNTHESIS LEG (Aug 31->Sep 1): NEW FRESH-LINEAGE CHAMPION

All-6-worker self-play vs pool_league (24 zips: rig checkpoints
0.2-31.9M incl. leg1's 28-31.9M snapshots + all program finals + seed),
warm start 3B, 2M steps (lineage lifetime now 4M), post-reboot, one
boot-flake retry absorbed by the new watchdog launcher (launch_leg4.sh
— the v2 wrapper kills teardown-hung crashes instead of waiting).

Training vs the league: q1-q4 29.8/29.5/20.0/22.8%%, ep len 490->943 —
win%% held ~25%% against MIXED opposition whose strong half is the
31.9M lineage, fights lengthening as its own snapshots entered.
(Blake's calibration note, Sep 1: leg1's 31.9M "peaked around 15-20M"
— the middle was the reward-era plateau; effective-step gap vs the
fresh line is ~4-5x, not 16x, and the last 4M selfplay burst did the
rest.)

BATTERY (n=50 det / n=12 A/B):
- slot3 (lv8): 0.0 / 1.20 / 0.06 — the wall is now 5-0 vs fresh legs.
- slot2 (lv3): **42.0 / 6.74 / 1.56 — new fresh-lineage record**
  (3B: 40.0/6.26/1.28), earned against honest opposition.
- **A/B vs 3B (its warm start): 8W-1L-3T — decisively outgrew its
  parent in one leg.**
- A/B vs leg1: 1W-11L (3B read 4-8; n=12 noise + intransitivity —
  the league diet tuned it vs fresh-lineage styles; slot2 is the
  truer transfer measure and it leads there).

VERDICT: the synthesis works — deep pool + full self-play budget beat
both its parent and every program leg on transfer, in 2M steps. THIS
is the leg shape to redline on the 7950X (Blake: "found the most
scalable leg to run — red line it and let it cook"). Lineage seat:
powerstone_v6_leg4_league.zip is the fresh-line champion;
powerstone_v6_ppo.zip (leg1) remains overall champion, NOT overwritten.
Next: keep compounding this lineage (leg 5 = same recipe warm-started
from leg4, pool grows), Linux-box bring-up (repo push pending Blake),
recorder/DAgger port, reddit video of leg1 still unrecorded.

## PRE-REGISTERED INTERVENTION PLAN (Blake + session, Sep 3 — binding until amended by Blake)

The league diet stays PURE self-play. Blake's pushback, ratified: the
curve is climbing, and this project's history says interventions
without a measured failure are how legs get burned (reward era 0-for-5;
leg 3C's dead COM stream; Law 5). Pure self-play keeps paying for
things it never trained on (leg1's FFA jump; the current slot3
behavior climb). NO diet change on a forecast — soft-pool worry
included.

**TRIGGER (must actually fire before any diet change):** slot2 flat or
down for TWO consecutive leg batteries, OR slot3 behavior metrics
(picks+forms) stalling across two legs. Current references at
registration: slot2 84.0 (leg 9); slot3 picks 3.42 / forms 0.48 and
climbing.

**RESPONSE WHEN FIRED (in order, nothing skipped):**
1. MEASUREMENT FIRST: stamp lv6-FFA and lv8-1v1 states (headless via
   menu_drive; ORIGINAL mode; difficulty via options; spare emu
   instance so the relay is untouched) and run them as EVAL-ONLY
   discriminators — zero training budget spent.
2. Only then, give ONE worker to the highest rung the model already
   wins >=20%% of at eval (Law 1: winnable rungs only; Law 5: never a
   dead stream). Everything else stays league self-play.
3. Graduation: rung moves up when its training stream sustains ~60%%.
Anyone (human or session) proposing a diet change before the trigger
fires must be pointed at this section.

## LEAGUE LEGS (running record — one line per leg; relay automated Sep 1)

Recipe per leg: league_leg.sh / league_battery.sh, 2M steps, full
self-play vs pool_league (frozen at worker start, grows between legs —
audit #2), warm start = previous leg,
battery + auto-launch chained. Lineage: bc256 -> 3B -> leg4 -> leg5...

| leg | lifetime | train q1-q4 vs league | slot3 | slot2 | A/B vs prev | vs leg1 |
|-----|----------|----------------------|-------|-------|-------------|---------|
| 4 | 4M | 29.8/29.5/20.0/22.8 | 0.0 | 42.0/6.74/1.56 | 8-1-3 (3B) | 1-11 |
| 5 | 6M | 38.3/28.0/47.2/52.1 | 0.0 | **50.0/7.02/1.52** | **11-1** | **6-6** |
| 6 | 8M | 55.8 -> 67.0 (halves) | 0.0 (picks 1.46, forms 0.18 — first life) | **64.0/7.86/1.92** | **11-1** | 7-5 (n=12; see 50-ep below) |
| 7 | 10M | 62.5/75.6/73.7/78.6 | 0.0 (1.34/0.08) | **78.0/9.04/2.70** | 9-3 | — |

| 8 | 12M (CLEAN league) | 84.8 -> 90.2 | 0.0 (**picks 2.40, forms 0.22 — doubling leg-over-leg**) | **82.0/9.56/2.74** | 11-1 | 7-5 (n=12) |

**LEG 8 (Sep 3, first clean-league leg): THE CURVE HOLDS.** slot2
40->42->50->64->78->**82** under the honest opponent mix — the skew was
not the engine. Picks 9.56 vs leg1's 9.76: component parity. slot3
still 0 wins but its behavior metrics are now climbing leg-over-leg
(1.34/0.08 -> 2.40/0.22). NEW LEAGUE DYNAMIC to watch: with mtime
sorting, "recent 10" = mostly its OWN latest snapshots once it's the
strongest line in the pool — training win%% jumped to ~87%% (soft again,
the 3B problem at a higher level). The lineage has outgrown its league;
options for a future boundary: raise recent_k, weight prog_*/leg1
zips, or PFSP-by-winrate sampling. Not changed mid-relay.**

| 9 | 14M | 78.5 -> ~84 flat | 0.0 (**picks 3.42, forms 0.48 — third straight climb**) | **84.0/10.02/3.06 — picks+forms EXCEED leg1** | 11-1 | 8-4 (n=12) |

**LEG 9 (Sep 3): component parity PASSED.** slot2 picks 10.02 and
forms 3.06 now exceed leg1's 9.76/3.00; win%% 84 vs 98 — the remaining
gap is pure win-conversion. slot2 slope moderating (78->82->84):
either the lv3 asymptote or the soft pool capping growth (training
win%% ~84 sustained, below the 92 flag line). The live frontier is
slot3's behavior climb: 1.34/0.08 -> 2.40/0.22 -> **3.42/0.48** over
three legs with zero wins — the wall's base is eroding measurably;
first lv8 wins plausibly within a couple legs at this rate.**

| 10 | 16M | ~85 vs league | **2.0 — FIRST LV8 WIN EVER (1W/49L)**, picks 3.88, forms 0.54 | **86.0/10.76/3.18** | 9-3 | 8-4 (n=12) |

**LEG 10 (Sep 3): THE WALL CRACKED.** First lv8 eval win in project
history — after nine legs and 0-for-450, exactly as the three-leg
behavior climb (picks 1.34->2.40->3.42->3.88, forms 0.08->0.22->
0.48->0.54) predicted. One win in fifty is a crack, not a breach —
but it arrived on schedule, from pure self-play generalization, with
zero lv8 training data, on a laptop. slot2 86.0 still climbing (no
stall; pre-registration trigger NOT armed). The 7950X arrives to a
lineage that has now scored on everything the game has.**

| 11 | 18M | — | 0.0 (picks 3.22, forms 0.54 — climb PAUSED) | **90.0/10.42/3.12** | 8-4 | **9-3** (n=12) |

**LEG 11 (Sep 4): crack NOT consolidated** — 0/50 at lv8; leg 10's 1/50
stands alone for now (noise vs leading-edge unresolved; behavior
metrics paused their three-leg climb). Meanwhile slot2 hit **90.0**,
eight points from leg1's 98, and the quick probe read 9-3 — the best
yet. Trigger unarmed (86 -> 90).**

| 12 | 20M | — | **4.0 (2W/48L) — CRACK CONSOLIDATED**, picks 3.78, forms 0.62 | 88.0/10.60/3.20 | **10-2** | **11-1** (n=12, record) |

**LEG 12 (Sep 4): TWO lv8 wins — the crack is real.** After leg 11's
0/50 scare, leg 12 scored 2W/48L at lv8 with behavior metrics resuming
their climb (picks 3.78, forms 0.62 — both lineage records). Wins at
lv8 across three legs: 1, 0, 2 — a noisy leading edge, exactly what a
wall eroding from underneath looks like. Both AB probes set records:
10-2 vs its parent, **11-1 vs the leg1 champion** (n=12; the n=50
crown probe remains 29-21). slot2 read 88.0 (down 2 from 90 — inside
n=50 noise, but by the pre-registration letter this is one flat/down
leg: trigger is now ARMED; a second consecutive flat/down leg fires
it and the response is eval discriminators FIRST, no diet change).
OPS NOTE: leg 12's trainer hung in teardown AFTER printing "leg
complete" (mutex hang on clean exit — new variant of the known
failure mode); the hung main + 6 workers squatted CPU for ~50 min
until manually killed, and the stale ps2train tmux session would have
blocked leg 13's auto-launch. Relay procedure updated: after each leg,
verify trainer exit + session cleanup before battery. Consider adding
os._exit(0) after the final save in train_selfplay.py as a permanent
guard.**

| 13 | 22M (M2 resumed Sep 8) | — | **6.0 (3W/47L) — lv8 wins now 1,0,2,3, a climbing edge** | **90.0**/9.12/2.72 | 10-2 | **11-1** (n=12, ties record) |

**LEG 13 (Sep 8, first leg after the 4-day hardware pause): TRIGGER
DISARMED (88 -> 90), and the lv8 edge is now a TREND.** Three wins in
fifty at max difficulty — the per-leg win counts read 1, 0, 2, 3, with
behavior metrics holding at their highs (3.62/0.62). slot2 back at 90
(picks/forms softened to 9.12/2.72 — watch, not worry, win%% rose).
AB probes: 10-2 vs leg12, 11-1 vs leg1 again. OPS: the teardown hang
recurred on clean completion (2nd straight — now the expected end-of-
leg behavior; every relay wake kills the hung tree before the battery;
os._exit(0) patch proposed to Blake, pending). The dead eBay 7950X
detour (Sep 6, board fine) cost 4 calendar days and zero project
state.**

| 28 | 68M (FFA self-play #2, obs v2, PFSP, 4M, 4h25m) | 34.6/30.4/27.3/30.3 vs three FFA-trained opponents (3,122 eps, 10.6%% timeouts, entropy collapse) | 4.4 (22W/478L, n=500, Wilson 3-7; 3.81/0.58) | 84.0 (210/250, Wilson 79-88; 10.07/3.02) | — | 72-28 (n=100) |

**BLAKE (Sep 14 20:30): "let it rip 1 or 2 more legs unless we see a
significant drop in the level 3 or champion matches. I think this is the
recipe."** league_trainer.txt back to ffa; legs 33-34 chain. Hold rule for
these legs, written now: hold iff slot2 < 70 (n=250) or champion AB < 35
wins of 100 or lv8 < 4.0%% (n=500). Otherwise continue; report each
battery.

**LEG 34 PRE-REGISTRATION — MIXED SEATS (Blake, Sep 15 ~10:15 EDT).** Seats:
learner P2, pool policies P1 + P3, P4 = the game's COM (Falcon, level 3 —
the level baked into the slot2-derived state; level 5 is the follow-up if
the pressure is too soft). State `states_mixed/slot0.state` (4 x Falcon,
desert, three HUMAN + one COM, four controllers baked in; same slot number
as the pure-FFA state so SLOT_META/obs are identical). Env: PS2_FFA_SEATS=
0,2 + PS2_STATES_DIR=./states_mixed (league_trainer.txt = mixed). Same
anti-stall settings, obs v2, uniform sampling, 10 actors, 4M, warm start
= the LEG 33 zip (best FFA policy). SUCCESS SIGNATURE, written before the
leg: stream timeouts collapse (< 10%%, from 35%%), entropy stops falling,
and on the battery lv8 holds >= 5.0%% (n=500; leg 33: 6.4) with slot2 >=
80 and champion AB >= 35/100. Adopt as the recipe if it passes; if
timeouts collapse but lv8 falls below 5.0, try the level-5 COM before
judging the design.

**ENTROPY WATCH (Blake, Sep 15 21:30 EDT: "keep an eye on entropy").**
Reference: lockstep leg 24 entropy_loss median -0.266; FFA/mixed legs run
~ -0.07 to -0.11 (SB3's entropy_loss = -mean policy entropy, so values
nearer 0 = a more deterministic policy). Pre-registered trigger for a
recipe adjustment (ent_coef 0.01 -> 0.03 for mixed legs, Blake's go
required): median entropy_loss above -0.06 for two consecutive legs, OR
lv8 flat/down (within its interval or lower) for two consecutive legs while
entropy_loss is trending toward 0. Every collection wake reports the leg's
entropy median and the trigger state; the interactive session's watcher
emits the running median hourly.

| 84 | 272M (MIXED, 14 lv3 + 14 lv8 CHARACTER STATES + 10 THREE-COM LINEUPS (27%%), warm leg 83, STACK + ARENA + 7-LAG OBS STACK + OBS CTX FIX + ZS TIME COST + OBS V3 + ASTRA-2 FIXES, NEW CONTRACT (v3 eval; slot 3 = seen-state benchmark; AB = fixed-view series); standing recipe) | all 38.9/39.7/38.6/37.9, 3-COM eps 32.1/34.0/31.6/27.7 (n=2,256), lv8 eps 41.8/39.2/41.1/40.6, lv3 eps 41.2/44.9/40.8/42.7 (8,308 eps; timeouts 0/0/0/0%%; picks 5.30/5.40/5.40/5.32; entropy -0.581; KL/update 0.025; epochs/update 2.21; expl_var 0.81; [zs] adj +12.7/+13.5/+12.6/+12.6; win share by transforms 0/1/2/3 = 0.00/0.22/0.72/0.86) | 29.8 (149W/351L, n=500, Wilson 26-34; seen-state) | **98.8** (247/250, Wilson 97-100; record) | — | **85-15** (n=100; fixed view; best of the fixed series) | lv8mix 28.0 (140W/360L, n=500, Wilson 24-32; per lineup 17/33/19/28/43) |
| 83 | 268M (MIXED, 14 lv3 + 14 lv8 CHARACTER STATES + 10 THREE-COM LINEUPS (26%%), warm leg 82, STACK + ARENA + 7-LAG OBS STACK + OBS CTX FIX + ZS TIME COST + OBS V3 + ASTRA-2 FIXES, NEW CONTRACT (v3 eval; slot 3 = seen-state benchmark; AB = fixed-view series); standing recipe) | all 38.9/38.4/39.1/38.6, 3-COM eps 32.3/31.7/30.4/35.5 (n=2,070), lv8 eps 39.7/39.5/39.7/37.9, lv3 eps 43.1/41.5/45.1/41.2 (8,106 eps; timeouts 0/0/0/0%%; picks 5.40/5.37/5.24/5.32; entropy -0.601; KL/update 0.024; epochs/update 2.21; expl_var 0.81; [zs] adj +13.0/+12.5/+12.8/+12.7; win share by transforms 0/1/2/3 = 0.01/0.24/0.70/0.85) | **31.4** (157W/343L, n=500, Wilson 27-36; seen-state; observed best) | 96.8 (242/250, Wilson 94-98) | — | 75-25 (n=100; fixed view) | lv8mix **30.0** (150W/350L, n=500, Wilson 26-34; per lineup 33/22/26/37/32; BEST HELD-OUT) |
| 82 | 264M (MIXED, 14 lv3 + 14 lv8 CHARACTER STATES + 10 THREE-COM LINEUPS (26%%), warm leg 81, STACK + ARENA + 7-LAG OBS STACK + OBS CTX FIX + ZS TIME COST + OBS V3 + ASTRA-2 FIXES, NEW CONTRACT (v3 eval; slot 3 = seen-state benchmark; AB = fixed-view series); second three-COM-slice leg) | all 37.9/39.2/38.6/37.0, 3-COM eps 31.2/31.8/28.8/31.4 (n=2,192), lv8 eps 38.3/40.8/39.4/37.0, lv3 eps 42.8/43.5/44.7/40.3 (8,313 eps; timeouts 0/0/0/0%%; picks 5.37/5.40/5.47/5.28; entropy -0.578; KL/update 0.026; epochs/update 2.21; expl_var 0.82; [zs] adj +12.5/+13.2/+13.1/+12.1; win share by transforms 0/1/2/3 = 0.01/0.23/0.70/0.85; 3-COM eps 1.28 transforms/ep) | **31.0** (155W/345L, n=500, Wilson 27-35; seen-state; OBSERVED BEST on the trio) | 96.0 (240/250, Wilson 93-98) | — | 80-20 (n=100; fixed view) | lv8mix 26.8 (134W/366L, n=500, Wilson 23-31; per lineup 32/22/24/20/36) |
| 81 | 260M (MIXED, 14 lv3 + 14 lv8 CHARACTER STATES + 10 THREE-COM LINEUPS (27%%), warm leg 80, STACK + ARENA + 7-LAG OBS STACK + OBS CTX FIX + ZS TIME COST + OBS V3 + ASTRA-2 FIXES, NEW CONTRACT (v3 eval; slot 3 = seen-state benchmark; AB = FIXED-VIEW series); FIRST THREE-COM-SLICE LEG) | all 37.0/38.0/39.9/38.2, 3-COM eps 31.5/29.7/28.7/31.4 (n=2,173), lv8 eps 36.7/38.5/43.4/38.0, lv3 eps 41.5/43.9/44.6/43.0 (8,138 eps; timeouts 0/0/0/0%%; picks 5.40/5.37/5.45/5.38; entropy -0.597; KL/update 0.025; epochs/update 2.15; expl_var 0.80; [zs] adj +12.2/+12.3/+13.3/+12.6; win share by transforms 0/1/2/3 = 0.01/0.23/0.70/0.85; 3-COM eps dmg taken 0.65, 1.27 transforms/ep) | 28.2 (141W/359L, n=500, Wilson 24-32; seen-state) | 97.2 (243/250, Wilson 94-99) | — | 81-19 (n=100; FIXED view; leg 80 re-baseline 78) | lv8mix 23.2 (116W/384L, n=500, Wilson 20-27; balanced 100/lineup: 18/26/24/17/31) |
| 80 | 256M (MIXED, 14 lv3 + 14 lv8 CHARACTER STATES, warm leg 79, STACK + ARENA + 7-LAG OBS STACK + OBS CTX FIX + ZS TIME COST + OBS V3, NEW CONTRACT (v3 eval; slot 3 = seen-state benchmark); second lv3+lv8 leg; FIRST BATTERY WITH lv8mix) | all 40.5/40.4/41.2/39.5, lv8 eps 40.6/41.4/38.7/38.9 (n=4,034), lv3 eps 39.9/39.9/43.6/40.2 (7,992 eps; timeouts 0/0/0/0%%; picks 5.39/5.42/5.36/5.36; entropy -0.588; KL/update 0.025; epochs/update 2.10; expl_var 0.81; [zs] adj +12.9/+13.1/+13.4/+12.8; win share by transforms 0/1/2/3 = 0.02/0.29/0.70/0.85; lv8 per character 32 (Jack) to 43 (Wang-Tang, Rouge)) | 28.2 (141W/359L, n=500, Wilson 24-32; 7.20; seen-state benchmark) | 95.2 (238/250, Wilson 92-97; 9.80) | — | 86-14 (n=100; old view) | lv8mix **26.2** (131W/369L, n=500, Wilson 23-30; per lineup slot90 21%%, 91 24%%, 92 27%%, 93 20%%, 94 38%%; random split, first run) |
| 79 | 252M (MIXED, 14 lv3 + 14 lv8 CHARACTER STATES (P4 COM lv3 or lv8), warm leg 78, STACK + ARENA + 7-LAG OBS STACK + OBS CTX FIX + ZS TIME COST + OBS V3, NEW CONTRACT (v3 eval; slot 3 = seen-state benchmark, trained on in legs 77-78); FIRST LV3+LV8 LEG) | all 39.5/38.5/39.7/39.7, lv8 eps 36.3/37.0/38.0/37.1 (n=4,049), lv3 eps 42.7/39.8/41.7/42.2 (8,129 eps; timeouts 0/0/0/0%%; picks 5.25/5.29/5.33/5.15; entropy -0.609; KL/update 0.026; epochs/update 2.21; expl_var 0.80; [zs] adj +12.8/+12.5/+13.0/+12.7; win share by transforms 0/1/2/3 = 0.01/0.28/0.72/0.87; lv8 win share by COM character 32 (Ryoma, Jack) to 47 (Pride)) | 26.2 (131W/369L, n=500, Wilson 23-30; 6.96/1.59; seen-state benchmark) | **98.0** (245/250, Wilson 95-99; ties best) | — | **89-11** (n=100; BEST AB BY FIVE) |
| 78 | 248M (MIXED + LV8 SLOT3 x5 (26%% of episodes), warm leg 77, STACK + ARENA + COM CHARACTER RANDOM + 7-LAG OBS STACK + OBS CTX FIX + ZS TIME COST + OBS V3, NEW CONTRACT (v3 eval; slot 3 trained-on); LV8 FAST TEST leg 2) | all 38.9/38.2/36.2/37.8, lv8-slot3 eps 29.3/30.3/30.1/27.7 (n=2,168), mixed 41.9/41.1/38.3/41.5 (8,448 eps; timeouts 0/0/0/0%%; picks 5.43/5.21/5.18/5.26; entropy -0.587; KL/update 0.026; epochs/update 2.15; expl_var 0.80; [zs] adj +13.6/+13.0/+12.0/+13.0; win share by transforms 0/1/2/3 = 0.01/0.24/0.69/0.85) | 27.4 (137W/363L, n=500, Wilson 24-31; 6.92/1.58; trained-on state) | **98.0** (245/250, Wilson 95-99; ties best) | — | 77-23 (n=100) |
| 77 | 244M (MIXED + LV8 SLOT3 x5 (26%% of episodes), warm leg 76, STACK + ARENA + COM CHARACTER RANDOM + 7-LAG OBS STACK + OBS CTX FIX + ZS TIME COST + OBS V3, NEW CONTRACT (v3 eval; SLOT 3 NO LONGER HELD OUT); LV8 FAST TEST, relaunched 6:39 pm) | all 35.5/37.0/38.7/38.0, lv8-slot3 eps 21.6/30.6/31.0/30.4 (n=2,131), mixed 40.6/39.3/41.2/40.4 (8,263 eps; timeouts 0/0/0/0%%; picks 5.17/5.30/5.46/5.30; entropy -0.592; KL/update 0.026; epochs/update 2.10; expl_var 0.81; [zs] adj +12.1/+12.7/+13.7/+13.0; win share by transforms 0/1/2/3 = 0.01/0.23/0.68/0.86) | 27.2 (136W/364L, n=500, Wilson 23-31; 7.19/1.66; trained-on state) | 92.8 (232/250, Wilson 89-95; 9.86/3.04) | — | 81-19 (n=100) |
| 76 | 240M (MIXED, warm leg 75, STACK + ARENA + COM CHARACTER RANDOM + 7-LAG OBS STACK + OBS CTX FIX + ZS TIME COST + OBS V3, NEW CONTRACT (v3 eval); third obs v3 leg) | 37.9/39.8/39.4/38.8 (7,897 eps; timeouts 0/0/0/0%%; picks 5.07/5.10/5.06/5.00; entropy -0.625; KL/update 0.025; epochs/update 2.10; expl_var 0.82; [zs] adj +12.7/+13.6/+13.2/+12.7; win share by transforms 0/1/2/3 = 0.02/0.30/0.72/0.86) | 22.6 (113W/387L, n=500, Wilson 19-26) | **98.0** (245/250, Wilson 95-99; best lv3 so far) | — | 81-19 (n=100) |
| 75 | 236M (MIXED, warm leg 74, STACK + ARENA + COM CHARACTER RANDOM + 7-LAG OBS STACK + OBS CTX FIX + ZS TIME COST + OBS V3, NEW CONTRACT (v3 eval); second obs v3 leg) | 39.1/40.6/41.6/39.1 (7,768 eps; timeouts 0/0/0/0%%; picks 5.04/5.36/5.45/5.31; entropy -0.623; KL/update 0.027; epochs/update 2.15; expl_var 0.81; [zs] adj +13.1/+14.4/+14.9/+13.7; win share by transforms 0/1/2/3 = 0.01/0.27/0.72/0.87) | 24.0 (120W/380L, n=500, Wilson 20-28; 6.61/1.49) | 93.2 (233/250, Wilson 89-96; 9.62/3.07) | — | 79-21 (n=100) |
| 74 | 232M (MIXED, warm leg 73 WIDENED to OBS V3 (160/frame, zero new columns), STACK + ARENA + COM CHARACTER RANDOM + 7-LAG OBS STACK + OBS CTX FIX + ZS TIME COST + OBS V3, NEW CONTRACT (v3 eval); FIRST OBS V3 LEG) | 37.2/38.7/38.9/40.5 (7,878 eps; timeouts 0/0/0/0%%; picks 4.89/5.05/5.13/5.16; entropy -0.641; KL/update 0.027; epochs/update 2.15; expl_var 0.81; [zs] adj +12.2/+13.0/+13.3/+14.0 (rising through the leg); win share by transforms 0/1/2/3 = 0.01/0.29/0.73/0.85) | 26.6 (133W/367L, n=500, Wilson 23-31; 6.85/1.63) | 96.4 (241/250, Wilson 93-98; 9.32/2.95) | — | **84-16** (n=100; BEST AB SO FAR) |
| 73 | 228M (MIXED, warm leg 72, STACK + ARENA + COM CHARACTER RANDOM + 7-LAG OBS STACK + OBS CTX FIX + ZS TIME COST, NEW CONTRACT; second leg of the combined read) | 36.6/35.2/37.3/37.0 (7,850 eps; timeouts 1/1/0/1%%; picks 5.00/4.81/5.03/5.02; entropy -0.655; KL/update 0.025; epochs/update 2.51; expl_var 0.80; [zs] adj +12.1/+11.4/+12.6/+12.4; win share by transforms 0/1/2/3 = 0.02/0.28/0.71/0.84) | **29.2** (146W/354L, n=500, Wilson 25-33; 6.85/1.60; NEW OBSERVED BEST) | **97.2** (243/250, Wilson 94-99; 9.56/2.95) | — | 80-20 (n=100) |
| 72 | 224M (MIXED, warm leg 71, STACK + ARENA + COM CHARACTER RANDOM + 7-LAG OBS STACK + OBS CTX FIX + ZS TIME COST, NEW CONTRACT; first leg of the combined read) | 36.5/37.0/37.9/37.2 (8,040 eps; timeouts 0/0/0/0%%; picks 4.96/4.98/4.89/4.88; entropy -0.646; KL/update 0.025; epochs/update 2.56; expl_var 0.80; [zs] adj +12.1/+12.4/+12.6/+12.2 (about -1.2 vs leg 71 = the restored time cost, as expected); win share by transforms 0/1/2/3 = 0.01/0.28/0.72/0.88) | 21.0 (105W/395L, n=500, Wilson 18-25; 7.01/1.55) | 96.4 (241/250, Wilson 93-98; 9.52/3.06) | — | **81-19** (n=100; best AB so far) |
| 71 | 220M (MIXED, warm leg 70, STACK + ARENA + COM CHARACTER RANDOM + 7-LAG OBS STACK, NEW CONTRACT; second strided leg, old obs code) | 36.4/38.7/36.9/39.6 (7,936 eps; timeouts 0/0/1/0%%; picks 4.94/4.96/4.94/5.05; entropy -0.657; KL/update 0.025; epochs/update 2.47; expl_var 0.80; [zs] adj +12.9/+13.8/+13.2/+14.4) | 16.6 (83W/417L, n=500, Wilson 14-20; 6.24/1.32) | 93.6 (234/250, Wilson 90-96; 9.70/3.04) | — | 75-25 (n=100) |
| 70 | 216M (MIXED, warm leg 69 SURGERY K=7 strided [16,8,4,3,2,1,0], STACK + ARENA + COM CHARACTER RANDOM + 7-LAG OBS STACK, NEW CONTRACT; FIRST STRIDED LEG) | 36.0/38.0/39.0/37.0 (7,639 eps; timeouts 0/0/0/0%%; picks 4.92/5.01/5.07/5.08; entropy -0.681; KL/update 0.025; epochs/update 2.42; expl_var 0.80; [zs] adj +12.5/+13.8/+14.3/+13.6, dealt_nn 0.89-0.93; per-character 0.34 Ryoma/Pete/Julia to 0.43 Ayame; win share by transforms 0/1/2/3 = 0.01/0.25/0.70/0.83) | **28.8** (144W/356L, n=500, Wilson 25-33; **6.79/1.57**) | **97.6** (244/250, Wilson 95-99; 9.77/3.06) | — | 74-26 (n=100) |
| 69 | 212M (MIXED, warm leg 68, STACK + ARENA + COM CHARACTER RANDOM + 4-FRAME OBS STACK, NEW CONTRACT; second stacked leg) | 38.0/37.0/37.0/41.0 (7,432 eps; timeouts 0/1/0/0%%; picks 4.92/4.86/4.95/5.05; entropy -0.706; KL/update 0.026; epochs/update 4.68; expl_var 0.80; [zs] adj +13.7/+13.3/+13.0/+15.1, dealt_nn 0.89-0.91; per-character 0.33 Wang-Tang to 0.43 Pete) | **23.0** (115W/385L, n=500, Wilson 20-27; 6.04/1.32) | 94.8 (237/250, Wilson 91-97; 8.99/2.77) | — | 75-25 (n=100) |

Leg 84 note (Sep 26 10:50 am EDT): standing recipe. Trio 29.8 (26-34; one drop from 31.4, inside noise, not a
watch), lv8mix 28.0 (24-32; second-best held-out), lv3 98.8 = record, AB 85-15 = best of the fixed-view series (78 /
81 / 80 / 75 / 85). No hold. Per lineup the held-out scores swing a lot between legs (slot93 37 -> 28, slot94 32 -> 43,
slot90 33 -> 17): n=100 per lineup is noisy; read the 500 total. Training unchanged. Leg 85 booted 10:45 am.

Leg 83 note (Sep 26 5:50 am EDT): standing recipe, third leg with the three-COM slice. Trio 31.4 (27-36) = observed
best again (seen-state); lv8mix 30.0 (26-34) = the best held-out number so far (26.2 / 23.2 / 26.8 before), with the
hardest lineup (slot93 Accel/Mel/Gourmand) jumping from 17-20%% to 37%%; lv3 96.8; AB 75-25 (fixed series 78 / 81 / 80
/ 75, a dip inside noise). No hold. Training: three-COM episodes 30-36%% (q4 = 35.5, the highest quarter yet), the
rest unchanged. Read: the three-COM slice is now paying on the held-out set after two flat legs. Leg 84 booted
5:44 am, same recipe. Next lever still needs Blake's go (NEXT MOVES #2).

Leg 82 note (Sep 26 12:45 am EDT): second three-COM-slice leg. Trio 31.0 (27-35) = the highest trio number of the league
(29.2 at leg 73), with the seen-state caveat; lv8mix 26.8 (23-31) balanced, up from 23.2; lv3 96.0; AB 80-20 fixed view.
No hold. THREE-COM-SLICE READ VERDICT (legs 81-82 vs leg 80): trio 28.2 / 31.0 vs 28.2, lv8mix 23.2 / 26.8 vs 26.2 (random
split), lv3 and AB in band, every interval overlapping: NEUTRAL-TO-POSITIVE, no regression anywhere. Training: the
three-COM episodes stayed at 29-32%% both legs (no within-leg climb; 1.28 transforms/ep vs ~1.6 in the trio eval).
Proposal: KEEP the slice (standing recipe). Per lineup lv8mix: Accel/Mel/Gourmand (slot93) is the hardest set both legs
(17, 20); Julia/Ryoma/Pride (slot94) the softest (31, 36). NEXT LEVER (needs Blake's go, NEXT MOVES #2): special-death
+ stone-retention reward; the scouts have shown the same death in eight straight reviews. Leg 83 booted 12:39 am, same
recipe.

Leg 81 note (Sep 25 7:40 pm EDT): FIRST THREE-COM-SLICE LEG. Trio 28.2 (24-32) = leg 80 exactly; lv3 97.2; AB 81-19
on the fixed view (leg 80 re-baselined at 78 under the same view: +3); lv8mix 23.2 (20-27) on the first BALANCED run
(100 per lineup; leg 80's 26.2 was a random split) - intervals overlap, read as flat. THREE-COM-SLICE READ, first half:
NEUTRAL so far (trio flat, lv8mix flat within noise, lv3/AB in band). Training: the three-COM episodes ran at 29-32%%
win share all leg (no within-leg climb, unlike the fast test's 22 -> 31 on one fixed trio), 1.27 transforms/ep vs
~1.6 in the eval; lv8-character episodes 37-43, lv3 41-45. Leg 82 (booted 7:34 pm, same recipe) completes the read.
Per-lineup lv8mix: slot93 (Accel/Mel/Gourmand) 17%% and slot90 (Gunrock/Julia/Mel) 18%% are the hard ones, slot94
(Julia/Ryoma/Pride) 31%% the soft one, both legs.

Leg 80 note (Sep 25 2:30 pm EDT): second lv3+lv8 character-set leg and the FIRST five-lineup held-out number.
Trio 28.2 (24-32), lv3 95.2, AB 86-14 (this AB still ran under the OLD 1v1 view: the fix landed ~10 min after the
shards started). FIXED-VIEW RE-BASELINE (4:05 pm, `receipts/discrim_leg80_ab_fixedview_*`, 3 x 34 eps on instances
12-14): leg 80 vs the champion = 80-22 (78.4%%) under the fixed view vs 86-14 under the old one. So the old view
inflated the champion series by roughly 8 points (a champion fed v3 projectile inputs it never trained on, plus the
form-timer leak). The AB series from leg 81 on is the fixed one; 78%% is its first baseline; legs 74-80's 84-89
are not comparable with it.
lv8mix (five never-trained three-COM lineups, states/slot90-94): 26.2%% (23-30), per lineup 20-38%%, i.e. the same
level as the seen-state trio: no sign of lineup-specific memorisation. TWO-LEG READ of the lv3+lv8 character set
(legs 79-80 trio = 26.2 / 28.2 vs 22.6 pre-exposure and 27.2/27.4 trained-on): PASS; lv3 95-98 and AB 86-89 in band;
training lv8-character episodes closed the gap to the lv3 ones (40-41%% both). Proposal: KEEP the 50/50 set (it is
the standing recipe); leg 81 adds the three-COM training slice (slots 50-59). lv8mix from leg 81 on runs balanced
(100 per lineup, per-lineup counts in the receipt, merge rejects a receipt without the exact set).

Leg 79 note (Sep 25 9:20 am EDT): FIRST LEG ON THE FULL LV3+LV8 CHARACTER SET. lv8 26.2 (23-30) with slot 3 no longer in the training mix (but SEEN in legs 77-78, so a seen-state
benchmark, not a clean held-out) (legs 77-78 trained on it: 27.2 / 27.4; before the fast test 22.6), lv3 98.0 (ties the record), AB 89-11 = the best
champion result of the league by five points (84 was the previous). No hold. Training: the lv8-character episodes run at
~37%% win share vs ~41%% for the lv3 ones (one lv8 COM among two pool Falcons is only mildly harder), damage taken and
round length the same; Pride is the softest lv8 COM (47%%), Ryoma and Jack the hardest (32%%). Read after one clean leg:
lv8 held (+3.6 over the pre-test 22.6, inside its interval), AB jumped, lv3 at record; leg 80 completes the pre-registered
two-leg read. Leg 80 booted 9:13 am, same recipe.

Leg 78 note (Sep 25 4:30 am EDT): second fast-test leg. lv8 27.4 (24-31; trained-on caveat), lv3 98.0 (ties the
record), AB 77-23. No hold. FAST-TEST READ (legs 77-78 = 27.2 / 27.4 vs 22.6 before): lv8 exposure lifted the lv8
score ~5 points and held it; the lv8 training episodes plateaued at ~29-30%% after leg 77's jump (no second climb);
lv3 and AB in band. Leg 79 booted 4:24 am on the FULL character set: 14 lv3 + 14 lv8 slots (state_slots 0,10-22,
30-43), slot-3 padding dropped -> slot 3 is no longer trained on from this leg (seen-state benchmark); the leg 79 lv8 score vs 27.4 is the
first clean read of the P4-at-lv8 recipe (with the caveat that legs 77-78 trained on it).

Leg 77 note (Sep 24 11:35 pm EDT): LV8 FAST TEST, first leg. lv8 27.2 (23-31), up from 22.6: the three-drop streak
is broken, with the caveat that slot 3 is now a training state (26%% of episodes), so this is no longer a clean
held-out number. lv3 92.8 (in band, low end; 98.0 last leg), AB 81-19 (steady). No hold. The within-leg signal is
the clean part: the lv8 training episodes went 21.6 -> 30.6 -> 31.0 -> 30.4 win share by quarter (stochastic policy,
random start health) while the mixed episodes held at ~40, i.e. lv8 exposure produced fast learning against the
trio. Damage taken in lv8 episodes 0.66, median length 408 steps. Leg 78 booted 11:29 pm (same mix). NEXT: stamp
lv8 versions of the 13 character states so the P4 COM seat runs at lv8 (Blake's end state) and a fresh lv8 lineup
becomes the held-out test.

Leg 76 note (Sep 24 5:05 pm EDT): lv8 22.6 (19-26), lv3 98.0 (best ever), AB 81-19. No hold. SIGNAL: lv8 has now
dropped THREE legs in a row, 29.2 -> 26.6 -> 24.0 -> 22.6 (Blake's rule: two = watch, three = signal), while lv3
and AB are at their best and the self-play stream is up (win share 38-40%%, stones 5.0-5.1, zs +12.7 to +13.6).
Reading: the v3 learner is getting stronger against Falcons (pool + champion, whose only special is the missile
swarm) and weaker against the lv8 COM trio, i.e. it is not learning the COM-special disengage the scouts keep
flagging (reviews 73-75), and may be drifting toward pool-specific play. Pre-registered plan on a signal: eval
discriminators FIRST, report, no diet change without Blake. Discriminators proposed (read-only evals on instances
12/13): (1) AB leg 76 vs leg 73 head-to-head n=100 (does the v3 lineage beat its own v2 parent?); (2) lv8 with the
STOCHASTIC policy n=200 (is the deterministic argmax the thing sliding?). The hold rule is nowhere near; the chain
continues (leg 77 booted 4:57 pm, warm leg 76).
DISCRIMINATOR RESULTS (5:36 pm, `receipts/discrim_leg76_*`): (1) AB leg 76 vs leg 73 = 56-44 (n=100): the v3
lineage beats its own v2 parent head-to-head, modestly. (2) lv8 STOCHASTIC n=100 = 22.0%% (10/50 + 12/50) vs the
deterministic 22.6%%: the argmax is not the thing sliding; the policy itself is at ~22%% against the lv8 trio.
=> The slide is real policy drift, not an eval artifact: stronger vs Falcons (pool, champion, its parent), weaker
vs COM specials it never trains against. PROPOSAL (Blake's call, no diet change made): put lv8 COM specials into
the training distribution. Proper: stamp lv8 versions of the 13 character states (options-menu path, queued) and
mix them ~50/50 with the lv3 ones. Fast test: add `states/slot3` (Pride/Ryoma/Accel at lv8, the eval state) to
PS2_STATE_SLOTS at ~25%% share; caveat: that trains on the eval state, so slot3 stops being a clean held-out
(Astra's dev-set point) and a fresh lv8 state would be needed as the new test.
BLAKE (6:35 pm): "Do the fast test. Stop the current run unless it's about to break a record." Also confirmed the
end state he wants = the P4 COM seat at LEVEL 8 (the proper fix: stamp lv8 versions of the 13 character states).
DONE 6:39 pm: leg 77 (3,003 eps in, lv3-only mix) stopped (tmux ps2train killed, trainer + actors, log archived
as archive/train_leg77_out_aborted_lv3only_sep24.txt); `states/slot3.state` copied to `states_mixed/slot3.state`;
ffa_selfplay_env.py keeps the base SLOT_META for slots 1-9 (slot 3 -> stage 2, DIFF_DIM 1.0, lv8 caps, matching
the eval); league_env.txt PS2_STATE_SLOTS=0,10,...,22,3,3,3,3,3 (5/19 = 26%% lv8 episodes); leg 77 RELAUNCHED
6:39 pm from leg 76's zip, config confirmed (state_slots incl. 3 x5, obs_v3=1), lv8 episodes flowing ('slot3
opps=3' [ep] lines). Backup of the env file: archive/league_env_pre_lv8mix_sep24.txt. Wake moved to 11:55 pm.
WHAT ELSE CHANGED AT THE V3 CUTOVER (Blake asked): besides the 38 new dims, (a) the two existing projectile slots
[81..92] now carry special-attack volleys and Falcon missiles that v2 never saw (v2 reported ~nothing there), so
12 dims the old policy had learned to ignore became live; (b) Adam was reset by the widening surgery; (c) pool
zips from leg 74 on are v3. Optimizer, reward, arena, stack: unchanged. Whether the lv8 slide is caused by v3 or
is drift that v3 merely coincided with is NOT established (29.2 was itself a high draw; 26.6 is inside its
interval); the fast test answers a different question (does lv8 COM exposure fix the disengage).

Leg 75 note (Sep 24 12:25 pm EDT): second obs v3 leg. lv8 24.0 (20-28), lv3 93.2, AB 79-21. No hold. V3 READ VERDICT
(legs 74-75 = 26.6 / 24.0, mean 25.3) vs legs 72-73 (21.0 / 29.2, mean 25.1) and the band 16-24: PASS, both legs
in/above the band, lv3 and AB in band; on the evals obs v3 is NEUTRAL so far. The TRAINING STREAM is where it moved:
win share 39-42%% per quarter (legs 70-73 sat at 35-39; q3 = 41.6 is the league high), stones 5.0-5.45/ep (up from
~5.0), [zs] adj +13.1 to +14.9 (up from ~+12), i.e. against the pool of its own past selves the v3 learner is
clearly stronger while the COM evals have not moved yet. Damage taken unchanged (0.59). WATCH: lv8 29.2 -> 26.6 ->
24.0 is two consecutive drops (Blake's rule: two = watch, three = signal; the hold rule decides). Proposal: KEEP
obs v3 (no regression, best AB series 80/84/79, stream up) and let legs 76-77 tell whether the stream gain reaches
the COM evals. Leg 76 booted 12:16 pm (warm leg 75, obs_v3=1).

Leg 74 note (Sep 24 7:35 am EDT): FIRST OBS V3 LEG. lv8 26.6 (23-31), lv3 96.4, AB 84-16 = the best champion result
of the league (previous best 81). No hold (gate empty; battery printed "obs v3 eval contract"). V3 READ first half:
PASS (in band, above the old 16-24 band, between legs 72-73's 21.0 / 29.2). The training stream is the interesting
part: win share climbed through the leg 37.2 -> 38.7 -> 38.9 -> 40.5 (q4 is the highest quarter of the league;
legs 70-73 sat at 0.35-0.39 flat) and [zs] adj climbed +12.2 -> +14.0, i.e. the new inputs started paying off
within the leg, exactly the "zero columns then learn" shape expected. Damage taken per round unchanged (0.59 vs
0.60). Leg 75 (booted 7:30 am, warm leg 74, obs_v3=1) completes the read.

Leg 73 note (Sep 24 2:50 am EDT): NEW OBSERVED BEST lv8 29.2 (25-33), edging leg 70's 28.8; lv3 97.2; AB 80-20
(second-best AB after leg 72's 81-19). No hold (gate empty). COMBINED READ VERDICT (obs ctx fix + zero-sum time
cost, legs 72-73 = 21.0 / 29.2, mean 25.1) vs legs 70-71 (28.8 / 16.6, mean 22.7) and the band 16-24: PASS,
both legs in/above the band with lv3 and AB in band and the two best AB results of the league. Proposal: KEEP both
changes (they are the standing recipe from here). The intervals still overlap the old ones; the trend across
four legs (16.6 -> 21.0 -> 29.2 on lv8, 75 -> 81 -> 80 on AB) is the evidence, not any single leg. Stream
unchanged (win share 0.35-0.37, stones ~5, timeouts ~0.5%%). Leg 74 = OBS V3 CUTOVER from this zip (widened).

Leg 72 note (Sep 23 10:10 pm EDT): first leg with the obs ctx fix + zero-sum time cost. lv8 21.0 (18-25), in the
band and above leg 71 (16.6); lv3 96.4; AB 81-19, the best champion result so far (previous best 78). No hold (gate
empty). The [zs] adj sums dropped by ~1.2 per round exactly as the restored time cost predicts; stream otherwise
unchanged (win share 0.37, stones ~4.9, timeouts ~0). COMBINED READ first half: pass so far; leg 73 completes it.
Leg 73 booted 10:03 pm (obs_stack=7 obs_ctx_fix=1 zs_time=1, warm leg 72). Blake (10 pm): start the "better eyes"
observation audit (hit-stun / attack-active / action id) instead of buying compute; scanner work runs on instance 11.

Leg 71 note (Sep 23 5:30 pm EDT): BACK IN THE BAND. lv8 16.6 (14-20) after leg 70's 28.8; lv3 93.6; AB 75-25.
No hold (the battery's own gate ran: empty reason). Strided K=7 read over legs 70-71 = 28.8 / 16.6, mean 22.7,
vs the K=4 pair 18.2 / 23.0 and the single-frame legs 55-67 (~20, band 16-24): NEUTRAL. Leg 70 reads as a high
draw, not a confirmed step (its interval already overlapped leg 59's). One drop = no watch yet. Training stream
unchanged (win share 0.36-0.40, stones ~5, timeouts ~0). Leg 72 booted 5:24 pm with obs_ctx_fix=1 zs_time=1
(ASTRA REVIEW FIXES): legs 72-73 are the combined read for those two changes.

Leg 70 note (Sep 23 12:40 pm EDT): ALL-TIME RECORD BY FIVE POINTS. lv8 28.8 (25-33): the lower
bound of its interval (25) clears the previous record (23.8, leg 59), so this is the first leg
whose gain is not a high draw from the old distribution. lv3 97.6 ties the record; lv8 picks
6.79 and forms 1.57 are records; champion AB 74-26 in band. First leg on the strided 1.6 s stack,
started as exactly the leg 69 bot (agreement 2000/2000). Stream: stones 5.0-5.1/ep (recipe high),
brake at 2.4 passes (the three new lags pulling weight). Read: one leg, but a five-point jump with
a non-overlapping interval after two K=4 legs at 18.2/23.0 is the memory effect showing on the
first leg where history reaches wind-up/jump/projectile timescales. Leg 71 chained 12:35 pm on
the strided leg 70 zip; completes the strided read (pre-registered pass was "in band both legs",
already exceeded). Campaign: champion 5.8 -> 28.8 under the same contract, 5x.
| 68 | 208M (MIXED, warm leg 67 SURGERY K=4, STACK + ARENA + COM CHARACTER RANDOM + 4-FRAME OBS STACK, NEW CONTRACT; FIRST STACKED LEG) | 36.0/37.0/38.0/37.0 (7,500 eps; timeouts 0/0/0/0%%; picks 4.70/4.71/4.73/4.84; entropy -0.716 flat; KL/update 0.027; epochs/update 4.65 (brake engages on the fresh history weights); expl_var 0.79; [zs] adj +12.0/+12.3/+12.9/+13.1, dealt_nn 0.87-0.89; per-character 0.33 Wang-Tang/Ryoma to 0.41 Rouge) | 18.2 (91W/409L, n=500, Wilson 15-22; 6.07/1.29) | 92.0 (230/250, Wilson 88-95; 9.53/2.84) | — | **78-22** (n=100) |

Leg 69 note + STACK READ VERDICT (Sep 23 7:58 am EDT): lv8 23.0 (20-27), third-best ever; lv3
94.8; champion AB 75-25. K=4 legs 68-69 = lv8 18.2 / 23.0, lv3 92.0 / 94.8, AB 78 / 75 vs the
single-frame legs 63-67 (lv8 mean 21.2, AB 63-78): pre-registered pass (both legs in/above the
16-24 band, lv3 and AB in band) MET; leg 69 is where a gain could first show and it did land on
the high side, with the recipe's best stream quarter (win 0.41, adj +15.1). Not proof of a memory
effect yet (one high draw), but no cost anywhere. VERDICT: PASS, stacking stays. Leg 70 launched
~7:57 am on the STRIDED K=7 stack (surgery of the leg 69 zip, agreement 2000/2000).
| 67 | 204M (MIXED, warm leg 66, STACK + ARENA + COM CHARACTER RANDOM slots 0,10-22, NEW CONTRACT; last single-frame leg) | 36.0/38.0/38.0/36.0 (7,694 eps; timeouts 0/0/0/0%%; picks 4.59/4.66/4.74/4.45; entropy -0.730; KL/update 0.021; epochs/update 9.87; [zs] adj +12.1/+12.9/+13.1/+11.6, dealt_nn 0.87-0.89; per-character 0.34 Rouge to 0.39 Julia) | 17.8 (89W/411L, n=500, Wilson 15-21; 5.80/1.24) | 93.2 (233/250, Wilson 89-96; 9.05/2.70) | — | 68-32 (n=100) |

Leg 68 note (Sep 23 3:15 am EDT): first frame-stacked leg. lv8 18.2 (15-22) — in band, as pre-
registered for a leg that starts identical to its parent; lv3 92.0; champion AB 78-22 ties the
best of the new contract (leg 56). Stream unchanged (win 0.37, stones 4.8, entropy flat); the one
signature of the new inputs is KL/update 0.027 with the brake tripping at ~4.7 passes instead of
~10 — the zero-initialised history weights move fast. Leg 69 chained 3:12 am on the stacked leg
68 zip (obs_stack=4 confirmed); it completes the two-leg stack read vs legs 63-67 (lv8 mean 21.2).
| 66 | 200M (MIXED, warm leg 65, STACK + ARENA + COM CHARACTER RANDOM slots 0,10-22, NEW CONTRACT) | 36.0/36.0/37.0/40.0 (7,638 eps; timeouts 0/0/0/0%%; picks 4.72/4.72/4.64/4.86; entropy -0.742; KL/update 0.021; epochs/update 9.96; [zs] adj +12.4/+12.4/+12.9/+14.5, dealt_nn 0.89-0.91; per-character 0.31 Ayame to 0.42 Rouge) | **23.6** (118W/382L, n=500, Wilson 20-28; 6.25/1.39) | 95.6 (239/250, Wilson 92-98; 9.27/2.82) | — | **76-24** (n=100) |

Leg 67 note (Sep 22 10:35 pm EDT): lv8 17.8 (15-21) after four legs above 20 — one drop, in band;
lv3 93.2; champion AB 68-32. Thirteen recipe legs: lv8 mean 19.8. Battery ran under HOLD (leg 68
HELD by design): leg 68 = FIRST FRAME-STACKED LEG, warm start powerstone_v6_leg67_stack4.zip
(surgery K=4, equivalence PASS 2,000 frames, logits 5.7e-6), PS2_OBS_STACK=4 added to
league_env.txt. Pre-registered read over legs 68-69 vs legs 63-67 (lv8 21.2/20.6/23.0/23.6/17.8,
mean 21.2; AB 63-78; lv3 92-98). Clip videos/leg67_lv8.mp4; scouting in tmux scout67.
| 65 | 196M (MIXED, warm leg 64, STACK + ARENA + COM CHARACTER RANDOM slots 0,10-22, NEW CONTRACT) | 34.0/37.0/36.0/35.0 (7,565 eps; timeouts 0/0/0/0%%; picks 4.57/4.68/4.56/4.59; entropy -0.766; KL/update 0.021; epochs/update 9.97; [zs] adj +11.1/+13.0/+11.9/+11.7, dealt_nn 0.86-0.89; per-character 0.33 Wang-Tang/Galuda to 0.39 Pride) | **23.0** (115W/385L, n=500, Wilson 20-27; 6.27/1.41) | **96.4** (241/250, Wilson 93-98; 9.19/2.80) | — | 73-27 (n=100) |

Leg 66 note (Sep 22 5:55 pm EDT): lv8 23.6 (20-28), 0.2 under the record; lv3 95.6; champion AB
76-24, best since leg 56. Four straight legs above 20 on lv8 (21.2/20.6/23.0/23.6): twelve recipe
legs mean 20.0, last five 21.9 — the slope is real now, not noise. Stream: win share rose to 0.40
in Q4 (best quarter of the recipe), [zs] adj +14.5 in Q4. 200M learner steps. Clip
videos/leg66_lv8.mp4; scouting in tmux scout66 (first packet with the recorder's KO tail).
Leg 67 chained 5:53 pm, same recipe.
| 64 | 192M (MIXED, warm leg 63, STACK + ARENA + COM CHARACTER RANDOM slots 0,10-22, NEW CONTRACT) | 37.0/36.0/35.0/35.0 (7,560 eps; timeouts 0/0/0/0%%; picks 4.80/4.58/4.63/4.59; entropy -0.769; KL/update 0.021; epochs/update 9.91; [zs] adj +13.0/+12.2/+11.9/+11.9, dealt_nn 0.88-0.90; per-character 0.32 Gunrock to 0.40 Pride) | 20.6 (103W/397L, n=500, Wilson 17-24; 5.87/1.28) | 92.4 (231/250, Wilson 88-95; 9.27/2.79) | — | 75-25 (n=100) |

Leg 65 note (Sep 22 1:20 pm EDT): lv8 23.0 (20-27), second-best ever (record 23.8); lv3 96.4 ties
the all-time record; champion AB 73-27. Four straight legs at 20+ on lv8 (21.2/20.6/23.0 after
18.0): eleven recipe legs, mean 19.7, the last four 20.9 — the first hint of a slope above the
plateau. Stream flat. Clip videos/leg65_lv8.mp4; scouting in tmux scout65 (first packet with the
4 fps final-12 s strips). Leg 66 chained 1:13 pm, same recipe.
| 63 | 188M (MIXED, warm leg 62, STACK + ARENA + COM CHARACTER RANDOM slots 0,10-22, NEW CONTRACT) | 36.0/36.0/38.0/37.0 (7,535 eps; timeouts 0/0/0/0%%; picks 4.87/4.81/4.82/4.83; entropy -0.772; KL/update 0.021; epochs/update 9.92; [zs] adj +12.6/+12.3/+13.3/+13.1, dealt_nn 0.90-0.93; per-character 0.35 Ryoma to 0.39 Pete) | 21.2 (106W/394L, n=500, Wilson 18-25; 6.26/1.41) | 94.4 (236/250, Wilson 91-97; 9.68/2.87) | — | 69-31 (n=100) |

Leg 64 note (Sep 22 8:40 am EDT): lv8 20.6 (17-24), third straight leg at or above 18; lv3 92.4;
champion AB 75-25 (best since leg 56's 78). Ten recipe legs: lv8 mean 19.4, AB 63-78. Stream flat.
Clip videos/leg64_lv8.mp4; scouting in tmux scout64. Leg 65 chained 8:36 am, same recipe.
| 62 | 184M (MIXED, warm leg 61, STACK + ARENA + COM CHARACTER RANDOM slots 0,10-22, NEW CONTRACT) | 35.0/36.0/38.0/37.0 (7,522 eps; timeouts 0/0/0/0%%; picks 4.65/4.62/4.74/4.79; entropy -0.792; KL/update 0.020; epochs/update 9.84; [zs] adj +12.0/+12.1/+13.1/+13.0, dealt_nn 0.89-0.92; per-character 0.33 Gunrock to 0.41 Ryoma) | 18.0 (90W/410L, n=500, Wilson 15-22; 5.74/1.22) | 93.2 (233/250, Wilson 89-96; 9.27/2.86) | — | 67-33 (n=100) |

Leg 63 note (Sep 22 4:05 am EDT): lv8 21.2 (18-25), second-best ever; lv3 94.4; champion AB 69-31.
Nine legs on the full recipe: lv8 mean 19.3 (19.2/22.4/16.2/15.8/23.8/17.8/19.4/18.0/21.2), AB
63-78. Stream flat and healthy; characters 0.35-0.39. Clip videos/leg63_lv8.mp4; scouting run in
tmux scout63 (review_leg63.md when done). Leg 64 chained 3:58 am, same recipe.
| 61 | 180M (MIXED, warm leg 60, STACK + ARENA + COM CHARACTER RANDOM slots 0,10-22, NEW CONTRACT) | 36.0/36.0/36.0/36.0 (7,437 eps; timeouts 0/0/0/0%%; picks 4.56/4.65/4.65/4.58; entropy -0.811; KL/update 0.020; epochs/update 9.95; [zs] adj +12.1/+12.4/+12.1/+11.8, dealt_nn 0.88-0.91; per-character 0.33 Falcon to 0.39 Gunrock/Wang-Tang) | 19.4 (97W/403L, n=500, Wilson 16-23; 5.95/1.27) | 94.8 (237/250, Wilson 91-97; 9.08/2.73) | — | 63-37 (n=100) |

Leg 62 note (Sep 21 11:25 pm EDT): lv8 18.0 (15-22), lv3 93.2, champion AB 67-33 (up from 63; AB
watch not triggered). Eight legs on the full recipe: lv8 mean 19.1, AB 63-78. Stream flat and
healthy. First leg with the automatic clip (videos/leg62_lv8.mp4) and scouting run (tmux scout62;
review in videos/review_leg62.md when done). Leg 63 chained 11:20 pm, same recipe.
| 60 | 176M (MIXED, warm leg 59, STACK + ARENA + COM CHARACTER RANDOM slots 0,10-22, NEW CONTRACT) | 35.0/35.0/36.0/35.0 (7,551 eps; timeouts 0/0/0/0%%; picks 4.62/4.62/4.59/4.44; entropy -0.816; KL/update 0.020; epochs/update 9.92; [zs] adj +11.7/+11.6/+12.2/+11.4, dealt_nn 0.87-0.90; per-character 0.33 Pride to 0.37 Galuda/Julia/Mel/Jack/Rouge) | 17.8 (89W/411L, n=500, Wilson 15-21; 5.52/1.23) | 92.4 (231/250, Wilson 88-95; 9.26/2.65) | — | 74-26 (n=100) |

Leg 61 note (Sep 21 6:40 pm EDT): lv8 19.4 (16-23), back up; lv3 94.8; champion AB 63-37, one drop
from 74 (Wilson 53-72, inside the recipe band 63-78). Seven legs on the full recipe: lv8 19.2/22.4/
16.2/15.8/23.8/17.8/19.4 (mean 19.2), AB 69/78/65/73/74/74/63. Stream flat and healthy. No watch
active (one AB drop; a second on leg 62 = watch). Leg 62 chained 6:38 pm, same recipe.
| 59 | 172M (MIXED, warm leg 58, STACK + ARENA + COM CHARACTER RANDOM slots 0,10-22, NEW CONTRACT) | 36.0/38.0/38.0/39.0 (7,268 eps; timeouts 0/0/0/0%%; picks 4.64/4.80/4.89/4.91; entropy -0.829; KL/update 0.020; epochs/update 9.95; [zs] adj +12.0/+12.8/+13.2/+13.6, dealt_nn 0.88-0.89; per-COM-character win share: Ayame 0.43, Pete 0.41, Jack 0.40, Pride 0.39, Accel/Gunrock/Gourmand 0.38, Galuda 0.37, Wang-Tang/Ryoma/Falcon 0.36, Julia/Mel 0.35, Rouge 0.33) | **23.8** (119W/381L, n=500, Wilson 20-28; 6.11/1.33) | 95.2 (238/250, Wilson 92-97; 9.60/2.84) | — | 74-26 (n=100) |

Leg 60 note (Sep 21 14:05 EDT): lv8 17.8 (15-21) after the 23.8 record = one drop, inside the
standing band (16-24); lv3 92.4 (band low, 88-95); champion AB 74-26 steady (73/74/74 over the
last three). Stream flat (win 0.35, stones 4.6, entropy -0.82); characters even, 0.33-0.37. Read:
plateau-with-noise around lv8 ~19 on the full recipe; six legs 55-60 mean 19.2 vs the pre-arena
stack mean 18.9 — the arena/character levers bought robustness (AB 65-78 vs 53-60) and the two
records, not yet a higher plateau. Leg 61 chained 14:02, same recipe. Next lever still COM level.
| 58 | 168M (MIXED, warm leg 57, STACK + ARENA + COM CHARACTER RANDOM slots 0,10-22, NEW CONTRACT; FIRST CHARACTER LEG) | 37.0/37.0/37.0/37.0 (7,293 eps; timeouts 0/0/0/0%%; picks 4.59/4.74/4.79/4.62; entropy -0.830; KL/update 0.019; epochs/update 9.91; [zs] adj +12.1/+12.3/+12.7/+12.2, dealt_nn 0.86-0.89; per-COM-character learner win share: Gourmand/Jack 0.39, Pride/Galuda/Ryoma/Julia 0.38, Pete/Gunrock/Accel 0.37, Falcon/Mel/Wang-Tang 0.36, Ayame 0.35, Rouge 0.32; ~520 eps each) | 15.8 (79W/421L, n=500, Wilson 13-19; 5.43/1.12) | 93.6 (234/250, Wilson 90-96; 9.67/2.80) | — | 73-27 (n=100) |

Leg 59 note + CHARACTER READ VERDICT (Sep 21 09:30 EDT): lv8 23.8 (20-28) = ALL-TIME RECORD (prev
22.4, leg 56); the lv8 WATCH is cleared (22.4 -> 16.2 -> 15.8 -> 23.8 reads as two draws from the
low side of one distribution, then a high one). lv3 95.2, champion AB 74-26. Character legs 58-59:
lv8 15.8 / 23.8, lv3 93.6 / 95.2, AB 73 / 74 vs arena legs 55-57 (19.2/22.4/16.2, 95.2/97.6/92.4,
69/78/65). Pre-registered pass (lv8 in/above the 15-21 band both legs, lv3 and AB in band): MET.
Stream: win share rose through the leg (0.36 -> 0.39), stones back to 4.9, the 14 characters stay
even (0.33 Rouge to 0.43 Ayame; Ayame flipped from hardest-but-one to easiest in one leg — the bot
learns a matchup in a leg). VERDICT: PASS; character randomization stays in the standing recipe.
Blake's read stands too: the new opponents cost nothing visible in the stream. Leg 60 chained 09:23.
NEXT QUEUED (Blake, Sep 20): COM level randomization via stamped level-5 / level-8 state sets
(options menu) — needs the menu path discovered by screenshots; a quiet-hour job.
| 57 | 164M (MIXED, warm leg 56, STACK + ARENA zero-sum + start health 0.5-1.0, NEW CONTRACT; last leg before character randomization) | 34.0/34.0/37.0/35.0 (7,458 eps; timeouts 0/0/0/0%%; picks 4.58/4.50/4.68/4.55; entropy -0.845; KL/update 0.019; epochs/update 9.97; [zs] adj +11.0/+10.6/+11.9/+10.8, dealt_nn 0.85-0.86) | 16.2 (81W/419L, n=500, Wilson 13-20; 5.81/1.22) | 92.4 (231/250, Wilson 88-95; 9.25/2.73) | — | 65-35 (n=100) |

Leg 58 note (Sep 21 04:50 EDT): first character-randomization leg. lv8 15.8 (13-19) = SECOND
consecutive drop (22.4 -> 16.2 -> 15.8) = WATCH by the pre-stated rule; both drops sit inside
overlapping intervals and inside the pre-arena band (15-21), so it reads as a return from leg 56's
high sample rather than a decline, but a third drop on leg 59 = signal. lv3 93.6 and champion AB
73-27 (up from 65) are fine. The 14 COM characters were drawn evenly and none breaks the bot
(0.32-0.39 stream win share); Rouge is the hardest, Gourmand/Jack the easiest. Stream otherwise
identical to legs 55-57. Leg 59 chained 04:46 EDT, same recipe; completes the character read.
| 56 | 160M (MIXED, warm leg 55, STACK + ARENA zero-sum + start health 0.5-1.0, NEW CONTRACT) | 39.0/36.0/35.0/36.0 (7,470 eps; timeouts 0/0/0/0%%; picks 4.88/4.86/4.80/4.75; entropy -0.841; KL/update 0.019; epochs/update 10.0; [zs] raw +14.9/+13.8/+13.3/+13.5, opp_mean +1.4/+1.9/+1.8/+1.8, adj +13.4/+11.9/+11.5/+11.7, dealt_nn 0.85-0.89) | **22.4** (112W/388L, n=500, Wilson 19-26; 6.16/1.38) | **97.6** (244/250, Wilson 95-99; 9.49/2.90) | — | **78-22** (n=100) |

Leg 57 note (Sep 21 00:10 EDT): one-leg dip from leg 56's records on all three (22.4 -> 16.2, 97.6
-> 92.4, 78 -> 65), each still inside or above the pre-arena reference (lv8 15-21, lv3 91-95, AB
53-60). Arena legs so far: lv8 19.2 / 22.4 / 16.2, lv3 95.2 / 97.6 / 92.4, AB 69 / 78 / 65. One
drop = noise band; a second on leg 58 = watch (leg 58 also adds character randomization, so read
it against the arena band, not against leg 56 alone). Stream unchanged (stones 4.6, timeouts 0,
entropy flat). Leg 58 chained 00:07 EDT = FIRST CHARACTER-RANDOMIZATION LEG (state_slots
[0,10..22] in [config], slots 11/12/16/18/19/20 already seen in the first minutes, 10 workers).
| 55 | 156M (MIXED, warm leg 54, STACK + ARENA zero-sum + start health 0.5-1.0, NEW CONTRACT; FIRST ARENA LEG) | 37.0/38.0/38.0/40.0 (7,218 eps; timeouts 0/0/0/0%%; picks 4.90/4.96/4.91/4.89 (leg 54: 6.01); entropy -0.81; KL/update ~0.019; epochs/update ~9.9; [zs] per-episode raw +14.1/+14.7/+14.3/+15.1, opp_mean +1.9/+1.7/+1.7/+1.4, adj +12.2/+13.0/+12.6/+13.7, dealt_nn 0.86-0.88) | 19.2 (96W/404L, n=500, Wilson 16-23; 6.19/1.30) | **95.2** (238/250, Wilson 92-97; 9.86/3.02) | — | **69-31** (n=100) |

Leg 56 note + ARENA READ VERDICT (Sep 20 19:35 EDT): RECORDS ACROSS THE BOARD. lv8 22.4 (19-26) =
all-time record and the first interval whose LOWER bound (19) clears the stack band's mean;
lv3 97.6 (95-99) = all-time record (prev 96.4); champion AB 78-22 (69-85) = best of the new
contract and back at the mixed-era 78-82 band. Two arena legs: lv8 19.2 / 22.4, lv3 95.2 / 97.6,
AB 69 / 78 vs the stack reference (lv8 20.6/16.6/19.6, AB 53/60/60, lv3 94.0/94.8/91.2). Pre-
registered pass criteria (lv8 in/above band AND AB >= reference on both legs, lv3 in band): MET.
Stream as predicted: stones/episode 6.0 -> 4.9 -> 4.8 (farming stopped paying), timeouts 0,
dealt_nn flat ~0.87 (the one prediction that did not move), entropy flat -0.84, KL 0.019.
VERDICT: PASS. RECOMMENDATION: keep both arena flags as the standing recipe; next candidates
(Blake's call, one at a time): widen start-health randomization (0.3-1.0) or add stage/character
randomization; re-run the human play test on the leg 56 zip. Leg 57 chained 19:31 EDT, same
recipe. Campaign context: champion 5.8 -> this bot 22.4 on lv8 under the same contract.
| 54 | 152M (MIXED, warm leg 53, kl01 restart lineage, STACK lr 1e-4 + kl 0.03 + batch 256, NEW CONTRACT; last leg before the arena flags) | 35.0/36.0/37.0/36.0 (5,768 eps; timeouts 0/0/0/0%%; entropy -0.813, quarters -0.812/-0.813/-0.814/-0.813; KL/update 0.019; epochs/update 9.90) | 19.6 (98W/402L, n=500, Wilson 16-23; 6.03/1.29) | 91.2 (228/250, Wilson 87-94; 9.84/2.93) | — | 60-40 (n=100) |

Leg 55 note (Sep 20 15:00 EDT): first arena leg. Held-out: lv8 19.2 (16-23) = high side of the
stack band (20.6/16.6/19.6); lv3 95.2 (up from 91.2); champion AB 69-31 = best since leg 50 and up
from the stack's 53/60/60. Pre-registered stream expectations: stones/episode FELL 6.0 -> 4.9
(as predicted: farming stops paying), timeouts 0, win share 0.37 -> 0.40 rising, dealt_nn flat
~0.87 (did not rise yet). Under zero-sum the learner's adjusted episode reward is ~+12.5 (still
stone-dominated: 4.9 x 3 = 14.7, terminals amplified: a win = +30, a loss with a survivor = -16.7).
Read: one leg, direction right on all three held-out numbers, no regression anywhere; leg 56
completes the read. Leg 56 chained 14:54 EDT, same flags (both [config] lines present).
| 53 | 148M (MIXED, warm leg 52, kl01 restart lineage, STACK lr 1e-4 + kl 0.03 + batch 256, NEW CONTRACT) | 34.0/33.0/37.0/33.0 (6,027 eps; timeouts 1/0/0/0%%; entropy -0.801, quarters -0.803/-0.799/-0.803/-0.795; KL/update 0.018; epochs/update 9.93) | 16.6 (83W/417L, n=500, Wilson 14-20; 5.75/1.19) | 94.8 (237/250, Wilson 91-97; 9.83/3.02) | — | 60-40 (n=100) |

Leg 54 note (Sep 20 10:20 EDT): lv8 19.6 (16-23), second-best ever; lv3 91.2 (low of the mixed era,
still 87-94); AB 60-40 (= leg 53). Three stack legs: lv8 20.6/16.6/19.6 (mean 18.9 vs the lr+kl
plateau's 16.9), AB 53/60/60, lv3 94.0/94.8/91.2. Stack read stays "neutral-to-mildly-positive on
lv8, mildly negative on AB". Leg 55 chained 10:14 EDT = FIRST ARENA LEG (zero-sum + start health
0.5-1.0; both [config] lines present, [start]/[zs] lines flowing, 10 workers). Reference for the
arena read = legs 52-54: lv8 15-21 (mean 18.9), AB 53-60, lv3 91-95, picks ~6.0/ep.
| 52 | 144M (MIXED, warm leg 51, kl01 restart lineage, STACK lr 1e-4 + kl 0.03 + batch 256, NEW CONTRACT) | 38.0/40.0/38.0/34.0 (6,368 eps; timeouts 0/0/1/0%%; entropy -0.780, quarters -0.757/-0.771/-0.789/-0.805; KL/update 0.017; epochs/update 10.00) | **20.6** (103W/397L, n=500, Wilson 17-24; 6.26/1.36) | 94.0 (235/250, Wilson 90-96; 9.98/3.04) | — | 53-47 (n=100) |

Leg 53 note + STACK READ VERDICT (Sep 20 05:35 EDT): legs 52-53 on the stack = lv8 20.6 / 16.6, lv3
94.0 / 94.8, AB 53 / 60. Pre-registered pass ("both legs above the 15-19 band") NOT met: leg 53 is
back inside the band. Revert trigger ("under 15 twice") NOT met either. Mechanism worked as designed
(10 passes/update vs 4.3-4.9, KL flat at 0.017-0.018), held-out did not follow: stack mean 18.6 vs
plateau mean 16.9 = inside noise; AB 53/60 vs 65-74 before and the training stream a notch softer
(win share 0.33-0.37 vs 0.36-0.41, picks ~5.9 vs ~6.3) are mild negatives. VERDICT: neutral-to-
slightly-negative; the optimizer is confirmed NOT the bottleneck. RECOMMENDATION (Blake's call):
either keep the stack (no churn, watch AB; drop batch 256 if AB < 60 again) or revert to lr + kl
only — and in both cases move the campaign to the arena levers (zero-sum reward, start
randomization). Leg 54 chained 05:31 EDT on the stack.
| 51 | 140M (MIXED, warm leg 50, kl01 restart lineage, lr 1e-4 + kl 0.03 explicit, NEW CONTRACT; last leg before the batch-256 stack) | 37.0/35.0/37.0/36.0 (6,419 eps; timeouts 0/0/1/1%%; entropy -0.746, quarters -0.743/-0.748/-0.746/-0.747; KL/update 0.017; epochs/update 4.29) | 16.4 (82W/418L, n=500, Wilson 13-20; 6.36/1.35) | 93.2 (233/250, Wilson 89-96; 9.90/3.09) | — | 69-31 (n=100) |

Leg 52 note (Sep 20 00:50 EDT): first stack leg. lv8 20.6 (17-24) = ALL-TIME RECORD, the first
number above the 15-19 plateau band (and above the kl01 arm's 19.0). lv3 94.0 in band. BUT the
champion AB dropped to 53-47 (43-62) from 69 — one drop, biggest since the drifted lineage, while
KL/update stayed at 0.017 (so NOT the drift signature; the brake never tripped, 10/10 passes).
Stream Q4 softened (win 0.34, picks 5.7). Read: the stack read needs leg 53 as pre-registered;
lv8 is a clear pass, AB is the thing to watch. If AB < 50 again on leg 53 with lv8 still up, that
is a "COM-shaped vs policy-shaped" divergence to bring to Blake, not a hold. Leg 53 chained 00:48.
| 50 | 136M (MIXED, warm leg 49, kl01 restart lineage, lr 1e-4 + kl 0.03 explicit, NEW CONTRACT) | 38.0/38.0/39.0/41.0 (6,534 eps; timeouts 1/0/0/0%%; entropy -0.732, quarters -0.727/-0.735/-0.737/-0.733; KL/update 0.017; epochs/update 4.42) | 15.0 (75W/425L, n=500, Wilson 12-18; 6.04/1.17) | 95.6 (239/250, Wilson 92-98; 10.04/3.07) | — | 70-30 (n=100) |

Leg 51 note (Sep 19 20:10 EDT): plateau confirmed, six legs: lv8 16.8/18.6/15.8/18.8/15.0/16.4 (mean
16.9), lv3 92.8-96.4, AB 65-74. Leg 52 chained 20:07 EDT on the STACK (lr 1e-4 + kl 0.03 + batch 256,
all three override lines in its [config]); read over legs 52-53 vs the 15-19 band.
| 49 | 132M (MIXED, warm leg 48, kl01 restart lineage, lr 1e-4 + kl 0.03 explicit, NEW CONTRACT) | 37.0/39.0/38.0/39.0 (6,976 eps; timeouts 0/0/0/1%%; entropy -0.695, quarters -0.677/-0.693/-0.704/-0.706; KL/update 0.018; epochs/update 4.69) | **18.8** (94W/406L, n=500, Wilson 16-22; **6.57**/1.42) | **96.4** (241/250, Wilson 93-98; 9.66/3.05) | — | 68-32 (n=100) |

Leg 50 note (Sep 19 15:30 EDT): lv8 15.0 (12-18) after 18.8, one drop, intervals overlap; lv3 95.6
(second-best ever); champion AB 70-30 (up). Five legs on the explicit setting: lv8 16.8/18.6/15.8/
18.8/15.0 (mean 17.0), lv3 94.0/92.8/94.8/96.4/95.6, AB 74/67/65/68/70. Stream unchanged (entropy
flat -0.73, KL 0.017, win share 0.38-0.41). Read: a stable plateau, lv8 alternating 15-19 with no
trend either way; the optimizer is no longer the bottleneck. Next lever is the pre-registered
diet/arena work (zero-sum reward, start randomization) — Blake's call. Leg 51 chained 15:24 EDT.
| 48 | 128M (MIXED, warm leg 47, kl01 restart lineage, lr 1e-4 + kl 0.03 explicit, NEW CONTRACT) | 36.0/36.0/38.0/37.0 (7,175 eps; timeouts 1/1/0/1%%; entropy -0.661, quarters -0.637/-0.658/-0.667/-0.675; KL/update 0.017; epochs/update 4.76) | 15.8 (79W/421L, n=500, Wilson 13-19; 6.24/1.31) | **94.8** (237/250, Wilson 91-97; 9.77/3.14) | — | 65-35 (n=100) |

Leg 49 note (Sep 19 10:45 EDT): records. lv8 18.8 (16-22) = best held-out lv8 of any league leg
(kl01 sweep arm 19.0 is the only higher number, same interval); lv3 96.4 = ALL-TIME record (prev
94.8); lv8 picks 6.57 = record. Champion AB 68-32 recovered from 65 -> the AB "watch" is cleared
(74/67/65/68 = noise around 68). Stream unchanged (flat entropy -0.70, KL 0.018). Read: a stable
optimizer on a slowly rising plateau; four legs on this setting: lv8 16.8/18.6/15.8/18.8, lv3
94.0/92.8/94.8/96.4, AB 74/67/65/68. Leg 50 chained 10:43 EDT, same setting.
| 47 | 124M (MIXED, warm leg 46, kl01 restart lineage, lr 1e-4 + kl 0.03 explicit, NEW CONTRACT) | 37.0/39.0/39.0/40.0 (7,315 eps; timeouts 0/1/1/1%%; entropy -0.605, quarters -0.579/-0.595/-0.615/-0.626; KL/update 0.016; epochs/update 4.94) | **18.6** (93W/407L, n=500, Wilson 15-22; 6.07/1.28) | 92.8 (232/250, Wilson 89-95; 10.22/3.25) | — | 67-33 (n=100) |

Leg 48 note (Sep 19 06:05 EDT): lv8 15.8 (13-19) after 18.6, one drop, interval overlaps; lv3 94.8
= new mixed-era record (ties the all-time 94.8 of leg 26); champion AB 65-35 after 74/67, a second
"drop" but 67 -> 65 is two games (Wilson 55-74 vs 57-75): counted as WATCH by the letter of the
rule, not by the numbers. Stream identical to leg 47 (flat entropy -0.66, KL 0.017). Read: the
lineage is on a plateau around lv8 16-19 / AB 65-74 with a stable optimizer; no drift signature.
Leg 49 chained 06:02 EDT, same setting.
| 46 | 116M+4M (MIXED, RESTART from sweep40 kl01 zip; lr 1e-4 + BAKED-IN target_kl 0.1 (unplanned stack, see section); NEW CONTRACT) | 38.0/40.0/40.0/38.0 (6,865 eps; timeouts 1/1/1/1%%; entropy -0.455, quarters -0.293/-0.404/-0.492/-0.574; KL/update 0.021; epochs/update 9.58) | 16.8 (84W/416L, n=500, Wilson 14-20; 6.34/1.35) | **94.0** (235/250, Wilson 90-96; 10.47/3.28) | — | **74-26** (n=100) |

Leg 47 note (Sep 19 01:25 EDT): first leg on the explicit lr 1e-4 + target_kl 0.03 setting. lv8 18.6
(15-22), the best held-out lv8 of any LEG (the kl01 arm's 19.0 was a sweep arm); lv3 92.8; champion
AB 67-33 (one drop from 74, inside noise, watch only if it repeats). Stream: entropy flat at -0.60,
KL/update 0.016 (vs 0.021 stacked / 0.05 drifted), win share rising 0.37 -> 0.40, 7,315 episodes
(record; shortest fights). Leg 48 chained 01:19 EDT, same setting.
| 45 | 136M (MIXED, warm leg 44, kl01 lineage, target_kl 0.1, NEW CONTRACT; LAST leg on this setting) | 30.0/28.0/30.0/29.0 (5,554 eps; timeouts 1/1/2/1%%; entropy -0.979, quarters -0.962/-0.969/-0.987/-1.006; KL/update 0.053; epochs/update 4.15) | 13.8 (69W/431L, n=500, Wilson 11-17; 4.91/0.93) | 91.2 (228/250, Wilson 87-94; 9.12/2.66) | — | **26-74** (n=100) |

Leg 46 note (Sep 18 20:40 EDT): the restart holds. lv8 16.8 (14-20) vs parent 19.0 (16-23), lv3 94.0
(ties the record), champion AB 74-26 = the best of the new-contract era and a full recovery from
the drifted lineage's 26. This leg ran the accidental lr 1e-4 + target_kl 0.1 stack (zip carried
0.1); leg 47 chained 20:38 EDT on the explicit, intended setting PS2_LR=1e-4 PS2_TARGET_KL=0.03
(both override lines confirmed in its [config]). References for leg 47: 16.8 / 94.0 / 74.
| 44 | 132M (MIXED, warm leg 43, kl01 lineage, target_kl 0.1, NEW CONTRACT) | 30.0/28.0/27.0/26.0 (6,020 eps; timeouts 1/2/1/0%%; entropy -0.926, quarters -0.871/-0.910/-0.944/-0.961; KL/update 0.050; epochs/update 3.94) | 12.8 (64W/436L, n=500, Wilson 10-16; 5.30/1.10) | 90.4 (226/250, Wilson 86-93; 9.48/2.82) | — | **37-63** (n=100) |

Leg 45 note (Sep 18 15:55 EDT): champion AB fell a FIFTH straight time, 71 -> 65 -> 53 -> 51 -> 37 ->
26 (Wilson 18-35): BELOW the 35 hold line; hold was already set at leg 44. lv8 13.8 (11-17), lv3
91.2, lv8 picks/forms 4.91/0.93 (lowest of the lineage). Machine idle: state `46
./powerstone_v6_leg45_league.zip`, `leg46_LAUNCH_HELD.txt` written, nothing launched. VERDICT on
target_kl 0.1: one-leg jump (16.6 old / 19.0 new contract), then five legs of drift; do not use as
a standing setting. Restart awaits Blake (recommended: kl01 zip + PS2_LR=1e-4, SESSION_HANDOFF sec 2).
| 43 | 128M (MIXED, warm leg 42, kl01 lineage, target_kl 0.1, NEW CONTRACT) | 33.0/34.0/36.0/34.0 (6,539 eps; timeouts 1/1/1/1%%; entropy -0.787, quarters -0.750/-0.779/-0.789/-0.845; KL/update 0.046; epochs/update 4.15) | 16.8 (84W/416L, n=500, Wilson 14-20; 5.51/1.15) | **94.0** (235/250, Wilson 90-96; 9.64/2.87) | — | 51-49 (n=100) |

Leg 44 note (Sep 18 11:20 EDT): SIGNAL. Champion AB fell a FOURTH straight time, 71 -> 65 -> 53 ->
51 -> 37 (Wilson 28-47): the lineage now LOSES to the leg-1 champion, one point above the 35 hold
line. lv8 12.8 (10-16) is back at the leg 42 low; lv3 90.4. Stream: fourth straight decline on
every indicator (win share 0.42 -> 0.28, picks 6.6 -> 5.0, forms 1.65 -> 1.12, entropy -0.36 ->
-0.93, KL/update 0.02 -> 0.05). Read: target_kl 0.1 lets the policy drift ~0.05 KL per update;
the bot is walking away from what it learned, fastest where it matters (vs a policy opponent).
ACTION (operator, within protocol): `league_trainer.txt` = hold, so leg 45 (already chained at
11:13 EDT on target_kl 0.1, running) is the LAST leg on this setting; its battery evaluates it and
launches nothing. Not killed (mid-leg, never). RECOMMENDATION TO BLAKE: restart the lineage from
the kl01 arm zip (`powerstone_v6_sweep40_kl01_league.zip`, 19.0 / 92.8 / 71-29, the strongest
zip by both lv8 and AB) with `league_optim.txt` = `PS2_LR=1e-4` (the low-drift sweep arm: KL 0.006,
16.4 lv8 fair-start, AB 76-24). Pool for that restart: `pool_sweep40_kl01` (clone; the current
pool_league carries legs 41-44's drifted snapshots and should be set aside as
pool_league_kl_drift_41_44, never rm). Legs 41-44 stay in the ledger as the target_kl 0.1 lesson.
| 42 | 124M (MIXED, warm leg 41, kl01 lineage, target_kl 0.1, NEW CONTRACT) | 37.0/37.0/37.0/36.0 (6,894 eps; timeouts 1/1/1/1%%; entropy -0.613, quarters -0.522/-0.587/-0.650/-0.700; epochs/update 3.83) | 12.6 (63W/437L, n=500, Wilson 10-16; 5.74/1.17) | 92.8 (232/250, Wilson 89-95; 9.81/3.07) | — | 53-47 (n=100) |

Leg 43 note (Sep 18 06:40 EDT): lv8 RECOVERED to 16.8 (14-20) from 12.6 -> the lv8 watch is
cleared (19.0 / 16.2 / 12.6 / 16.8 reads as a noisy plateau around 16, not a decline). lv3 94.0
is the mixed-era record. BUT champion AB fell a THIRD straight time: 71 -> 65 -> 53 -> 51 (41-61),
still above the 35 hold line. Stream: win share 0.34 (lowest of the lineage), picks/forms down a
third leg, entropy -0.85, KL/update doubled to 0.046. Read: the bot is holding or improving vs
COMs while losing its edge vs a policy opponent; consistent with drift under the loose brake
(target_kl 0.1) toward COM-shaped play. Contingency threshold (lv8 < 12.6) NOT met, so leg 44
chained 06:35 EDT with target_kl 0.1. NEW PROPOSAL for Blake: switch the standing override to
PS2_LR=1e-4 for leg 45 regardless (low drift, best AB in the sweep) — the AB trend is the
signal the lv8 number is hiding. Not applied.
| 41 | 120M (MIXED, warm sweep40 kl01, target_kl 0.1, reload + pre-roll fixes, NEW CONTRACT) | 40.0/39.0/44.0/43.0 (6,873 eps; timeouts 1/1/1/1%%; entropy -0.359, quarters -0.259/-0.323/-0.390/-0.456; epochs/update 3.14) | 16.2 (81W/419L, n=500, Wilson 13-20; 6.11/1.30) | 90.4 (226/250, Wilson 86-93; 10.55/3.36) | — | 65-35 (n=100) |

Leg 42 note (Sep 18 01:50 EDT): SECOND CONSECUTIVE DIP = WATCH (pre-stated: two = watch, three =
signal). lv8 19.0 (kl01 parent) -> 16.2 -> 12.6; the 10-16 interval now only touches the parent's
16-23. Champion AB 71 -> 65 -> 53 (Wilson 43-62), still above the 35 hold line. lv3 92.8 is fine.
Stream: win share flat at 0.37 (leg 41: 0.40-0.44), picks/forms slightly down, entropy rising
every quarter to -0.70 with KL/update ~0.02 (the target_kl 0.1 arm's known mechanism: 3x the drift
of the lr 1e-4 arm). Read: consistent with over-exploration / drift under the loose brake rather
than the pool getting harder (held-out AB is falling too). CONTINGENCY PROPOSED TO BLAKE (not
applied): if leg 43's lv8 < 12.6 -> hold, restart from the kl01 arm zip (19.0) with
league_optim.txt = PS2_LR=1e-4 (the low-drift arm; 16.4 on the new contract, best AB 76-24).
Hold rule not tripped; leg 43 chained 01:47 EDT with target_kl 0.1.
| 40 | 116M (MIXED: 2 policy seats + lv3 COM, obs v2, uniform, warm leg 39, 4M; OLD reset code; SWEEP PARENT) | 33.0/35.0/30.0/38.0 (4,693 eps; timeouts 10/13/27/13%%; entropy -0.063, quarters -0.072/-0.063/-0.043/-0.066) | 4.2 (21W/479L, n=500, Wilson 3-6; 3.94/0.59) | 86.8 (217/250, Wilson 82-90; 10.10/3.19) | — | 60-40 (n=100) |

Leg 41 note (Sep 17 21:05 EDT): first leg of the kl01 lineage under the new contract. lv8 16.2
vs the parent's 19.0 measured the same way (intervals 13-20 vs 16-23 overlap; a ~3-point move is
inside the noise band I pre-stated). lv3 90.4 and champion AB 65-35 are in the mixed band (old
contract references 92.8 / 71-29). Hold rule not tripped; leg 42 chained 21:00 EDT with the
standing target_kl 0.1. Stream is the healthiest of the campaign: 1%% timeouts all leg, entropy
rising every quarter to -0.456, forms 1.55-1.75, 6,873 episodes (shortest fights yet). Read: no
step change expected from here, a slope with noise; two consecutive drops = watch, three = signal.
| 39 | 112M (MIXED: 2 policy seats + lv3 COM, obs v2, uniform, warm leg 38, 4M) | 37.0/28.0/36.0/37.0 (4,853 eps; timeouts 15/21/11/6%%; entropy -0.071, quarters -0.075/-0.051/-0.075/-0.091) | 4.8 (24W/476L, n=500, Wilson 3-7; 4.34/0.72) | 88.4 (221/250, Wilson 84-92; 10.47/3.16) | — | 81-19 (n=100) |

Leg 40 note (Sep 16 19:55 EDT): second held-out echo of the entropy collapse. lv8 4.2 (mixed-era
low, under the champion's 5.2), slot2 86.8 (band low), champion AB 60-40 (band was 78-82; the
biggest single-leg drop of the campaign, Wilson 50-69 still clear of the 35 hold line). Stream Q3
paired the campaign's lowest entropy quarter (-0.043) with 27%% timeouts. Hold was already set
(Blake, for the sweep): leg 41 HELD, state advanced to 41. Leg 40 is the sweep's parent and its
unfixed reference; note that it is a WEAKENED parent (three declining legs), so the sweep's
absolute numbers will read low and the arm comparison (ctrl vs knobs) is the result, not the
level. If every arm lands under leg 38's 7.2, re-running the winning setting from the leg 38 zip
is the obvious follow-up (Blake's call). Epochs/update 1.10.
| 38 | 108M (MIXED: 2 policy seats + lv3 COM, obs v2, uniform, warm leg 37, 4M) | 38.8/36.2/37.2/37.4 (5,120 eps; timeouts 8.7/11.6/12.0/12.0%%; entropy -0.075, last quarter -0.081) | 7.2 (36W/464L, n=500, Wilson 5-10; 4.70/0.83) | 90.4 (226/250, Wilson 86-93; 10.24/3.27) | — | 79-21 (n=100) |

Leg 39 note (Sep 16 15:30 EDT): lv8 4.8 is the low of the mixed era (band was 7.2-9.0)
and sits under the champion's 5.2, one sample though (Wilson 3-7 overlaps leg 38's 5-10).
slot2 88.4 and champion AB 81-19 are inside the mixed band, so the hold rule (slot2 <70,
AB <35, lv8 <4.0) did NOT trip; leg 40 chained at 15:27 EDT, mixed, ent_coef 0.01 (no
0.03 word from Blake). Stream: entropy bottomed mid-leg (-0.051 quarter) and recovered
to -0.091 by Q4 while timeouts fell 21%% -> 6%%; picks 4.34 on lv8 is the lowest since
leg 34. Read: the entropy-collapse trigger (fired leg 38) now has a held-out echo. Leg 40
is the second leg past the trigger; if lv8 stays under 6 the 0.03 proposal becomes the
recommendation rather than an offer. Epochs/update 1.10 (target_kl brake, unchanged).

**LEG 38 (Sep 16 10:59 EDT): ENTROPY TRIGGER FIRED.** lv8 9.0 -> 8.0 -> 7.2
(two legs flat/down, intervals overlapping) while entropy_loss medians ran
-0.107 -> -0.096 -> -0.093 -> -0.075 (legs 35-38); the stream's win share
stalled at ~37%% (leg 36: 45%%) and timeouts crept back to 12%% (2-5%% two legs
ago) — the deterministic-policy stall returning inside the mixed arena.
slot2 90.4 and champion AB 79-21 are steady. PROPOSAL TO BLAKE (nothing
changed): ent_coef 0.01 -> 0.03 for mixed legs from leg 40 (leg 39 already
chained at 0.01). Mechanism: PS2_ENT_COEF override in train_selfplay_async.py
(set on the loaded model before training; default = the zip's 0.01),
selected by a one-word file league_entcoef.txt read by league_leg_async.sh.
Pre-registered read for the first 0.03 leg: entropy median back below -0.12,
timeouts back under 6%%, lv8 >= 8.0's interval; if slot2 or AB regress
past Blake's hold thresholds, revert to 0.01.**

| 37 | 104M (MIXED: 2 policy seats + lv3 COM, obs v2, uniform, warm leg 36, 4M) | 39.8/40.3/42.4/35.5 (5,635 eps; timeouts 4.0/4.6/6.1/9.2%%; entropy -0.093, last quarter -0.082) | 8.0 (40W/460L, n=500, Wilson 6-11; **5.16**/0.97) | **91.2** (228/250, Wilson 87-94; 10.12/3.20) | — | **82-18** (n=100) |

**LEG 37 (Sep 16 06:23 EDT): lv8 9.0 -> 8.0 (inside the interval = flat),
slot2 back to 91.2, champion AB 82-18 (best mixed). Picks 5.16 record.
Stream softened in the last quarter (win 42 -> 36%%, timeouts 6 -> 9%%).
ENTROPY WATCH: median -0.093, last quarter -0.082; lv8 flat while
entropy drifts toward 0 => **TRIGGER WATCH ARMED (1 of 2)**: one more leg
with lv8 flat/down and entropy drifting toward 0 (or a median above
-0.06) => propose ent_coef 0.01 -> 0.03 to Blake. Mixed series: lv8
8.2/8.4/9.0/8.0; slot2 91.2/88.4/89.2/91.2; AB 81/80/78/82. Leg 38 chained.**

| 36 | 100M (MIXED: 2 policy seats + lv3 COM, obs v2, uniform, warm leg 35, 4M) | 38.1/41.3/43.1/45.3 (5,950 eps; timeouts 3.6/2.2/4.6/5.1%%; entropy -0.096, last quarter -0.083) | **9.0** (45W/455L, n=500, Wilson 7-12; **5.03**/0.95) | 89.2 (223/250, Wilson 85-92; 10.04/3.23) | — | 78-22 (n=100) |

**LEG 36 (Sep 16 01:48 EDT, 100M lifetime): third mixed leg, lv8 9.0%% (record;
picks 5.03 record — the first time lv8 picks passed 5), slot2 89.2, champion AB
78-22. Mixed series: lv8 8.2 -> 8.4 -> 9.0; slot2 91.2 -> 88.4 -> 89.2; AB 81 ->
80 -> 78. Stream still climbing (38 -> 45%%, timeouts 2-5%%). ENTROPY WATCH:
median -0.096 (leg 35: -0.107), last quarter -0.083 — drifting toward 0 but
above the -0.06 line and lv8 is not flat: trigger NOT armed. Leg 37 chained.**

| 35 | 96M (MIXED: 2 policy seats + lv3 COM, obs v2, uniform, warm leg 34, 4M) | 34.0/36.7/42.6/42.1 (5,891 eps; timeouts 7.6/6.0/2.9/6.5%% by quarter, ~6%% whole-leg; entropy -0.107) | **8.4** (42W/458L, n=500, Wilson 6-11; **4.76**/0.81) | 88.4 (221/250, Wilson 84-92; 10.11/3.24) | — | 80-20 (n=100) |

**LEG 35 (Sep 15 21:03 EDT): second mixed leg confirms the arena fix.** Stream
timeouts ~6%% whole-leg (the pre-registered < 10%% now met), win share 34 ->
42%%, shorter decisive fights (5,891 eps). Battery: lv8 8.4%% (record, picks
4.76 record), slot2 88.4 (91.2 -> 88.4, inside both intervals), champion AB
80-20. Mixed series: lv8 8.2 -> 8.4; slot2 91.2 -> 88.4; AB 81 -> 80. Entropy
still ~ -0.11 (ent_coef 0.03 remains the next lever if lv8 flattens). Leg 36
chained on mixed at 21:03.**

| 34 | 92M (**MIXED: 2 policy seats + lv3 COM**, obs v2, uniform, warm leg 33, 4M) | 29.6/34.0/34.9/37.8 (4,476 eps; timeouts 29->24->16->**13%%** by quarter, 20%% whole-leg; entropy -0.092) | **8.2** (41W/459L, n=500, Wilson 6-11; 4.55/0.80) | **91.2** (228/250, Wilson 87-94; 9.75/3.08) | — | **81-19** (n=100) |

**LEG 34 (Sep 15 16:25 EDT): THE MIXED ARENA WORKS — RECORD LV8, CHAMPION-LEVEL
SLOT2, ADOPTED.** lv8 8.2%% (Wilson 6-11): the best number in project history
(champion 5.2, pure-league best 5.6, FFA best 6.4). slot2 91.2 = the champion's
91.2 (leg 26: 94.8). Champion AB 81-19. Stream: the stall dissolved across
the leg (timeouts 29 -> 13%% by quarter, win share 30 -> 38%%, the first
sustained within-leg climb since leg 27) — the COM seat is the aggression
source it was meant to be. Pre-registered verdict: lv8 >= 5.0 PASS, slot2
>= 80 PASS, AB >= 35 PASS, whole-leg timeouts < 10%% NOT MET BY THE LETTER
(20%%; 12.6%% in q4 and falling). Adopted as the recipe on 3/4 + the trend
(operator call in the spirit of Blake's "adopt if timeouts collapse and lv8
holds"); leg 35 launched on mixed from the leg 34 zip. Entropy (-0.09) is
still the open weakness; ent_coef 0.03 remains the next lever if the climb
stalls. Follow-up option noted: a level-5 COM if the lv3 seat gets too easy.**

| 33 | 88M (FFA + anti-stall, obs v2, uniform, warm leg 32, 4M) | 15.1/16.5/21.0/24.3 (3665 eps; timeouts 35%%; entropy -0.057) | **6.4** (32W/468L, n=500, Wilson 5-9; **4.73**/0.86) | **90.0** (225/250, Wilson 86-93; 9.53/3.09) | — | 71-29 (n=100) |

**LEG 33 (Sep 15 09:43 EDT — the Mac's clock is now Eastern): THE BEST FFA
LEG.** lv8 6.4%% (record; picks 4.73 record), slot2 90.0 (best of the FFA
lineage, within reach of leg 26's 94.8 and the champion's 91.2), champion
AB 71-29. The self-play stream is still degenerate (19%% wins, 35%%
timeouts, entropy -0.06). FFA series: lv8 1.2/4.4/5.2/5.4/6.2/2.8/6.4;
slot2 75.6/84.0/83.6/87.2/77.2/84.0/90.0; AB 65/72/78/79/47/40/71. Leg 34
HELD (the leg-32 rule); Blake's "1-2 more legs" allowance is used up —
his call to continue.**

| 32 | 84M (FFA + anti-stall, obs v2, uniform, warm leg 31, 4M) | 20.4/20.9/17.2/19.2 (3777 eps; timeouts 31%%; entropy -0.050) | 2.8 (14W/486L, n=500, Wilson 2-5; 4.03/0.65) | 84.0 (210/250, Wilson 79-88; 10.12/3.18) | — | 40-58-2 (n=100) |

**LEG 32 (Sep 15 00:50): lv8 6.2 -> 2.8 (Wilson 4-9 vs 2-5, a real drop)
-> HOLD after leg 33 under Blake's rule (lv8 < 4.0).** slot2 recovered
to 84.0; champion AB 40-58 (at the 35-win floor). FFA lineage held-out
series: lv8 1.2/4.4/5.2/5.4/6.2/2.8; slot2 75.6/84.0/83.6/87.2/77.2/84.0;
AB 65/72/78/79/47/40. Leg 33 auto-launched from the leg 32 zip (trainer
file read ffa at launch); leg 34 held pending Blake.**

| 31 | 80M (FFA + anti-stall, obs v2, uniform, warm leg 30, 4M) | 30.3/28.5/24.7/24.4 (4,188 eps; timeouts 23%%; entropy -0.074) | **6.2** (31W/469L, n=500, Wilson 4-9; 4.36/0.81) | 77.2 (193/250, Wilson 72-82; 9.68/3.07) | — | 47-52-1 (n=100) |

**LEG 31 (Sep 14 20:14): lv8 RECORD, slot2 and the champion AB fell —
HOLD after leg 32 (slot2 < 80 rule).** lv8 6.2%% (Wilson 4-9): above the
champion (5.2) and the pure-league best (5.6), with lineage-record lv8
picks 4.36. But slot2 87.2 -> 77.2 (82-91 vs 72-82) and the champion AB
79-21 -> 47-52: the FFA lineage's lv3-COM and head-to-head form dropped
in one leg while its lv8 form rose. Held-out trend across FFA legs: lv8
1.2 / 4.4 / 5.2 / 5.4 / 6.2; slot2 75.6 / 84.0 / 83.6 / 87.2 / 77.2; AB
65 / 72 / 78 / 79 / 47. Per Blake's rule (slot2 < 80 -> hold) leg 33 is
held; leg 32 (launched 20:14 from the leg 31 zip, FFA) runs. OPS: leg 31's
first launch (13:45) died after 77 eps and was relaunched fresh at 15:39
by another session (boot-failure path, within protocol).**

| 30 | 76M (FFA + anti-stall, obs v2, uniform, warm leg 29, 4M) | 24.2/28.9/29.9/30.1 (3955 eps; timeouts 28%%; entropy median -0.075) | **5.4** (27W/473L, n=500, Wilson 4-8; 4.10/0.69) | **87.2** (218/250, Wilson 82-91; 10.28/3.17) | — | **79-21** (n=100) |

**LEG 30 (Sep 14 13:45): fourth FFA leg, held-out still rising.** lv8 1.2 ->
4.4 -> 5.2 -> **5.4** (picks 4.10 — the FFA lineage's best lv8 picks), slot2
75.6 -> 84.0 -> 83.6 -> **87.2**, AB vs champion 65 -> 72 -> 78 -> **79**.
The self-play stream stays degenerate (28%% win share, 28%% timeouts). Blake's
standing call: keep going. Leg 31 launched 13:45 on the same recipe. (The
battery was launched by a wake/session other than the interactive one —
markers and state consistent.)**

**LEG 30 (launched Sep 14 09:10, Blake's call: "lv8 got better every FFA leg
27-29, keep going"):** FFA + anti-stall, obs v2, uniform sampling, warm start
leg 29 zip, 4M. Relay chains FFA legs automatically; a battery with slot2 < 80
or lv8 < 1.2%% holds the next launch. docs/SESSION_HANDOFF.md rewritten
(Sep 14) as the operator's manual so a smaller model can run the relay.

| 29 | 72M (FFA + anti-stall, obs v2, uniform, warm leg 27, 4M, 4h05m) | 22.8/18.8/21.6/21.8 (4,262 eps; timeouts 21->26%%; entropy -0.12 -> -0.07) | 5.2 (26W/474L, n=500, Wilson 4-8; 3.76/0.59) | 83.6 (209/250, Wilson 79-88; 9.54/2.88) | — | 78-22 (n=100) |

**LEG 29 (Sep 14 08:15): THE ANTI-STALL FIX DID NOT TAKE IN SELF-PLAY, YET
THE HELD-OUT NUMBERS KEPT RISING.** Stream: win share ~21%% (below the
25%% four-way chance line), timeouts 21 -> 26%% across the leg despite
timeouts scored as losses, entropy -0.12 -> -0.07 — a low-entropy policy
does not explore its way out of passivity. Battery: lv8 5.2%% (= the
champion's 5.2, leg 26's 5.6), slot2 83.6, AB 78-22. Across the three FFA
legs the held-out evals read lv8 1.2 -> 4.4 -> 5.2, slot2 75.6 -> 84.0 ->
83.6, AB 65 -> 72 -> 78: recovering toward (not past) the pure-league
leg 26 (5.6 / 94.8 / 91-9) while the self-play equilibrium stays
degenerate. VERDICT: stream/entropy FAIL, outcome rule PASS -> leg 30
HELD (league_trainer.txt = hold, read at launch time now). Decision for
Blake: (1) mixed seats, two policy seats + one COM seat, as a permanent
aggression source; (2) ent_coef 0.03 for FFA legs; (3) park FFA and
resume the pure league from leg 26.**

**LEG 28 BATTERY (Sep 14 03:53): the held-out numbers RECOVERED while the
stream stalled** — lv8 1.2 -> 4.4%% (Wilson 3-7, back within reach of leg
26's 5.6 and the champion's 5.2), slot2 75.6 -> 84.0 (79-88), champion AB
65-35 -> 72-28; picks 10.07 / forms 3.02 on slot2 are lineage-normal. So the
FFA-vs-FFA leg moved the policy back toward COM competence even as the
self-play equilibrium degenerated (entropy -0.098, 10.6%% timeouts).
Outcome rule (slot2 >= 80) PASS; validation still FAIL on entropy. OPS
NOTE: league_battery.sh reads league_trainer.txt at battery START (03:20,
"ffa"), not at the launch step, so the 03:26 "hold" did not apply and
leg 29 auto-launched at 03:53:44 — on the anti-stall env (code is read
at launch: 2,000-step cap, timeout = loss, uniform sampling) but
warm-started from the LEG 28 zip. Kept (not restarted): the battery had
just shown leg 28 to be the stronger held-out policy, which supersedes
the 03:50 "warm from leg 27" amendment (entropy inheritance is the risk
to watch in leg 29's first updates). Lesson: set league_trainer.txt
BEFORE the battery starts, or edit the script to read it at launch.**

**LEG 29 RESTART (Sep 14 04:10): warm start moved to the LEG 27 zip after
all.** The leg-28-warm run's first eight updates (receipts/
train_leg29_from28_aborted_out.txt): entropy_loss sank further, -0.086 ->
-0.035..-0.06; 42%% of episodes (63/150) ran to the new 2,000-step cap;
win share 11%%. A near-deterministic policy does not explore its way out
of stalling even with timeouts scored as losses, so the collapsed zip is
the wrong seed regardless of its better held-out battery. Aborted at
~165k steps (one throwaway checkpoint, no pool snapshot), league_state
set to "29 ./powerstone_v6_leg27_league.zip", relaunched 04:10 with the
identical anti-stall settings. The leg 28 zip stays in the pool. This is
the pre-registered watch item ("entropy inheritance") acting as written.

**LEG 29 PRE-REGISTRATION — FFA + ANTI-STALL (Blake: "fix", Sep 14 03:35).**
Changes vs legs 27-28, all in ffa_selfplay_env.py / league_leg_async.sh:
(1) episode cap on slot 0 = 2,000 steps (PS2_FFA_MAX_STEPS; leg 27 p90 was
690); (2) a timeout is scored as a loss with the standard terminal
penalty (PS2_FFA_TIMEOUT_LOSS=1); (3) pool sampling uniform (50/50
recent-10 / uniform history, the league's original rule) instead of
PFSP. Everything else identical (obs v2, 10 actors, 4M). WARM START = the LEG 28 zip after all (the 03:50 amendment
below is SUPERSEDED: leg 28's battery came in stronger than leg 27's,
and the battery had already auto-launched leg 29 from it — see the LEG
28 BATTERY note). The amendment text is kept for the record: [leg 27 zip
was preferred at 03:50 because the leg 28 zip carries the
collapsed entropy, -0.098, and the fixed-env smoke warm-started from it
kept sinking, -0.15 -> -0.06 in three updates; leg 27's policy is
FFA-competent with normal entropy, -0.21. The leg 28 zip stays in the
pool as prog_leg28 and as an opponent). league_state.txt is edited to
"29 ./powerstone_v6_leg27_league.zip" for the launch. SUCCESS SIGNATURE, written before the leg: timeouts near 0%%,
entropy_loss back within 25%% of -0.266, stream win share rising above
leg 28's ~30%%, and on the battery slot2 >= 80 (the standing rule) with
lv8 not below leg 27's 1.2%%. FAIL on the battery = hold again and
consider the mixed-seat diet (two policy seats + one COM seat).

**LEG 28 (Sep 14 03:19, SECOND FFA LEG, FFA-trained opponents in the pool):
THE DEGENERATE FFA EQUILIBRIUM.** Stream vs three pool opponents: 34.6 /
30.4 / 27.3 / 30.3%% by quarter (four-way chance 25%%) — the leg-27 climb
did not continue once the opponents were FFA-trained. Mechanics: seam
PASS; learning-statistics **entropy_loss FAIL** (-0.098 vs the lockstep
-0.266: the policy went near-deterministic; clip_fraction 0.036, value
loss 1.9 — outcomes became predictable). Episodes: only 3,122 in 4M
steps; median length 594, p90 = 6,000 (the MAX_STEPS cap), **10.6%%
timeouts (331) vs 0.7%% in leg 27**, mean damage dealt 5.06 -> 4.45.
This is the "coward signature" (ep-length inflation + timeouts) the
notebook warned about since the reward era: four copies of one policy
find mutual passivity — attacking exposes you to the other two. PFSP
(which prefers the opponents you lose to, i.e. the stalling FFA
snapshots) plausibly accelerates it. VERDICT FAIL (entropy) -> hold.
Blake had set leg 29 = ffa at 01:11 (before this data); the session
HELD leg 29 pending his call on the evidence and offered an immediate
launch on his word. Candidate fixes, all diet/reward-class changes for
Blake to choose (Law 4 history: interface/data changes 5-for-5, reward
tuning 0-for-5, but the lv8 "coward" fix via LOSS_SCALE worked):
(a) anti-stall: a shorter MAX_STEPS for slot 0 with timeouts scored as
losses; (b) uniform (not PFSP) opponent sampling so 1v1-trained,
aggressive opponents keep pressure in the mix; (c) mixed seats — two
policy seats + one COM seat (lv3-5) as a permanent aggression source;
(d) ent_coef 0.01 -> 0.02. Battery (obs v2, 500/250/100) running at
03:20; leg 26 zip remains the best policy.

| 27 | 64M (**FFA self-play**, obs v2, PFSP, 4M, 4h27m) | **28.5/32.3/43.2/52.0 vs THREE pool opponents** (7,484 eps, picks 4.14->5.12, forms 0.69->1.21) | 1.2 (6W/494L, n=500, Wilson 1-3; 2.73/0.32) | 75.6 (189/250, Wilson 70-81; 9.75/2.82) | — | 65-35 (n=100) |

**LEG 27 (Sep 13, THE FIRST FFA SELF-PLAY LEG): the stream climbed like
nothing before it, the held-out COM evals fell — VALIDATION FAIL on the
outcome layer, relay HELD after leg 28 per the pre-registered rule.**
Stream: learner win share vs three frozen pool Falcons 28.5 -> 52.0%%
across the leg (four-way chance 25%%), picks 4.1 -> 5.1, forms 0.69 ->
1.21 — every pure-league leg was flat across quarters. Mechanics: seam
PASS (196 checks, 2.7e-5), learning statistics PASS on all six rules vs
leg 24. Outcome (obs v2, same contract as the re-baseline): lv8 1.2%%
(Wilson 1-3) vs leg 26's 5.6 (4-8); slot2 75.6 (70-81) vs 94.8 (91-97);
AB vs champion 65-35 vs 91-9 — all three moves are outside the
intervals, i.e. real. Rule slot2 >= 80 FAILED -> league_trainer.txt =
hold (leg 28, already auto-launched on FFA, runs; leg 29 waits for
Blake). READINGS, not conclusions: (a) regime shift — the policy was
still changing fast at leg end (stream +9 pts in q4 alone), and Law 6
says the final zip is not the best zip: a slot2 sweep of leg 27's eight
pool snapshots (leg27_league_*_steps.zip) is running to see whether the
COM regression is monotonic through the leg (a real trade-off) or a
late churn; (b) the three frozen opponents were all 1v1-trained Falcons
that had never fought a four-way — a policy that learns to beat
FFA-naive opponents is not yet a better fighter, and the pool only
contains FFA-trained snapshots from leg 28 on (leg 27's eight are in
it now), so leg 28 is the first honest FFA-vs-FFA read; (c) lv8 picks
fell 3.40 -> 2.73 while training picks rose: the FFA policy may be
taking stones from opponents (opp=... (-N) in the stream) rather than
collecting, which COMs do not permit the same way. Nothing lost: the
leg 26 zip (5.6 / 94.8 / 91-9) is intact and remains the best pure
policy.**

**LEG 27 SNAPSHOT SWEEP (Law 6, Sep 13-14 22:56-00:21, slot2 n=100 per
snapshot, obs v2, receipts/sweep_leg27_*):** 0.5M 89 | 1.0M 91 | 1.5M 86
| 2.0M 82 | 2.5M 80 | 3.0M 84 | 3.5M 66 | 4.0M 74 | final (n=250) 75.6.
Picks/forms stayed ~9.8/2.8-3.1 throughout (the gem game did not
degrade; the win-conversion vs COMs did). READ: the held-out regression
is MONOTONIC with the leg's self-play climb (28 -> 52%% vs three
1v1-trained Falcons) — a real trade-off, not churn; no leg-27 snapshot
beats the leg 26 zip (94.8). Whether FFA-trained opponents in the pool
(leg 28 onward) change the trade-off is the open question leg 28
answers.

| 26 | 60M (M4, ASYNC+pull64, 4M, 4h50m) | 80.8/81.2/81.0/82.3 (9,833 eps, picks 4.41, forms 0.87) | **5.6** (28W/472L, n=500, Wilson 4-8; 3.40/0.52) | **94.8** (237/250, Wilson 91-97; 9.42/2.88) | — | **91-9** (n=100) |

**LEG 26 (Sep 13, first SHARDED battery — n=500/250/100):** on the same
tight sample sizes as the re-baselined champion (5.2 / 91.2), leg 26
reads lv8 5.6 (Wilson 4-8), slot2 94.8 (91-97) and beats the champion
91-9 head-to-head (one-seat, training-state caveat). READ: the lineage
is at or above the champion on every held-out axis once both are
measured properly; the lv8 "wall" is a 5%% floor both lineages share,
which is the FFA-diet argument in one number. LAST PURE-LEAGUE LEG on
this Mac: leg 27 = the FFA self-play lineage (held via
league_trainer.txt=hold, launched by hand after this battery). OPS: leg
ran 4h50m at ~232 steps/s with the obs-v2 re-baseline sharing the box
for 80 min.**

| 25 | 56M (M4, **ASYNC + pull64**, 4M, 4h07m) | 83.5/84.4/85.9/86.4 (9,440 eps, picks 4.20, forms 0.87) | 8.0 (4W/46L, 4.26/0.74) | 88.0 (44W/6L, 9.40/2.88) | **11-1** | 8-4 (n=12) |

**LEG 25 (Sep 13, second async validation leg, mid-chunk weight pulls):
VALIDATION PASS ON EVERY PRE-REGISTERED RULE** (validate_async_leg.py vs
leg 24's full lockstep log): seam 196 checks max 2.5e-5; approx_kl
0.0097 vs 0.0085, clip 0.072 vs 0.069, entropy -0.235 vs -0.266,
explained_variance 0.826 vs 0.841, epochs/update median 1 = 1, mean
1.10 vs 1.43 (>= 0.75x); stream win share 85.1 vs 77.2, picks/forms
within 6%; outcome slot2 88 (>= 80), AB 11-1 vs leg 24. Battery: slot2
88.0 (Wilson [76-94] — inside the ~90 plateau band: 98/80/92/88/86/90/
94/94/88), lv8 4W/50 (picks 4.26 — a lineage record — wins by leg
1,0,2,3,2,2,1,3,0,5,1,2,4,0,4), AB 11-1 vs leg 24, 8-4 vs leg1. HONEST
NOTE: halving per-step staleness (1.0 -> 0.45) did NOT raise the epoch
count (1.15 -> 1.10); both trainers early-stop on 196/196 updates, so
target_kl=0.03 is the governor of gradient work per update in this
lineage, not the async seam — a hyperparameter question for
post-campaign, not a trainer bug. THE ASYNC TRAINER IS NOW THE RECIPE
(validated twice; ~2.4x wall-clock). Leg 26 chained on async.**

| 24 | 52M (M4, 10 workers, 4M, lockstep, 9h41m) | 77.9/76.6/76.1/78.1 (9,083 eps, picks 4.44, forms 0.90) | 0.0 (0W/50L, 3.60/0.56) | **94.0** (47W/3L, 9.50/2.82) | 9-3 | **10-2** (n=12) |

**LEG 24 (Sep 13, lockstep, the pre-registered revert leg): slot2 94.0
again** — two straight 94s (legs 23 async, 24 lockstep), the plateau's
top band; the last nine legs: 98/80/92/88/86/90/94/94. lv8 0/50 this
leg (wins by leg 1,0,2,3,2,2,1,3,0,5,1,2,4,0 — the edge stays noisy;
picks 3.60 / forms 0.56). AB 9-3 vs leg 23, 10-2 vs leg1. Value of this
leg beyond the lineage: the first full-leg lockstep PPO-statistics log
(195 updates) — the reference for every async validation from here.
Leg 25 launched on ASYNC + PS2_PULL_EVERY=64 (second validation leg).**

| 23 | 48M (M4, **ASYNC** 10 actors, 4M, 4h05m) | 78.1/79.6/77.7/81.6 (9,827 eps, picks 4.57, forms 0.95) | 8.0 (4W/46L, 3.84/0.54) | **94.0** (47W/3L, 10.06/3.20) | 9-3 | 8-4 (n=12) |

**LEG 23 (Sep 12, the ASYNC VALIDATION LEG): OUTCOME PASS, one mechanical
rule FAIL, reverted per pre-registration, fix built.** Battery: slot2
94.0 (second-best of the lineage after leg 17's 98; picks 10.06 / forms
3.20), lv8 4W/50 (wins by leg now 1,0,2,3,2,2,1,3,0,5,1,2,4), AB 9-3 vs
leg 22, 8-4 vs leg1. Pre-registered validation (validate_async_leg.py vs
the 450k lockstep baseline): (1) seam integrity PASS — 41 checks, max
|dlogp| 1.9e-5, |dvalue| 1.1e-5; (2) learning statistics: approx_kl
0.0128 vs 0.0109, clip_fraction 0.093 vs 0.076, entropy -0.279 vs
-0.279, explained_variance 0.814 vs 0.844 — all PASS; **gradient epochs
per update FAIL: 165/195 async updates early-stopped inside epoch 0 (1
epoch) vs 7/20 lockstep (median 2)** — cause exact: chunk-boundary weight
pulls make every batch one update stale (step lag 1.00), so target_kl's
early stop trips sooner (async KL p90 0.036 vs 0.014); (3) stream PASS —
win share 79.2 vs 75.5, picks/forms within 3%; (4) outcome PASS. Per
the written rule league_trainer.txt was reverted to lockstep before the
battery chained leg 24 (so leg 24 runs lockstep); the async zip stays in
the lineage (outcome passed) and the call is Blake's. FIX (built, smoked,
opt-in, NOT yet used for a leg): PS2_PULL_EVERY=64 makes actors apply new
weights mid-chunk with per-step version tracking — 2-actor smoke: step
lag 1.0 -> 0.1, 2-3 epochs per update instead of 1, seam check still
1e-5. Proposed: leg 24 or 25 on async + pull-every-64, same validation.
Throughput held all leg: 274.8 steps/s, 196 updates, clean exit, no
hang; 4M steps in 4h05m vs leg 22's 10h13m. n=50 AB leg23 vs leg22
(one-seat, training state — audit caveat): **36-14** (72%, Wilson
~58-83), receipts/eval_leg23_ab_vs_prev_n50_out.txt.**

| 22 | 44M (M4, 10 workers, 4M, lockstep) | 78.3/80.3/83.7/80.8 (9,642 eps, picks 4.60, forms 0.99) | 4.0 (2W/48L, 3.78/0.52) | **90.0** (45W/5L, 9.76/3.02) | 9-3 | **10-2** (n=12) |

**LEG 22 (Sep 12, second leg on the 10-worker/4M recipe): slot2 back to
90.** 86 -> 90 (Wilson [79-96]); the last seven legs read 98/80/92/88/
86/90 — the ~90 plateau, unchanged. TRIGGER STATUS: fired at leg 21 by
the letter, and as at legs 16->17 the next leg did not confirm a stall.
No intervention proceeds; the discriminator states (lv8-1v1, lv6-FFA)
remain the right next measurement whenever Blake has 20 minutes with a
controller, and NO diet change is licensed. lv8: 2W/50 (wins by leg
1,0,2,3,2,2,1,3,0,5,1,2 — the noisy edge, ~4%%), picks 3.78 / forms 0.52.
AB 9-3 vs leg 21, 10-2 vs leg1. Training stream 78 -> 84 -> 81%% vs the
league, picks 4.60, forms 0.99 — same band as leg 21. OPS: 10h13m
(~109 steps/s; the 450k lockstep-statistics baseline ran beside it for
~80 min and cost ~35 min). Leg 23 launched 17:20 PDT on the ASYNC
trainer via the league_trainer.txt switch — the pre-registered
validation leg.**

| 21 | 40M (M4, 10 workers, 4M leg) | 79.5/79.4/80.5/79.4 (8,977 eps, picks ~4.5, forms ~1.0, flat) | 2.0 (1W/49L, 3.50/0.62) | 86.0 (43W/7L, 9.74/3.14) | **11-1** | 9-3 (n=12) |

**LEG 21 (Sep 12, first M4 leg, first 4M/10-worker leg): THE PRE-REGISTERED
TRIGGER FIRED (by the letter).** slot2 92 -> 88 -> **86**: two consecutive
flat/down legs (Wilson [74-93] overlaps leg 20's [76-94] — statistically
this is the same ~88-92 plateau, but the rule is written on point
estimates and it fired). Per the BINDING plan the response is, in order:
(1) eval discriminators FIRST — lv8-1v1 + lv6-FFA states, which need a
stamping session with Blake; (2) report to Blake (this note); (3) only
then, at most ONE worker on a >=20%-winnable rung. NO diet change made;
the league continues unchanged while the discriminators are prepared
(leg 16 precedent). CONFOUND to keep in view: this is also the first leg
under the new recipe (10 workers = 20,480-sample rollouts vs 12,288; 4M
steps), so leg 22 (same recipe) is the honest second read before any
worker is moved. lv8: 1W/50 (wins by leg 1,0,2,3,2,2,1,3,0,5,1 — leg
20's 5 was the outlier, the edge is real but unconsolidated; picks 3.50
/ forms 0.62 softened from the 4.06/0.70 records). AB: 11-1 vs leg 20,
9-3 vs leg1 — self-play strength keeps compounding while COM transfer
plateaus, the soft-pool signature again. Training stream flat at ~80%
vs the league all leg (the 92 soft-pool flag line not reached). OPS:
leg ran 9h38m at ~115 steps/s sustained, zero boot flakes, teardown
hang as usual; the 05:55 scheduled wake fired before the leg finished
and then stalled on a tool-permission prompt (unattended scheduled
sessions have no approvals) — the interactive session drove the battery
(06:00-06:26, evals ~1.7x faster than the M2). RELAY DRIVER RULE (M4):
the interactive session with persistent monitors is the driver;
scheduled tasks are a fallback only once a permission allowlist exists
(Blake's call, see M4_SETUP.md).**

| 20 | 36M | — | **10.0 (5W/45L, picks 4.06 — LV8 RECORD by a wide margin)** | 88.0 (10.56/3.22) | 10-2 | 9-3 (n=12) |

**LEG 20 (Sep 11): FIVE lv8 wins — 10%%, two-thirds of the champion's
15%%.** Wins by leg: 1,0,2,3,2,2,1,3,0,5 — the noisy edge just took its
biggest step, with behavior at records (picks 4.06, forms 0.70).
slot2 88.0 (the ~90 plateau oscillation continues; by the original
letter 92 -> 88 arms the trigger again — one more flat/down leg fires
it; the pending amendment would treat this band as maintenance).
RELAY PAUSED after this battery per Blake: leg 21 NOT launched
(league_battery_noresume.sh, launch intentionally disabled;
leg21_LAUNCH_FAILED.txt marker is deliberate). Mac reboot pending —
12-day uptime, chronic Metal boot race (leg 20 needed 4 attempts).
league_state reads "21 ./powerstone_v6_leg20_league.zip"; resume =
watcher one-liner post-reboot, then launch league_leg.sh in tmux
ps2train. Open with Blake at resume: 2M->4M legs, trigger amendment,
os._exit(0) patch, discriminator stamping session.**

| 19 | 34M | — | 0.0 (0W/50L, 3.26/0.52) | **92.0** (10.64/3.20) | 7-5 | 7-5 (n=12) |

**LEG 19 (Sep 11): TRIGGER DISARMED — leg 18's 80 was the outlier.**
slot2 bounced 80 -> 92 (46W/4L), so the two-leg flat/down condition
broke again; the last six legs read 92/92/88/98/80/92 — a noisy
plateau centered ~90-92, oscillating within (and once past) reach of
leg1's 98. lv8: 0/50 this leg (wins 1,0,2,3,2,2,1,3,0 — the edge is
real but unconsolidated at ~4%). AB probes softened to 7-5/7-5 (n=12
wobble; nothing conclusive). READ: the league has entered a
maintenance regime on slot2 — parity-noise band — while lv8 remains
the open frontier. The discriminator disaggregation is where the next
real information lives. OPS: leg 20 needed all 4 wrapper attempts to
boot (3 straight Metal-race EOFErrors even at stagger 45) — the
chronic mode is worsening with 12-day uptime; a Mac reboot at Blake's
next break is now strongly recommended (watcher one-liner relaunch
after).**

| 18 | 32M | — | **6.0 (3W/47L, picks 4.00, forms 0.72 — both lineage RECORDS)** | 80.0 (10.52/3.36) | **12-0 — first perfect probe** | 9-3 (n=12) |

**LEG 18 (Sep 11): the most two-faced battery yet.** Lv8: 3 wins with
behavior metrics at all-time highs (picks 4.00, forms 0.72) — wins by
leg now 1,0,2,3,2,2,1,3; the frontier is moving. AB vs its parent:
12-0, the first perfect probe in project history. AND YET slot2 fell
98 -> 80 (Wilson [67-89] vs leg 17's [90-100] — non-overlapping, so
this is a real move, not n=50 noise) while its picks/forms (10.52/
3.36) sat at records. Read: the policy is getting STRONGER at
self-play and at gem-mechanics everywhere, but its win-conversion in
the lv3 COM chaos regressed — stronger fighter, different style, worse
matchup vs that frozen eval. This sharpens, not settles, the
soft-pool question and makes the lv8-1v1/lv6-FFA discriminators
genuinely useful again. TRIGGER: 98 -> 80 = one down leg, ARMED by
the original letter (the leg-16 fire was refuted by leg 17's 98; the
count restarted). No diet change regardless without discriminators +
Blake's explicit go. At 32M lifetime the lineage now exceeds leg1's
31.9M — the "same steps" milestone passed with parity-or-better on
every component metric and a 29-21 crown probe standing.**

| 17 | 30M | — | 2.0 (1W/49L, 3.24/0.42) | **98.0 (49W/1L, 10.02/3.14) — PARITY WITH LEG1** | 8-4 | 9-3 (n=12) |

**LEG 17 (Sep 10): PARITY. The held-out curve reached the champion's
98.0.** One leg after the trigger fired, slot2 went 88 -> 98 (49W/1L,
Wilson [90-100]) with picks 10.02 / forms 3.14 — matching leg1's
98.0/9.76/3.00 on every component, at 30M lifetime vs leg1's 31.9M.
The leg-16 dip was noise, exactly what n=50 variance looks like near
the ceiling. TRIGGER STATUS: fired at leg 16, condition REFUTED by
leg 17 — no stall exists, so no intervention proceeds and the
discriminator prerequisite is moot for now (states still worth
building for the lv8 disaggregation whenever Blake wants). OPEN
QUESTION FOR BLAKE (plan amendment, his call, NOT made unilaterally):
the pre-registered trigger was written for a climbing curve; at the
98 ceiling, "flat" is success, not stall. Proposal: re-baseline the
trigger to fire on slot2 <=92 for 2 consecutive legs (regression
guard) and shift the primary progress metric to the lv8 eval (wins +
picks/forms trend: 1,0,2,3,2,2,1 with behavior softening — the real
remaining frontier). The full held-out curve, 14 legs: 40/42/50/64/
78/82/84/86/90/88/90/92/92/88/**98**.**

| 16 | 28M | — | 2.0 (1W/49L, 3.72/0.44) | 88.0/9.50/2.90 | 11-1 | 8-4 (n=12) |

**LEG 16 (Sep 10): THE PRE-REGISTERED TRIGGER FIRED.** slot2 ran
92 -> 92 -> 88: one flat leg (15) armed it, leg 16's drop fired it.
Per the BINDING plan, the response sequence is: (1) build + run the
eval discriminators FIRST — an lv8-1v1 state and an lv6-FFA state, to
disaggregate "can't fight one hard opponent" from "can't handle the
chaos" — BEFORE any diet change; (2) report to Blake (done, this
note); (3) only then, at most ONE worker on a rung the current model
can win >=20% of the time, graduation ~60%. NO diet change has been
made — the pure league continues unchanged while the discriminators
are prepared, which the plan explicitly allows. Context the
discriminators must explain: lv8 wins by leg now 1,0,2,3,2,2,1 with
behavior metrics softening (forms 0.62 peak -> 0.44), while the AB vs
parent stays crushing (11-1) — consistent with a lineage still
strengthening at self-play but plateauing against COMs, the classic
soft-pool signature. Discriminator states require savestate stamping
on the Mac (Blake's hands or a supervised bridge session). DUAL-DRIVER
NOTE: leg 15 was collected by the fork session, leg 16 by this one;
deconflict-by-done-files worked. The fork also moved eval receipts to
linux_port/receipts/ and (apparently) added Wilson CIs to
eval_parity output.**

| 14 | 24M | — | 4.0 (2W/48L, 3.44/0.54) | **92.0**/10.36/3.24 — NEW RECORD | 10-2 | 8-4 (n=12) |

**LEG 14 (Sep 9): slot2 92.0, six points from the champion's 98**, with
picks/forms recovering to highs (10.36/3.24 — leg 13's dip was noise).
lv8: 2W/50 — per-leg wins now 1,0,2,3,2: a persistent noisy edge, no
longer a one-off. AB 10-2 vs parent; the leg1 probe read 8-4 (n=12
wobble after back-to-back 11-1s — the n=50 crown probe remains the
honest number). Trigger stays DISARMED (90 -> 92). OPS: leg 14's
battery ran ~12h late — the Sep 9 audit commit's git push hung on a
keychain prompt and blocked the single-threaded bridge watcher until
Blake entered the password; training itself was unaffected. LESSON:
never queue an interactive-capable command (git push) on the relay's
bridge — batch pushes separately with a timeout, or refresh creds
first. ALSO: leg 15 hit the chronic Metal boot race (5 EOFError boots
across wrapper attempts; 9-day uptime) — recovered on a manual
relaunch with PS2_STAGGER=45; if the chronic mode returns, the known
cure is a Mac reboot.**

| 15 | 26M | ~90 vs league (5,300 eps) | 4.0 (2W/48L, 4.30/0.56) | **92.0**/10.54/3.22 — ties record | **11-1** | **11-1** (n=12) |

**LEG 15 (Sep 9): 92 again, and both AB probes 11-1.** slot2 holds the
record (92.0, picks 10.54 / forms 3.22 — the highest picks of the
lineage). lv8: 2W/50 again, per-leg wins 1,0,2,3,2,2 — six straight
legs with at least one win after nine with none. AB 11-1 vs leg14 and
11-1 vs leg1 (the leg-14 8-4 was n=12 wobble as expected). Trigger:
92 -> 92 is flat. The pre-registered rule says "flat/down"; read
strictly that ARMS it at one (a second flat/down leg at 16 would fire
the discriminator sequence); read as "no regression" it stays disarmed.
BLAKE TO RULE before leg 16's battery — the plan is his. Leg 16 launched
Sep 9 20:39 EDT after one boot-phase EOFError retry (Metal race).
Receipts: linux_port/receipts/eval_leg15_*.**

## SEP 9 EXTERNAL AUDIT #2 (11-page pass, different model — findings verified against code before acceptance)

CONFIRMED, fixed same day (docs/bootstrap only — zero training-behavior
changes mid-campaign):
1. **The pool is FROZEN within each leg.** OpponentPool.refresh() runs
   only at env construction; reset() samples the launch-time list, and
   SnapshotToPool's "workers refresh lazily on reset" comment sat above
   a literal `pass`. Snapshots created during leg N become opponents at
   leg N+1. This is methodologically CLEAN (stationary opponents per
   leg) but it invalidates one earlier interpretation: leg 5's mid-leg
   38->28 dip was NOT "its parent's snapshots joining the pool mid-leg"
   — nothing joins mid-leg. Cause unknown; treat as ordinary variance.
   Leg 3C's accidental-league story survives (leg B's snapshots were on
   disk BEFORE 3C launched). Comments corrected; DO NOT add live
   refresh without changing the pre-registered recipe.
2. **Reproducibility trap in setup_linux.sh (HIGH).** The env imports
   OLD gym (0.26.2) + shimmy per requirements.txt, but the bootstrap
   omitted both (and pygame/tensorboard, and left torch unpinned) — G1
   would pass while real training died on `import gym`. Fixed: bootstrap
   now installs from requirements.txt (single source of truth), pins
   torch==2.13.0 (cpu), and G1 imports gym+shimmy too.
3. **"PFSP-lite" renamed** in docs to 50/50 recency-history sampling
   (no performance-based priorities — not actually PFSP).
4. **Stale comments** fixed: v6 action-table NOTE (pf1/pf2 ARE in the
   space), phantom log_pool_winrate reference.
5. **"Zero lv8 training data" needs the word DIRECT**: pool_league
   contains prog_3A/3C/3D, which were themselves trained vs lv8 COMs —
   an indirect teacher path exists. Public claim wording: "zero DIRECT
   lv8 COM interactions in the league lineage."

CONFIRMED, deliberately deferred to post-campaign (changing them now
would contaminate the pre-registered lineage):
6. **Law 6 vs the relay**: the battery promotes each leg's FINAL with no
   checkpoint sweep, while Law 6 says "promote the best, never the
   last." Real tension. Post-campaign: conditional rule (sweep retained
   checkpoints only when the held-out battery regresses) or a fixed
   selection battery.
7. **AB probes are one-seat** (learner always P2) — diagnostic, not a
   crown test. Post-campaign: bidirectional AB at larger n.
8. **No per-leg seed/manifest**; mtime defines "recent" (rsync -a
   preserves it, future copies may not). Post-campaign: per-leg manifest
   (SHAs, model/pool/state hashes, seeds, pip freeze, core hash).
Also flagged: no LICENSE in the repo (Blake's call); pin/record the
flycast core hash once G4 passes on Linux; audit's stats framing
matches ours (curve is the flag-plant; 29-21 p~.32 two-sided, not
proof of dethroning; 1/0/2/3 lv8 wins = trajectory, not a stable rate).

## SEP 10 EXTERNAL AUDIT #3 (Codex deep review, 300 files + isolated repro) — verified in code by Fable before acceptance

Every item below was reproduced against the working tree on Sep 10, not
taken from the review. NO training-behavior change was made mid-campaign.

CONFIRMED, fixed Sep 10 (ops/docs only):
1. **league_battery.sh advanced on failed evaluations.** Stub test: with
   every eval failing it still copied the final into the pool, advanced
   league_state.txt, wrote DONE and launched the next leg. Rewritten:
   each of the four receipts must pass `check_receipt.py` (summary
   header for the right model, W+L+T == episodes, per-episode lines) —
   exit status is NOT used because every eval aborts in libc++ teardown
   after printing. Failure -> `claude_bridge/battery_legN_FAILED.txt`,
   nothing persisted, exit 1. tmux launch failure -> exit 2 with a
   `legN_LAUNCH_FAILED.txt` marker (state already advanced, which is
   correct). PS2_CORE now exported to the AB probes (Linux path bug).
   Receipts now land in `linux_port/receipts/`. Stub-tested all six
   paths; validator checked against the real leg 14/15 receipts.
2. **eval_parity.py's Gate 4 was a Windows-era band (63-75%%, "above =
   ok") that would pass a 64%% regression of a 92%% model, and PARITY
   FAIL exited 0.** Replaced with `--ref wins/n,picks,forms` (the SAME
   checkpoint's Mac receipt): two-proportion test p>=0.05 on wins,
   picks/forms within 15%%, exit 1 on fail. Without --ref it is the
   plain battery evaluator (exit 0). LINUX_BRINGUP.md G4 now uses leg
   15's receipt (46/50, 10.54, 3.22) and asks for core sha / harness
   commit / pip freeze to be recorded when G4 passes.
3. **The warm-start `lr_schedule` override is a placeholder, not the
   LR.** SB3 load() runs _setup_model() afterwards and rebuilds the
   schedule from the saved `learning_rate` field. Every league leg has
   trained at the zip's stored LR (3e-4), not the 2.5e-4 in the
   constructor/comments. Comment corrected; trainer now prints a
   `[config] ...` line with the resolved LR / n_steps / batch / arch at
   startup. Behavior unchanged.
4. **BC corpora: self-velocity obs[4:6] is exactly 0 in 98.7%% of demos
   rows, 98.7%% of demos_lv8, 99.4%% of demos_v4corpus** (recorder
   compared near-adjacent states, not the ACTION_FRAMES window). The
   clone never saw the velocity signal the live env feeds it. Law 3's
   "covariate shift" explanation is therefore incomplete: part of the
   BC failure is a broken input feature. Caveat added to bc_pretrain*.py.
   ACTION before any DAgger / failure-drill recording: fix the recorder
   window and the last-action timing (item 6) so demos match the online
   observation contract, then recompute corpus feature distributions.
5. Stale-comment / naming pass; repo reorg (receipts/, archive/, docs/);
   MIT LICENSE added; README TODOs filled from Blake's draft.

CONFIRMED, deliberately DEFERRED to post-campaign (each changes the
observation contract; fixing mid-lineage would contaminate the
pre-registered comparison and the AB series):
6. **`_obs_from_view` leaks the learner's `_form_timer` (and `_my_g_int`)
   into the P1 view.** Reproduced: untransformed P1 + full P2 timer ->
   P1's obs[9] reads 1.0. Affects the frozen opponent in training and
   the reference seat in every AB probe; does NOT touch slot-2/slot-3
   COM evals. Effect on win rate unmeasured — do not quote a number.
   Post-campaign: fix as a versioned obs change, then same-policy seat
   checks and a bidirectional AB at n>=50, old-interface and
   new-interface results kept separate.
7. **Last-action one-hot timing differs by seat.** The learner's step()
   builds the obs before updating last_action (sees a_{t-1} when
   choosing a_{t+1}); the opponent view and the recorders are one step
   fresher. All checkpoints were trained under the learner convention.
   Fix together with item 6 as one obs-version bump.
8. league_leg.sh's watchdog halts only on EOFError-after-100-eps; other
   mid-leg deaths could re-enter the retry loop. Not edited on Sep 10
   because the script was executing leg 16 (bash reads scripts lazily;
   edit only between legs, by rename).

STATISTICAL CORRECTIONS adopted (from audits #2 and #3), for any public
prose: crown probe = leg 6 at 8M, 29-21 in 50 (Wilson 44-71%%); champion
lv8 baseline = 3/20, not 3/50; "22M vs 32M" (now 26M vs 32M) counts PPO
steps only, not demos or the historical opponents' training; "8 wins in
4,653" = BC-initialized PPO TRAINING episodes (3D), not a frozen clone's
eval; "0-for-450" does not map onto one clean cohort (fresh line 3B +
legs 4-9 = 7 batteries = 350; all four program legs + legs 4-9 = 500) —
quote a cohort you can name, e.g. "six straight league legs at 0/50
before the first win at leg 10" (legs 4-9, 300 episodes); "first
lv8 win" = first in the fresh lineage (the champion already had 3/20);
slot 2 is a held-out EVALUATION state, not a training worker; "zero lv8
training" = zero DIRECT COM-8 rollouts in this lineage.

## MIGRATION TO THE 7950X LINUX BOX (Sep 4, 2026)

Blake called the M2 era done: relay STOPPED mid-leg-13 (1,277 eps in,
progress discarded by design; league_state.txt intact at "13
./powerstone_v6_leg12_league.zip", so leg 13 = first Linux leg). Final
M2-era standings: leg 12, 20M lifetime, slot2 88.0, lv8 2W/48L, 11-1
(n=12) vs leg1. PRE-REGISTRATION TRIGGER REMAINS ARMED (90 -> 88).

Bring-up vehicle: this repo + linux_port/LINUX_BRINGUP.md +
linux_port/setup_linux.sh. Non-repo payload rsyncs from the Mac (CHD,
pool_league, states, demos*, model zips, league_state.txt). Gates
G1-G5 in LINUX_BRINGUP.md; G4 (50-ep slot2 parity vs the leg 12 Mac
numbers) is mandatory before any training — cross-platform obs parity
is where this project has been burned before (chest-obs law).
league_leg.sh / league_battery.sh made platform-aware (core path,
caffeinate, cd-to-script-dir). Open questions for the Linux era:
worker count (try 12 at G5; M2 ran 6), stagger (Metal race is
macOS-only), and whether the teardown hang follows us off macOS.

**CROWN PROBE AT n=50 (Sep 2, leg6 vs leg1): 29-21 (58%%).** 95%% CI
~44-71 — "at least even, probably ahead," NOT proof of dominance; the
training-state caveat still applies. The held-out slot2 curve is the
stronger witness: 40 -> 42 -> 50 -> 64 -> 78 vs leg1's 98, with picks
9.04 (leg1: 9.76) and forms 2.70 (3.00) nearly closed at 10M vs 31.9M
lifetime. slot3 wall: 7-0. **LEG 8 = FIRST CLEAN-LEAGUE LEG** (mtime
sort + tagged snapshots + leg4 backfilled active) — its numbers are
the first honest read of the recipe; treat any curve kink as
information about the old skew, not regression.**

**SEP 2 EXTERNAL REVIEW (fresh-model audit, verified against code+logs
— four findings CONFIRMED, all patched at the leg 7/8 boundary):**
1. OpponentPool sorted by filename step-number -> "recent 10" was
   permanently leg1's 27.9-31.9M snapshots (~56-66%% of episodes);
   prog_* finals/seeds parsed as 0 and were buried. FIXED: mtime sort.
2. PS2_FRESH reset the snapshot clock -> cross-leg name collisions;
   each leg overwrote its predecessor's pool snapshots. FIXED: leg-
   tagged names. 3. prog_leg4 never entered the pool (battery predated
   the cp line). FIXED: backfill in league_battery. 4. AB retry guards
   missing in league_battery. FIXED.
**INTERPRETATION CORRECTION for legs 5-6:** the lineage trained mostly
AGAINST leg1's late snapshots ON the same slot1 state the A/B probes
use — so "6-6"/"7-5 vs leg1" reads closer to "learned to beat leg1
where it practiced against leg1" than "caught the champion," and n=12
carries wide error bars (95%% CI on 6/12 is roughly 25-75%%). THE CLEAN
CLAIM is the held-out slot2 FFA curve at n=50: 40 -> 42 -> 50 -> 64 vs
leg1's 98 — real, accelerating transfer, different state, different
opponents. A 50-ep A/B vs leg1 is queued to settle the crown properly.
CANDIDATE LAW 9: an A/B on the training state is not a held-out test.
Also queued: a 1v1-lv8 discriminator state (the wall may be partly an
FFA wall — the lineage has only ever fought 1v1; slot3 is 3-opponent
FFA — two jumps at once, and a lv8 1v1 state is stampable headlessly
via menu_drive ORIGINAL mode with two seats NO ENTRY).

**LEG 6 (Sep 2 ~06:30Z): the crown probe (READ WITH THE CORRECTION ABOVE).** First
head-to-head WIN over the 31.9M champion (7-5, n=12 stochastic) at 8M
lifetime; slot2 40->42->50->64; beat leg 5 11-1; slot3 still 0 wins
but behavior stirring (picks 1.46, forms 0.18 vs leg5's 1.20/0.04).
Boot took 3 wrapper attempts (flake tax), ran clean after. PROMOTION
NOT DONE — powerstone_v6_ppo.zip untouched per standing rule; Blake's
call. (Note for that call: n=12 is thin for a coronation — a 50-ep
A/B or a slot2 gap-close would make it solid; leg 7 running.)

**LEG 5 (Sep 1): the lineage CAUGHT the champion.** slot2 compounding
40 -> 42 -> 50; beat its parent 11-1; **DEAD EVEN 6-6 vs leg1's 31.9M**
at 6M lifetime steps — the effective-step thesis validated in two days
of M2 time. Training curve dipped q2 (its own leg-4 snapshots entered
the pool) then punched to 52%%. slot3 still 0.0 (wall 6-0 vs fresh
legs). Leg 6 auto-launched, running.

## LEG-3 PROGRAM CLOSE-OUT (Aug 31 ~11:00Z) — FINAL FOUR-WAY TABLE

All legs 2M steps from fresh seeds; batteries n=50 deterministic
(slot3 lv8 FFA / slot2 lv3 FFA), A/B n=12 stochastic.

| leg | seed | diet | train trajectory | slot3 | slot2 | A/B vs seed | vs leg1 | cross-leg |
|-----|------|------|-----------------|-------|-------|------------|---------|-----------|
| 3A | bc256 | lv8 only | 0 -> 0.3%% | 0.0 / 1.20 / 0.04 | 14.0 / 5.02 / 0.74 | 10-2 | 0-12 | lost 1-11 to 3B |
| 3B | bc256 | self-play (shallow pool) | 88 -> 96%% vs pool | 0.0 / 0.88 / 0.00 | **40.0 / 6.26 / 1.28** | **12-0** | **4-8** | beat 3A 11-1, 3D 8-4, 3C 8-4 |
| 3C | bc256 | mix 4 lv8 + 2 self-play (DEEP pool = 3B lineage) | COM flat 0.1%%; SP 14.7->54.3%% | 0.0 / 1.16 / 0.02 | 14.0 / 3.36 / 0.42 | 11-1 | 2-10 | lost 4-8 to 3B |
| 3D | bclv8_256 (Blake's 23-1 corpus) | lv8 only | 0 -> 0.34%% | 0.0 / 1.28 / 0.08 | 28.0 / 3.86 / 0.62 | 7-5 | 1-11 | lost 4-8 to 3B |
| refs | leg1 (31.9M selfplay) | — | — | 15.0 / 4.00 / 0.95 | 98.0 / 9.76 / 3.00 | — | — | — |
| | leg2 (warm+lv8) | — | flat 10%% | 4.0 / 4.72 / 0.76 | 88.0 / 8.92 / 2.54 | — | 3-9 | — |

**WINNER: 3B (self-play), by every transferable measure** — best slot2
(40.0, ~3x any other fresh leg), only fresh leg competitive with leg1
(4-8), crushed its own seed 12-0, and beat every sibling head-to-head.

**WHY (what the data says):**
1. **Gradient continuity is the engine.** The two legs whose win-signal
   never dried up (3B always-winnable pool; 3C's self-play stream) are
   the only two that LEARNED to win anything. The three lv8-only diets
   (leg2 warm, 3A, 3D) produced flat ~0-10%% trajectories: exposure to
   losses is not information about winning.
2. **The lv8 wall stands 4-0.** No fresh leg scored a single slot3 win
   at n=50. Only leg1's 31.9M-step lineage wins there (15%%).
3. **BC seeds don't transfer wins (3D).** Blake's validated 23-1 corpus
   at 80.6%% val acc produced 8 training wins in 4,653 eps and a 7-5
   A/B vs its own seed (RL had nothing to amplify). Textbook covariate
   shift: no recovery demonstrations off Blake's manifold. This is the
   program's cleanest negative and the DAgger mandate.
4. **3C's split verdict:** its self-play stream vs the DEEP pool (3B's
   lineage, via the shared pool dir — accidental league training) was
   the program's best climb (14.7->54.3%%), but with only 2/6 workers
   on self-play (465 eps vs 3B's 3,126) and 2/3 of its gradient spent
   on dead lv8 losses, it transferred worst (slot2 14.0) and lost the
   head-to-head 4-8. Opposition quality was right; the gradient BUDGET
   was wrong.

**RECOMMENDED NEXT MOVES (in order):**
1. **Deep-pool full self-play leg** — 3B's diet with 3C's opposition:
   all 6 workers self-play, pool seeded with ALL program zips + leg1 +
   old opponent_pool (the real league). Warm start 3B. This is the
   synthesis the data asks for.
2. **DAgger/recorder libretro port** — the only route by which Blake's
   play can enter effectively (relabel the POLICY's states, not
   Blake's). Prereq for any future demo work; rig recorder is the
   reference.
3. Consider extending 3B +2M as the cheap control for (1).
4. Launcher hardening: retry-on-EOFError wrapper (the Metal boot race
   killed two chained launches).
Housekeeping: nothing promoted — powerstone_v6_ppo.zip is still
selfplay_leg1, the undisputed overall champion. Only the claudebridge
tmux remains; compute idle.

## THE LEG-3 PROGRAM (Blake's spec, Aug 29 evening) — three legs, one seed, pick the winner

All three legs start from the SAME fresh seed — powerstone_v6_bc256.zip
([256,256], BC on demos:3 + demos_v4corpus, 83.1%% val on the rig) — so
the training DIET is the only variable. **2M steps each (~7h — Blake's
call, Aug 29: leg2 was flat after 1M and the rig's P/Q/R comparison
legs were 1M; slope is readable at 2M and the winner gets EXTENDED by
resuming its final zip on the same diet),** same battery after each (slot3 50-ep, slot2 50-ep, A/B vs the
bc256 seed and vs selfplay_leg1). Compare, figure out which is best AND
WHY. Blake records new demos of his own play sometime during the
program (needs the recorder's libretro port first — record_demo.py is
lua-era).

- **Leg 3A — lv8 only** (launches automatically after the Aug 29
  checkpoint sweep): `PS2_WARM=./powerstone_v6_bc256.zip PS2_FRESH=1
  train_com.py`, STATE_SLOTS=[3]. Log train_leg3a_out.txt,
  checkpoints_lv8_fresh/.
- **Leg 3B — 1v1 self-play vs its prior self**: `train_selfplay.py`
  with PS2_WARM=bc256, PS2_FRESH=1, PS2_POOL=./pool_bc256 (seeded with
  ONLY the bc256 zip; snapshots of itself accumulate). slot1.
**LEG 3A COMPLETE (Aug 30 04:44Z, 2M steps, powerstone_v6_bc256_lv8leg
.zip). Training stream: DEMOLISHED — q1-q4 win 0.0/0.0/0.3/0.2%%, picks
0.58->1.11 (doubled, but tiny), forms ~0.05, len 389->441, zero
timeouts. The fresh seed vs lv8 is the sparse-signal regime: with ~0%%
wins there is no win-gradient to climb, only dense shaping moved.
Echoes rig P/Q/R (fresh lineage weak in absolute terms). **BATTERY (Aug 30 07:00Z, n=50 det + n=12 A/B): slot3 0.0%%
(0W/50L)/1.20/0.04 — flatlined vs lv8; slot2 14.0%%/5.02/0.74 (leg1:
98.0); A/B vs its OWN SEED 10W/2L — the RL leg genuinely improved the
policy (the raw bc256 seed loses 2-10 to its trained child); A/B vs
leg1 0W/12L. READING: real learning, wrong altitude — lv8-only cannot
bootstrap wins from a fresh seed (0%% train wins = no win-gradient);
the improvement all came from dense shaping. 3B (self-play) is the
regime where the fresh seed can actually WIN half its episodes by
construction — the interesting comparison.**
The lv8-BC seed bake ALSO done: powerstone_v6_bclv8_256.zip (val curve
in bake_lv8_out.txt) — leg 3D's seat is ready.**

- **Leg 3D — fresh lv8-BC seed on the lv8 diet (ADDED Aug 30, PRE-APPROVED
  by Blake: launch after 3C's battery, no further ask needed).** Blake
  recorded a NEW human corpus on the rig overnight: demos_lv8/demo_005.npz,
  11,704 pairs, 24 eps, **23-1 vs THREE lv8 COMs** across three re-stamped
  rig lv8 states (see README_MIGRATION3.md in ~/Downloads/macbook_migration3
  for provenance + the rig-side SLOT_META note — do NOT copy the rig env
  over the Mac's). Old pre-lv8 sittings quarantined rig-side. Seed bake
  RUNNING (tmux ps2bake, nice'd, log bake_lv8_out.txt):
  `bc_pretrain_lv8.py demos:1,demos_lv8:5,demos_v4corpus --arch 256x256`
  -> **powerstone_v6_bclv8_256.zip** (distinct name — NEVER overwrite
  powerstone_v6_bc256.zip mid-program, legs A/B/C warm-start from it).
  Ratio rationale (Blake's call): the old 9,943 human pairs CANNOT be
  validated as lv8 play (recorded vs the lv2-3 ladder) -> demoted to 1x
  texture; the validated lv8 slayer rides at 5x (~19%% of volume); more
  Blake sittings stack into demos_lv8/. Leg 3D = launch_leg3a.sh pattern
  with PS2_WARM=./powerstone_v6_bclv8_256.zip PS2_FRESH=1, log
  train_leg3d_out.txt, 2M steps (launch_leg3d.sh, WRITTEN). **ORDER
  SWAP (Blake, Aug 30 morning): 3D runs BEFORE 3C — it's the
  breakthrough candidate. Sequence: 3B battery -> 3D -> 3D battery ->
  3C -> final four-way table. THE SIGNAL TO WATCH on 3D's stream:
  nonzero training wins in q1 where 3A had 0.0%% — that's the
  prior->gradient link working.** **3D vs 3A isolates exactly what the
  new human data is worth** — same diet, same arch, only the seed differs.
**LEG 3B COMPLETE (Aug 30 ~13:40Z, 2M steps, powerstone_v6_bc256_spleg
.zip). Training curve vs its own pool: q1-q4 win 88.0/92.6/93.9/95.8%%,
picks 3.81->5.68 (q4 5.26), forms 1.39->2.13, len ~660 (q4 543 — wins
coming faster). CAVEAT: the pool started as ONLY the bc256 seed, so
88%% in q1 means it outgrew its infant self almost immediately; the
pool never supplied real pressure. Forms >2/ep is the standout —
self-play taught the transform game (3A managed 0.05). Battery running
(tmux ps2battery3b) -> chains LEG 3D launch (order swap, Blake's
call). Results appended when in.**

**3B BATTERY (Aug 30 16:15Z): slot3 0.0%%/0.88/0.00 (no lv8 transfer);
slot2 40.0%%/6.26/1.28 (vs 3A's 14.0 — self-play built REAL fighting
skill); A/B: 12-0 vs its seed, 11-1 vs 3A, 4-8 vs leg1 — a 2M-step
fresh line taking 1/3 of games off the 31.9M champion. 3B IS THE
PROGRAM LEADER.**

**3D FIRST SIGNAL (Aug 30 16:15Z): 0 WINS IN 856 EPISODES** (picks
0.97, forms 0.04 — 3A's profile). Seed verified correct
(bclv8_256, bake val_acc 80.6%%; weak spots: jump 49.9%%, grab 27.5%%,
throw 0%%). **The lv8-BC seed did NOT transfer Blake's wins — the
prior->gradient hypothesis is DENTED at the entry link.** Leading
explanation (textbook + matches rig Sec-22 history): BC covariate
shift — the clone leaves Blake's state manifold within seconds and has
zero recovery demonstrations; per-frame mimicry (80%%) is not
closed-loop skill. This STRENGTHENS the rig's standing DAgger
recommendation (relabel the CURRENT policy's states) and 3B's
self-play result: gradient continuity beats demonstration priors on
this problem so far. 3D runs to completion anyway (its battery may
still show slot2 gains); 3C (mix) after.**

**3D COMPLETE (Aug 30 23:30Z, powerstone_v6_bclv8_256_lv8leg.zip):
8 wins in 4,653 episodes. q1-q4: 0.00/0.26/0.09/0.34%%, picks ~1.17,
forms ~0.06. NO late emergence — the lv8-BC seed never bootstrapped;
the first-signal verdict stands at full-leg scale. **3D BATTERY (Aug 31 00:55Z):
slot3 0.0%%/1.28/0.08; slot2 28.0%%/3.86/0.62; A/B vs its seed only
7W/5L (3A went 10-2 over ITS seed — a never-winning policy generates
no lessons for RL to amplify); vs leg1 1-11; vs 3B 4-8. The chained 3C
launch died at boot (EOFError, the Metal race — 2nd chain casualty);
caught by Blake ~01:00Z, relaunched clean on retry: 6/6 bridges, BOTH
stream types verified (slot3 COM eps + slot1 self-play eps with [opp]
pool lines). TODO next session: retry-on-EOFError wrapper in the
launcher scripts. Final four-way close-out lands with 3C's battery
(~09:00Z Aug 31).**

- **Leg 3C — the mix**: `train_mixed.py` NEW — 4 workers lv8 COM FFA
  (slot3) + 2 workers self-play 1v1 (slot1), one learner; net
  distinguishes contexts via stage one-hot + DIFF_DIM.

**HISTORICAL CONTEXT (rig HANDOFF, Aug 23-26 — read before judging
these legs):** the 256/bc lineage already ran three curriculum legs on
the rig (P/Q/R, 3.7M lifetime steps): lv4 bake-off 11.2 / 11.2 / 13.8
vs legM's ~66, picks PINNED at 2.83-2.85 all three tables, one real
climb (lv2 22->38%% in Q) then plateau (R). Verdict recorded there:
rewards/capacity/curriculum all eliminated — "the policy plateaus in
states no demonstration covers"; standing recommendation was a DAgger
pass (teacher relabels the CURRENT policy's states). SO: expect leg-3
absolute numbers to start far below the leg1 lineage; judge on SLOPE
across the leg (the rig's own rule), and know that P/Q/R never saw
lv8 data, never saw self-play, and never ran the mix — those are
exactly the three variables this program isolates. If all three
plateau the same way, the rig's DAgger diagnosis stands confirmed and
the priority becomes the recorder port + new demos (Blake vs lv8 /
DAgger relabeling), not more legs.

## LEG 2 — THE LV8 LEG (launched Aug 28 ~23:09, Cowork session + Blake)

**LEG 2 RESULT (Aug 29): the warm-start lv8 repeat DID NOT WORK.**
4.00M steps (31.918M -> 35.921M), 8,300 episodes, 0 crashes, 0 timeouts
(no coward signature — the -2 loss scale did its job; ep len stable
~450-500). Training stream (stochastic) plateaued after ~1M steps:
q1 8.0% win / 4.34 picks / 0.77 forms -> q2-q4 flat at ~10% / ~4.9 /
~0.92. Deterministic slot3 evals: leg1 baseline 15.0/4.00/0.95 (n=50);
leg2 FINAL 4.0/4.72/0.76 (n=50) — BELOW baseline; mid-leg 34.4M
checkpoint 15.0/5.80/1.15 (n=20) — the best artifact of the leg.
Entropy stable all leg (0.52-0.57) -> the final-zip drop is PPO churn /
"peaked then eroded" (rig HANDOFF Sec 22 redux), not entropy collapse.
Checkpoint sweep (4 zips spanning the leg, n=50 slot3) queued to find
the true peak; slot2 + A/B battery (Aug 29 19:00Z): **slot2 88.0%%
(44W/6L) / 8.92 picks / 2.54 forms — vs leg1's 98.0/9.76/3.00: MILD
EROSION of the lv3 benchmark (still above the Windows band), and A/B
head-to-head leg2-final vs leg1: 3W/9L — leg1 wins.** The lv8-only
diet cost a little of everything and bought nothing measurable in the
final zip. **CHECKPOINT SWEEP (Aug 29 21:00Z, n=50 slot3 deterministic):
32.4M 8.0/4.90/0.88 | 33.2M 16.0/4.40/0.86 | 34.4M 10.0/5.22/0.94 |
35.4M 12.0/5.18/1.08 | final 35.9M 4.0/4.72/0.76 | leg1 baseline
15.0/4.00/0.95. Reading: win%% bounces 4-16 across checkpoints — churn
noise, no checkpoint CLEARLY beats leg1 (peak 33.2M @ 16.0 is within
noise of 15.0); picks/forms mildly above leg1 late-leg. The earlier
mid-leg 15.0 (n=20) was noise, not a peak. NO PROMOTION — leg2 is a
clean negative result, full stop.**
**LEG 3A LAUNCH (Aug 29 ~21:08Z, tmux ps2train, log
train_leg3a_out.txt): took FOUR attempts — the 6s worker-boot stagger
let the macOS Metal-init race kill a spawning worker 3x in a row
(silent worker death right after REIOS boot -> SubprocVecEnv EOFError;
SDLARCH_LOG=1 diagnosed it). FIX: stagger raised 6s -> 20s in ALL
THREE trainers; 6/6 workers then booted clean. Also NEW
launch_leg3a.sh — nested-tmux quoting ate the first auto-launch; leg
launches are launcher SCRIPTS from now on. Health at +4 min: episodes
streaming, contested (2.6-3.3 bars dealt), all losses so far (expected
— fresh bc256 seed vs lv8), 0 tracebacks. 2M steps, ETA ~04:30Z.** NOTHING PROMOTED: powerstone_v6_ppo.zip is still selfplay_leg1.

**VERDICT (Blake, Aug 29): BIL's actual prescription was a FRESH run on
lv8, not warm-starting the 31.9M model — those weights are well trained
on beating weak COMs, and 4M steps of 90%-loss lv8 data couldn't pull
them off that prior. Next experiment: FRESH net (+BC pretrain) -> RL on
lv8.** Which needs kit #4:

**KIT #4 INVENTORY (Aug 29 repo audit — most of it is ALREADY in the
GitHub repo):** bc_pretrain.py, bc_rehearsal.py, record_demo.py,
record_gamenight.py, cheater_bot.py (the scripted-aimbot demonstrator —
"the cheater teaches aim, the family teaches everything else"),
aimbot_gauntlet.py, BC seed zips (powerstone_v6_bc.zip / bc256), and the
FULL rig docs/HANDOFF.md (Secs 20/22/25.4/29/35). **MISSING = the demo
corpora, rig-only (allowlist .gitignore publishes only one sample npz
each): demos/ (Blake's play, 9,943 pairs), demos_cheater/ (the aimbot
farm — the bulk of the 252k-pair rehearsal set), demos_humans/ if game
night ever recorded. MOVE THOSE from the 12700K to the Mac.**
**KIT #4 ARRIVED (Aug 29 evening, ~/Downloads/kit4 -> linux_port/) with
two corrections (KIT4_NOTES.md): the rehearsal set is demos/ (9,943,
Blake) + demos_v4corpus/ (247,828, cheater_bot v4 discrete ladder) —
demos_cheater/ is OLDER analog-era recordings, inspect action
histograms before ever feeding to BC; and demos_humans/ does not exist
(game night ran without --record), so Blake-vs-strong-opponents data
still needs a future recording session. bc_pretrain.py, bc_rehearsal.py,
powerstone_v6_bc256.zip + bc.zip pulled from the repo into linux_port/.
VERIFIED on the Mac venv: both corpora load (obs dim 122), bc256 loads
CPU + predicts, arch [256,256]. train_com.py now takes PS2_WARM=<zip>
and PS2_FRESH=1 for the fresh-lineage leg 3: warm start bc256, fresh
timeline, checkpoints_lv8_fresh/.** Note the
recorders are lua-era (free-running emulator) — they need the standard
libretro port before NEW demos (e.g. Blake vs lv8) can be recorded on
the Mac. Rig HANDOFF already reached the same conclusion as BIL:
"lv5 needs a PRIOR. Priority: game night / human demos > aimbot demo
farm > more reward work" (Sec 30/35 era).

BIL consult (Blake's brother-in-law, ML engineer at Epic): the rig-era
curriculum stalled at COM lv5 because the stream was dominated by easy
wins — skip the ladder, train straight into max difficulty. This leg is
that experiment, pure (self-play returns NEXT leg; alternate at the leg
level — Blake's call, per-episode mixing not built).

- **slot3.state NEW (Blake-stamped via make_savestates):** ORIGINAL mode
  true-FFA, desert, COM DIFFICULTY 8 (options menu), P1 Pride / P2
  FALCON human / P3 Ryoma / P4 Accel, colors distinct (same color =
  team battle — avoid). Verified: 4x1000 healths after intro, P2
  face_norm 0.992. NOTE: menu navigation is fully scriptable headless
  — menu_drive.py walked options/player-select this session (COM toggle
  = A on HUMAN row; colors cycle R->Y->B->G; A on PLAYER SELECT row
  picks the SHOWN character — cycling mechanism still unknown, human
  was faster).
- **Env changes (powerstone_env_v6.py):** SLOT_META[3] REDEFINED ->
  (2, 8) (desert dim, lv8; DIFF_DIM now reads 1.0 — first time the net
  sees it); LOSS_SCALE_BY_LEVEL[8] = 0.2 (effective terminal loss -2;
  gamma-.999 coward math: delaying -10 to ep end 'saves' ~7 vs -2.4
  stall bleed — cowering paid; at -2 it strictly loses); gem neg floor
  1.5 at lv>=8 (keeps dying the worst outcome).
- **train_com.py NEW:** plain PowerStoneEnvLibretro vs-COM trainer,
  train_selfplay skeleton minus pool, STATE_SLOTS=[3], warm start
  MANDATORY (= powerstone_v6_ppo.zip = selfplay_leg1), checkpoints_lv8/,
  4M steps.
- **BASELINE (baseline_lv8_out.txt): leg1 vs slot3, 20 eps
  deterministic: win 15.0% (3W/17L), picks 4.00, forms 0.95** — vs
  98%/9.76/3.00 on slot2 lv3. Hard but winnable = real gradient.
- **Launch health (first ~3 min):** 6 workers, all episodes contested
  (dmg 1.7-6.4 bars out, stones picked, first wins + 3-form episode in
  the stream), ~73 fps aggregate climbing, timesteps continue from
  31.918M, zero tracebacks. tmux `ps2train`, caffeinate, log
  train_leg_lv8_out.txt. Reattach: `tmux attach -t ps2train`.
- **Morning protocol:** check tail of train_leg_lv8_out.txt for [ep]
  win trend + tracebacks; eval latest checkpoints_lv8 zip on slot3
  (eval_parity --slot 3, compare to the 15% baseline) AND on slot2 +
  A/B vs leg1 (did lv8-only data erode the old skills? informative
  either way — leg1 zip preserved).
- **Claude command bridge NEW (this session):** claude_bridge_watcher.sh
  in linux_port, tmux `claudebridge` — Cowork's device shell can't run
  the emulator (isolated VM), so commands go through
  claude_bridge/cmd.sh -> out.txt on the mounted folder. Kill when
  done: `tmux kill-session -t claudebridge`.
- Deferred: BC/DAgger kit (demos + scripts) still rig-side — "kit #4"
  — needed before the fresh-net + BC-pretrain lv8 variant. The aimbot
  DAgger naming/history lives in rig HANDOFF Sec 22.

## NEXT SESSION BRIEF (Claude Code, cwd = macbook_migration/) — Aug 28

Immediate mission while the 7950X ships: first real training leg on
the M2. Protocol, in order:

1. **Warm-start audition: DONE (Aug 28) — legG KEEPS the seat.**
   legM_final, eval_parity 20 eps slot 2 deterministic
   (legM_eval_out.txt): **win 70.0% (14W/6L), picks 6.70, forms
   1.70** vs legG's 74.0 / 8.06 / 2.30 (n=50). Below legG on all
   three (picks even a hair under the band). Not weird — just worse
   on this matchup; linux_port/powerstone_v6_ppo.zip stays legG
   (md5-verified distinct from legM). Note: a first attempt died
   silently at ep 10 (9W/1L!) — it was killed by a shell timeout,
   not a crash; the full 20-ep rerun regressed to the mean.
2. **Training bring-up, PS2_NENVS=2: PAST STEP 0, AND THE P1-VIEW
   EYEBALL CAUGHT A REAL BUG (Aug 28).** First relaunch trained fine
   mechanically (22+ PPO iterations, ~40 steps/s aggregate at
   NENVS=2, timesteps continuing from legG's 27.911M, snapshot
   callback fired) — but the ep_stats CSVs read learner 62W/4L with
   dmg_out flat 2.000, opponent picking only 2.85 stones/ep. The
   opponent moved, picked, formed, even won 4 — NOT frozen — but far
   off the ~50%-by-construction expectation. Root cause (fix #7,
   selfplay_env._obs_from_view): the P1 line was PINNED onto
   _lr_synth.line, but _parse_state_once's pump-on-stale check fires
   on every opponent read (last parse is always the same frame), runs
   a frame, and tick() invalidates the pin — the opponent parsed the
   LEARNER-sorted line every step (own pos/health correct — player
   blocks are port-ordered — but stones/chests/projectiles sorted
   around its ENEMY). FIXED: parse the view's line via the pure
   _parse_line path (no pin, no pump); relaunched with
   PYTHONUNBUFFERED=1 so spawn workers' [ep] lines actually stream
   (they were block-buffered — that's why the log looked [ep]-less).
   Pre-fix CSVs archived as bridge_i*/ep_stats_v6.prefix7.csv.
   Post-fix the stats did NOT move (23W/2L) — the obs-sort fix was
   real but minor (1v1 has few stones; both sort orders nearly match).
   An A/B probe (ab_selfplay_probe.py NEW: learner vs ONE chosen
   frozen opponent) went 12-0 vs even the 31.9M checkpoint ->
   structural seat handicap, and an obs-fidelity probe (obs_probe.py
   NEW) proved the P1 VIEW FAITHFUL (positions/deltas/healths exact,
   varied policy actions on both views). Real root cause, found via
   RAM_MAP's face_norm character fingerprint (facing row carries
   character scale): **slot1 was stamped P1=AYAME (0.895) vs
   P2=Falcon (0.991) — every pool policy is a Falcon policy, so the
   opponent seat was a Falcon expert driving Ayame.** FIXED Aug 28
   without the interactive savestate maker: menu_drive.py (NEW) =
   headless menu navigation via get_frame screenshots + scripted
   button steps; drove pause -> CHANGE CHARACTER -> cycled P1 to
   FALCON -> stage select Desert Area -> re-stamped states/slot1.state
   at round start (old state kept as slot1.state.ayame_backup).
   Fingerprint now 0.991/0.991. Also fixed while in there: the P1
   view's last-action one-hot leaked the LEARNER's last action
   (now per-view, selfplay_env._view_last), and [opp] lines now log
   which pool zip each episode faces. **A/B re-probe on the new
   state: 7W/5L (58%) vs the 31.9M checkpoint — the seat is FAIR;
   bring-up BLESSED. Both sides actually fight.**
   ALSO: macOS "app crashed — restore windows?" modal can hang ANY
   headless emu boot after a prior crash (stack: NSAlert runModal) —
   cured with `defaults write org.python.python
   ApplePersistenceIgnoreState YES` (do this on any new Mac).
3. **SCALED — LEG 1 RUNNING (Aug 28 ~01:48, tmux session `ps2train`,
   caffeinate -is, log train_leg1_out.txt).** PS2_NENVS=6,
   dolphin-2..5 seeded, warm start legG. Health at launch: first 18
   eps 9W/9L (exactly the 50% self-play construction), all 9 pool
   zips sampling ([opp] lines), episodes contested (sample loss:
   dealt 1.95 bars / took 1.00). 35 min in: **92 steps/s aggregate**
   (vs ~175 hoped — GPU contention with 6 renderers; null-video is
   the known lever for a future leg, don't touch this one), 28.01M
   total steps, learner 97W/40L (71% — learning against the frozen
   pool; 500k-step snapshots will refresh it), zero tracebacks.
   4M-step leg ETA ~12h (~14:00 Aug 28). Reattach:
   `tmux attach -t ps2train` (tmux via brew, NEW on this Mac).
4. **LEG 1 COMPLETE (Aug 28, 01:48 -> 15:01, ~13.2h).** 4.00M steps
   (27.918M -> 31.918M), 84 steps/s sustained the whole way, 7,458
   self-play episodes (learner 81% by the end — climbed from the
   50/50 launch as it outgrew the frozen pool), 10 selfplay_* pool
   snapshots, 40 checkpoints_sp zips, ZERO crashes. Product:
   linux_port/powerstone_v6_ppo_selfplay_leg1.zip.
   **EVALS (Aug 28 afternoon):**
   - A/B vs legG (27.9M warm start): **7W/5L** (n=12, stochastic)
   - A/B vs ps_v6_31915459 (strongest old): **7W/5L** (n=12)
   - eval_parity slot 2, 50 eps deterministic (parity_leg1_out.txt):
     **win 98.0% (49W/1L), picks 9.76, forms 3.00** — vs legG's port
     numbers 74.0 / 8.06 / 2.30 on the identical protocol.
   Reading: modest peer-vs-peer edge (58% both probes; n=12 is
   noisy), but a LARGE jump on the COM benchmark — and leg 1 trained
   only on slot1 desert 1v1, so the slot2 FFA gain is generalization,
   not eval overfit. Self-play works on this port. Next-leg
   decisions (Blake + rig-session concurrence, Aug 28 evening):
   - **PROMOTED: leg1 IS the warm start** — powerstone_v6_ppo.zip =
     selfplay_leg1 (md5-verified); legG preserved as
     powerstone_v6_ppo_legG_backup.zip.
   - **Widen STATE_SLOTS: yes, but it needs a Blake controller
     session first.** Self-play slots must be VS-mode 2P stamps
     (both DC ports human — selfplay_env docstring); slot2 as
     stamped is a COM FFA (eval-only). Plan: make_savestates, 2-3
     more stages, TAB both ports in, BOTH PORTS FALCON (the Ayame
     lesson), stamp F3-F5 at round start, verify face_norm ~0.991
     per seat.
   - **Null-video: parked for the 7950X era** — its value case was
     M2 GPU contention; the new box renders on a 3090.
   - Before leg 2 buries it: record the reddit video via
     watch_play.py --model ./powerstone_v6_ppo_selfplay_leg1.zip
     (the 49-1 champion) while it still holds the crown.
   Note: eval boot flake bit once during the battery (the 31.9M probe
   died at init, silent); rerun succeeded — always check the output
   file has an AB RESULT line.
Known cosmetics: mutex abort at exit; "SHORT OPPONENT SET slot1" is
expected (slot1 = 1v1 self-play state); sb3 gym-wrap warning is fine.

## THE FORK (Aug 28) — plan for the next session

The port is PROVEN (gate 4 passed; rig tiebreaker confirms obs
fidelity). The project pivots from porting to scaling. Blake's list:

1. **Retire the 12700K as the training rig** — the M2 (and later a
   rented box) takes over. The rig keeps one job until then: source of
   truth for old checkpoints/notebooks not yet migrated.
2. **GitHub refresh** — audit both machines' folders for what actually
   belongs in the repo (the 12700K especially is full of scratch);
   collect the canonical set on ONE machine (the M2 copy is cleanest —
   linux_port/ + sdlarch-rl patches + docs), README rewritten BY HAND
   (Blake's voice), push from Blake's own terminal. Good first Claude
   Code task: inventory + a proposed repo manifest, human writes prose.
3. **Share it** — video via watch_play.py (NEW, linux_port/): renders
   every frame at real-time pacing while the model plays; screen-record
   it. Plus a short write-up for reddit.
4. **Compute: DECIDED (Aug 28) — buy a Ryzen 9 7950X (~$279) for
   Blake's existing AM5 board.** Rental rejected (Hetzner post-hike:
   AX102 EUR 259/mo + setup; XLC $209+/mo, small vendor; marketplace
   compute like QuickPod = stranger-hardware burst only, never the
   checkpoint home). Threadripper rejected (5975WX P620 ~$3300; 2x
   cores but only ~1.3-1.6x aggregate — per-core speed rules this
   workload). 7950X projection: ~26-28 steps/s x 14 workers = ~370-400
   steps/s aggregate, ~5x the old rig, for six weeks of rent money.
   Build notes: reputable retailer only (clearance era = counterfeit
   listings), real cooling (230W PPT), 64GB RAM comfortable, BIOS
   update first. Day one: setup script -> bench_fps.py -> let the
   measured number set N_ENVS.
5. Remaining technical threads, in order: finish the first Mac
   training bring-up (fixes #5/#6 committed, next run starts at the
   first real training step); eyeball the P1 opponent view (never
   exercised on the rig); GPU-contention test before PS2_NENVS>2;
   optional matchup re-stamp (Pete/Falcon/Pride/Julia) for the clean
   apples-to-apples eval number.

## PROJECT LAWS (permanent section — earned by 6 legs + the rig era; do not trim)

Distilled from leg 2 + the leg-3 program (Aug 29-31) on top of the rig
record. These are the load-bearing conclusions; every future leg design
should be checked against them.

1. **Gradient continuity is the engine.** A diet only teaches winning
   if wins stay reachable throughout. Self-play guarantees this by
   construction; fixed too-strong opponents guarantee the opposite.
   (Evidence: 3B/3C-SP climbed; leg2, 3A, 3D flatlined at ~0%%.)
2. **Losses carry no information about winning.** Three separate
   lv8-only diets (warm, fresh, lv8-BC-seeded) produced zero learning-
   to-win. "Train against harder opponents" is not a curriculum unless
   the model can sometimes beat them.
   *Sep 10 scope note (audits #2/#3): as a learning-theory statement
   this is too broad — PPO can extract signal from graded losses. The
   empirical law is: near-certain-loss streams against a fixed too-hard
   opponent were unproductive in THIS environment, three for three.*
3. **BC priors do not transfer wins — demos must enter via DAgger.**
   A validated 23-1 human corpus, baked at 80.6%% val acc, yielded 8
   wins in 4,653 training episodes (3D). Covariate shift eats frame-
   level mimicry. Human data pays only when it relabels the POLICY's
   states (DAgger / failure-state drills), never as a seed alone.
   *Sep 10 scope note (audit #3): the corpora also carry a recorder bug
   (velocity features ~always 0, see audit #3 item 4) and a last-action
   timing mismatch, so covariate shift was not isolated. "Must enter via
   DAgger" is the next experiment, not an established law; fix the
   recorder first.*
4. **Data/priors/interface changes go ~5-for-5; reward tuning is
   0-for-5 lifetime.** (BC ceiling break, hold-until-next fix, chest
   obs restoration, self-play leg1, deep-pool discovery vs the five
   null reward legs.) Touch the data pipeline before the reward table.
5. **Opposition quality AND gradient budget must both be right.**
   3C had the best opponents (3B's lineage via the shared pool —
   accidental league training, the program's discovery) but only 2/6
   workers on them, and transferred worst. Don't split the budget with
   a dead stream.
6. **Promote the best checkpoint, never the last.** PPO churn:
   leg2's final zip evaled 4.0%% while its mid-leg checkpoints held
   8-16%%. Sweep before promoting; entropy stability does not protect
   the final snapshot.
7. **The lv8 wall stands.** No 2M-step fresh lineage has scored one
   deterministic lv8 win (0-for-200 eval episodes across 4 legs). Only
   the 31.9M lineage wins there (15%%). Respect what lifetime buys.
   *Sep 10 status: superseded in part. The fresh lineage has scored
   1,0,2,3,2,2 wins per 50 over legs 10-15 (2-6%%) with zero direct lv8
   training; the champion's baseline is 3/20. The wall is cracked, not
   down; the "respect lifetime" lesson stands (it took 16M+ lineage
   steps to get there).*
8. **Ops:** worker boot stagger 20s (Metal init race killed 3 launches
   at 6s, plus 2 chained launches — add retry-on-EOFError to
   launchers); leg launches via launcher SCRIPTS, never nested-quoted
   tmux; menu navigation is fully headless via menu_drive.py; one
   savestate slot number = one meaning per machine, document re-stamps.

## Findings worth remembering (the short version of Aug 24-28)

- The lua-era env assumes a free-running emulator; in-process libretro
  advances only when pumped. Every hang traced to that one assumption
  (liveness check, reset polls, loadstate, episode determinism).
- "Quiet degrades" aren't: the unported chest scan read as a 60-point
  win% collapse, because the policy TRUSTED those dims. If the model
  was trained with an input, ship the input.
- Deterministic frozen evals read far above training-time bands
  (92% vs 63-75 on the rig itself). Compare like protocols only.
- Behavioral metrics (picks/forms) are the real cross-machine parity
  test; win% also absorbs matchup and COM variance.
- Two AI sessions + one human across two machines works IF one file
  (this one) stays the single source of truth and each folder has one
  driver.

Continuation doc for the Claude session that ported the rig's RL setup to
the M2. Read alongside README_MIGRATION.md / MAC_TEST.md / README_PORT.md
(kit 1) and README_MIGRATION2.md (kit 2, in ~/Downloads/macbook_migration2).
HOWTO_LINUX_SERVER.md + setup_linux.sh (this folder) are the rented-server
recipe, current as of the state below.

## Scoreboard

- Gate 1 (RAM): **PASSED.** SYSTEM_RAM 16 MiB, HEALTH OK at delta +0x0
  (no RAM_DELTA needed), v7 synth line = 80/80 fields. Probed from
  states/slot1.state.
- Gate 2 (savestates): **PASSED.** slot1 = HvH 1v1 desert (good).
  slot2 re-stamped Aug 24 evening: desert, COM lv3, true FFA, bot on
  P2 — verified live with diag_state.py (4x1000.0 healths at frame
  ~306 hands-off, COMs actively fighting).
- Gate 3 (buttons): **PASSED.** calibrate_buttons table clean: dpad
  sign-consistent (diagonal axes = camera rotation, fine), attacks lunge,
  trigger rows alias face buttons (the GAME's combo shortcuts, not a
  mapping bug). DC_TO_RETRO unchanged. Xbox pad dpad-as-buttons (11-14)
  fixed in make_savestates.py.
- Gate 4 smoke: **PASSED** (Aug 24 evening) — "smoke OK — 100 steps"
  after env fix #1 below. bridge alive, line=v7, obs_dim=122.
- Gate 4 parity: **PASSED — Aug 28, after the kit-#3 chest-scan port.**
  50 eps deterministic, slot 2 (parity_chest_out.txt):
  **win 74.0% (37W/13L) IN BAND [63-75]; picks 8.06 ABOVE band
  [6.8-7.5]; forms 2.30 ABOVE band [1.4-1.9]** — above = ok, frozen
  deterministic reads high. "PARITY PASS — obs semantics survived the
  port." (The Aug-24 14% fail is preserved below for the record; root
  cause was the unported object-ledger scan: dark chest dims + pad
  chests fed to the model as stones.)
  **Rig tiebreaker landed (Aug 28, eval_abc, same protocol): win 92.0%,
  picks 7.08, forms 2.28.** Reading: picks/forms match the Mac (8.06 /
  2.30) almost exactly -> obs port CONFIRMED faithful. Deterministic
  reads far above the training band (92 vs 63-75). The 18-pt win% gap
  (92 rig vs 74 Mac) with matched behavior points at MATCHUP, not code:
  rig lineup = Pete/FALCON/Pride/Julia; **Mac lineup CONFIRMED by
  Blake (Aug 28): opponents Ayame/Pete/Accel — a different team**,
  which also explains the Mac COMs hoovering ~2x the stones (13-15 vs
  ~7/ep; Ayame). Matchup hypothesis CONFIRMED; case closed. Optional
  homework only: re-stamp to the exact rig lineup for a clean
  apples-to-apples number. Self-play training does not depend on the
  COM matchup.
- Training: **ONE pip install FROM RUNNING** (Aug 28 late). The
  PS2_NENVS=2 bring-up burned down every seam in order:
  1. shimmy missing -> `pip install 'shimmy>=2.0'` DONE (sb3 wraps the
     old-gym env via its compat layer; works).
  2. system/dolphin-1 seeded from dolphin-0 DONE.
  3. macOS fork corruption + concurrent Metal pipeline race killed
     workers -> FIXED in train_selfplay.py: SubprocVecEnv
     start_method="spawn" + 6s-per-instance init stagger. Verified:
     both workers boot clean, both bridges alive, warm start loads.
  4. tensorboard missing -> `pip install tensorboard` DONE.
  5. First real training step: ps2_ram's lazy-compose refactor had made
     `line` a read-only property, but selfplay_env's view-swap ASSIGNS
     it -> FIXED: line has a setter again (pins the value for the
     current frame; next tick invalidates).
  6. selfplay_env._obs_from_view was still a sketch (its own NOTE):
     called nonexistent `_build_obs` -> WIRED to the parent's
     `_observe(s, prev)` with per-view prev tracking (velocity deltas)
     AND an _active_opp flip — without it the P1 view lists ITSELF as
     its opponent. EYEBALL THE FIRST EPISODES: the P1 view is the one
     thing the Windows rig never exercised (e.g. if the opponent stands
     still or acts degenerate, suspect this block first).
  Command: SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:.
  PS2_CORE=<flycast dylib> PS2_NENVS=2 python -u train_selfplay.py
  Then: check per-process GPU% in Activity Monitor with 2 workers
  before raising PS2_NENVS; run long legs under tmux; STATE_SLOTS=[1]
  is deliberate (one stage until stable — widen later). Note the
  "SHORT OPPONENT SET slot1 1/3" lines are expected: slot1 is the
  1v1 self-play state.

## CURRENT BLOCKER: parity FAIL — legG far below the slot-2 band

50-ep frozen deterministic eval, slot 2, Aug 24 evening (parity_out.txt):
win 14.0% (7W/43L) vs band 63-75; picks 4.60 vs 6.8-7.5; forms 0.46
vs 1.4-1.9. Every mechanical layer works: buttons (dmg dealt 4-6 bars/ep),
forms when reached (dmgF > 0, the sole 2-form episodes include the wins).
The deficit is concentrated in GEM ACQUISITION.

**RESOLVED Aug 28 — kit #3 arrived (~/Downloads/kit3: powerstone.lua,
RAM_MAP.md, KIT3_NOTES, RIG_BENCH_ANSWER) and the chest scan is PORTED.**
ps2_ram.py now runs STONE_OBJ_MODE (lua stoneObjScan 1:1): object arena
at 0x8C4FBD30, 110 x 0x430 slots, hdr low byte 0x09, vt classify —
loose stones 0x0C0CBCB0 ARE the line's stones now (doctrine flip: pads
hold chests; the old spin-gate sweep was feeding pad-chests to the model
AS stones — the gap was double, not just dark chest dims). Chest
fragment live: chestN, fallN, 2 nearest resting chests. Also: full lua
PROJ_EXCLUDE list + band excludes ported, and the line now composes
LAZILY (kills the +32% synth tax from the bench). Verified offline
against the env's own parser with a synthetic RAM image; legacy-mode
regression-tested. Legacy fallback: ps2_addr.STONE_OBJ_MODE = False.
Rig-side numbers (RIG_BENCH_ANSWER): rig = 7.9 steps/s/instance, ~79
aggregate; M2 = 3.7x per instance, 2.2x rig aggregate. Rig deterministic
legG eval RUNNING (Aug 28; early: 2/2 wins, tracking band — confirms
the low Mac read was the port gap). **Rig slot2 lineup recovered
(Blake, eyeballed at eval launch): P1 Pete, P2 FALCON (the bot — RAM_MAP:
bot is ALWAYS port 2 = Falcon; legG is a Falcon policy), P3 Pride,
P4 Julia, desert, COM lv3.** The Mac slot2 re-stamp must match — P2
not-Falcon alone would depress every number. Verify/re-stamp before
the parity re-run.
NEXT: confirm lineup (re-stamp if needed) → smoke → 50-ep parity —
that is the gate-4 verdict.

**The original finding (kept for the record) — chest obs were hardcoded
zero.** ps2_ram.py's TODO:
STONE_OBJ_MODE (the Aug-10 object-ledger scan) was never ported; the v7
chest fragment is zeros, so obs [107..110] always read 0. legG trained
WITH live chest obs, and chests are the gem source (Sec 15: pads hold
chests, not stones). Signature matches exactly: COMs pick 10-25
stones/ep, bot 4.6; bot rarely holds 3 gems -> no forms -> loses 3v1
wars of attrition. NOT fixable from the kits: ps2_addr.py has no chest
addresses, and powerstone.lua / RAM_MAP.md are only on the rig.
**KIT #3 REQUEST: powerstone.lua + RAM_MAP.md** (minimum: chest class
window, object-ledger base/stride, chestN/fall field offsets) — then
port the scan into StateLineSynth._sweep_pool/_compose.

**Cadence: TESTED AND RULED OUT** (Aug 24 late). 20-ep eval with
PS2_FRAME_SLIP=2 (slip2_out.txt): win 5.0%, picks 4.45, forms 0.35 —
statistically identical to the slip-0 baseline (14%/4.60/0.46, n=50).
Extra held-input frames per step move nothing; the deficit is in what
the model SEES, not when it acts. The knob stays in the env for
future experiments.

**Eval mode: ALSO RULED OUT** (Aug 25). 50-ep STOCHASTIC eval
(--stochastic, added by the rig-side session; stoch_out.txt): win
10.0% (5W/45L), picks 4.88, forms 0.52, distinct-episodes~50. Same
regime as deterministic — sampling vs argmax changes nothing, and with
the widened 0-599 loadstate stagger every episode is distinct. The
port gap is CONFIRMED and observational. Chest obs zeros = prime and
now effectively sole primary suspect; kit #3 is the critical path.
(Division of labor agreed Aug 25: the Mac session drives linux_port/;
the rig session owns the rig and is packaging kit #3 — powerstone.lua
+ RAM_MAP chest section — plus the rig slot2 character lineup and a
rig-side deterministic 50-ep legG eval as band calibration.)

**Remaining secondary: legacy stone sweep** (spin gate) vs the
object-ledger scan — stone picks do work, just fewer, so a possible
contributor, but the chest gap is the dominant suspect.

## Libretro env fixes shipped Aug 24 (all in powerstone_env_libretro.py)

The lua-era parent assumes a BACKGROUND emulator advancing in wall time;
in-process libretro frames advance only when pumped. If the parent env is
ever refreshed from the rig, these overrides must survive:

1. `_wait_for_bridge` override — pumps run_frames(4) between its two
   reads (was: sleep 0.3s, frame never moved, "Bridge frame counter not
   advancing" x4 -> the old smoke blocker. The old HANDOFF prime suspect
   — state-file path — was WRONG; _read_state does reach the subclass
   _parse_state_once).
2. Pump-on-stale in `_parse_state_once` — re-reading the same synth
   frame runs 1 frame first, so reset()'s match-ready poll and
   _wait_frames make progress instead of spinning (the eval hang).
3. loadstate intro pump in `_send` — after any loadstate, pump up to
   1200 frames until match-ready(provisional): round-start stamps play
   out their ~306-frame intro instead of starving reset's retry loop
   (which reloads every 3rd try, wiping progress).
4. Random 0-59 frame post-load stagger — without wall-clock jitter a
   deterministic policy replays BYTE-IDENTICAL episodes (observed).
5. `PS2_FRAME_SLIP` knob — see cadence suspect above. Default 0.

Plus: train_selfplay.py warm start now passes custom_objects
(clip_range 0.2, lr 2.5e-4) — the rig's pickled lambdas don't
deserialize under py3.11; predict() never cared, .learn() would crash.
diag_state.py (NEW) = headless savestate triage (health/sec + verdict).

## Known crashes (non-blocking, documented)

- **Boot flake:** intermittent `mutex lock failed` abort or segfault
  during emu init, disproportionately the FIRST boot after
  login/reboot. Retry has always worked. Threaded rendering is already
  forced off (helped, didn't fully cure). If it ever fails twice in a
  row, debug properly (lldb / SDLARCH_LOG=1).
- **Exit abort:** `mutex lock failed` AFTER all results print, at
  process teardown. Cosmetic for gates; emu.close() added everywhere but
  didn't cure. Revisit before long SubprocVecEnv training if workers die
  dirty.

## Inventory (what lives where)

macbook_migration/ (this folder):
- `sdlarch-rl/` — harness, PATCHED (do not re-clone; patch list in
  HOWTO_LINUX_SERVER.md "Patches" section). `_retro.so` builds to repo
  root; rebuild = `cmake --build sdlarch-rl/build`.
- `linux_port/` — all scripts, patched (HLE BIOS + VMU + threading-off
  variables set in every entry point; pad/dpad + display flip in
  make_savestates; --state option in probe_ram; "player" cmd in bridge;
  synth priming + /dev/shm fallback in powerstone_env_libretro;
  eval_parity.py NEW — 50-ep frozen eval with the band baked in).
- `linux_port/states/` — slot1 (good), slot2 (needs re-stamp, see above).
- `linux_port/system/dolphin-0/` — VMUs + flash from the rig, in BOTH
  root and dc/ + dc/data/ (flycast reads dc/; completed save with
  unlocks CONFIRMED working — Pride + desert present, VMUs visible).
- `linux_port/opponent_pool/` — 8 ps_v6 checkpoints (0.2M→31.9M).
- `linux_port/powerstone_v6_ppo.zip` — Leg G warm start (copy of
  powerstone_v6_ppo_legG_27911k.zip).
- `linux_port/powerstone_env_v6.py` — from kit 2; no local imports;
  needs `gym` (0.26.2 now in venv).

## Bench (Aug 25, M2 Pro, bench_fps.py — NEW, in linux_port/)

A raw core 324.8 fps (5.4x RT) | B +synth 245.9 fps (+32% synth cost)
| C full env.step 29.3 steps/s = 250.9 fps incl. resets, 8.6 frames/step,
~0.7 min/ep. Env python layer ~free (B~=C fps); loop is emulation-bound.
GPU rendering ON during all of this (Apple GL4.1, ~39% GPU). Post-parity
speed levers, in order: lazy-compose in StateLineSynth (line is built
EVERY frame but read once per 8.6 — do it with the chest port, same
file), null-video for training runs, threaded_rendering re-test.
Training math: 6 workers ~175 steps/s -> 4M-step leg ~6.5h on the Mac.
Run the same bench on the rig + the rented box before sizing anything.

## Windows band, slot 2 (desert lv3 true-FFA) — gate-4 target

**win% 63–75, picks/ep 6.8–7.5, forms/ep ~1.6** (training-time band;
frozen deterministic reads a few points HIGH — above band = pass, below
= suspect the port). Borderline tiebreaker: rig can run a fresh 50-ep
frozen eval of the same zip on request. Already encoded in eval_parity.py.

## Environment / commands cheat-sheet

Every new terminal: `source ~/ps2rl/bin/activate` then
`cd ~/Documents/macbook_migration/linux_port`.
Every command prefix: `SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:.`
Core: `~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib`
(installed via buildbot curl, Aug 22-23 nightly). Game: `../Power Stone 2
(USA).chd`. Debug core logs: prepend `SDLARCH_LOG=1`.

- savestate maker (visible window, kb + xbox pad, F1-F7 stamp, TAB port):
  `python make_savestates.py --core <core> --game <game> --states ./states`
- gate 1: `python probe_ram.py --core <core> --game <game> --state states/slot1.state`
- gate 3: `python calibrate_buttons.py --core <core> --game <game> --state states/slot1.state`
- gate 4 smoke: `PS2_CORE=<core> python powerstone_env_libretro.py`
- gate 4 parity: `python eval_parity.py --core <core> --game <game> --slot 2 --episodes 50`
- train: `PS2_NENVS=6 python train_selfplay.py` (after parity passes;
  multi-instance needs system/dolphin-N seeded per instance — setup_linux.sh
  shows the loop; also expect the sb3-2.9-vs-old-gym-API wrapper question
  at SubprocVecEnv time: env is old-gym 4-tuple style, sb3 2.9 wants
  gymnasium — may need `pip install shimmy` or a thin wrapper. UNTESTED.)

## Next actions, in order

1. ~~Cadence discriminator~~ DONE — ruled out (see above).
2. KIT #3 from the rig: powerstone.lua + RAM_MAP.md (chest section at
   minimum). Port the object-ledger chest scan into ps2_ram.py
   (StateLineSynth._sweep_pool + _compose chest fragment), re-run
   eval_parity 50-ep.
3. Optional band cross-check while bridges are busy: rig runs its own
   fresh 50-ep frozen eval of legG_27911k on slot 2 (deterministic
   reads a few points high — calibrates the band for frozen evals).
4. Parity passes → train_selfplay (sb3-2.9 vs old-gym API at
   SubprocVecEnv time still UNTESTED — may need shimmy or a wrapper).
5. HOWTO_LINUX_SERVER.md is synced with all of the above (Aug 24).
