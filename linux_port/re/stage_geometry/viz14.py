"""Visualise s14 npz: xz displacement, final y, state, health delta. Usage: viz14.py tag"""
import sys, numpy as np
from imgutil import heat, hstack
tag = sys.argv[1]
d = np.load(f"data/s14_{tag}.npz"); xs, zs, res = d["xs"], d["zs"], d["res"]
disp = np.hypot(res[..., 0] - xs[None, :], res[..., 2] - zs[:, None])
sc = max(1, 400 // max(len(xs), len(zs)))
y = res[..., 1]
hstack([heat(np.minimum(disp, 150), 0, 150, sc, title=f"{tag} xz-disp"),
        heat(y, float(np.nanmin(y)), float(np.nanmax(y)) + 1e-3, sc, title="final y"),
        heat(res[..., 3], 0, 40, sc, title="state"),
        heat(-res[..., 4], 0, 100, sc, title="dmg")]).save(f"shots/viz14_{tag}.png")
print("saved", f"shots/viz14_{tag}.png")
