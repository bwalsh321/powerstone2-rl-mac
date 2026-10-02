#!/bin/bash
# Self-compounding league leg. Reads league_state.txt: "<N> <warm-start zip>".
# Watchdog wrapper: retries boot-phase EOFError crashes (teardown-hang aware),
# never blind-retries a mid-leg crash.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
read N PREV < league_state.txt
# Oct 1 2026 (GPT review P1): launch permission is HOST-LOCAL. Only a machine whose untracked
# linux_port/host_role.txt reads "train" may start a leg; league_trainer.txt is tracked in git, so a pull
# must never grant another machine permission to train.
ROLE="$(tr -d '[:space:]' < host_role.txt 2>/dev/null)"
if [ "$ROLE" != "train" ]; then
  echo "[wrapper] REFUSED: host_role.txt='${ROLE}' (not the training host); nothing launched $(date)" | tee -a wrapper_league.log >&2
  exit 2
fi
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. PYTHONUNBUFFERED=1
if [ -z "$PS2_CORE" ]; then
  if [ "$(uname)" = "Darwin" ]; then
    export PS2_CORE="$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib"
  else
    export PS2_CORE="$HOME/cores/flycast_libretro.so"
  fi
fi
export PS2_WARM=$PREV PS2_FRESH=1 PS2_POOL=./pool_league
# Sep 11 2026 (M4 Pro, Blake's call after the throughput probes): 10 workers
# (aggregate plateaus at ~120 steps/s from 10 up; the sync vec env is the
# cap, not the CPUs) and 4M-step legs. Override per launch by exporting.
export PS2_OUT=./powerstone_v6_leg${N}_league PS2_NENVS=${PS2_NENVS:-10} PS2_STAGGER=${PS2_STAGGER:-20}
export PS2_TOTAL_STEPS=${PS2_TOTAL_STEPS:-4000000}
LOG=train_leg${N}_out.txt
for attempt in 1 2 3 4; do
  echo "[wrapper] leg $N attempt $attempt $(date)" >> wrapper_league.log
  python -u train_selfplay.py > "$LOG" 2>&1 &
  PID=$!
  while kill -0 $PID 2>/dev/null; do
    sleep 30
    if grep -q "EOFError" "$LOG" 2>/dev/null; then
      eps=$(grep -c "\[ep\]" "$LOG")
      kill -9 $PID 2>/dev/null; pkill -9 -f spawn_main 2>/dev/null
      echo "[wrapper] leg $N EOFError after $eps eps" >> wrapper_league.log
      [ "$eps" -gt 100 ] && { echo "[wrapper] mid-leg crash, halting" >> wrapper_league.log; exit 1; }
      sleep 20; continue 2
    fi
  done
  grep -q "leg complete" "$LOG" && { echo "[wrapper] leg $N complete" >> wrapper_league.log; exit 0; }
  sleep 20
done
echo "[wrapper] leg $N out of attempts" >> wrapper_league.log
exit 1
