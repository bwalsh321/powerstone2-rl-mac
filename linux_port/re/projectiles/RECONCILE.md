# Melee signal reconciliation (projectiles agent vs player_state agent)

Oct 4 2026, instance 4. The only files touched are in `re/projectiles/`: `tools/e1_reconcile.py`,
`tools/e2_reconcile2.py` and the new capture `cap/Dpobj` (18 MB).

## 1. Base address
My player-object offsets use **the same base**: P_k = PLAYER_MAT[k] − 0x490 = 0x8C532498 + k·0x3938.
"+0x414" and "+0x134" in PROJECTILES.md are therefore P+0x414 and P+0x134.

- **No conflict at +0x134.** My "move id" is **byte 0** of that word. The player_state airborne bit
  (0x400) is in **byte 1**.
- **Use byte reads at +0x134.** Read byte 0 for the move id and test bit 2 of byte 1 for airborne. A u32
  read of the whole word mixes the two.

## 2. Side-by-side capture
**Data:** two lv8 all-COM desert captures with full player objects: `cap/Afull` (1,800 frames) plus a new
`cap/Dpobj` (1,800 frames, lineup Ayame/Gunrock/Falcon/Pride). Together they hold **41 melee hits**, where
the victim's hit-source pointer is the attacker's player object.

**How lead is measured:** the number of frames from the signal turning on (for the current move) to the
frame the victim's health drops.

| signal | on at the hit (f−2..f) | lead before hit: median / p10 / p90 | duty cycle (A / D) |
|---|---|---|---|
| P+0x414 ≠ 0 (attack-data pointer; per move = until the pointer changes) | 41/41 | **9 / 7 / 62** frames | 14.4% / 2.4% |
| P+0x124 byte1 ≠ 0 (hitbox live) | 41/41 | **0 / 0 / 13** frames | 12.9% / 1.9% |

**How the two relate:** they are two phases of the same attack, not competing signals.
- **+0x414 is the startup signal.** It turns on when the move starts, which is about 7 frames before the
  first hit on single strikes (11 of 41 hits show exactly 7 frames).
- **+0x124 byte1 is the active-frames signal.** In 29 of 41 hits it switches on within 0–2 frames of
  the hit itself.
- **Order:** +0x414 came on no later than +0x124 for 95% of hits (39 of 41). In the 2 exceptions the
  pointer advanced to the next combo step on the hit frame, while +0x124 was already live.
- **Long leads:** the 62–95 frame cases are Ryoma's state-26 multi-hit string, where one descriptor
  covers a long window.

**+0x124 also lights without +0x414:** 5.7% of seat-frames in A. Those frames are in state 15 (379
frames), state 32 (thrown body, 42) and state 14 (37). These are body hitboxes (getup, thrown, tumbling),
which agrees with the player_state note. So +0x124 is the broader "this body can hurt you right now" flag.
+0x414 is melee-move-specific.

**Answer:**
- **Earliest reliable warning: P+0x414 ≠ 0.** It gives about 7 frames of lead on single strikes and
  caught 41/41 hits. Its weaknesses are that it does not mark the exact active frames, and it stays on
  through recovery and whole combo strings.
- **Exact "hitbox live now": P+0x124 byte1.** It also caught 41/41 hits, but gives essentially no lead
  (median 0).
- **Use both in obs.** They map onto the player_state attack phases: startup = 414 on and 124 off;
  active = 124 on; recovery = 414 on after 124 goes off.

## 3. Is P+0x1AC a usable hitbox centre/radius?
**Method:** at the last frame with the hitbox live before each hit (n = 41), I compared the f32 centre
x,y,z and radius (+0x1AC..+0x1B8) with the victim's PLAYER_MAT+0x30 position.

**Results:**
- **Radius:** median 31, range 30–208. It matches player_state's "radius 40-ish" for punches; bigger
  moves are larger.
- **Freshness:** the centre is rewritten when each window opens (41/41), so it is live data, not stale.
- **Height:** vertically it sits near the victim's position height (dy median −17).
- **Horizontal distance to the victim:**
  - Centre to victim: median **101 u** (p90 228).
  - Attacker to victim: median 231 u.
  - So the sphere sits roughly 100 u in front of the attacker, about halfway to the victim.
- **Fit:** the horizontal distance is ≤ radius + 50 for only 44% of hits, and ≤ radius + 100 for 78%.

**Verdict: usable as an approximate strike point, not as an exact collision test.** The likely reasons:
- The victim's hurtbox is not a point. It is probably about 60–100 u around PLAYER_MAT+0x30.
- Some moves have more than one sphere, and only the last one is stored here.

For obs, I recommend:
- Encode the bot-relative centre (dx, dy, dz), the radius, and a live flag (+0x124 byte1).
- Do not rely on "distance < radius" as a hit predictor. If a scalar is needed, use distance −
  (radius + ~80) as a soft margin.
