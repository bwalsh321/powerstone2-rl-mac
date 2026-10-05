"""Menu driver: m_drive.py STATE 'p1:btn:frames,wait:n,shot:name,save:path' (paths relative to this folder)."""
from harness import *
br = boot(); st = sys.argv[1]
load(br, st if os.path.isabs(st) or st.startswith("states") else (os.path.join(LP, st) if st.startswith("menu_") else os.path.join(HERE, st)))
os.makedirs(os.path.join(HERE, "shots/md"), exist_ok=True)
for step in sys.argv[2].split(","):
    p = step.split(":")
    if p[0] in ("p1", "p2"):
        m = 0
        for b in p[1].split("+"): m |= BTN[b]
        br.press(m, int(p[2]), player=0 if p[0] == "p1" else 1); br.press(0, 6, player=0 if p[0] == "p1" else 1)
    elif p[0] == "wait": br.run_frames(int(p[1]))
    elif p[0] == "shot": shot(br, os.path.join(HERE, "shots/md", p[1] + ".png")); print("shot", p[1], "fightctr", u32(snap(br), 0x8C475200))
    elif p[0] == "save":
        with gzip.open(os.path.join(HERE, p[1]), "wb") as fh: fh.write(br.emu.get_state())
        print("saved", p[1])
print("DONE"); sys.stdout.flush(); os._exit(0)
