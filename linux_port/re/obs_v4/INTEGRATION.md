# Adopting obs v4: step by step (PROPOSAL; nothing here has been applied)

This changes the live observation contract, so it needs Blake's approval. The design and evidence are in
`OBS_V4_SPEC.md`. The steps follow the obs-v3 cutover (`cutover_v3.sh`, Sep 23) and the `league_surgery.txt` hook
(Oct 3). Line numbers refer to upstream leg 121.

**Contract after adoption.** `PS2_OBS_V4=1` (requires `PS2_OBS_V3=1`) gives 430 dims per frame:
- `obs[0:160]` is the v3 builder's output, unchanged, except obs[12..17], which reads 0 for 430-dim consumers
  under `PS2_OBS_V4_ITEMEMB=zero`;
- `obs[160:430]` comes from `obs_v4_reader.py`.

Older pool seats and evals of older models keep their exact contract:
- `obs_v[:dv]` slicing, as today;
- the slot hash in [12..17], via `_legacy_item`;
- the v2-rule projectiles, via `_legacy_proj` (unchanged).

---------------------------------------------------------------------------------------------------------------

## Step 0: independent bug fix first (its own leg, recommended)

`ps2_addr.py:72`: change `OBJ_GRID_N = 110` to `OBJ_GRID_N = 208`.
- This fixes 6.5% of missed chest and 8.6% of missed stone sightings in obs [57..80] / [107..110]. It changes
  values only, not semantics.
- Run the usual 50-episode parity eval and a scouting leg on its own, so its effect is not confounded with v4.
- `ps2_addr` comments: mark `PROJ_CLASSES`, `PROJ_EXCLUDE` and the band comments as *slot3-lineup-specific*
  (PROJECTILES.md TL;DR 1). Rename `CHEST_FALL_VT` to something like `ITEM_GENERIC_VT` (GROUND.md 0.5); it is
  not used by obs.

## Step 1: put the reader on the import path

```
cp re/obs_v4/obs_v4_reader.py re/obs_v4/stage_geom.py .   # the contract lives next to the env, not under re/
                                                           # (stage_geom.py = the vendored spatial encoder)
cp re/obs_v4/surgery_widen_v4.py re/obs_v4/equivalence_v4.py re/obs_v4/measure_item_emb.py .
```
(`surgery_widen_v4.py` and `equivalence_v4.py` import `obs_v4_reader` / `obs_v4_envpatch` from their own folder.
Either copy `obs_v4_envpatch.py` too, or run them from `re/obs_v4/` as the tests do.)

## Step 2: env changes (`powerstone_env_v6.py`)

a) Class attributes. Put these next to `OBS_V3` (line 76), and change `OBS_DIM` (line 495):
```python
    # obs v4 (PS2_OBS_V4=1, needs PS2_OBS_V3=1): 270 dims appended at [160..429] from obs_v4_reader
    # (re/obs_v4/OBS_V4_SPEC.md). [0..159] = v3, unchanged except [12..17] (slot-hash item embedding) which reads 0
    # for 430-dim consumers when PS2_OBS_V4_ITEMEMB=zero (default). Libretro envs only (needs RAM).
    OBS_V4 = os.environ.get("PS2_OBS_V4", "0") == "1"
    OBS_V4_ITEMEMB = os.environ.get("PS2_OBS_V4_ITEMEMB", "zero")
...
    OBS_DIM = (430 if os.environ.get("PS2_OBS_V4", "0") == "1"
               else 160 if os.environ.get("PS2_OBS_V3", "0") == "1" else 122)
```

b) In `_observe`, at line 1444, replace `return np.clip(obs, -5.0, 5.0)` with:
```python
        obs = np.clip(obs, -5.0, 5.0)
        if self.OBS_V4:
            rdr = getattr(self, "_v4", None)
            if rdr is None:
                from obs_v4_reader import ObsV4Reader
                rdr = self._v4 = ObsV4Reader(self._lr_bridge.ram)      # one reader per emulator
            oo = [j for _, j, _ in self._opps(s)[:self.N_OPP]]          # SAME order as the opponent block
            # ONE frame counter per emulator: the learner synth's (view synths count from a later attach)
            obs[160:430], _ = rdr.features(i, oo, self._lr_synth.frame)
            if self.OBS_V4_ITEMEMB == "zero" and not getattr(self, "_legacy_item", False):
                obs[12:18] = 0.0
        return obs
```
(`i = self.AGENT_PLAYER - 1` is already defined at the top of `_observe`.)

