# Linux box bring-up (written Sep 4, 2026; refreshed Sep 10)

Written for the 7950X box; applies to any Linux machine (the 12700K fallback
included). The relay keeps running on the M2 until G4 passes here, so read
`league_state.txt` on the Mac at migration time for the current leg number
and warm-start zip; the leg numbers below are examples from Sep 10 (leg 15
final, leg 16 in progress). Full project context: HANDOFF.md
at the repo root (read PROJECT LAWS + the LEAGUE LEGS table first).

## 1. On the Linux box (fresh install)

```bash
sudo apt-get install -y git
git clone https://github.com/bwalsh321/powerstone2-rl-mac.git
cd powerstone2-rl-mac
git clone https://github.com/bwalsh321/sdlarch-rl.git     # must sit at repo root, beside linux_port/
bash linux_port/setup_linux.sh                             # deps, venv ~/ps2rl, flycast core, gates G1-G2
```

G2 will report the CHD/pool/states/models as missing until step 2 runs.

## 2. From the Mac — push the big files over the LAN (~530MB)

```bash
cd ~/Documents/macbook_migration
BOX=USER@BOX_IP   # <-- fill in
rsync -avP "Power Stone 2 (USA).chd" $BOX:powerstone2-rl-mac/
rsync -avP linux_port/pool_league linux_port/states \
  linux_port/demos linux_port/demos_lv8 linux_port/demos_v4corpus linux_port/demos_cheater \
  linux_port/powerstone_v6_*.zip linux_port/league_state.txt \
  $BOX:powerstone2-rl-mac/linux_port/
```

Re-run `setup_linux.sh` after — G2 should PASS.

## 3. Parity gates (run these before trusting any training)

Cross-platform parity is this project's known hard problem (see the
chest-obs port bug in HANDOFF). Do not skip G4.

```bash
cd ~/powerstone2-rl-mac/linux_port
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy SDL_VIDEODRIVER=dummy PYTHONPATH=../sdlarch-rl:. PYTHONUNBUFFERED=1
CORE=~/cores/flycast_libretro.so
GAME="../Power Stone 2 (USA).chd"

# G3 — boots, loads state + model, runs (minutes)
python eval_parity.py --core "$CORE" --game "$GAME" --slot 2 --episodes 3 --model ./powerstone_v6_leg15_league.zip

# G4 — full parity vs the SAME checkpoint's Mac battery (~40 min). MANDATORY.
#   --ref is the matched reference: leg 15's Mac receipt was 46/50 wins,
#   10.54 picks/ep, 3.22 forms/ep (linux_port/receipts/eval_leg15_slot2_out.txt).
#   If you migrate a later leg, use THAT leg's receipt instead.
python eval_parity.py --core "$CORE" --game "$GAME" --slot 2 --episodes 50 \
  --model ./powerstone_v6_leg15_league.zip --ref 46/50,10.54,3.22
#   Pass rule: win% not significantly different at n=50 (two-proportion test,
#   p>=0.05), picks/forms within 15%. Exit code 1 on PARITY FAIL. A marginal
#   fail: rerun once (random reset delay). A big miss = obs divergence: check
#   RAM offsets/endianness before anything else, per the chest-obs law.
#   Also record here, in a comment or HANDOFF note: the flycast core sha256,
#   the sdlarch-rl commit, and `pip freeze` at the time G4 passed.

# G5 — throughput probe, 6 workers, ~20k steps (M2 reference: ~80 steps/s total)
PS2_TOTAL_STEPS=20000 PS2_POOL=./pool_league PS2_WARM=./powerstone_v6_leg15_league.zip \
  PS2_FRESH=1 PS2_OUT=./powerstone_v6_linuxprobe PS2_NENVS=6 PS2_STAGGER=5 \
  python -u train_selfplay.py 2>&1 | tee g5_probe.log
#   Compute steps/s from log timestamps. If CPU headroom is huge (expected on
#   a 7950X: 16c/32t), try PS2_NENVS=12 and re-measure before settling the
#   worker count for leg 13. Delete powerstone_v6_linuxprobe* after.
```

### After G4 passes: freeze the artifacts
The buildbot core is a mutable "latest" — the moment G4 passes, record
what actually passed: `shasum -a 256 ~/cores/flycast_libretro.so` and the
sdlarch-rl git SHA (`git -C ../sdlarch-rl rev-parse HEAD`), into a
`linux_parity_manifest.txt` beside this file. Any future core/harness
change reruns G4 before training.

## 4. Resume the league

```bash
tmux new -s ps2train -d "bash $(pwd)/league_leg.sh"     # no caffeinate on Linux
```

`league_leg.sh` / `league_battery.sh` are platform-aware now (core path,
keep-awake). The Metal boot race is macOS-only — if boots are clean, drop
PS2_STAGGER (export in league_leg.sh env or leave default 20 for safety).
The teardown hang (trainer alive after "leg complete", see leg 12 note in
HANDOFF) may or may not follow us to Linux — verify the trainer EXITS after
the first leg completes before chaining batteries.

## 5. Claude on this box

Install the Claude desktop app, link a session, connect the
powerstone2-rl-mac folder. The session's shell is an isolated VM, so start
the command bridge exactly as on the Mac:

```bash
cd ~/powerstone2-rl-mac/linux_port && tmux new -s claudebridge -d "bash claude_bridge_watcher.sh"
```

Then point the new session at HANDOFF.md — PROJECT LAWS, the LEAGUE LEGS
table, the pre-registered intervention plan (BINDING; trigger is ARMED as of
leg 12: slot2 went 90 -> 88, one more flat/down leg fires it), and the
standing constraint: NEVER overwrite or promote powerstone_v6_ppo.zip.
