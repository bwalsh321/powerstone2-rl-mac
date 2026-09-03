#!/bin/bash
# Battery for the just-finished league leg, then advance state + launch next.
cd ~/Documents/macbook_migration/linux_port
read N PREV < league_state.txt
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. PYTHONUNBUFFERED=1
CORE="$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib"
GAME="../Power Stone 2 (USA).chd"
M=./powerstone_v6_leg${N}_league.zip
python eval_parity.py --core "$CORE" --game "$GAME" --slot 3 --episodes 50 --model $M > eval_leg${N}_slot3_out.txt 2>&1
grep -q "GATE 4" eval_leg${N}_slot3_out.txt || python eval_parity.py --core "$CORE" --game "$GAME" --slot 3 --episodes 50 --model $M > eval_leg${N}_slot3_out.txt 2>&1
python eval_parity.py --core "$CORE" --game "$GAME" --slot 2 --episodes 50 --model $M > eval_leg${N}_slot2_out.txt 2>&1
grep -q "GATE 4" eval_leg${N}_slot2_out.txt || python eval_parity.py --core "$CORE" --game "$GAME" --slot 2 --episodes 50 --model $M > eval_leg${N}_slot2_out.txt 2>&1
python -u ab_selfplay_probe.py --model $M --opp $PREV --episodes 12 > eval_leg${N}_ab_vs_prev_out.txt 2>&1
grep -q "AB RESULT" eval_leg${N}_ab_vs_prev_out.txt || python -u ab_selfplay_probe.py --model $M --opp $PREV --episodes 12 > eval_leg${N}_ab_vs_prev_out.txt 2>&1
python -u ab_selfplay_probe.py --model $M --opp ./powerstone_v6_ppo.zip --episodes 12 > eval_leg${N}_ab_vs_leg1_out.txt 2>&1
grep -q "AB RESULT" eval_leg${N}_ab_vs_leg1_out.txt || python -u ab_selfplay_probe.py --model $M --opp ./powerstone_v6_ppo.zip --episodes 12 > eval_leg${N}_ab_vs_leg1_out.txt 2>&1
# Sep 2 one-time repairs: leg 4's final never entered the league (its battery
# script predated the cp line); backfill idempotently.
[ -f pool_league/prog_leg4.zip ] || cp ./powerstone_v6_leg4_league.zip pool_league/prog_leg4.zip
cp $M pool_league/prog_leg${N}.zip
NEXT=$((N+1))
echo "$NEXT $M" > league_state.txt
echo DONE > claude_bridge/battery_leg${N}_done.txt
tmux new -s ps2train -d "caffeinate -is bash ~/Documents/macbook_migration/linux_port/league_leg.sh"
