#!/bin/bash
# Post-leg battery for the self-compounding league, then advance state and
# launch the next leg.
#
# Contract (Sep 10 rewrite, external audit R1): persistent state is touched
# ONLY after all four evaluations have produced complete, consistent
# receipts (check_receipt.py). On any failure the pool, league_state.txt and
# the DONE marker are left untouched, a FAILED marker is written for the
# relay wake, and the script exits nonzero. Battery completion and next-leg
# startup are reported separately.
#
# Exit codes: 0 all good and next leg launched; 1 an evaluation failed
# (state unchanged); 2 battery complete and state advanced but the next-leg
# tmux launch failed.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
read N PREV < league_state.txt
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. PYTHONUNBUFFERED=1
if [ "$(uname)" = "Darwin" ]; then
  CORE="${PS2_CORE:-$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib}"
  KEEPAWAKE="caffeinate -is"
else
  CORE="${PS2_CORE:-$HOME/cores/flycast_libretro.so}"
  KEEPAWAKE=""
fi
# ab_selfplay_probe.py reads its core from PS2_CORE; it used to fall back to
# the Mac default on Linux because CORE was never exported.
export PS2_CORE="$CORE"
GAME="../Power Stone 2 (USA).chd"
M=./powerstone_v6_leg${N}_league.zip
LEG1=./powerstone_v6_ppo.zip
R=receipts
mkdir -p "$R" claude_bridge
[ -f "$M" ] || { echo "battery leg $N: final $M missing" | tee "claude_bridge/battery_leg${N}_FAILED.txt"; exit 1; }
# the finished leg's training log joins the receipts (the wrapper wrote it
# beside the scripts; the trainer may still hold it open, rename is fine)
[ -f "train_leg${N}_out.txt" ] && mv "train_leg${N}_out.txt" "$R/"

FAILED=()

# run_eval <receipt> <check-args...> -- <command...>
# Runs the command up to twice; a receipt is accepted only if
# check_receipt.py says it is complete. Exit status of the eval itself is
# deliberately ignored: on macOS every eval aborts in libc++ teardown after
# printing its summary, so the receipt content is the evidence.
run_eval() {
  local out="$1"; shift
  local check=()
  while [ "$1" != "--" ]; do check+=("$1"); shift; done; shift
  local attempt
  for attempt in 1 2; do
    "$@" > "$out" 2>&1
    if python check_receipt.py "${check[@]}" "$out"; then return 0; fi
    echo "battery leg $N: $out attempt $attempt invalid" >&2
  done
  FAILED+=("$out")
  return 1
}

run_eval "$R/eval_leg${N}_slot3_out.txt" slot --model "$M" --episodes 50 -- \
  python eval_parity.py --core "$CORE" --game "$GAME" --slot 3 --episodes 50 --model "$M"
run_eval "$R/eval_leg${N}_slot2_out.txt" slot --model "$M" --episodes 50 -- \
  python eval_parity.py --core "$CORE" --game "$GAME" --slot 2 --episodes 50 --model "$M"
run_eval "$R/eval_leg${N}_ab_vs_prev_out.txt" ab --model "$M" --opp "$PREV" --episodes 12 -- \
  python -u ab_selfplay_probe.py --model "$M" --opp "$PREV" --episodes 12
run_eval "$R/eval_leg${N}_ab_vs_leg1_out.txt" ab --model "$M" --opp "$LEG1" --episodes 12 -- \
  python -u ab_selfplay_probe.py --model "$M" --opp "$LEG1" --episodes 12

if [ ${#FAILED[@]} -gt 0 ]; then
  {
    echo "battery leg $N FAILED $(date -u +%FT%TZ): incomplete receipts after retry:"
    printf '  %s\n' "${FAILED[@]}"
    echo "state NOT advanced, pool NOT updated, next leg NOT launched"
  } | tee "claude_bridge/battery_leg${N}_FAILED.txt" >&2
  exit 1
fi

# ---- all four receipts complete: persist, then launch ----
cp "$M" "pool_league/prog_leg${N}.zip"
NEXT=$((N+1))
echo "$NEXT $M" > league_state.txt.tmp && mv league_state.txt.tmp league_state.txt
echo DONE > "claude_bridge/battery_leg${N}_done.txt"
if tmux new -s ps2train -d "$KEEPAWAKE bash $(pwd)/league_leg.sh"; then
  echo "battery leg $N complete; leg $NEXT launched in tmux ps2train"
  exit 0
fi
echo "battery leg $N complete and state advanced to leg $NEXT, but tmux launch FAILED" \
  | tee "claude_bridge/leg${NEXT}_LAUNCH_FAILED.txt" >&2
exit 2
