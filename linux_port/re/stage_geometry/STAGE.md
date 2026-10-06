# STAGE GEOMETRY / SPATIAL AWARENESS — Power Stone 2 RE (Oct 4 2026, instance 5)

Goal: give the bot a sense of walls, obstacles, poles, floor height and stage bounds. Today it sees only its own
absolute x/z/y plus relative opponents, stones and projectiles.

Every claim below names the script that reproduces it and the output file (`out/`), and carries a confidence:
**CONFIRMED** (measured directly, reproducible), **LIKELY** (strong indirect evidence) or **GUESS**.

---------------------------------------------------------------------------------------------------------------------
## 0. TL;DR

1. **The training stage is Desert Area.** That covers states/slot1, slot2 and slot3 (every SLOT_META stage dim; slot1 was
   restamped from menu_match) and all the states_mixed and 3-COM lineups, which their README says are Desert.
   Its geometry is very simple. CONFIRMED:
   - It is a **flat floor at y = 0** with no pits, hazards or water damage. The oasis pond is cosmetic.
   - It is a **hard square clamp box |x|, |z| <= 1140**. The player centre can never leave it, and it does not
     depend on direction or approach.
   - It has **4 tall cacti ("poles")**. Each is a hard cylinder with a player-centre pushout radius of exactly 75.
   - It has **8 round cactus clusters**. These are soft and pushable, with an effective radius of about 120.
   - There is nothing else static. A clean 13,689-point teleport probe (s14) found **zero unexplained pushes**.
2. **The props are dynamic.** In a 7,200-frame lv8 3-COM match (s20), 6 of 8 clusters moved by up to 1,256 u and one
   pole moved 1,061 u. A precomputed map therefore cannot hold them. They are read **live** from the object ledger:
   vtable `0x0C0F18D4` is a pole, `0x0C0F1688` is a cluster, and x/y/z sit at +0x2C/+0x30/+0x34.
3. **The dpad acts in camera space, and the camera yaw is fixed per stage.**
   - On Desert, `up` = world (-x,-z)/√2, `right` = (+x,-z)/√2 and `up+right` = (0,-1). Run speed is 7.2 u/frame.
   - The dpad `up` direction always equals minus the camera back-vector at **0x8C541194**. This is exact on all
     8 stages (s19), so the action frame can be derived live from RAM.
4. **Stage ID**:
   - u32 at **0x8C46E198** (mirror 0x8C472CF8): 0 Blue sky, 1 Dark castle, 2 Tomb, 3 Iceberg, 4 Space station,
     5 Desert, 6 Chaos.
   - Pharaoh walker reuses id 5 and is told apart by the variant byte **0x8C54235E**: 0 normal, 1 pharaoh, 2 chaos.
   - CONFIRMED on 9 states (s13, s16).
5. **The other 6 stages are multi-phase and scrolling.** All 8 stages have empirical walk maps. Their floors move by
   thousands of units: Space station is the elevator (floor 0 → 3500 → 8000), Tomb descends (0 → -10000 → -20000) and
   Dark castle rises to 3300. These need a phase-aware map, which is deferred because the bot trains only on Desert.
6. **Obs-v4 spatial block**: `stage_geom.py` gives 27 floats per step in about 130 µs. It contains:
   - 8 action-frame ray distances (static box plus live props);
   - the nearest pole, nearest cluster and nearest wall (vector and distance);
   - the floor-height channels.

   Validated in closed loop on the live game (s24). For walls the predicted free run matches the actual run with a
   **median error of 4 u** (p90 11 u, n = 74).

---------------------------------------------------------------------------------------------------------------------
## 1. Harness and reproduction

