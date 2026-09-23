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
# Sep 13 2026: an "ffa" lineage (league_trainer.txt) trains under obs v2 on the
# 4-port harness; its checkpoints must be EVALUATED under the same contract.
# the finished leg's OWN mode (recorded at its launch in leg_modes.txt) decides the
# eval contract; league_trainer.txt is only a fallback for legs launched before Sep 15.
TRAINER_MODE="$(awk -v n="$N" '$1==n {m=$2} END {print m}' leg_modes.txt 2>/dev/null)"
[ -n "$TRAINER_MODE" ] || TRAINER_MODE="$(tr -d '[:space:]' < league_trainer.txt 2>/dev/null || echo lockstep)"
if [ "$TRAINER_MODE" = "ffa" ] || [ "$TRAINER_MODE" = "mixed" ]; then
  export PYTHONPATH=../sdlarch-rl/p4:$PYTHONPATH PS2_OBS_V2=1
fi
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

# ---- Sep 13 2026: PARALLEL SHARDED EVALUATIONS (Blake: "use the cores") ----
# Each evaluation runs as K shards on K emulator instances (system/dolphin-<id>,
# per-shard bridge dirs), then merge_receipts.py validates every shard and
# writes ONE receipt in the standard format (what the relay/HANDOFF read).
# Per-leg totals: slot3 (lv8) 10x50 = 500 eps, slot2 (lv3) 10x25 = 250 eps,
# AB vs the leg1 champion 10x10 = 100 eps. The AB vs the parent was dropped
# (Blake, Sep 13: it always wins; a fixed reference is the informative test).
# A failed shard is rerun once on its own before the receipt is declared bad.
SHARDS=${PS2_EVAL_SHARDS:-10}
EVAL_BASE=${PS2_EVAL_INSTANCE_BASE:-0}     # instance ids EVAL_BASE..EVAL_BASE+SHARDS-1
S3_PER=${PS2_SLOT3_PER_SHARD:-50}
S2_PER=${PS2_SLOT2_PER_SHARD:-25}
AB_PER=${PS2_AB_PER_SHARD:-10}
STAGGER=${PS2_EVAL_STAGGER:-6}             # seconds between shard boots (Metal race)
mkdir -p "$R/shards"

# run_shard <out> <check-kind> <check-args...> -- <command...>   (foreground, one attempt)
run_shard() {
  local out="$1"; shift
  "$@" > "$out" 2>&1
}

# sharded_eval <label> <kind:slot|ab> <per-shard> <merge-args...> -- <cmd prefix...>
#   the command gets "--episodes <per-shard> --instance <id>" appended per shard
sharded_eval() {
  local label="$1" kind="$2" per="$3"; shift 3
  local margs=()
  while [ "$1" != "--" ]; do margs+=("$1"); shift; done; shift
  local i pids=() outs=()
  for ((i=0; i<SHARDS; i++)); do
    local inst=$((EVAL_BASE + i)) out="$R/shards/eval_leg${N}_${label}_s${i}_out.txt"
    outs+=("$out")
    ( sleep $((i * STAGGER)); "$@" --episodes "$per" --instance "$inst" > "$out" 2>&1 ) &
    pids+=($!)
  done
  wait "${pids[@]}" 2>/dev/null
  # retry any invalid shard once, serially
  for ((i=0; i<SHARDS; i++)); do
    local inst=$((EVAL_BASE + i)) out="${outs[$i]}"
    if ! python merge_receipts.py "$kind" "${margs[@]}" --per-shard "$per" --out /dev/null "$out" >/dev/null 2>&1; then
      echo "battery leg $N: shard $label/$i invalid, retrying once" >&2
      "$@" --episodes "$per" --instance "$inst" > "$out" 2>&1
    fi
  done
  local merged="$R/eval_leg${N}_${label}_out.txt"
  if python merge_receipts.py "$kind" "${margs[@]}" --per-shard "$per" --out "$merged" "${outs[@]}"; then
    return 0
  fi
  FAILED+=("$merged")
  return 1
}

sharded_eval slot3 slot "$S3_PER" --model "$M" --slot 3 -- \
  python eval_parity.py --core "$CORE" --game "$GAME" --slot 3 --model "$M"
sharded_eval slot2 slot "$S2_PER" --model "$M" --slot 2 -- \
  python eval_parity.py --core "$CORE" --game "$GAME" --slot 2 --model "$M"
sharded_eval ab_vs_leg1 ab "$AB_PER" --model "$M" --opp "$LEG1" -- \
  python -u ab_selfplay_probe.py --model "$M" --opp "$LEG1"

if [ ${#FAILED[@]} -gt 0 ]; then
  {
    echo "battery leg $N FAILED $(date -u +%FT%TZ): incomplete receipts after shard retry:"
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
# Sep 12 2026 (Blake): the next leg's trainer is chosen by league_trainer.txt —
# "async" -> league_leg_async.sh (actor-learner, 2.3x), anything else ->
# league_leg.sh (lockstep SubprocVecEnv). One word, durable across wakes.
# Sep 14 04:05: the LAUNCH mode is re-read HERE (the eval contract above must use
# the finished leg's mode, captured at battery start; the next leg's mode must be
# whatever league_trainer.txt says NOW — a "hold" written during the battery used
# to be ignored, and the wrapper then re-read the file itself: leg 29 mislaunch).
LAUNCH_MODE="$(tr -d '[:space:]' < league_trainer.txt 2>/dev/null || echo lockstep)"
LEG_SCRIPT=league_leg.sh
case "$LAUNCH_MODE" in
  async|ffa|mixed) LEG_SCRIPT=league_leg_async.sh ;;   # ffa/mixed: the async wrapper reads the mode itself
  hold)
    echo "battery leg $N complete and state advanced to leg $NEXT; launch HELD (league_trainer.txt = hold at launch time)" \
      | tee "claude_bridge/leg${NEXT}_LAUNCH_HELD.txt"
    exit 0 ;;
esac
if tmux new -s ps2train -d "$KEEPAWAKE bash $(pwd)/$LEG_SCRIPT"; then
  echo "battery leg $N complete; leg $NEXT launched in tmux ps2train via $LEG_SCRIPT"
  exit 0
fi
echo "battery leg $N complete and state advanced to leg $NEXT, but tmux launch FAILED" \
  | tee "claude_bridge/leg${NEXT}_LAUNCH_FAILED.txt" >&2
exit 2
