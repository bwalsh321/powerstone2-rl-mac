#!/bin/bash
# Leg 3A launcher — fresh bc256 seed, lv8 only (LEG-3 PROGRAM leg A)
cd ~/Documents/macbook_migration/linux_port
source ~/ps2rl/bin/activate
export SDLARCH_LOG=1 SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:. PYTHONUNBUFFERED=1
export PS2_CORE="$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib"
export PS2_WARM=./powerstone_v6_bc256.zip PS2_FRESH=1 PS2_NENVS=6
exec python -u train_com.py > train_leg3a_out.txt 2>&1
