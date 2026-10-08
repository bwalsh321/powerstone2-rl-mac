#!/bin/bash
# League leg on the ASYNC actor-learner trainer (train_selfplay_async.py).
# Same contract as league_leg.sh: reads league_state.txt "<N> <warm zip>",
# writes train_leg<N>_out.txt and powerstone_v6_leg<N>_league.zip, logs to
# wrapper_league.log, exit 0 only on "leg complete". Watchdog: a trainer
# that dies BEFORE 100 episodes is treated as a boot failure and retried
# (max 4 attempts); one that dies after 100 episodes is a mid-leg crash ->
# halt, never blind-relaunch (the async trainer prints "ACTOR DIED" and
# exits 1 when an actor process dies). NOT chained by league_battery.sh
# (which launches league_leg.sh); launch by hand for a validation leg:
#   tmux new -s ps2train -d "caffeinate -is bash league_leg_async.sh"
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
read N PREV < league_state.txt
source ~/ps2rl/bin/activate
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/linux_gpu_env.sh"   # Oct 1: GPU EGL on Linux (was Xvfb :99)
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. PYTHONUNBUFFERED=1
if [ -z "$PS2_CORE" ]; then
  if [ "$(uname)" = "Darwin" ]; then
    export PS2_CORE="$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib"
  else
    export PS2_CORE="$HOME/cores/flycast_libretro.so"
  fi
fi
export PS2_WARM=$PREV PS2_FRESH=1 PS2_POOL=./pool_league
export PS2_OUT=./powerstone_v6_leg${N}_league
# Oct 1 2026 (9950X): Linux defaults from the throughput sweep (receipts/parity_9950x/sweep3-4):
# 16 actors (~365 steps/s vs 219 at 10; policy lag 1.6 vs 1.0 = a RECIPE CHANGE, noted per leg),
# NENVS stays 10 (rollout size unchanged), actors on instances 20.. so they never collide with the
# battery's eval shards (0-9) or the scout (11), 3 s boot stagger (the Metal race is macOS-only; a
# small stagger avoids the simultaneous-boot freeze), learner torch threads capped at 4 (uncapped it
# fought the actors: 40-75 s updates at 22 actors).
if [ "$(uname)" != "Darwin" ]; then
  export PS2_NACTORS=${PS2_NACTORS:-16} PS2_INSTANCE_BASE=${PS2_INSTANCE_BASE:-20} PS2_STAGGER=${PS2_STAGGER:-3}
  export OMP_NUM_THREADS=${OMP_NUM_THREADS:-4} MKL_NUM_THREADS=${MKL_NUM_THREADS:-4}
fi
export PS2_NACTORS=${PS2_NACTORS:-10} PS2_NENVS=${PS2_NENVS:-10} PS2_STAGGER=${PS2_STAGGER:-20}
export PS2_TOTAL_STEPS=${PS2_TOTAL_STEPS:-4000000} PS2_INSTANCE_BASE=${PS2_INSTANCE_BASE:-0}
# Sep 13 (Blake, after the leg-23 validation): actors refresh weights mid-chunk
# every 64 steps so batches are not a flat one update stale (the leg-23 finding:
# target_kl early-stopped 165/195 updates in epoch 0). 0 = boundary-only.
export PS2_PULL_EVERY=${PS2_PULL_EVERY:-64}
# Sep 13 2026: league_trainer.txt = "ffa" -> four-seat self-play FFA lineage
# (ffa_selfplay_env.py on the 4-port harness, obs v2, slot 0 state, PFSP pool
# sampling). Anything else = the 2-seat SelfPlayEnv on slot 1 (obs v1).
MODE="$(tr -d '[:space:]' < league_trainer.txt 2>/dev/null)"
# Oct 1 2026 (GPT review P1): launch permission is HOST-LOCAL. Only a machine whose untracked
# linux_port/host_role.txt reads "train" may start a leg; league_trainer.txt is tracked in git, so a pull
# must never grant another machine permission to train.
ROLE="$(tr -d '[:space:]' < host_role.txt 2>/dev/null)"
if [ "$ROLE" != "train" ]; then
  echo "[wrapper] REFUSED: host_role.txt='${ROLE}' (not the training host); nothing launched $(date)" | tee -a wrapper_league.log >&2
  exit 2
fi
# Oct 1 2026 (GPT review P1): this wrapper used to train on ANY mode word, including "hold" (only the
# battery's chain honoured it). Refuse anything but a known async mode, before any log or Python.
case "$MODE" in
  async|ffa|mixed) ;;
  *) echo "[wrapper-async] leg $N REFUSED: league_trainer.txt='${MODE}' (hold or unknown mode); nothing launched $(date)" | tee -a wrapper_league.log >&2
     exit 2 ;;
