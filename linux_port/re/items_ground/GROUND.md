# Power Stone 2: ground items, chests, stage objects (guest-RAM RE)

Folder: `linux_port/re/items_ground/`. All scripts run headless on FlycastBridge **instance 2**:

```
cd linux_port; source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:.:re/items_ground
python re/items_ground/<script>.py ...
```

Confidence tags: **CONFIRMED** means a reproducible script, an output file and (where it applies) a screenshot. **LIKELY** means strong data with no direct visual or exhaustive check. **GUESS** is a label only.

---------------------------------------------------------------------------------------------

## 0. Headlines

1. **Every ground item, chest, loose stone and throwable stage prop is a record in the object arena** (the "ledger"). Records are 0x430 bytes on a grid at `0x8C4FBD30 + k*0x430`. Pickups are the records whose header byte `+0x04 == 9`. **CONFIRMED**
2. **`+0x420` (u8) is the object's TYPE ID.** Values: 1..121 are items in catalogue order (1 Gun, 2 Bazooka, 4 Hammer, 5 Sword, 8 Small Bomb, 12 Machine Gun, 16 Apple, 25 Umbrella, 70 Skateboard ...), 0xC1 = power stone, 0xC2 = treasure chest, 0xC3 = throwable stage prop (desert barrel cactus), 0xC8 = big prop or pole (desert saguaro, bamboo). Each item model maps 1:1 to one id across 6 runs and 3 savestates (`out/p07_all.txt`, 30 models, `+0x420` constant within every model). Each id was checked by forcing chest contents (sec. 3), and 8 crops were eyeballed against the catalogue names. **CONFIRMED**
3. **Chest contents are decided at chest birth.** They are stored in the resting chest's `+0x42C` (u8, same id space; **0xC1 = a power stone**). 35/35 chest openings spawned exactly that id at the chest (`out/p12_s2_21.txt`). Writing the byte changes what comes out (forced sweep, `out/p13_force_*.txt`). About 30-35% of chests hold a stone. **CONFIRMED.** The agent can know which chest holds a stone.
4. **`F+0x54` (held item) is NOT an item-type key.** It is a pointer to the held object's own arena record + 4. The same pointer value carries different items over a match: `0x0C50C504` held Ice Rod (0x39), Hammer (0x04) and Large Bomb (0x0A); `0x0C50DE24`, the env's "molotov", held Ice Rod (`out/p17_ptr_vs_type.txt`, 761 samples, 0 off-grid). **Held item type = `u8[ *(F+0x54) + 0x41C ]`** (= record `+0x420`). **CONFIRMED.** Consequences:
   * the env's `ITEM_NAMES` and the `bucket = (ptr // 0x430) % 256` hashed item embedding (obs [12..17]) encode an arena SLOT, not an item;
   * the other agent's "definition pointer" table needs re-keying on the type byte.
5. **`ps2_addr.CHEST_FALL_VT = 0x0C0C9810` is a misnomer.** That vtable is the generic weapon/item class. The v7 line's `fallN` counts ground + flying + **held** weapons (`out/p19_s2_51.txt`: 321 resting, 212 held, 31 thrown, 19 popping). No chest ever falls on Desert: all 39 chest births in `out/p10_s2_21.txt` happen at y = 50. **CONFIRMED**
6. **The production ledger window (`OBJ_GRID_N = 110`) is too short.** Live records reach grid idx 139, and the arena runs idx 0..207. The current `_obj_scan` misses 6.5% of chest and 8.6% of stone sightings (`out/p15_window.txt`). The live check found a frame with 5 chests where the legacy scan reported 4 (`out/p19_s2_51.txt`). Fix: `OBJ_GRID_N = 208`. **CONFIRMED**
7. **Holding is directly readable:** `+0x421` (state) is 5 or 7 when held. Header byte `+0x05` = holder seat 0..3 (last holder; 0xFF = never held). **CONFIRMED** (`out/p11_all.txt`: every held sample has state 5/7; no non-held sample does).

---------------------------------------------------------------------------------------------

## 1. Arena layout

