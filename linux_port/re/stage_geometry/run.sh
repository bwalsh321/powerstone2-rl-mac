#!/bin/bash
# usage: ./run.sh script.py [args] -- headless, boot-flake retry, log -> out/<script>.log
cd "$(dirname "$0")"
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../../../sdlarch-rl:../..
log="out/$(basename "$1" .py).log"
for i in 1 2 3 4; do
  python -u "$@" > "$log" 2>&1
  if grep -q "^DONE" "$log"; then break; fi
  echo "retry $i" >&2
done
grep -v "^Set variable\|pygame\|savedState\|mutex lock failed\|^Hello from" "$log"
