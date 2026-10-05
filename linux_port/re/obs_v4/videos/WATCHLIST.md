# Obs-v4 overlay videos: what to look for

There are three 75-second clips (640×480, H.264, 30 fps, real time), made by `overlay_v4.py`.
- P2 (yellow, Falcon) is a simple scripted bot: it chases, picks things up and attacks. The COMs play the other
  seats.
- Everything drawn comes from the v4 reader's decode of RAM, projected with the RAM camera.
- Projection accuracy: `calibrate_projection.py` reports a held-out median error of 12 px (7 px for cacti, 12 for
  chests, 34 for the tall saguaros, whose bounding-box centre is fuzzy).
- Every event time below was logged automatically by the renderer (`*.events.json`).

**Legend**

Players:
- Thin rings at the feet and the top of each player, in the seat colour, are the hurtbox cylinder.
- The label above each head reads `P# <state> INV AIR`.
- A red circle is a live hit sphere. Above the head, `HIT xN Nf` gives the sphere count and how many frames it has
  been live, and `startup Nf` is the P+0x414 attack-startup flag with its age.
- `ITEM SWING (blade spheres)`: the player is swinging a held melee item. Its blade spheres come from the item's own
  ledger record, and they are among the red circles.
- Cyan `[Item uses/initial]` above a head is the held item.

Stones and items:
- **Gold ring + `STONE v3#k`**: a loose power stone that today's obs sees, in v3 stone slot k (0 = nearest).
- **Orange `STONE 208-only (idx N)`**: a stone the live contract MISSES because its ledger slot is ≥ 110
  (`OBJ_GRID_N = 110`). v4 sees it.
- **Orange `STONE not in v3 (>6)`**: beyond the 6 nearest.
- The HUD line `stones:` counts them.
- Cyan text on the ground is a ground item. A `~` suffix means it is in flight or popping out. A small box marks
  the 3 items the bot's obs carries.
- Text on a chest gives its contents **before it opens**: gold `STONE inside`, otherwise the item name. It changes
  to `OPENING: …` when the chest is hit.

Projectiles:
- Orange dot plus arrow: a v4 ledger projectile, with 0.25 s of velocity.
- Magenta: a v4 thrown object.
- Grey: the bot's own projectile. It is **not** in the bot's obs; the owner comes from the ledger header byte.
- `v4#k`: the obs slot that projectile occupies.
- **Cyan square `v3#k`**: today's v3 pool projectile slots, for comparison.

Spatial and HUD:
- Green lines from P2 are the 8 free-run rays of the spatial block, labelled U/D/L/R/UL/UR/DL/DR with their
  distance.
- The top-left HUD shows the bot's held item and uses fraction, the v4 threat count, the chest contents of the 2
  chests in the obs, and the per-opponent melee summary (`HIT`, `/su` = startup, `m` = contact margin).

## slot2_lv3_ffa.mp4 (4P FFA: Ayame / Falcon(bot) / Pete / Accel, COM lv3)

| time | look for |
|---|---|
| 0:05–0:09 | Chest labels show item names before anything opens. Compare them with what pops out |
| **0:08.0** | First v4 projectile marker (orange) |
| **0:08.6** | First hit: P2 loses health to P4 (Accel). Look for P4's red hit sphere / `HIT` label on the frames before, and P2's state going to `HIT` |
| **0:09.5** | **First chest opening.** The chest read "Hammer" beforehand, and a Hammer pops out |
| **0:10.8** | **Bot picks up the Hammer.** The HUD switches to `held: Hammer`, and uses counts down as it is held (melee durability ticks every frame) |
| 0:13.5 | A chest opens with a Fire-Bottle |
| **0:20.4–0:20.7** | **Thrown cactus** (magenta arrow) flying near P4. There is no cyan v3 marker on it: v3 hides thrown objects |
| 0:26.5 | A resting chest at (-650, 180) shows gold **STONE inside** |
| 0:33.8 | P4 holds a Small Bomb. Its uses fraction is the fuse, falling |
| 0:42.6 | P1 holds a Soap Bubble Gun (ranged-short) |
| **0:08.7** | First loose stone: gold ring, `STONE v3#0` |
| **0:11.7** | **Bot swings the Hammer**: `ITEM SWING (blade spheres)` above P2, with red blade circles. P1 takes 103 at 0:11.7 |
| **0:29.0 / 0:32.1 / 0:35.1** | **Bot fires its Machine Gun.** The bullets are drawn grey and the HUD threat count does not include them (fixed: before this, they were reported as threats to the bot) |
| **1:14.0** | **`STONE 208-only (idx 117)`** in orange next to P2: a stone the live v3 obs does not see (OBJ_GRID_N bug) |

