# Power Stone 2 RL — Session Handoff (rewritten Sep 14 2026, 09:15 PDT, M4 Pro era)

Canonical lab notebook: `HANDOFF.md` at the project root (PROJECT LAWS, the LEAGUE
LEGS table, pre-registrations, every finding with numbers). Trust it over this
file. This document is the *operator's* handoff: what is live, how the relay
runs on this machine, the exact per-leg procedure, and the open decisions.
It is written so a smaller model can run the relay without re-deriving anything.

## 1. Where things are

- Project: `/Users/Apple/Downloads/macbook_migration` (symlink `~/Documents/macbook_migration`).
  Scripts in `linux_port/`. Machine: M4 Pro, 10 P-cores, 48 GB. Clock: US/Eastern since Sep 15 (Pacific before).
- The Claude session's shell runs DIRECTLY on this Mac (no VM, no file bridge).
- Venv: `~/ps2rl` (Python 3.11). Every command: `cd linux_port && source ~/ps2rl/bin/activate`
  then `export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. PYTHONUNBUFFERED=1`.
  For anything in the FFA lineage (obs v2, four seats) use
  `PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:.` and `PS2_OBS_V2=1`.
- Two harness binaries: `sdlarch-rl/_retro.so` (2 controller ports, the proven
  one) and `sdlarch-rl/p4/_retro.so` (4 ports, built Sep 13, parity-checked).
  NEVER rebuild into the repo root: `cmake --build sdlarch-rl/build_p4` with
  `-DSDLARCH_COPY_TO_ROOT=OFF` is the only sanctioned build.
- Unattended permission allowlist: `.claude/settings.local.json` (git-ignored).
  Scheduled tasks run without prompts because of it.

## 2. Live state (Sep 24 5:05 pm EDT; leg 77 live, launched 4:57 pm; leg 76 = 22.6 / 98.0 / 81-19; lv8 SIGNAL after three drops, discriminators proposed; trainer = mixed)

- **Standing override changed 16:00 EDT Sep 19 (Blake: "Stack")**: `league_optim.txt` =
  `PS2_LR=1e-4 PS2_TARGET_KL=0.03 PS2_BATCH_SIZE=256`, applies from leg 52 (leg 51 unchanged). Read over two legs vs the
  legs 46-50 band (lv8 15-19); revert to lr + kl only if lv8 < 15 twice.
