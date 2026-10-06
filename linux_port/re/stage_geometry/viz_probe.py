"""Visualise a s05 probe npz: displacement magnitude, final y, state. Usage: viz_probe.py tag"""
import sys, numpy as np
from imgutil import heat, hstack
tag = sys.argv[1]
d = np.load(f"data/s05_{tag}.npz"); xs, res = d["xs"], d["res"]
dx = res[..., 0] - xs[None, :]; dz = res[..., 2] - xs[:, None]
disp = np.hypot(dx, dz)
sc = max(1, 480 // len(xs))
hstack([heat(np.minimum(disp, 150), 0, 150, sc, title=f"{tag} xz-disp"),
        heat(res[..., 1], float(res[..., 1].min()), float(res[..., 1].max()), sc, title="final y"),
        heat(res[..., 3], 0, 40, sc, title="state")]).save(f"shots/viz_{tag}.png")
print("saved")
