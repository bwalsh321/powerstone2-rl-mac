# Projectile blind spots: the object ledger is the source of truth

Oct 4 2026, instance 4. Nothing outside `re/projectiles/` was changed and nothing was committed.
The proposed scanner is in `proposed_ledger_threats.py`. It is a separate file and does not edit `ps2_ram.py`.

## TL;DR
1. **Pool class whitelists do not carry across lineups.** The pool word at +0x3C is a model-data address,
   and it moves when the lineup changes. Falcon's missile body is `0x0C7FABC8` in the slot3 lineup and
   `0x0C808BC8` when Ayame and Gunrock are loaded (Δ = +0xE000). The v2 "rocket" `0x0C7F9A10` becomes
   `0x0C807A10`. With other characters loaded, the `0x0C7Exxxx` band that ps2_addr credits to Pride
   holds **Ayame's shurikens**. So `PROJ_CLASSES`, `PROJ_EXCLUDE` and the comments that credit classes
   to characters are only valid for the slot3 lineup (Pride/Falcon/Ryoma/Accel). On lv8mix mixed-arena
   states they are partly wrong. `PROJ_EXCLUDE` 0x0C7FABC8, labelled "explosion", is in fact the
   **missile body** in that lineup (2,137 co-located frames with the ledger missile object).
   (Evidence: `tools/b5_poolvar.py`, `tools/b4_pride.py`.)
2. **The ledger has the real game objects.** Each slot sits at 0x8C4FBD30 + k·0x430. The word at +0x08 is
   a behaviour vtable, which is a code address and therefore stable across every lineup and seat. The low
   byte of the header at +0x04 is a category, and **category 1 means a live hit volume**: every special,
   super, projectile, item bullet and explosion we saw. The game's own hit-source pointer
   (PLAYER_MAT+0x32E4) points at these slots (slot+4) for every non-melee hit. No class whitelist is needed.
3. **Coverage, measured against the game's own hit attribution** over 6 lineups and about 50k frames:
   - **Category-1 hits** (n=499):
     - The proposed rule had already reported the exact source object in the 6 frames before the hit
       for **79.6%** of them.
     - The other 20.4% are point-blank spawns: the hit volume was created on the hit frame itself
       (spawn→hit gap = 0 for all 103 misses), so no object-based reader could have warned earlier.
     - A replica of the current v3 pool rule had *anything* within 200 u of the victim in that window
       for 50.3%; the proposed rule managed 74.9% on that same measure.
   - **Thrown or knocked objects** (category 9, moving, n=21): 81.0% exact for the proposed rule versus
     0% for v3. The 0x0C6 band exclusion hides them all in v3.
   - **Frames with at least one threat reported**: 30.5% (proposed) versus 18.4% (v3).
   - **Cost**: 0.16 ms median per sweep in Python (live smoke, `tools/d3_live.py`).
4. **Answers to the open items:**
   - (b) X-pattern beam and (c) gatling trail are both **Accel** ledger objects: `0x0C143118` (beam, about
     200 frames) and `0x0C143608` (bullets, 2,400 u/s, 1–7 frames). They are not pool movers, which fits
     HANDOFF.
   - (d) Missile swarms are `0x0C122FEC`, **shared by Falcon and Pride**, with one object per missile.
   - (a) Thrown items and props are category-9 objects in flight (see below).
   - (e) The class table below covers 13 of 14 characters plus the item weapons.
   - (f) For melee there is an exact "attack window open" flag plus a move descriptor. A geometric
     hitbox radius was not found.