| what | address / offset | notes | conf |
|---|---|---|---|
| grid base (idx 0) | `0x8C4FBD30` (= `ps2_addr.OBJ_GRID_LO`) | stride 0x430 | CONFIRMED |
| live records | idx 8 .. 207 | idx 208 = `0x8C532430` is the arena manager, not a record | CONFIRMED (`dbg` dump: `re/items_held/ram_slot2_f2000.bin`, free records chain via +0x0C) |
| category list heads | `u32 @ 0x8C532434 + 4*cat` → first record + 4 | records chain by `+0x10` (next) / `+0x0C` (prev), both pointing at record + 4 | CONFIRMED for cat 9: grid scan == list walk in 266/266 checks (`p19`) |
| `+0x04` hdr | b0 = category, b1 = holder seat / 0xFF, b2 = per-class spawn index | categories: **9 pickups / interactables**, 5 effects & scenery, 1 character-owned shots (LIKELY), 7 scene managers (GUESS), 8 per-player attached (GUESS), 2 misc | CONFIRMED (b0, b1) |
| `+0x08` vt | behaviour class | sec. 2 | CONFIRMED |
| `+0x28` | allocation serial (×8) | unique per spawn | LIKELY |
| `+0x2C/+0x30/+0x34` | x, y, z world | **hand-local offset while held** (e.g. (40,-55,0)) | CONFIRMED |
| `+0x68..+0xA4` | 4×4 world matrix, translation `+0x98/+0x9C/+0xA0` | moving this + pos moves the drawn object (ablation, sec. 6) | CONFIRMED |
| `+0xC4`, `+0xC8..` | render-node count, node pointers | each node points at **entity POOL record + 0x34** (`0x8C3E7400`, stride 0x90). The pool record's class `+0x3C` is the MODEL (`0x0C6xxxxx` for items, `0x0C59xxxx` stone gems, `0x0C591xxx` chest) | CONFIRMED |
| `+0x420` u8 | **type id** | sec. 2 | CONFIRMED |
| `+0x421` u8 | **state** | sec. 4 | CONFIRMED |
| `+0x423` u8 | flag 0/1/3 | unknown | - |
| `+0x424` u16 | remaining uses / durability (Hammer 600, Flame Thrower 220, matches items_held "counter") | | LIKELY |
| `+0x428` u8 | stone colour index 0..6 (type 0xC1 only; one pool model per value) | | CONFIRMED |
| `+0x42C` u8 | **chest content** (type 0xC2 only; 0 once opening) | sec. 3 | CONFIRMED |

**Pool vs ledger.** The `0x0C6xxxxx` "loot gem / ground weapon" pool classes in `PROJ_EXCLUDE_BANDS_V3` are the render nodes of these ledger objects. Every pool node belongs to an arena record (record `+0xC8` → pool `+0x34`). Read the ledger, not the pool. The pool only gives a model, and model addresses are load-dependent. Model → id is in `out/p06_all.txt`/`p07_all.txt`. In particular, `0x0C6486D0` (called "gem glow" in obs v3) is the **Ice Rod (0x39)** model, and `0x0C630A28/0x0C6311E8` is the **Leg Weight (0x24)** model.

## 2. Type ids and vtables (category 9)

| vt | type id(s) | what | conf |
|---|---|---|---|
| `0x0C0C9810` | most items 1..121 | generic weapon/item (melee, guns, rods, axes ...) | CONFIRMED |
| `0x0C0CA928` | 8, 9, 10 | bombs (Small/Medium/Large) | CONFIRMED |
| `0x0C0CA5D8` | 16, 17, 18, 74, 83..88, 104 | consume-on-pickup (food; 74 Angel Wing too) | CONFIRMED (forced) |
| `0x0C0C9F50` | 70 | Skateboard (ride) | CONFIRMED (crop) |
| `0x0C0CE6EC` | 78 | Beehive | CONFIRMED (forced) |
| `0x0C0CEB94` | 54 → 0xC8 | Bamboo Shoot; grows into a tall bamboo pole (type 0xC8) | CONFIRMED (crop `gallery/idc8_vt0c0ceb94*`) |
| `0x0C0CA114` | 89+ wearables | born at (0,0,0) (worn by the opener). Some 0x59+ ids spawn nothing. **Not a ground object** | LIKELY (`out/p21_s2_41.txt`) |
| `0x0C0CBCB0` | 0xC1 | **loose power stone** (knock-outs and chest stones). Colour at +0x428 | CONFIRMED |
| `0x0C0CC7A8` | 0xC2 | **treasure chest**, born at y = 50 on its pad, content +0x42C | CONFIRMED |
| `0x0C0F1688` | 0xC3 | **Desert barrel cactus** ×8 (y = 100). Pick up, carry overhead, throw; regrows at its home spot | CONFIRMED (`shots/abl_s2_21_900_overview.png`) |
| `0x0C0F18D4` | 0xC8 | **Desert tall saguaro** ×4 (y = 0, fixed homes (-1000,-1000), (950,-850), (100,1000), (-1050,800)). Can be uprooted, carried and thrown, then regrows | CONFIRMED (`shots/replay_s3_11_f11820.png`: Pride carries one) |
| `0x0C0CACAC` | 0 / 70 | rare, short-lived (4-40 f), player-owned helper. Not a pickup; ignore | GUESS (`out/p14_cacac.txt`) |
| `0x0C0F0E08` | 0xC3 | metal crates (factory / elevator stages) | LIKELY (`gallery/idc3_vt0c0f0e08*`) |
| `0x0C0E8AE4` | 0xC3 | wooden crates (battleship stage) | LIKELY (`shots/tour_f37800.png`) |
| `0x0C0E7FF0` | 0xC3 | red push-button box (battleship stage) | GUESS |
| `0x0C0F109A` | 0xC8 | pole (factory / elevator stages) | LIKELY |
| `0x0C0E455E` | 0xC4 | ship cannons / turrets (battleship) | GUESS (`gallery/idc4*`) |
| `0x0C0E5522` | 0xCC | red mounted cannon (battleship, green ship) | GUESS (`gallery/idcc*`) |
| `0x0C0CD554` | 0xC6 | small factory-stage object (two at a time) | GUESS |
| `0x0C0EBC60` | 0xCA | large green wall / tower blocks, elevator stage | GUESS |

