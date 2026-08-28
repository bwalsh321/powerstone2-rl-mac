# Power Stone 2 RL — macOS port

Training a PPO agent to play **Power Stone 2** (Dreamcast) with no pixels —
the policy reads the emulator's RAM directly and drives the controller through
a libretro harness. This repo is the **macOS (Apple Silicon) deployment** of a
project that started on Windows and moved to Linux: the game env, the self-play
training loop, recorded savestates, and trained checkpoints, all runnable from
this folder.

> Draft README — the intent (per `HANDOFF.md`) was for this prose to be
> rewritten by hand. Treat the sections below as an accurate scaffold, not the
> final voice.

## How it works

The agent never sees the screen. Instead:

- **Observation** — a zero-copy numpy view of the emulator's 16 MiB SYSTEM_RAM,
  parsed into a ~122-dim vector (player/opponent health, positions, forms,
  picked-up stones, the object ledger) by `linux_port/powerstone_env_v6.py`.
- **Action** — a 16-slot RetroPad button mask per player, written straight into
  the core each frame.
- **Transport** — the [sdlarch-rl](https://github.com/paulo101977/sdlarch-rl)
  libretro harness running the flycast core in-process. The emulator is pumped
  one frame at a time (`run()`), which is the key difference from the original
  free-running Lua bridge.
- **Opponent** — frozen self-play: a snapshot of a past policy drives P2.

The env's parser, observation bus, reward path, and trained checkpoints are
**unchanged** across every platform port — only the transport (Lua + files →
in-process RAM reads and button masks) and the opponent (game AI → frozen self)
were replaced.

## Repo layout

| Path | What it is |
|------|-----------|
| `linux_port/` | The whole port: gym env, self-play trainer, parity/bench/diag tools |
| `linux_port/powerstone_env_v6.py` | The v6 environment — RAM parser, obs, rewards |
| `linux_port/selfplay_env.py` / `train_selfplay.py` | Self-play wrapper + PPO training entry |
| `linux_port/watch_play.py` | Renders the model playing at real-time pacing (for capture) |
| `linux_port/opponent_pool/` | 8 frozen `ps_v6` checkpoints (0.2M → 31.9M steps) |
| `linux_port/states/` | Savestates recorded under the libretro core |
| `linux_port/system/dolphin-*/` | VMU + flash images (unlocks, stage config) |
| `powerstone_v6_ppo_leg*.zip` | Top-level checkpoints: `legG_27911k` (parity yardstick), `legM_final` (champ) |
| `HANDOFF.md` | Living session log — status, gates, decisions, next steps |
| `HOWTO_LINUX_SERVER.md` + `setup_linux.sh` | Recipe for a rented Ubuntu/Debian box |
| `README_MIGRATION.md`, `linux_port/MAC_TEST.md`, `linux_port/README_PORT.md` | The porting docs |

**Not in git** (see [`.gitignore`](.gitignore)): the game dump
`Power Stone 2 (USA).chd` (260 MB — copy it in one level above `linux_port/`),
the patched `sdlarch-rl/` harness (its own repo — see below), and runtime churn.

## The harness

The libretro harness carries macOS-specific patches (GL 4.1 core context,
CMake/venv fixes, GLSL 150 shader, POSIX shims) that live in a **separate
private repo**, forked from `paulo101977/sdlarch-rl`. Clone and build it
alongside this folder; the scripts expect the flycast core at
`../cores/flycast_libretro.*` and the game at `../Power Stone 2 (USA).chd`.

## Running

The bring-up is gated — each step verifies the one before it. In short:

```bash
# RAM access (gates everything else)
python3 linux_port/probe_ram.py --core ../cores/flycast_libretro.dylib \
  --game "../Power Stone 2 (USA).chd"

# Parity eval — confirm obs semantics survived the port
python3 linux_port/eval_parity.py   # 50 eps deterministic vs a known band

# Self-play training
python3 linux_port/train_selfplay.py
```

`linux_port/README_PORT.md` walks the full gate sequence (RAM → buttons →
savestates → smoke → parity); `MAC_TEST.md` covers the macOS-specific setup
(RetroArch smoke test, HLE BIOS, building the core).

## Status

The port is **proven** — gate 4 (behavioral parity) passed on Aug 28, 2026,
and a rig tiebreaker confirmed the observation port is faithful (picks/forms
match the source machine almost exactly). The project has pivoted from porting
to scaling training. See `HANDOFF.md` for the current scoreboard and next steps.
