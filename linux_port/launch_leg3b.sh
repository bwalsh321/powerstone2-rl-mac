#!/bin/bash
# Leg 3B launcher — fresh bc256 seed, 1v1 self-play vs its prior self
cd ~/Documents/macbook_migration/linux_port
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. PYTHONUNBUFFERED=1
export PS2_CORE="$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib"
export PS2_WARM=./powerstone_v6_bc256.zip PS2_FRESH=1 PS2_POOL=./pool_bc256 PS2_NENVS=6
exec python -u train_selfplay.py > train_leg3b_out.txt 2>&1
