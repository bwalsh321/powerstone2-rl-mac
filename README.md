# Power Stone 2 RL

> **TODO (Blake): intro.** One or two paragraphs in your own voice — what this
> is, why Power Stone 2, the no-pixels hook, the family/game-night angle.
> Everything below this block is technical scaffold and can stay.

> **TODO (Blake): the story.** Windows rig → Linux plan → M2 port → the leg
> program → the 7950X. The receipts live in `HANDOFF.md`; this section is the
> human version.

## How it works

The agent never sees the screen. Instead:

- **Observation** — a zero-copy numpy view of the emulator's 16 MiB
  SYSTEM_RAM, parsed into a ~122-dim vector (player/opponent health,
  positions, forms, picked-up stones, the object ledger) by
  `linux_port/powerstone_env_v6.py` + `linux_port/ps2_ram.py`.
- **Action** — a 16-slot RetroPad button mask per player, written straight
  into the core each frame.
- **Transport** — the [sdlarch-rl](https://github.com/paulo101977/sdlarch-rl)
  libretro harness (our macOS fork:
  [bwalsh321/sdlarch-rl](https://github.com/bwalsh321/sdlarch-rl)) running the
  flycast core in-process, pumped one frame at a time.
- **Opponent** — self-play: frozen snapshots of past policies drive the other
  seat, sampled from a growing pool.

## What you need

Nothing copyrighted ships in this repo. To run it you supply:

1. **Your own dump of Power Stone 2 (USA)** as a `.chd`, from a disc you own.
   It lives at the repo root as `Power Stone 2 (USA).chd` (gitignored).
2. **The flycast libretro core** — easiest via RetroArch's core downloader or
   the [libretro buildbot](https://buildbot.libretro.com/nightly/); on macOS
   it lands at
   `~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib`.
3. **The patched harness** — clone
   [bwalsh321/sdlarch-rl](https://github.com/bwalsh321/sdlarch-rl) *next to
   this repo's folder or inside it as `sdlarch-rl/`* (gitignored here; it's
   its own repo). The macOS patches (GL 4.1 core context, CMake/venv fixes,
   GLSL 150 shader, POSIX shims) are committed there, on top of upstream.
4. **Python 3.11** and the pinned deps in [`requirements.txt`](requirements.txt).

## Setup

All commands below run from `linux_port/` with the venv active, and every
emulator-touching command uses the same prefix:

```bash
export PS2_PREFIX='SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:.'
export CORE="$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib"
export GAME="../Power Stone 2 (USA).chd"
```

### 1. Python env

```bash
python3.11 -m venv ~/ps2rl
source ~/ps2rl/bin/activate
pip install -r requirements.txt
```

### 2. Build the harness

```bash
cd sdlarch-rl
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
cmake --build build   # produces _retro.so in the repo root
```

macOS note (do this once on any new Mac — cures a modal that can hang
headless boots after a prior crash):

```bash
defaults write org.python.python ApplePersistenceIgnoreState YES
```

### 3. First boot + Dreamcast system files

`linux_port/system/dolphin-0/` is where flycast keeps its nvmem + VMU saves.
It is **not** in the repo — the core creates fresh files on first boot.

> **TODO (Blake):** note what the training save had unlocked (Pride, the
> desert stage) and what a fresh save needs before the savestates below can
> be stamped — or whether stock unlocks are enough. Multi-worker training
> seeds `system/dolphin-1..N` by copying `dolphin-0` (see `setup_linux.sh`).

Sanity gates, in order (each verifies the one before):

```bash
python probe_ram.py --core "$CORE" --game "$GAME" --state states/slot1.state   # gate 1: RAM
python calibrate_buttons.py --core "$CORE" --game "$GAME" --state states/slot1.state  # gate 3: buttons
PS2_CORE="$CORE" python powerstone_env_libretro.py    # gate 4 smoke
```

### 4. Stamp savestates

Savestates are game-derived, so they're not distributed either — you stamp
your own with the interactive maker (visible window; keyboard + gamepad;
`F1`–`F7` stamps `states/slotN.state`, `TAB` toggles a controller port in):

```bash
python make_savestates.py --core "$CORE" --game "$GAME" --states ./states
```

The three slots the scripts expect (one slot number = one meaning):

| Slot | Purpose | Recipe |
|------|---------|--------|
| `slot1` | self-play training | VS mode 1v1, desert, **both ports human (TAB both in), both Falcon**, stamped at round start |
| `slot2` | standard eval | Original mode true-FFA, desert, COM difficulty 3, P2 = the bot's seat (Falcon) |
| `slot3` | hard eval ("the lv8 wall") | Original mode true-FFA, desert, COM difficulty 8 |

Verify a stamp headlessly with `python diag_state.py` (healths 4×1000 after
the intro, correct character fingerprint). Menu navigation is also fully
scriptable — see `menu_drive.py`.

### 5. Watch the champion play

The leg-1 self-play checkpoint (49–1 on the slot-2 eval) rendering at
real-time pacing, with sound:

```bash
SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. python -u watch_play.py \
  --core "$CORE" --game "$GAME" \
  --model ./powerstone_v6_ppo_selfplay_leg1.zip --slot 2
```

`SPACE` pauses, `F` fast-forwards, `--record out.mp4` captures, `--slot 3`
shows it fighting the lv8 wall instead.

### 6. Train

```bash
SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. \
  PS2_CORE="$CORE" PS2_NENVS=6 python -u train_selfplay.py
```

- Warm start = `powerstone_v6_ppo.zip`; `PS2_WARM=<zip> PS2_FRESH=1` starts a
  fresh lineage from any seed. `PS2_POOL=<dir>` picks the opponent pool.
- Long legs run under `tmux` via launcher scripts (`launch_leg4.sh` is the
  current watchdog pattern) — never a bare terminal. Workers boot with a 20 s
  stagger to dodge a macOS Metal init race.
- After a leg, run the eval battery (`run_leg4_battery.sh` pattern): 50-ep
  deterministic on slots 3 and 2, plus stochastic A/B probes
  (`ab_selfplay_probe.py`). **Promote the best checkpoint, never the last.**
- The distilled do's-and-don'ts from six legs live in `HANDOFF.md` →
  "PROJECT LAWS".

## Repo layout

| Path | What it is |
|------|-----------|
| `linux_port/` | The whole port: env, trainers, eval battery, launchers, logs |
| `linux_port/powerstone_env_v6.py` | The v6 environment — RAM parser, obs, rewards |
| `linux_port/ps2_ram.py`, `ps2_addr.py` | RAM map + object-ledger scan (stones/chests) |
| `linux_port/selfplay_env.py`, `train_selfplay.py` | Self-play wrapper + PPO trainer |
| `linux_port/train_com.py`, `train_mixed.py` | vs-COM and mixed-diet trainers |
| `linux_port/bc_pretrain*.py`, `bc_rehearsal.py`, `demos*/` | Behavior-cloning kit + demo corpora |
| `linux_port/eval_parity.py`, `run_*_battery.sh`, `eval_*_out.txt` | Eval battery + the raw receipts for every leg |
| `linux_port/watch_play.py` | Real-time viewer/recorder for any checkpoint |
| `linux_port/powerstone_v6_*.zip` | Named checkpoints: `ppo` = current warm start, `ppo_selfplay_leg1` = overall champion, `leg4_league` = fresh-line champion, `bc*` = BC seeds |
| `linux_port/opponent_pool/` | Frozen `ps_v6`/`selfplay` checkpoints (0.2M → 31.9M steps) |
| `HANDOFF.md` | Living session log — status, results tables, PROJECT LAWS |
| `HOWTO_LINUX_SERVER.md`, `setup_linux.sh`, `setup_mac.sh` | Machine bring-up recipes |
| `README_MIGRATION.md`, `linux_port/MAC_TEST.md`, `linux_port/README_PORT.md` | The porting docs |

**Not in git** (see [`.gitignore`](.gitignore)): the game dump (`*.chd`),
`linux_port/states/` and `linux_port/system/` (game-derived — stamp your
own, steps 3–4 above), the `sdlarch-rl/` harness (its own repo), rendered
video, and runtime churn (checkpoints dirs, pools, bridges, logs).

## Results so far

> **TODO (Blake):** the headline numbers in your voice — leg-1's 49–1, the
> leg-3 program table, the leg-4 synthesis. Source material: `HANDOFF.md`.

## Credits & license

- Harness: [sdlarch-rl](https://github.com/paulo101977/sdlarch-rl) by
  Paulo Sérgio Galdino Sacramento (BSD 3-Clause) — our fork keeps the
  upstream `LICENSE` and only adds macOS build/runtime patches. Upstream's
  channel: [AI Brain](https://www.youtube.com/@AiBrainAi).
- Emulation: [flycast](https://github.com/flyinghead/flycast) via libretro.
- Power Stone 2 © Capcom. No game data, BIOS, or saves are distributed here.

> **TODO (Blake):** pick a license for this repo's own code (MIT?) and add
> the `LICENSE` file.
