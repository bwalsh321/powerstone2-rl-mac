# Obs v4 proposal: "give the bot as good vision as possible"

Status: **PROPOSAL, not applied.** Blake approves any change to the live observation contract. Nothing outside
`linux_port/re/obs_v4/` was modified, and nothing was committed. Oct 4 2026, upstream leg 121, Mac instance 8.

Files in this folder:

| file | what |
|---|---|
| `obs_v4_reader.py` | The reader: `ObsV4Reader(ram).features(seat, opp_order, frame) -> (vec[270], info)`. Numpy only, vendored, seat-generic |
| `test_obs_v4.py` | Live tests on slots 1/2/3, the env-integration parity test, FFA `_obs_from_view`, and threat-owner / item-swing checks against the game's own fire and hit events. Writes `obs_v4_stats.txt` |
| `obs_v4_stats.txt` | Per-feature distribution over 18,000 frames × 4 seats (non-zero fraction, min, max, mean) |
| `surgery_widen_v4.py` + `test_surgery_v4.py` | 160 → 430 warm-start surgery for PPO-MLP **and** SkipLSTM RecurrentPPO, with an offline exactness check |
| `measure_item_emb.py` | Measures how much a trained policy leans on obs[12..17] (the slot-hash item embedding) |
| `obs_v4_envpatch.py` | The INTEGRATION.md env change as a mixin (`with_obs_v4(EnvClass)`), used by the tests |
| `equivalence_v4.py` | Live surgery check: widened vs parent on real v4 frames (MLP and SkipLSTM) |
| `stage_geom.py` | **Vendored** from `re/stage_geometry/` (block H: the 27-dim spatial encoder). It is copied rather than imported because `re/` shadows Python's `re` module |
| `calibrate_projection.py`, `projection.json` | World → screen for the overlay: RAM camera plus intrinsics fitted by ablation (accuracy in section 10) |
| `overlay_v4.py`, `videos/*.mp4`, `videos/WATCHLIST.md` | **Overlay videos** (3 × 75 s): v4 decode drawn on the real frames, with timestamps of what to check |
| `INTEGRATION.md` | Step-by-step adoption for Blake |

## 1. Design in one paragraph

**v4 = v3's 160 dims, byte-identical, + 270 appended dims = 430 per frame.** The one exception is the opt-in
[12..17] change (section 3). Because the prefix is unchanged and the new input columns start at zero, warm-start
surgery reproduces the current policy exactly. That is the same mechanism as `surgery_widen.py` (122 → 160) and
`surgery_lstm.py`. Measured:
- offline, logit and value diff = 0.0 for MLP and SkipLSTM;
- live (`equivalence_v4.py`, 600 steps on a real checkpoint widened 122 → 160 → 430), max logit diff 7.6e-6 and
  greedy agreement 600/600;
- the env-integration test shows v3-prefix parity 1.0000 over 1,201 observation builds.

Every v4 feature comes from guest RAM through the game's own structures:
- the player struct `P_k = 0x8C532498 + k*0x3938`;
- the 208-slot object ledger at `0x8C4FBD30`, stride 0x430.

The v3 pool-class whitelists are not used. Those whitelists are lineup-dependent, so v4 stays correct on lv8mix
lineups. Older pool seats keep their contract, because FFA already feeds `obs_v[:dv]` and the prefix is unchanged.

## 2. Blocks, by expected value to the bot

Total appended = 270. Offsets are absolute obs indices.

| prio | block | obs | dims | what the bot gains | measured activity (P2 view, slots 2/3) |
|---|---|---|---|---|---|
| 1 | **A melee threat** | 160–196 | 37 | Per opponent (nearest-first, the same order as the v2 opponent block), 11 dims:<br>• live hit sphere nearest **my hurt cylinder**: offset, radius, contact **margin** (≤ 0 = this frame would hit), hitbox age. The spheres include a **swung held melee item's blade** (section 5b);<br>• **P+0x414 attack-startup flag** (median 9 frames of warning) plus its age;<br>• body-hitbox flag P+0x124;<br>• **item_swing** flag.<br>Self, 4 dims: my live hitbox, my best margin to any opponent, my startup flag, my item swing | spheres live 4–8% of opponent-frames; startup flag 7–16% |
| 2 | **B projectile / thrown threats** | 197–230 | 34 | 3 nearest **enemy** ledger threats, 11 dims each:<br>• category-1 hit volumes. My own are dropped, using the +0x14 owner chain or, when it has none (item bullets, Pete's soldiers), the **header owner byte +0x05** (section 5b). Bomb blasts are kept even when they are mine;<br>• thrown items and props in flight (category 9, state 8);<br>• the category-2 crawler.<br>Each slot gives position, velocity, radius and a thrown flag, plus derived **time / distance of closest approach** (a product the MLP would otherwise have to learn). One extra dim: a crowd count within 600 u for volleys | ≥ 1 threat on 31.5% of frames (slot 2 and 3), versus 18.4% for v3 (PROJECTILES.md) |
| 3 | **C ground items, props, chests** | 231–274 | 44 | 3 nearest free items (position, ready, 5-way class: melee/ranged/thrown/food/other). The nearest ready throwable prop (cactus, crate, saguaro). 2 nearest chests with **has_stone** from `+0x42C` | items on 57% of frames, chests on 93%; a stone chest is visible on 17% |
| 4 | **D true held items** | 275–298 | 24 | Self and 3 opponents: 5-way class (melee, ranged-long, ranged-short, thrown, other) plus **uses fraction** (ammo, durability, bomb fuse), read from the held record's `+0x420/+0x424` | someone holds something on 20–83% of frames |
| 5 | **E state refinements** | 299–336 | 38 | Self and 3 opponents: invulnerable, airborne, vy, hurt half-height (down / getting up), knocked down, held-by-opponent, grabbing, state age. Per opponent: "last hit me" (game attribution), "COM is targeting me" | invulnerable 3% (opponents), airborne 21–36% |
| 6 | **F character ids** | 337–392 | 56 | One-hot over the 14 selectable characters, for self and 3 opponents. Matters for lv8mix lineups and for pool policies driving other characters | 6 lineups present in tests |
| 7 | **G globals** | 393–402 | 10 | Fight-live flag, menu-open flag, stage-id one-hot (7 stages), stage variant flag (Pharaoh walker / Chaos) | stage 5 (Desert) on all test states |
| 6b | **H spatial** (stage geometry) | 403–429 | 27 | `stage_geom.SpatialEncoder` at my **logical** position, in the **action frame** (ray k points where dpad k moves me):<br>• free run along the 8 dpad directions (the Desert ±1140 box plus live poles r75 and clusters r120);<br>• nearest pole, cluster and wall (right/up components plus distance);<br>• height above the floor;<br>• floor height 150 u ahead × 8;<br>• map-present flag.<br>Desert only (map_present = 0 and the block is zeros on other stages). Section 6 | rays below 1000 u on most frames; pole/cluster/wall always present on Desert |

Dims that never fired in the tests are all explained:
- character one-hots for the 8 characters that are not in the test lineups;
- the "other" item class;
- stage ids other than 5 (desert) and the variant flag;
- the menu flag;
- floor-ahead channels that are 0 on the flat Desert floor (they fire only at the box edge, where there is no
  floor ahead).

There are no unexplained dead features (`obs_v4_stats.txt`).

**Possible trims** if 430 is too wide (none of these affect the surgery):
- F self (14 dims): the learner is always Falcon, but pool views are not, so this is not recommended.
- G stage one-hot (8): the training states are all Desert.
- H floor-ahead channels (8): always 0 on Desert except at the edge, so the rays already cover it.
- C items 3 → 2 slots (10).

The cost of width is small here (section 7).

## 3. The item embedding [12..17]: recommendation

**Finding (CONFIRMED twice, then independently verified).** F+0x54 is a pointer to the held object's own ledger
record plus 4. It is not an item-definition pointer.
- `re/verify/v1_out.txt`: 29 distinct pointers, all on the 0x430 grid with residue 0x1E4. Two of the pointers
  carried different item types.
- So `bucket = (ptr // 0x430) % 256` encodes **which arena slot** the item happens to occupy. obs[12..17] is a
  fixed random 6-vector per slot. It carries **no item identity**: the same Hammer gets a different code each
  match, and one slot serves many items. obs[11] (has_item) is correct and stays.

**Does the trained policy read it anyway? Measured with `measure_item_emb.py`** on the two v2 checkpoints on this
Mac (sweep40, K=1, 122/frame). The current SkipLSTM lineage lives on the 9950X; rerun the tool there.

| model / slot | steps with a non-zero embedding | greedy agreement, real vs [12..17]=0 | action-distribution TV distance on those steps | value change |
|---|---|---|---|---|
| sweep40_ctrl, slot 3 (lv8) | 67 / 2000 | 67 / 67 | mean 0.016, p90 0.053, max 0.20 | 0.95 |
| sweep40_lr1e4, slot 2 (lv3) | 9 / 2000 | 6 / 9 | mean 0.28, p90 0.71 | 0.50 |

So the network does react to this slot noise. One model barely does. The other swings its action distribution a
lot and flips the greedy action on 3 of 9 holding steps. Its value head moves by 0.5–1.0 return units. That is
fitted noise.

**Recommendation: zero it for v4 consumers, and drop it from the surgery parent's columns.**
- Env flag `PS2_OBS_V4_ITEMEMB=zero` (default with v4) writes 0 into obs[12..17] **only when the consumer is a v4
  (430) model**.
- v2/v3 pool seats keep the hash. It is the contract they were trained on, and FFA knows each seat's `dv` (the
  same pattern as `_legacy_proj`).
