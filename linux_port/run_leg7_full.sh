#!/bin/bash
# Leg 7 battery + 50-ep crown probe (before leg 8, per Sep 2 review), then leg 8.
cd ~/Documents/macbook_migration/linux_port
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. PYTHONUNBUFFERED=1
CORE="$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib"
GAME="../Power Stone 2 (USA).chd"
M=./powerstone_v6_leg7_league.zip
PREV=./powerstone_v6_leg6_league.zip
python eval_parity.py --core "$CORE" --game "$GAME" --slot 3 --episodes 50 --model $M > eval_leg7_slot3_out.txt 2>&1
grep -q "GATE 4" eval_leg7_slot3_out.txt || python eval_parity.py --core "$CORE" --game "$GAME" --slot 3 --episodes 50 --model $M > eval_leg7_slot3_out.txt 2>&1
python eval_parity.py --core "$CORE" --game "$GAME" --slot 2 --episodes 50 --model $M > eval_leg7_slot2_out.txt 2>&1
grep -q "GATE 4" eval_leg7_slot2_out.txt || python eval_parity.py --core "$CORE" --game "$GAME" --slot 2 --episodes 50 --model $M > eval_leg7_slot2_out.txt 2>&1
python -u ab_selfplay_probe.py --model $M --opp $PREV --episodes 12 > eval_leg7_ab_vs_prev_out.txt 2>&1
grep -q "AB RESULT" eval_leg7_ab_vs_prev_out.txt || python -u ab_selfplay_probe.py --model $M --opp $PREV --episodes 12 > eval_leg7_ab_vs_prev_out.txt 2>&1
# THE CROWN PROBE at real sample size: leg 6 vs leg1, n=50
python -u ab_selfplay_probe.py --model ./powerstone_v6_leg6_league.zip --opp ./powerstone_v6_ppo.zip --episodes 50 > eval_leg6_ab_vs_leg1_50ep_out.txt 2>&1
grep -q "AB RESULT" eval_leg6_ab_vs_leg1_50ep_out.txt || python -u ab_selfplay_probe.py --model ./powerstone_v6_leg6_league.zip --opp ./powerstone_v6_ppo.zip --episodes 50 > eval_leg6_ab_vs_leg1_50ep_out.txt 2>&1
# pool maintenance: leg4 backfill + leg7 final in
[ -f pool_league/prog_leg4.zip ] || cp ./powerstone_v6_leg4_league.zip pool_league/prog_leg4.zip
cp $M pool_league/prog_leg7.zip
echo "8 $M" > league_state.txt
echo DONE > claude_bridge/battery_leg7_done.txt
tmux new -s ps2train -d "caffeinate -is bash ~/Documents/macbook_migration/linux_port/league_leg.sh"
