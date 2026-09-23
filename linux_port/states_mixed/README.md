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
