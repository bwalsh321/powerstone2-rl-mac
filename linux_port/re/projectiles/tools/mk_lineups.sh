#!/bin/bash
# Builds all-COM desert lv8 lineup states from work/cc_slot3.state (instance 4).
cd "$(dirname "$0")/../../.."
source ~/ps2rl/bin/activate; export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:.
P=re/projectiles
while read -r N C1 C2 C3 C4; do
  python $P/tools/drive.py --load $P/work/cc_slot3.state \
    --steps "$(python $P/tools/lineup.py $P/work/lineup$N $C1 $C2 $C3 $C4)" --outdir $P/shots/lineups </dev/null 2>&1 | grep "^\[dr\] s"
done <<LIST
A Pride Falcon Ryoma Accel
C Pete Julia Gourmand Mel
D Ayame Gunrock Falcon Pride
LIST
