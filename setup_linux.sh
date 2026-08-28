#!/bin/bash
# Power Stone 2 RL — Linux server setup (see HOWTO_LINUX_SERVER.md)
# Run from inside the copied macbook_migration/ folder:
#   bash setup_linux.sh [N_ENVS]
# Idempotent; re-run after fixing anything.
set -uo pipefail

N_ENVS="${1:-$(( $(nproc) - 2 ))}"
MIG="$(cd "$(dirname "$0")" && pwd)"
step() { printf '\n\033[1;36m== %s ==\033[0m\n' "$*"; }
fail() { printf '\033[1;31mFAIL: %s\033[0m\n' "$*"; exit 1; }

step "0. Sanity"
[ -f "$MIG/Power Stone 2 (USA).chd" ] || fail "CHD missing from $MIG"
[ -d "$MIG/sdlarch-rl" ] || fail "sdlarch-rl/ missing (copy the WHOLE folder — it carries local patches)"
[ -f "$MIG/linux_port/system/dolphin-0/vmu_save_A1.bin" ] || fail "VMU images missing (linux_port/system/dolphin-0/)"
[ -f "$MIG/linux_port/powerstone_env_v6.py" ] || echo "WARN: powerstone_env_v6.py not in linux_port/ — gates 1-3 will run, gate 4 + training will not"

step "1. apt packages (needs sudo)"
sudo apt-get update -qq && sudo apt-get install -y -qq \
  build-essential cmake pkg-config git \
  libsdl2-dev libgl1-mesa-dev xvfb \
  python3.11 python3.11-venv python3.11-dev unzip curl \
  || fail "apt install failed"

step "2. Python venv ~/ps2rl"
[ -d "$HOME/ps2rl" ] || python3.11 -m venv "$HOME/ps2rl"
source "$HOME/ps2rl/bin/activate"
python -m pip install -q --upgrade pip
pip install -q numpy "stable-baselines3<3" gymnasium torch pygame
python -c "import numpy, torch, gymnasium, stable_baselines3, pygame" || fail "python deps"
echo "python deps OK"

step "3. flycast core (linux x86_64 nightly — pin to the Mac's date if states misbehave)"
mkdir -p "$MIG/cores"
if [ ! -f "$MIG/cores/flycast_libretro.so" ]; then
  curl -fsSL https://buildbot.libretro.com/nightly/linux/x86_64/latest/flycast_libretro.so.zip \
    -o /tmp/fc.zip && unzip -o -q /tmp/fc.zip -d "$MIG/cores/" || fail "core download"
fi
echo "core: $MIG/cores/flycast_libretro.so"

step "4. Build sdlarch-rl"
cd "$MIG/sdlarch-rl"
[ -f third-party/pybind11/CMakeLists.txt ] || git submodule update --init --recursive
rm -rf build/CMakeCache.txt   # drop any cache copied from the mac
( cmake -B build -DCMAKE_BUILD_TYPE=Release \
    -DPython3_EXECUTABLE="$HOME/ps2rl/bin/python" \
    -DPython_EXECUTABLE="$HOME/ps2rl/bin/python" \
    -DPYBIND11_FINDPYTHON=ON 2>&1 \
  && cmake --build build -j 2>&1 ) | tee "$MIG/sdlarch_build_linux.log" \
  || fail "build failed — see sdlarch_build_linux.log"
[ -f _retro.so ] || fail "_retro.so not produced"

step "5. Seed per-instance VMU/system dirs (dolphin-0..$((N_ENVS-1)))"
cd "$MIG/linux_port"
for i in $(seq 0 $((N_ENVS-1))); do
  mkdir -p "system/dolphin-$i"
  cp -rn system/dolphin-0/. "system/dolphin-$i/" 2>/dev/null || true
done
echo "seeded $N_ENVS instance dirs"

step "6. Gate 1 (headless probe)"
if [ -f states/slot1.state ]; then
  SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl xvfb-run -a \
    python probe_ram.py --core ../cores/flycast_libretro.so \
    --game "../Power Stone 2 (USA).chd" --state states/slot1.state \
    || fail "gate 1 failed"
else
  SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl xvfb-run -a \
    python probe_ram.py --core ../cores/flycast_libretro.so \
    --game "../Power Stone 2 (USA).chd" \
    || fail "gate 1 failed (no states/slot1.state — attract-mode probe)"
fi

step "DONE"
cat <<EOF
Next (see HOWTO_LINUX_SERVER.md):
  gate 3:  xvfb-run -a python calibrate_buttons.py --core ../cores/flycast_libretro.so --game "../Power Stone 2 (USA).chd" --state states/slot1.state
  gate 4:  PS2_CORE=../cores/flycast_libretro.so xvfb-run -a python powerstone_env_libretro.py
  train:   mkdir -p opponent_pool && cp <checkpoints_v6 picks> opponent_pool/
           cp ../powerstone_v6_ppo_legG_27911k.zip powerstone_v6_ppo.zip
           PS2_NENVS=$N_ENVS xvfb-run -a python train_selfplay.py
EOF
