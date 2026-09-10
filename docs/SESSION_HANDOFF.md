# Power Stone 2 RL — Session Handoff (written Sep 9, 2026, ~00:30Z; relay notes updated Sep 10)

> **Sep 10 update for relay wakes.** (1) `league_battery.sh` is now
> fail-safe: on the collection wake, check for
> `claude_bridge/battery_legN_done.txt` (success) OR
> `claude_bridge/battery_legN_FAILED.txt` (an eval receipt was incomplete
> after retry: state/pool untouched, next leg NOT launched — halt and
> report, do not hand-advance) OR `claude_bridge/legN+1_LAUNCH_FAILED.txt`
> (battery complete and state advanced but tmux launch failed: relaunch
> `league_leg.sh` in tmux `ps2train` after confirming no trainer is alive).
> (2) Eval receipts and finished train logs now live in
> `linux_port/receipts/`. (3) `league_leg.sh` must only be edited BETWEEN
> legs and by rename (bash reads it lazily while a leg runs). (4) Never
> queue `git push` on the bridge (keychain prompt blocks the watcher);
> Blake pushes. (5) Leg 16 is live as of Sep 9 20:39 EDT; leg 15 slot2 was
> 92 = 92 flat — Blake rules on whether that arms the trigger.

Canonical lab notebook: `HANDOFF.md` at the root of `~/Documents/macbook_migration` on Blake's M2 MacBook (same file in the `powerstone2-rl-mac` GitHub repo). This document is the *session* handoff: what this conversation was doing, how the automation works, and what's live right now. Anything that conflicts with HANDOFF.md — trust HANDOFF.md.

## 1. The project in one paragraph

RL agent for Power Stone 2 (Dreamcast) via Flycast/libretro headless on Blake's M2 MacBook. Observations = 122-dim vector read straight from emulator RAM (zero pixels), 10 discrete actions, PPO via stable-baselines3, 6 emulator workers. The training recipe that won a 4-leg controlled comparison is deep-league self-play: each 2M-step "leg" warm-starts from the previous leg's final model and trains against a growing pool (`linux_port/pool_league/`) of every checkpoint the project ever produced. A fully automated relay has been compounding legs since Sep 1.

## 2. Live state right now

- **Leg 14 is training** (launched Sep 8 22:42Z, tmux session `ps2train`, 6 workers confirmed). Legs take ~7-8h.
- **A scheduled relay wake exists**: trig_01UkRVGUwSq3CuZkbp42FhyM fires 06:15Z Sep 9 to handle leg 14's end. If forking kills that schedule, recreate it (protocol in section 5).
- `league_state.txt` reads `14 ./powerstone_v6_leg13_league.zip`.
- **Pre-registration trigger: DISARMED** as of leg 13 (slot2 went 88 → 90). One flat/down slot2 leg (≤90) re-arms it; two consecutive fire it.
- **Teardown hang is now expected behavior**: the trainer prints "leg complete", writes the final zip, then hangs forever with its 6 workers (macOS mutex bug). Every end-of-leg wake must `kill -9` the train_selfplay PID, `pkill -9 -f spawn_main`, and `tmux kill-session -t ps2train` BEFORE launching the battery — otherwise the battery's `tmux new -s ps2train` chain fails and CPU stays squatted. An `os._exit(0)` patch after the final save was proposed to Blake; NOT yet approved, do not apply unprompted.

## 3. Current verified numbers (through leg 13, Sep 8)

Baselines: leg1 champion (`powerstone_v6_ppo.zip`, 31.9M steps ≈ "32M") = slot2 98.0% (9.76 picks, 3.00 forms), slot3 (lv8) 15%. Blake's own play vs three lv8 COMs: 23-1.

| leg | lifetime | slot3 lv8 (n=50) | slot2 lv3 (n=50) | AB vs prev (n=12) | AB vs leg1 (n=12) |
|---|---|---|---|---|---|
| 11 | 18M | 0W (3.22/0.54) | 90.0 (10.42/3.12) | 8-4 | 9-3 |
| 12 | 20M | 2W (3.78/0.62) | 88.0 (10.60/3.20) | 10-2 | **11-1** |
| 13 | 22M | **3W** (3.62/0.62) | 90.0 (9.12/2.72) | 10-2 | **11-1** |

