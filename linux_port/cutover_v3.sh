#!/bin/bash
# cutover_v3.sh <N> — launch leg N as the FIRST obs v3 leg (Sep 23 2026, Blake: "Go").
# Preconditions: leg N-1 finished and its battery ran with the launch HELD (league_trainer.txt = hold,
# claude_bridge/leg<N>_LAUNCH_HELD.txt present), league_state.txt = "<N> ./powerstone_v6_leg<N-1>_league.zip",
# no trainer alive. Steps: widen leg N-1's zip (122 -> 160 per frame, zero columns), prove equivalence on
# live frames, run the unit tests, point league_state.txt at the widened zip, add PS2_OBS_V3=1 to
# league_env.txt, set mixed, launch, verify the boot. Every check aborts before touching the relay files.
set -u
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
N="$1"; P=$((N-1))
read SN SZ < league_state.txt
[ "$SN" = "$N" ] || { echo "state says leg $SN, not $N; abort"; exit 1; }
[ "$SZ" = "./powerstone_v6_leg${P}_league.zip" ] || { echo "state zip $SZ is not leg $P; abort"; exit 1; }
[ "$(tr -d '[:space:]' < league_trainer.txt)" = "hold" ] || { echo "league_trainer.txt is not hold; abort"; exit 1; }
[ -e "claude_bridge/leg${N}_LAUNCH_HELD.txt" ] || { echo "no leg${N}_LAUNCH_HELD marker; abort"; exit 1; }
pgrep -f 'train_selfplay_asyn[c]' >/dev/null && { echo "a trainer is alive; abort"; exit 1; }
tmux has-session -t ps2train 2>/dev/null && { echo "tmux ps2train exists; abort"; exit 1; }
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl/p4:. PYTHONUNBUFFERED=1 PS2_OBS_V2=1 PS2_OBS_V3=1
V3="./powerstone_v6_leg${P}_v3.zip"
python surgery_widen.py "$SZ" "$V3" | tail -1 || { echo "surgery failed; abort"; exit 1; }
python test_obs_v3.py 2>&1 | tail -1 | grep -q "0 failures" || { echo "unit test failed; abort"; exit 1; }
python equivalence_widen.py "$SZ" "$V3" --frames 600 --instance 12 2>&1 | grep -E "^widen equivalence|^PASS|^FAIL" | tee claude_bridge/cutover_v3_leg${N}_equivalence.txt
grep -q "^PASS" claude_bridge/cutover_v3_leg${N}_equivalence.txt || { echo "equivalence FAIL; abort"; exit 1; }
grep -q "PS2_OBS_V3=1" league_env.txt || { printf '%s PS2_OBS_V3=1\n' "$(tr -d '\n' < league_env.txt)" > league_env.txt; }
echo "$N $V3" > league_state.txt.tmp && mv league_state.txt.tmp league_state.txt
echo mixed > league_trainer.txt
echo "cutover: state=[$(cat league_state.txt)] env=[$(cat league_env.txt)]"
tmux new -s ps2train -d "caffeinate -is bash $(pwd)/league_leg_async.sh" || { echo "tmux launch failed"; exit 2; }
sleep 150
grep '\[config\]' "train_leg${N}_out.txt" | grep -o "obs_stack=[0-9]*\|obs_v3=[01] obs_dim=[0-9]*\|warm=[^ ]*" | tr '\n' ' '; echo
echo "actors: $(pgrep -f 'spawn_mai[n]' | wc -l | tr -d ' ')"
tail -1 leg_modes.txt
