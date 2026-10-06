# Power Stone 2: per-player state machine and match globals

All addresses are guest addresses (`0x8C......`). Pointers stored in RAM use the `0x0C......` alias (same byte = `addr & 0xFFFFFF`).
Everything here was measured on flycast libretro, instance 3, from `states/slot1|2|3.state` (all three are the desert stage).
Scripts and raw outputs are all in this folder. Confidence levels:
- **CONFIRMED**: a controlled experiment plus census statistics agree.
- **LIKELY**: consistent evidence, no causal test.
- **GUESS**: plausible, thin evidence.

## 0. The player struct (the key finding)

```
P_k = 0x8C532498 + k * 0x3938            (k = 0..3)
    = PLAYER_MAT[k] - 0x490 = HEALTH_OBJ[k] - 0x160 = GEMS F_anchor[k] - 0x3718
```
The game's SH-4 code hard-codes `0x0C532498` (about 400 literal-pool references; `out_*`/E2 pointer scan), so this is the real object base. P+0x08/+0x0C/+0x10 are list links to the other seats' structs.
Offsets the project already knows, written relative to P: state byte `PSTATE_OFF` = P+0x3715; stun `PSTUN_OFF` = P+0x3822; `HEALTH_OBJ` = P+0x160; render matrix = P+0x490; F anchor = P+0x3718 (gems P+0x374D, meter P+0x37B8, item ptr P+0x376C). All of these match my measurements.

## 1. Per-player field table

| Offset | Type | Meaning | Conf. | Evidence |
|---|---|---|---|---|
| +0x0001 | u8 | seat index 0..3 | CONFIRMED | e12 header dump (`out_e12_header.txt`) |
| +0x0002 | u8 | **character id**: 0 Falcon, 1 Ryoma, 2 Wang-Tang, 3 Jack, 4 Gunrock, 5 Galuda, 6 Ayame, 7 Rouge, 8 Pete, 9 Gourmand, 10 Julia, 11 Accel, 14 Mel, 15 Pride (12/13 never selectable, probably bosses) | CONFIRMED (all 14) | menu cycle with portraits (`shots/cc_strip.png`, `out_t_charcycle.log`); every built match has P+2 == seat-table id (`out_e17_mkchars.txt`) |
| +0x0014 | u32 | hit sub-phase: 0x010101 → 0x020101 → 0x030101 during a flinch | GUESS | e6 |
| +0x001C | u32 | short action timer (counts down, e.g. 10..0 after a grab; 8..0 after hit-stun) | GUESS | e6 |
| +0x0028 | f32×3 | **logical world position** x,y,z. y = 0 on the floor. This is not the render-matrix translation, which adds about 85 u of hip offset plus animation bob | CONFIRMED | e3 (`out_e3_jump.txt`) |
| +0x0038 | u16 | **facing angle** (65536 = 360°). Forward unit vector in (x,z) = (sin a, cos a) | CONFIRMED | e1/e3 rotation steps of 0x400 per frame; t_reader: facing matches the velocity direction for all 4 seats |
| +0x004C | f32×3 | **velocity** vx, vy, vz in units/frame (×60 gives u/s; run ≈ 7.2 u/f ≈ 430 u/s) | CONFIRMED with caveats (below) | e3, e4 full-RAM gravity ramp, census (`out_census_velocity.txt`) |
| +0x0058 | f32×3 | acceleration. ay = -1.2 while airborne (gravity), 0 on the ground. ax/az are braking deceleration | CONFIRMED | e1, e3 |
| +0x0064 | f32 4×4 | logic orientation matrix. r0 = (cos a, 0, -sin a); translation at +0x94 (copy of pos) | CONFIRMED | e3 dump |
| +0x0124 | u32 | attack flag: byte1 ≠ 0 while a melee hitbox is live (0x201 punch, 0x401 kick). It is **also** set in states 14/15/32 with no hit sphere (about 4% of frames), so use the sphere count in §1b instead | superseded | `out_e19b_multisphere.txt`: sphere count > 0 implies flag 100%, flag without spheres 2.2–2.4k frames |
| +0x012C | u32 | **hurtbox mask**: low u16 == 0 means the player cannot be hit; 0xFFFF means hittable. 0 for the whole held state (34), from landing after a throw through knockdown (14), getting up (15) and power change (25) | CONFIRMED (timing) | e11 sweep: a punch whiffs through every frame with 0x0000 and lands on the first frame it flips to 0xFFFF (`out_e11_invuln_sweep.log`). Census table in `out_census_hurtbox.txt` |
| +0x0130 | u32 | hit-stop counter: 0x106→0x100 on the attacker and 0x10006→0x10000 on the victim (6 frames) | LIKELY | e6 |
| +0x0134 | u32 | flags. **bit 0x400 = grounded** (clear means airborne); low nibble = attack kind (1 punch, 5 kick…); bit 0x10000 = the attack connected | CONFIRMED (grounded bit) | `out_census_airborne.txt`: matches y > 2 on 98.9–99.8% of 26k×4 frames |
| +0x0160 | f32 | health (= HEALTH_OBJ) | CONFIRMED | |
| +0x0184… | records | **collision list**: hurt cylinder plus live hit spheres, see §1b | CONFIRMED | §1b |
| +0x0404 | u32 | floor-collision pointer (0 when airborne). Worse than the 0x134 bit (93% agreement) | LIKELY | census |
| +0x0414 | u32 | attack-data pointer, set at the start of some attacks (0x0C27C544 punch, 0x0C27C594 kick) | GUESS | only 44% of state-7 frames |
| +0x3714 | u32 | byte0 = 01; **byte1 = state byte (+0x3715)**; byte2 = previous state (+0x3716); byte3 = 0x63 | CONFIRMED | |
| +0x3720 | u8 | **COM flag**: 1 = COM, 0 = human | CONFIRMED | constant for every seat across slots 1/2/3 and 26k census frames |
| +0x3770 | u32 | **partner pointer**. For humans it is set **only** in grab/hold states (0 holding overhead, 11, 12, 33, 34) and points to the other player. For COMs it is also set outside grabs and points to another player, which is most likely the AI's current target | CONFIRMED (grab) / LIKELY (COM target) | 100% of state-34 and 11/12 frames point to a player (1.3k frames, `out_e19c_partner_hurt.txt`); human-vs-human E18: set only in states 0/11/33/34 (`out_e18_partner_human.txt`) |
| +0x3774 | u32 | **last melee attacker**'s struct pointer. Projectile and object damage does not set it to a player in 91% of cases | CONFIRMED | 166/166 sphere-attributed melee hits in 4P fights (`out_e19c_partner_hurt.txt`) |
| +0x3818 | u16 | **action / animation id** (the u16 at +0x381A is a copy). Much finer than the state byte; see §3 | CONFIRMED | all scenarios |
| +0x38CC | u32 | motion-script pointer for the current act (0 when idle); +0x38D0 = script step | LIKELY | e6 |

