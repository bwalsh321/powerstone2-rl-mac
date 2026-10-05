"""E15: pause flag. base_s1: 4 snaps while fighting, press START, 4 snaps paused, press START, 4 snaps."""
from harness import *
br = boot(); load(br, os.path.join(HERE, "base_s1.state"))
S = []; L = []
for k in range(4): br.run_frames(15); S.append(snap(br)); L.append(0)
br.press(BTN["start"], 3, player=0); br.press(0, 30, player=0)
shot(br, os.path.join(HERE, "shots/e15_paused.png"))
for k in range(4): br.run_frames(15); S.append(snap(br)); L.append(1)
br.press(BTN["start"], 3, player=0); br.press(0, 30, player=0)
for k in range(4): br.run_frames(15); S.append(snap(br)); L.append(0)
shot(br, os.path.join(HERE, "shots/e15_unpaused.png"))
S = np.stack(S); L = np.array(L)
fc = [struct.unpack_from("<I", s, 0x475200)[0] for s in S]
print("fight frame counter 0x8C475200:", fc)
ok = np.ones(S.shape[1], bool)
for g in (0, 1):
    idx = np.nonzero(L == g)[0]; ok &= np.all(S[idx] == S[idx[0]], axis=0)
m = ok & (S[0] != S[4])
print("bytes constant within phase, differ paused vs fighting:", m.sum())
for j in np.nonzero(m)[0][:40]:
    print(f"  {0x8C000000+j:08X} fight={S[0,j]:#04x} paused={S[4,j]:#04x}")
print("DONE"); sys.stdout.flush(); os._exit(0)