esac
# Sep 16: optional entropy coefficient for this leg, one number in league_entcoef.txt
# (absent/empty = the zip's 0.01). Recorded in leg_modes.txt as a third column.
ENTC="$(tr -d '[:space:]' < league_entcoef.txt 2>/dev/null)"
[ -n "$ENTC" ] && export PS2_ENT_COEF="$ENTC"
# Sep 15: record this leg's mode so the battery evaluates it under the right
# contract regardless of what league_trainer.txt says later (holds!).
# Sep 17: standing optimizer overrides for the lineage, one line of VAR=VAL pairs in
# league_optim.txt (e.g. "PS2_LR=1e-4" or "PS2_LR=1e-4 PS2_BATCH_SIZE=256"); absent/empty
# = the zip's values. Exported here, printed by the trainer as "[config] ... override",
# recorded in leg_modes.txt as a fourth column. Sweep 40 result: lr 1e-4 -> lv8 13.6.
OPTIM="$(tr -s '[:space:]' ' ' < league_optim.txt 2>/dev/null | sed 's/^ //;s/ $//')"
for kv in $OPTIM; do case "$kv" in PS2_LR=*|PS2_BATCH_SIZE=*|PS2_TARGET_KL=*) export "$kv" ;; *) echo "[wrapper-async] ignoring unknown override $kv" >> wrapper_league.log ;; esac; done
# Sep 20: training-only ARENA flags, one line of VAR=VAL pairs in league_env.txt
# (PS2_ZERO_SUM=1, PS2_START_HEALTH=lo,hi); absent/empty = off. Exported here, the
# FFA env prints "[config] zero_sum=1" / "[config] start_health=...", recorded in
# leg_modes.txt as a fifth column. Evals never see these (base env), so the eval
# contract is unchanged.
ARENA="$(tr -s '[:space:]' ' ' < league_env.txt 2>/dev/null | sed 's/^ //;s/ $//')"
unset PS2_OBS_V4 PS2_OBS_V4_ITEMEMB PS2_DMG_ATTRIB PS2_GEM_EP_CAP    # Oct 5 2026 (Oct 7: + reward-cleanup flags): the v4 contract comes from league_env.txt only, never an inherited env
for kv in $ARENA; do case "$kv" in PS2_ZERO_SUM=*|PS2_START_HEALTH=*|PS2_STATE_SLOTS=*|PS2_OBS_STACK=*|PS2_OBS_CTX_FIX=*|PS2_ZS_TIME=*|PS2_OBS_V3=*|PS2_SPECIAL_DMG_W=*|PS2_SPECIAL_R=*|PS2_LOST_EXTRA_W=*|PS2_LOSS_SCALE_LV8=*|PS2_SPECIAL_WINDOW=*|PS2_SPECIAL_WINDOW_CLOCK=*|PS2_SPECIAL_EVENTS=*|PS2_SPECIAL_ATTRIB=*|PS2_BUTTON_TAP=*|PS2_DEMOS=*|PS2_BC_COEF=*|PS2_BC_STEPS=*|PS2_BC_SEQS=*|PS2_BC_ANNEAL=*|PS2_BC_HOLDOUT=*|PS2_BC_EVAL=*|PS2_BC_PATIENCE=*|PS2_BC_RESULTS=*|PS2_OBJ_GRID_N=*|PS2_OBS_V4=*|PS2_OBS_V4_ITEMEMB=*|PS2_PPO_KL_REF=*|PS2_DMG_ATTRIB=*|PS2_GEM_EP_CAP=*) export "$kv" ;; *) echo "[wrapper-async] ignoring unknown arena flag $kv" >> wrapper_league.log ;; esac; done
# Oct 3 2026 (Blake: action space "is priority"): league_surgery.txt holds one "<from_leg> <kind>" per line, applied in
# file order. lstm128 = SkipLSTM memory (surgery_lstm.py); joint63 = 63-action direction x button set
# (surgery_actions.py, combo penalty 3). Each applies only to a warm zip that does not have it yet.
# Oct 5 2026: obsv4 = widen 160 -> 430 per frame (surgery_widen_v4.py: new columns zero = exact warm start); needs
# PS2_OBS_V4=1 in league_env.txt. With PS2_OBS_V4_ITEMEMB=zero the parent's [12..17] columns are zeroed too.
# Oct 7 2026: itememb0 = zero the [12..17] columns of an already-430-wide zip (surgery_zero_itememb.py); needs
# PS2_OBS_V4_ITEMEMB=zero in league_env.txt.
while read -r SURG_FROM SURG_KIND; do
  [ -n "$SURG_FROM" ] && [ "$N" -ge "$SURG_FROM" ] || continue
  case "$SURG_KIND" in
    lstm128)
      CHECK="from recurrent_policy import is_recurrent_zip as f; ok = f('${PREV}')"
      CMD="python surgery_lstm.py \"$PREV\" \"./powerstone_v6_leg$((N-1))_lstm128.zip\" --hidden 128"
      OUT="./powerstone_v6_leg$((N-1))_lstm128.zip"; TAG="RECURRENT=lstm128" ;;
    joint63)
      CHECK="from recurrent_policy import load_model as f; ok = int(f('${PREV}').action_space.n) == 63"
      OUT="./powerstone_v6_leg$((N-1))_joint63.zip"
      CMD="python surgery_actions.py \"$PREV\" \"$OUT\" --penalty 3"; TAG="ACTIONS=joint63" ;;
    obsv4)
      [ "${PS2_OBS_V4:-0}" = "1" ] || { echo "[wrapper-async] leg $N REFUSED: obsv4 surgery listed but league_env.txt lacks PS2_OBS_V4=1; nothing launched $(date)" | tee -a wrapper_league.log >&2; exit 2; }
      CHECK="from obs_stack import kd_for; from recurrent_policy import load_model as f; ok = kd_for(f('${PREV}'))[1] == 430"
      OUT="./powerstone_v6_leg$((N-1))_v4.zip"
      ZI=""; [ "${PS2_OBS_V4_ITEMEMB:-keep}" = "zero" ] && ZI="--zero-item-emb"
      CMD="python surgery_widen_v4.py \"$PREV\" \"$OUT\" $ZI"; TAG="OBS=v4" ;;
    itememb0)
      # Oct 7 2026 (reward-cleanup bundle): zero the obs[12..17] slot-hash columns of an ALREADY-430-wide policy
      # (every frame slot of the first layers + LSTM input columns 12..17, and their Adam moments). The env must
      # write 0 there too, so refuse unless league_env.txt says PS2_OBS_V4_ITEMEMB=zero.
      [ "${PS2_OBS_V4_ITEMEMB:-keep}" = "zero" ] || { echo "[wrapper-async] leg $N REFUSED: itememb0 surgery listed but league_env.txt lacks PS2_OBS_V4_ITEMEMB=zero; nothing launched $(date)" | tee -a wrapper_league.log >&2; exit 2; }
      CHECK="from surgery_zero_itememb import is_zeroed as f; ok = f('${PREV}')"
      OUT="./powerstone_v6_leg$((N-1))_ie0.zip"
      CMD="python surgery_zero_itememb.py \"$PREV\" \"$OUT\""; TAG="ITEMEMB=zero" ;;
    *) echo "[wrapper-async] leg $N REFUSED: unknown surgery kind '$SURG_KIND'; nothing launched $(date)" | tee -a wrapper_league.log >&2; exit 2 ;;
  esac
  if ! python -c "import sys; ${CHECK}; sys.exit(0 if ok else 1)" 2>/dev/null; then
    echo "[wrapper-async] leg $N: surgery ${SURG_KIND} ${PREV} -> ${OUT} $(date)" >> wrapper_league.log
    if eval "$CMD" >> wrapper_league.log 2>&1 && [ -s "$OUT" ]; then
      PREV="$OUT"; export PS2_WARM="$OUT"
    else
      echo "[wrapper-async] leg $N REFUSED: ${SURG_KIND} surgery failed; nothing launched $(date)" | tee -a wrapper_league.log >&2
      exit 2
    fi
  fi
  ARENA="${ARENA:+$ARENA }${TAG}"
