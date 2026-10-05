# Power Stone 2: held-item dictionary, ammo/uses, categories, obs-v4 proposal

Folder: `linux_port/re/items_held/`. Every probe ran headless on FlycastBridge **instance 1**.
No existing repo file was modified.

```
cd linux_port/re/items_held; source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../../../sdlarch-rl:../..
python probe3_holds.py states/slot2.state 20000 11      # one hold-timeline run
python an4_behavior.py                                   # per-item counter and throw behaviour
```

Confidence tags: **CONFIRMED** means a script, its output file here and, where it applies, a screenshot. **LIKELY** means strong data without a direct check. **GUESS** is a label only.

Data volume: 26 hold-timeline runs (slots 1/2/3; 18 x 20k frames, plus 8 runs with random START presses that reached the menus, attract demo and other stages), **1276 holds**, logged in `ev/holds_*.json`.

---------------------------------------------------------------------------------------------

## 0. Headlines

1. **`F+0x54` is not an item-type key. CONFIRMED.** It points at the held object's own record in the 0x430-stride object arena, plus 4. `(ptr - 0x0C500030) % 0x430 == 4` for every pointer seen (`probe1_slot2_out.txt`). That explains why every value sits at "residue 0x1E4". Record slots get reused, so one pointer value carries different items over a match. The env's `ITEM_NAMES`, and the `bucket = (ptr//0x430)%256` hashed embedding in obs `[12..17]`, therefore encode an **arena slot**, not an item. The items_ground agent found the same thing independently (`../items_ground/GROUND.md` sec. 0.4), and the two analyses agree.
2. **The item type is the u8 at `record + 0x420`**, where record = `(F+0x54) - 4`. Equivalently it is `ptr + 0x41C`. **CONFIRMED.** Codes 0x01..0x79 are items, and **code = item_no + 1** into the game's own name table. Codes from 0xC1 up are stones, chests and stage props.
3. **The game's own item tables are in RAM and are static across all three savestates. CONFIRMED** (`check_table_static_out.txt`, identical md5 hashes).
   * Name-pointer table: `0x0C29DDD0`, 183 x u32, indexed by item_no (`item_names.json`).
   * **Item property table: `0x0C273900 + item_no*0x34`.** It holds the initial uses/ammo counter, a thrown-on-use flag, a melee/use flag, grip, attach bone and more (sec. 2; `item_table.json`, `decode_table_out.txt`).
4. **Remaining ammo/uses: u16 at `record + 0x424`. CONFIRMED.** At pickup of a fresh item it equals the table counter. This held for all 30 item codes seen live (Gun 6, Bazooka 5, Machine Gun 25, 3-Way Shotgun 7, Flame Thrower 220, Soap Bubble Gun 250, Trident 480, Hammer 600, bombs 420, and so on; `an4_behavior_out.txt`). That match is also the proof of the code→name mapping. The counter is what the **pink HUD gauge** above a player's life bar draws: f=9000 Hammer counter 351/600 = 0.585, and the gauge measures 87/149 px = 0.58 (`shots/reader_f9000.png`, `test_reader_out.txt`).
5. **Thrown items are visible in flight.** The state byte `record+0x421` becomes 8 when an item is thrown (bombs, Fire-Bottle, Leg Weight, Leg Trap, cactus props), and the record's world position at `+0x2C/+0x30/+0x34` moves 400-2000 units in 12 frames. These records can feed the projectile channel directly (sec. 5).

## 1. Reading the held item (drop-in)

