# Power Stone 2 RL — Linux/libretro port + self-play

Drop this `linux_port/` folder next to `powerstone_env_v6.py` in the repo,
copy the repo to the superserver, and work through the steps in order.
Design principle: **the env's parser, obs bus, reward path and the trained
checkpoints are untouched** — we replace only the transport (lua + files →
in-process RAM reads and button masks) and the opponent (COM → frozen self).

Grounding: sdlarch-rl's `RetroEmulator` (verified against the source) gives
`get_ram()` (zero-copy SYSTEM_RAM numpy view), `set_button_mask(mask, player)`
(16-slot RetroPad mask, per player), `get_state()/set_state()` (savestate
bytes; `.state` files are gzip'd), `run()` (exactly one frame), and analog
buttons report full-press when masked — enough for everything below.

## 0. Build (once, on the superserver)

```bash
cd ~/sdlarch-rl && cmake -B build && cmake --build build   # you have this
# 1v1 self-play works out of the box (MAX_PLAYERS = 2).
# For 4-player FFA later: edit src/sdlarch.h -> MAX_PLAYERS = 4, rebuild,
# and confirm flycast's per-port controller config (4 pads) in core options.
```

## 1. Go/no-go: RAM access  ← do this first, it gates everything

```bash
DISPLAY=:99 SDL_AUDIODRIVER=dummy python3 probe_ram.py \
  --core ../cores/flycast_libretro.so --game "../Power Stone 2 (USA).chd"
```

Want: `SYSTEM_RAM exposed: 16 MiB` and plausible health floats. If the
addresses miss, the script auto-scans for the 4×1000.0 signature and prints
the `RAM_DELTA` to set in `ps2_addr.py`. If `get_ram()` itself throws, the
core build doesn't export SYSTEM_RAM — that's the only hard blocker, and the
fix is a small flycast patch (or ctypes over `get_memory_pointer()`).

## 2. Button mapping sanity (30 seconds, saves a week)

Needs one savestate first (step 3, or any mid-match state):

```bash
python3 calibrate_buttons.py --core ... --game ... --state states/slot1.state
```

Confirm dpad moves x/z, DC A jumps (dy > 0), attacks drain health. Fix
`DC_TO_RETRO` in `flycast_bridge.py` if anything is swapped.

## 3. Recreate savestates (the one real one-time cost)

Standalone-Flycast states don't load in the libretro core. On any Linux
machine with a display (or X-forward/VNC to the server):

```bash
python3 make_savestates.py --core ... --game ... --states ./states
```

- **CPU-opponent states** (parity testing): mirror the Windows lineup —
  P2 human, set COM level in options first, F1–F7 stamps slot1–7.
- **Self-play states** (Leg I): VS mode, **both DC ports human** (TAB
  switches which port the keyboard drives), save at round start. Start with
  ONE stage; widen after parity.

Keep the in-game bot on **DC port B (P2)** — every anchor and the whole
Windows lineage assume it.

## 4. Parity smoke test

```bash
python3 powerstone_env_libretro.py     # 100 random steps, prints reward
```

Then the real check: `test_env_v6.py` logic against this env, and load
`powerstone_v6_ppo_legG_27911k.zip`, run 50 episodes on a CPU-opponent
state, and compare win%/picks/forms to the Windows band for that slot. If
behavior metrics land in-band, obs semantics survived the port.

Known v1 gaps (documented quiet-degrades, fix after parity):
- chest fragment is zeros (stoneObjScan not ported) → obs [107..110] read 0
- spin gate warms up over 2 sweeps after loadstate (same as lua)

## 5. Self-play (Leg I)

```bash
mkdir opponent_pool && cp ../checkpoints_v6/ps_v6_27911619_steps.zip \
  ../checkpoints_v6/ps_v6_2{0,4}*_steps.zip opponent_pool/   # seed variety
PS2_NENVS=6 python3 train_selfplay.py
```

- Learner = P2 (warm-started from Leg G), opponent = P1, frozen policy
  sampled per episode: 50% from the newest 10 snapshots, 50% uniform over
  history. `SnapshotToPool` adds the live model every 500k.
- **Metrics change meaning**: win% vs a frozen self hovers ~50% by
  construction. Progress = beating OLDER snapshots at >50% (pool ELO),
  plus picks/forms/dmg trends in the untouched ep_stats CSVs. Held-out
  eval vs COM lv4 stays the external yardstick — run it per snapshot.
- One integration point is left deliberately loose: `selfplay_env` calls
  `self._build_obs(s)` for the P1 view — wire it to whatever
  `powerstone_env_v6.py` actually names its obs constructor, and check the
  AGENT_PLAYER flip covers every P2-specific branch in it.

## Scaling (the "can we still do 10?" question)

Yes — self-play does not multiply emulator cost. The emulator (~95% of
each instance's CPU) runs the same frames either way; the opponent adds one
extra MLP forward per env step (a 2×64 net on CPU is ~50µs — noise). What
changes per box:

| box | instances | why |
|---|---|---|
| 12700K (Windows, today) | 10 | unchanged — but it can't do self-play (lua channel drives one port) |
| 7600 superserver (6c/12t) | start 5–6, benchmark | libretro in-process reads remove the file-bridge overhead + no vsync, so per-instance fps should beat the Windows rig; find the knee, don't guess |
| rented 48-core | ~40+ | same benchmark × cores |

Throughput per instance should IMPROVE vs Windows: no file polling, no 2ms
sleeps, no window compositor — the step loop is `set mask → run 6 frames →
read RAM`, all in-process.

## File map

| file | what |
|---|---|
| `ps2_addr.py` | every guest address (from RAM_MAP.md + calibration files) |
| `ps2_ram.py` | RAM reader + exact v7 (80-field) state-line synthesis |
| `flycast_bridge.py` | RetroEmulator wrapper: press/axis/loadstate semantics, hold-until-next |
| `powerstone_env_libretro.py` | EnvV6 subclass — transport swapped, everything else inherited |
| `selfplay_env.py` | 1v1 mirror: learner P2 vs frozen-pool P1 |
| `train_selfplay.py` | Leg I trainer: warm start, pool snapshots, BC rehearsal off |
| `probe_ram.py` | step-1 go/no-go + address auto-scan |
| `calibrate_buttons.py` | empirical RetroPad↔DC mapping check |
| `make_savestates.py` | interactive 2-port savestate creator |
