#!/bin/bash
# all-stage random walks (sequential: one emulator at a time, instance 5)
cd "$(dirname "$0")"
for s in desert bluesky darkcastle tomb iceberg spacestation pharaoh chaos; do
  ./run.sh s15_random_walk.py $s walk_$s 60000 7 | grep -v "^$"
done
echo ALLDONE