Per-id names, behaviour class and a crop for each forced id: **`out/item_id_table.md`** (121 rows). Names come from `re/items_held/item_names.json`; the numbering is the same (code n = type n). Ids observed in natural Desert play are flagged "natural". Eyeballed crops that match the names: 2 Bazooka, 4 Hammer, 5 Sword, 8 Small Bomb, 12 Machine Gun, 16 Apple, 25 Umbrella, 70 Skateboard.

Non-pickup categories (cat 1/5/7/8) seen on Desert (`out/p03_s2_1.txt`):
* cat 1: `0x0C143118`, `0x0C143608`, `0x0C163144`, `0x0C163514`, `0x0C1682B0`. These are character-owned moving objects whose nodes sit in the `0x0C81xxxx` Accel band. **LIKELY character projectiles / special-move objects**, a cleaner projectile source than the pool, not pursued here.
* cat 5: effects and scenery, with `0x0C150A2C`, `0x0C1576C8`, `0x0C15DF9C`, `0x0C15F1A4`, `0x0C152E84` the most frequent. Others:
  * `0x0C0F156C` / `0x0C0F1590`: far-away background scenery (LIKELY);
  * `0x0C153A4C` ×4: per-player overhead marker carrying the player's stone model (LIKELY);
  * `0x0C0E25AC`: dust riding with fighters (nodes `0x0C54D6C0/0x0C54DAC0` = the obs-v3 0x0C54Dxxx band).
* cat 7: `0x0C058D44` ×4, `0x0C0593EE`, `0x0C059A28` (scene/camera/HUD managers, GUESS).
* cat 8: `0x0C154E00`, `0x0C15530C`, `0x0C155B7C`, `0x0C156924`, ×4 each, one per seat (GUESS: per-player attachments). Plus `0x0C031486` during the intro.
* cat 2: `0x0C0CB310` (seen once in a dump).

`OBJ_KNOWN_UNREPORTED`:
* `0x0C0CACAC`: as above.
* `0x0C0F18D4`: Desert saguaro (**throwable big prop**, not a "static spawner").
* `0x0C0F1688`: Desert barrel cactus (**throwable prop**, the "economy point" the bot learned blind).

## 3. Chest contents (goal 2)

* A chest is born (vt `0x0C0CC7A8`, state 2, y = 50) **already holding its content** in `+0x42C`. The value never changes while resting.
* When it is hit open: state goes 2 → 9. About 26-28 f later `+0x42C` drops to 0, and in the same frame a new object of that type spawns at the chest xz, rising (state 0, ~20 f) and then resting (state 2). The chest then goes to state 11 (breaking) and is freed.
* Evidence:
  * `p10_chest_life.py 2 8000 21 v` → `out/p10_s2_21.txt`;
  * `p12_chest_verify.py` → `out/p12_s2_21.txt`: **MATCH = 35, MISMATCH = 0**;
  * forcing `+0x42C` at chest birth makes the game spawn the forced id (`p13_gallery.py` with `CHEST_FORCE`, `p21_force_spawn.py`).
* `p09_chest_link.py` is a superseded naive linker. It read the chest bytes after the content had cleared. Its output `out/p09_all.txt` is kept only for the record.

## 4. State byte `+0x421`

