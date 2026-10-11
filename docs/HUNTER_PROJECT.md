# Hunter side project (M2) — Oct 8 2026

**Blake's idea:** a scripted, maximally aggressive opponent that only hunts our bot, like his old aimbot. Why: in
grading the three level-8 CPUs target our bot only ~2-5% of the time (obs v4 `com_targets_me`; an even split would
be ~33%). Part of the 56% lv8mix comes from being ignored. People gang up; a hunter tests and trains for that.

**Where it runs:** Blake's M2 MacBook, as a short parallel test (the M4 is busy with another project). The Ryzen relay is not touched: it keeps training on its
own recipe (see docs/NEXT_CHANGES.md). Nothing here changes `league_env.txt`, the pool, or the grading.

## Steps

1. **Port the aimbot into a hunter seat.** Source: `cheater_bot.py` (v4 "BLAKE-FIT" ladder, fitted from Blake's
   recorded play) in the Windows-era repo github.com/bwalsh321/powerstone2-rl (also `aimbot_gauntlet.py`).
   - New `linux_port/hunter_bot.py`: `HunterBot.decide(state, my_seat, target_seat) -> joint action (0..62)`
     (`action_space.py`; buttons are taps when `PS2_BUTTON_TAP=1`). Use the bot's own 63-action interface, not the
     analog stick, so the hunter's edge is aggression, not better controls.
   - Ladder (target = our bot, seat P2 / player index 1): carrying 2 stones -> finish the set; target carrying
     stones -> mug it; transformed -> missiles/Power Drive at the target; otherwise close distance and attack the
     target; never pick another fighter as a target (stones dropped by others are fair game).
   - Hook: `ffa_selfplay_env.py` `step()` (~line 289) drives each policy seat via `v.runner.act(obs_v)` then
     `self._apply_action_for(a, player_port=v.player, n_act=63)`. Add a hunter path there: when a seat is a
     hunter (e.g. `PS2_HUNTER_SEATS=0` or a pool entry named `HUNTER`), call `HunterBot.decide(self.prev, ...)`
     instead of a model. Raw RAM state is in `self.prev` (positions, health, stones, forms; see `_me`, `_opps`,
     `ps2_ram.py`). Default off: with no hunter flag everything is bit-identical (prove it with a test, as for
     obs v4 / reward cleanup).
2. **Hunted grading mode.** Savestates with open (HUMAN) seats are `states_mixed/slot30-43` (P1/P3 human, P4 = one
   lv8 CPU, the 14 characters). Grade with P1 = hunter and P3 = hunter (or P3 = a pool bot), P4 = lv8 CPU, e.g. 500
   rounds round-robin over 30-43, deterministic, paired pre-roll (eval_parity.py already supports `--slots` and
   the paired schedule). Output: win %, and how often the bot is KO'd by the hunter vs the CPU.
3. **Measure** the Ryzen's best bot (leg 145, `powerstone_v6_leg145_league.zip`, vision: needs
   `PS2_OBS_V2=1 PS2_OBS_V3=1 PS2_OBS_V4=1 PS2_OBS_V4_ITEMEMB=keep PS2_OBJ_GRID_N=208 PS2_BUTTON_TAP=1`) in hunted
   mode. Also sanity-check the hunter itself: a hunter vs three lv8 CPUs alone (no bot) should be clearly
   aggressive and score real damage.
4. **A one-to-two-leg training test (Blake, Oct 8):** on the M2, warm from leg 145, run 1-2 legs with hunters
   in some pool seats (e.g. P1 = hunter in a fraction of episodes on slots 30-43; the 3-CPU slots 50-68 stay as
   they are), own lineage numbers (e.g. 2146, 2147) in its own checkout, then grade each leg on BOTH lv8mix
   (compare with the Ryzen's legs 146-147 on the same 1000 games) and hunted mode (compare with leg 145).
   The M2 is slower than the Ryzen; 2M-step legs are fine for a test. If it helps, moving it to the Ryzen is a
   separate decision for Blake.

## M2 notes
- Fresh clone of ryzen-bringup from the Ryzen (`git clone superserver@192.168.0.105:powerstone2-rl-mac ps2_hunter`)
  on a new branch `hunter`; copy the leg 145 zip, `states/`, `states_mixed/` and `pool_league/` (legs 140+ is
  enough) from the Ryzen with rsync (paths in docs/M4_VISION_ARM.md, which ran the same kind of arm). The M2 needs
  the game .chd, the flycast core, a Python venv from requirements.txt and the harness built from `sdlarch-rl/`;
  the old M2 setup script is in git history (`git show 314f5b3^:setup_mac.sh`).
- Lineage, host_role.txt = train, and relay files stay inside that checkout (see docs/M4_VISION_ARM.md rules).
- macOS: `pgrep -c` does not exist (use `pgrep -f ... | wc -l`); the 4-player harness needs
  `PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:.`.
- Report back: hunter behaviour clip, hunted-mode win % for leg 145 vs its normal 56.5%, and the code on branch
  `hunter` pushed to GitHub (the Macs have credentials) so the Ryzen can pull it.

## Results (Ryzen worktree, Oct 10 2026; done here instead of on the M2)
- Code: `linux_port/hunter_bot.py`, the hook in `ffa_selfplay_env.py` (`PS2_HUNTER_SEATS`, `PS2_HUNTER_P`,
  `PS2_HUNTER_SLOTS`, `PS2_HUNTER_TARGET`, `PS2_HUNTER_STATS`), `eval_hunted.py`, `test_hunter_flagoff.py`. Flags off
  (also stats-only, and hunters set with no eligible slot): bit-identical to ed362b0 on slots 30 and 55 (PASS).
- Hunted grading of leg 159, slots 30-43, 280 rounds (20 per slot, round-robin), deterministic, paired pre-roll:

  | P1 / P3 | win % | bot damage taken /round by source (P1, P3, P4 COM, unattributed) | KOs of the bot (P1, P3, P4, unattr.) | median length |
  |---|---|---|---|---|
  | frozen leg 159 (baseline) | 40.4 (113/280) | 0.09, 0.10, 0.15, 0.50 | 15, 21, 18, 113 | 697 |
  | hunters | 7.1 (20/280) | 0.39, 0.34, 0.11, 0.14 | 89, 78, 52, 40 | 346 |

  Paired by start point: 99 rounds won only in the baseline, 6 only when hunted. Receipts: `linux_port/receipts/hunter/`.
  "Unattributed" = the game's hit-source pointer is null or unowned; most of the frozen bots' damage lands there
  (projectiles / specials), so the per-seat split of the baseline understates P1/P3.
- Training readiness: 2-actor smoke of `train_selfplay_async.py` (live recipe + `PS2_HUNTER_P=0.3`, warm leg 159,
  16,384 steps) ended in "leg complete"; 6 of the 12 slot-30-43 episodes had `hunters=1`.
