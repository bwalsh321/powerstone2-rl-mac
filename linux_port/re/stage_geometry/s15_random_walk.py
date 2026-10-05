"""S15: long random-walk drive of P2 (goal 1: empirical walkability). Usage: s15_random_walk.py <stage> <tag> <frames> [seed]
P1 is left idle (human seat, no input). P2 holds a random 8-way dpad direction for 20-90 f; 15% of segments add a jump (A)
at a random point. Logged per frame: P2 logical xyz, state byte, dpad mask, P2 health. -> data/s15_<tag>.npz
Stall detection (wall contact) is done offline (an15)."""
from common import *
stage, tag, N = sys.argv[1], sys.argv[2], int(sys.argv[3])
rng = np.random.default_rng(int(sys.argv[4]) if len(sys.argv) > 4 else 0)
DIRS = ["up", "down", "left", "right", "up+left", "up+right", "down+left", "down+right"]
br = boot()
load(br, STAGE_STATES[stage]); br.run_frames(10)
log = np.zeros((N, 6), np.float32)
t = 0
while t < N:
    d = DIRS[rng.integers(8)]; n = int(rng.integers(20, 90)); jump_at = int(rng.integers(0, n)) if rng.random() < 0.15 else -1
    for k in range(n):
        if t >= N: break
        setpad(br, d + ("+a" if 0 <= k - jump_at < 6 else ""), 1)
        br.emu.run()
        r = br.ram; p = logpos(r, 1)
        log[t] = (p[0], p[1], p[2], pstate(r, 1), mask_of(d), health(r, 1))
        t += 1
        if t % 20000 == 0:      # long runs: the round timer / a KO can end the match -> reload
            load(br, STAGE_STATES[stage]); br.run_frames(2)
np.savez_compressed(f"data/s15_{tag}.npz", log=log, stage=stage)
print(f"{tag}: {N} frames  x {log[:,0].min():.0f}..{log[:,0].max():.0f}  z {log[:,2].min():.0f}..{log[:,2].max():.0f}  y {log[:,1].min():.0f}..{log[:,1].max():.0f}")
print("DONE")
