#!/bin/bash
# setup_9950x.sh — ONE-SHOT bring-up of the Power Stone 2 RL league on a fresh Ubuntu box
# (written Sep 24 2026 for Blake's Ryzen 9950X; NOT yet run on real Linux hardware — the first run
# on the box is the test). Idempotent: re-run after fixing anything.
#
#   git clone https://github.com/bwalsh321/powerstone2-rl-mac.git ~/macbook_migration
#   cd ~/macbook_migration && bash linux_port/setup_9950x.sh [N_INSTANCES]
#
# Then rsync the runtime files from the Mac (section 7 prints the exact list) and run the gates
# (section 8). Nothing here touches training or the Mac.
set -uo pipefail
N_INST="${1:-14}"                       # emulator instances to seed: 10 actors + 11 scout + 12/13 probes
MIG="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
step() { printf '\n\033[1;36m== %s ==\033[0m\n' "$*"; }
fail() { printf '\033[1;31mFAIL: %s\033[0m\n' "$*"; exit 1; }
PYBIND11_TAG="v3.0.1"                    # the version vendored on the Mac

step "1. apt packages (sudo)"
sudo apt-get update -qq
sudo apt-get install -y -qq build-essential cmake pkg-config git tmux rsync openssh-server wget curl unzip \
  libsdl2-dev libgl1-mesa-dev libegl1-mesa-dev mesa-utils xvfb zlib1g-dev ffmpeg \
  software-properties-common || fail "apt install"
if ! command -v python3.11 >/dev/null; then
  echo "python3.11 not present: adding deadsnakes PPA (Ubuntu 24.04 ships 3.12; the pinned wheels target 3.11)"
  sudo add-apt-repository -y ppa:deadsnakes/ppa && sudo apt-get update -qq
fi
sudo apt-get install -y -qq python3.11 python3.11-venv python3.11-dev || fail "python3.11"

step "2. venv ~/ps2rl (torch CPU wheel + requirements.txt + pillow/imageio-ffmpeg)"
[ -d "$HOME/ps2rl" ] || python3.11 -m venv "$HOME/ps2rl"
"$HOME/ps2rl/bin/pip" install -q --upgrade pip
"$HOME/ps2rl/bin/pip" install -q "torch==2.13.0" --index-url https://download.pytorch.org/whl/cpu || fail "torch"
"$HOME/ps2rl/bin/pip" install -q -r "$MIG/requirements.txt" || fail "requirements"
"$HOME/ps2rl/bin/python" -c "import torch, stable_baselines3, gymnasium, numpy, gym, shimmy, pygame, PIL, imageio_ffmpeg; print('G1 imports OK', torch.__version__, stable_baselines3.__version__)" || fail "G1 imports"

step "3. flycast libretro core -> ~/cores/flycast_libretro.so"
mkdir -p "$HOME/cores"
if [ ! -f "$HOME/cores/flycast_libretro.so" ]; then
  wget -q -O /tmp/flycast.zip https://buildbot.libretro.com/nightly/linux/x86_64/latest/flycast_libretro.so.zip \
    && unzip -o -q /tmp/flycast.zip -d "$HOME/cores/" || fail "core download"
fi
ls -la "$HOME/cores/flycast_libretro.so"

step "4. pybind11 $PYBIND11_TAG into sdlarch-rl/third-party (gitignored; the submodule link is NOT in this repo)"
cd "$MIG/sdlarch-rl"
if [ ! -f third-party/pybind11/CMakeLists.txt ]; then
  mkdir -p third-party
  git clone -q --depth 1 --branch "$PYBIND11_TAG" https://github.com/pybind/pybind11 third-party/pybind11 || fail "pybind11 clone"
fi

step "5. build the harness TWICE: 2-port (repo root) and 4-port (sdlarch-rl/p4/, what the league uses)"
PY="$HOME/ps2rl/bin/python"
rm -f build/CMakeCache.txt build_p4/CMakeCache.txt
( cmake -B build -DCMAKE_BUILD_TYPE=Release -DPython3_EXECUTABLE="$PY" -DPython_EXECUTABLE="$PY" -DPYBIND11_FINDPYTHON=ON \
    -DSDLARCH_COPY_TO_ROOT=ON && cmake --build build -j"$(nproc)" ) > "$MIG/sdlarch_build_2port.log" 2>&1 \
  || fail "2-port build; see sdlarch_build_2port.log"
