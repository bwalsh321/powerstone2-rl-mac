"""E16b: stage-id diff using the saved stage_*.state files + slot1/2/3 (desert)."""
from harness import *
br = boot()
groups = {"iceberg": ["c0", "rr"], "space": ["r"], "desertA": ["d"], "ship": ["dd", "u"], "pharaoh": ["rd"], "garden": ["rdd"]}
S = {}
for g, ns in groups.items():
    for n in ns:
        load(br, os.path.join(HERE, f"stage_{n}.state")); a = snap(br); br.run_frames(45); b = snap(br)
        S[(g, n)] = (a, b)
for s in (1, 2, 3):
    load(br, f"states/slot{s}.state"); br.run_frames(400); a = snap(br); br.run_frames(45); b = snap(br)
    S[("desertA", f"slot{s}")] = (a, b)
keys = list(S)
ok = np.ones(len(S[keys[0]][0]), bool)
for k in keys: ok &= S[k][0] == S[k][1]
gnames = list(groups)
for (g, n) in keys:
    rep = [k for k in keys if k[0] == g][0]
    ok &= S[(g, n)][0] == S[rep][0]
reps = np.stack([S[[k for k in keys if k[0] == g][0]][0] for g in gnames])
cand = np.nonzero(ok)[0]
sub = reps[:, cand]
dist = np.array([len(np.unique(sub[:, k])) for k in range(sub.shape[1])])
best = cand[(dist == len(gnames))]
print("groups", gnames)
print("u8 candidates constant within stage (incl. 3 desert slots), distinct across 6 stages:", len(best))
small = [j for j in best if 0x400000 <= j < 0x480000 or 0x530000 <= j < 0x560000]
for j in small[:80]: print(f"  {0x8C000000+j:08X}", reps[:, j].tolist())
print("first 20 any-value:", [f"{0x8C000000+j:08X}" for j in best[:20]])
print("DONE"); sys.stdout.flush(); os._exit(0)
