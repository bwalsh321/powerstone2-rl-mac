#!/bin/bash
# top_grade.sh <N> -- TOP-MOVE (deterministic) grade of leg N, 500 rounds beside the next leg (Oct 12 2026). Since leg 165
# the per-leg grade and the hold gate use SAMPLED moves (the way the bot trains); this keeps the old top-move number as a
# secondary. Writes receipts/eval_leg<N>_lv8mix_top_out.txt + claude_bridge/top_leg<N>_done.txt; never gates the relay.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source ~/ps2rl/bin/activate
source ./linux_gpu_env.sh
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:. PYTHONUNBUFFERED=1 PS2_OBS_V2=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
N=$1; M=./powerstone_v6_leg${N}_league.zip
ROW="$(awk -v n="$N" '$1==n' leg_modes.txt 2>/dev/null)"
# the leg's eval contract, as in scout_leg.sh (tmux does not pass the battery's environment)
echo "$ROW" | grep -q "PS2_OBS_V3=1" && export PS2_OBS_V3=1
echo "$ROW" | grep -q "PS2_BUTTON_TAP=1" && export PS2_BUTTON_TAP=1
G="$(echo "$ROW" | grep -o "PS2_OBJ_GRID_N=[0-9]*" | head -1)"; [ -n "$G" ] && export "$G"
if echo "$ROW" | grep -q "PS2_OBS_V4=1"; then export PS2_OBS_V4=1
  E="$(echo "$ROW" | grep -o "PS2_OBS_V4_ITEMEMB=[a-z]*" | head -1)"; [ -n "$E" ] && export "$E"; fi
CORE="${PS2_CORE:-$HOME/cores/flycast_libretro.so}"; GAME="../Power Stone 2 (USA).chd"
export PS2_EVAL_INSTANCE_BASE=50 PS2_EVAL_TOTAL=500
mkdir -p receipts/shards claude_bridge
for i in 0 1 2 3 4 5 6 7 8 9; do
  ( sleep $((i * 4)); nice -n 15 python eval_parity.py --core "$CORE" --game "$GAME" --slots 90,91,92,93,94 --model "$M" \
      --episodes 50 --instance $((50 + i)) > "receipts/shards/eval_leg${N}_lv8mix_top_s${i}_out.txt" 2>&1 ) &
done
wait
python merge_receipts.py slot --model "$M" --slot 90 --slots 90,91,92,93,94 --per-shard 50 \
  --out "receipts/eval_leg${N}_lv8mix_top_out.txt" receipts/shards/eval_leg${N}_lv8mix_top_s*_out.txt \
  && echo DONE > "claude_bridge/top_leg${N}_done.txt"
