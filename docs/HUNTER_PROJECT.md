# Hunter side project (M4) — Oct 8 2026

**Blake's idea:** a scripted, maximally aggressive opponent that only hunts our bot, like his old aimbot. Why: in
grading the three level-8 CPUs target our bot only ~2-5% of the time (obs v4 `com_targets_me`; an even split would
be ~33%). Part of the 56% lv8mix comes from being ignored. People gang up; a hunter tests and trains for that.

**Where it runs:** the M4, as a parallel side project. The Ryzen relay is not touched: it keeps training on its
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
4. **Only if hunted mode exposes a big weakness:** propose mixing hunters into training (e.g. 1 in 5 pool seats)
   as a separate Ryzen experiment with its own 3-leg read. That is Blake's call, not part of this project.

## M4 notes
- Work in the vision-arm checkout `~/ps2_vision_arm` (or a fresh clone of ryzen-bringup from the Ryzen) on a
  branch `hunter`; copy the leg 145 zip and states from the Ryzen with rsync (paths in docs/M4_VISION_ARM.md).
- Coordinate with whatever else runs on the M4 (Blake is training Pokemon Emerald there): keep to 2-4 emulators.
- macOS: `pgrep -c` does not exist (use `pgrep -f ... | wc -l`); the 4-player harness needs
  `PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:.`.
- Report back: hunter behaviour clip, hunted-mode win % for leg 145 vs its normal 56.5%, and the code on branch
  `hunter` pushed to GitHub (the M4 has credentials) so the Ryzen can pull it.
