# M4 vision arm — setup for the Mac session (Oct 5 2026)

Blake approved this on Oct 5: while the 9950X relay runs DAgger v2 (legs 129-131), the M4 runs a **parallel vision
arm**: obs v4 (`linux_port/re/obs_v4`, commit 3d95b23) plus the object-grid fix (`PS2_OBJ_GRID_N=208`), starting from
the same bot (leg 128). Both arms are graded on lv8mix n=1000 and read against the same baseline (legs 117-124 + 128).
The Ryzen session wrote this; the Mac session executes it. **Do not start until the go-condition below is met.**

## Go-condition (all three)

1. The Ryzen session reports that the vision integration branch passed its gates (flag-off bit identity, all
   training + held-out lineups, exact warm start, throughput/memory, smoke run). Blake will relay it, with the
   branch name (below: `obs-v4`).
2. `powerstone_v6_leg128_league.zip` exists on the Ryzen (leg 128 finishes ~1:55 pm EDT Oct 5, graded ~2:30 pm).
3. Blake has finished his drill session on the M4 tonight (~9-10:30 pm). drill_play needs the M4 in real time,
   so the arm must not be running while he plays.

## Rules (read first)

- **A separate checkout, a separate lineage.** Never run the arm from `~/Downloads/macbook_migration`. Every relay
  file (league_state.txt, pool_league/, receipts/, leg_modes.txt, wrapper_league.log, claude_bridge/) lives in
  the arm's own directory, so nothing can collide with the Ryzen's files.
- **Leg numbers 1129 and up** (arm leg k = 1128 + k). File names (`powerstone_v6_leg1129_league.zip`, receipts,
  leg_modes rows) can never clash with the Ryzen's 129+ when receipts are compared or committed.
- **The Mac never launches Ryzen legs and vice versa.** `host_role.txt = train` is created only inside the arm's
  directory.
- **Never edit a relay script (league_leg_async.sh, league_battery.sh, scout_leg.sh, relay_watch_linux.sh) while an
  instance of it is running.** Bash reads scripts as it goes; a mid-run edit killed the Ryzen's leg 127 battery.
  If a script must change, write a new file and `mv` it into place.
- Never promote or overwrite `powerstone_v6_ppo.zip`. No changes to the reward, env or optimizer beyond the v4 flags.

## Steps

```bash
# 1. the arm's own checkout of the integration branch (from the Ryzen repo; the Mac has ssh access)
cd ~ && git clone superserver@192.168.0.105:powerstone2-rl-mac ps2_vision_arm
cd ~/ps2_vision_arm && git checkout obs-v4
# the game + sdlarch: the relay scripts expect ../sdlarch-rl and "../Power Stone 2 (USA).chd" next to linux_port/
ln -s ~/Downloads/macbook_migration/sdlarch-rl ../sdlarch-rl 2>/dev/null || true   # adjust to where they live
ls "../Power Stone 2 (USA).chd" || ln -s "$HOME/Downloads/macbook_migration/Power Stone 2 (USA).chd" ..

# 2. bring over what git does not carry (untracked on the Ryzen): states, the opponent pool, the warm zip
cd ~/ps2_vision_arm/linux_port
for d in states states_mixed states_mixed_lv8 states_3com_lv8 states_mixed_new; do
  rsync -a superserver@192.168.0.105:powerstone2-rl-mac/linux_port/$d/ $d/; done
rsync -a superserver@192.168.0.105:powerstone2-rl-mac/linux_port/pool_league/ pool_league/
rsync -a superserver@192.168.0.105:powerstone2-rl-mac/linux_port/powerstone_v6_leg128_league.zip .
```

3. The arm's relay state (all inside `~/ps2_vision_arm/linux_port`):
   - `league_state.txt`: `1129 ./powerstone_v6_leg128_league.zip`
   - `league_trainer.txt`: `mixed`
   - `host_role.txt`: `train`
   - `league_env.txt`: copy the Ryzen's `claude_bridge/league_env_leg128_taps_only.txt` (the leg 128 recipe: taps
     on, DAgger off), then append `PS2_OBS_V4=1 PS2_OBS_V4_ITEMEMB=keep PS2_OBJ_GRID_N=208` (`keep` = exact warm start; the
     slot-hash item embedding at obs[12..17] is left as is). **No `PS2_DEMOS`**: the drill recordings are 160-wide and would be dropped anyway.
   - `league_surgery.txt`: one line, `1129 obsv4` (the hook widens the leg 128 warm zip once, writes
     `powerstone_v6_leg128_v4.zip` and warms from it; league_state.txt keeps pointing at the leg 128 zip).
   - `leg_modes.txt`: keep the file (rows for 1129+ are appended by the launcher).
4. Before the first leg, rerun two gates on the M4 (its emulator and torch builds differ from the Ryzen's):
   `test_obs_v4_flagoff.py` (flag-off identity) and the equivalence check of `surgery_widen_v4.py` on the leg 128 zip
   (see each script's docstring for its command). Memory: the rollout buffer is ~247 MB and the actor queue can hold
   up to ~790 MB; fine on the M4, but check free RAM.
5. Start the relay (Darwin defaults: 10 actors, instance base 0, 10 eval shards):
   ```bash
   cd ~/ps2_vision_arm/linux_port
   tmux new -s ps2train -d "caffeinate -is bash league_leg_async.sh"
   tmux new -s relay -d "caffeinate -is bash relay_watch_linux.sh"
   ```
   relay_watch_linux.sh is portable (tmux + pgrep); `linux_gpu_env.sh` is sourced by the wrapper, so confirm it is a
   no-op on Darwin before launch.
6. Confirm the boot: `train_leg1129_out.txt` shows the `[config]` lines for v4 width (430 per frame, 3010 stacked,
   LSTM input 430), `actions=63`, the surgery line, no `dagger` line, and steps/s.

## Reporting

- Per leg: the same one-report format Blake gets from the Ryzen (lv8mix table with per-lineup counts, three lines
  of read, win clip). Read the arm against legs 117-124 + 128 pooled, as a 3-leg pool once 1131 is graded.
- Copy each graded receipt to the Ryzen so both arms can be compared in one place:
  `rsync -a receipts/eval_leg11[0-9][0-9]_lv8mix_out.txt superserver@192.168.0.105:powerstone2-rl-mac/linux_port/claude_bridge/vision_arm/`
- Kill switch, report only: lv8mix < 28 on two consecutive arm legs. Act only with Blake's go.
- Before Blake's next drill session, stop the arm cleanly at a leg boundary (`echo hold > league_trainer.txt`
  in the arm's directory before the leg ends), or let him play on the Ryzen.
