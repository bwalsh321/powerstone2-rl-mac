"""S22: dynamic stage state. Both players idle on <stage> for N frames; sample every 120 f: P2 y/state, the stage-id cells,
and a RAM float window. Find floats (outside player structs) that track P2's grounded y (the moving floor / elevator) and
small ints that step when the floor level changes (phase counter). Usage: s22_stage_phase.py <stage> <frames>"""
from common import *
stage, N = sys.argv[1], int(sys.argv[2])
LO, HI = 0x300000, 0x600000
br = boot()
load(br, STAGE_STATES[stage]); br.run_frames(10)
F, Y, S, E, W = [], [], [], [], []
for k in range(N // 120):
    br.run_frames(120)
    r = br.ram
    F.append(np.frombuffer(r[LO:HI].tobytes(), "<f4").copy())
    Y.append(logpos(r, 1)[1]); S.append(pstate(r, 1)); E.append(f32(r, 0x8C471A78)); W.append([u32(r, 0x8C471A60 + 4 * j) for j in range(12)])
F = np.stack(F); Y = np.array(Y); S = np.array(S)
print(f"{stage}: P2 y over time (every 1200 f):", np.round(Y[::10]).astype(int).tolist())
print("   P2 state every 1200 f:", S[::10].tolist())
print("   0x8C471A78 (stage floor/elevator y) every 1200 f:", np.round(np.array(E)[::10]).astype(int).tolist())
W = np.array(W); chg = [j for j in range(12) if len(np.unique(W[:, j])) > 1]
print("   words 0x8C471A60+4j that change:", {hex(0x8C471A60 + 4 * j): np.unique(W[:, j]).tolist()[:8] for j in chg})
lv = np.unique(np.round(Y / 50) * 50)
print("   distinct y levels:", lv.tolist())
if Y.std() > 10:
    G = np.where(np.isfinite(F) & (np.abs(F) < 1e6), F, 0).astype(np.float32)
    yc = Y - Y.mean(); Gc = G - G.mean(0)
    c = (Gc * yc[:, None]).sum(0) / (np.sqrt((Gc ** 2).sum(0) * (yc ** 2).sum()) + 1e-9)
    pl_lo, pl_hi = ((P0 & 0xFFFFFF) - LO) // 4, (((P0 + 4 * PSTRIDE) & 0xFFFFFF) - LO) // 4
    c[pl_lo:pl_hi] = 0
    top = np.argsort(-c)[:20]
    for i in top:
        err = np.abs(G[:, i] - Y)
        print(f"   {0x8C000000+LO+4*i:08X} corr {c[i]:.3f}  mean|v-y| {err.mean():8.1f}  samples {np.round(G[::15, i]).astype(int).tolist()}")
print("DONE")
