#!/bin/bash
# hunt_grade.sh <N> — "hunted" grade of leg N (Oct 11 2026, Blake): 280 rounds on slots 30-43 with P1 and P3 driven by
# hunter_bot.py (they only attack our bot) and P4 the lv8 CPU, deterministic, the same start points every leg
# (eval_hunted.py). Leg 159 scored 7.1% here vs 40.4% against copies of itself. Runs beside the next leg's training,
# low priority, instances 60-62; writes receipts/eval_leg<N>_hunted_out.txt + claude_bridge/hunt_leg<N>_done.txt.
# Started by league_battery.sh after the launch, like stoch_grade.sh; never gates the relay.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source ~/ps2rl/bin/activate
source ./linux_gpu_env.sh
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:. PYTHONUNBUFFERED=1 PS2_OBS_V2=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
N=$1; M=./powerstone_v6_leg${N}_league.zip
ROW="$(awk -v n="$N" '$1==n' leg_modes.txt 2>/dev/null)"
echo "$ROW" | grep -q "PS2_OBS_V3=1" && export PS2_OBS_V3=1
echo "$ROW" | grep -q "PS2_BUTTON_TAP=1" && export PS2_BUTTON_TAP=1
G="$(echo "$ROW" | grep -o "PS2_OBJ_GRID_N=[0-9]*" | head -1)"; [ -n "$G" ] && export "$G"
if echo "$ROW" | grep -q "PS2_OBS_V4=1"; then export PS2_OBS_V4=1
  E="$(echo "$ROW" | grep -o "PS2_OBS_V4_ITEMEMB=[a-z]*" | head -1)"; [ -n "$E" ] && export "$E"; fi
mkdir -p receipts/hunter claude_bridge
i=0
for spec in "0 98" "7 98" "14 84"; do
  set -- $spec
  ( sleep $((i * 5)); nice -n 15 python eval_hunted.py --model "$M" --hunters 0,2 --slots 30-43 --episodes $2 \
      --visit-offset $1 --visits-total 20 --instance $((60 + i)) --out "receipts/hunter/leg${N}_hunted_s${i}.jsonl" \
      > "receipts/hunter/leg${N}_hunted_s${i}.log" 2>&1 ) &
  i=$((i + 1))
done
wait
python eval_hunted.py --merge receipts/hunter/leg${N}_hunted_s*.jsonl --label "leg $N hunted" > "receipts/eval_leg${N}_hunted_out.txt" \
  && echo DONE > "claude_bridge/hunt_leg${N}_done.txt"