| value | items | stone 0xC1 | chest 0xC2 | props 0xC3/0xC8 |
|---|---|---|---|---|
| 0 | popping out of a chest (~22 f, ~600 u/s) | ejected / flying (~48 f, ~1200 u/s) | - | hidden before regrow |
| 1 | - | - | - | regrowing at home (300 f) |
| 2 | **resting, pickable** | **resting** | **resting** | **ready** |
| 5 | **held** | - | - | **held / carried** |
| 6 | tossed / dropped, bouncing (~32 f, max ~1170 u/s) | - | - | knocked loose |
| 7 | held and in use (swing / fire) | - | - | - |
| 8 | thrown hard (2400 u/s) | - | - | **thrown, in flight (~10 f, ~1800 u/s)** |
| 9 | - | - | opening | - |
| 10 / 11 | breaking / dying | dying | breaking | 10 = shatter |

Durations and speeds: `p20_thrown.py 2 10000 61` → `out/p20_s2_61.txt`. State semantics for 5/7 are CONFIRMED (`p11`). The others are LIKELY from timing and speed.

**Thrown-object projectiles:** category-9 records in state 8 (and 6) are physical threats. A thrown cactus moves at ~1800 u/s. These can feed the projectile channel by vt-free, state-based selection instead of the 0x0C6 pool band.

## 5. Desert stage objects (training stage, all 3 savestates)

| object | type / vt | count | home positions | interaction |
|---|---|---|---|---|
| barrel cactus | 0xC3 / `0x0C0F1688` | 8 | y = 100: (-500,1000) (114,-900) (300,-1100) (-850,1000) (-650,1050) (-1000,-100) (-900,100) (-1100,300) | pick up (state 5), throw (8, ~1800 u/s), shatter (10), regrow (1) → ready (2) |
| tall saguaro | 0xC8 / `0x0C0F18D4` | 4 | y = 0: (-1000,-1000) (950,-850) (100,1000) (-1050,800) | uproot, carry and throw like a big prop; regrows |
| chest pads | 0xC2 | ≤ 6 live | (-600,650) (0,600) (250,-600) (-650,180) (950,300) (650,800) | hit to open; content `+0x42C` |

No sky-falling chests and no other category-9 hazards were seen on Desert in about 120k frames across slots 1/2/3.

## 6. Visual validation method ("ablation")

`p05_ablate.py` / `p18_replay_shot.py` / `p16_tour.py` restore a checkpoint, lift one record (pos and matrix y + 3000) for 3 frames, and diff the rendered frame. The diff bbox is exactly where that object is drawn. Outputs:
* `shots/abl_s2_21_900_overview.png`: cacti, saguaro, stone, umbrella, machine gun, chest;
* `shots/tour_f*.png`: other stages, labelled with type ids;
* `gallery/*.png`: crops for each type id, ×3 scale.

## 7. Scanner (ready to paste): `ground_scan.py`

`ground_scan.scan_ground(PS2Ram(ram), include_held=False, include_fixed=False) -> [GroundObj(idx, addr, vt, tid, state, holder, x, y, z, content, cat)]`. It scans the arena grid (208 slots, 7 vectorised `grid_words`) for live category-9 records:
* vt-agnostic: it ignores only the helper and wearable vts, and drops records at exactly (0,0,0);
* it classifies by the type byte.

It is validated live against the game's own category-9 linked list (0 mismatches / 266) and against the production `_obj_scan` (`p19_validate.py` → `out/p19_s2_51.txt`). Cost is ~0.22 ms per call on the M4 at every 3rd frame; restrict to idx 20..160 if that matters.

