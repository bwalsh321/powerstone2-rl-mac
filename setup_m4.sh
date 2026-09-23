#!/bin/bash
# M4 MacBook setup for the Power Stone 2 RL league (macOS -> macOS move, Sep 12 2026).
# Run from inside the unzipped macbook_migration folder:  bash setup_m4.sh
set -e
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== [1/4] Homebrew deps (python 3.11 + tmux) ==="
command -v brew >/dev/null || { echo "Install Homebrew first: https://brew.sh"; exit 1; }
brew list python@3.11 >/dev/null 2>&1 || brew install python@3.11
command -v tmux >/dev/null || brew install tmux

echo "=== [2/4] venv ~/ps2rl from requirements.txt ==="
[ -d ~/ps2rl ] || /opt/homebrew/bin/python3.11 -m venv ~/ps2rl
~/ps2rl/bin/pip install -q --upgrade pip
~/ps2rl/bin/pip install -q -r "$HERE/requirements.txt"

echo "=== [3/4] flycast core -> RetroArch cores dir (arm64 dylib, same as M2) ==="
CORE_DIR="$HOME/Library/Application Support/RetroArch/cores"
mkdir -p "$CORE_DIR"
cp -n "$HERE/cores/flycast_libretro.dylib" "$CORE_DIR/" 2>/dev/null || true
ls -la "$CORE_DIR/flycast_libretro.dylib"

echo "=== [3b/4] native binaries: quarantine + signature + rpath + SDL2 (M4 bring-up, Sep 11) ==="
# Files that arrive via a browser download carry com.apple.quarantine, and
# macOS then refuses to dlopen the M2-signed _retro.so ("library load
# disallowed by system policy"). Strip the flag, re-sign ad-hoc locally.
xattr -dr com.apple.quarantine "$HERE" 2>/dev/null || true
xattr -d com.apple.quarantine "$CORE_DIR/flycast_libretro.dylib" 2>/dev/null || true
# _retro.so finds libpcsx2_headless.dylib via an rpath baked in on the M2
# (/Users/blakewalsh/...). Add this checkout's sdlarch-rl dir as an rpath.
if ! otool -l "$HERE/sdlarch-rl/_retro.so" | grep -q "path $HERE/sdlarch-rl "; then
  install_name_tool -add_rpath "$HERE/sdlarch-rl" "$HERE/sdlarch-rl/_retro.so" 2>/dev/null || true
fi
codesign -s - -f "$HERE/sdlarch-rl/_retro.so" "$HERE/sdlarch-rl/libpcsx2_headless.dylib" \
  "$HERE/cores/flycast_libretro.dylib" "$CORE_DIR/flycast_libretro.dylib" 2>&1 | grep -v "replacing existing" || true
# _retro.so links Homebrew's sdl2-compat (libSDL2-2.0.0.dylib).
brew list sdl2-compat >/dev/null 2>&1 || brew install sdl2-compat

echo "=== [4/4] sanity: imports + files ==="
PYTHONPATH="$HERE/sdlarch-rl" ~/ps2rl/bin/python - << 'PY'
import torch, stable_baselines3, gymnasium, gym, shimmy, numpy
import _retro   # the built harness must dlopen (quarantine/rpath/SDL2 — step 3b)
print("torch", torch.__version__, "| sb3", stable_baselines3.__version__,
      "| gym(old)", gym.__version__, "| numpy", numpy.__version__)
print("G1 PASS")
PY
ok=1
[ -f "$HERE/Power Stone 2 (USA).chd" ] || { echo "MISSING CHD"; ok=0; }
[ -d "$HERE/sdlarch-rl" ] || { echo "MISSING sdlarch-rl"; ok=0; }
[ -f "$HERE/linux_port/states/slot2.state" ] || { echo "MISSING states"; ok=0; }
[ -d "$HERE/linux_port/pool_league" ] || { echo "MISSING pool_league"; ok=0; }
for i in 1 2 3 4 5 6 7 8 9 10 11 12 13; do   # per-instance VMU/system dirs (core reads system/dolphin-<id>)
  [ -d "$HERE/linux_port/system/dolphin-$i" ] || { mkdir -p "$HERE/linux_port/system/dolphin-$i"; cp -Rn "$HERE/linux_port/system/dolphin-0/." "$HERE/linux_port/system/dolphin-$i/"; }
done
[ -f "$HERE/linux_port/league_state.txt" ] && cat "$HERE/linux_port/league_state.txt"
[ $ok -eq 1 ] && echo "G2 PASS — see M4_SETUP.md for the parity gate (G3) and resume" || echo "G2 INCOMPLETE"
