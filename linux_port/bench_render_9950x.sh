#!/bin/bash
# usage: [env VAR=..] bash bench_render_9950x.sh N [FRAMES]  -> aggregate fps of N parallel instances
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source ./linux_gpu_env.sh; source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl/p4:. PYTHONUNBUFFERED=1
N=$1; F=${2:-3000}
for i in $(seq 0 $((N-1))); do python bench_render_9950x.py $i $F 2>/dev/null | grep fps= & done | awk -F'fps=' '{s+=$2; n++} END {printf "N=%d aggregate_fps=%.0f per_instance=%.0f\n", n, s, s/n}'
