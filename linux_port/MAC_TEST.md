# Power Stone 2 RL — M2 MacBook port test (the "can I skip Linux?" answer)

Companion to `README_PORT.md` (same folder). That doc's steps are the
truth; this one is the macOS-specific setup in front of them, written for
one evening on the M2. Nothing here touches the Windows rig — fully
parallel workstream.

The "Linux" in linux_port was always incidental: the port targets
**libretro**, and every load-bearing piece (flycast core, `get_ram()`
numpy view, button masks, in-memory savestates, `run()` one frame) is
cross-platform. macOS differences are all in the plumbing around it:

| Linux plan | macOS reality |
|---|---|
| `DISPLAY=:99` (Xvfb virtual display) | not a thing — just let a real window open. For the test phase that's a FEATURE: you can see the screen, make savestates, eyeball behavior. Hidden/offscreen GL is a later optimization, not a gate. |
| `flycast_libretro.so` | `flycast_libretro.dylib` (arm64) |
| `SDL_AUDIODRIVER=dummy` | same, works on macOS |

## 0. One-time machine setup

```bash
xcode-select --install                # compiler toolchain
brew install cmake sdl2 pkg-config git python@3.11
python3.11 -m venv ~/ps2rl && source ~/ps2rl/bin/activate
pip install numpy "stable-baselines3<3" gymnasium torch
# torch here is arm64-native with MPS — the 3090 conversation's Mac cousin.
```

## 1. Get the repo + the unpublishables onto the Mac

Copy the project folder from sff-turd (SMB / external drive / whatever).
The code is small; the two things that MUST come from your own machine and
must NEVER touch git (the .gitignore hard-denies already cover them):

- `Power Stone 2 (USA).chd` — from any flycast-inst folder
- the Dreamcast BIOS files — from `flycast-win64-2.6/data/`

## 2. Get the flycast libretro core (arm64)

Easiest: install RetroArch (`brew install --cask retroarch` or from
retroarch.com), open it once, Online Updater -> Core Downloader ->
"Sega Dreamcast/NAOMI (Flycast)". The core lands in
`~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib`.
Put the BIOS files in RetroArch's `system/dc/` dir (Settings -> Directory
shows the path). Sanity check before any of our code: **boot the CHD in
RetroArch itself.** If Power Stone 2 runs in RetroArch on the M2, the
core/BIOS/game triangle is proven and every later failure is our harness,
not the emulator.

## 3. Build sdlarch-rl

Clone the same sdlarch-rl you have on the superserver plan, then:

```bash
cd sdlarch-rl && cmake -B build && cmake --build build
```

This is the likeliest place to spend the evening's swearing budget —
it's C+SDL and verified on Linux, not macOS. Expected friction, in order:
OpenGL deprecation warnings (ignore), a missing `-framework OpenGL` in the
link step (add it), Linux-only includes (`#include <GL/gl.h>` ->
`<OpenGL/gl.h>` behind an `#ifdef __APPLE__`). If MAX_PLAYERS matters
later remember the README's note: 2 out of the box, 4 needs the
`sdlarch.h` edit + rebuild. If the build fights for more than an evening,
stop and report — that's the signal the Mac path needs a different
harness, and the Linux plan is unhurt.

## 4. Run README_PORT.md steps 1-4, mac flavor

Same order, same gates — only the invocation changes:

```bash
cd linux_port
SDL_AUDIODRIVER=dummy python probe_ram.py \
  --core ~/Library/Application\ Support/RetroArch/cores/flycast_libretro.dylib \
  --game "../Power Stone 2 (USA).chd"
```

- **Gate 1 (probe_ram):** want `SYSTEM_RAM exposed: 16 MiB` + plausible
  health floats. Address misses auto-scan and print a `RAM_DELTA` for
  `ps2_addr.py`. `get_ram()` throwing is the ONLY hard blocker (core not
  exporting SYSTEM_RAM — fixable, but stop and report).
- **Gate 2 (make_savestates):** the visible-window step, and why the Mac
  is the right LAB even if a Linux box becomes the factory. VS mode, both
  ports human, TAB to switch which port the keyboard drives, F1-F7 stamps
  slots. Bot stays on **DC port B (P2)** — the entire Windows lineage
  assumes it. Standalone-Flycast .state files do NOT load here; that
  re-recording is the one real one-time cost.
- **Gate 3 (calibrate_buttons):** dpad moves x/z, A jumps, attacks drain
  health; fix `DC_TO_RETRO` in `flycast_bridge.py` if swapped.
- **Gate 4 (parity):** `python powerstone_env_libretro.py` for the
  100-step smoke, then the real one — load
  `powerstone_v6_ppo_legG_27911k.zip`, 50 episodes on a CPU-opponent
  state, compare win%/picks/forms to that slot's Windows band. In-band =
  the obs semantics survived the port and every checkpoint is portable.

Known quiet-degrades at v1 (documented in README_PORT, fix after parity):
chest obs [107..110] read zeros; stone spin gate warms up ~2 sweeps after
loadstate.

## 5. What passing buys (why this evening is worth it)

Cadence: python owns the frame loop, so 6 frames/decision EXACTLY, at any
wall-clock speed — the turbo-vs-cadence war (HANDOFF, Leg I forensics)
simply ends. No windows to tile, no F9 focus, no zombie processes, no
boot races, no boot sentry. And the port is write-once: the same python
runs on the M2 (lab: visible screen, savestate making, quick evals), the
32-core box or a rented Linux server (factory: 20+ headless cores), and
eventually multiple machines feeding one learner.

Report back per gate — especially gate 1's exact output and any gate-3
swaps, since those calibrations feed back into this folder for whichever
machine runs next.
