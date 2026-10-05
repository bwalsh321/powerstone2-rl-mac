# Ryzen (9950X) session handoff — Oct 5 2026, ~8:30 pm EDT

The Linux session runs the relay on the 9950X. The Mac session is the sole writer of HANDOFF.md and should fold this
file into it. Everything here is committed on branch `ryzen-bringup` on the box (the Mac pulls it with
`git pull --no-rebase --no-edit superserver@192.168.0.105:powerstone2-rl-mac ryzen-bringup`, then pushes to GitHub).

## 1. What is live

- **The relay runs unattended.** tmux `ps2train` runs the leg (`league_leg_async.sh`). tmux `relay` runs
  `relay_watch_linux.sh`, which starts `league_battery.sh` when a leg completes; the battery grades the leg, runs the
  hold gate, launches the next leg and starts the scout (`scout_leg.sh`). Both run under `systemd-inhibit`.
- **Leg 124** is training (launched ~7:15 pm Oct 4), with **leg 125 at ~10:45 pm**. A leg is ~2 h 55 min of training
  plus a ~31 min battery, about 7 legs/day.
- **Launch permission is host-local:** `linux_port/host_role.txt` = `train` (untracked) exists only on the box, so
  the Mac can never launch a leg.
- **Box clock is EDT; the Claude scheduler (CronCreate) runs on UTC.** Write cron times in UTC.
- Hourly report cron at :23 UTC (session-only). `claude_bridge/last_reported_leg.txt` = the last leg reported to Blake.

## 2. Recipe changes made on the Ryzen (in order; leg_modes.txt carries each leg's flags)

| Leg | Change | Read |
|---|---|---|
| 104 | New machine (16 actors on instances 20-35, learner OMP 4) | lv8mix 37.0 at n=500 |
| 109 | Mac's two bug fixes (proj_hist_v2 reset, hit-source bounds) | flat |
| 110 | **Memory**: SkipLSTM hidden 128 (`surgery_lstm.py`, exact warm start) | memory-only read 111-112 FLAT (+1.3, p=0.31) |
| 113 | **63-action joint controls** (direction x button, `surgery_actions.py`, penalty 3) | dip to 27.5, recovered by 114 |
| 117-123 | memory + 63 actions settled | **lv8mix 37.2% vs feedforward 32.3%, p<1e-6** |
| 125 | **Buttons-as-taps + DAgger** (`PS2_BUTTON_TAP=1 PS2_DEMOS=drills/leg123 PS2_BC_COEF=0.2`) | pending |

lv8mix by leg: 104 37.0* · 105 31.4 · 106 33.7 · 107 32.0 · 108 30.9 · 109 31.1 · 110 30.0† · 111 32.8† · 112 33.5 ·
113 27.5 · 114 31.1 · 115 30.3 · 116 33.1 · 117 40.2 · 118 33.1 · 119 36.5 · 120 39.2 · 121 40.0 · 122 37.8 · 123 33.6.
(*n=500; †corrected seed-fix re-evals, see 4.) Per-leg grade is lv8mix only, n=1000 on 20 shards (Blake, Oct 2;
trio, lv3 and champion AB on demand from saved zips).

**Pre-registered read for leg 125+:** baseline = legs 117-124 (~37%). Expect a dip on the first tap leg (changed
button semantics, like leg 113). Kill switch: lv8mix < 30 on two consecutive legs -> report to Blake; revert =
`claude_bridge/league_env_pre_leg125_dagger.txt`. DAgger signals: `[bc] agree=` rising in the training log; reviews
showing fewer "final 1v1 with no transform left" deaths.

## 3. DAgger pipeline (built Oct 3-5)

1. `drill_capture.py`: the bot plays lv8mix deterministically. Each loss saves emulator snapshots ~8 s and ~4 s before
   the KO. `drills/leg116` holds 120 drills; `drills/leg123` is being harvested now (60 losses -> ~120 drills).
2. `drill_play.py` (Blake, on the M4): plays the bot's seat from each drill through the bot's own 63-action interface
   with taps. It records the bot's exact observation plus his action, is resumable, and detects Xbox pads (d-pad
   buttons 11-14, LB/LT = L, RB/RT = R, background-events hint).
3. `dagger.py` + `train_selfplay_async.py`: after each PPO update, coef x mean(-log pi(a_human|s)) on 16 drills, before
   the broadcast. It only loads recordings whose `button_tap` matches the trainer's.
- **Blake's 26 recordings in drills/leg116 are HOLD mode** and are ignored by the tap-mode trainer. In them he avoided
  the KO in 21/26 moments the bot lost. Leg 121 agreed with his action 7.4% (direction 17.7%, button 39.8%).
- The Mac commands are in the chat history (pull, rsync the drills over, run drill_play, rsync rec_* +
  recordings.jsonl back).

## 4. Bugs found and fixed (worth knowing)

- **Seed bug:** surgery saved `seed=0`; SB3 load re-seeded every process identically. All 20 eval shards replayed
  50 rounds (leg 110-111 numbers were n=50), and actors were correlated. Fixed in `recurrent_policy.load_model`. Leg
  110/111 re-graded in `receipts/reeval_seedfix/`.
- **LSTM evals thrashed** (thread per core x 20 shards): batteries set `OMP_NUM_THREADS=1`.
- **Held buttons:** the same button on consecutive decisions was one press, so no double jump and one rocket.
  `PS2_BUTTON_TAP` (5 frames on, 1 off; jump height identical tap vs hold; double jump 383-421 vs 331 held).
- **Drill freeze:** a low-health drill failed the env's start-of-match test and reloaded forever. drill_play relaxes
  it to "alive" while loading a drill.
- **Linux pygame:** its crash-signal handlers broke flycast's dynarec (`sig_guard.py`); `--hidden` uses the SDL dummy
  driver for pygame; the scout needs system ffmpeg (drawtext).
- Duplicate rounds within an eval (~840 unique of 1000) are the eval contract's 0-239 frame pre-roll, not a bug.

## 5. Infrastructure notes

- Rendering: SDL offscreen EGL on the RTX 3090 (`linux_gpu_env.sh`). Harness lazy frame readback (+25-57%). RAM reader
  shares sweeps across synths (bit-identical, `test_sweep_twin.py`).
- 16 actors ~370-380 steps/s with memory (~345 at first). Learner update ~6-14 s with the LSTM.
- `league_surgery.txt` = `110 lstm128` / `113 joint63` (one-shot surgeries keyed by leg).
- Hold gate (`hold_gate.py`): lv8mix floor 20%; lv8mix receipt required; trio/AB/lv3 checks only if present.

## 6. Open / queued (Blake's order)

1. DAgger: Blake records tap-mode drills from `drills/leg123`, which enter at the next leg start after they arrive.
2. Item vision: the bot can't see ground items, bombs or cacti (it memorizes cactus positions). Reverse-engineer
   item objects, then a zero-init obs block, then its own read. Not started.
3. Pinned: the split battery (M4 as eval box). Character stays Falcon (Blake).
4. The Mac's `git stash` holds Blake's old local play_vs.py edit (Oct 4), not yet reviewed.
