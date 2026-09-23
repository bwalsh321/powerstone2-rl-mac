#!/bin/bash
# Quiet-machine throughput measurement of train_selfplay_async.py, then launch
# the next league leg. Written Sep 11 2026 for the leg 21 -> 22 window
# (Blake: hold leg 22, measure, then go). Zero footprint: <100k steps per
# probe, so no pool snapshots or checkpoints are written; probe zips deleted.
# Outputs: claude_bridge/async_measure_result.txt, claude_bridge/async_measure_done.txt
# Fail-safe: whatever happens to the probes, the next leg is launched at the end.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. PYTHONUNBUFFERED=1
export PS2_CORE="$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib"
mkdir -p claude_bridge receipts
R=claude_bridge/async_measure_result.txt
read N PREV < league_state.txt          # warm start = the leg just finished
echo "async_measure start $(date) warm=$PREV" > "$R"

# only real Python processes count (a shell whose argv mentions these names must not)
busy() { ps -axo comm=,args= | awk '$1 ~ /[Pp]ython/' | grep -qE "train_selfplay|eval_parity|ab_selfplay_probe"; }
if busy; then
  echo "machine NOT quiet (trainer/eval alive) — skipping measurement" >> "$R"
else
  run_probe() {   # run_probe <label> <NACTORS> <NENVS> <steps>
    local label=$1 na=$2 ne=$3 steps=$4
    local log=receipts/async_probe_${label}.log   # (was one `local` line: label unset when log expanded)
    echo "=== $label actors=$na envs=$ne steps=$steps $(date)" >> "$R"
    PS2_NACTORS=$na PS2_NENVS=$ne PS2_TOTAL_STEPS=$steps PS2_POOL=./pool_league \
      PS2_WARM=$PREV PS2_FRESH=1 PS2_OUT=./powerstone_v6_asyncprobe_$label PS2_STAGGER=20 \
      PS2_INSTANCE_BASE=0 \
      python -u train_selfplay_async.py 2>&1 | while IFS= read -r line; do printf '%s %s\n' "$(date +%s)" "$line"; done > "$log" &
    local pid=$!
    local t0=$(date +%s)
    while kill -0 $pid 2>/dev/null; do
      sleep 15
      if [ $(( $(date +%s) - t0 )) -gt 1500 ]; then echo "$label: TIMEOUT after 25 min, killing" >> "$R"; break; fi
    done
    pkill -9 -f train_selfplay_async.py 2>/dev/null; pkill -9 -f spawn_main 2>/dev/null; sleep 5
    # headline: steps/s between the first and last [learner] update lines
    python3 - "$log" "$label" >> "$R" << 'PY'
import re, sys
lines = open(sys.argv[1]).read().splitlines()
ups = [(int(l.split()[0]), int(re.search(r'steps=(\d+)', l).group(1))) for l in lines if '[learner] update' in l]
cfg = [int(l.split()[0]) for l in lines if '[config]' in l]
eps = sum(1 for l in lines if '[ep]' in l); wins = sum(1 for l in lines if '[ep]' in l and ' win ' in l)
done = any('leg complete' in l for l in lines); errs = sum(1 for l in lines if 'Traceback' in l or 'ACTOR DIED' in l)
if len(ups) >= 2:
    (t0, s0), (t1, s1) = ups[0], ups[-1]
    print(f"{sys.argv[2]}: {(s1-s0)/(t1-t0):.1f} steps/s over updates 2..{len(ups)} ({s1-s0} steps in {t1-t0}s); "
          f"first chunk at +{ups[0][0]-cfg[0]}s; eps {eps} (learner wins {wins}); complete={done} errors={errs}")
    lag = [re.search(r'max\)=(\d+)/([\d.]+)/(\d+)', l) for l in lines if '[learner] update' in l]
    print(f"{sys.argv[2]}: version lag max over run = {max(int(m.group(3)) for m in lag if m)}")
else:
    print(f"{sys.argv[2]}: INCOMPLETE — {len(ups)} learner updates, eps {eps}, errors={errs}")
PY
    rm -f ./powerstone_v6_asyncprobe_${label}.zip
  }
  # 10 actors / 10 columns (apples-to-apples with the 10-worker lockstep 120.5),
  # then 12 actors / 10 columns (slack absorbs the slowest actor).
  run_probe a10e10 10 10 80000
  run_probe a12e10 12 10 80000
  echo "lockstep reference (Sep 11 probes): 8w 106.9, 10w 120.5, 12w 117.7, 14w 123.1 steps/s" >> "$R"
fi

# ---- launch the next leg regardless ----
ls ./powerstone_v6_asyncprobe_* 2>/dev/null && rm -f ./powerstone_v6_asyncprobe_*.zip
if ps -axo comm=,args= | awk '$1 ~ /[Pp]ython/' | grep -q train_selfplay; then
  echo "a trainer is alive; NOT launching leg $N" >> "$R"
elif tmux has-session -t ps2train 2>/dev/null; then
  echo "tmux ps2train already exists; NOT launching leg $N" >> "$R"
else
  tmux new -s ps2train -d "caffeinate -is bash $(pwd)/league_leg.sh" \
    && echo "leg $N launched $(date) in tmux ps2train (league_leg.sh defaults: 10 workers, 4M)" >> "$R" \
    || echo "leg $N tmux launch FAILED $(date)" >> "$R"
fi
echo "async_measure end $(date)" >> "$R"
echo DONE > claude_bridge/async_measure_done.txt
