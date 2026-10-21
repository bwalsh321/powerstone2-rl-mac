# Power Stone 2 RL

A reinforcement-learning bot for Power Stone 2 (Dreamcast, 2000) that plays four-player free-for-alls. It reads
the game straight out of emulator RAM: no pixels, no decomp, no published memory map. The RAM interface was
reverse-engineered for this project.

**Why:** I grew up playing four-player Power Stone 2 with my two brothers and a stock CPU player that was useless.
I wanted a fourth player at our level. The project grew from RAM discovery into a training environment, an
unattended experiment relay, and a bot that now wins most of its measured Desert free-for-alls against the
hardest CPUs. The experiments, including the recipes that did not work, are recorded in the notebooks linked below.

## Where it stands (October 20, 2026 — through leg 211)

**74.4% average wins over the latest three legs against three level-8 (hardest) CPUs.** The bot plays Falcon.
Its main grade, **lv8mix**, is 1,000 four-player free-for-alls on five Desert lineups excluded from training,
with 200 games per lineup and matching starting conditions across checkpoints.

| Checkpoint | Sampled-action lv8mix | Wins / games |
|---|---|---|
| [Leg 209](linux_port/receipts/eval_leg209_lv8mix_out.txt) | **75.3%** | 753 / 1,000 |
| [Leg 210](linux_port/receipts/eval_leg210_lv8mix_out.txt) | **74.6%** | 746 / 1,000 |
| [Leg 211](linux_port/receipts/eval_leg211_lv8mix_out.txt) | **73.4%** | 734 / 1,000 |
| Latest three-leg average | **74.4%** | 2,233 / 3,000 |

The main grade samples actions from the policy, as training does. A separate deterministic evaluation always
chooses the highest-probability action: leg 209 reached [78.2% over 500 games](linux_port/receipts/eval_leg209_lv8mix_top_out.txt).
These are different evaluation modes; the sampled grade has driven the relay's keep/hold decisions since leg 165.

### What transfers, and what still fails

A second test set checks new opponent lineups and stages. Its latest published result is **leg 204**, not leg 211:

| Test | Leg 204 result |
|---|---|
| Three unseen Desert lineups | **70.7%** (212 / 300) |
| Blue Sky and Dark Castle, never trained on | **1.0%** (2 / 200) |
| Entire second test set | **42.8%** (214 / 500) |

[Raw results](linux_port/receipts/sealed/eval_leg204_sealed_out.txt) ·
[Test construction and training exclusions](linux_port/states_sealed/README.md).
Leg 200 scored [72.0% on the unseen Desert lineups](linux_port/receipts/sealed/eval_leg200_sealed_out.txt).
The bot generalizes to new lineups on Desert, but broad stage coverage remains unfinished: it trains only on
Desert, and the geometry observation block returns zeros on the other two stages.

Focused pressure is also harder: leg 210 won [22.9% of 280 games](linux_port/receipts/eval_leg210_hunted_out.txt)
against two scripted hunters targeting it plus a level-8 CPU. CPU benchmark wins do not establish how well it
plays against humans; the original goal still needs games with me and my brothers.

### How it got here

| Milestone | Evaluation | Win rate |
|---|---|---|
| Feedforward policy, 10 actions (legs 100–109) | Top-move lv8mix | ~32% |
| LSTM memory + 63 direction×button actions (117–124) | Top-move lv8mix | ~37% |
| RAM observations of items, chests, projectiles, hitboxes and props (134–138) | Top-move lv8mix | 44.6% |
| More recent opponents + balanced lineups (139–141) | Top-move lv8mix | 46.2% |
| Learning rate reduced to 5e-5 (170–172) | Sampled lv8mix | 58.6% |
| Frame stack reduced from 7 to 2 (174–176) | Sampled lv8mix | 60.2% |
| MLP widened from 256 to 512 (179–181) | Sampled lv8mix | 64.0% |
| Learning rate reduced to 2.5e-5 (191–193) | Sampled lv8mix | 69.7% |
| Latest legs (209–211) | Sampled lv8mix | **74.4%** |

These are successive checkpoints in one training lineage, not independent seeds or isolated estimates of each
change's effect. The older top-move scores and newer sampled scores should not be compared as one uniform curve.
The main test is reused for experiment decisions, so it is a development benchmark even though its lineups are
excluded from training. The second set is checked less often and is reported separately. Each latest main-test
receipt reports 1,000 distinct episodes; the three-leg average reuses starting conditions across checkpoints.