| field | address | meaning | conf |
|---|---|---|---|
| held pointer | `u32 F+0x54` (F = `ps2_addr.GEMS[k][1]`) | 0 = empty hands, else record+4 | CONFIRMED |
| record | `ptr - 4` (RAM offset `(ptr-4) & 0xFFFFFF`) | 0x430-byte arena record | CONFIRMED |
| **type code** | `u8 rec+0x420` | dictionary key (sec. 6) | CONFIRMED |
| state | `u8 rec+0x421` | 0 popping out of a chest, 2 resting, **5 held, 7 held and in use**, 6 dropped/tossed, **8 thrown in flight**, 10/11 dying. The 5/7/8 values are CONFIRMED here and in items_ground `p11`. | CONFIRMED (5/8), LIKELY (others) |
| **uses / ammo** | `u16 rec+0x424` | sec. 3 | CONFIRMED |
| holder mask | `u8 rec+0x426` | `1 << seat` of the holder (0x01 P1, 0x02 P2, 0x04 P3, 0x08 P4 in `probe2_slot2_s1_out.txt`) | LIKELY |
| holder seat | `u8 rec+0x05` | last holder seat, 0xFF = never held (items_ground) | CONFIRMED (items_ground) |
| behaviour fn | `u32 rec+0x08` | `0x0C0C9810` generic item, `0x0C0CA928` bombs, `0x0C0CA5D8` food, `0x0C0C9F50` skateboard, `0x0C0F1688` cactus prop, `0x0C0F18D4` saguaro | CONFIRMED |
| hand-local pos | `rec+0x2C..0x34` while held | e.g. (0,-13,20). World coordinates once dropped or thrown. | CONFIRMED |

`items_dict.held_item(ram, F)` implements this and returns `(code, name, category, range_class, thrown, counter, counter_frac)`. It was replayed live in `test_reader.py`, and its output matches the probe logs.

## 2. Item property table `0x0C273900 + no*0x34` (static game data)

Decoded by `decode_table.py`; the full table is in `decode_table_out.txt`. Byte offsets inside one entry:

