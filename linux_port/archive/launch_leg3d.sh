#!/bin/bash
# Leg 3D launcher — fresh lv8-BC seed (Blake's 23-1 corpus woven in), lv8 diet
cd ~/Documents/macbook_migration/linux_port
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. PYTHONUNBUFFERED=1
export PS2_CORE="$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib"
export PS2_WARM=./powerstone_v6_bclv8_256.zip PS2_FRESH=1 PS2_NENVS=6
exec python -u train_com.py > train_leg3d_out.txt 2>&1
