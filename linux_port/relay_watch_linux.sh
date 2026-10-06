#!/bin/bash
# relay_watch_linux.sh — the 9950X relay's leg -> battery link (Oct 1 2026).
# On the Mac a Claude session started each battery (SESSION_HANDOFF sec 4). Here a tmux loop does
# it with the same guards: leg N's log says "leg complete", no trainer alive, no bat<N> session,
# no battery lock/done marker. league_battery.sh then evaluates, advances league_state.txt and
# (unless league_trainer.txt = hold or the hold gate fires) launches leg N+1 in tmux ps2train.
#   tmux new -s relay -d "systemd-inhibit --what=sleep:idle --who=ps2rl --why=league bash relay_watch_linux.sh"
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
log() { echo "[relay $(date '+%F %r')] $*" | tee -a wrapper_league.log; }
log "watcher up"
while true; do
  read N PREV < league_state.txt
  if [ -f "train_leg${N}_out.txt" ] && grep -q "leg complete" "train_leg${N}_out.txt" \
     && [ "$(pgrep -f 'train_selfplay_asyn[c]' | wc -l | tr -d ' ')" -eq 0 ] \
     && ! tmux has-session -t "bat${N}" 2>/dev/null \
     && [ ! -d "claude_bridge/battery_leg${N}.lock" ] && [ ! -f "claude_bridge/battery_leg${N}_done.txt" ]; then
    log "leg $N complete -> battery (tmux bat${N})"
    tmux new -s "bat${N}" -d "bash $(pwd)/league_battery.sh > claude_bridge/battery_leg${N}.log 2>&1"
  fi
  sleep 60
done
