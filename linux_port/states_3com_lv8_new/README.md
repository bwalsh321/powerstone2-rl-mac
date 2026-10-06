# states_3com_lv8_new: staging for three-COM lv8 training lineups, slots 60-68 (Oct 6 2026)

Same shape as states_3com_lv8/slot50-59: P1, P3 and P4 are lv8 COMs, P2 is the HUMAN Falcon (the learner), the stage is
Desert Area, and each state is saved 200 frames after the stage-select A press. The files are gzip (level 9), the same
format as slot50-59; the raw state is 36,439,543 bytes, as in slot50. Nothing has been registered yet: there is no
SLOT_META entry and no league_env change, and nothing is committed.

## Lineups (lineups_new.json, role "train")
| slot | P1 | P3 | P4 |
|---|---|---|---|
| 60 | Gunrock | Gourmand | Pride |
| 61 | Accel | Gunrock | Ayame |
| 62 | Pride | Pete | Gunrock |
| 63 | Gunrock | Accel | Mel |
| 64 | Gourmand | Galuda | Jack |
| 65 | Mel | Jack | Gourmand |
| 66 | Falcon | Rouge | Accel |
| 67 | Wang-Tang | Ayame | Pride |
| 68 | Galuda | Julia | Pete |

COM seat counts over slots 50-68 (57 seats): every character has 4, except Jack with 5. None of the nine sets
equals a held-out lineup (90-94), a slot 50-59 lineup, or another new lineup. Checked by script against lineups.json.

## Procedure (headless, from the main menu, as in states_mixed/README.md slot30-43/50-59)
Tools are in tools/ (scratch copies; no tracked file was edited). drive.py is origin/main
re/discriminators/tools/drive.py with the Linux core path, instance 70 and an `info:` RAM step added. gen.py builds the
step string for each slot. Instances 70/71 were used, nice 15, OMP_NUM_THREADS=1, at most 2 emulators.
1. Load states_mixed/slot0.state (read only; lv3, so difficulty cell = 2). wait 1300 frames (the fight must be live;
   a START press during the intro is ignored). P2: START, DOWN x3, A (QUIT), DOWN x5, A (GAME OPTIONS), RIGHT x5
   (DIFFICULTY 8), DOWN x10, A (EXIT), B (do not save), UP x3, A (ORIGINAL), which lands on PLAYER SELECT. This
   menu state was kept as scratch orig_select_opt8.state.
2. Per slot, each COM port works on its own column: A (HUMAN to COM), DOWN x2, A (shows the default: P1 Falcon,
   P3 Pete, P4 Accel), then A x (target - default) or B x (default - target) in roster order Falcon, Ayame, Gunrock,
   Ryoma, Wang-Tang, Galuda, Rouge, Jack, Pete, Julia, Gourmand, Accel, Mel, Pride. Stepping never crosses RANDOM
   SELECT. P2: DOWN x2, A (Ryoma), B x3 (Falcon). Then P2 START, UP (Desert Area), A, wait 200, save.

## Verification (all 9 slots pass)
- (a) Select-screen names: sheets/select_sheet.png (PLAYER SELECT) and sheets/stage_sheet.png (STAGE SELECT,
  Desert area highlighted). All names match the plan.
- (b) Difficulty: global cell 0x8C472AD4 = 7 at load. The AI copies 0x8C5429AD/0x8C5429C8 also read 7 at load.
  0x8C4683A6/0x8C46C3D4 read 2 at load and 7 from +50 frames. These two cells change during the intro (slot50 also
  moves through 7 -> 47 -> 103 -> 34 -> 144), so the new states sit a few dozen frames earlier in that transient
  than slot50. The fight goes live about 825-840 frames after load, against 826 for slot50.
- (c) Seat table 0x8C472DA8 + 0x14k (type/char id, decoding per re/player_state/PLAYER_STATE.md). The decoder was
  first checked on slot50/54/59, where it matched lineups.json. After a fresh reload of every staging file, P1/P3/P4
  are COM with the planned characters.
- (d) P2 = HUMAN Falcon in the seat table; P2 face_norm is 0.991-0.993.
- (e) Stage area id 0x8C472CF8 = 5 (desert). Screenshots are in sheets/verify_sheet.png (desert, +50 frames) and
  sheets/fight_sheet.png (+1200 frames, HUD names).
- (f) Production env: tools/envtest.py builds PowerStoneEnvLibretro the way eval_parity.py does (instances 72/73).
  states_dir is a scratch copy of these files under their own slot numbers, and SLOT_META 60-68 = (2, 8) is set as
  an instance override to match 50-59. Each slot ran reset() plus 100 random steps. Result: active_opp = [0, 2, 3]
  (3 opponents), finite obs, DIFF_DIM = 1.0, no "SHORT OPPONENT SET" and no errors on any slot.

To adopt: copy slot60-68 into states_3com_lv8/, merge lineups_new.json, add range(60, 69) -> (2, 8) to SLOT_META in
powerstone_env_v6 (and ffa_selfplay_env if it mirrors it), and add the slots to PS2_STATE_SLOTS.
Note: the drive.py process segfaults in emu.close() at exit, after the save. This is a teardown issue and does not
affect the saved states, which were reloaded and verified above.
