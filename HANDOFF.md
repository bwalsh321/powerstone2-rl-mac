# HANDOFF — Power Stone 2 RL, M2 MacBook port session (Aug 22–28, 2026)

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
4. **Compute: BUY, don't rent (decided Aug 28).** Hetzner's June-2026
   price adjustment killed the rental math: AX102 (16c 7950X3D) is now
   EUR 259/mo + EUR 129 setup; AX162 (48c EPYC) EUR 614/mo. A Ryzen 9
   9950X streets at ~$434-584 — one to two months of rent buys the
   chip outright for Blake's existing AM5 board. At ~25-30 steps/s x
   ~14 workers that's the ~350-420 steps/s aggregate tier, always on.
   Hourly cloud (no setup fee) remains the burst option only.
   HOWTO_LINUX_SERVER.md stays current either way — the recipe is the
   same for a home Linux box; run bench_fps.py before sizing N_ENVS.
5. Remaining technical threads, in order: finish the first Mac
   training bring-up (fixes #5/#6 committed, next run starts at the
   first real training step); eyeball the P1 opponent view (never
   exercised on the rig); GPU-contention test before PS2_NENVS>2;
   optional matchup re-stamp (Pete/Falcon/Pride/Julia) for the clean
   apples-to-apples eval number.

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
