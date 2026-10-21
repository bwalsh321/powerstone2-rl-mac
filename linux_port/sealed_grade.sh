#!/bin/bash
# sealed_grade.sh <N> -- SEALED-set grade of leg N (Oct 17 2026, audit item 4: "one sealed test set for 60+ legs of
# decisions"). Every keep/revert since leg ~130 has been judged on the same five held-out lineups (states/slot90-94);
# picking by one test set slowly overfits to it. This is the SECOND, sealed set: five new three-lv8-COM lineups that
# no training slot or held-out slot shares, three on Desert and two on stages the bot has never trained on
# (states/slot95-99, lineups in states_3com_lv8/lineups.json):
#   95 Jack / Accel / Wang-Tang  Desert        98 Ryoma / Gunrock / Wang-Tang  Blue Sky
#   96 Mel / Falcon / Ayame      Desert        99 Pride / Galuda / Accel       Dark Castle
#   97 Gourmand / Pete / Rouge   Desert
# (P1 / P3 / P4 COM at level 8, P2 = our Falcon.) Note: obs v4's stage-geometry block is Desert-only, so on 98/99 it
# reads zero; read the per-slot line, and the Desert three (95-97) on their own, before comparing with lv8mix.
#
# USE RARELY: only to confirm a big claim (a new record, "we broke 80"), never to pick between legs. It is NOT run by
# league_battery.sh or any relay script, and training refuses slots 90-99 (train_selfplay_async.py, drill guards).
#
# Sampled moves (--stochastic, like the per-leg lv8mix grade), 500 rounds = 10 shards x 50 (100 per lineup), paired
# pre-roll (the k-th visit to a lineup gets the same start point every leg), instances 90-99 (relay: 20-59 actors and
# grading; side grades 50-65), nice 15. The leg's eval contract (obs stack, grid, v3/v4, taps) is read from its
# leg_modes.txt row like top_grade.sh. Writes receipts/sealed/eval_leg<N>_sealed_out.txt (shards in receipts/shards/).
#   PS2_SEALED_PAR=<k>   at most k shards (emulators) at once (default 10 = all; use 4 beside a busy relay)
#   PS2_SEALED_MODEL=<zip>  grade this zip instead of ./powerstone_v6_leg<N>_league.zip (contract still from row N)
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
N=$1; [ -n "$N" ] || { echo "usage: sealed_grade.sh <leg>" >&2; exit 2; }
M="${PS2_SEALED_MODEL:-./powerstone_v6_leg${N}_league.zip}"
[ -s "$M" ] || { echo "sealed_grade: no model $M" >&2; exit 2; }
SLOTS=95,96,97,98,99
for s in ${SLOTS//,/ }; do [ -s "states/slot${s}.state" ] || { echo "sealed_grade: missing states/slot${s}.state" >&2; exit 2; }; done
ROW="$(awk -v n="$N" '$1==n' leg_modes.txt 2>/dev/null)"
[ -n "$ROW" ] || { echo "sealed_grade: no leg_modes.txt row for leg $N (its eval contract is unknown)" >&2; exit 2; }
source ~/ps2rl/bin/activate
source ./linux_gpu_env.sh
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:. PYTHONUNBUFFERED=1 PS2_OBS_V2=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1
unset PS2_OBS_V3 PS2_BUTTON_TAP PS2_OBJ_GRID_N PS2_OBS_V4 PS2_OBS_V4_ITEMEMB PS2_OBS_STACK PS2_PREROLL
# the leg's eval contract, as in top_grade.sh / scout_leg.sh
echo "$ROW" | grep -q "PS2_OBS_V3=1" && export PS2_OBS_V3=1
echo "$ROW" | grep -q "PS2_BUTTON_TAP=1" && export PS2_BUTTON_TAP=1
G="$(echo "$ROW" | grep -o "PS2_OBJ_GRID_N=[0-9]*" | head -1)"; [ -n "$G" ] && export "$G"
if echo "$ROW" | grep -q "PS2_OBS_V4=1"; then export PS2_OBS_V4=1
  E="$(echo "$ROW" | grep -o "PS2_OBS_V4_ITEMEMB=[a-z]*" | head -1)"; [ -n "$E" ] && export "$E"; fi
K="$(echo "$ROW" | grep -o "PS2_OBS_STACK=[0-9]*" | head -1)"; [ -n "$K" ] && export "$K"
CORE="${PS2_CORE:-$HOME/cores/flycast_libretro.so}"; GAME="../Power Stone 2 (USA).chd"
SHARDS=10; PER=50; BASE=90
export PS2_EVAL_INSTANCE_BASE=$BASE PS2_EVAL_TOTAL=$((SHARDS * PER))
PAR="${PS2_SEALED_PAR:-10}"
mkdir -p receipts/sealed receipts/shards
LOCK=receipts/sealed/.lock
mkdir "$LOCK" 2>/dev/null || { echo "sealed_grade: another sealed grade holds $LOCK (instances $BASE-$((BASE + SHARDS - 1)))" >&2; exit 3; }
trap 'rmdir "$LOCK" 2>/dev/null' EXIT
echo "sealed_grade leg $N: $M, slots $SLOTS, $SHARDS x $PER sampled, instances $BASE-$((BASE + SHARDS - 1)), par $PAR, $(date)"
echo "  contract: OBS_V3=${PS2_OBS_V3:-0} TAP=${PS2_BUTTON_TAP:-0} V4=${PS2_OBS_V4:-0} ITEMEMB=${PS2_OBS_V4_ITEMEMB:-} GRID=${PS2_OBJ_GRID_N:-} STACK=${PS2_OBS_STACK:-}"
for i in $(seq 0 $((SHARDS - 1))); do
  while [ "$(jobs -rp | wc -l)" -ge "$PAR" ]; do wait -n; done
  nice -n 15 python eval_parity.py --core "$CORE" --game "$GAME" --states ./states --slots "$SLOTS" --model "$M" \
      --stochastic --episodes "$PER" --instance $((BASE + i)) > "receipts/shards/eval_leg${N}_sealed_s${i}_out.txt" 2>&1 &
  sleep 4
done
wait
python merge_receipts.py slot --model "$M" --slot 95 --slots "$SLOTS" --per-shard "$PER" \
  --out "receipts/sealed/eval_leg${N}_sealed_out.txt" receipts/shards/eval_leg${N}_sealed_s*_out.txt || exit 1
# Desert-only subtotal (95-97), so the number can sit beside lv8mix (all Desert) without the two new stages
python - "receipts/sealed/eval_leg${N}_sealed_out.txt" <<'EOF'
import re, sys
p = sys.argv[1]; t = open(p).read()
per = {int(s): (int(w), int(n)) for s, w, n in re.findall(r"slot(\d+)=(\d+)W/(\d+)", t.split("per-slot:")[1].splitlines()[0])}
d = [per[s] for s in (95, 96, 97) if s in per]; o = [per[s] for s in (98, 99) if s in per]
line = (f"desert 95-97: {100 * sum(w for w, _ in d) / max(1, sum(n for _, n in d)):.1f}% ({sum(w for w, _ in d)}W/{sum(n for _, n in d)})"
        f"   new stages 98-99: {100 * sum(w for w, _ in o) / max(1, sum(n for _, n in o)):.1f}% ({sum(w for w, _ in o)}W/{sum(n for _, n in o)})")
open(p, "a").write(line + "\n"); print(line)
EOF
cat "receipts/sealed/eval_leg${N}_sealed_out.txt"