```
cd linux_port/re/stage_geometry
./run.sh <script.py> [args]      # headless, instance_id=5, boot-flake retry, log -> out/<script>.log
```
- `common.py` holds: boot/load, RAM readers, `place()` teleport, `logpos()`, `ledger()` and `STAGE_STATES`.
- `imgutil.py` draws heatmaps with PIL only, because `~/ps2rl` has no matplotlib or scipy.
- **Logical player position** is player struct `P_i = 0x8C532498 + i*0x3938` (from re/player_state).
  - x/y/z are at `P+0x28/+0x2C/+0x30`, and y is the feet (0 on the Desert floor).
  - Teleport means writing both `P+0x28..` and `P+0x94..`.
  - The env's `PLAYER_MAT +0x30` position is a **render bone**, offset about (+14, +150, -11) from the logical
    position (s00). Use the logical one for geometry.
- **Stage savestates** (new, 2-human Falcon vs Falcon, no COMs) are in `states/<stage>.state`. They were stamped from
  `menu_stage.state` by `s11_stamp_stages.py`. Stage-select grid:

  | | col 0 | col 1 | col 2 |
  |---|---|---|---|
  | **row 0** | Blue sky | Dark castle | Tomb |
  | **row 1** | Iceberg (cursor start) | Space station | Random |
  | **row 2** | Desert | Pharaoh walker | Chaos |

  The contact sheet is `shots/s01_sheet.png`. `desert` in the scripts means `states/slot1.state`, the training state.

---------------------------------------------------------------------------------------------------------------------
## 2. Desert Area (stage id 5, variant 0): the training stage

### 2.1 Bounds: a square clamp box at ±1140
**CONFIRMED.**
- **Teleport tests.** Placing P2 at (3000,·,0) gives x = 1140. Placing it at (±3000, ±3000) gives (±1140, ±1140),
  a corner, so the box is square, not round. Placing it at (1100,·,1100) leaves it unchanged.
  Scripts: `s02_teleport_test.py` and `s03_find_bounds.py` (out/s02, s03).
- **Out-of-bounds respawn.** A placement around 5000 u out on the diagonal triggers **state 22**, an out-of-bounds
  respawn drop at (200, 0, 200). Script: `s12_stage_discovery.py`.
- **Walking.** Running head-on into the z = -1140 wall stops dead at -1140 with no auto-jump. Running in obliquely
  slides along the wall at 5.1 u/f (7.2·cos 45°). A jump at the wall lands back at -1140. Script: `s21_wall_tests.py`.
- **Random walk.** 60k frames with 8-way random inputs and jumps covered x and z in [-1140, 1140] exactly, never
  more (`s15_random_walk.py desert`, out/an15_walk.txt).
- **RAM.** The float 1140.0 sits in a record at 0x8C3F2134: (1141, -350, 1140) appears twice, with a mirror at
  0x8C5433EC. These are candidate bounds records (s03/s04). **GUESS:** this is the stage AABB (x half-extent,
  y floor-kill, z half-extent). It is not proven by an edit test.

### 2.2 Floor: flat, y = 0, no hazards
**CONFIRMED.**
- **Clean probe** (`s14_clean_probe.py desert desert_ground -1160 1160 -1160 1160 20 0 20`; heatmap
  `shots/viz14_desert_ground.png`). The method:
  - 13,689 probes on a 20-u grid;
  - savestate restored before every probe;
  - P1 parked in a far corner, with two passes;
  - P2 placed at y = 0 and run for 20 frames.

  Result: final y = 0 everywhere, state 0 everywhere, health delta 0 everywhere.
- **Drop probes** from y = 400 next to props all land at y = 0 (`s09_prop_probe.py`).
- **No floor changes over time.** The idle run showed no floor change in 12k frames, and no words changed in the
  probed block (`s22_stage_phase.py desert`, out/s22_all.txt).
- **Cluster tops.** The random walk recorded "ground" (state 0/1/2) at y ≈ 151 on a few cells next to clusters
  (out/an15_walk.txt: 7 cells). **LIKELY:** a fighter can stand on top of a cactus cluster at y ≈ 151, which is the
  centre of its upper collision sphere. A drop probe straight onto a cluster slid off to y = 0, because the cluster
  gets pushed.