## Ledger slot layout (offsets from the slot base)
| off | type | meaning | evidence |
|---|---|---|---|
| +0x04 | u32 | low byte = category: **1 hit volume**, 2 = small ground-mover set, 5 = effects, 7/8 = system, 9 = stage objects (items, chests, loose stones, throwable props), 0 = free. The upper bytes vary (list position). | `a2_life.py`: every damage-dealing class is category 1 except held swings and thrown objects (category 9) |
| +0x08 | u32 | behaviour vtable = class id, lineup-independent | Falcon `0x0C122FEC` in lineups A, D, E, F at seats 1 and 2 |
| +0x0C / +0x10 | ptr | category-list prev/next (pointer = slot+4) | `a5_parent.py` |
| +0x14 | ptr | **parent**: a player object ([PLAYER_MAT−0x490, +0x3938)) or another ledger object. Follow it, as Gourmand's pot → `0x0C13B906` → Gourmand does. Items and some summons have 0 here. | `a6_owner.py`; matches the Sep 29 "+0x10 of the pointed-to object" (that pointer is slot+4) |
| +0x2C/30/34 | f32 | position x, y, z | — |
| +0x50/54/58 | f32 | **velocity in units per frame** (×60 = u/s). Exact (0.0 median error) for category 1, items, props and loose stones. **It is not cleared when a prop respawns**, so the scanner gates on observed motion. | `b8_fields.py`, `c5_h9vel.py`, `c9_cactus.py` |
| +0x44/48/4C | f32 | scale (1,1,1) | — |
| +0x19C | f32 | **hit radius candidate**. Values: missile 10, Accel bullet 50, Gunrock boulder 20 (and +0x1BC 180), Ryoma big pillar 275, Wang-Tang wave 187, Pete blade 400, item blast 140 (grows over time). Several classes read 0 here. | `b9_radius.py` on full-slot captures; medium confidence |
| +0x1BC | f32 | second extent candidate (30–190) | same |

Ledger slots that were live ran from about k=8 to k=130. Scan k = 0..149.

## Class table: category-1 hit volumes (all captures; `tools/d4_table.py`)
- **Lineups:**
  - A = Pride/Falcon/Ryoma/Accel
  - B = Wang-Tang/Galuda/Rouge/Jack
  - C = Pete/Julia/Gourmand/Mel
  - D = Ayame/Gunrock/Falcon/Pride
  - E = Pride/Rouge/Pete/Wang-Tang
  - F = Julia/Pride/Rouge/Galuda
