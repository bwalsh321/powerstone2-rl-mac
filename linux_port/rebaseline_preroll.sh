#!/bin/bash
# Re-baseline under the pre-roll fix (Sep 17 2026): stagger 0-239 instead of 0-599.
# Champion on slot3 (lv8, 10x50) + slot2 (lv3, 10x25); the two leg-41 candidates
# (sweep40 lr1e4, kl01) on slot3. Zero footprint. Receipts: receipts/rebase_preroll_*.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:. PYTHONUNBUFFERED=1 PS2_OBS_V2=1
CORE="$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib"
GAME="../Power Stone 2 (USA).chd"
R=receipts; mkdir -p $R/shards
run() {  # run <label> <model> <slot> <per-shard>
  local label=$1 model=$2 slot=$3 per=$4 i pids=() outs=()
  for ((i=0; i<10; i++)); do
    local out="$R/shards/rebase_preroll_${label}_s${i}_out.txt"; outs+=("$out")
    ( sleep $((i*6)); python eval_parity.py --core "$CORE" --game "$GAME" --slot $slot --model "$model" --episodes $per --instance $i > "$out" 2>&1 ) &
    pids+=($!)
  done
  wait "${pids[@]}" 2>/dev/null
  python merge_receipts.py slot --model "$model" --slot $slot --per-shard $per --out "$R/rebase_preroll_${label}_out.txt" "${outs[@]}"
}
echo "rebaseline preroll start $(date)"
run champ_slot3 ./powerstone_v6_ppo.zip 3 50
run lr1e4_slot3 ./powerstone_v6_sweep40_lr1e4_league.zip 3 50
run kl01_slot3 ./powerstone_v6_sweep40_kl01_league.zip 3 50
run champ_slot2 ./powerstone_v6_ppo.zip 2 25
echo "rebaseline preroll end $(date)"
for f in champ_slot3 lr1e4_slot3 kl01_slot3 champ_slot2; do echo "== $f"; grep -E 'win%|picks|forms|distinct' $R/rebase_preroll_${f}_out.txt | head -4; done
echo DONE > claude_bridge/rebaseline_preroll_done.txt