### 2.3 Poles: the 4 tall cacti
Poles are object-ledger vtable `0x0C0F18D4`. Spawn positions: (-1000,-1000), (950,-850), (100,1000), (-1050,800).
- **Pushout: CONFIRMED.**
  - A probe anywhere inside 75 u of the centre ends at exactly 75.0 u, and does so instantly (`s09_prop_probe.py`).
  - All 4 poles ended at a minimum and maximum of 75.0/75.0 in the grid (`an14_desert.py` → out/an14_desert.txt).
  - The pole stays solid up to at least the apex of a jump (y = 331 at a distance of 75; `s10_pole_interact.py`).
- **The ledger record carries collision primitives.**
  - At +0x188 is a header word (0x01FF0204 for a pole, 0x02FF0206 for a cluster: the 2nd byte is the count).
  - At +0x190 are 0x20-byte entries {x, y, z, r, y-copy, …}. A pole is {x, 300, z, 15}. A cluster is
    {x, 80, z, 55} plus {x, 151, z, 60}.
  - **LIKELY:** these are the collision spheres or cylinders. A pole's r of 15 plus a player radius of about 60
    gives 75.
  - Writing 100 into the pole's r field (+0x19C) did **not** change the pushout (s09). Collision is either read from
    another copy or cached. Confidence on the field meaning: GUESS.
- **Not climbable or swingable with the inputs tested: LIKELY.** The tests ran into the pole, then: jumped into it;
  pressed A next to it; held up+A; and pressed B, X or up+B while in contact (`s10_pole_interact.py`,
  `s25_pole_pickup.py`). P2 never entered a new state, and the pole never moved.
- **Can be displaced in real matches: CONFIRMED.** The (100,1000) pole moved 1,061 u during an lv8 3-COM match
  (`s20_desert_dynamics.py` (a)), probably knocked or thrown by a COM.

### 2.4 Cactus clusters: the 8 round groups
Clusters are object-ledger vtable `0x0C0F1688`, resting at y = 100 (the ps2_addr.py "static spawner" `OBJ_KNOWN_UNREPORTED`).
- **Soft pushout: CONFIRMED.** The player is pushed out gradually (about 2.5 u/f), up to a start radius of about
  113–128 (`s09`, `an14_desert.py`).
- **Pushable: CONFIRMED.** Walking into the (-500,1000) cluster for 90 frames shoves it to (-693, 807) (s20 (b)).
  In a lv8 match, 6 of 8 clusters moved by 158–1,256 u (s20 (a)). They never vanished: 8 were alive at every sample
  across 7,200 frames.
- B and three X presses next to a cluster did nothing (s20 (b)).

### 2.5 Chests, opponents and other blockers
- **Opponents are solid.** P1 at the corner pushed probes away; this is why s14 uses two passes. Opponents are already
  in the obs.
- **Chests** (resting at y = 50, already in the obs as the nearest chest) were **not** probed for collision. GUESS:
  they are solid.

### 2.6 Validation of the composite model
**CONFIRMED.**
- `an14_desert.py` (out/an14_desert.txt) compares probe pushes against the model "box ∪ pole r75 ∪ cluster r125".
  - Agreement is 99.13%.
  - **0 pushes are unexplained** by the model.
  - 119 cells are model-blocked but unmoved: cluster rims where the cluster moved instead of the player.
- Map and figure: `build_desert_map.py` writes `data/map_desert.npz` and `shots/map_desert.png`. The figure's panels
  are: probe pushout; walk visits; minimum ray over the 8 dirs; and the dpad-UP ray field.

---------------------------------------------------------------------------------------------------------------------
## 3. Movement frame and camera

**Dpad to world mapping: CONFIRMED** (`s08_dpad_map.py`, `s16_dpad_all.py`).
- On Desert the mapping is constant at every position tested and at t+0 and t+1500:
  - `up` = (-1,-1)/√2, `down` = (1,1)/√2, `left` = (-1,1)/√2, `right` = (1,-1)/√2;
  - `up-left` = (-1,0), `up-right` = (0,-1), `down-left` = (0,1), `down-right` = (1,0).