Also in the module:
* `nearest_ground(objs, bx, by, bz, n, cats)`;
* `obs_v4_block(objs, bx, by, bz, n=4)`, a reference encoder for the proposal below;
* `category(tid)`, giving 8 coarse classes: stone, chest, ranged, melee, throw, food, prop, other. The ranged/melee/throw/food sets are hand-assigned from the catalogue names (GUESS for edge cases; the vt column in `out/item_id_table.md` is the game's own split for bombs and food).

Held item type for any seat `p` (no arena scan needed):

```python
from ground_scan import held_type        # held_type(PS2Ram(ram), seat) -> type id, 0 = empty
# = u8[(F+0x54 pointer | 0x80000000) + 0x41C]   (PS2Ram wants the 0x8C mirror)
```
Exercised live in `p22_heldtype.py` → `out/p22_s2_71.txt`.

## 8. obs-v4 proposal (nearest ground items)

Current bus: v2 122 dims plus v3 [122..159]. Free reserved dims are 111..117 and 119..121 (118 = DIFF_DIM).

**Option A (no bus change, 10 dims in the reserved block).** Fill the reserved dims; old models see zeros there today, so this is a soft-start, not an orphaning:
* [111..115]: nearest free WEAPON/ITEM (cat ranged/melee/throw/other, state ∈ {0,2,6}): present, dx/1000, dz/1000, dy/1000, kind scalar (ranged +1, melee +0.5, throw −0.5, other 0);
* [116,117,119]: nearest throwable PROP (cactus/saguaro, state 2): present, dx/1000, dz/1000;
* [120]: **nearest chest holds a stone** (`+0x42C == 0xC1`);
* [121]: food present within 600 u (heal pickup).

**Option B (recommended for the next fresh bus, append [160..]).**
* G1. Ground items: 4 nearest-first slots × 12 = 48 dims:
  * `present, dx, dz, dy` (dx, dz, dy = (obj − self)/1000, clipped ±2; same POS_SCALE as stones/chests);
  * `dist` (/1500, clip 1);
  * `state_ready` (state 2) vs `airborne` (state 0/6);
  * a 5-way one-hot {ranged, melee, throw, food, other}.
  * Exclude held (5/7), dying (10/11) and wearables. Stones and chests stay in their own blocks.
* G2. Props: 2 nearest READY props (cactus, saguaro, crates) × 4 = 8 dims: present, dx, dz, `big` (type 0xC8).
* G3. Chest content flags: for the 2 chests already on the v7 line, `has_stone` (1) and `has_item` (1) = 4 dims. This is the gem-economy shortcut: walk to the chest that has the stone.
* G4. Held-item truth for self and the 3 opponents: the 5-way category one-hot of `type(F+0x54)` and `uses/600` clipped 1, (5+1) × 4 = 24 dims. This **replaces** the slot-hash embedding [12..17] (sec. 0.4), which encodes an arena slot. The opponent part is new information: an opponent holding a gun is a ranged threat.
* G5. Thrown props/items in flight (state 8, or 6 with speed > 700): feed into the existing projectile slots instead of new dims.
* B = 48 + 8 + 4 + 24 = **84 dims** (v4 = 244).

Fixes that are independent of any new obs:
* (a) `OBJ_GRID_N` 110 → 208, so chests and stones are not dropped;
* (b) rename CHEST_FALL_VT; `fallN` currently counts weapons including held ones;
* (c) the item embedding as above.

## 9. Script index (all outputs in `out/`, cited images in `shots/` and `gallery/`)

| script | purpose | output |
|---|---|---|
| `common.py` | boot (instance 2), load, ledger/pool readers, RandomPad, shot | |
| `p01_snapshot.py` | first look | `out/p01_slot2.txt` |
| `p02_census.py` | 6000 f census of ledger vts and pool classes | `out/p02_s2_1.txt`, `out/events_s2_1.txt`, `out/vtdump_s2_1.txt` |
| `p03_track.py` | per-slot change log + held/gem events (found F+0x54 → record) | `out/p03_s2_1.txt` |
| `p04_events.py` | 12k-frame raw recorders, slots 1/2/3 × 2 seeds (pickles deleted for disk; rerun to regenerate) | |
| `p06/p07/p08` | model groups, type-field search (+0x420), tail fields | `out/p06_all.txt`, `p07_all.txt`, `p08_all.txt` |
| `p10_chest_life.py`, `p12_chest_verify.py` | chest lifecycle; content == spawn 35/35 | `out/p10_s2_21.txt`, `out/p12_s2_21.txt` |
| `p11_heldstate.py` | state 5/7 ⇔ held | `out/p11_all.txt` |
| `p13_gallery.py`, `p16_tour.py`, `p21_force_spawn.py` | forced chest contents, crops, other-stage tour | `gallery/`, `out/p13_force_*.txt`, `out/p16_tour.txt`, `out/p21_s2_41.txt` |
| `p14_cacac.py` | the 0x0C0CACAC helper | `out/p14_cacac.txt` |
| `p15_window.py` | grid idx distribution (window bug) | `out/p15_window.txt` |
| `p17_ptr_vs_type.py` | F+0x54 is per-instance | `out/p17_ptr_vs_type.txt` |
| `p18_replay_shot.py`, `p05_ablate.py` | ablation screenshots | `shots/replay_*`, `shots/abl_*` |
| `p19_validate.py` | scanner vs list walk vs legacy `_obj_scan` | `out/p19_s2_51.txt` |
| `p20_thrown.py` | state durations and speeds | `out/p20_s2_61.txt` |
| `p22_heldtype.py` | live check of `held_type()` (0 of ~2700 held samples outside state 5/7) | `out/p22_s2_71.txt` |
| `ground_scan.py` | **the scanner** (`scan_ground`, `nearest_ground`, `held_type`, `obs_v4_block`, `category`) | |
