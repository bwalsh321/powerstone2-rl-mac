"""verify.py <slots> <instance> -- RAM check of the sealed savestates (Oct 17 2026), run from linux_port/ with the venv,
linux_gpu_env.sh and PYTHONPATH=../sdlarch-rl/p4:../sdlarch-rl:. Each states/slot<N>.state is loaded fresh and checked:
seat table 0x8C472DA8 + 0x14k (P1/P3/P4 = COM with the planned character, P2 = HUMAN Falcon), the global difficulty
cell 0x8C472AD4 and the AI copies 0x8C5429AD / 0x8C5429C8 = 7 (level 8, 0-based) at load (0x8C4683A6 / 0x8C46C3D4 are
transient during the intro, as in the Oct 6 README), the stage id G_STAGE 0x8C46E198 900 frames in (obs_v4_reader:
0 Blue sky, 1 Dark castle, 5 Desert) and P2 face_norm. 90/91 are accepted as controls.
"""
import gzip, math, os, sys
import numpy as np
from flycast_bridge import FlycastBridge
from ps2_ram import StateLineSynth
NAMES = {0:"Falcon",1:"Ryoma",2:"Wang-Tang",3:"Jack",4:"Gunrock",5:"Galuda",6:"Ayame",7:"Rouge",8:"Pete",9:"Gourmand",10:"Julia",11:"Accel",14:"Mel",15:"Pride"}
STAGES = {0:"Blue sky",1:"Dark castle",2:"Tomb",3:"Iceberg",4:"Space station",5:"Desert",6:"Chaos"}
PLAN = {95:("Jack","Accel","Wang-Tang",5), 96:("Mel","Falcon","Ayame",5), 97:("Gourmand","Pete","Rouge",5),
        98:("Ryoma","Gunrock","Wang-Tang",0), 99:("Pride","Galuda","Accel",1),
        90:("Gunrock","Julia","Mel",5), 91:("Galuda","Gunrock","Pete",5)}
slots = [int(x) for x in sys.argv[1].split(",")]; inst = int(sys.argv[2])
br = FlycastBridge(os.path.expanduser("~/cores/flycast_libretro.so"), "../Power Stone 2 (USA).chd", "./states", instance_id=inst)
synth = StateLineSynth(br.ram, bot_player=2); br.attach_synth(synth)
br.run_frames(8)
def rd():
    r = np.asarray(br.ram, dtype=np.uint8); u32 = lambda o: int.from_bytes(bytes(r[o:o+4]), "little")
    diff = [int(r[o]) for o in (0x472AD4, 0x4683A6, 0x46C3D4, 0x5429AD, 0x5429C8)]
    seats = []
    for k in range(4):
        b = 0x472DA8 + 0x14 * k
        seats.append((["HUM","COM","EMPTY"][u32(b)] if u32(b) < 3 else u32(b), NAMES.get(u32(b+8), u32(b+8))))
    return diff, seats, u32(0x472CF8), u32(0x46E198), u32(0x475200)
allok = True
for s in slots:
    with gzip.open(f"./states/slot{s}.state", "rb") as f:
        br.emu.set_state(f.read())
    br.run_frames(8)
    d0, seats, area, gst, live0 = rd()
    v = [float(x) for x in synth.line.split(",")]
    fn = math.hypot(v[5+5+3], v[5+5+4])   # P2 face_norm
    br.run_frames(900)
    d1, seats1, area1, gst1, live1 = rd()
    p1, p3, p4, st = PLAN[s]
    ok = (seats == [("COM", p1), ("HUM", "Falcon"), ("COM", p3), ("COM", p4)] and d0[0] == 7 and d0[3] == 7 and d0[4] == 7
          and gst1 == st and seats1 == seats)
    allok &= ok
    print(f"slot{s}: {'PASS' if ok else 'FAIL'} seats={seats} diff@load={d0} diff@+900={d1} area_id={area}/{area1} "
          f"G_STAGE@+900={gst1} ({STAGES.get(gst1)}) expect {STAGES[st]}  P2 face_norm={fn:.3f}", flush=True)
print("ALL PASS" if allok else "SOME FAIL", flush=True)
os._exit(0)