- The true item class moves to block D, for self **and** opponents.
- Do not repurpose [12..17] with the true class. The parent's weights on those 6 columns were fitted to the slot
  code, so new semantics there would read as a confusing old signal. Zero weights plus zero inputs is clean, and
  the D block's columns start at zero like every other new input.

**Surgery implication.** `surgery_widen_v4.py --zero-item-emb` also zeros the parent's columns for obs[12..17],
in every lag slot and in the LSTM input. The widened policy then equals *the parent evaluated with
obs[12..17] = 0*. That is exact (test_surgery_v4: diff 0.0) but **not** bit-identical to the parent on real
frames. The difference is confined to steps where the bot (or, for views, that seat) holds an item: 0.5–3% of steps
in the runs above.
- Gate: run `measure_item_emb.py` on the live lineage zip. Proceed if greedy agreement on holding steps is ≥ 90%;
  otherwise widen without `--zero-item-emb` first (exact), and zero the embedding one leg later.
- Fallback (fully exact): keep the hash in v4 (flag `PS2_OBS_V4_ITEMEMB=keep`) and let training learn to ignore it
  next to the true class in D.

## 4. Production bugs: fix in place or append?

| bug | evidence | what v4 does | does the fix change existing dims? |
|---|---|---|---|
| **OBJ_GRID_N = 110** (should be 208) in `ps2_addr.py` and used by `StateLineSynth._obj_scan` | GROUND.md 0.6: live records reach idx 139 (the arena is 0..207); misses 6.5% of chest and 8.6% of stone sightings. **Verified independently**: max live slot 125, 1,808 sightings at idx ≥ 110 in one run | v4's own ledger reads use 208. Blocks C and B are correct regardless | **Yes, values only.** Stones [57..80] and the chest [107..110] gain the objects they were missing. The meaning is unchanged, so this is a bug fix, not a re-definition. Recommend fixing in place (`OBJ_GRID_N = 208`) **as its own change**, with the usual 50-episode parity eval, either before or at the v4 cutover. It changes the obs for v2/v3 pool seats too, in the same direction (they now see stones and chests that were really there). It does not affect surgery exactness, because the equivalence check feeds the same obs to parent and child |
| **Item key** (F+0x54 treated as an item-definition pointer) | Section 3 | Block D carries the true class and uses, for self and opponents | [12..17] → zero for v4 consumers (opt-in; a contract break confined to 6 dims, measured above). `ITEM_NAMES` / `item_bucket` in the env are misleading for telemetry and should be relabelled; they are not obs |
| **Lineup-dependent projectile whitelist** (`PROJ_CLASSES`, `PROJ_EXCLUDE`, the band comments in `ps2_addr.py`) | PROJECTILES.md TL;DR 1: pool class words are model-data addresses that move with the lineup (Falcon missile 0x0C7FABC8 → 0x0C808BC8). `PROJ_EXCLUDE`'s "explosion" 0x0C7FABC8 is really Falcon's missile body in lineup A. Thrown items are hidden by the 0x0C6 band | Block B replaces the role. It uses ledger category 1 (lineup-independent vtables), owner chains and the category-9 state byte. No whitelist | **Appended, so no change.** The v3 slots [81..92]+[154..159] stay as they are (v2/v3 contracts, `_legacy_proj` unchanged). Rewriting the pool rule in place would change those dims' values for every trained model, so it is not recommended. Once a v4 lineage is established, the v3 slots could be zeroed for v4 consumers in a later measured step (the same pattern as [12..17]). Also relabel the ps2_addr comments as "valid for the slot3 lineup only" |

## 5. Where the RE docs conflict (and what v4 uses)

| topic | conflict | v4 uses |
|---|---|---|
| Ledger size | `proposed_ledger_threats.py` LEDGER_N = 150; GROUND.md: 208 (idx 208 is the arena manager) | **208** (CONFIRMED plus independent verification) |
| Melee hitbox geometry | PROJECTILES.md (f): "a geometric hitbox radius was not found". RECONCILE.md: P+0x1AC is only an "approximate strike point" (44% within r+50 of the victim). PLAYER_STATE.md 1b: full record list (count at P+0x187), contact test precision 1.000 / recall 0.978 on 14 characters | **PLAYER_STATE** (CONFIRMED). RECONCILE measured against PLAYER_MAT+0x30 (render, hip offset +85) and only the first sphere, which explains its weak fit |
| P+0x414 | PLAYER_STATE: GUESS (set on 44% of state-7 frames). RECONCILE: on for 41/41 melee hits, median lead 9 frames, and on no later than +0x124 for 39/41 | Used as the **startup warning** (it marks the moves that hit). Its duty cycle covers only part of attack frames, so the A block also carries the sphere and state (via E) |
| P+0x134 | "move id" (PROJECTILES) versus "grounded bit 0x400" (PLAYER_STATE) | Both are true: byte 0 = move id, byte 1 bit 0x04 = grounded (RECONCILE). v4 reads **byte** P+0x135 |
| Hit-sphere records | PLAYER_STATE: "records past the count are stale" | **New:** records *inside* the count can be empty too (header 0, r 0 at the origin; seen in Ryoma's power special, act 0x11b). v4 accepts a record only if `hdr & 0xFFFF == 1` and r > 0. Without this filter you get phantom spheres at the world origin |
| Thrown objects | PROJECTILES: category 9 with velocity ≥ 600, gated by an observed-motion history (stale +0x50 after a respawn). GROUND/ITEMS: state byte +0x421 = 8 means thrown in flight (CONFIRMED) | **State byte** (8, or 6 with ≥ 600 u/s). It is stateless, so it works at the env's 6–10 frame cadence. A thrown cactus flies about 10 frames, and the history gate would reject the first (often only) sighting |
| Stage id | PLAYER_STATE: 0x8C472CF8 / mirror 0x8C46E198 = {0 ship, 1 garden, 3 iceberg, 4 space, 5 desert}, LIKELY (6 menu-built stages). stage_geometry: the same cell (also 0x8C542237, 0x8C542360) = {0 Blue sky, 1 Dark castle, 2 Tomb, 3 Iceberg, 4 Space station, 5 Desert, 6 Chaos}; Pharaoh walker reads 5 and is disambiguated by the variant byte 0x8C54235E (0/1/2). CONFIRMED on 9 states built for all 8 stages | **stage_geometry's names** (it built and visited every stage). The two agents agree on the address and on 3/4/5. "ship" vs "Blue sky" (0) and "garden" vs "Dark castle" (1) are naming differences for the same stages, as seen in the stage-select grid. v4 one-hots ids 0..6 plus a variant flag |
| `CHEST_FALL_VT` | ps2_addr: "falling chest". GROUND: the generic item class; `fallN` counts weapons, including held ones | Not used (v4 classifies by the type byte) |
| F+0x54 "definition pointer" | env docstring versus both item agents | Record+4 (section 3) |
| Player position | The env (v2/v3 dims) uses PLAYER_MAT+0x30, a **render bone** offset about (+14, +150, −11) from the logical position P+0x28 (stage_geometry s00) | **v4 uses the logical position everywhere** (relative vectors, threats, items, chests, spatial rays, hurt cylinder). See the note below this table |
| Owner of category 1 | GROUND: "LIKELY character-owned". PROJECTILES: owner chain +0x14, validated against the game's hit attribution; item bullets have no chain | Chain first, then **header byte +0x05 = owner seat** (new, section 5b) |
| Category byte +0x04 = 1 | PROJECTILES: "category 1 means a live hit volume". VERIFY 6b: zeroing it does **not** stop the hit (22/22) | Used only as a **selection label** for finding hit-volume records, not as a liveness gate. That is all v4 needs |

**Logical vs render position (surgery implications).** The v2/v3 dims stay on the render position: self abs x/z/height,
opponent dx/dz/dy, stone/chest/projectile dx/dz/dy. Moving them to the logical position would change values that
every trained policy reads, which breaks the contract and the exact surgery, for little gain:
- horizontally the bone offset is about 15 u against POS_SCALE 1000, so negligible;
- vertically it is about +150 u, but it cancels in opponent dy (render − render). It biases stone/chest dy by a
  near-constant −0.3, which the network has long since absorbed.

v4 is internally consistent on the logical position, which is also what the game's collision tests use (hurt
cylinder, spheres, map). The network sees both frames without conflict, because each feature is used consistently
within itself. If a future fresh model is ever trained (no surgery), switch the v2/v3 dims to logical at that point.

## 5b. New findings from this integration (Oct 4)

**Threat owner = ledger header byte +0x05.** A category-1 record's header byte 1 holds the owner seat (0xFF = none),
the same byte GROUND.md calls "holder seat" for category 9. Measured by `test_obs_v4.py` part `owner` (slots 1/2/3,
90/240/240 s, every frame) against the game's own events:
- it equals the +0x14 chain owner on **355/355** chain-owned volumes (slot 2 123, slot 3 232);
- for **item bullets** (no chain): the seat in byte 1 holds a ranged item at the bullet's birth on **136/136**. It
  equals the seat whose gun/rod counter ticked 0–3 frames before the birth on **114/116** (5/5, 77/77, 32/34). Both
  misses are one item class (`0x0C16BF02`, delayed, Ray-Gun-like) born while a *different* seat's bazooka fired, so
  the fire-window truth is the ambiguous side there;
- it also names the owner of Pete's toy soldiers (unowned by chain).

