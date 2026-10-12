# Ryzen (9950X) session handoff — Oct 12 2026, ~9:30 am EDT

The Linux session runs the Power Stone 2 relay on the 9950X. Blake (owner) wants SHORT plain-language reports,
12-hour EDT times, one change at a time read over ~3 legs, and is asked before any recipe change. Queue and current
recipe: `docs/NEXT_CHANGES.md` (keep it current). Branch `ryzen-bringup` on the box; the box has no GitHub login, so
pushes go through a Mac: `git fetch superserver@192.168.0.105:powerstone2-rl-mac ryzen-bringup:ryzen-bringup && git
push origin ryzen-bringup` (main was fast-forwarded to 314f5b3 on Oct 8 for the new README).

## 1. Live state

- **Leg 165** training since 7:15 am Oct 12, warm from leg 164, hunters in 50% of the slot 30-43
  rounds. Grades ~10:50 am. Relay = tmux `ps2train` (leg) + `relay` (watcher) -> `league_battery.sh` grades, holds or
  launches the next leg, then starts side jobs in tmux: `scout<N>` (video + contact sheets), `top<N>` (top-move grade,
  500 rounds), `hunt<N>` (hunted grade, 280 rounds, sampled).
- **Recipe** (league_env.txt): vision obs v4 (430/frame x 7 stack, SkipLSTM 128, 63 actions, taps), OBJ_GRID_N=208,
  PS2_PPO_KL_REF=prox, training slots 30-43 + 50-68 (lv3 slots dropped, balanced lineups 60-68 added), opponent pool =
  legs 113+ only (older in pool_league_archive/), pool cache 4 models/actor, PS2_HUNTER_P=0.5. league_optim.txt:
  lr 1e-4, target_kl 0.03, batch 256.
- **Grading (since leg 165, Blake Oct 12):** the per-leg lv8mix grade (1000 rounds, held-out lineups 90-94, paired
  start points) uses SAMPLED moves; the hold gate fires when it is >6 below the mean of the last 5 sampled grades
  (earlier legs' sampled numbers: receipts/eval_leg<k>_lv8mix_stoch_out.txt, n=500). Top-move grades swung +-15 from
  policy brittleness (145->148, 163->164) while sampled play held, and held the relay twice for nothing. Sampled runs
  ~5-7 points below top-move. Hunted grade is sampled too; its sampled baseline for leg 164 is running
  (receipts/hunter_sampled_baseline/). Top-move hunted grades were 161 = 5.0, 162 = 13.6, 163 = 13.9, 164 = 9.3.
- **Reporting:** the app scheduled task "Power Stone relay: hourly leg report" (ps2-relay-hourly) has been stuck on a
  permission prompt since Oct 9 (Blake must approve it once in the app). Until then the session reports each leg via
  a background `until [ -f claude_bridge/battery_leg<N>_done.txt ] ...` wait (re-arm it for each leg). Phone push is
  off in Blake's settings. `claude_bridge/last_reported_leg.txt` = last leg reported (164).
- **Safety nets:** `relay_boot.sh` (@reboot cron: restarts watcher, relaunches an interrupted leg; skips
  systemd-inhibit under cron), `relay_alert.sh` (*/15 cron -> claude_bridge/ALERT.txt). An OS reboot is pending
  (Blake runs `sudo reboot` right after a leg launches).

## 2. Results (lv8mix, top-move unless noted)

~4% early Sep -> 28.8% leg 70 (Sep 23) -> ~32% feedforward (100-109) -> 37% memory + 63 actions (117-124) ->
44.6% vision (134-138) -> 46-52% recent pool + balanced lineups (139-142) -> 56.5% leg 145 -> plateau 54-58% through
leg 163. Sampled-move grades over 153-164: 41.6-57.8, mostly ~49-52.
Lineage: ~545M steps (~2 years of game time); ~600M counting abandoned branches.

## 3. What was tried (Oct 4-12)

| Change | Legs | Result |
|---|---|---|
| Taps | 125+ | kept (harmless; enables double jumps) |
| DAgger v1 / v2 (imitate Blake's drill play) | 125-127, 129-132 | hurt 6-15 pts, off |
| Vision (obs v4) | 134+ | **kept, +6-8 pts** |
| Recent-only pool + balanced lineups + no lv3 | 139+ | kept (+1.6, unproven; fixed memory) |
| Reward cleanup (hit-source credit, stone cap 9, item inputs zeroed) | 143 | -11 pts, reverted |
| Learner batching fixes (global adv norm, split clip, batch 1024) | 149-152 | entropy rose 1.99 -> 2.35, sampled grade fell to 44; reverted (153 restarted from 149) |
| Practice start points (drill resets from the bot's losing moments) | 157-160 | no effect, off |
| KO study (10 games, Sonnet eyes + RAM) | — | bot lands ~90% of KOs (transformed barrages); dies near freshly transformed opponents / after its own form ends; per-KO reward NOT pursued |
| **Hunters** (Blake's aimbot ladder retargeted at our bot, hunter_bot.py) | 162+ | test: 40.4% vs self-copies -> 7.1% hunted; training: hunted grade 5.0 -> 13.6 -> 13.9 in 2 legs, normal grade unchanged; share raised 0.3 -> 0.5 at 165 |

Bigger network: Blake notes a 512-wide net did worse than 256 long ago; low on the list.

## 4. Rules learned the hard way

- Never edit a running relay script in place (bash reads incrementally): write `name.new` + `mv`, or before a git
  merge give the running script a new inode (`cp -p f f.tmp && mv f.tmp f`).
- Restarting a leg: `echo hold > league_trainer.txt; tmux kill-session -t ps2train`, wait for no trainer, archive the
  partial `train_leg<N>_out.txt`, delete the `<N>` row from leg_modes.txt, set league_state.txt, `echo mixed`, relaunch
  `tmux new -s ps2train -d "systemd-inhibit ... bash $PWD/league_leg_async.sh"`.
- Big experiments are built by agents in git worktrees on their own emulator ids (60-95), flags default OFF, with a
  flag-off bit-identity test and a 2-actor smoke, then merged.
- Watch entropy, training win rate (excluding drill/hunter rounds when relevant) and the sampled grade, not just the
  top-move grade.

## 5. Open items

1. Read hunters at 50% (legs 165-167) on sampled lv8mix + sampled hunted grade (vs leg 164's sampled hunted baseline).
2. Blake to approve the stuck scheduled task; optionally enable phone push.
3. Pending OS reboot.
4. Later queue in docs/NEXT_CHANGES.md (frame stack, second sealed test set, scout upgrades, cleanup).