**Velocity caveats** (`out_census_velocity.txt`, s3a):
- `vy` (+0x50) is exact in the air: Δy equals vy on 93–96% of frames, with the expected -1.2/frame gravity ramp.
- On the ground, horizontal (vx,vz) equals the position delta on 90% of run frames and about 96% of idle frames.
- During a running jump the horizontal motion is **not** in +0x4C. +0x4C keeps only the air-steer part (±0.57). The carried run momentum (7.0 × facing) is applied from somewhere I did not find; the char run-speed constant 7.0 sits at P+0x4DC.
- During attacks and throws, root motion moves the player without using +0x4C.

Recommended observation: `v = (pos[t]-pos[t-1])` horizontally (what the env does now) **plus** `vy = P+0x50` directly. +0x4C/+0x54 is still the right "intended movement" signal for opponents who are running.

## 1b. Collision records: hurt cylinder and melee hit spheres (round 2)

Records are 0x20 bytes each, starting at **P+0x184**. The record count is **byte3 of the word at P+0x184** (u8 at P+0x187).
- **Record 0 = hurt cylinder** (header 0x??FF0206):
  - centre x, y, z at P+0x18C / P+0x190 / P+0x194, radius at P+0x198, half-height at P+0x19C.
  - The centre equals pos + (0, half-height, 0) on 99.8% of frames, and x/z equal pos on 99.1–99.6%.
  - The size depends on character and state. Standing Falcon is r 60 / h 85. Knocked down (14) is about h 30, getting up (15) about h 55, pole hang (35) r 30, a power special (26) up to r 67 / h 95.
