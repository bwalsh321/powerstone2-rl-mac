"""AN14: compare the clean desert ground probe against the analytic model (box +-1140, 4 poles r75, 8 clusters ~r120)."""
import numpy as np
d = np.load("data/s14_desert_ground.npz"); xs, zs, res = d["xs"], d["zs"], d["res"]
X, Z = np.meshgrid(xs, zs)
disp = np.hypot(res[..., 0] - X, res[..., 2] - Z)
poles = [(-1000, -1000), (950, -850), (100, 1000), (-1050, 800)]
clus = [(-500, 1000), (100, -900), (300, -1100), (-850, 1000), (-650, 1050), (-1000, -100), (-900, 100), (-1100, 300)]
outside = (np.abs(X) > 1140) | (np.abs(Z) > 1140)
dp = np.min([np.hypot(X - a, Z - b) for a, b in poles], 0)
dc = np.min([np.hypot(X - a, Z - b) for a, b in clus], 0)
model = outside | (dp < 75) | (dc < 125)
moved = disp > 2
print("moved:", moved.sum(), " model-blocked:", model.sum(), " agree:", (moved == model).mean().round(4))
print("moved but model free:", (moved & ~model).sum(), "   model blocked but not moved:", (~moved & model).sum())
for a, b in [(int(X[i]), int(Z[i])) for i in zip(*np.nonzero(moved & ~model))][:20]: print("   unexplained push at", a, b)
# pole pushout distance & cluster pushout distances
fp = np.hypot(res[..., 0][dp < 75] - 0, 0)
for (a, b) in poles:
    m = np.hypot(X - a, Z - b) < 70
    print(f"pole ({a},{b}): final dist from centre min/max {np.hypot(res[...,0][m]-a, res[...,2][m]-b).min():.1f}/{np.hypot(res[...,0][m]-a, res[...,2][m]-b).max():.1f}")
for (a, b) in clus[:3]:
    m = (np.hypot(X - a, Z - b) < 130) & moved
    r = np.hypot(X[m] - a, Z[m] - b)
    print(f"cluster ({a},{b}): displaced probes up to start-radius {r.max():.0f}")