## slot3_lv8_ffa.mp4 (4P FFA: Pride / Falcon(bot) / Ryoma / Accel, COM lv8)

| time | look for |
|---|---|
| **0:06.5–0:08.8** | First hits: P2 is hit by P4 (0:06.5) and by P3 (0:08.6). P2 hits P4 at 0:07.9, so watch P2's own red sphere |
| 0:08.8 | First thrown object (magenta) |
| **0:11.9** | Gold **STONE inside** on the chest at (-600, 650). It **opens at 0:35.9**, and a stone pops out |
| **0:17.6** | First chest opening (Flame Thrower, named on the chest beforehand) |
| 0:18.0 | First v4 projectile |
| **0:27.6** | **Bot picks up a Sword.** Check the HUD and the cyan label above P2 |
| 0:30.6 | P3 (Ryoma) holds an Iron Pipe. The uses label above his head counts down |
| 0:39.4 | P1 (Pride) holds a Magic Rod (ranged). Projectiles follow (0:40.0) |
| 0:39.7 | A burst of thrown objects near the bot |
| **0:07.9** | First loose stone, gold `STONE v3#0`. Two stones at 0:26.7 |
| **0:32.9** | **Opponent item swing**: P3 (Ryoma) swings an Iron Pipe. `ITEM SWING (blade spheres)` above him, red blade circles on P2, and the HUD shows `o0:HIT/su(m-37)` (contact margin −37) |
| **1:04.2** | **`STONE 208-only`**: a stone at ledger idx ≥ 110 that the live obs misses |

## slot1_1v1.mp4 (1v1: Falcon (P1, idle, no COM) / Falcon(bot), desert)

Slot 1 is two **human** seats, so P1 never moves. For the first 50 s the bot goes for chests on purpose.

| time | look for |
|---|---|
| **0:05.0** | First hit: P2 hits the idle P1 on the way. P2's red sphere, then P1 `HIT` |
| **0:05.9** | The chest at (950, 300) holds a stone. The HUD line `chests: STONE item` shows it; the chest itself is at the **top edge or just off-screen** here, because the camera frames both players |
| **0:07.8** | **That chest is opened.** The HUD flips to `chests: item item`, and a stone's white glow appears at the top edge (0:08–0:09). Openings in view with the label beforehand are at 0:09.6 onward |
| 0:09.6 / 0:11.2 / 0:11.9 | More openings: Power Shield, Toy Hammer, Medium Bomb. Each was named before opening |
| **0:39.5** | **Bot holds a Magic Rod.** HUD `held: Magic Rod uses 1.00`, dropping by 1/5 per shot |
| **0:41.2** | **Own-bullet fix**: the bot's own Magic Rod shot is drawn **grey** and is not in its obs (HUD `v4 threats 0`). Before the fix this was an orange threat |
| 0:35.0 | Two loose stones (gold `STONE v3#k`) |
| **0:46.0 / 0:49.0** | **Bot swings the Battlefield Axe**: `ITEM SWING` with blade spheres. Hits on the idle P1 follow |
| 0:44.8 | Bot switches to a Battlefield Axe |

**Things that would mean the decode is wrong:**
- a visible loose stone with no gold or orange ring, or a ring on a chest (the old chest-vs-stone confusion);
- an orange or magenta threat marker on a bullet the bot just fired;
- a label that does not match the visible item;
- `STONE inside` on a chest that then drops an item, or the reverse;
- red spheres where nobody is attacking;
- a hurtbox ring that drifts off a player (that would be the projection, not the obs);
- free-run rays that pass through a cactus or the arena edge.
