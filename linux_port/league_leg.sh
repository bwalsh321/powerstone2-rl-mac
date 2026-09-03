#!/bin/bash
# Self-compounding league leg. Reads league_state.txt: "<N> <warm-start zip>".
# Watchdog wrapper: retries boot-phase EOFError crashes (teardown-hang aware),
# never blind-retries a mid-leg crash.
cd ~/Documents/macbook_migration/linux_port
read N PREV < league_state.txt
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. PYTHONUNBUFFERED=1
export PS2_CORE="$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib"
export PS2_WARM=$PREV PS2_FRESH=1 PS2_POOL=./pool_league
export PS2_OUT=./powerstone_v6_leg${N}_league PS2_NENVS=6 PS2_STAGGER=20
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
