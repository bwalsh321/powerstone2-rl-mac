#!/bin/bash
# Law-6 sweep: slot2 (lv3 FFA) on each leg-27 pool snapshot, obs v2 / 4-port harness,
# 10 shards x 10 eps = 100 per snapshot, instances 20-29 (beside the running leg 28).
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:. PYTHONUNBUFFERED=1 PS2_OBS_V2=1
CORE="$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib"; GAME="../Power Stone 2 (USA).chd"
R=receipts; mkdir -p $R/shards; OUT=$R/sweep_leg27_slot2.txt; echo "sweep leg27 slot2 start $(date)" > $OUT
for snap in $(ls pool_league/leg27_league_*_steps.zip | sort -t_ -k3 -n); do
  tag=$(basename $snap .zip); pids=(); outs=()
  for i in 0 1 2 3 4 5 6 7 8 9; do
    o=$R/shards/sweep_${tag}_s${i}.txt; outs+=("$o")
    ( sleep $((i*5)); python eval_parity.py --core "$CORE" --game "$GAME" --slot 2 --model $snap --episodes 10 --instance $((20+i)) > $o 2>&1 ) &
    pids+=($!)
  done
  wait "${pids[@]}" 2>/dev/null
  python merge_receipts.py slot --model $snap --slot 2 --per-shard 10 --out $R/sweep_${tag}_out.txt "${outs[@]}" >/dev/null 2>&1
  echo "$tag: $(grep 'win%' $R/sweep_${tag}_out.txt | cut -c1-60) $(grep picks $R/sweep_${tag}_out.txt) $(grep forms $R/sweep_${tag}_out.txt)" >> $OUT
done
echo "sweep end $(date)" >> $OUT; echo DONE > claude_bridge/sweep_leg27_done.txt
