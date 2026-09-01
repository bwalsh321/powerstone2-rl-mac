#!/bin/bash
# Leg 4 — synthesis leg. Watchdog wrapper v2: boot-phase EOFError crashes
# HANG in teardown (mutex), so we kill the tree ourselves instead of
# waiting on wait().
cd ~/Documents/macbook_migration/linux_port
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. PYTHONUNBUFFERED=1
export PS2_CORE="$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib"
export PS2_WARM=./powerstone_v6_bc256_spleg.zip PS2_FRESH=1 PS2_POOL=./pool_league
export PS2_OUT=./powerstone_v6_leg4_league PS2_NENVS=6 PS2_STAGGER=20
LOG=train_leg4_out.txt
for attempt in 1 2 3 4; do
  echo "[wrapper] attempt $attempt $(date)" >> wrapper_leg4.log
  python -u train_selfplay.py > "$LOG" 2>&1 &
  PID=$!
  while kill -0 $PID 2>/dev/null; do
    sleep 30
    if grep -q "EOFError" "$LOG" 2>/dev/null; then
      eps=$(grep -c "\[ep\]" "$LOG")
      echo "[wrapper] EOFError after $eps eps — killing tree" >> wrapper_leg4.log
      kill -9 $PID 2>/dev/null; pkill -9 -f spawn_main 2>/dev/null
      [ "$eps" -gt 100 ] && { echo "[wrapper] mid-leg crash, NOT retrying" >> wrapper_leg4.log; exit 1; }
      sleep 20; continue 2
    fi
  done
  grep -q "leg complete" "$LOG" && { echo "[wrapper] leg complete" >> wrapper_leg4.log; exit 0; }
  echo "[wrapper] python exited without completion" >> wrapper_leg4.log
  sleep 20
done
echo "[wrapper] out of attempts" >> wrapper_leg4.log
