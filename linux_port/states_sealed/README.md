# Sealed test set: slots 95-99 (Oct 17 2026)

A second held-out set, graded rarely by `sealed_grade.sh <N>` to confirm big claims. The per-leg grade keeps using
slots 90-94 (lv8mix). Audit item 4 in docs/AUDIT_OCT17.md explains why: 60+ legs of keep/revert decisions were all
judged on 90-94.

The states live in `states/slot95.state` to `states/slot99.state`, next to 90-94. They are gitignored like every
savestate. This folder holds only the recipe and the tools. Each state is gzip level 9, saved 200 frames after the
stage-select A press, the same as 50-68 and 90-94.

| slot | P1 COM | P3 COM | P4 COM | stage | sha256 (first 16) |
|---|---|---|---|---|---|
| 95 | Jack | Accel | Wang-Tang | Desert | b94f13a1d7637cf8 |
| 96 | Mel | Falcon | Ayame | Desert | 8beec331568fb09b |
| 97 | Gourmand | Pete | Rouge | Desert | f562b193b1cd9d1e |
| 98 | Ryoma | Gunrock | Wang-Tang | Blue Sky | 354a65c8772a9d58 |
| 99 | Pride | Galuda | Accel | Dark Castle | b71808d7620c867b |

P2 is our HUMAN Falcon. All three COMs are level 8.

## How the lineups were chosen
- A script listed every 3-character set that shares at most one character with each lineup in 50-68 and 90-94
  (states_3com_lv8/lineups.json and states_3com_lv8_new/lineups_new.json); 17 sets qualify. It then picked 5 of those
  that also share at most one character with each other, maximising the number of distinct characters. The result
  covers 13 of the 14 characters. Julia is left out because she already has the most seats elsewhere (7).
- Training slots 30-43 are single-COM lineups on Desert, so they do not overlap.
- Stages: every training and held-out slot is on Desert. 95-97 are Desert, so they can be compared with lv8mix.
  98 (Blue Sky) and 99 (Dark Castle) are stages the bot has never trained on. On those two, obs v4's stage-geometry
  block reads 0, because it is built only for Desert. `sealed_grade.sh` prints the Desert subtotal and the new-stage
  subtotal separately.
- SLOT_META 95-99 = (2, 8), the same context as 90-94. Here the stage dim marks the three-COM lv8 regime, not the stage.

## Guards (training can never see them)
- `train_selfplay_async.py` exits if PS2_STATE_SLOTS contains any slot from 90 to 99.
- `drill_capture.py` always refuses 95-99. `--allow-heldout` does not unlock them.
- `ffa_selfplay_env.load_drill_index` refuses drills from 90-99.
- `league_battery.sh` and the relay never call `sealed_grade.sh`.

## Procedure
These are the steps used on Oct 17 2026: headless, instances 70-73, nice 15, at most 3 emulators at once. Run them
from linux_port/ with the venv active, `source ./linux_gpu_env.sh`, and
`SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:.`.

1. Make the menu state. Load states_mixed/slot0.state (read only) and run
   `wait:1300, p2:start, DOWN x3, A (QUIT), wait 180, DOWN x5, A (GAME OPTIONS), RIGHT x5 (DIFFICULTY 8), DOWN x10, A (EXIT), B (no VMU save), UP x3, A (ORIGINAL), wait 120, save`.
   This lands on PLAYER SELECT with the global difficulty cell at 7. In drive.py syntax:
   `wait:1300,p2:start:4,wait:40,rep:3:p2:down:3;wait:10,p2:a:4,wait:180,rep:5:p2:down:3;wait:10,p2:a:4,wait:60,rep:5:p2:right:3;wait:10,rep:10:p2:down:3;wait:10,p2:a:4,wait:60,p2:b:4,wait:60,rep:3:p2:up:3;wait:10,p2:a:4,wait:120,save:<scratch>/orig_select_opt8.state`
2. Stamp each slot. Run `python tools/drive.py --load <scratch>/orig_select_opt8.state --instance 70 --steps "$(python tools/gen.py <slot> '<stage>,wait:30,p2:a:4,wait:200,save:<scratch>/slot<slot>.state')"`.
   Replace `<stage>` with `p2:up:3` for Desert, `wait:1` for Blue Sky (the default), or `p2:right:3` for Dark Castle.
   The STAGE SELECT grid is: top row Blue sky, Dark castle, Tomb; middle row Space station and RANDOM; Desert is UP from
   Blue sky. drive.py segfaults in emu.close() after the save. That is the known teardown crash and the saved state
   is not affected.
3. Verify. Copy the states to states/ and run `python states_sealed/tools/verify.py 95,96,97,98,99,90,91 73`.
   Result on Oct 17, after a fresh reload of every file: ALL PASS.
   - Seat table: P1/P3/P4 are COM with the planned characters; P2 is HUMAN Falcon.
   - Difficulty at load: [global, AI, AI, AI, AI] = [7, x, x, 7, 7]. The two transient cells (x) behave as in 90/91.
   - G_STAGE 900 frames in: 5/5/5 Desert, 0 Blue sky, 1 Dark castle. The area id 0x8C472CF8 agrees.
   - P2 face_norm is 0.991-0.993.
   Select-screen and stage-screen contact sheets and the fight screenshots (+1200 frames, HUD names) were checked by eye.
4. Production env. A 5-episode `eval_parity.py --slots 95,96,97,98,99 --stochastic` run on leg 193 under the live
   contract (obs v4, stack 2, taps, grid 208) gave opps=3 on every slot and no errors.
