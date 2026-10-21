#!/bin/bash
# test_entcoef_wrapper.sh -- exercise ONLY the league_entcoef.txt / league_optim.txt parsing of league_leg_async.sh (Oct 17
# 2026, PS2_ENT_COEF pass-through) without ever running the wrapper itself (its retry path pkills every trainer on the
# machine). The block from `ENTC="$(tr ...league_entcoef.txt` through the end of the `for kv in $OPTIM` loop is cut out of
# this tree's wrapper and the parent commit's, then run in a scratch dir with a scratch league_optim.txt /
# league_entcoef.txt; each case prints the exit status, the exported optimizer variables, the leg_modes row the wrapper
# would append (same echo as the wrapper, ARENA stubbed) and the wrapper log. Flag-absent cases must print the same text
# under OLD and NEW (checked with diff at the end).
#   bash test_entcoef_wrapper.sh [PARENT_COMMIT]          (run from linux_port; no Python, no emulator)
set -u
PARENT="${1:-b709911}"
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCR="${TMPDIR:-/tmp}/entcoef_wrapper_$$"; mkdir -p "$SCR"
extract() {   # wrapper text -> the ENTC + OPTIM block, then the wrapper's own leg_modes echo
  printf '%s\n' "$1" | awk '/^ENTC="\$\(tr/{on=1} on{print} on && (/^esac; done$/ || (/^for kv in \$OPTIM/ && /done$/)){exit}'
  printf '%s\n' "$1" | grep -m1 '^echo "\$N \${MODE' 
}
NEW_BLOCK="$(extract "$(cat "$HERE/league_leg_async.sh")")"
OLD_BLOCK="$(extract "$(git -C "$HERE" show "$PARENT:linux_port/league_leg_async.sh")")"
LIVE_OPTIM="PS2_LR=2.5e-5 PS2_TARGET_KL=0.03 PS2_BATCH_SIZE=256"

run_case() {  # name block optim_text|__ABSENT__ entcoef_text|__ABSENT__
  local name="$1" block="$2" optim="$3" entc="$4"
  echo "== $name"
  ( cd "$SCR" || exit 9
    rm -f league_optim.txt league_entcoef.txt; : > wrapper_league.log; : > leg_modes.txt
    [ "$optim" = __ABSENT__ ] || printf '%s\n' "$optim" > league_optim.txt
    [ "$entc" = __ABSENT__ ] || printf '%s\n' "$entc" > league_entcoef.txt
    unset PS2_LR PS2_BATCH_SIZE PS2_TARGET_KL PS2_ENT_COEF
    N=196 MODE=mixed ARENA="PS2_ZERO_SUM=1 RECURRENT=lstm128"
    eval "$block"
    echo "    -> exit 0 LR=${PS2_LR:-unset} BATCH=${PS2_BATCH_SIZE:-unset} KL=${PS2_TARGET_KL:-unset} ENT_COEF=${PS2_ENT_COEF:-unset}"
    echo "    leg_modes: $(tail -1 leg_modes.txt)"
  ) > "$SCR/case.out" 2>&1
  local st=$?
  cat "$SCR/case.out"; echo "  (status $st)"
  sed 's/^/  log| /' "$SCR/wrapper_league.log"
}

both() {      # flag-absent case under OLD and NEW, then diff
  # bash's own "line N:" in a missing-file message is the eval'd block's line number, not output: normalised
  run_case "$1 [OLD]" "$OLD_BLOCK" "$2" "$3" | sed 's/ \[OLD\]//; s/: line [0-9]*:/: line N:/' > "$SCR/old.txt"
  run_case "$1 [NEW]" "$NEW_BLOCK" "$2" "$3" | sed 's/ \[NEW\]//; s/: line [0-9]*:/: line N:/' > "$SCR/new.txt"
  cat "$SCR/new.txt"
  if diff -q "$SCR/old.txt" "$SCR/new.txt" >/dev/null; then echo "  IDENTICAL old vs new"; else echo "  DIFFERS old vs new:"; diff "$SCR/old.txt" "$SCR/new.txt"; fi
}

both "a) flag absent: live league_optim.txt, no league_entcoef.txt" "$LIVE_OPTIM" __ABSENT__
both "b) flag absent: no league_optim.txt at all" __ABSENT__ __ABSENT__
both "c) flag absent: empty league_optim.txt" "" __ABSENT__
both "d) flag absent: live optim + league_entcoef.txt 0.02 (old Sep 16 path)" "$LIVE_OPTIM" "0.02"
both "e) flag absent: unknown override still ignored" "$LIVE_OPTIM PS2_GAMMA=0.99" __ABSENT__
run_case "f) PS2_ENT_COEF=0.005 in league_optim.txt" "$NEW_BLOCK" "$LIVE_OPTIM PS2_ENT_COEF=0.005" __ABSENT__
run_case "g) PS2_ENT_COEF=5e-3 first, multi-line file" "$NEW_BLOCK" "PS2_ENT_COEF=5e-3
$LIVE_OPTIM" __ABSENT__
run_case "h) optim PS2_ENT_COEF beats league_entcoef.txt" "$NEW_BLOCK" "$LIVE_OPTIM PS2_ENT_COEF=0.005" "0.02"
run_case "i) bad value PS2_ENT_COEF=0.0.5 refuses" "$NEW_BLOCK" "$LIVE_OPTIM PS2_ENT_COEF=0.0.5" __ABSENT__
run_case "j) bad value PS2_ENT_COEF= (empty) refuses" "$NEW_BLOCK" "$LIVE_OPTIM PS2_ENT_COEF=" __ABSENT__
run_case "k) OLD wrapper with PS2_ENT_COEF=0.005 (the bug: ignored)" "$OLD_BLOCK" "$LIVE_OPTIM PS2_ENT_COEF=0.005" __ABSENT__
rm -rf "$SCR"