- Held-out slot2 curve: 40 / 42 / 50 / 64 / 78 / 82 / 84 / 86 / 90 / 88 / 90 (vs leg1's 98).
- Lv8 wins by leg: 1, 0, 2, 3 after nine legs of 0-for-450 — a climbing edge, zero lv8 training data. Predicted in advance by the picks/forms behavior climb.
- The honest large-sample head-to-head: crown probe n=50, leg6 (12M) vs leg1: **29-21**. The 11-1s are n=12 quick probes.
- Watch items: slot2 picks/forms softened at leg 13 (9.12/2.72, from 10.60/3.20) — flag if it repeats; soft-pool flag if training win% >92 sustained.

## 4. The command bridge (how Claude reaches the Mac)

Cowork's `device_bash` runs in an isolated Linux VM with the Mac folder mounted at `$HOME/mnt/macbook_migration/` — file reads/writes work, but Mac processes/tmux/emulators are invisible from there. To run things ON the Mac:

1. Write `linux_port/claude_bridge/cmd.sh` (through the mount) containing the commands + a unique `echo TAG_xxx` at the end.
2. A tmux watcher on the Mac (`claudebridge` session, running since Aug 31) executes it and writes stdout+exit code to `claude_bridge/out.txt`.
3. Poll `out.txt` for the TAG. **Never `rm` inside the VM mount** (blocked, "Operation not permitted"); completion detection is TAG tokens only. Long-running work goes in detached tmux sessions launched from cmd.sh (launcher scripts, never nested-quoted tmux commands).

If the Mac reboots, Blake restarts the watcher with: `cd ~/Documents/macbook_migration/linux_port && tmux new -s claudebridge -d "caffeinate -is bash claude_bridge_watcher.sh"`

## 5. The relay protocol (one cycle)

1. **Leg-end wake** (~7h15m after launch): check `train_legN_out.txt` for "leg complete"; kill the hung trainer tree + `ps2train` session (see section 2); launch `league_battery.sh` in detached tmux (`batN`). Mid-leg crash (eps>100 then death) = HALT and report, never blind-relaunch.
2. **Collection wake** (~2h15m later): battery writes `claude_bridge/battery_legN_done.txt`, four eval files (`receipts/eval_legN_slot3/slot2/ab_vs_prev/ab_vs_leg1_out.txt`), copies the final into the pool as `prog_legN.zip`, advances `league_state.txt`, and chains the next leg via `tmux new -s ps2train`. Verify leg N+1 booted (6 workers), update the HANDOFF.md LEAGUE LEGS table + note block, report the table to Blake, schedule the next wake via send_later.

## 6. Standing constraints (binding)

- **NEVER overwrite or promote `powerstone_v6_ppo.zip`** (the leg1 champion) without Blake's explicit go.
- The **pre-registered intervention plan in HANDOFF.md is binding**: no diet changes until the trigger fires (slot2 flat/down 2 consecutive legs OR slot3 behavior stall); response = eval discriminators FIRST (lv8-1v1 + lv6-FFA), then at most 1 worker on a ≥20%-winnable rung; report to Blake before executing any diet change.
- **Public-facing prose is Blake's voice** — Claude proofs and fact-checks, never ghostwrites the post. No em dashes in drafted text.
- The CHD/ROM is never committed to any repo. Savestates/VMU files are acceptable per community norm (gym-retro precedent); currently NO states are tracked in `powerstone2-rl-mac` and it's clean for public linking.
- Halt + report on mid-leg crashes; never blind-relaunch.

## 7. The hardware saga (Sep 4-8)

Blake bought an eBay 7950X ("New (other) / unable to test", condensation noted in listing, no-returns seller) for a fresh-Linux box with an Aorus B650. It arrived **internally shorted** — installing it played the whole system dead (standby blink-and-die, even with the socket empty) until a full AC drain reset the PSU protection. Board and RAM tested fine. Advised: file an eBay Not-As-Described claim (no-returns doesn't block the Money Back Guarantee). His fallback option, undecided: convert the old 12700K rig into a temp Linux box (expect ~M2-class throughput, but it retires the G4 parity risk). Meanwhile the relay resumed on the M2 (Sep 8, leg 13 onward).

The Linux bring-up kit is done and committed to `powerstone2-rl-mac`: `linux_port/setup_linux.sh` (deps, `~/ps2rl` venv with pinned versions — torch CPU, sb3 2.9.0, gymnasium 1.3.0, numpy 2.4.6 — flycast core from the libretro buildbot, gates G1-G2) and `linux_port/LINUX_BRINGUP.md` (rsync payload ~530MB: CHD, pool_league, states, demos*, model zips, league_state.txt; gates G3-G5 — **G4, the 50-ep slot2 parity run vs leg 12's Mac numbers, is mandatory before trusting any training**). `league_leg.sh`/`league_battery.sh` are platform-aware (core path, caffeinate, cd-to-script-dir).

## 8. Reddit post (in flight, Blake finishing TODAY-ish)

- Blake's draft covers: Pokemon Red RL origin → brothers/useless-4th-bot dream → year-long RAM wall → new-baby late nights → Windows-to-Mac scaling → level-5 wall → self-play breakthrough. Reference docs on the Mac: `REDDIT_POST_KIT.md` (verified numbers, arc, posting plan) and `REDDIT_POST_DRAFT.md`.
- **Link `powerstone2-rl-mac` only** (verified clean; old rig-era repo gets one line inside the README, not the post). README has two TODO blocks awaiting his intro/story paragraphs.
- Corrections he still needs to apply: stale stats (use 22M vs 32M, 11-1 n=12 twice, 29-21 n=50, curve ending 90, lv8 wins 1/0/2/3); the "waiting for a 7950X" line is now fiction (the DOA-chip detour is a better beat); the recipe sentence must make clear the low-level FFA is a held-out EVAL, not a 7th training instance; strengthen the AI-involvement disclosure (repo commits are co-authored — his earlier "I gave direction while AI agents drove the code, and I understand every result" line preempts the gotcha).
- Missing beats he planned: BC/covariate-shift heartbreaker (23-1 recordings → clone won 8 of 4,653), the external-audit disclosure (pool-sorting bug found, fixed, re-ran, curve held), the lv8 wall-crack ending, video, parenting closer.
- Posting plan: r/reinforcementlearning first (video at top), then r/MachineLearning [P], then r/emulation + r/Fighters + r/dreamcast. Claude does one final proof + stat pass when his back half is drafted.

## 9. Key files (all under `~/Documents/macbook_migration/`)

`HANDOFF.md` (canonical: PROJECT LAWS — 8, do not trim; LEAGUE LEGS table; pre-registered plan; migration section). `linux_port/`: `train_selfplay.py` (env knobs: PS2_CORE/GAME/POOL/WARM/FRESH/OUT/NENVS/STAGGER/TOTAL_STEPS), `selfplay_env.py` (mtime-sorted pool, PFSP-lite 50% recent-10/50% uniform), `powerstone_env_v6.py` (SLOT_META, LOSS_SCALE_BY_LEVEL), `league_leg.sh` (watchdog wrapper), `league_battery.sh`, `eval_parity.py`, `ab_selfplay_probe.py`, `bc_pretrain_lv8.py`, `setup_linux.sh`, `LINUX_BRINGUP.md`, `pool_league/`, `states/` (slot1 = 1v1 ditto, slot2 = lv3 FFA held-out eval, slot3 = lv8 FFA), `claude_bridge/`. GitHub: `bwalsh321/powerstone2-rl-mac` (current through leg 12 receipts + kit; leg 13 not yet pushed), `bwalsh321/sdlarch-rl` (harness fork).

## 10. Open items, in priority order

1. Reddit post: Blake drafts the back half → Claude final proof + stat pass → README TODOs filled → push leg-13 receipts + HANDOFF to the repo → post.
2. Keep the relay running (leg 14 wake at 06:15Z Sep 9; each cycle per section 5).
3. Hardware decision: eBay claim outcome, 12700K temp box vs replacement AM5 chip; then LINUX_BRINGUP.md gates.
4. `os._exit(0)` teardown patch — pending Blake's approval, apply between legs only.
5. Deferred backlog: recorder/DAgger libretro port + failure-state drill loop, discriminator eval states (only if the trigger fires), league boundary options if soft-pool >92 sustains (raise recent_k / weight prog_* / PFSP-by-winrate — pre-registered as future options, not licensed yet).
