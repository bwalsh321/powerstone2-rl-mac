#!/bin/bash
# relay_boot.sh — bring the 9950X relay back after a reboot or power loss (Oct 6 2026, audit: nothing restarted it).
# Run from the user crontab:  @reboot bash /home/superserver/powerstone2-rl-mac/linux_port/relay_boot.sh
#   1. starts the relay watcher (tmux "relay") if it is not running;
#   2. if the current leg was interrupted mid-training (log without "leg complete", no trainer, no battery),
#      archives the partial log and relaunches the leg from its warm zip (a leg restarts from scratch; the
#      one-shot surgeries are idempotent);
#   3. if a battery was interrupted (lock dir, no done/FAILED marker, no bat<N> session), renames the lock so the
#      watcher reruns the battery.
# Respects league_trainer.txt = hold and host_role.txt != train (then it only starts the watcher).
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
log() { echo "[boot $(date '+%F %r')] $*" | tee -a wrapper_league.log; }
sleep "${PS2_BOOT_DELAY:-90}"                    # let the NVIDIA driver and the network come up
INHIBIT="systemd-inhibit --what=sleep:idle --who=ps2rl"
log "relay_boot after reboot (uptime $(cut -d' ' -f1 /proc/uptime)s)"
if ! tmux has-session -t relay 2>/dev/null; then
  tmux new -s relay -d "$INHIBIT --why=league bash $(pwd)/relay_watch_linux.sh" && log "relay watcher started"
fi
read N PREV < league_state.txt
MODE="$(tr -d '[:space:]' < league_trainer.txt 2>/dev/null)"
ROLE="$(tr -d '[:space:]' < host_role.txt 2>/dev/null)"
TRAINING="$(pgrep -f 'train_selfplay_asyn[c]' | wc -l | tr -d ' ')"
if [ "$ROLE" != "train" ] || [ "$MODE" = "hold" ]; then
  log "role=$ROLE mode=$MODE: watcher only, no leg relaunch"; exit 0
fi
if [ -d "claude_bridge/battery_leg${N}.lock" ] && [ ! -f "claude_bridge/battery_leg${N}_done.txt" ] \
   && [ ! -f "claude_bridge/battery_leg${N}_FAILED.txt" ] && ! tmux has-session -t "bat${N}" 2>/dev/null; then
  mv "claude_bridge/battery_leg${N}.lock" "claude_bridge/battery_leg${N}.lock.interrupted_$(date +%s)"
  log "leg $N battery was interrupted; lock moved aside, the watcher reruns it"
  exit 0
fi
if [ "$TRAINING" -eq 0 ] && ! tmux has-session -t ps2train 2>/dev/null && ! tmux has-session -t "bat${N}" 2>/dev/null \
   && ! { [ -f "train_leg${N}_out.txt" ] && grep -q "leg complete" "train_leg${N}_out.txt"; }; then
  mkdir -p archive
  [ -f "train_leg${N}_out.txt" ] && mv "train_leg${N}_out.txt" "archive/train_leg${N}_out_interrupted_$(date +%Y%m%d_%H%M).txt"
  tmux new -s ps2train -d "$INHIBIT --why=league-leg bash $(pwd)/league_leg_async.sh" \
    && log "leg $N was interrupted mid-training; relaunched from $PREV"
fi