- All lineups are desert, lv8, all-COM, health refilled every 240 frames.
- **Owner** comes from the +0x14 chain; "-" means unowned.
- **Labels** were confirmed on contact sheets (`shots/cat1/sheet00-09.jpg`) when a name is given. Pete
  versus Julia was split by lineup (the class appears in C and E but not F, so it is Pete's).
- **Conf** = high when there are 10 or more instances plus attributed hits.
- "Light pillar" and "pink flyer" were only seen in lineup C, and nobody owns them. The vtable range
  points to Pete's code block, but this is not confirmed.

| vtable | label | owner (resolved via +0x14) | lineups | n | life med/max (f) | speed med/max (u/s) | radius +0x19C | hits / dmg | conf |
|---|---|---|---|---|---|---|---|---|---|
| `0x0c122fec` | missile (Falcon PF swarm / Pride rocket swarm) | Falcon 120, Pride 96 | ADEF | 216 | 43/145 | 1200/2100 | 10 | 29 / 2056 | high |
| `0x0c139010` | Pete toy soldiers | - 187 | CE | 187 | 24/156 | 3600/3600 | 0 (+0x1BC 50) | 24 / 157 | high |
| `0x0c12cf48` | Gunrock rocks | Gunrock 175 | D | 175 | 9/15 | 1800/3600 | 0 | 1 / 7 | high |
| `0x0c132d70` | Rouge | Rouge 91 | E | 91 | 41/41 | 1206/2400 |  | 79 / 994 | high |
| `0x0c162dac` | item gun bullet | - 75 | ABCDEF | 75 | 7/50 | 2400/2400 | 10 | 31 / 207 | high |
| `0x0c143608` | Accel gatling bullet | Accel 63 | A | 63 | 7/59 | 2400/2400 | 50 | 34 / 425 | high |
| `0x0c16b9d2` | item | - 57 | BEF | 57 | 15/241 | 900/900 | 0 | 11 / 365 | high |
| `0x0c136ab4` | light pillar (Pete? C only) | - 43 | C | 43 | 19/19 | 0/0 |  | 24 / 231 | high |
| `0x0c136ff4` | light pillar (Pete? C only) | - 43 | C | 43 | 43/43 | 0/0 |  | 0 / 0 | med |
| `0x0c12da56` | Gunrock shockwave | Gunrock 42 | D | 42 | 45/46 | 1380/2760 | 0 (+0x1BC 180) | 6 / 203 | high |
| `0x0c12fb0a` | Ayame shuriken | Ayame 40 | D | 40 | 52/88 | 1800/1800 |  | 37 / 329 | high |
| `0x0c16bf02` | item | - 35 | E | 35 | 62/62 | 600/600 | 18~ | 2 / 61 | high |
| `0x0c163514` | item flame | - 31 | BF | 31 | 30/30 | 872/1741 |  | 24 / 110 | high |
| `0x0c1682b0` | item ray shot | - 27 | AD | 27 | 2/44 | 1200/1200 | 20~ | 6 / 249 | high |
| `0x0c14d830` | Mel (card wall) | Mel 24 | C | 24 | 60/60 | 0/0 |  | 6 / 111 | high |
| `0x0c143118` | Accel beam (the X-pattern beam) | Accel 20 | A | 20 | 198/258 | 1620/1782 |  | 27 / 213 | high |
| `0x0c12e7d0` | Galuda wing beam | Galuda 20 | BF | 20 | 65/107 | 2400/4260 |  | 8 / 129 | high |
| `0x0c163144` | item blast | - 19 | ABCDEF | 19 | 16/16 | 0/0 | 140~ | 11 / 176 | high |
| `0x0c13eacc` | Gourmand pot/pig (velocity field unreliable) | Gourmand 18 (via `0x0c13b906`) | C | 18 | 277/292 | (teleports) |  | 8 / 263 | high |
| `0x0c12b034` | Jack knives / magic circle | Jack 16 | B | 16 | 124/126 | 4230/4680 |  | 14 / 204 | high |
| `0x0c130640` | Ayame dash beam | Ayame 16 | D | 16 | 54/68 | 1800/1800 |  | 3 / 72 | high |
| `0x0c129c70` | Wang-Tang shot | Wang-Tang 14 | BE | 14 | 48/80 | 3000/3000 | 9 | 18 / 210 | high |
| `0x0c13d28a` | Gourmand | Gourmand 14 | C | 14 | 40/46 | 1200/1200 |  | 1 / 11 | high |
| `0x0c13a36c` | Pete | - 14 | CE | 14 | 18/52 | 919/1200 | 15 | 9 / 198 | high |
| `0x0c13831c` | pink flyer (C only) | - 12 | C | 12 | 88/160 | 1027/1331 |  | 2 / 49 | high |
| `0x0c12360c` | Pride | Pride 12 | EF | 12 | 62/122 | 0/0 | 0 | 0 / 0 | med |
| `0x0c1638b4` | item fire (ground) | - 10 | BE | 10 | 199/199 | 120/1080 | 45~ | 0 / 0 | med |
| `0x0c16906c` | item hammer/swing | - 9 | BCD | 9 | 92/92 | 1200/1200 | 134~ | 6 / 230 | med |
| `0x0c13a79e` / `0x0c13ac58` / `0x0c13a990` | Pete | - 7 each | CE | 21 | 21–42 | 0–480 |  | 0 / 0 | med |
| `0x0c128a18` | Wang-Tang slash wave | Wang-Tang 6 | BE | 6 | 31/31 | 0/0 | 187~ | 10 / 195 | med |
| `0x0c1351ca` / `0x0c1357ee` | Rouge | Rouge 5 / 4 | E | 9 | 12–42 | 6–3000 |  | 7 / 86 | med |
| `0x0c14e224` | Pride | Pride 5 | EF | 5 | 38/38 | 2880/2880 | 36~ | 2 / 66 | med |
| `0x0c163f9e` | item | - 5 | F | 5 | 16/19 | 1200/1200 |  | 6 / 177 | med |
| `0x0c127448` | Ryoma sky pillar | Ryoma 4 | A | 4 | 18/18 | 0/0 | 75~ | 5 / 29 | med |
| `0x0c12212c` | Falcon shot (= old pool "rocket" 0x0C7F9A10 in lineup A) | Falcon 4 | AD | 4 | 75/136 | 1200/1200 | 10 | 1 / 25 | med |
| `0x0c162fd0` | item explosion | - 4 | DE | 4 | 10/21 | 1200/1200 | 20 | 3 / 45 | med |
| `0x0c140cc0` | Julia | Julia 4 | F | 4 | 17/31 | 1200/1200 |  | 4 / 80 | med |
| `0x0c137cb4` | Pete energy blade | - 3 | CE | 3 | 163/163 | 0/0 | 400 | 31 / 566 | low (n) |
| `0x0c1392d8` | Pete | - 3 | CE | 3 | 162 | 0 | 0 (+0x1BC 190) | 0 / 0 | low |
| `0x0c128112` | Ryoma big pillar (unowned) | - 2 | A | 2 | 15/15 | 0/0 | 275~ | 4 / 264 | low (n) |
| `0x0c12c8d0` | Gunrock boulder | Gunrock 2 | D | 2 | 25/29 | 2400/2400 | 20~ (+0x1BC 180) | 4 / 197 | low (n) |
| `0x0c13b906` / `0x0c13d04c` | Gourmand | Gourmand | C | 3 | — | — |  | 0 | low |
| `0x0c129fa2` | Wang-Tang | Wang-Tang 1 | E | 1 | 44 | 3000 |  | 1 / 24 | low |

The vtables cluster by character: 0x0C122–0x0C125 Falcon (and the shared missile), 0x0C127–0x0C128 Ryoma,
0x0C128–0x0C129 Wang-Tang, 0x0C12A–B Jack, 0x0C12C–D Gunrock, 0x0C12E–F Galuda, 0x0C12F–0x0C132 Ayame,
0x0C132–0x0C135 Rouge, 0x0C136–0x0C13A Pete, 0x0C13B–0x0C13E Gourmand, 0x0C140 Julia, 0x0C141–0x0C143
Accel, 0x0C14D–E Mel/Pride, 0x0C15x common effects (category 5), 0x0C162–0x0C16C item weapons.
**Gaps:** Julia (4 instances) and Pride's own special (`0x0C12360C`/`0x0C14E224`, few instances) are
thin. The scanner does not need them listed, because category 1 is generic. Labels only matter for analysis.

## (a) Thrown items and props
These are category-9 objects (the same family as the existing `STONE_OBJ_MODE` ledger scan).
- **`0x0C0F1688`** is a throwable desert prop: the cactus. ps2_addr calls it a "static spawner"; it is in
  fact thrown and hits for 40–55. There are 8 per desert stage.
- **`0x0C0F18D4`** is a big prop (pole or log) swung as a weapon.
- **`0x0C0C9810`** (ps2_addr: "falling chest") is really the generic item/chest object. It flies when
  thrown (B f35 at 3,600 u/s, C f6101 at 2,400 u/s), and also when it is a held-weapon swing source.
- **`0x0C0CA928` / `0x0C0C9F50` / `0x0C0CA5D8`** are other item objects.
- Category 2 **`0x0C16DBD4`** is a ground-crawling item (10 hits, 750 u/s).

**Rule** (implemented in `LedgerThreatScanner`): category 9, or category 2 with vtable `0x0C16DBD4`,
excluding the loose stone, resting chest and absorb arc. All of the following must hold:
- the +0x50 speed is at least 600 u/s (300 u/s for category 2);
- the horizontal speed is at least 300 u/s;
- the **observed** position change since the last sweep agrees with +0x50 (this kills stale velocity
  after a respawn, which had produced 200-frame phantom flights);
- the object is not "held", meaning within 120 u of a fighter and moving within 300 u/s of that fighter.

Result on the captures:
- Thrown-cactus flight runs average 11 frames, and 16 of 26 end in a hit.
- 81% of hits from moving category-9 objects were pre-reported.
- The remaining category-9 hit sources are **static**. They are held-weapon swings: the source is the
  item object in the swinger's hand, 64 of them. Those belong to the melee channel, not the projectile one.

**Stage caveat:** prop vtables are desert-specific. lv8mix uses mixed arenas, so other stages' props
will appear as unlabelled category-9 movers. The rule is generic (no whitelist), but the held/stale
gates were only validated on desert.

## (f) Melee
Player object = PLAYER_MAT[k] − 0x490.

| off | type | meaning |
|---|---|---|
| +0x134 | u8 | move id while a melee attack window is open; 0 otherwise |
| +0x414 | u32 | pointer to the move's attack descriptor while the window is open; 0 otherwise. Descriptors are 0x14-byte entries in per-character tables (Falcon 0x8C27C544…, Pride 0x8C283B78…, Ryoma 0x8C27Dxxx, Accel 0x8C2826EC). They advance by 0x14 per combo hit. |

What the flag shows:
- 40/40 melee hits (the hit source is a player object) landed inside the attacker's window.
- The hit typically landed at **frame 7 of the window**, so the flag gives about 7 frames of warning
  (`tools/c1_melee.py`–`c3_melee3.py`, cap/Afull pobj).
- The window covers about half of attack-state frames (7/8/26), including multi-hit combos.
- The descriptor holds byte fields, not floats. +2 looks like a damage value (25/30/45…) but is unverified.

**What was not found:** a hitbox radius or volume. Hitbox spheres are probably bone-attached tables
elsewhere. The flag and descriptor are the practical "hitbox active" signal.

## Proposed obs v4 (`obs_block()` in `proposed_ledger_threats.py`)
- **Replace** the v3 projectile slots with **3 nearest enemy ledger threats**, 9 dims each. Own threats
  (owner == bot seat) are dropped.
  - dims: dx/2000, dy/1000, dz/2000 (bot-relative), vx, vy, vz /3000, radius/300 (+0x19C, 0 if unknown),
    is_thrown, present.
  - Total: 27 dims, versus 3×4 today.
- **Add per opponent:** melee_active (+0x414 != 0), frames since the window opened (/30), and descriptor
  byte +2 /64. That is 3 dims × 3 opponents = 9.
- **Optional:** a count of enemy threats within 600 u (/5) as a crowd signal for volleys. Pete's soldiers
  and missile swarms are 6–15 objects, which overflow the 3 slots.
- **Ordering and consistency:** the threats are nearest-first, as v3 does; the owner can be dropped. The
  scanner is stateless apart from one previous sweep, so the reader keeps its 3-frame cadence.
- **Compatibility:** v2/v3 policies keep their prefix contracts if the new block is appended. It must not
  replace the v3 slots for older pool seats. Use the same `_legacy_proj` pattern as the v3 cutover.

## Reproduce
- **Build states.** `bash tools/mk_lineups.sh` builds all-COM lineups from `work/cc_slot3.state`
  (slot3 → 2P pause → CHANGE CHARACTER). The navigation is in `tools/lineup.py`:
  - A cycles a column forward and B backward through: Ryoma, Wang-Tang, Galuda, Rouge, Jack, Pete, Julia,
    Gourmand, Accel, Mel, Pride, RANDOM, Falcon, Ayame, Gunrock.
  - A on the HUMAN row cycles HUMAN → COM → NO ENTRY.
  - Lineups E and F were made with direct `lineup.py` calls.
- **Capture.** `tools/cap.py --load work/lineupX_live.state --out cap/X --frames 7200` records per frame:
  hp, state, position, hit source, pool, and ledger bytes 0..0x100 (trimmed to 0x60 on disk).
  `--lb 1072 --pobj` gives full slots and player objects (`cap/Afull`).
- **Analysis.** In `tools/`:
  - `a1` hit census, `a2` lifetimes, `a3`/`a5`/`a6` owners, `a4` sheets, `a7`/`a9` hit and flight tiles
  - `b3`/`b5` pool↔ledger links, `b8`/`b9` fields and radius, `c1`–`c4` melee
  - `c6_validate.py` coverage versus v3, `d3_live.py` live smoke, `d4_table.py` this table
- **Disk.** Screenshot dumps and raw RAM were deleted to save space. The contact sheets in `shots/` are
  what was reviewed.

## Not done / next
- **Live A/B:** wire the scanner into the reader behind a flag and run obs_overlay on lv8mix states.
  Mixed arenas need the category-9 gates re-checked on each stage.
- **Missing classes:** Julia, Pride and Mel specials need more samples. Pete versus Julia for the C-only
  pillars needs a Pete-only capture.
- **Radius:** confirm +0x19C, for example by checking whether hit distance ≤ radius + fighter radius.
- **Earlier:** `ps2_addr.py`'s pool class comments, `PROJ_CLASSES` and `PROJ_EXCLUDE` should be
  documented as lineup-specific, whether or not v4 is adopted.
