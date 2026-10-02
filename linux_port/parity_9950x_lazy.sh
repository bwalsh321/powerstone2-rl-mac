#!/bin/bash
# G5 parity on the 9950X (Oct 1 2026): leg 103 zip, obs v3 contract, sharded like league_battery.sh.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source ./linux_gpu_env.sh
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:. PYTHONUNBUFFERED=1 PS2_OBS_V2=1 PS2_OBS_V3=1
export PS2_CORE=$HOME/cores/flycast_libretro.so
GAME="../Power Stone 2 (USA).chd"; M=./powerstone_v6_leg103_league.zip; R=receipts/parity_9950x_lazy
date +%s > $R/start.txt
PIDS=()
for i in $(seq 0 9); do
  ( sleep $((i*2)); exec python eval_parity.py --core "$PS2_CORE" --game "$GAME" --slot 3 --model $M --episodes 20 --instance $i > $R/slot3_s$i.txt 2>&1 ) & PIDS+=($!)
  ( sleep $((i*2+1)); exec python eval_parity.py --core "$PS2_CORE" --game "$GAME" --slot 2 --model $M --episodes 25 --instance $((i+10)) > $R/slot2_s$i.txt 2>&1 ) & PIDS+=($!)
done
# Oct 1 2026 (GPT review P2): wait on each shard, then require the full episode count per shard; a bare
# wait reported success even if a shard died.
bad=0
for pid in "${PIDS[@]}"; do wait "$pid"; done   # exit codes are not evidence: the harness aborts at teardown after saving
for i in $(seq 0 9); do
  [ "$(grep -c '^\[ep\]' $R/slot3_s$i.txt)" -eq 20 ] || bad=$((bad+1))
  [ "$(grep -c '^\[ep\]' $R/slot2_s$i.txt)" -eq 25 ] || bad=$((bad+1))
done
date +%s > $R/end.txt
[ "$bad" -eq 0 ] || { echo "PARITY RUN INCOMPLETE: $bad shard problems" | tee $R/FAILED.txt >&2; exit 1; }
