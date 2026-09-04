#!/bin/bash
# 7950X Linux box environment setup (Ubuntu/Debian). Idempotent — safe to re-run.
# Provisions deps, venv, and the flycast core, then runs quick sanity gates.
# The big files (CHD, pool_league, states, demos, model zips) arrive via rsync
# from the Mac — see LINUX_BRINGUP.md. Full parity gates run after that.
set -e
echo "=== [0/4] apt dependencies ==="
sudo apt-get update -qq
sudo apt-get install -y -qq build-essential python3-venv python3-dev git tmux \
  rsync openssh-server wget unzip libsdl2-dev zlib1g-dev

echo "=== [1/4] venv ~/ps2rl (torch CPU build — no CUDA needed) ==="
[ -d ~/ps2rl ] || python3 -m venv ~/ps2rl
~/ps2rl/bin/pip install -q --upgrade pip
~/ps2rl/bin/pip install -q torch --index-url https://download.pytorch.org/whl/cpu
~/ps2rl/bin/pip install -q stable-baselines3==2.9.0 gymnasium==1.3.0 "numpy==2.4.6" opencv-python-headless

echo "=== [2/4] flycast libretro core -> ~/cores/flycast_libretro.so ==="
mkdir -p ~/cores
if [ ! -f ~/cores/flycast_libretro.so ]; then
  wget -q -O /tmp/flycast.zip https://buildbot.libretro.com/nightly/linux/x86_64/latest/flycast_libretro.so.zip
  unzip -o -q /tmp/flycast.zip -d ~/cores/
fi

echo "=== [3/4] gate G1: python imports ==="
~/ps2rl/bin/python - << 'PY'
import torch, stable_baselines3, gymnasium, numpy
print("torch", torch.__version__, "| sb3", stable_baselines3.__version__,
      "| gym", gymnasium.__version__, "| numpy", numpy.__version__)
print("G1 PASS")
PY

echo "=== [4/4] gate G2: files present ==="
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ok=1
[ -f ~/cores/flycast_libretro.so ] || { echo "MISSING core"; ok=0; }
[ -f "$HERE/../Power Stone 2 (USA).chd" ] || { echo "MISSING CHD (rsync from Mac)"; ok=0; }
[ -d "$HERE/../sdlarch-rl" ] || { echo "MISSING sdlarch-rl (git clone into repo root)"; ok=0; }
[ -f "$HERE/states/slot2.state" ] || ls "$HERE/states" >/dev/null 2>&1 || { echo "MISSING states/ (rsync from Mac)"; ok=0; }
[ -f "$HERE/powerstone_v6_leg12_league.zip" ] || { echo "MISSING model zips (rsync from Mac)"; ok=0; }
[ -d "$HERE/pool_league" ] || { echo "MISSING pool_league/ (rsync from Mac)"; ok=0; }
[ $ok -eq 1 ] && echo "G2 PASS — ready for parity gates (G3-G5, see LINUX_BRINGUP.md)" || echo "G2 INCOMPLETE — finish transfers, re-run"