[ -f _retro.so ] || fail "_retro.so (2-port) not in sdlarch-rl/"
( cmake -B build_p4 -DCMAKE_BUILD_TYPE=Release -DPython3_EXECUTABLE="$PY" -DPython_EXECUTABLE="$PY" -DPYBIND11_FINDPYTHON=ON \
    -DSDLARCH_COPY_TO_ROOT=OFF -DCMAKE_CXX_FLAGS="-DSDLARCH_MAX_PLAYERS=4" -DCMAKE_C_FLAGS="-DSDLARCH_MAX_PLAYERS=4" \
    && cmake --build build_p4 -j"$(nproc)" ) > "$MIG/sdlarch_build_4port.log" 2>&1 \
  || fail "4-port build; see sdlarch_build_4port.log"
mkdir -p p4
P4_SO="$(find build_p4 -name '_retro*.so' | head -1)"; P4_LIB="$(find build_p4 -name 'libpcsx2_headless*' | head -1)"
[ -n "$P4_SO" ] && [ -n "$P4_LIB" ] || fail "4-port artifacts not found under build_p4/"
cp -f "$P4_SO" p4/_retro.so && cp -f "$P4_LIB" p4/ && echo "p4/: $(ls p4)"
# the module must find libpcsx2_headless next to itself (M4_SETUP.md rpath trap): check both builds import
cd "$MIG/linux_port"
SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl xvfb-run -a "$PY" -c "import _retro; print('2-port _retro import OK')" || fail "2-port import"
SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl xvfb-run -a "$PY" -c "import _retro, os; print('4-port _retro import OK from', os.path.dirname(_retro.__file__))" || fail "4-port import"

step "6. seed per-instance system dirs (system/dolphin-0..$((N_INST-1)); dolphin-0 arrives via rsync)"
if [ -d system/dolphin-0 ]; then
  for i in $(seq 1 $((N_INST-1))); do mkdir -p "system/dolphin-$i"; cp -rn system/dolphin-0/. "system/dolphin-$i/" 2>/dev/null || true; done
  echo "seeded $N_INST instance dirs"
else
  echo "system/dolphin-0 not here yet: rsync it, then re-run this script (section 6 only needs it)"
fi

step "7. runtime files that are NOT in git (rsync from the Mac; ~4.7 GB minimum)"
cat <<TXT
  From the Mac (user Apple), into $MIG:
    rsync -av --progress Apple@<mac>:"~/Downloads/macbook_migration/Power\ Stone\ 2\ \(USA\).chd" "$MIG/"
    rsync -av --progress Apple@<mac>:~/Downloads/macbook_migration/linux_port/{states,states_mixed,system,pool_league} "$MIG/linux_port/"
    rsync -av --progress Apple@<mac>:~/Downloads/macbook_migration/linux_port/receipts/ "$MIG/linux_port/receipts/"   # optional, for parity comparisons
  Model zips (linux_port/*.zip) are tracked in git; videos/ and demos are optional.
TXT
missing=0
for f in "$MIG/Power Stone 2 (USA).chd" states/slot3.state states_mixed/slot0.state system/dolphin-0 pool_league powerstone_v6_ppo.zip powerstone_v6_leg73_league.zip; do
  [ -e "$f" ] || { echo "  MISSING: $f"; missing=1; }
done
[ $missing -eq 0 ] && echo "  all runtime files present" || echo "  finish the rsync, then run the gates below"

step "8. gates to run BEFORE any training moves here (each under xvfb-run; never SDL_VIDEODRIVER=dummy)"
cat <<TXT
  export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl/p4:. PS2_OBS_V2=1 PS2_CORE=\$HOME/cores/flycast_libretro.so
  source ~/ps2rl/bin/activate; cd $MIG/linux_port
  G3 headless probe:   xvfb-run -a python probe_ram.py --core \$PS2_CORE --game "../Power Stone 2 (USA).chd" --state states/slot3.state
  G4 unit tests:       PS2_OBS_V3=1 python test_obs_v3.py && python test_obs_context.py
  G5 PARITY (the gate): xvfb-run -a python eval_parity.py --core \$PS2_CORE --game "../Power Stone 2 (USA).chd" --slot 3 \\
                          --model powerstone_v6_leg73_league.zip --episodes 100 --instance 12
       PASS = its win% lies inside the Mac's n=500 Wilson interval for the same zip (leg 73: 29.2%, [25, 33]).
       Repeat with --slot 2 (Mac: 97.2%, [94, 99]). Only after both pass does the league move (HANDOFF top block).
  Speed check:          time the G5 run; the Mac does 50 lv8 episodes per shard in ~15 min with 10 shards.
TXT
step "DONE"
