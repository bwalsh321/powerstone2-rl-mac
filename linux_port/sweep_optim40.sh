#!/bin/bash
# sweep_optim40.sh — Sep 16 2026. Blake: "sweep, and fix the timeout reload before it".
# Four arms from ONE parent (the leg 40 zip), the mixed recipe, ent_coef 0.01,
# reload-on-reset fix active (powerstone_env_v6.RELOAD_ON_RESET), 4M steps each:
#   ctrl   no optimizer change            (isolates the reset fix vs leg 40)
#   bs256  PS2_BATCH_SIZE=256             (64 in the zip)
#   lr1e4  PS2_LR=1e-4                    (3e-4 in the zip)
#   kl01   PS2_TARGET_KL=0.1              (0.03 in the zip)
# Each arm trains into its OWN pool copy (pool_sweep40_<arm>, APFS clone of
# pool_league at arm start) so the league pool is untouched, then gets the
# standard sharded battery: lv8 10x50, lv3 10x25, AB vs champion 10x10.
# Waits for leg 40's battery (hold is set, so leg 41 is HELD) before starting.
# Receipts: receipts/eval_sweep40_<arm>_{slot3,slot2,ab_vs_leg1}_out.txt,
# summary receipts/sweep40_summary.txt, markers claude_bridge/sweep40_<arm>_done.txt
# and claude_bridge/sweep40_done.txt. Log: wrapper_sweep40.log. ~20 h total.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONUNBUFFERED=1
export PS2_CORE="${PS2_CORE:-$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib}"
CORE="$PS2_CORE"; GAME="../Power Stone 2 (USA).chd"; LEG1=./powerstone_v6_ppo.zip
PARENT=${SWEEP_PARENT:-./powerstone_v6_leg40_league}
ARMS=${SWEEP_ARMS:-"ctrl bs256 lr1e4 kl01"}
R=receipts; mkdir -p "$R/shards" claude_bridge; SUM=$R/sweep40_summary.txt
SHARDS=10; S3_PER=50; S2_PER=25; AB_PER=10; STAGGER=6
log() { echo "[sweep40] $(date '+%F %T') $*" | tee -a wrapper_sweep40.log; }

# ---- 1) wait for leg 40's battery to finish and the machine to go quiet ----
log "waiting for claude_bridge/battery_leg40_done.txt (league_trainer.txt=$(cat league_trainer.txt))"
while :; do
  [ -e claude_bridge/battery_leg40_FAILED.txt ] && { log "leg 40 battery FAILED marker present; NOT starting"; exit 1; }
  if [ -e claude_bridge/battery_leg40_done.txt ] && ! tmux has-session -t bat40 2>/dev/null; then
    n=$(pgrep -f 'eval_parit[y]|ab_selfplay_prob[e]|train_selfplay_asyn[c]|spawn_mai[n]' | wc -l | tr -d ' ')
    [ "$n" -eq 0 ] && break
  fi
  sleep 60
done
[ -f "$PARENT.zip" ] || { log "parent $PARENT.zip missing; NOT starting"; exit 1; }
sleep 30
log "start parent=$PARENT arms=[$ARMS]"
echo "sweep40 start $(date)  parent=$PARENT  arms=[$ARMS]  reload-on-reset fix ACTIVE, mixed recipe, ent_coef 0.01, 4M steps" >> "$SUM"

# ---- 2) train one arm (watchdog like league_leg_async.sh) ----
train_arm() {  # train_arm <arm> <VAR=VAL or ->
  local arm=$1 ov=$2 out=./powerstone_v6_sweep40_${arm}_league log=train_sweep40_${arm}_out.txt
  local pool=./pool_sweep40_${arm}
  [ -d "$pool" ] || cp -Rc pool_league "$pool"          # APFS clone: instant, no extra space
  # bash 3.2 + set -u: expanding an EMPTY array aborts the script ("ovs[@]: unbound
  # variable") — that killed the first launch at 19:52 EDT before any trainer ran.
  # Use the ${arr[@]+"${arr[@]}"} idiom below, which expands to nothing when empty.
  local -a ovs=(); [ "$ov" != "-" ] && ovs=("$ov")
  local attempt eps
  for attempt in 1 2 3; do
    log "arm $arm attempt $attempt override=${ov}"
    env ${ovs[@]+"${ovs[@]}"} PS2_WARM="$PARENT" PS2_FRESH=1 PS2_POOL="$pool" PS2_OUT="$out" \
        PS2_CKPT_DIR="./checkpoints_sweep40_${arm}" \
        PS2_NACTORS=10 PS2_NENVS=10 PS2_STAGGER=20 PS2_TOTAL_STEPS=4000000 PS2_INSTANCE_BASE=0 \
        PS2_PULL_EVERY=64 PS2_ENV=ffa PS2_OBS_V2=1 PS2_STATE_SLOT=0 PS2_POOL_SAMPLING=uniform \
        PS2_STATES_DIR=./states_mixed PS2_FFA_SEATS=0,2 \
        PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:. \
        python -u train_selfplay_async.py > "$log" 2>&1
    grep -q "leg complete" "$log" && { log "arm $arm training complete"; mv "$log" "$R/"; return 0; }
    eps=$(grep -c "\[ep\]" "$log" | tr -d ' ')
    pkill -9 -f 'train_selfplay_asyn[c]' 2>/dev/null; pkill -9 -f 'spawn_mai[n]' 2>/dev/null
    log "arm $arm trainer exited without completion after $eps eps"
    [ "$eps" -gt 100 ] && { log "arm $arm MID-RUN CRASH, arm abandoned"; mv "$log" "$R/train_sweep40_${arm}_crashed_out.txt"; return 1; }
    sleep 20
  done
  log "arm $arm out of attempts"; return 1
}

