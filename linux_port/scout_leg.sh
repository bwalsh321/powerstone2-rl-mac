#!/bin/bash
# scout_leg.sh <N> — per-leg fight-scouting clip (Sep 21 2026, Blake: "Totally worth it").
# Records the finished leg's bot on slot 3 (3x lv8 COM) until it has one WIN and one LOSS
# (cap 14 rounds), builds 1-fps contact sheets, copies the sheets covering the first loss
# and the first win into videos/review_leg<N>/, cuts videos/leg<N>_win.mp4 (phone size), then
# writes claude_bridge/scout_leg<N>_done.txt. The LLM review (scout_rubric.md) is done by whoever
# collects the leg: the interactive session spawns a Sonnet agent; a scheduled wake reads the
# sheets itself. Runs on instance 11 beside the next leg's training; zero footprint elsewhere.
cd "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source ~/ps2rl/bin/activate
source "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/linux_gpu_env.sh"   # Oct 1: GPU EGL on Linux (was Xvfb :99)
export SDL_AUDIODRIVER=dummy PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:. PYTHONUNBUFFERED=1 PS2_OBS_V2=1
N=$1; M=./powerstone_v6_leg${N}_league.zip
# Sep 24 2026 (obs v3; must come AFTER N is set): tmux does not pass the battery's environment; read the leg's own contract.
if awk -v n="$N" '$1==n' leg_modes.txt 2>/dev/null | grep -q "PS2_OBS_V3=1"; then export PS2_OBS_V3=1; fi
if [ "$(uname)" = "Darwin" ]; then CORE="$HOME/Library/Application Support/RetroArch/cores/flycast_libretro.dylib"; else CORE="${PS2_CORE:-$HOME/cores/flycast_libretro.so}"; fi; GAME="../Power Stone 2 (USA).chd"
mkdir -p videos claude_bridge
echo "scout leg $N start $(date)"
python -u watch_play.py --core "$CORE" --game "$GAME" --slot 3 --model "$M" --episodes 14 --stop-after-win \
  --speed 0 --no-sound --hidden --instance 11 --record "videos/leg${N}_scout_raw.mp4" > "videos/leg${N}_scout_rec.log" 2>&1
[ -s "videos/leg${N}_scout_raw.mp4" ] || { echo "scout leg $N: no recording" | tee "claude_bridge/scout_leg${N}_FAILED.txt"; exit 1; }
bash scout_frames.sh "$N" "videos/leg${N}_scout_raw.mp4" > /dev/null
python - "$N" <<'PY'
import re, shutil, os, subprocess, sys, imageio_ffmpeg
N=sys.argv[1]; log=open(f'videos/leg{N}_scout_rec.log').read()
eps=re.findall(r'\[ep\] slot3 opps=3\s+(\w+) len=\s*(\d+)', log)
ff=shutil.which('ffmpeg') or imageio_ffmpeg.get_ffmpeg_exe()   # Oct 1: system ffmpeg first (the imageio build lacks drawtext on Linux)
info=subprocess.run([ff,'-i',f'videos/leg{N}_scout_raw.mp4'],capture_output=True,text=True).stderr
h,m,s=re.search(r'Duration: (\d+):(\d+):([\d.]+)',info).groups(); dur=int(h)*3600+int(m)*60+float(s)
play=sum(int(L) for _,L in eps)*0.1; over=(dur-play)/max(len(eps),1)
# Sep 22: EXACT round boundaries from the recorder's "[cut] ep N res end_frame=F" lines (60 fps);
# the old estimate (6 frames/step) put the first loss's strip mid-fight. Fallback = the estimate.
cuts=[(r,int(f)) for r,f in re.findall(r'\[cut\] ep \d+ (\w+) end_frame=(\d+)', log)]
bounds=[]
if len(cuts)==len(eps) and cuts:
    t=0.0
    for r,f in cuts:
        a=t; t=f/60.0; bounds.append((r,a,t))
else:
    t=0
    for res,L in eps:
        a=t; t+=over+int(L)*0.1; bounds.append((res,a,t))
out=f'videos/review_leg{N}'
if os.path.isdir(out): shutil.rmtree(out)     # fresh folder every run (videos/ only)
os.makedirs(out)
picks=[]
for want in ('loss','win'):
    for i,(res,a,b) in enumerate(bounds):
        if res==want: picks.append((f'{want}_ep{i+1:02d}',a,b)); break
for tag,a,b in picks:
    for k in range(int(a//12)+1, int(b//12)+2):
        src=f'videos/scout_leg{N}/sheet_{k:02d}.png'
        if os.path.exists(src): shutil.copy(src,f'{out}/{tag}_sheet{k:03d}.png')
    if tag.startswith('win'):
        subprocess.run([ff,'-y','-loglevel','error','-ss',str(max(0,a-2)),'-to',str(b+2),'-i',f'videos/leg{N}_scout.mp4','-c','copy',f'videos/leg{N}_win.mp4'])
    # Sep 22 (Blake: "add the 4 fps strip"): the round's last 12 s at 4 fps (48 frames, 6x8 tile) so the
    # reviewer can see the KO moment that 1 fps misses; reads from the raw (60 fps) clip.
    subprocess.run([ff,'-y','-loglevel','error','-ss',str(max(0,b-12)),'-t','12','-i',f'videos/leg{N}_scout_raw.mp4',
        '-vf',"fps=4,scale=240:180:flags=neighbor,drawtext=fontfile=/System/Library/Fonts/Helvetica.ttc:text='%{pts\\:hms}':x=4:y=4:fontsize=14:fontcolor=yellow:box=1:boxcolor=black@0.6,tile=6x8",
        '-frames:v','1',f'{out}/{tag}_last12s_4fps.png'])
with open(f'{out}/episodes.txt','w') as f:
    f.write(f"rounds {len(eps)}: "+" ".join(r for r,_ in eps)+f"\nvideo {dur:.0f}s play {play:.0f}s non-play+long-press overhead ~{over:.0f}s/round\n")
    for tag,a,b in picks: f.write(f"{tag}: {a:.0f}-{b:.0f}s\n")
    f.write("stats lines:\n"+"\n".join(l for l in log.splitlines() if l.startswith('[ep]'))+"\n")
print(f"review sheets: {len(os.listdir(out))-1}; picks {[(t,round(a),round(b)) for t,a,b in picks]}")
PY
rm -f "videos/leg${N}_scout_raw.mp4"
echo DONE > "claude_bridge/scout_leg${N}_done.txt"
echo "scout leg $N end $(date)"
