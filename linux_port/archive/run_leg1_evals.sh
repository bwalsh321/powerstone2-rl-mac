#!/bin/zsh
source ~/ps2rl/bin/activate
cd ~/Documents/macbook_migration/linux_port
export SDL_AUDIODRIVER=dummy PYTHONUNBUFFERED=1 PYTHONPATH=../sdlarch-rl:.
CORE="$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib"
python -u ab_selfplay_probe.py --model powerstone_v6_ppo_selfplay_leg1.zip \
  --opp opponent_pool/ps_v6_27911619_steps.zip --episodes 12 > ab_leg1_vs_legG.txt 2>&1
python -u ab_selfplay_probe.py --model powerstone_v6_ppo_selfplay_leg1.zip \
  --opp opponent_pool/ps_v6_31915459_steps.zip --episodes 12 > ab_leg1_vs_31M.txt 2>&1
python -u eval_parity.py --core "$CORE" --game "../Power Stone 2 (USA).chd" \
  --model powerstone_v6_ppo_selfplay_leg1.zip --slot 2 --episodes 50 > parity_leg1_out.txt 2>&1
echo "ALL EVALS DONE"