The [experiment log](docs/NEXT_CHANGES.md) and [October 14–19 experiment summary](docs/VACATION_PLAN.md#outcome-oct-19-leg-204)
record the comparisons and reversions. Failed or neutral experiments include five earlier reward-shaping legs,
behaviour cloning from my play, two DAgger-style imitation variants (both cost 6–15 points), practice resets from
losing positions, and the latest learning-rate cut to 1.25e-5 (neutral in its initial three-leg read).

## How it works

- **Observation:** 430 numbers per frame parsed from RAM (`linux_port/powerstone_env_v6.py`, `ps2_ram.py`,
  `obs_v4_reader.py`): health, positions, stones, transformations, plus nearby threats, hitboxes, projectiles,
  ground items, chests, held items and Desert geometry. Two frames are stacked (860 inputs). "Vision" in the logs
  means these RAM-derived features, not pixels.
- **Policy:** recurrent PPO (sb3-contrib) with a skip-connected 128-unit LSTM and 512-wide MLP layers
  (`recurrent_policy.py`). The current learning rate is 1.25e-5; entropy coefficient 0.01.
- **Actions:** 63 direction × button combinations, with buttons as taps so double jumps and repeated attacks work
  (`action_space.py`).
- **Reward:** win/loss, damage dealt and taken, capped stone pickups, special-move damage and a time cost,
  with own reward minus the other three seats' mean. Ordinary damage credit uses a nearest-attacker heuristic.
  The hit-source-pointer alternative was reverted with the leg-143 reward bundle and is not enabled.
- **Training:** async actor-learner PPO (`train_selfplay_async.py`), 16 actors on a Ryzen 9950X, 4M steps per leg.
  Episodes mix three lv8 CPUs with one lv8 CPU plus two past bots. In half of the latter rounds, scripted hunters
  replace the past bots. The opponent pool was refreshed at leg 198 by archiving snapshots older than leg 170.
  The adaptive health handicap is implemented but is not enabled in the recipe through leg 211.
- **Transport:** the flycast libretro core in-process through
  [sdlarch-rl](https://github.com/paulo101977/sdlarch-rl) (patched copy in `sdlarch-rl/`), rendered headless on the GPU (EGL).

## The relay

Training runs unattended as back-to-back legs (`linux_port/`):

| Script | Job |
|---|---|
| `league_leg_async.sh` | one 4M-step leg from `league_state.txt`, with the recipe flags in `league_env.txt` and one-shot model surgeries in `league_surgery.txt` |
| `relay_watch_linux.sh` | starts the grading run when a leg finishes |
| `league_battery.sh` | grades the leg (sampled lv8mix on 20 emulators, 1,000 paired starts), runs the hold gate, saves it to the opponent pool, launches the next leg, starts scouting and side evaluations |
| `top_grade.sh`, `hunt_grade.sh` | separate top-move and targeted-hunter evaluations |
| `sealed_grade.sh` | manually run second test set; never part of the automatic relay |
| `relay_boot.sh`, `relay_alert.sh` | restart after a reboot; 15-minute watchdog writing `claude_bridge/ALERT.txt` |

The sampled-grade hold gate catches a drop of more than six percentage points below the mean of the previous
five sampled grades. It also checks for missing/unparseable results and too few distinct episodes.
Edit relay scripts only between runs or with an atomic `mv` (bash reads scripts as it runs them).

## What you need

Nothing copyrighted ships here. You supply:

1. **Your own dump of Power Stone 2 (USA)** as `Power Stone 2 (USA).chd` at the repo root (gitignored).
2. **The flycast libretro core** (RetroArch's core downloader or the libretro buildbot).
3. **The harness** is tracked in this repo under `sdlarch-rl/` (patched [sdlarch-rl](https://github.com/paulo101977/sdlarch-rl)); build it with CMake.
4. **Python 3.11+** with [`requirements.txt`](requirements.txt).
5. **Savestates**, stamped from your own save with `make_savestates.py` or headlessly with `menu_drive.py`
   (game-derived, so not distributed): training lineups in `linux_port/states_mixed/` (slots 30–43, 50–68) and
   the main evaluation set in `linux_port/states/` (slots 90–94). The second test set uses slots 95–99.
6. **A compatible trained checkpoint** for watching or grading a bot. Commands below assume the leg-211 zip
   is available locally; game files, savestates, and that checkpoint are not created by these commands.

Linux setup: `linux_port/setup_9950x.sh` and [`linux_port/LINUX_BRINGUP.md`](linux_port/LINUX_BRINGUP.md).

## Quick commands

From `linux_port/` with the venv active, your core/game/states installed, and the checkpoint available locally:

```bash
# Observation/action contract for the leg-211 checkpoint.
export PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:.
export PS2_OBS_V2=1 PS2_OBS_V3=1 PS2_OBS_V4=1 PS2_OBS_STACK=2
export PS2_OBS_CTX_FIX=1 PS2_OBS_V4_ITEMEMB=keep PS2_OBJ_GRID_N=208 PS2_BUTTON_TAP=1

# watch a bot play (real time)
python -u watch_play.py \
  --core ~/cores/flycast_libretro.so --game "../Power Stone 2 (USA).chd" \
  --model ./powerstone_v6_leg211_league.zip --slot 90 --stochastic

# quick 50-game sampled check; this is not the full published 1,000-game grade
python eval_parity.py --core ~/cores/flycast_libretro.so --game "../Power Stone 2 (USA).chd" \
  --slots 90,91,92,93,94 --episodes 50 --model ./powerstone_v6_leg211_league.zip --stochastic
```

For other checkpoints, use their observation/action settings from `leg_modes.txt`; the battery reads that row
automatically. The full grade runs 20 shards of 50 games with coordinated starting conditions. The battery also
advances the training relay, so use `eval_parity.py` for standalone checks.

## Docs

| File | What it is |
|---|---|
| [`docs/NEXT_CHANGES.md`](docs/NEXT_CHANGES.md) | Experiment decisions, results, and queued changes; some earlier status notes remain |
| [`docs/VACATION_PLAN.md`](docs/VACATION_PLAN.md) | October 14–19 experiment plan and outcomes through leg 204 |
| [`docs/AUDIT_OCT17.md`](docs/AUDIT_OCT17.md) | October 17 audit; subsequent outcomes are in the experiment log |
| [`docs/SESSION_HANDOFF_RYZEN.md`](docs/SESSION_HANDOFF_RYZEN.md) | Historical Ryzen handoff snapshot through leg 165 |
| [`linux_port/leg_modes.txt`](linux_port/leg_modes.txt) | Per-leg training settings |
| [`HANDOFF.md`](HANDOFF.md) | The full lab notebook (Mac/Windows eras through ~leg 106: audits, project laws, every leg) |
| [`linux_port/receipts/`](linux_port/receipts/) | Published evaluation receipts and experiment checks |
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
