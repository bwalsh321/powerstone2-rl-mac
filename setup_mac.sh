#!/bin/bash
# Power Stone 2 RL — M2 MacBook setup (MAC_TEST.md steps 0-3, automated)
# Run with:  bash ~/Documents/macbook_migration/setup_mac.sh
# Safe to re-run; every step is idempotent.
set -uo pipefail

MIG="$HOME/Documents/macbook_migration"
step() { printf '\n\033[1;36m== %s ==\033[0m\n' "$*"; }
fail() { printf '\033[1;31mFAIL: %s\033[0m\n' "$*"; exit 1; }

step "0a. Xcode Command Line Tools"
if xcode-select -p >/dev/null 2>&1; then
  echo "CLT present: $(xcode-select -p)"
else
  echo "Triggering the CLT installer — click Install in the dialog that pops up,"
  echo "wait for it to finish, then RE-RUN this script."
  xcode-select --install
  exit 0
fi

step "0b. Homebrew"
if ! command -v brew >/dev/null 2>&1; then
  [ -x /opt/homebrew/bin/brew ] && eval "$(/opt/homebrew/bin/brew shellenv)"
fi
command -v brew >/dev/null 2>&1 || fail "Homebrew not found. Install it from https://brew.sh (needs your password), then re-run this script."
echo "brew: $(brew --version | head -1)"

step "0c. Packages: cmake sdl2 pkg-config git python@3.11"
brew install cmake sdl2 pkg-config git python@3.11

step "0d. RetroArch"
brew list --cask retroarch >/dev/null 2>&1 || brew install --cask retroarch

step "0e. Python venv ~/ps2rl + RL deps"
[ -d "$HOME/ps2rl" ] || python3.11 -m venv "$HOME/ps2rl"
source "$HOME/ps2rl/bin/activate"
python -m pip install -q --upgrade pip
pip install numpy "stable-baselines3<3" gymnasium torch
python - <<'EOF'
import numpy, torch, gymnasium, stable_baselines3 as sb3
print(f"OK: numpy {numpy.__version__} | torch {torch.__version__} (MPS available: {torch.backends.mps.is_available()}) | gymnasium {gymnasium.__version__} | sb3 {sb3.__version__}")
EOF

step "1. Clone sdlarch-rl (into the migration folder so Claude can patch it)"
cd "$MIG"
[ -d sdlarch-rl ] || git clone https://github.com/paulo101977/sdlarch-rl.git
cd sdlarch-rl
git submodule update --init --recursive   # third-party/pybind11 lives here

step "2. Build sdlarch-rl (macOS failures are EXPECTED here — Claude patches, you re-run)"
# Point cmake at the venv python so the module imports in ~/ps2rl (not brew's 3.13)
VENV_PY="$HOME/ps2rl/bin/python"
rm -f build/CMakeCache.txt   # drop any stale configure (e.g. the python 3.13 one)
if ( cmake -B build -DCMAKE_BUILD_TYPE=Release \
       -DPython3_EXECUTABLE="$VENV_PY" \
       -DPython_EXECUTABLE="$VENV_PY" \
       -DPYBIND11_FINDPYTHON=ON 2>&1 \
     && cmake --build build 2>&1 ) | tee "$MIG/sdlarch_build.log"; then
  echo
  echo ">>> BUILD OK"
else
  echo
  echo ">>> BUILD FAILED — full log saved to $MIG/sdlarch_build.log."
  echo ">>> Claude reads that log from the folder; wait for the patch, then re-run this script."
fi

step "DONE"
echo "Next: open RetroArch once (Claude drives the core download + HLE BIOS option from there)."
