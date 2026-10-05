"""Per-state-byte statistics from a census run."""
import sys, struct, numpy as np, collections
tag = sys.argv[1]
R = np.load(f"data_census_{tag}.npy", mmap_mode="r")
N = R.shape[0]
st = np.asarray(R[:, :, 0x3715]).astype(int)
prev = np.asarray(R[:, :, 0x3716]).astype(int)
act = np.asarray(R[:, :, 0x3818:0x381A]).copy().view("<u2")[..., 0].astype(int)
fl = lambda o: np.asarray(R[:, :, o:o+4]).copy().view("<f4")[..., 0]
u32 = lambda o: np.asarray(R[:, :, o:o+4]).copy().view("<u4")[..., 0]
y = fl(0x2C); vx, vy, vz = fl(0x4C), fl(0x50), fl(0x54); hp = fl(0x160)
gnd = u32(0x404); f134 = u32(0x134)
stun = np.asarray(R[:, :, 0x3822:0x3824]).copy().view("<u2")[..., 0]
print(f"{'st':>3} {'frames':>6} {'eps':>4} {'dur med/p90/max':>16} {'air%':>5} {'gnd0%':>5} {'|vh|':>5} {'vy':>6} seats  top acts  -> next states")
for s in sorted(set(st.ravel())):
    m = st == s
    durs = []; nxt = collections.Counter(); seats = collections.Counter()
    for i in range(4):
        col = st[:, i]; t = 0
        while t < N:
            if col[t] == s:
                t0 = t
                while t < N and col[t] == s: t += 1
                if t0 > 0 and t < N: durs.append(t - t0); nxt[int(col[t])] += 1
                seats[i+1] += 1
            else: t += 1
    acts = collections.Counter(act[m].tolist()).most_common(6)
    d = np.array(durs) if durs else np.array([0])
    vh = np.hypot(vx[m], vz[m])
    print(f"{s:3d} {m.sum():6d} {len(durs):4d} {int(np.median(d)):5d}/{int(np.percentile(d,90)):4d}/{d.max():4d}"
          f" {100*(y[m]>5).mean():5.0f} {100*(gnd[m]==0).mean():5.0f} {np.nanmean(vh):5.1f} {np.nanmean(vy):6.1f} "
          f"{dict(seats)} {[hex(a)+':'+str(c) for a,c in acts]} -> {dict(nxt.most_common(5))}")
