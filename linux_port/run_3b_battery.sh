#!/bin/bash
# 3A end-of-leg battery, then chain into leg 3B
cd ~/Documents/macbook_migration/linux_port
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. PYTHONUNBUFFERED=1
CORE="$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib"
GAME="../Power Stone 2 (USA).chd"
M=./powerstone_v6_bc256_spleg.zip
python eval_parity.py --core "$CORE" --game "$GAME" --slot 3 --episodes 50 --model $M > eval_leg3b_slot3_out.txt 2>&1
grep -q "GATE 4" eval_leg3b_slot3_out.txt || python eval_parity.py --core "$CORE" --game "$GAME" --slot 3 --episodes 50 --model $M > eval_leg3b_slot3_out.txt 2>&1
python eval_parity.py --core "$CORE" --game "$GAME" --slot 2 --episodes 50 --model $M > eval_leg3b_slot2_out.txt 2>&1
grep -q "GATE 4" eval_leg3b_slot2_out.txt || python eval_parity.py --core "$CORE" --game "$GAME" --slot 2 --episodes 50 --model $M > eval_leg3b_slot2_out.txt 2>&1
python -u ab_selfplay_probe.py --model $M --opp ./powerstone_v6_bc256.zip --episodes 12 > eval_leg3b_ab_vs_seed_out.txt 2>&1
grep -q "AB RESULT" eval_leg3b_ab_vs_seed_out.txt || python -u ab_selfplay_probe.py --model $M --opp ./powerstone_v6_bc256.zip --episodes 12 > eval_leg3b_ab_vs_seed_out.txt 2>&1
python -u ab_selfplay_probe.py --model $M --opp ./powerstone_v6_ppo.zip --episodes 12 > eval_leg3b_ab_vs_leg1_out.txt 2>&1
grep -q "AB RESULT" eval_leg3b_ab_vs_leg1_out.txt || python -u ab_selfplay_probe.py --model $M --opp ./powerstone_v6_ppo.zip --episodes 12 > eval_leg3b_ab_vs_leg1_out.txt 2>&1
python -u ab_selfplay_probe.py --model $M --opp ./powerstone_v6_bc256_lv8leg.zip --episodes 12 > eval_leg3b_ab_vs_3a_out.txt 2>&1
grep -q "AB RESULT" eval_leg3b_ab_vs_3a_out.txt || python -u ab_selfplay_probe.py --model $M --opp ./powerstone_v6_bc256_lv8leg.zip --episodes 12 > eval_leg3b_ab_vs_3a_out.txt 2>&1
echo DONE > claude_bridge/battery_3b_done.txt
tmux new -s ps2train -d "caffeinate -is bash ~/Documents/macbook_migration/linux_port/launch_leg3d.sh"