# ---- 3) sharded battery on the arm's final zip (same contract as league_battery.sh) ----
sharded_eval() {  # sharded_eval <arm> <label> <kind> <per> <merge-args...> -- <cmd...>
  local arm=$1 label=$2 kind=$3 per=$4; shift 4
  local margs=(); while [ "$1" != "--" ]; do margs+=("$1"); shift; done; shift
  local i pids=() outs=()
  for ((i=0; i<SHARDS; i++)); do
    local out="$R/shards/eval_sweep40_${arm}_${label}_s${i}_out.txt"; outs+=("$out")
    ( sleep $((i * STAGGER)); "$@" --episodes "$per" --instance "$i" > "$out" 2>&1 ) &
    pids+=($!)
  done
  wait "${pids[@]}" 2>/dev/null
  for ((i=0; i<SHARDS; i++)); do
    local out="${outs[$i]}"
    if ! python merge_receipts.py "$kind" "${margs[@]}" --per-shard "$per" --out /dev/null "$out" >/dev/null 2>&1; then
      log "arm $arm shard $label/$i invalid, retrying once"
      "$@" --episodes "$per" --instance "$i" > "$out" 2>&1
    fi
  done
  python merge_receipts.py "$kind" "${margs[@]}" --per-shard "$per" --out "$R/eval_sweep40_${arm}_${label}_out.txt" "${outs[@]}"
}
eval_arm() {  # eval_arm <arm>
  local arm=$1 M=./powerstone_v6_sweep40_${arm}_league.zip ok=1
  export PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:. PS2_OBS_V2=1
  sharded_eval "$arm" slot3 slot "$S3_PER" --model "$M" --slot 3 -- python eval_parity.py --core "$CORE" --game "$GAME" --slot 3 --model "$M" || ok=0
  sharded_eval "$arm" slot2 slot "$S2_PER" --model "$M" --slot 2 -- python eval_parity.py --core "$CORE" --game "$GAME" --slot 2 --model "$M" || ok=0
  sharded_eval "$arm" ab_vs_leg1 ab "$AB_PER" --model "$M" --opp "$LEG1" -- python -u ab_selfplay_probe.py --model "$M" --opp "$LEG1" || ok=0
  {
    echo "== arm $arm  ($(date))"
    grep -h 'win%' "$R/eval_sweep40_${arm}_slot3_out.txt" 2>/dev/null | sed 's/^/   lv8   /'
    grep -h 'win%' "$R/eval_sweep40_${arm}_slot2_out.txt" 2>/dev/null | sed 's/^/   lv3   /'
    grep -h 'AB RESULT' "$R/eval_sweep40_${arm}_ab_vs_leg1_out.txt" 2>/dev/null | sed 's/^/   /'
    [ "$ok" -eq 1 ] || echo "   (one or more receipts INCOMPLETE)"
  } >> "$SUM"
  return $((1 - ok))
}

for arm in $ARMS; do
  case $arm in
    ctrl)  ov=- ;;
    bs256) ov=PS2_BATCH_SIZE=256 ;;
    lr1e4) ov=PS2_LR=1e-4 ;;
    kl01)  ov=PS2_TARGET_KL=0.1 ;;
    *) log "unknown arm $arm"; continue ;;
  esac
  if train_arm "$arm" "$ov"; then
    eval_arm "$arm" && log "arm $arm battery complete" || log "arm $arm battery INCOMPLETE"
  else
    echo "== arm $arm TRAINING FAILED ($(date))" >> "$SUM"
  fi
  echo DONE > "claude_bridge/sweep40_${arm}_done.txt"
done
echo "sweep40 end $(date)" >> "$SUM"
echo DONE > claude_bridge/sweep40_done.txt
log "sweep complete"
