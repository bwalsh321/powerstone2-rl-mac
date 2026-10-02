#!/bin/bash
# G5 parity on the 9950X (Oct 1 2026): leg 103 zip, obs v3 contract, sharded like league_battery.sh.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source ./linux_gpu_env.sh
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:. PYTHONUNBUFFERED=1 PS2_OBS_V2=1 PS2_OBS_V3=1
export PS2_CORE=$HOME/cores/flycast_libretro.so
GAME="../Power Stone 2 (USA).chd"; M=./powerstone_v6_leg103_league.zip; R=receipts/parity_9950x
date +%s > $R/start.txt
for i in $(seq 0 9); do
  ( sleep $((i*2)); python eval_parity.py --core "$PS2_CORE" --game "$GAME" --slot 3 --model $M --episodes 20 --instance $i > $R/slot3_s$i.txt 2>&1 ) &
  ( sleep $((i*2+1)); python eval_parity.py --core "$PS2_CORE" --game "$GAME" --slot 2 --model $M --episodes 25 --instance $((i+10)) > $R/slot2_s$i.txt 2>&1 ) &
done
wait
date +%s > $R/end.txt
