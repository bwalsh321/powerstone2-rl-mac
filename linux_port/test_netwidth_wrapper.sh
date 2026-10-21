#!/bin/bash
# test_netwidth_wrapper.sh -- exercise ONLY the league_surgery.txt loop of league_leg_async.sh (Oct 14 2026, bigger-network
# option) without ever running the wrapper itself (its retry path pkills every trainer on the machine).
#
# The ARENA-parse ... leg_modes.txt-append block is cut out of league_leg_async.sh (this tree's and, for the flag-off case,
# the parent commit's) and run in a scratch dir that holds symlinks to this tree's *.py and a read-only symlink of the warm
# zip; surgery outputs land in the scratch dir. Each case prints the exit status, PREV, PS2_WARM, the leg_modes row
# and the wrapper log lines.
#   bash test_netwidth_wrapper.sh /abs/warm_256.zip [PARENT_COMMIT]      (run from linux_port, venv active)
set -u
WARM="$1"; PARENT="${2:-45af941}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCR="${TMPDIR:-/tmp}/netwidth_wrapper_$$"; mkdir -p "$SCR"
for f in "$HERE"/*.py; do ln -sf "$f" "$SCR/"; done
LIVE_SURG="$(printf '110 lstm128\n113 joint63\n134 obsv4\n174 framestack2fold\n')"
LIVE_ENV="PS2_ZERO_SUM=1 PS2_OBS_STACK=2 PS2_OBS_V3=1 PS2_OBS_V4=1 PS2_OBS_V4_ITEMEMB=keep PS2_OBJ_GRID_N=208 PS2_PPO_KL_REF=prox"

extract() {   # $1 = wrapper text -> the surgery block as a runnable script
  printf '%s\n' "$1" | awk '/^ARENA="\$\(tr/{on=1} on{print} /^echo "\$N \$\{MODE/{exit}'
}
NEW_BLOCK="$(extract "$(cat "$HERE/league_leg_async.sh")")"
OLD_BLOCK="$(extract "$(git -C "$HERE" show "$PARENT:linux_port/league_leg_async.sh")")"

run_case() {  # name block prev_name surgery_text env_text
  local name="$1" block="$2" prev="$3" surg="$4" envt="$5"
  echo "== $name"
  ( cd "$SCR" || exit 9
    : > wrapper_league.log; : > leg_modes.txt
    printf '%s\n' "$surg" > league_surgery.txt; printf '%s\n' "$envt" > league_env.txt
    N=178 PREV="$prev" MODE=mixed ENTC="" OPTIM="PS2_LR=5e-5"
    unset PS2_WARM PS2_NET_WIDTH PS2_LSTM_HIDDEN
    eval "$block"
    echo "    -> exit 0 PREV=$PREV PS2_WARM=${PS2_WARM:-unset} NET_WIDTH=${PS2_NET_WIDTH:-unset} LSTM_HIDDEN=${PS2_LSTM_HIDDEN:-unset}"
    echo "    leg_modes: $(tail -1 leg_modes.txt | sed 's/PS2_STATE_SLOTS=[^ ]* //')"
  ) > "$SCR/case.out" 2>&1
  local st=$?
  cat "$SCR/case.out"; echo "  (status $st)"
  sed 's/^/  log| /' "$SCR/wrapper_league.log"
}

ln -sf "$WARM" "$SCR/powerstone_v6_leg177_league.zip"
P=./powerstone_v6_leg177_league.zip
run_case "f) flag off (live surgery list + live env), OLD wrapper" "$OLD_BLOCK" "$P" "$LIVE_SURG" "$LIVE_ENV"
run_case "f) flag off (live surgery list + live env), NEW wrapper" "$NEW_BLOCK" "$P" "$LIVE_SURG" "$LIVE_ENV"
run_case "b) widen512 listed but PS2_NET_WIDTH unset" "$NEW_BLOCK" "$P" "$LIVE_SURG
178 widen512" "$LIVE_ENV"
run_case "c) widen512 listed, PS2_NET_WIDTH=256" "$NEW_BLOCK" "$P" "$LIVE_SURG
178 widen512" "$LIVE_ENV PS2_NET_WIDTH=256"
run_case "e) bad kind widenx" "$NEW_BLOCK" "$P" "$LIVE_SURG
178 widenx" "$LIVE_ENV PS2_NET_WIDTH=512"
run_case "a) widen512 from leg 178, PS2_NET_WIDTH=512" "$NEW_BLOCK" "$P" "$LIVE_SURG
178 widen512" "$LIVE_ENV PS2_NET_WIDTH=512"
run_case "d) next leg: warm zip already 512 (no second surgery)" "$NEW_BLOCK" ./powerstone_v6_leg177_w512.zip "$LIVE_SURG
178 widen512" "$LIVE_ENV PS2_NET_WIDTH=512"
run_case "g) widen512 + lstm256 (both flags)" "$NEW_BLOCK" "$P" "$LIVE_SURG
178 widen512
178 lstm256" "$LIVE_ENV PS2_NET_WIDTH=512 PS2_LSTM_HIDDEN=256"
run_case "h) lstm256 listed, PS2_LSTM_HIDDEN unset" "$NEW_BLOCK" "$P" "$LIVE_SURG
178 lstm256" "$LIVE_ENV"
rm -rf "$SCR"
