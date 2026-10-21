#!/bin/bash
# stoch_grade.sh <N> — sampled-move grade of leg N (Oct 9 2026, Blake). The per-leg lv8mix grade takes the policy's
# single top move, and that number swung 56.5 -> 41.4 over legs 145-148 while the same bots graded with SAMPLED moves
# (the way they train) held at 54.4 / 53.0. This runs 500 rounds (10 shards x 50, the same 500 start points every leg)
# with --stochastic beside the next leg's training, low priority, instances 50-59, and writes
# receipts/eval_leg<N>_lv8mix_stoch_out.txt + claude_bridge/stoch_leg<N>_done.txt. Started by league_battery.sh after
# the launch, like scout_leg.sh; it never gates the relay.
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
K="$(echo "$ROW" | grep -o "PS2_OBS_STACK=[0-9]*" | head -1)"; [ -n "$K" ] && export "$K"   # Oct 13 2026: frame-stack option (eval stack_for checks the zip)
CORE="${PS2_CORE:-$HOME/cores/flycast_libretro.so}"; GAME="../Power Stone 2 (USA).chd"
export PS2_EVAL_INSTANCE_BASE=50 PS2_EVAL_TOTAL=500
mkdir -p receipts/shards claude_bridge
for i in 0 1 2 3 4 5 6 7 8 9; do
  ( sleep $((i * 4)); nice -n 15 python eval_parity.py --core "$CORE" --game "$GAME" --slots 90,91,92,93,94 --model "$M" \
      --episodes 50 --instance $((50 + i)) --stochastic > "receipts/shards/eval_leg${N}_lv8mix_stoch_s${i}_out.txt" 2>&1 ) &
done
wait
python merge_receipts.py slot --model "$M" --slot 90 --slots 90,91,92,93,94 --per-shard 50 \
  --out "receipts/eval_leg${N}_lv8mix_stoch_out.txt" receipts/shards/eval_leg${N}_lv8mix_stoch_s*_out.txt \
  && echo DONE > "claude_bridge/stoch_leg${N}_done.txt"
