# Linux bring-up (Ryzen 9950X, Sep 24 2026) — the one path

Older notes (`docs/HOWTO_LINUX_SERVER.md`, the root `setup_linux.sh`, the previous version of this file)
are superseded by `linux_port/setup_9950x.sh`. Do not `git clone bwalsh321/sdlarch-rl` into the repo root:
the patched harness source is tracked in THIS repo under `sdlarch-rl/` since Sep 23 2026.

## 1. Clone and provision
```bash
git clone https://github.com/bwalsh321/powerstone2-rl-mac.git ~/macbook_migration
cd ~/macbook_migration && bash linux_port/setup_9950x.sh 14
```
The script installs apt packages (cmake, SDL2, Mesa GL/EGL, xvfb, tmux, python3.11), makes the `~/ps2rl`
venv from `requirements.txt` (+ the CPU torch wheel), downloads the flycast core to `~/cores/`, clones
pybind11 v3.0.1 into `sdlarch-rl/third-party/` (the submodule link is not in git), builds the harness
TWICE — the default 2-port build into `sdlarch-rl/` and the 4-port build (`-DSDLARCH_MAX_PLAYERS=4`)
into `sdlarch-rl/p4/` — checks both import under `xvfb-run`, and seeds `system/dolphin-0..13`.
It has not run on real Linux yet: the first run on the 9950X is the test; re-run after fixing anything.

## 2. Transfer the runtime files (not in git, ~4.7 GB)
From the Mac: the game `Power Stone 2 (USA).chd` (repo root), `linux_port/states/`, `states_mixed/`,
`system/dolphin-0/`, `pool_league/` (1.6 GB, the opponent pool), optionally `receipts/` and `videos/`.
Model zips are tracked in git. The script prints the rsync lines (section 7) and checks presence.

## 3. Headless rule
**Oct 1 2026, as run on the 9950X: GPU EGL, no X server.** Every relay script sources
`linux_gpu_env.sh`, which sets `SDL_VIDEODRIVER=offscreen` (SDL's EGL driver: a real GL context, no window,
no DISPLAY) and points glvnd at the NVIDIA EGL vendor (`10_nvidia.json`, the RTX 3090). Measured: 16 parallel
instances x 3600 frames = 14.6 s on the 3090 vs 35.8 s on the Radeon iGPU (EGL); one instance under Xvfb burned
~45 CPU-s per 3600 frames vs ~10 with a GPU (llvmpipe). Prerequisite: the NVIDIA driver must load, which under
Secure Boot means the DKMS signing key is enrolled (`sudo mokutil --import /var/lib/shim-signed/mok/MOK.der`,
reboot, MOK Manager -> Enroll). `PS2_RENDER=xvfb` restores the Xvfb path below (expects :99).
Python: the box runs Ubuntu 24.04's python3.12 venv (not 3.11); every pinned wheel installed and parity passed.

Superseded plan (kept for the fallback):
One PERSISTENT X server for the whole relay (Astra Sep 25: the launchers and battery shards call python
directly and spawn tmux sessions, so a per-command `xvfb-run` does not cover them):
```bash
sudo tee /etc/systemd/system/xvfb99.service >/dev/null <<'UNIT'
[Unit]
Description=Xvfb :99 for the Power Stone 2 relay
[Service]
ExecStart=/usr/bin/Xvfb :99 -screen 0 1280x720x24 -nolisten tcp
Restart=always
[Install]
WantedBy=multi-user.target
UNIT
sudo systemctl enable --now xvfb99
```
Every relay script exports `DISPLAY=${DISPLAY:-:99}` on Linux (league_leg_async.sh, league_battery.sh,
scout_leg.sh, cutover_v3.sh), with `SDL_AUDIODRIVER=dummy`. NEVER set `SDL_VIDEODRIVER=dummy`: the harness
opens a hidden real GL 4.1 window and dies without one. Try GPU EGL later as a speed experiment.

## 4. Gates, in order (all must pass before training moves)
- G1 imports (in the script). G2 files present (in the script).
- G3 headless probe: `probe_ram.py` on `states/slot3.state` reads four live health floats.
- G4 unit tests: `PS2_OBS_V3=1 python test_obs_v3.py` and `python test_obs_context.py` print 0 failures.
- G5 PARITY: `eval_parity.py --slot 3 --model powerstone_v6_leg73_league.zip --episodes 200` under
  `PS2_OBS_V2=1` (deterministic). PASS rule (Astra Sep 25: a fresh point estimate need not fall inside the
  reference interval): two-proportion z-test between the box's 200 and the Mac's 500 (leg 73: 146/500) with
  p >= 0.05, AND the absolute gap <= 6 points; repeat on slot 2 (243/250). A v3 zip (leg 74+) needs
  `PS2_OBS_V3=1`. Pin the core: record `sha256sum ~/cores/flycast_libretro.so` in the parity receipt and
  in HANDOFF; the nightly URL is mutable, so keep the exact file that passed.
- Speed: time G5. The Mac runs 10 shards x 50 lv8 episodes in ~15 min; the league needs 10 actors + the
  scout instance, so measure with 12 emulator instances alive before choosing `n_actors`.

## 5. Moving the league
Copy the relay files (`league_state.txt`, `league_trainer.txt`, `league_optim.txt`, `league_env.txt`,
`leg_modes.txt`) and the latest zip; stop launching legs on the Mac (write `hold`), launch on the box with
`bash league_leg_async.sh` in tmux. The Mac stays as it is until two legs on the box land in band.
`caffeinate` is Mac-only and guarded in the scripts; tmux is required on both.