done < <(cat league_surgery.txt 2>/dev/null)
echo "$N ${MODE:-async} ${ENTC:-0.01} ${OPTIM:--} ${ARENA:--}" >> leg_modes.txt
if [ "$MODE" = "ffa" ] || [ "$MODE" = "mixed" ]; then
  export PYTHONPATH=../sdlarch-rl/p4:$PYTHONPATH
  export PS2_ENV=ffa PS2_OBS_V2=1 PS2_STATE_SLOT=${PS2_STATE_SLOT:-0} PS2_POOL_SAMPLING=${PS2_POOL_SAMPLING:-uniform}
fi
# Sep 15 (Blake): "mixed" = two policy seats (P1, P3) + one COM seat (P4, lv3),
# state ./states_mixed/slot0.state (same slot number -> identical obs contract).
if [ "$MODE" = "mixed" ]; then
  export PS2_STATES_DIR=./states_mixed PS2_FFA_SEATS=0,2
fi
LOG=train_leg${N}_out.txt
for attempt in 1 2 3 4; do
  echo "[wrapper-async] leg $N attempt $attempt $(date)" >> wrapper_league.log
  python -u train_selfplay_async.py > "$LOG" 2>&1
  grep -q "leg complete" "$LOG" && { echo "[wrapper-async] leg $N complete" >> wrapper_league.log; exit 0; }
  eps=$(grep -c "\[ep\]" "$LOG")
  pkill -9 -f train_selfplay_async.py 2>/dev/null; pkill -9 -f spawn_main 2>/dev/null
  echo "[wrapper-async] leg $N trainer exited without completion after $eps eps" >> wrapper_league.log
  [ "$eps" -gt 100 ] && { echo "[wrapper-async] mid-leg crash, halting" >> wrapper_league.log; exit 1; }
  sleep 20
done
echo "[wrapper-async] leg $N out of attempts" >> wrapper_league.log
exit 1