c) In `powerstone_env_libretro.py` `_send` (line 59), restart the reader clocks on a loadstate. Add this inside the
existing `if cmd.startswith("loadstate"):` branch:
```python
            if getattr(self, "_v4", None) is not None:
                self._v4.reset()
```

d) In `__init__`, add a guard: `assert not self.OBS_V4 or self.OBS_V3, "PS2_OBS_V4 needs PS2_OBS_V3"`.

## Step 3: FFA self-play (`ffa_selfplay_env.py`)

`_obs_from_view` needs **no change**. It swaps `AGENT_PLAYER` / `_active_opp` and calls `_observe`, so the v4
block is computed for that seat automatically. The reader's scan is shared: 0.251 scans per observation build,
measured.

In `step()`, extend the existing legacy-contract lines 282–287:
```python
            kv, dv = kd_for(v.model)
            self._legacy_proj = (dv == 122)
            self._legacy_item = (dv <= 160)       # obs v4: a v2/v3 pool policy keeps the slot-hash [12..17]
            try:
                obs_v = self._obs_from_view(v)
            finally:
                self._legacy_proj = getattr(self, "_legacy_proj_main", False)
                self._legacy_item = getattr(self, "_legacy_item_main", False)
```
Make the same `_legacy_item` addition in `selfplay_env.py:123` if the 2-seat env is still used.

## Step 4: dimension plumbing

| file | line | change |
|---|---|---|
| `obs_stack.py` | 92 | `BASE_DIMS = (430, 160, 122)`. Checked: 430·K never collides with 160·K or 122·K for K in OFFSETS_BY_K |
| `train_selfplay_async.py` | 260 | `_D = 430 if os.environ.get("PS2_OBS_V4", "0") == "1" else 160 if ... else 122`. Add `obs_v4=` to the `[config]` print at line 315 |
| `eval_parity.py` | 110 | add `env._legacy_item_main = env._legacy_item = (_d <= 160)` |
| `play_vs.py` | 92, 101 | same |
| `watch_play.py` | 75 | same |
| `league_leg_async.sh` | 79 | add `PS2_OBS_V4=*\|PS2_OBS_V4_ITEMEMB=*` to the arena-flag allowlist |
| `league_battery.sh` | 52 | mirror the v3 block: if the leg's `leg_modes.txt` row has `PS2_OBS_V4=1`, `export PS2_OBS_V4=1` (and `PS2_OBS_V4_ITEMEMB` if set) |
| `scout_leg.sh` | 18 | same |

## Step 5: surgery hook (`league_leg_async.sh`, the `league_surgery.txt` case at line 84)

```bash
    obsv4)
      CHECK="from obs_stack import kd_for; from recurrent_policy import load_model as f; ok = kd_for(f('${PREV}'))[1] == 430"
      OUT="./powerstone_v6_leg$((N-1))_v4.zip"
      CMD="python surgery_widen_v4.py \"$PREV\" \"$OUT\" --zero-item-emb"; TAG="OBS=v4" ;;
```
Then, for the cutover leg N:
```
echo "N obsv4" >> league_surgery.txt
printf '%s PS2_OBS_V4=1 PS2_OBS_V4_ITEMEMB=zero\n' "$(tr -d '\n' < league_env.txt)" > league_env.txt
```
- **Order matters.** `league_surgery.txt` already lists `110 lstm128` and `113 joint63`. They apply only to zips
  that lack them, so `obsv4` simply runs last.
- `surgery_widen_v4.py` handles both the MLP and the SkipLSTM lineage. It widens the policy/value first layers
  (the K lag slots plus the trailing lstm_out columns) and `lstm_{actor,critic}.weight_ih_l0`, and sets
  `lstm_input_dim` to 430.
- If the `--zero-item-emb` gate below fails, drop the flag and use `PS2_OBS_V4_ITEMEMB=keep`.