v4 drops my own volumes from block B, except the bomb blast and explosion classes (`SELF_HARM_VT`). Self-damage from
those is not ruled out. Result: P2's obs carried **0** of its own item bullets while carrying 477 item bullets in total (test check (c)). This
fixes the "dodging its own shots" defect. `_hit_source` ("last hit me") uses the same fallback, and agrees with the
chain owner on **195/195** projectile hits (test check (e)).

**Held melee-item swings have their own hit spheres in the ITEM's ledger record**, not in the player list (VERIFY 2:
P+0x187 never exceeds 1 during a swing).
- The layout mirrors the player list. At record +0x188 the header has low u16 == 1 and byte 3 = count (3 for an
  axe or sword). Spheres sit at +0x188 + 0x20·j with x, y, z at +8/+0xC/+0x10 and r at +0x14 (r = 40 for the axe).
- A header of 0x01FF0104 is a different (pickup) volume and is ignored.
- The spheres follow the blade during the swing.
- Live while the holder is in state 7/8 and the record is in state 7 ("held and in use").
- **Measured against the hit-source pointer** (victim P+0x3774 == the held record + 4):
  - test part `owner`: **22/22 item-melee hits** had reader contact (margin ≤ 0) on the hit frame or the frame
    before (2/2 slot 1, 10/10 slot 2, 10/10 slot 3);
  - window level (probe): TP 19, FP 5, FN 0. "FP" here is a swing window in contact without damage, e.g. the
    victim was already reeling;
  - confidence: CONFIRMED-CORRELATIONAL, the same class as the player spheres.
- Block A merges these blade spheres into the opponent's sphere set, so offset, radius and margin cover swords and
  hammers, and adds an `item_swing` flag per opponent and for self (+4 dims).
- Same caveat as the player spheres: the game rewrites them every frame, so they are **correlational** observations
  (exact geometry), not something a frontend can drive.

