#!/bin/bash
# usage: ./run.sh script.py [args]  -- runs headless with boot-flake retry, writes out_<script>.log
cd "$(dirname "$0")"
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy
log="out_$(basename "$1" .py).log"
for i in 1 2 3 4; do
  python -u "$@" > "$log" 2>&1
  if grep -q "^DONE" "$log"; then break; fi
  echo "retry $i" >&2
done
grep -v "^Set variable\|pygame\|savedState\|mutex lock failed" "$log"
