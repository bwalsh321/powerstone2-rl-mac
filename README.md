# Power Stone 2 RL

A reinforcement-learning bot for Power Stone 2 (Dreamcast, 2000) that plays four-player free-for-alls. It reads
the game straight out of emulator RAM: no pixels, no decomp, no published memory map. The RAM interface was
reverse-engineered for this project.

**Why:** I grew up playing four-player Power Stone 2 with my two brothers and a stock CPU player that was useless.
I wanted a fourth player at our level. The longer story, including a year stuck on RAM discovery and every recipe
that didn't work, is in the write-up: <!-- Blake: paste the Reddit post URL here -->
[Reddit post](https://www.reddit.com/r/reinforcementlearning/).

## Where it stands (Oct 2026)

The bot plays Falcon. Its grade is **lv8mix**: 1000 free-for-alls against three level-8 (hardest) CPUs, on five
held-out lineups it never trains on. Pure chance in a four-way fight is 25%.

| Stage | lv8mix |
|---|---|
| Early self-play legs, vs three lv8 CPUs | ~2–6% |
| Feedforward policy, 10 actions (legs 100–109) | ~32% |
| + memory (LSTM) and 63 direction×button actions (legs 117–124) | 37% |
| + vision of items, chests, projectiles, hitboxes and props (legs 134–138) | 45% |
| + recent-only opponent pool and balanced training lineups (legs 139–141) | **46%** (best leg 50.8%) |

Each step is a pooled multi-leg read with a control, not a single lucky leg; receipts for every number are in
`linux_port/receipts/`. Things that did not help, with receipts: reward shaping (five legs), behaviour cloning from
my own play, and DAgger-style imitation of my drill corrections (two versions, both cost 6–15 points).

## How it works

- **Observation:** 430 numbers per frame parsed from RAM (`linux_port/powerstone_env_v6.py`, `ps2_ram.py`,
  `obs_v4_reader.py`): health, positions, stones, transformations, plus nearby threats, hitboxes, projectiles,
  ground items, chests, held items and stage geometry. The last 7 frames are stacked.
- **Policy:** recurrent PPO (sb3-contrib) with a skip-connected LSTM (`recurrent_policy.py`).
- **Actions:** 63 direction × button combinations, with buttons as taps so double jumps and repeated attacks work
  (`action_space.py`).
- **Reward:** win/loss, damage dealt and taken (credited via the game's own hit-source pointer), stone pickups
  (capped), special-move damage and a small time cost, zero-sum against the other three.
- **Training:** async actor-learner PPO (`train_selfplay_async.py`), 16 actors on a Ryzen 9950X, ~370 steps/s,
  4M steps per leg. Each episode is a four-player FFA: either three lv8 CPUs, or one lv8 CPU plus two copies of
  past versions of the bot (the opponent pool).
- **Transport:** the flycast libretro core in-process through
  [sdlarch-rl](https://github.com/paulo101977/sdlarch-rl) (fork:
  [bwalsh321/sdlarch-rl](https://github.com/bwalsh321/sdlarch-rl)), rendered headless on the GPU (EGL).

## The relay

Training runs unattended as back-to-back legs (`linux_port/`):

| Script | Job |
|---|---|
| `league_leg_async.sh` | one 4M-step leg from `league_state.txt`, with the recipe flags in `league_env.txt` and one-shot model surgeries in `league_surgery.txt` |
| `relay_watch_linux.sh` | starts the grading run when a leg finishes |
| `league_battery.sh` | grades the leg (lv8mix on 20 emulators, the same 1000 games every leg), runs the hold gate, saves it to the opponent pool, launches the next leg, starts a scouting video |
| `relay_boot.sh`, `relay_alert.sh` | restart after a reboot; 15-minute watchdog writing `claude_bridge/ALERT.txt` |

Edit relay scripts only between runs or with an atomic `mv` (bash reads scripts as it runs them).

## What you need

Nothing copyrighted ships here. You supply:

1. **Your own dump of Power Stone 2 (USA)** as `Power Stone 2 (USA).chd` at the repo root (gitignored).
2. **The flycast libretro core** (RetroArch's core downloader or the libretro buildbot).
3. **The harness:** clone [bwalsh321/sdlarch-rl](https://github.com/bwalsh321/sdlarch-rl) as `sdlarch-rl/`.
4. **Python 3.11+** with [`requirements.txt`](requirements.txt).
5. **Savestates**, stamped from your own save with `make_savestates.py` or headlessly with `menu_drive.py`
   (game-derived, so not distributed): training lineups in `linux_port/states_mixed/` (slots 30–43, 50–68) and
   the held-out set in `linux_port/states/` (slots 90–94).

Linux setup: `linux_port/setup_linux.sh` and [`linux_port/LINUX_BRINGUP.md`](linux_port/LINUX_BRINGUP.md).

## Quick commands

From `linux_port/` with the venv active:

```bash
# watch a bot play (real time)
SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:. python -u watch_play.py \
  --core ~/cores/flycast_libretro.so --game "../Power Stone 2 (USA).chd" --model ./powerstone_v6_leg141_league.zip --slot 3

# grade a bot on the held-out set (one shard; the battery runs 20 x 50)
python eval_parity.py --core ~/cores/flycast_libretro.so --game "../Power Stone 2 (USA).chd" \
  --slots 90,91,92,93,94 --episodes 50 --model ./powerstone_v6_leg141_league.zip
```

Vision bots need the recipe's flags in the environment (`PS2_OBS_V2=1 PS2_OBS_V3=1 PS2_OBS_V4=1 PS2_OBJ_GRID_N=208
PS2_BUTTON_TAP=1`); the battery reads them from the leg's row in `leg_modes.txt`.

## Docs

| File | What it is |
|---|---|
| [`docs/NEXT_CHANGES.md`](docs/NEXT_CHANGES.md) | What is running now and the queue of next changes |
| [`docs/SESSION_HANDOFF_RYZEN.md`](docs/SESSION_HANDOFF_RYZEN.md) | Ryzen relay state and history from legs 104 on |
| [`HANDOFF.md`](HANDOFF.md) | The full lab notebook (Mac/Windows eras through ~leg 106: audits, project laws, every leg) |
| `linux_port/receipts/` | Raw output of every grading and training run |
| `linux_port/re/` | Reverse-engineering workspace behind the vision features |

The Windows-era repo, [bwalsh321/powerstone2-rl](https://github.com/bwalsh321/powerstone2-rl), holds the original
RAM discovery and early experiments; nothing there is needed to run this one.

## On AI assistance

I directed this project and understand every result in it, but I did not type most of the code. Claude wrote the
bulk of the Python and shell under my direction, hunted RAM values with me, and runs the unattended relay. Commits
are co-authored accordingly. The experiment design, the gameplay knowledge that caught wrong telemetry, the demo
recordings and every call on what to run next are mine. Generated code still had bugs; they are documented, not
hidden.

## Credits and license

- Harness: [sdlarch-rl](https://github.com/paulo101977/sdlarch-rl) by Paulo Sérgio Galdino Sacramento
  (BSD 3-Clause); the fork keeps the upstream `LICENSE`.
- Emulation: [flycast](https://github.com/flyinghead/flycast) via libretro.
- Power Stone 2 © Capcom. No game data, BIOS or saves are distributed here.
- This repo's own code: MIT, see [`LICENSE`](LICENSE).
