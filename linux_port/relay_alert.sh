#!/bin/bash
# relay_alert.sh — relay watchdog (Oct 6 2026, audit: crashes, failed batteries and holds were silent).
# Run from the user crontab every 15 min:  */15 * * * * bash /home/superserver/powerstone2-rl-mac/linux_port/relay_alert.sh
# Writes new problems to claude_bridge/ALERT.txt (the hourly Claude check reads it). If claude_bridge/ntfy_topic.txt
# exists (Blake's opt-in), each new alert is also pushed to https://ntfy.sh/<topic>.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SEEN=claude_bridge/alert_seen.txt; touch "$SEEN"
alert() {   # alert <key> <message>: once per key
  grep -qxF "$1" "$SEEN" && return
  echo "$1" >> "$SEEN"
  echo "[alert $(date '+%F %r')] $2" | tee -a claude_bridge/ALERT.txt >> wrapper_league.log
  T=""; [ -f claude_bridge/ntfy_topic.txt ] && T="$(tr -d "[:space:]" < claude_bridge/ntfy_topic.txt)"
  [ -n "$T" ] && curl -s -m 10 -H "Title: Power Stone relay" -d "$2" "https://ntfy.sh/$T" >/dev/null
}
read N PREV < league_state.txt
MODE="$(tr -d '[:space:]' < league_trainer.txt 2>/dev/null)"
for f in claude_bridge/battery_leg*_FAILED.txt; do [ -f "$f" ] && alert "$f" "battery failed: $f ($(head -1 "$f"))"; done
for f in claude_bridge/hold_leg*.txt; do [ -f "$f" ] && alert "$f" "hold gate fired: $(head -1 "$f")"; done
grep -E "halting|out of attempts|REFUSED" wrapper_league.log | tail -3 | while read -r l; do alert "wrap:$l" "wrapper: $l"; done
[ -f "train_leg${N}_out.txt" ] && grep -qE "Traceback|ACTOR DIED" "train_leg${N}_out.txt" && alert "trace:$N" "leg $N training log has a Traceback/ACTOR DIED"
TRAINING="$(pgrep -f 'train_selfplay_asyn[c]' | wc -l | tr -d ' ')"
BATTERY="$(tmux ls 2>/dev/null | grep -c '^bat')"
STALL=claude_bridge/alert_idle_since.txt
if [ "$TRAINING" -eq 0 ] && [ "$BATTERY" -eq 0 ] && [ "$MODE" != "hold" ]; then
  [ -f "$STALL" ] || date +%s > "$STALL"
  [ $(( $(date +%s) - $(cat "$STALL") )) -ge 1800 ] && alert "idle:$N:$(cat "$STALL")" "relay idle 30+ min at leg $N: no trainer, no battery, mode=$MODE"
else
  rm -f "$STALL"
fi
if [ "$TRAINING" -gt 0 ] && [ -f "train_leg${N}_out.txt" ] \
   && [ $(( $(date +%s) - $(stat -c %Y "train_leg${N}_out.txt") )) -ge 1800 ]; then
  alert "stale:$N:$(stat -c %Y "train_leg${N}_out.txt")" "leg $N trainer alive but its log has not moved for 30+ min (hung?)"
fi
[ -f /var/run/reboot-required ] && alert "reboot:$(stat -c %Y /var/run/reboot-required)" "OS asks for a reboot (do it between legs; relay_boot.sh brings the relay back)"
