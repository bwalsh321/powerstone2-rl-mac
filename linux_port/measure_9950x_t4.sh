#!/bin/bash
# Throughput sweep for the 9950X (Oct 1 2026): standing recipe exactly as league_leg_async.sh exports it
# (mixed, league_optim.txt + league_env.txt), NENVS=10 fixed (rollout size = recipe), actor count varied.
# Writes only *_meas9950x_* outputs and the hardlinked pool_smoke_9950x/; never touches relay state.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# Oct 1 2026 (GPT review P2): this diagnostic ends each trial with a broad pkill of spawn_main, which
# would also kill a live league's actors. Refuse to run unless the machine is quiet.
if tmux has-session -t ps2train 2>/dev/null || [ "$(pgrep -fc 'train_selfplay_asyn[c]|eval_parit[y]|ab_selfplay_prob[e]|watch_pla[y]')" -gt 0 ]; then
  echo "REFUSED: a league leg, eval or scout is running; measure only on an idle machine" >&2; exit 2
fi
source ./linux_gpu_env.sh; source ~/ps2rl/bin/activate
export OMP_NUM_THREADS=${OMP_NUM_THREADS:-4} MKL_NUM_THREADS=${OMP_NUM_THREADS:-4}
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:. PYTHONUNBUFFERED=1
export PS2_CORE=$HOME/cores/flycast_libretro.so PS2_WARM=./powerstone_v6_leg103_league.zip PS2_FRESH=1 PS2_POOL=./pool_smoke_9950x
export PS2_NENVS=10 PS2_STAGGER=${PS2_STAGGER:-3} PS2_PULL_EVERY=64 PS2_INSTANCE_BASE=0
export PS2_ENV=ffa PS2_OBS_V2=1 PS2_STATE_SLOT=0 PS2_POOL_SAMPLING=uniform PS2_STATES_DIR=./states_mixed PS2_FFA_SEATS=0,2
for kv in $(cat league_optim.txt league_env.txt); do export "$kv"; done
for NA in ${ACTORS:-10 16 22}; do
  export PS2_NACTORS=$NA PS2_TOTAL_STEPS=${STEPS:-204800} PS2_OUT=./powerstone_v6_meas9950x2_a$NA
  echo "== actors=$NA start $(date +%s)"
  python -u train_selfplay_async.py > receipts/parity_9950x/sweep2/meas_a$NA.txt 2>&1
  echo "== actors=$NA end $(date +%s) rc=$?"
  pkill -9 -f spawn_main 2>/dev/null; sleep 5
done
