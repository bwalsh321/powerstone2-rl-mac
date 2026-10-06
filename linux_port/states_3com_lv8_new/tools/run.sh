#!/bin/bash
cd /home/superserver/powerstone2-rl-mac/linux_port
source ./linux_gpu_env.sh; source ~/ps2rl/bin/activate
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:. OMP_NUM_THREADS=1
exec nice -n 15 python /tmp/claude-1000/stamp60/drive.py "$@"
