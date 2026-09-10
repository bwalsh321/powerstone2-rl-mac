# Power Stone 2 RL

A reinforcement-learning agent for Power Stone 2 (Dreamcast, 2000) that
reads the game straight out of emulator RAM. No pixels, no decomp, no
published memory map: the state interface was reverse-engineered for this
project. The current agent trains only by playing frozen copies of itself
in 1v1, and is measured on a held-out four-player free-for-all against the
game's built-in COMs.

**Why:** I grew up playing four-player Power Stone 2 free-for-alls with my
two brothers and a stock CPU player that was useless. I wanted a fourth
player at our level. There was no decomp and no memory map, so the RAM
interface, the training environment, and the evaluation harness were all
built from scratch; the trained agent is the by-product. The longer story,
including a year stuck on RAM discovery and every recipe that did not
work, is in the write-up: <!-- Blake: paste the Reddit post URL here -->
[Reddit post](https://www.reddit.com/r/reinforcementlearning/).

## How it works

The agent never sees the screen. Instead:

- **Observation**: a zero-copy numpy view of the emulator's 16 MiB
  SYSTEM_RAM, parsed into a 122-dim vector (own and opponent health,
  positions, velocity, facing, transformation state, stones held, an
  object ledger of stones / chests / projectiles, stage, last action) by
  `linux_port/powerstone_env_v6.py` + `linux_port/ps2_ram.py`. The RAM map
  carries confidence labels (confirmed / heuristic / retired) because a lot
  of plausible-looking addresses turned out to be wrong.
- **Action**: 10 discrete actions (four directions, jump, grab, attack,
  throw, two transformed specials) written as a RetroPad button mask into
  the core each frame. Every action holds for a fixed number of frames.
- **Reward** (`MINIMAL_REWARD=True`): win / loss, damage dealt and taken,
  gem pickups (capped per episode), and a small time cost. The historical
  shaping terms in the code are zeroed; five reward-tuning legs never
  helped.
- **Learner**: PPO (stable-baselines3), 256x256 MLP, 6 `SubprocVecEnv`
  workers, no recurrence.
- **Opponent**: self-play. A frozen past checkpoint drives the other seat,
  sampled per episode 50% from the ten newest files in the pool and 50%
  uniformly from the whole pool. The pool is read once at worker start, so
  each 2M-step leg trains against a fixed opponent set; the leg's own
  snapshots join the pool for the next leg. (Earlier docs described this as
  refreshing within a leg; it does not, and the September audit that found
  that is in `HANDOFF.md`.)
- **Transport**: the [sdlarch-rl](https://github.com/paulo101977/sdlarch-rl)
  libretro harness (our macOS fork:
  [bwalsh321/sdlarch-rl](https://github.com/bwalsh321/sdlarch-rl)) running
  the flycast core in-process, stepped one frame at a time. Six instances
  run at roughly 150 fps each on an M2.

## Results

Lineage: a behavior-cloning seed from my own play (`bc256`), then thirteen
2M-step self-play legs (leg 3B, then legs 4 through 15), 26M PPO steps in
total. The reference "champion" is an older 31.9M-step self-play checkpoint
from the Windows era (`powerstone_v6_ppo.zip`, "leg 1").

**Held-out benchmark (slot 2): Original mode true FFA vs three COM
difficulty-3 opponents, 50 deterministic episodes per leg.** The learner
never trains on this state. Win rate by leg:

| 3B | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | champion |
|----|---|---|---|---|---|---|----|----|----|----|----|----|----------|
| 40 | 42 | 50 | 64 | 78 | 82 | 84 | 86 | 90 | 88 | 90 | 92 | 92 | 98 |

Stone pickups and transformations per episode climbed alongside it (6.3 to
10.5 picks, 1.3 to 3.2 forms per episode), passing the champion on both
before win rate caught up. The one thing changing between legs is more
self-play.

**Hard benchmark (slot 3): the same FFA at COM difficulty 8.** Nine legs
went 0 for 450. Since leg 10 the per-leg wins read 1, 0, 2, 3, 2, 2 out of
50. That is a persistent edge, not a stable win rate; the champion scored
3/20 on the same state. For scale, I win that matchup 23-1.

**Head to head vs the champion** (1v1 on the training savestate, learner in
the P2 seat, stochastic actions): the honest large-sample number is 29-21 in
50 games at leg 6 (95% interval roughly 44 to 71%, so not proof of a
dethroning). The quick 12-game probes run after each leg read 9-3, 11-1,
11-1, 8-4, 11-1 for legs 11 through 15. All of these are one-seat probes;
a seat-swapped comparison is on the post-campaign list.

Things that did not work, all with receipts in `HANDOFF.md`: training
against difficulty-8 COMs from a warm start, from a fresh BC seed, or mixed
with self-play workers (three separate legs, zero learning to win);
behavior cloning from a 23-1 human corpus at 80.6% validation accuracy,
which produced 8 training wins in 4,653 episodes when PPO took over (a
covariate-shift problem, and also a recorder bug: the velocity features in
every demo corpus are zero in over 98% of rows, see the note at the top of
`bc_pretrain.py`); and five reward-shaping legs.

Statistical footnotes an ML reader will want: each leg is one training run,
so the curve is one lineage, not a mean over seeds. n=50 evaluations carry
roughly plus or minus 10 points at these win rates. "Zero difficulty-8
training" means zero direct COM-8 rollouts in this lineage; the opponent
pool contains earlier program checkpoints that were themselves trained
against COM-8, so indirect exposure exists.

A video of the champion on the held-out FFA is linked from the Reddit post
(the file is too large for git).

## Independent reviews

In September 2026 the repo and notebook were audited by two separate AI
reviewers (an 11-page technical audit and a code-level deep review). Every
finding was verified against the code before being accepted. The confirmed
ones, what was fixed, and what is deliberately deferred until the current
pre-registered campaign ends, are recorded in `HANDOFF.md` under
"EXTERNAL AUDIT". Short version: the transfer curve held up; the docs
overstated a couple of mechanisms; the relay and the Linux bootstrap needed
fail-safes, which they now have.

## On AI assistance

I directed this project and understand every result in it, but I did not
type most of the code. Claude wrote the bulk of the Python and shell under
my direction, hunted RAM values with me, and ran the unattended relay
between legs. Commits are co-authored accordingly. The experiment design,
the gameplay knowledge that caught wrong telemetry, the demo recordings,
and every decision about what to run next are mine. Generated code got
the same scrutiny as any other research code and, as the audits above
show, still had bugs; they are documented rather than hidden.

## What you need

Nothing copyrighted ships in this repo. To run it you supply:

1. **Your own dump of Power Stone 2 (USA)** as a `.chd`, from a disc you
   own. It lives at the repo root as `Power Stone 2 (USA).chd` (gitignored).
2. **The flycast libretro core**, easiest via RetroArch's core downloader
   or the [libretro buildbot](https://buildbot.libretro.com/nightly/); on
   macOS it lands at
   `~/Library/Application Support/RetroArch/cores/flycast_libretro.dylib`.
3. **The patched harness**: clone
   [bwalsh321/sdlarch-rl](https://github.com/bwalsh321/sdlarch-rl) next to
   this repo's folder or inside it as `sdlarch-rl/` (gitignored here; it is
   its own repo). The macOS patches (GL 4.1 core context, CMake/venv fixes,
   GLSL 150 shader, POSIX shims) are committed there on top of upstream.
4. **Python 3.11** and the pinned deps in [`requirements.txt`](requirements.txt).
   Note the environment imports legacy `gym` 0.26 (via `shimmy`), which is
   pinned there; `setup_linux.sh` installs from this file.

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

On Linux, `setup_linux.sh` does this plus the core download and the
import gates; `linux_port/LINUX_BRINGUP.md` is the full clean-machine
procedure including the mandatory parity check against a Mac receipt.

### 2. Build the harness

```bash
cd sdlarch-rl
cmake -B build -S . -DCMAKE_BUILD_TYPE=Release
cmake --build build   # produces _retro.so in the repo root
```

macOS note (do this once on any new Mac; cures a modal that can hang
headless boots after a prior crash):

```bash
defaults write org.python.python ApplePersistenceIgnoreState YES
```

### 3. First boot and Dreamcast system files

`linux_port/system/dolphin-0/` is where flycast keeps its nvmem and VMU
saves. It is **not** in the repo; the core creates fresh files on first
boot. The savestates in this project were stamped on a save that had
progressed through the game (extra characters such as Pride, the desert
stage in Original mode). If a fresh save does not offer the stage or
characters listed in the table below, play through Original mode once to
unlock them before stamping. Multi-worker training seeds
`system/dolphin-1..N` by copying `dolphin-0` (see `setup_linux.sh`).

<!-- Blake: you know exactly what the save had unlocked and whether stock
     is enough. Tighten the paragraph above if you can be more specific. -->

Sanity gates, in order (each verifies the one before):

```bash
python probe_ram.py --core "$CORE" --game "$GAME" --state states/slot1.state          # RAM access
python calibrate_buttons.py --core "$CORE" --game "$GAME" --state states/slot1.state  # button map
PS2_CORE="$CORE" python powerstone_env_libretro.py                                    # env smoke
```

### 4. Stamp savestates

Savestates are game-derived, so they are not distributed either. Stamp
your own with the interactive maker (visible window; keyboard + gamepad;
`F1` to `F7` stamp `states/slotN.state`, `TAB` toggles a controller port in):

```bash
python make_savestates.py --core "$CORE" --game "$GAME" --states ./states
```

The three slots the scripts expect (one slot number = one meaning):

| Slot | Purpose | Recipe |
|------|---------|--------|
| `slot1` | self-play training | VS mode 1v1, desert, **both ports human (TAB both in), both Falcon**, stamped at round start |
| `slot2` | held-out benchmark | Original mode true FFA, desert, COM difficulty 3, P2 = the bot's seat (Falcon) |
| `slot3` | hard benchmark | Original mode true FFA, desert, COM difficulty 8 |

Verify a stamp headlessly with `python diag_state.py` (healths 4x1000 after
the intro, correct character fingerprint). Menu navigation is also fully
scriptable; see `menu_drive.py`.

### 5. Watch a checkpoint play

Real-time pacing, with sound:

```bash
SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. python -u watch_play.py \
  --core "$CORE" --game "$GAME" \
  --model ./powerstone_v6_leg15_league.zip --slot 2
```

`SPACE` pauses, `F` fast-forwards, `--record out.mp4` captures, `--slot 3`
shows it against the difficulty-8 wall, `--model ./powerstone_v6_ppo.zip`
is the old champion.

### 6. Evaluate

```bash
python eval_parity.py --core "$CORE" --game "$GAME" --slot 2 --episodes 50 \
  --model ./powerstone_v6_leg15_league.zip
```

Prints wins, picks and forms per episode with a Wilson interval. With
`--ref wins/n,picks,forms` it becomes the migration parity gate and exits
nonzero on a significant miss. `ab_selfplay_probe.py --model A --opp B`
runs the 1v1 head-to-head probe.

### 7. Train

One leg by hand:

```bash
SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. PS2_CORE="$CORE" \
  PS2_WARM=./powerstone_v6_leg15_league.zip PS2_FRESH=1 PS2_POOL=./pool_league \
  PS2_OUT=./powerstone_v6_leg16_league PS2_NENVS=6 python -u train_selfplay.py
```

The unattended relay is two scripts: `league_leg.sh` (reads
`league_state.txt`, runs one 2M-step leg under a crash watchdog) and
`league_battery.sh` (runs the four evaluations, validates each receipt
with `check_receipt.py`, and only then adds the final to `pool_league/`,
advances the state file and launches the next leg). The trainer prints its
resolved configuration (`[config] ...`) at startup; trust that line over
any comment.

Two honest caveats about the relay: it promotes each leg's final
checkpoint without sweeping the mid-leg snapshots, which contradicts
project law 6 ("promote the best, never the last"); and the head-to-head
probe is one-seat. Both are documented in `HANDOFF.md` and deliberately
left alone until the current pre-registered campaign ends, so as not to
change the recipe being measured.

## Repo layout

| Path | What it is |
|------|-----------|
| `linux_port/powerstone_env_v6.py` | The v6 environment: RAM parser, observation, reward |
| `linux_port/ps2_ram.py`, `ps2_addr.py` | RAM map + object-ledger scan (stones / chests / projectiles) |
| `linux_port/powerstone_env_libretro.py`, `flycast_bridge.py` | libretro transport: in-process core, RAM view, button masks |
| `linux_port/selfplay_env.py`, `train_selfplay.py` | Self-play wrapper (opponent pool, P1 view) + PPO trainer |
| `linux_port/league_leg.sh`, `league_battery.sh`, `check_receipt.py` | The unattended relay |
| `linux_port/eval_parity.py`, `ab_selfplay_probe.py` | Held-out COM evaluation / parity gate; 1v1 head-to-head probe |
| `linux_port/train_com.py`, `train_mixed.py` | The vs-COM and mixed-diet trainers from the leg-3 program (kept for the record) |
| `linux_port/bc_pretrain*.py`, `bc_rehearsal.py`, `demos*/` | Behavior-cloning kit + demo corpora (see the corpus caveat in the docstrings) |
| `linux_port/watch_play.py`, `make_savestates.py`, `menu_drive.py`, `diag_state.py`, `probe_ram.py`, `calibrate_buttons.py` | Tooling: viewer / recorder, savestate stamping, headless menu driving, diagnostics |
| `linux_port/powerstone_v6_*.zip` | Named checkpoints: `ppo` = leg-1 champion (31.9M), `legN_league` = each league leg's final, `bc*` = BC seeds, `bc256_*leg` / `bclv8_*` = leg-3 program finals |
| `linux_port/opponent_pool/` | Frozen Windows-era checkpoints (0.2M to 31.9M steps) that seed the league pool |
| `linux_port/receipts/` | Raw output of every evaluation and training run, by leg. Nothing in the tables above lacks a file here |
| `linux_port/archive/` | One-off launchers and batteries from before the relay, plus two rig-era checkpoints |
| `linux_port/LINUX_BRINGUP.md`, `setup_linux.sh`, `setup_mac.sh` | Machine bring-up |
| `HANDOFF.md` | The lab notebook: results tables, pre-registered plan, PROJECT LAWS, audits, every leg |
| `docs/` | Porting notes from the Windows-to-Mac move, the Reddit post kit, and the session handoff used by the relay |

**Not in git** (see [`.gitignore`](.gitignore)): the game dump (`*.chd`),
`linux_port/states/` and `linux_port/system/` (game-derived; stamp your
own, steps 3 and 4 above), the `sdlarch-rl/` harness (its own repo),
rendered video, `pool_league/` (rebuildable from the named checkpoints plus
`opponent_pool/`), and runtime churn (checkpoint dirs, bridges, logs).

The Windows-era repo, [bwalsh321/powerstone2-rl](https://github.com/bwalsh321/powerstone2-rl),
is the historical lab notebook: RAM discovery, the multi-instance
synchronization bug, the reward experiments, and the first behavior-cloning
work. Nothing there is needed to run this repo.

## Credits and license

- Harness: [sdlarch-rl](https://github.com/paulo101977/sdlarch-rl) by
  Paulo Sérgio Galdino Sacramento (BSD 3-Clause); our fork keeps the
  upstream `LICENSE` and only adds macOS build/runtime patches. Upstream's
  channel: [AI Brain](https://www.youtube.com/@AiBrainAi).
- Emulation: [flycast](https://github.com/flyinghead/flycast) via libretro.
- Power Stone 2 © Capcom. No game data, BIOS, or saves are distributed here.
- This repo's own code: MIT, see [`LICENSE`](LICENSE).
