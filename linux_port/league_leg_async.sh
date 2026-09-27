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
[ "$(uname)" = "Darwin" ] || export DISPLAY="${DISPLAY:-:99}"   # Sep 25: Linux relay uses a persistent Xvfb :99
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
for kv in $ARENA; do case "$kv" in PS2_ZERO_SUM=*|PS2_START_HEALTH=*|PS2_STATE_SLOTS=*|PS2_OBS_STACK=*|PS2_OBS_CTX_FIX=*|PS2_ZS_TIME=*|PS2_OBS_V3=*|PS2_SPECIAL_DMG_W=*|PS2_SPECIAL_R=*|PS2_LOST_EXTRA_W=*|PS2_LOSS_SCALE_LV8=*|PS2_SPECIAL_WINDOW=*) export "$kv" ;; *) echo "[wrapper-async] ignoring unknown arena flag $kv" >> wrapper_league.log ;; esac; done
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