- **Leg 71 training** (launched 12:35 pm EDT Sep 23, done ~5:00 pm), state `71 ./powerstone_v6_leg70_league.zip`
  (854-input, strided lags 16,8,4,3,2,1,0), `league_env.txt` carries `PS2_OBS_STACK=7`, wake `ps2-leg71-end-wake`
  (5:50 pm EDT). Leg 70 (first strided) = lv8 28.8 ALL-TIME RECORD / lv3 97.6 / AB 74-26. K=4 legs 68-69 = 18.2 / 23.0.
  References from here: lv8 record 28.8, band now 20-30; lv3 92-98; AB 63-78.
  Every zip from leg 70 on is 854-input; evaluators detect it. Revert: state -> powerstone_v6_leg69_league.zip
  (488) with PS2_OBS_STACK=4.
  Every zip from leg 68 on is 488-input; evaluators detect it. Revert: state -> powerstone_v6_leg67_league.zip
  and remove PS2_OBS_STACK from league_env.txt.
  Blake prefers 12-hour times with am/pm in reports. STANDING RECIPE (all passed their reads): mixed + stack (lr 1e-4,
  kl 0.03, batch 256) + zero-sum + start health 0.5-1.0 + COM character random (slots 0,10-22).
  Leg 59 = lv8 23.8 (all-time record) / 95.2 / 74-26. References: lv8 16-24, lv3 92-98, AB 65-78, stones ~4.8.
  No watch active. Next lever queued: COM level randomization (stamp level-5/8 state sets; HANDOFF leg 59 note). STANDING RECIPE: mixed + stack
  (lr 1e-4, kl 0.03, batch 256) + arena (zero-sum, start health 0.5-1.0) + COM character random (slots 0,10-22).
  Leg 57 (arena, no char random) = 16.2 / 92.4 / 65-35 (one-leg dip from leg 56's 22.4 / 97.6 / 78). Arena read PASSED: leg 55 = 19.2 / 95.2 / 69, leg 56 = 22.4 / 97.6 / 78
  (all-time records on lv8 and lv3). References for the next legs: lv8 19-22, lv3 95-98, AB 69-78, stones/ep ~4.8.
- **CHARACTER RANDOMIZATION enabled for leg 58+** (22:45 EDT): `league_env.txt` now also carries
  `PS2_STATE_SLOTS=0,10,...,22` (COM seat character sampled per episode; `states_mixed/README.md`). Leg 58's
  [config] shows `state_slots=[0, 10, ..., 22]`; [ep] lines carry `slotNN`. Read over legs 58-59 vs 55-56.
- **ARENA FLAGS ENABLED for leg 55+** (08:30 EDT, Blake): `league_env.txt` = `PS2_ZERO_SUM=1 PS2_START_HEALTH=0.5,1.0`.
  Leg 55's trainer log must show "[config] zero_sum=1" and "[config] start_health=U(0.5, 1.0)" plus per-episode
  "[zs]" and "[start]" lines; leg_modes.txt row 55 has five columns. Read over legs 55-56 (HANDOFF "ARENA LEVERS
  BUILT"). Revert: `: > league_env.txt` before a launch. Stack legs 52-53 = lv8 20.6 /
  16.6, lv3 94.0 / 94.8, AB 53 / 60: STACK READ VERDICT neutral (HANDOFF leg 53 note). Awaiting Blake: keep the
  stack or `echo "PS2_LR=1e-4 PS2_TARGET_KL=0.03" > league_optim.txt` to revert (applies at the next launch);
  either way the next lever is the arena work (zero-sum reward, start randomization), not the optimizer. Lineage legs 46-51 (lr + kl only): lv8
  16.8 / 18.6 / 15.8 / 18.8 / 15.0 / 16.4 (plateau, mean 16.9); lv3 92.8-96.4; AB 65-74. No watch active.
- Lineage (since leg 46): mixed recipe, restarted from `powerstone_v6_sweep40_kl01_league.zip`
  (19.0 / 92.8 / 71-29), standing override `league_optim.txt` =
  `PS2_LR=1e-4 PS2_TARGET_KL=0.03` (set 20:20 EDT; leg 46 itself ran with the kl01 zip's BAKED-IN target_kl 0.1,
  see HANDOFF "ZIPS PERSIST target_kl"; from leg 47 both lines print as "[config] ... override"), `league_trainer.txt` = mixed, state
  advances each leg. Each battery chains the next leg with the same overrides.
- Pools: `pool_league` = clone of `pool_sweep40_kl01` (fresh); `pool_league_kl_drift_41_45/` = the abandoned
  target_kl 0.1 lineage (legs 41-45, AB 71 -> 26); `pool_league_pre41_leg40/` = pre-sweep league pool. Keep all.
- Lesson recorded: target_kl 0.1 = one-leg jump then five legs of drift (KL/update 0.02 -> 0.05). Not a standing setting.
- Restart procedure (used 16:03 EDT Sep 18; keep for reference), machine quiet:
  `mv pool_league pool_league_kl_drift_41_45 && cp -Rc pool_sweep40_kl01 pool_league &&
  echo "46 ./powerstone_v6_sweep40_kl01_league.zip" > league_state.txt && echo PS2_LR=1e-4 > league_optim.txt &&
  echo mixed > league_trainer.txt && tmux new -s ps2train -d "caffeinate -is bash $(pwd)/league_leg_async.sh"`.
  Then verify `[config] learning_rate override -> 0.0001` in train_leg46_out.txt and 10 workers.
- Lineage settings (since leg 41): mixed recipe, warm start lineage from
  `powerstone_v6_sweep40_kl01_league.zip` (sweep winner, Blake's pick), ent_coef 0.01, standing
  override `league_optim.txt` = `PS2_TARGET_KL=0.1` (exported by league_leg_async.sh every leg; the
  trainer prints "[config] target_kl override -> 0.1"; leg_modes.txt col 4). `league_trainer.txt` = mixed;
  each battery chains the next leg with the same override.
- **New eval contract from leg 41** (both env fixes live: reload on every reset; live stagger 0-239,
  `PS2_STAGGER_FRAMES`, 600 = old). References: champion lv8 5.8 / lv3 92.0; parent kl01 lv8 19.0.
  Old-contract numbers (legs 1-40, the sweep table) are NOT directly comparable; HANDOFF "PRE-ROLL FIX".
- Pools: `pool_league` = kl01 arm pool (league pool + kl01 snapshots); `pool_league_pre41_leg40/` =
  the pre-sweep league pool (keep); `pool_sweep40_<arm>/` = the other arms (keep until Blake says).
- Hold rule (Blake): slot2 < 70, champion AB < 35/100, or lv8 < 4.0 -> `echo hold > league_trainer.txt`.
  Since Sep 23 the battery enforces this itself via `hold_gate.py` (marker `claude_bridge/hold_leg<N>.txt`);
  the collector still reads the receipts and confirms. The battery also takes `claude_bridge/battery_leg<N>.lock`
  (a dir; after a FAILED marker, `rmdir` it before any rerun) and verifies the pool copy before advancing state.
  Leg 72+ recipe adds `PS2_OBS_CTX_FIX=1 PS2_ZS_TIME=1` in `league_env.txt` (HANDOFF "ASTRA REVIEW FIXES");
  `test_obs_context.py` (no emulator) must print 0 failures after any observation-builder edit.
- Sweep 40 (HANDOFF "SWEEP 40 RESULTS"): ctrl 6.2 / bs256 9.0 / lr1e4 13.6 / kl01 16.6 on lv8.
  Open follow-up: stack lr 1e-4 + batch 256 (one arm). ent_coef 0.03 proposal withdrawn.

## 3. Relay modes and scripts

`linux_port/league_trainer.txt` holds ONE word and is read by `league_battery.sh`
AT LAUNCH TIME (fixed Sep 14) and by `league_leg_async.sh` at its start:
- `ffa`  -> `league_leg_async.sh` with `PS2_ENV=ffa PS2_OBS_V2=1 PS2_STATE_SLOT=0
  PS2_POOL_SAMPLING=uniform`, p4 harness, `PS2_PULL_EVERY=64`. (Current.)
- `async` -> the 2-seat actor-learner trainer on slot 1 (obs v1). The validated
  fast recipe for the pure league (2.4x lockstep).
- `lockstep` -> the original `league_leg.sh` / `train_selfplay.py` (hangs at exit).
- `mixed` -> like `ffa` but `PS2_FFA_SEATS=0,2 PS2_STATES_DIR=./states_mixed`: pool
  policies in seats P1+P3, the game's COM (level 3) in P4. (Leg 34 test, Sep 15.)
- `hold` -> the battery runs and advances state but launches nothing; writes
  `claude_bridge/leg<N>_LAUNCH_HELD.txt`. Use it whenever a decision is pending.

Per-leg files: `train_leg<N>_out.txt` (moved to `receipts/` by the battery),
`powerstone_v6_leg<N>_league.zip`, pool snapshots `pool_league/leg<N>_league_*_steps.zip`
every 500k, `pool_league/prog_leg<N>.zip` (the final, copied by the battery),
`wrapper_league.log` (launch/complete lines; `[wrapper-async]` for async/ffa legs).

Each leg's mode is appended to `leg_modes.txt` at launch ("34 mixed"); the battery
reads THAT for the eval contract (obs v2 + p4 harness for ffa/mixed legs), so
holds never change how a finished leg is evaluated.
Battery (`league_battery.sh`, Sep 13 parallel version): 10 shards per eval on
instances 0-9 -> `receipts/shards/`, merged by `merge_receipts.py` into
`receipts/eval_leg<N>_slot3_out.txt` (lv8, 500 eps), `eval_leg<N>_slot2_out.txt`
(lv3, 250 eps), `eval_leg<N>_ab_vs_leg1_out.txt` (100 eps vs the champion). No
parent A/B any more. ~35-50 min. Since Sep 21 the battery also records two lv8 rounds of the
finished bot to `videos/leg<N>_lv8.mp4` (phone size, instance 11, ~3 min; `PS2_LEG_VIDEO=0`
disables) — attach it to the leg report; Blake watches every leg. It also starts `scout_leg.sh <N>` in tmux
`scout<N>` (records until one win + one loss on lv8, cap 14 rounds; 1-fps contact sheets for the first loss
and the first win in `videos/review_leg<N>/`, `videos/leg<N>_win.mp4`, marker `claude_bridge/scout_leg<N>_done.txt`).
At collection, whoever collects writes `videos/review_leg<N>.md` from `scout_rubric.md`: the interactive
session spawns a Sonnet agent (~110k tokens); a scheduled wake reads the sheets itself. Attach the win clip
and three review lines to the report. In `ffa` mode it evaluates under obs v2 on p4.
Markers in `claude_bridge/`: `battery_leg<N>_done.txt` / `_FAILED.txt`,
`leg<N+1>_LAUNCH_HELD.txt` / `_LAUNCH_FAILED.txt`.

## 4. The per-leg procedure (async and ffa legs)

1. Wait for `leg complete` in `train_leg<N>_out.txt`. The async trainer EXITS BY
   ITSELF (no teardown hang; the tmux session ends). Verify no trainer is alive:
   `pgrep -f 'train_selfplay_asyn[c]'` (the bracket avoids matching your own shell —
   a plain `pkill -f train_selfplay_async.py` kills the shell that runs it).
2. Launch the battery: `tmux new -s bat<N> -d "caffeinate -is bash league_battery.sh"`.
   Guard first: state file starts with `<N> `, no `bat<N>` session, no done marker.
   Compare process counts numerically (`[ "$n" -eq 0 ]`), never as strings.
3. ~50 min later collect the three receipts, confirm `league_state.txt` advanced and
   `pool_league/prog_leg<N>.zip` exists, confirm leg N+1 booted
   (`grep '\[config\]' train_leg<N+1>_out.txt` shows `env=ffa obs_v2=1
   pool_sampling=uniform n_actors=10 total_steps=4000000`; `pgrep -f 'spawn_mai[n]' | wc -l` = 10).
4. Training-stream quartiles from the `[ep]` lines (win share, timeouts, picks, forms)
   and the entropy trend from the `[stats]` lines; run
   `python validate_async_leg.py --async-log receipts/train_leg<N>_out.txt
   --lockstep-log receipts/train_leg24_out.txt --async-receipts <N> --stream-report-only`.
5. Add the row + a short note to HANDOFF.md's LEAGUE LEGS table (newest row on top,
   directly above the previous leg's row; format in the table). Report to Blake.
6. Create the next fallback wake (section 5). Mid-leg crash (trainer dead, no
   `leg complete`, >100 `[ep]` lines) = HALT and report, never relaunch.

Lockstep legs (only if `lockstep` mode is ever used again) hang after `leg
complete`: `kill -9` the `train_selfplay.py` PID, `pkill -9 -f 'spawn_mai[n]'`,
`tmux kill-session -t ps2train`, then the battery.

## 5. Two drivers, both unattended

- REPORTING CADENCE (Blake, Sep 20): report ONCE per leg, when the battery lands (table + three
  lines). No hourly entropy messages, no "leg complete, battery launched" interim notes unless
  something is wrong. Entropy is read from the [stats] lines at collection time and goes in the row.
- The interactive session keeps a persistent watcher (scratchpad `relay_watch.sh`)
  that reports LEG COMPLETE / BOOTED / markers / crashes. If you are a new session,
  recreate it: a loop that greps the current `train_leg*_out.txt` for
  `leg complete`, `[config]`, `Traceback|ACTOR DIED`, the `claude_bridge` markers,
  and `out of attempts` in the wrapper log, printing once per transition.
- Scheduled fallback wakes (mcp scheduled-tasks, one-time `fireAt`, never local cron):
  one per leg, fired ~5h15m after launch for FFA legs, with hard guards (state file
  still on this leg, no battery session/markers, no next-leg log) and NO kill
  commands. Each wake's collection task records the row and creates the next wake.
  Example prompts: `~/.claude/scheduled-tasks/ps2-leg29-end-wake/SKILL.md`.
  Current: see section 2.

## 6. What this session found and built (Sep 11-14), shortest form

- Bring-up on the M4: quarantine/rpath/SDL2 fixes (in `setup_m4.sh`); parity passed.
- Throughput: lockstep plateaus at ~120 steps/s from 10 workers up (sync vec env, not
  CPU/GPU); the async actor-learner trainer (`train_selfplay_async.py`) does ~275,
  validated twice by a pre-registered 4-layer harness (`validate_async_leg.py`);
  render tricks (resolution, frame skip) are dead ends. 10 workers, 4M-step legs.
- Both trainers early-stop after 1-1.4 epochs per update (target_kl=0.03 in the zip).
  Not a bug; a post-campaign hyperparameter question.
- Batteries: 500/250/100 sharded; the champion's 98 / 15% were small-n; honest is 91 / 5.
- obs v2 (`PS2_OBS_V2=1`): last-action = a_t for all seats; per-view counters (fixes
  the audit's form-timer leak). Held-out numbers unchanged by it.
- Four-seat FFA env (`ffa_selfplay_env.py`), 4-port harness (`sdlarch-rl/p4`), the
  four-human four-Falcon desert state `states/slot0.state` stamped headlessly (menu
  map in HANDOFF); savestates restore the controller table, so the state carries four
  controllers baked in; opt-in `PS2_RECONNECT_PORTS=1` hook in `flycast_bridge.py`.
- FFA legs 27-29: self-play stream degenerates (passivity, entropy collapse, timeouts);
  anti-stall (2,000-step cap + timeout = loss + uniform sampling) did not cure it;
  held-out lv8 rose 1.2 -> 4.4 -> 5.2 anyway; slot2 ~84 (leg 26: 94.8). Blake: continue.
- bash 3.2 + `set -u`: expanding an EMPTY array (`"${arr[@]}"`) aborts the whole script
  ("unbound variable"). Use `${arr[@]+"${arr[@]}"}`. This killed the first sweep launch
  (Sep 16 19:52) silently: tmux session gone, no trainer, nothing harmed.
- Ops lessons: scheduled wakes must fire AFTER a leg can finish and must never kill;
  the battery must read the launch mode at launch time (fixed); `pkill -f` with the
  target name in your own command kills your shell (use `[c]` brackets); leg 29 was
  mislaunched twice and corrected (both logged in `receipts/train_leg29_*aborted*`).

## 7. Open decisions (Blake's)

1. FFA arena design if held-out gains stall: two policy seats + one COM seat as an
   aggression source; `ent_coef` 0.03 for FFA legs; or park FFA and resume the pure
   league from the leg 26 zip (`echo async > league_trainer.txt`, state file to
   `<N> ./powerstone_v6_leg26_league.zip`).
2. The discriminator states (lv8 1v1, lv6 FFA) — stampable headlessly now with the
   menu map; still useful for attributing lv8 gains.
3. Post-campaign: target_kl/epochs, the pool's `recent_k`, promote-best-not-last (Law 6).
4. The M2 stays untouched (Blake). Public numbers must carry their n.

## 8. Key files

`linux_port/`: `train_selfplay_async.py` (actor-learner PPO; env switch `PS2_ENV`),
`ffa_selfplay_env.py`, `selfplay_env.py`, `powerstone_env_v6.py` (`OBS_V2` switch),
`flycast_bridge.py`, `league_leg_async.sh`, `league_leg.sh`, `league_battery.sh`,
`merge_receipts.py`, `check_receipt.py`, `eval_parity.py` (`--instance`),
`ab_selfplay_probe.py` (`--instance`), `validate_async_leg.py`, `menu_drive.py`
(p1-p4 steps), `rebaseline_obsv2.sh`, `sweep_leg27.sh`, `league_trainer.txt`,
`league_state.txt`, `states/slot0.state` (FFA4), `receipts/`, `pool_league/`.
`sdlarch-rl/p4/` (4-port harness), `sdlarch-rl/build_p4/`.

## 9. Watch it / play it (Sep 16)

Both need `PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:. PS2_OBS_V2=1 SDL_AUDIODRIVER=dummy`
(mixed-lineage eval contract) and an instance id nobody else uses (trainer = 0-9).
Never set SDL_VIDEODRIVER=dummy (kills the harness GL window); use `--hidden`.

    python -u watch_play.py --core "$CORE" --game "$GAME" --slot 3 --model ./powerstone_v6_leg<N>_league.zip \
        --episodes 3 --speed 0 --no-sound --hidden --instance 11 --record videos/leg<N>_vs_lv8.mp4
    python -u play_vs.py --core "$CORE" --game "$GAME" --mode 1v1 --model ./powerstone_v6_leg<N>_league.zip

`CORE="$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib"`, `GAME="../Power Stone 2 (USA).chd"`.
play_vs modes: 1v1 / ffa (you vs three policies) / mixed (you, bot, policy, lv3 COM).
Keys: arrows, Z jump, X grab, C attack, V throw, A/S = L/R, Enter start, P pause, Esc quit.

## 10. Arena flags (built Sep 20, off by default)

`linux_port/league_env.txt` holds one line of `VAR=VAL` pairs read by `league_leg_async.sh` at
each leg launch (column 5 of leg_modes.txt). Allowed: `PS2_ZERO_SUM=1` (learner reward = own
minus mean of the other seats, one consistent reward function, nearest-attacker damage
attribution) and `PS2_START_HEALTH=lo,hi` (per-seat random starting health written into the
player object in RAM at reset) and `PS2_STATE_SLOTS=0,10,...,22` (character randomization: the COM seat's
character sampled per episode from `states_mixed/slot10-22`; see `states_mixed/README.md`). Training-only:
batteries never see them. Enable:
`echo "PS2_ZERO_SUM=1 PS2_START_HEALTH=0.5,1.0" > league_env.txt`; disable: `: > league_env.txt`.
The trainer log shows "[config] zero_sum=1" / "[config] start_health=..." and per-episode
"[zs]" / "[start]" lines. Details and the pre-registered read: HANDOFF "ARENA LEVERS BUILT".

## 11. Frame stacking (built Sep 22; HANDOFF "FRAME STACKING BUILT")

A stacked policy has input 122*K. `PS2_OBS_STACK=K` in `league_env.txt` makes the trainer stack the
learner's frames; the warm zip MUST already be K-frame (make one with
`python surgery_stack.py <single_frame.zip> <out.zip> --k K`, then prove it with
`python equivalence_stack.py <single_frame.zip> <out.zip> --instance 13` -> PASS). Evaluators and the
self-play envs detect K from each model, so batteries, pool opponents and clips need no flags.
K=4 = contiguous [3,2,1,0]; K=6 = STRIDED [16,8,4,2,1,0]; K=7 = STRIDED [16,8,4,3,2,1,0] (1.6 s window with
every K=4 lag kept = exact surgery; Blake's strided choice as run from leg 70); K=8 = contiguous. Surgery between layouts: `python surgery_stack.py <src.zip> <out.zip> --k 6`, check with
`python agreement_stack.py <src.zip> <out.zip> --instance 13` (argmax agreement ~100%).
To revert: point `league_state.txt` at the last zip of the previous layout and set PS2_OBS_STACK to its K
(or drop it for single-frame).
