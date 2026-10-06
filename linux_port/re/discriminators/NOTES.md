# Discriminator stamping — STOPPED (superseded by lv8mix battery)

Work halted on coordinator instruction before slot4/slot5 were stamped.
Nothing outside this folder was modified. Tools: `tools/drive.py` (menu_drive.py
+ p3/p4 ports, L/R triggers `pN:l|r:<frames>`, `dump:` RAM, `rep:n:a;b`, upright
PNGs, default instance 4), `tools/montage.py` (contact sheets).

## Option RAM (SYSTEM_RAM offset; DC address = 0x8C000000 + offset)
Found by stepping DIFFICULTY 3->8->1->2->1 in OPTIONS and diffing dumps (unique hit):

| offset | DC addr | meaning |
|---|---|---|
| 0x472AD4 | 0x8C472AD4 | COM DIFFICULTY - 1 (0..7; 8 wraps to 1) — CONFIRMED |
| 0x472AD5 | 0x8C472AD5 | TIME LIMIT (0 = OFF) — inferred |
| 0x472AD6 | 0x8C472AD6 | DAMAGE - 1 (2 = "3") — inferred |
| 0x472AD7.. | | VMU ITEMS(1=ON), SOUND(1=STEREO), BGM-1 (0x0e), SE-1 (0x0e), QUICK CONTINUE(0=OFF) — inferred from layout |

Readings of existing states: slot1 diff=4 (byte 03; also time/damage bytes differ: 01 01),
slot2 diff=3, slot3 diff=8. Difficulty set in OPTIONS and declined at the save prompt
(B = "No") stays live in RAM — no VMU write needed.

## Menu facts (headless, verified with screenshots in shots/)
- In-fight: `p2:start` = 2P PAUSE; `down x3` = QUIT; `a` -> title menu cursor on 1-ON-1.
- Title carousel (vertical): ITEM SHOP, GAME OPTIONS, EXTRA OPTIONS, SAVE/LOAD, 1-ON-1,
  ARCADE, ORIGINAL, ADVENTURE. From 1-ON-1: `up x3` = GAME OPTIONS. From GAME OPTIONS: `down x5` = ORIGINAL.
- OPTIONS: cursor starts on DIFFICULTY; `right` +1 (wraps 8->1). EXIT = `down x10`, `a`; save prompt `b` = no save.
- PLAYER SELECT (ORIGINAL): any player's cursor can edit any column. A on the HUMAN row cycles
  HUMAN -> COM -> NO ENTRY. A on the PLAYER SELECT box picks a default character
  (col1 = Falcon, col2 = Ryoma); then A = next, B = previous in this cycle:
  Ryoma, Wang-Tang, Galuda, Rouge, Jack, Pete, Julia, Gourmand, Accel, Mel, Pride,
  RANDOM, Falcon, Ayame, Gunrock (wraps).
- When all picked: "PRESS START" marquee; a "TEAM BATTLE PLAY" logo appeared for the
  Pride(red COM) vs Falcon(yellow HUMAN) 1v1 config even with distinct colors; 4-seat configs show
  "BATTLE ROYAL PLAY" instead. Whether 2-player ORIGINAL is rule-different (team logic) is UNRESOLVED.
- STAGE SELECT 3x3 grid (cursor starts top-left): row1 Blue sky, Dark castle, Tomb;
  row2 Iceberg, Space station, Extra stage 2 / RANDOM; row3 Desert, Pharaoh walker, Chaos.
  Desert = `down x2`, `a`. Intro then ~25 s of camera/character intros until "ACTION!".

## Verified lv8 1v1 step script (reached the fight; NOT saved as a deliverable)
```
--load states/slot2.state --steps "wait:600,p2:start:4,wait:30,rep:3:p2:down:3;wait:8,p2:a:4,wait:240,
rep:3:p1:up:3;wait:20,p1:a:4,wait:90,rep:5:p1:right:3;wait:10,rep:10:p1:down:3;wait:8,p1:a:4,wait:60,
p1:b:4,wait:150,rep:5:p1:down:3;wait:20,p1:a:4,wait:120,
p1:a:4,wait:12,rep:2:p1:down:3;wait:10,p1:a:4,wait:15,rep:2:p1:up:3;wait:10,rep:2:p1:right:3;wait:10,
p1:a:4,wait:12,p1:a:4,wait:12,p1:right:3,wait:10,p1:a:4,wait:12,p1:a:4,wait:12,
rep:3:p1:left:3;wait:10,rep:2:p1:down:3;wait:10,p1:b:4,wait:15,p1:b:4,wait:15,
rep:2:p2:down:3;wait:10,p2:a:4,wait:15,rep:3:p2:b:4;wait:15,p2:start:4,wait:120,
rep:2:p2:down:3;wait:15,p2:a:4"
```
Result: P1 Pride COM, P2 Falcon HUMAN, P3/P4 NO ENTRY, desert, diff byte = 8.
For lv6 use `rep:3:p1:right:3` in OPTIONS (from slot2's 3).

## BLOCKER found (matters for any future 1v1 stamp)
Starting from an in-fight state leaves STALE health/pos for NO ENTRY seats
(HEALTH[2] stayed 954 from slot2's match). The env's `_detect_opp` (health > 100
and pos != 0) would count those ghosts as opponents, so the win would never
fire. Navigate from a fresh boot instead (healths 0); boot reaches the attract
movie at ~32 s (`work/boot_32s.state`), title menu navigation from there not yet done.
(Disk cleanup: RAM dumps and most WIP states/screens were deleted; `work/w8_stage.state` = lv8
Pride-vs-Falcon stage select, `work/boot_32s.state` kept.)

## Other finding
Mac `states/slot2.state` lineup is P1 AYAME, P2 FALCON, P3 PETE, P4 ACCEL (desert,
lv3) per the in-fight HUD — not the rig lineup (Pete/Falcon/Pride/Julia) that
HANDOFF said the Mac slot2 "must match". The re-stamp was never done.
