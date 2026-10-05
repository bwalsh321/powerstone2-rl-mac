# Independent intervention check of the Oct 4 RE claims (Power Stone 2, flycast, instance 9)

Verifier: separate session. It did not import the RE agents' readers: `vcommon.py` has its own readers. Every verdict
below comes from a machine check (RAM fields, hp deltas, the game's hit-source pointer, record spawns). The PNGs
in `shots/` are only supporting evidence for eyeballing.

**Method.** The emulator is deterministic: load → 300 f gives identical RAM hashes, and snapshot/restore → 300 f does
too (`v0_probe.py`). Each condition therefore restores the **same snapshot**, so the only difference between control
and intervention is the RAM write. Writes are made between frames (after `emu.run()` returns), which is the only
place a frontend can touch RAM. Run any script with `re/verify/vrun.sh <script> [args]`.

## Verdict table

| # | claim | verdict | key numbers |
|---|---|---|---|
| 1 | Chest content = resting chest `+0x42C` (0xC1 = stone) | **CONFIRMED-CAUSAL** | 65/65 conditions spawned exactly the byte's id at the chest. That is 13 chest events (7 slot2 + 6 slot3) × {ctl, 0xC1, 0x02, 0x05, 0x0C}. Controls predicted from the untouched byte: 13/13, including 2 natural stones. |
| 2a | Held type = `u8[(F+0x54) - 4 + 0x420]` | **CONFIRMED-CAUSAL** | Held type == the ground record's type in 8/8 controls and 8/8 swaps. Writing `+0x420` before pickup changes behaviour: melee→Gun swaps fired a `0x0C162DAC` (item-gun bullet) record and used gun acts 0x357/0x35C in 4/4. Gun→Sword swaps lost the gun rule (no bullets, 0/4) and ticked durability per frame in 4/4. |
| 2b | Uses counter `+0x424` starts at table `0x0C273900+(code-1)*0x34+6` | **CONFIRMED, with a correction** | The counter is set **when the record is spawned**, from the spawn type (18/18 forced chest spawns == table). It is **not** re-initialised at pickup: swapped items kept their spawn-time counter in 8/8. |
| 2c | Decrement rules | **CONFIRMED-CAUSAL** | Gun/rod: −1 per shot, 0 per idle frame (MG 25→19 with 6 bullet records; Ray Gun, Magic Rod 5→4). Melee: −1 per held frame (60/60 frames idle, 4 items). Which rule applies follows the type byte (swap test). |
| 3 | Hit spheres `P+0x187` count, `P+0x1AC+0x20(k-1)` x,y,z,r | **CONFIRMED-CORRELATIONAL (exact geometry); field-level causality INCONCLUSIVE** | Moving the victim around the reported sphere: the claimed contact test agrees with the game in **132/132 placements**. Per frame: 59 TP, 1 FP, 0 FN, 259 TN. Hits stop at exactly margin ≤ 0 (−1 hits, +1 misses). Writes to sphere, count, hurt cylinder or mask are **overwritten before the next collision in every frame** (survived 1/11, 0/11), so the fields can't be driven from outside. They are recomputed inside the frame, not stale display copies. |
| 4 | Hurt mask `P+0x12C` low u16 (0 = unhittable) | **CONFIRMED-CORRELATIONAL; causality INCONCLUSIVE** | 150 live-overlap frames across a 60-delay getup sweep: mask≠0 → hit 32/32, mask==0 → no hit 118/118. Forcing it 0 during a hit, or 0xFFFF during getup, changed nothing because the game rewrites it every frame (0/43 survived). |
| 5 | Stage id `0x8C472CF8` | **INCONCLUSIVE (constant only)** | It reads 5 constantly over 6000 f in slot1/2/3, and so does the mirror `0x8C46E198`. But 4–8 other u32s in 0x8C46E000–0x8C476000 are also constantly 5, so desert-only states can't single it out. Needs other-stage states. |
| 6a | Category-1 ledger records are the live hit volumes (position is what hits) | **CONFIRMED-CAUSAL** | Moving the source record's y to 5000 a few frames before impact stops **that record's** hit in **22/22** events (14 in `v6`, 8 in `v6b`). Controls hit 22/22. A negative control that moves a different record the same way still let the hit land 8/8. |
| 6b | The header low byte (=1) is what makes it live | **REFUTED as a causal gate** | Zeroing `+0x04` low byte (it stayed 0) did **not** stop the hit in 22/22. Category 1 is a good filter label for finding hit volumes, but the game doesn't gate collision on it. |

## 1. Chest contents (`v1_chest.py` → `v1_chest_out_slot2.txt`, `v1_chest_out_slot3.txt`)
- **Phase A:** slot2/slot3 run for 14000 f with seat1 idle and hp refilled every 60 f. It saw 59 + 58 chests and took a snapshot of each new resting chest (vt `0x0C0CC7A8`, state 2).
- **Phase B:** for each of the first 7 (slot2) / 6 (slot3) chests that open, restore the snapshot and write only `+0x42C` once.
  - Then run until the chest goes to state 9 (COMs open it), +120 f.
  - A new record counts if it is a new (idx, serial) pair, category 9, and within 150 u xz of the chest.
- **Results:**
  - The first spawn matched the predicted id in **65/65** runs.
  - Every 0xC1 write produced vt `0x0C0CBCB0` type 0xC1, a loose stone (13/13).
  - Item writes produced `0x0C0C9810` with the written type.
  - Natural controls included bomb (vt `0x0C0CA928`), skateboard (`0x0C0C9F50`) and food (`0x0C0CA5D8`). All matched.
  - The game never rewrote the byte before opening (`content_before_open` == written value, 65/65).
  - The opening frame was identical across conditions, so the COMs did not react to the content.
- Shots: `shots/v1_slot2_ev1_ctl.png` vs `v1_slot2_ev1_0xc1.png` (natural Magic Rod vs forced stone, 45 f after opening), plus the slot3 pairs.

## 2. Held items (`v2_items.py` → `v2_items_out.txt`; `v5_misc.py` → `v5_misc_out.txt`)
- **Setup:** natural resting items from slot2 (6 gun-class, 6 melee).
  - For each item: restore, optionally write `+0x420`, teleport seat1 (human Falcon) onto it, and press B (or Y) to pick up.
  - Pickup counts only when `F+0x54 == rec+4`. That worked for 8 of 12 items. 4 items never got picked up in either condition and are excluded, not counted as failures.
  - Then hold idle for 60 f, press X once, and watch 60 f.
- **Controls (8):**
  - Held type == natural type (8/8).
  - Uses at pickup == table (8/8).
  - Guns: 0 ticks idle, −1 per shot. MG: 6 `0x0C162DAC` bullets and −6.
  - Melee: −60 over 60 idle frames.
- **Swaps (8):**
  - Melee (0x06 ×2, 0x04, 0x2B) → Gun 0x01. Held type reads 0x01. Idle ticks 0. X → −1 and one new `0x0C162DAC` bullet in **4/4**. Gun acts 0x357/0x35C replace the melee acts 0x300/0x303/0x324.
  - Guns (0x0C, 0x3B ×2, 0x0D) → Sword 0x05. Held type reads 0x05. The counter ticks −1 per frame from its spawn value (25 or 5), not 600. The item ran out within ~25 f / ~5 f, and then X produced a bare-hand punch (act 0x100, sphere live), with no gun bullets.
  - **Conclusion:** the type byte drives behaviour, but the counter is not re-derived at pickup.
- **Counter initialisation:** `v5_misc.py` forced chest contents 0x01/0x02/0x05/0x0C/0x33/0x04 in 3 chests. Uses on the spawned record's first frame == table in **18/18**.
- **Side observation (contradicts PLAYER_STATE §1b "item swing uses the same sphere list"):** in the 5 melee-item controls, X put seat1 in state 8 (acts 0x300/0x303/0x324/0x3CF). `P+0x187` **never exceeded 1** during the 60 f. Held-item swings are not in the player sphere list here; PROJECTILES says their hit source is the cat-9 item record. Damage from the swing was not tested.
- Shots: `shots/v7_item_ctl_type06_x12.png` vs `shots/v7_item_swap_type01_x12.png` (`v7_shots.py`; the same Power Sword record, natural vs written 0x01, shown firing).

## 3 + 4. Hit spheres and hurt mask (`v3_hitbox.py` → `v3_hitbox_out.txt`; `v3b_geometry.py` → `v3b_geometry_out.txt`, `v3b_invuln_out.txt`)
- **Setup:** slot1 (both seats human Falcon). Seat0 punches (X) or kicks (Y); seat1 is the victim.
  - Close punch: sphere (250,130,808) r40 live f8–f18; hit on f8, 32.8 dmg.
  - Whiff at 600 u: no damage.
  - Tele-in (victim placed on the sphere after the first live frame): hit on f9.
- **Direct field writes (v3).** Each was re-applied on every live frame (or every frame).
  - The writes: sphere centre +3000, r=0, count=1, victim hurt cylinder +3000 or r=h=0, victim mask=0, sphere r=700/2000 or centre:=victim on a whiff.
  - Damage was unchanged in every case (tele-in still hit at f9; whiffs still missed).
  - The written values almost never survived one frame (`write_survived_next_frame` 1/11, 0/11, 0/43).
  - So the game recomputes them each frame before collision. A frontend write can't test whether collision reads these bytes or a register/stack copy.
- **Victim-position intervention (v3b):**
  - The victim was placed at d = 40..180 u from the reported sphere in 4 directions, plus 6 heights, for both punch and kick (132 placements).
  - The claimed contact test agrees with the game in 132/132 placements. Per frame: 59 TP, 1 FP, 0 FN, 259 TN.
  - The boundary is exact. Punch: right d=100 hits at margin −1, left d=100 misses at margin +1. Kick: fwd hits to d=140, back only to d=50, all matching the per-frame margins.
  - So the reported spheres and cylinders are the game's collision volumes (no other explanation fits a ±1 u boundary). We just can't overwrite them.
- **Mask timing (v3b, 60 delays after a grab-throw knockdown):** victim states 34→32→14→15→0, mask 0 in 34/14/15.
  - Over all live overlap frames, mask≠0 coincides with a hit 32/32 and mask==0 with no hit 118/118.
  - In the first hittable frame, the mask reads 0 before the frame and 0xFFFF after it, i.e. it is set within the frame, before collision.
  - The mask=0xFFFF-during-getup and mask=0-during-hit writes (v3) had no effect, because they were overwritten.
- Shot: `shots/v3_close_ctl_f9.png`.

## 5. Stage id (`v5_misc.py` → `v5_misc_out.txt`)
- Constant 5 for 6000 f in all three states; the mirror agrees.
- Not distinctive: 4 (slot1) / 8 (slot2, slot3) other u32s in the same 32 KiB window are also constantly 5.
- The mapping to stages can't be checked without other-stage savestates. PLAYER_STATE also reports a collision with Pharaoh Walker.

## 6. Projectiles (`v6_proj.py` → `v6_proj_out.txt`; `v6b_proj.py` → `v6b_proj_out.txt`)
- **Events:** natural 4P COM fights (slot3 lv8, slot2 lv3). An event is a victim hp drop where the victim's `P+0x3774` == `rec+4` of a category-1 record that already existed (same serial) ≥4 frames earlier.
  - Found: 18 in slot3 and 89 in slot2 over 9000 f each.
  - Tested: 14 + 8, spread over classes. Falcon/Pride missile `0x0C122FEC`, item `0x0C16B9D2`, Ryoma `0x0C127D88`/`0x0C127448`, Accel `0x0C142BDC`/`0x0C143118`, Ayame `0x0C12FB0A`/`0x0C130640`, Pete soldiers `0x0C139010`, item flame `0x0C163514`.
- **Conditions,** each from a snapshot 4 f before impact:
  - ctl;
  - `far`: y = 5000 every frame, both pos `+0x30` and matrix `+0x9C`;
  - `farpos`: `+0x30` only;
  - `hdr0`: low byte of `+0x04` := 0, once;
  - `other`: a different live record moved the same way.
- **Results:**
  - The source record hit: ctl 22/22, far 0/22, farpos 0/14, hdr0 22/22 (the byte read back 0 on all 3 following frames), other 8/8.
  - Some `far` runs still show victim damage from *other* sources in the 12-frame window (e.g. Pete soldier swarms, Accel beams). The machine check is on the hit-source pointer, so those don't count against the claim.
- Shots: `shots/v7_proj_ctl_hitframe.png` vs `shots/v7_proj_moved_hitframe.png` (missile rec81 → seat3: 111 dmg vs 0).

## Files
- Helpers: `vcommon.py` (own readers), `vrun.sh` (runner), `v0_probe.py` (seat/ledger dump, determinism check).
- `v1_chest.py [nevents] [slotN]`: claim 1.
- `v2_items.py`: claim 2. `v5_misc.py`: claim 5 and the uses-at-spawn check.
- `v3_hitbox.py`, `v3b_geometry.py [geo]`: claims 3/4. `v3b_invuln_out.txt` is the mask-timing part of the first v3b run; the prediction bug that was fixed only affected the geometry part.
- `v6_proj.py`, `v6b_proj.py`: claim 6.
- `v7_shots.py`: evidence PNGs.
- `v1_item_key.py` / `v1_out.txt` belong to the main session and are untouched.