- **Records 1..count-1 = live melee hit spheres.**
  - Header = bone << 16 | 1.
  - x, y, z at +8 / +0xC / +0x10 and radius at +0x14. The first sphere is at P+0x1AC, the next at P+0x1CC, P+0x1EC, ….
  - Up to 4 spheres were seen at once (Power specials); 1 for normal moves.
  - Records past the count are stale and must be ignored.
- **Hitbox live** = count > 1 (i.e. `u8[P+0x187] > 1`).
- **Contact test** (reproduces the game's damage decision): for some sphere, `hypot(x-cx, z-cz) <= r + R and |y - cy| <= r + H`, and the victim's hurt mask P+0x12C low u16 ≠ 0.

| Validation | Precision | Recall | Notes |
|---|---|---|---|
| E18 controlled: all **14 characters** × punch, 3-hit combo, kick, air punch, air kick, dash punch, dash kick × 5 distances vs an idle Falcon (`an_e18b.py`, `out_e18b_multisphere.txt`) | **1.000** (0 FP / 407) | **0.978** | All 9 FN are air kicks (jb). 457/466 damage events had a live sphere; the 9 others are grab-type air moves (Accel act 0x206, Ayame act 0x211) that deal damage through the grab path |
| E18 timing | | | damage lands on the **first** live frame in 84% of windows (350/416), within 2 frames in 94%. Median active window: 11 frames for punches, 13 for kicks, 10 for dash punches; hitstop freezes the sphere |
| E19 4P COM fights, slot2 + slot3, 2×15k frames (`out_e19b_multisphere.txt`) | 1.000 / 0.989 | 0.63 / 0.85 at window level | Almost every FN has the attacker's sphere 3–20× its reach away from the victim (`FN=1 an_e19b.py`), so the damage came from a simultaneous projectile/object, not a missed melee hit. Of all damage events, 23/157 and 143/276 are melee; the rest (about 121 per run) have no live sphere anywhere, i.e. projectiles, thrown objects or stage |
| Power specials (state 26), e19 + e21 + e21b (4×40k frames) | 0.98 (157/161) | 0.96 (157/164) | `out_e21_items_pole_special.txt`, `out_e21b_items_long.txt`; sphere radii up to 224 |
| Pole swings (state 35 → 7, acts 0x208–0x20f / 0x21f), e21 + e21b | 0.98 (86/88) | 0.86 (86/100) | some FN are likely damage from another source landing in the window |
| Held-item melee swings (state 7/8 with item ptr ≠ 0) | 1/1 | 1/1 | **not verified**: only 9 windows in 190k frames, since COMs mostly throw or fire items (state 8 → projectile objects). The item swing uses the same sphere list (radii 42/60 seen) |

**Threat feature for the bot**, per opponent k: the sphere nearest to *my* hurt cylinder gives
- (dx, dy, dz) = sphere centre minus my hurt centre;
- r = sphere radius;
- margin = max(horizontal gap − (r+R), |dy| − (r+H)); ≤ 0 means contact;
- frames active (from `HitboxClock`).

`threat_features()` in `player_state_reader.py` computes it.

## 2. State byte P+0x3715: full enum (all seen values)

Durations come from the three census runs (26k frames × 4 seats, COM lv3 and lv8, 6 characters) in `out_census_*_states.txt`. "dur" is the median/p90 length of an episode in frames. Names come from controlled scenarios (`out_moves_far.txt`, `out_moves_grab.txt`, scen RLE) and full-res screenshots under `shots/`.

| val | name | dur (med/p90) | air? | how established |
|---|---|---|---|---|
| 0 | idle (also idle while holding something overhead, act 0x211) | 1/4 (often 1-frame transitions) | no | CONFIRMED |
| 1 | run (also run while carrying: act 0x218/0x219) | 20/162 | no | CONFIRMED |
| 2 | brake / stop skid | 12/25 | no | CONFIRMED (release after run) |
| 4 | jump squat | 4 | no | CONFIRMED (A press: s4 for 2 frames → s5) |
| 5 | airborne (jump rising/falling) | 48/54 | yes | CONFIRMED |
| 6 | landing | 4 | no | CONFIRMED |
| 7 | **melee attack**: ground punch (act 0x100–0x102 combo), kick 0x106, air punch 0x115, air kick/dive 0x203–0x207, pole-swing kicks 0x209–0x20b/0x21f, item swings 0x3a0/0x3b2 | 39–48 / 60–82 | 12–15% | CONFIRMED |
| 8 | use item / throw a carried object / fire a weapon (acts 0x202, 0x3xx) | 28–34 / 56–89 | 4–42% | LIKELY |
| 9 | grab attempt (B near or far) | 10 | no | CONFIRMED (g_b_*) |
| 10 | pick up an object or item (acts 0x210, 0x301, 0x323, 0x349…) | 18–24 / 25 | no | LIKELY (item ptr becomes non-zero) |
| 11 | grab success, lifting the opponent | 24 | no | CONFIRMED |
| 12 | throw the held player | 36 | no | CONFIRMED |
| 14 | knocked down, lying | 11 / 13 | no | CONFIRMED (invulnerable) |
| 15 | getting up | 23–30 / 85 | no | CONFIRMED (invulnerable; long tail is a rolling get-up, act 0x43d) |
| 16 | hit recovery / launched (control returning, often high in the air: act 0x43c) | 8–32 / 53 | 93% | CONFIRMED (follows 32) |
| 19 | entry pose at round start (act 0x601) | – | no | LIKELY (frame 0 of a state only) |
| 25 | **Power Change** (transform animation, act 0x607) | 59 (fixed) | no | CONFIRMED (form flag goes up; invulnerable) |
| 26 | **Power special in progress** (transformed super, act 0x10e/0x11x) | 44–72 / 205–251 | 22% | CONFIRMED (hits come from projectiles while in 26) |
| 30 | short airborne state, act 0x8, followed by holding an item (catching an item in the air?) | 16–26 | yes | GUESS |
| 32 | **hit reel / thrown / knocked back** (acts 0x400–0x45x) | 45–74 / 162–170 | 42–68% | CONFIRMED |
| 33 | follow-through after a pole kick or object interaction, with partner pointer set (acts 0x20c, 0x211, 0x392) | 81–100 / 110 | partly | GUESS |
| 34 | **held by an opponent** (grabbed or carried overhead; acts 0x51b/0x521/0x526/0x52c) | 65 / 97 | partly | CONFIRMED (invulnerable; hurt mask hi u16 also 0) |
| 35 | **pole grab**: hanging on a pole or cactus (act 0x208); usually 1 frame, then state 7 pole-swing kick | 1 / 26 | yes | CONFIRMED by screenshot (`shots/census_s2b/s_0023_1_f3007_P2.png`, Falcon on the cactus) |
| 36 | guard with an item (Ryoma behind a large shield/umbrella item; acts 0x345/0x346) | 41 | no | GUESS (`shots/census_s3a/a_0346_1_f5998_P3.png`) |

Never observed in about 100k player-frames: 3, 13, 17, 18, 20–24, 27–29, 31. **There is no general block/guard state**; Power Stone 2 has no guard button. Item guard (36) is the only one. There is also no separate dash state: "run" (1) is the dash.

Typical sequences (frame counts from controlled runs):
- **Jump**: 0(1) → 4(2) → 5(≈49) → 6(4) → 0.
- **Punch whiff**: 7 for 28 frames. The hitbox is live on frames 8–12 (startup 7, active 5, recovery 16).
- **Kick whiff** (B or Y far from anyone): 7 for 48 frames. Hitbox live on frames 10–13.
- **Grab + throw**: attacker 9(10) → 11(24) → 0 holding (act 0x211) → 12(36) → 0. Victim 34(46) → 32 thrown(≈112) → 14(12) → 15(30) → 0. The victim is invulnerable from the grab until the end of 15.
- **Punch hit**: victim 32 for about 20 frames (act 0x400→0x401→0x402), then 16 for 8 frames, then 0. Hitstop is 6 frames.
- **Air kick hit**: victim 32 for about 100 frames → 14 → 15 → 0.

## 3. Action id P+0x3818: structure

The high byte is a category:
- 0x00: locomotion. 0 idle/run, 4/5 run-start/run, 6 brake, 7 jump squat, 8 rise, 9/0xb fall, 0xa land.
- 0x01: melee and specials. 0x100–0x102 punch chain, 0x106 kick, 0x108 dash attack, 0x115 air punch, 0x10e/0x11x power specials.
- 0x02: carry and poles. 0x202 throw, 0x203–0x207 air attack, 0x208–0x20f / 0x21f pole, 0x210 lift, 0x211 hold, 0x213–0x215 carry-jump, 0x218/0x219 carry-walk, 0x21a carry-brake.
- 0x03: hand-held item / weapon actions. The range depends on the item: 0x30x, 0x31x–0x33x, 0x34x, 0x36x, 0x38x–0x3bx, 0x3cx, 0x3ex.
- 0x04: damage. 0x400–0x408 flinch chain, 0x41x–0x43x reels and launches, 0x435/0x436 down, 0x437–0x43e getting up, 0x43c launched high.
- 0x05: grabs. 0x522 attempt, 0x519 lift, 0x51b/0x521/0x52x held.
- 0x06: 0x601 entry, 0x607 power change.

Full per-act table with state, held-item, partner and air percentages: `out_census_acts_all.txt`. Act ids are partly character-specific (low byte), but the category byte is universal.

**Attack phase** (what the bot needs to know about an opponent's attack):
- `startup` = state 7 and hitbox not yet live
- `active` = P+0x124 byte1 ≠ 0
- `recovery` = state 7 after the hitbox went dead

Median startup/active/recovery per move is in `out_census_attackptr.txt`, e.g. kick 0x106 = 9/4/35 frames.

The melee hitbox flag does **not** cover projectiles or thrown items. Those have their own objects; use the existing projectile channel.

## 4. Fusion / Power Change
- State 25 = transform animation: exactly 59 frames, invulnerable (hurt mask 0).
- State 26 = transformed special in progress, typically 44–72 frames and up to 250 for long specials. Acts 0x10e / 0x112–0x121.
- Form type = character id (P+0x0002); each character has one form. The form flag (F bit 0x10000) and meter (F+0xA0) are already in ps2_addr.
- Special-attack availability: I did not find a separate flag. The proxy is transformed and meter > 0 (GUESS).

## 5. Match globals

| Address | Type | Meaning | Conf. | Evidence |
|---|---|---|---|---|
| 0x8C475200 | u32 | **fight-live frame counter**. It increments once per frame only while the fight is live. It starts on "ACTION!" (slot1 frame 174, slot2 367, slot3 295; players can already move during READY), stops on the KO hit, and is frozen while paused. Not reset between rounds | CONFIRMED | e13, `out_e13_counters.txt`, `out_t_clock.log`, e15 |
| 0x8C46E1BB | u8 | 1 while a menu overlay is up (pause menu or post-match CONTINUE menu), else 0 | LIKELY | e14/e15 (`shots/e15_paused.png`) |
| 0x8C472DA8 + 0x14·k | 5×u32 | seat table: +0 type (**0 human, 1 COM, 2 empty**), +4 pad index, +8 character id, +0xC unknown (costume/variant?), +0x10 seat present | CONFIRMED (type, char, present) | `out_e12_globals_dump.txt` |
| 0x8C472AD4 | u8 | equals COM level − 1 on slot2 (lv3) / slot3 (lv8); reads 3 in menu-built matches. **Writing it changes nothing**: neither mid-match nor before stage select did any byte value change COM behaviour (identical attack/damage counts frame-for-frame). It is a settings copy, not the live difficulty. The live level was not found; no state with another level exists | REJECTED as live level | `out_e20_comlevel.txt`, `out_e20b_comlevel.txt`, `out_e20c_comlevel_menu.txt` |
| 0x8C472CF8 (mirror 0x8C46E198) | u32 | **stage area id**: 0 pirate ship, 1 castle garden, 3 iceberg, 4 space station, 5 desert. The Pharaoh Walker stage also reads 5; 0x8C472DD8 = 12 only on Pharaoh Walker | LIKELY (6 stages, 1 collision) | e16: 6 stages built from menu_stage.state; menus in `shots/menus_sheet.png` (`shots/e16_sheet.png`, `out_e16c_stage_globals.txt`); 5 on all three desert slot states |
| 0x8C472A7C | u32 | a seconds-like counter (+1 every 60 frames in some runs, frozen in others) | GUESS | e5 |

Not found:
- **Round timer**. There is no count-down anywhere in 0x8C470000–0x8C480000, and these versus matches seem to have no time limit.
- **A single "round phase" enum**. The full-RAM labelled diff (e14) found no clean byte. Use the counter instead: intro = not live and no KO; fighting = live; KO = health 0 and not live; results = menu flag.
- **Stage id**: see 0x8C472CF8 above. Only 6 of the stages were sampled, and Pharaoh Walker collides with desert.
- **KO / score count**. Not tested; matches here end at the first KO.

## 6. Proposed obs-v4 encoding

Per seat, for self and each opponent: 29 dims per seat, 116 for 4 seats.

| Feature | Dims | Encoding |
|---|---|---|
| state byte | 12 one-hot | groups: idle{0,19}, run{1,2}, air{4,5,6,30}, attack{7}, item-use{8,10,36}, grab{9,11,12}, held{34}, hit{32}, launched{16}, down{14,15}, pole{35,33}, power{25,26} |
| attack phase | 3 | startup / active / recovery (state 7/26 plus hit-sphere count > 0) |
| **threat** (opponents) | 6 | from the nearest live hit sphere: dx/300, dy/300, dz/300 (rotated into my frame), r/100, clip(margin/200, −1, 1), min(frames_active/20, 1). All 0 with a 'none' flag (+1 dim) when no sphere is live |
| hurt half-height | 1 | P+0x19C / 100 (tells standing / getting up / down) |
| invulnerable | 1 | (P+0x12C & 0xFFFF) == 0 |
| airborne | 1 | (P+0x134 & 0x400) == 0 |
| vy | 1 | P+0x50 / 30, clipped to ±1 (jump take-off ≈ 28 u/f) |
| v_h (opponents) | 2 | P+0x4C, P+0x54 / 8 (run ≈ 7.2). Rotate into the agent's frame if the env uses relative coordinates |
| facing | 2 | (sin a, cos a) from P+0x38. For opponents, also add dot(facing_opp, unit(me - opp)) ∈ [-1,1], i.e. "is he facing me" (1 extra dim) |
| stun | 1 | P+0x3822 / 40 (already in v3) |
| state age | 1 | frames since the state byte last changed / 60, clipped to 1. Tracked in the env |
| holding a player | 1 | partner pointer resolves to a seat (P+0x3770) while in states 0/11/12/33/34 |
| COM target is me | 1 | opponent is COM and its P+0x3770 points to my struct (LIKELY) |
| last hit me | 1 | my P+0x3774 points to this opponent |
| COM flag | 1 | P+0x3720 |
| character | – | P+0x0002 via a 6-dim hashed embedding (same trick as items), or omit if the training pool is Falcon-only |

Globals:
- fight_live (1 dim): from 0x8C475200 advancing.
- menu_open (1 dim): to mask garbage frames.
- stage area (5 one-hot), if training uses several stages.

## 7. Files
- `harness.py`: boot, load, record, teleport and poke helpers (instance 3). `run.sh` runs a script with boot-flake retry.
- `scen.py`: two-port scripted scenarios with per-frame struct capture plus state/act RLE.
- `e1`–`e21*.py`: experiments (see docstrings). Round 2: e16 stages, e17 per-character match states (cstates/, deleted after use), e18 hitbox validation × 14 characters, e19 4P compact census, e20 COM level poke tests, e21 items/poles/specials. `m_drive.py`: menu driver. Reproduce order: e16 (writes stage_*.state) → e16b/e16c; e17 (writes cstates/) → e18 → an_e18b; e19 → an_e19b/an_e19c. `e7_census.py`: 4P census with screenshots of the first occurrence of every state and act.
- `an_*.py`: analyses. `out_*.txt` / `out_*.log`: their outputs. `shots/`: screenshots.
- `player_state_reader.py`: ready-to-paste reader for `ps2_ram.PS2Ram`. Smoke tests: `t_reader.py` → `out_t_reader.log`; round 2 threat features `t_reader2.py` → `out_t_reader2.log`.
- Raw captures are deleted after analysis; only summaries (`out_*`) and the cited shots are kept.
