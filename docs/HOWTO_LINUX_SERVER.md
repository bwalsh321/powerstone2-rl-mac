> Moved to `docs/` on Sep 10 2026. These are the porting notes from the Windows-to-Mac move (Aug 2026), kept for the record; the current entry points are the root README.md and linux_port/LINUX_BRINGUP.md.

# Power Stone 2 RL — rented Linux server: copy folder, run script, train

Written Aug 23 after the M2 port session. The Mac evening proved the port;
this doc turns it into a repeatable recipe for any Ubuntu/Debian x86_64 box.
`setup_linux.sh` (same folder) automates steps 2–5.

## 0. What travels (this folder IS the deployment)

Copy the WHOLE `macbook_migration/` folder to the server. It now contains
everything the port needs, including things not in the original kit:

- `sdlarch-rl/` — the harness, **with local patches not in upstream git**
  (see "Patches" below). Do NOT re-clone from GitHub — you'd lose them.
  The `build/` dir can be deleted before copying (it's rebuilt native).
- `linux_port/` — env + tools, patched (HLE BIOS + VMU core options wired,
  /dev/shm fallback, savestate maker with controller + display flip).
- `linux_port/system/dolphin-0/` — **VMU + flash images from the rig**
  (completed save: Pride, desert stage, full unlocks). Every instance
  needs a copy (the setup script seeds dolphin-0..N-1 automatically).
- `linux_port/states/` — savestates recorded under the libretro core on
  the Mac. These are CORE-VERSION-SENSITIVE: use the same flycast nightly
  on the server as on the Mac (see step 3) or re-record.
- `Power Stone 2 (USA).chd` — one level above linux_port, where the tools
  expect it (`../Power Stone 2 (USA).chd`).
- `powerstone_v6_ppo_legG_27911k.zip`, `powerstone_v6_ppo_legM_final.zip`
  — parity yardstick + reigning champ.

~~Still needed from the Windows rig~~ — kit #2 delivered all of it
(Aug 24): `linux_port/powerstone_env_v6.py` (no local imports, needs
`gym==0.26.2` in the venv), `linux_port/opponent_pool/` seeded with 8
ps_v6 checkpoints (0.2M→31.9M steps), and Leg G copied to
`linux_port/powerstone_v6_ppo.zip` for the warm start. Nothing else is
owed from the rig except optional fresh frozen-eval tiebreakers.

## 1. Server sizing

Emulator ≈ 95% of per-instance CPU; self-play adds ~nothing. Start
N_ENVS ≈ physical cores − 2, benchmark the knee, don't guess. RAM: ~1 GB
per instance is generous. GPU irrelevant (PPO on 2x64/2x256 MLP = CPU).

## 2. System packages (Ubuntu 22.04/24.04)

```bash
sudo apt-get update && sudo apt-get install -y \
  build-essential cmake pkg-config git \
  libsdl2-dev libgl1-mesa-dev xvfb \
  python3.11 python3.11-venv python3.11-dev unzip curl
```

Headless GL: flycast needs a real-ish GL 4.x context. Two options, try in
order: (a) `xvfb-run -s "-screen 0 1280x720x24"` with Mesa llvmpipe —
slow-ish but proven path, fine for gates; (b) for throughput, Mesa's
`LIBGL_ALWAYS_SOFTWARE=1` vs GPU EGL — benchmark on the actual box.
The step loop's cost is emulation, not blit, so llvmpipe usually holds.

## 3. Flycast core — PIN THE VERSION

Mac used the buildbot nightly of Aug 22–23 2026. Grab the matching Linux
build (savestates + variables behavior must match):

```bash
curl -L https://buildbot.libretro.com/nightly/linux/x86_64/latest/flycast_libretro.so.zip \
  -o /tmp/fc.zip && unzip -o /tmp/fc.zip -d cores/
```

If states refuse to load: nightly drifted — either fetch the same-date
build from buildbot archives, or re-record states (make_savestates works
under xvfb + VNC, or record on the Mac with the matched nightly).

## 4. Python env

```bash
python3.11 -m venv ~/ps2rl && source ~/ps2rl/bin/activate
pip install numpy "stable-baselines3<3" gymnasium torch pygame \
    "gym==0.26.2" "shimmy>=2.0" tensorboard
# gym: powerstone_env_v6 imports it; shimmy: sb3's old-gym compat layer
# (SubprocVecEnv refuses to start without it); tensorboard: model.learn()
# logger. All three bit on the Mac bring-up (Aug 28) — install up front.
# The macOS-only fixes (spawn start method + staggered init) are already
# in train_selfplay.py and are harmless on Linux.
```

## 5. Build the harness

```bash
cd sdlarch-rl
git submodule update --init --recursive   # only if third-party/pybind11 empty
rm -f build/CMakeCache.txt                 # kill any copied mac cache
cmake -B build -DCMAKE_BUILD_TYPE=Release \
  -DPython3_EXECUTABLE="$HOME/ps2rl/bin/python" \
  -DPython_EXECUTABLE="$HOME/ps2rl/bin/python" \
  -DPYBIND11_FINDPYTHON=ON
cmake --build build -j
```

Produces `_retro.so` in the repo root (that's the import; PYTHONPATH
points here).

## 6. Gates, headless flavor (minutes, not the evening)

From `linux_port/`, with `PYTHONPATH=../sdlarch-rl` and
`SDL_AUDIODRIVER=dummy` on everything, wrapped in `xvfb-run`:

```bash
# gate 1 — RAM (probe from a real-match state, no attract-mode guessing)
xvfb-run -a python probe_ram.py --core ../cores/flycast_libretro.so \
  --game "../Power Stone 2 (USA).chd" --state states/slot1.state
# gate 3 — buttons
xvfb-run -a python calibrate_buttons.py --core ../cores/flycast_libretro.so \
  --game "../Power Stone 2 (USA).chd" --state states/slot1.state
# gate 4 — env smoke, then the legG 50-episode parity run
PS2_CORE=../cores/flycast_libretro.so xvfb-run -a python powerstone_env_libretro.py
xvfb-run -a python -u eval_parity.py --core ../cores/flycast_libretro.so \
  --game "../Power Stone 2 (USA).chd" --slot 2 --episodes 50 2>&1 | tee parity_out.txt
```

Use `python -u` whenever piping through `tee` — stdout is block-buffered
through a pipe, and the run looks dead while stderr warnings jump ahead.
`diag_state.py` (same folder) is the savestate triage tool: loads a slot
headless and reports the health quad per second (hands-off, then A taps,
then Start taps) with a reaches-fight verdict.

Gate 2 (savestates) should NOT need re-doing if the core version matched.
Savestates may be stamped AT ROUND START (health bars need not be up
yet): the env's loadstate pumps up to 1200 frames until the match goes
live (fix #3 below). A state that can't reach a live match hands-off
within ~1200 frames (menus, character select) will NOT work — check with
diag_state.py.

## 6b. Libretro-era env fixes (Aug 24, all in powerstone_env_libretro.py)

The lua-era parent env assumes a BACKGROUND emulator advancing in wall
time; in-process libretro frames advance only when pumped. Four fixes
restore the old invariants — if the parent env is ever updated from the
rig, make sure these overrides survive:

1. `_wait_for_bridge` override: liveness check pumps `run_frames(4)`
   between its two reads instead of `time.sleep(0.3)` (else "Bridge frame
   counter not advancing" forever — the original gate-4 smoke blocker).
2. Pump-on-stale in `_parse_state_once`: re-reading the same synth frame
   runs 1 frame first, so the parent's wall-clock poll loops (reset's
   match-ready loop, `_wait_frames`) make progress instead of spinning.
3. `loadstate` intro pump in `_send`: after any loadstate, pump up to
   1200 frames until match-ready — round-start stamps play their intro
   out (~306 frames for slot2) instead of starving reset's retry loop,
   which reloads every 3rd try and wipes progress.
4. Random 0-59 frame stagger after the intro pump: without the lua era's
   wall-clock jitter, a deterministic policy replays BYTE-IDENTICAL
   episodes (seen live: eval eps 2-5 with identical stats). The stagger
   re-creates the Windows rig's frame-alignment spread; in-distribution,
   harmless for training.

**Gate-4 status (Aug 24, Mac):** the mechanics above all work, but the
50-ep parity eval FAILED below band on slot 2 — win 14% (band 63-75),
picks 4.60 (6.8-7.5), forms 0.46 (1.4-1.9). Combat and buttons are fine
(form attacks land, dmgF > 0 when formed; the one thing broken is gem
acquisition). Prime suspect: `ps2_ram.py`'s chest fragment is hardcoded
zeros (STONE_OBJ_MODE never ported) while legG trained with live chest
obs — and chests are the gem source. The chest addresses are NOT in the
kits: porting needs `powerstone.lua` + `RAM_MAP.md` (chest class window
/ object-ledger addrs) from the rig ("kit #3"). Second suspect, testable
now: `PS2_FRAME_SLIP=<k>` env var runs k extra held-input frames per
action, emulating the rig's free-running-emulator latency; try a 20-ep
eval at 2-4. Do not start server training until parity passes.

sb3 note (matters for training, harmless for eval): PPO.load of the
rig's zips under py3.11 warns `Could not deserialize object clip_range /
lr_schedule` (lambdas pickled under the rig's python). `predict()` never
touches them; `train_selfplay.py` warm-starts MUST pass
`custom_objects={"clip_range": 0.2, "lr_schedule": lambda _: 2.5e-4}`
(match the rig's values) or `.learn()` will call the broken stubs.

## 7. Train

```bash
mkdir -p opponent_pool && cp <your checkpoints_v6 picks> opponent_pool/
cp powerstone_v6_ppo_legG_27911k.zip powerstone_v6_ppo.zip  # warm start
PS2_NENVS=<cores-2> xvfb-run -a python train_selfplay.py
```

Watch: pool ELO (beating OLDER snapshots >50%), picks/forms/dmg in
ep_stats CSVs, held-out eval vs COM lv4 per snapshot. Raw win% hovers
~50% by construction — that's self-play working, not failing.

## Patches carried in this folder (vs upstream sdlarch-rl)

All in `sdlarch-rl/src/sdlarch.cpp` + `CMakeLists.txt`, applied Aug 23:

1. `_strdup`/`mkdir` POSIX guards (mac/linux compile).
2. glad linked into `pcsx2_headless` on non-Windows (mac ld strictness;
   harmless on Linux).
3. macOS-only GL 4.1 core-profile context override (ifdef'd APPLE — inert
   on Linux).
4. Fragment shader modernized to real GLSL 150 (`FragColor`/`texture()`)
   — required on mac, valid everywhere.
5. **GET_VARIABLE consults `set_variable` overrides first**, including
   keys the core never registered via legacy SET_VARIABLES. This is how
   `flycast_hle_bios` and the VMU device options reach the core.
6. **`set_variable` raises the variables-updated flag** — flycast only
   attaches VMU/expansion devices on a post-startup variables update.
7. `core_log` printable in Release via `SDLARCH_LOG=1`.
8. CMake: pybind11 submodule build, venv python pinning, `.so` suffix on
   macOS (mac-only effect).

Python-side conventions (already in the linux_port scripts): every entry
point sets `flycast_hle_bios=enabled` (+ legacy `reicast_` alias) and
`flycast_device_port1_slot1=VMU`, `flycast_device_port2_slot1=VMU` before
init. VMU/flash images are read from `./system/dolphin-<instance>/`
relative to the CWD of the process (i.e. `linux_port/`).
