# states_mixed — mixed-arena savestates (learner = P2 Falcon HUMAN, P1/P3 = HUMAN Falcon pool seats, P4 = COM lv3)
slot0.state  P4 COM = Falcon (Sep 15; the original mixed state)
slot10-22    P4 COM character randomization set (Sep 20 2026), stamped headlessly with menu_drive.py
             from slot0: pause -> CHANGE CHARACTER -> P2 cursor into the P4 column, portrait row,
             A x k (roster order) -> START -> stage UP (Desert Area) -> A -> saved 200 frames in.
             Verified by select-screen portrait (scratchpad contact sheet) and in-env probe.
  slot10 Ayame   slot11 Gunrock  slot12 Ryoma   slot13 Wang-Tang  slot14 Galuda  slot15 Rouge  slot16 Jack
  slot17 Pete    slot18 Julia    slot19 Gourmand slot20 Accel     slot21 Mel     slot22 Pride
Enable in training: league_env.txt gets PS2_STATE_SLOTS=0,10,11,12,13,14,15,16,17,18,19,20,21,22
(FFA env forces SLOT_META (1,2) for every configured slot). Evals never use this directory.

slot30-43    P4 COM at LEVEL 8 (Sep 25 2026), same lineup (P1/P2/P3 HUMAN Falcon, P4 COM), Desert Area, saved
             200 frames in; roster order 30 Falcon, 31 Ayame, 32 Gunrock, 33 Ryoma, 34 Wang-Tang, 35 Galuda, 36 Rouge,
             37 Jack, 38 Pete, 39 Julia, 40 Gourmand, 41 Accel, 42 Mel, 43 Pride. Stamped headlessly from the MAIN MENU
             (pause -> QUIT -> GAME OPTIONS -> DIFFICULTY 8 -> EXIT (No to VMU save) -> ORIGINAL -> PLAYER SELECT:
             p4:A = COM; each port picks on its PLAYER SELECT row, A cycles the roster forward, B backward; the human
             roster has a RANDOM SELECT entry after Pride (COM roster does not); P2 from Ryoma B x3 -> Falcon, P3 from
             Pete B x8 -> Falcon, P4 from Accel A x ((k-11) mod 14); START -> stage UP -> A). Verified: global
             difficulty cell 0x8C472AD4 = 7 (0-based) + 4 AI copies (0x8C4683A6, 0x8C46C3D4, 0x8C5429AD, 0x8C5429C8);
             idle probe: COM first hit ~1,000 f vs ~1,400 f and 3-13x the damage of the lv3 set; P1-P3 face_norm 0.991
             (Falcon body). Source copies in states_mixed_lv8/.
