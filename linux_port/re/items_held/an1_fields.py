"""Field analysis over pickup-event object dumps: per word offset, the
number of distinct values across events, restricted to non-stage objects."""
import sys, glob, numpy as np, collections
fs = sys.argv[1:] or glob.glob("ev/*_dumps.npz")
O = []; M = []
for f in fs:
    z = np.load(f); O.append(z["obj"]); M.append(z["meta"])
O = np.concatenate(O); M = np.concatenate(M)
W = O.view("<u4")
vt = W[:, 2]
print("vt counts", collections.Counter(f"{v:08x}" for v in vt))
sel = vt != 0x0C0F1688
Ws = W[sel]
print("n events (non-stage):", len(Ws))
for k in range(Ws.shape[1]):
    c = collections.Counter(Ws[:, k].tolist())
    if 2 <= len(c) <= 12 and max(c.values()) < len(Ws):
        print(f"+{k*4:#05x}", " ".join(f"{v:08x}:{n}" for v, n in c.most_common()))