- Run speed is 7.17–7.20 u/frame (430 u/s).

**The dpad-up angle is fixed per stage** (atan2(z,x), measured; the bot's raycasts must use these frames):

| stage | id | variant | up angle |
|---|---|---|---|
| Blue sky | 0 | 0 | -90.0° |
| Dark castle | 1 | 0 | -135.0° |
| Tomb | 2 | 0 | -123.3° |
| Iceberg | 3 | 0 | -128.5° |
| Space station | 4 | 0 | -144.1° |
| Desert | 5 | 0 | -135.0° |
| Pharaoh | 5 | 1 | -135.0° |
| Chaos | 6 | 2 | 180.0° |

**Camera** (`s17_camera.py`, `s18_camera_dump.py`, `s19_camera_yaw.py`):
- `0x8C541194` holds f32×3: the camera **back vector** (unit, from target to eye). On Desert it is
  (0.593, 0.545, 0.593). **CONFIRMED:** `up = -(back.x, back.z)` normalised matches the measured dpad angle on all
  8 stages to 0.1°.
- `0x8C5411A4` holds f32×3: the camera **eye position**. It moves with the players' midpoint and pulls back as they
  spread. For example, mid (0,0,0) with spread 1131 gives eye (975, 785, 975). **LIKELY:** the target is not exactly
  the midpoint. Several mirrors exist (`0x8C5411B8`, `0x8C5411E8`, …, a stride of about 0x2F8 out to 0x8C541ADC).
- `0x8C00ECE0..EC` holds 4 floats that scale with the player spread: 533 at spread 120, 1885 at spread 1131,
  2296 at spread 1903. **LIKELY:** zoom or frustum distances.

---------------------------------------------------------------------------------------------------------------------
## 4. Stage ID and dynamic stage state

**Stage ID: CONFIRMED** (`s13_stage_id.py` → out/s13_stage_id.txt, `s16`):

| addr | meaning | values |
|---|---|---|
| 0x8C46E198 (u32) / 0x8C472CF8 / 0x8C542237 / 0x8C542360 | stage index | bluesky 0, darkcastle 1, tomb 2, iceberg 3, spacestation 4, desert 5, pharaoh 5, chaos 6 |
| 0x8C54235E (u8) | variant | 0 normal, 1 pharaoh walker, 2 chaos |
| 0x8C542363 (u8) | extra-stage flag | 0xFF normal, 0x02 pharaoh/chaos |
| 0x8C472CF0 / 0x8C472CF4 | stage-select cursor (row, col) | persists into the match |

- Training states slot1, slot2 and slot3 all read id 5, variant 0 (s16).

**Dynamic stage state** (`s22_stage_phase.py <stage> 12000`, both players idle; out/s22_all.txt):
- **Space station is the elevator stage** (CONFIRMED). The floor carrying idle players moves 0 → 3500 (around
  f2400–3600) → 8000 (around f6000+) in 18k frames. Grounded y takes every value in between, so it is a continuous
  lift.
- **Tomb descends** (CONFIRMED): 0 → about -9900/-10000 (around f3600) → -20000 (around f6000).
- **Dark castle** goes 0 → 1600 → 3300 and back to 0. Idle P2 also had respawn states 22/23 here (LIKELY a
  lift/collapse phase).
- **Blue sky** goes 0 → 35 → 1014 → 0 (deck motion, then a fall or landing; state 27 for 3,066 frames in the walk).
- **Iceberg** bobs between -13 and 28 (floating boats), then settles at 298 (onto the iceberg).
- **Pharaoh**: the idle player ends up riding the walker (y ≈ 680–860, state 41 for 13,765 frames in the walk). It is
  also the most damaging stage: 61 non-respawn health drops in 60k frames.
- **Chaos** is a corridor at z ≈ 7400 with raised platforms at y ≈ 800–830.
- **Desert** is static (CONFIRMED).
- **Negative result:** `0x8C471A78` tracked P2's y perfectly on every stage, but it is part of a **player-position
  mirror block** (0x8C471A60..), not a stage floor. It follows P2 into the air on a jump (`s23_ground_cell.py`).
  No dedicated elevator-height or phase variable was isolated. The best phase signal today is the stage id plus the
  player's own grounded y.

---------------------------------------------------------------------------------------------------------------------
## 5. All-stage empirical walkability maps (Goal 1)

`s15_random_walk.py <stage> walk_<stage> 60000 7` runs P2 for 60k frames. It holds a random 8-way dpad direction for
20–90 frames at a time and adds A on 15% of segments. P1 is idle. The analysis is `an15_walk.py`, which writes
`data/map_walk_<stage>.npz` with 25-u cells:
- `visits`: occupancy;
- `floor`: median y while grounded, i.e. states 0/1/2;
- `ymax`;
- `stalls`: dpad held, state 1, speed < 1 u/f, i.e. pressing into a wall;
- `respawn_xyz`;
- `dmg_xyz`.

Heatmaps are in `shots/walk_<stage>.png`, with panels for visits, ground y and wall stalls; Tomb adds per-phase
panels. Summary (out/an15_walk.txt):

| stage | x range | z range | grounded floor levels (y: cells) | respawns | health drops (non-respawn) |
|---|---|---|---|---|---|
| desert | -1140..1140 | -1140..1140 | 0: 3412, ~150: 7 (cluster tops) | 0 | 0 |
| bluesky | -2070..1816 | -970..1898 | -100…0 deck, 100–150, 380, 500 | 63 (falls off; kill y ≈ -1250) | 5 |
| darkcastle | -2443..2040 | -1635..1390 | 0, 20–100, 3300–3400 | 13 | 8 |
| tomb | -5062..7651 | -920..810 | 0 / -10000 / -20000 (3 rooms) + 250, 550 | 8 (kill y ≈ -10950 in room 2) | 43 |
| iceberg | -790..1540 | -735..1440 | -20…20 (boats), 140, 220, 300 | 0 | 4 |
| spacestation | -1010..910 | -915..910 | 0 → 3500 → 8000 (lift) | 17 | 8 |
| pharaoh | -2462..2032 | -1561..1146 | 0, 20–100, walker 2700–3300 | 6 | 61 |
| chaos | -2206..534 | -1290..7660 | 0, 100–200, 800–830 | 0 | 66 |

Caveats:
- The random walk sometimes picked up gems and **transformed** P2 (Falcon's flying form: states 25/44). This explains
  why Desert shows y up to 721 and 66% airborne frames. Only grounded samples feed `floor`.
- **Teleport probes cannot find walls on the mesh stages.** On Tomb, a teleport to x = 5840 stood at y = 0 (s12).
  These stages do not resolve penetration the way the Desert clamp does, so walls must be found by walking. That is
  why Goal 1 used the walk for the other stages.

**LIKELY:** each of these stages needs a (phase, x, z) map. The walk data mixes phases, except Tomb, which is split
into bands in `data/map_walk_tomb_bands.npz`.

**Collision mesh in RAM: not found** (time-boxed). Next step: walk into a known Tomb wall and diff RAM for the frame
in which the slide starts, or locate the stage model's collision list via the ledger records' +0xC0 pointer
(0x0C3F1124 / 0x0C3F15A4 point into a 0x8C3F.. block next to the 1140/-350 record).

---------------------------------------------------------------------------------------------------------------------
## 6. Obs-v4 spatial encoding (Goal 3)

`stage_geom.py` is numpy only. It precomputes in 0.7 s once per stage, then costs about 115–230 µs per call
(`t_stage_geom.py`). `SPATIAL_DIM = 27`, all in the **action frame**, so ray k points where dpad direction k actually
moves the fighter:

| dims | feature | how it is computed each step |
|---|---|---|
| 0–7 | free distance along dpad up, down, left, right, up-left, up-right, down-left, down-right ÷ 1000 (1.0 = clear ≥ 1000 u) | `min(static_ray[k][cell], ray_vs_circle(live props))`. The static rays are precomputed per 10-u cell by a world-space march over the walkable grid (the box). Props come from the ledger each step: pole r 75, cluster r 120, skipped if `abs(prop_y - my_y)` exceeds 400/300. |
| 8–10 | nearest pole (right-component, up-component, distance) ÷ 1000 | live ledger |
| 11–13 | nearest cluster, same layout | live ledger |
| 14–16 | nearest wall / boundary point, same layout | precomputed nearest-boundary field (exact brute force on boundary cells, once) |
| 17 | (my y − floor under me) ÷ 500 | floor grid (Desert: 0); this is "height above ground" |
| 18–25 | floor 150 u ahead in each dpad dir − floor here, ÷ 500 (no floor → -1) | floor grid; all 0 on Desert, and the ledge / step channel for multi-level stages |
| 26 | map-present flag | 1 if a map exists for (stage id, variant), else the whole block is 0 |

Notes:
- Dims 8–16 use action-frame components: projection on the dpad `right` and `up` world vectors. This lets the policy
  read "the pole is up-left of me" in its own button space.
- The dpad frame comes either from the stage table or live from the camera (`dpad_dirs_from_camera(ram)`,
  0x8C541194). Both are identical because the yaw is fixed per stage (s16 at t+0/t+1500; s19).

**Closed-loop validation** (`s24_validate_rays.py` → out/s24_validate.txt, `data/s24_validate.npz`). The test:
1. Restore the savestate and teleport P2 to a random point.
2. Compute the encoder with live props and the live camera frame.
3. Hold a random dpad direction for 160 frames.
4. "Actual" = progress along that direction when the 6-frame mean speed along it first drops below 6 u/f. Free run
   is 7.2 u/f, and a 45° wall slide is 5.1 u/f.

| blocker the model predicts | n | median abs err | p90 | comment |
|---|---|---|---|---|
| box wall | 74 | **4.3 u** | 11.2 u | CONFIRMED |
| pole | 19 | 42.9 u | 413 u | head-on hits are exact; grazing hits deflect less than the detector threshold, so the fighter keeps running past |
| cluster | 45 | 20.7 u | 347 u | clusters are pushed, so the fighter travels a little further than the ray |
| nothing within 1000 | 90 | — | — | 93% ran ≥ 1000 u unobstructed; min travel 1002 |

### 6.1 Ready-to-paste integration
`linux_port/re` shadows Python's `re` module, so **copy** `stage_geom.py` to `linux_port/stage_geom.py`. Then
subclass, or patch `PowerStoneEnvLibretro`, which owns the live RAM view as `self._lr_bridge.ram`:

```python
# powerstone_env_libretro.py  (obs-v4 spatial block, opt-in: PS2_OBS_V4=1)
import os, struct
import numpy as np
import stage_geom as SG

OBS_V4 = os.environ.get("PS2_OBS_V4", "0") == "1"
_P0, _PSTRIDE = 0x8C532498, 0x3938          # player struct; logical x,y,z at +0x28/+0x2C/+0x30

class PowerStoneEnvLibretro(PowerStoneEnvV6):
    if OBS_V4:
        OBS_DIM = PowerStoneEnvV6.OBS_DIM + SG.SPATIAL_DIM     # appended at the END: old dims keep their meaning
    def __init__(self, *a, **kw):
        super().__init__(*a, **kw)
        self._sg = SG.SpatialEncoder() if OBS_V4 else None    # 0.7 s one-off precompute (desert box)
    def _observe(self, s, prev):
        obs = super()._observe(s, prev)
        if self._sg is None:
            return obs
        ram = self._lr_bridge.ram
        p = _P0 + (self.AGENT_PLAYER - 1) * _PSTRIDE + 0x28
        x, y, z = struct.unpack_from("<3f", ram, p & 0xFFFFFF)
        obs[-SG.SPATIAL_DIM:] = self._sg(ram, x, y, z)       # already ~[-2, 2]; env clips to +-5 anyway
        return obs
```
- Note that `super()._observe` allocates `np.zeros(self.OBS_DIM)` and returns `np.clip(obs)`, so the block above
  writes into the last 27 dims of the same array.
- Widening OBS_DIM orphans the input layer of existing checkpoints. Use the surgery_widen.py path the project already
  has for obs v3.
- For the FFA/self-play envs, call the encoder per seat with that seat's logical position.

**Why these features (priorities for the bot):**
1. **Rays 0–7** answer the question the policy actually faces: "if I press this direction, how far can I run before
   hitting something?" On Desert that is the box edge (cornering, being cornered, wall-trapping an opponent) and the
   poles and clusters.
2. **Nearest wall vector** helps it avoid getting pinned and lets it learn to pin others.
3. **Pole and cluster vectors** cover cover-from-projectiles, footsies, and cluster tops as a ~150 u platform.
4. **The floor channels** are 0 on Desert today. They exist so the same bus serves Space station, Tomb and the other
   stages once phase maps exist (the `maps` dict takes `StageMap.load(npz, dirs)`).

---------------------------------------------------------------------------------------------------------------------
## 7. Open items / what I could not settle

- **Collision mesh / static wall list** for the non-desert stages: not found (§5). Needed for exact maps there.
- **Pole swing/climb**: no input combination tested (§2.3) produced a grab. Power Stone's pole-swing may exist only on
  specific stage objects (bars or lamps on other stages). Untested.
- **Chest collision** was not probed (GUESS: solid).
- **Stage phase variable** (elevator height, tomb room): not isolated. Use the stage id plus own y as a proxy.
- **Cluster standability at y ≈ 151** is only seen in the walk (LIKELY); no targeted test was run.
- **The 0x8C3F2134 (1141, -350, 1140) record** as the stage AABB is a GUESS; no edit test was run.

---------------------------------------------------------------------------------------------------------------------
## 8. File index (all under linux_port/re/stage_geometry/)

| file | what |
|---|---|
| `STAGE.md` | this report |
| `stage_geom.py`, `t_stage_geom.py` | **obs-v4 encoder** + offline unit test |
| `common.py`, `run.sh`, `imgutil.py` | harness (instance 5), runner, PIL heatmaps |
| `s00`–`s25_*.py`, `an14_desert.py`, `an15_walk.py`, `build_desert_map.py`, `viz14.py`, `viz_probe.py`, `run_walks.sh` | experiments, analyses and builders; each docstring states its question |
| `out/*.log`, `out/*.txt` | outputs; logs hold the latest run of each script |
| `data/map_desert.npz` | **shipped Desert map**: x0, z0, res = 10, walk, floor, spawn_poles, spawn_clusters |
| `data/map_walk_<stage>.npz` (+ `map_walk_tomb_bands.npz`) | empirical walk maps for all 8 stages |
| `data/s14_desert_ground.npz` | clean 20-u teleport probe of Desert |
| `data/s15_walk_<stage>.npz` | raw 60k-frame walk logs (x, y, z, state, dpad, hp per frame; about 0.5 MB each) |
| `data/s24_validate.npz` | ray validation trials + trajectories |
| `data/s13_stage_id_windows.npz`, `data/s17_camera_cands.npz` | small RAM windows behind the stage-id and camera findings |
| `states/<stage>.state` | 2-human Falcon savestates for all 8 stages (`desert_menu` = menu-stamped desert) |
| `shots/map_desert.png`, `viz14_desert_ground.png`, `walk_<stage>.png`, `s01_sheet.png` (stage select), `s07_sheet.png` (props), `s00_slot1.png`, `s20_*.png`, `s25_contact_X.png` | cited figures (screenshots: `s01`/`s07` are montages; images are stored upright) |

The folder is about 67 MB. The raw full-RAM capture used for the stage-id search was deleted after analysis, per the
disk budget. `s13_stage_id.py` regenerates the small windows.
