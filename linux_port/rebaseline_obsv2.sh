#!/bin/bash
# Re-baseline under obs v2 (Sep 13 2026): the leg 25 zip and the leg1 champion
# evaluated on slot3 (lv8 FFA) and slot2 (lv3 FFA) with PS2_OBS_V2=1 on the
# 4-port harness, sharded like the battery (10x50 / 10x25). Gives every later
# FFA-lineage number a same-contract reference. Zero footprint (no pool or
# state writes). Run on a quiet machine (~50 min). Receipts: receipts/rebase_v2_*.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:. PYTHONUNBUFFERED=1 PS2_OBS_V2=1
CORE="$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib"
GAME="../Power Stone 2 (USA).chd"
R=receipts; mkdir -p $R/shards
SHARDS=${PS2_EVAL_SHARDS:-10}; BASE=${PS2_EVAL_INSTANCE_BASE:-0}
run() {  # run <label> <model> <slot> <per-shard>
  local label=$1 model=$2 slot=$3 per=$4 i pids=() outs=()
  for ((i=0; i<SHARDS; i++)); do
    local out="$R/shards/rebase_v2_${label}_s${i}_out.txt"; outs+=("$out")
    ( sleep $((i*6)); python eval_parity.py --core "$CORE" --game "$GAME" --slot $slot --model "$model" --episodes $per --instance $((BASE+i)) > "$out" 2>&1 ) &
    pids+=($!)
  done
  wait "${pids[@]}" 2>/dev/null
  python merge_receipts.py slot --model "$model" --slot $slot --per-shard $per --out "$R/rebase_v2_${label}_out.txt" "${outs[@]}"
}
echo "rebaseline start $(date)"
run leg25_slot3 ./powerstone_v6_leg25_league.zip 3 50
run leg25_slot2 ./powerstone_v6_leg25_league.zip 2 25
run champ_slot3 ./powerstone_v6_ppo.zip 3 50
run champ_slot2 ./powerstone_v6_ppo.zip 2 25
echo "rebaseline end $(date)"
for f in leg25_slot3 leg25_slot2 champ_slot3 champ_slot2; do echo "== $f"; grep -A3 "EVAL SUMMARY" $R/rebase_v2_${f}_out.txt | tail -3; done
echo REBASELINE_DONE > claude_bridge/rebaseline_v2_done.txt
