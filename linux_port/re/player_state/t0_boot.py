from harness import *
br = boot(); load(br, "states/slot1.state")
r = snap(br)
for i in range(4):
    print(i, "hp", f32(r, A.HEALTH[i]), "pos", [round(f32(r, MAT[i]+o),1) for o in A.MAT_POS], "F", hex(u32(r, F[i])))
shot(br, os.path.join(HERE, "shots", "t0.png"))
sys.stdout.flush(); os._exit(0)