| off | meaning | evidence | conf |
|---|---|---|---|
| +0x00 u8 | **thrown on use** (1 = the item leaves the hand: bombs, Fire-Bottle, Fire Cracker, Leg Weight, Bamboo Shoot, Pitfall, Petrifier, Transparentizer, Stick Bomb, Beehive, Hand Grenade, Thumbtack, Exciting Book, PS Magazine) | every b0=1 item seen live went to state 8 with a large displacement after release; b0=0 items dropped with about 60 units of displacement | CONFIRMED for the live ones |
| +0x01 u8 | 0 normal, 1 heavy/overhead (Dragon Slayer, Gigantic Hammer, Brave Man's Axe, Morning Star, Skateboard, Scooter, Meteor, Fireworks), 2 thrown projectile, 3 deployed/trap (Large Bomb, Leg Trap, Pitfall, Beehive, Thumbtack) | pattern only | GUESS |
| +0x02 u8 | grip: 1 one-handed, 2 two-handed | Sword 1, Hammer 2 | GUESS |
| +0x03 u8 | **action class: 1 = swing (melee), 2 = use/fire/throw/eat** | all guns and rods 2, all blades and hammers 1 | LIKELY |
| +0x04 u8 | attach bone: 8 hand, 12 shield arm, 7 forearm (arm guns), 4 head (hats/ears), 2 tail, 15 feet (Inline Skate), 18 paw, 0 none (Scooter) | names line up | LIKELY |
| +0x05 u8 | special mode: 1 normal, 2 (MG, bombs, homing missile, traps), 3 wings/scooter, 5 dragons/Morning Star/Leg Weight, 16 creatures | | GUESS |
| **+0x06 u16** | **initial uses counter** | equals the live `rec+0x424` at fresh pickup for 30/30 codes | CONFIRMED |
| +0x08 f32 | effect radius? (Large Bomb/traps 53, Fireworks/Beehive 55, Meteor 51) | | GUESS |
| +0x0C, +0x10 f32 | hold offsets / blade length (Sword 51, Dragon Slayer 150, Hammer 60, Toy Hammer 25) | used as the reach heuristic in sec. 6 | GUESS |
| +0x21 u8 | equals the code byte for rows 0..118 (two exceptions) | sanity check | CONFIRMED |

Rows 119-120 (Devil Wing, Kitten) do not decode cleanly, so the dictionary covers codes 0x01..0x77. Neither row was ever seen live.

## 3. What the counter means, per class (`an4_behavior_out.txt`, `an5_persist_out.txt`)

| class | counter | how it ticks | conf |
|---|---|---|---|
| guns / rods / shotguns / Loudspeaker (Gun 6, Bazooka 5, MG 25, Ray Gun 5, 3-Way 7, rods 5, Loudspeaker 5) | **shots left** | -1 per shot, only in holder state 8 (firing) | CONFIRMED |
| stream weapons (Flame Thrower 220, Soap Bubble Gun 250) | **frames of fire left** | -1 per frame while firing (state 8) | CONFIRMED |
| melee, shields, Magic Stick, Skateboard (600 / 480 / 420) | **frames of durability left** | -1 per frame for **every frame held**, whether or not it is swung (walk, air and attack states all tick). The item breaks at 0. | CONFIRMED |
| bombs Small/Medium/Large (420) | **fuse frames** | -1 per frame once picked up; explodes at 0. The item is then thrown (state 8) and the record turns into an explosion (code 0xC6). | CONFIRMED |
| Fire-Bottle, Leg Weight, Leg Trap, stage props (10) | not used (stays 10) | single throw | CONFIRMED |
| food (45..200) | probably the heal amount (consumed on pickup, vt `0x0C0CA5D8`) | | GUESS |

The counter is **per record and persists across drop and re-pickup**: 189/190 same-record re-pickups within 600 frames had an unchanged counter (`an5_persist_out.txt`). It does **not** tick while the item lies on the ground. A half-used gun on the floor stays half-used.

## 4. Stage objects in the type space

| code | what | conf |
|---|---|---|
| 0xC1 | power stone (not reachable through F+0x54) | CONFIRMED (items_ground) |
| 0xC2 | treasure chest | CONFIRMED (items_ground) |
| 0xC3 | Desert barrel cactus. Carried and thrown at ~1800 u/s; 560 holds logged; counter 10 never used. | CONFIRMED |
| 0xC8 | Desert tall saguaro (uprooted and carried) | CONFIRMED (items_ground crop) |
| 0xC4 | **stage-specific**. Boat stage (fn `0x0C0E455E`): looks like the deck turret, counter 30 ticking per use with the holder in state 18. Airship (fn `0x0C0D1BAE`): unknown. Seen only in attract-demo footage (`shots/v_c4_*.png`). | GUESS |
| 0xC5, 0xCC | other-stage props (fn `0x0C0DF0CA` thrown; fn `0x0C0E5522` counter 600) | GUESS |

Codes from 0xC3 up are **reused per stage**. The three training savestates are all Desert, so only 0xC3 and 0xC8 matter there. A carried prop is a throw threat.

## 5. obs-v4 proposal (requested: which item each opponent holds, ammo, range, thrown)

Read everything from the record. A raw ID never reaches the net; it is mapped to a threat category. The categories are derived from the game's own table (sec. 2) plus a few hand sets (`gen_dict.py`).

**Category set (5 one-hot dims + 1 fraction):**

| dim | category | members |
|---|---|---|
| c0 | MELEE | `cat == melee` or `shield` (swing, contact range; reach class melee_short/long available if more dims are wanted) |
| c1 | RANGED_LONG | guns, bazooka, homing missile, rods, ray/beam guns, shotguns, Lance of Lava, Meteor, Fireworks |
| c2 | RANGED_SHORT | Flame Thrower, Soap Bubble Gun, Adhesive Spray, Trumpet, Loudspeaker, Typhoon (stream/cone) |
| c3 | THROWN | `thrown_on_use` items (explosive, throwable, trap) **and stage props (code >= 0xC3)** |
| c4 | OTHER | food, mount, creature, wearable, unknown |
| f  | uses_frac | `rec+0x424 / table counter`, clipped to [0,1]. Shots left for guns; durability left for melee; **for bombs, fuse left (low = about to explode)**; 1.0 for single-use throws |

has_item equals `any(c0..c4)`, so it no longer needs its own dim for opponents.

* **Self** (same width as today, 7 dims, slots `[11..17]`): `[11] has_item, [12] MELEE, [13] RANGED_LONG, [14] RANGED_SHORT, [15] THROWN, [16] OTHER, [17] uses_frac`. This replaces the slot-hash embedding, which carries no item information. The width is unchanged, but the semantics change, so existing models should be retrained or fine-tuned, not reused as-is.
* **Each opponent k** (nearest-first, in the existing block): keep `[+12] has_item` and add 5 dims in the reserved/v3 tail: `MELEE, RANGED (long or short), THROWN, OTHER, uses_frac` (3 x 5 = 15 dims). Merging long and short ranged for opponents saves a dim. Split them if the reserved budget allows.
* **Thrown items as projectiles.** Scan the arena (grid `0x8C4FBD30 + k*0x430`, k 8..207, header byte `+0x04 == 9`) for `rec+0x421 == 8` (thrown, in flight) and, for bombs, `== 6` (tossed and bouncing). Report their position `+0x2C/+0x30/+0x34` and frame-difference velocity. A live **bomb lying on the ground with a low fuse** (code 8/9/10, state 2/6, `+0x424` small) is also worth a slot. This covers what `PROJ_EXCLUDE_BANDS_V3` currently drops as "accepted loss".
* Wire format: the v8 line already carries the F+0x54 pointer per seat (`ps2_ram.py` line ~310). Two more per-seat fields (type byte and counter) avoid a pointer dereference in the env, or the synth can compute the 6-dim block itself.

Desert reality check: 30 distinct item codes plus the two props appeared in about 600k logged frames. The common ones are Gun, Bazooka, Flame Thrower, Hammer, Sword, Power Sword, Iron Pipe, 3 bombs, Fire-Bottle, MG, Ray Gun, Magic Stick, Power Shield, Umbrella, Toy Hammer, Bubble Gun, Leg Weight, Battlefield Axe, Trident, 3-Way Shotgun, Leg Trap, Ice/Magic Rod, Loudspeaker, Devil Sickle, Skateboard and Harisen. All five threat categories occur.

## 6. Dictionary

The full generated file is **`items_dict.py`**: `ITEMS` (119 codes), `LIVE_CONFIRMED`, `STAGE_CODES`, `held_item()`. Columns: name, category, range_class, thrown_on_use, initial_counter, counter_kind.
* name: CONFIRMED for all 119. It comes from the game's own table, and the code = no+1 mapping is proven by 30 counter matches, a skateboard crop and a gun crop. items_ground's force-spawn gallery (`../items_ground/out/item_id_table.md`) shows every id 1..121 with the same names.
* initial_counter: CONFIRMED (game table).
* category / range: LIKELY where derived from table flags +0x00/+0x03/+0x04; GUESS for the hand-assigned sets (FOOD, MOUNT, RANGED_SHORT, TRAP) and for the melee_short/long split (blade length >= 70 or heavy flag).

Live-confirmed subset (fresh-pickup counter == table counter, n holds):

| code | name | category | range | thrown | counter | n |
|---|---|---|---|---|---|---|
| 0x01 | Gun | ranged | ranged_long | no | 6 shots | 34 |
| 0x02 | Bazooka | ranged | ranged_long | no | 5 shots | 30 |
| 0x03 | Flame Thrower | ranged | ranged_short | no | 220 fire frames | 21 |
| 0x04 | Hammer | melee | melee_short | no | 600 frames | 33 |
| 0x05 | Sword | melee | melee_short | no | 600 | 30 |
| 0x06 | Power Sword | melee | melee_short | no | 600 | 43 |
| 0x07 | Iron Pipe | melee | melee_short | no | 600 | 29 |
| 0x08 | Small Bomb | explosive | throw | yes | 420 fuse | 16 |
| 0x09 | Medium Bomb | explosive | throw | yes | 420 fuse | 18 |
| 0x0A | Large Bomb | explosive | throw | yes | 420 fuse | 19 |
| 0x0B | Fire-Bottle | explosive | throw | yes | 10 (unused) | 26 |
| 0x0C | Machine Gun | ranged | ranged_long | no | 25 shots | 36 |
| 0x0D | Ray Gun | ranged | ranged_long | no | 5 shots | 26 |
| 0x0E | Magic Stick | melee | melee_long (GUESS) | no | 420 frames | 27 |
| 0x0F | Power Shield | shield | melee | no | 420 frames | 21 |
| 0x13 | Flame Sword | melee | melee_long | no | 600 | 6 |
| 0x19 | Umbrella | melee | melee_long | no | 600 | 15 |
| 0x1D | Toy Hammer | melee | melee_short | no | 600 | 25 |
| 0x21 | Soap Bubble Gun | ranged | ranged_short | no | 250 fire frames | 21 |
| 0x24 | Leg Weight | throwable | throw | yes | 10 | 10 |
| 0x2B | Battlefield Axe | melee | melee_short | no | 600 | 23 |
| 0x30 | Trident | melee | melee_long | no | 480 | 19 |
| 0x33 | 3-Way Shotgun | ranged | ranged_long | no | 7 shots | 34 |
| 0x35 | Leg Trap | trap | throw | yes | 10 | 4 |
| 0x39 | Ice Rod | ranged | ranged_long | no | 5 shots | 29 |
| 0x3B | Magic Rod | ranged | ranged_long | no | 5 shots | 20 |
| 0x43 | Loudspeaker | ranged | ranged_short | no | 5 uses | 24 |
| 0x44 | Devil Sickle | melee | melee_short | no | 420 | 9 |
| 0x46 | Skateboard | mount | none | no | 600 frames | 23 |
| 0x6A | Harisen | melee | melee_short | no | 600 | 9 |

Ready-to-paste minimal name dict (key = type byte at `(F+0x54) - 4 + 0x420`):

```python
ITEM_NAMES = {  # code -> name ; code = item_no + 1
    0x01: "Gun", 0x02: "Bazooka", 0x03: "Flame Thrower", 0x04: "Hammer", 0x05: "Sword",
    0x06: "Power Sword", 0x07: "Iron Pipe", 0x08: "Small Bomb", 0x09: "Medium Bomb",
    0x0A: "Large Bomb", 0x0B: "Fire-Bottle", 0x0C: "Machine Gun", 0x0D: "Ray Gun",
    0x0E: "Magic Stick", 0x0F: "Power Shield", 0x10: "Apple", 0x11: "Short Cake", 0x12: "Meat",
    0x13: "Flame Sword", 0x14: "Ice Sword", 0x15: "Thunder Sword", 0x16: "Dragon Slayer",
    0x17: "Legendary Sword", 0x18: "Frozen Tuna", 0x19: "Umbrella", 0x1A: "Deluxe Umbrella",
    0x1B: "Cheap Umbrella", 0x1C: "Tranquilizer Gun", 0x1D: "Toy Hammer", 0x1E: "Pickaxe",
    0x1F: "Magical Mallet", 0x20: "Gigantic Hammer", 0x21: "Soap Bubble Gun",
    0x22: "Homing Missile", 0x23: "Fire Cracker", 0x24: "Leg Weight", 0x25: "Deluxe Shield",
    0x26: "Spear", 0x27: "Deluxe Spear", 0x28: "Beam Gun", 0x29: "Powerful Buster",
    0x2A: "Arm Gun", 0x2B: "Battlefield Axe", 0x2C: "Victory Axe", 0x2D: "Lumber Jack's Axe",
    0x2E: "Brave Man's Axe", 0x2F: "Big Racket", 0x30: "Trident", 0x31: "Deluxe Trident",
    0x32: "Fork", 0x33: "3-Way Shotgun", 0x34: "5-Way Shotgun", 0x35: "Leg Trap",
    0x36: "Bamboo Shoot", 0x37: "Pitfall Hoop", 0x38: "Flame Rod", 0x39: "Ice Rod",
    0x3A: "Thunder Rod", 0x3B: "Magic Rod", 0x3C: "Mystic Rod", 0x3D: "Weird Rod",
    0x3E: "Adhesive Spray", 0x3F: "Medusa", 0x40: "Petrifier", 0x41: "Transparentizer",
    0x42: "Trumpet", 0x43: "Loudspeaker", 0x44: "Devil Sickle", 0x45: "Morning Star",
    0x46: "Skateboard", 0x47: "Inline Skate", 0x48: "Scooter", 0x49: "Stick Bomb",
    0x4A: "Angel Wing", 0x4B: "Meteor", 0x4C: "Typhoon", 0x4D: "Fireworks", 0x4E: "Beehive",
    0x4F: "Fire Dragon", 0x50: "Ice Dragon", 0x51: "Thunder Dragon", 0x52: "Panther",
    0x53: "Rice Ball", 0x54: "Banana", 0x55: "Hamburger", 0x56: "Roast Chicken",
    0x57: "Roast Pork", 0x58: "Wedding Cake", 0x59: "Rabbit Ear", 0x5A: "Rabbit Tail",
    0x5B: "Rabbit Arm", 0x5C: "Rabbit Paw", 0x5D: "Cat Ear", 0x5E: "Cat Tail", 0x5F: "Cat Arm",
    0x60: "Crown", 0x61: "Silk Hat", 0x62: "Straw Hat", 0x63: "Party Hat",
    0x64: "Exciting Book", 0x65: "Spoon", 0x66: "Beam Sword", 0x67: "Devil Tail",
    0x68: "Cheese", 0x69: "Metallic Bat", 0x6A: "Harisen", 0x6B: "Hand Grenade",
    0x6C: "Wind-Up Key", 0x6D: "Flower", 0x6E: "Cat Paw", 0x6F: "Shoes of Achilles",
    0x70: "Bracelet", 0x71: "Emperor's Crown", 0x72: "Thumbtack",
    0x73: "Power Stone Magazine", 0x74: "Lance of Lava", 0x75: "Light Stone",
    0x76: "Plaster", 0x77: "Punching Gloves", 0x78: "Devil Wing", 0x79: "Kitten",
    0xC3: "stage prop (Desert barrel cactus)", 0xC8: "stage prop (Desert saguaro)",
}
```

## 7. Files

| file | what |
|---|---|
| `common.py` | boot/load/read helpers, `refill()` (HEALTH_OBJ writes keep matches going), instance 1 |
| `probe1_live.py` / `probe1_slot2_out.txt` | F+0x54 lands on arena slot + 4; the "vtables" are behaviour classes |
| `probe2_events.py` / `probe2_slot2_s1_out.txt`, `ev/slot2_s1_dumps.npz` | pickup-event record dumps; first sight of the +0x420/+0x424/+0x426 fields |
| `an1_fields.py` | field-cardinality scan over those dumps |
| `probe3_holds.py`, `run_batch.sh`, `batch1_log.txt`, `ev/holds_*.json` | 26 hold-timeline runs (1276 holds). The batch hit the 30-min background limit after its 7th START run; all finished runs are kept. |
| `an3_holds.py` / `an3_holds_out.txt`, `an4_behavior.py` / `an4_behavior_out.txt`, `an5_persist.py` / `an5_persist_out.txt` | per-code summaries, counter semantics, throw behaviour, persistence |
| `find_proptable.py` | located the property table by searching for the observed counters |
| `decode_table.py` / `decode_table_out.txt`, `item_table.json`, `item_names.json` | the decoded game tables (from `ram_slot2_f2000_lo.bin`, the first 2.6 MB of a slot2 RAM dump) |
| `check_table_static.py` / `_out.txt` | the tables are identical in slot1/2/3 |
| `gen_dict.py` -> `items_dict.py` | dictionary + `held_item()` reader |
| `test_reader.py` / `_out.txt`, `shots/reader_f9000.png` | live reader check + HUD gauge == counter fraction |
| `verify_shots.py` / `verify_stageobj_out.txt`, `shots/v_*.png` | deterministic replay screenshots (stage objects) |
| `shots/slot2_s1_ev027_P3.png` (skateboard, code 0x46) and `shots/slot2_s1_ev031_P3.png` (pistol, code 0x01) | visual confirmations of code = no+1 |

## 8. Open items

* Category assignments for items never seen live (Desert spawns only about 30 types) are table-derived or GUESS.
* Field meanings in table bytes +0x01/+0x02/+0x05 and the floats are GUESS.
* Food counter = heal amount is not verified.
* Stage props on non-Desert stages (0xC4/0xC5/0xCC) were seen only in the attract demo.
* `rec+0x426` holder mask and `rec+0x427`/`+0x428` are not fully pinned down. Use items_ground's header `+0x05` for the holder seat.
