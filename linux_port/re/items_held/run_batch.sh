#!/bin/bash
# sequential batch (one emulator at a time, instance 1)
cd "$(dirname "$0")"
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../../../sdlarch-rl:../..
for seed in 11 12 13 14 15 16; do
  for s in slot1 slot2 slot3; do
    for try in 1 2; do
      python probe3_holds.py states/$s.state 20000 $seed 2>&1 | grep holds && break
    done
  done
done
for seed in 21 22 23 24; do
  for s in slot2 slot3; do
    START_P=0.03 python probe3_holds.py states/$s.state 40000 $seed ${s}_st 2>&1 | grep holds
  done
done
echo BATCH_DONE
