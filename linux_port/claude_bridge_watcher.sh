#!/bin/bash
# Claude command bridge — Aug 29 2026. Runs on the Mac inside tmux.
# Claude (Cowork session) drops claude_bridge/cmd.sh via the mounted folder;
# this loop runs it and writes stdout+stderr to claude_bridge/out.txt.
# Stop with: tmux kill-session -t claudebridge
cd "$(dirname "$0")"
mkdir -p claude_bridge
echo "watcher up $(date)" > claude_bridge/watcher.log
while true; do
  if [ -f claude_bridge/cmd.sh ]; then
    mv claude_bridge/cmd.sh claude_bridge/running.sh
    echo "=== $(date) ===" >> claude_bridge/watcher.log
    bash claude_bridge/running.sh > claude_bridge/out.txt 2>&1
    echo "exit=$?" >> claude_bridge/out.txt
    mv claude_bridge/running.sh claude_bridge/last.sh
    touch claude_bridge/done.flag
  fi
  sleep 2
done