## Step 6: checks before the league leg (all must pass; mirror `cutover_v3.sh`)

Run these on the 9950X, `source ~/ps2rl/bin/activate`, with `PS2_OBS_V2=1 PS2_OBS_V3=1`. Set `PS2_CORE` and
`PS2_V4_TEST_INSTANCE` for Linux.

1. **Reader tests** (`python re/obs_v4/test_obs_v4.py`): must end with `0 failures -> PASS`.
   - What it covers: 18k frames on slots 1/2/3 × 4 seats; ranges; one-hots; seat symmetry; independent RAM
     cross-checks; determinism; and the env-integration parity of obs[:160] against the v3 builder, including
     FFA `_obs_from_view`.
   - On the Mac this took 75 s. Check that `obs_v4_stats.txt` shows `UNEXPECTED dead features (0)`.
2. **Surgery unit test** (`python re/obs_v4/test_surgery_v4.py`): needs sb3_contrib, so it covers the SkipLSTM path
   there. It must report 4/4 PASS.
3. **Item-embedding gate** (decides `--zero-item-emb`):
   - Run `PS2_OBS_V3=1 python measure_item_emb.py <live leg zip> --steps 3000 --slot 3`, then again with
     `--slot 2`.
   - Proceed with `zero` only if greedy agreement on steps with an embedding is ≥ 90%.
   - Mac reference (v2 models): 67/67 and 6/9.
4. **Live equivalence**:
   - Run `python re/obs_v4/equivalence_v4.py <live leg zip> <widened zip> --zero-item-emb --steps 600`. Use the
     same zero flag as the surgery.
   - It must print `PASS`: max |logit| and |value| difference < 1e-4 against the parent fed the same prefix, and
     greedy agreement N/N.
   - It also reports agreement against the parent on the real v3 prefix; this is the size of the [12..17] change.
   - Mac reference (MLP built from sweep40): 7.6e-06 / 3.8e-06, 600/600, and 597/600 on the real prefix.
5. **Battery parity**: evaluate the widened zip with `league_battery.sh` / `eval_parity.py` under
   `PS2_OBS_V4=1` against the parent under v3 on lv8mix, with the same episode count as the usual leg battery.
   - Expect equality within noise. With `--zero-item-emb`, expect only the measured small shift.
   - A large drop means the integration is wrong. Most likely causes: a wrong opponent order, `_legacy_item`
     not set for the main model, or the frame counter.
6. **Throughput smoke**: one short leg with `league_trainer.txt = hold` afterwards. Check that `[config]` shows
   `obs_dim=430` and `lstm_input=430`, and that steps/s stays within 2% of leg 121 (expected about +2% obs cost;
   section 7 of the spec).
7. **Overlay eyeball**: watch `re/obs_v4/videos/*.mp4` with `videos/WATCHLIST.md`. To regenerate:
   `python re/obs_v4/overlay_v4.py --slot 2 --seconds 75 --out re/obs_v4/videos/slot2_lv3_ffa.mp4`. Slot 1 also
   needs `--chests-first 50`. `calibrate_projection.py` refits `projection.json` if the camera ever looks off.

## Step 7: what NOT to switch on yet

- The spatial block H (obs[403..429]) is **live** on Desert and all zeros on other stages (`map_present = 0`). If
  training ever moves to a mapped multi-phase stage, add its map to `SpatialEncoder(maps=...)` first. Columns that
  are 0 after surgery stay at 0 while the input is 0, so a new map is a soft start.
- Do not retire the v3 projectile slots [81..92] / [154..159] at the cutover. They stay for the prefix contract.
  Zeroing them for v4 consumers is a later, separately measured step, like [12..17].

## Rollback

1. Remove `PS2_OBS_V4=1 PS2_OBS_V4_ITEMEMB=...` from `league_env.txt`.
2. Delete the `obsv4` line from `league_surgery.txt`.
3. Point `league_state.txt` back at the pre-surgery zip, `powerstone_v6_leg<N-1>_*.zip`. The widened zip is a new
   file; the parent is never modified.

Steps 2–4 are all gated on the flag, so with `PS2_OBS_V4` unset every env and script behaves exactly as at leg 121.