Category-1 projectile records use the same sphere layout. That is why PROJECTILES saw a "radius candidate" at +0x19C
(= the first sphere's r at +0x188+0x14) and a "second extent" at +0x1BC (the second sphere). Block B still reports only
the first radius; using the full list is a possible refinement.

## 5c. Confidence after the independent intervention tests (`re/verify/VERIFY.md`)

| feature | label |
|---|---|
| chest has_stone / contents `+0x42C` | **CONFIRMED-CAUSAL** (65/65 forced contents spawned exactly) |
| held type `(F+0x54)-4+0x420` | **CONFIRMED-CAUSAL** (type swaps change behaviour 8/8) |
| uses `+0x424` | **CONFIRMED-CAUSAL** decrement rules. The counter is set **at spawn**, not at pickup, so uses_frac (counter ÷ table initial) is right for natural items |
| ledger projectile position (block B) | **CONFIRMED-CAUSAL** (moving the record stops its hit, 22/22) |
| hit spheres / contact margin (A) | **CONFIRMED-CORRELATIONAL**: the contact test is exact (132/132 placements, ±1 u boundary). The game recomputes the fields each frame, which is fine for observation |
| invulnerable mask (E) | **CONFIRMED-CORRELATIONAL** (150/150) |
| category byte +0x04 = 1 | selection label only (**REFUTED** as a liveness gate) |
| stage id | the verifier found it INCONCLUSIVE on desert-only states (constant 5). stage_geometry CONFIRMED it on 9 states across all 8 stages, and v4 uses that |

## 6. Spatial block (stage geometry, integrated)

obs[403..429] = `stage_geom.SpatialEncoder` (vendored from `re/stage_geometry/stage_geom.py`, STAGE.md section 6),
evaluated per seat at that seat's logical position.
- Live props (poles `0x0C0F18D4`, clusters `0x0C0F1688`) come from the reader's shared 208-slot ledger scan. This
  avoids the encoder's own 170-slot Python loop. The test checks that the result equals the encoder with its own
  ledger read, bit for bit, on every learner sample.
- The **action frame** uses the per-stage dpad table, which equals −camera-back from RAM on all 8 stages.
- **Confidence**:
  - box-wall rays: median error 4 u (p90 11 u, n = 74; closed-loop runs in the live game);
  - pole rays: head-on hits exact, but p90 413 u, because grazing hits deflect the fighter past;
  - cluster rays: p90 347 u, because clusters are pushed;
  - so rays are CONFIRMED for walls and LIKELY for props.
- **Stages**: Desert is fully mapped. The other 6 stages are multi-phase and scrolling (elevator, descending tomb),
  have only rough walk maps, and get `map_present = 0` with the block all zeros. Training is Desert-only today.
- **Cost**: about 0.13 ms of the per-seat assembly (12 ray-circle tests plus lookups). It could be vectorised
  across props if needed.

## 7. Cost (measured, M4 Mac, Python, instance 8)

| quantity | value |
|---|---|
| shared RAM scan (player structs + 208-slot ledger + held-item blade spheres), once per emulator frame | **0.147 ms** mean (p99 0.28) |
| per-seat assembly, including the spatial block (≈ 0.13 ms of it) | **0.164 ms** mean (p99 0.26) |
| learner-only env step | ~0.31 ms |
| FFA step (learner obs plus 3 `_obs_from_view`; one scan shared, 0.251 scans per build measured) | ~0.80 ms |
| training budget | 365 steps/s over 16 actors ≈ 44 ms per actor step → v4 adds **≈ 1.8%** (FFA). Vectorising the spatial props loop would bring it near 0.8% |
| network | first layer 7 × 430 = 3,010 inputs (was 1,120); LSTM input 430 (was 160). Negligible CPU inference (~1.5M MACs). The rollout obs buffer grows about 2.7× (about 49 MB at 256 × 16 × 3,010 float32) |

The slot-3 timings in one run were 2× higher because other agents' emulators were loading the machine at the time.
The numbers above are from the unloaded slot-1/2 runs.

## 8. Open risks

1. **Own bomb blasts stay visible** as threats (`SELF_HARM_VT`), because self-damage was not tested. Volumes with no
   owner at all (byte 0xFF and no chain: rare, e.g. some item blasts) are reported to everyone. The own-bullet
   defect is **fixed** (section 5b).
2. **Clocks have step resolution.** Hitbox, attack-window and state ages are measured at the env's sampling
   instants (6–10 frames), so onsets can be up to one step late. This is deterministic and consistent between
   training and eval.
3. **The reader needs ONE frame counter per emulator.** In the integration, pass `self._lr_synth.frame` (the
   learner synth), not `s["frame"]`. The view synths are attached later and count differently. The reader clamps
   ages ≥ 0, but sharing and caching rely on this.
4. **Stage generality.** Every live test is desert (slots 1/2/3).
   - Category-9 props on other stages are classified by type byte (0xC3..0xCF), which is generic. The prop-type
     list and the thrown state values were validated on desert only.
   - lv8mix "mixed" slots are desert too, as far as the docs say. Check `G.stage*` on any new state.
5. **Item classes** for the roughly 90 items never seen on desert come from the game table plus hand sets (LIKELY
   or GUESS). A wrong class only blurs a one-hot.
6. **`com_targets_me`** (COM partner pointer = target) is LIKELY only. In pure policy FFA it is always 0, which is
   harmless.
7. **[12..17] zeroing** is a small, measured behaviour change (section 3). It is opt-in and gated.
8. **Determinism.** Replays within a process are bit-identical (test `det`, which includes a different seat
   query order). The raw-part tallies were also identical across three separate full test runs.
9. **Not yet run on the 9950X** or against the live SkipLSTM lineage zip (sb3_contrib is not in the Mac venv). The
   recurrent surgery was tested on a synthetic SkipLSTM built with sb3-contrib 2.9.0 from a scratch directory.
10. **Spatial block** is Desert-only (map_present = 0 elsewhere), and its prop rays are LIKELY (p90 350–400 u).

## 10. Overlay videos and projection accuracy

`videos/` has three 75-second clips (slot2 4P lv3, slot3 4P lv8, slot1 1v1), about 30 MB in total.
`videos/WATCHLIST.md` gives timestamps for the first chest opening, the chest with a stone, held items, projectiles,
thrown objects and hits.

**Projection method: the RAM camera, not a per-frame fit to the players.**
- View basis: eye at 0x8C5411A4, back vector at 0x8C541194 (stage_geometry). Up = world y, no roll.
- Intrinsics fitted once by **ablation** in `calibrate_projection.py`. Every category-9 object in 9 frames on 3
  states is lifted out of view, and the vanishing bounding box gives its screen position.
- Result: fx 619, fy 587, cx 319, cy 255.
- Held-out accuracy (n = 25): **median 12 px** on 640×480 (p90 48 px). By kind: cacti 7 px, chests 12, items 8,
  tall saguaros 34 (their bounding-box centre is ill-defined).
- The fit's train and test errors match, and the hurtbox rings sit on the players' feet in the videos. So the eye
  address and the fixed field of view are both right; the "LIKELY" eye from STAGE.md is in effect confirmed.

## 11. Dim-by-dim table

Non-zero, min and max come from `obs_v4_stats.txt`: 12,000 seat-vectors, slots 1/2/3, random P2 inputs plus COMs.
Positions are relative to my **logical** position P+0x28 (y = 0 on the floor), not the render matrix. Opponent
k = the k-th entry of the env's v2 opponent order (nearest-first, alive only). Seat order in the D/E/F blocks is
self, opp0, opp1, opp2. Empty slots are zero, except `margin` = 1 and `dca` = 2, so that "absent" reads as "far".

| obs | feature | source | normalisation | range | confidence | non-zero | measured min..max |
|---|---|---|---|---|---|---|---|
| 160 | `A.opp0.hit_live` | P+0x187 count>1, record hdr&0xFFFF==1, r>0; or a swung melee item (item record +0x188 list) | 1 if a live hit sphere | {0,1} | CONFIRMED-CORRELATIONAL | 0.063 | 0.00..1.00 |
| 161 | `A.opp0.sph_dx` | sphere x (P+0x184+0x20j+8) - my hurt cx (P+0x18C) | /300 | [-5,5] | CONFIRMED | 0.063 | -4.09..4.03 |
| 162 | `A.opp0.sph_dy` | sphere y - my hurt cy (P+0x190) | /300 | [-5,5] | CONFIRMED | 0.063 | -3.83..2.42 |
| 163 | `A.opp0.sph_dz` | sphere z - my hurt cz (P+0x194) | /300 | [-5,5] | CONFIRMED | 0.063 | -5.00..5.00 |
| 164 | `A.opp0.sph_r` | sphere radius (+0x14 of record) | /100 | [0,~2.3] | CONFIRMED | 0.063 | 0.00..2.08 |
| 165 | `A.opp0.margin` | max(hgap-(r+R), |dy|-(r+H)) of the nearest sphere; <=0 = contact | /200 clip[-1,1]; 1 if none/absent | [-1,1] | CONFIRMED-CORRELATIONAL (132/132 exact) | 1.000 | -0.57..1.00 |
| 166 | `A.opp0.hit_age` | frames the hitbox has been live (reader clock) | /20 clip 1 | [0,1] | CONFIRMED (signal); step resolution | 0.063 | 0.00..1.00 |
| 167 | `A.opp0.atk414` | P+0x414 != 0 (attack-descriptor ptr, startup) | flag | {0,1} | CONFIRMED-ish (41/41 melee hits, lead med 9 f) | 0.119 | 0.00..1.00 |
| 168 | `A.opp0.atk414_age` | frames since P+0x414 turned on / changed (reader clock) | /30 clip 1 | [0,1] | LIKELY | 0.119 | 0.00..1.00 |
| 169 | `A.opp0.body124` | P+0x125 (byte1 of P+0x124) != 0 | flag | {0,1} | CONFIRMED (41/41; also body hitboxes) | 0.075 | 0.00..1.00 |
| 170 | `A.opp0.item_swing` | holder state 7/8 + held melee record state 7 with sphere list at +0x188 | flag | {0,1} | CONFIRMED (22/22 item-melee hits in contact) | 0.005 | 0.00..1.00 |
| 171 | `A.opp1.hit_live` | P+0x187 count>1, record hdr&0xFFFF==1, r>0; or a swung melee item (item record +0x188 list) | 1 if a live hit sphere | {0,1} | CONFIRMED-CORRELATIONAL | 0.048 | 0.00..1.00 |
| 172 | `A.opp1.sph_dx` | sphere x (P+0x184+0x20j+8) - my hurt cx (P+0x18C) | /300 | [-5,5] | CONFIRMED | 0.048 | -4.49..3.90 |
| 173 | `A.opp1.sph_dy` | sphere y - my hurt cy (P+0x190) | /300 | [-5,5] | CONFIRMED | 0.048 | -5.00..2.85 |
| 174 | `A.opp1.sph_dz` | sphere z - my hurt cz (P+0x194) | /300 | [-5,5] | CONFIRMED | 0.048 | -5.00..3.26 |
| 175 | `A.opp1.sph_r` | sphere radius (+0x14 of record) | /100 | [0,~2.3] | CONFIRMED | 0.048 | 0.00..2.08 |
| 176 | `A.opp1.margin` | max(hgap-(r+R), |dy|-(r+H)) of the nearest sphere; <=0 = contact | /200 clip[-1,1]; 1 if none/absent | [-1,1] | CONFIRMED-CORRELATIONAL (132/132 exact) | 1.000 | -0.42..1.00 |
| 177 | `A.opp1.hit_age` | frames the hitbox has been live (reader clock) | /20 clip 1 | [0,1] | CONFIRMED (signal); step resolution | 0.048 | 0.00..1.00 |
| 178 | `A.opp1.atk414` | P+0x414 != 0 (attack-descriptor ptr, startup) | flag | {0,1} | CONFIRMED-ish (41/41 melee hits, lead med 9 f) | 0.084 | 0.00..1.00 |
| 179 | `A.opp1.atk414_age` | frames since P+0x414 turned on / changed (reader clock) | /30 clip 1 | [0,1] | LIKELY | 0.084 | 0.00..1.00 |
| 180 | `A.opp1.body124` | P+0x125 (byte1 of P+0x124) != 0 | flag | {0,1} | CONFIRMED (41/41; also body hitboxes) | 0.065 | 0.00..1.00 |
| 181 | `A.opp1.item_swing` | holder state 7/8 + held melee record state 7 with sphere list at +0x188 | flag | {0,1} | CONFIRMED (22/22 item-melee hits in contact) | 0.007 | 0.00..1.00 |
| 182 | `A.opp2.hit_live` | P+0x187 count>1, record hdr&0xFFFF==1, r>0; or a swung melee item (item record +0x188 list) | 1 if a live hit sphere | {0,1} | CONFIRMED-CORRELATIONAL | 0.031 | 0.00..1.00 |
| 183 | `A.opp2.sph_dx` | sphere x (P+0x184+0x20j+8) - my hurt cx (P+0x18C) | /300 | [-5,5] | CONFIRMED | 0.031 | -5.00..5.00 |
| 184 | `A.opp2.sph_dy` | sphere y - my hurt cy (P+0x190) | /300 | [-5,5] | CONFIRMED | 0.031 | -2.23..2.52 |
| 185 | `A.opp2.sph_dz` | sphere z - my hurt cz (P+0x194) | /300 | [-5,5] | CONFIRMED | 0.031 | -5.00..5.00 |
| 186 | `A.opp2.sph_r` | sphere radius (+0x14 of record) | /100 | [0,~2.3] | CONFIRMED | 0.031 | 0.00..0.70 |
| 187 | `A.opp2.margin` | max(hgap-(r+R), |dy|-(r+H)) of the nearest sphere; <=0 = contact | /200 clip[-1,1]; 1 if none/absent | [-1,1] | CONFIRMED-CORRELATIONAL (132/132 exact) | 1.000 | 0.15..1.00 |
| 188 | `A.opp2.hit_age` | frames the hitbox has been live (reader clock) | /20 clip 1 | [0,1] | CONFIRMED (signal); step resolution | 0.031 | 0.00..1.00 |
| 189 | `A.opp2.atk414` | P+0x414 != 0 (attack-descriptor ptr, startup) | flag | {0,1} | CONFIRMED-ish (41/41 melee hits, lead med 9 f) | 0.056 | 0.00..1.00 |
| 190 | `A.opp2.atk414_age` | frames since P+0x414 turned on / changed (reader clock) | /30 clip 1 | [0,1] | LIKELY | 0.056 | 0.00..1.00 |
| 191 | `A.opp2.body124` | P+0x125 (byte1 of P+0x124) != 0 | flag | {0,1} | CONFIRMED (41/41; also body hitboxes) | 0.050 | 0.00..1.00 |
| 192 | `A.opp2.item_swing` | holder state 7/8 + held melee record state 7 with sphere list at +0x188 | flag | {0,1} | CONFIRMED (22/22 item-melee hits in contact) | 0.003 | 0.00..1.00 |
| 193 | `A.self.hit_live` | P+0x187 count>1, record hdr&0xFFFF==1, r>0; or a swung melee item (item record +0x188 list) | 1 if a live hit sphere | {0,1} | CONFIRMED-CORRELATIONAL | 0.047 | 0.00..1.00 |
| 194 | `A.self.best_margin` | my spheres vs every opp hurt cylinder, min margin | /200 clip[-1,1]; 1 if none | [-1,1] | CONFIRMED | 1.000 | -0.57..1.00 |
| 195 | `A.self.atk414` | P+0x414 != 0 (attack-descriptor ptr, startup) | flag | {0,1} | CONFIRMED-ish (41/41 melee hits, lead med 9 f) | 0.086 | 0.00..1.00 |
| 196 | `A.self.item_swing` | holder state 7/8 + held melee record state 7 with sphere list at +0x188 | flag | {0,1} | CONFIRMED (22/22 item-melee hits in contact) | 0.005 | 0.00..1.00 |
| 197 | `B.thr0.present` | ledger cat 1 (not mine: owner via +0x14 chain, else header byte +0x05; bomb blasts kept) / cat 9 thrown (holder != me) / cat 2 mover; dedupe 5 u | flag | {0,1} | CONFIRMED-CAUSAL (position 22/22); owner 111/114 | 0.194 | 0.00..1.00 |
| 198 | `B.thr0.dx` | ledger +0x2C/+0x30/+0x34 - my logical pos (P+0x28) | (obj-me)/1000 | [-5,5] | CONFIRMED | 0.194 | -1.74..1.34 |
| 199 | `B.thr0.dy` | ledger +0x2C/+0x30/+0x34 - my logical pos (P+0x28) | (obj-me)/500 | [-5,5] | CONFIRMED | 0.155 | -2.42..3.02 |
| 200 | `B.thr0.dz` | ledger +0x2C/+0x30/+0x34 - my logical pos (P+0x28) | (obj-me)/1000 | [-5,5] | CONFIRMED | 0.194 | -2.01..2.15 |
| 201 | `B.thr0.vx` | ledger +0x50 x60 (u/s) | /2400 | [-2,2] | CONFIRMED (exact, cat 1/9) | 0.178 | -1.35..1.50 |
| 202 | `B.thr0.vy` | ledger +0x54 x60 | /2400 | [-2,2] | CONFIRMED | 0.156 | -1.05..0.67 |
| 203 | `B.thr0.vz` | ledger +0x58 x60 | /2400 | [-2,2] | CONFIRMED | 0.176 | -1.49..0.93 |
| 204 | `B.thr0.radius` | ledger +0x19C (0 if implausible) | /300 | [0,1.4] | medium (PROJECTILES) | 0.150 | 0.00..1.33 |
| 205 | `B.thr0.thrown` | cat-9 state 8, or state 6 with |v|>=600; or cat-2 mover | flag | {0,1} | CONFIRMED (state 8) / LIKELY (6) | 0.112 | 0.00..1.00 |
| 206 | `B.thr0.tca` | time of closest approach, me static: clip(-p.v/|v|^2, 0, 1 s) | seconds | [0,1] | derived | 0.090 | 0.00..1.00 |
| 207 | `B.thr0.dca` | distance at closest approach | /500 clip 2; 2 if absent | [0,2] | derived | 1.000 | 0.01..2.00 |
| 208 | `B.thr1.present` | ledger cat 1 (not mine: owner via +0x14 chain, else header byte +0x05; bomb blasts kept) / cat 9 thrown (holder != me) / cat 2 mover; dedupe 5 u | flag | {0,1} | CONFIRMED-CAUSAL (position 22/22); owner 111/114 | 0.065 | 0.00..1.00 |
| 209 | `B.thr1.dx` | ledger +0x2C/+0x30/+0x34 - my logical pos (P+0x28) | (obj-me)/1000 | [-5,5] | CONFIRMED | 0.065 | -1.30..1.59 |
| 210 | `B.thr1.dy` | ledger +0x2C/+0x30/+0x34 - my logical pos (P+0x28) | (obj-me)/500 | [-5,5] | CONFIRMED | 0.063 | -1.53..3.20 |
| 211 | `B.thr1.dz` | ledger +0x2C/+0x30/+0x34 - my logical pos (P+0x28) | (obj-me)/1000 | [-5,5] | CONFIRMED | 0.065 | -2.30..2.16 |
| 212 | `B.thr1.vx` | ledger +0x50 x60 (u/s) | /2400 | [-2,2] | CONFIRMED (exact, cat 1/9) | 0.059 | -1.43..1.50 |
| 213 | `B.thr1.vy` | ledger +0x54 x60 | /2400 | [-2,2] | CONFIRMED | 0.050 | -1.05..0.67 |
| 214 | `B.thr1.vz` | ledger +0x58 x60 | /2400 | [-2,2] | CONFIRMED | 0.059 | -1.50..1.01 |
| 215 | `B.thr1.radius` | ledger +0x19C (0 if implausible) | /300 | [0,1.4] | medium (PROJECTILES) | 0.043 | 0.00..1.33 |
| 216 | `B.thr1.thrown` | cat-9 state 8, or state 6 with |v|>=600; or cat-2 mover | flag | {0,1} | CONFIRMED (state 8) / LIKELY (6) | 0.011 | 0.00..1.00 |
| 217 | `B.thr1.tca` | time of closest approach, me static: clip(-p.v/|v|^2, 0, 1 s) | seconds | [0,1] | derived | 0.027 | 0.00..1.00 |
| 218 | `B.thr1.dca` | distance at closest approach | /500 clip 2; 2 if absent | [0,2] | derived | 1.000 | 0.00..2.00 |
| 219 | `B.thr2.present` | ledger cat 1 (not mine: owner via +0x14 chain, else header byte +0x05; bomb blasts kept) / cat 9 thrown (holder != me) / cat 2 mover; dedupe 5 u | flag | {0,1} | CONFIRMED-CAUSAL (position 22/22); owner 111/114 | 0.048 | 0.00..1.00 |
| 220 | `B.thr2.dx` | ledger +0x2C/+0x30/+0x34 - my logical pos (P+0x28) | (obj-me)/1000 | [-5,5] | CONFIRMED | 0.048 | -1.26..1.83 |
| 221 | `B.thr2.dy` | ledger +0x2C/+0x30/+0x34 - my logical pos (P+0x28) | (obj-me)/500 | [-5,5] | CONFIRMED | 0.048 | -1.59..2.99 |
| 222 | `B.thr2.dz` | ledger +0x2C/+0x30/+0x34 - my logical pos (P+0x28) | (obj-me)/1000 | [-5,5] | CONFIRMED | 0.048 | -1.35..2.12 |
| 223 | `B.thr2.vx` | ledger +0x50 x60 (u/s) | /2400 | [-2,2] | CONFIRMED (exact, cat 1/9) | 0.045 | -1.42..1.50 |
| 224 | `B.thr2.vy` | ledger +0x54 x60 | /2400 | [-2,2] | CONFIRMED | 0.039 | -0.67..0.67 |
| 225 | `B.thr2.vz` | ledger +0x58 x60 | /2400 | [-2,2] | CONFIRMED | 0.044 | -1.50..1.23 |
| 226 | `B.thr2.radius` | ledger +0x19C (0 if implausible) | /300 | [0,1.4] | medium (PROJECTILES) | 0.032 | 0.00..0.93 |
| 227 | `B.thr2.thrown` | cat-9 state 8, or state 6 with |v|>=600; or cat-2 mover | flag | {0,1} | CONFIRMED (state 8) / LIKELY (6) | 0.000 | 0.00..1.00 |
| 228 | `B.thr2.tca` | time of closest approach, me static: clip(-p.v/|v|^2, 0, 1 s) | seconds | [0,1] | derived | 0.019 | 0.00..0.97 |
| 229 | `B.thr2.dca` | distance at closest approach | /500 clip 2; 2 if absent | [0,2] | derived | 1.000 | 0.00..2.00 |
| 230 | `B.crowd600` | enemy threats within 600 u (xz) | min(n,10)/5 | [0,2] | derived | 0.106 | 0.00..2.00 |
| 231 | `C.item0.present` | ledger cat 9, type 1..0x77, state 0/2/6 | flag | {0,1} | CONFIRMED | 0.575 | 0.00..1.00 |
| 232 | `C.item0.dx` | ledger pos - my logical pos | (obj-me)/1000 | [-5,5] | CONFIRMED | 0.567 | -1.29..1.91 |
| 233 | `C.item0.dz` | ledger pos - my logical pos | (obj-me)/1000 | [-5,5] | CONFIRMED | 0.575 | -1.55..1.65 |
| 234 | `C.item0.dy` | ledger pos - my logical pos | (obj-me)/500 | [-5,5] | CONFIRMED | 0.575 | -3.40..0.83 |
| 235 | `C.item0.ready` | ledger +0x421 == 2 (resting, pickable) | flag | {0,1} | CONFIRMED | 0.532 | 0.00..1.00 |
| 236 | `C.item0.melee` | items_dict ground class | one-hot | {0,1} | LIKELY | 0.205 | 0.00..1.00 |
| 237 | `C.item0.ranged` | items_dict class | one-hot | {0,1} | CONFIRMED (name/table) / LIKELY (class) | 0.281 | 0.00..1.00 |
| 238 | `C.item0.thrown` | cat-9 state 8, or state 6 with |v|>=600; or cat-2 mover | flag | {0,1} | CONFIRMED (state 8) / LIKELY (6) | 0.087 | 0.00..1.00 |
| 239 | `C.item0.food` | items_dict class | one-hot | {0,1} | LIKELY | 0.002 | 0.00..1.00 |
| 240 | `C.item0.other` | items_dict ground class | one-hot | {0,1} | LIKELY | 0.000 | 0.00..0.00 |
| 241 | `C.item1.present` | ledger cat 9, type 1..0x77, state 0/2/6 | flag | {0,1} | CONFIRMED | 0.320 | 0.00..1.00 |
| 242 | `C.item1.dx` | ledger pos - my logical pos | (obj-me)/1000 | [-5,5] | CONFIRMED | 0.320 | -1.65..1.95 |
| 243 | `C.item1.dz` | ledger pos - my logical pos | (obj-me)/1000 | [-5,5] | CONFIRMED | 0.320 | -1.48..1.90 |
| 244 | `C.item1.dy` | ledger pos - my logical pos | (obj-me)/500 | [-5,5] | CONFIRMED | 0.320 | -2.15..0.83 |
| 245 | `C.item1.ready` | ledger +0x421 == 2 (resting, pickable) | flag | {0,1} | CONFIRMED | 0.308 | 0.00..1.00 |
| 246 | `C.item1.melee` | items_dict ground class | one-hot | {0,1} | LIKELY | 0.119 | 0.00..1.00 |
| 247 | `C.item1.ranged` | items_dict class | one-hot | {0,1} | CONFIRMED (name/table) / LIKELY (class) | 0.136 | 0.00..1.00 |
| 248 | `C.item1.thrown` | cat-9 state 8, or state 6 with |v|>=600; or cat-2 mover | flag | {0,1} | CONFIRMED (state 8) / LIKELY (6) | 0.040 | 0.00..1.00 |
| 249 | `C.item1.food` | items_dict class | one-hot | {0,1} | LIKELY | 0.025 | 0.00..1.00 |
| 250 | `C.item1.other` | items_dict ground class | one-hot | {0,1} | LIKELY | 0.000 | 0.00..0.00 |
| 251 | `C.item2.present` | ledger cat 9, type 1..0x77, state 0/2/6 | flag | {0,1} | CONFIRMED | 0.123 | 0.00..1.00 |
| 252 | `C.item2.dx` | ledger pos - my logical pos | (obj-me)/1000 | [-5,5] | CONFIRMED | 0.123 | -1.61..2.07 |
| 253 | `C.item2.dz` | ledger pos - my logical pos | (obj-me)/1000 | [-5,5] | CONFIRMED | 0.123 | -1.65..1.94 |
| 254 | `C.item2.dy` | ledger pos - my logical pos | (obj-me)/500 | [-5,5] | CONFIRMED | 0.123 | -1.58..0.42 |
| 255 | `C.item2.ready` | ledger +0x421 == 2 (resting, pickable) | flag | {0,1} | CONFIRMED | 0.118 | 0.00..1.00 |
| 256 | `C.item2.melee` | items_dict ground class | one-hot | {0,1} | LIKELY | 0.031 | 0.00..1.00 |
| 257 | `C.item2.ranged` | items_dict class | one-hot | {0,1} | CONFIRMED (name/table) / LIKELY (class) | 0.067 | 0.00..1.00 |
| 258 | `C.item2.thrown` | cat-9 state 8, or state 6 with |v|>=600; or cat-2 mover | flag | {0,1} | CONFIRMED (state 8) / LIKELY (6) | 0.016 | 0.00..1.00 |
| 259 | `C.item2.food` | items_dict class | one-hot | {0,1} | LIKELY | 0.009 | 0.00..1.00 |
| 260 | `C.item2.other` | items_dict ground class | one-hot | {0,1} | LIKELY | 0.000 | 0.00..0.00 |
| 261 | `C.prop.present` | ledger cat 9, type 0xC3..0xCF, state 2 | flag | {0,1} | CONFIRMED | 1.000 | 1.00..1.00 |
| 262 | `C.prop.dx` | ledger pos - my logical pos | (obj-me)/1000 | [-5,5] | CONFIRMED | 0.997 | -1.11..0.97 |
| 263 | `C.prop.dz` | ledger pos - my logical pos | (obj-me)/1000 | [-5,5] | CONFIRMED | 0.990 | -1.15..1.07 |
| 264 | `C.prop.big` | type 0xC8 (tall saguaro / pole) | flag | {0,1} | CONFIRMED (desert) | 0.329 | 0.00..1.00 |
| 265 | `C.chest0.present` | ledger cat 9, type 0xC2, state 2/9 | flag | {0,1} | CONFIRMED | 0.928 | 0.00..1.00 |
| 266 | `C.chest0.dx` | ledger pos - my logical pos | (obj-me)/1000 | [-5,5] | CONFIRMED | 0.927 | -1.60..1.95 |
| 267 | `C.chest0.dz` | ledger pos - my logical pos | (obj-me)/1000 | [-5,5] | CONFIRMED | 0.928 | -1.47..1.79 |
| 268 | `C.chest0.dy` | ledger pos - my logical pos | (obj-me)/500 | [-5,5] | CONFIRMED | 0.928 | -3.44..0.10 |
| 269 | `C.chest0.has_stone` | chest +0x42C == 0xC1 | flag | {0,1} | CONFIRMED-CAUSAL (65/65) | 0.172 | 0.00..1.00 |
| 270 | `C.chest1.present` | ledger cat 9, type 0xC2, state 2/9 | flag | {0,1} | CONFIRMED | 0.861 | 0.00..1.00 |
| 271 | `C.chest1.dx` | ledger pos - my logical pos | (obj-me)/1000 | [-5,5] | CONFIRMED | 0.859 | -1.60..2.09 |
| 272 | `C.chest1.dz` | ledger pos - my logical pos | (obj-me)/1000 | [-5,5] | CONFIRMED | 0.861 | -1.66..1.94 |
| 273 | `C.chest1.dy` | ledger pos - my logical pos | (obj-me)/500 | [-5,5] | CONFIRMED | 0.861 | -3.44..0.10 |
| 274 | `C.chest1.has_stone` | chest +0x42C == 0xC1 | flag | {0,1} | CONFIRMED-CAUSAL (65/65) | 0.124 | 0.00..1.00 |
| 275 | `D.self.melee` | held type u8[(F+0x54)-4+0x420] -> items_dict class | one-hot | {0,1} | CONFIRMED-CAUSAL (key) / LIKELY (class) | 0.042 | 0.00..1.00 |
| 276 | `D.self.r_long` | held class | one-hot | {0,1} | LIKELY | 0.038 | 0.00..1.00 |
| 277 | `D.self.r_short` | held class | one-hot | {0,1} | LIKELY | 0.006 | 0.00..1.00 |
| 278 | `D.self.thrown` | held type u8[(F+0x54)-4+0x420] -> items_dict class | flag | {0,1} | CONFIRMED-CAUSAL (key) / LIKELY (class) | 0.083 | 0.00..1.00 |
| 279 | `D.self.other` | held type u8[(F+0x54)-4+0x420] -> items_dict class | one-hot | {0,1} | CONFIRMED-CAUSAL (key) / LIKELY (class) | 0.000 | 0.00..0.00 |
| 280 | `D.self.uses_frac` | record +0x424 / table initial counter (1.0 for single-use) | frac | [0,1] | CONFIRMED-CAUSAL (rules; counter set at spawn) | 0.168 | 0.00..1.00 |
| 281 | `D.opp0.melee` | held type u8[(F+0x54)-4+0x420] -> items_dict class | one-hot | {0,1} | CONFIRMED-CAUSAL (key) / LIKELY (class) | 0.046 | 0.00..1.00 |
| 282 | `D.opp0.r_long` | held class | one-hot | {0,1} | LIKELY | 0.036 | 0.00..1.00 |
| 283 | `D.opp0.r_short` | held class | one-hot | {0,1} | LIKELY | 0.009 | 0.00..1.00 |
| 284 | `D.opp0.thrown` | held type u8[(F+0x54)-4+0x420] -> items_dict class | flag | {0,1} | CONFIRMED-CAUSAL (key) / LIKELY (class) | 0.083 | 0.00..1.00 |
| 285 | `D.opp0.other` | held type u8[(F+0x54)-4+0x420] -> items_dict class | one-hot | {0,1} | CONFIRMED-CAUSAL (key) / LIKELY (class) | 0.000 | 0.00..0.00 |
| 286 | `D.opp0.uses_frac` | record +0x424 / table initial counter (1.0 for single-use) | frac | [0,1] | CONFIRMED-CAUSAL (rules; counter set at spawn) | 0.174 | 0.00..1.00 |
| 287 | `D.opp1.melee` | held type u8[(F+0x54)-4+0x420] -> items_dict class | one-hot | {0,1} | CONFIRMED-CAUSAL (key) / LIKELY (class) | 0.045 | 0.00..1.00 |
| 288 | `D.opp1.r_long` | held class | one-hot | {0,1} | LIKELY | 0.045 | 0.00..1.00 |
| 289 | `D.opp1.r_short` | held class | one-hot | {0,1} | LIKELY | 0.007 | 0.00..1.00 |
| 290 | `D.opp1.thrown` | held type u8[(F+0x54)-4+0x420] -> items_dict class | flag | {0,1} | CONFIRMED-CAUSAL (key) / LIKELY (class) | 0.094 | 0.00..1.00 |
| 291 | `D.opp1.other` | held type u8[(F+0x54)-4+0x420] -> items_dict class | one-hot | {0,1} | CONFIRMED-CAUSAL (key) / LIKELY (class) | 0.000 | 0.00..0.00 |
| 292 | `D.opp1.uses_frac` | record +0x424 / table initial counter (1.0 for single-use) | frac | [0,1] | CONFIRMED-CAUSAL (rules; counter set at spawn) | 0.190 | 0.00..1.00 |
| 293 | `D.opp2.melee` | held type u8[(F+0x54)-4+0x420] -> items_dict class | one-hot | {0,1} | CONFIRMED-CAUSAL (key) / LIKELY (class) | 0.033 | 0.00..1.00 |
| 294 | `D.opp2.r_long` | held class | one-hot | {0,1} | LIKELY | 0.033 | 0.00..1.00 |
| 295 | `D.opp2.r_short` | held class | one-hot | {0,1} | LIKELY | 0.003 | 0.00..1.00 |
| 296 | `D.opp2.thrown` | held type u8[(F+0x54)-4+0x420] -> items_dict class | flag | {0,1} | CONFIRMED-CAUSAL (key) / LIKELY (class) | 0.071 | 0.00..1.00 |
| 297 | `D.opp2.other` | held type u8[(F+0x54)-4+0x420] -> items_dict class | one-hot | {0,1} | CONFIRMED-CAUSAL (key) / LIKELY (class) | 0.000 | 0.00..0.00 |
| 298 | `D.opp2.uses_frac` | record +0x424 / table initial counter (1.0 for single-use) | frac | [0,1] | CONFIRMED-CAUSAL (rules; counter set at spawn) | 0.141 | 0.00..1.00 |
| 299 | `E.self.invuln` | P+0x12C low u16 == 0 | flag | {0,1} | CONFIRMED-CORRELATIONAL (150/150) | 0.236 | 0.00..1.00 |
| 300 | `E.self.airborne` | P+0x135 bit 0x04 clear | flag | {0,1} | CONFIRMED (99%) | 0.361 | 0.00..1.00 |
| 301 | `E.self.vy` | P+0x50 (u/frame) | /30 clip[-2,2] | [-2,2] | CONFIRMED (air) | 0.230 | -2.00..2.00 |
| 302 | `E.self.hurt_h` | hurt half-height P+0x19C | /100 clip[0,2] | [0,~1] | CONFIRMED | 0.833 | 0.00..1.10 |
| 303 | `E.self.down` | state in {14,15} | flag | {0,1} | CONFIRMED | 0.026 | 0.00..1.00 |
| 304 | `E.self.held` | state == 34 (held by an opponent) | flag | {0,1} | CONFIRMED | 0.004 | 0.00..1.00 |
| 305 | `E.self.grabbing` | state in {9,11,12} | flag | {0,1} | CONFIRMED | 0.003 | 0.00..1.00 |
| 306 | `E.self.state_age` | frames since state byte P+0x3715 changed (reader clock) | /60 clip 1 | [0,1] | CONFIRMED (byte) | 0.893 | 0.00..1.00 |
| 307 | `E.opp0.invuln` | P+0x12C low u16 == 0 | flag | {0,1} | CONFIRMED-CORRELATIONAL (150/150) | 0.029 | 0.00..1.00 |
| 308 | `E.opp0.airborne` | P+0x135 bit 0x04 clear | flag | {0,1} | CONFIRMED (99%) | 0.207 | 0.00..1.00 |
| 309 | `E.opp0.vy` | P+0x50 (u/frame) | /30 clip[-2,2] | [-2,2] | CONFIRMED (air) | 0.228 | -2.00..2.00 |
| 310 | `E.opp0.hurt_h` | hurt half-height P+0x19C | /100 clip[0,2] | [0,~1] | CONFIRMED | 0.981 | 0.00..1.10 |
| 311 | `E.opp0.down` | state in {14,15} | flag | {0,1} | CONFIRMED | 0.008 | 0.00..1.00 |
| 312 | `E.opp0.held` | state == 34 (held by an opponent) | flag | {0,1} | CONFIRMED | 0.006 | 0.00..1.00 |
| 313 | `E.opp0.grabbing` | state in {9,11,12} | flag | {0,1} | CONFIRMED | 0.004 | 0.00..1.00 |
| 314 | `E.opp0.state_age` | frames since state byte P+0x3715 changed (reader clock) | /60 clip 1 | [0,1] | CONFIRMED (byte) | 0.851 | 0.00..1.00 |
| 315 | `E.opp1.invuln` | P+0x12C low u16 == 0 | flag | {0,1} | CONFIRMED-CORRELATIONAL (150/150) | 0.033 | 0.00..1.00 |
| 316 | `E.opp1.airborne` | P+0x135 bit 0x04 clear | flag | {0,1} | CONFIRMED (99%) | 0.193 | 0.00..1.00 |
| 317 | `E.opp1.vy` | P+0x50 (u/frame) | /30 clip[-2,2] | [-2,2] | CONFIRMED (air) | 0.213 | -2.00..2.00 |
| 318 | `E.opp1.hurt_h` | hurt half-height P+0x19C | /100 clip[0,2] | [0,~1] | CONFIRMED | 0.814 | 0.00..1.10 |
| 319 | `E.opp1.down` | state in {14,15} | flag | {0,1} | CONFIRMED | 0.014 | 0.00..1.00 |
| 320 | `E.opp1.held` | state == 34 (held by an opponent) | flag | {0,1} | CONFIRMED | 0.005 | 0.00..1.00 |
| 321 | `E.opp1.grabbing` | state in {9,11,12} | flag | {0,1} | CONFIRMED | 0.002 | 0.00..1.00 |
| 322 | `E.opp1.state_age` | frames since state byte P+0x3715 changed (reader clock) | /60 clip 1 | [0,1] | CONFIRMED (byte) | 0.706 | 0.00..1.00 |
| 323 | `E.opp2.invuln` | P+0x12C low u16 == 0 | flag | {0,1} | CONFIRMED-CORRELATIONAL (150/150) | 0.037 | 0.00..1.00 |
| 324 | `E.opp2.airborne` | P+0x135 bit 0x04 clear | flag | {0,1} | CONFIRMED (99%) | 0.103 | 0.00..1.00 |
| 325 | `E.opp2.vy` | P+0x50 (u/frame) | /30 clip[-2,2] | [-2,2] | CONFIRMED (air) | 0.122 | -2.00..1.17 |
| 326 | `E.opp2.hurt_h` | hurt half-height P+0x19C | /100 clip[0,2] | [0,~1] | CONFIRMED | 0.522 | 0.00..1.10 |
| 327 | `E.opp2.down` | state in {14,15} | flag | {0,1} | CONFIRMED | 0.011 | 0.00..1.00 |
| 328 | `E.opp2.held` | state == 34 (held by an opponent) | flag | {0,1} | CONFIRMED | 0.002 | 0.00..1.00 |
| 329 | `E.opp2.grabbing` | state in {9,11,12} | flag | {0,1} | CONFIRMED | 0.003 | 0.00..1.00 |
| 330 | `E.opp2.state_age` | frames since state byte P+0x3715 changed (reader clock) | /60 clip 1 | [0,1] | CONFIRMED (byte) | 0.447 | 0.00..1.00 |
| 331 | `E.opp0.last_hit_me` | my P+0x3774 (== PLAYER_MAT+0x32E4) -> player, else ledger owner chain | flag | {0,1} | CONFIRMED (melee) / LIKELY (projectile) | 0.180 | 0.00..1.00 |
| 332 | `E.opp0.com_targets_me` | opp COM flag P+0x3720 and its P+0x3770 points at my struct | flag | {0,1} | LIKELY | 0.049 | 0.00..1.00 |
| 333 | `E.opp1.last_hit_me` | my P+0x3774 (== PLAYER_MAT+0x32E4) -> player, else ledger owner chain | flag | {0,1} | CONFIRMED (melee) / LIKELY (projectile) | 0.145 | 0.00..1.00 |
| 334 | `E.opp1.com_targets_me` | opp COM flag P+0x3720 and its P+0x3770 points at my struct | flag | {0,1} | LIKELY | 0.042 | 0.00..1.00 |
| 335 | `E.opp2.last_hit_me` | my P+0x3774 (== PLAYER_MAT+0x32E4) -> player, else ledger owner chain | flag | {0,1} | CONFIRMED (melee) / LIKELY (projectile) | 0.082 | 0.00..1.00 |
| 336 | `E.opp2.com_targets_me` | opp COM flag P+0x3720 and its P+0x3770 points at my struct | flag | {0,1} | LIKELY | 0.025 | 0.00..1.00 |
| 337 | `F.self.Falcon` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.500 | 0.00..1.00 |
| 338 | `F.self.Ryoma` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.083 | 0.00..1.00 |
| 339 | `F.self.Wang-Tang` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 340 | `F.self.Jack` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 341 | `F.self.Gunrock` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 342 | `F.self.Galuda` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 343 | `F.self.Ayame` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.083 | 0.00..1.00 |
| 344 | `F.self.Rouge` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 345 | `F.self.Pete` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.083 | 0.00..1.00 |
| 346 | `F.self.Gourmand` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 347 | `F.self.Julia` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 348 | `F.self.Accel` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.167 | 0.00..1.00 |
| 349 | `F.self.Mel` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 350 | `F.self.Pride` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.083 | 0.00..1.00 |
| 351 | `F.opp0.Falcon` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.419 | 0.00..1.00 |
| 352 | `F.opp0.Ryoma` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.105 | 0.00..1.00 |
| 353 | `F.opp0.Wang-Tang` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 354 | `F.opp0.Jack` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 355 | `F.opp0.Gunrock` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 356 | `F.opp0.Galuda` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 357 | `F.opp0.Ayame` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.083 | 0.00..1.00 |
| 358 | `F.opp0.Rouge` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 359 | `F.opp0.Pete` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.088 | 0.00..1.00 |
| 360 | `F.opp0.Gourmand` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 361 | `F.opp0.Julia` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 362 | `F.opp0.Accel` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.203 | 0.00..1.00 |
| 363 | `F.opp0.Mel` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 364 | `F.opp0.Pride` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.083 | 0.00..1.00 |
| 365 | `F.opp1.Falcon` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.266 | 0.00..1.00 |
| 366 | `F.opp1.Ryoma` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.105 | 0.00..1.00 |
| 367 | `F.opp1.Wang-Tang` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 368 | `F.opp1.Jack` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 369 | `F.opp1.Gunrock` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 370 | `F.opp1.Galuda` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 371 | `F.opp1.Ayame` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.095 | 0.00..1.00 |
| 372 | `F.opp1.Rouge` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 373 | `F.opp1.Pete` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.083 | 0.00..1.00 |
| 374 | `F.opp1.Gourmand` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 375 | `F.opp1.Julia` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 376 | `F.opp1.Accel` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.173 | 0.00..1.00 |
| 377 | `F.opp1.Mel` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 378 | `F.opp1.Pride` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.091 | 0.00..1.00 |
| 379 | `F.opp2.Falcon` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.175 | 0.00..1.00 |
| 380 | `F.opp2.Ryoma` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.032 | 0.00..1.00 |
| 381 | `F.opp2.Wang-Tang` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 382 | `F.opp2.Jack` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 383 | `F.opp2.Gunrock` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 384 | `F.opp2.Galuda` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 385 | `F.opp2.Ayame` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.065 | 0.00..1.00 |
| 386 | `F.opp2.Rouge` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 387 | `F.opp2.Pete` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.072 | 0.00..1.00 |
| 388 | `F.opp2.Gourmand` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 389 | `F.opp2.Julia` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 390 | `F.opp2.Accel` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.110 | 0.00..1.00 |
| 391 | `F.opp2.Mel` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.000 | 0.00..0.00 |
| 392 | `F.opp2.Pride` | P+0x02 character id | one-hot (14 selectable) | {0,1} | CONFIRMED (14/14) | 0.068 | 0.00..1.00 |
| 393 | `G.fight_live` | 0x8C475200 advanced since the previous frame read | flag | {0,1} | CONFIRMED | 0.962 | 0.00..1.00 |
| 394 | `G.menu_open` | u8 0x8C46E1BB | flag | {0,1} | LIKELY | 0.000 | 0.00..0.00 |
| 395 | `G.stage0` | u32 0x8C46E198: Blue sky | one-hot | {0,1} | CONFIRMED (stage_geometry, 9 states) | 0.000 | 0.00..0.00 |
| 396 | `G.stage1` | u32 0x8C46E198: Dark castle | one-hot | {0,1} | CONFIRMED (stage_geometry, 9 states) | 0.000 | 0.00..0.00 |
| 397 | `G.stage2` | u32 0x8C46E198: Tomb | one-hot | {0,1} | CONFIRMED (stage_geometry, 9 states) | 0.000 | 0.00..0.00 |
| 398 | `G.stage3` | u32 0x8C46E198: Iceberg | one-hot | {0,1} | CONFIRMED (stage_geometry, 9 states) | 0.000 | 0.00..0.00 |
| 399 | `G.stage4` | u32 0x8C46E198: Space station | one-hot | {0,1} | CONFIRMED (stage_geometry, 9 states) | 0.000 | 0.00..0.00 |
| 400 | `G.stage5` | u32 0x8C46E198: Desert (+Pharaoh) | one-hot | {0,1} | CONFIRMED (stage_geometry, 9 states) | 1.000 | 1.00..1.00 |
| 401 | `G.stage6` | u32 0x8C46E198: Chaos | one-hot | {0,1} | CONFIRMED (stage_geometry, 9 states) | 0.000 | 0.00..0.00 |
| 402 | `G.variant` | u8 0x8C54235E != 0 (1 Pharaoh walker, 2 Chaos) | flag | {0,1} | CONFIRMED (stage_geometry) | 0.000 | 0.00..0.00 |
| 403 | `H.ray_up` | free run along dpad dir (action frame): min(static box ray, live pole r75 / cluster r120) | /1000 clip[0,1] | [0,1] | CONFIRMED walls (median err 4 u); poles/clusters LIKELY (p90 350-400 u) | 0.960 | 0.00..1.00 |
| 404 | `H.ray_down` | free run along dpad dir (action frame): min(static box ray, live pole r75 / cluster r120) | /1000 clip[0,1] | [0,1] | CONFIRMED walls (median err 4 u); poles/clusters LIKELY (p90 350-400 u) | 0.960 | 0.00..1.00 |
| 405 | `H.ray_left` | free run along dpad dir (action frame): min(static box ray, live pole r75 / cluster r120) | /1000 clip[0,1] | [0,1] | CONFIRMED walls (median err 4 u); poles/clusters LIKELY (p90 350-400 u) | 0.960 | 0.00..1.00 |
| 406 | `H.ray_right` | free run along dpad dir (action frame): min(static box ray, live pole r75 / cluster r120) | /1000 clip[0,1] | [0,1] | CONFIRMED walls (median err 4 u); poles/clusters LIKELY (p90 350-400 u) | 0.960 | 0.00..1.00 |
| 407 | `H.ray_upleft` | free run along dpad dir (action frame): min(static box ray, live pole r75 / cluster r120) | /1000 clip[0,1] | [0,1] | CONFIRMED walls (median err 4 u); poles/clusters LIKELY (p90 350-400 u) | 0.960 | 0.00..1.00 |
| 408 | `H.ray_upright` | free run along dpad dir (action frame): min(static box ray, live pole r75 / cluster r120) | /1000 clip[0,1] | [0,1] | CONFIRMED walls (median err 4 u); poles/clusters LIKELY (p90 350-400 u) | 0.960 | 0.00..1.00 |
| 409 | `H.ray_downleft` | free run along dpad dir (action frame): min(static box ray, live pole r75 / cluster r120) | /1000 clip[0,1] | [0,1] | CONFIRMED walls (median err 4 u); poles/clusters LIKELY (p90 350-400 u) | 0.960 | 0.00..1.00 |
| 410 | `H.ray_downright` | free run along dpad dir (action frame): min(static box ray, live pole r75 / cluster r120) | /1000 clip[0,1] | [0,1] | CONFIRMED walls (median err 4 u); poles/clusters LIKELY (p90 350-400 u) | 0.960 | 0.00..1.00 |
| 411 | `H.pole_right` | nearest live pole (ledger vt 0x0C0F18D4 / 0x0C0F1688), dpad-right component | /1000 | [-1.5,1.5] | CONFIRMED (positions) / LIKELY (as obstacle) | 0.926 | -1.14..1.15 |
| 412 | `H.pole_up` | nearest live pole (ledger vt 0x0C0F18D4 / 0x0C0F1688), dpad-up component | /1000 | [-1.5,1.5] | CONFIRMED (positions) / LIKELY (as obstacle) | 0.926 | -1.04..1.20 |
| 413 | `H.pole_dist` | nearest live pole (ledger vt 0x0C0F18D4 / 0x0C0F1688), distance | /1000 | [-1.5,1.5] | CONFIRMED (positions) / LIKELY (as obstacle) | 0.926 | 0.00..1.20 |
| 414 | `H.cluster_right` | nearest live cluster (ledger vt 0x0C0F18D4 / 0x0C0F1688), dpad-right component | /1000 | [-1.5,1.5] | CONFIRMED (positions) / LIKELY (as obstacle) | 0.929 | -1.28..0.86 |
| 415 | `H.cluster_up` | nearest live cluster (ledger vt 0x0C0F18D4 / 0x0C0F1688), dpad-up component | /1000 | [-1.5,1.5] | CONFIRMED (positions) / LIKELY (as obstacle) | 0.929 | -0.99..1.49 |
| 416 | `H.cluster_dist` | nearest live cluster (ledger vt 0x0C0F18D4 / 0x0C0F1688), distance | /1000 | [-1.5,1.5] | CONFIRMED (positions) / LIKELY (as obstacle) | 0.929 | 0.00..1.57 |
| 417 | `H.wall_right` | nearest boundary of the walkable map, right | /1000 | [-1,1] | CONFIRMED (desert; map_present=0 elsewhere) | 0.998 | -0.71..0.71 |
| 418 | `H.wall_up` | nearest boundary of the walkable map, up | /1000 | [-1,1] | CONFIRMED (desert; map_present=0 elsewhere) | 0.998 | -0.71..0.71 |
| 419 | `H.wall_dist` | nearest boundary of the walkable map, dist | /1000 | [-1,1] | CONFIRMED (desert; map_present=0 elsewhere) | 0.998 | 0.00..1.00 |
| 420 | `H.height_above_floor` | my logical y - floor under me | /500 | [0,~2.6] | CONFIRMED (desert; map_present=0 elsewhere) | 0.501 | -0.00..3.54 |
| 421 | `H.floor_ahead_up` | floor 150 u ahead - floor here (no floor -> -1) | /500 | [-1,1] | CONFIRMED (desert; map_present=0 elsewhere) | 0.067 | -1.00..0.00 |
| 422 | `H.floor_ahead_down` | floor 150 u ahead - floor here (no floor -> -1) | /500 | [-1,1] | CONFIRMED (desert; map_present=0 elsewhere) | 0.007 | -1.00..0.00 |
| 423 | `H.floor_ahead_left` | floor 150 u ahead - floor here (no floor -> -1) | /500 | [-1,1] | CONFIRMED (desert; map_present=0 elsewhere) | 0.021 | -1.00..0.00 |
| 424 | `H.floor_ahead_right` | floor 150 u ahead - floor here (no floor -> -1) | /500 | [-1,1] | CONFIRMED (desert; map_present=0 elsewhere) | 0.055 | -1.00..0.00 |
| 425 | `H.floor_ahead_upleft` | floor 150 u ahead - floor here (no floor -> -1) | /500 | [-1,1] | CONFIRMED (desert; map_present=0 elsewhere) | 0.032 | -1.00..0.00 |
| 426 | `H.floor_ahead_upright` | floor 150 u ahead - floor here (no floor -> -1) | /500 | [-1,1] | CONFIRMED (desert; map_present=0 elsewhere) | 0.058 | -1.00..0.00 |
| 427 | `H.floor_ahead_downleft` | floor 150 u ahead - floor here (no floor -> -1) | /500 | [-1,1] | CONFIRMED (desert; map_present=0 elsewhere) | 0.004 | -1.00..0.00 |
| 428 | `H.floor_ahead_downright` | floor 150 u ahead - floor here (no floor -> -1) | /500 | [-1,1] | CONFIRMED (desert; map_present=0 elsewhere) | 0.010 | -1.00..0.00 |
| 429 | `H.map_present` | a map exists for (stage id, variant); else the block is 0 | flag | {0,1} | CONFIRMED (desert; map_present=0 elsewhere) | 1.000 | 1.00..1.00 |
