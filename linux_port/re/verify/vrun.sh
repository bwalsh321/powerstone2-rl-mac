#!/bin/bash
# usage: re/verify/vrun.sh script.py args...   (no auto-retry; rerun by hand on a boot flake)
cd /Users/blakewalsh/Documents/macbook_migration/linux_port
source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl:.:re/verify
python -u "re/verify/$@" 2>&1 | grep --line-buffered -v "ApplePersist\|Set variable\|mutex lock failed\|pygame"
