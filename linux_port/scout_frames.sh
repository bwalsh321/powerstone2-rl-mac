#!/bin/bash
# scout_frames.sh <leg> <input.mp4> — one frame per second into 4x3 contact sheets (12 s each)
# under videos/scout_leg<N>/sheet_NN.png, plus a phone-size copy of the clip. For the Sonnet
# fight-review sub-agent (Sep 21 2026). Zero footprint.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source ~/ps2rl/bin/activate
N=$1; IN=$2; OUT=videos/scout_leg$N; mkdir -p "$OUT"
FF="$(command -v ffmpeg || python -c 'import imageio_ffmpeg;print(imageio_ffmpeg.get_ffmpeg_exe())')"   # Oct 1: system ffmpeg first (drawtext)
"$FF" -y -loglevel error -i "$IN" -vf "fps=1,scale=320:240:flags=neighbor,drawtext=fontfile=/System/Library/Fonts/Helvetica.ttc:text='%{pts\:hms}':x=4:y=4:fontsize=16:fontcolor=yellow:box=1:boxcolor=black@0.6,tile=4x3" "$OUT/sheet_%02d.png"
"$FF" -y -loglevel error -threads 2 -i "$IN" -vf "scale=480:360:flags=neighbor,fps=30" -c:v libx264 -preset medium -crf 30 -pix_fmt yuv420p -c:a aac -b:a 64k "videos/leg${N}_scout.mp4"
ls "$OUT" | wc -l | tr -d ' '
